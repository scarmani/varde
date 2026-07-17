"""Corrected set-valued root proof guidance for MCTS Search V5.

This implementation is independent of the research oracle.  It consumes the
frozen declarative obligation schema but imports no corpus, certificate, or
oracle implementation.  Every result is three-valued and bounded; no local
proof is a game-theoretic value.
"""

from __future__ import annotations

from dataclasses import dataclass
import json

from actions import RulesAction, legal_actions, legal_transitions
from varde import GJERDE_RULESETS, control, groups_of, other


SOLVER_FORMAT = "varde-mcts-v5-root-proof-guidance"
SOLVER_VERSION = 1
DEFAULT_NODE_LIMIT = 10_000
STATUSES = frozenset(("proven", "disproven", "unknown"))


def action_id(action):
    if action.point is None:
        return action.kind
    return f"{action.kind}:{action.point[0]},{action.point[1]}"


def _point(value):
    return tuple(value) if value is not None else None


def _obligation_key(obligation):
    return json.dumps(obligation, sort_keys=True, separators=(",", ":"))


def _fence_owner(state, cell):
    owners = {
        control(state.game.state, point)
        for point in state.game.board.cell_edges[tuple(cell)]
    }
    return next(iter(owners)) if len(owners) == 1 else None


@dataclass(frozen=True)
class ProofResult:
    obligation: dict
    action_statuses: tuple[tuple[RulesAction, str], ...]
    proven_actions: tuple[RulesAction, ...]
    unknown_actions: tuple[RulesAction, ...]
    disproven_actions: tuple[RulesAction, ...]
    nodes: int
    cache_hits: int
    node_limit: int
    limit_reached: bool

    def to_dict(self):
        return {
            "format": SOLVER_FORMAT,
            "version": SOLVER_VERSION,
            "obligation": self.obligation,
            "action_statuses": {
                action_id(action): status
                for action, status in self.action_statuses
            },
            "proven_actions": [action_id(item) for item in self.proven_actions],
            "unknown_actions": [action_id(item) for item in self.unknown_actions],
            "disproven_actions": [
                action_id(item) for item in self.disproven_actions
            ],
            "nodes": self.nodes,
            "cache_hits": self.cache_hits,
            "node_limit": self.node_limit,
            "limit_reached": self.limit_reached,
            "claim_limit": (
                "declared local obligation and horizon only; "
                "not a game-theoretic result"
            ),
        }


@dataclass(frozen=True)
class RootProofScan:
    obligations: tuple[dict, ...]
    results: tuple[ProofResult, ...]
    action_statuses: tuple[tuple[RulesAction, str], ...]
    proven_actions: tuple[RulesAction, ...]
    unknown_actions: tuple[RulesAction, ...]
    disproven_actions: tuple[RulesAction, ...]
    nodes: int
    cache_hits: int
    root_scans: int = 1

    @property
    def status(self):
        if not self.obligations:
            return "no-obligation"
        if self.proven_actions:
            return "guided"
        return "abstain"

    def status_for(self, action):
        return dict(self.action_statuses)[action]

    def bias_for(self, action, visits):
        status = self.status_for(action)
        coefficient = 1 if status == "proven" else -1 if status == "disproven" else 0
        return coefficient / (1 + visits)


class _Budget:
    def __init__(self, node_limit):
        if (
            isinstance(node_limit, bool)
            or not isinstance(node_limit, int)
            or node_limit < 1
        ):
            raise ValueError("solver node limit must be a positive integer")
        self.node_limit = node_limit
        self.nodes = 0
        self.cache_hits = 0
        self.memo = {}

    @property
    def exhausted(self):
        return self.nodes >= self.node_limit

    def count(self):
        if self.exhausted:
            return False
        self.nodes += 1
        return True


def _capture_status(root, action, advanced, obligation, budget):
    del obligation
    if not budget.count():
        return "unknown"
    if action.kind not in ("play", "extend"):
        return "disproven"
    captured = sum(len(wave) for wave in advanced.game.last_capture_waves)
    actor = root.actor_color
    if captured < 1 or control(advanced.game.state, action.point) != actor:
        return "disproven"
    for _reply, replied in legal_transitions(advanced):
        if not budget.count():
            return "unknown"
        if control(replied.game.state, action.point) != actor:
            return "disproven"
    return "proven"


def _group_and_liberties(state, anchor):
    component = next(
        (
            component
            for component in groups_of(
                state.game.board,
                state.game.state,
                state.actor_color,
            )
            if anchor in component
        ),
        (),
    )
    liberties = {
        neighbor
        for point in component
        for neighbor in state.game.board.neighbors[point]
        if not state.game.state[neighbor]
    }
    return component, liberties


