"""Varde rules engine (reference implementation).

Implements the Varde rules document (rev 1.3) exactly:
board, terrain, summits, skies with placed-this-turn exclusion,
simultaneous capture waves with per-wave re-evaluation, global
mover suicide, situational superko over full stacks, scoring,
two-pass ending with one resumption, and the stagnation ending
(NO_PROGRESS_LIMIT quiet moves end the game finally).

Colors are 'B' and 'W'. A stack is a tuple of colors, bottom to top.
Points are integer (x, y) pairs on an exact scaled lattice.
"""

from collections import deque

BLACK, WHITE = "B", "W"

# A move is "quiet" when it captures nothing and changes no column's
# control: a pass, or a placement onto a column the mover already
# controls. This many consecutive quiet moves end the game finally.
NO_PROGRESS_LIMIT = 12


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


def group_has_ring(board, comp):
    """True when the group's columns contain a closed ring.

    A connected component has a cycle exactly when it has at least as
    many internal adjacencies as members (a tree has one fewer). The
    honeycomb lattice has girth six, so any ring encircles a cell.
    """
    members = set(comp)
    edges = sum(
        1 for p in comp for nb in board.neighbors[p] if nb in members
    ) // 2
    return edges >= len(comp)


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


def group_alive(board, state, comp, placed, rules="classic"):
    """A group has a liberty at an adjacent empty point or through skies.

    Classic rules: a sky above any member column strictly lower than all
    its neighbors (top stone not placed this turn).

    Rosette rules: a suffocated group breathes through skies only if its
    columns contain a closed ring — life is enclosure. (Every ring has
    at least six columns, so some member's top predates this turn.)
    """
    for p in comp:
        for nb in board.neighbors[p]:
            if not state[nb]:
                return True
    if rules == "rosette":
        return group_has_ring(board, comp)
    if rules in BREATH_RULESETS:
        return False  # flat game: empty-adjacent points are the only liberties
    for p in comp:
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


def _enemy_column_is_sky_bound(board, state, p, color):
    """Rosette stacking gate: `p` must belong to an enemy group whose
    only liberties are skies (no adjacent empty point anywhere)."""
    if control(state, p) != other(color):
        return False
    seen = {p}
    dq = deque([p])
    while dq:
        q = dq.popleft()
        for nb in board.neighbors[q]:
            if not state[nb]:
                return False
            if nb not in seen and control(state, nb) == control(state, p):
                seen.add(nb)
                dq.append(nb)
    return True


def resolve(
    board, state, p, color, history, trace=None, rules="classic",
    allow_stack=False,
):
    """Attempt the placement.  Returns (new_state, captured_count).

    Raises Illegal(reason) if any step fails.  `state` is not mutated.
    `history` is a set of signatures already recorded.  `allow_stack`
    is used only by breath-cap rescue extensions, which may land on an
    occupied point.
    """
    # 0. rosette stacking gate: occupied columns accept a stone only when
    #    they belong to an enemy group breathing through skies alone.
    #    Breath rulesets are flat games: no stacking except cap rescues.
    if state[p]:
        if rules in BREATH_RULESETS and not allow_stack:
            raise Illegal("stack")
        if rules == "rosette" and not _enemy_column_is_sky_bound(
            board, state, p, color
        ):
            raise Illegal("stack")

    # 1. terrain and summits govern the stacked rulesets only; breath
    #    games are flat (a cap rescue lands unconditionally)
    summit = False
    if rules not in BREATH_RULESETS:
        if not terrain_ok(board, state, p):
            raise Illegal("terrain")
        summit = is_summit(board, state, p)

    # 2. provisional placement; the new stone controls its column at once
    st = dict(state)
    st[p] = st[p] + (color,)
    placed = p
    enemy = other(color)

    # 2b. breath-first: the placed group must have a liberty counted
    #     before any removals — capture never legalizes a breathless stone
    if rules in BREATH_RULESETS:
        comp = next(
            g for g in groups_of(board, st, color) if p in g
        )
        if not group_alive(board, st, comp, placed, rules):
            raise Illegal("suicide")

    # 3. summit: two-of-three majority, or an enemy group without a liberty
    #    at this moment, before any removal
    if summit:
        majority = sum(
            1 for nb in board.neighbors[p] if control(st, nb) == color
        ) >= 2
        if not majority:
            captures_now = any(
                not group_alive(board, st, g, placed, rules)
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
            if not group_alive(board, st, g, placed, rules)
        ]
        if not dead:
            break
        cols = [q for g in dead for q in g]
        if trace is not None:
            trace.append(tuple(cols))
        for q in cols:
            st[q] = st[q][:-1]
            captured += 1

    # 5. suicide: any group of the mover's without a liberty
    for g in groups_of(board, st, color):
        if not group_alive(board, st, g, placed, rules):
            raise Illegal("suicide")

    # 6. repetition: resulting position with the opponent to move
    if signature(board, st, enemy) in history:
        raise Illegal("repetition")

    return st, captured


