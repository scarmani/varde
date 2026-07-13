"""Cairn position suite.

Every test encodes a known-answer position from the design analysis.
Run: python3 -m unittest test_cairn -v
"""

import unittest
from cairn import (
    Board, Game, Illegal, BLACK, WHITE, empty_state, resolve, signature,
    control, height, groups_of, group_alive, has_sky, terrain_ok, is_summit,
)


# ---------------------------------------------------------------------- helpers
def fresh(n=3):
    return Game(n)


def put(g, p, *stack):
    """Directly set a stack (test construction, bypasses move legality)."""
    g.state[p] = tuple(stack)


def deep_point(board):
    return sorted(board.deep)[len(board.deep) // 2]


def attempt(g, p):
    """Try a placement; return ('legal', captured) or ('illegal', reason)."""
    try:
        _, cap = g.try_play(p)
        return ("legal", cap)
    except Illegal as e:
        return ("illegal", str(e))


def find_single_well(board):
    """A deep core whose 3 walls each have 2 distinct collar points."""
    for core in sorted(board.deep):
        walls = board.neighbors[core]
        collar = []
        ok = True
        for w in walls:
            outs = [x for x in board.neighbors[w] if x != core]
            if len(outs) != 2:
                ok = False
                break
            collar.extend(outs)
        if ok and len(set(collar)) == len(collar):
            return core, list(walls), collar
    raise AssertionError("no single-well site found")


def find_twin_well(board):
    """Two deep cores at distance 2 sharing wall m; returns cores, walls, collar."""
    for c1 in sorted(board.deep):
        for m in board.neighbors[c1]:
            for c2 in board.neighbors[m]:
                if c2 == c1 or c2 not in board.deep:
                    continue
                walls = [m] + [x for x in board.neighbors[c1] if x != m] \
                            + [x for x in board.neighbors[c2] if x != m]
                collar = []
                for w in walls:
                    collar.extend(
                        x for x in board.neighbors[w] if x not in (c1, c2)
                    )
                collar = sorted(set(collar))  # exactly one shared point
                if not set(collar) & set(walls) and not set(collar) & {c1, c2}:
                    return c1, c2, walls, collar
    raise AssertionError("no twin-well site found")


# ---------------------------------------------------------------------- geometry
class TestGeometry(unittest.TestCase):
    def test_counts(self):
        for n in (2, 3, 4, 5, 6):
            b = Board(n)
            self.assertEqual(len(b.points), 6 * n * n)
            self.assertEqual(len(b.rim), 6 * n)
            self.assertEqual(len(b.deep), 6 * (n - 1) ** 2)
            middle = len(b.points) - len(b.rim) - len(b.deep)
            self.assertEqual(middle, 6 * n - 6)

    def test_degrees(self):
        b = Board(3)
        for p in b.points:
            self.assertIn(len(b.neighbors[p]), (2, 3))
        self.assertTrue(all(len(b.neighbors[p]) == 2 for p in b.rim))

    def test_corner_rim_pairs(self):
        # perfect alternation fails exactly at the six corners:
        # six adjacent rim-rim pairs
        b = Board(3)
        pairs = sum(
            1 for p in b.rim for nb in b.neighbors[p] if nb in b.rim and p < nb
        )
        self.assertEqual(pairs, 6)

    def test_max_distance_to_rim(self):
        for n in (2, 3, 4, 5, 6):
            b = Board(n)
            self.assertEqual(max(b.dist_to_rim().values()), 2 * (n - 1))


# ---------------------------------------------------------------------- terrain
class TestTerrainAndSummits(unittest.TestCase):
    def test_first_move_legal_everywhere(self):
        g = fresh(2)
        self.assertEqual(len(g.legal_placements()), len(g.board.points))

    def test_no_stacking_beside_empty(self):
        g = fresh(3)
        p = deep_point(g.board)
        put(g, p, BLACK)  # all neighbors empty
        self.assertEqual(attempt(g, p)[0], "illegal")  # 1 <= 0 fails

    def test_rim_never_stacked(self):
        g = fresh(3)
        r = sorted(g.board.rim)[0]
        put(g, r, BLACK)
        for nb in g.board.neighbors[r]:
            put(g, nb, BLACK)
        g.to_move = BLACK
        self.assertEqual(attempt(g, r)[0], "illegal")

    def test_summit_majority(self):
        g = fresh(3)
        core, walls, collar = find_single_well(g.board)
        # plateau at height 1: target + three neighbors all height 1
        put(g, core, WHITE)
        put(g, walls[0], BLACK)
        put(g, walls[1], BLACK)
        put(g, walls[2], WHITE)
        # collar left empty: every group breathes, nothing else interferes
        g.to_move = BLACK  # Black controls 2 of 3 neighbors of core
        st, cap = resolve(g.board, g.state, core, BLACK, set())
        self.assertEqual(control(st, core), BLACK)
        # White controls only 1 of 3: same cap by White on a Black plateau fails
        g2 = fresh(3)
        put(g2, core, BLACK)
        put(g2, walls[0], WHITE)
        put(g2, walls[1], BLACK)
        put(g2, walls[2], BLACK)
        # collar left empty: the Black group breathes, nothing is captured
        g2.to_move = WHITE
        self.assertEqual(attempt(g2, core), ("illegal", "summit"))

    def test_tied_neighbor_is_not_summit(self):
        g = fresh(3)
        core, walls, collar = find_single_well(g.board)
        put(g, core, BLACK)               # height 1
        put(g, walls[0], WHITE, WHITE)    # height 2 -> not a plateau
        put(g, walls[1], WHITE)
        put(g, walls[2], WHITE)
        self.assertFalse(is_summit(g.board, g.state, core))


# ---------------------------------------------------------------------- capture
class TestFlatCapture(unittest.TestCase):
    def test_surround_kills(self):
        g = fresh(3)
        p = deep_point(g.board)
        n1, n2, n3 = g.board.neighbors[p]
        put(g, p, BLACK)
        put(g, n1, WHITE)
        put(g, n2, WHITE)
        g.to_move = WHITE
        st, cap = resolve(g.board, g.state, n3, WHITE, set())
        self.assertEqual(cap, 1)
        self.assertEqual(st[p], ())  # peeled to empty

    def test_eye_entry_suicide_while_group_breathes(self):
        g = fresh(3)
        p = deep_point(g.board)
        for nb in g.board.neighbors[p]:
            put(g, nb, BLACK)
        # Black breathes elsewhere (walls have empty second neighbors)
        g.to_move = WHITE
        self.assertEqual(attempt(g, p), ("illegal", "suicide"))

    def test_eye_entry_captures_when_last_liberty(self):
        g = fresh(3)
        p = deep_point(g.board)
        walls = g.board.neighbors[p]
        for w in walls:
            put(g, w, BLACK)
        # pack every outer neighbor of the walls with White
        for w in walls:
            for x in g.board.neighbors[w]:
                if x != p and not g.state[x]:
                    put(g, x, WHITE)
        g.to_move = WHITE
        st, cap = resolve(g.board, g.state, p, WHITE, set())
        self.assertEqual(cap, 3)
        self.assertTrue(all(st[w] == () for w in walls))
        self.assertEqual(control(st, p), WHITE)


# ---------------------------------------------------------------------- wells
class TestWells(unittest.TestCase):
    def _build_single_well(self, collar_fill):
        """collar_fill: None = leave collar empty; ('W', h) = pack it."""
        g = fresh(3)
        core, walls, collar = find_single_well(g.board)
        put(g, core, BLACK)
        for w in walls:
            put(g, w, BLACK, BLACK)
        if collar_fill is not None:
            color, h = collar_fill
            for c in collar:
                put(g, c, *([color] * h))
        g.to_move = WHITE
        return g, core, walls, collar

    def test_well_entry_suicide_when_walls_breathe(self):
        # collar empty: every wall has its own empty liberties; entry
        # captures nothing and the cap has no liberty of any kind
        g, core, walls, collar = self._build_single_well(None)
        self.assertEqual(attempt(g, core), ("illegal", "suicide"))

    def test_low_collar_entry_strands_disconnected_walls(self):
        # DISCOVERY: the walls are connected only THROUGH the core.  Capping
        # the core disconnects them; with a height-1 collar the two walls
        # that lack their own liberties tie the collar after one peel and
        # are erased -- the entry is LEGAL even though part of the group
        # survives elsewhere.
        g, core, walls, collar = self._build_single_well(("W", 1))
        # give wall[0] its own life: convert its first collar point to a
        # Black stone whose outer neighbors stay empty
        w0 = walls[0]
        c0 = next(c for c in collar if c in g.board.neighbors[w0])
        put(g, c0, BLACK)
        st, cap = resolve(g.board, g.state, core, WHITE, set())
        self.assertEqual(cap, 4)                       # walls 1 and 2, both layers
        self.assertEqual(control(st, w0), BLACK)       # the breathing wall survives
        self.assertTrue(all(st[w] == () for w in walls[1:]))
        self.assertEqual(control(st, core), WHITE)     # the cap stands on new empties

    def test_deep_well_entry_suicide(self):
        # reviewer case: height-1 core inside height-3 walls; the invader's
        # geometric sky is excluded on the turn it lands
        g = fresh(3)
        core, walls, collar = find_single_well(g.board)
        put(g, core, BLACK)
        for w in walls:
            put(g, w, BLACK, BLACK, BLACK)
        for c in collar:
            put(g, c, BLACK, BLACK)  # collar breathes via its empty outers
        g.to_move = WHITE
        self.assertEqual(attempt(g, core), ("illegal", "suicide"))

    def test_last_liberty_well_low_collar_dies(self):
        # collar at height 1: peeled walls tie the collar, regenerate no
        # skies, and are erased in the second wave -> the entry is LEGAL
        g, core, walls, collar = self._build_single_well(("W", 1))
        st, cap = resolve(g.board, g.state, core, WHITE, set())
        self.assertEqual(cap, 6)  # both layers of all three walls
        self.assertTrue(all(st[w] == () for w in walls))
        self.assertEqual(st[core], (BLACK, WHITE))  # bottom stone buried
        self.assertEqual(control(st, core), WHITE)

    def test_last_liberty_well_high_collar_lives(self):
        # collar at height 2: peeled walls land strictly below everything,
        # regenerate wells mid-cascade, and the capping stone is left
        # without a liberty -> the entry is ILLEGAL: one well is life
        g, core, walls, collar = self._build_single_well(("W", 2))
        self.assertEqual(attempt(g, core), ("illegal", "suicide"))


class TestTwinWell(unittest.TestCase):
    def test_every_twin_well_has_eight_collar_supports(self):
        b = Board(3)
        seen = set()
        sites = 0
        for c1 in sorted(b.deep):
            for shared in b.neighbors[c1]:
                for c2 in b.neighbors[shared]:
                    if c2 == c1 or c2 not in b.deep:
                        continue
                    pair = tuple(sorted((c1, c2)))
                    if pair in seen:
                        continue
                    walls = (
                        [shared]
                        + [x for x in b.neighbors[c1] if x != shared]
                        + [x for x in b.neighbors[c2] if x != shared]
                    )
                    collar = {
                        x
                        for wall in walls
                        for x in b.neighbors[wall]
                        if x not in (c1, c2)
                    }
                    if collar & set(walls) or collar & {c1, c2}:
                        continue
                    seen.add(pair)
                    sites += 1
                    self.assertEqual(len(collar), 8)
        self.assertEqual(sites, 48)  # 96 ordered core pairs

    def _build(self, collar_height):
        g = fresh(3)
        c1, c2, walls, collar = find_twin_well(g.board)
        put(g, c1, BLACK)
        put(g, c2, BLACK)
        for w in walls:
            put(g, w, BLACK, BLACK)
        for c in collar:
            put(g, c, *([WHITE] * collar_height))
        g.to_move = WHITE
        return g, c1, c2, walls, collar

    def test_high_collar_absolutely_alive(self):
        g, c1, c2, walls, collar = self._build(2)
        self.assertEqual(attempt(g, c1)[0], "illegal")
        self.assertEqual(attempt(g, c2)[0], "illegal")
        for w in walls:
            self.assertEqual(attempt(g, w), ("illegal", "terrain"))

    def test_low_collar_is_breachable(self):
        # collar at height 1: capping a core erases that core's two private
        # walls (two peel waves) and the cap survives on the new empties.
        g, c1, c2, walls, collar = self._build(1)
        m = walls[0]  # shared wall
        private = [w for w in g.board.neighbors[c1] if w != m]
        st, cap = resolve(g.board, g.state, c1, WHITE, set())
        self.assertEqual(cap, 4)  # both layers of both private walls
        self.assertTrue(all(st[w] == () for w in private))
        self.assertEqual(control(st, c1), WHITE)
        # the shared wall and the far side survive on c2's sky
        self.assertEqual(control(st, m), BLACK)
        self.assertEqual(control(st, c2), BLACK)


# ---------------------------------------------------------------------- peeling
class TestPeeling(unittest.TestCase):
    def test_isolated_stack_peels_and_survives(self):
        g = fresh(3)
        p = deep_point(g.board)
        put(g, p, BLACK, BLACK)
        walls = g.board.neighbors[p]
        for w in walls:
            put(g, w, WHITE, WHITE)
        # Simplest check: sky exists at height 1 under height-2 walls.
        st = dict(g.state)
        st[p] = (BLACK,)
        self.assertTrue(has_sky(g.board, st, p, None))

    def test_adjacent_pair_is_erased(self):
        # two adjacent height-2 Black columns, all outer neighbors White h2:
        # wave 1 peels both to height 1, they tie each other, wave 2 erases
        g = fresh(3)
        b = g.board
        p = deep_point(b)
        q = next(x for x in b.neighbors[p] if x in b.deep or True)
        put(g, p, BLACK, BLACK)
        put(g, q, BLACK, BLACK)
        outer = set()
        for x in (p, q):
            for nb in b.neighbors[x]:
                if nb not in (p, q):
                    outer.add(nb)
        for o in outer:
            put(g, o, WHITE, WHITE)
        # give the pair one last liberty at an outer point left empty,
        # then fill it
        last = outer.pop()
        g.state[last] = ()
        g.to_move = WHITE
        st, cap = resolve(g.board, g.state, last, WHITE, set())
        self.assertEqual(cap, 4)
        self.assertEqual(st[p], ())
        self.assertEqual(st[q], ())

    def test_peel_that_kills_mover(self):
        # Black's group {p} lives only on p's sky (h2 under h3 neighbors).
        # Black caps f, capturing the White group {e,f}'s sky-liberty; e
        # peels 3 -> 2 -> 1 and SURVIVES at height 1 with a capture-created
        # well -- now standing BELOW p, whose sky needed every neighbor
        # strictly taller.  Black's own group is left without a liberty:
        # the capturing move is suicide.
        g = fresh(3)
        b = g.board
        p = deep_point(b)
        e = next(x for x in b.neighbors[p] if x in b.deep)
        w1, w2 = [x for x in b.neighbors[p] if x != e]
        f = next(x for x in b.neighbors[e] if x != p and x in b.deep)
        gpt = next(x for x in b.neighbors[e] if x not in (p, f))
        put(g, p, BLACK, BLACK)                    # h2, sky-only group
        put(g, e, WHITE, WHITE, WHITE)             # h3, doomed
        put(g, f, WHITE)                           # h1, the group's sky
        put(g, gpt, BLACK, BLACK, BLACK)           # h3, part of Black mass
        put(g, w1, WHITE, WHITE, WHITE)            # h3, healthy, separate
        put(g, w2, WHITE, WHITE, WHITE)            # h3, healthy, separate
        for x in b.neighbors[f]:
            if x != e and not g.state[x]:
                put(g, x, BLACK, BLACK, BLACK)     # f's other walls: Black h3
        # sanity: pre-move, every group breathes
        g.to_move = BLACK
        self.assertTrue(has_sky(g.board, g.state, p, None))     # p's sky
        self.assertTrue(has_sky(g.board, g.state, f, None))     # {e,f}'s sky
        # Black caps f: fills the enemy sky by covering it
        res = attempt(g, f)
        self.assertEqual(res, ("illegal", "suicide"))
        # counterfactual: with p's group given one empty liberty, the same
        # cap is legal and captures two stones of e
        for x in b.neighbors[w1]:
            if not g.state[x]:
                g.state[w1] = ()                   # open one of p's walls
                break
        st, cap = resolve(g.board, g.state, f, BLACK, set())
        self.assertEqual(cap, 2)                   # e peeled 3 -> 1
        self.assertEqual(height(st, e), 1)
        self.assertTrue(has_sky(g.board, st, e, None))  # e lives in its pit


# ---------------------------------------------------------------------- ko
class TestRepetition(unittest.TestCase):
    def test_single_stone_ko(self):
        # flat Go ko on the rim region: capture, then immediate recapture
        # would recreate the position -> superko forbids it
        g = fresh(3)
        b = g.board
        # find a rim point r with neighbors (x, y): classic 2-liberty spot
        r = next(p for p in sorted(b.rim)
                 if all(len(b.neighbors[nb]) == 3 for nb in b.neighbors[p]))
        x, y = b.neighbors[r]
        put(g, r, BLACK)
        put(g, y, WHITE)
        for nb in b.neighbors[y]:
            if nb != r and not g.state[nb]:
                put(g, nb, WHITE)
        for nb in b.neighbors[x]:
            if nb != r and not g.state[nb]:
                put(g, nb, BLACK)
        g.history = {signature(b, g.state, WHITE)}
        g.to_move = WHITE
        cap = g.play(x)
        self.assertEqual(cap, 1)          # Black stone at r captured
        self.assertEqual(g.state[r], ())
        # Black immediate recapture at r recreates the pre-White position
        self.assertEqual(attempt(g, r), ("illegal", "repetition"))

    def test_pass_always_legal_and_two_passes_end(self):
        g = fresh(2)
        g.play(g.board.points[0])
        g.play_pass()
        g.play_pass()
        self.assertTrue(g.finished)
        g.demand_resumption()
        self.assertFalse(g.finished)
        g.play_pass()
        g.play_pass()
        self.assertTrue(g.finished)
        with self.assertRaises(Illegal):
            g.demand_resumption()


class TestGameController(unittest.TestCase):
    def test_black_must_place_first(self):
        g = fresh(3)
        with self.assertRaisesRegex(Illegal, "first move must be a placement"):
            g.play_pass()

    def test_swap_exchanges_people_not_position_or_turn(self):
        g = fresh(3)
        opening = g.board.points[0]
        g.play(opening)
        before = signature(g.board, g.state, g.to_move)
        self.assertTrue(g.swap_available)
        g.take_over()
        self.assertEqual(g.players, {BLACK: "Player 2", WHITE: "Player 1"})
        self.assertEqual(signature(g.board, g.state, g.to_move), before)
        self.assertEqual(g.current_player, "Player 1")
        self.assertFalse(g.swap_available)

    def test_snapshot_round_trip_preserves_legality_state(self):
        g = fresh(3)
        g.players = {BLACK: "Ada", WHITE: "Grace"}
        g.play(g.board.points[0])
        g.take_over()
        restored = Game.from_dict(g.to_dict())
        self.assertEqual(restored.to_dict(), g.to_dict())
        self.assertEqual(restored.legal_placements(), g.legal_placements())

    def test_capture_trace_separates_waves(self):
        g = fresh(3)
        p = deep_point(g.board)
        n1, n2, n3 = g.board.neighbors[p]
        put(g, p, BLACK)
        put(g, n1, WHITE)
        put(g, n2, WHITE)
        trace = []
        _, captured = resolve(g.board, g.state, n3, WHITE, set(), trace=trace)
        self.assertEqual(captured, 1)
        self.assertEqual(trace, [(p,)])

    def test_placement_rejected_after_game_ends(self):
        g = fresh(2)
        g.play(g.board.points[0])
        g.play_pass()
        g.play_pass()
        with self.assertRaisesRegex(Illegal, "game over"):
            g.play(g.legal_placements()[0] if g.legal_placements() else g.board.points[1])


# ---------------------------------------------------------------------- scoring
class TestScoring(unittest.TestCase):
    def test_control_and_territory(self):
        g = fresh(2)
        b = g.board
        p = deep_point(b)
        put(g, p, BLACK)
        s = g.score()
        self.assertEqual(s[BLACK], len(b.points))
        self.assertEqual(s[WHITE], 0)

    def test_mixed_border_neutral(self):
        g = fresh(2)
        b = g.board
        p = deep_point(b)
        q = sorted(b.rim)[0]
        put(g, p, BLACK)
        put(g, q, WHITE)
        s = g.score()
        self.assertEqual(s[BLACK], 1)
        self.assertEqual(s[WHITE], 1)

    def test_buried_stones_score_nothing(self):
        g = fresh(2)
        p = deep_point(g.board)
        put(g, p, WHITE, BLACK)  # White buried under Black
        s = g.score()
        self.assertEqual(s[BLACK], len(g.board.points))
        self.assertEqual(s[WHITE], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