def _defense_status(root, action, advanced, obligation, budget):
    if not budget.count():
        return "unknown"
    parameters = obligation["parameters"]
    anchor = _point(parameters["anchor"])
    liberty = _point(parameters["liberty"])
    _component, liberties = _group_and_liberties(root, anchor)
    if (
        action.kind not in ("play", "extend")
        or action.point != liberty
        or liberties != {liberty}
    ):
        return "disproven"
    actor = root.actor_color
    if control(advanced.game.state, anchor) != actor:
        return "disproven"
    for _reply, replied in legal_transitions(advanced):
        if not budget.count():
            return "unknown"
        if control(replied.game.state, anchor) != actor:
            return "disproven"
    return "proven"


def _rescue_closure(state, actor_seat, actor_color, anchor, remaining, budget):
    key = (state.key(), actor_seat, actor_color, anchor, remaining)
    if key in budget.memo:
        budget.cache_hits += 1
        return budget.memo[key]

    # Closure is evaluated before any recursion.  An automatic Breath-run
    # finish changes the actor during the extension transition itself.
    if state.actor_seat != actor_seat:
        outcome = control(state.game.state, anchor) == actor_color
        budget.memo[key] = outcome
        return outcome
    if remaining <= 0:
        budget.memo[key] = None
        return None

    transitions = tuple(
        (action, advanced)
        for action, advanced in legal_transitions(state)
        if action.kind in ("extend", "finish-extension")
    )
    if not transitions:
        budget.memo[key] = False
        return False
    saw_unknown = False
    for _action, advanced in transitions:
        if not budget.count():
            saw_unknown = True
            continue
        outcome = _rescue_closure(
            advanced,
            actor_seat,
            actor_color,
            anchor,
            remaining - 1,
            budget,
        )
        if outcome is True:
            budget.memo[key] = True
            return True
        saw_unknown = saw_unknown or outcome is None
    budget.memo[key] = None if saw_unknown else False
    return budget.memo[key]


def _rescue_status(root, action, advanced, obligation, budget):
    if not budget.count():
        return "unknown"
    if action.kind != "extend":
        return "disproven"
    anchor = _point(obligation["parameters"]["anchor"])
    result = _rescue_closure(
        advanced,
        root.actor_seat,
        root.actor_color,
        anchor,
        len(obligation["quantifier_schedule"]),
        budget,
    )
    return "proven" if result is True else "disproven" if result is False else "unknown"


def _fence_status(root, action, advanced, obligation, budget):
    if not budget.count():
        return "unknown"
    parameters = obligation["parameters"]
    cell = _point(parameters["cell"])
    completion = _point(parameters["completion"])
    actor = root.actor_color
    if (
        action.kind not in ("play", "extend")
        or action.point != completion
        or _fence_owner(advanced, cell) != actor
    ):
        return "disproven"
    durable = bool(obligation["quantifier_schedule"])
    if not durable:
        return "proven"
    for _reply, replied in legal_transitions(advanced):
        if not budget.count():
            return "unknown"
        if _fence_owner(replied, cell) != actor:
            return "disproven"
    return "proven"


def _takeover_status(root, action, advanced, obligation, budget):
    del obligation
    if not budget.count():
        return "unknown"
    if action.kind not in ("swap", "play", "pass"):
        return "disproven"
    color = advanced.color_for_seat(root.actor_seat)
    score = advanced.game.score()
    margin = score[color] - score[other(color)]
    return "proven" if margin > 0 else "disproven" if margin < 0 else "unknown"


def _ending_status(root, action, advanced, obligation, budget):
    del advanced, obligation
    if not budget.count():
        return "unknown"
    score = root.game.score()
    actor = root.actor_color
    margin = score[actor] - score[other(actor)]
    if margin > 0:
        return "proven" if action.kind == "accept" else "disproven"
    if margin < 0:
        return "proven" if action.kind == "resume" else "disproven"
    return "unknown"


_CLASSIFIERS = {
    "capture": _capture_status,
    "defense": _defense_status,
    "rescue": _rescue_status,
    "fence": _fence_status,
    "takeover": _takeover_status,
    "ending": _ending_status,
}


def solve_root_obligation(
    state,
    obligation,
    *,
    transitions=None,
    node_limit=DEFAULT_NODE_LIMIT,
):
    """Classify all root actions without importing the independent oracle."""
    before = state.key()
    transitions = (
        tuple(legal_transitions(state))
        if transitions is None else tuple(transitions)
    )
    transition_actions = tuple(action for action, _advanced in transitions)
    legal = legal_actions(state)
    if len(transition_actions) != len(legal) or set(transition_actions) != set(legal):
        raise ValueError("root transitions do not match the legal action set")
    family = obligation.get("family")
    if family not in _CLASSIFIERS:
        raise ValueError("unknown V5 proof obligation")
    budget = _Budget(node_limit)
    statuses = tuple(
        (
            action,
            _CLASSIFIERS[family](state, action, advanced, obligation, budget),
        )
        for action, advanced in transitions
    )
    if any(status not in STATUSES for _action, status in statuses):
        raise AssertionError("V5 solver returned an invalid status")
    if state.key() != before:
        raise AssertionError("V5 root solver mutated the analyzed state")
    return ProofResult(
        dict(obligation),
        statuses,
        tuple(action for action, status in statuses if status == "proven"),
        tuple(action for action, status in statuses if status == "unknown"),
        tuple(action for action, status in statuses if status == "disproven"),
        budget.nodes,
        budget.cache_hits,
        node_limit,
        budget.exhausted,
    )


