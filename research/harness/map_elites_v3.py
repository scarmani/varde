#!/usr/bin/env python3
"""Deterministic four-axis MAP-Elites search for Varde evaluator profiles.

The harness is deliberately separate from live play.  Its 20N watchdog only
classifies research rollouts as incomplete; it never forces a move or changes
the rules engine.  All stochastic choices are derived from a candidate id, so
parallel scheduling and checkpoint boundaries cannot change the result.
"""

from __future__ import annotations

import argparse
from bisect import bisect_right
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from copy import deepcopy
from dataclasses import asdict, dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import random
import subprocess
import sys
from typing import Callable


REPO_ROOT = Path(__file__).resolve().parents[2]
ENGINE_ROOT = REPO_ROOT / "engine"
if str(ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(ENGINE_ROOT))

from varde import BLACK, WHITE, Game, Illegal, control, other  # noqa: E402
from opponent import BALANCED_WEIGHTS, choose_decision  # noqa: E402


FORMAT = "varde-map-elites"
VERSION = 3
RECIPE = "four-axis-map-elites-v3"
DESCRIPTORS = ("engagement", "verticality", "edge_reach", "consolidation")
DEFAULT_OUTPUT = Path("/tmp/varde-map-elites-v3")
DEFAULT_SEED = 20260713
DEFAULT_CALIBRATION = 512
DEFAULT_MUTATIONS = 1536
DEFAULT_BATCH_SIZE = 128
DEFAULT_CHECKPOINT = 128
WATCHDOG_MULTIPLIER = 20
PAIR_BOARDS = (3, 3, 3, 4)
V3_MUTATION_CANDIDATES = (
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

# Bounds are intentionally conservative until the Batch 5 audit narrows the
# active mutation schema.  Search depth and difficulty are never genome genes.
WEIGHT_BOUNDS = {
    "controlled": (6.0, 18.0),
    "captured": (10.0, 55.0),
    "skies": (5.0, 32.0),
    "liberties": (0.0, 8.0),
    "vulnerable": (-28.0, -3.0),
    "development": (-1.0, 5.0),
    "territory": (0.0, 5.0),
    "control_resilience": (-24.0, 24.0),
    "latent_reserves": (-24.0, 24.0),
    "sky_durability": (-24.0, 24.0),
    "connection": (-24.0, 24.0),
    "capturing_moves": (-24.0, 24.0),
    "max_capture": (-24.0, 24.0),
    "covers": (-24.0, 24.0),
    "hostile_covers": (-24.0, 24.0),
    "reinforcements": (-24.0, 24.0),
    "summits": (-24.0, 24.0),
}


@dataclass(frozen=True)
class RolloutResult:
    board_size: int
    pair_slot: int
    seed: int
    initial_candidate_color: str
    final_candidate_color: str
    result: float
    margin: int
    actions: int
    complete: bool
    error: str | None
    candidate_captures: int
    early_placements: int
    engagement: int
    all_placements: int
    verticality: int
    edge_reach_sum: float
    consolidation: int
    all_engagement: int
    all_consolidation: int
    hostile_covers: int
    reinforcements: int
    candidate_points: tuple[tuple[int, int], ...]


def _canonical_bytes(payload):
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()


def stable_hash(payload):
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def derive_seed(master_seed, *parts):
    digest = hashlib.sha256(
        _canonical_bytes([int(master_seed), *parts])
    ).digest()
    return int.from_bytes(digest[:8], "big")


def source_commit():
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _code_hash():
    paths = (Path(__file__), ENGINE_ROOT / "opponent.py")
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def write_json_atomic(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n"
    )
    temporary.replace(path)


def balanced_genome():
    return {name: float(BALANCED_WEIGHTS[name]) for name in WEIGHT_BOUNDS}


def _runtime_weights(genome):
    """Use the literal parity-locked mapping for an exact Balanced genome."""
    return BALANCED_WEIGHTS if genome == balanced_genome() else genome


def validate_genome(genome, bounds=None):
    active_bounds = WEIGHT_BOUNDS if bounds is None else bounds
    if not isinstance(genome, dict) or set(genome) != set(active_bounds):
        raise ValueError("invalid evaluator genome schema")
    for name, (lower, upper) in active_bounds.items():
        value = genome[name]
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or not lower <= value <= upper
        ):
            raise ValueError(f"invalid evaluator weight: {name}")
    return genome


