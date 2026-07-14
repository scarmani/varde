#!/usr/bin/env python3
"""Run non-claim Intermediate and Full generalization smoke matches."""

import argparse
from dataclasses import asdict
from pathlib import Path

from common import play_heldout_game, source_sha, write_json_atomic
from varde import BLACK, other
from learning import LearningModel


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("model", type=Path)
    parser.add_argument("--pairs", type=int, default=2)
    parser.add_argument("--seed", type=int, default=8102026)
    parser.add_argument("--output", type=Path, default=Path("/tmp/varde-v2/smoke.json"))
    args = parser.parse_args()
    model = LearningModel.load(args.model)
    if model.load_error:
        parser.error(model.load_error)
    results = []
    for n in (5, 6):
        for pair_index in range(args.pairs):
            seed = args.seed + n * 100000 + pair_index
            for color in (BLACK, other(BLACK)):
                result = play_heldout_game(model, color, seed, n)
                results.append(asdict(result))
                print(
                    f"smoke n={n} pair={pair_index + 1}/{args.pairs} "
                    f"color={color} complete={result.complete}",
                    flush=True,
                )
    summary = {
        "source_sha": source_sha(),
        "configuration": {"pairs_per_board": args.pairs, "seed": args.seed},
        "claim_scope": "none; Intermediate and Full are untrained generalization smokes",
        "complete": all(item["complete"] for item in results),
        "results": results,
    }
    write_json_atomic(args.output, summary)


if __name__ == "__main__":
    main()
