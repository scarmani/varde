import math
import unittest

from native_evaluators import (
    FEATURE_NAMES,
    NATIVE_EVALUATOR_HASH,
    NATIVE_EVALUATOR_VERSION,
    NATIVE_EVALUATORS,
    NATIVE_VALUE_PER_POINT_BOUND,
    native_evaluate_state,
    native_evaluators_public,
    native_features,
)
from opponent import _root_candidates, choose_decision
from varde import BLACK, WHITE, CORNERS, Game, other, signature


CANDIDATES = ("classic", "rosette", "breath", "breath-run", "gjerde", "gjerde-go")


def color_swapped(state):
    return {
        point: tuple(other(stone) for stone in stack)
        for point, stack in state.items()
    }


def ring_of_cell(q=0, r=0):
    cx, cy = 3 * q, 2 * r + q
    return [(cx + dx, cy + dy) for dx, dy in CORNERS]


def seal(game, points, color):
    members = set(points)
    for point in points:
        for neighbor in game.board.neighbors[point]:
            if neighbor not in members and not game.state[neighbor]:
                game.state[neighbor] = (color,)


class TestNativeEvaluatorCatalog(unittest.TestCase):
    def test_catalog_is_versioned_hashable_complete_and_immutable(self):
        self.assertEqual(NATIVE_EVALUATOR_VERSION, 1)
        self.assertEqual(set(NATIVE_EVALUATORS), set(CANDIDATES))
        self.assertEqual(len(NATIVE_EVALUATOR_HASH), 64)
        int(NATIVE_EVALUATOR_HASH, 16)
        payload = native_evaluators_public()
        self.assertEqual(payload["hash"], NATIVE_EVALUATOR_HASH)
        self.assertEqual(set(payload["evaluators"]), set(CANDIDATES))
        self.assertTrue(all(
            tuple(item["weights"]) == FEATURE_NAMES
            for item in payload["evaluators"].values()
        ))
        with self.assertRaises(TypeError):
            NATIVE_EVALUATORS["breath"]["capture"] = 0

    def test_all_candidates_are_finite_symmetric_deterministic_and_nonmutating(self):
        for rules in CANDIDATES:
            with self.subTest(rules=rules):
                game = Game(3, rules=rules)
                for index in range(8):
                    legal = game.legal_placements()
                    game.play(legal[(index * 7) % len(legal)])
                before = game.to_dict()
                black = native_evaluate_state(
                    game.board, game.state, BLACK, game.moves_played, rules
                )
                white = native_evaluate_state(
                    game.board, game.state, WHITE, game.moves_played, rules
                )
                repeat = native_evaluate_state(
                    game.board, game.state, BLACK, game.moves_played, rules
                )
                swapped = native_evaluate_state(
                    game.board,
                    color_swapped(game.state),
                    BLACK,
                    game.moves_played,
                    rules,
                )
                self.assertTrue(math.isfinite(black))
                self.assertLessEqual(
                    abs(black), NATIVE_VALUE_PER_POINT_BOUND * len(game.board.points)
                )
                self.assertEqual(black, repeat)
                self.assertEqual(black, -white)
                self.assertEqual(swapped, white)
                self.assertEqual(game.to_dict(), before)

    def test_classic_seeded_search_parity_is_unchanged(self):
        fixtures = (
            (3, "casual", 20260716, (-2, -2), 27, 54),
            (3, "standard", 20260716, (-2, 2), -27, 604),
            (6, "standard", 20260719, (-2, 2), -39, 2386),
        )
        for n, difficulty, seed, point, score, nodes in fixtures:
            with self.subTest(n=n, difficulty=difficulty):
                decision = choose_decision(
                    Game(n), BLACK, difficulty=difficulty, seed=seed
                )
                self.assertEqual(
                    (decision.point, decision.score, decision.nodes),
                    (point, score, nodes),
                )

    def test_native_search_is_legal_deterministic_nonmutating_and_save_compatible(self):
        for rules in CANDIDATES[1:]:
            for difficulty in ("casual", "standard"):
                with self.subTest(rules=rules, difficulty=difficulty):
                    game = Game(3, rules=rules)
                    opening = game.legal_placements()[0]
                    game.play(opening)
                    blocked = game.legal_placements()[0]
                    repeated, _captured = game.try_play(blocked)
                    game.history.add(signature(game.board, repeated, BLACK))
                    legal = set(game.legal_placements())
                    self.assertNotIn(blocked, legal)
                    before = game.to_dict()
                    first = choose_decision(
                        game, WHITE, difficulty=difficulty, seed=20260715
                    )
                    second = choose_decision(
                        Game.from_dict(before),
                        WHITE,
                        difficulty=difficulty,
                        seed=20260715,
                    )
                    self.assertEqual(
                        (first.action, first.point, first.score, first.nodes),
                        (second.action, second.point, second.score, second.nodes),
                    )
                    if first.action == "play":
                        self.assertIn(first.point, legal)
                        self.assertNotEqual(first.point, blocked)
                    self.assertEqual(game.to_dict(), before)


