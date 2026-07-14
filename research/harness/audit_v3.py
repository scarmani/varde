#!/usr/bin/env python3
"""Generate and analyze the deterministic 2,000-position Varde V3 audit."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
import hashlib
import math
import os
from pathlib import Path
import random
import subprocess
import sys
import time


REPO_ROOT = Path(__file__).resolve().parents[2]
ENGINE_ROOT = REPO_ROOT / "engine"
HARNESS_ROOT = Path(__file__).resolve().parent
if str(ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(ENGINE_ROOT))
if str(HARNESS_ROOT) not in sys.path:
    sys.path.insert(0, str(HARNESS_ROOT))

from varde import BLACK, WHITE, Game, Illegal, control, other, resolve  # noqa: E402
from learning import FEATURE_NAMES  # noqa: E402
from opponent import (  # noqa: E402
    BALANCED_WEIGHTS,
    choose_decision,
    normalized_transition_features,
    normalized_v3_features,
)
from map_elites_v3 import (  # noqa: E402
    WATCHDOG_MULTIPLIER,
    derive_seed,
    stable_hash,
    write_json_atomic,
)


FORMAT = "varde-evaluator-audit"
VERSION = 3
RECIPE = "v3-audit-2000"
POLICIES = ("random", "epsilon", "casual", "standard")
BOARD_POSITION_TOTALS = {3: 800, 4: 600, 5: 400, 6: 200}
SAMPLES_PER_GAME = 10
V3_CANDIDATES = (
    "control_resilience",
    "latent_reserves",
    "sky_durability",
    "connection",
    "capturing_moves",
    "max_capture",
    "covers",
    "hostile_covers",
    "reinforcements",
    "summits",
)
TRANSITION_CANDIDATES = V3_CANDIDATES[4:]


@dataclass(frozen=True)
class SimpleDecision:
    action: str
    point: tuple | None = None
    elapsed_ms: float = 0.0


def source_commit():
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def code_hash():
    digest = hashlib.sha256()
    for path in (Path(__file__), ENGINE_ROOT / "opponent.py"):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def audit_jobs(seed):
    jobs = []
    for n, total in BOARD_POSITION_TOTALS.items():
        per_policy = total // len(POLICIES)
        if per_policy % SAMPLES_PER_GAME:
            raise RuntimeError("audit quota does not divide into game groups")
        for policy in POLICIES:
            for ordinal in range(per_policy // SAMPLES_PER_GAME):
                jobs.append(
                    {
                        "n": n,
                        "policy": policy,
                        "ordinal": ordinal,
                        "seed": derive_seed(seed, "audit-game", n, policy, ordinal),
                    }
                )
    return jobs


def _random_decision(game, rng):
    started = time.perf_counter()
    legal = game.legal_placements()
    should_pass = (
        game.moves_played > 0
        and game.moves_played >= len(game.board.points)
        and rng.random() < 0.18
    )
    if not legal or should_pass:
        return SimpleDecision(
            "pass", elapsed_ms=(time.perf_counter() - started) * 1000
        )
    return SimpleDecision(
        "play",
        legal[rng.randrange(len(legal))],
        (time.perf_counter() - started) * 1000,
    )


def _policy_decision(game, policy, rng, seed):
    if policy == "random":
        return _random_decision(game, rng)
    if (
        policy == "epsilon"
        and game.moves_played < 0.6 * len(game.board.points)
        and rng.random() < 0.10
    ):
        return _random_decision(game, rng)
    difficulty = "standard" if policy == "standard" else "casual"
    return choose_decision(
        game,
        game.to_move,
        difficulty,
        seed=derive_seed(seed, "seat", game.to_move),
    )


def _transitions(board, state, color):
    transitions = []
    for point in board.points:
        try:
            next_state, captured = resolve(
                board, state, point, color, set()
            )
        except Illegal:
            continue
        transitions.append((point, next_state, captured))
    return transitions


def _swap_state(state):
    return {
        point: tuple(other(stone) for stone in stack)
        for point, stack in state.items()
    }


def _feature_row(board, snapshot, group_id, policy, outcome, margin):
    state = snapshot["state"]
    moves = snapshot["moves_played"]
    structural = normalized_v3_features(board, state, moves)
    black_transitions = _transitions(board, state, BLACK)
    white_transitions = _transitions(board, state, WHITE)
    transitions = normalized_transition_features(
        board, state, black_transitions, white_transitions
    )
    features = dict(structural)
    features.update(transitions)

    swapped = _swap_state(state)
    swapped_structural = normalized_v3_features(board, swapped, moves)
    swapped_transitions = normalized_transition_features(
        board,
        swapped,
        _transitions(board, swapped, BLACK),
        _transitions(board, swapped, WHITE),
    )
    swapped_features = dict(swapped_structural)
    swapped_features.update(swapped_transitions)
    symmetry_error = max(
        abs(features[name] + swapped_features[name]) for name in features
    )
    return {
        "group_id": group_id,
        "board_size": board.n,
        "policy": policy,
        "moves_played": moves,
        "outcome": outcome,
        "margin": margin,
        "features": features,
        "symmetry_error": symmetry_error,
    }


def play_audit_game(job):
    n = job["n"]
    policy = job["policy"]
    seed = job["seed"]
    rng = random.Random(seed)
    game = Game(n)
    identities = {BLACK: "A", WHITE: "B"}
    accepted = set()
    snapshots = []
    actions = 0
    captures = 0
    placements = 0
    contacts = 0
    friendly_contacts = 0
    vertical = 0
    hostile_covers = 0
    reinforcements = 0
    swaps = 0
    heat = Counter()
    latencies = []
    error = None
    watchdog = WATCHDOG_MULTIPLIER * len(game.board.points)

    try:
        while actions < watchdog:
            if game.finished:
                if game.resumption_used:
                    actions += 1  # One seat accepts the post-resumption ending.
                    break
                score = game.score()
                ordered = (game.to_move, other(game.to_move))
                color = next(
                    (
                        candidate
                        for candidate in ordered
                        if identities[candidate] not in accepted
                    ),
                    None,
                )
                if color is None:
                    break
                actions += 1
                if score[color] < score[other(color)]:
                    game.demand_resumption()
                    accepted.clear()
                else:
                    accepted.add(identities[color])
                continue

            color = game.to_move
            decision = _policy_decision(game, policy, rng, seed)
            latencies.append(decision.elapsed_ms)
            actions += 1
            if decision.action == "play":
                point = decision.point
                enemy_adjacent = any(
                    control(game.state, neighbor) == other(color)
                    for neighbor in game.board.neighbors[point]
                )
                friendly_adjacent = any(
                    control(game.state, neighbor) == color
                    for neighbor in game.board.neighbors[point]
                )
                occupied = bool(game.state[point])
                top = control(game.state, point)
                captured = game.play(point)
                captures += captured
                placements += 1
                contacts += enemy_adjacent
                friendly_contacts += friendly_adjacent
                vertical += occupied
                hostile_covers += occupied and top == other(color)
                reinforcements += occupied and top == color
                heat[f"{point[0]},{point[1]}"] += 1
                snapshots.append(
                    {
                        "moves_played": game.moves_played,
                        "state": dict(game.state),
                    }
                )
            elif decision.action == "pass":
                game.play_pass()
            elif decision.action == "swap":
                game.take_over()
                identities[BLACK], identities[WHITE] = (
                    identities[WHITE],
                    identities[BLACK],
                )
                swaps += 1
            else:
                raise RuntimeError("invalid audit decision")
        else:
            error = "watchdog_incomplete"
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"

    if error is not None or not game.finished or len(snapshots) < SAMPLES_PER_GAME:
        return {"job": job, "complete": False, "error": error or "too_few_positions"}
    score = game.score()
    margin = score[BLACK] - score[WHITE]
    outcome = 1.0 if margin > 0 else 0.5 if margin == 0 else 0.0
    usable = snapshots[5:] if len(snapshots) >= 15 else snapshots
    if len(usable) == SAMPLES_PER_GAME:
        selected = usable
    else:
        selected = [
            usable[round(index * (len(usable) - 1) / (SAMPLES_PER_GAME - 1))]
            for index in range(SAMPLES_PER_GAME)
        ]
    group_id = f"n{n}-{policy}-{job['ordinal']}"
    rows = [
        _feature_row(game.board, snapshot, group_id, policy, outcome, margin)
        for snapshot in selected
    ]
    return {
        "job": job,
        "group_id": group_id,
        "complete": True,
        "rows": rows,
        "behavior": {
            "board_size": n,
            "policy": policy,
            "actions": actions,
            "placements": placements,
            "contact": contacts,
            "friendly_contact": friendly_contacts,
            "vertical": vertical,
            "hostile_covers": hostile_covers,
            "reinforcements": reinforcements,
            "captures": captures,
            "swaps": swaps,
            "heat": dict(sorted(heat.items())),
            "decision_latencies_ms": latencies,
        },
    }


def _average_ranks(values):
    ordered = sorted(range(len(values)), key=lambda index: values[index])
    ranks = [0.0] * len(values)
    cursor = 0
    while cursor < len(ordered):
        stop = cursor + 1
        while stop < len(ordered) and values[ordered[stop]] == values[ordered[cursor]]:
            stop += 1
        rank = (cursor + stop - 1) / 2.0
        for index in ordered[cursor:stop]:
            ranks[index] = rank
        cursor = stop
    return ranks


def spearman(left, right):
    if len(left) != len(right) or not left:
        raise ValueError("Spearman inputs must be equal and non-empty")
    x = _average_ranks(left)
    y = _average_ranks(right)
    mean_x = sum(x) / len(x)
    mean_y = sum(y) / len(y)
    numerator = sum((a - mean_x) * (b - mean_y) for a, b in zip(x, y))
    denominator = math.sqrt(
        sum((a - mean_x) ** 2 for a in x)
        * sum((b - mean_y) ** 2 for b in y)
    )
    return numerator / denominator if denominator else 0.0


def _sigmoid(value):
    if value >= 0:
        z = math.exp(-value)
        return 1 / (1 + z)
    z = math.exp(value)
    return z / (1 + z)


def grouped_log_loss(rows, names, seed, epochs=240):
    train = []
    test = []
    for row in rows:
        target = (
            test
            if derive_seed(seed, "heldout-fold", row["group_id"]) % 5 == 0
            else train
        )
        target.append(row)
    if not train or not test:
        raise ValueError("grouped split produced an empty partition")
    weights = [0.0] * len(names)
    mean_label = sum(row["outcome"] for row in train) / len(train)
    mean_label = max(1e-6, min(1 - 1e-6, mean_label))
    bias = math.log(mean_label / (1 - mean_label))
    for epoch in range(epochs):
        gradient = [0.0] * len(names)
        bias_gradient = 0.0
        for row in train:
            values = row["features"]
            prediction = _sigmoid(
                bias + sum(weight * values[name] for weight, name in zip(weights, names))
            )
            error = prediction - row["outcome"]
            bias_gradient += error
            for index, name in enumerate(names):
                gradient[index] += error * values[name]
        rate = 0.35 / math.sqrt(1 + epoch / 20)
        bias -= rate * bias_gradient / len(train)
        for index in range(len(weights)):
            weights[index] -= rate * (
                gradient[index] / len(train) + 0.001 * weights[index]
            )
    losses = []
    for row in test:
        prediction = _sigmoid(
            bias
            + sum(
                weight * row["features"][name]
                for weight, name in zip(weights, names)
            )
        )
        prediction = max(1e-9, min(1 - 1e-9, prediction))
        label = row["outcome"]
        losses.append(
            -(label * math.log(prediction) + (1 - label) * math.log(1 - prediction))
        )
    return sum(losses) / len(losses)


def percentile95(values):
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[max(0, math.ceil(0.95 * len(ordered)) - 1)]


def latency_audit(samples, seed):
    if samples < 2:
        raise ValueError("latency audit requires at least two samples")
    baseline = []
    choose_decision(Game(6), BLACK, "standard", seed=seed)
    for index in range(samples):
        baseline.append(
            choose_decision(
                Game(6), BLACK, "standard", seed=derive_seed(seed, "base", index)
            ).elapsed_ms
        )
    baseline_p95 = percentile95(baseline)
    candidates = {}
    for name in V3_CANDIDATES:
        weights = dict(BALANCED_WEIGHTS)
        weights[name] = 1.0
        timings = []
        choose_decision(Game(6), BLACK, "standard", seed=seed, weights=weights)
        for index in range(samples):
            timings.append(
                choose_decision(
                    Game(6),
                    BLACK,
                    "standard",
                    seed=derive_seed(seed, "latency", name, index),
                    weights=weights,
                ).elapsed_ms
            )
        p95 = percentile95(timings)
        candidates[name] = {
            "samples_ms": timings,
            "p95_ms": p95,
            "added_fraction": (p95 / baseline_p95 - 1) if baseline_p95 else 0.0,
            "below_1500_ms": p95 < 1500,
            "within_15_percent": p95 <= 1.15 * baseline_p95,
        }
    return {
        "samples": samples,
        "baseline_samples_ms": baseline,
        "baseline_p95_ms": baseline_p95,
        "candidates": candidates,
    }


def behavior_summary(games):
    buckets = {}
    for key in [f"n{n}-{policy}" for n in BOARD_POSITION_TOTALS for policy in POLICIES]:
        selected = [
            game["behavior"]
            for game in games
            if f"n{game['behavior']['board_size']}-{game['behavior']['policy']}" == key
        ]
        totals = defaultdict(float)
        heat = Counter()
        latency = []
        for item in selected:
            for name in (
                "actions",
                "placements",
                "contact",
                "friendly_contact",
                "vertical",
                "hostile_covers",
                "reinforcements",
                "captures",
                "swaps",
            ):
                totals[name] += item[name]
            heat.update(item["heat"])
            latency.extend(item["decision_latencies_ms"])
        placements = max(1, totals["placements"])
        buckets[key] = {
            "games": len(selected),
            "placements": int(totals["placements"]),
            "contact_rate": totals["contact"] / placements,
            "friendly_contact_rate": totals["friendly_contact"] / placements,
            "stack_rate": totals["vertical"] / placements,
            "hostile_cover_rate": totals["hostile_covers"] / placements,
            "reinforcement_rate": totals["reinforcements"] / placements,
            "captures_per_game": totals["captures"] / max(1, len(selected)),
            "swap_rate": totals["swaps"] / max(1, len(selected)),
            "decision_p95_ms": percentile95(latency),
            "heat_map": dict(sorted(heat.items())),
        }
    return buckets


def analyze(rows, games, latency, seed):
    names = tuple(rows[0]["features"])
    columns = {
        name: [row["features"][name] for row in rows] for name in names
    }
    correlations = {
        left: {
            right: spearman(columns[left], columns[right]) for right in names
        }
        for left in names
    }
    retained = list(FEATURE_NAMES)
    current_loss = grouped_log_loss(rows, retained, seed)
    baseline_loss = current_loss
    decisions = {}
    for name in V3_CANDIDATES:
        max_correlation = max(abs(correlations[name][other_name]) for other_name in retained)
        trial_names = retained + [name]
        trial_loss = grouped_log_loss(rows, trial_names, seed)
        improvement = (current_loss - trial_loss) / current_loss if current_loss else 0.0
        finite_bounded = all(
            math.isfinite(value) and -1 <= value <= 1 for value in columns[name]
        )
        symmetry_error = max(row["symmetry_error"] for row in rows)
        timing = latency["candidates"][name]
        accepted = (
            finite_bounded
            and symmetry_error <= 1e-12
            and (max_correlation < 0.85 or improvement >= 0.01)
            and timing["below_1500_ms"]
            and timing["within_15_percent"]
        )
        decisions[name] = {
            "finite_bounded": finite_bounded,
            "max_symmetry_error": symmetry_error,
            "max_abs_correlation": max_correlation,
            "heldout_log_loss_before": current_loss,
            "heldout_log_loss_with_feature": trial_loss,
            "relative_log_loss_improvement": improvement,
            "latency_p95_ms": timing["p95_ms"],
            "latency_added_fraction": timing["added_fraction"],
            "accepted_for_optimization": accepted,
            "evaluator_weight": "mutable" if accepted else 0.0,
        }
        if accepted:
            retained.append(name)
            current_loss = trial_loss
    ablations = {}
    for name in retained:
        reduced = [item for item in retained if item != name]
        reduced_loss = grouped_log_loss(rows, reduced, seed)
        ablations[name] = {
            "without_feature_log_loss": reduced_loss,
            "relative_worsening": (
                (reduced_loss - current_loss) / current_loss if current_loss else 0.0
            ),
        }
    return {
        "feature_names": list(names),
        "spearman": correlations,
        "outcome_prediction": {
            "split": "game-grouped deterministic 4:1",
            "baseline_features": list(FEATURE_NAMES),
            "baseline_log_loss": baseline_loss,
            "retained_features": retained,
            "retained_log_loss": current_loss,
        },
        "candidate_decisions": decisions,
        "feature_ablations": ablations,
        "behavior": behavior_summary(games),
    }


def run_audit(output_dir, seed=20260713, workers=1, latency_samples=5):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    jobs = audit_jobs(seed)
    if workers == 1:
        games = [play_audit_game(job) for job in jobs]
    else:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            games = list(executor.map(play_audit_game, jobs))
    incomplete = [game for game in games if not game["complete"]]
    if incomplete:
        failure = {
            "format": FORMAT,
            "version": VERSION,
            "recipe": RECIPE,
            "source_commit": source_commit(),
            "code_hash": code_hash(),
            "configuration": {"seed": seed, "jobs": len(jobs)},
            "status": "failed",
            "incomplete_games": incomplete,
        }
        write_json_atomic(output_dir / "audit-failure.json", failure)
        raise RuntimeError(f"{len(incomplete)} audit games incomplete")
    rows = [row for game in games for row in game["rows"]]
    if len(rows) != 2000:
        raise RuntimeError(f"audit generated {len(rows)} positions, expected 2000")
    latency = latency_audit(latency_samples, derive_seed(seed, "latency"))
    analysis = analyze(rows, games, latency, seed)
    payload = {
        "format": FORMAT,
        "version": VERSION,
        "recipe": RECIPE,
        "source_commit": source_commit(),
        "code_hash": code_hash(),
        "configuration": {
            "seed": seed,
            "workers": workers,
            "positions_hash_is_worker_independent": True,
            "positions": 2000,
            "samples_per_game": SAMPLES_PER_GAME,
            "board_position_totals": BOARD_POSITION_TOTALS,
            "policies": list(POLICIES),
            "watchdog_multiplier": WATCHDOG_MULTIPLIER,
            "latency_samples": latency_samples,
        },
        "status": "complete",
        "positions_hash": stable_hash(rows),
        "positions": rows,
        "latency": latency,
        "analysis": analysis,
    }
    payload["report_hash"] = stable_hash(payload)
    write_json_atomic(output_dir / "audit-v3.json", payload)
    return payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("/tmp/varde-audit-v3"))
    parser.add_argument("--seed", type=int, default=20260713)
    parser.add_argument("--workers", type=int, default=max(1, os.cpu_count() or 1))
    parser.add_argument("--latency-samples", type=int, default=5)
    args = parser.parse_args()
    result = run_audit(
        args.output_dir,
        seed=args.seed,
        workers=args.workers,
        latency_samples=args.latency_samples,
    )
    accepted = [
        name
        for name, item in result["analysis"]["candidate_decisions"].items()
        if item["accepted_for_optimization"]
    ]
    print(args.output_dir / "audit-v3.json")
    print(f"positions=2000 accepted={','.join(accepted) or 'none'}")


if __name__ == "__main__":
    main()
