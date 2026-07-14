#!/usr/bin/env python3
"""Run profile-vs-profile and larger-board Varde V3 smoke matches."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
from itertools import combinations
import hashlib
import os
from pathlib import Path
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
from curate_v3 import load_hashed  # noqa: E402
from map_elites_v3 import (  # noqa: E402
    balanced_genome,
    derive_seed,
    play_rollout,
    stable_hash,
    write_json_atomic,
)


FORMAT = "varde-profile-smoke"
VERSION = 3


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


def smoke_jobs(curation, seed, matchup_pairs=20, larger_pairs=4):
    profiles = {"balanced": balanced_genome()}
    profiles.update(
        {
            profile_id: item["weights"]
            for profile_id, item in curation["selected"].items()
        }
    )
    jobs = []
    for left, right in combinations(profiles, 2):
        for pair in range(matchup_pairs):
            n = 3 if pair < math_ceil_ratio(matchup_pairs, 0.75) else 4
            pair_seed = derive_seed(seed, "matchup", left, right, pair)
            for color in (BLACK, WHITE):
                jobs.append(
                    {
                        "kind": "matchup",
                        "label": f"{left}-vs-{right}",
                        "profile": left,
                        "opponent": right,
                        "weights": profiles[left],
                        "opponent_weights": profiles[right],
                        "n": n,
                        "pair": pair,
                        "color": color,
                        "seed": pair_seed,
                    }
                )
    for profile in curation["selected"]:
        for n in (5, 6):
            for pair in range(larger_pairs):
                pair_seed = derive_seed(seed, "larger", profile, n, pair)
                for color in (BLACK, WHITE):
                    jobs.append(
                        {
                            "kind": "larger",
                            "label": f"{profile}-n{n}",
                            "profile": profile,
                            "opponent": "balanced",
                            "weights": profiles[profile],
                            "opponent_weights": profiles["balanced"],
                            "n": n,
                            "pair": pair,
                            "color": color,
                            "seed": pair_seed,
                        }
                    )
    return jobs


def math_ceil_ratio(total, fraction):
    value = total * fraction
    return int(value) if value == int(value) else int(value) + 1


def play_smoke_game(job):
    game = play_rollout(
        job["weights"],
        job["opponent_weights"],
        job["color"],
        job["seed"],
        job["n"],
        job["pair"],
        "standard",
    )
    return {
        "kind": job["kind"],
        "label": job["label"],
        "profile": job["profile"],
        "opponent": job["opponent"],
        **asdict(game),
    }


def summarize(games):
    summaries = {}
    for label in sorted({game["label"] for game in games}):
        selected = [game for game in games if game["label"] == label]
        summaries[label] = {
            "kind": selected[0]["kind"],
            "games": len(selected),
            "complete": all(game["complete"] for game in selected),
            "score_rate": statistics.mean(game["result"] for game in selected),
            "mean_margin": statistics.mean(game["margin"] for game in selected),
            "mean_actions": statistics.mean(game["actions"] for game in selected),
            "max_actions": max(game["actions"] for game in selected),
            "captures_per_game": statistics.mean(
                game["candidate_captures"] for game in selected
            ),
        }
    return summaries


def run_smokes(
    curation_path,
    output_path,
    *,
    seed=20260713,
    workers=1,
    matchup_pairs=20,
    larger_pairs=4,
):
    curation = load_hashed(curation_path, "curation_hash")
    if not curation.get("selection_complete"):
        raise ValueError("profile curation is incomplete")
    jobs = smoke_jobs(curation, seed, matchup_pairs, larger_pairs)
    if workers == 1:
        games = [play_smoke_game(job) for job in jobs]
    else:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            games = list(executor.map(play_smoke_game, jobs))
    payload = {
        "format": FORMAT,
        "version": VERSION,
        "source_commit": source_commit(),
        "code_hash": code_hash(),
        "curation_hash": curation["curation_hash"],
        "configuration": {
            "seed": seed,
            "matchup_pairs": matchup_pairs,
            "matchup_mix": "75% Toy / 25% Beginner",
            "larger_pairs_per_board": larger_pairs,
            "workers_excluded_from_canonical_result": True,
        },
        "summaries": summarize(games),
        "games": games,
    }
    payload["smoke_hash"] = stable_hash(payload)
    write_json_atomic(output_path, payload)
    if not all(game["complete"] for game in games):
        raise RuntimeError("profile smoke contained an incomplete game")
    return payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("curation", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20260713)
    parser.add_argument("--workers", type=int, default=max(1, os.cpu_count() or 1))
    parser.add_argument("--matchup-pairs", type=int, default=20)
    parser.add_argument("--larger-pairs", type=int, default=4)
    args = parser.parse_args()
    result = run_smokes(
        args.curation,
        args.output,
        seed=args.seed,
        workers=args.workers,
        matchup_pairs=args.matchup_pairs,
        larger_pairs=args.larger_pairs,
    )
    print(args.output)
    print(f"games={len(result['games'])} complete=true")


if __name__ == "__main__":
    main()
