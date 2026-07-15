#!/usr/bin/env python3
"""Validate and compact a frozen native-only Varde screening run."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
ENGINE_ROOT = REPO_ROOT / "engine"
HARNESS_ROOT = REPO_ROOT / "research" / "harness"
if str(ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(ENGINE_ROOT))
if str(HARNESS_ROOT) not in sys.path:
    sys.path.insert(0, str(HARNESS_ROOT))

from evaluate_rulesets import (  # noqa: E402
    _load_state,
    build_schedule,
    stable_hash,
    write_json_atomic,
)


FORMAT = "varde-native-screening-audit"
VERSION = 1
DEFAULT_MANIFEST = (
    REPO_ROOT / "research" / "manifests" / "native-screening-v2-20260715.json"
)
DEFAULT_OUTPUT = (
    REPO_ROOT / "research" / "results" / "native-screening-v2-20260715.json"
)
TASK_KEYS = (
    "task_id",
    "rules",
    "rules_revision",
    "board_size",
    "matchup",
    "pair_index",
    "leg",
    "seed",
    "agent_a",
    "agent_b",
    "initial_a_color",
)


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _validate_job(manifest, job):
    output = Path(job["output_dir"])
    state_path = output / "state.json"
    games_path = output / "games.jsonl"
    summary_path = output / "summary.json"
    if not all(path.exists() for path in (state_path, games_path, summary_path)):
        raise ValueError(f"job {job['id']} is missing a raw artifact")

    state = _load_state(state_path)
    summary = json.loads(summary_path.read_text())
    tasks = build_schedule(job["config"])
    if stable_hash(tasks) != job["schedule_sha256"]:
        raise ValueError(f"job {job['id']} schedule differs from manifest")
    if len(tasks) != job["games"]:
        raise ValueError(f"job {job['id']} game count differs from manifest")
    if state["status"] != "complete" or summary["status"] != "complete":
        raise ValueError(f"job {job['id']} did not finish")
    if state["config"] != job["config"]:
        raise ValueError(f"job {job['id']} config differs from manifest")
    if summary["config_hash"] != stable_hash(job["config"]):
        raise ValueError(f"job {job['id']} summary config hash differs")

    expected_provenance = {
        name: manifest["source"][name]
        for name in (
            "code_hash",
            "ruleset_registry_hash",
            "native_evaluator_hash",
            "mcts_agent_hash",
        )
    }
    for name, expected in expected_provenance.items():
        if state["provenance"].get(name) != expected:
            raise ValueError(f"job {job['id']} provenance differs at {name}")

    records = state["records"]
    if len(records) != len(tasks):
        raise ValueError(f"job {job['id']} record count differs from schedule")
    for task, record in zip(tasks, records):
        if any(record.get(key) != task[key] for key in TASK_KEYS):
            raise ValueError(f"job {job['id']} record differs at task {task['task_id']}")

    accounting = summary["accounting"]
    if accounting["attempted"] != len(tasks) or accounting["pending"] != 0:
        raise ValueError(f"job {job['id']} accounting differs from schedule")
    return {
        "id": job["id"],
        "games": len(records),
        "run_source_commit": state["provenance"]["source_commit"],
        "accounting": accounting,
        "strata": summary["strata"],
        "rules_specific": summary["rules_specific"],
        "raw_artifact_sha256": {
            "state.json": file_hash(state_path),
            "games.jsonl": file_hash(games_path),
            "summary.json": file_hash(summary_path),
        },
    }


def audit_manifest(manifest):
    if manifest.get("format") != "varde-native-screening-manifest":
        raise ValueError("unknown native screening manifest format")
    if manifest.get("version") != 2:
        raise ValueError("native screening manifest must be version 2")
    jobs = manifest.get("jobs", [])
    if len(jobs) != 2:
        raise ValueError("native screening manifest must contain two jobs")
    evidence = [_validate_job(manifest, job) for job in jobs]
    accounting = {
        key: sum(item["accounting"][key] for item in evidence)
        for key in (
            "attempted",
            "complete",
            "illegal",
            "crash",
            "watchdog_incomplete",
            "pending",
        )
    }
    payload = {
        "format": FORMAT,
        "version": VERSION,
        "status": "complete",
        "claim_status": "diagnostic native-only falsification evidence",
        "manifest_payload_hash": stable_hash(manifest),
        "source": manifest["source"],
        "accounting": accounting,
        "correctness_gate_passed": (
            accounting["attempted"] == manifest["fixed_parameters"]["games"]
            and accounting["complete"] == accounting["attempted"]
            and accounting["illegal"] == 0
            and accounting["crash"] == 0
            and accounting["watchdog_incomplete"] == 0
            and accounting["pending"] == 0
        ),
        "jobs": evidence,
        "claim_limits": manifest["claim_limits"],
        "promotion_blocked": True,
    }
    payload["payload_hash"] = stable_hash(payload)
    return payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    payload = audit_manifest(manifest)
    write_json_atomic(args.output, payload)
    print(args.output)


if __name__ == "__main__":
    main()
