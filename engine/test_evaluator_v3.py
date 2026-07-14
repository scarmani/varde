import math
import unittest

from varde import BLACK, WHITE, Game, Illegal, other, resolve, signature
from opponent import (
    BALANCED_WEIGHTS,
    _root_candidates,
    _structural_features,
    _transition_features,
    choose_decision,
    normalized_transition_features,
    normalized_v3_features,
)


PARITY_FIXTURES = (
    ("fresh", 3, "casual", 20260716, "play", (-2, -2), "develop", 27, 54),
    ("fresh", 3, "standard", 20260716, "play", (-2, 2), "develop", -27, 604),
    ("fresh", 4, "casual", 20260717, "play", (-1, 1), "develop", 33, 96),
    ("fresh", 4, "standard", 20260717, "play", (-2, -2), "develop", -31, 1066),
    ("fresh", 5, "casual", 20260718, "play", (2, 0), "develop", 37, 150),
    ("fresh", 5, "standard", 20260718, "play", (2, -2), "develop", -35, 1660),
    ("fresh", 6, "casual", 20260719, "play", (-2, -2), "develop", 39, 216),
    ("fresh", 6, "standard", 20260719, "play", (-2, 2), "develop", -39, 2386),
)


def color_swapped(state):
    return {
        point: tuple(other(stone) for stone in stack)
        for point, stack in state.items()
    }


def transitions_for(board, state, color, history=None):
    history = set() if history is None else history
    transitions = []
    for point in board.points:
        try:
            next_state, captured = resolve(
                board, state, point, color, history
            )
        except Illegal:
            continue
        transitions.append((point, next_state, captured))
    return transitions


class TestBalancedParity(unittest.TestCase):
    def test_named_balanced_weights_are_immutable(self):
        self.assertEqual(BALANCED_WEIGHTS["controlled"], 12)
        self.assertEqual(BALANCED_WEIGHTS["captured"], 35)
        with self.assertRaises(TypeError):
            BALANCED_WEIGHTS["controlled"] = 0

    def test_fresh_seeded_decisions_match_pre_refactor_fixtures(self):
        for fixture in PARITY_FIXTURES:
            (
                _kind,
                n,
                difficulty,
                seed,
                action,
                point,
                reason,
                score,
                nodes,
            ) = fixture
            with self.subTest(n=n, difficulty=difficulty):
                game = Game(n)
                before = game.to_dict()
                decision = choose_decision(
                    game, BLACK, difficulty=difficulty, seed=seed
                )
                self.assertEqual(
                    (
                        decision.action,
                        decision.point,
                        decision.reason_code,
                        decision.score,
                        decision.nodes,
                    ),
                    (action, point, reason, score, nodes),
                )
                self.assertEqual(game.to_dict(), before)

    def test_pie_pass_endings_and_superko_match_pre_refactor_fixtures(self):
        pie = Game(3)
        opening = max(
            pie.board.points,
            key=lambda point: (pie.board.dist_to_rim()[point], point),
        )
        pie.play(opening)
        casual = choose_decision(pie, WHITE, "casual", seed=8042)
        standard = choose_decision(pie, WHITE, "standard", seed=8042)
        self.assertEqual(
            (casual.action, casual.point, casual.score, casual.nodes),
            ("play", (-2, 0), 0, 53),
        )
        self.assertEqual(
            (standard.action, standard.point, standard.score, standard.nodes),
            ("swap", None, 0, 583),
        )

        locked = Game(3)
        distances = locked.board.dist_to_rim()
        for index, point in enumerate(locked.board.points):
            color = BLACK if index % 2 == 0 else WHITE
            locked.state[point] = (color,) * (distances[point] + 1)
        locked.moves_played = len(locked.board.points)
        passed = choose_decision(locked, BLACK, "standard", seed=9)
        self.assertEqual(
            (passed.action, passed.reason_code, passed.score, passed.nodes),
            ("pass", "pass", 0.0, 0),
        )

        finished = Game(2)
        finished.play(finished.board.points[0])
        finished.play_pass()
        finished.play_pass()
        self.assertEqual(choose_decision(finished, WHITE).action, "resume")
        self.assertEqual(choose_decision(finished, BLACK).action, "accept")
        finished.demand_resumption()
        finished.play_pass()
        finished.play_pass()
        self.assertEqual(choose_decision(finished, WHITE).action, "accept")

        superko = Game(3)
        superko.play(superko.board.points[0])
        blocked = superko.legal_placements()[0]
        repeated_state, _ = superko.try_play(blocked)
        superko.history.add(signature(superko.board, repeated_state, BLACK))
        casual = choose_decision(superko, WHITE, "casual", seed=4242)
        standard = choose_decision(superko, WHITE, "standard", seed=4242)
        self.assertEqual(
            (casual.point, casual.score, casual.nodes), ((1, -1), 11, 52)
        )
        self.assertEqual(
            (standard.point, standard.score, standard.nodes),
            ((-1, 1), -18, 582),
        )
        self.assertNotEqual(casual.point, blocked)
        self.assertNotEqual(standard.point, blocked)


