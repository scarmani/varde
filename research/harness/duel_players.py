#!/usr/bin/env python3
"""Attack-focused and defense-focused greedy players for balance probes.

The attacker chooses, each turn, the legal move that maximizes stones
captured and minimizes the opponent's total horizontal liberties. The
defender maximizes its own liberties and minimizes its own imperiled
stones, capturing only when that serves safety. Both are one-ply and
rules-agnostic: legality, captures, and (in breath-extend) the free
extension all flow through the engine, so the same objectives apply
under every ruleset.

Usage: python3 duel_players.py [--output PATH]
"""

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "engine"))

from varde import BLACK, WHITE, Game, groups_of, other


def _tiebreak(point, seed):
    digest = hashlib.sha256(f"{seed}:{point}".encode()).hexdigest()
    return int(digest[:8], 16)


def _liberty_summary(game, state, color):
    """Total horizontal liberties and one-liberty stone count for color."""
    board = game.board
    total = 0
    imperiled = 0
    for comp in groups_of(board, state, color):
        libs = {
            nb
            for q in comp
            for nb in board.neighbors[q]
            if not state[nb]
        }
        total += len(libs)
        if len(libs) == 1:
            imperiled += len(comp)
    return total, imperiled


def attacker_move(game, seed):
    """Maximize captures, then starve the opponent of liberties."""
    me = game.to_move
    enemy = other(me)
    best = None
    for point in game.legal_placements():
        state, captured = game.try_play(point)
        enemy_libs, enemy_imperiled = _liberty_summary(game, state, enemy)
        _own_libs, own_imperiled = _liberty_summary(game, state, me)
        score = (
            1000.0 * captured
            - 10.0 * enemy_libs
            + 25.0 * enemy_imperiled
            - 15.0 * own_imperiled
        )
        key = (score, -_tiebreak(point, seed))
        if best is None or key > best[0]:
            best = (key, point)
    return best[1] if best else None


def defender_move(game, seed):
    """Maximize own liberties and safety; capture only as a shield."""
    me = game.to_move
    best = None
    for point in game.legal_placements():
        state, captured = game.try_play(point)
        own_libs, own_imperiled = _liberty_summary(game, state, me)
        controlled = sum(
            1 for q in game.board.points
            if state[q] and state[q][-1] == me
        )
        score = (
            10.0 * own_libs
            - 50.0 * own_imperiled
            + 20.0 * captured
            + 1.0 * controlled
        )
        key = (score, -_tiebreak(point, seed))
        if best is None or key > best[0]:
            best = (key, point)
    return best[1] if best else None


MOVERS = {"attacker": attacker_move, "defender": defender_move}


def run_duel(rules, black_role, white_role, n, seed, move_cap=3000):
    game = Game(n, rules=rules)
    roles = {BLACK: black_role, WHITE: white_role}
    captures = {"attacker": 0, "defender": 0}
    extensions = {"attacker": 0, "defender": 0}
    started = time.time()
    while not game.finished and game.moves_played < move_cap:
        color = game.to_move
        role = roles[color]
        if rules == "breath-extend":
            candidates = game.extension_candidates()
            if candidates:
                game.play_extension(candidates[0])
                extensions[role] += 1
        point = MOVERS[role](game, seed)
        if point is None:
            game.play_pass()
            continue
        captures[role] += game.play(point)
    score = game.score()
    margin = score[BLACK] - score[WHITE]
    if margin > 0:
        winner = black_role
    elif margin < 0:
        winner = white_role
    else:
        winner = "draw"
    return {
        "rules": rules, "n": n, "seed": seed,
        "black": black_role, "white": white_role,
        "score": score, "winner": winner, "margin": abs(margin),
        "actions": game.moves_played,
        "captures": captures, "extensions": extensions,
        "no_progress_end": game.no_progress_end,
        "elapsed_s": round(time.time() - started, 1),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path,
                        default=Path("/tmp/varde-duels/duels.json"))
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    results = []
    for rules in ("classic", "rosette", "breath", "breath-extend"):
        for n, seeds in ((4, (1, 2, 3)), (6, (1,))):
            for seed in seeds:
                for black_role, white_role in (
                    ("attacker", "defender"),
                    ("defender", "attacker"),
                ):
                    r = run_duel(rules, black_role, white_role, n, seed)
                    results.append(r)
                    print(
                        f"{rules:14s} n={n} s={seed} {black_role[:3]}(B) v "
                        f"{white_role[:3]}(W): {r['winner']:8s} by {r['margin']:3d}  "
                        f"{r['actions']:4d} acts  caps A{r['captures']['attacker']}"
                        f"/D{r['captures']['defender']}",
                        flush=True,
                    )
                    args.output.write_text(json.dumps(results, indent=1))
    print("done")


if __name__ == "__main__":
    main()
