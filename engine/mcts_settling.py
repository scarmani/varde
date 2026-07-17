"""Domain-aware playout settling that still reaches real accepted terminals."""

from __future__ import annotations

from dataclasses import dataclass

from actions import apply_action, legal_actions, legal_transitions
from varde import BLACK, WHITE, GJERDE_RULESETS, control, groups_of


SETTLING_FORMAT = "varde-mcts-true-terminal-settling"
SETTLING_VERSION = 1


@dataclass(frozen=True)
class SettlingRollout:
    terminal_state: object
    actions: int
    phase_counts: tuple[tuple[str, int], ...]
    terminal_reason: str
    resumption_used: bool


def _ordinary_defense_points(state):
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


def _fence_completion_points(state):
    if state.game.rules not in GJERDE_RULESETS or state.game.finished:
        return set()
    actor = state.actor_color
    completions = set()
    for cell in state.game.board.cells:
        edges = state.game.board.cell_edges[cell]
        own = sum(control(state.game.state, point) == actor for point in edges)
        empty = [point for point in edges if not state.game.state[point]]
        if own == len(edges) - 1 and len(empty) == 1:
            completions.add(empty[0])
    return completions


def _control_key(state):
    return tuple(
        control(state.game.state, point) for point in state.game.board.points
    )


def immediate_progress_transitions(state, transitions=None):
    """Return legal transitions that make one declared immediate progress fact."""
    transitions = (
        legal_transitions(state) if transitions is None else tuple(transitions)
    )
    before_score = state.game.score()
    before_control = _control_key(state)
    defense_points = _ordinary_defense_points(state)
    fence_points = _fence_completion_points(state)
    progress = []
    for action, advanced in transitions:
        captured = sum(
            len(wave) for wave in advanced.game.last_capture_waves
        )
        protects = (
            action.kind in ("play", "extend")
            and action.point in defense_points
        )
        completes_fence = (
            action.kind == "play" and action.point in fence_points
        )
        changes_position = (
            advanced.game.score() != before_score
            or _control_key(advanced) != before_control
        )
        if (
            captured
            or protects
            or action.kind == "extend"
            or completes_fence
            or changes_position
        ):
            progress.append((action, advanced))
    return tuple(progress)


def _terminal_reason(state):
    game = state.game
    if game.no_progress_end:
        return "accepted-no-progress"
    if game.resumption_used:
        return "accepted-after-resumption"
    return "accepted-two-pass"


def run_settling_rollout(state, fallback_action):
    """Settle a cloned rollout through the engine's accepted terminal state.

    ``fallback_action`` receives ``(state, actions)`` and must choose one of the
    supplied legal actions.  No heuristic or nonterminal value is returned.
    """
    rollout = state.clone()
    actions_played = 0
    phases = {}
    post_resumption_progress = False
    resumption_used = False

    def record(phase):
        phases[phase] = phases.get(phase, 0) + 1

    while not rollout.terminal:
        actions = legal_actions(rollout)
        if not actions:
            raise AssertionError("nonterminal settling state has no legal action")
        if rollout.game.finished:
            resume = next(
                (action for action in actions if action.kind == "resume"),
                None,
            )
            score = rollout.game.score()
            actor = rollout.actor_color
            opponent = WHITE if actor == BLACK else BLACK
            if resume is not None and score[actor] < score[opponent]:
                action = resume
                post_resumption_progress = True
                resumption_used = True
                phase = "ending-resume"
            else:
                action = next(
                    item for item in actions if item.kind == "accept"
                )
                phase = "ending-accept"
            apply_action(rollout, action, copy=False, validate=False)
            actions_played += 1
            record(phase)
            continue

        points = len(rollout.game.board.points)
        move_clock = rollout.game.moves_played
        transitions = legal_transitions(rollout)
        transition_map = dict(transitions)
        pass_action = next(
            (action for action in actions if action.kind == "pass"),
            None,
        )
        finish = next(
            (
                action for action in actions
                if action.kind == "finish-extension"
            ),
            None,
        )

        if finish is not None and move_clock >= 2 * points:
            action = finish
            phase = "settle-finish-extension"
        elif post_resumption_progress:
            progress = immediate_progress_transitions(rollout, transitions)
            if progress:
                progress_actions = tuple(item[0] for item in progress)
                action = fallback_action(rollout, progress_actions)
                phase = "post-resumption-progress"
            elif finish is not None:
                action = finish
                phase = "post-resumption-finish"
            elif pass_action is not None:
                action = pass_action
                phase = "post-resumption-pass"
            else:
                action = fallback_action(rollout, actions)
                phase = "post-resumption-fallback"
            post_resumption_progress = False
        elif move_clock >= 2 * points:
            if finish is not None:
                action = finish
                phase = "settle-finish-extension"
            elif pass_action is not None:
                action = pass_action
                phase = "settle-pass"
            else:
                action = fallback_action(rollout, actions)
                phase = "settle-forced-fallback"
        elif move_clock >= points:
            if pass_action is not None and rollout.game.consecutive_passes:
                action = pass_action
                phase = "settle-reply-pass"
            else:
                progress = immediate_progress_transitions(rollout, transitions)
                if progress:
                    progress_actions = tuple(item[0] for item in progress)
                    action = fallback_action(rollout, progress_actions)
                    phase = "progress"
                elif finish is not None:
                    action = finish
                    phase = "settle-finish-extension"
                elif pass_action is not None:
                    action = pass_action
                    phase = "settle-no-progress-pass"
                else:
                    action = fallback_action(rollout, actions)
                    phase = "settle-forced-fallback"
        else:
            action = fallback_action(rollout, actions)
            phase = "fallback"

        advanced = transition_map.get(action)
        if advanced is None:
            apply_action(rollout, action, copy=False, validate=False)
        else:
            rollout = advanced
        actions_played += 1
        record(phase)

    if not rollout.terminal:
        raise AssertionError("settling rollout backed up a nonterminal state")
    return SettlingRollout(
        rollout,
        actions_played,
        tuple(sorted(phases.items())),
        _terminal_reason(rollout),
        resumption_used,
    )
