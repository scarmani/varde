"""Cairn rules engine (reference implementation).

Implements the Cairn rules document (rev 1.2) exactly:
board, terrain, summits, skies with placed-this-turn exclusion,
simultaneous capture waves with per-wave re-evaluation, global
mover suicide, situational superko over full stacks, scoring,
two-pass ending with one resumption.

Colors are 'B' and 'W'. A stack is a tuple of colors, bottom to top.
Points are integer (x, y) pairs on an exact scaled lattice.
"""

from collections import deque

BLACK, WHITE = "B", "W"


def other(color):
    return WHITE if color == BLACK else BLACK


# ---------------------------------------------------------------------------
# Board geometry
# ---------------------------------------------------------------------------
# Flat-top hexagon cells in axial coords (q, r), |q|,|r|,|q+r| <= n-1.
# Scaled cartesian (x' = 2x, y' = 2y/sqrt(3)) makes every vertex integer:
# cell center (3q, 2r+q); corners at center + CORNERS.
CORNERS = [(2, 0), (1, 1), (-1, 1), (-2, 0), (-1, -1), (1, -1)]


class Board:
    def __init__(self, n):
        self.n = n
        cells = [
            (q, r)
            for q in range(-(n - 1), n)
            for r in range(-(n - 1), n)
            if abs(q + r) <= n - 1
        ]
        pts = set()
        edges = set()
        for (q, r) in cells:
            cx, cy = 3 * q, 2 * r + q
            corners = [(cx + dx, cy + dy) for (dx, dy) in CORNERS]
            pts.update(corners)
            for i in range(6):
                a, b = corners[i], corners[(i + 1) % 6]
                edges.add(frozenset((a, b)))
        self.points = sorted(pts)
        self.index = {p: i for i, p in enumerate(self.points)}
        nbrs = {p: [] for p in self.points}
        for e in edges:
            a, b = tuple(e)
            nbrs[a].append(b)
            nbrs[b].append(a)
        self.neighbors = {p: tuple(sorted(v)) for p, v in nbrs.items()}
        # missing (phantom) neighbor count: honeycomb vertices have degree 3
        self.phantoms = {p: 3 - len(self.neighbors[p]) for p in self.points}
        self.rim = frozenset(p for p in self.points if self.phantoms[p] > 0)
        self.deep = frozenset(
            p
            for p in self.points
            if p not in self.rim and all(nb not in self.rim for nb in self.neighbors[p])
        )

    def dist_to_rim(self):
        """Graph distance from every point to the nearest rim point."""
        dist = {p: (0 if p in self.rim else None) for p in self.points}
        dq = deque(self.rim)
        while dq:
            p = dq.popleft()
            for nb in self.neighbors[p]:
                if dist[nb] is None:
                    dist[nb] = dist[p] + 1
                    dq.append(nb)
        return dist


# ---------------------------------------------------------------------------
# Position primitives.  state: dict point -> tuple(stack, bottom..top)
# ---------------------------------------------------------------------------
def empty_state(board):
    return {p: () for p in board.points}


def height(state, p):
    return len(state[p])


def control(state, p):
    s = state[p]
    return s[-1] if s else None


def nb_heights(board, state, p):
    """Heights of all three neighbor slots; phantom slots count 0."""
    hs = [height(state, nb) for nb in board.neighbors[p]]
    hs.extend([0] * board.phantoms[p])
    return hs


def terrain_ok(board, state, p):
    """Rule: target height must not exceed that of each neighbor."""
    return height(state, p) <= min(nb_heights(board, state, p))


def is_summit(board, state, p):
    """Pre-placement: target and all three neighbors occupied at same height.

    Phantom columns are never occupied, so rim points are never summits.
    """
    h = height(state, p)
    if h < 1 or board.phantoms[p] > 0:
        return False
    return all(height(state, nb) == h for nb in board.neighbors[p])


def has_sky(board, state, p, placed):
    """Sky: strictly lower than every neighbor, top stone not placed this turn."""
    if p == placed or not state[p]:
        return False
    return height(state, p) < min(nb_heights(board, state, p))


def groups_of(board, state, color):
    """Connected components of columns controlled by `color`."""
    seen = set()
    out = []
    for p in board.points:
        if p in seen or control(state, p) != color:
            continue
        comp = []
        dq = deque([p])
        seen.add(p)
        while dq:
            q = dq.popleft()
            comp.append(q)
            for nb in board.neighbors[q]:
                if nb not in seen and control(state, nb) == color:
                    seen.add(nb)
                    dq.append(nb)
        out.append(comp)
    return out


