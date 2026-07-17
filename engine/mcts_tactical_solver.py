"""Bounded exact local-obligation solver for research-only MCTS recipes.

This module returns three-valued facts, never a heuristic score.  ``proven``
always means proven only for the declared local obligation and horizon.
Reaching the node limit or obligation horizon returns ``unknown``.
"""

from __future__ import annotations

from dataclasses import dataclass
import json

from actions import RulesAction, apply_action, legal_actions, legal_transitions
from varde import GJERDE_RULESETS, control, groups_of, other


SOLVER_FORMAT = "varde-mcts-certified-local-solver"
SOLVER_VERSION = 1
DEFAULT_NODE_LIMIT = 10_000
STATUSES = frozenset(("proven", "disproven", "unknown"))


def _action_id(action):
    if action.point is None:
        return action.kind
    return f"{action.kind}:{action.point[0]},{action.point[1]}"


def _obligation_key(obligation):
    return json.dumps(obligation, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class SolverResult:
    obligation: dict
    action_statuses: tuple[tuple[RulesAction, str], ...]
    override_action: RulesAction | None
    nodes: int
    cache_hits: int
    node_limit: int
    limit_reached: bool

    @property
    def status(self):
        return "override" if self.override_action is not None else "abstain"

    def to_dict(self):
        return {
            "format": SOLVER_FORMAT,
            "version": SOLVER_VERSION,
            "status": self.status,
            "obligation": self.obligation,
            "action_statuses": {
                _action_id(action): status
                for action, status in self.action_statuses
            },
            "override_action": (
                self.override_action.to_dict()
                if self.override_action is not None else None
            ),
            "nodes": self.nodes,
            "cache_hits": self.cache_hits,
            "node_limit": self.node_limit,
            "limit_reached": self.limit_reached,
            "claim_limit": (
                "bounded local obligation only; not a game-theoretic result"
            ),
        }


@dataclass(frozen=True)
class TacticalScan:
    result: SolverResult | None
    obligations_checked: int
    nodes: int
    cache_hits: int

    @property
    def override_action(self):
        return self.result.override_action if self.result else None

    @property
    def status(self):
        if self.result is None:
            return "no-obligation"
        return self.result.status


class _Solver:
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

    def advance(self, state, action):
        if self.exhausted:
            return None
        self.nodes += 1
        return apply_action(state, action)

    def classify(self, state, action, obligation):
        horizon = obligation.get("horizon", 0)
        key = (
            state.key(),
            _obligation_key(obligation),
            horizon,
            action,
        )
        if key in self.memo:
            self.cache_hits += 1
            return self.memo[key]
        category = obligation.get("category")
        methods = {
            "capture": self.capture,
            "defense": self.defense,
            "rescue": self.rescue,
            "fence": self.fence,
            "takeover": self.takeover,
            "ending": self.ending,
        }
        if category not in methods:
            raise ValueError("unknown tactical obligation")
        status = methods[category](state, action, obligation)
        if status not in STATUSES:
            raise AssertionError("solver returned an invalid status")
        self.memo[key] = status
        return status

    def capture(self, state, action, obligation):
        del obligation
        if action.kind not in ("play", "extend"):
            return "disproven"
        advanced = self.advance(state, action)
        if advanced is None:
            return "unknown"
        captured = sum(len(wave) for wave in advanced.game.last_capture_waves)
        actor = state.actor_color
        if captured < 1 or control(advanced.game.state, action.point) != actor:
            return "disproven"
        for reply in legal_actions(advanced):
            replied = self.advance(advanced, reply)
            if replied is None:
                return "unknown"
            if control(replied.game.state, action.point) != actor:
                return "disproven"
        return "proven"

    def defense(self, state, action, obligation):
        anchor = tuple(obligation["anchor"])
        liberty = tuple(obligation["liberty"])
        if action.kind not in ("play", "extend") or action.point != liberty:
            return "disproven"
        actor = state.actor_color
        advanced = self.advance(state, action)
        if advanced is None:
            return "unknown"
        if control(advanced.game.state, anchor) != actor:
            return "disproven"
        for reply in legal_actions(advanced):
            replied = self.advance(advanced, reply)
            if replied is None:
                return "unknown"
            if control(replied.game.state, anchor) != actor:
                return "disproven"
        return "proven"

    def _can_close_rescue(self, state, actor, anchor, horizon, obligation_key):
        key = (state.key(), obligation_key, horizon, "rescue-closure")
        if key in self.memo:
            self.cache_hits += 1
            return self.memo[key]
        if horizon < 0 or self.exhausted:
            return None
        actions = legal_actions(state)
        finish = next(
            (item for item in actions if item.kind == "finish-extension"),
            None,
        )
        if finish is not None:
            closed = self.advance(state, finish)
            if closed is None:
                return None
            if control(closed.game.state, anchor) == actor:
                self.memo[key] = True
                return True
        if horizon == 0:
            self.memo[key] = None
            return None
        saw_unknown = False
        for action in actions:
            if action.kind != "extend":
                continue
            advanced = self.advance(state, action)
            if advanced is None:
                return None
            outcome = self._can_close_rescue(
                advanced,
                actor,
                anchor,
                horizon - 1,
                obligation_key,
            )
            if outcome is True:
                self.memo[key] = True
                return True
            saw_unknown = saw_unknown or outcome is None
        self.memo[key] = None if saw_unknown else False
        return self.memo[key]

    def rescue(self, state, action, obligation):
        if action.kind != "extend":
            return "disproven"
        actor = state.actor_color
        anchor = tuple(obligation["anchor"])
        advanced = self.advance(state, action)
        if advanced is None:
            return "unknown"
        outcome = self._can_close_rescue(
            advanced,
            actor,
            anchor,
            obligation["horizon"] - 1,
            _obligation_key(obligation),
        )
        if outcome is True:
            return "proven"
        if outcome is False:
            return "disproven"
        return "unknown"

    @staticmethod
    def _fence_owner(game, cell):
        owners = {
            control(game.state, point) for point in game.board.cell_edges[cell]
        }
        return next(iter(owners)) if len(owners) == 1 else None

    def fence(self, state, action, obligation):
        cell = tuple(obligation["cell"])
        actor = state.actor_color
        advanced = self.advance(state, action)
        if advanced is None:
            return "unknown"
        if self._fence_owner(advanced.game, cell) != actor:
            return "disproven"
        for reply in legal_actions(advanced):
            replied = self.advance(advanced, reply)
            if replied is None:
                return "unknown"
            if self._fence_owner(replied.game, cell) != actor:
                return "disproven"
        return "proven"

    def takeover(self, state, action, obligation):
        del obligation
        root_seat = state.actor_seat
        advanced = self.advance(state, action)
        if advanced is None:
            return "unknown"
        color = advanced.color_for_seat(root_seat)
        score = advanced.game.score()
        margin = score[color] - score[other(color)]
        if margin > 0:
            return "proven"
        if margin < 0:
            return "disproven"
        return "unknown"

    def ending(self, state, action, obligation):
        del obligation
        if self.exhausted:
            return "unknown"
        self.nodes += 1
        actor = state.actor_color
        score = state.game.score()
        margin = score[actor] - score[other(actor)]
        if margin < 0:
            if action.kind == "resume":
                return "proven"
            if action.kind == "accept":
                return "disproven"
        elif margin > 0:
            if action.kind == "accept":
                return "proven"
            if action.kind == "resume":
                return "disproven"
        return "unknown"


def solve_local_obligation(state, obligation, *, node_limit=DEFAULT_NODE_LIMIT):
    """Classify every legal root action for one explicit local obligation."""
    before = state.key()
    solver = _Solver(node_limit)
    statuses = tuple(
        (action, solver.classify(state, action, obligation))
        for action in legal_actions(state)
    )
    proven = [action for action, status in statuses if status == "proven"]
    override = None
    if len(proven) == 1 and all(
        status == "disproven"
        for action, status in statuses
        if action != proven[0]
    ):
        override = proven[0]
    if state.key() != before:
        raise AssertionError("local tactical solver mutated the analyzed state")
    return SolverResult(
        obligation=dict(obligation),
        action_statuses=statuses,
        override_action=override,
        nodes=solver.nodes,
        cache_hits=solver.cache_hits,
        node_limit=node_limit,
        limit_reached=solver.exhausted,
    )


def _threatened_obligations(state):
    actor = state.actor_color
    obligations = []
    for component in groups_of(state.game.board, state.game.state, actor):
        liberties = {
            neighbor
            for point in component
            for neighbor in state.game.board.neighbors[point]
            if not state.game.state[neighbor]
        }
        if len(liberties) == 1:
            obligations.append({
                "category": "defense",
                "scope": (
                    "threatened friendly group survives every immediate reply"
                ),
                "horizon": 1,
                "anchor": list(min(component)),
                "liberty": list(next(iter(liberties))),
            })
    return obligations


def _rescue_obligations(state):
    return [
        {
            **obligation,
            "category": "rescue",
            "scope": "rescue reaches extension-turn closure with target alive",
            "horizon": 4,
        }
        for obligation in _threatened_obligations(state)
    ]


def _fence_obligations(state):
    if state.game.rules not in GJERDE_RULESETS:
        return []
    actor = state.actor_color
    obligations = []
    for cell in state.game.board.cells:
        edges = state.game.board.cell_edges[cell]
        own = sum(control(state.game.state, point) == actor for point in edges)
        empty = sum(not state.game.state[point] for point in edges)
        if own == len(edges) - 1 and empty == 1:
            obligations.append({
                "category": "fence",
                "scope": (
                    "completed fence remains complete through every "
                    "immediate reply"
                ),
                "horizon": 1,
                "cell": list(cell),
            })
    return obligations


def _has_capture(state):
    for action, advanced in legal_transitions(state):
        if action.kind in ("play", "extend") and any(
            advanced.game.last_capture_waves
        ):
            return True
    return False


def _detected_obligations(state):
    if state.game.finished:
        return ({
            "category": "ending",
            "scope": (
                "seat accepts a lead or uses its one legal resumption while "
                "behind"
            ),
            "horizon": 0,
        },)
    if state.game.swap_available:
        return ({
            "category": "takeover",
            "scope": (
                "original seat owns the strictly leading color after choice"
            ),
            "horizon": 0,
        },)
    actions = legal_actions(state)
    if any(action.kind == "extend" for action in actions):
        return tuple(_rescue_obligations(state))
    capture = ({
            "category": "capture",
            "scope": "capture remains safe through every immediate reply",
            "horizon": 1,
        },) if _has_capture(state) else ()
    threatened = _threatened_obligations(state)
    fences = _fence_obligations(state)
    if state.game.rules in GJERDE_RULESETS:
        return tuple((*fences, *capture, *threatened))
    return tuple((*capture, *threatened))


def find_tactical_override(state, *, node_limit=DEFAULT_NODE_LIMIT):
    """Detect the highest-priority urgent fact and solve it exactly or abstain."""
    before = state.key()
    total_nodes = 0
    total_cache_hits = 0
    checked = 0
    last_result = None
    for obligation in _detected_obligations(state):
        remaining = node_limit - total_nodes
        if remaining <= 0:
            break
        result = solve_local_obligation(
            state,
            obligation,
            node_limit=remaining,
        )
        checked += 1
        total_nodes += result.nodes
        total_cache_hits += result.cache_hits
        last_result = result
        if result.override_action is not None:
            break
    if state.key() != before:
        raise AssertionError("tactical scan mutated the analyzed state")
    return TacticalScan(last_result, checked, total_nodes, total_cache_hits)
