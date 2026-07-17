"""Seeded ruleset-neutral UCT using terminal game score only."""

from dataclasses import dataclass
import hashlib
import json
import math
import random

from actions import (
    RulesAction,
    RulesState,
    apply_action,
    legal_actions,
    legal_transitions,
)
from varde import BLACK, WHITE, GJERDE_RULESETS, control, groups_of


MCTS_FORMAT = "varde-terminal-mcts"
MCTS_VERSION = 4
TACTICAL_MCTS_VERSION = 5
ROLLOUT_POLICIES = frozenset(("uniform", "epsilon-greedy"))
SEARCH_VARIANTS = frozenset(("tie-margin", "tactical-only", "combined"))
DEFAULT_SEARCH_VARIANT = "tie-margin"
EXPLORATION = math.sqrt(2.0)
ROLLOUT_EPSILON = 0.15
LIGHT_LATE_PASS_RATE = 0.35


def _agent_spec(search_variant):
    if search_variant not in SEARCH_VARIANTS:
        raise ValueError("unknown MCTS search variant")
    if search_variant == DEFAULT_SEARCH_VARIANT:
        return {
            "format": MCTS_FORMAT,
            "version": MCTS_VERSION,
            "exploration": EXPLORATION,
            "epsilon": ROLLOUT_EPSILON,
            "late_pass_rate": LIGHT_LATE_PASS_RATE,
            "terminal": "game-score-win-draw-loss",
            "terminal_margin": "secondary-normalized-by-scoreable-area",
            "ties": "sha256(seed,root-position,node-position,action)",
        }
    tactical = search_variant in ("tactical-only", "combined")
    margin = search_variant in ("tie-margin", "combined")
    return {
        "format": MCTS_FORMAT,
        "version": TACTICAL_MCTS_VERSION if tactical else MCTS_VERSION,
        "search_variant": search_variant,
        "exploration": EXPLORATION,
        "epsilon": ROLLOUT_EPSILON,
        "late_pass_rate": LIGHT_LATE_PASS_RATE,
        "terminal": "game-score-win-draw-loss",
        "terminal_margin": (
            "secondary-normalized-by-scoreable-area" if margin else "disabled"
        ),
        "tactical_guidance": (
            "single-legal-transition-set-v1" if tactical else "disabled"
        ),
        "ties": "sha256(seed,root-position,node-position,action)",
    }


