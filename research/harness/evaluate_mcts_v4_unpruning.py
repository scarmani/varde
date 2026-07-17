#!/usr/bin/env python3
"""Evaluate Candidate B structural feasibility before common admission."""

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

from actions import RulesState  # noqa: E402
from mcts import choose_mcts_state_action, mcts_agent_hash  # noqa: E402
from mcts_tactical_admission import file_hash, stable_hash  # noqa: E402
from mcts_tactical_fixtures import admission_positions  # noqa: E402
from mcts_unpruning import (  # noqa: E402
    next_exposure_visit,
    ordered_rule_transitions,
    progressive_exposure_count,
)
from varde import BLACK, Game  # noqa: E402


FORMAT = "varde-mcts-search-v4-unpruning-feasibility"
VERSION = 1


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
        ENGINE_ROOT / "mcts_unpruning.py",
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


def build_result(*, created_date=None, source_commit_value=None):
    schedule = {
        str(visits): progressive_exposure_count(visits, 100)
        for visits in (4, 16, 64, 256, 1024)
    }
    opening = RulesState.from_game(Game(3, rules="breath"))
    before = opening.key()
    started = time.perf_counter()
    decision = choose_mcts_state_action(
        opening,
        BLACK,
        simulations=64,
        seed=20260717,
        rollout_policy="uniform",
        search_variant="v4-unpruning",
        include_root_telemetry=True,
    )
    elapsed_ms = (time.perf_counter() - started) * 1000
    exposed = [item for item in decision.root_actions if item["exposed"]]
    hidden = [item for item in decision.root_actions if not item["exposed"]]
    forced = next(
        item for item in admission_positions()
        if item.id == "admission-gjerde-go-forced-acceptance"
    )
    admin = choose_mcts_state_action(
        forced.state,
        forced.state.actor_color,
        simulations=1,
        seed=5,
        search_variant="v4-unpruning",
        include_root_telemetry=True,
    )
    direction_winners = {
        ordered_rule_transitions(opening, seed)[0].action.point
        for seed in range(128)
    }
    gates = {
        "exact_schedule": schedule == {
            "4": 4, "16": 8, "64": 16, "256": 32, "1024": 64
        },
        "eventual_full_expansion": (
            progressive_exposure_count(10_000, 73) == 73
            and next_exposure_visit(10_000, 73) is None
        ),
        "forced_administrative_action_visible": (
            admin.action.kind == "accept"
            and admin.exposed_actions == 1
            and admin.hidden_actions == 0
        ),
        "natural_root_exposes_16_at_64": (
            decision.exposed_actions == 16 and len(exposed) == 16
        ),
        "median_visits_per_exposed_child": statistics.median(
            item["visits"] for item in exposed
        ),
        "median_visits_at_least_3": statistics.median(
            item["visits"] for item in exposed
        ) >= 3,
        "hidden_actions_unvisited": all(
            item["visits"] == 0 for item in hidden
        ),
        "directional_winners_across_128_seeds": len(direction_winners),
        "no_fixed_directional_preference": len(direction_winners) >= 20,
        "state_unchanged": opening.key() == before,
        "action_legal": decision.action in {
            item.action for item in ordered_rule_transitions(opening, 20260717)
        },
        "high_rung_admission_delta_at_least_10_points": None,
    }
    structural_pass = all(
        value
        for key, value in gates.items()
        if key not in (
            "median_visits_per_exposed_child",
            "directional_winners_across_128_seeds",
            "high_rung_admission_delta_at_least_10_points",
        )
    )
    payload = {
        "format": FORMAT,
        "version": VERSION,
        "created_date": created_date or date.today().isoformat(),
        "source": {
            "source_commit": source_commit_value or source_commit(),
            "code_hash": _code_hash(),
            "ordered_control_agent_hash": mcts_agent_hash(
                "v4-ordered-control"
            ),
            "unpruning_agent_hash": mcts_agent_hash("v4-unpruning"),
            "files": {
                str(path.relative_to(REPO_ROOT)): file_hash(path)
                for path in _code_files()
            },
        },
        "recipe_ids": {
            "ordered_control": "mcts-search-v4-ordered-control-v1",
            "progressive_unpruning": "mcts-search-v4-unpruning-v1",
        },
        "schedule": schedule,
        "natural_root": {
            "rules": "breath",
            "board_size": 3,
            "visits": 64,
            "legal_actions": len(decision.root_actions),
            "exposed_actions": decision.exposed_actions,
            "hidden_actions": decision.hidden_actions,
            "exposed_visits": [item["visits"] for item in exposed],
            "elapsed_ms": round(elapsed_ms, 3),
        },
        "feasibility_gate": gates,
        "structural_feasibility_passed": structural_pass,
        "qualified_for_common_development_screen": structural_pass,
        "admission_pending": True,
        "claim_limits": {
            "structural_feasibility_only": True,
            "candidate_admission_evidence": False,
            "strength_evidence": False,
            "strategic_depth_evidence": False,
        },
    }
    deterministic = json.loads(json.dumps(payload))
    deterministic["natural_root"].pop("elapsed_ms")
    payload["deterministic_sha256"] = stable_hash(deterministic)
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
