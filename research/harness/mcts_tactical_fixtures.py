"""Deterministic tactical positions for outcome-blind MCTS admission tests."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib

from actions import RulesAction, RulesState, apply_action, legal_actions
from mcts_telemetry import action_key, tactical_context
from varde import BLACK, WHITE, CORNERS, Game, signature


FIXTURE_FORMAT = "varde-mcts-tactical-fixtures"
FIXTURE_VERSION = 1


@dataclass(frozen=True)
class TacticalPosition:
    id: str
    fixture_id: str
    category: str
    description: str
    state: RulesState
    acceptable_actions: tuple[RulesAction, ...]
    synthetic_history: bool = False

    def public_dict(self):
        context = tactical_context(self.state)
        return {
            "id": self.id,
            "fixture_id": self.fixture_id,
            "category": self.category,
            "description": self.description,
            "rules": self.state.game.rules,
            "board_size": self.state.game.board.n,
            "actor_color": self.state.actor_color,
            "acceptable_actions": [
                action_key(action) for action in self.acceptable_actions
            ],
            "legal_actions": context["root_legal_actions"],
            "state_key_sha256": hashlib.sha256(
                repr(self.state.key()).encode()
            ).hexdigest(),
            "synthetic_history": self.synthetic_history,
        }


def _prepared_game(rules, color, *, n=3, moves=8):
    game = Game(n, rules=rules)
    game.to_move = color
    game.moves_played = moves
    game.swap_decided = True
    return game


def _freeze(game):
    game.history = {signature(game.board, game.state, game.to_move)}
    return RulesState.from_game(game)


def _central_point(game, degree):
    return min(
        (point for point in game.board.points
         if len(game.board.neighbors[point]) == degree),
        key=lambda point: (sum(abs(value) for value in point), point),
    )


def _capture_fixture(rules, fixture_id, description):
    game = _prepared_game(rules, BLACK)
    center = _central_point(game, 3)
    first, second, capture = game.board.neighbors[center]
    game.state[center] = (WHITE,)
    game.state[first] = (BLACK,)
    game.state[second] = (BLACK,)
    state = _freeze(game)
    action = RulesAction("play", capture)
    _next_state, captured = game.try_play(capture)
    if captured != 1 or action not in legal_actions(state):
        raise AssertionError(f"invalid {fixture_id} capture fixture")
    return TacticalPosition(
        fixture_id,
        fixture_id,
        "capture",
        description,
        state,
        (action,),
    )


def _classic_capture():
    return _capture_fixture(
        "classic",
        "classic-immediate-capture",
        "Capture the isolated enemy surface stone immediately.",
    )


def _breath_capture():
    return _capture_fixture(
        "breath",
        "breath-immediate-capture",
        "Fill the last ordinary liberty and capture the isolated enemy stone.",
    )


def _breath_defense():
    game = _prepared_game("breath", BLACK)
    center = _central_point(game, 3)
    first, second, liberty = game.board.neighbors[center]
    game.state[center] = (BLACK,)
    game.state[first] = (WHITE,)
    game.state[second] = (WHITE,)
    state = _freeze(game)
    action = RulesAction("play", liberty)
    context = tactical_context(state)
    if action_key(action) not in context["defense_actions"]:
        raise AssertionError("invalid Breath sole-liberty defense fixture")
    return TacticalPosition(
        "breath-sole-liberty-defense",
        "breath-sole-liberty-defense",
        "defense",
        "Defend the isolated friendly stone by filling its sole liberty.",
        state,
        (action,),
    )


def _takeover():
    # This is a decision-isolation state rather than a reachable opening:
    # the synthetic move clock exposes the pie rule while a full Black board
    # reduces the root to swap versus pass. Both transitions remain legal and
    # score through the real engine, so the fixture tests seat perspective
    # without conflating it with a 56-way opening search.
    game = Game(3, rules="breath")
    for point in game.board.points:
        game.state[point] = (BLACK,)
    game.to_move = WHITE
    game.moves_played = 1
    game.swap_decided = False
    state = _freeze(game)
    if legal_actions(state) != (RulesAction("swap"), RulesAction("pass")):
        raise AssertionError("takeover fixture must isolate swap versus pass")
    return TacticalPosition(
        "pie-takeover-seat-perspective",
        "pie-takeover-seat-perspective",
        "takeover",
        "Take over the overwhelmingly winning Black seat rather than pass.",
        state,
        (RulesAction("swap"),),
        synthetic_history=True,
    )


def _ring_of_cell(q=0, r=0):
    cx, cy = 3 * q, 2 * r + q
    return [(cx + dx, cy + dy) for dx, dy in CORNERS]


def _rosette_entombment():
    game = _prepared_game("rosette", BLACK, moves=10)
    ring = _ring_of_cell()
    members = set(ring)
    for point in ring:
        game.state[point] = (WHITE,)
    for point in ring:
        for neighbor in game.board.neighbors[point]:
            if neighbor not in members:
                game.state[neighbor] = (BLACK,)
    state = _freeze(game)
    caps = []
    for point in ring:
        action = RulesAction("play", point)
        if action not in legal_actions(state):
            continue
        _next_state, captured = game.try_play(point)
        if captured == 5:
            caps.append(action)
    if len(caps) != 6:
        raise AssertionError("Rosette fixture must admit all six entombment caps")
    return TacticalPosition(
        "rosette-entombment-cap",
        "rosette-entombment-cap",
        "capture",
        "Cap any column of the sealed lone ring to unzip five stones.",
        state,
        tuple(caps),
    )


def _breath_run_positions():
    game = _prepared_game("breath-run", BLACK)
    center = max(game.board.deep)
    first, second, liberty = game.board.neighbors[center]
    onward = [point for point in game.board.neighbors[liberty] if point != center]
    game.state[center] = (BLACK,)
    game.state[first] = (WHITE,)
    game.state[second] = (WHITE,)
    game.state[onward[0]] = (WHITE,)
    first_state = _freeze(game)
    first_action = RulesAction("extend", liberty)
    if first_action not in legal_actions(first_state):
        raise AssertionError("Breath-run entry must offer the rescue")

    continued = apply_action(first_state, first_action)
    second_action = RulesAction("extend", onward[1])
    if second_action not in legal_actions(continued):
        raise AssertionError("Breath-run continuation must offer another rescue")
    if RulesAction("finish-extension") not in legal_actions(continued):
        raise AssertionError("Breath-run continuation must allow chain closure")
    return (
        TacticalPosition(
            "breath-run-rescue-chain:entry",
            "breath-run-rescue-chain",
            "rescue-chain",
            "Choose the free rescue of a one-liberty group over a normal move.",
            first_state,
            (first_action,),
        ),
        TacticalPosition(
            "breath-run-rescue-chain:continue",
            "breath-run-rescue-chain",
            "rescue-chain",
            "Continue the rescue chain instead of ending it immediately.",
            continued,
            (second_action,),
        ),
    )


def _gjerde_fence_completion():
    game = _prepared_game("gjerde", BLACK)
    cell = (0, 0)
    fence = game.board.cell_edges[cell]
    for point in fence[:-1]:
        game.state[point] = (BLACK,)
    state = _freeze(game)
    action = RulesAction("play", fence[-1])
    context = tactical_context(state)
    if action_key(action) not in context["fence_completion_actions"]:
        raise AssertionError("invalid Gjerde fence-completion fixture")
    next_state = apply_action(state, action)
    if next_state.game.score()[BLACK] != 1:
        raise AssertionError("Gjerde completion must close exactly one cell")
    return TacticalPosition(
        "gjerde-fence-completion",
        "gjerde-fence-completion",
        "fence-completion",
        "Claim the sixth boundary line to complete a one-cell fence.",
        state,
        (action,),
    )


def _gjerde_go_capture():
    game = _prepared_game("gjerde-go", BLACK)
    center = _central_point(game, 4)
    neighbors = game.board.neighbors[center]
    game.state[center] = (WHITE,)
    for point in neighbors[:-1]:
        game.state[point] = (BLACK,)
    state = _freeze(game)
    action = RulesAction("play", neighbors[-1])
    _next_state, captured = game.try_play(neighbors[-1])
    if captured != 1:
        raise AssertionError("invalid Gjerde-Go immediate-capture fixture")
    return TacticalPosition(
        "gjerde-go-immediate-capture",
        "gjerde-go-immediate-capture",
        "capture",
        "Fill the fourth liberty and capture the isolated enemy line.",
        state,
        (action,),
    )


def _gjerde_go_acceptance():
    game = _prepared_game("gjerde-go", BLACK)
    for point in game.board.cell_edges[(0, 0)]:
        game.state[point] = (BLACK,)
    game.history = {signature(game.board, game.state, game.to_move)}
    game.play_pass()
    game.play_pass()
    state = RulesState.from_game(game)
    if state.actor_color != BLACK or game.score() != {BLACK: 1, WHITE: 0}:
        raise AssertionError("invalid sparse-score acceptance fixture")
    return TacticalPosition(
        "gjerde-go-ahead-acceptance",
        "gjerde-go-ahead-acceptance",
        "acceptance",
        "Accept the sparse 1-0 fenced score rather than reopen play.",
        state,
        (RulesAction("accept"),),
    )


def tactical_positions():
    positions = (
        _classic_capture(),
        _breath_capture(),
        _breath_defense(),
        _takeover(),
        _rosette_entombment(),
        *_breath_run_positions(),
        _gjerde_fence_completion(),
        _gjerde_go_capture(),
        _gjerde_go_acceptance(),
    )
    if len({position.id for position in positions}) != len(positions):
        raise AssertionError("tactical position ids must be unique")
    return positions


def fixture_catalog():
    positions = tactical_positions()
    return {
        "format": FIXTURE_FORMAT,
        "version": FIXTURE_VERSION,
        "positions": [position.public_dict() for position in positions],
    }
