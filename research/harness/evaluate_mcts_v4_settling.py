#!/usr/bin/env python3
"""Evaluate Candidate C terminal integrity before the common comparison."""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import random
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
ENGINE_ROOT = REPO_ROOT / "engine"
HARNESS_ROOT = Path(__file__).resolve().parent
for root in (ENGINE_ROOT, HARNESS_ROOT):
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

from mcts import _rollout_action, mcts_agent_hash  # noqa: E402
from mcts_settling import run_settling_rollout  # noqa: E402
from mcts_tactical_admission import file_hash, stable_hash  # noqa: E402
from mcts_tactical_fixtures import admission_positions  # noqa: E402


FORMAT = "varde-mcts-search-v4-settling-feasibility"
VERSION = 1
RECIPE_ID = "mcts-search-v4-settling-v1"


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
        ENGINE_ROOT / "mcts_settling.py",
        ENGINE_ROOT / "mcts.py",
        ENGINE_ROOT / "actions.py",
        ENGINE_ROOT / "varde.py",
    )


def _code_hash():
    digest = hashlib.sha256()
    for path in _code_files():
        digest.update(str(path.relative_to(REPO_ROOT)).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _fallback(policy, seed):
    rng = random.Random(seed)
    return lambda state, actions: _rollout_action(
        state,
        policy,
        rng,
        actions,
    )


def build_result(*, created_date=None, source_commit_value=None):
    records = []
    for position in admission_positions():
        for policy in ("uniform", "epsilon-greedy"):
            before = position.state.key()
            result = run_settling_rollout(
                position.state,
                _fallback(policy, 20260717),
            )
            points = len(position.state.game.board.points)
            records.append({
                "position_id": position.id,
                "rules": position.state.game.rules,
                "board_size": position.state.game.board.n,
                "policy": policy,
                "actions": result.actions,
                "four_p_limit": 4 * points,
                "within_four_p": result.actions <= 4 * points,
                "terminal": result.terminal_state.terminal,
                "terminal_reason": result.terminal_reason,
                "resumption_used": result.resumption_used,
                "phase_counts": dict(result.phase_counts),
                "state_unchanged": position.state.key() == before,
            })
    integrity = all(
        record["terminal"]
        and record["within_four_p"]
        and record["state_unchanged"]
        for record in records
    )
    gate = {
        "accepted_terminal_backups_100_percent": all(
            record["terminal"] for record in records
        ),
        "no_rollout_longer_than_4p": all(
            record["within_four_p"] for record in records
        ),
        "resumption_observed": any(
            record["resumption_used"] for record in records
        ),
        "integrity_clean": integrity,
        "mean_rollout_reduction_at_least_50_percent": None,
        "p95_latency_reduction_at_least_40_percent": None,
        "admission_within_5_points_of_control": None,
    }
    structural_pass = all(
        value
        for key, value in gate.items()
        if key not in (
            "mean_rollout_reduction_at_least_50_percent",
            "p95_latency_reduction_at_least_40_percent",
            "admission_within_5_points_of_control",
        )
    )
    payload = {
        "format": FORMAT,
        "version": VERSION,
        "created_date": created_date or date.today().isoformat(),
        "recipe_id": RECIPE_ID,
        "source": {
            "source_commit": source_commit_value or source_commit(),
            "code_hash": _code_hash(),
            "mcts_agent_hash": mcts_agent_hash("v4-settling"),
            "files": {
                str(path.relative_to(REPO_ROOT)): file_hash(path)
                for path in _code_files()
            },
        },
        "config": {
            "positions": len(admission_positions()),
            "policies": ["uniform", "epsilon-greedy"],
            "seed": 20260717,
            "terminal_values_only": True,
        },
        "accounting": {
            "rollouts": len(records),
            "terminal": sum(record["terminal"] for record in records),
            "over_4p": sum(
                not record["within_four_p"] for record in records
            ),
            "mutated": sum(
                not record["state_unchanged"] for record in records
            ),
        },
        "feasibility_gate": gate,
        "structural_feasibility_passed": structural_pass,
        "efficiency_gate_pending_common_screen": True,
        "qualified_for_common_development_screen": structural_pass,
        "records": records,
        "claim_limits": {
            "terminal_integrity_only": True,
            "efficiency_evidence": False,
            "candidate_admission_evidence": False,
            "strength_evidence": False,
        },
    }
    payload["payload_sha256"] = stable_hash(payload)
    return payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--created-date")
    args = parser.parse_args()
    payload = build_result(created_date=args.created_date)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n"
    )
    print(args.output)


if __name__ == "__main__":
    main()
