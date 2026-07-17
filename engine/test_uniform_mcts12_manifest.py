import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from test_ruleset_evaluation import synthetic_game

from research.harness.audit_uniform_mcts12 import audit_manifest
from research.harness.evaluate_rulesets import (
    build_schedule,
    code_hash,
    run_evaluation,
    stable_hash,
)
from mcts import MCTS_AGENT_HASH
from native_evaluators import NATIVE_EVALUATOR_HASH
from varde import rulesets_public


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = (
    ROOT / "research" / "manifests" / "uniform-mcts12-20260716.json"
)
RESULT_PATH = ROOT / "research" / "results" / "uniform-mcts12-20260716.json"


class TestFrozenUniformMcts12Manifest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(MANIFEST_PATH.read_text())

    def test_exact_independent_job_is_frozen_before_outcomes(self):
        manifest = self.manifest
        self.assertEqual(manifest["status"], "frozen-before-outcomes")
        self.assertEqual(len(manifest["jobs"]), 1)
        job = manifest["jobs"][0]
        config = job["config"]
        self.assertEqual(config["board_sizes"], [4])
        self.assertEqual(config["pairs"], 20)
        self.assertEqual(
            [agent["id"] for agent in config["agents"]],
            ["native-standard", "mcts-uniform@12"],
        )
        self.assertEqual(config["agents"][1]["budget"], 12)
        self.assertEqual(config["agents"][1]["rollout_policy"], "uniform")
        self.assertEqual(config["agents"][1]["hash"], manifest["source"]["mcts_agent_hash"])
        self.assertEqual(config["agents"][0]["hash"], manifest["source"]["native_evaluator_hash"])
        tasks = build_schedule(config)
        self.assertEqual(len(tasks), 240)
        self.assertEqual(stable_hash(config), job["config_sha256"])
        self.assertEqual(stable_hash(tasks), job["schedule_sha256"])

    def test_pairing_and_stage_blockers_are_explicit(self):
        job = self.manifest["jobs"][0]
        pairs = {}
        for task in build_schedule(job["config"]):
            key = (task["rules"], task["matchup"], task["pair_index"])
            pairs.setdefault(key, []).append(task)
        self.assertEqual(len(pairs), 120)
        for legs in pairs.values():
            self.assertEqual([item["leg"] for item in legs], [0, 1])
            self.assertEqual(len({item["seed"] for item in legs}), 1)
            self.assertEqual(
                [item["initial_a_color"] for item in legs], ["B", "W"]
            )
        gate = self.manifest["freeze_gate"]
        self.assertTrue(gate["uniform_mcts24_blocked_until_this_job_audits_cleanly"])
        self.assertTrue(gate["light_rollout_blocked_until_this_job_audits_cleanly"])
        self.assertTrue(self.manifest["claim_limits"]["flagship_promotion_blocked"])

    def test_all_recorded_hashes_are_sha256_values(self):
        source = self.manifest["source"]
        values = [
            source["code_hash"],
            source["ruleset_registry_hash"],
            source["native_evaluator_hash"],
            source["mcts_agent_hash"],
            source["evaluation_harness_sha256"],
            source["audit_harness_sha256"],
            source["fixture_test_sha256"],
            *source["engine_files"].values(),
        ]
        for value in values:
            self.assertRegex(value, r"^[0-9a-f]{64}$")


class TestUniformMcts12Audit(unittest.TestCase):
    def _synthetic_manifest(self, root):
        manifest = copy.deepcopy(json.loads(MANIFEST_PATH.read_text()))
        manifest["source"].update({
            "code_hash": code_hash(),
            "ruleset_registry_hash": stable_hash(rulesets_public()),
            "native_evaluator_hash": NATIVE_EVALUATOR_HASH,
            "mcts_agent_hash": MCTS_AGENT_HASH,
        })
        manifest["candidates"] = manifest["candidates"][:1]
        manifest["fixed_parameters"]["games"] = 2
        manifest["fixed_parameters"]["pairs_per_ruleset_matchup"] = 1
        job = manifest["jobs"][0]
        job["config"]["rulesets"] = ["classic"]
        job["config"]["pairs"] = 1
        job["output_dir"] = str(root / "run")
        tasks = build_schedule(job["config"])
        job["games"] = len(tasks)
        job["config_sha256"] = stable_hash(job["config"])
        job["schedule_sha256"] = stable_hash(tasks)
        return manifest

    def test_compact_audit_accepts_only_a_complete_exact_job(self):
        with TemporaryDirectory() as directory:
            manifest = self._synthetic_manifest(Path(directory))
            job = manifest["jobs"][0]
            run_evaluation(
                job["output_dir"],
                config=job["config"],
                workers=2,
                checkpoint_interval=2,
                evaluator=synthetic_game,
            )
            result = audit_manifest(manifest)

        self.assertEqual(result["accounting"]["complete"], 2)
        self.assertTrue(result["correctness_and_provenance_audit_clean"])
        self.assertTrue(result["next_stage_gate"]["uniform_mcts24_may_be_frozen"])
        self.assertTrue(result["next_stage_gate"]["light_rollout_may_be_frozen"])
        self.assertFalse(result["next_stage_gate"]["later_stages_launched_by_this_unit"])
        self.assertTrue(result["promotion_blocked"])

    def test_audit_rejects_a_different_mcts_budget(self):
        with TemporaryDirectory() as directory:
            manifest = self._synthetic_manifest(Path(directory))
            manifest["jobs"][0]["config"]["agents"][1]["budget"] = 24
            with self.assertRaisesRegex(ValueError, "MCTS agent differs"):
                audit_manifest(manifest)


class TestGeneratedUniformMcts12Audit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(MANIFEST_PATH.read_text())
        cls.result = json.loads(RESULT_PATH.read_text())

    def test_compact_artifact_is_hash_valid_and_operationally_complete(self):
        payload = dict(self.result)
        recorded_hash = payload.pop("payload_hash")
        self.assertEqual(recorded_hash, stable_hash(payload))
        self.assertEqual(
            self.result["manifest_payload_hash"], stable_hash(self.manifest)
        )
        self.assertEqual(
            self.result["accounting"],
            {
                "attempted": 240,
                "complete": 240,
                "illegal": 0,
                "crash": 0,
                "watchdog_incomplete": 0,
                "pending": 0,
            },
        )
        self.assertTrue(
            self.result["correctness_and_provenance_audit_clean"]
        )
        self.assertTrue(self.result["promotion_blocked"])
        self.assertFalse(
            self.result["next_stage_gate"]["later_stages_launched_by_this_unit"]
        )

    def test_result_records_agent_admission_failure_without_a_game_claim(self):
        self.assertEqual(
            self.result["job"]["run_source_commit"],
            "22b2176731d2ca4b98def08c8321a8f88870453e",
        )
        strata = self.result["job"]["strata"]
        self.assertEqual(len(strata), 6)
        for value in strata.values():
            self.assertEqual(value["games_complete"], 40)
            self.assertEqual(value["paired_samples"], 20)
            self.assertFalse(value["headline_eligible"])
            self.assertGreaterEqual(value["agent_a_score_rate"], 0.8875)
        self.assertFalse(
            self.result["claim_limits"]["strategic_depth_evidence"]
        )
        for value in self.result["job"]["raw_artifact_sha256"].values():
            self.assertRegex(value, r"^[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()
