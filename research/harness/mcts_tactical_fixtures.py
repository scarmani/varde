"""Deterministic tactical positions for outcome-blind MCTS admission tests."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib

from actions import RulesAction, RulesState, apply_action, legal_actions
from mcts_telemetry import action_key, tactical_context
from varde import BLACK, WHITE, CORNERS, Game, signature


FIXTURE_FORMAT = "varde-mcts-tactical-fixtures"
FIXTURE_VERSION = 2
PROOF_FORMAT = "varde-exhaustive-root-transition-proof"
PROOF_VERSION = 1
EVIDENCE_CLASSES = frozenset(("diagnostic", "admission"))


@dataclass(frozen=True)
class TacticalPosition:
    id: str
    fixture_id: str
    category: str
    description: str
    state: RulesState
    acceptable_actions: tuple[RulesAction, ...]
    synthetic_history: bool = False
    evidence_class: str = "diagnostic"
    proof: dict | None = None

    def __post_init__(self):
        if self.evidence_class not in EVIDENCE_CLASSES:
            raise ValueError("unknown tactical evidence class")
        if (self.evidence_class == "admission") != (self.proof is not None):
            raise ValueError("only admission positions contain a proof")

    def public_dict(self, *, schema_version=FIXTURE_VERSION):
        context = tactical_context(self.state)
        payload = {
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
        if schema_version >= 2:
            payload["evidence_class"] = self.evidence_class
            payload["proof"] = self.proof
        return payload


def _prepared_game(rules, color, *, n=3, moves=8):
    game = Game(n, rules=rules)
    game.to_move = color
    game.moves_played = moves
    game.swap_decided = True
    return game


def _freeze(game):
    game.history = {signature(game.board, game.state, game.to_move)}
    return RulesState.from_game(game)


def _snapshot_state(
    rules,
    stacks,
    color,
    moves,
    *,
    extension_used=False,
    extension_points=(),
):
    game = Game(3, rules=rules)
    if len(stacks) != len(game.board.points):
        raise AssertionError("snapshot stack count differs from board")
    for point, stack in zip(game.board.points, stacks):
        game.state[point] = tuple(stack)
    game.to_move = color
    game.moves_played = moves
    game.swap_decided = True
    game.extension_used = extension_used
    game.extension_points = list(extension_points)
    game.quiet_moves = 0
    game.finished = False
    game.no_progress_end = False
    return _freeze(game)


def _transition_value(state, action, metric):
    context = tactical_context(state)
    key = action_key(action)
    if metric == "immediate-capture-count":
        return context["immediate_capture_actions"].get(key, 0)
    if metric == "sole-liberty-defense":
        return int(key in context["defense_actions"])
    if metric == "rescue-continuation":
        return int(action.kind == "extend")
    if metric == "fence-completion":
        return int(key in context["fence_completion_actions"])
    if metric == "seat-score-after-action":
        root_seat = state.actor_seat
        advanced = apply_action(state, action)
        return advanced.game.score()[advanced.color_for_seat(root_seat)]
    if metric == "forced-score-acceptance":
        return int(action.kind == "accept")
    raise ValueError("unknown transition-proof metric")


def transition_proof(state, metric):
    """Exhaustively rank every legal root transition under one rule fact.

    This proves a local tactical choice, not a forced game outcome. Full
    terminal enumeration is intentionally not implied by this proof format.
    """
    actions = legal_actions(state)
    values = {
        action_key(action): _transition_value(state, action, metric)
        for action in actions
    }
    best_value = max(values.values())
    best_actions = tuple(
        action for action in actions if values[action_key(action)] == best_value
    )
    rejected = [
        value for key, value in values.items()
        if key not in {action_key(action) for action in best_actions}
    ]
    return best_actions, {
        "format": PROOF_FORMAT,
        "version": PROOF_VERSION,
        "scope": "exhaustive-legal-root-transitions",
        "metric": metric,
        "root_actions": len(actions),
        "action_values": dict(sorted(values.items())),
        "best_value": best_value,
        "strict_over_rejected": not rejected or best_value > max(rejected),
        "claim_limit": "local tactical transition only; not a forced game outcome",
    }


def validate_transition_proof(position):
    if position.evidence_class != "admission" or position.proof is None:
        raise ValueError("position is not admission-grade")
    acceptable, proof = transition_proof(
        position.state, position.proof["metric"]
    )
    if acceptable != position.acceptable_actions or proof != position.proof:
        raise ValueError("transition proof does not reproduce")
    if proof["root_actions"] > 8 or not proof["strict_over_rejected"]:
        raise ValueError("admission proof is not small-root and strict")
    return proof


def _admission_position(
    position_id,
    fixture_id,
    category,
    description,
    state,
    metric,
    expected,
):
    acceptable, proof = transition_proof(state, metric)
    if acceptable != expected:
        raise AssertionError(
            f"{position_id} proof selected {acceptable!r}, expected {expected!r}"
        )
    position = TacticalPosition(
        position_id,
        fixture_id,
        category,
        description,
        state,
        acceptable,
        synthetic_history=True,
        evidence_class="admission",
        proof=proof,
    )
    validate_transition_proof(position)
    return position


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


def diagnostic_positions():
    return (
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


def _small_capture():
    state = _snapshot_state(
        "breath",
        (
            "", "W", "", "W", "W", "W", "", "", "B", "W", "W", "B",
            "B", "W", "W", "", "B", "B", "W", "W", "B", "B", "B", "B",
            "W", "", "W", "B", "B", "W", "W", "W", "W", "B", "", "B",
            "W", "W", "", "B", "", "W", "W", "B", "W", "B", "W", "B",
            "B", "W", "B", "B", "W", "",
        ),
        BLACK,
        52,
    )
    return _admission_position(
        "admission-breath-small-capture",
        "admission-breath-small-capture",
        "capture",
        "Choose the unique immediate capture from an eight-action Breath root.",
        state,
        "immediate-capture-count",
        (RulesAction("play", (2, -2)),),
    )


def _small_defense():
    state = _snapshot_state(
        "breath",
        (
            "", "W", "W", "W", "W", "W", "", "W", "B", "W", "W", "B",
            "B", "W", "W", "W", "B", "B", "W", "W", "", "B", "B", "B",
            "W", "W", "W", "B", "B", "B", "W", "W", "W", "B", "B", "B",
            "W", "W", "B", "B", "", "W", "W", "B", "W", "B", "W", "B",
            "B", "W", "B", "B", "W", "",
        ),
        WHITE,
        61,
    )
    return _admission_position(
        "admission-breath-small-defense",
        "admission-breath-small-defense",
        "defense",
        "Fill the unique sole-liberty defense from a four-action Breath root.",
        state,
        "sole-liberty-defense",
        (RulesAction("play", (-8, -2)),),
    )


def _small_takeover():
    state = _takeover().state
    return _admission_position(
        "admission-pie-small-takeover",
        "admission-pie-small-takeover",
        "takeover",
        "Take the high-scoring Black seat in the isolated two-action pie state.",
        state,
        "seat-score-after-action",
        (RulesAction("swap"),),
    )


def _small_rescue_continuation():
    state = _snapshot_state(
        "breath-run",
        (
            "W", "B", "", "", "W", "", "", "", "B", "B", "", "B",
            "B", "W", "", "B", "B", "", "W", "W", "", "", "", "",
            "", "", "", "", "W", "", "", "", "", "", "", "", "",
            "", "", "", "", "", "", "", "W", "B", "W", "", "", "W",
            "", "B", "", "",
        ),
        WHITE,
        19,
        extension_used=True,
        extension_points=((-8, -2),),
    )
    return _admission_position(
        "admission-breath-run-small-continuation",
        "admission-breath-run-small-continuation",
        "rescue-chain",
        "Continue the only legal rescue instead of ending the extension turn.",
        state,
        "rescue-continuation",
        (RulesAction("extend", (-7, -3)),),
    )


def _small_fence_completion():
    state = _snapshot_state(
        "gjerde-go",
        (
            "B", "", "B", "W", "W", "W", "B", "B", "W", "W", "B", "B",
            "B", "B", "B", "W", "", "W", "B", "B", "B", "W", "", "B",
            "B", "B", "B", "", "B", "W", "W", "W", "B", "B", "B", "B",
            "W", "", "", "B", "W", "W", "W", "B", "W", "W", "W", "",
            "W", "W", "", "W", "B", "W", "W", "W", "W", "W", "W", "W",
            "B", "W", "W", "W", "B", "B", "W", "W", "B", "B", "B", "",
        ),
        BLACK,
        80,
    )
    return _admission_position(
        "admission-gjerde-go-small-fence",
        "admission-gjerde-go-small-fence",
        "fence-completion",
        "Choose either exact fence completion from a seven-action Gjerde-Go root.",
        state,
        "fence-completion",
        (
            RulesAction("play", (-15, -3)),
            RulesAction("play", (-3, -1)),
        ),
    )


def _forced_acceptance():
    game = _prepared_game("gjerde-go", BLACK)
    for point in game.board.cell_edges[(0, 0)]:
        game.state[point] = (BLACK,)
    game.history = {signature(game.board, game.state, game.to_move)}
    game.play_pass()
    game.play_pass()
    game.resumption_used = True
    state = RulesState.from_game(game)
    if legal_actions(state) != (RulesAction("accept"),):
        raise AssertionError("forced acceptance fixture must have one action")
    return _admission_position(
        "admission-gjerde-go-forced-acceptance",
        "admission-gjerde-go-forced-acceptance",
        "acceptance",
        "Accept the terminal score after the one resumption has been consumed.",
        state,
        "forced-score-acceptance",
        (RulesAction("accept"),),
    )


def admission_positions():
    return (
        _small_capture(),
        _small_defense(),
        _small_takeover(),
        _small_rescue_continuation(),
        _small_fence_completion(),
        _forced_acceptance(),
    )


def tactical_positions():
    positions = (*diagnostic_positions(), *admission_positions())
    if len({position.id for position in positions}) != len(positions):
        raise AssertionError("tactical position ids must be unique")
    return positions


def fixture_catalog(*, schema_version=FIXTURE_VERSION, positions=None):
    positions = tactical_positions() if positions is None else tuple(positions)
    return {
        "format": FIXTURE_FORMAT,
        "version": schema_version,
        "positions": [
            position.public_dict(schema_version=schema_version)
            for position in positions
        ],
    }