def _goal(
    family,
    scope,
    root_predicate,
    state_predicate,
    *,
    success_mode="leaf",
    schedule=(),
    parameters=None,
):
    return {
        "family": family,
        "scope": scope,
        "root_predicate": root_predicate,
        "state_predicate": state_predicate,
        "success_mode": success_mode,
        "quantifier_schedule": [dict(step) for step in schedule],
        "parameters": dict(parameters or {}),
    }


def _threatened(state):
    obligations = []
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
            obligations.append((min(component), next(iter(liberties))))
    return tuple(obligations)


def detect_root_obligations(state, transitions=None):
    """Detect urgent facts once; this is not part of the independent oracle."""
    transitions = (
        tuple(legal_transitions(state))
        if transitions is None else tuple(transitions)
    )
    if state.game.finished:
        return (_goal(
            "ending",
            "accept a strict lead or resume while behind",
            "ending-choice",
            "ending-choice-rational",
        ),)
    if state.game.swap_available:
        return (_goal(
            "takeover",
            "original acting seat owns the strictly leading color",
            "takeover-choice",
            "root-seat-leading",
        ),)

    actions = tuple(action for action, _advanced in transitions)
    threatened = _threatened(state)
    if any(action.kind == "extend" for action in actions):
        step = {
            "quantifier": "exists",
            "actor": "root-seat",
            "action_kinds": ["extend", "finish-extension"],
        }
        return tuple(
            _goal(
                "rescue",
                "extension chain closes with target controlled",
                "rescue-extension",
                "rescue-closed-alive",
                success_mode="closure",
                schedule=(step, step, step, step),
                parameters={"anchor": list(anchor)},
            )
            for anchor, _liberty in threatened
        )

    obligations = []
    if any(
        action.kind in ("play", "extend")
        and any(advanced.game.last_capture_waves)
        for action, advanced in transitions
    ):
        obligations.append(_goal(
            "capture",
            "immediate capture remains controlled through every reply",
            "immediate-capture",
            "action-point-controlled",
            schedule=({"quantifier": "forall", "actor": "any"},),
        ))
    for anchor, liberty in threatened:
        obligations.append(_goal(
            "defense",
            "specified sole-liberty group survives every reply",
            "specified-defense",
            "anchor-controlled",
            schedule=({"quantifier": "forall", "actor": "any"},),
            parameters={"anchor": list(anchor), "liberty": list(liberty)},
        ))
    if state.game.rules in GJERDE_RULESETS:
        actor = state.actor_color
        for cell in state.game.board.cells:
            edges = state.game.board.cell_edges[cell]
            own = sum(control(state.game.state, point) == actor for point in edges)
            empty = [point for point in edges if not state.game.state[point]]
            if own == len(edges) - 1 and len(empty) == 1:
                durable = state.game.rules == "gjerde"
                obligations.append(_goal(
                    "fence",
                    (
                        "specified fence remains owned through every reply"
                        if durable else "specified fence is owned immediately"
                    ),
                    "specified-fence-completion",
                    "fence-owned",
                    schedule=(
                        ({"quantifier": "forall", "actor": "any"},)
                        if durable else ()
                    ),
                    parameters={
                        "cell": list(cell),
                        "completion": list(empty[0]),
                    },
                ))
    return tuple(obligations)


def scan_root_guidance(
    state,
    *,
    transitions=None,
    obligations=None,
    node_limit=DEFAULT_NODE_LIMIT,
):
    """Perform exactly one bounded root scan and aggregate all obligations."""
    before = state.key()
    transitions = (
        tuple(legal_transitions(state))
        if transitions is None else tuple(transitions)
    )
    actions = tuple(action for action, _advanced in transitions)
    obligations = (
        detect_root_obligations(state, transitions)
        if obligations is None else tuple(obligations)
    )
    results = []
    remaining = node_limit
    for obligation in obligations:
        if remaining <= 0:
            break
        result = solve_root_obligation(
            state,
            obligation,
            transitions=transitions,
            node_limit=remaining,
        )
        results.append(result)
        remaining -= result.nodes

    by_action = {}
    for action in actions:
        statuses = [dict(result.action_statuses)[action] for result in results]
        by_action[action] = (
            "proven" if "proven" in statuses
            else "disproven" if statuses and all(
                status == "disproven" for status in statuses
            )
            else "unknown"
        )
    if state.key() != before:
        raise AssertionError("V5 proof scan mutated the analyzed state")
    statuses = tuple((action, by_action[action]) for action in actions)
    return RootProofScan(
        tuple(obligations),
        tuple(results),
        statuses,
        tuple(action for action, status in statuses if status == "proven"),
        tuple(action for action, status in statuses if status == "unknown"),
        tuple(action for action, status in statuses if status == "disproven"),
        sum(result.nodes for result in results),
        sum(result.cache_hits for result in results),
    )
