import math
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import threading
import unittest

from cairn import BLACK, Game
from learning import (
    FEATURE_NAMES,
    LEGACY_FEATURE_NAMES,
    LearningModel,
    RECIPE,
    TrainingService,
    training_board_size,
)
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
            self.assertEqual(model.games_attempted, 1)
            self.assertTrue(all(math.isfinite(value) for value in model.weights.values()))
            self.assertTrue(all(-4 <= value <= 4 for value in model.weights.values()))
            restored = LearningModel.load(path)
            self.assertEqual(restored.weights, model.weights)
            self.assertEqual(restored.games_trained, 1)
            self.assertEqual(restored.training_seed, 22)
            self.assertEqual(restored.status()["model_version"], 2)
            self.assertEqual(restored.recipe, RECIPE)

    def test_reset_removes_persisted_model(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "advanced-model.json"
            model = LearningModel(path=path)
            model.update([{name: 0.25 for name in FEATURE_NAMES}], 1.0, 3)
            model.save()
            model.reset()
            self.assertFalse(path.exists())
            self.assertEqual(model.games_trained, 0)
            self.assertEqual(model.games_attempted, 0)
            self.assertEqual(set(model.weights.values()), {0.0})

    def test_version_one_model_migrates_without_losing_weights(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "advanced-model.json"
            legacy_weights = {
                name: (index + 1) / 10
                for index, name in enumerate(LEGACY_FEATURE_NAMES)
            }
            path.write_text(json.dumps({
                "format": "cairn-linear-eval",
                "version": 1,
                "weights": legacy_weights,
                "games_trained": 17,
                "training_seed": 44,
                "updated_at": "2026-01-01T00:00:00+00:00",
            }))
            model = LearningModel.load(path)
            self.assertIsNone(model.load_error)
            self.assertEqual(model.games_attempted, 17)
            self.assertEqual(model.games_trained, 17)
            self.assertTrue(model.needs_retraining)
            for name in LEGACY_FEATURE_NAMES:
                self.assertEqual(model.weights[name], legacy_weights[name])
            for name in set(FEATURE_NAMES) - set(LEGACY_FEATURE_NAMES):
                self.assertEqual(model.weights[name], 0.0)
            model.update([{name: 0.0 for name in FEATURE_NAMES}], 0.5, 44)
            self.assertTrue(model.needs_retraining)
            self.assertEqual(model.recipe, "mixed-v1-v2")

    def test_normalized_features_are_bounded_and_color_symmetric(self):
        for n in (3, 4, 5, 6):
            with self.subTest(n=n):
                game = Game(n)
                for _ in range(8):
                    legal = game.legal_placements()
                    if not legal:
                        break
                    game.play(legal[len(legal) // 2])
                features = normalized_features(
                    game.board, game.state, game.moves_played
                )
                self.assertEqual(set(features), set(FEATURE_NAMES))
                self.assertTrue(
                    all(math.isfinite(value) and -1 <= value <= 1
                        for value in features.values())
                )
                swapped = {
                    p: tuple("W" if color == "B" else "B" for color in stack)
                    for p, stack in game.state.items()
                }
                inverted = normalized_features(
                    game.board, swapped, game.moves_played
                )
                for name in FEATURE_NAMES:
                    self.assertAlmostEqual(inverted[name], -features[name])


class TestTrainingService(unittest.TestCase):
    def test_training_board_mix_continues_across_batch_boundaries(self):
        self.assertEqual(
            [training_board_size(index) for index in range(8)],
            [3, 3, 3, 4, 3, 3, 3, 4],
        )

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
            self.assertEqual(status["model"]["games_attempted"], 4)
            self.assertEqual(active.to_dict(), before)

    def test_batch_partitioning_uses_one_global_attempt_sequence(self):
        with TemporaryDirectory() as directory:
            seen_partitioned = []
            seen_single = []

            def runner_for(seen):
                def runner(_model, _seed, index, _cancel):
                    seen.append(index)
                    sample = {
                        name: ((index + offset) % 7) / 7
                        for offset, name in enumerate(FEATURE_NAMES)
                    }
                    return [sample], 0.75, True
                return runner

            partitioned = LearningModel(path=Path(directory) / "partitioned.json")
            service = TrainingService(partitioned, runner_for(seen_partitioned))
            service.start(2, seed=91)
            service.thread.join(timeout=2)
            service.start(3, seed=91)
            service.thread.join(timeout=2)

            single = LearningModel(path=Path(directory) / "single.json")
            other_service = TrainingService(single, runner_for(seen_single))
            other_service.start(5, seed=91)
            other_service.thread.join(timeout=2)

            self.assertEqual(seen_partitioned, [0, 1, 2, 3, 4])
            self.assertEqual(seen_single, seen_partitioned)
            self.assertEqual(partitioned.weights, single.weights)
            self.assertEqual(partitioned.games_attempted, 5)

    def test_discard_advances_cursor_and_seed_change_requires_reset(self):
        with TemporaryDirectory() as directory:
            seen = []

            def runner(_model, _seed, index, _cancel):
                seen.append(index)
                return [], None, False

            model = LearningModel(path=Path(directory) / "model.json")
            service = TrainingService(model, runner=runner)
            service.start(1, seed=12)
            service.thread.join(timeout=2)
            service.start(1, seed=12)
            service.thread.join(timeout=2)
            self.assertEqual(seen, [0, 1])
            self.assertEqual(model.games_attempted, 2)
            self.assertEqual(model.games_trained, 0)
            with self.assertRaisesRegex(ValueError, "reset the model"):
                service.start(1, seed=13)

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