def random_genome(master_seed, candidate_id, bounds=None):
    active_bounds = WEIGHT_BOUNDS if bounds is None else bounds
    rng = random.Random(derive_seed(master_seed, "random-genome", candidate_id))
    genome = {
        name: round(rng.uniform(lower, upper), 12)
        for name, (lower, upper) in active_bounds.items()
    }
    return validate_genome(genome, active_bounds)


def mutate_genome(parent, master_seed, candidate_id, bounds=None):
    active_bounds = WEIGHT_BOUNDS if bounds is None else bounds
    validate_genome(parent, active_bounds)
    rng = random.Random(derive_seed(master_seed, "mutation", candidate_id))
    child = {}
    mutable = [
        index
        for index, (_name, (lower, upper)) in enumerate(active_bounds.items())
        if lower != upper
    ]
    if not mutable:
        raise ValueError("mutation schema has no mutable evaluator weights")
    forced = mutable[rng.randrange(len(mutable))]
    for index, (name, (lower, upper)) in enumerate(active_bounds.items()):
        value = float(parent[name])
        if lower != upper and (index == forced or rng.random() < 0.28):
            sigma = 0.12 * (upper - lower)
            value += rng.gauss(0.0, sigma)
        child[name] = round(max(lower, min(upper, value)), 12)
    return validate_genome(child, active_bounds)


def audited_mutation_bounds(path):
    """Load the audit gate and freeze rejected V3 weights at zero."""
    payload = json.loads(Path(path).read_text())
    expected = payload.get("report_hash")
    canonical = {
        key: value for key, value in payload.items() if key != "report_hash"
    }
    if not isinstance(expected, str) or stable_hash(canonical) != expected:
        raise ValueError("audit report hash mismatch")
    if payload.get("format") != "varde-evaluator-audit" or payload.get("version") != 3:
        raise ValueError("unsupported evaluator audit")
    if payload.get("status") != "complete":
        raise ValueError("evaluator audit is not complete")
    decisions = payload.get("analysis", {}).get("candidate_decisions", {})
    if set(decisions) != set(V3_MUTATION_CANDIDATES):
        raise ValueError("audit candidate schema mismatch")
    bounds = dict(WEIGHT_BOUNDS)
    accepted = []
    for name in V3_MUTATION_CANDIDATES:
        if decisions[name].get("accepted_for_optimization") is True:
            accepted.append(name)
        else:
            bounds[name] = (0.0, 0.0)
    return bounds, expected, tuple(accepted)


def _sigmoid(value):
    if value >= 0:
        z = math.exp(-value)
        return 1.0 / (1.0 + z)
    z = math.exp(value)
    return z / (1.0 + z)


def _identity_color(seats, identity):
    for color, seat in seats.items():
        if seat["identity"] == identity:
            return color
    raise RuntimeError("seat identity disappeared")


def _decision_for(game, color, seat, difficulty):
    return choose_decision(
        game,
        color,
        difficulty,
        seed=seat["seed"],
        weights=seat["weights"],
    )