# ---------------------------------------------------------------------------
# Game controller: turns, passes, resumption, scoring
# ---------------------------------------------------------------------------
# Extension-rule variants over the breath base. `scope` controls which
# groups may take the free extension and how often within one turn:
#   single   — one extension, one group
#   multi    — any number of distinct one-liberty groups, once each
#   chain    — one group, repeatedly, while it still has one liberty
#   adjacent — one extension on ANY space adjacent to a one-liberty
#              group, empty or occupied (a rescue may cap a stone)
# `after_move` False makes the extensions the entire turn (no normal
# move follows); the turn then ends with finish_extensions().
EXTENSION_RULES = {
    "breath-extend": {"scope": "single", "after_move": True},
    "breath-extend-multi": {"scope": "multi", "after_move": True},
    "breath-extend-run": {"scope": "chain", "after_move": True},
    "breath-rescue": {"scope": "multi", "after_move": False},
    "breath-run": {"scope": "chain", "after_move": False},
    "breath-cap": {"scope": "adjacent", "after_move": True},
}
BREATH_RULESETS = ("breath",) + tuple(EXTENSION_RULES)
RULESETS = ("classic", "rosette") + BREATH_RULESETS


class Game:
    def __init__(self, n=3, rules="classic"):
        if rules not in RULESETS:
            raise ValueError(
                "rules must be one of: " + ", ".join(RULESETS)
            )
        self.rules = rules
        self.board = Board(n)
        self.state = empty_state(self.board)
        self.to_move = BLACK
        self.history = set()
        self.history.add(signature(self.board, self.state, self.to_move))
        self.consecutive_passes = 0
        self.quiet_moves = 0
        self.moves_played = 0
        self.finished = False
        self.no_progress_end = False
        self.resumption_used = False
        self.extension_used = False
        self.extension_points = []
        self.players = {BLACK: "Player 1", WHITE: "Player 2"}
        self.swap_decided = False
        self.last_capture_waves = []

    @property
    def current_player(self):
        return self.players[self.to_move]

    @property
    def swap_available(self):
        return (
            self.moves_played == 1
            and self.to_move == WHITE
            and not self.swap_decided
            and not self.finished
        )

    def take_over(self):
        """Exercise the pie rule after Black's opening placement.

        The board and color to move do not change. Only the human identities
        assigned to Black and White are exchanged; the original first player,
        now White, still makes the next move.
        """
        if not self.swap_available:
            raise Illegal("swap unavailable")
        self.players[BLACK], self.players[WHITE] = (
            self.players[WHITE], self.players[BLACK]
        )
        self.swap_decided = True

    def try_play(self, p):
        """Resolve without committing.  Returns (state, captured) or raises."""
        if self.finished:
            raise Illegal("game over")
        return resolve(
            self.board, self.state, p, self.to_move, self.history,
            rules=self.rules,
        )

    def _eligible_extension_groups(self):
        """Mover's one-liberty groups still eligible this turn, with
        their sole liberties, respecting the ruleset's scope."""
        spec = EXTENSION_RULES.get(self.rules)
        if spec is None or self.finished:
            return []
        scope = spec["scope"]
        if scope in ("single", "adjacent") and self.extension_used:
            return []
        marked = set(self.extension_points)
        out = []
        for comp in groups_of(self.board, self.state, self.to_move):
            libs = {
                nb
                for q in comp
                for nb in self.board.neighbors[q]
                if not self.state[nb]
            }
            if len(libs) != 1:
                continue
            touched = bool(marked & set(comp))
            if scope == "multi" and touched:
                continue          # each group extends at most once
            if scope == "chain" and marked and not touched:
                continue          # the chain stays with one group
            out.append((comp, next(iter(libs))))
        return out

    def _legal_extension(self, p, allow_stack=False):
        try:
            resolve(
                self.board, self.state, p, self.to_move, self.history,
                rules=self.rules, allow_stack=allow_stack,
            )
            return True
        except Illegal:
            return False

    def extension_candidates(self):
        """Points where the mover could legally place a free extension."""
        spec = EXTENSION_RULES.get(self.rules)
        if spec is None:
            return []
        eligible = self._eligible_extension_groups()
        if spec["scope"] == "adjacent":
            points = {
                nb
                for comp, _lib in eligible
                for q in comp
                for nb in self.board.neighbors[q]
            } - {q for comp, _lib in eligible for q in comp}
            return sorted(
                p for p in points
                if self._legal_extension(p, allow_stack=bool(self.state[p]))
            )
        return sorted(
            {lib for _comp, lib in eligible if self._legal_extension(lib)}
        )

    def play_extension(self, p):
        """Freely extend an atari'd group per the ruleset's extension
        scope. The turn does not pass; in the extend-only rulesets the
        turn instead ends with finish_extensions()."""
        spec = EXTENSION_RULES.get(self.rules)
        if spec is None:
            raise Illegal("no extension in this ruleset")
        if self.finished:
            raise Illegal("game over")
        if spec["scope"] in ("single", "adjacent") and self.extension_used:
            raise Illegal("extension already used this turn")
        eligible = self._eligible_extension_groups()
        allow_stack = False
        if spec["scope"] == "adjacent":
            adjacent = {
                nb
                for comp, _lib in eligible
                for q in comp
                for nb in self.board.neighbors[q]
            } - {q for comp, _lib in eligible for q in comp}
            if p not in adjacent:
                raise Illegal("extension must touch a one-liberty group")
            allow_stack = bool(self.state[p])
        else:
            if p not in {lib for _comp, lib in eligible}:
                raise Illegal("extension must fill a group's sole liberty")
        waves = []
        st, captured = resolve(
            self.board, self.state, p, self.to_move, self.history,
            trace=waves, rules=self.rules, allow_stack=allow_stack,
        )
        self.state = st
        self.history.add(signature(self.board, self.state, self.to_move))
        self.extension_used = True
        self.extension_points = self.extension_points + [p]
        self.consecutive_passes = 0
        self.quiet_moves = 0
        self.last_capture_waves = waves
        return captured

    @property
    def extension_only_turn(self):
        """True when extensions were taken in an extend-only ruleset,
        so the turn must end with finish_extensions()."""
        spec = EXTENSION_RULES.get(self.rules)
        return bool(
            spec and not spec["after_move"] and self.extension_used
        )

    def finish_extensions(self):
        """End an extend-only turn after at least one extension."""
        if not self.extension_only_turn:
            raise Illegal("no extension turn to finish")
        self.to_move = other(self.to_move)
        self.history.add(signature(self.board, self.state, self.to_move))
        self.moves_played += 1
        self.consecutive_passes = 0
        self.extension_used = False
        self.extension_points = []
        self.last_capture_waves = []

    def play(self, p):
        if self.finished:
            raise Illegal("game over")
        if self.extension_only_turn:
            raise Illegal("finish the extension turn instead")
        mover = self.to_move
        prior_control = control(self.state, p)
        waves = []
        st, captured = resolve(
            self.board, self.state, p, self.to_move, self.history,
            trace=waves, rules=self.rules,
        )
        was_swap_reply = self.moves_played == 1
        self.state = st
        self.to_move = other(self.to_move)
        self.history.add(signature(self.board, self.state, self.to_move))
        self.consecutive_passes = 0
        if captured or prior_control != mover:
            self.quiet_moves = 0
        else:
            self.quiet_moves += 1
        self.moves_played += 1
        if was_swap_reply:
            self.swap_decided = True
        self.last_capture_waves = waves
        self.extension_used = False
        self.extension_points = []
        if self.quiet_moves >= NO_PROGRESS_LIMIT:
            self.finished = True
            self.no_progress_end = True
        return captured

    def play_pass(self):
        if self.finished:
            raise Illegal("game over")
        if self.extension_only_turn:
            raise Illegal("finish the extension turn instead")
        if self.moves_played == 0:
            raise Illegal("first move must be a placement")
        if self.moves_played == 1:
            self.swap_decided = True
        self.to_move = other(self.to_move)
        self.history.add(signature(self.board, self.state, self.to_move))
        self.consecutive_passes += 1
        self.quiet_moves += 1
        self.moves_played += 1
        if self.consecutive_passes >= 2:
            self.finished = True
        if self.quiet_moves >= NO_PROGRESS_LIMIT:
            self.finished = True
            self.no_progress_end = True
        self.extension_used = False
        self.extension_points = []
        self.last_capture_waves = []

    @property
    def resumption_available(self):
        return (
            self.finished
            and not self.resumption_used
            and not self.no_progress_end
        )

    def demand_resumption(self):
        """Once per game, after two passes; normal turn order continues.

        A stagnation ending is final: it already proves that neither
        player can make progress, so it cannot be reopened.
        """
        if not self.resumption_available:
            raise Illegal("no resumption available")
        self.resumption_used = True
        self.finished = False
        self.consecutive_passes = 0
        self.quiet_moves = 0
        self.last_capture_waves = []

    def legal_placements(self):
        if self.finished:
            return []
        out = []
        for p in self.board.points:
            try:
                resolve(
                    self.board, self.state, p, self.to_move, self.history,
                    rules=self.rules,
                )
                out.append(p)
            except Illegal:
                pass
        return out

    def control_count(self):
        """Points controlled outright, without empty-region attribution."""
        pts = {BLACK: 0, WHITE: 0}
        for p in self.board.points:
            c = control(self.state, p)
            if c:
                pts[c] += 1
        return pts

    def score(self):
        b = self.board
        pts = self.control_count()
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

    def to_dict(self):
        """Return a JSON-compatible, versioned snapshot of the full game."""
        history = [
            {
                "to_move": sig[0],
                "stacks": [list(stack) for stack in sig[1]],
            }
            for sig in sorted(self.history, key=repr)
        ]
        return {
            "format": "varde-game",
            "version": 1,
            "n": self.board.n,
            "rules": self.rules,
            "stacks": [list(self.state[p]) for p in self.board.points],
            "to_move": self.to_move,
            "history": history,
            "consecutive_passes": self.consecutive_passes,
            "quiet_moves": self.quiet_moves,
            "moves_played": self.moves_played,
            "finished": self.finished,
            "no_progress_end": self.no_progress_end,
            "resumption_used": self.resumption_used,
            "extension_used": self.extension_used,
            "extension_points": [list(q) for q in self.extension_points],
            "players": dict(self.players),
            "swap_decided": self.swap_decided,
        }

    @classmethod
    def from_dict(cls, payload):
        """Restore a snapshot created by :meth:`to_dict`."""
        if payload.get("format") not in ("varde-game", "cairn-game") or payload.get("version") != 1:
            raise ValueError("unsupported Varde snapshot")
        n = payload.get("n")
        if not isinstance(n, int) or n < 1:
            raise ValueError("invalid board size")
        rules = payload.get("rules", "classic")
        if rules not in RULESETS:
            raise ValueError("invalid ruleset")
        game = cls(n, rules=rules)

        def parse_stacks(raw):
            if not isinstance(raw, list) or len(raw) != len(game.board.points):
                raise ValueError("invalid stack array")
            parsed = []
            for stack in raw:
                if not isinstance(stack, list) or any(
                    c not in (BLACK, WHITE) for c in stack
                ):
                    raise ValueError("invalid stack")
                parsed.append(tuple(stack))
            return parsed

        stacks = parse_stacks(payload.get("stacks"))
        game.state = dict(zip(game.board.points, stacks))
        if payload.get("to_move") not in (BLACK, WHITE):
            raise ValueError("invalid player to move")
        game.to_move = payload["to_move"]
        game.history = set()
        for item in payload.get("history", []):
            if item.get("to_move") not in (BLACK, WHITE):
                raise ValueError("invalid history")
            old_stacks = parse_stacks(item.get("stacks"))
            game.history.add((item["to_move"], tuple(old_stacks)))
        current = signature(game.board, game.state, game.to_move)
        game.history.add(current)
        game.consecutive_passes = int(payload.get("consecutive_passes", 0))
        game.quiet_moves = int(payload.get("quiet_moves", 0))
        game.moves_played = int(payload.get("moves_played", 0))
        game.finished = bool(payload.get("finished", False))
        game.no_progress_end = bool(payload.get("no_progress_end", False))
        game.resumption_used = bool(payload.get("resumption_used", False))
        game.extension_used = bool(payload.get("extension_used", False))
        game.extension_points = [
            tuple(q) for q in payload.get("extension_points", [])
        ]
        players = payload.get("players", {})
        if set(players) != {BLACK, WHITE} or not all(
            isinstance(name, str) and name for name in players.values()
        ):
            raise ValueError("invalid players")
        game.players = dict(players)
        game.swap_decided = bool(payload.get("swap_decided", False))
        game.last_capture_waves = []
        return game
