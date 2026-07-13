#!/usr/bin/env python3
"""Run the predeclared paired Advanced V2 strength gate."""

import argparse
from datetime import datetime, timezone
from pathlib import Path

from common import (
    file_sha256,
    paired_evaluation,
    source_sha,
    write_json_atomic,
)
from learning import LearningModel, MODEL_VERSION, RECIPE


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("model", type=Path)
    parser.add_argument("--toy-pairs", type=int, default=75)
    parser.add_argument("--beginner-pairs", type=int, default=25)
    parser.add_argument("--seed", type=int, default=9102026)
    parser.add_argument("--output-dir", type=Path, default=Path("/tmp/cairn-v2"))
    args = parser.parse_args()
    if args.toy_pairs < 0 or args.beginner_pairs < 0:
        parser.error("pair counts cannot be negative")
    if args.toy_pairs + args.beginner_pairs == 0:
        parser.error("at least one pair is required")
    model = LearningModel.load(args.model)
    if model.load_error:
        parser.error(model.load_error)
    if model.needs_retraining or model.recipe != RECIPE:
        parser.error("evaluation requires a clean margin-v2 model")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    log_path = args.output_dir / "heldout.jsonl"
    result_path = args.output_dir / "heldout-summary.json"
    log_path.write_text("")

    def progress(done, total, pair):
        print(
            f"heldout {done}/{total} n={pair['board_size']} "
            f"score={pair['score']:.2f} complete={pair['complete']}",
            flush=True,
        )

    result = paired_evaluation(
        model,
        args.toy_pairs,
        args.beginner_pairs,
        args.seed,
        log_path,
        progress,
    )
    result.update({
        "source_sha": source_sha(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model_version": MODEL_VERSION,
        "recipe": RECIPE,
        "model_sha256": file_sha256(args.model),
    })
    write_json_atomic(result_path, result)
    print(result_path)
    print(f"gate_passed={result['passed']}")


if __name__ == "__main__":
    main()
