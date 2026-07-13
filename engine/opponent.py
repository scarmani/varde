"""Bounded, rule-aware computer opponent for Cairn.

The opponent deliberately uses shallow heuristic search rather than the
self-play policies.  It is intended to provide coherent local practice play,
not expert strength.
"""

from dataclasses import asdict, dataclass, replace
import hashlib
import time

from cairn import (
    BLACK,
    Illegal,
    WHITE,
    control,
    groups_of,
    has_sky,
    other,
    resolve,
    signature,
)


CONTROL_WEIGHT = 12
CAPTURE_WEIGHT = 35
SKY_WEIGHT = 18
LIBERTY_WEIGHT = 3
VULNERABLE_WEIGHT = 15
DEVELOPMENT_WEIGHT = 2
TERRITORY_WEIGHT = 1
PASS_IMPROVEMENT = 2
SWAP_MARGIN = 5

DIFFICULTIES = frozenset(("casual", "standard", "advanced"))


@dataclass(frozen=True)
class BotDecision:
    action: str
    point: tuple | None = None
    reason_code: str = ""
    reason_text: str = ""
    score: float = 0.0
    nodes: int = 0
    elapsed_ms: float = 0.0

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
class _Candidate:
    point: tuple
    state: dict
    captured: int
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


def normalized_features(board, state, moves_played):
    """Return color-symmetric, normalized features from Black's perspective."""
    black = _features(board, state, BLACK, moves_played)
    white = _features(board, state, WHITE, moves_played)
    total = len(board.points)
    max_distance = max(1, 2 * (board.n - 1))
    occupied = black.controlled + white.controlled
    territory = 0.0
    if occupied >= 0.55 * total:
        score = _area_score(board, state)
        territory = (score[BLACK] - score[WHITE]) / total
    return {
        "controlled": (black.controlled - white.controlled) / total,
        "skies": (black.skies - white.skies) / total,
        "liberties": (black.liberties - white.liberties) / (3 * total),
        "vulnerable": (white.vulnerable_stones - black.vulnerable_stones) / total,
        "development": (black.development - white.development) / (total * max_distance),
        "territory": territory,
    }


def evaluate_state(board, state, perspective, moves_played, model=None):
    """Return the fixed-weight static evaluation from ``perspective``."""
    enemy = other(perspective)
    mine = _features(board, state, perspective, moves_played)
    theirs = _features(board, state, enemy, moves_played)
    value = CONTROL_WEIGHT * (mine.controlled - theirs.controlled)
    value += SKY_WEIGHT * (mine.skies - theirs.skies)
    value += LIBERTY_WEIGHT * (mine.liberties - theirs.liberties)
    value -= VULNERABLE_WEIGHT * (
        mine.vulnerable_stones - theirs.vulnerable_stones
    )
    value += DEVELOPMENT_WEIGHT * (mine.development - theirs.development)
    occupied = mine.controlled + theirs.controlled
    if occupied >= 0.55 * len(board.points):
        score = _area_score(board, state)
        value += TERRITORY_WEIGHT * (score[perspective] - score[enemy])
    if model is not None:
        value += model.correction(
            normalized_features(board, state, moves_played), perspective
        )
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


def _root_candidates(game, perspective, model=None):
    candidates = []
    for point in game.legal_placements():
        state, captured = game.try_play(point)
        score = evaluate_state(
            game.board, state, perspective, game.moves_played + 1, model
        ) + CAPTURE_WEIGHT * captured
        reason_code, reason_text = _rationale(
            game, point, state, captured, game.to_move
        )
        candidates.append(
            _Candidate(
                point=point,
                state=state,
                captured=captured,
                root_score=score,
                score=score,
                reason_code=reason_code,
                reason_text=reason_text,
            )
        )
    return candidates


def _standard_scores(game, candidates, perspective, model=None):
    """Apply a full opponent-reply scan to the best ten root candidates."""
    ranked = sorted(candidates, key=lambda item: item.root_score, reverse=True)
    searched = []
    nodes = len(candidates)
    reply_color = other(game.to_move)
    for candidate in ranked[:10]:
        history = set(game.history)
        history.add(signature(game.board, candidate.state, reply_color))
        replies = []
        for point in game.board.points:
            try:
                state, captured = resolve(
                    game.board,
                    candidate.state,
                    point,
                    reply_color,
                    history,
                )
            except Illegal:
                continue
            nodes += 1
            replies.append(
                evaluate_state(
                    game.board, state, perspective, game.moves_played + 2, model
                )
                + CAPTURE_WEIGHT * candidate.captured
                - CAPTURE_WEIGHT * captured
            )
        worst = min(replies) if replies else candidate.root_score
        searched.append(replace(candidate, score=worst))
    return searched, nodes


def _choose_candidate(game, difficulty, seed, perspective, model=None):
    evaluation_model = model if difficulty == "advanced" else None
    candidates = _root_candidates(game, perspective, evaluation_model)
    nodes = len(candidates)
    if not candidates:
        return None, nodes, candidates
    if difficulty in ("standard", "advanced"):
        pool, nodes = _standard_scores(
            game, candidates, perspective, evaluation_model
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


def _swap_value(game, computer_color, model=None):
    """Worst value after the human's best White reply following a swap."""
    assert computer_color == BLACK
    replies = []
    for point in game.legal_placements():
        state, captured = game.try_play(point)
        replies.append(
            evaluate_state(
                game.board, state, computer_color, game.moves_played + 1, model
            )
            - CAPTURE_WEIGHT * captured
        )
    return min(replies) if replies else evaluate_state(
        game.board, game.state, computer_color, game.moves_played, model
    )


def choose_decision(game, computer_color, difficulty="standard", seed=1, model=None):
    """Choose one computer action without mutating ``game``."""
    started = time.perf_counter()
    if difficulty not in DIFFICULTIES:
        raise ValueError("difficulty must be casual, standard, or advanced")
    if computer_color not in (BLACK, WHITE):
        raise ValueError("computer color must be B or W")

    if game.finished:
        if not game.resumption_used:
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
        stay, nodes, _ = _choose_candidate(game, difficulty, seed, WHITE, model)
        stay_value = stay.score if stay else evaluate_state(
            game.board,
            game.state,
            WHITE,
            game.moves_played,
            model if difficulty == "advanced" else None,
        )
        swap_value = _swap_value(
            game, BLACK, model if difficulty == "advanced" else None
        )
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
        game, difficulty, seed, computer_color, model
    )
    if chosen is None:
        decision = BotDecision(
            action="pass",
            reason_code="pass",
            reason_text="Passed because no placement is legal.",
            nodes=nodes,
        )
    else:
        baseline = evaluate_state(
            game.board,
            game.state,
            computer_color,
            game.moves_played,
            model if difficulty == "advanced" else None,
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
