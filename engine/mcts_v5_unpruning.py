"""Obligation-reserved progressive unpruning for MCTS Search V5."""

from __future__ import annotations

from dataclasses import dataclass

from mcts_unpruning import ADMINISTRATIVE_ACTIONS, progressive_exposure_count


UNPRUNING_FORMAT = "varde-mcts-v5-obligation-reserved-unpruning"
UNPRUNING_VERSION = 1


def _matches_obligation(item, obligation):
    action = item.action
    family = obligation["family"]
    parameters = obligation.get("parameters", {})
    if family == "capture":
        return (
            action.kind in ("play", "extend")
            and any(item.state.game.last_capture_waves)
        )
    if family == "defense":
        return (
            action.kind in ("play", "extend")
            and action.point == tuple(parameters["liberty"])
        )
    if family == "rescue":
        return action.kind == "extend"
    if family == "fence":
        return (
            action.kind in ("play", "extend")
            and action.point == tuple(parameters["completion"])
        )
    if family == "takeover":
        return action.kind == "swap"
    if family == "ending":
        return action.kind in ("resume", "accept")
    raise ValueError("unknown V5 unpruning obligation")


@dataclass(frozen=True)
class ReservedExposurePlan:
    ordered_actions: tuple
    administrative_actions: tuple
    obligation_actions: tuple
    proven_actions: tuple

    @property
    def mandatory_actions(self):
        mandatory = []
        for action in (
            *self.administrative_actions,
            *self.obligation_actions,
            *self.proven_actions,
        ):
            if action not in mandatory:
                mandatory.append(action)
        return tuple(mandatory)

    def base_count(self, visits):
        return progressive_exposure_count(visits, len(self.ordered_actions))

    def exposed_actions(self, visits):
        mandatory = self.mandatory_actions
        target = max(self.base_count(visits), len(mandatory))
        exposed = list(mandatory)
        for action in self.ordered_actions:
            if action not in exposed:
                exposed.append(action)
            if len(exposed) >= target:
                break
        return tuple(exposed)


def build_reserved_exposure_plan(ordered, obligations, *, proven_actions=()):
    """Freeze mandatory membership using rule order and semantic seeded ties."""
    ordered = tuple(ordered)
    ordered_actions = tuple(item.action for item in ordered)
    administrative = tuple(
        item.action for item in ordered
        if item.action.kind in ADMINISTRATIVE_ACTIONS
    )
    reserved = []
    for obligation in obligations:
        candidate = next(
            (item.action for item in ordered if _matches_obligation(item, obligation)),
            None,
        )
        if candidate is not None and candidate not in reserved:
            reserved.append(candidate)
    proven = tuple(
        action for action in ordered_actions if action in set(proven_actions)
    )
    return ReservedExposurePlan(
        ordered_actions,
        administrative,
        tuple(reserved),
        proven,
    )


def next_reserved_exposure_visit(plan, visits):
    current = plan.exposed_actions(visits)
    if len(current) >= len(plan.ordered_actions):
        return None
    candidate = visits + 1
    while plan.exposed_actions(candidate) == current:
        candidate += 1
    return candidate