def play_rollout(
    candidate_weights,
    opponent_weights,
    initial_candidate_color,
    seed,
    board_size,
    pair_slot,
    difficulty="standard",
):
    """Play one paired-rollout leg and return candidate-identity telemetry."""
    validate_genome(candidate_weights)
    validate_genome(opponent_weights)
    game = Game(board_size)
    seats = {
        initial_candidate_color: {
            "identity": "candidate",
            "weights": _runtime_weights(candidate_weights),
            "seed": derive_seed(seed, "candidate"),
        },
        other(initial_candidate_color): {
            "identity": "opponent",
            "weights": _runtime_weights(opponent_weights),
            "seed": derive_seed(seed, "opponent"),
        },
    }
    accepted = set()
    actions = 0
    placements = 0
    candidate_captures = 0
    early_placements = 0
    engagement = 0
    all_placements = 0
    verticality = 0
    edge_reach_sum = 0.0
    consolidation = 0
    all_engagement = 0
    all_consolidation = 0
    hostile_covers = 0
    reinforcements = 0
    candidate_points = []
    total = len(game.board.points)
    early_limit = 0.6 * total
    distances = game.board.dist_to_rim()
    maximum_distance = max(distances.values()) or 1
    watchdog = WATCHDOG_MULTIPLIER * total
    error = None

    try:
        while actions < watchdog:
            if game.finished:
                if game.resumption_used:
                    color = game.to_move
                    seat = seats[color]
                else:
                    ordered = (seats[game.to_move], seats[other(game.to_move)])
                    seat = next(
                        (
                            item
                            for item in ordered
                            if item["identity"] not in accepted
                        ),
                        None,
                    )
                    if seat is None:
                        break
                    color = _identity_color(seats, seat["identity"])
                decision = _decision_for(game, color, seat, difficulty)
                actions += 1
                if decision.action == "resume":
                    game.demand_resumption()
                    accepted.clear()
                    continue
                if decision.action != "accept":
                    raise RuntimeError("invalid finished-game decision")
                accepted.add(seat["identity"])
                if game.resumption_used or len(accepted) == 2:
                    break
                continue

            color = game.to_move
            seat = seats[color]
            decision = _decision_for(game, color, seat, difficulty)
            actions += 1
            if decision.action == "play":
                point = decision.point
                if point not in game.legal_placements():
                    raise Illegal("computer selected an illegal placement")
                is_candidate = seat["identity"] == "candidate"
                if is_candidate:
                    enemy_adjacent = any(
                        control(game.state, neighbor) == other(color)
                        for neighbor in game.board.neighbors[point]
                    )
                    friendly_adjacent = any(
                        control(game.state, neighbor) == color
                        for neighbor in game.board.neighbors[point]
                    )
                    all_placements += 1
                    verticality += bool(game.state[point])
                    all_engagement += enemy_adjacent
                    all_consolidation += friendly_adjacent
                    hostile_covers += (
                        bool(game.state[point])
                        and control(game.state, point) == other(color)
                    )
                    reinforcements += (
                        bool(game.state[point])
                        and control(game.state, point) == color
                    )
                    candidate_points.append(point)
                    if placements < early_limit:
                        early_placements += 1
                        engagement += enemy_adjacent
                        consolidation += friendly_adjacent
                        edge_reach_sum += 1.0 - (
                            distances[point] / maximum_distance
                        )
                captured = game.play(point)
                placements += 1
                if is_candidate:
                    candidate_captures += captured
            elif decision.action == "pass":
                game.play_pass()
            elif decision.action == "swap":
                game.take_over()
                seats[BLACK], seats[WHITE] = seats[WHITE], seats[BLACK]
            else:
                raise RuntimeError("invalid live-game decision")
        else:
            error = "watchdog_incomplete"
    except Exception as exc:  # A failed research attempt is evidence, not a crash.
        error = f"{type(exc).__name__}: {exc}"

    complete = error is None and game.finished
    final_color = _identity_color(seats, "candidate")
    if complete:
        score = game.score()
        margin = score[final_color] - score[other(final_color)]
        result = 1.0 if margin > 0 else 0.5 if margin == 0 else 0.0
    else:
        margin = 0
        result = 0.0
    return RolloutResult(
        board_size=board_size,
        pair_slot=pair_slot,
        seed=seed,
        initial_candidate_color=initial_candidate_color,
        final_candidate_color=final_color,
        result=result,
        margin=margin,
        actions=actions,
        complete=complete,
        error=error,
        candidate_captures=candidate_captures,
        early_placements=early_placements,
        engagement=engagement,
        all_placements=all_placements,
        verticality=verticality,
        edge_reach_sum=edge_reach_sum,
        consolidation=consolidation,
        all_engagement=all_engagement,
        all_consolidation=all_consolidation,
        hostile_covers=hostile_covers,
        reinforcements=reinforcements,
        candidate_points=tuple(candidate_points),
    )


