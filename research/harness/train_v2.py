#!/usr/bin/env python3
"""Train a fresh or resumed production V2 model with reproducible metadata."""

import argparse
from datetime import datetime, timezone
from pathlib import Path
import threading
import time

from common import append_jsonl, file_sha256, source_sha, write_json_atomic
from learning import LearningModel, MODEL_VERSION, RECIPE, play_training_game


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--games", type=int, default=200)
    parser.add_argument("--seed", type=int, default=20260712)
    parser.add_argument("--output-dir", type=Path, default=Path("/tmp/varde-v2"))
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.games <= 0:
        parser.error("--games must be positive")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    model_path = args.output_dir / "advanced-model-v2.json"
    log_path = args.output_dir / "training.jsonl"
    summary_path = args.output_dir / "training-summary.json"
    if model_path.exists() and not args.resume:
        parser.error(f"{model_path} exists; use --resume or another output directory")
    if not args.resume:
        log_path.write_text("")
    model = LearningModel.load(model_path) if args.resume else LearningModel(path=model_path)
    if model.load_error:
        parser.error(model.load_error)
    if model.needs_retraining:
        parser.error("reset legacy/mixed model before V2 evidence training")
    if model.games_attempted and model.training_seed != args.seed:
        parser.error("resume seed must match the persisted model seed")

    cancel = threading.Event()
    started = time.perf_counter()
    completed = 0
    discarded = 0
    starting_attempt = model.games_attempted
    try:
        for offset in range(args.games):
            index = starting_attempt + offset
            samples, label, complete = play_training_game(
                model, args.seed, index, cancel
            )
            model.record_attempt(args.seed, index)
            if complete:
                model.update(samples, label, args.seed)
                completed += 1
            else:
                discarded += 1
            model.save()
            entry = {
                "attempt": index,
                "complete": complete,
                "samples": len(samples),
                "label": label,
                "games_trained": model.games_trained,
                "elapsed_seconds": round(time.perf_counter() - started, 3),
            }
            append_jsonl(log_path, entry)
            print(
                f"training {offset + 1}/{args.games} attempt={index} "
                f"complete={complete} samples={len(samples)}",
                flush=True,
            )
    except KeyboardInterrupt:
        cancel.set()

    summary = {
        "source_sha": source_sha(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "configuration": {
            "games_requested": args.games,
            "seed": args.seed,
            "starting_attempt": starting_attempt,
            "model_version": MODEL_VERSION,
            "recipe": RECIPE,
        },
        "completed": completed,
        "discarded": discarded,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "model": model.status(),
        "model_sha256": file_sha256(model_path),
    }
    write_json_atomic(summary_path, summary)
    print(summary_path)


if __name__ == "__main__":
    main()
