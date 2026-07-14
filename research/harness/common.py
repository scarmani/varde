"""Reproducible training/evaluation helpers for Varde Advanced V2."""

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import random
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
ENGINE_ROOT = REPO_ROOT / "engine"
if str(ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(ENGINE_ROOT))

from varde import BLACK, Game, other  # noqa: E402
from learning import TRAINING_WATCHDOG_MULTIPLIER  # noqa: E402
from opponent import choose_decision  # noqa: E402


@dataclass(frozen=True)
class GameResult:
    board_size: int
    seed: int
    initial_variant_color: str
    final_variant_color: str
    result: float
    margin: int
    actions: int
    complete: bool


def source_sha():
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def file_sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json_atomic(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def append_jsonl(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def play_heldout_game(model, variant_color, seed, n):
    """Play one no-exploration Advanced-vs-Standard game.

    The operational watchdog reports an incomplete result; it never changes
    the live rules or forces a game action.
    """
    game = Game(n)
    initial_variant_color = variant_color
    actions = 0
    limit = TRAINING_WATCHDOG_MULTIPLIER * len(game.board.points)
    while actions < limit:
        if game.finished:
            if not game.resumption_used:
                score = game.score()
                if score[BLACK] != score[other(BLACK)]:
                    game.demand_resumption()
                    actions += 1
                    continue
            break
        color = game.to_move
        if color == variant_color:
            decision = choose_decision(
                game, color, "advanced", seed=seed, model=model
            )
        else:
            decision = choose_decision(
                game, color, "standard", seed=seed + 7777
            )
        if decision.action == "play":
            game.play(decision.point)
        elif decision.action == "pass":
            game.play_pass()
        elif decision.action == "swap":
            game.take_over()
            variant_color = other(variant_color)
        elif decision.action == "resume":
            game.demand_resumption()
        elif decision.action == "accept":
            break
        actions += 1
    else:
        return GameResult(
            n, seed, initial_variant_color, variant_color, 0.0, 0, actions, False
        )
    score = game.score()
    margin = score[variant_color] - score[other(variant_color)]
    result = 1.0 if margin > 0 else 0.5 if margin == 0 else 0.0
    return GameResult(
        n,
        seed,
        initial_variant_color,
        variant_color,
        result,
        margin,
        actions,
        True,
    )


def one_sided_bootstrap_lower(pair_scores, seed, samples=10000):
    if not pair_scores:
        return 0.0
    rng = random.Random(seed)
    size = len(pair_scores)
    estimates = sorted(
        sum(pair_scores[rng.randrange(size)] for _ in range(size)) / size
        for _ in range(samples)
    )
    return estimates[int(0.05 * samples)]


def paired_evaluation(
    model,
    toy_pairs,
    beginner_pairs,
    seed,
    log_path,
    progress=None,
):
    schedule = [3] * toy_pairs + [4] * beginner_pairs
    pairs = []
    all_games = []
    for pair_index, n in enumerate(schedule):
        game_seed = seed + 104729 * pair_index
        games = [
            play_heldout_game(model, color, game_seed, n)
            for color in (BLACK, other(BLACK))
        ]
        pair = {
            "pair": pair_index,
            "board_size": n,
            "seed": game_seed,
            "score": sum(game.result for game in games) / 2,
            "mean_margin": sum(game.margin for game in games) / 2,
            "complete": all(game.complete for game in games),
            "games": [asdict(game) for game in games],
        }
        pairs.append(pair)
        all_games.extend(games)
        append_jsonl(log_path, pair)
        if progress:
            progress(pair_index + 1, len(schedule), pair)

    complete_games = [game for game in all_games if game.complete]
    strata = {}
    for n in (3, 4):
        games = [game for game in complete_games if game.board_size == n]
        strata[str(n)] = {
            "games": len(games),
            "score": sum(game.result for game in games) / len(games) if games else 0.0,
            "mean_margin": sum(game.margin for game in games) / len(games) if games else 0.0,
        }
    pair_scores = [pair["score"] for pair in pairs if pair["complete"]]
    overall_score = (
        sum(game.result for game in complete_games) / len(complete_games)
        if complete_games
        else 0.0
    )
    mean_margin = (
        sum(game.margin for game in complete_games) / len(complete_games)
        if complete_games
        else 0.0
    )
    incomplete = len(all_games) - len(complete_games)
    lower = one_sided_bootstrap_lower(pair_scores, seed + 1)
    gate = {
        "overall_at_least_60": overall_score >= 0.60,
        "toy_above_50": strata["3"]["score"] > 0.50,
        "beginner_above_50": strata["4"]["score"] > 0.50,
        "bootstrap_lower_above_50": lower > 0.50,
        "positive_margin": mean_margin > 0,
        "all_games_complete": incomplete == 0,
    }
    return {
        "configuration": {
            "toy_pairs": toy_pairs,
            "beginner_pairs": beginner_pairs,
            "seed": seed,
            "bootstrap_samples": 10000,
        },
        "games": len(all_games),
        "complete_games": len(complete_games),
        "incomplete_games": incomplete,
        "overall_score": overall_score,
        "mean_margin": mean_margin,
        "one_sided_95_lower": lower,
        "strata": strata,
        "gate": gate,
        "passed": all(gate.values()),
        "pairs": pairs,
    }
