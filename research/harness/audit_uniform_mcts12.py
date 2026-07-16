#!/usr/bin/env python3
"""Validate and compact the frozen uniform-MCTS@12 diagnostic."""

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


FORMAT = "varde-uniform-mcts12-audit"
VERSION = 1
DEFAULT_MANIFEST = (
    REPO_ROOT / "research" / "manifests" / "uniform-mcts12-20260716.json"
)
DEFAULT_OUTPUT = (
    REPO_ROOT / "research" / "results" / "uniform-mcts12-20260716.json"
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


def _validate_frozen_contract(manifest, job):
    candidates = [item["id"] for item in manifest["candidates"]]
    config = job["config"]
    if config["rulesets"] != candidates:
        raise ValueError("job rulesets differ from frozen candidates")
    fixed = manifest["fixed_parameters"]
    if (
        config["board_sizes"] != fixed["board_sizes"]
        or config["pairs"] != fixed["pairs_per_ruleset_matchup"]
    ):
        raise ValueError("job board size or pair count differs from frozen contract")
    if not config["telemetry"] or config["include_mirrors"]:
        raise ValueError("job telemetry or matchup contract differs")
    if config["watchdog_multiplier"] != 20:
        raise ValueError("job watchdog differs from frozen contract")
    agents = config["agents"]
    if len(agents) != 2:
        raise ValueError("job must contain exactly two agent families")
    native, mcts = agents
    if (
        native["id"] != "native-standard"
        or native["family"] != "native"
        or native["difficulty"] != "standard"
    ):
        raise ValueError("job native agent differs from frozen contract")
    if (
        mcts["id"] != "mcts-uniform@12"
        or mcts["family"] != "mcts"
        or mcts["budget"] != 12
        or mcts["rollout_policy"] != "uniform"
    ):
        raise ValueError("job MCTS agent differs from frozen contract")


def _validate_job(manifest, job):
    _validate_frozen_contract(manifest, job)
    output = Path(job["output_dir"])
    paths = {
        name: output / name
        for name in ("state.json", "games.jsonl", "summary.json")
    }
    if not all(path.exists() for path in paths.values()):
        raise ValueError(f"job {job['id']} is missing a raw artifact")

    state = _load_state(paths["state.json"])
    summary = json.loads(paths["summary.json"].read_text())
    tasks = build_schedule(job["config"])
    if stable_hash(job["config"]) != job["config_sha256"]:
        raise ValueError("job config differs from manifest hash")
    if stable_hash(tasks) != job["schedule_sha256"]:
        raise ValueError("job schedule differs from manifest")
    if len(tasks) != job["games"]:
        raise ValueError("job game count differs from manifest")
    if state["status"] != "complete" or summary["status"] != "complete":
        raise ValueError("job did not finish")
    if state["config"] != job["config"]:
        raise ValueError("raw config differs from manifest")
    if summary["config_hash"] != stable_hash(job["config"]):
        raise ValueError("summary config hash differs")

    for name in (
        "code_hash",
        "ruleset_registry_hash",
        "native_evaluator_hash",
        "mcts_agent_hash",
    ):
        if state["provenance"].get(name) != manifest["source"][name]:
            raise ValueError(f"job provenance differs at {name}")

    records = state["records"]
    if len(records) != len(tasks):
        raise ValueError("job record count differs from schedule")
    for task, record in zip(tasks, records):
        if any(record.get(key) != task[key] for key in TASK_KEYS):
            raise ValueError(f"job record differs at task {task['task_id']}")

    accounting = summary["accounting"]
    if accounting["attempted"] != len(tasks) or accounting["pending"] != 0:
        raise ValueError("job accounting differs from schedule")
    return {
        "id": job["id"],
        "games": len(records),
        "run_source_commit": state["provenance"]["source_commit"],
        "accounting": accounting,
        "strata": summary["strata"],
        "rules_specific": summary["rules_specific"],
        "raw_artifact_sha256": {
            name: file_hash(path) for name, path in paths.items()
        },
    }


def audit_manifest(manifest):
    if manifest.get("format") != "varde-uniform-mcts12-manifest":
        raise ValueError("unknown uniform-MCTS@12 manifest format")
    if manifest.get("version") != 1:
        raise ValueError("uniform-MCTS@12 manifest must be version 1")
    jobs = manifest.get("jobs", [])
    if len(jobs) != 1:
        raise ValueError("uniform-MCTS@12 manifest must contain one job")
    evidence = _validate_job(manifest, jobs[0])
    accounting = {
        key: evidence["accounting"][key]
        for key in (
            "attempted",
            "complete",
            "illegal",
            "crash",
            "watchdog_incomplete",
            "pending",
        )
    }
    correctness = (
        accounting["attempted"] == manifest["fixed_parameters"]["games"]
        and accounting["complete"] == accounting["attempted"]
        and accounting["illegal"] == 0
        and accounting["crash"] == 0
        and accounting["watchdog_incomplete"] == 0
        and accounting["pending"] == 0
    )
    payload = {
        "format": FORMAT,
        "version": VERSION,
        "status": "complete",
        "claim_status": "shallow independent diagnostic evidence",
        "manifest_payload_hash": stable_hash(manifest),
        "source": manifest["source"],
        "constructed_fixture_contract": manifest["constructed_fixture_contract"],
        "accounting": accounting,
        "correctness_and_provenance_audit_clean": correctness,
        "job": evidence,
        "next_stage_gate": {
            "uniform_mcts12_required": True,
            "uniform_mcts12_clean": correctness,
            "uniform_mcts24_may_be_frozen": correctness,
            "light_rollout_may_be_frozen": correctness,
            "later_stages_launched_by_this_unit": False,
        },
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
    payload = audit_manifest(json.loads(args.manifest.read_text()))
    write_json_atomic(args.output, payload)
    print(args.output)


if __name__ == "__main__":
    main()
