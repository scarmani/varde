"""Bounded, rule-aware computer opponent for Varde.

The opponent deliberately uses shallow heuristic search rather than the
self-play policies.  It is intended to provide coherent local practice play,
not expert strength.
"""

from dataclasses import asdict, dataclass, replace
import hashlib
import time
from types import MappingProxyType

from varde import (
    BLACK,
    Illegal,
    WHITE,
    control,
    groups_of,
    has_sky,
    is_summit,
    nb_heights,
    other,
    resolve,
    score_cells,
    signature,
    terrain_ok,
)


BALANCED_WEIGHTS = MappingProxyType(
    {
        "controlled": 12.0,
        "captured": 35.0,
        "skies": 18.0,
        "liberties": 3.0,
        "vulnerable": -15.0,
        "development": 2.0,
        "territory": 1.0,
        # V3 measurements begin disabled.  Curated profiles may assign them
        # weights later, but Balanced must remain the historical evaluator.
        "control_resilience": 0.0,
        "latent_reserves": 0.0,
        "sky_durability": 0.0,
        "connection": 0.0,
        "capturing_moves": 0.0,
        "max_capture": 0.0,
        "covers": 0.0,
        "hostile_covers": 0.0,
        "reinforcements": 0.0,
        "summits": 0.0,
    }
)
PASS_IMPROVEMENT = 2
SWAP_MARGIN = 5

DIFFICULTIES = frozenset(("casual", "standard"))
LEGACY_DIFFICULTIES = DIFFICULTIES | {"advanced"}


@dataclass(frozen=True)
class BotDecision:
    action: str
    point: tuple | None = None
    reason_code: str = ""
    reason_text: str = ""
    score: float = 0.0
    nodes: int = 0
    elapsed_ms: float = 0.0
    profile: str = ""

    def to_dict(self):
        payload = asdict(self)
        if self.point is not None:
            payload["point"] = list(self.point)
        payload["score"] = round(self.score, 2)
        payload["elapsed_ms"] = round(self.elapsed_ms, 2)
        return payload


@dataclass(frozen=True)
class _Features:
    controlled: int
    skies: int
    liberties: int
    vulnerable_stones: int
    development: int


@dataclass(frozen=True)
class _StructuralFeatures:
    control_resilience: int
    latent_reserves: int
    sky_durability: int
    connection: int


@dataclass(frozen=True)
class _TransitionFeatures:
    capturing_moves: int
    max_capture: int
    covers: int
    hostile_covers: int
    reinforcements: int
    summits: int


@dataclass(frozen=True)
class _Candidate:
    point: tuple
    state: dict
    captured: int
    transition_bonus: float
    root_score: float
    score: float
    reason_code: str
    reason_text: str


def _group_features(board, state, color):
    skies = 0
    liberties = 0
    vulnerable_stones = 0
    for group in groups_of(board, state, color):
        empty = {
            neighbor
            for point in group
            for neighbor in board.neighbors[point]
            if not state[neighbor]
        }
        group_skies = sum(has_sky(board, state, point, None) for point in group)
        skies += group_skies
        liberties += min(3, len(empty))
        if len(empty) == 1 and group_skies == 0:
            vulnerable_stones += len(group)
    return skies, liberties, vulnerable_stones


def _features(board, state, color, moves_played):
    controlled = [point for point in board.points if control(state, point) == color]
    skies, liberties, vulnerable = _group_features(board, state, color)
    opening = moves_played < int(0.6 * len(board.points))
    development = 0
    if opening:
        distances = board.dist_to_rim()
        development = sum(distances[point] for point in controlled)
    return _Features(
        controlled=len(controlled),
        skies=skies,
        liberties=liberties,
        vulnerable_stones=vulnerable,
        development=development,
    )


