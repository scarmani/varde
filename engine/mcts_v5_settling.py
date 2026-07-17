"""True-terminal Settling V2 rollout policy for MCTS Search V5."""

from __future__ import annotations

from dataclasses import dataclass
import math

from actions import apply_action, legal_actions, legal_transitions
from varde import GJERDE_RULESETS, control, groups_of, other


SETTLING_FORMAT = "varde-mcts-true-terminal-settling"
SETTLING_VERSION = 2
EVENT_ORDER = (
    "capture",
    "extension",
    "extension-closure",
    "sole-liberty-defense",
    "fence-completion",
)
EVENT_KINDS = frozenset(EVENT_ORDER)


class SettlingIntegrityError(RuntimeError):
    """The research rollout failed to reach a real terminal within 4P."""


@dataclass(frozen=True)
class EventTransition:
    action: object
    state: object
    events: tuple[str, ...]


@dataclass(frozen=True)
class SettlingV2Rollout:
    terminal_state: object
    actions: int
    phase_counts: tuple[tuple[str, int], ...]
    terminal_reason: str
    resumption_used: bool
    event_counts: tuple[tuple[str, int], ...]
    transition_batches: int
    states_visited: int


def _threatened_groups(state):
    threatened = []
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
            threatened.append((min(component), next(iter(liberties))))
    return tuple(threatened)


def _fence_completions(state):
    if state.game.rules not in GJERDE_RULESETS or state.game.finished:
        return {}
    actor = state.actor_color
    completions = {}
    for cell in state.game.board.cells:
        edges = state.game.board.cell_edges[cell]
        empty = [point for point in edges if not state.game.state[point]]
        own = sum(control(state.game.state, point) == actor for point in edges)
        if own == len(edges) - 1 and len(empty) == 1:
            completions.setdefault(empty[0], []).append(cell)
    return completions


def _fence_owner(state, cell):
    owners = {
        control(state.game.state, point)
        for point in state.game.board.cell_edges[cell]
    }
    return next(iter(owners)) if len(owners) == 1 else None


def classify_event_transitions(state, transitions=None):
    """Classify one pre-generated legal transition batch by exact V2 events."""
    before = state.key()
    transitions = (
        tuple(legal_transitions(state))
        if transitions is None else tuple(transitions)
    )
    threatened = _threatened_groups(state) if not state.game.finished else ()
    fences = _fence_completions(state)
    actor = state.actor_color
    classified = []
    for action, advanced in transitions:
        events = []
        if (
            action.kind in ("play", "extend")
            and any(advanced.game.last_capture_waves)
        ):
            events.append("capture")
        if action.kind == "extend":
            events.append("extension")
            if advanced.actor_seat != state.actor_seat:
                events.append("extension-closure")
        elif action.kind == "finish-extension":
            events.append("extension-closure")
        if action.kind in ("play", "extend"):
            if any(
                action.point == liberty
                and control(advanced.game.state, anchor) == actor
                for anchor, liberty in threatened
            ):
                events.append("sole-liberty-defense")
            if any(
                _fence_owner(advanced, cell) == actor
                for cell in fences.get(action.point, ())
            ):
                events.append("fence-completion")
        if events:
            classified.append(EventTransition(
                action,
                advanced,
                tuple(event for event in EVENT_ORDER if event in events),
            ))
    if state.key() != before:
        raise AssertionError("Settling V2 event scan mutated the rollout state")
    return tuple(classified)


def _terminal_reason(state):
    if state.game.no_progress_end:
        return "accepted-no-progress"
    if state.game.resumption_used:
        return "accepted-after-resumption"
    return "accepted-two-pass"