def evaluate_candidate(task):
    """Evaluate a serialized candidate task; safe for process workers."""
    candidate_id = task["candidate_id"]
    genome = validate_genome(task["genome"])
    games = []
    for pair_slot, board_size in enumerate(PAIR_BOARDS):
        opponent = task["opponents"][pair_slot]
        opponent_weights = validate_genome(opponent["genome"])
        game_seed = derive_seed(task["master_seed"], "game", candidate_id, pair_slot)
        for color in (BLACK, WHITE):
            games.append(
                play_rollout(
                    genome,
                    opponent_weights,
                    color,
                    game_seed,
                    board_size,
                    pair_slot,
                    task["difficulty"],
                )
            )

    serialized_games = [asdict(game) for game in games]
    incomplete = sum(not game.complete for game in games)
    errors = sorted({game.error for game in games if game.error})
    rejected = incomplete > 0
    early = sum(game.early_placements for game in games)
    placed = sum(game.all_placements for game in games)
    descriptors = {
        "engagement": sum(game.engagement for game in games) / max(1, early),
        "verticality": sum(game.verticality for game in games) / max(1, placed),
        "edge_reach": sum(game.edge_reach_sum for game in games) / max(1, early),
        "consolidation": sum(game.consolidation for game in games) / max(1, early),
    }
    score_rate = sum(game.result for game in games) / len(games)
    margin_term = sum(
        _sigmoid(game.margin / (0.15 * 6 * game.board_size**2))
        for game in games
    ) / len(games)
    quality = 0.7 * score_rate + 0.3 * margin_term
    if rejected or not math.isfinite(quality) or any(
        not math.isfinite(value) or not 0.0 <= value <= 1.0
        for value in descriptors.values()
    ):
        rejected = True
        quality = None
    result = {
        "candidate_id": candidate_id,
        "kind": task["kind"],
        "parent_id": task.get("parent_id"),
        "genome": genome,
        "genome_hash": stable_hash(genome),
        "opponents": [
            {"id": item["id"], "genome_hash": stable_hash(item["genome"])}
            for item in task["opponents"]
        ],
        "games": serialized_games,
        "games_attempted": len(games),
        "games_incomplete": incomplete,
        "descriptors": descriptors,
        "score_rate": score_rate,
        "margin_quality": margin_term,
        "quality": quality,
        "rejected": rejected,
        "errors": errors,
    }
    result["result_hash"] = stable_hash(result)
    return result


def calibration_edges(results):
    if not results:
        raise ValueError("calibration requires results")
    edges = {}
    for descriptor in DESCRIPTORS:
        values = sorted(float(item["descriptors"][descriptor]) for item in results)
        count = len(values)
        cuts = []
        for numerator in (1, 2, 3):
            boundary = numerator * count / 4
            left = max(0, math.ceil(boundary) - 1)
            right = min(count - 1, left + 1)
            cuts.append((values[left] + values[right]) / 2.0)
        edges[descriptor] = cuts
    return edges


def archive_cell(descriptors, edges):
    return tuple(
        min(3, bisect_right(edges[name], descriptors[name]))
        for name in DESCRIPTORS
    )


def _cell_key(cell):
    return ",".join(str(value) for value in cell)


def archive_insert(archive, result, edges):
    if result["rejected"]:
        return None
    key = _cell_key(archive_cell(result["descriptors"], edges))
    existing = archive.get(key)
    replaces = existing is None or result["quality"] > existing["quality"]
    if not replaces:
        return None
    archive[key] = {
        "candidate_id": result["candidate_id"],
        "quality": result["quality"],
        "descriptors": dict(result["descriptors"]),
        "genome": dict(result["genome"]),
        "genome_hash": result["genome_hash"],
    }
    return {
        "candidate_id": result["candidate_id"],
        "cell": key,
        "replaced_candidate_id": (
            existing["candidate_id"] if existing is not None else None
        ),
        "quality": result["quality"],
    }


