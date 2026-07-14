import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from cairn import BLACK

from research.harness.map_elites_v3 import (
    DESCRIPTORS,
    WEIGHT_BOUNDS,
    _make_batch,
    _runtime_weights,
    audited_mutation_bounds,
    archive_cell,
    archive_insert,
    balanced_genome,
    calibration_edges,
    derive_seed,
    mutate_genome,
    play_rollout,
    random_genome,
    refresh_hall_of_fame,
    run_optimizer,
    stable_hash,
)
from opponent import BALANCED_WEIGHTS


def synthetic_evaluator(task):
    candidate_id = task["candidate_id"]
    descriptors = {
        name: (derive_seed(991, candidate_id, name) % 1001) / 1000
        for name in DESCRIPTORS
    }
    quality = (derive_seed(991, candidate_id, "quality") % 1001) / 1000
    result = {
        "candidate_id": candidate_id,
        "kind": task["kind"],
        "parent_id": task.get("parent_id"),
        "genome": dict(task["genome"]),
        "genome_hash": stable_hash(task["genome"]),
        "opponents": [
            {"id": item["id"], "genome_hash": stable_hash(item["genome"])}
            for item in task["opponents"]
        ],
        "games": [],
        "games_attempted": 8,
        "games_incomplete": 0,
        "descriptors": descriptors,
        "score_rate": quality,
        "margin_quality": quality,
        "quality": quality,
        "rejected": False,
        "errors": [],
    }
    result["result_hash"] = stable_hash(result)
    return result


def incomplete_first_evaluator(task):
    result = synthetic_evaluator(task)
    if task["candidate_id"] == 0:
        result["games_incomplete"] = 8
        result["quality"] = None
        result["rejected"] = True
        result["errors"] = ["watchdog_incomplete"]
        result["result_hash"] = stable_hash(
            {key: value for key, value in result.items() if key != "result_hash"}
        )
    return result


def sample_result(candidate_id, quality, descriptors=None):
    return {
        "candidate_id": candidate_id,
        "quality": quality,
        "descriptors": descriptors
        or {name: 0.25 for name in DESCRIPTORS},
        "genome": balanced_genome(),
        "genome_hash": stable_hash(balanced_genome()),
        "rejected": False,
    }


class TestQualityDiversityPrimitives(unittest.TestCase):
    def test_exact_balanced_genome_uses_parity_locked_runtime_mapping(self):
        self.assertIs(_runtime_weights(balanced_genome()), BALANCED_WEIGHTS)

    def test_audit_rejected_features_are_frozen_at_zero(self):
        with TemporaryDirectory() as directory:
            decisions = {
                name: {"accepted_for_optimization": name == "covers"}
                for name in (
                    "control_resilience",
                    "latent_reserves",
                    "sky_durability",
                    "connection",
                    "capturing_moves",
                    "max_capture",
                    "covers",
                    "hostile_covers",
                    "reinforcements",
                    "summits",
                )
            }
            payload = {
                "format": "varde-evaluator-audit",
                "version": 3,
                "status": "complete",
                "analysis": {"candidate_decisions": decisions},
            }
            payload["report_hash"] = stable_hash(payload)
            path = Path(directory) / "audit.json"
            path.write_text(json.dumps(payload))
            bounds, report_hash, accepted = audited_mutation_bounds(path)
            self.assertEqual(report_hash, payload["report_hash"])
            self.assertEqual(accepted, ("covers",))
            self.assertNotEqual(bounds["covers"], (0.0, 0.0))
            self.assertEqual(bounds["connection"], (0.0, 0.0))
            genome = random_genome(8, 2, bounds)
            self.assertEqual(genome["connection"], 0.0)

    def test_random_and_mutated_genomes_are_deterministic_and_bounded(self):
        first = random_genome(17, 4)
        self.assertEqual(first, random_genome(17, 4))
        self.assertNotEqual(first, random_genome(17, 5))
        child = mutate_genome(first, 17, 99)
        self.assertEqual(child, mutate_genome(first, 17, 99))
        self.assertNotEqual(first, child)
        for name, value in child.items():
            lower, upper = WEIGHT_BOUNDS[name]
            self.assertGreaterEqual(value, lower)
            self.assertLessEqual(value, upper)

    def test_four_axis_calibration_and_binning(self):
        results = [
            {
                "descriptors": {
                    name: index / 7 for name in DESCRIPTORS
                }
            }
            for index in range(8)
        ]
        edges = calibration_edges(results)
        self.assertEqual(tuple(edges), DESCRIPTORS)
        self.assertEqual(archive_cell({name: 0.0 for name in DESCRIPTORS}, edges), (0, 0, 0, 0))
        self.assertEqual(archive_cell({name: 1.0 for name in DESCRIPTORS}, edges), (3, 3, 3, 3))

    def test_archive_replaces_only_on_strict_quality_improvement(self):
        edges = {name: [0.25, 0.5, 0.75] for name in DESCRIPTORS}
        archive = {}
        first = sample_result(1, 0.5)
        self.assertIsNotNone(archive_insert(archive, first, edges))
        self.assertIsNone(archive_insert(archive, sample_result(2, 0.5), edges))
        replacement = archive_insert(archive, sample_result(3, 0.6), edges)
        self.assertEqual(replacement["replaced_candidate_id"], 1)
        self.assertEqual(archive["1,1,1,1"]["candidate_id"], 3)

    def test_hall_of_fame_contains_balanced_quality_and_extremes(self):
        attempts = [
            sample_result(
                index,
                0.5 + index / 100,
                {
                    name: (index + offset) / 10
                    for offset, name in enumerate(DESCRIPTORS)
                },
            )
            for index in range(5)
        ]
        hall = refresh_hall_of_fame(attempts)
        self.assertEqual(hall[0]["id"], "balanced")
        self.assertIn(4, {item["candidate_id"] for item in hall})
        self.assertLessEqual(len(hall), 6)


