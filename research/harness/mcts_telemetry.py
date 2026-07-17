"""Research-only tactical opportunity and decision telemetry for Varde."""

from __future__ import annotations

from collections import Counter

from actions import apply_action, legal_actions
from varde import GJERDE_RULESETS, control, groups_of


def action_key(action):
    return (
        action.kind
        if action.point is None
        else f"{action.kind}:{action.point[0]},{action.point[1]}"
    )


def _sole_liberty_points(state):
    game = state.game
    points = set()
    groups = 0
    for comp in groups_of(game.board, game.state, state.actor_color):
        liberties = {
            neighbor
            for point in comp
            for neighbor in game.board.neighbors[point]
            if not game.state[neighbor]
        }
        if len(liberties) == 1:
            groups += 1
            points.update(liberties)
    return groups, points


def _fence_completion_points(state):
    game = state.game
    if game.rules not in GJERDE_RULESETS or game.finished:
        return set()
    color = state.actor_color
    completions = set()
    for cell in game.board.cells:
        edges = game.board.cell_edges[cell]
        own = [point for point in edges if control(game.state, point) == color]
        empty = [point for point in edges if not game.state[point]]
        if len(own) == len(edges) - 1 and len(empty) == 1:
            completions.add(empty[0])
    return completions


def tactical_context(state):
    """Describe tactical opportunities without mutating ``state``.

    This deliberately records observable rule transitions rather than an
    evaluator score. It is used only for research telemetry and admission
    fixtures, never to choose a live action.
    """
    before = state.key()
    actions = legal_actions(state)
    captures = {}
    for action in actions:
        if action.kind == "play":
            _next_state, captured = state.game.try_play(action.point)
        elif action.kind == "extend":
            next_state = apply_action(state, action, validate=False)
            captured = sum(
                len(wave) for wave in next_state.game.last_capture_waves
            )
        else:
            continue
        if captured:
            captures[action_key(action)] = captured

    threatened_groups, defense_points = _sole_liberty_points(state)
    fence_points = _fence_completion_points(state)
    kinds = Counter(action.kind for action in actions)
    payload = {
        "root_legal_actions": len(actions),
        "action_kinds": dict(sorted(kinds.items())),
        "immediate_capture_actions": dict(sorted(captures.items())),
        "maximum_immediate_capture": max(captures.values(), default=0),
        "sole_liberty_groups": threatened_groups,
        "defense_actions": sorted(
            action_key(action)
            for action in actions
            if action.point in defense_points
            and action.kind in ("play", "extend")
        ),
        "swap_available": any(action.kind == "swap" for action in actions),
        "extension_actions": sorted(
            action_key(action) for action in actions if action.kind == "extend"
        ),
        "extension_turn_open": state.game.extension_only_turn,
        "fence_completion_actions": sorted(
            action_key(action)
            for action in actions
            if action.kind == "play" and action.point in fence_points
        ),
    }
    if state.key() != before:
        raise AssertionError("tactical telemetry mutated the analyzed state")
    return payload


def annotate_choice(context, action):
    key = action_key(action)
    capture = context["immediate_capture_actions"].get(key, 0)
    return {
        "chosen_action_key": key,
        "chose_immediate_capture": capture > 0,
        "chosen_immediate_capture_count": capture,
        "chose_maximum_capture": bool(capture)
        and capture == context["maximum_immediate_capture"],
        "chose_defense": key in context["defense_actions"],
        "chose_takeover": action.kind == "swap",
        "chose_extension": action.kind == "extend",
        "chose_finish_extension": action.kind == "finish-extension",
        "chose_fence_completion": key in context["fence_completion_actions"],
    }