class TestV3Measurements(unittest.TestCase):
    def test_constructed_structure_measurements(self):
        game = Game(3)
        center = max(
            game.board.points,
            key=lambda point: (game.board.dist_to_rim()[point], point),
        )
        first, second, third = game.board.neighbors[center]
        game.state[first] = (BLACK, BLACK)
        game.state[second] = (BLACK, WHITE)
        game.state[third] = (BLACK, BLACK, BLACK)
        game.state[center] = (BLACK,)

        black = _structural_features(game.board, game.state, BLACK)
        white = _structural_features(game.board, game.state, WHITE)
        self.assertGreaterEqual(black.control_resilience, 5)
        self.assertEqual(black.latent_reserves, 1)
        self.assertGreaterEqual(black.sky_durability, 1)
        self.assertGreaterEqual(white.control_resilience, 1)

        capped = Game(3)
        capped.state[center] = (WHITE, BLACK, BLACK, BLACK)
        capped_black = _structural_features(
            capped.board, capped.state, BLACK
        )
        self.assertEqual(capped_black.control_resilience, 2)

        reserves = Game(3)
        reserves.state[center] = (BLACK, BLACK, WHITE)
        reserve_black = _structural_features(
            reserves.board, reserves.state, BLACK
        )
        self.assertEqual(reserve_black.latent_reserves, 2)

        durable = Game(3)
        durable.state[center] = (BLACK,)
        for neighbor in durable.board.neighbors[center]:
            durable.state[neighbor] = (WHITE,) * 4
        durable_black = _structural_features(
            durable.board, durable.state, BLACK
        )
        self.assertEqual(durable_black.sky_durability, 2)

        connection_game = Game(3)
        center = max(
            connection_game.board.points,
            key=lambda point: (
                connection_game.board.dist_to_rim()[point],
                point,
            ),
        )
        first, second, _ = connection_game.board.neighbors[center]
        connection_game.state[first] = (BLACK,)
        connection_game.state[second] = (BLACK,)
        black = _structural_features(
            connection_game.board, connection_game.state, BLACK
        )
        self.assertGreaterEqual(black.connection, 1)

    def test_structural_features_are_bounded_symmetric_and_nonmutating(self):
        for n in (3, 4, 5, 6):
            with self.subTest(n=n):
                game = Game(n)
                for index in range(min(12, len(game.board.points))):
                    legal = game.legal_placements()
                    game.play(legal[(index * 7) % len(legal)])
                before = game.to_dict()
                values = normalized_v3_features(
                    game.board, game.state, game.moves_played
                )
                swapped = normalized_v3_features(
                    game.board,
                    color_swapped(game.state),
                    game.moves_played,
                )
                for name in (
                    "control_resilience",
                    "latent_reserves",
                    "sky_durability",
                    "connection",
                ):
                    self.assertTrue(math.isfinite(values[name]))
                    self.assertLessEqual(abs(values[name]), 1)
                    self.assertAlmostEqual(values[name], -swapped[name])
                self.assertEqual(game.to_dict(), before)

    def test_transition_measurements_reuse_transitions_and_are_symmetric(self):
        game = Game(3)
        center = max(
            game.board.points,
            key=lambda point: (game.board.dist_to_rim()[point], point),
        )
        first, second, _ = game.board.neighbors[center]
        game.state[center] = (WHITE,)
        game.state[first] = (BLACK,)
        game.state[second] = (BLACK,)
        before = game.to_dict()
        black_transitions = transitions_for(game.board, game.state, BLACK)
        white_transitions = transitions_for(game.board, game.state, WHITE)
        black_raw = _transition_features(
            game.board, game.state, BLACK, black_transitions
        )
        self.assertGreater(black_raw.capturing_moves, 0)
        self.assertGreater(black_raw.max_capture, 0)

        mobility = Game(3)
        center = max(
            mobility.board.points,
            key=lambda point: (mobility.board.dist_to_rim()[point], point),
        )
        mobility.state[center] = (WHITE,)
        for neighbor in mobility.board.neighbors[center]:
            mobility.state[neighbor] = (BLACK,)
        mobility_transitions = transitions_for(
            mobility.board, mobility.state, BLACK
        )
        mobility_raw = _transition_features(
            mobility.board, mobility.state, BLACK, mobility_transitions
        )
        self.assertGreater(mobility_raw.covers, 0)
        self.assertGreater(mobility_raw.hostile_covers, 0)
        self.assertGreater(mobility_raw.summits, 0)
        self.assertEqual(
            mobility_raw.hostile_covers + mobility_raw.reinforcements,
            mobility_raw.covers,
        )

        reinforcement = Game(3)
        center = max(
            reinforcement.board.points,
            key=lambda point: (
                reinforcement.board.dist_to_rim()[point],
                point,
            ),
        )
        reinforcement.state[center] = (BLACK,)
        for neighbor in reinforcement.board.neighbors[center]:
            reinforcement.state[neighbor] = (BLACK,)
        reinforcement_raw = _transition_features(
            reinforcement.board,
            reinforcement.state,
            BLACK,
            transitions_for(
                reinforcement.board, reinforcement.state, BLACK
            ),
        )
        self.assertGreater(reinforcement_raw.reinforcements, 0)

        values = normalized_transition_features(
            game.board, game.state, black_transitions, white_transitions
        )
        swapped_state = color_swapped(game.state)
        swapped_black = transitions_for(game.board, swapped_state, BLACK)
        swapped_white = transitions_for(game.board, swapped_state, WHITE)
        swapped = normalized_transition_features(
            game.board, swapped_state, swapped_black, swapped_white
        )
        for name, value in values.items():
            self.assertTrue(math.isfinite(value))
            self.assertLessEqual(abs(value), 1)
            self.assertAlmostEqual(value, -swapped[name])
        self.assertEqual(game.to_dict(), before)

    def test_transition_measurements_are_bounded_on_every_board_size(self):
        for n in (3, 4, 5, 6):
            with self.subTest(n=n):
                game = Game(n)
                for index in range(6):
                    legal = game.legal_placements()
                    game.play(legal[(index * 11) % len(legal)])
                before = game.to_dict()
                black = transitions_for(game.board, game.state, BLACK)
                white = transitions_for(game.board, game.state, WHITE)
                values = normalized_transition_features(
                    game.board, game.state, black, white
                )
                self.assertEqual(
                    set(values),
                    {
                        "capturing_moves",
                        "max_capture",
                        "covers",
                        "hostile_covers",
                        "reinforcements",
                        "summits",
                    },
                )
                for value in values.values():
                    self.assertTrue(math.isfinite(value))
                    self.assertLessEqual(abs(value), 1)
                self.assertEqual(game.to_dict(), before)

    def test_profile_transition_weights_score_generated_covers(self):
        game = Game(3)
        center = max(
            game.board.points,
            key=lambda point: (game.board.dist_to_rim()[point], point),
        )
        game.state[center] = (WHITE,)
        for neighbor in game.board.neighbors[center]:
            game.state[neighbor] = (BLACK,)
        weights = dict(BALANCED_WEIGHTS)
        weights["hostile_covers"] = 25
        candidates = _root_candidates(game, BLACK, weights=weights)
        cover = next(candidate for candidate in candidates if candidate.point == center)
        self.assertEqual(cover.transition_bonus, 25)
        balanced = _root_candidates(game, BLACK)
        balanced_cover = next(
            candidate for candidate in balanced if candidate.point == center
        )
        self.assertEqual(balanced_cover.transition_bonus, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
