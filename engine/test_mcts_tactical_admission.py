import copy
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest


ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "engine"
HARNESS = ROOT / "research" / "harness"
if str(ENGINE) not in sys.path:
    sys.path.insert(0, str(ENGINE))
if str(HARNESS) not in sys.path:
    sys.path.insert(0, str(HARNESS))

from actions import apply_action, legal_actions
from evaluate_rulesets import _agent_action
from mcts_tactical_admission import (
    DEFAULT_BUDGETS,
    DEFAULT_POLICIES,
    DEFAULT_REPLICATES,
    TASK_KEYS,
    build_schedule,
    deterministic_records_hash,
    evaluate_task,
    load_state,
    run_admission,
    stable_hash,
)
from audit_mcts_tactical_admission import _validate_manifest
from mcts_tactical_fixtures import fixture_catalog, tactical_positions
from mcts_telemetry import action_key, annotate_choice, tactical_context


def synthetic_admission(task):
    return {key: task[key] for key in TASK_KEYS} | {
        "root_legal_actions": task["root_legal_actions"],
        "state_key_sha256": task["state_key_sha256"],
        "acceptable_actions": task["acceptable_actions"],
        "status": "complete",
        "error": None,
        "action": task["acceptable_actions"][0],
        "hit": True,
        "state_unchanged": True,
        "captured": 0,
        "decision": {
            "simulations": task["budget"],
            "nodes": task["budget"] + 1,
            "mean_value": 0.5,
            "average_rollout_actions": 12.0,
            "max_rollout_actions": 20,
            "root_coverage_fraction": min(
                1.0, task["budget"] / task["root_legal_actions"]
            ),
        },
        "timing": {"elapsed_ms": float(task["task_id"] % 3)},
        "tactical_context": {},
        "tactical_choice": {},
    }


class TestTacticalFixtureCatalog(unittest.TestCase):
    def test_catalog_covers_all_candidates_and_declared_decision_types(self):
        positions = tactical_positions()
        catalog = fixture_catalog()
        self.assertEqual(len(positions), 10)
        self.assertEqual(len(catalog["positions"]), 10)
        self.assertEqual(
            {position.state.game.rules for position in positions},
            {"classic", "rosette", "breath", "breath-run", "gjerde", "gjerde-go"},
        )
        self.assertTrue({
            "capture", "defense", "takeover", "rescue-chain",
            "fence-completion", "acceptance",
        }.issubset({position.category for position in positions}))
        self.assertEqual(
            sum(position.synthetic_history for position in positions), 1
        )

    def test_every_acceptable_action_is_legal_nonmutating_and_categorized(self):
        for position in tactical_positions():
            with self.subTest(position=position.id):
                state = position.state
                before = state.key()
                context = tactical_context(state)
                legal = set(legal_actions(state))
                self.assertTrue(position.acceptable_actions)
                self.assertTrue(set(position.acceptable_actions).issubset(legal))
                for action in position.acceptable_actions:
                    chosen = annotate_choice(context, action)
                    advanced = apply_action(state, action)
                    self.assertNotEqual(advanced.key(), state.key())
                    if position.category == "capture":
                        self.assertTrue(chosen["chose_maximum_capture"])
                    elif position.category == "defense":
                        self.assertTrue(chosen["chose_defense"])
                    elif position.category == "takeover":
                        self.assertTrue(chosen["chose_takeover"])
                    elif position.category == "rescue-chain":
                        self.assertTrue(chosen["chose_extension"])
                    elif position.category == "fence-completion":
                        self.assertTrue(chosen["chose_fence_completion"])
                self.assertEqual(state.key(), before)

    def test_telemetry_reports_exact_root_opportunities(self):
        contexts = {
            position.id: tactical_context(position.state)
            for position in tactical_positions()
        }
        self.assertEqual(
            contexts["classic-immediate-capture"]["maximum_immediate_capture"], 1
        )
        self.assertEqual(
            contexts["rosette-entombment-cap"]["maximum_immediate_capture"], 5
        )
        self.assertEqual(
            contexts["breath-sole-liberty-defense"]["defense_actions"],
            ["play:-1,1"],
        )
        self.assertTrue(
            contexts["pie-takeover-seat-perspective"]["swap_available"]
        )
        self.assertEqual(
            contexts["breath-run-rescue-chain:continue"]["action_kinds"],
            {"extend": 1, "finish-extension": 1},
        )
        self.assertEqual(
            contexts["gjerde-fence-completion"]["fence_completion_actions"],
            ["play:3,1"],
        )