def mcts_agent_hash(search_variant=DEFAULT_SEARCH_VARIANT):
    return hashlib.sha256(
        json.dumps(
            _agent_spec(search_variant),
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()


MCTS_AGENT_HASH = mcts_agent_hash()
MCTS_AGENT_HASHES = {
    variant: mcts_agent_hash(variant) for variant in sorted(SEARCH_VARIANTS)
}


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
    agent_hash: str = MCTS_AGENT_HASH
    search_variant: str = DEFAULT_SEARCH_VARIANT
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
            "agent_hash": self.agent_hash,
        }
        if self.search_variant != DEFAULT_SEARCH_VARIANT:
            payload["search_variant"] = self.search_variant
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
    normalized_margin: float
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
        "normalized_margin_sum",
        "normalized_margin_min",
        "normalized_margin_max",
        "tactical_prepared",
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
        self.normalized_margin_sum = 0.0
        self.normalized_margin_min = None
        self.normalized_margin_max = None
        self.tactical_prepared = False

    @property
    def mean(self):
        return self.value_sum / self.visits if self.visits else 0.5

    @property
    def normalized_margin_mean(self):
        return self.normalized_margin_sum / self.visits if self.visits else 0.0

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
        self.normalized_margin_sum += sample.normalized_margin
        self.normalized_margin_min = (
            sample.normalized_margin
            if self.normalized_margin_min is None
            else min(self.normalized_margin_min, sample.normalized_margin)
        )
        self.normalized_margin_max = (
            sample.normalized_margin
            if self.normalized_margin_max is None
            else max(self.normalized_margin_max, sample.normalized_margin)
        )


def _seed_for_position(seed, state):
    digest = hashlib.sha256(f"{seed}|{state.key()!r}".encode()).digest()
    return int.from_bytes(digest[:8], "big")


def _scoreable_area(game):
    if game.rules in GJERDE_RULESETS:
        return len(game.board.cells)
    return len(game.board.points)


def _terminal_sample(state, root_seat):
    if not state.terminal:
        raise ValueError("MCTS rewards require an accepted terminal score")
    color = state.color_for_seat(root_seat)
    other_color = WHITE if color == BLACK else BLACK
    score = state.game.score()
    margin = score[color] - score[other_color]
    area = _scoreable_area(state.game)
    normalized_margin = max(-1.0, min(1.0, margin / area))
    if margin > 0:
        return _TerminalSample(1.0, margin, normalized_margin, "win")
    if margin < 0:
        return _TerminalSample(0.0, margin, normalized_margin, "loss")
    return _TerminalSample(0.5, margin, normalized_margin, "draw")


def _terminal_reward(state, root_seat):
    """Compatibility helper for the original terminal W/D/L value."""
    return _terminal_sample(state, root_seat).reward


def _uniform_action(state, rng, actions=None):
    actions = legal_actions(state) if actions is None else actions
    return actions[rng.randrange(len(actions))]


def _light_action(state, rng, actions=None):
    actions = legal_actions(state) if actions is None else actions
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
    return _uniform_action(state, rng, actions)


def _rollout_action(state, policy, rng, actions=None):
    if policy == "uniform" or rng.random() < ROLLOUT_EPSILON:
        return _uniform_action(state, rng, actions)
    return _light_action(state, rng, actions)


def _sole_liberty_points(state):
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
    game = state.game
    if game.rules not in GJERDE_RULESETS or game.finished:
        return set()
    color = state.actor_color
    completions = set()
    for cell in game.board.cells:
        edges = game.board.cell_edges[cell]
        own = sum(control(game.state, point) == color for point in edges)
        empty = [point for point in edges if not game.state[point]]
        if own == len(edges) - 1 and len(empty) == 1:
            completions.add(empty[0])
    return completions


def _tactical_priorities(state, transitions):
    """Rank one generated legal-transition set by immediate rule facts."""
    if not transitions:
        return {}
    game = state.game
    actor_seat = state.actor_seat
    actions = tuple(action for action, _advanced in transitions)
    extension_available = any(action.kind == "extend" for action in actions)
    defense_points = _sole_liberty_points(state) if not game.finished else set()
    fence_points = _fence_completion_points(state)
    priorities = {}
    for action, advanced in transitions:
        if game.finished:
            score = game.score()
            color = state.actor_color
            behind = score[color] < score[WHITE if color == BLACK else BLACK]
            utility = int(
                (action.kind == "resume" and behind)
                or (action.kind == "accept" and not behind)
            )
            priorities[action] = (5, utility, 0, 0, 0)
            continue
        if game.swap_available:
            color = advanced.color_for_seat(actor_seat)
            score = advanced.game.score()
            margin = score[color] - score[WHITE if color == BLACK else BLACK]
            priorities[action] = (4, margin, 0, 0, 0)
            continue
        if extension_available or game.extension_only_turn:
            priorities[action] = (
                3,
                int(action.kind == "extend"),
                int(action.kind == "finish-extension"),
                0,
                0,
            )
            continue
        captured = (
            sum(len(wave) for wave in advanced.game.last_capture_waves)
            if action.kind in ("play", "extend") else 0
        )
        defense = int(
            action.kind in ("play", "extend")
            and action.point in defense_points
        )
        fence = int(
            action.kind == "play" and action.point in fence_points
        )
        priorities[action] = (
            int(bool(captured or defense or fence)),
            captured,
            defense,
            fence,
            0,
        )
    return priorities


def _guided_transition(state, policy, rng):
    transitions = legal_transitions(state)
    actions = tuple(action for action, _advanced in transitions)
    priorities = _tactical_priorities(state, transitions)
    best = max(priorities.values())
    if best[0] > 0:
        choices = [
            (action, advanced)
            for action, advanced in transitions
            if priorities[action] == best
        ]
        return choices[rng.randrange(len(choices))]
    action = _rollout_action(state, policy, rng, actions)
    return next(item for item in transitions if item[0] == action)


def _prepare_tactical_expansion(node, rng):
    transitions = legal_transitions(node.state)
    priorities = _tactical_priorities(node.state, transitions)
    ordered = [action for action, _advanced in transitions]
    rng.shuffle(ordered)
    ordered.sort(key=priorities.__getitem__)
    node.untried = ordered
    node.tactical_prepared = True
    action = node.untried.pop()
    advanced = next(
        advanced for candidate, advanced in transitions if candidate == action
    )
    return action, advanced


def _rollout(state, root_seat, policy, rng, tactical_guidance=False):
    rollout = state.clone()
    actions_played = 0
    while not rollout.terminal:
        if tactical_guidance:
            _action, rollout = _guided_transition(rollout, policy, rng)
        else:
            action = _rollout_action(rollout, policy, rng)
            apply_action(rollout, action, copy=False, validate=False)
        actions_played += 1
    return _terminal_sample(rollout, root_seat), actions_played


def _seeded_tie_value(seed, root_key, node_key, action):
    """Return a reproducible, direction-neutral tie value.

    The digest uses semantic action identity rather than the canonical action
    ordering. Coordinates contribute entropy but never an increasing/decreasing
    preference; changing the analyzed position or seed reshuffles every tie.
    """
    payload = repr((seed, root_key, node_key, _action_identity(action))).encode()
    return int.from_bytes(hashlib.sha256(payload).digest(), "big")


def _select_child(node, root_seat, seed, root_key, use_terminal_margin=True):
    maximizing = node.state.actor_seat == root_seat
    log_parent = math.log(max(1, node.visits))

    def score(child):
        exploitation = child.mean if maximizing else 1.0 - child.mean
        exploration = EXPLORATION * math.sqrt(log_parent / child.visits)
        primary = (
            exploitation + exploration,
        )
        if use_terminal_margin:
            primary += ((
                child.normalized_margin_mean
                if maximizing else -child.normalized_margin_mean
            ),)
        return primary + (
            _seeded_tie_value(seed, root_key, node.state.key(), child.action),
        )

    return max(node.children, key=score)


def _final_selection_key(child, seed, root_key, use_terminal_margin=True):
    primary = (
        child.visits,
        child.mean,
    )
    if use_terminal_margin:
        primary += (child.normalized_margin_mean,)
    return primary + (
        _seeded_tie_value(seed, root_key, root_key, child.action),
    )


def _action_identity(action):
    if action.point is None:
        return action.kind
    return f"{action.kind}:{action.point[0]},{action.point[1]}"


def _selection_reason(root, selected, use_terminal_margin=True):
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
    final_leaders = mean_leaders
    if use_terminal_margin:
        best_margin = max(child.normalized_margin_mean for child in mean_leaders)
        final_leaders = [
            child
            for child in mean_leaders
            if child.normalized_margin_mean == best_margin
        ]
        if len(final_leaders) == 1:
            return "terminal-margin"
    if selected not in final_leaders:
        raise AssertionError("selected root action is outside the final tie")
    return "seeded-hash"


def _root_action_telemetry(
    root,
    selected,
    seed,
    root_key,
    use_terminal_margin=True,
):
    children = {child.action: child for child in root.children}
    actions = [*children, *root.untried]

    def rank_key(action):
        child = children.get(action)
        if child is None:
            primary = (
                0,
                0.5,
            )
            if use_terminal_margin:
                primary += (0.0,)
            return primary + (
                _seeded_tie_value(seed, root_key, root_key, action),
            )
        return _final_selection_key(
            child,
            seed,
            root_key,
            use_terminal_margin,
        )

    ranked = sorted(actions, key=rank_key, reverse=True)
    records = []
    for rank, action in enumerate(ranked, start=1):
        child = children.get(action)
        visits = child.visits if child is not None else 0
        margin_sum = child.margin_sum if child is not None else 0
        normalized_margin_sum = (
            child.normalized_margin_sum if child is not None else 0.0
        )
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
            "normalized_terminal_margin_count": visits,
            "normalized_terminal_margin_sum": normalized_margin_sum,
            "normalized_terminal_margin_mean": (
                normalized_margin_sum / visits if visits else None
            ),
            "normalized_terminal_margin_min": (
                child.normalized_margin_min if child is not None else None
            ),
            "normalized_terminal_margin_max": (
                child.normalized_margin_max if child is not None else None
            ),
        })
    return tuple(records)


