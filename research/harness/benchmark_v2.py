#!/usr/bin/env python3
"""Benchmark fresh-position Standard and Advanced V2 decisions."""

import argparse
from pathlib import Path
import statistics
import time

from common import write_json_atomic
from cairn import BLACK, Game
from learning import LearningModel
from opponent import choose_decision


def percentile_95(values):
    ordered = sorted(values)
    return ordered[max(0, int(0.95 * len(ordered)) - 1)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("model", type=Path)
    parser.add_argument("--samples", type=int, default=20)
    parser.add_argument("--output", type=Path, default=Path("/tmp/cairn-v2/benchmark.json"))
    args = parser.parse_args()
    model = LearningModel.load(args.model)
    if model.load_error:
        parser.error(model.load_error)
    results = {}
    for n in (3, 6):
        for difficulty in ("standard", "advanced"):
            timings = []
            for seed in range(args.samples):
                game = Game(n)
                started = time.perf_counter()
                choose_decision(
                    game,
                    BLACK,
                    difficulty,
                    seed=seed,
                    model=model if difficulty == "advanced" else None,
                )
                timings.append((time.perf_counter() - started) * 1000)
            results[f"n{n}_{difficulty}"] = {
                "samples": len(timings),
                "median_ms": statistics.median(timings),
                "p95_ms": percentile_95(timings),
                "max_ms": max(timings),
            }
            print(f"n={n} {difficulty} p95={percentile_95(timings):.2f}ms")
    results["acceptance"] = {
        "toy_under_500ms": results["n3_standard"]["p95_ms"] < 500
        and results["n3_advanced"]["p95_ms"] < 500,
        "full_under_1500ms": results["n6_standard"]["p95_ms"] < 1500
        and results["n6_advanced"]["p95_ms"] < 1500,
    }
    write_json_atomic(args.output, results)


if __name__ == "__main__":
    main()