class TestNativeTacticalAdmission(unittest.TestCase):
    def test_classic_collar_stability_and_rosette_ring_structure(self):
        classic = Game(3)
        center = max(classic.board.deep)
        classic.state[center] = (BLACK,)
        for neighbor in classic.board.neighbors[center]:
            classic.state[neighbor] = (WHITE, WHITE, WHITE)
        feature = native_features(classic.board, classic.state, "classic", BLACK)
        self.assertEqual(feature.collar_stability, 1)

        rosette = Game(3, rules="rosette")
        ring = ring_of_cell()
        for point in ring:
            rosette.state[point] = (BLACK,)
        intact = native_features(rosette.board, rosette.state, "rosette", BLACK)
        intact_value = native_evaluate_state(
            rosette.board, rosette.state, BLACK, 6, "rosette"
        )
        rosette.state[ring[0]] = ()
        broken = native_features(rosette.board, rosette.state, "rosette", BLACK)
        broken_value = native_evaluate_state(
            rosette.board, rosette.state, BLACK, 6, "rosette"
        )
        self.assertEqual((intact.cyclic_groups, intact.ring_stones), (1, 6))
        self.assertEqual((broken.cyclic_groups, broken.ring_stones), (0, 0))
        self.assertGreater(intact_value, broken_value)

    def test_rosette_entombment_and_capture_progress_are_admitted(self):
        game = Game(3, rules="rosette")
        ring = ring_of_cell()
        for point in ring:
            game.state[point] = (WHITE,)
        seal(game, ring, BLACK)
        game.moves_played = 10
        game.history = {signature(game.board, game.state, BLACK)}
        feature = native_features(game.board, game.state, "rosette", BLACK)
        self.assertGreater(feature.entombment_caps, 0)
        candidates = _root_candidates(game, BLACK)
        best = max(candidates, key=lambda candidate: candidate.root_score)
        self.assertIn(best.point, ring)
        self.assertEqual(best.captured, 5)

    def test_breath_cavities_cuts_and_capture_threats_are_admitted(self):
        cavity = Game(3, rules="breath")
        center = max(cavity.board.deep)
        for neighbor in cavity.board.neighbors[center]:
            cavity.state[neighbor] = (BLACK,)
        black = native_features(cavity.board, cavity.state, "breath", BLACK)
        self.assertGreaterEqual(black.cavities, 1)
        self.assertGreaterEqual(black.cavity_points, 1)

        cutting = Game(3, rules="breath")
        center = max(cutting.board.deep)
        first, second, capture = cutting.board.neighbors[center]
        cutting.state[first] = (WHITE,)
        cutting.state[second] = (WHITE,)
        cut = native_features(cutting.board, cutting.state, "breath", BLACK)
        self.assertGreaterEqual(cut.cut_points, 1)

        cutting.state[center] = (BLACK,)
        cutting.to_move = WHITE
        cutting.moves_played = 6
        cutting.history = {signature(cutting.board, cutting.state, WHITE)}
        candidates = _root_candidates(cutting, WHITE)
        best = max(candidates, key=lambda candidate: candidate.root_score)
        self.assertEqual(best.point, capture)
        self.assertEqual(best.captured, 1)

    def test_breath_run_values_chase_tempo_without_rewarding_self_squeeze(self):
        game = Game(3, rules="breath-run")
        center = max(game.board.deep)
        first, second, _liberty = game.board.neighbors[center]
        game.state[center] = (BLACK,)
        game.state[first] = (WHITE,)
        game.state[second] = (WHITE,)
        black = native_features(game.board, game.state, "breath-run", BLACK)
        white = native_features(game.board, game.state, "breath-run", WHITE)
        self.assertGreaterEqual(black.self_squeeze, 1)
        self.assertGreaterEqual(white.pressure, 1)
        self.assertGreaterEqual(white.chase_length, 1)
        self.assertGreater(
            native_evaluate_state(game.board, game.state, WHITE, 6, "breath-run"),
            native_evaluate_state(game.board, game.state, BLACK, 6, "breath-run"),
        )

    def test_gjerde_fences_denial_eyes_and_ko_exposure_are_admitted(self):
        game = Game(4, rules="gjerde")
        cell = (0, 0)
        fence = game.board.cell_edges[cell]
        missing = fence[-1]
        for line in fence[:-1]:
            game.state[line] = (BLACK,)
        near = native_features(game.board, game.state, "gjerde", BLACK)
        self.assertGreaterEqual(near.near_fences, 1)
        game.to_move = BLACK
        game.moves_played = 8
        game.history = {signature(game.board, game.state, BLACK)}
        best = max(_root_candidates(game, BLACK), key=lambda item: item.root_score)
        self.assertEqual(best.point, missing)

        game.state[missing] = (WHITE,)
        denied = native_features(game.board, game.state, "gjerde", BLACK)
        self.assertGreater(denied.denial_lines, 0)

        go = Game(4, rules="gjerde-go")
        eye = next(
            point for point in go.board.points
            if len(go.board.neighbors[point]) == 4
        )
        for neighbor in go.board.neighbors[eye]:
            go.state[neighbor] = (BLACK,)
        eye_features = native_features(go.board, go.state, "gjerde-go", BLACK)
        self.assertGreaterEqual(eye_features.eye_space, 1)

        victim = next(
            point for point in go.board.points
            if point != eye and len(go.board.neighbors[point]) == 4
        )
        go.state[victim] = (WHITE,)
        for neighbor in go.board.neighbors[victim][:-1]:
            go.state[neighbor] = (BLACK,)
        ko = native_features(go.board, go.state, "gjerde-go", WHITE)
        self.assertGreaterEqual(ko.ko_exposure, 1)


if __name__ == "__main__":
    unittest.main()
