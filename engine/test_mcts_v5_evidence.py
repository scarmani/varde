import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class TestMCTSV5Evidence(unittest.TestCase):
    def _load(self, relative):
        return json.loads((ROOT / relative).read_text())

    def test_complete_factorial_preserves_integrity_and_gated_stop(self):
        payload = self._load(
            "research/results/"
            "mcts-search-v5-development-factorial-20260717.json"
        )
        self.assertEqual(payload["status"], "complete-gated-stop")
        self.assertEqual(payload["accounting"]["scheduled"], 4_704)
        self.assertEqual(payload["accounting"]["complete"], 4_704)
        self.assertEqual(payload["accounting"]["crash"], 0)
        self.assertEqual(payload["accounting"]["oracle_solver_disagreements"], 0)
        self.assertEqual(payload["accounting"]["false_positive_guidance"], 0)
        self.assertEqual(
            payload["accounting"]["terminal_backups"],
            payload["accounting"]["expected_terminal_backups"],
        )
        self.assertTrue(payload["accounting"]["integrity_passed"])
        self.assertEqual(payload["selection"]["eligible_recipes"], [])
        self.assertIsNone(payload["selection"]["selected_recipe"])
        self.assertFalse(payload["selection"]["holdout_may_run"])

    def test_all_arms_failed_admission_and_settling_failed_efficiency(self):
        payload = self._load(
            "research/results/"
            "mcts-search-v5-development-factorial-20260717.json"
        )
        self.assertLess(max(payload["high_rung_admission"].values()), 0.80)
        self.assertTrue(payload["proof_guidance"]["scan_latency_gate_passed"])
        self.assertTrue(payload["reserved_unpruning"]["ten_point_gate_passed"])
        self.assertFalse(payload["settling_v2"]["efficiency_gate_passed"])
        self.assertEqual(payload["settling_v2"]["qualified_arms"], 0)

    def test_no_conditional_result_was_created(self):
        results = ROOT / "research" / "results"
        forbidden = (
            "mcts-search-v5-holdout-20260717.json",
            "mcts-search-v5-deep-ladder-20260717.json",
            "mcts-search-v5-paired-diagnostic-20260717.json",
        )
        for name in forbidden:
            with self.subTest(name=name):
                self.assertFalse((results / name).exists())


if __name__ == "__main__":
    unittest.main()