def refresh_hall_of_fame(attempts):
    eligible = [item for item in attempts if not item["rejected"]]
    hall = [
        {
            "id": "balanced",
            "candidate_id": -1,
            "genome": balanced_genome(),
            "quality": None,
            "descriptors": None,
        }
    ]
    if not eligible:
        return hall
    selections = [max(eligible, key=lambda item: (item["quality"], -item["candidate_id"]))]
    selections.extend(
        max(
            eligible,
            key=lambda item, name=name: (
                item["descriptors"][name],
                item["quality"],
                -item["candidate_id"],
            ),
        )
        for name in DESCRIPTORS
    )
    seen = {-1}
    for result in selections:
        if result["candidate_id"] in seen:
            continue
        seen.add(result["candidate_id"])
        hall.append(
            {
                "id": f"candidate-{result['candidate_id']}",
                "candidate_id": result["candidate_id"],
                "genome": dict(result["genome"]),
                "quality": result["quality"],
                "descriptors": dict(result["descriptors"]),
            }
        )
    return hall


def _opponents_for(master_seed, candidate_id, frozen_hall):
    balanced = {"id": "balanced", "genome": balanced_genome()}
    hall = frozen_hall or [balanced]
    opponents = [balanced, balanced]
    for pair_slot in (2, 3):
        index = derive_seed(
            master_seed, "opponent", candidate_id, pair_slot
        ) % len(hall)
        selected = hall[index]
        opponents.append(
            {"id": selected["id"], "genome": dict(selected["genome"])}
        )
    return opponents


def _make_batch(state):
    start = state["next_candidate"]
    calibration_count = state["configuration"]["calibration_count"]
    target = state["target_candidates"]
    batch_size = state["configuration"]["batch_size"]
    stop = min(target, start + batch_size)
    if start < calibration_count:
        stop = min(stop, calibration_count)
    frozen_hall = deepcopy(state["hall_of_fame"])
    occupied = sorted(state["archive"])
    bounds = {
        name: tuple(state["mutation_bounds"][name]) for name in WEIGHT_BOUNDS
    }
    tasks = []
    for candidate_id in range(start, stop):
        if candidate_id < calibration_count:
            kind = "calibration"
            parent_id = None
            genome = random_genome(
                state["master_seed"], candidate_id, bounds
            )
        else:
            kind = "mutation"
            selector = derive_seed(
                state["master_seed"], "archive-parent", candidate_id
            )
            if occupied:
                parent = state["archive"][occupied[selector % len(occupied)]]
                parent_id = parent["candidate_id"]
                genome = mutate_genome(
                    parent["genome"],
                    state["master_seed"],
                    candidate_id,
                    bounds,
                )
            else:
                parent_id = None
                genome = random_genome(
                    state["master_seed"], candidate_id, bounds
                )
        tasks.append(
            {
                "candidate_id": candidate_id,
                "kind": kind,
                "parent_id": parent_id,
                "genome": genome,
                "opponents": _opponents_for(
                    state["master_seed"], candidate_id, frozen_hall
                ),
                "master_seed": state["master_seed"],
                "difficulty": state["configuration"]["difficulty"],
            }
        )
    return {
        "start": start,
        "stop": stop,
        "cursor": 0,
        "frozen_hall_hash": stable_hash(frozen_hall),
        "tasks": tasks,
    }


def _state_without_hash(state):
    return {key: value for key, value in state.items() if key != "state_hash"}


def _checkpoint(path, state):
    state["state_hash"] = stable_hash(_state_without_hash(state))
    write_json_atomic(path, state)


