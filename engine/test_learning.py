import math
from pathlib import Path
from tempfile import TemporaryDirectory
import threading
import unittest

from cairn import BLACK, Game
from learning import FEATURE_NAMES, LearningModel, TrainingService
from opponent import normalized_features


class TestLearningModel(unittest.TestCase):
    def test_update_persists_and_reloads_finite_clamped_weights(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "advanced-model.json"
            model = LearningModel(path=path)
            sample = {name: 1.0 for name in FEATURE_NAMES}
            model.update([sample] * 1000, 1.0, seed=22)
            model.save()
            self.assertTrue(path.exists())
            self.assertFalse(path.with_suffix(".json.tmp").exists())
            self.assertEqual(model.games_trained, 1)
            self.assertTrue(all(math.isfinite(value) for value in model.weights.values()))
            self.assertTrue(all(-4 <= value <= 4 for value in model.weights.values()))
            restored = LearningModel.load(path)
            self.assertEqual(restored.weights, model.weights)
            self.assertEqual(restored.games_trained, 1)
            self.assertEqual(restored.training_seed, 22)

    def test_reset_removes_persisted_model(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "advanced-model.json"
            model = LearningModel(path=path)
            model.update([{name: 0.25 for name in FEATURE_NAMES}], 1.0, 3)
            model.save()
            model.reset()
            self.assertFalse(path.exists())
            self.assertEqual(model.games_trained, 0)
            self.assertEqual(set(model.weights.values()), {0.0})

    def test_normalized_features_are_bounded_and_color_symmetric(self):
        game = Game(3)
        point = game.board.points[0]
        game.play(point)
        features = normalized_features(game.board, game.state, game.moves_played)
        self.assertEqual(set(features), set(FEATURE_NAMES))
        self.assertTrue(all(-1 <= value <= 1 for value in features.values()))
        swapped = {
            p: tuple("W" if color == "B" else "B" for color in stack)
            for p, stack in game.state.items()
        }
        inverted = normalized_features(game.board, swapped, game.moves_played)
        for name in FEATURE_NAMES:
            self.assertAlmostEqual(inverted[name], -features[name])


class TestTrainingService(unittest.TestCase):
    def test_background_training_updates_without_touching_active_game(self):
        with TemporaryDirectory() as directory:
            model = LearningModel(path=Path(directory) / "model.json")
            active = Game(3)
            before = active.to_dict()

            def runner(_model, seed, index, cancel):
                sample = {name: (index + 1) / 10 for name in FEATURE_NAMES}
                return [sample], 1.0 if index % 2 == 0 else 0.0, True

            service = TrainingService(model, runner=runner)
            service.start(4, seed=31)
            service.thread.join(timeout=2)
            status = service.status()
            self.assertFalse(status["running"])
            self.assertEqual(status["completed"], 4)
            self.assertEqual(status["model"]["games_trained"], 4)
            self.assertEqual(active.to_dict(), before)

    def test_cancel_and_reset(self):
        with TemporaryDirectory() as directory:
            started = threading.Event()

            def runner(_model, _seed, _index, cancel):
                started.set()
                cancel.wait(1)
                return [], None, False

            model = LearningModel(path=Path(directory) / "model.json")
            service = TrainingService(model, runner=runner)
            service.start(10)
            self.assertTrue(started.wait(1))
            with self.assertRaisesRegex(ValueError, "already running"):
                service.start(10)
            service.cancel()
            service.thread.join(timeout=2)
            self.assertFalse(service.status()["running"])
            self.assertTrue(service.status()["cancel_requested"])
            service.reset()
            self.assertEqual(service.status()["model"]["games_trained"], 0)
            self.assertFalse(service.status()["cancel_requested"])
            self.assertEqual(service.status()["total"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