class TestQualityDiversityRun(unittest.TestCase):
    def test_resume_and_worker_count_are_byte_identical(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            full = root / "full"
            resumed = root / "resumed"
            common = {
                "seed": 42,
                "checkpoint_interval": 3,
                "calibration_count": 8,
                "mutations": 8,
                "batch_size": 4,
                "difficulty": "standard",
                "evaluator": synthetic_evaluator,
            }
            run_optimizer(full, workers=1, **common)
            paused = run_optimizer(
                resumed, workers=3, max_candidates=5, **common
            )
            self.assertEqual(paused["status"], "paused")
            run_optimizer(resumed, workers=4, resume=True, **common)
            self.assertEqual(
                (full / "state.json").read_bytes(),
                (resumed / "state.json").read_bytes(),
            )

    def test_batch_freezes_hall_and_assigns_candidate_owned_opponents(self):
        with TemporaryDirectory() as directory:
            state = run_optimizer(
                Path(directory),
                seed=7,
                workers=2,
                checkpoint_interval=2,
                calibration_count=4,
                mutations=0,
                batch_size=4,
                evaluator=synthetic_evaluator,
            )
            state["target_candidates"] = 8
            batch = _make_batch(state)
            self.assertEqual(batch["start"], 4)
            self.assertEqual(batch["stop"], 8)
            self.assertEqual(
                batch["frozen_hall_hash"], stable_hash(state["hall_of_fame"])
            )
            for task in batch["tasks"]:
                self.assertEqual(
                    [item["id"] for item in task["opponents"][:2]],
                    ["balanced", "balanced"],
                )
                expected = derive_seed(
                    state["master_seed"],
                    "game",
                    task["candidate_id"],
                    0,
                )
                self.assertEqual(
                    expected,
                    derive_seed(
                        state["master_seed"],
                        "game",
                        task["candidate_id"],
                        0,
                    ),
                )

    def test_cancel_then_resume_and_incomplete_attempt_accounting(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            cancel = root / "cancel"
            cancel.touch()
            state = run_optimizer(
                root / "cancelled",
                seed=5,
                calibration_count=4,
                mutations=0,
                batch_size=4,
                cancel_file=cancel,
                evaluator=synthetic_evaluator,
            )
            self.assertEqual(state["status"], "cancelled")
            self.assertEqual(state["next_candidate"], 0)
            cancel.unlink()
            state = run_optimizer(
                root / "cancelled",
                seed=5,
                calibration_count=4,
                mutations=0,
                batch_size=4,
                resume=True,
                evaluator=synthetic_evaluator,
            )
            self.assertEqual(state["status"], "complete")

            incomplete = run_optimizer(
                root / "incomplete",
                seed=5,
                calibration_count=4,
                mutations=0,
                batch_size=4,
                evaluator=incomplete_first_evaluator,
            )
            self.assertEqual(incomplete["counters"]["candidates_rejected"], 1)
            self.assertEqual(incomplete["counters"]["games_incomplete"], 8)
            self.assertEqual(incomplete["counters"]["candidates_attempted"], 4)

    def test_checkpoint_hash_detects_tampering(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            run_optimizer(
                root,
                calibration_count=4,
                mutations=0,
                batch_size=4,
                evaluator=synthetic_evaluator,
            )
            path = root / "state.json"
            payload = json.loads(path.read_text())
            payload["master_seed"] += 1
            path.write_text(json.dumps(payload))
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                run_optimizer(
                    root,
                    seed=payload["master_seed"],
                    calibration_count=4,
                    mutations=0,
                    batch_size=4,
                    resume=True,
                    evaluator=synthetic_evaluator,
                )

    def test_real_rollout_finishes_legally_under_research_watchdog(self):
        result = play_rollout(
            balanced_genome(),
            balanced_genome(),
            BLACK,
            seed=123,
            board_size=3,
            pair_slot=0,
            difficulty="casual",
        )
        self.assertTrue(result.complete, result.error)
        self.assertIsNone(result.error)
        self.assertIn(result.final_candidate_color, ("B", "W"))
        self.assertLess(result.actions, 20 * 54)


if __name__ == "__main__":
    unittest.main(verbosity=2)
