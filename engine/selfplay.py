"""Cairn stage-2 smoke test: random self-play with metric logging.

Verifies practical termination and collects the playtest-table metrics:
game length, first stack move, cap share by phase, capture waves,
score margins, draws.  Random players reveal rules pathologies, not
strategy.

Run: python3 selfplay.py [n_board] [n_games]
     python3 selfplay.py [n_board] [n_games] greedy
"""

import random
import sys
import statistics
from cairn import Game, Illegal, BLACK, WHITE, resolve, signature, height


def play_one(n, rng, max_moves=None):
    g = Game(n)
    N = len(g.board.points)
    if max_moves is None:
        max_moves = 8 * N  # generous hard stop; report if ever hit
    stats = {
        "moves": 0, "caps": 0, "caps_open": 0, "caps_late": 0,
        "first_stack": None, "captured": 0, "max_wave_stones": 0,
        "hit_cap": False,
    }
    opening = int(0.6 * N)
    while not g.finished and stats["moves"] < max_moves:
        moves = g.legal_placements()
        if not moves:
            g.play_pass()
            stats["moves"] += 1
            continue
        # random players pass rarely, but must be able to end the game:
        # small chance to pass when few moves change anything
        if rng.random() < 0.02:
            g.play_pass()
            stats["moves"] += 1
            continue
        p = rng.choice(moves)
        was_stack = height(g.state, p) >= 1
        captured = g.play(p)
        stats["moves"] += 1
        stats["captured"] += captured
        stats["max_wave_stones"] = max(stats["max_wave_stones"], captured)
        if was_stack:
            stats["caps"] += 1
            if stats["moves"] <= opening:
                stats["caps_open"] += 1
            else:
                stats["caps_late"] += 1
            if stats["first_stack"] is None:
                stats["first_stack"] = stats["moves"]
    stats["hit_cap"] = stats["moves"] >= max_moves
    s = g.score()
    stats["score_b"], stats["score_w"] = s[BLACK], s[WHITE]
    stats["margin"] = s[BLACK] - s[WHITE]
    return stats


def greedy_move(g, rng):
    """Best score-differential move; None means pass (nothing gains)."""
    me = g.to_move
    from cairn import other
    base = g.score()
    base_diff = base[me] - base[other(me)]
    best, best_diff = None, base_diff
    moves = g.legal_placements()
    rng.shuffle(moves)
    for p in moves:
        st, cap = g.try_play(p)
        saved = g.state
        g.state = st
        s = g.score()
        g.state = saved
        d = s[me] - s[other(me)]
        if d > best_diff:
            best, best_diff = p, d
    return best


def play_one_greedy(n, rng, max_moves=None):
    g = Game(n)
    N = len(g.board.points)
    if max_moves is None:
        max_moves = 8 * N
    stats = {"moves": 0, "caps": 0, "captured": 0, "first_stack": None,
             "max_wave_stones": 0, "hit_cap": False}
    while not g.finished and stats["moves"] < max_moves:
        p = greedy_move(g, rng)
        if p is None:
            g.play_pass()
        else:
            was_stack = height(g.state, p) >= 1
            cap = g.play(p)
            stats["captured"] += cap
            stats["max_wave_stones"] = max(stats["max_wave_stones"], cap)
            if was_stack:
                stats["caps"] += 1
                if stats["first_stack"] is None:
                    stats["first_stack"] = stats["moves"] + 1
        stats["moves"] += 1
    stats["hit_cap"] = stats["moves"] >= max_moves
    s = g.score()
    stats["score_b"], stats["score_w"] = s[BLACK], s[WHITE]
    stats["margin"] = s[BLACK] - s[WHITE]
    return stats


def main_greedy(n, games):
    rng = random.Random(11)
    allstats = [play_one_greedy(n, rng) for _ in range(games)]
    N = 6 * n * n
    moves = [s["moves"] for s in allstats]
    caps = sum(s["caps"] for s in allstats)
    firsts = [s["first_stack"] for s in allstats if s["first_stack"]]
    margins = [s["margin"] for s in allstats]
    print(f"GREEDY board n={n} ({N} points), {games} games")
    print(f"  terminated normally : {sum(1 for s in allstats if not s['hit_cap'])}/{games}")
    print(f"  game length         : median {statistics.median(moves)}  "
          f"({statistics.mean(moves)/N:.2f}N mean)")
    print(f"  first stack move    : median {statistics.median(firsts) if firsts else '-'}")
    print(f"  cap share (all)     : {caps/max(1,sum(moves)):.1%}")
    print(f"  captured/game       : mean {statistics.mean([s['captured'] for s in allstats]):.1f}  "
          f"max wave {max(s['max_wave_stones'] for s in allstats)}")
    print(f"  margin B-W          : mean {statistics.mean(margins):+.1f}  "
          f"draws {sum(1 for m in margins if m == 0)}")


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    games = int(sys.argv[2]) if len(sys.argv) > 2 else 50
    rng = random.Random(7)
    allstats = [play_one(n, rng) for _ in range(games)]
    N = 6 * n * n

    def col(k):
        return [s[k] for s in allstats]

    moves = col("moves")
    caps = col("caps")
    firsts = [s["first_stack"] for s in allstats if s["first_stack"]]
    print(f"board n={n} ({N} points), {games} random games")
    print(f"  terminated normally : {sum(1 for s in allstats if not s['hit_cap'])}/{games}")
    print(f"  game length         : median {statistics.median(moves)}  "
          f"mean {statistics.mean(moves):.0f}  max {max(moves)}  "
          f"({statistics.mean(moves)/N:.2f}N mean)")
    print(f"  first stack move    : median {statistics.median(firsts) if firsts else '-'}")
    print(f"  cap share (all)     : {sum(caps)/max(1,sum(moves)):.1%}")
    open_caps = sum(col("caps_open"))
    late_caps = sum(col("caps_late"))
    open_moves = sum(min(m, int(0.6 * N)) for m in moves)
    late_moves = sum(max(0, m - int(0.6 * N)) for m in moves)
    print(f"  cap share opening   : {open_caps/max(1,open_moves):.1%}")
    print(f"  cap share late      : {late_caps/max(1,late_moves):.1%}")
    print(f"  stones captured/game: mean {statistics.mean(col('captured')):.1f}  "
          f"max single wave {max(col('max_wave_stones'))}")
    margins = col("margin")
    print(f"  margin B-W          : mean {statistics.mean(margins):+.1f}  "
          f"draws {sum(1 for m in margins if m == 0)}")


if __name__ == "__main__":
    if len(sys.argv) > 3 and sys.argv[3] == "greedy":
        main_greedy(int(sys.argv[1]), int(sys.argv[2]))
    else:
        main()
