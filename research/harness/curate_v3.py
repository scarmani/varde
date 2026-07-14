#!/usr/bin/env python3
"""Select evidence-eligible Varde personalities from a MAP-Elites archive."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import statistics
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
HARNESS_ROOT = Path(__file__).resolve().parent
if str(HARNESS_ROOT) not in sys.path:
    sys.path.insert(0, str(HARNESS_ROOT))

from map_elites_v3 import DESCRIPTORS, stable_hash, write_json_atomic  # noqa: E402


FORMAT = "varde-profile-curation"
VERSION = 3
PROFILE_RULES = {
    "raider": ("engagement", 0.15),
    "mason": ("verticality", 0.10),
    "surveyor": ("edge_reach", 0.15),
    "weaver": ("consolidation", 0.15),
}
MIN_NORMALIZED_DISTANCE = 1.0


def load_hashed(path, hash_field):
    payload = json.loads(Path(path).read_text())
    expected = payload.get(hash_field)
    if not isinstance(expected, str):
        raise ValueError(f"missing {hash_field}")
    canonical = {key: value for key, value in payload.items() if key != hash_field}
    if stable_hash(canonical) != expected:
        raise ValueError(f"{hash_field} mismatch")
    return payload


def descriptor_scales(attempts):
    eligible = [item for item in attempts if not item["rejected"]]
    if len(eligible) < 2:
        raise ValueError("archive needs at least two eligible attempts")
    return {
        name: max(
            1e-9,
            statistics.pstdev(item["descriptors"][name] for item in eligible),
        )
        for name in DESCRIPTORS
    }


def normalized_distance(left, right, scales):
    return math.sqrt(
        sum(
            ((left[name] - right[name]) / scales[name]) ** 2
            for name in DESCRIPTORS
        )
    )


def select_profiles(state, audit):
    if state.get("status") != "complete":
        raise ValueError("optimizer state is not complete")
    if audit.get("status") != "complete":
        raise ValueError("audit report is not complete")
    reference = state.get("balanced_reference")
    if not isinstance(reference, dict) or set(reference.get("descriptors", ())) != set(DESCRIPTORS):
        raise ValueError("optimizer state lacks a Balanced descriptor reference")
    baseline = reference["descriptors"]
    scales = descriptor_scales(state["attempts"])
    elites = sorted(
        state["archive"].values(),
        key=lambda item: (-item["quality"], item["candidate_id"]),
    )
    audit_decisions = audit["analysis"]["candidate_decisions"]
    rejected_features = {
        name
        for name, decision in audit_decisions.items()
        if not decision["accepted_for_optimization"]
    }
    selected = {}
    used_ids = set()
    for profile_id, (primary, minimum_shift) in PROFILE_RULES.items():
        for elite in elites:
            if elite["candidate_id"] in used_ids:
                continue
            if elite["descriptors"][primary] < baseline[primary] + minimum_shift:
                continue
            if any(
                normalized_distance(
                    elite["descriptors"], prior["descriptors"], scales
                )
                < MIN_NORMALIZED_DISTANCE
                for prior in selected.values()
            ):
                continue
            if any(abs(elite["genome"][name]) > 1e-12 for name in rejected_features):
                raise ValueError("elite assigns weight to an audit-rejected feature")
            selected[profile_id] = {
                "candidate_id": elite["candidate_id"],
                "quality": elite["quality"],
                "descriptors": dict(elite["descriptors"]),
                "primary_descriptor": primary,
                "required_shift": minimum_shift,
                "measured_shift": elite["descriptors"][primary] - baseline[primary],
                "minimum_distance_to_prior": min(
                    (
                        normalized_distance(
                            elite["descriptors"], prior["descriptors"], scales
                        )
                        for prior in selected.values()
                    ),
                    default=None,
                ),
                "weights": dict(elite["genome"]),
                "model_hash": elite["genome_hash"],
            }
            used_ids.add(elite["candidate_id"])
            break
    missing = [profile_id for profile_id in PROFILE_RULES if profile_id not in selected]
    return {
        "balanced_descriptors": dict(baseline),
        "descriptor_scales": scales,
        "selected": selected,
        "missing": missing,
        "needs_one_refinement": bool(missing),
        "selection_complete": not missing,
    }


def run_curation(optimizer_path, audit_path, output_path):
    state = load_hashed(optimizer_path, "state_hash")
    audit = load_hashed(audit_path, "report_hash")
    selection = select_profiles(state, audit)
    payload = {
        "format": FORMAT,
        "version": VERSION,
        "optimizer_state_hash": state["state_hash"],
        "optimizer_source_commit": state["source_commit"],
        "audit_report_hash": audit["report_hash"],
        "audit_source_commit": audit["source_commit"],
        "rules": {
            profile_id: {
                "primary_descriptor": primary,
                "minimum_shift": shift,
            }
            for profile_id, (primary, shift) in PROFILE_RULES.items()
        },
        "minimum_normalized_distance": MIN_NORMALIZED_DISTANCE,
        **selection,
    }
    payload["curation_hash"] = stable_hash(payload)
    write_json_atomic(output_path, payload)
    return payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("optimizer", type=Path)
    parser.add_argument("audit", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run_curation(args.optimizer, args.audit, args.output)
    print(args.output)
    print(
        "selected="
        + (",".join(result["selected"]) or "none")
        + " missing="
        + (",".join(result["missing"]) or "none")
    )


if __name__ == "__main__":
    main()