def group_alive(board, state, comp, placed):
    """A group has a liberty at an adjacent empty point or a member sky."""
    for p in comp:
        for nb in board.neighbors[p]:
            if not state[nb]:
                return True
        if has_sky(board, state, p, placed):
            return True
    return False


def signature(board, state, to_move):
    return (to_move, tuple(state[p] for p in board.points))


# ---------------------------------------------------------------------------
# Placement resolution (rules, steps 1-6)
# ---------------------------------------------------------------------------
class Illegal(Exception):
    pass


def resolve(board, state, p, color, history):
    """Attempt the placement.  Returns (new_state, captured_count).

    Raises Illegal(reason) if any step fails.  `state` is not mutated.
    `history` is a set of signatures already recorded.
    """
    # 1. terrain
    if not terrain_ok(board, state, p):
        raise Illegal("terrain")
    summit = is_summit(board, state, p)

    # 2. provisional placement; the new stone controls its column at once
    st = dict(state)
    st[p] = st[p] + (color,)
    placed = p
    enemy = other(color)

    # 3. summit: two-of-three majority, or an enemy group without a liberty
    #    at this moment, before any removal
    if summit:
        majority = sum(
            1 for nb in board.neighbors[p] if control(st, nb) == color
        ) >= 2
        if not majority:
            captures_now = any(
                not group_alive(board, st, g, placed)
                for g in groups_of(board, st, enemy)
            )
            if not captures_now:
                raise Illegal("summit")

    # 4. capture waves: simultaneous peel, recount, repeat
    captured = 0
    while True:
        dead = [
            g
            for g in groups_of(board, st, enemy)
            if not group_alive(board, st, g, placed)
        ]
        if not dead:
            break
        cols = [q for g in dead for q in g]
        for q in cols:
            st[q] = st[q][:-1]
            captured += 1

    # 5. suicide: any group of the mover's without a liberty
    for g in groups_of(board, st, color):
        if not group_alive(board, st, g, placed):
            raise Illegal("suicide")

    # 6. repetition: resulting position with the opponent to move
    if signature(board, st, enemy) in history:
        raise Illegal("repetition")

    return st, captured


# ---------------------------------------------------------------------------
# Game controller: turns, passes, resumption, scoring
# ---------------------------------------------------------------------------
class Game:
    def __init__(self, n=3):
        self.board = Board(n)
        self.state = empty_state(self.board)
        self.to_move = BLACK
        self.history = set()
        self.history.add(signature(self.board, self.state, self.to_move))
        self.consecutive_passes = 0
        self.moves_played = 0
        self.finished = False
        self.resumption_used = False

    def try_play(self, p):
        """Resolve without committing.  Returns (state, captured) or raises."""
        if self.finished:
            raise Illegal("game over")
        return resolve(self.board, self.state, p, self.to_move, self.history)

    def play(self, p):
        st, captured = self.try_play(p)
        self.state = st
        self.to_move = other(self.to_move)
        self.history.add(signature(self.board, self.state, self.to_move))
        self.consecutive_passes = 0
        self.moves_played += 1
        return captured

    def play_pass(self):
        if self.finished:
            raise Illegal("game over")
        self.to_move = other(self.to_move)
        self.history.add(signature(self.board, self.state, self.to_move))
        self.consecutive_passes += 1
        self.moves_played += 1
        if self.consecutive_passes >= 2:
            self.finished = True

    def demand_resumption(self):
        """Once per game, after two passes; normal turn order continues."""
        if not self.finished or self.resumption_used:
            raise Illegal("no resumption available")
        self.resumption_used = True
        self.finished = False
        self.consecutive_passes = 0

    def legal_placements(self):
        out = []
        for p in self.board.points:
            try:
                resolve(self.board, self.state, p, self.to_move, self.history)
                out.append(p)
            except Illegal:
                pass
        return out

    def score(self):
        b = self.board
        pts = {BLACK: 0, WHITE: 0}
        for p in b.points:
            c = control(self.state, p)
            if c:
                pts[c] += 1
        seen = set()
        for p in b.points:
            if p in seen or self.state[p]:
                continue
            region = []
            border = set()
            dq = deque([p])
            seen.add(p)
            while dq:
                q = dq.popleft()
                region.append(q)
                for nb in b.neighbors[q]:
                    if self.state[nb]:
                        border.add(control(self.state, nb))
                    elif nb not in seen:
                        seen.add(nb)
                        dq.append(nb)
            if len(border) == 1:
                pts[border.pop()] += len(region)
        return pts
