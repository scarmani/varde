#!/usr/bin/env python3
"""Outcome-blind throughput gate for Varde ruleset evaluation methods."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import statistics
import subprocess
import sys
import time


REPO_ROOT = Path(__file__).resolve().parents[2]
ENGINE_ROOT = REPO_ROOT / "engine"
if str(ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(ENGINE_ROOT))

from actions import RulesState, apply_action, legal_actions  # noqa: E402
from mcts import MCTS_AGENT_HASH, choose_mcts_state_action  # noqa: E402
from native_evaluators import NATIVE_EVALUATOR_HASH  # noqa: E402
from opponent import choose_decision  # noqa: E402
from varde import Game, get_ruleset_spec, rulesets_public  # noqa: E402


FORMAT = "varde-evidence-feasibility-gate"
VERSION = 1
RULESETS = ("classic", "rosette", "breath", "breath-run", "gjerde", "gjerde-go")
POLICIES = ("uniform", "epsilon-greedy")
POSITIONS = ("opening", "midgame")
DECISION_GATES = (2, 10, 30)
BOARD_SIZE = 4
PREFIX_MOVES = 12
STAGE_GAMES_PER_RULESET_POLICY = 40
STAGE_TOTAL_GAMES = 480
STAGE_WORKERS = 8
REVISED_LADDER = (16, 32)
MAX_STAGE_HOURS = 24.0
DEFAULT_OUTPUT = (
    REPO_ROOT / "research" / "results" / "evidence-feasibility-gate-20260715.json"
)
FORBIDDEN_MEASUREMENT_KEYS = frozenset(
    ("action", "point", "score", "winner", "margin", "result", "decision")
)


def canonical_bytes(payload):
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()


def stable_hash(payload):
    return hashlib.sha256(canonical_bytes(payload)).hexdigest()


def derive_seed(master_seed, *parts):
    digest = hashlib.sha256(canonical_bytes([int(master_seed), *parts])).digest()
    return int.from_bytes(digest[:8], "big")


def source_commit():
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def percentile(values, quantile):
    """Linearly interpolated quantile over a non-empty finite sample."""
    if not values or not 0.0 <= quantile <= 1.0:
        raise ValueError("invalid percentile input")
    ordered = sorted(float(value) for value in values)
    if any(not math.isfinite(value) for value in ordered):
        raise ValueError("percentile values must be finite")
    if len(ordered) == 1:
        return ordered[0]
    index = quantile * (len(ordered) - 1)
    lower = math.floor(index)
    upper = math.ceil(index)
    fraction = index - lower
    return ordered[lower] + fraction * (ordered[upper] - ordered[lower])


def maximum_budget(gate_seconds, simulation_seconds):
    if gate_seconds <= 0 or simulation_seconds <= 0:
        raise ValueError("timing inputs must be positive")
    return max(0, math.floor(gate_seconds / simulation_seconds))


def projected_game_seconds(
    budget,
    simulation_seconds,
    native_seconds,
    mean_game_moves,
    *,
    mcts_fraction=0.5,
):
    if budget < 1:
        return None
    values = (simulation_seconds, native_seconds, mean_game_moves, mcts_fraction)
    if any(value < 0 or not math.isfinite(value) for value in values):
        raise ValueError("projection inputs must be non-negative and finite")
    if mcts_fraction > 1:
        raise ValueError("MCTS fraction cannot exceed one")
    per_move = (
        mcts_fraction * budget * simulation_seconds
        + (1.0 - mcts_fraction) * native_seconds
    )
    return mean_game_moves * per_move


def projected_stage_hours(game_seconds, games, workers):
    if game_seconds is None:
        return None
    if game_seconds < 0 or games < 1 or workers < 1:
        raise ValueError("invalid stage projection inputs")
    return game_seconds * games / workers / 3600.0


def passes_feasibility_gate(
    *,
    maximum_common_budget,
    projected_hours,
    per_decision_p95,
    required_high_budget=REVISED_LADDER[-1],
    maximum_stage_hours=MAX_STAGE_HOURS,
    maximum_decision_seconds=DECISION_GATES[-1],
):
    return bool(
        maximum_common_budget >= required_high_budget
        and projected_hours is not None
        and projected_hours <= maximum_stage_hours
        and per_decision_p95 <= maximum_decision_seconds
    )


def build_midgame_state(rules, seed, prefix_moves=PREFIX_MOVES):
    state = RulesState.from_game(Game(BOARD_SIZE, rules=rules))
    rng = random.Random(derive_seed(seed, rules, "midgame-prefix"))
    for _index in range(prefix_moves):
        candidates = [
            item
            for item in legal_actions(state)
            if item.kind not in ("pass", "resume", "accept")
        ]
        if not candidates:
            raise RuntimeError(f"no non-ending prefix action for {rules}")
        apply_action(
            state,
            candidates[rng.randrange(len(candidates))],
            copy=False,
            validate=False,
        )
        if state.terminal or state.game.finished:
            raise RuntimeError(f"midgame prefix ended {rules}")
    return state


def random_game_length(rules, seed, *, watchdog_multiplier=20):
    state = RulesState.from_game(Game(BOARD_SIZE, rules=rules))
    rng = random.Random(derive_seed(seed, rules, "random-game"))
    maximum_moves = watchdog_multiplier * len(state.game.board.points)
    moves = 0
    while not state.terminal and moves < maximum_moves:
        actions = legal_actions(state)
        apply_action(
            state,
            actions[rng.randrange(len(actions))],
            copy=False,
            validate=False,
        )
        moves += 1
    if not state.terminal:
        raise RuntimeError(f"random game watchdog reached for {rules}")
    return moves


def _timed_nonmutating(call, state):
    before = state.key()
    started = time.perf_counter()
    call()
    elapsed = time.perf_counter() - started
    if state.key() != before:
        raise AssertionError("timing probe mutated its position")
    return elapsed


def _sample_summary(durations):
    return {
        "repetitions": len(durations),
        "mean_seconds": statistics.fmean(durations),
        "p95_seconds": percentile(durations, 0.95),
        "maximum_seconds": max(durations),
    }


def _measure_ruleset(rules, seed, repetitions, deadline):
    positions = {
        "opening": RulesState.from_game(Game(BOARD_SIZE, rules=rules)),
        "midgame": build_midgame_state(rules, seed),
    }
    native = {}
    simulations = {policy: {} for policy in POLICIES}
    for position_name, state in positions.items():
        durations = []
        for repetition in range(repetitions):
            if time.perf_counter() >= deadline:
                raise TimeoutError("feasibility measurement exceeded wall limit")
            probe_seed = derive_seed(seed, rules, position_name, "native", repetition)
            durations.append(
                _timed_nonmutating(
                    lambda: choose_decision(
                        state.game,
                        state.actor_color,
                        difficulty="standard",
                        seed=probe_seed,
                    ),
                    state,
                )
            )
        native[position_name] = _sample_summary(durations)

        for policy in POLICIES:
            durations = []
            for repetition in range(repetitions):
                if time.perf_counter() >= deadline:
                    raise TimeoutError("feasibility measurement exceeded wall limit")
                probe_seed = derive_seed(
                    seed, rules, position_name, policy, repetition
                )
                durations.append(
                    _timed_nonmutating(
                        lambda: choose_mcts_state_action(
                            state,
                            state.actor_color,
                            simulations=1,
                            seed=probe_seed,
                            rollout_policy=policy,
                        ),
                        state,
                    )
                )
            simulations[policy][position_name] = _sample_summary(durations)

    lengths = []
    for repetition in range(repetitions):
        if time.perf_counter() >= deadline:
            raise TimeoutError("feasibility measurement exceeded wall limit")
        lengths.append(random_game_length(rules, derive_seed(seed, repetition)))

    mean_native = max(
        item["mean_seconds"] for item in native.values()
    )
    mean_moves = statistics.fmean(lengths)
    projections = {}
    for policy, position_data in simulations.items():
        all_means = [item["mean_seconds"] for item in position_data.values()]
        all_p95 = [item["p95_seconds"] for item in position_data.values()]
        conservative_sim_seconds = max(all_means)
        conservative_p95 = max(all_p95)
        gates = {}
        for gate_seconds in DECISION_GATES:
            budget = maximum_budget(gate_seconds, conservative_sim_seconds)
            game_seconds = projected_game_seconds(
                budget,
                conservative_sim_seconds,
                mean_native,
                mean_moves,
            )
            gates[str(gate_seconds)] = {
                "maximum_budget": budget,
                "projected_game_seconds": game_seconds,
                "projected_ruleset_policy_stage_hours": projected_stage_hours(
                    game_seconds,
                    STAGE_GAMES_PER_RULESET_POLICY,
                    STAGE_WORKERS,
                ),
                "projected_full_stage_if_uniform_rate_hours": projected_stage_hours(
                    game_seconds,
                    STAGE_TOTAL_GAMES,
                    STAGE_WORKERS,
                ),
            }
        projections[policy] = {
            "conservative_simulation_seconds": conservative_sim_seconds,
            "conservative_simulation_p95_seconds": conservative_p95,
            "decision_gates": gates,
        }

    return {
        "rules_revision": get_ruleset_spec(rules).evaluation_id,
        "board_size": BOARD_SIZE,
        "midgame_prefix_moves": PREFIX_MOVES,
        "midgame_state_hash": stable_hash(repr(positions["midgame"].key())),
        "native_standard": native,
        "single_simulation": simulations,
        "random_game_length": {
            "repetitions": len(lengths),
            "mean_moves": mean_moves,
            "minimum_moves": min(lengths),
            "maximum_moves": max(lengths),
        },
        "projections": projections,
    }


def _aggregate_gate(measurements, gate_seconds):
    gate_key = str(gate_seconds)
    budgets = []
    stage_seconds = 0.0
    decision_p95 = 0.0
    for measurement in measurements.values():
        moves = measurement["random_game_length"]["mean_moves"]
        native_seconds = max(
            item["mean_seconds"]
            for item in measurement["native_standard"].values()
        )
        for policy in POLICIES:
            projection = measurement["projections"][policy]
            budget = projection["decision_gates"][gate_key]["maximum_budget"]
            budgets.append(budget)
            decision_p95 = max(
                decision_p95,
                budget * projection["conservative_simulation_p95_seconds"],
            )
    common_budget = min(budgets)
    if common_budget >= 1:
        for measurement in measurements.values():
            moves = measurement["random_game_length"]["mean_moves"]
            native_seconds = max(
                item["mean_seconds"]
                for item in measurement["native_standard"].values()
            )
            for policy in POLICIES:
                simulation_seconds = measurement["projections"][policy][
                    "conservative_simulation_seconds"
                ]
                stage_seconds += (
                    projected_game_seconds(
                        common_budget,
                        simulation_seconds,
                        native_seconds,
                        moves,
                    )
                    * STAGE_GAMES_PER_RULESET_POLICY
                )
        stage_hours = stage_seconds / STAGE_WORKERS / 3600.0
    else:
        stage_hours = None
    return {
        "maximum_common_budget": common_budget,
        "projected_stage_wall_hours": stage_hours,
        "projected_per_decision_p95_seconds": decision_p95,
        "supports_predeclared_16_32_ladder": common_budget >= REVISED_LADDER[-1],
        "passes_feasibility_gate": passes_feasibility_gate(
            maximum_common_budget=common_budget,
            projected_hours=stage_hours,
            per_decision_p95=decision_p95,
        ),
    }


def validate_outcome_blind(payload):
    def visit(value):
        if isinstance(value, dict):
            forbidden = FORBIDDEN_MEASUREMENT_KEYS & set(value)
            if forbidden:
                raise ValueError(
                    "outcome-blind payload contains forbidden keys: "
                    + ", ".join(sorted(forbidden))
                )
            for nested in value.values():
                visit(nested)
        elif isinstance(value, list):
            for nested in value:
                visit(nested)

    visit(payload.get("measurements", {}))
    if payload.get("evidence_eligible") is not False:
        raise ValueError("feasibility output cannot be evidence eligible")
    if payload.get("outcomes_inspected") is not False:
        raise ValueError("feasibility output cannot inspect outcomes")
    if payload.get("decisions_inspected") is not False:
        raise ValueError("feasibility output cannot inspect decisions")


def write_json_atomic(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n"
    )
    temporary.replace(path)


def run_measurements(*, seed, repetitions, max_wall_seconds):
    started = time.perf_counter()
    deadline = started + max_wall_seconds
    measurements = {}
    for rules in RULESETS:
        measurements[rules] = _measure_ruleset(
            rules, seed, repetitions, deadline
        )
    aggregate = {
        str(gate): _aggregate_gate(measurements, gate)
        for gate in DECISION_GATES
    }
    payload = {
        "format": FORMAT,
        "version": VERSION,
        "created_date": "2026-07-15",
        "evidence_eligible": False,
        "outcomes_inspected": False,
        "decisions_inspected": False,
        "purpose": "Timing and game-length feasibility only",
        "configuration": {
            "rulesets": list(RULESETS),
            "board_size": BOARD_SIZE,
            "seed": seed,
            "repetitions_per_cell": repetitions,
            "midgame_prefix_moves": PREFIX_MOVES,
            "decision_gates_seconds": list(DECISION_GATES),
            "stage_games_per_ruleset_policy": STAGE_GAMES_PER_RULESET_POLICY,
            "stage_total_games": STAGE_TOTAL_GAMES,
            "stage_workers": STAGE_WORKERS,
            "revised_diagnostic_ladder": list(REVISED_LADDER),
            "maximum_stage_hours": MAX_STAGE_HOURS,
            "maximum_measurement_wall_seconds": max_wall_seconds,
        },
        "provenance": {
            "source_commit": source_commit(),
            "harness_sha256": file_hash(Path(__file__)),
            "mcts_agent_hash": MCTS_AGENT_HASH,
            "native_evaluator_hash": NATIVE_EVALUATOR_HASH,
            "ruleset_registry_hash": stable_hash(rulesets_public()),
            "engine_sha256": {
                name: file_hash(ENGINE_ROOT / name)
                for name in (
                    "actions.py",
                    "mcts.py",
                    "native_evaluators.py",
                    "opponent.py",
                    "varde.py",
                )
            },
        },
        "measurements": measurements,
        "aggregate_decision_gates": aggregate,
        "measurement_wall_seconds": time.perf_counter() - started,
        "claim_limits": {
            "calibration_relaunch_blocked": True,
            "strategic_depth_claim_blocked": True,
            "balance_claim_blocked": True,
            "old_and_redesigned_results_must_not_be_pooled": True,
        },
    }
    validate_outcome_blind(payload)
    payload["payload_hash"] = stable_hash(payload)
    return payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--seed", type=int, default=20260715)
    parser.add_argument("--repetitions", type=int, default=2)
    parser.add_argument("--max-wall-seconds", type=float, default=1800.0)
    args = parser.parse_args()
    if args.repetitions < 1 or args.max_wall_seconds <= 0:
        parser.error("repetitions and wall limit must be positive")
    try:
        payload = run_measurements(
            seed=args.seed,
            repetitions=args.repetitions,
            max_wall_seconds=args.max_wall_seconds,
        )
    except (AssertionError, RuntimeError, TimeoutError, ValueError) as exc:
        parser.error(str(exc))
    write_json_atomic(args.output, payload)
    print(args.output)


if __name__ == "__main__":
    main()
