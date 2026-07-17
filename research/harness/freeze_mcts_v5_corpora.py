#!/usr/bin/env python3
"""Freeze MCTS Search V5 development and holdout corpora before candidates."""

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

from mcts_tactical_fixtures import tactical_positions  # noqa: E402
from mcts_v4_holdout import holdout_positions as v4_holdout_positions  # noqa: E402
from mcts_v5_corpus import (  # noqa: E402
    corpus_catalog,
    development_positions,
    holdout_positions,
)
from mcts_v5_oracle import state_hash  # noqa: E402


FORMAT = "varde-mcts-search-v5-corpus-manifest"
VERSION = 1
STACKED_BASE = "808c31720730fcf23bbc02c4549bd7151bdab3ec"
DEFAULT_OUTPUT = Path.home() / "varde-runs" / "mcts-search-v5-20260717"


def stable_hash(payload):
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
    ).hexdigest()


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


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
        HARNESS_ROOT / "mcts_v5_corpus.py",
        HARNESS_ROOT / "mcts_v5_oracle.py",
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
    split,
    *,
    output_dir,
    created_date=None,
    source_commit_value=None,
):
    if split not in ("development", "holdout"):
        raise ValueError("split must be development or holdout")
    positions = (
        development_positions() if split == "development"
        else holdout_positions()
    )
    catalog = corpus_catalog(split)
    historical = {
        state_hash(position.state) for position in tactical_positions()
    } | {
        state_hash(position.state) for position in v4_holdout_positions()
    }
    own_hashes = {state_hash(position.state) for position in positions}
    other_positions = (
        holdout_positions() if split == "development"
        else development_positions()
    )
    other_hashes = {
        state_hash(position.state) for position in other_positions
    }
    manifest = {
        "format": FORMAT,
        "version": VERSION,
        "status": "frozen-before-v5-candidate-implementation",
        "split": split,
        "created_date": created_date or date.today().isoformat(),
        "source": {
            "source_commit": source_commit_value or source_commit(),
            "stacked_base": STACKED_BASE,
            "code_hash": _code_hash(),
            "files": {
                str(path.relative_to(REPO_ROOT)): file_hash(path)
                for path in _code_files()
            },
        },
        "catalog": catalog,
        "catalog_sha256": stable_hash(catalog),
        "configuration": {
            "positions": 24,
            "families": 6,
            "toy": 12,
            "beginner": 12,
            "narrow_roots_2_to_12": 12,
            "wide_roots_at_least_32": 12,
            "decoys": 6,
            "oracle_node_limit": 10_000,
        },
        "independence": {
            "historical_v3_v4_state_count": len(historical),
            "historical_state_hashes_disjoint": own_hashes.isdisjoint(historical),
            "other_v5_split_state_hashes_disjoint": own_hashes.isdisjoint(
                other_hashes
            ),
            "other_split": (
                "holdout" if split == "development" else "development"
            ),
        },
        "hand_audit": {
            "positive_trace_per_family": True,
            "decoy_trace_per_family": True,
            "actor_seat_and_color_each_ply": True,
        },
        "freeze_gate": {
            "candidate_code_present": False,
            "candidate_outcomes_inspected": False,
            "holdout_used_for_recipe_selection": False,
            "oracle_certificates_complete": True,
            "oracle_limit_reached": False,
        },
        "execution": {
            "output_dir": str(Path(output_dir).expanduser().resolve()),
            "raw_output_repository_external": True,
            "resume_required": True,
            "worker_count_invariant_required": True,
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
    parser.add_argument("--split", choices=("development", "holdout"), required=True)
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
            raise SystemExit("V5 corpus manifest is absent")
        existing = json.loads(args.manifest.read_text())
    payload = build_manifest(
        args.split,
        output_dir=args.output_dir,
        created_date=(existing["created_date"] if existing else args.created_date),
        source_commit_value=(
            existing["source"]["source_commit"] if existing else None
        ),
    )
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.check:
        if args.manifest.read_text() != rendered:
            raise SystemExit("MCTS V5 corpus manifest differs")
    else:
        if args.manifest.exists():
            parser.error("manifest already exists; use --check")
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(rendered)
    print(args.manifest)


if __name__ == "__main__":
    main()
