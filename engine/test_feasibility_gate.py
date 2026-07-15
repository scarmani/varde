import math
from pathlib import Path
import sys
import unittest


HARNESS_ROOT = Path(__file__).resolve().parents[1] / "research" / "harness"
if str(HARNESS_ROOT) not in sys.path:
    sys.path.insert(0, str(HARNESS_ROOT))

from feasibility_gate import (  # noqa: E402
    REVISED_LADDER,
    RULESETS,
    build_midgame_state,
    maximum_budget,
    passes_feasibility_gate,
    percentile,
    projected_game_seconds,
    projected_stage_hours,
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


if __name__ == "__main__":
    unittest.main()
