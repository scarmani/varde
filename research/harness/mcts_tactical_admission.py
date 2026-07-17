#!/usr/bin/env python3
"""Run the frozen, outcome-blind tactical admission ladder for terminal MCTS."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time


REPO_ROOT = Path(__file__).resolve().parents[2]
ENGINE_ROOT = REPO_ROOT / "engine"
HARNESS_ROOT = Path(__file__).resolve().parent
for root in (ENGINE_ROOT, HARNESS_ROOT):
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

from actions import apply_action, legal_actions  # noqa: E402
from mcts import MCTS_AGENT_HASH, choose_mcts_state_action  # noqa: E402
from mcts_tactical_fixtures import (  # noqa: E402
    FIXTURE_VERSION,
    fixture_catalog,
    tactical_positions,
)
from mcts_telemetry import action_key, annotate_choice, tactical_context  # noqa: E402


FORMAT = "varde-mcts-tactical-admission"
VERSION = 2
RECIPE = "terminal-mcts-tactical-admission-v2"
DEFAULT_OUTPUT = Path.home() / "varde-runs" / "mcts-tactical-admission"
DEFAULT_BUDGETS = (4, 16, 64)
DEFAULT_POLICIES = ("uniform", "epsilon-greedy")
DEFAULT_REPLICATES = 4
DEFAULT_SEED = 20260716021
TASK_KEYS = (
    "task_id",
    "position_id",
    "fixture_id",
    "category",
    "rules",
    "policy",
    "budget",
    "replicate",
    "seed",
)


def canonical_bytes(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()


def stable_hash(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def derive_seed(*parts):
    return int.from_bytes(hashlib.sha256(canonical_bytes(parts)).digest()[:8], "big")


def source_commit():
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def code_hash():
    paths = (
        Path(__file__),
        HARNESS_ROOT / "mcts_tactical_fixtures.py",
        HARNESS_ROOT / "mcts_telemetry.py",
        ENGINE_ROOT / "actions.py",
        ENGINE_ROOT / "mcts.py",
        ENGINE_ROOT / "varde.py",
    )
    digest = hashlib.sha256()
    for path in paths:
        digest.update(str(path.relative_to(REPO_ROOT)).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def provenance(*, schema_version=FIXTURE_VERSION, positions=None):
    positions = tactical_positions() if positions is None else tuple(positions)
    return {
        "source_commit": source_commit(),
        "code_hash": code_hash(),
        "mcts_agent_hash": MCTS_AGENT_HASH,
        "fixture_catalog_hash": stable_hash(fixture_catalog(
            schema_version=schema_version,
            positions=positions,
        )),
        "files": {
            str(path.relative_to(REPO_ROOT)): file_hash(path)
            for path in (
                Path(__file__),
                HARNESS_ROOT / "mcts_tactical_fixtures.py",
                HARNESS_ROOT / "mcts_telemetry.py",
                ENGINE_ROOT / "actions.py",
                ENGINE_ROOT / "mcts.py",
                ENGINE_ROOT / "varde.py",
            )
        },
    }


def validate_config(config):
    budgets = config.get("budgets")
    policies = config.get("policies")
    replicates = config.get("replicates")
    seed = config.get("seed")
    if (
        not isinstance(budgets, list)
        or not budgets
        or any(isinstance(item, bool) or not isinstance(item, int) or item < 1
               for item in budgets)
        or budgets != sorted(set(budgets))
    ):
        raise ValueError("budgets must be unique increasing positive integers")
    if policies != list(dict.fromkeys(policies or [])) or not policies:
        raise ValueError("policies must be a non-empty unique list")
    if any(policy not in DEFAULT_POLICIES for policy in policies):
        raise ValueError("unknown rollout policy")
    if isinstance(replicates, bool) or not isinstance(replicates, int) or replicates < 1:
        raise ValueError("replicates must be a positive integer")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")


def build_schedule(config, *, positions=None, schema_version=VERSION):
    validate_config(config)
    positions = tactical_positions() if positions is None else tuple(positions)
    tasks = []
    for position in positions:
        public = position.public_dict(schema_version=schema_version)
        for policy in config["policies"]:
            for budget in config["budgets"]:
                for replicate in range(config["replicates"]):
                    task = {
                        "task_id": len(tasks),
                        "position_id": position.id,
                        "fixture_id": position.fixture_id,
                        "category": position.category,
                        "rules": position.state.game.rules,
                        "policy": policy,
                        "budget": budget,
                        "replicate": replicate,
                        "seed": derive_seed(
                            config["seed"], position.id, policy, budget, replicate
                        ),
                        "root_legal_actions": public["legal_actions"],
                        "state_key_sha256": public["state_key_sha256"],
                        "acceptable_actions": public["acceptable_actions"],
                    }
                    if schema_version >= 2:
                        task.update({
                            "evidence_class": public["evidence_class"],
                            "proof_sha256": (
                                stable_hash(public["proof"])
                                if public["proof"] is not None
                                else None
                            ),
                        })
                    tasks.append(task)
    return tasks


def _base_record(task):
    record = {key: task[key] for key in TASK_KEYS} | {
        "root_legal_actions": task["root_legal_actions"],
        "state_key_sha256": task["state_key_sha256"],
        "acceptable_actions": task["acceptable_actions"],
    }
    for key in ("evidence_class", "proof_sha256"):
        if key in task:
            record[key] = task[key]
    return record


def _validate_root_telemetry(decision, expected_actions):
    telemetry = decision.root_actions
    if len(telemetry) != expected_actions:
        raise AssertionError("root telemetry action count differs")
    if len({item["action_id"] for item in telemetry}) != len(telemetry):
        raise AssertionError("root telemetry action ids are not unique")
    if [item["final_rank"] for item in telemetry] != list(
        range(1, len(telemetry) + 1)
    ):
        raise AssertionError("root telemetry ranks are not contiguous")
    if sum(item["visits"] for item in telemetry) != decision.simulations:
        raise AssertionError("root telemetry visits do not reconcile")
    for item in telemetry:
        if item["wins"] + item["draws"] + item["losses"] != item["visits"]:
            raise AssertionError("root W/D/L counts do not reconcile")
        if item["terminal_margin_count"] != item["visits"]:
            raise AssertionError("root margin counts do not reconcile")
    selected = [item for item in telemetry if item["selected"]]
    if len(selected) != 1 or selected[0]["final_rank"] != 1:
        raise AssertionError("root telemetry selected rank differs")
    if selected[0]["action_id"] != action_key(decision.action):
        raise AssertionError("root telemetry selected action differs")


def evaluate_task(task):
    """Evaluate one canonical position without inspecting a game outcome."""
    record = _base_record(task)
    positions = {position.id: position for position in tactical_positions()}
    position = positions[task["position_id"]]
    state = position.state
    before = state.key()
    try:
        context = tactical_context(state)
        started = time.perf_counter()
        decision = choose_mcts_state_action(
            state,
            state.actor_color,
            simulations=task["budget"],
            seed=task["seed"],
            rollout_policy=task["policy"],
            include_root_telemetry=True,
        )
        elapsed_ms = (time.perf_counter() - started) * 1000
        state_unchanged = state.key() == before
        if not state_unchanged:
            raise AssertionError("MCTS mutated the admission position")
        if decision.action not in legal_actions(state):
            raise AssertionError("MCTS returned an illegal admission action")
        _validate_root_telemetry(decision, context["root_legal_actions"])
        next_state = apply_action(state, decision.action)
        captured = sum(
            len(wave) for wave in next_state.game.last_capture_waves
        )
        record.update({
            "status": "complete",
            "error": None,
            "action": action_key(decision.action),
            "hit": decision.action in position.acceptable_actions,
            "state_unchanged": state_unchanged,
            "captured": captured,
            "decision": {
                "simulations": decision.simulations,
                "nodes": decision.nodes,
                "mean_value": round(decision.mean_value, 6),
                "average_rollout_actions": round(
                    decision.average_rollout_actions, 3
                ),
                "max_rollout_actions": decision.max_rollout_actions,
                "selection_reason": decision.selection_reason,
                "root_action_telemetry": [
                    dict(item) for item in decision.root_actions
                ],
                "root_coverage_fraction": round(
                    sum(item["visits"] > 0 for item in decision.root_actions)
                    / context["root_legal_actions"],
                    6,
                ),
            },
            # Timing is observational and intentionally excluded from all
            # deterministic decision hashes used by the auditor.
            "timing": {"elapsed_ms": round(elapsed_ms, 3)},
            "tactical_context": context,
            "tactical_choice": annotate_choice(context, decision.action),
        })
    except Exception as exc:
        record.update({
            "status": "crash",
            "error": f"{type(exc).__name__}: {exc}",
            "action": None,
            "hit": False,
            "state_unchanged": state.key() == before,
            "captured": None,
            "decision": None,
            "timing": None,
            "tactical_context": None,
            "tactical_choice": None,
        })
    return record


def _percentile(values, fraction):
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(fraction * len(ordered) + 0.999999) - 1))
    return ordered[index]


def _metrics(records):
    complete = [record for record in records if record["status"] == "complete"]
    if not complete:
        return {
            "decisions": 0,
            "hit_rate": None,
            "nodes_mean": None,
            "nodes_p95": None,
            "average_rollout_actions_mean": None,
            "max_rollout_actions": None,
            "latency_ms_median": None,
            "latency_ms_p95": None,
            "root_coverage_fraction_mean": None,
            "selected_terminal_margin_mean": None,
            "selection_reasons": {},
        }
    nodes = [record["decision"]["nodes"] for record in complete]
    rollout = [
        record["decision"]["average_rollout_actions"] for record in complete
    ]
    latency = [record["timing"]["elapsed_ms"] for record in complete]
    coverage = [
        record["decision"]["root_coverage_fraction"] for record in complete
    ]
    selected_margins = []
    reasons = {}
    for record in complete:
        decision = record["decision"]
        reasons[decision["selection_reason"]] = (
            reasons.get(decision["selection_reason"], 0) + 1
        )
        selected = next(
            item for item in decision["root_action_telemetry"]
            if item["selected"]
        )
        if selected["terminal_margin_mean"] is not None:
            selected_margins.append(selected["terminal_margin_mean"])
    return {
        "decisions": len(complete),
        "hit_rate": sum(record["hit"] for record in complete) / len(complete),
        "nodes_mean": round(statistics.fmean(nodes), 3),
        "nodes_p95": _percentile(nodes, 0.95),
        "average_rollout_actions_mean": round(statistics.fmean(rollout), 3),
        "max_rollout_actions": max(
            record["decision"]["max_rollout_actions"] for record in complete
        ),
        "latency_ms_median": round(statistics.median(latency), 3),
        "latency_ms_p95": _percentile(latency, 0.95),
        "root_coverage_fraction_mean": round(statistics.fmean(coverage), 6),
        "selected_terminal_margin_mean": (
            round(statistics.fmean(selected_margins), 6)
            if selected_margins else None
        ),
        "selection_reasons": dict(sorted(reasons.items())),
    }


def deterministic_records_hash(records):
    deterministic = []
    for record in records:
        payload = dict(record)
        payload.pop("timing", None)
        deterministic.append(payload)
    return stable_hash(deterministic)


def summarize(records, config, run_provenance, status):
    groups = {}
    positions = {}
    for record in records:
        groups.setdefault((record["policy"], record["budget"]), []).append(record)
        positions.setdefault(
            (record["position_id"], record["policy"], record["budget"]), []
        ).append(record)

    ladder = {
        f"{policy}@{budget}": _metrics(items)
        for (policy, budget), items in sorted(groups.items())
    }
    position_ladder = {
        f"{position}|{policy}@{budget}": _metrics(items)
        for (position, policy, budget), items in sorted(positions.items())
    }
    correctness = (
        len(records) == len(build_schedule(config))
        and all(record["status"] == "complete" for record in records)
        and all(record["state_unchanged"] for record in records)
    )
    high = max(config["budgets"])
    admission_records = [
        record for record in records
        if record.get("evidence_class", "diagnostic") == "admission"
    ]
    diagnostic_records = [
        record for record in records
        if record.get("evidence_class", "diagnostic") == "diagnostic"
    ]
    high_groups = [
        items for (position, _policy, budget), items in positions.items()
        if budget == high and items[0].get("evidence_class") == "admission"
    ]
    every_position_policy_75 = bool(high_groups) and all(
        _metrics(items)["hit_rate"] >= 0.75 for items in high_groups
    )
    high_records = [
        record for record in admission_records if record["budget"] == high
    ]
    high_overall = _metrics(high_records)["hit_rate"]
    monotonic = {}
    for policy in config["policies"]:
        rates = [
            _metrics([
                record for record in groups.get((policy, budget), [])
                if record.get("evidence_class") == "admission"
            ])["hit_rate"]
            for budget in config["budgets"]
        ]
        monotonic[policy] = (
            all(rate is not None for rate in rates)
            and all(left <= right for left, right in zip(rates, rates[1:]))
        )
    gate = {
        "all_decisions_legal_nonmutating_and_complete": correctness,
        "every_high_budget_position_policy_at_least_75_percent": (
            every_position_policy_75
        ),
        "high_budget_overall_at_least_80_percent": (
            high_overall is not None and high_overall >= 0.80
        ),
        "aggregate_hit_rate_nondecreasing_by_policy": all(monotonic.values()),
    }
    return {
        "format": FORMAT,
        "version": VERSION,
        "recipe": RECIPE,
        "status": status,
        "config": config,
        "config_hash": stable_hash(config),
        "provenance": run_provenance,
        "accounting": {
            "scheduled": len(build_schedule(config)),
            "attempted": len(records),
            "complete": sum(record["status"] == "complete" for record in records),
            "crash": sum(record["status"] == "crash" for record in records),
            "pending": len(build_schedule(config)) - len(records),
        },
        "ladder": ladder,
        "position_ladder": position_ladder,
        "admission_ladder": {
            f"{policy}@{budget}": _metrics([
                record for record in items
                if record.get("evidence_class") == "admission"
            ])
            for (policy, budget), items in sorted(groups.items())
        },
        "diagnostic_ladder": {
            f"{policy}@{budget}": _metrics([
                record for record in items
                if record.get("evidence_class") == "diagnostic"
            ])
            for (policy, budget), items in sorted(groups.items())
        },
        "evidence_accounting": {
            "admission_positions": len({
                record["position_id"] for record in admission_records
            }),
            "admission_decisions": len(admission_records),
            "diagnostic_positions": len({
                record["position_id"] for record in diagnostic_records
            }),
            "diagnostic_decisions": len(diagnostic_records),
        },
        "high_budget": high,
        "high_budget_overall_hit_rate": high_overall,
        "monotonic_by_policy": monotonic,
        "admission_gate": gate,
        "admitted": all(gate.values()),
        "deterministic_records_hash": deterministic_records_hash(records),
        "interpretation": (
            "Admission positions prove strict local rule-transition dominance; "
            "natural-width positions remain diagnostics. Neither class proves a "
            "forced game outcome, match strength, balance, strategic depth, or "
            "ruleset promise."
        ),
        "paired_match_stages_launched": False,
    }


def _checkpoint_payload(state):
    payload = dict(state)
    payload.pop("checkpoint_hash", None)
    payload["checkpoint_hash"] = stable_hash(payload)
    return payload


def write_json_atomic(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n"
    )
    temporary.replace(path)


def write_jsonl_atomic(path, records):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(
        b"".join(canonical_bytes(record) + b"\n" for record in records)
    )
    temporary.replace(path)


def _write_artifacts(output_dir, state):
    output_dir = Path(output_dir)
    write_json_atomic(output_dir / "state.json", _checkpoint_payload(state))
    write_jsonl_atomic(output_dir / "decisions.jsonl", state["records"])
    write_json_atomic(
        output_dir / "summary.json",
        summarize(
            state["records"], state["config"], state["provenance"], state["status"]
        ),
    )


def load_state(path):
    payload = json.loads(Path(path).read_text())
    expected = payload.pop("checkpoint_hash", None)
    if not isinstance(expected, str) or stable_hash(payload) != expected:
        raise ValueError("admission checkpoint hash mismatch")
    payload["checkpoint_hash"] = expected
    return payload


def _ordered_results(tasks, evaluator, workers):
    if workers == 1:
        return [evaluator(task) for task in tasks]
    executor = ProcessPoolExecutor if evaluator is evaluate_task else ThreadPoolExecutor
    with executor(max_workers=workers) as pool:
        return list(pool.map(evaluator, tasks))


def run_admission(
    output_dir,
    *,
    config,
    workers=1,
    checkpoint_interval=8,
    resume=False,
    cancel_file=None,
    max_tasks=None,
    evaluator=evaluate_task,
):
    validate_config(config)
    if workers < 1 or checkpoint_interval < 1:
        raise ValueError("workers and checkpoint interval must be positive")
    output_dir = Path(output_dir)
    state_path = output_dir / "state.json"
    tasks = build_schedule(config)
    current_provenance = provenance()
    if resume:
        if not state_path.exists():
            raise ValueError("no admission checkpoint to resume")
        state = load_state(state_path)
        state.pop("checkpoint_hash", None)
        if state["config"] != config:
            raise ValueError("resume configuration does not match checkpoint")
        if state["provenance"] != current_provenance:
            raise ValueError("source or MCTS code changed since checkpoint")
    else:
        if state_path.exists():
            raise ValueError("output already contains a checkpoint; use --resume")
        output_dir.mkdir(parents=True, exist_ok=True)
        state = {
            "format": FORMAT,
            "version": VERSION,
            "recipe": RECIPE,
            "config": config,
            "provenance": current_provenance,
            "status": "running",
            "next_task": 0,
            "records": [],
        }
        _write_artifacts(output_dir, state)

    cancel_path = Path(cancel_file) if cancel_file else None
    state["status"] = "running"
    stop = len(tasks)
    if max_tasks is not None:
        stop = min(stop, state["next_task"] + max_tasks)
    while state["next_task"] < stop:
        if cancel_path and cancel_path.exists():
            state["status"] = "cancelled"
            break
        end = min(stop, state["next_task"] + checkpoint_interval)
        batch = tasks[state["next_task"]:end]
        results = _ordered_results(batch, evaluator, workers)
        for task, result in zip(batch, results):
            if result.get("task_id") != task["task_id"]:
                raise ValueError("evaluator returned an out-of-order task")
            state["records"].append(result)
            state["next_task"] += 1
        _write_artifacts(output_dir, state)
    if state["next_task"] == len(tasks):
        state["status"] = "complete"
    elif state["status"] != "cancelled":
        state["status"] = "paused"
    _write_artifacts(output_dir, state)
    return state


def _csv(value, cast=str):
    return [cast(item.strip()) for item in value.split(",") if item.strip()]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--budgets", default=",".join(map(str, DEFAULT_BUDGETS)))
    parser.add_argument("--policies", default=",".join(DEFAULT_POLICIES))
    parser.add_argument("--replicates", type=int, default=DEFAULT_REPLICATES)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--workers", type=int, default=max(1, os.cpu_count() or 1))
    parser.add_argument("--checkpoint-interval", type=int, default=8)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--cancel-file", type=Path)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--max-tasks", type=int, help=argparse.SUPPRESS)
    args = parser.parse_args()
    config = {
        "budgets": _csv(args.budgets, int),
        "policies": _csv(args.policies),
        "replicates": args.replicates,
        "seed": args.seed,
    }
    try:
        run_admission(
            args.output_dir,
            config=config,
            workers=args.workers,
            checkpoint_interval=args.checkpoint_interval,
            resume=args.resume,
            cancel_file=args.cancel_file,
            max_tasks=args.max_tasks,
        )
    except ValueError as exc:
        parser.error(str(exc))
    print(args.output_dir / "summary.json")


if __name__ == "__main__":
    main()