def _structural_features(board, state, color):
    """Return inexpensive V3 structure measurements for one color.

    This routine intentionally performs no legal move generation.  Connection
    points use only the terrain precondition; full move legality remains the
    rules engine's responsibility.
    """
    resilience = 0
    reserves = 0
    durability = 0
    for point in board.points:
        stack = state[point]
        top = control(state, point)
        if top == color:
            consecutive = 0
            for stone in reversed(stack):
                if stone != color:
                    break
                consecutive += 1
            resilience += min(2, consecutive)
            if has_sky(board, state, point, None):
                clearance = min(nb_heights(board, state, point)) - len(stack)
                durability += min(2, max(0, clearance))
        elif stack:
            reserves += sum(stone == color for stone in stack[:-1])

    group_index = {}
    for index, group in enumerate(groups_of(board, state, color)):
        for point in group:
            group_index[point] = index
    connection = 0
    for point in board.points:
        if not terrain_ok(board, state, point):
            continue
        adjacent_groups = {
            group_index[neighbor]
            for neighbor in board.neighbors[point]
            if neighbor in group_index
        }
        connection += len(adjacent_groups) >= 2

    return _StructuralFeatures(
        control_resilience=resilience,
        latent_reserves=reserves,
        sky_durability=durability,
        connection=connection,
    )


def _transition_features(board, state, color, transitions):
    """Summarize already-generated legal transitions for one color.

    Each transition is ``(point, next_state, captured)``.  The function never
    asks the engine for another move, preventing feature instrumentation from
    turning the bounded search into an accidental deeper scan.
    """
    capturing_moves = 0
    max_capture = 0
    covers = 0
    hostile_covers = 0
    reinforcements = 0
    summits = 0
    for transition in transitions:
        if isinstance(transition, _Candidate):
            point = transition.point
            captured = transition.captured
        else:
            point, _next_state, captured = transition
        capturing_moves += captured > 0
        max_capture = max(max_capture, captured)
        if state[point]:
            covers += 1
            if control(state, point) == color:
                reinforcements += 1
            else:
                hostile_covers += 1
        summits += is_summit(board, state, point)
    return _TransitionFeatures(
        capturing_moves=capturing_moves,
        max_capture=max_capture,
        covers=covers,
        hostile_covers=hostile_covers,
        reinforcements=reinforcements,
        summits=summits,
    )


def _area_score(board, state):
    """Score an arbitrary state without mutating or constructing a Game."""
    from collections import deque

    scores = {BLACK: 0, WHITE: 0}
    for point in board.points:
        color = control(state, point)
        if color:
            scores[color] += 1
    seen = set()
    for point in board.points:
        if point in seen or state[point]:
            continue
        region = []
        border = set()
        queue = deque([point])
        seen.add(point)
        while queue:
            current = queue.popleft()
            region.append(current)
            for neighbor in board.neighbors[current]:
                if state[neighbor]:
                    border.add(control(state, neighbor))
                elif neighbor not in seen:
                    seen.add(neighbor)
                    queue.append(neighbor)
        if len(border) == 1:
            scores[border.pop()] += len(region)
    return scores


