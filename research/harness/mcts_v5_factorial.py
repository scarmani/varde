#!/usr/bin/env python3
"""Freeze, run, resume, and audit the MCTS Search V5 development factorial."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
from datetime import date
from functools import cache
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

from actions import legal_actions  # noqa: E402
from mcts import choose_mcts_state_action, mcts_agent_hash  # noqa: E402
from mcts_v5_corpus import corpus_catalog, development_positions  # noqa: E402
from mcts_v5_oracle import certify_goal  # noqa: E402
from mcts_v5_solver import (  # noqa: E402
    detect_root_obligations,
    scan_root_guidance,
    solve_root_obligation,
)


FORMAT = "varde-mcts-search-v5-development-factorial"
VERSION = 1
RECIPE = "mcts-search-v5-eight-arm-factorial-v1"
STACKED_BASE = "808c31720730fcf23bbc02c4549bd7151bdab3ec"
FACTORIAL_VARIANTS = tuple(
    f"v5-g{guidance}-u{unpruning}-s{settling}"
    for guidance in (0, 1)
    for unpruning in (0, 1)
    for settling in (0, 1)
)
ORDERED_INSTRUMENT = "v4-ordered-control"
BUDGETS = (4, 16, 64)
POLICIES = ("uniform", "epsilon-greedy")
REPLICATES = 4
MASTER_SEED = 20260717051
DEFAULT_OUTPUT = Path.home() / "varde-runs" / "mcts-search-v5-20260717" / "development"


def canonical_bytes(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()


def stable_hash(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def derive_seed(*parts):
    return int.from_bytes(
        hashlib.sha256(canonical_bytes(parts)).digest()[:8], "big"
    )


def source_commit():
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, check=True,
        capture_output=True, text=True,
    ).stdout.strip()


def repository_is_clean():
    result = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=REPO_ROOT, check=True, capture_output=True, text=True,
    )
    return not result.stdout.strip()


def _code_files():
    return (
        Path(__file__),
        HARNESS_ROOT / "mcts_v5_corpus.py",
        HARNESS_ROOT / "mcts_v5_oracle.py",
        ENGINE_ROOT / "actions.py",
        ENGINE_ROOT / "mcts.py",
        ENGINE_ROOT / "mcts_v5_solver.py",
        ENGINE_ROOT / "mcts_v5_unpruning.py",
        ENGINE_ROOT / "mcts_v5_settling.py",
        ENGINE_ROOT / "varde.py",
    )


def code_hash():
    digest = hashlib.sha256()
    for path in _code_files():
        digest.update(str(path.relative_to(REPO_ROOT)).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def code_hash_at_commit(commit):
    digest = hashlib.sha256()
    for path in _code_files():
        relative = str(path.relative_to(REPO_ROOT))
        content = subprocess.run(
            ["git", "show", f"{commit}:{relative}"],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
        ).stdout
        digest.update(relative.encode())
        digest.update(content)
    return digest.hexdigest()


def _position_rows():
    return tuple(position.public_dict() for position in development_positions())


@cache
def build_schedule(*, seed=MASTER_SEED):
    positions = development_positions()
    tasks = []
    for budget in BUDGETS:
        for variant in FACTORIAL_VARIANTS:
            for position in positions:
                for policy in POLICIES:
                    for replicate in range(REPLICATES):
                        tasks.append({
                            "task_id": len(tasks),
                            "kind": "factorial",
                            "variant": variant,
                            "position_id": position.id,
                            "family": position.family,
                            "width_class": position.width_class,
                            "board_size": position.state.game.board.n,
                            "board_points": len(position.state.game.board.points),
                            "decoy": position.decoy,
                            "acceptable_actions": [
                                _action_id(action)
                                for action in position.acceptable_actions
                            ],
                            "policy": policy,
                            "budget": budget,
                            "replicate": replicate,
                            "seed": derive_seed(
                                seed, variant, position.id, policy, budget,
                                replicate,
                            ),
                        })
    for position in positions:
        if position.width_class != "wide":
            continue
        for policy in POLICIES:
            for replicate in range(REPLICATES):
                tasks.append({
                    "task_id": len(tasks),
                    "kind": "ordered-control-instrument",
                    "variant": ORDERED_INSTRUMENT,
                    "position_id": position.id,
                    "family": position.family,
                    "width_class": position.width_class,
                    "board_size": position.state.game.board.n,
                    "board_points": len(position.state.game.board.points),
                    "decoy": position.decoy,
                    "acceptable_actions": [
                        _action_id(action) for action in position.acceptable_actions
                    ],
                    "policy": policy,
                    "budget": 64,
                    "replicate": replicate,
                    "seed": derive_seed(
                        seed, ORDERED_INSTRUMENT, position.id, policy, 64,
                        replicate,
                    ),
                })
    return tuple(tasks)


def build_manifest(*, output_dir, created_date=None, source_commit_value=None):
    schedule = build_schedule()
    catalog = corpus_catalog("development")
    declared_agreement = True
    guidance_agreement = True
    for position in development_positions():
        oracle = position.certificate()
        solver = solve_root_obligation(position.state, position.goal)
        declared_agreement &= (
            dict(oracle.action_statuses) == dict(solver.action_statuses)
        )
        guidance = scan_root_guidance(position.state)
        oracle_guidance = _position_oracle_guidance_statuses(position.id)
        guidance_agreement &= all(
            oracle_guidance[_action_id(action)] == status
            for action, status in guidance.action_statuses
        )
    payload = {
        "format": FORMAT,
        "version": VERSION,
        "recipe": RECIPE,
        "status": "frozen-before-factorial-outcomes",
        "created_date": created_date or date.today().isoformat(),
        "source": {
            "source_commit": source_commit_value or source_commit(),
            "stacked_base": STACKED_BASE,
            "code_hash": code_hash(),
            "files": {
                str(path.relative_to(REPO_ROOT)): file_hash(path)
                for path in _code_files()
            },
            "agent_hashes": {
                variant: mcts_agent_hash(variant)
                for variant in (*FACTORIAL_VARIANTS, ORDERED_INSTRUMENT)
            },
        },
        "corpus": {
            "manifest": "research/manifests/mcts-search-v5-development-20260717.json",
            "catalog_sha256": stable_hash(catalog),
            "positions": 24,
            "positive_positions": 18,
            "decoys": 6,
        },
        "configuration": {
            "variants": list(FACTORIAL_VARIANTS),
            "ordered_control_instrument": ORDERED_INSTRUMENT,
            "budgets": list(BUDGETS),
            "policies": list(POLICIES),
            "replicates": REPLICATES,
            "seed": MASTER_SEED,
            "factorial_tasks": len(schedule) - 96,
            "instrument_tasks": 96,
            "tasks": len(schedule),
            "task_schedule_sha256": stable_hash(schedule),
            "task_order": "budget-variant-position-policy-replicate-then-instrument",
        },
        "preflight": {
            "declared_oracle_solver_agreement": bool(declared_agreement),
            "oracle_solver_agreement": bool(guidance_agreement),
            "root_scan_once_required": True,
            "terminal_backups_only": True,
            "holdout_not_loaded": True,
        },
        "gates": {
            "pooled_admission_at_64": 0.80,
            "positive_position_policy_cell_at_64": "3/4",
            "monotonic_by_policy": True,
            "mandatory_wide_median_visits_at_64": 3,
            "unpruning_delta_over_ordered_control": 0.10,
            "settling_mean_rollout_reduction": 0.50,
            "settling_p95_latency_reduction": 0.40,
            "settling_admission_floor_delta": -0.05,
            "max_rollout_actions": "4P",
            "integrity_failures": 0,
        },
        "execution": {
            "output_dir": str(Path(output_dir).expanduser().resolve()),
            "raw_output_repository_external": True,
            "checkpoint_resume": True,
            "worker_count_invariant": True,
        },
        "claim_limits": {
            "development_tactical_admission_only": True,
            "holdout_evidence": False,
            "strength_evidence": False,
            "balance_evidence": False,
            "strategic_depth_evidence": False,
        },
    }
    payload["payload_sha256"] = stable_hash(payload)
    return payload


def validate_manifest(manifest):
    payload = dict(manifest)
    expected = payload.pop("payload_sha256", None)
    if stable_hash(payload) != expected:
        raise ValueError("factorial manifest payload hash mismatch")
    if manifest["source"]["code_hash"] != code_hash():
        commit = manifest["source"]["source_commit"]
        if manifest["source"]["code_hash"] != code_hash_at_commit(commit):
            raise ValueError("factorial source code hash mismatch")
        for relative, expected_hash in manifest["source"]["files"].items():
            content = subprocess.run(
                ["git", "show", f"{commit}:{relative}"],
                cwd=REPO_ROOT,
                check=True,
                capture_output=True,
            ).stdout
            if hashlib.sha256(content).hexdigest() != expected_hash:
                raise ValueError("factorial historical source file mismatch")
    if manifest["configuration"]["task_schedule_sha256"] != stable_hash(
        build_schedule(seed=manifest["configuration"]["seed"])
    ):
        raise ValueError("factorial task schedule hash mismatch")
    if not manifest["preflight"]["oracle_solver_agreement"]:
        raise ValueError("oracle/solver preflight did not pass")
    return True


def regenerate_manifest(manifest):
    """Regenerate a frozen manifest while preserving its exact source snapshot."""
    rebuilt = build_manifest(
        output_dir=manifest["execution"]["output_dir"],
        created_date=manifest["created_date"],
        source_commit_value=manifest["source"]["source_commit"],
    )
    rebuilt["source"] = manifest["source"]
    rebuilt.pop("payload_sha256", None)
    rebuilt["payload_sha256"] = stable_hash(rebuilt)
    return rebuilt


def _action_id(action):
    if action.point is None:
        return action.kind
    return f"{action.kind}:{action.point[0]},{action.point[1]}"


def _oracle_guidance_statuses(state):
    """Classify the detected proof set with the independent exhaustive oracle."""
    actions = tuple(legal_actions(state))
    remaining = 10_000
    certificates = []
    for obligation in detect_root_obligations(state):
        if remaining <= 0:
            break
        certificate = certify_goal(state, obligation, node_limit=remaining)
        certificates.append(certificate)
        remaining -= certificate.nodes
    by_action = {}
    for action in actions:
        statuses = [
            dict(certificate.action_statuses)[action]
            for certificate in certificates
        ]
        by_action[_action_id(action)] = (
            "proven" if "proven" in statuses
            else "disproven" if statuses and all(
                status == "disproven" for status in statuses
            )
            else "unknown"
        )
    return by_action


@cache
def _position_oracle_guidance_statuses(position_id):
    position = next(
        item for item in development_positions() if item.id == position_id
    )
    return _oracle_guidance_statuses(position.state)


def evaluate_task(task):
    positions = {position.id: position for position in development_positions()}
    position = positions[task["position_id"]]
    state = position.state
    before = state.key()
    base = {key: task[key] for key in (
        "task_id", "kind", "variant", "position_id", "family",
        "width_class", "board_size", "board_points", "decoy", "policy", "budget",
        "replicate", "seed",
    )}
    try:
        started = time.perf_counter()
        decision = choose_mcts_state_action(
            state,
            state.actor_color,
            simulations=task["budget"],
            seed=task["seed"],
            rollout_policy=task["policy"],
            search_variant=task["variant"],
            include_root_telemetry=True,
        )
        elapsed_ms = (time.perf_counter() - started) * 1000
        if state.key() != before:
            raise AssertionError("factorial decision mutated the position")
        if decision.action not in legal_actions(state):
            raise AssertionError("factorial decision is illegal")
        if len(decision.root_actions) != len(legal_actions(state)):
            raise AssertionError("factorial root telemetry is incomplete")
        if sum(item["visits"] for item in decision.root_actions) != task["budget"]:
            raise AssertionError("factorial root visits do not reconcile")
        if decision.terminal_backups != task["budget"]:
            raise AssertionError("factorial backed up a nonterminal result")
        if (
            task["variant"].endswith("s1")
            and decision.max_rollout_actions > task["board_points"] * 4
        ):
            raise AssertionError("factorial rollout exceeded 4P")
        selected = _action_id(decision.action)
        mandatory_visits = [
            item["visits"] for item in decision.root_actions
            if item["mandatory_exposure"]
        ]
        oracle_statuses = (
            _position_oracle_guidance_statuses(position.id)
            if "-g1-" in f"-{task['variant']}-" else None
        )
        oracle_solver_agreement = (
            None if oracle_statuses is None else all(
                oracle_statuses[item["action_id"]]
                == item["proof_guidance_status"]
                for item in decision.root_actions
            )
        )
        false_positive_guidance = (
            False if oracle_statuses is None else any(
                item["proof_guidance_status"] == "proven"
                and oracle_statuses[item["action_id"]] != "proven"
                for item in decision.root_actions
            )
        )
        return {
            **base,
            "status": "complete",
            "error": None,
            "action": selected,
            "hit": (
                None if position.decoy
                else selected in task["acceptable_actions"]
            ),
            "elapsed_ms": round(elapsed_ms, 3),
            "average_rollout_actions": round(
                decision.average_rollout_actions, 6
            ),
            "max_rollout_actions": decision.max_rollout_actions,
            "terminal_backups": decision.terminal_backups,
            "solver_status": decision.solver_status,
            "solver_nodes": decision.solver_nodes,
            "solver_elapsed_ms": round(decision.solver_elapsed_ms, 3),
            "solver_invocations": decision.solver_invocations,
            "solver_overrides": decision.solver_overrides,
            "oracle_solver_agreement": oracle_solver_agreement,
            "exposed_actions": decision.exposed_actions,
            "hidden_actions": decision.hidden_actions,
            "mandatory_actions": decision.mandatory_actions,
            "mandatory_visits": mandatory_visits,
            "false_positive_guidance": false_positive_guidance,
            "selection_reason": decision.selection_reason,
            "deterministic_decision_sha256": stable_hash({
                "action": selected,
                "mean": decision.mean_value,
                "root": [
                    {
                        "action": item["action_id"],
                        "visits": item["visits"],
                        "value_sum": item["value_sum"],
                        "margin_sum": item["terminal_margin_sum"],
                        "proof": item["proof_guidance_status"],
                        "exposed": item["exposed"],
                        "mandatory": item["mandatory_exposure"],
                    }
                    for item in decision.root_actions
                ],
            }),
        }
    except Exception as exc:
        return {
            **base,
            "status": "crash",
            "error": f"{type(exc).__name__}: {exc}",
            "action": None,
            "hit": False,
            "elapsed_ms": None,
        }


def _percentile(values, fraction):
    ordered = sorted(values)
    if not ordered:
        return None
    rank = max(1, math_ceil(len(ordered) * fraction))
    return ordered[min(len(ordered), rank) - 1]


def math_ceil(value):
    return int(value) if value == int(value) else int(value) + 1


def _rate(records):
    scored = [record for record in records if record["hit"] is not None]
    return sum(record["hit"] for record in scored) / len(scored) if scored else None


def _metrics(records):
    complete = [record for record in records if record["status"] == "complete"]
    return {
        "decisions": len(complete),
        "hit_rate": _rate(complete),
        "mean_rollout_actions": (
            statistics.fmean(item["average_rollout_actions"] for item in complete)
            if complete else None
        ),
        "latency_ms_p95": _percentile(
            [item["elapsed_ms"] for item in complete], 0.95
        ),
        "max_rollout_actions": max(
            (item["max_rollout_actions"] for item in complete), default=None
        ),
    }


def audit_records(records, manifest):
    expected = len(build_schedule(seed=manifest["configuration"]["seed"]))
    if len(records) != expected:
        raise ValueError("complete factorial audit requires every scheduled record")
    integrity = {
        "scheduled": expected,
        "records": len(records),
        "complete": sum(item["status"] == "complete" for item in records),
        "crash": sum(item["status"] == "crash" for item in records),
        "false_positive_guidance": sum(
            item.get("false_positive_guidance", False) for item in records
        ),
        "oracle_solver_disagreements": sum(
            item.get("oracle_solver_agreement") is False for item in records
        ),
        "terminal_backups": sum(
            item.get("terminal_backups", 0) for item in records
        ),
        "expected_terminal_backups": sum(
            item["budget"] for item in records
            if item["status"] == "complete"
        ),
    }
    integrity["passed"] = (
        integrity["records"] == integrity["scheduled"]
        and integrity["complete"] == integrity["scheduled"]
        and integrity["crash"] == 0
        and integrity["false_positive_guidance"] == 0
        and integrity["oracle_solver_disagreements"] == 0
        and integrity["terminal_backups"]
        == integrity["expected_terminal_backups"]
    )
    variants = {}
    for variant in FACTORIAL_VARIANTS:
        selected = [
            item for item in records
            if item["variant"] == variant and item["kind"] == "factorial"
        ]
        high = [item for item in selected if item["budget"] == 64]
        high_positive = [item for item in high if not item["decoy"]]
        cells = {}
        for position_id in sorted({item["position_id"] for item in high_positive}):
            for policy in POLICIES:
                cell = [
                    item for item in high_positive
                    if item["position_id"] == position_id
                    and item["policy"] == policy
                ]
                cells[f"{position_id}|{policy}"] = _rate(cell)
        monotonic = {}
        for policy in POLICIES:
            rates = [
                _rate([
                    item for item in selected
                    if item["budget"] == budget and item["policy"] == policy
                    and not item["decoy"]
                ])
                for budget in BUDGETS
            ]
            monotonic[policy] = all(
                left <= right for left, right in zip(rates, rates[1:])
            )
        mandatory = [
            visit
            for item in high
            if item["width_class"] == "wide"
            for visit in item.get("mandatory_visits", [])
        ]
        guidance = "-g1-" in f"-{variant}-"
        unpruning = "-u1-" in f"-{variant}-"
        scan_once = all(
            item.get("solver_invocations") == (1 if guidance else 0)
            for item in selected
        )
        oracle_agreement = all(
            item.get("oracle_solver_agreement") is True
            for item in selected
        ) if guidance else True
        scan_latency = {
            str(board_size): _percentile([
                item["solver_elapsed_ms"] for item in selected
                if item["board_size"] == board_size
            ], 0.95)
            for board_size in (3, 4)
        } if guidance else {"3": None, "4": None}
        mandatory_median = (
            statistics.median(mandatory) if mandatory else None
        )
        gate = {
            "pooled_64_at_least_80_percent": _rate(high_positive) >= 0.80,
            "every_positive_cell_at_least_3_of_4": all(
                rate >= 0.75 for rate in cells.values()
            ),
            "monotonic_both_policies": all(monotonic.values()),
            "root_scan_exactly_once_when_guided": scan_once,
            "oracle_solver_agreement": oracle_agreement,
            "root_scan_latency": (
                not guidance or (
                    scan_latency["3"] < 100
                    and scan_latency["4"] < 400
                )
            ),
            "mandatory_wide_median_at_least_3": (
                not unpruning or (
                    mandatory_median is not None and mandatory_median >= 3
                )
            ),
            "integrity_clean": all(
                item["status"] == "complete" for item in selected
            ),
        }
        variants[variant] = {
            "overall": _metrics(selected),
            "high_64": _metrics(high_positive),
            "cells": cells,
            "monotonic": monotonic,
            "root_scan_latency_ms_p95": scan_latency,
            "mandatory_wide_median_visits": mandatory_median,
            "gate": gate,
            "admitted": all(gate.values()),
        }

    ordered = [
        item for item in records if item["kind"] == "ordered-control-instrument"
        and not item["decoy"]
    ]
    unpruned = [
        item for item in records
        if item["variant"] == "v5-g0-u1-s0" and item["budget"] == 64
        and item["width_class"] == "wide" and not item["decoy"]
    ]
    unpruning_delta = _rate(unpruned) - _rate(ordered)

    settling = {}
    for guidance in (0, 1):
        for unpruning in (0, 1):
            base = f"v5-g{guidance}-u{unpruning}-s0"
            candidate = f"v5-g{guidance}-u{unpruning}-s1"
            base_records = [item for item in records if item["variant"] == base]
            candidate_records = [
                item for item in records if item["variant"] == candidate
            ]
            base_metrics = _metrics(base_records)
            candidate_metrics = _metrics(candidate_records)
            mean_reduction = 1 - (
                candidate_metrics["mean_rollout_actions"]
                / base_metrics["mean_rollout_actions"]
            )
            latency_reduction = 1 - (
                candidate_metrics["latency_ms_p95"]
                / base_metrics["latency_ms_p95"]
            )
            admission_delta = (
                variants[candidate]["high_64"]["hit_rate"]
                - variants[base]["high_64"]["hit_rate"]
            )
            within_four_p = all(
                item["max_rollout_actions"] <= 4 * item["board_points"]
                for item in candidate_records
                if item["status"] == "complete"
            )
            settling[candidate] = {
                "matched_base": base,
                "mean_rollout_reduction": mean_reduction,
                "p95_latency_reduction": latency_reduction,
                "admission_delta": admission_delta,
                "all_rollouts_within_4p": within_four_p,
                "qualified": (
                    mean_reduction >= 0.50
                    and latency_reduction >= 0.40
                    and admission_delta >= -0.05
                    and within_four_p
                ),
            }

    attribution = {}
    for variant in FACTORIAL_VARIANTS:
        rate = variants[variant]["high_64"]["hit_rate"]
        removals = {}
        parts = variant.split("-")
        for index, part in enumerate(parts):
            if part in ("g1", "u1", "s1"):
                removed = list(parts)
                removed[index] = part[0] + "0"
                other_variant = "-".join(removed)
                removals[part[0]] = {
                    "recipe": other_variant,
                    "delta": rate - variants[other_variant]["high_64"]["hit_rate"],
                }
        attribution[variant] = removals

    eligible = []
    for variant in FACTORIAL_VARIANTS:
        if variant == "v5-g0-u0-s0" or not integrity["passed"]:
            continue
        if not variants[variant]["admitted"]:
            continue
        factors = attribution[variant]
        if any(item["delta"] <= 0 for item in factors.values()):
            continue
        if "u1" in variant and unpruning_delta < 0.10:
            continue
        if variant.endswith("s1") and not settling[variant]["qualified"]:
            continue
        eligible.append(variant)
    eligible.sort(key=lambda variant: (
        -variants[variant]["high_64"]["hit_rate"],
        variants[variant]["overall"]["latency_ms_p95"],
        variant,
    ))
    selected = eligible[0] if eligible else None
    payload = {
        "format": "varde-mcts-search-v5-development-factorial-audit",
        "version": 1,
        "status": "complete",
        "manifest_payload_sha256": manifest["payload_sha256"],
        "integrity": integrity,
        "variants": variants,
        "unpruning": {
            "ordered_control_hit_rate": _rate(ordered),
            "reserved_unpruning_hit_rate": _rate(unpruned),
            "delta": unpruning_delta,
            "delta_at_least_10_points": unpruning_delta >= 0.10,
        },
        "settling": settling,
        "factorial_attribution": attribution,
        "selection": {
            "eligible_recipes": eligible,
            "selected_recipe": selected,
            "holdout_may_run": selected is not None,
        },
        "deterministic_records_sha256": stable_hash([
            {key: value for key, value in record.items() if key != "elapsed_ms"}
            for record in records
        ]),
        "claim_limits": manifest["claim_limits"],
    }
    payload["payload_sha256"] = stable_hash(payload)
    return payload


def progress_audit(records, manifest, status):
    payload = {
        "format": "varde-mcts-search-v5-development-factorial-progress",
        "version": 1,
        "status": status,
        "manifest_payload_sha256": manifest["payload_sha256"],
        "scheduled": manifest["configuration"]["tasks"],
        "records": len(records),
        "complete": sum(item["status"] == "complete" for item in records),
        "crash": sum(item["status"] == "crash" for item in records),
        "last_task_id": records[-1]["task_id"] if records else None,
        "deterministic_records_sha256": stable_hash([
            {key: value for key, value in record.items() if key != "elapsed_ms"}
            for record in records
        ]),
    }
    payload["payload_sha256"] = stable_hash(payload)
    return payload


def write_json_atomic(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def write_jsonl_atomic(path, records):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(b"".join(canonical_bytes(item) + b"\n" for item in records))
    temporary.replace(path)


def _checkpoint_payload(state):
    payload = dict(state)
    payload.pop("checkpoint_sha256", None)
    payload["checkpoint_sha256"] = stable_hash(payload)
    return payload


def load_checkpoint(path):
    payload = json.loads(Path(path).read_text())
    expected = payload.pop("checkpoint_sha256", None)
    if not isinstance(expected, str) or stable_hash(payload) != expected:
        raise ValueError("factorial checkpoint hash mismatch")
    return payload


def _write_checkpoint(output_dir, state, manifest):
    output_dir = Path(output_dir)
    write_json_atomic(output_dir / "state.json", _checkpoint_payload(state))
    write_jsonl_atomic(output_dir / "decisions.jsonl", state["records"])
    expected = manifest["configuration"]["tasks"]
    if len(state["records"]) == expected:
        write_json_atomic(
            output_dir / "audit.json",
            audit_records(state["records"], manifest),
        )
    else:
        write_json_atomic(
            output_dir / "progress.json",
            progress_audit(state["records"], manifest, state["status"]),
        )


def run_factorial(
    manifest,
    output_dir,
    *,
    workers=1,
    checkpoint_interval=8,
    resume=False,
    max_tasks=None,
    evaluator=evaluate_task,
):
    validate_manifest(manifest)
    if workers < 1 or checkpoint_interval < 1:
        raise ValueError("workers and checkpoint interval must be positive")
    tasks = build_schedule(seed=manifest["configuration"]["seed"])
    output_dir = Path(output_dir)
    state_path = output_dir / "state.json"
    if resume:
        state = load_checkpoint(state_path)
        if state["manifest_payload_sha256"] != manifest["payload_sha256"]:
            raise ValueError("factorial resume manifest mismatch")
    else:
        if state_path.exists():
            raise ValueError("factorial output exists; use --resume")
        state = {
            "format": FORMAT,
            "version": VERSION,
            "status": "running",
            "manifest_payload_sha256": manifest["payload_sha256"],
            "next_task": 0,
            "records": [],
        }
        _write_checkpoint(output_dir, state, manifest)
    stop = len(tasks)
    if max_tasks is not None:
        stop = min(stop, state["next_task"] + max_tasks)
    pool = (
        ProcessPoolExecutor(max_workers=workers)
        if workers > 1 else None
    )
    try:
        while state["next_task"] < stop:
            end = min(stop, state["next_task"] + checkpoint_interval)
            batch = tasks[state["next_task"]:end]
            results = (
                list(pool.map(evaluator, batch))
                if pool is not None
                else [evaluator(task) for task in batch]
            )
            for task, result in zip(batch, results):
                if result["task_id"] != task["task_id"]:
                    raise ValueError("factorial evaluator reordered tasks")
                state["records"].append(result)
                state["next_task"] += 1
            _write_checkpoint(output_dir, state, manifest)
            if any(result["status"] != "complete" for result in results):
                state["status"] = "failed-integrity"
                _write_checkpoint(output_dir, state, manifest)
                return state
    finally:
        if pool is not None:
            pool.shutdown()
    state["status"] = "complete" if state["next_task"] == len(tasks) else "paused"
    _write_checkpoint(output_dir, state, manifest)
    return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--workers", type=int, default=max(1, os.cpu_count() or 1))
    parser.add_argument("--checkpoint-interval", type=int, default=8)
    parser.add_argument("--max-tasks", type=int, help=argparse.SUPPRESS)
    args = parser.parse_args()
    modes = sum((args.freeze, args.check, args.run))
    if modes != 1:
        parser.error("choose exactly one of --freeze, --check, or --run")
    if args.freeze:
        if not repository_is_clean():
            parser.error("tracked repository changes must be committed before freeze")
        if args.manifest.exists():
            parser.error("manifest already exists")
        payload = build_manifest(output_dir=args.output_dir)
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        print(args.manifest)
        return
    manifest = json.loads(args.manifest.read_text())
    if args.check:
        validate_manifest(manifest)
        rebuilt = regenerate_manifest(manifest)
        if rebuilt != manifest:
            raise SystemExit("factorial manifest differs from regeneration")
        print(args.manifest)
        return
    state = run_factorial(
        manifest,
        args.output_dir,
        workers=args.workers,
        checkpoint_interval=args.checkpoint_interval,
        resume=args.resume,
        max_tasks=args.max_tasks,
    )
    print(args.output_dir / "audit.json")
    if state["status"] == "failed-integrity":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
