import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest


ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "engine"
HARNESS = ROOT / "research" / "harness"
for path in (ENGINE, HARNESS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from mcts_v5_factorial import (  # noqa: E402
    FACTORIAL_VARIANTS,
    ORDERED_INSTRUMENT,
    audit_records,
    build_manifest,
    build_schedule,
    evaluate_task,
    load_checkpoint,
    run_factorial,
    stable_hash,
    validate_manifest,
)


def synthetic_factorial(task):
    guided = "-g1-" in f"-{task['variant']}-"
    unpruned = "-u1-" in f"-{task['variant']}-"
    settling = task["variant"].endswith("s1")
    return {
        **{
            key: task[key]
            for key in (
                "task_id",
                "kind",
                "variant",
                "position_id",
                "family",
                "width_class",
                "board_size",
                "board_points",
                "decoy",
                "policy",
                "budget",
                "replicate",
                "seed",
            )
        },
        "status": "complete",
        "error": None,
        "action": "synthetic",
        "hit": None if task["decoy"] else True,
        "elapsed_ms": 4.0 if settling else 10.0,
        "average_rollout_actions": 10.0 if settling else 20.0,
        "max_rollout_actions": 10,
        "terminal_backups": task["budget"],
        "solver_status": "guided" if guided else None,
        "solver_nodes": 1 if guided else 0,
        "solver_elapsed_ms": 1.0 if guided else 0.0,
        "solver_invocations": 1 if guided else 0,
        "solver_overrides": 0,
        "oracle_solver_agreement": True if guided else None,
        "exposed_actions": 16 if unpruned else None,
        "hidden_actions": 16 if unpruned else None,
        "mandatory_actions": 1 if unpruned else None,
        "mandatory_visits": [3] if unpruned else [],
        "false_positive_guidance": False,
        "selection_reason": "synthetic",
        "deterministic_decision_sha256": stable_hash(task),
    }


def deterministic_records_hash(records):
    return stable_hash([
        {key: value for key, value in record.items() if key != "elapsed_ms"}
        for record in records
    ])


class TestMCTSV5Factorial(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = build_manifest(output_dir="/tmp/varde-v5-test-output")

    def test_schedule_is_the_frozen_full_factorial_and_instrument(self):
        tasks = build_schedule()
        factorial = [item for item in tasks if item["kind"] == "factorial"]
        instrument = [
            item for item in tasks
            if item["kind"] == "ordered-control-instrument"
        ]
        self.assertEqual(len(tasks), 4_704)
        self.assertEqual(len(factorial), 4_608)
        self.assertEqual(len(instrument), 96)
        self.assertEqual(
            {item["variant"] for item in factorial},
            set(FACTORIAL_VARIANTS),
        )
        self.assertEqual(
            {item["variant"] for item in instrument},
            {ORDERED_INSTRUMENT},
        )
        self.assertEqual([item["task_id"] for item in tasks], list(range(4_704)))
        self.assertEqual(
            stable_hash(tasks),
            self.manifest["configuration"]["task_schedule_sha256"],
        )

    def test_manifest_is_hash_valid_and_preflight_agrees(self):
        self.assertTrue(validate_manifest(self.manifest))
        self.assertTrue(
            self.manifest["preflight"]["declared_oracle_solver_agreement"]
        )
        self.assertTrue(self.manifest["preflight"]["oracle_solver_agreement"])
        self.assertEqual(len(self.manifest["source"]["agent_hashes"]), 9)
        self.assertEqual(
            len(set(self.manifest["source"]["agent_hashes"].values())),
            9,
        )

    def test_checkpoint_resume_matches_uninterrupted_across_workers(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            partitioned = root / "partitioned"
            state = run_factorial(
                self.manifest,
                partitioned,
                workers=3,
                checkpoint_interval=5,
                max_tasks=7,
                evaluator=synthetic_factorial,
            )
            self.assertEqual(state["status"], "paused")
            self.assertEqual(state["next_task"], 7)
            self.assertTrue((partitioned / "progress.json").exists())
            state = run_factorial(
                self.manifest,
                partitioned,
                workers=2,
                checkpoint_interval=997,
                resume=True,
                evaluator=synthetic_factorial,
            )
            self.assertEqual(state["status"], "complete")
            self.assertEqual(state["next_task"], 4_704)

            uninterrupted = run_factorial(
                self.manifest,
                root / "uninterrupted",
                workers=1,
                checkpoint_interval=1_003,
                evaluator=synthetic_factorial,
            )
            self.assertEqual(uninterrupted["status"], "complete")
            self.assertEqual(
                deterministic_records_hash(state["records"]),
                deterministic_records_hash(uninterrupted["records"]),
            )
            audit = audit_records(state["records"], self.manifest)
            self.assertTrue(audit["integrity"]["passed"])
            self.assertIsNone(audit["selection"]["selected_recipe"])

    def test_checkpoint_tamper_is_rejected(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            run_factorial(
                self.manifest,
                root,
                workers=1,
                checkpoint_interval=2,
                max_tasks=2,
                evaluator=synthetic_factorial,
            )
            path = root / "state.json"
            payload = json.loads(path.read_text())
            payload["next_task"] = 0
            path.write_text(json.dumps(payload))
            with self.assertRaisesRegex(ValueError, "checkpoint hash mismatch"):
                load_checkpoint(path)

    def test_real_guided_settling_task_has_complete_integrity(self):
        task = next(
            item for item in build_schedule()
            if item["variant"] == "v5-g1-u1-s1"
            and item["budget"] == 4
            and item["width_class"] == "narrow"
            and not item["decoy"]
        )
        record = evaluate_task(task)
        self.assertEqual(record["status"], "complete", record.get("error"))
        self.assertEqual(record["solver_invocations"], 1)
        self.assertTrue(record["oracle_solver_agreement"])
        self.assertEqual(record["solver_overrides"], 0)
        self.assertEqual(record["terminal_backups"], 4)
        self.assertLessEqual(record["max_rollout_actions"], 4 * task["board_points"])


if __name__ == "__main__":
    unittest.main()