def _normalized_features(board, state, moves_played, include_v3):
    """Return color-symmetric, normalized features from Black's perspective.

    ``include_v3=False`` is the compatibility fast path used by the existing
    nine-weight Personal model.  Audits and V3 profiles request the structural
    candidates explicitly.
    """
    black = _features(board, state, BLACK, moves_played)
    white = _features(board, state, WHITE, moves_played)
    total = len(board.points)
    max_distance = max(1, 2 * (board.n - 1))
    occupied = black.controlled + white.controlled
    territory = 0.0
    if hasattr(board, "cells"):
        cells = score_cells(board, state)
        territory = (cells[BLACK] - cells[WHITE]) / max(1, len(board.cells))
    elif occupied >= 0.55 * total:
        score = _area_score(board, state)
        territory = (score[BLACK] - score[WHITE]) / total
    black_height = 0
    white_height = 0
    black_rim = 0
    white_rim = 0
    for point in board.points:
        color = control(state, point)
        if color == BLACK:
            black_height += len(state[point])
            black_rim += point in board.rim
        elif color == WHITE:
            white_height += len(state[point])
            white_rim += point in board.rim
    black_groups = len(groups_of(board, state, BLACK))
    white_groups = len(groups_of(board, state, WHITE))

    def clipped(value):
        return max(-1.0, min(1.0, value))

    values = {
        "controlled": (black.controlled - white.controlled) / total,
        "skies": (black.skies - white.skies) / total,
        "liberties": (black.liberties - white.liberties) / (3 * total),
        "vulnerable": (white.vulnerable_stones - black.vulnerable_stones) / total,
        "development": (black.development - white.development) / (total * max_distance),
        "territory": territory,
        "height": clipped((black_height - white_height) / total),
        "rim": (black_rim - white_rim) / max(1, len(board.rim)),
        "groups": clipped(9 * (white_groups - black_groups) / total),
    }
    if include_v3:
        black_structure = _structural_features(board, state, BLACK)
        white_structure = _structural_features(board, state, WHITE)
        stack_capacity = sum(
            distance + 1 for distance in board.dist_to_rim().values()
        )
        values.update(
            {
                "control_resilience": (
                    black_structure.control_resilience
                    - white_structure.control_resilience
                )
                / (2 * total),
                "latent_reserves": clipped(
                    (
                        black_structure.latent_reserves
                        - white_structure.latent_reserves
                    )
                    / max(1, stack_capacity)
                ),
                "sky_durability": (
                    black_structure.sky_durability
                    - white_structure.sky_durability
                )
                / (2 * total),
                "connection": (
                    black_structure.connection - white_structure.connection
                )
                / total,
            }
        )
    return {name: clipped(value) for name, value in values.items()}


def normalized_features(board, state, moves_played):
    """Return the existing nine Personal-model features unchanged."""
    return _normalized_features(board, state, moves_played, include_v3=False)


def normalized_v3_features(board, state, moves_played):
    """Return Personal-model features plus V3 structural telemetry."""
    return _normalized_features(board, state, moves_played, include_v3=True)


def normalized_transition_features(
    board, state, black_transitions, white_transitions
):
    """Return bounded color-symmetric V3 move-set telemetry.

    Callers provide transitions they already generated.  This makes capture
    initiative and vertical mobility measurable without hidden nested scans.
    """
    black = _transition_features(board, state, BLACK, black_transitions)
    white = _transition_features(board, state, WHITE, white_transitions)
    total = len(board.points)
    stack_capacity = sum(distance + 1 for distance in board.dist_to_rim().values())

    def clipped(value):
        return max(-1.0, min(1.0, value))

    return {
        "capturing_moves": clipped(
            (black.capturing_moves - white.capturing_moves) / total
        ),
        "max_capture": clipped(
            (black.max_capture - white.max_capture) / max(1, stack_capacity)
        ),
        "covers": clipped((black.covers - white.covers) / total),
        "hostile_covers": clipped(
            (black.hostile_covers - white.hostile_covers) / total
        ),
        "reinforcements": clipped(
            (black.reinforcements - white.reinforcements) / total
        ),
        "summits": clipped((black.summits - white.summits) / total),
    }


