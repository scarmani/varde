#!/usr/bin/env python3
"""Run the predeclared paired release gates for curated Varde profiles."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
import hashlib
import math
import os
from pathlib import Path
import random
import statistics
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
HARNESS_ROOT = Path(__file__).resolve().parent
ENGINE_ROOT = REPO_ROOT / "engine"
for path in (HARNESS_ROOT, ENGINE_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from varde import BLACK, WHITE  # noqa: E402
from curate_v3 import PROFILE_RULES, load_hashed, normalized_distance  # noqa: E402
from map_elites_v3 import (  # noqa: E402
    DESCRIPTORS,
    balanced_genome,
    derive_seed,
    play_rollout,
    stable_hash,
    write_json_atomic,
)


FORMAT = "varde-profile-gate"
VERSION = 3
DEFAULT_TOY_PAIRS = 75
DEFAULT_BEGINNER_PAIRS = 25
BOOTSTRAP_SAMPLES = 10000


def source_commit():
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def code_hash():
    digest = hashlib.sha256()
    for path in (Path(__file__), HARNESS_ROOT / "map_elites_v3.py"):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def profile_gate_jobs(curation, seed, toy_pairs=DEFAULT_TOY_PAIRS, beginner_pairs=DEFAULT_BEGINNER_PAIRS):
    profiles = {"balanced": balanced_genome()}
    profiles.update(
        {
            profile_id: item["weights"]
            for profile_id, item in curation["selected"].items()
        }
    )
    jobs = []
    pair = 0
    for n, count in ((3, toy_pairs), (4, beginner_pairs)):
        for stratum_index in range(count):
            game_seed = derive_seed(seed, "profile-gate", n, stratum_index)
            for profile_id, weights in profiles.items():
                for color in (BLACK, WHITE):
                    jobs.append(
                        {
                            "profile": profile_id,
                            "weights": weights,
                            "n": n,
                            "pair": pair,
                            "stratum_index": stratum_index,
                            "color": color,
                            "seed": game_seed,
                        }
                    )
            pair += 1
    return jobs


def play_gate_game(job):
    result = play_rollout(
        job["weights"],
        balanced_genome(),
        job["color"],
        job["seed"],
        job["n"],
        job["pair"],
        "standard",
    )
    return {
        "profile": job["profile"],
        "board_size": job["n"],
        "pair": job["pair"],
        "stratum_index": job["stratum_index"],
        "initial_color": job["color"],
        "seed": job["seed"],
        **asdict(result),
    }


def game_descriptors(game):
    return {
        "engagement": game["engagement"] / max(1, game["early_placements"]),
        "verticality": game["verticality"] / max(1, game["all_placements"]),
        "edge_reach": game["edge_reach_sum"] / max(1, game["early_placements"]),
        "consolidation": game["consolidation"] / max(1, game["early_placements"]),
    }


def one_sided_bootstrap_lower(pair_scores, seed, samples=BOOTSTRAP_SAMPLES):
    if not pair_scores:
        return 0.0
    rng = random.Random(seed)
    count = len(pair_scores)
    estimates = sorted(
        sum(pair_scores[rng.randrange(count)] for _ in range(count)) / count
        for _ in range(samples)
    )
    return estimates[max(0, math.ceil(0.05 * samples) - 1)]


def pooled_effect_size(profile_values, balanced_values):
    if not profile_values or not balanced_values:
        return 0.0
    mean_difference = statistics.mean(profile_values) - statistics.mean(balanced_values)
    variance = (
        statistics.pvariance(profile_values) + statistics.pvariance(balanced_values)
    ) / 2
    if variance <= 1e-18:
        return math.inf if mean_difference > 0 else 0.0
    return mean_difference / math.sqrt(variance)


def summarize_profile(profile_id, games, balanced_games, primary, seed):
    selected = [game for game in games if game["profile"] == profile_id]
    pair_scores = []
    for pair in sorted({game["pair"] for game in selected}):
        legs = [game for game in selected if game["pair"] == pair]
        pair_scores.append(sum(game["result"] for game in legs) / len(legs))
    strata = {}
    for label, n in (("toy", 3), ("beginner", 4)):
        legs = [game for game in selected if game["board_size"] == n]
        strata[label] = {
            "games": len(legs),
            "score_rate": sum(game["result"] for game in legs) / max(1, len(legs)),
            "mean_margin": sum(game["margin"] for game in legs) / max(1, len(legs)),
            "incomplete": sum(not game["complete"] for game in legs),
        }
    descriptor_cells = {}
    for n_label, n in (("toy", 3), ("beginner", 4)):
        for color in (BLACK, WHITE):
            profile_values = [
                game_descriptors(game)[primary]
                for game in selected
                if game["board_size"] == n and game["initial_color"] == color
            ]
            reference_values = [
                game_descriptors(game)[primary]
                for game in balanced_games
                if game["board_size"] == n and game["initial_color"] == color
            ]
            shift = statistics.mean(profile_values) - statistics.mean(reference_values)
            descriptor_cells[f"{n_label}-{color}"] = {
                "profile_mean": statistics.mean(profile_values),
                "balanced_mean": statistics.mean(reference_values),
                "shift": shift,
                "positive": shift > 0,
            }
    profile_primary = [game_descriptors(game)[primary] for game in selected]
    balanced_primary = [game_descriptors(game)[primary] for game in balanced_games]
    effect = pooled_effect_size(profile_primary, balanced_primary)
    complete = all(game["complete"] for game in selected)
    overall_score = sum(game["result"] for game in selected) / max(1, len(selected))
    mean_margin = sum(game["margin"] for game in selected) / max(1, len(selected))
    lower = one_sided_bootstrap_lower(pair_scores, derive_seed(seed, "bootstrap", profile_id))
    gates = {
        "overall_score_at_least_45": overall_score >= 0.45,
        "toy_score_at_least_40": strata["toy"]["score_rate"] >= 0.40,
        "beginner_score_at_least_40": strata["beginner"]["score_rate"] >= 0.40,
        "bootstrap_lower_at_least_35": lower >= 0.35,
        "all_games_complete": complete,
        "primary_shift_all_color_strata": all(
            cell["positive"] for cell in descriptor_cells.values()
        ),
        "primary_effect_size_at_least_08": effect >= 0.8,
    }
    means = {
        name: statistics.mean(game_descriptors(game)[name] for game in selected)
        for name in DESCRIPTORS
    }
    return {
        "profile": profile_id,
        "primary_descriptor": primary,
        "games": len(selected),
        "overall_score": overall_score,
        "mean_margin": mean_margin,
        "one_sided_95_paired_bootstrap_lower": lower,
        "strata": strata,
        "descriptor_cells": descriptor_cells,
        "primary_effect_size": effect,
        "mean_descriptors": means,
        "gates": gates,
        "passed_individual_gates": all(gates.values()),
    }


def summarize_gates(curation, games, seed):
    balanced_games = [game for game in games if game["profile"] == "balanced"]
    profiles = {
        profile_id: summarize_profile(
            profile_id,
            games,
            balanced_games,
            PROFILE_RULES[profile_id][0],
            seed,
        )
        for profile_id in curation["selected"]
    }
    individually_eligible = {
        profile_id
        for profile_id, profile in profiles.items()
        if profile["passed_individual_gates"]
    }
    pairwise = {}
    ids = list(profiles)
    for left_index, left in enumerate(ids):
        for right in ids[left_index + 1 :]:
            distance = normalized_distance(
                profiles[left]["mean_descriptors"],
                profiles[right]["mean_descriptors"],
                curation["descriptor_scales"],
            )
            eligible_pair = left in individually_eligible and right in individually_eligible
            pairwise[f"{left}-{right}"] = {
                "distance": distance,
                "at_least_10": distance >= 1.0,
                "eligible_pair": eligible_pair,
            }
    pairwise_passed = all(
        item["at_least_10"]
        for item in pairwise.values()
        if item["eligible_pair"]
    )
    for profile_id, profile in profiles.items():
        conflicts = sorted(
            pair_id
            for pair_id, item in pairwise.items()
            if item["eligible_pair"]
            and not item["at_least_10"]
            and profile_id in pair_id.split("-")
        )
        profile["pairwise_conflicts"] = conflicts
        profile["passed"] = profile["passed_individual_gates"] and not conflicts
    available_profiles = [
        profile_id for profile_id in ids if profiles[profile_id]["passed"]
    ]
    return {
        "profiles": profiles,
        "pairwise_normalized_descriptor_distance": pairwise,
        "pairwise_gate_passed": pairwise_passed,
        "available_profiles": available_profiles,
        "all_profiles_passed": bool(profiles)
        and all(profile["passed"] for profile in profiles.values()),
    }


def run_gates(
    curation_path,
    output_path,
    *,
    seed=20260713,
    workers=1,
    toy_pairs=DEFAULT_TOY_PAIRS,
    beginner_pairs=DEFAULT_BEGINNER_PAIRS,
):
    curation = load_hashed(curation_path, "curation_hash")
    if not curation.get("selection_complete"):
        raise ValueError("profile curation is incomplete")
    jobs = profile_gate_jobs(curation, seed, toy_pairs, beginner_pairs)
    if workers == 1:
        games = [play_gate_game(job) for job in jobs]
    else:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            games = list(executor.map(play_gate_game, jobs))
    summary = summarize_gates(curation, games, seed)
    payload = {
        "format": FORMAT,
        "version": VERSION,
        "source_commit": source_commit(),
        "code_hash": code_hash(),
        "curation_hash": curation["curation_hash"],
        "configuration": {
            "seed": seed,
            "toy_pairs": toy_pairs,
            "beginner_pairs": beginner_pairs,
            "paired_colors": [BLACK, WHITE],
            "bootstrap_samples": BOOTSTRAP_SAMPLES,
            "workers_excluded_from_canonical_result": True,
        },
        "summary": summary,
        "games": games,
    }
    payload["gate_hash"] = stable_hash(payload)
    write_json_atomic(output_path, payload)
    return payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("curation", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20260713)
    parser.add_argument("--workers", type=int, default=max(1, os.cpu_count() or 1))
    parser.add_argument("--toy-pairs", type=int, default=DEFAULT_TOY_PAIRS)
    parser.add_argument("--beginner-pairs", type=int, default=DEFAULT_BEGINNER_PAIRS)
    args = parser.parse_args()
    result = run_gates(
        args.curation,
        args.output,
        seed=args.seed,
        workers=args.workers,
        toy_pairs=args.toy_pairs,
        beginner_pairs=args.beginner_pairs,
    )
    print(args.output)
    print(f"all_profiles_passed={result['summary']['all_profiles_passed']}")


if __name__ == "__main__":
    main()