def run_settling_v2_rollout(state, fallback_action, *, action_limit=None):
    """Run a cloned policy to the engine's real accepted terminal score."""
    rollout = state.clone()
    points = len(rollout.game.board.points)
    eligibility = math.ceil(0.5 * points)
    action_limit = 4 * points if action_limit is None else action_limit
    if (
        isinstance(action_limit, bool)
        or not isinstance(action_limit, int)
        or not 1 <= action_limit <= 4 * points
    ):
        raise ValueError("settling action limit must be within 1..4P")
    actions_played = 0
    states_visited = 0
    transition_batches = 0
    phases = {}
    events_seen = {}
    post_resumption_events = None
    resumption_used = False

    def record(mapping, key):
        mapping[key] = mapping.get(key, 0) + 1

    while not rollout.terminal:
        if actions_played >= action_limit:
            raise SettlingIntegrityError(
                f"Settling V2 exceeded {action_limit} actions without terminal"
            )
        states_visited += 1
        actions = legal_actions(rollout)
        if not actions:
            raise SettlingIntegrityError(
                "nonterminal Settling V2 state has no legal action"
            )

        if rollout.game.finished:
            resume = next(
                (action for action in actions if action.kind == "resume"),
                None,
            )
            score = rollout.game.score()
            actor = rollout.actor_color
            if resume is not None and score[actor] < score[other(actor)]:
                action = resume
                phase = "ending-resume"
                post_resumption_events = 1
                resumption_used = True
            else:
                action = next(
                    item for item in actions if item.kind == "accept"
                )
                phase = "ending-accept"
            apply_action(rollout, action, copy=False, validate=False)
            actions_played += 1
            record(phases, phase)
            continue

        transitions = legal_transitions(rollout)
        transition_batches += 1
        transition_map = dict(transitions)
        event_transitions = classify_event_transitions(rollout, transitions)
        pass_action = next(
            (action for action in actions if action.kind == "pass"), None
        )
        finish = next(
            (
                action for action in actions
                if action.kind == "finish-extension"
            ),
            None,
        )
        clock = rollout.game.moves_played

        if post_resumption_events is not None:
            if post_resumption_events > 0 and event_transitions:
                choices = tuple(item.action for item in event_transitions)
                action = fallback_action(rollout, choices)
                phase = "post-resumption-event"
                post_resumption_events = 0
            elif finish is not None:
                action = finish
                phase = "post-resumption-finish"
                post_resumption_events = 0
            elif pass_action is not None:
                action = pass_action
                phase = "post-resumption-pass"
                post_resumption_events = 0
            else:
                action = fallback_action(rollout, actions)
                phase = "post-resumption-forced"
                post_resumption_events = 0
        elif clock >= points:
            if finish is not None:
                action = finish
                phase = "p-finish-extension"
            elif pass_action is not None:
                action = pass_action
                phase = "p-pass"
            else:
                action = fallback_action(rollout, actions)
                phase = "p-forced"
        elif clock >= eligibility:
            if pass_action is not None and rollout.game.consecutive_passes:
                action = pass_action
                phase = "settle-reply-pass"
            elif event_transitions:
                choices = tuple(item.action for item in event_transitions)
                action = fallback_action(rollout, choices)
                phase = "event"
            elif pass_action is not None:
                action = pass_action
                phase = "settle-no-event-pass"
            elif finish is not None:
                action = finish
                phase = "settle-finish-extension"
            else:
                action = fallback_action(rollout, actions)
                phase = "settle-forced"
        else:
            action = fallback_action(rollout, actions)
            phase = "fallback"

        selected_event = next(
            (item for item in event_transitions if item.action == action),
            None,
        )
        if selected_event is not None:
            for event in selected_event.events:
                record(events_seen, event)
        advanced = transition_map.get(action)
        if advanced is None:
            apply_action(rollout, action, copy=False, validate=False)
        else:
            rollout = advanced
        actions_played += 1
        record(phases, phase)

    return SettlingV2Rollout(
        rollout,
        actions_played,
        tuple(sorted(phases.items())),
        _terminal_reason(rollout),
        resumption_used,
        tuple(sorted(events_seen.items())),
        transition_batches,
        states_visited,
    )