def _load_state(path):
    payload = json.loads(Path(path).read_text())
    expected = payload.get("state_hash")
    if not isinstance(expected, str) or stable_hash(_state_without_hash(payload)) != expected:
        raise ValueError("optimizer checkpoint hash mismatch")
    if payload.get("format") != FORMAT or payload.get("version") != VERSION:
        raise ValueError("unsupported optimizer checkpoint")
    if payload.get("recipe") != RECIPE:
        raise ValueError("optimizer recipe mismatch")
    if payload.get("code_hash") != _code_hash():
        raise ValueError("optimizer code changed since checkpoint")
    return payload


def new_state(
    seed,
    calibration_count,
    mutations,
    batch_size,
    difficulty,
    mutation_bounds=None,
    audit_report_hash=None,
    accepted_v3=(),
):
    if calibration_count < 4 or calibration_count % 4:
        raise ValueError("calibration count must be a positive multiple of four")
    if mutations < 0:
        raise ValueError("mutation count cannot be negative")
    if batch_size < 1:
        raise ValueError("batch size must be positive")
    if difficulty not in ("casual", "standard"):
        raise ValueError("research difficulty must be casual or standard")
    active_bounds = WEIGHT_BOUNDS if mutation_bounds is None else mutation_bounds
    if set(active_bounds) != set(WEIGHT_BOUNDS):
        raise ValueError("invalid mutation schema")
    for name, (lower, upper) in active_bounds.items():
        if not all(isinstance(value, (int, float)) and math.isfinite(value) for value in (lower, upper)) or lower > upper:
            raise ValueError(f"invalid mutation bounds: {name}")
    return {
        "format": FORMAT,
        "version": VERSION,
        "recipe": RECIPE,
        "source_commit": source_commit(),
        "code_hash": _code_hash(),
        "feature_schema_hash": stable_hash(
            {name: list(values) for name, values in active_bounds.items()}
        ),
        "master_seed": int(seed),
        "mutation_bounds": {
            name: [float(lower), float(upper)]
            for name, (lower, upper) in active_bounds.items()
        },
        "configuration": {
            "calibration_count": calibration_count,
            "batch_size": batch_size,
            "difficulty": difficulty,
            "pair_boards": list(PAIR_BOARDS),
            "pairs_per_candidate": len(PAIR_BOARDS),
            "games_per_candidate": 2 * len(PAIR_BOARDS),
            "watchdog_multiplier": WATCHDOG_MULTIPLIER,
            "bins_per_axis": 4,
            "audit_report_hash": audit_report_hash,
            "accepted_v3_features": list(accepted_v3),
        },
        "target_candidates": calibration_count + mutations,
        "next_candidate": 0,
        "status": "running",
        "pending_batch": None,
        "bin_edges": None,
        "archive": {},
        "archive_replacements": [],
        "hall_of_fame": refresh_hall_of_fame([]),
        "balanced_reference": None,
        "attempts": [],
        "counters": {
            "candidates_attempted": 0,
            "candidates_rejected": 0,
            "games_attempted": 0,
            "games_incomplete": 0,
            "reference_games_attempted": 0,
        },
    }


def _balanced_reference_task(state):
    balanced = {"id": "balanced", "genome": balanced_genome()}
    return {
        "candidate_id": -1,
        "kind": "balanced_reference",
        "parent_id": None,
        "genome": balanced_genome(),
        "opponents": [deepcopy(balanced) for _ in PAIR_BOARDS],
        "master_seed": state["master_seed"],
        "difficulty": state["configuration"]["difficulty"],
    }


def _ordered_results(tasks, evaluator, workers):
    if workers == 1:
        return [evaluator(task) for task in tasks]
    executor_type = (
        ProcessPoolExecutor if evaluator is evaluate_candidate else ThreadPoolExecutor
    )
    with executor_type(max_workers=workers) as executor:
        return list(executor.map(evaluator, tasks))


