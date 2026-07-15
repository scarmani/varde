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

    def to_dict(self):
        return {
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


class _Node:
    __slots__ = (
        "state",
        "parent",
        "action",
        "children",
        "untried",
        "visits",
        "value_sum",
    )

    def __init__(self, state, parent=None, action=None):
        self.state = state
        self.parent = parent
        self.action = action
        self.children = []
        self.untried = list(legal_actions(state))
        self.visits = 0
        self.value_sum = 0.0

    @property
    def mean(self):
        return self.value_sum / self.visits if self.visits else 0.5


def _seed_for_position(seed, state):
    digest = hashlib.sha256(f"{seed}|{state.key()!r}".encode()).digest()
    return int.from_bytes(digest[:8], "big")


def _terminal_reward(state, root_seat):
    if not state.terminal:
        raise ValueError("MCTS rewards require an accepted terminal score")
    color = state.color_for_seat(root_seat)
    other_color = WHITE if color == BLACK else BLACK
    score = state.game.score()
    if score[color] > score[other_color]:
        return 1.0
    if score[color] < score[other_color]:
        return 0.0
    return 0.5


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
    return _terminal_reward(rollout, root_seat), actions_played


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


def choose_mcts_state_action(
    rules_state,
    computer_color,
    *,
    simulations=250,
    seed=1,
    rollout_policy="uniform",
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
        reward, rollout_actions = _rollout(
            node.state, root_seat, rollout_policy, rng
        )
        total_rollout_actions += rollout_actions
        max_rollout_actions = max(max_rollout_actions, rollout_actions)
        while node is not None:
            node.visits += 1
            node.value_sum += reward
            node = node.parent

    if rules_state.key() != before:
        raise AssertionError("MCTS mutated the analyzed rules state")
    if not root.children:
        raise ValueError("no legal MCTS action")
    selected = max(
        root.children,
        key=lambda child: (
            child.visits,
            child.mean,
            -child.action.sort_key()[0],
            child.action.point or (),
        ),
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
    )


def choose_mcts_action(
    game,
    computer_color,
    *,
    simulations=250,
    seed=1,
    rollout_policy="uniform",
):
    """Compatibility wrapper for analyzing a plain engine game."""
    return choose_mcts_state_action(
        RulesState.from_game(game),
        computer_color,
        simulations=simulations,
        seed=seed,
        rollout_policy=rollout_policy,
    )


def _walk(root):
    stack = list(root.children)
    while stack:
        node = stack.pop()
        yield node
        stack.extend(node.children)
