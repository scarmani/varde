"""Independent bounded oracle for MCTS Search V5 tactical corpora.

The oracle is deliberately declarative.  A certificate supplies named root
and state predicates plus an explicit existential/universal ply schedule.  The
module shares only the real rules transition API with MCTS; it imports neither
the tactical solver nor search code and contains no automatic obligation
detection.  Results prove only the declared predicate within its finite
schedule.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json

from actions import RulesAction, legal_transitions
from varde import BLACK, WHITE, control, groups_of, other, signature


ORACLE_FORMAT = "varde-mcts-v5-generic-exhaustive-oracle"
ORACLE_VERSION = 1
DEFAULT_NODE_LIMIT = 10_000
STATUSES = frozenset(("proven", "disproven", "unknown"))
QUANTIFIERS = frozenset(("exists", "forall"))


def action_id(action):
    if action.point is None:
        return action.kind
    return f"{action.kind}:{action.point[0]},{action.point[1]}"


def state_hash(state):
    return hashlib.sha256(repr(state.key()).encode()).hexdigest()


def _goal_key(goal):
    return json.dumps(goal, sort_keys=True, separators=(",", ":"))


def _point(value):
    return tuple(value) if value is not None else None


def _fence_owner(state, cell):
    owners = {
        control(state.game.state, point)
        for point in state.game.board.cell_edges[tuple(cell)]
    }
    return next(iter(owners)) if len(owners) == 1 else None


def _root_predicate(name, root, action, advanced, goal, context):
    del context
    if name == "immediate-capture":
        return (
            action.kind in ("play", "extend")
            and sum(len(wave) for wave in advanced.game.last_capture_waves) > 0
        )
    if name == "specified-defense":
        anchor = _point(goal["parameters"]["anchor"])
        liberty = _point(goal["parameters"]["liberty"])
        component = next(
            (
                component
                for component in groups_of(
                    root.game.board,
                    root.game.state,
                    root.actor_color,
                )
                if anchor in component
            ),
            (),
        )
        liberties = {
            neighbor
            for point in component
            for neighbor in root.game.board.neighbors[point]
            if not root.game.state[neighbor]
        }
        return (
            action.kind in ("play", "extend")
            and action.point == liberty
            and liberties == {liberty}
        )
    if name == "rescue-extension":
        return action.kind == "extend"
    if name == "specified-fence-completion":
        return (
            action.kind in ("play", "extend")
            and action.point == _point(goal["parameters"]["completion"])
            and _fence_owner(advanced, goal["parameters"]["cell"])
            == root.actor_color
        )
    if name == "takeover-choice":
        return action.kind in ("swap", "play", "pass")
    if name == "ending-choice":
        return action.kind in ("accept", "resume")
    if name == "never-applicable":
        return False
    raise ValueError(f"unknown V5 oracle root predicate: {name}")


def _state_predicate(name, state, goal, context):
    root = context["root"]
    action = context["root_action"]
    actor = context["root_actor_color"]
    if name == "action-point-controlled":
        return control(state.game.state, action.point) == actor
    if name == "anchor-controlled":
        return control(
            state.game.state,
            _point(goal["parameters"]["anchor"]),
        ) == actor
    if name == "rescue-closed-alive":
        if state.actor_seat == context["root_actor_seat"]:
            return None
        return control(
            state.game.state,
            _point(goal["parameters"]["anchor"]),
        ) == actor
    if name == "fence-owned":
        return _fence_owner(state, goal["parameters"]["cell"]) == actor
    if name == "root-seat-leading":
        color = state.color_for_seat(context["root_actor_seat"])
        score = state.game.score()
        margin = score[color] - score[other(color)]
        return True if margin > 0 else False if margin < 0 else None
    if name == "ending-choice-rational":
        score = root.game.score()
        margin = score[actor] - score[other(actor)]
        if margin > 0:
            return True if action.kind == "accept" else False
        if margin < 0:
            return True if action.kind == "resume" else False
        return None
    raise ValueError(f"unknown V5 oracle state predicate: {name}")


@dataclass(frozen=True)
class OracleCertificate:
    goal: dict
    action_statuses: tuple[tuple[RulesAction, str], ...]
    proven_actions: tuple[RulesAction, ...]
    unknown_actions: tuple[RulesAction, ...]
    disproven_actions: tuple[RulesAction, ...]
    nodes: int
    cache_hits: int
    node_limit: int
    limit_reached: bool
    traces: tuple[tuple[str, tuple[dict, ...]], ...]

    def to_dict(self, *, include_traces=False):
        payload = {
            "format": ORACLE_FORMAT,
            "version": ORACLE_VERSION,
            "goal": self.goal,
            "action_statuses": {
                action_id(action): status
                for action, status in self.action_statuses
            },
            "proven_actions": [action_id(action) for action in self.proven_actions],
            "unknown_actions": [action_id(action) for action in self.unknown_actions],
            "disproven_actions": [
                action_id(action) for action in self.disproven_actions
            ],
            "nodes": self.nodes,
            "cache_hits": self.cache_hits,
            "node_limit": self.node_limit,
            "limit_reached": self.limit_reached,
            "claim_limit": (
                "declared local predicate and quantifier schedule only; "
                "not a game-theoretic result"
            ),
        }
        if include_traces:
            payload["traces"] = {
                action: list(records) for action, records in self.traces
            }
        return payload


class _Oracle:
    def __init__(self, node_limit):
        if (
            isinstance(node_limit, bool)
            or not isinstance(node_limit, int)
            or node_limit < 1
        ):
            raise ValueError("oracle node limit must be a positive integer")
        self.node_limit = node_limit
        self.nodes = 0
        self.cache_hits = 0
        self.memo = {}

    @property
    def exhausted(self):
        return self.nodes >= self.node_limit

    def _trace(self, state, *, ply, action=None, quantifier=None, result=None):
        return {
            "ply": ply,
            "actor_seat": state.actor_seat,
            "actor_color": state.actor_color,
            "action": action_id(action) if action is not None else None,
            "quantifier": quantifier,
            "result": result,
            "state_key_sha256": state_hash(state),
        }

    def classify(self, root, action, advanced, goal):
        trace = [self._trace(root, ply=0, action=action, quantifier="root")]
        context = {
            "root": root,
            "root_action": action,
            "root_actor_seat": root.actor_seat,
            "root_actor_color": root.actor_color,
        }
        if self.exhausted:
            trace.append(self._trace(root, ply=0, result="unknown-node-limit"))
            return "unknown", tuple(trace)
        self.nodes += 1
        if not _root_predicate(
            goal["root_predicate"], root, action, advanced, goal, context
        ):
            trace.append(self._trace(advanced, ply=1, result="disproven-root"))
            return "disproven", tuple(trace)
        status, subtrace = self._evaluate(advanced, goal, context, 0, 1)
        trace.extend(subtrace)
        return status, tuple(trace)

    def _evaluate(self, state, goal, context, schedule_index, ply):
        memo_key = (state.key(), _goal_key(goal), schedule_index)
        if memo_key in self.memo:
            self.cache_hits += 1
            status = self.memo[memo_key]
            return status, (self._trace(
                state,
                ply=ply,
                result=f"{status}-cache",
            ),)

        schedule = goal["quantifier_schedule"]
        predicate = _state_predicate(
            goal["state_predicate"], state, goal, context
        )
        if goal["success_mode"] == "closure" and predicate is not None:
            status = "proven" if predicate else "disproven"
            self.memo[memo_key] = status
            return status, (self._trace(state, ply=ply, result=status),)

        if schedule_index >= len(schedule):
            status = (
                "proven" if predicate is True
                else "disproven" if predicate is False
                else "unknown"
            )
            self.memo[memo_key] = status
            return status, (self._trace(state, ply=ply, result=status),)

        step = schedule[schedule_index]
        quantifier = step["quantifier"]
        if quantifier not in QUANTIFIERS:
            raise ValueError("invalid V5 oracle quantifier")
        if (
            step.get("actor") == "root-seat"
            and state.actor_seat != context["root_actor_seat"]
        ):
            status = "disproven" if quantifier == "exists" else "unknown"
            self.memo[memo_key] = status
            return status, (self._trace(
                state, ply=ply, quantifier=quantifier,
                result=f"{status}-actor-mismatch",
            ),)

        allowed_kinds = frozenset(step.get("action_kinds", ()))
        transitions = tuple(
            (action, advanced)
            for action, advanced in legal_transitions(state)
            if not allowed_kinds or action.kind in allowed_kinds
        )
        if not transitions:
            status = "disproven" if quantifier == "exists" else "proven"
            self.memo[memo_key] = status
            return status, (self._trace(
                state, ply=ply, quantifier=quantifier,
                result=f"{status}-empty-domain",
            ),)

        statuses = []
        trace = []
        for action, advanced in transitions:
            if self.exhausted:
                statuses.append("unknown")
                trace.append(self._trace(
                    state, ply=ply, action=action, quantifier=quantifier,
                    result="unknown-node-limit",
                ))
                continue
            self.nodes += 1
            trace.append(self._trace(
                state, ply=ply, action=action, quantifier=quantifier,
            ))
            status, child_trace = self._evaluate(
                advanced,
                goal,
                context,
                schedule_index + 1,
                ply + 1,
            )
            statuses.append(status)
            trace.extend(child_trace)
            if quantifier == "exists" and status == "proven":
                break
            if quantifier == "forall" and status == "disproven":
                break

        if quantifier == "exists":
            status = (
                "proven" if "proven" in statuses
                else "disproven" if all(item == "disproven" for item in statuses)
                else "unknown"
            )
        else:
            status = (
                "disproven" if "disproven" in statuses
                else "proven" if all(item == "proven" for item in statuses)
                else "unknown"
            )
        self.memo[memo_key] = status
        trace.append(self._trace(
            state, ply=ply, quantifier=quantifier, result=status
        ))
        return status, tuple(trace)


def certify_goal(state, goal, *, node_limit=DEFAULT_NODE_LIMIT):
    """Classify every legal root action under one declarative local goal."""
    before = state.key()
    _validate_goal(goal)
    oracle = _Oracle(node_limit)
    statuses = []
    traces = []
    for action, advanced in legal_transitions(state):
        status, trace = oracle.classify(state, action, advanced, goal)
        if status not in STATUSES:
            raise AssertionError("oracle returned an invalid status")
        statuses.append((action, status))
        traces.append((action_id(action), trace))
    if state.key() != before:
        raise AssertionError("V5 oracle mutated the analyzed position")
    return OracleCertificate(
        dict(goal),
        tuple(statuses),
        tuple(action for action, status in statuses if status == "proven"),
        tuple(action for action, status in statuses if status == "unknown"),
        tuple(action for action, status in statuses if status == "disproven"),
        oracle.nodes,
        oracle.cache_hits,
        node_limit,
        oracle.exhausted,
        tuple(traces),
    )


def _validate_goal(goal):
    required = {
        "family",
        "scope",
        "root_predicate",
        "state_predicate",
        "success_mode",
        "quantifier_schedule",
        "parameters",
    }
    if set(goal) != required:
        raise ValueError("V5 oracle goal fields differ from the frozen schema")
    if goal["success_mode"] not in ("leaf", "closure"):
        raise ValueError("invalid V5 oracle success mode")
    for step in goal["quantifier_schedule"]:
        if step.get("quantifier") not in QUANTIFIERS:
            raise ValueError("invalid V5 oracle quantifier")
        if step.get("actor", "any") not in ("any", "root-seat"):
            raise ValueError("invalid V5 oracle actor constraint")


def goal(
    family,
    scope,
    root_predicate,
    state_predicate,
    *,
    success_mode="leaf",
    quantifier_schedule=(),
    parameters=None,
):
    """Build the JSON-safe frozen goal schema used by corpus definitions."""
    return {
        "family": family,
        "scope": scope,
        "root_predicate": root_predicate,
        "state_predicate": state_predicate,
        "success_mode": success_mode,
        "quantifier_schedule": [dict(step) for step in quantifier_schedule],
        "parameters": dict(parameters or {}),
    }


def swapped_color_state(state):
    """Color-swap a fixture for exact symmetry checks without changing rules."""
    swapped = state.clone()
    swapped.game.state = {
        point: tuple(WHITE if color == BLACK else BLACK for color in stack)
        for point, stack in swapped.game.state.items()
    }
    swapped.game.to_move = other(swapped.game.to_move)
    swapped.game.history = {signature(
        swapped.game.board,
        swapped.game.state,
        swapped.game.to_move,
    )}
    return swapped
