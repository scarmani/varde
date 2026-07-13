import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from cairn import BLACK, WHITE, Game, control
from learning import LearningModel
from opponent import (
    _features,
    _group_features,
    _root_candidates,
    choose_decision,
)
from test_cairn import find_single_well, put


class TestOpponentEvaluation(unittest.TestCase):
    def test_only_strict_well_counts_as_sky(self):
        game = Game(3)
        core, walls, _ = find_single_well(game.board)
        put(game, core, BLACK)
        for wall in walls:
            put(game, wall, BLACK, BLACK)
        self.assertEqual(
            _features(game.board, game.state, BLACK, game.moves_played).skies,
            1,
        )
        for wall in walls:
            put(game, wall, BLACK)
        self.assertEqual(
            _features(game.board, game.state, BLACK, game.moves_played).skies,
            0,
        )

    def test_sky_is_not_double_counted_as_an_ordinary_liberty(self):
        game = Game(3)
        core = sorted(game.board.deep)[len(game.board.deep) // 2]
        for point in game.board.points:
            put(game, point, BLACK, BLACK)
        put(game, core, BLACK)
        skies, liberties, vulnerable = _group_features(
            game.board, game.state, BLACK
        )
        self.assertGreaterEqual(skies, 1)
        self.assertEqual(liberties, 0)
        self.assertEqual(vulnerable, 0)

    def test_immediate_capture_outranks_quiet_moves(self):
        game = Game(3)
        core = sorted(game.board.deep)[len(game.board.deep) // 2]
        first, second, capture = game.board.neighbors[core]
        put(game, core, BLACK)
        put(game, first, WHITE)
        put(game, second, WHITE)
        game.to_move = WHITE
        candidates = _root_candidates(game, WHITE)
        capturing = next(item for item in candidates if item.point == capture)
        quiet = [item.root_score for item in candidates if item.captured == 0]
        self.assertEqual(capturing.captured, 1)
        self.assertGreater(capturing.root_score, max(quiet))

    def test_all_difficulties_are_legal_deterministic_and_nonmutating(self):
        with TemporaryDirectory() as directory:
            model = LearningModel(path=Path(directory) / "model.json")
            for difficulty in ("casual", "standard", "advanced"):
                with self.subTest(difficulty=difficulty):
                    game = Game(3)
                    before = game.to_dict()
                    legal = set(game.legal_placements())
                    first = choose_decision(
                        game, BLACK, difficulty, seed=71, model=model
                    )
                    second = choose_decision(
                        game, BLACK, difficulty, seed=71, model=model
                    )
                    self.assertEqual(first.action, "play")
                    self.assertIn(first.point, legal)
                    self.assertEqual(first.point, second.point)
                    self.assertEqual(game.to_dict(), before)

    def test_zero_weight_advanced_matches_standard(self):
        with TemporaryDirectory() as directory:
            game = Game(3)
            model = LearningModel(path=Path(directory) / "model.json")
            standard = choose_decision(game, BLACK, "standard", seed=91)
            advanced = choose_decision(
                game, BLACK, "advanced", seed=91, model=model
            )
            self.assertEqual(advanced.point, standard.point)
            self.assertEqual(advanced.score, standard.score)

    def test_decision_uses_engine_superko_filter(self):
        game = Game(3)
        opening = game.board.points[0]
        game.play(opening)
        legal = set(game.legal_placements())
        for difficulty in ("casual", "standard", "advanced"):
            decision = choose_decision(game, WHITE, difficulty, seed=4)
            if decision.action == "play":
                self.assertIn(decision.point, legal)

    def test_finished_game_resumes_only_when_behind(self):
        behind = Game(2)
        behind.play(behind.board.points[0])
        behind.play_pass()
        behind.play_pass()
        self.assertEqual(
            choose_decision(behind, WHITE).action,
            "resume",
        )
        self.assertEqual(
            choose_decision(behind, BLACK).action,
            "accept",
        )

    def test_rationale_reports_capture(self):
        game = Game(3)
        core = sorted(game.board.deep)[len(game.board.deep) // 2]
        first, second, capture = game.board.neighbors[core]
        put(game, core, BLACK)
        put(game, first, WHITE)
        put(game, second, WHITE)
        game.to_move = WHITE
        decision = choose_decision(game, WHITE, "standard", seed=3)
        self.assertEqual(control(game.state, core), BLACK)
        self.assertEqual(decision.point, capture)
        self.assertEqual(decision.reason_code, "capture")


if __name__ == "__main__":
    unittest.main(verbosity=2)
