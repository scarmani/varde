import json
import math
from pathlib import Path
import unittest

from mcts import MCTS_AGENT_HASH


REPO_ROOT = Path(__file__).resolve().parents[1]
TIMING_PATH = REPO_ROOT / "research" / "profiles" / "mcts-250-v1-v2-timing.json"
GOLDEN_PATH = REPO_ROOT / "research" / "fixtures" / "mcts-v1-golden.json"


class TestMCTSPerformanceEvidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.timing = json.loads(TIMING_PATH.read_text())
        cls.golden = json.loads(GOLDEN_PATH.read_text())

    def test_timing_compares_the_same_outcome_blind_workload(self):
        config = self.timing["configuration"]
        self.assertEqual(config["action_output"], "intentionally-omitted")
        self.assertEqual(config["simulations"], 250)
        v1 = self.timing["measurements"]["v1"]
        v2 = self.timing["measurements"]["v2"]
        self.assertEqual(v1["agent_hash"], self.golden["mcts_agent_hash"])
        self.assertRegex(v2["agent_hash"], r"^[0-9a-f]{64}$")
        self.assertNotEqual(v2["agent_hash"], MCTS_AGENT_HASH)
        self.assertEqual(v1["average_rollout_actions"], v2["average_rollout_actions"])
        self.assertEqual(v1["max_rollout_actions"], v2["max_rollout_actions"])

    def test_reported_timing_calculations_are_reproducible(self):
        v1 = self.timing["measurements"]["v1"]["elapsed_seconds"]
        v2 = self.timing["measurements"]["v2"]["elapsed_seconds"]
        result = self.timing["result"]
        self.assertTrue(math.isclose(result["speedup_factor"], v1 / v2))
        self.assertTrue(
            math.isclose(
                result["wall_time_reduction_percent"],
                100.0 * (v1 - v2) / v1,
            )
        )
        self.assertTrue(
            math.isclose(
                result["gate_overrun_factor"],
                v2 / self.timing["gates"]["decision_250_max_seconds"],
            )
        )

    def test_failed_prerequisite_skips_larger_timing_jobs(self):
        gates = self.timing["gates"]
        self.assertFalse(gates["decision_250_passed"])
        self.assertEqual(
            gates["decision_1000_status"],
            "skipped-after-250-gate-failure",
        )
        self.assertEqual(
            gates["full_game_status"],
            "skipped-after-250-gate-failure",
        )


if __name__ == "__main__":
    unittest.main()
