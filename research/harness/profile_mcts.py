#!/usr/bin/env python3
"""Profile one MCTS decision without reporting its game-theoretic outcome."""

from __future__ import annotations

import argparse
import cProfile
import io
from pathlib import Path
import pstats
import subprocess
import sys
import time


REPO_ROOT = Path(__file__).resolve().parents[2]
ENGINE_ROOT = REPO_ROOT / "engine"
if str(ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(ENGINE_ROOT))

from actions import RulesState  # noqa: E402
from mcts import MCTS_AGENT_HASH, choose_mcts_state_action  # noqa: E402
from varde import BLACK, Game  # noqa: E402


def source_commit():
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, check=True,
        capture_output=True, text=True,
    ).stdout.strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rules", default="classic")
    parser.add_argument("--board-size", type=int, default=4)
    parser.add_argument("--simulations", type=int, default=250)
    parser.add_argument("--seed", type=int, default=20260715)
    parser.add_argument("--policy", default="uniform")
    parser.add_argument("--top", type=int, default=30)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    state = RulesState.from_game(Game(args.board_size, rules=args.rules))
    profiler = cProfile.Profile()
    started = time.perf_counter()
    profiler.enable()
    decision = choose_mcts_state_action(
        state,
        BLACK,
        simulations=args.simulations,
        seed=args.seed,
        rollout_policy=args.policy,
    )
    profiler.disable()
    elapsed = time.perf_counter() - started

    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream).strip_dirs()
    stats.sort_stats("cumulative").print_stats(args.top)
    header = (
        "Varde MCTS decision profile\n"
        f"source_commit: {source_commit()}\n"
        f"mcts_agent_hash: {MCTS_AGENT_HASH}\n"
        f"rules: {args.rules}\n"
        f"board_size: {args.board_size}\n"
        f"simulations: {args.simulations}\n"
        f"seed: {args.seed}\n"
        f"policy: {args.policy}\n"
        f"elapsed_seconds: {elapsed:.6f}\n"
        f"average_rollout_actions: {decision.average_rollout_actions:.3f}\n"
        f"max_rollout_actions: {decision.max_rollout_actions}\n"
        "decision_action: intentionally omitted (performance artifact only)\n\n"
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(header + stream.getvalue())
    print(args.output)


if __name__ == "__main__":
    main()