def _validate_result(result, expected_id):
    if result.get("candidate_id") != expected_id:
        raise ValueError("worker returned a result out of identity order")
    if set(result.get("genome", ())) != set(WEIGHT_BOUNDS):
        raise ValueError("worker returned an invalid genome")
    descriptors = result.get("descriptors", {})
    if tuple(descriptors) != DESCRIPTORS:
        raise ValueError("worker returned invalid descriptors")
    if any(
        not isinstance(value, (int, float))
        or not math.isfinite(value)
        or not 0 <= value <= 1
        for value in descriptors.values()
    ):
        raise ValueError("worker returned non-finite descriptors")
    if result.get("rejected"):
        if result.get("quality") is not None:
            raise ValueError("rejected result has archive quality")
    elif (
        not isinstance(result.get("quality"), (int, float))
        or not math.isfinite(result["quality"])
    ):
        raise ValueError("worker returned invalid quality")


def _commit_result(state, result):
    _validate_result(result, state["next_candidate"])
    bounds = {
        name: tuple(state["mutation_bounds"][name]) for name in WEIGHT_BOUNDS
    }
    validate_genome(result["genome"], bounds)
    state["attempts"].append(result)
    state["next_candidate"] += 1
    counters = state["counters"]
    counters["candidates_attempted"] += 1
    counters["candidates_rejected"] += bool(result["rejected"])
    counters["games_attempted"] += int(result.get("games_attempted", 0))
    counters["games_incomplete"] += int(result.get("games_incomplete", 0))

    calibration_count = state["configuration"]["calibration_count"]
    if state["next_candidate"] == calibration_count:
        eligible = [item for item in state["attempts"] if not item["rejected"]]
        if not eligible:
            raise RuntimeError("all calibration candidates were rejected")
        state["bin_edges"] = calibration_edges(eligible)
        for item in eligible:
            replacement = archive_insert(
                state["archive"], item, state["bin_edges"]
            )
            if replacement:
                state["archive_replacements"].append(replacement)
    elif state["next_candidate"] > calibration_count and not result["rejected"]:
        replacement = archive_insert(
            state["archive"], result, state["bin_edges"]
        )
        if replacement:
            state["archive_replacements"].append(replacement)


