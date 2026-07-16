import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from mcts import MCTS_AGENT_HASH
from native_evaluators import NATIVE_EVALUATOR_HASH
from test_ruleset_evaluation import synthetic_game
from varde import rulesets_public

from research.harness.audit_native_screening import audit_manifest
from research.harness.evaluate_rulesets import (
    build_schedule,
    code_hash,
    run_evaluation,
    stable_hash,
)


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = (
    ROOT / "research" / "manifests" / "native-screening-v2-20260715.json"
)
RESULT_PATH = ROOT / "research" / "results" / "native-screening-v2-20260715.json"


class TestNativeScreeningManifest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(MANIFEST_PATH.read_text())

    def test_historical_source_and_harness_hashes_are_well_formed(self):
        source = self.manifest["source"]
        self.assertEqual(
            source["main_merge_commit"],
            "78fae9d30e03f603496af7b1af7e423b58facfc4",
        )
        # This manifest records a historical run. Later rules-engine and
        # harness changes must not force us to rewrite its frozen provenance.
        # Runtime compatibility is checked fail-closed by the auditor instead.
        recorded_hashes = [
            source["code_hash"],
            source["ruleset_registry_hash"],
            source["native_evaluator_hash"],
            source["mcts_agent_hash"],
            source["evaluation_harness_sha256"],
            source["audit_harness_sha256"],
            *source["engine_files"].values(),
        ]
        for value in recorded_hashes:
            self.assertRegex(value, r"^[0-9a-f]{64}$")

    def test_schedule_is_exactly_480_unique_paired_color_legs(self):
        rows = []
        pair_seeds = set()
        for job in self.manifest["jobs"]:
            tasks = build_schedule(job["config"])
            self.assertEqual(len(tasks), 240)
            self.assertEqual(stable_hash(job["config"]), job["config_sha256"])
            self.assertEqual(stable_hash(tasks), job["schedule_sha256"])
            pairs = {}
            for task in tasks:
                key = (task["rules"], task["matchup"], task["pair_index"])
                pairs.setdefault(key, []).append(task)
                rows.append([
                    job["id"], task["rules"], task["matchup"],
                    task["pair_index"], task["leg"], task["seed"],
                ])
            self.assertEqual(len(pairs), 120)
            for legs in pairs.values():
                self.assertEqual([item["leg"] for item in legs], [0, 1])
                self.assertEqual(
                    [item["initial_a_color"] for item in legs], ["B", "W"]
                )
                self.assertEqual(len({item["seed"] for item in legs}), 1)
                pair_seeds.add(legs[0]["seed"])
        self.assertEqual(len(rows), 480)
        self.assertEqual(len({tuple(row[:5]) for row in rows}), 480)
        self.assertEqual(len(pair_seeds), 240)
        self.assertEqual(
            stable_hash(rows),
            self.manifest["seed_scheme"]["schedule_tuple_sha256"],
        )

    def test_claim_and_launch_gates_are_explicit(self):
        claims = self.manifest["claim_limits"]
        self.assertTrue(claims["diagnostic_falsification_only"])
        self.assertFalse(claims["independent_agent_family_evidence"])
        self.assertFalse(claims["strategic_depth_evidence"])
        self.assertFalse(claims["balance_evidence"])
        self.assertTrue(claims["flagship_promotion_blocked"])
        self.assertFalse(claims["pool_with_historical_250_simulation_manifest"])
        feasibility = self.manifest["feasibility_gate"]
        self.assertTrue(feasibility["checkpoint_resume_required"])
        self.assertLessEqual(
            feasibility["projected_native_480_game_wall_hours_at_8_workers"],
            feasibility["maximum_launch_wall_hours"],
        )


class TestNativeScreeningOrchestration(unittest.TestCase):
    def test_checkpoint_resume_is_byte_equivalent_without_real_games(self):
        config = copy.deepcopy(
            json.loads(MANIFEST_PATH.read_text())["jobs"][0]["config"]
        )
        config["rulesets"] = ["classic"]
        config["pairs"] = 2
        with TemporaryDirectory() as directory:
            root = Path(directory)
            full = root / "full"
            resumed = root / "resumed"
            run_evaluation(
                full,
                config=config,
                workers=2,
                checkpoint_interval=2,
                evaluator=synthetic_game,
            )
            paused = run_evaluation(
                resumed,
                config=config,
                workers=2,
                checkpoint_interval=2,
                max_games=2,
                evaluator=synthetic_game,
            )
            self.assertEqual(paused["status"], "paused")
            run_evaluation(
                resumed,
                config=config,
                workers=2,
                checkpoint_interval=2,
                resume=True,
                evaluator=synthetic_game,
            )
            for filename in ("state.json", "games.jsonl", "summary.json"):
                self.assertEqual(
                    (full / filename).read_bytes(),
                    (resumed / filename).read_bytes(),
                )

    def test_compact_audit_validates_synthetic_schedule_and_provenance(self):
        manifest = copy.deepcopy(json.loads(MANIFEST_PATH.read_text()))
        manifest["fixed_parameters"]["games"] = 4
        manifest["source"].update({
            "code_hash": code_hash(),
            "ruleset_registry_hash": stable_hash(rulesets_public()),
            "native_evaluator_hash": NATIVE_EVALUATOR_HASH,
            "mcts_agent_hash": MCTS_AGENT_HASH,
        })
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for job in manifest["jobs"]:
                job["config"]["rulesets"] = ["classic"]
                job["config"]["pairs"] = 1
                tasks = build_schedule(job["config"])
                job["games"] = len(tasks)
                job["schedule_sha256"] = stable_hash(tasks)
                job["output_dir"] = str(root / job["id"])
                run_evaluation(
                    job["output_dir"],
                    config=job["config"],
                    workers=2,
                    checkpoint_interval=2,
                    evaluator=synthetic_game,
                )
            audit = audit_manifest(manifest)
            self.assertEqual(audit["accounting"]["attempted"], 4)
            self.assertTrue(audit["correctness_gate_passed"])
            self.assertTrue(audit["promotion_blocked"])


class TestGeneratedNativeScreeningAudit(unittest.TestCase):
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
                "attempted": 480,
                "complete": 480,
                "illegal": 0,
                "crash": 0,
                "watchdog_incomplete": 0,
                "pending": 0,
            },
        )
        self.assertTrue(self.result["correctness_gate_passed"])

    def test_result_remains_native_only_diagnostic_evidence(self):
        self.assertTrue(self.result["promotion_blocked"])
        self.assertEqual(len(self.result["jobs"]), 2)
        for job in self.result["jobs"]:
            self.assertEqual(
                job["run_source_commit"],
                "c31a6986001c5a09e97d023162229d8ffbee838e",
            )
            self.assertEqual(len(job["strata"]), 6)
            for stratum in job["strata"].values():
                self.assertEqual(stratum["paired_samples"], 20)
                self.assertFalse(stratum["headline_eligible"])
            for value in job["raw_artifact_sha256"].values():
                self.assertRegex(value, r"^[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()