def evaluate_state(
    board, state, perspective, moves_played, model=None, weights=None
):
    """Return the fixed-weight static evaluation from ``perspective``."""
    weights = BALANCED_WEIGHTS if weights is None else weights
    enemy = other(perspective)
    mine = _features(board, state, perspective, moves_played)
    theirs = _features(board, state, enemy, moves_played)
    value = weights["controlled"] * (mine.controlled - theirs.controlled)
    value += weights["skies"] * (mine.skies - theirs.skies)
    value += weights["liberties"] * (mine.liberties - theirs.liberties)
    value += weights["vulnerable"] * (
        mine.vulnerable_stones - theirs.vulnerable_stones
    )
    value += weights["development"] * (mine.development - theirs.development)
    occupied = mine.controlled + theirs.controlled
    if hasattr(board, "cells"):
        # Gjerde: fenced fields are the game's only score. Value them
        # from the first move — fences complete midgame, and a 0.55
        # occupancy gate would blind the evaluator for most of it.
        cells = score_cells(board, state)
        value += 25.0 * (cells[perspective] - cells[enemy])
    elif occupied >= 0.55 * len(board.points):
        score = _area_score(board, state)
        value += weights["territory"] * (score[perspective] - score[enemy])
    v3_names = (
        "control_resilience",
        "latent_reserves",
        "sky_durability",
        "connection",
    )
    uses_v3 = any(weights.get(name, 0.0) for name in v3_names)
    features = None
    if uses_v3:
        features = normalized_v3_features(board, state, moves_played)
        direction = 1 if perspective == BLACK else -1
        for name in v3_names:
            value += weights.get(name, 0.0) * features[name] * direction
    if model is not None:
        if features is None:
            features = normalized_features(board, state, moves_played)
        value += model.correction(features, perspective)
    return value


def _tie_value(game, seed, point, label="move"):
    digest = hashlib.sha256(
        f"{seed}|{label}|{signature(game.board, game.state, game.to_move)!r}|{point!r}".encode()
    ).digest()
    return int.from_bytes(digest[:8], "big")


def _rationale(game, point, next_state, captured, mover):
    board = game.board
    enemy = other(mover)
    before_mine = _features(board, game.state, mover, game.moves_played)
    after_mine = _features(board, next_state, mover, game.moves_played + 1)
    before_enemy = _features(board, game.state, enemy, game.moves_played)
    after_enemy = _features(board, next_state, enemy, game.moves_played + 1)
    if captured:
        return "capture", f"Captured {captured} stone{'s' if captured != 1 else ''}."
    if after_mine.vulnerable_stones < before_mine.vulnerable_stones:
        return "rescue", "Strengthened a threatened group."
    if after_mine.skies > before_mine.skies:
        return "sky", "Created a sky liberty."
    if after_enemy.vulnerable_stones > before_enemy.vulnerable_stones:
        return "pressure", "Reduced an opposing group's breathing room."
    if game.state[point]:
        return "cover", "Covered a column to contest control."
    return "develop", "Developed a flexible position toward the interior."


def _weights_or_balanced(weights):
    return BALANCED_WEIGHTS if weights is None else weights


def _is_balanced_weights(weights):
    return weights is None or weights is BALANCED_WEIGHTS


def _uses_transition_style(weights):
    if _is_balanced_weights(weights):
        return False
    return any(
        weights.get(name, 0.0)
        for name in (
            "capturing_moves",
            "max_capture",
            "covers",
            "hostile_covers",
            "reinforcements",
            "summits",
        )
    )


def _transition_bonus(
    board, state, color, point, captured, maximum_capture, weights
):
    """Score one already-generated transition for a style profile."""
    if _is_balanced_weights(weights):
        return 0.0
    bonus = weights.get("capturing_moves", 0.0) * (captured > 0)
    bonus += weights.get("max_capture", 0.0) * (
        captured / max(1, maximum_capture)
    )
    if state[point]:
        bonus += weights.get("covers", 0.0)
        if control(state, point) == color:
            bonus += weights.get("reinforcements", 0.0)
        else:
            bonus += weights.get("hostile_covers", 0.0)
    if is_summit(board, state, point):
        bonus += weights.get("summits", 0.0)
    return bonus


def _evaluate_with_weights(
    board, state, perspective, moves_played, model, weights
):
    # Preserve the historical five-argument call surface for Balanced.  Several
    # tests and external research probes patch evaluate_state directly.
    if _is_balanced_weights(weights):
        return evaluate_state(board, state, perspective, moves_played, model)
    return evaluate_state(
        board, state, perspective, moves_played, model, weights
    )


