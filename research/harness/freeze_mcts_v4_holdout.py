#!/usr/bin/env python3
"""Freeze the independent MCTS Search V4 holdout before candidate code."""

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

from mcts_tactical_admission import file_hash, stable_hash  # noqa: E402
from mcts_tactical_fixtures import tactical_positions  # noqa: E402
from mcts_v4_holdout import (  # noqa: E402
    CERTIFICATE_FORMAT,
    CERTIFICATE_VERSION,
    HOLDOUT_FORMAT,
    HOLDOUT_VERSION,
    decoy_positions,
    holdout_catalog,
    positive_positions,
    state_hash,
)


FORMAT = "varde-mcts-search-v4-holdout-manifest"
VERSION = 1
DEFAULT_OUTPUT = Path.home() / "varde-runs" / "mcts-search-v4-20260717"


def source_commit():
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def repository_is_clean():
    result = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return not result.stdout.strip()


def _code_files():
    return (
        Path(__file__),
        HARNESS_ROOT / "mcts_v4_holdout.py",
        HARNESS_ROOT / "mcts_tactical_fixtures.py",
        HARNESS_ROOT / "mcts_telemetry.py",
        ENGINE_ROOT / "actions.py",
        ENGINE_ROOT / "varde.py",
    )


def _code_hash():
    digest = hashlib.sha256()
    for path in _code_files():
        digest.update(str(path.relative_to(REPO_ROOT)).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def build_manifest(
    *,
    output_dir,
    created_date=None,
    source_commit_value=None,
):
    positives = positive_positions()
    decoys = decoy_positions()
    catalog = holdout_catalog((*positives, *decoys))
    historical_hashes = {
        state_hash(position.state) for position in tactical_positions()
    }
    holdout_hashes = {
        state_hash(position.state) for position in (*positives, *decoys)
    }
    manifest = {
        "format": FORMAT,
        "version": VERSION,
        "status": "frozen-before-candidate-implementation",
        "created_date": created_date or date.today().isoformat(),
        "source": {
            "source_commit": source_commit_value or source_commit(),
            "code_hash": _code_hash(),
            "files": {
                str(path.relative_to(REPO_ROOT)): file_hash(path)
                for path in _code_files()
            },
            "stacked_base": "315443366ddeb499d294f47221e89c2c1dbca4d7",
        },
        "holdout_format": HOLDOUT_FORMAT,
        "holdout_version": HOLDOUT_VERSION,
        "catalog": catalog,
        "catalog_sha256": stable_hash(catalog),
        "positive_positions": len(positives),
        "decoy_positions": len(decoys),
        "reachable_positive_positions": sum(
            item.provenance["kind"] == "reachable-seeded-play"
            for item in positives
        ),
        "certificate": {
            "format": CERTIFICATE_FORMAT,
            "version": CERTIFICATE_VERSION,
            "scope": "bounded local obligation",
            "node_limit": 100_000,
            "claim_limit": "not a game-theoretic result",
        },
        "independence": {
            "v3_positions": len(tactical_positions()),
            "v3_unique_state_hashes": len(historical_hashes),
            "v4_positions": len(holdout_hashes),
            "v3_state_hashes_disjoint": holdout_hashes.isdisjoint(
                historical_hashes
            ),
            "v3_common_screen_manifest": (
                "research/manifests/mcts-tactical-margin-v4-20260717.json"
            ),
            "v3_common_screen_sha256": file_hash(
                REPO_ROOT
                / "research/manifests/mcts-tactical-margin-v4-20260717.json"
            ),
        },
        "execution": {
            "output_dir": str(Path(output_dir).expanduser().resolve()),
            "workers": 1,
            "raw_output_repository_external": True,
        },
        "freeze_gate": {
            "candidate_code_present": False,
            "candidate_outcomes_inspected": False,
            "holdout_outcomes_used_to_tune_candidates": False,
            "positive_certificates_reproduced": True,
            "decoys_require_abstention": True,
            "root_width_between_2_and_12": True,
            "at_least_half_positives_reachable": True,
        },
        "claim_limits": {
            "local_tactical_evidence_only": True,
            "strength_evidence": False,
            "balance_evidence": False,
            "strategic_depth_evidence": False,
            "ruleset_promise_evidence": False,
        },
    }
    manifest["payload_sha256"] = stable_hash(manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--created-date")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if not repository_is_clean():
        parser.error("tracked repository changes must be committed before freeze")
    existing = None
    if args.check:
        if not args.manifest.exists():
            raise SystemExit("holdout manifest is absent")
        existing = json.loads(args.manifest.read_text())
    payload = build_manifest(
        output_dir=args.output_dir,
        created_date=(
            existing["created_date"] if existing else args.created_date
        ),
        source_commit_value=(
            existing["source"]["source_commit"] if existing else None
        ),
    )
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.check:
        if args.manifest.read_text() != rendered:
            raise SystemExit("MCTS V4 holdout manifest differs")
    else:
        if args.manifest.exists():
            parser.error("manifest already exists; use --check")
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(rendered)
    print(args.manifest)


if __name__ == "__main__":
    main()
