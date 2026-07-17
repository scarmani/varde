#!/usr/bin/env python3
"""Audit and compact a frozen MCTS tactical-admission run."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
ENGINE_ROOT = REPO_ROOT / "engine"
HARNESS_ROOT = Path(__file__).resolve().parent
for root in (ENGINE_ROOT, HARNESS_ROOT):
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

from mcts_tactical_admission import (  # noqa: E402
    TASK_KEYS,
    build_schedule,
    deterministic_records_hash,
    load_state,
    provenance,
    stable_hash,
    summarize,
    write_json_atomic,
)
from mcts_tactical_fixtures import (  # noqa: E402
    diagnostic_positions,
    fixture_catalog,
    tactical_positions,
)


FORMAT = "varde-mcts-tactical-admission-audit"
VERSION = 2


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _validate_manifest(manifest):
    if manifest.get("format") != "varde-mcts-tactical-admission-manifest":
        raise ValueError("unknown tactical-admission manifest format")
    version = manifest.get("version")
    if version not in (1, 2):
        raise ValueError("unsupported tactical-admission manifest version")
    if manifest.get("status") != "frozen-before-outcomes":
        raise ValueError("tactical-admission manifest was not frozen")
    config = manifest.get("config")
    positions = diagnostic_positions() if version == 1 else tactical_positions()
    tasks = build_schedule(
        config,
        positions=positions,
        schema_version=version,
    )
    if stable_hash(config) != manifest.get("config_sha256"):
        raise ValueError("manifest config hash differs")
    if stable_hash(tasks) != manifest.get("schedule_sha256"):
        raise ValueError("manifest schedule hash differs")
    if len(tasks) != manifest.get("decisions"):
        raise ValueError("manifest decision count differs")
    catalog = fixture_catalog(schema_version=version, positions=positions)
    if stable_hash(catalog) != manifest["source"].get("fixture_catalog_hash"):
        raise ValueError("manifest fixture catalog differs")
    return tasks


def _validate_runtime_source(manifest):
    current = provenance()
    for key in ("code_hash", "mcts_agent_hash", "fixture_catalog_hash", "files"):
        if current[key] != manifest["source"].get(key):
            raise ValueError(f"runtime source differs at {key}")
    return current


def _validate_raw(manifest, tasks):
    output = Path(manifest["execution"]["output_dir"])
    paths = {
        name: output / name
        for name in ("state.json", "decisions.jsonl", "summary.json")
    }
    if not all(path.exists() for path in paths.values()):
        raise ValueError("tactical-admission raw artifact is missing")
    state = load_state(paths["state.json"])
    raw_summary = json.loads(paths["summary.json"].read_text())
    if state["status"] != "complete" or raw_summary["status"] != "complete":
        raise ValueError("tactical-admission run did not finish")
    if state["config"] != manifest["config"]:
        raise ValueError("raw config differs from manifest")
    for key in ("code_hash", "mcts_agent_hash", "fixture_catalog_hash", "files"):
        if state["provenance"].get(key) != manifest["source"].get(key):
            raise ValueError(f"raw provenance differs at {key}")
    records = state["records"]
    if len(records) != len(tasks):
        raise ValueError("raw record count differs from schedule")
    for task, record in zip(tasks, records):
        if any(record.get(key) != task[key] for key in TASK_KEYS):
            raise ValueError(f"raw record differs at task {task['task_id']}")
        if record.get("root_legal_actions") != task["root_legal_actions"]:
            raise ValueError(f"raw root width differs at task {task['task_id']}")
        if record.get("acceptable_actions") != task["acceptable_actions"]:
            raise ValueError(f"raw acceptable actions differ at task {task['task_id']}")
        for key in ("evidence_class", "proof_sha256"):
            if key in task and record.get(key) != task[key]:
                raise ValueError(
                    f"raw {key} differs at task {task['task_id']}"
                )
    recomputed = summarize(
        records, state["config"], state["provenance"], state["status"]
    )
    if raw_summary != recomputed:
        raise ValueError("raw summary does not recompute exactly")
    if raw_summary["deterministic_records_hash"] != deterministic_records_hash(records):
        raise ValueError("deterministic decision hash differs")
    return paths, state, raw_summary


def audit_manifest(manifest):
    tasks = _validate_manifest(manifest)
    runtime = _validate_runtime_source(manifest)
    paths, state, summary = _validate_raw(manifest, tasks)
    failures = [
        record["task_id"] for record in state["records"]
        if record["status"] != "complete" or not record["state_unchanged"]
    ]
    declared_gate = manifest["admission_gate"]
    if declared_gate != {
        "all_decisions_legal_nonmutating_and_complete": True,
        "every_high_budget_position_policy_at_least_75_percent": True,
        "high_budget_overall_at_least_80_percent": True,
        "aggregate_hit_rate_nondecreasing_by_policy": True,
    }:
        raise ValueError("manifest admission gate differs from frozen recipe")
    audited_clean = not failures and summary["accounting"]["pending"] == 0
    admitted = audited_clean and summary["admitted"]
    payload = {
        "format": FORMAT,
        "version": manifest["version"],
        "status": "complete",
        "claim_status": "outcome-blind tactical admission evidence",
        "manifest_payload_hash": stable_hash(manifest),
        "source": manifest["source"],
        "run_source_commit": state["provenance"]["source_commit"],
        "runtime_source_commit_at_audit": runtime["source_commit"],
        "config": manifest["config"],
        "fixture_catalog": fixture_catalog(
            schema_version=manifest["version"],
            positions=(
                diagnostic_positions()
                if manifest["version"] == 1
                else tactical_positions()
            ),
        ),
        "accounting": summary["accounting"],
        "correctness_and_provenance_audit_clean": audited_clean,
        "failure_task_ids": failures,
        "ladder": summary["ladder"],
        "position_ladder": summary["position_ladder"],
        "high_budget_overall_hit_rate": summary[
            "high_budget_overall_hit_rate"
        ],
        "admission_gate": summary["admission_gate"],
        "admitted": admitted,
        "next_stage_gate": {
            "paired_mcts24_may_be_frozen": admitted,
            "paired_light_rollout_may_be_frozen": admitted,
            "paired_match_stage_launched_by_this_unit": False,
            "required_action_if_not_admitted": (
                None if admitted else "diagnose failed fixture-policy-budget cells"
            ),
        },
        "reproducibility": {
            "config_sha256": manifest["config_sha256"],
            "schedule_sha256": manifest["schedule_sha256"],
            "deterministic_records_sha256": summary[
                "deterministic_records_hash"
            ],
            "raw_artifact_sha256": {
                name: file_hash(path) for name, path in paths.items()
            },
            "latency_is_observational_and_excluded_from_decision_hash": True,
        },
        "claim_limits": copy.deepcopy(manifest["claim_limits"]),
        "promotion_blocked": True,
    }
    payload["payload_hash"] = stable_hash(payload)
    return payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = audit_manifest(json.loads(args.manifest.read_text()))
    write_json_atomic(args.output, payload)
    print(args.output)


if __name__ == "__main__":
    main()