def _balanced_root_candidates(game, perspective, model):
    """Historical root path kept literal for parity and latency."""
    candidates = []
    for point in game.legal_placements():
        state, captured = game.try_play(point)
        score = evaluate_state(
            game.board, state, perspective, game.moves_played + 1, model
        ) + BALANCED_WEIGHTS["captured"] * captured
        reason_code, reason_text = _rationale(
            game, point, state, captured, game.to_move
        )
        candidates.append(
            _Candidate(
                point=point,
                state=state,
                captured=captured,
                transition_bonus=0.0,
                root_score=score,
                score=score,
                reason_code=reason_code,
                reason_text=reason_text,
            )
        )
    return candidates


def _root_candidates(game, perspective, model=None, weights=None):
    if _is_balanced_weights(weights):
        return _balanced_root_candidates(game, perspective, model)
    candidates = []
    active_weights = _weights_or_balanced(weights)
    if _uses_transition_style(weights):
        transitions = []
        for point in game.legal_placements():
            state, captured = game.try_play(point)
            transitions.append((point, state, captured))
        maximum_capture = max(
            (captured for _point, _state, captured in transitions), default=0
        )
    else:
        transitions = (
            (point, *game.try_play(point))
            for point in game.legal_placements()
        )
        maximum_capture = 0
    for point, state, captured in transitions:
        transition_bonus = _transition_bonus(
            game.board,
            game.state,
            game.to_move,
            point,
            captured,
            maximum_capture,
            weights,
        )
        if _is_balanced_weights(weights):
            score = evaluate_state(
                game.board,
                state,
                perspective,
                game.moves_played + 1,
                model,
            )
        else:
            score = evaluate_state(
                game.board,
                state,
                perspective,
                game.moves_played + 1,
                model,
                weights,
            )
        score += active_weights["captured"] * captured + transition_bonus
        reason_code, reason_text = _rationale(
            game, point, state, captured, game.to_move
        )
        candidates.append(
            _Candidate(
                point=point,
                state=state,
                captured=captured,
                transition_bonus=transition_bonus,
                root_score=score,
                score=score,
                reason_code=reason_code,
                reason_text=reason_text,
            )
        )
    return candidates


def _balanced_standard_scores(game, candidates, perspective, model):
    """Historical two-ply path kept literal for parity and latency."""
    ranked = sorted(candidates, key=lambda item: item.root_score, reverse=True)
    searched = []
    nodes = len(candidates)
    reply_color = other(game.to_move)
    for candidate in ranked[:10]:
        history = set(game.history)
        history.add(signature(game.board, candidate.state, reply_color))
        replies = [
            evaluate_state(
                game.board,
                candidate.state,
                perspective,
                game.moves_played + 2,
                model,
            )
            + BALANCED_WEIGHTS["captured"] * candidate.captured
        ]
        nodes += 1
        for point in game.board.points:
            try:
                state, captured = resolve(
                    game.board,
                    candidate.state,
                    point,
                    reply_color,
                    history,
                    rules=game.rules,
                )
            except Illegal:
                continue
            nodes += 1
            replies.append(
                evaluate_state(
                    game.board, state, perspective, game.moves_played + 2, model
                )
                + BALANCED_WEIGHTS["captured"] * candidate.captured
                - BALANCED_WEIGHTS["captured"] * captured
            )
        if game.moves_played == 0 and game.to_move == BLACK:
            replies.append(
                evaluate_state(
                    game.board,
                    candidate.state,
                    WHITE,
                    game.moves_played + 1,
                    model,
                )
            )
            nodes += 1
        searched.append(replace(candidate, score=min(replies)))
    return searched, nodes


