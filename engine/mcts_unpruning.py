"""Rules-derived expansion order and visit-gated progressive unpruning."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import math

from actions import RulesAction, legal_transitions
from varde import GJERDE_RULESETS, control, groups_of


UNPRUNING_FORMAT = "varde-mcts-progressive-unpruning"
UNPRUNING_VERSION = 1
ADMINISTRATIVE_ACTIONS = frozenset((
    "swap",
    "pass",
    "finish-extension",
    "resume",
    "accept",
))
TIER_LABELS = (
    "administrative",
    "extension",
    "capture",
    "defense",
    "fence-completion",
    "other",
)


@dataclass(frozen=True)
class OrderedTransition:
    action: RulesAction
    state: object = field(compare=False, repr=False)
    tier: int
    tier_label: str
    tie_value: int


def progressive_exposure_count(visits, actions):
    if isinstance(visits, bool) or not isinstance(visits, int) or visits < 0:
        raise ValueError("visits must be a nonnegative integer")
    if isinstance(actions, bool) or not isinstance(actions, int) or actions < 0:
        raise ValueError("actions must be a nonnegative integer")
    if actions == 0:
        return 0
    return min(actions, max(1, math.ceil(2 * math.sqrt(visits))))


def next_exposure_visit(visits, actions):
    current = progressive_exposure_count(visits, actions)
    if current >= actions:
        return None
    candidate = visits + 1
    while progressive_exposure_count(candidate, actions) == current:
        candidate += 1
    return candidate


def _action_identity(action):
    if action.point is None:
        return action.kind
    return f"{action.kind}:{action.point[0]},{action.point[1]}"


def _semantic_tie(seed, state, action):
    payload = repr((seed, state.key(), _action_identity(action))).encode()
    return int.from_bytes(hashlib.sha256(payload).digest(), "big")


def _sole_liberties(state):
    points = set()
    for component in groups_of(
        state.game.board,
        state.game.state,
        state.actor_color,
    ):
        liberties = {
            neighbor
            for point in component
            for neighbor in state.game.board.neighbors[point]
            if not state.game.state[neighbor]
        }
        if len(liberties) == 1:
            points.update(liberties)
    return points


def _fence_completions(state):
    if state.game.rules not in GJERDE_RULESETS or state.game.finished:
        return set()
    completions = set()
    actor = state.actor_color
    for cell in state.game.board.cells:
        edges = state.game.board.cell_edges[cell]
        own = sum(control(state.game.state, point) == actor for point in edges)
        empty = [point for point in edges if not state.game.state[point]]
        if own == len(edges) - 1 and len(empty) == 1:
            completions.add(empty[0])
    return completions


def _tier(action, advanced, defense_points, fence_points):
    if action.kind in ADMINISTRATIVE_ACTIONS:
        return 0
    if action.kind == "extend":
        return 1
    captured = sum(len(wave) for wave in advanced.game.last_capture_waves)
    if captured:
        return 2
    if action.kind == "play" and action.point in defense_points:
        return 3
    if action.kind == "play" and action.point in fence_points:
        return 4
    return 5


def ordered_rule_transitions(state, seed):
    """Generate legal transitions once and order only by immediate rule facts."""
    before = state.key()
    defense_points = _sole_liberties(state) if not state.game.finished else set()
    fence_points = _fence_completions(state)
    ordered = []
    for action, advanced in legal_transitions(state):
        tier = _tier(action, advanced, defense_points, fence_points)
        ordered.append(OrderedTransition(
            action,
            advanced,
            tier,
            TIER_LABELS[tier],
            _semantic_tie(seed, state, action),
        ))
    ordered.sort(key=lambda item: (item.tier, item.tie_value))
    if state.key() != before:
        raise AssertionError("expansion ordering mutated the analyzed state")
    return tuple(ordered)
