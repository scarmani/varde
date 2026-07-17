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

from actions import apply_action, legal_actions, legal_transitions  # noqa: E402
from evaluate_rulesets import _agent_action  # noqa: E402
from mcts_tactical_admission import (  # noqa: E402
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
from audit_mcts_tactical_admission import _validate_manifest  # noqa: E402
from freeze_mcts_tactical_admission import build_manifest  # noqa: E402
from mcts_tactical_fixtures import (  # noqa: E402
    admission_positions,
    diagnostic_positions,
    fixture_catalog,
    tactical_positions,
    validate_transition_proof,
)
from mcts_telemetry import action_key, annotate_choice, tactical_context  # noqa: E402
from mcts import _tactical_priorities, mcts_agent_hash  # noqa: E402


def synthetic_admission(task):
    root_telemetry = [
        {
            "action": {"action": "pass"},
            "action_id": f"synthetic:{index}",
            "final_rank": index + 1,
            "selected": index == 0,
            "visits": task["budget"] if index == 0 else 0,
            "value_sum": task["budget"] * 0.5 if index == 0 else 0.0,
            "mean_value": 0.5,
            "wins": 0,
            "draws": task["budget"] if index == 0 else 0,
            "losses": 0,
            "terminal_margin_count": task["budget"] if index == 0 else 0,
            "terminal_margin_sum": 0,
            "terminal_margin_mean": 0.0 if index == 0 else None,
            "terminal_margin_min": 0 if index == 0 else None,
            "terminal_margin_max": 0 if index == 0 else None,
            "normalized_terminal_margin_count": (
                task["budget"] if index == 0 else 0
            ),
            "normalized_terminal_margin_sum": 0.0,
            "normalized_terminal_margin_mean": 0.0 if index == 0 else None,
            "normalized_terminal_margin_min": 0.0 if index == 0 else None,
            "normalized_terminal_margin_max": 0.0 if index == 0 else None,
        }
        for index in range(task["root_legal_actions"])
    ]
    return {key: task[key] for key in TASK_KEYS} | {
        "root_legal_actions": task["root_legal_actions"],
        "state_key_sha256": task["state_key_sha256"],
        "acceptable_actions": task["acceptable_actions"],
        "evidence_class": task["evidence_class"],
        "proof_sha256": task["proof_sha256"],
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
            "selection_reason": "most-visits",
            "root_action_telemetry": root_telemetry,
            "root_coverage_fraction": min(
                1.0, task["budget"] / task["root_legal_actions"]
            ),
        },
        "timing": {"elapsed_ms": float(task["task_id"] % 3)},
        "tactical_context": {},
        "tactical_choice": {},
    }


