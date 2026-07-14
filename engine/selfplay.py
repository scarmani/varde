"""Instrumented Varde self-play smoke tests.

Policies are diagnostic, not claims about strong play:

* random: legal placements plus a 2% pass chance after the opening;
* greedy: pass unless a placement immediately improves area score;
* epsilon: 15% random exploration around the greedy policy.

Run: python3 selfplay.py [board_n] [games] [random|greedy|epsilon]
"""

import random
import statistics
import sys

from varde import BLACK, WHITE, Game, Illegal, height


def scan_placements(game):
    """Return legal placements and the number currently blocked by superko."""
    legal = []
    repetition_blocks = 0
    for point in game.board.points:
        try:
            game.try_play(point)
            legal.append(point)
        except Illegal as exc:
            if str(exc) == "repetition":
                repetition_blocks += 1
    return legal, repetition_blocks


def greedy_move(game, rng, legal):
    """Return the move with best immediate area gain, or None to pass."""
    from varde import other

    me = game.to_move
    base = game.score()
    best = None
    best_diff = base[me] - base[other(me)]
    legal = list(legal)
    rng.shuffle(legal)
    for point in legal:
        state, _ = game.try_play(point)
        saved = game.state
        game.state = state
        score = game.score()
        game.state = saved
        difference = score[me] - score[other(me)]
        if difference > best_diff:
            best = point
            best_diff = difference
    return best


def choose_move(game, rng, legal, policy):
    if not legal:
        return None
    if policy == "random":
        if game.moves_played > 0 and rng.random() < 0.02:
            return None
        return rng.choice(legal)
    if policy == "epsilon" and rng.random() < 0.15:
        return rng.choice(legal)
    return greedy_move(game, rng, legal)


def play_one(n, rng, policy="random", max_turns=None):
    game = Game(n)
    points = len(game.board.points)
    if max_turns is None:
        max_turns = 8 * points
    opening = int(0.6 * points)
    stats = {
        "turns": 0,
        "placements": 0,
        "passes": 0,
        "caps": 0,
        "caps_open": 0,
        "caps_late": 0,
        "first_stack": None,
        "captured": 0,
        "capture_moves": 0,
        "capture_waves": 0,
        "wave_depths": [],
        "max_wave_depth": 0,
        "max_wave_size": 0,
        "superko_blocks": 0,
        "hit_cap": False,
    }

    while not game.finished and stats["turns"] < max_turns:
        legal, repetition_blocks = scan_placements(game)
        stats["superko_blocks"] += repetition_blocks
        point = choose_move(game, rng, legal, policy)
        if point is None:
            game.play_pass()
            stats["passes"] += 1
        else:
            was_stack = height(game.state, point) >= 1
            captured = game.play(point)
            stats["placements"] += 1
            stats["captured"] += captured
            if captured:
                wave_sizes = [len(wave) for wave in game.last_capture_waves]
                stats["capture_moves"] += 1
                stats["capture_waves"] += len(wave_sizes)
                stats["wave_depths"].append(len(wave_sizes))
                stats["max_wave_depth"] = max(
                    stats["max_wave_depth"], len(wave_sizes)
                )
                stats["max_wave_size"] = max(
                    stats["max_wave_size"], max(wave_sizes, default=0)
                )
            if was_stack:
                stats["caps"] += 1
                if stats["placements"] <= opening:
                    stats["caps_open"] += 1
                else:
                    stats["caps_late"] += 1
                if stats["first_stack"] is None:
                    stats["first_stack"] = stats["placements"]
        stats["turns"] += 1

    stats["hit_cap"] = not game.finished
    score = game.score()
    stats["score_b"], stats["score_w"] = score[BLACK], score[WHITE]
    stats["margin"] = score[BLACK] - score[WHITE]
    return stats


def summarize(n, games, policy):
    seeds = {"random": 7, "greedy": 11, "epsilon": 17}
    rng = random.Random(seeds[policy])
    results = [play_one(n, rng, policy) for _ in range(games)]
    points = 6 * n * n
    placements = [item["placements"] for item in results]
    turns = [item["turns"] for item in results]
    firsts = [item["first_stack"] for item in results if item["first_stack"]]
    total_placements = sum(placements)
    opening_placements = sum(min(p, int(0.6 * points)) for p in placements)
    late_placements = sum(max(0, p - int(0.6 * points)) for p in placements)
    capture_moves = sum(item["capture_moves"] for item in results)
    capture_waves = sum(item["capture_waves"] for item in results)
    wave_depths = [depth for item in results for depth in item["wave_depths"]]
    margins = [item["margin"] for item in results]

    print(f"{policy.upper()} board n={n} ({points} points), {games} games")
    print(
        f"  terminated before 8N: "
        f"{sum(1 for item in results if not item['hit_cap'])}/{games}"
    )
    print(
        f"  placements          : median {statistics.median(placements)}  "
        f"mean {statistics.mean(placements):.1f} ({statistics.mean(placements)/points:.2f}N)"
    )
    print(f"  turns incl. passes  : median {statistics.median(turns)}")
    print(f"  first stack         : median {statistics.median(firsts) if firsts else '-'}")
    print(f"  cap share all       : {sum(item['caps'] for item in results)/max(1,total_placements):.1%}")
    print(f"  cap share opening   : {sum(item['caps_open'] for item in results)/max(1,opening_placements):.1%}")
    print(f"  cap share late      : {sum(item['caps_late'] for item in results)/max(1,late_placements):.1%}")
    print(
        f"  capture waves/move  : "
        f"{capture_waves/max(1,capture_moves):.2f} mean; "
        f"median {statistics.median(wave_depths) if wave_depths else 0}; "
        f"p95 {sorted(wave_depths)[max(0, int(0.95 * len(wave_depths)) - 1)] if wave_depths else 0}; "
        f"max depth {max(item['max_wave_depth'] for item in results)}; "
        f"max wave size {max(item['max_wave_size'] for item in results)}"
    )
    print(
        f"  superko blocks seen : {sum(item['superko_blocks'] for item in results)}; "
        f"margin B-W mean {statistics.mean(margins):+.1f}; "
        f"draws {sum(1 for margin in margins if margin == 0)}"
    )


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    games = int(sys.argv[2]) if len(sys.argv) > 2 else 40
    policy = sys.argv[3] if len(sys.argv) > 3 else "random"
    if policy not in {"random", "greedy", "epsilon"}:
        raise SystemExit("policy must be random, greedy, or epsilon")
    summarize(n, games, policy)


if __name__ == "__main__":
    main()