def choose_mcts_state_action(
    rules_state,
    computer_color,
    *,
    simulations=250,
    seed=1,
    rollout_policy="uniform",
    search_variant=DEFAULT_SEARCH_VARIANT,
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
    if search_variant not in SEARCH_VARIANTS:
        raise ValueError("unknown MCTS search variant")
    if not isinstance(include_root_telemetry, bool):
        raise ValueError("include_root_telemetry must be a boolean")
    if computer_color not in (BLACK, WHITE):
        raise ValueError("computer color must be B or W")

    root_state = rules_state.clone()
    if root_state.actor_color != computer_color:
        raise ValueError("it is not the computer's action")
    before = rules_state.key()
    root_seat = root_state.actor_seat
    root_key = root_state.key()
    use_terminal_margin = search_variant in ("tie-margin", "combined")
    tactical_guidance = search_variant in ("tactical-only", "combined")
    rng = random.Random(_seed_for_position(seed, root_state))
    root = _Node(root_state)
    total_rollout_actions = 0
    max_rollout_actions = 0

    for _simulation in range(simulations):
        node = root
        while not node.state.terminal and not node.untried and node.children:
            node = _select_child(
                node,
                root_seat,
                seed,
                root_key,
                use_terminal_margin,
            )
        if not node.state.terminal and node.untried:
            if tactical_guidance and not node.tactical_prepared:
                action, child_state = _prepare_tactical_expansion(node, rng)
            elif tactical_guidance:
                action = node.untried.pop()
                child_state = apply_action(node.state, action, validate=False)
            else:
                index = rng.randrange(len(node.untried))
                action = node.untried.pop(index)
                child_state = apply_action(node.state, action, validate=False)
            child = _Node(child_state, parent=node, action=action)
            node.children.append(child)
            node = child
        sample, rollout_actions = _rollout(
            node.state,
            root_seat,
            rollout_policy,
            rng,
            tactical_guidance,
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
    selected = max(
        root.children,
        key=lambda child: _final_selection_key(
            child,
            seed,
            root_key,
            use_terminal_margin,
        ),
    )
    selection_reason = (
        _selection_reason(root, selected, use_terminal_margin)
        if include_root_telemetry else None
    )
    root_actions = (
        _root_action_telemetry(
            root,
            selected,
            seed,
            root_key,
            use_terminal_margin,
        )
        if include_root_telemetry else ()
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
        agent_hash=mcts_agent_hash(search_variant),
        search_variant=search_variant,
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
    search_variant=DEFAULT_SEARCH_VARIANT,
    include_root_telemetry=False,
):
    """Compatibility wrapper for analyzing a plain engine game."""
    return choose_mcts_state_action(
        RulesState.from_game(game),
        computer_color,
        simulations=simulations,
        seed=seed,
        rollout_policy=rollout_policy,
        search_variant=search_variant,
        include_root_telemetry=include_root_telemetry,
    )


def _walk(root):
    stack = list(root.children)
    while stack:
        node = stack.pop()
        yield node
        stack.extend(node.children)
