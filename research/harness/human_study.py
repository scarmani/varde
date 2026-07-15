#!/usr/bin/env python3
"""Generate and validate Varde's local, pseudonymous human-study package."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
ENGINE_ROOT = REPO_ROOT / "engine"
if str(ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(ENGINE_ROOT))

from varde import (  # noqa: E402
    BLACK,
    WHITE,
    Game,
    get_ruleset_spec,
    signature,
)


FORMAT = "varde-human-study-package"
VERSION = 1
RECORD_FORMAT = "varde-human-playtest"
RECORD_VERSION = 1
CANDIDATES = (
    "classic", "rosette", "breath", "breath-run", "gjerde", "gjerde-go"
)
RATINGS = (
    "agency",
    "clarity",
    "tension",
    "strategic_variety",
    "surprise",
    "inevitable_in_retrospect",
    "visual_beauty",
    "satisfying_closure",
    "desire_to_play_again",
)
PII_KEYS = {
    "name", "email", "phone", "address", "birthday", "birthdate", "age",
    "gender", "race", "ethnicity", "employer", "location", "ip", "user_agent",
}
ACTION_KINDS = {
    "play", "pass", "swap", "extend", "finish-extension", "resume"
}
SESSION_ID_PATTERN = re.compile(
    r"^(?:[0-9a-f]{32}|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
    r"[0-9a-f]{4}-[0-9a-f]{12})$"
)
HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def canonical_bytes(payload):
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()


def stable_hash(payload):
    return hashlib.sha256(canonical_bytes(payload)).hexdigest()


def source_commit():
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def build_crossover(participants, rulesets, games_per_ruleset=6):
    """Return fixed-pair Latin rotations with exact within-pair color balance."""
    if participants not in (8, 10, 12) or participants % 2:
        raise ValueError("participants must be 8, 10, or 12")
    if games_per_ruleset < 2 or games_per_ruleset % 2:
        raise ValueError("games per ruleset must be a positive even number")
    rulesets = tuple(rulesets)
    if not 2 <= len(rulesets) <= 3 or len(set(rulesets)) != len(rulesets):
        raise ValueError("select two or three distinct candidate rulesets")
    for rules in rulesets:
        if rules not in CANDIDATES:
            raise ValueError(f"not a frozen candidate: {rules}")

    pairs = []
    pair_count = participants // 2
    for pair_index in range(pair_count):
        first = f"P{2 * pair_index + 1:02d}"
        second = f"P{2 * pair_index + 2:02d}"
        offset = pair_index % len(rulesets)
        order = list(rulesets[offset:] + rulesets[:offset])
        if (pair_index // len(rulesets)) % 2:
            order.reverse()
        games = []
        for block, rules in enumerate(order):
            for game_index in range(games_per_ruleset):
                black = (
                    first
                    if (game_index + block + pair_index) % 2 == 0
                    else second
                )
                games.append({
                    "sequence": len(games) + 1,
                    "rules": rules,
                    "rules_revision": get_ruleset_spec(rules).evaluation_id,
                    "phase": "scored",
                    "game_in_ruleset": game_index + 1,
                    "black": black,
                    "white": second if black == first else first,
                })
        pairs.append({
            "pair_id": f"PAIR-{pair_index + 1:02d}",
            "players": [first, second],
            "ruleset_order": order,
            "practice": [
                {"rules": rules, "scored": False} for rules in order
            ],
            "games": games,
        })
    return {
        "participants": participants,
        "pair_count": pair_count,
        "rulesets": list(rulesets),
        "games_per_ruleset": games_per_ruleset,
        "pairs": pairs,
        "counterbalancing": {
            "opponent": "fixed anonymous pair",
            "color": "each player has three games per color per ruleset",
            "order": "Latin rotation with reversal on the second cycle",
        },
    }


def _find_resolution_position(rules):
    n = 4 if rules.startswith("gjerde") else 3
    game = Game(n, rules=rules)
    for ply in range(300):
        legal = game.legal_placements()
        opportunities = []
        quiet = []
        for point in legal:
            _state, captured = game.try_play(point)
            (opportunities if captured else quiet).append((point, captured))
        if opportunities:
            capture_point, captured = opportunities[0]
            alternative = quiet[0] if quiet else opportunities[-1]
            # These are isolated teaching fixtures, not continuations of the
            # generated playout. Keep only the current-position superko key so
            # the package remains compact and the marked replies stay exact.
            game.history = {signature(game.board, game.state, game.to_move)}
            return game, (capture_point, captured), alternative
        if not legal or game.finished:
            break
        game.play(legal[(ply * 17 + 3) % len(legal)])
    raise RuntimeError(f"could not construct a resolution puzzle for {rules}")


def _predicted_play(snapshot, point):
    game = Game.from_dict(snapshot)
    before_score = game.score()
    before_move = game.moves_played
    legal = point in game.legal_placements()
    if not legal:
        return {
            "legal": False,
            "captured": None,
            "capture_waves": None,
            "score_delta": None,
            "next_color": game.to_move,
            "move_delta": 0,
        }
    captured = game.play(point)
    after_score = game.score()
    return {
        "legal": True,
        "captured": captured,
        "capture_waves": [
            [list(item) for item in wave] for wave in game.last_capture_waves
        ],
        "score_delta": {
            color: after_score[color] - before_score[color]
            for color in (BLACK, WHITE)
        },
        "next_color": game.to_move,
        "move_delta": game.moves_played - before_move,
    }


def _gjerde_puzzle_cases(rules):
    enclosure = Game(4, rules=rules)
    fence = enclosure.board.cell_edges[(0, 0)]
    for point in fence[:-1]:
        enclosure.state[point] = (BLACK,)
    enclosure.to_move = BLACK
    enclosure.moves_played = len(fence) - 1
    enclosure.history = {
        signature(enclosure.board, enclosure.state, enclosure.to_move)
    }

    boundary = Game(4, rules=rules)
    outer = next(
        point for point in boundary.board.points
        if len(boundary.board.edge_cells[point]) == 1
    )
    return (
        (enclosure, fence[-1], "closing an interior fence"),
        (boundary, outer, "unclaimed outer-boundary openness"),
    )


def build_resolution_puzzles(rulesets):
    """Build two engine-derived call-your-shot puzzles for each ruleset."""
    puzzles = []
    for rules in rulesets:
        if rules.startswith("gjerde"):
            cases = _gjerde_puzzle_cases(rules)
        else:
            game, capture, alternative = _find_resolution_position(rules)
            cases = (
                (game, capture[0], "capture resolution"),
                (game, alternative[0], "legality, score, and next actor"),
            )
        for suffix, (game, point, focus) in zip(("A", "B"), cases):
            snapshot = game.to_dict()
            puzzles.append({
                "puzzle_id": f"{get_ruleset_spec(rules).evaluation_id}-{suffix}",
                "rules": rules,
                "rules_revision": get_ruleset_spec(rules).evaluation_id,
                "focus": focus,
                "prompt": (
                    "Without moving the piece, state whether the marked action "
                    "is legal, which stones are removed and in what waves, how "
                    "the displayed score changes, and which color acts next."
                ),
                "action": {"kind": "play", "point": list(point)},
                "snapshot": snapshot,
                "answer": _predicted_play(snapshot, point),
                "scored": False,
                "answer_hidden_from_player": True,
            })
    return puzzles


def instruments():
    return {
        "briefing_rules": [
            "Describe only the objective, legal actions, resolution order, pie rule, ending, and scoring.",
            "Do not name candidate-specific motifs, strategic hypotheses, or expected strengths.",
            "Allow rules questions; record the question without coaching a move.",
        ],
        "before_scored_games": {
            "neutral_explanation_max_minutes": 10,
            "preferred_minutes": 5,
            "resolution_puzzles": 2,
            "unscored_practice_games": 1,
        },
        "post_game_questions": [
            {"id": "deciding_event", "prompt": "What decided the game?"},
            {"id": "plan_change", "prompt": "Which move changed your plan?"},
            {"id": "reusable_shape", "prompt": "Did you discover a reusable shape or strategic principle?"},
            {"id": "next_time", "prompt": "What would you do differently next time?"},
            {"id": "decisive_understood", "prompt": "Did you understand the decisive event when it happened?", "choices": ["yes", "partly", "no"]},
            {"id": "misunderstanding_affected_game", "prompt": "Did a rules misunderstanding materially affect the game?", "choices": ["yes", "no"]},
            {"id": "optional_rematch", "prompt": "Would you accept an optional immediate rematch?", "choices": ["yes", "no"]},
        ],
        "ratings": {
            "scale": [1, 2, 3, 4, 5, 6, 7],
            "anchors": {"1": "very low", "4": "neutral", "7": "very high"},
            "items": list(RATINGS),
            "instruction": "Rate each item separately; do not average them.",
        },
        "readability_check": {
            "by_scored_game": 3,
            "local_resolution_prediction_target": 0.80,
            "material_misunderstanding_limit": 0.20,
        },
        "retention_after_days": 7,
        "retention_questions": [
            "Describe any position you still remember.",
            "Describe any reusable pattern or principle you remember.",
            "Did you voluntarily think about, discuss, or analyze the game afterward?",
            "Would you choose to play this ruleset again?",
        ],
        "emergence_coding": {
            "minimum_independent_pairs_per_motif": 2,
            "designer_supplied_terms_do_not_count": True,
        },
    }


def _assert_no_pii_keys(value, path="record"):
    if isinstance(value, dict):
        for key, item in value.items():
            if key.lower() in PII_KEYS:
                raise ValueError(f"PII field is forbidden: {path}.{key}")
            _assert_no_pii_keys(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _assert_no_pii_keys(item, f"{path}[{index}]")


def validate_playtest_record(record):
    """Validate the exact browser export surface and reject PII field names."""
    if not isinstance(record, dict):
        raise ValueError("record must be an object")
    _assert_no_pii_keys(record)
    allowed = {
        "format", "version", "session_id", "source", "rules", "board_size",
        "catalog_version", "native_evaluator_hash", "status", "actions",
        "final_score", "resumption_used", "ended_by_stagnation",
    }
    if set(record) - allowed:
        raise ValueError("unknown record fields: " + ", ".join(sorted(set(record) - allowed)))
    if record.get("format") != RECORD_FORMAT or record.get("version") != RECORD_VERSION:
        raise ValueError("unsupported playtest record")
    if (
        not isinstance(record.get("session_id"), str)
        or not SESSION_ID_PATTERN.fullmatch(record["session_id"])
    ):
        raise ValueError("session_id must be a browser-generated pseudonymous id")
    if record.get("source") != "browser-local-hotseat":
        raise ValueError("record source must be local hotseat")
    rules = record.get("rules")
    if not isinstance(rules, dict) or set(rules) != {"id", "revision"}:
        raise ValueError("rules must contain only id and revision")
    if rules["id"] not in CANDIDATES:
        raise ValueError("record ruleset is not a frozen candidate")
    if rules["revision"] != get_ruleset_spec(rules["id"]).evaluation_id:
        raise ValueError("record rules revision mismatch")
    if not isinstance(record.get("board_size"), int):
        raise ValueError("board_size must be an integer")
    if not isinstance(record.get("catalog_version"), int):
        raise ValueError("catalog_version must be an integer")
    if (
        not isinstance(record.get("native_evaluator_hash"), str)
        or not HASH_PATTERN.fullmatch(record["native_evaluator_hash"])
    ):
        raise ValueError("native_evaluator_hash must be SHA-256")
    if record.get("status") not in ("active", "complete"):
        raise ValueError("record status must be active or complete")
    actions = record.get("actions")
    if not isinstance(actions, list):
        raise ValueError("actions must be a list")
    action_fields = {
        "index", "kind", "point", "actor_color", "elapsed_ms", "move_before",
        "move_after", "captured", "capture_waves", "score_after",
    }
    for index, action in enumerate(actions):
        if not isinstance(action, dict) or set(action) != action_fields:
            raise ValueError(f"action {index} has invalid fields")
        if action["index"] != index or action["kind"] not in ACTION_KINDS:
            raise ValueError(f"action {index} has invalid identity")
        if action["actor_color"] not in (BLACK, WHITE):
            raise ValueError(f"action {index} has invalid actor color")
        if not isinstance(action["elapsed_ms"], int) or action["elapsed_ms"] < 0:
            raise ValueError(f"action {index} has invalid elapsed time")
        for key in ("move_before", "move_after", "captured"):
            if not isinstance(action[key], int) or action[key] < 0:
                raise ValueError(f"action {index} has invalid {key}")
        point = action["point"]
        if point is not None and (
            not isinstance(point, list) or len(point) != 2
            or any(not isinstance(value, int) for value in point)
        ):
            raise ValueError(f"action {index} has invalid point")
        if action["kind"] in ("play", "extend") and point is None:
            raise ValueError(f"action {index} requires a point")
        if action["kind"] not in ("play", "extend") and point is not None:
            raise ValueError(f"action {index} cannot contain a point")
        if not isinstance(action["capture_waves"], list):
            raise ValueError(f"action {index} has invalid capture waves")
        if (
            not isinstance(action["score_after"], dict)
            or set(action["score_after"]) != {BLACK, WHITE}
            or any(not isinstance(value, int) for value in action["score_after"].values())
        ):
            raise ValueError(f"action {index} has invalid score")
    if record["status"] == "complete" and (
        not isinstance(record.get("final_score"), dict)
        or set(record["final_score"]) != {BLACK, WHITE}
        or any(not isinstance(value, int) for value in record["final_score"].values())
    ):
        raise ValueError("complete record requires final_score")
    if record["status"] == "active" and record.get("final_score") is not None:
        raise ValueError("active record cannot have final_score")
    return True


def write_package(output_dir, participants, rulesets, games_per_ruleset=6):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "format": FORMAT,
        "version": VERSION,
        "source_commit": source_commit(),
        "rulesets": [get_ruleset_spec(rules).public_dict() for rules in rulesets],
        "schedule": build_crossover(participants, rulesets, games_per_ruleset),
        "instruments": instruments(),
        "puzzles": build_resolution_puzzles(rulesets),
        "browser_record_schema": {
            "format": RECORD_FORMAT,
            "version": RECORD_VERSION,
            "source": "browser-local-hotseat",
            "actions": sorted(ACTION_KINDS),
            "timing": "monotonic elapsed milliseconds; no wall-clock timestamp",
            "validator": "research/harness/human_study.py:validate_playtest_record",
        },
        "privacy": {
            "collection": "local JSON export only",
            "network_submission": False,
            "direct_identifiers": False,
            "participant_ids": "facilitator-assigned P01 through P12",
        },
    }
    payload["package_hash"] = stable_hash(payload)
    path = output_dir / "human-study-package.json"
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--participants", type=int, default=8, choices=(8, 10, 12))
    parser.add_argument("--rulesets", default="breath,breath-run")
    parser.add_argument("--games-per-ruleset", type=int, default=6)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    rulesets = tuple(item.strip() for item in args.rulesets.split(",") if item.strip())
    try:
        path = write_package(
            args.output_dir,
            args.participants,
            rulesets,
            args.games_per_ruleset,
        )
    except (ValueError, RuntimeError) as exc:
        parser.error(str(exc))
    print(path)


if __name__ == "__main__":
    main()
