"""Seeded ruleset-neutral UCT using terminal game score only."""

from dataclasses import dataclass
import hashlib
import json
import math
import random

from actions import RulesAction, RulesState, apply_action, legal_actions
from varde import BLACK, WHITE, control


MCTS_FORMAT = "varde-terminal-mcts"
MCTS_VERSION = 2
ROLLOUT_POLICIES = frozenset(("uniform", "epsilon-greedy"))
EXPLORATION = math.sqrt(2.0)
ROLLOUT_EPSILON = 0.15
LIGHT_LATE_PASS_RATE = 0.35
MCTS_AGENT_HASH = hashlib.sha256(
    json.dumps(
        {
            "format": MCTS_FORMAT,
            "version": MCTS_VERSION,
            "exploration": EXPLORATION,
            "epsilon": ROLLOUT_EPSILON,
            "late_pass_rate": LIGHT_LATE_PASS_RATE,
            "terminal": "game-score-win-draw-loss",
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
).hexdigest()


@dataclass(frozen=True)
class MCTSDecision:
    action: RulesAction
    simulations: int
    nodes: int
    mean_value: float
    rollout_policy: str
    seed: int
    average_rollout_actions: float
    max_rollout_actions: int
    root_actions: tuple = ()
    selection_reason: str | None = None

    def to_dict(self):
        payload = {
            **self.action.to_dict(),
            "simulations": self.simulations,
            "nodes": self.nodes,
            "mean_value": round(self.mean_value, 6),
            "rollout_policy": self.rollout_policy,
            "seed": self.seed,
            "average_rollout_actions": round(self.average_rollout_actions, 3),
            "max_rollout_actions": self.max_rollout_actions,
            "agent_hash": MCTS_AGENT_HASH,
        }
        if self.root_actions:
            payload["root_action_telemetry"] = [
                dict(item) for item in self.root_actions
            ]
            payload["selection_reason"] = self.selection_reason
        return payload


@dataclass(frozen=True)
class _TerminalSample:
    reward: float
    margin: int | float
    outcome: str


class _Node:
    __slots__ = (
        "state",
        "parent",
        "action",
        "children",
        "untried",
        "visits",
        "value_sum",
        "wins",
        "draws",
        "losses",
        "margin_sum",
        "margin_min",
        "margin_max",
    )

    def __init__(self, state, parent=None, action=None):
        self.state = state
        self.parent = parent
        self.action = action
        self.children = []
        self.untried = list(legal_actions(state))
        self.visits = 0
        self.value_sum = 0.0
        self.wins = 0
        self.draws = 0
        self.losses = 0
        self.margin_sum = 0
        self.margin_min = None
        self.margin_max = None

    @property
    def mean(self):
        return self.value_sum / self.visits if self.visits else 0.5

    def record(self, sample):
        self.visits += 1
        self.value_sum += sample.reward
        if sample.outcome == "win":
            self.wins += 1
        elif sample.outcome == "draw":
            self.draws += 1
        else:
            self.losses += 1
        self.margin_sum += sample.margin
        self.margin_min = (
            sample.margin
            if self.margin_min is None
            else min(self.margin_min, sample.margin)
        )
        self.margin_max = (
            sample.margin
            if self.margin_max is None
            else max(self.margin_max, sample.margin)
        )


def _seed_for_position(seed, state):
    digest = hashlib.sha256(f"{seed}|{state.key()!r}".encode()).digest()
    return int.from_bytes(digest[:8], "big")


def _terminal_sample(state, root_seat):
    if not state.terminal:
        raise ValueError("MCTS rewards require an accepted terminal score")
    color = state.color_for_seat(root_seat)
    other_color = WHITE if color == BLACK else BLACK
    score = state.game.score()
    margin = score[color] - score[other_color]
    if margin > 0:
        return _TerminalSample(1.0, margin, "win")
    if margin < 0:
        return _TerminalSample(0.0, margin, "loss")
    return _TerminalSample(0.5, margin, "draw")


def _terminal_reward(state, root_seat):
    """Compatibility helper for the original terminal W/D/L value."""
    return _terminal_sample(state, root_seat).reward


def _uniform_action(state, rng):
    actions = legal_actions(state)
    return actions[rng.randrange(len(actions))]


def _light_action(state, rng):
    actions = legal_actions(state)
    if state.game.finished:
        resume = next((action for action in actions if action.kind == "resume"), None)
        if resume is not None:
            color = state.actor_color
            score = state.game.score()
            if score[color] < score[WHITE if color == BLACK else BLACK]:
                return resume
        return next(action for action in actions if action.kind == "accept")

    pass_action = next(
        (action for action in actions if action.kind == "pass"), None
    )
    if pass_action is not None and state.game.moves_played >= len(state.game.board.points):
        # A light policy treats a late opponent pass as an invitation to score,
        # and otherwise samples a legal late pass. This is policy behavior, not
        # a cutoff: every rollout still reaches and backs up the real score.
        if state.game.consecutive_passes or rng.random() < LIGHT_LATE_PASS_RATE:
            return pass_action

    extensions = [action for action in actions if action.kind == "extend"]
    if extensions:
        return extensions[rng.randrange(len(extensions))]
    finish = next(
        (action for action in actions if action.kind == "finish-extension"), None
    )
    if finish is not None:
        return finish

    placements = []
    for action in actions:
        if action.kind != "play":
            continue
        enemy = WHITE if state.game.to_move == BLACK else BLACK
        contact = sum(
            control(state.game.state, neighbor) == enemy
            for neighbor in state.game.board.neighbors[action.point]
        )
        cover = bool(state.game.state[action.point])
        placements.append((contact + cover, action))
    if placements:
        best = max(score for score, _action in placements)
        choices = [action for score, action in placements if score == best]
        return choices[rng.randrange(len(choices))]
    return _uniform_action(state, rng)


def _rollout_action(state, policy, rng):
    if policy == "uniform" or rng.random() < ROLLOUT_EPSILON:
        return _uniform_action(state, rng)
    return _light_action(state, rng)


def _rollout(state, root_seat, policy, rng):
    rollout = state.clone()
    actions_played = 0
    while not rollout.terminal:
        action = _rollout_action(rollout, policy, rng)
        apply_action(rollout, action, copy=False, validate=False)
        actions_played += 1
    return _terminal_sample(rollout, root_seat), actions_played


def _select_child(node, root_seat):
    maximizing = node.state.actor_seat == root_seat
    log_parent = math.log(max(1, node.visits))

    def score(child):
        exploitation = child.mean if maximizing else 1.0 - child.mean
        exploration = EXPLORATION * math.sqrt(log_parent / child.visits)
        return (
            exploitation + exploration,
            -child.action.sort_key()[0],
            child.action.point or (),
        )

    return max(node.children, key=score)


def _final_selection_key(child):
    return (
        child.visits,
        child.mean,
        -child.action.sort_key()[0],
        child.action.point or (),
    )


def _action_identity(action):
    if action.point is None:
        return action.kind
    return f"{action.kind}:{action.point[0]},{action.point[1]}"


def _selection_reason(root, selected):
    most_visits = max(child.visits for child in root.children)
    visit_leaders = [
        child for child in root.children if child.visits == most_visits
    ]
    if len(visit_leaders) == 1:
        return "most-visits"
    best_mean = max(child.mean for child in visit_leaders)
    mean_leaders = [
        child for child in visit_leaders if child.mean == best_mean
    ]
    if len(mean_leaders) == 1:
        return "mean-value"
    if selected not in mean_leaders:
        raise AssertionError("selected root action is outside the final tie")
    return "legacy-action-order"


def _root_action_telemetry(root, selected):
    children = {child.action: child for child in root.children}
    actions = [*children, *root.untried]

    def rank_key(action):
        child = children.get(action)
        if child is None:
            return (0, 0.5, -action.sort_key()[0], action.point or ())
        return _final_selection_key(child)

    ranked = sorted(actions, key=rank_key, reverse=True)
    records = []
    for rank, action in enumerate(ranked, start=1):
        child = children.get(action)
        visits = child.visits if child is not None else 0
        margin_sum = child.margin_sum if child is not None else 0
        records.append({
            "action": action.to_dict(),
            "action_id": _action_identity(action),
            "final_rank": rank,
            "selected": action == selected.action,
            "visits": visits,
            "value_sum": child.value_sum if child is not None else 0.0,
            "mean_value": child.mean if child is not None else 0.5,
            "wins": child.wins if child is not None else 0,
            "draws": child.draws if child is not None else 0,
            "losses": child.losses if child is not None else 0,
            "terminal_margin_count": visits,
            "terminal_margin_sum": margin_sum,
            "terminal_margin_mean": margin_sum / visits if visits else None,
            "terminal_margin_min": child.margin_min if child is not None else None,
            "terminal_margin_max": child.margin_max if child is not None else None,
        })
    return tuple(records)


def choose_mcts_state_action(
    rules_state,
    computer_color,
    *,
    simulations=250,
    seed=1,
    rollout_policy="uniform",
    include_root_telemetry=False,
):
    """Choose one legal action without mutating ``rules_state``.

    No heuristic value is backed up: every simulation runs to an accepted game
    score.  Research harnesses may watchdog whole games, but this live search
    routine introduces no move or rollout cutoff.
    """
    if isinstance(simulations, bool) or not isinstance(simulations, int) or simulations < 1:
        raise ValueError("simulations must be a positive integer")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    if rollout_policy not in ROLLOUT_POLICIES:
        raise ValueError("unknown rollout policy")
    if not isinstance(include_root_telemetry, bool):
        raise ValueError("include_root_telemetry must be a boolean")
    if computer_color not in (BLACK, WHITE):
        raise ValueError("computer color must be B or W")

    root_state = rules_state.clone()
    if root_state.actor_color != computer_color:
        raise ValueError("it is not the computer's action")
    before = rules_state.key()
    root_seat = root_state.actor_seat
    rng = random.Random(_seed_for_position(seed, root_state))
    root = _Node(root_state)
    total_rollout_actions = 0
    max_rollout_actions = 0

    for _simulation in range(simulations):
        node = root
        while not node.state.terminal and not node.untried and node.children:
            node = _select_child(node, root_seat)
        if not node.state.terminal and node.untried:
            index = rng.randrange(len(node.untried))
            action = node.untried.pop(index)
            child_state = apply_action(node.state, action, validate=False)
            child = _Node(child_state, parent=node, action=action)
            node.children.append(child)
            node = child
        sample, rollout_actions = _rollout(
            node.state, root_seat, rollout_policy, rng
        )
        total_rollout_actions += rollout_actions
        max_rollout_actions = max(max_rollout_actions, rollout_actions)
        while node is not None:
            node.record(sample)
            node = node.parent

    if rules_state.key() != before:
        raise AssertionError("MCTS mutated the analyzed rules state")
    if not root.children:
        raise ValueError("no legal MCTS action")
    selected = max(root.children, key=_final_selection_key)
    selection_reason = (
        _selection_reason(root, selected) if include_root_telemetry else None
    )
    root_actions = (
        _root_action_telemetry(root, selected) if include_root_telemetry else ()
    )
    return MCTSDecision(
        action=selected.action,
        simulations=simulations,
        nodes=1 + sum(1 for _ in _walk(root)),
        mean_value=selected.mean,
        rollout_policy=rollout_policy,
        seed=seed,
        average_rollout_actions=total_rollout_actions / simulations,
        max_rollout_actions=max_rollout_actions,
        root_actions=root_actions,
        selection_reason=selection_reason,
    )


def choose_mcts_action(
    game,
    computer_color,
    *,
    simulations=250,
    seed=1,
    rollout_policy="uniform",
    include_root_telemetry=False,
):
    """Compatibility wrapper for analyzing a plain engine game."""
    return choose_mcts_state_action(
        RulesState.from_game(game),
        computer_color,
        simulations=simulations,
        seed=seed,
        rollout_policy=rollout_policy,
        include_root_telemetry=include_root_telemetry,
    )


def _walk(root):
    stack = list(root.children)
    while stack:
        node = stack.pop()
        yield node
        stack.extend(node.children)
