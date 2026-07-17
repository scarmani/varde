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
from mcts_tactical_solver import find_tactical_override
from mcts_v5_solver import scan_root_guidance
from mcts_settling import run_settling_rollout
from mcts_unpruning import (
    next_exposure_visit,
    ordered_rule_transitions,
    progressive_exposure_count,
)
from varde import BLACK, WHITE, GJERDE_RULESETS, control, groups_of


MCTS_FORMAT = "varde-terminal-mcts"
MCTS_VERSION = 4
TACTICAL_MCTS_VERSION = 5
ROLLOUT_POLICIES = frozenset(("uniform", "epsilon-greedy"))
SEARCH_VARIANTS = frozenset((
    "tie-margin",
    "tactical-only",
    "combined",
    "v4-control",
    "v4-solver",
    "v4-ordered-control",
    "v4-unpruning",
    "v4-settling",
    "v5-g0-u0-s0",
    "v5-g1-u0-s0",
))
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
    if search_variant in ("v5-g0-u0-s0", "v5-g1-u0-s0"):
        guidance = search_variant == "v5-g1-u0-s0"
        return {
            "format": MCTS_FORMAT,
            "version": MCTS_VERSION,
            "search_variant": search_variant,
            "recipe_id": f"mcts-search-{search_variant}-v1",
            "exploration": EXPLORATION,
            "epsilon": ROLLOUT_EPSILON,
            "late_pass_rate": LIGHT_LATE_PASS_RATE,
            "terminal": "game-score-win-draw-loss",
            "terminal_margin": "secondary-normalized-by-scoreable-area",
            "root_proof_guidance": (
                "set-valued-decay-1-over-1-plus-visits-v1"
                if guidance else "disabled"
            ),
            "progressive_unpruning": "disabled",
            "true_terminal_settling": "disabled",
            "ties": "sha256(seed,root-position,node-position,action)",
        }
    tactical = search_variant in ("tactical-only", "combined")
    margin = search_variant in (
        "tie-margin",
        "combined",
        "v4-control",
        "v4-solver",
        "v4-ordered-control",
        "v4-unpruning",
        "v4-settling",
        "v5-g0-u0-s0",
        "v5-g1-u0-s0",
    )
    solver = search_variant == "v4-solver"
    ordered = search_variant in ("v4-ordered-control", "v4-unpruning")
    unpruning = search_variant == "v4-unpruning"
    settling = search_variant == "v4-settling"
    return {
        "format": MCTS_FORMAT,
        "version": TACTICAL_MCTS_VERSION if tactical else MCTS_VERSION,
        "search_variant": search_variant,
        "recipe_id": f"mcts-search-{search_variant}-v1",
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
        "certified_local_solver": (
            "three-valued-10000-node-v1" if solver else "disabled"
        ),
        "rules_derived_expansion_order": (
            "administrative-extension-capture-defense-fence-v1"
            if ordered else "disabled"
        ),
        "progressive_unpruning": (
            "ceil-2-sqrt-visits-v1" if unpruning else "disabled"
        ),
        "true_terminal_settling": (
            "p-2p-resume-once-v1" if settling else "disabled"
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
    solver_status: str | None = None
    solver_nodes: int = 0
    solver_cache_hits: int = 0
    solver_invocations: int = 0
    solver_overrides: int = 0
    exposed_actions: int | None = None
    hidden_actions: int | None = None
    next_expansion_visit: int | None = None
    settling_phase_counts: tuple = ()
    terminal_reasons: tuple = ()
    resumption_rollouts: int = 0
    terminal_backups: int = 0

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
        if self.solver_status is not None:
            payload["solver"] = {
                "status": self.solver_status,
                "nodes": self.solver_nodes,
                "cache_hits": self.solver_cache_hits,
                "invocations": self.solver_invocations,
                "overrides": self.solver_overrides,
                "claim_limit": (
                    "bounded local obligation only; not a game-theoretic result"
                ),
            }
        if self.exposed_actions is not None:
            payload["expansion"] = {
                "exposed_actions": self.exposed_actions,
                "hidden_actions": self.hidden_actions,
                "next_expansion_visit": self.next_expansion_visit,
            }
        if self.terminal_backups:
            payload["rollout_terminal_telemetry"] = {
                "settling_phase_counts": dict(self.settling_phase_counts),
                "terminal_reasons": dict(self.terminal_reasons),
                "resumption_rollouts": self.resumption_rollouts,
                "terminal_backups": self.terminal_backups,
                "all_backups_terminal": (
                    self.terminal_backups == self.simulations
                ),
            }
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
        "solver_scan",
        "ordered_actions",
        "ordered_tiers",
        "transition_states",
        "progressive_unpruning",
        "root_proof_scan",
    )

    def __init__(
        self,
        state,
        parent=None,
        action=None,
        *,
        solver_enabled=False,
        ordered_expansion=False,
        progressive_unpruning=False,
        root_guidance_enabled=False,
        expansion_seed=0,
    ):
        self.state = state
        self.parent = parent
        self.action = action
        self.children = []
        ordered = (
            ordered_rule_transitions(state, expansion_seed)
            if ordered_expansion else ()
        )
        proof_transitions = (
            tuple((item.action, item.state) for item in ordered)
            if root_guidance_enabled and ordered
            else legal_transitions(state) if root_guidance_enabled else ()
        )
        self.ordered_actions = tuple(item.action for item in ordered)
        self.ordered_tiers = {
            item.action: item.tier_label for item in ordered
        }
        self.transition_states = {
            item.action: item.state for item in ordered
        }
        if proof_transitions:
            self.transition_states.update(dict(proof_transitions))
        self.untried = list(
            self.ordered_actions if ordered else legal_actions(state)
        )
        self.progressive_unpruning = progressive_unpruning
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
        self.solver_scan = (
            find_tactical_override(state) if solver_enabled else None
        )
        self.root_proof_scan = (
            scan_root_guidance(state, transitions=proof_transitions)
            if root_guidance_enabled else None
        )

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


def _node_exposure_count(node):
    total = len(node.ordered_actions)
    if not total:
        return len(node.children) + len(node.untried)
    if not node.progressive_unpruning:
        return total
    return progressive_exposure_count(node.visits, total)


def _expansion_candidates(node):
    if not node.ordered_actions:
        return tuple(node.untried)
    exposed = set(node.ordered_actions[:_node_exposure_count(node)])
    return tuple(action for action in node.untried if action in exposed)


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


def _accepted_terminal_reason(state):
    if state.game.no_progress_end:
        return "accepted-no-progress"
    if state.game.resumption_used:
        return "accepted-after-resumption"
    return "accepted-two-pass"


def _rollout(
    state,
    root_seat,
    policy,
    rng,
    tactical_guidance=False,
    settling=False,
):
    if settling:
        settled = run_settling_rollout(
            state,
            lambda current, actions: _rollout_action(
                current,
                policy,
                rng,
                actions,
            ),
        )
        return (
            _terminal_sample(settled.terminal_state, root_seat),
            settled.actions,
            {
                "phase_counts": settled.phase_counts,
                "terminal_reason": settled.terminal_reason,
                "resumption_used": settled.resumption_used,
                "backup_terminal": settled.terminal_state.terminal,
            },
        )
    rollout = state.clone()
    actions_played = 0
    while not rollout.terminal:
        if tactical_guidance:
            _action, rollout = _guided_transition(rollout, policy, rng)
        else:
            action = _rollout_action(rollout, policy, rng)
            apply_action(rollout, action, copy=False, validate=False)
        actions_played += 1
    return (
        _terminal_sample(rollout, root_seat),
        actions_played,
        {
            "phase_counts": (),
            "terminal_reason": _accepted_terminal_reason(rollout),
            "resumption_used": rollout.game.resumption_used,
            "backup_terminal": rollout.terminal,
        },
    )


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
        guidance = (
            node.root_proof_scan.bias_for(child.action, child.visits)
            if node.root_proof_scan is not None else 0.0
        )
        primary = (exploitation + exploration + guidance,)
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
    exposed = (
        set(root.ordered_actions[:_node_exposure_count(root)])
        if root.ordered_actions else set(actions)
    )

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
            "solver_status": (
                root.solver_scan.status if root.solver_scan is not None else None
            ),
            "solver_override": bool(
                root.solver_scan is not None
                and root.solver_scan.override_action == action
            ),
            "proof_guidance_status": (
                root.root_proof_scan.status_for(action)
                if root.root_proof_scan is not None else None
            ),
            "proof_guidance_bias": (
                root.root_proof_scan.bias_for(action, visits)
                if root.root_proof_scan is not None else None
            ),
            "exposed": action in exposed,
            "ordering_tier": root.ordered_tiers.get(action),
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
    use_terminal_margin = search_variant in (
        "tie-margin",
        "combined",
        "v4-control",
        "v4-solver",
        "v4-ordered-control",
        "v4-unpruning",
        "v4-settling",
        "v5-g0-u0-s0",
        "v5-g1-u0-s0",
    )
    tactical_guidance = search_variant in ("tactical-only", "combined")
    solver_enabled = search_variant == "v4-solver"
    ordered_expansion = search_variant in (
        "v4-ordered-control", "v4-unpruning"
    )
    progressive_unpruning = search_variant == "v4-unpruning"
    settling_enabled = search_variant == "v4-settling"
    root_guidance_enabled = search_variant == "v5-g1-u0-s0"
    rng = random.Random(_seed_for_position(seed, root_state))
    root = _Node(
        root_state,
        solver_enabled=solver_enabled,
        ordered_expansion=ordered_expansion,
        progressive_unpruning=progressive_unpruning,
        root_guidance_enabled=root_guidance_enabled,
        expansion_seed=seed,
    )
    total_rollout_actions = 0
    max_rollout_actions = 0
    settling_phase_counts = {}
    terminal_reason_counts = {}
    resumption_rollouts = 0
    terminal_backups = 0

    for _simulation in range(simulations):
        node = root
        while not node.state.terminal:
            expansion_candidates = _expansion_candidates(node)
            forced = (
                node.solver_scan.override_action
                if node.solver_scan is not None else None
            )
            if forced is not None:
                forced_child = next(
                    (
                        child for child in node.children
                        if child.action == forced
                    ),
                    None,
                )
                if forced_child is not None:
                    node = forced_child
                    continue
                if forced in expansion_candidates:
                    break
            if expansion_candidates or not node.children:
                break
            node = _select_child(
                node,
                root_seat,
                seed,
                root_key,
                use_terminal_margin,
            )
        expansion_candidates = _expansion_candidates(node)
        if not node.state.terminal and expansion_candidates:
            forced = (
                node.solver_scan.override_action
                if node.solver_scan is not None else None
            )
            if forced is not None and forced in expansion_candidates:
                node.untried.remove(forced)
                action = forced
                child_state = apply_action(node.state, action, validate=False)
            elif (
                node.root_proof_scan is not None
                and any(
                    node.root_proof_scan.status_for(candidate) != "unknown"
                    for candidate in expansion_candidates
                )
            ):
                ranked = {
                    "proven": 1,
                    "unknown": 0,
                    "disproven": -1,
                }
                best = max(
                    ranked[node.root_proof_scan.status_for(candidate)]
                    for candidate in expansion_candidates
                )
                choices = [
                    candidate for candidate in expansion_candidates
                    if ranked[node.root_proof_scan.status_for(candidate)] == best
                ]
                action = choices[rng.randrange(len(choices))]
                node.untried.remove(action)
                child_state = node.transition_states[action]
            elif tactical_guidance and not node.tactical_prepared:
                action, child_state = _prepare_tactical_expansion(node, rng)
            elif tactical_guidance:
                action = node.untried.pop()
                child_state = apply_action(node.state, action, validate=False)
            elif node.ordered_actions:
                action = expansion_candidates[0]
                node.untried.remove(action)
                child_state = node.transition_states[action]
            else:
                action = expansion_candidates[
                    rng.randrange(len(expansion_candidates))
                ]
                node.untried.remove(action)
                child_state = apply_action(node.state, action, validate=False)
            child = _Node(
                child_state,
                parent=node,
                action=action,
                solver_enabled=solver_enabled,
                ordered_expansion=ordered_expansion,
                progressive_unpruning=progressive_unpruning,
                root_guidance_enabled=False,
                expansion_seed=seed,
            )
            node.children.append(child)
            node = child
        sample, rollout_actions, rollout_telemetry = _rollout(
            node.state,
            root_seat,
            rollout_policy,
            rng,
            tactical_guidance,
            settling_enabled,
        )
        total_rollout_actions += rollout_actions
        max_rollout_actions = max(max_rollout_actions, rollout_actions)
        for phase, count in rollout_telemetry["phase_counts"]:
            settling_phase_counts[phase] = (
                settling_phase_counts.get(phase, 0) + count
            )
        reason = rollout_telemetry["terminal_reason"]
        terminal_reason_counts[reason] = terminal_reason_counts.get(reason, 0) + 1
        resumption_rollouts += rollout_telemetry["resumption_used"]
        terminal_backups += rollout_telemetry["backup_terminal"]
        while node is not None:
            node.record(sample)
            node = node.parent

    if rules_state.key() != before:
        raise AssertionError("MCTS mutated the analyzed rules state")
    if not root.children:
        raise ValueError("no legal MCTS action")
    forced = (
        root.solver_scan.override_action
        if root.solver_scan is not None else None
    )
    selected = next(
        (child for child in root.children if child.action == forced),
        None,
    )
    if selected is None:
        selected = max(
            root.children,
            key=lambda child: _final_selection_key(
                child,
                seed,
                root_key,
                use_terminal_margin,
            ),
        )
    selection_reason = None
    if include_root_telemetry:
        selection_reason = (
            "certified-local-obligation"
            if forced is not None
            else _selection_reason(root, selected, use_terminal_margin)
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
    tree_nodes = (root, *tuple(_walk(root)))
    solver_scans = [
        node.solver_scan for node in tree_nodes if node.solver_scan is not None
    ]
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
        solver_status=(
            root.root_proof_scan.status
            if root_guidance_enabled else (
                root.solver_scan.status if solver_enabled else None
            )
        ),
        solver_nodes=(
            root.root_proof_scan.nodes
            if root_guidance_enabled else sum(scan.nodes for scan in solver_scans)
        ),
        solver_cache_hits=(
            root.root_proof_scan.cache_hits
            if root_guidance_enabled
            else sum(scan.cache_hits for scan in solver_scans)
        ),
        solver_invocations=(
            root.root_proof_scan.root_scans
            if root_guidance_enabled else len(solver_scans)
        ),
        solver_overrides=(
            0 if root_guidance_enabled else sum(
                scan.override_action is not None for scan in solver_scans
            )
        ),
        exposed_actions=(
            _node_exposure_count(root) if root.ordered_actions else None
        ),
        hidden_actions=(
            len(root.ordered_actions) - _node_exposure_count(root)
            if root.ordered_actions else None
        ),
        next_expansion_visit=(
            next_exposure_visit(root.visits, len(root.ordered_actions))
            if root.progressive_unpruning else None
        ),
        settling_phase_counts=tuple(sorted(settling_phase_counts.items())),
        terminal_reasons=tuple(sorted(terminal_reason_counts.items())),
        resumption_rollouts=resumption_rollouts,
        terminal_backups=terminal_backups,
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
