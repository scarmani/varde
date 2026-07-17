#!/usr/bin/env python3
"""Evaluate Candidate A against the frozen local-obligation certificates."""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
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
from mcts import mcts_agent_hash  # noqa: E402
from mcts_tactical_admission import file_hash, stable_hash  # noqa: E402
from mcts_tactical_solver import (  # noqa: E402
    DEFAULT_NODE_LIMIT,
    solve_local_obligation,
)
from mcts_v4_holdout import (  # noqa: E402
    decoy_positions,
    positive_positions,
    state_hash,
)


FORMAT = "varde-mcts-search-v4-solver-feasibility"
VERSION = 1
RECIPE_ID = "mcts-search-v4-certified-solver-v1"


def source_commit():
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _code_files():
    return (
        Path(__file__),
        ENGINE_ROOT / "mcts_tactical_solver.py",
        ENGINE_ROOT / "mcts.py",
        ENGINE_ROOT / "actions.py",
        ENGINE_ROOT / "varde.py",
        HARNESS_ROOT / "mcts_v4_holdout.py",
    )


def _code_hash():
    digest = hashlib.sha256()
    for path in _code_files():
        digest.update(str(path.relative_to(REPO_ROOT)).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _percentile(values, fraction):
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, int(len(ordered) * fraction + 0.999999))
    return ordered[min(len(ordered), rank) - 1]


def _action_id(action):
    if action is None:
        return None
    if action.point is None:
        return action.kind
    return f"{action.kind}:{action.point[0]},{action.point[1]}"


def evaluate_position(position):
    before = position.state.key()
    started = time.perf_counter()
    result = solve_local_obligation(
        position.state,
        position.obligation,
        node_limit=DEFAULT_NODE_LIMIT,
    )
    elapsed_ms = (time.perf_counter() - started) * 1000
    statuses = {
        _action_id(action): status for action, status in result.action_statuses
    }
    expected = position.certificate["action_statuses"]
    legal = set(legal_actions(position.state))
    return {
        "position_id": position.id,
        "category": position.category,
        "rules": position.state.game.rules,
        "board_size": position.state.game.board.n,
        "decoy": position.decoy,
        "state_key_sha256": state_hash(position.state),
        "status": result.status,
        "override_action": _action_id(result.override_action),
        "expected_action": (
            _action_id(position.acceptable_actions[0])
            if position.acceptable_actions else None
        ),
        "certificate_reproduced": statuses == expected,
        "correct": (
            result.override_action is None
            if position.decoy
            else result.override_action == position.acceptable_actions[0]
        ),
        "legal": result.override_action is None or result.override_action in legal,
        "state_unchanged": position.state.key() == before,
        "nodes": result.nodes,
        "cache_hits": result.cache_hits,
        "limit_reached": result.limit_reached,
        "elapsed_ms": round(elapsed_ms, 3),
    }


def build_result(*, created_date=None, source_commit_value=None):
    records = [
        evaluate_position(position)
        for position in (*positive_positions(), *decoy_positions())
    ]
    positives = [record for record in records if not record["decoy"]]
    decoys = [record for record in records if record["decoy"]]
    p95 = {
        str(n): _percentile(
            [
                record["elapsed_ms"]
                for record in records
                if record["board_size"] == n
            ],
            0.95,
        )
        for n in (3, 4)
    }
    integrity = all(
        record["certificate_reproduced"]
        and record["legal"]
        and record["state_unchanged"]
        for record in records
    )
    resolved = sum(record["correct"] for record in positives)
    false_overrides = sum(
        record["override_action"] is not None for record in decoys
    )
    feasibility = {
        "positive_certificates_reproduced": all(
            record["certificate_reproduced"] for record in positives
        ),
        "positive_resolution_rate": resolved / len(positives),
        "positive_resolution_at_least_90_percent": (
            resolved / len(positives) >= 0.9
        ),
        "decoy_false_overrides": false_overrides,
        "decoy_false_overrides_zero": false_overrides == 0,
        "toy_p95_ms": p95["3"],
        "toy_p95_below_100_ms": p95["3"] < 100,
        "beginner_p95_ms": p95["4"],
        "beginner_p95_below_400_ms": p95["4"] < 400,
        "integrity_clean": integrity,
    }
    payload = {
        "format": FORMAT,
        "version": VERSION,
        "created_date": created_date or date.today().isoformat(),
        "recipe_id": RECIPE_ID,
        "source": {
            "source_commit": source_commit_value or source_commit(),
            "code_hash": _code_hash(),
            "mcts_agent_hash": mcts_agent_hash("v4-solver"),
            "holdout_manifest": (
                "research/manifests/mcts-search-v4-holdout-20260717.json"
            ),
            "holdout_manifest_sha256": file_hash(
                REPO_ROOT
                / "research/manifests/mcts-search-v4-holdout-20260717.json"
            ),
            "files": {
                str(path.relative_to(REPO_ROOT)): file_hash(path)
                for path in _code_files()
            },
        },
        "config": {
            "node_limit": DEFAULT_NODE_LIMIT,
            "positions": len(records),
            "positive_positions": len(positives),
            "decoy_positions": len(decoys),
            "single_process": True,
        },
        "accounting": {
            "complete": len(records),
            "positive_resolved": resolved,
            "decoy_false_overrides": false_overrides,
            "limit_reached": sum(
                record["limit_reached"] for record in records
            ),
            "illegal": sum(not record["legal"] for record in records),
            "mutated": sum(
                not record["state_unchanged"] for record in records
            ),
            "certificate_mismatch": sum(
                not record["certificate_reproduced"] for record in records
            ),
        },
        "latency": {
            "p95_ms_by_board_size": p95,
            "mean_ms": statistics.fmean(
                record["elapsed_ms"] for record in records
            ),
            "observational_not_deterministic": True,
        },
        "feasibility_gate": feasibility,
        "qualified_for_common_development_screen": all((
            feasibility["positive_certificates_reproduced"],
            feasibility["positive_resolution_at_least_90_percent"],
            feasibility["decoy_false_overrides_zero"],
            feasibility["toy_p95_below_100_ms"],
            feasibility["beginner_p95_below_400_ms"],
            feasibility["integrity_clean"],
        )),
        "records": records,
        "claim_limits": {
            "local_obligation_feasibility_only": True,
            "strength_evidence": False,
            "balance_evidence": False,
            "strategic_depth_evidence": False,
            "ruleset_promise_evidence": False,
        },
    }
    deterministic_payload = json.loads(json.dumps(payload))
    for record in deterministic_payload["records"]:
        record.pop("elapsed_ms")
    deterministic_payload["latency"] = {
        "observational_not_deterministic": True
    }
    payload["deterministic_sha256"] = stable_hash(deterministic_payload)
    payload["payload_sha256"] = stable_hash(payload)
    return payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--created-date")
    args = parser.parse_args()
    payload = build_result(created_date=args.created_date)
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered)
    print(args.output)


if __name__ == "__main__":
    main()
