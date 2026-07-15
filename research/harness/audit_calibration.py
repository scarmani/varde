#!/usr/bin/env python3
"""Deterministically audit completed calibration jobs without ranking games."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
HARNESS_ROOT = REPO_ROOT / "research" / "harness"
if str(HARNESS_ROOT) not in sys.path:
    sys.path.insert(0, str(HARNESS_ROOT))

from evaluate_rulesets import (  # noqa: E402
    _load_state,
    parse_agents,
    stable_hash,
    write_json_atomic,
)


FORMAT = "varde-calibration-audit"
VERSION = 1


def _sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _argv_value(argv, name, default=None):
    try:
        return argv[argv.index(name) + 1]
    except ValueError:
        return default


def expected_config(job):
    argv = job.get("argv")
    if not argv:
        raise ValueError(f"job {job.get('id')} does not have frozen argv")
    budgets = tuple(
        int(item) for item in _argv_value(argv, "--budgets").split(",")
    )
    agents = parse_agents(
        tuple(_argv_value(argv, "--agents").split(",")), budgets
    )
    return {
        "rulesets": _argv_value(argv, "--rulesets").split(","),
        "board_sizes": [
            int(item)
            for item in _argv_value(argv, "--board-sizes").split(",")
        ],
        "agents": [asdict(agent) for agent in agents],
        "pairs": int(_argv_value(argv, "--pairs")),
        "seed": int(_argv_value(argv, "--seed")),
        "telemetry": "--telemetry" in argv,
        "include_mirrors": "--include-mirrors" in argv,
        "watchdog_multiplier": int(
            _argv_value(argv, "--watchdog-multiplier", "20")
        ),
    }


def _expected_provenance(manifest):
    source = manifest["source"]
    return {
        "code_hash": source["code_hash"],
        "ruleset_registry_hash": source["ruleset_registry_hash"],
        "native_evaluator_hash": source["native_evaluator_hash"],
        "mcts_agent_hash": source["mcts_agent_hash"],
    }


def _stratum(summary, rules):
    matches = [
        value
        for key, value in summary["strata"].items()
        if key.startswith(f"{rules}|")
    ]
    if len(matches) != 1:
        raise ValueError(f"expected one completed stratum for {rules}")
    return matches[0]


def audit_stage_a(manifest):
    candidates = [item["id"] for item in manifest["candidates"]]
    jobs = [
        item for item in manifest["jobs"]
        if item["id"] in ("A-uniform-250", "A-light-250")
    ]
    if len(jobs) != 2:
        raise ValueError("manifest must contain both frozen stage A jobs")

    expected_provenance = _expected_provenance(manifest)
    job_evidence = []
    candidate_evidence = {rules: {"jobs": {}} for rules in candidates}
    source_commits = set()

    for job in jobs:
        output = Path(job["output_dir"])
        state_path = output / "state.json"
        games_path = output / "games.jsonl"
        summary_path = output / "summary.json"
        if not all(path.exists() for path in (state_path, games_path, summary_path)):
            raise ValueError(f"job {job['id']} is missing an artifact")

        state = _load_state(state_path)
        summary = json.loads(summary_path.read_text())
        config = expected_config(job)
        if state["status"] != "complete" or summary["status"] != "complete":
            raise ValueError(f"job {job['id']} is not complete")
        if state["config"] != config:
            raise ValueError(f"job {job['id']} config differs from manifest")
        if summary["config_hash"] != stable_hash(config):
            raise ValueError(f"job {job['id']} summary config hash differs")
        for name, expected in expected_provenance.items():
            if state["provenance"].get(name) != expected:
                raise ValueError(f"job {job['id']} provenance differs at {name}")
        source_commits.add(state["provenance"]["source_commit"])

        records = state["records"]
        expected_records = 2 * config["pairs"] * len(config["rulesets"])
        if len(records) != expected_records:
            raise ValueError(f"job {job['id']} record count differs from schedule")
        failures = [item for item in records if item["status"] != "complete"]
        job_evidence.append({
            "id": job["id"],
            "config_hash": stable_hash(config),
            "records": len(records),
            "complete": len(records) - len(failures),
            "failures": len(failures),
            "artifact_sha256": {
                "state.json": _sha256_file(state_path),
                "games.jsonl": _sha256_file(games_path),
                "summary.json": _sha256_file(summary_path),
            },
        })

        for rules in candidates:
            rules_records = [item for item in records if item["rules"] == rules]
            rules_failures = [
                item for item in rules_records if item["status"] != "complete"
            ]
            stratum = _stratum(summary, rules)
            candidate_evidence[rules]["jobs"][job["id"]] = {
                "games": len(rules_records),
                "complete": len(rules_records) - len(rules_failures),
                "failures": [
                    {"task_id": item["task_id"], "status": item["status"],
                     "error": item["error"]}
                    for item in rules_failures
                ],
                "diagnostic_health_gates": stratum["health_gates"],
                "headline_eligible": stratum["headline_eligible"],
            }

    if len(source_commits) != 1:
        raise ValueError("stage A jobs used different source commits")
    stage_b_rulesets = []
    for rules, evidence in candidate_evidence.items():
        operational_pass = all(
            not item["failures"] and item["complete"] == item["games"]
            for item in evidence["jobs"].values()
        )
        evidence["operational_pass"] = operational_pass
        evidence["advancement_reason"] = (
            "zero correctness/termination failures in both rollout jobs"
            if operational_pass else
            "rejected by the predeclared correctness/termination gate"
        )
        if operational_pass:
            stage_b_rulesets.append(rules)

    return {
        "format": FORMAT,
        "version": VERSION,
        "stage": "A-250",
        "status": "complete",
        "source_commit": next(iter(source_commits)),
        "manifest_hash": stable_hash(manifest),
        "audit_script_sha256": _sha256_file(__file__),
        "jobs": job_evidence,
        "candidates": candidate_evidence,
        "stage_b_rulesets": stage_b_rulesets,
        "promotion_blocked": True,
        "claim_status": "non-claim calibration operational audit",
        "interpretation": (
            "Stage A can reject correctness or termination failures. Its "
            "20 paired seeds cannot establish balance, depth, emergence, "
            "elegance, beauty, or flagship status."
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest", type=Path,
        default=REPO_ROOT / "research/manifests/ruleset-calibration-20260715.json",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    payload = audit_stage_a(manifest)
    write_json_atomic(args.output, payload)
    print(args.output)


if __name__ == "__main__":
    main()