def _standard_scores(
    game, candidates, perspective, model=None, weights=None
):
    """Apply a full opponent-reply scan to the best ten root candidates."""
    if _is_balanced_weights(weights):
        return _balanced_standard_scores(game, candidates, perspective, model)
    ranked = sorted(candidates, key=lambda item: item.root_score, reverse=True)
    searched = []
    nodes = len(candidates)
    reply_color = other(game.to_move)
    active_weights = _weights_or_balanced(weights)
    for candidate in ranked[:10]:
        history = set(game.history)
        history.add(signature(game.board, candidate.state, reply_color))
        # Passing is a legal reply.  The board stands pat, but the move count
        # advances, which can switch off the opening-development feature.
        if _is_balanced_weights(weights):
            pass_value = evaluate_state(
                game.board,
                candidate.state,
                perspective,
                game.moves_played + 2,
                model,
            )
        else:
            pass_value = evaluate_state(
                game.board,
                candidate.state,
                perspective,
                game.moves_played + 2,
                model,
                weights,
            )
        replies = [
            pass_value
            + active_weights["captured"] * candidate.captured
            + candidate.transition_bonus
        ]
        nodes += 1
        reply_transitions = [] if _uses_transition_style(weights) else None
        for point in game.board.points:
            try:
                state, captured = resolve(
                    game.board,
                    candidate.state,
                    point,
                    reply_color,
                    history,
                    rules=game.rules,
                )
            except Illegal:
                continue
            nodes += 1
            if reply_transitions is not None:
                reply_transitions.append((point, state, captured))
                continue
            if _is_balanced_weights(weights):
                reply_value = evaluate_state(
                    game.board,
                    state,
                    perspective,
                    game.moves_played + 2,
                    model,
                )
            else:
                reply_value = evaluate_state(
                    game.board,
                    state,
                    perspective,
                    game.moves_played + 2,
                    model,
                    weights,
                )
            replies.append(
                reply_value
                + active_weights["captured"] * candidate.captured
                - active_weights["captured"] * captured
            )
        if reply_transitions is not None:
            maximum_reply_capture = max(
                (
                    captured
                    for _point, _state, captured in reply_transitions
                ),
                default=0,
            )
        else:
            maximum_reply_capture = 0
        for point, state, captured in reply_transitions or ():
            reply_bonus = _transition_bonus(
                game.board,
                candidate.state,
                reply_color,
                point,
                captured,
                maximum_reply_capture,
                weights,
            )
            replies.append(
                evaluate_state(
                    game.board,
                    state,
                    perspective,
                    game.moves_played + 2,
                    model,
                    weights,
                )
                + active_weights["captured"] * candidate.captured
                + candidate.transition_bonus
                - active_weights["captured"] * captured
                - reply_bonus
            )
        # After Black's opening, White may take over instead of placing or
        # passing.  The original Black seat then evaluates the same board as
        # White; takeover itself does not increment the placement count.
        if game.moves_played == 0 and game.to_move == BLACK:
            if _is_balanced_weights(weights):
                takeover_value = evaluate_state(
                    game.board,
                    candidate.state,
                    WHITE,
                    game.moves_played + 1,
                    model,
                )
            else:
                takeover_value = evaluate_state(
                    game.board,
                    candidate.state,
                    WHITE,
                    game.moves_played + 1,
                    model,
                    weights,
                )
            replies.append(takeover_value)
            nodes += 1
        searched.append(replace(candidate, score=min(replies)))
    return searched, nodes


def _choose_candidate(
    game, difficulty, seed, perspective, model=None, weights=None
):
    candidates = _root_candidates(game, perspective, model, weights)
    nodes = len(candidates)
    if not candidates:
        return None, nodes, candidates
    if difficulty == "standard":
        pool, nodes = _standard_scores(
            game, candidates, perspective, model, weights
        )
        best = max(item.score for item in pool)
        tied = [item for item in pool if item.score == best]
        chosen = min(
            tied, key=lambda item: _tie_value(game, seed, item.point, "standard")
        )
        return chosen, nodes, candidates

    best = max(item.root_score for item in candidates)
    pool = sorted(
        (item for item in candidates if item.root_score >= best - 12),
        key=lambda item: item.root_score,
        reverse=True,
    )[:8]
    index = _tie_value(game, seed, "casual", "casual") % len(pool)
    return pool[index], nodes, candidates


