#!/usr/bin/env python3
"""Freeze an MCTS tactical-admission V2 manifest before any decisions run."""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
ENGINE_ROOT = REPO_ROOT / "engine"
HARNESS_ROOT = Path(__file__).resolve().parent
for root in (ENGINE_ROOT, HARNESS_ROOT):
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

from mcts_tactical_admission import (  # noqa: E402
    DEFAULT_BUDGETS,
    DEFAULT_POLICIES,
    DEFAULT_REPLICATES,
    DEFAULT_SEED,
    build_schedule,
    provenance,
    stable_hash,
)
from mcts_tactical_fixtures import (  # noqa: E402
    PROOF_FORMAT,
    PROOF_VERSION,
    admission_positions,
    diagnostic_positions,
    fixture_catalog,
    tactical_positions,
)
from mcts import MCTS_VERSION  # noqa: E402


FORMAT = "varde-mcts-tactical-admission-manifest"
VERSION = 2


def repository_is_clean():
    result = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return not result.stdout.strip()


def build_manifest(
    config,
    *,
    output_dir,
    workers,
    checkpoint_interval,
    created_date=None,
    purpose=None,
):
    positions = tactical_positions()
    admissions = admission_positions()
    diagnostics = diagnostic_positions()
    tasks = build_schedule(config)
    run_provenance = provenance()
    run_provenance["manifest_builder_sha256"] = hashlib.sha256(
        Path(__file__).read_bytes()
    ).hexdigest()
    created_date = created_date or date.today().isoformat()
    return {
        "format": FORMAT,
        "version": VERSION,
        "status": "frozen-before-outcomes",
        "created_date": created_date,
        "purpose": purpose or (
            f"MCTS V{MCTS_VERSION} split proof-grade admission versus "
            "natural-width diagnostic baseline"
        ),
        "source": run_provenance,
        "config": config,
        "config_sha256": stable_hash(config),
        "schedule_sha256": stable_hash(tasks),
        "decisions": len(tasks),
        "positions": len(positions),
        "fixture_contract": {
            "fixture_catalog_sha256": stable_hash(fixture_catalog()),
            "diagnostic_positions": len(diagnostics),
            "admission_positions": len(admissions),
            "maximum_admission_root_actions": max(
                len(position.proof["action_values"])
                for position in admissions
            ),
            "proof_format": PROOF_FORMAT,
            "proof_version": PROOF_VERSION,
            "proof_scope": "exhaustive legal root transitions",
            "proof_claim_limit": "local tactical choice, not forced outcome",
            "outcomes_used": False,
        },
        "admission_gate": {
            "all_decisions_legal_nonmutating_and_complete": True,
            "every_high_budget_position_policy_at_least_75_percent": True,
            "high_budget_overall_at_least_80_percent": True,
            "aggregate_hit_rate_nondecreasing_by_policy": True,
        },
        "execution": {
            "workers": workers,
            "checkpoint_interval": checkpoint_interval,
            "output_dir": str(Path(output_dir).expanduser().resolve()),
            "argv": [
                "python3",
                "research/harness/mcts_tactical_admission.py",
                "--budgets", ",".join(map(str, config["budgets"])),
                "--policies", ",".join(config["policies"]),
                "--replicates", str(config["replicates"]),
                "--seed", str(config["seed"]),
                "--workers", str(workers),
                "--checkpoint-interval", str(checkpoint_interval),
                "--output-dir", str(Path(output_dir).expanduser().resolve()),
            ],
            "audit_argv": [
                "python3",
                "research/harness/audit_mcts_tactical_admission.py",
                "--manifest", "MANIFEST_PATH",
                "--output", "AUDIT_OUTPUT_PATH",
            ],
        },
        "freeze_gate": {
            "fixture_and_harness_tests_passed": True,
            "outcomes_inspected_before_freeze": False,
            "paired_matches_blocked_until_search_variant_selection": True,
            "paired_matches_launched_by_this_unit": False,
        },
        "claim_limits": {
            "local_tactical_admission_evidence_only": True,
            "natural_width_positions_are_diagnostic_only": True,
            "forced_game_outcome_evidence": False,
            "match_strength_evidence": False,
            "balance_evidence": False,
            "strategic_depth_evidence": False,
            "ruleset_promise_evidence": False,
            "latency_observational_not_deterministic": True,
            "promotion_blocked": True,
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--budgets", default=",".join(map(str, DEFAULT_BUDGETS)))
    parser.add_argument("--policies", default=",".join(DEFAULT_POLICIES))
    parser.add_argument("--replicates", type=int, default=DEFAULT_REPLICATES)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--checkpoint-interval", type=int, default=8)
    parser.add_argument("--created-date")
    parser.add_argument("--purpose")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    config = {
        "budgets": [int(value) for value in args.budgets.split(",")],
        "policies": [value for value in args.policies.split(",") if value],
        "replicates": args.replicates,
        "seed": args.seed,
    }
    if not repository_is_clean():
        parser.error("tracked repository changes must be committed before freeze")
    payload = build_manifest(
        config,
        output_dir=args.output_dir,
        workers=args.workers,
        checkpoint_interval=args.checkpoint_interval,
        created_date=args.created_date,
        purpose=args.purpose,
    )
    rendered = json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.check:
        if not args.manifest.exists() or args.manifest.read_text() != rendered:
            raise SystemExit("tactical-admission manifest differs")
    else:
        if args.manifest.exists():
            parser.error("manifest already exists; use --check")
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(rendered)
    print(args.manifest)


if __name__ == "__main__":
    main()