class TestTacticalAdmissionHarness(unittest.TestCase):
    def _config(self, **updates):
        config = {
            "budgets": [1],
            "policies": ["uniform"],
            "replicates": 1,
            "seed": 20260716,
        }
        config.update(updates)
        return config

    def test_default_schedule_is_deterministic_and_outcome_blind(self):
        config = self._config(
            budgets=list(DEFAULT_BUDGETS),
            policies=list(DEFAULT_POLICIES),
            replicates=DEFAULT_REPLICATES,
        )
        first = build_schedule(config)
        second = build_schedule(copy.deepcopy(config))
        self.assertEqual(first, second)
        self.assertEqual(len(first), 10 * 2 * 3 * 4)
        self.assertNotIn("outcome", first[0])
        self.assertNotIn("score", first[0])

    def test_frozen_manifest_contract_rebuilds_exact_schedule(self):
        path = ROOT / "research/manifests/mcts-tactical-admission-20260716.json"
        manifest = json.loads(path.read_text())
        tasks = _validate_manifest(manifest)
        self.assertEqual(len(tasks), 240)
        self.assertEqual(
            manifest["execution"]["output_dir"],
            "/Users/armand/varde-runs/mcts-tactical-admission-20260716",
        )

    def test_committed_audit_is_clean_negative_admission_evidence(self):
        path = ROOT / "research/results/mcts-tactical-admission-20260716.json"
        payload = json.loads(path.read_text())
        expected_hash = payload.pop("payload_hash")
        self.assertEqual(stable_hash(payload), expected_hash)
        self.assertEqual(payload["accounting"]["complete"], 240)
        self.assertTrue(payload["correctness_and_provenance_audit_clean"])
        self.assertEqual(payload["high_budget_overall_hit_rate"], 0.2625)
        self.assertFalse(payload["admitted"])
        self.assertFalse(
            payload["next_stage_gate"]["paired_mcts24_may_be_frozen"]
        )
        self.assertFalse(
            payload["next_stage_gate"]["paired_match_stage_launched_by_this_unit"]
        )
        self.assertTrue(payload["promotion_blocked"])

    def test_real_takeover_decision_is_legal_telemetric_and_nonmutating(self):
        task = next(
            task for task in build_schedule(self._config(budgets=[2]))
            if task["position_id"] == "pie-takeover-seat-perspective"
        )
        record = evaluate_task(task)
        self.assertEqual(record["status"], "complete")
        self.assertTrue(record["state_unchanged"])
        self.assertEqual(record["action"], "swap")
        self.assertTrue(record["hit"])
        self.assertEqual(record["decision"]["simulations"], 2)
        self.assertGreaterEqual(record["decision"]["nodes"], 2)
        self.assertGreaterEqual(record["decision"]["average_rollout_actions"], 0)
        self.assertGreaterEqual(record["timing"]["elapsed_ms"], 0)
        self.assertTrue(record["tactical_choice"]["chose_takeover"])

    def test_match_harness_retains_mcts_decision_telemetry(self):
        position = next(
            item for item in tactical_positions()
            if item.id == "pie-takeover-seat-perspective"
        )
        action, telemetry = _agent_action(
            position.state,
            {
                "family": "mcts",
                "budget": 2,
                "rollout_policy": "uniform",
            },
            47,
        )
        self.assertEqual(action_key(action), "swap")
        self.assertEqual(telemetry["agent_family"], "mcts")
        self.assertEqual(telemetry["simulations"], 2)
        self.assertIn("nodes", telemetry)
        self.assertIn("average_rollout_actions", telemetry)
        self.assertIn("elapsed_ms", telemetry)

    def test_checkpoint_resume_is_ordered_and_tamper_evident(self):
        config = self._config()
        with TemporaryDirectory() as directory:
            root = Path(directory)
            state = run_admission(
                root,
                config=config,
                workers=3,
                checkpoint_interval=3,
                max_tasks=4,
                evaluator=synthetic_admission,
            )
            self.assertEqual(state["status"], "paused")
            resumed = run_admission(
                root,
                config=config,
                workers=2,
                checkpoint_interval=4,
                resume=True,
                evaluator=synthetic_admission,
            )
            self.assertEqual(resumed["status"], "complete")
            self.assertEqual(
                [record["task_id"] for record in resumed["records"]],
                list(range(10)),
            )
            baseline_hash = deterministic_records_hash(resumed["records"])
            fresh = root / "fresh"
            uninterrupted = run_admission(
                fresh,
                config=config,
                workers=1,
                checkpoint_interval=10,
                evaluator=synthetic_admission,
            )
            self.assertEqual(
                baseline_hash,
                deterministic_records_hash(uninterrupted["records"]),
            )

            checkpoint = root / "state.json"
            payload = json.loads(checkpoint.read_text())
            payload["next_task"] = 0
            checkpoint.write_text(json.dumps(payload))
            with self.assertRaisesRegex(ValueError, "checkpoint hash mismatch"):
                load_state(checkpoint)


if __name__ == "__main__":
    unittest.main()