def _swap_value(game, computer_color, model=None, weights=None):
    """Worst value after the human's best White reply following a swap."""
    assert computer_color == BLACK
    if _is_balanced_weights(weights):
        replies = [
            evaluate_state(
                game.board,
                game.state,
                computer_color,
                game.moves_played + 1,
                model,
            )
        ]
        for point in game.legal_placements():
            state, captured = game.try_play(point)
            replies.append(
                evaluate_state(
                    game.board,
                    state,
                    computer_color,
                    game.moves_played + 1,
                    model,
                )
                - BALANCED_WEIGHTS["captured"] * captured
            )
        return min(replies)
    # The new White player may pass after takeover, leaving the board intact
    # and advancing the move count by one.
    replies = [
        _evaluate_with_weights(
            game.board,
            game.state,
            computer_color,
            game.moves_played + 1,
            model,
            weights,
        )
    ]
    transitions = []
    for point in game.legal_placements():
        state, captured = game.try_play(point)
        transitions.append((point, state, captured))
    maximum_capture = max(
        (captured for _point, _state, captured in transitions), default=0
    )
    for point, state, captured in transitions:
        reply_bonus = _transition_bonus(
            game.board,
            game.state,
            WHITE,
            point,
            captured,
            maximum_capture,
            weights,
        )
        replies.append(
            _evaluate_with_weights(
                game.board,
                state,
                computer_color,
                game.moves_played + 1,
                model,
                weights,
            )
            - _weights_or_balanced(weights)["captured"] * captured
            - reply_bonus
        )
    return min(replies)


def choose_decision(
    game,
    computer_color,
    difficulty="standard",
    seed=1,
    model=None,
    weights=None,
):
    """Choose one computer action without mutating ``game``."""
    started = time.perf_counter()
    if difficulty == "advanced":
        difficulty = "standard"
    elif difficulty not in DIFFICULTIES:
        raise ValueError("difficulty must be casual or standard")
    if computer_color not in (BLACK, WHITE):
        raise ValueError("computer color must be B or W")

    if game.finished:
        if game.resumption_available:
            score = game.score()
            if score[computer_color] < score[other(computer_color)]:
                decision = BotDecision(
                    action="resume",
                    reason_code="resume",
                    reason_text="Resumed play because the computer is behind.",
                )
            else:
                decision = BotDecision(
                    action="accept",
                    reason_code="accept",
                    reason_text="Accepted the final score.",
                )
        else:
            decision = BotDecision(
                action="accept",
                reason_code="accept",
                reason_text="Accepted the final score.",
            )
        return replace(
            decision, elapsed_ms=(time.perf_counter() - started) * 1000
        )

    if game.to_move != computer_color:
        raise ValueError("it is not the computer's turn")

    if game.swap_available and computer_color == WHITE:
        stay, nodes, _ = _choose_candidate(
            game, difficulty, seed, WHITE, model, weights
        )
        stay_value = stay.score if stay else _evaluate_with_weights(
            game.board, game.state, WHITE, game.moves_played, model, weights
        )
        swap_value = _swap_value(game, BLACK, model, weights)
        if swap_value >= stay_value + SWAP_MARGIN:
            return BotDecision(
                action="swap",
                reason_code="swap",
                reason_text="Took over Black because the opening is strong.",
                score=swap_value,
                nodes=nodes,
                elapsed_ms=(time.perf_counter() - started) * 1000,
            )

    chosen, nodes, all_candidates = _choose_candidate(
        game, difficulty, seed, computer_color, model, weights
    )
    if chosen is None:
        decision = BotDecision(
            action="pass",
            reason_code="pass",
            reason_text="Passed because no placement is legal.",
            nodes=nodes,
        )
    else:
        baseline = _evaluate_with_weights(
            game.board,
            game.state,
            computer_color,
            game.moves_played,
            model,
            weights,
        )
        best_root = max(item.root_score for item in all_candidates)
        if (
            game.moves_played >= len(game.board.points)
            and best_root <= baseline + PASS_IMPROVEMENT
        ):
            decision = BotDecision(
                action="pass",
                reason_code="pass",
                reason_text="Passed because no placement improves the position.",
                score=baseline,
                nodes=nodes,
            )
        else:
            decision = BotDecision(
                action="play",
                point=chosen.point,
                reason_code=chosen.reason_code,
                reason_text=chosen.reason_text,
                score=chosen.score,
                nodes=nodes,
            )
    return replace(
        decision, elapsed_ms=(time.perf_counter() - started) * 1000
    )