class TestTacticalFixtureCatalog(unittest.TestCase):
    def test_tactical_transition_priorities_solve_all_admission_proofs(self):
        for position in admission_positions():
            with self.subTest(position=position.id):
                before = position.state.key()
                transitions = legal_transitions(position.state)
                priorities = _tactical_priorities(position.state, transitions)
                best = max(priorities.values())
                selected = tuple(
                    action
                    for action, _advanced in transitions
                    if priorities[action] == best
                )
                self.assertEqual(selected, position.acceptable_actions)
                self.assertEqual(position.state.key(), before)

    def test_catalog_covers_all_candidates_and_declared_decision_types(self):
        positions = tactical_positions()
        catalog = fixture_catalog()
        self.assertEqual(len(positions), 16)
        self.assertEqual(len(catalog["positions"]), 16)
        self.assertEqual(len(diagnostic_positions()), 10)
        self.assertEqual(len(admission_positions()), 6)
        self.assertEqual(
            {position.state.game.rules for position in positions},
            {"classic", "rosette", "breath", "breath-run", "gjerde", "gjerde-go"},
        )
        self.assertTrue({
            "capture", "defense", "takeover", "rescue-chain",
            "fence-completion", "acceptance",
        }.issubset({position.category for position in positions}))
        self.assertEqual(sum(position.synthetic_history for position in positions), 7)

    def test_admission_positions_have_small_strict_reproducible_proofs(self):
        expected_metrics = {
            "immediate-capture-count",
            "sole-liberty-defense",
            "seat-score-after-action",
            "rescue-continuation",
            "fence-completion",
            "forced-score-acceptance",
        }
        proofs = [
            validate_transition_proof(position)
            for position in admission_positions()
        ]
        self.assertEqual({proof["metric"] for proof in proofs}, expected_metrics)
        self.assertTrue(all(proof["root_actions"] <= 8 for proof in proofs))
        self.assertTrue(all(proof["strict_over_rejected"] for proof in proofs))
        self.assertTrue(all(
            "not a forced game outcome" in proof["claim_limit"]
            for proof in proofs
        ))

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
        self.assertEqual(len(first), 16 * 2 * 3 * 4)
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

    def test_v2_manifest_is_deterministic_split_and_valid_before_outcomes(self):
        config = self._config(
            budgets=list(DEFAULT_BUDGETS),
            policies=list(DEFAULT_POLICIES),
            replicates=DEFAULT_REPLICATES,
        )
        first = build_manifest(
            config,
            output_dir="/tmp/varde-mcts-v2-test",
            workers=2,
            checkpoint_interval=8,
            created_date="2026-07-17",
        )
        second = build_manifest(
            copy.deepcopy(config),
            output_dir="/tmp/varde-mcts-v2-test",
            workers=2,
            checkpoint_interval=8,
            created_date="2026-07-17",
        )
        self.assertEqual(first, second)
        self.assertEqual(first["version"], 2)
        self.assertEqual(first["status"], "frozen-before-outcomes")
        self.assertEqual(first["positions"], 16)
        self.assertEqual(first["decisions"], 384)
        self.assertEqual(first["fixture_contract"]["diagnostic_positions"], 10)
        self.assertEqual(first["fixture_contract"]["admission_positions"], 6)
        self.assertLessEqual(
            first["fixture_contract"]["maximum_admission_root_actions"], 8
        )
        self.assertEqual(len(_validate_manifest(first)), 384)

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

    def test_committed_v2_audit_preserves_split_negative_evidence(self):
        path = ROOT / "research/results/mcts-tactical-admission-v2-20260717.json"
        payload = json.loads(path.read_text())
        expected_hash = payload.pop("payload_hash")
        self.assertEqual(stable_hash(payload), expected_hash)
        self.assertEqual(payload["accounting"]["complete"], 384)
        self.assertEqual(payload["accounting"]["crash"], 0)
        self.assertTrue(payload["correctness_and_provenance_audit_clean"])
        self.assertAlmostEqual(
            payload["high_budget_overall_hit_rate"],
            0.6041666666666666,
        )
        self.assertFalse(payload["admitted"])
        self.assertFalse(
            payload["next_stage_gate"]["paired_mcts24_may_be_frozen"]
        )
        self.assertFalse(
            payload["next_stage_gate"]["paired_match_stage_launched_by_this_unit"]
        )
        self.assertTrue(payload["promotion_blocked"])

    def test_committed_tie_v3_audit_preserves_isolated_regression(self):
        path = ROOT / "research/results/mcts-tactical-tie-v3-20260717.json"
        payload = json.loads(path.read_text())
        expected_hash = payload.pop("payload_hash")
        self.assertEqual(stable_hash(payload), expected_hash)
        self.assertEqual(payload["accounting"]["complete"], 384)
        self.assertEqual(payload["accounting"]["crash"], 0)
        self.assertTrue(payload["correctness_and_provenance_audit_clean"])
        self.assertAlmostEqual(
            payload["high_budget_overall_hit_rate"],
            0.5416666666666666,
        )
        self.assertFalse(payload["admitted"])
        self.assertFalse(
            payload["admission_gate"][
                "aggregate_hit_rate_nondecreasing_by_policy"
            ]
        )
        self.assertTrue(payload["promotion_blocked"])

    def test_committed_margin_v4_audit_preserves_saturation_result(self):
        path = ROOT / "research/results/mcts-tactical-margin-v4-20260717.json"
        payload = json.loads(path.read_text())
        expected_hash = payload.pop("payload_hash")
        self.assertEqual(stable_hash(payload), expected_hash)
        self.assertEqual(payload["accounting"]["complete"], 384)
        self.assertEqual(payload["accounting"]["crash"], 0)
        self.assertTrue(payload["correctness_and_provenance_audit_clean"])
        self.assertAlmostEqual(
            payload["high_budget_overall_hit_rate"],
            0.5208333333333334,
        )
        self.assertFalse(payload["admitted"])
        self.assertEqual(
            payload["ladder"]["uniform@64"]["selection_reasons"][
                "terminal-margin"
            ],
            26,
        )
        self.assertEqual(
            payload["ladder"]["epsilon-greedy@64"]["selection_reasons"][
                "terminal-margin"
            ],
            23,
        )
        self.assertTrue(payload["promotion_blocked"])

    def test_committed_tactical_v5_audits_preserve_failed_gate(self):
        expected = {
            "mcts-tactical-only-v5-20260717.json": (
                "tactical-only",
                0.5416666666666666,
            ),
            "mcts-tactical-combined-v5-20260717.json": (
                "combined",
                0.4166666666666667,
            ),
        }
        for filename, (variant, high_rate) in expected.items():
            with self.subTest(variant=variant):
                path = ROOT / "research/results" / filename
                payload = json.loads(path.read_text())
                expected_hash = payload.pop("payload_hash")
                self.assertEqual(stable_hash(payload), expected_hash)
                self.assertEqual(payload["config"]["search_variant"], variant)
                self.assertEqual(payload["accounting"]["complete"], 384)
                self.assertEqual(payload["accounting"]["crash"], 0)
                self.assertTrue(
                    payload["correctness_and_provenance_audit_clean"]
                )
                self.assertAlmostEqual(
                    payload["high_budget_overall_hit_rate"],
                    high_rate,
                )
                self.assertFalse(payload["admitted"])
                self.assertFalse(
                    payload["admission_gate"][
                        "aggregate_hit_rate_nondecreasing_by_policy"
                    ]
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
        self.assertEqual(
            len(record["decision"]["root_action_telemetry"]),
            record["root_legal_actions"],
        )
        self.assertEqual(
            sum(
                item["visits"]
                for item in record["decision"]["root_action_telemetry"]
            ),
            2,
        )
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

    def test_tactical_variants_are_separately_hashed_and_recorded(self):
        for variant in ("tactical-only", "combined"):
            config = self._config(budgets=[2])
            config["search_variant"] = variant
            task = next(
                item for item in build_schedule(config)
                if item["position_id"] == "admission-pie-small-takeover"
            )
            record = evaluate_task(task)
            self.assertEqual(record["status"], "complete")
            self.assertEqual(record["search_variant"], variant)
            self.assertEqual(record["decision"]["search_variant"], variant)
            self.assertEqual(
                record["decision"]["agent_hash"],
                mcts_agent_hash(variant),
            )
            self.assertEqual(record["action"], "swap")

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
                list(range(16)),
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
