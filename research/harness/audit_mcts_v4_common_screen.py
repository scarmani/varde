#!/usr/bin/env python3
"""Compare the five frozen Search V4 development-screen recipes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
ENGINE_ROOT = REPO_ROOT / "engine"
HARNESS_ROOT = Path(__file__).resolve().parent
for root in (ENGINE_ROOT, HARNESS_ROOT):
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

from mcts_tactical_admission import load_state, stable_hash  # noqa: E402
from mcts_tactical_fixtures import tactical_positions  # noqa: E402


FORMAT = "varde-mcts-search-v4-common-screen-audit"
VERSION = 1
VARIANTS = (
    "v4-control",
    "v4-solver",
    "v4-ordered-control",
    "v4-unpruning",
    "v4-settling",
)


def _percentile(values, fraction):
    ordered = sorted(values)
    rank = max(1, int(len(ordered) * fraction + 0.999999))
    return ordered[min(len(ordered), rank) - 1]


def _load_variant(manifest_path, audit_path):
    manifest = json.loads(Path(manifest_path).read_text())
    audit = json.loads(Path(audit_path).read_text())
    variant = manifest["config"]["search_variant"]
    if variant not in VARIANTS:
        raise ValueError("unexpected Search V4 common-screen variant")
    if audit["config"] != manifest["config"]:
        raise ValueError("audit and manifest configuration differ")
    if audit["manifest_payload_hash"] != stable_hash(manifest):
        raise ValueError("audit and manifest payload hashes differ")
    state = load_state(Path(manifest["execution"]["output_dir"]) / "state.json")
    if state["status"] != "complete":
        raise ValueError("common-screen raw run is incomplete")
    return variant, manifest, audit, state["records"]


def _overall_metrics(records):
    complete = [record for record in records if record["status"] == "complete"]
    latency = [record["timing"]["elapsed_ms"] for record in complete]
    rollout = [
        record["decision"]["average_rollout_actions"] for record in complete
    ]
    return {
        "decisions": len(complete),
        "mean_rollout_actions": statistics.fmean(rollout),
        "max_rollout_actions": max(
            record["decision"]["max_rollout_actions"] for record in complete
        ),
        "latency_ms_p95": _percentile(latency, 0.95),
        "terminal_backups": sum(
            record["decision"]["settling"]["terminal_backups"]
            for record in complete
        ),
        "expected_terminal_backups": sum(
            record["budget"] for record in complete
        ),
    }


def audit_common(inputs):
    loaded = {}
    for manifest_path, audit_path in inputs:
        variant, manifest, audit, records = _load_variant(
            manifest_path,
            audit_path,
        )
        if variant in loaded:
            raise ValueError("duplicate common-screen variant")
        loaded[variant] = {
            "manifest": manifest,
            "audit": audit,
            "records": records,
            "metrics": _overall_metrics(records),
        }
    if set(loaded) != set(VARIANTS):
        raise ValueError("common-screen variant set is incomplete")

    control = loaded["v4-control"]
    ordered = loaded["v4-ordered-control"]
    unpruning = loaded["v4-unpruning"]
    settling = loaded["v4-settling"]
    solver = loaded["v4-solver"]
    unpruning_delta = (
        unpruning["audit"]["high_budget_overall_hit_rate"]
        - ordered["audit"]["high_budget_overall_hit_rate"]
    )
    solver_qualified = solver["audit"]["admitted"]
    unpruning_qualified = (
        unpruning["audit"]["admitted"] and unpruning_delta >= 0.10
    )
    tactical = []
    if solver_qualified:
        tactical.append("v4-solver")
    if unpruning_qualified:
        tactical.append("v4-unpruning")
    tactical.sort(key=lambda variant: (
        -loaded[variant]["audit"]["high_budget_overall_hit_rate"],
        loaded[variant]["metrics"]["latency_ms_p95"],
        variant,
    ))
    selected_tactical = tactical[0] if tactical else None

    control_metrics = control["metrics"]
    settling_metrics = settling["metrics"]
    mean_reduction = 1 - (
        settling_metrics["mean_rollout_actions"]
        / control_metrics["mean_rollout_actions"]
    )
    p95_reduction = 1 - (
        settling_metrics["latency_ms_p95"]
        / control_metrics["latency_ms_p95"]
    )
    admission_delta = (
        settling["audit"]["high_budget_overall_hit_rate"]
        - control["audit"]["high_budget_overall_hit_rate"]
    )
    positions = {position.id: position for position in tactical_positions()}
    within_four_p = all(
        record["decision"]["max_rollout_actions"]
        <= 4 * len(positions[record["position_id"]].state.game.board.points)
        for record in settling["records"]
        if record["status"] == "complete"
    )
    terminal_only = (
        settling_metrics["terminal_backups"]
        == settling_metrics["expected_terminal_backups"]
    )
    settling_gate = {
        "accepted_terminal_backups_100_percent": terminal_only,
        "mean_rollout_reduction": mean_reduction,
        "mean_rollout_reduction_at_least_50_percent": mean_reduction >= 0.50,
        "p95_latency_reduction": p95_reduction,
        "p95_latency_reduction_at_least_40_percent": p95_reduction >= 0.40,
        "no_rollout_longer_than_4p": within_four_p,
        "admission_delta_from_control": admission_delta,
        "admission_no_more_than_5_points_below_control": admission_delta >= -0.05,
        "integrity_clean": settling["audit"][
            "correctness_and_provenance_audit_clean"
        ],
    }
    settling_qualified = all(
        value for key, value in settling_gate.items()
        if key not in (
            "mean_rollout_reduction",
            "p95_latency_reduction",
            "admission_delta_from_control",
        )
    )
    if selected_tactical and settling_qualified:
        selected_recipe = f"{selected_tactical}+v4-settling"
        selection_kind = "conditional-composition"
    elif selected_tactical:
        selected_recipe = selected_tactical
        selection_kind = "tactical-standalone"
    elif settling_qualified:
        selected_recipe = "v4-settling"
        selection_kind = "efficiency-standalone"
    else:
        selected_recipe = None
        selection_kind = "none-qualified"

    variants = {}
    for variant in VARIANTS:
        item = loaded[variant]
        variants[variant] = {
            "admitted": item["audit"]["admitted"],
            "high_budget_overall_hit_rate": item["audit"][
                "high_budget_overall_hit_rate"
            ],
            "admission_gate": item["audit"]["admission_gate"],
            "metrics": item["metrics"],
            "manifest_payload_hash": item["audit"]["manifest_payload_hash"],
            "deterministic_records_sha256": item["audit"][
                "reproducibility"
            ]["deterministic_records_sha256"],
        }
    payload = {
        "format": FORMAT,
        "version": VERSION,
        "status": "complete",
        "variants": variants,
        "candidate_a": {
            "qualified": solver_qualified,
        },
        "candidate_b": {
            "unpruning_high_rung_delta_over_ordered_control": unpruning_delta,
            "delta_at_least_10_points": unpruning_delta >= 0.10,
            "qualified": unpruning_qualified,
        },
        "candidate_c": {
            "gate": settling_gate,
            "qualified": settling_qualified,
        },
        "selection": {
            "tactical_candidates": tactical,
            "selected_tactical": selected_tactical,
            "selected_recipe": selected_recipe,
            "selection_kind": selection_kind,
            "sealed_holdout_may_run": selected_recipe is not None,
            "composition_requires_implementation": bool(
                selected_tactical and settling_qualified
            ),
        },
        "claim_limits": {
            "development_screen_only": True,
            "holdout_evidence": False,
            "strength_evidence": False,
            "balance_evidence": False,
            "strategic_depth_evidence": False,
        },
    }
    payload["payload_sha256"] = stable_hash(payload)
    return payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        action="append",
        nargs=2,
        metavar=("MANIFEST", "AUDIT"),
        required=True,
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = audit_common(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n"
    )
    print(args.output)


if __name__ == "__main__":
    main()