# ---------------------------------------------------------------------------
# Greedy duel styles: attacker and defender (research probes, playable)
# ---------------------------------------------------------------------------
def _duel_tiebreak(point, seed):
    digest = hashlib.sha256(f"{seed}:{point}".encode()).hexdigest()
    return int(digest[:8], 16)


def _duel_liberties(game, state, color):
    """Total horizontal liberties and one-liberty stone count."""
    board = game.board
    total = 0
    imperiled = 0
    for comp in groups_of(board, state, color):
        libs = {
            nb
            for q in comp
            for nb in board.neighbors[q]
            if not state[nb]
        }
        total += len(libs)
        if len(libs) == 1:
            imperiled += len(comp)
    return total, imperiled


def greedy_decision(game, computer_color, style, seed=1):
    """One-ply attack- or defense-maximizing move for the duel profiles."""
    started = time.perf_counter()
    if game.finished:
        return choose_decision(game, computer_color, "casual", seed=seed)
    enemy = other(computer_color)
    best = None
    nodes = 0
    for point in game.legal_placements():
        state, captured = game.try_play(point)
        nodes += 1
        if style == "attacker":
            enemy_libs, enemy_imperiled = _duel_liberties(game, state, enemy)
            _own, own_imperiled = _duel_liberties(game, state, computer_color)
            score = (
                1000.0 * captured
                - 10.0 * enemy_libs
                + 25.0 * enemy_imperiled
                - 15.0 * own_imperiled
            )
        else:
            own_libs, own_imperiled = _duel_liberties(game, state, computer_color)
            controlled = sum(
                1 for q in game.board.points
                if state[q] and state[q][-1] == computer_color
            )
            fenced = 0.0
            if game.rules == "gjerde":
                # Defense in a fencing game means completed fields:
                # score the fenced-cell differential of the candidate.
                cells = score_cells(game.board, state)
                fenced = 30.0 * (cells[computer_color] - cells[enemy])
            score = (
                10.0 * own_libs
                - 50.0 * own_imperiled
                + 20.0 * captured
                + fenced
                + 1.0 * controlled
            )
        key = (score, -_duel_tiebreak(point, seed))
        if best is None or key > best[0]:
            best = (key, point, captured)
    if best is None:
        return BotDecision(
            action="pass",
            reason_code="pass",
            reason_text="Passed with no legal placement.",
            nodes=nodes,
            elapsed_ms=(time.perf_counter() - started) * 1000,
        )
    _key, point, captured = best
    text = (
        "Pressed the attack." if style == "attacker" else "Shored up defenses."
    )
    if captured:
        text = f"Captured {captured} stone{'s' if captured > 1 else ''}."
    return BotDecision(
        action="play",
        point=point,
        reason_code=style,
        reason_text=text,
        score=float(best[0][0]),
        nodes=nodes,
        elapsed_ms=(time.perf_counter() - started) * 1000,
    )
