#!/usr/bin/env python3
"""Run the predeclared Varde development/liberty evaluator ablations."""

from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
import hashlib
import os
from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
ENGINE_ROOT = REPO_ROOT / "engine"
HARNESS_ROOT = Path(__file__).resolve().parent
for path in (ENGINE_ROOT, HARNESS_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from varde import BLACK, WHITE  # noqa: E402
from map_elites_v3 import (  # noqa: E402
    balanced_genome,
    derive_seed,
    play_rollout,
    stable_hash,
    write_json_atomic,
)


FORMAT = "varde-evaluator-ablation"
VERSION = 3
RECIPE = "development-liberty-paired-v3"
VARIANTS = ("development_disabled", "liberty_disabled", "both_disabled")
DEFAULT_TOY_PAIRS = 40
DEFAULT_BEGINNER_PAIRS = 20


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


def variant_genome(variant):
    if variant not in VARIANTS:
        raise ValueError("unknown ablation variant")
    weights = balanced_genome()
    if variant in ("development_disabled", "both_disabled"):
        weights["development"] = 0.0
    if variant in ("liberty_disabled", "both_disabled"):
        weights["liberties"] = 0.0
    return weights


def ablation_jobs(seed, toy_pairs=DEFAULT_TOY_PAIRS, beginner_pairs=DEFAULT_BEGINNER_PAIRS):
    jobs = []
    for variant in VARIANTS:
        ordinal = 0
        for n, count in ((3, toy_pairs), (4, beginner_pairs)):
            for stratum_index in range(count):
                jobs.append(
                    {
                        "variant": variant,
                        "n": n,
                        "pair": ordinal,
                        "stratum_index": stratum_index,
                        "seed": derive_seed(
                            seed, "ablation", variant, n, stratum_index
                        ),
                    }
                )
                ordinal += 1
    return jobs


def play_ablation_pair(task):
    candidate = variant_genome(task["variant"])
    balanced = balanced_genome()
    games = [
        play_rollout(
            candidate,
            balanced,
            color,
            task["seed"],
            task["n"],
            task["pair"],
            task.get("difficulty", "standard"),
        )
        for color in (BLACK, WHITE)
    ]
    return {
        "variant": task["variant"],
        "board_size": task["n"],
        "pair": task["pair"],
        "stratum_index": task["stratum_index"],
        "seed": task["seed"],
        "complete": all(game.complete for game in games),
        "games": [asdict(game) for game in games],
    }


def summarize_pairs(pairs):
    summaries = {}
    for variant in VARIANTS:
        for stratum, n in (("toy", 3), ("beginner", 4), ("overall", None)):
            selected_pairs = [
                pair
                for pair in pairs
                if pair["variant"] == variant
                and (n is None or pair["board_size"] == n)
            ]
            games = [game for pair in selected_pairs for game in pair["games"]]
            placements = sum(game["all_placements"] for game in games)
            early = sum(game["early_placements"] for game in games)
            heat = Counter()
            for game in games:
                heat.update(
                    f"{point[0]},{point[1]}" for point in game["candidate_points"]
                )
            key = f"{variant}-{stratum}"
            summaries[key] = {
                "variant": variant,
                "stratum": stratum,
                "pairs": len(selected_pairs),
                "games": len(games),
                "score_rate": sum(game["result"] for game in games) / max(1, len(games)),
                "mean_margin": sum(game["margin"] for game in games) / max(1, len(games)),
                "engagement_rate": sum(game["engagement"] for game in games) / max(1, early),
                "contact_rate": sum(game["all_engagement"] for game in games) / max(1, placements),
                "consolidation_rate": sum(game["all_consolidation"] for game in games) / max(1, placements),
                "verticality_rate": sum(game["verticality"] for game in games) / max(1, placements),
                "hostile_cover_rate": sum(game["hostile_covers"] for game in games) / max(1, placements),
                "reinforcement_rate": sum(game["reinforcements"] for game in games) / max(1, placements),
                "edge_reach": sum(game["edge_reach_sum"] for game in games) / max(1, early),
                "captures_per_game": sum(game["candidate_captures"] for game in games) / max(1, len(games)),
                "mean_actions": sum(game["actions"] for game in games) / max(1, len(games)),
                "incomplete_games": sum(not game["complete"] for game in games),
                "heat_map": dict(sorted(heat.items())),
            }
    return summaries


def run_ablations(
    output_dir,
    *,
    seed=20260713,
    workers=1,
    toy_pairs=DEFAULT_TOY_PAIRS,
    beginner_pairs=DEFAULT_BEGINNER_PAIRS,
    difficulty="standard",
):
    if toy_pairs < 1 or beginner_pairs < 1:
        raise ValueError("each ablation stratum requires at least one pair")
    if difficulty not in ("casual", "standard"):
        raise ValueError("invalid ablation difficulty")
    jobs = ablation_jobs(seed, toy_pairs, beginner_pairs)
    for job in jobs:
        job["difficulty"] = difficulty
    if workers == 1:
        pairs = [play_ablation_pair(job) for job in jobs]
    else:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            pairs = list(executor.map(play_ablation_pair, jobs))
    incomplete = [pair for pair in pairs if not pair["complete"]]
    payload = {
        "format": FORMAT,
        "version": VERSION,
        "recipe": RECIPE,
        "source_commit": source_commit(),
        "code_hash": code_hash(),
        "configuration": {
            "seed": seed,
            "difficulty": difficulty,
            "toy_pairs": toy_pairs,
            "beginner_pairs": beginner_pairs,
            "paired_colors": [BLACK, WHITE],
            "workers_excluded_from_canonical_result": True,
        },
        "status": "complete" if not incomplete else "failed",
        "incomplete_pairs": len(incomplete),
        "summaries": summarize_pairs(pairs),
        "pairs": pairs,
    }
    payload["report_hash"] = stable_hash(payload)
    output_dir = Path(output_dir)
    write_json_atomic(output_dir / "ablation-v3.json", payload)
    if incomplete:
        raise RuntimeError(f"{len(incomplete)} ablation pairs incomplete")
    return payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("/tmp/varde-ablation-v3"))
    parser.add_argument("--seed", type=int, default=20260713)
    parser.add_argument("--workers", type=int, default=max(1, os.cpu_count() or 1))
    parser.add_argument("--toy-pairs", type=int, default=DEFAULT_TOY_PAIRS)
    parser.add_argument("--beginner-pairs", type=int, default=DEFAULT_BEGINNER_PAIRS)
    parser.add_argument("--difficulty", choices=("casual", "standard"), default="standard")
    args = parser.parse_args()
    result = run_ablations(
        args.output_dir,
        seed=args.seed,
        workers=args.workers,
        toy_pairs=args.toy_pairs,
        beginner_pairs=args.beginner_pairs,
        difficulty=args.difficulty,
    )
    print(args.output_dir / "ablation-v3.json")
    print(
        f"status={result['status']} pairs={len(result['pairs'])} "
        f"games={sum(len(pair['games']) for pair in result['pairs'])}"
    )


if __name__ == "__main__":
    main()