def run_optimizer(
    output_dir,
    *,
    seed=DEFAULT_SEED,
    workers=1,
    checkpoint_interval=DEFAULT_CHECKPOINT,
    calibration_count=DEFAULT_CALIBRATION,
    mutations=DEFAULT_MUTATIONS,
    batch_size=DEFAULT_BATCH_SIZE,
    difficulty="standard",
    resume=False,
    cancel_file=None,
    max_candidates=None,
    audit_report=None,
    evaluator: Callable = evaluate_candidate,
):
    """Run or resume the optimizer and return its canonical checkpoint state."""
    if workers < 1 or checkpoint_interval < 1:
        raise ValueError("workers and checkpoint interval must be positive")
    output_dir = Path(output_dir)
    state_path = output_dir / "state.json"
    output_dir.mkdir(parents=True, exist_ok=True)
    if audit_report is not None:
        mutation_bounds, audit_hash, accepted_v3 = audited_mutation_bounds(
            audit_report
        )
    else:
        mutation_bounds = None
        audit_hash = None
        accepted_v3 = ()
    if resume:
        if not state_path.exists():
            raise ValueError("no optimizer checkpoint to resume")
        state = _load_state(state_path)
        if state["master_seed"] != int(seed):
            raise ValueError("resume seed does not match checkpoint")
        config = state["configuration"]
        if (
            config["calibration_count"] != calibration_count
            or config["batch_size"] != batch_size
            or config["difficulty"] != difficulty
        ):
            raise ValueError("resume configuration does not match checkpoint")
        if audit_report is not None and (
            config.get("audit_report_hash") != audit_hash
            or state["mutation_bounds"]
            != {
                name: [float(lower), float(upper)]
                for name, (lower, upper) in mutation_bounds.items()
            }
        ):
            raise ValueError("resume audit does not match checkpoint")
        requested_target = calibration_count + mutations
        if requested_target < state["target_candidates"]:
            raise ValueError("cannot shorten a resumed optimizer run")
        state["target_candidates"] = requested_target
        state["status"] = "running"
    else:
        if state_path.exists():
            raise ValueError("output already contains a checkpoint; use --resume")
        state = new_state(
            seed,
            calibration_count,
            mutations,
            batch_size,
            difficulty,
            mutation_bounds,
            audit_hash,
            accepted_v3,
        )
        _checkpoint(state_path, state)

    committed_this_run = 0
    cancel_path = Path(cancel_file) if cancel_file else None
    if cancel_path and cancel_path.exists():
        state["status"] = "cancelled"
        _checkpoint(state_path, state)
        return state
    if state.get("balanced_reference") is None:
        reference = evaluator(_balanced_reference_task(state))
        _validate_result(reference, -1)
        if reference["rejected"]:
            raise RuntimeError("Balanced reference rollout was rejected")
        state["balanced_reference"] = reference
        state["counters"]["reference_games_attempted"] = int(
            reference.get("games_attempted", 0)
        )
        _checkpoint(state_path, state)
    stop_requested = False
    while state["next_candidate"] < state["target_candidates"]:
        if cancel_path and cancel_path.exists():
            state["status"] = "cancelled"
            break
        if max_candidates is not None and committed_this_run >= max_candidates:
            state["status"] = "paused"
            break
        if state["pending_batch"] is None:
            state["pending_batch"] = _make_batch(state)
            _checkpoint(state_path, state)
        pending = state["pending_batch"]
        cursor = pending["cursor"]
        remaining_tasks = pending["tasks"][cursor:]
        if max_candidates is not None:
            remaining_tasks = remaining_tasks[
                : max(0, max_candidates - committed_this_run)
            ]
        results = _ordered_results(remaining_tasks, evaluator, workers)
        for result in results:
            task = pending["tasks"][pending["cursor"]]
            _validate_result(result, task["candidate_id"])
            _commit_result(state, result)
            pending["cursor"] += 1
            committed_this_run += 1
            if committed_this_run % checkpoint_interval == 0:
                _checkpoint(state_path, state)
            if cancel_path and cancel_path.exists():
                state["status"] = "cancelled"
                stop_requested = True
                break
        if pending["cursor"] == len(pending["tasks"]):
            state["hall_of_fame"] = refresh_hall_of_fame(state["attempts"])
            state["pending_batch"] = None
        if stop_requested:
            break
        if max_candidates is not None and committed_this_run >= max_candidates:
            state["status"] = "paused"
            break

    if state["next_candidate"] >= state["target_candidates"]:
        state["status"] = "complete"
        state["pending_batch"] = None
    _checkpoint(state_path, state)
    return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--workers", type=int, default=max(1, os.cpu_count() or 1))
    parser.add_argument("--checkpoint-interval", type=int, default=DEFAULT_CHECKPOINT)
    parser.add_argument("--calibration-count", type=int, default=DEFAULT_CALIBRATION)
    parser.add_argument("--mutations", type=int, default=DEFAULT_MUTATIONS)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--difficulty", choices=("casual", "standard"), default="standard")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--cancel-file", type=Path)
    parser.add_argument(
        "--audit-report",
        type=Path,
        help="freeze audit-rejected V3 candidates at zero",
    )
    args = parser.parse_args()
    state = run_optimizer(
        args.output_dir,
        seed=args.seed,
        workers=args.workers,
        checkpoint_interval=args.checkpoint_interval,
        calibration_count=args.calibration_count,
        mutations=args.mutations,
        batch_size=args.batch_size,
        difficulty=args.difficulty,
        resume=args.resume,
        cancel_file=args.cancel_file,
        audit_report=args.audit_report,
    )
    print(args.output_dir / "state.json")
    print(
        f"status={state['status']} candidates={state['next_candidate']}/"
        f"{state['target_candidates']} archive={len(state['archive'])} "
        f"rejected={state['counters']['candidates_rejected']}"
    )


if __name__ == "__main__":
    main()
