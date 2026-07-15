import json
import math
from pathlib import Path
import sys
import unittest


HARNESS_ROOT = Path(__file__).resolve().parents[1] / "research" / "harness"
if str(HARNESS_ROOT) not in sys.path:
    sys.path.insert(0, str(HARNESS_ROOT))

from feasibility_gate import (  # noqa: E402
    DEFAULT_OUTPUT,
    POLICIES,
    REVISED_LADDER,
    RULESETS,
    _aggregate_gate,
    build_midgame_state,
    file_hash,
    maximum_budget,
    passes_feasibility_gate,
    percentile,
    projected_game_seconds,
    projected_stage_hours,
    stable_hash,
    validate_outcome_blind,
)


class TestFeasibilityArithmetic(unittest.TestCase):
    def test_percentile_and_maximum_budget(self):
        self.assertEqual(percentile([1.0], 0.95), 1.0)
        self.assertTrue(math.isclose(percentile([1.0, 3.0], 0.5), 2.0))
        self.assertEqual(maximum_budget(2.0, 0.75), 2)
        self.assertEqual(maximum_budget(2.0, 3.0), 0)
        with self.assertRaises(ValueError):
            maximum_budget(0.0, 1.0)

    def test_game_and_stage_projection(self):
        seconds = projected_game_seconds(4, 0.5, 0.1, 100)
        self.assertTrue(math.isclose(seconds, 105.0))
        self.assertTrue(
            math.isclose(projected_stage_hours(seconds, 480, 8), 1.75)
        )
        self.assertIsNone(projected_game_seconds(0, 0.5, 0.1, 100))

    def test_feasibility_gate_requires_budget_time_and_stage_capacity(self):
        self.assertTrue(
            passes_feasibility_gate(
                maximum_common_budget=REVISED_LADDER[-1],
                projected_hours=23.0,
                per_decision_p95=29.0,
            )
        )
        self.assertFalse(
            passes_feasibility_gate(
                maximum_common_budget=REVISED_LADDER[-1] - 1,
                projected_hours=23.0,
                per_decision_p95=29.0,
            )
        )
        self.assertFalse(
            passes_feasibility_gate(
                maximum_common_budget=REVISED_LADDER[-1],
                projected_hours=25.0,
                per_decision_p95=29.0,
            )
        )

    def test_aggregate_tests_the_declared_ladder_not_the_common_maximum(self):
        policy_projection = {
            "conservative_simulation_seconds": 0.5,
            "conservative_simulation_p95_seconds": 0.6,
            "decision_gates": {"30": {"maximum_budget": 60}},
        }
        measurement = {
            "random_game_length": {"mean_moves": 10.0},
            "native_standard": {"opening": {"mean_seconds": 0.1}},
            "projections": {
                policy: dict(policy_projection) for policy in POLICIES
            },
        }
        aggregate = _aggregate_gate({"classic": measurement}, 30)
        self.assertEqual(aggregate["maximum_common_budget"], 60)
        self.assertEqual(
            aggregate["revised_ladder_high_budget"], REVISED_LADDER[-1]
        )
        self.assertLess(
            aggregate["revised_ladder_projected_stage_wall_hours"],
            aggregate["projected_stage_at_common_maximum_hours"],
        )
        self.assertTrue(aggregate["passes_feasibility_gate"])


class TestOutcomeBlindHarness(unittest.TestCase):
    def test_midgame_prefix_is_deterministic_and_nonterminal(self):
        for rules in RULESETS:
            with self.subTest(rules=rules):
                first = build_midgame_state(rules, 20260715)
                second = build_midgame_state(rules, 20260715)
                self.assertEqual(first.key(), second.key())
                self.assertEqual(first.game.moves_played, second.game.moves_played)
                self.assertFalse(first.terminal)
                self.assertFalse(first.game.finished)

    def test_outcome_blind_contract_rejects_forbidden_measurement_keys(self):
        valid = {
            "evidence_eligible": False,
            "outcomes_inspected": False,
            "decisions_inspected": False,
            "measurements": {"classic": {"mean_seconds": 1.0}},
        }
        validate_outcome_blind(valid)
        for key in ("action", "point", "score", "winner", "margin", "result"):
            invalid = dict(valid)
            invalid["measurements"] = {"classic": {key: 1}}
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_outcome_blind(invalid)


class TestGeneratedFeasibilityEvidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(DEFAULT_OUTPUT.read_text())

    def test_artifact_is_hash_pinned_and_outcome_blind(self):
        payload = dict(self.payload)
        expected_hash = payload.pop("payload_hash")
        self.assertEqual(stable_hash(payload), expected_hash)
        validate_outcome_blind(self.payload)
        self.assertEqual(
            self.payload["provenance"]["harness_sha256"],
            file_hash(HARNESS_ROOT / "feasibility_gate.py"),
        )

    def test_artifact_completed_the_declared_matrix_with_finite_values(self):
        self.assertEqual(set(self.payload["measurements"]), set(RULESETS))
        self.assertEqual(
            self.payload["configuration"]["repetitions_per_cell"], 10
        )
        self.assertLess(
            self.payload["measurement_wall_seconds"],
            self.payload["configuration"]["maximum_measurement_wall_seconds"],
        )
        for measurement in self.payload["measurements"].values():
            self.assertGreater(
                measurement["random_game_length"]["mean_moves"], 0
            )
            for policy in POLICIES:
                projection = measurement["projections"][policy]
                self.assertGreater(
                    projection["conservative_simulation_seconds"], 0
                )
                for gate in projection["decision_gates"].values():
                    self.assertGreaterEqual(gate["maximum_budget"], 0)

    def test_predeclared_16_32_gate_honestly_fails(self):
        gates = self.payload["aggregate_decision_gates"]
        self.assertTrue(gates["30"]["supports_predeclared_16_32_ladder"])
        self.assertFalse(gates["30"]["passes_feasibility_gate"])
        self.assertGreater(
            gates["30"]["revised_ladder_projected_per_decision_p95_seconds"],
            self.payload["configuration"]["decision_gates_seconds"][-1],
        )


if __name__ == "__main__":
    unittest.main()
