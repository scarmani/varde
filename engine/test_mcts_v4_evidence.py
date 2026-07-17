import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "engine"
HARNESS = ROOT / "research" / "harness"
for path in (ENGINE, HARNESS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from audit_mcts_tactical_admission import _validate_manifest  # noqa: E402
from mcts_tactical_admission import stable_hash  # noqa: E402


class TestMCTSV4Evidence(unittest.TestCase):
    def _load(self, relative):
        return json.loads((ROOT / relative).read_text())

    def _assert_hash(self, payload, key):
        expected = payload.pop(key)
        self.assertEqual(stable_hash(payload), expected)

    def test_common_manifests_are_frozen_distinct_and_reproducible(self):
        variants = (
            "control",
            "solver",
            "ordered-control",
            "unpruning",
            "settling",
        )
        agent_hashes = set()
        for slug in variants:
            with self.subTest(variant=slug):
                manifest = self._load(
                    f"research/manifests/mcts-search-v4-{slug}-screen-"
                    "20260717.json"
                )
                tasks = _validate_manifest(manifest)
                self.assertEqual(len(tasks), 384)
                self.assertEqual(manifest["status"], "frozen-before-outcomes")
                self.assertEqual(manifest["config"]["budgets"], [4, 16, 64])
                self.assertEqual(manifest["config"]["replicates"], 4)
                agent_hashes.add(manifest["source"]["mcts_agent_hash"])
        self.assertEqual(len(agent_hashes), 5)

    def test_every_individual_screen_is_complete_clean_and_hash_valid(self):
        for slug in (
            "control",
            "solver",
            "ordered-control",
            "unpruning",
            "settling",
        ):
            with self.subTest(variant=slug):
                payload = self._load(
                    f"research/results/mcts-search-v4-{slug}-screen-"
                    "20260717.json"
                )
                self._assert_hash(payload, "payload_hash")
                self.assertEqual(payload["accounting"]["complete"], 384)
                self.assertEqual(payload["accounting"]["crash"], 0)
                self.assertEqual(payload["accounting"]["pending"], 0)
                self.assertTrue(
                    payload["correctness_and_provenance_audit_clean"]
                )

    def test_common_result_preserves_the_predeclared_gated_stop(self):
        payload = self._load(
            "research/results/mcts-search-v4-common-screen-20260717.json"
        )
        self._assert_hash(payload, "payload_sha256")
        rates = {
            variant: item["high_budget_overall_hit_rate"]
            for variant, item in payload["variants"].items()
        }
        self.assertEqual(rates, {
            "v4-control": 0.5208333333333334,
            "v4-ordered-control": 0.5416666666666666,
            "v4-settling": 0.4583333333333333,
            "v4-solver": 0.8541666666666666,
            "v4-unpruning": 0.6041666666666666,
        })
        self.assertFalse(payload["candidate_a"]["qualified"])
        self.assertFalse(payload["candidate_b"]["qualified"])
        self.assertFalse(payload["candidate_c"]["qualified"])
        self.assertEqual(
            payload["candidate_b"][
                "unpruning_high_rung_delta_over_ordered_control"
            ],
            0.0625,
        )
        self.assertEqual(
            len(payload["variants"]["v4-solver"]["failed_high_rung_cells"]),
            3,
        )
        self.assertIsNone(payload["selection"]["selected_recipe"])
        self.assertFalse(payload["selection"]["sealed_holdout_may_run"])
        self.assertEqual(
            payload["selection"]["selection_kind"],
            "none-qualified",
        )

    def test_feasibility_and_holdout_artifacts_remain_hash_valid(self):
        cases = (
            (
                "research/manifests/mcts-search-v4-holdout-20260717.json",
                "payload_sha256",
            ),
            (
                "research/results/mcts-search-v4-solver-feasibility-"
                "20260717.json",
                "payload_sha256",
            ),
            (
                "research/results/mcts-search-v4-unpruning-feasibility-"
                "20260717.json",
                "payload_sha256",
            ),
            (
                "research/results/mcts-search-v4-settling-feasibility-"
                "20260717.json",
                "payload_sha256",
            ),
        )
        for path, key in cases:
            with self.subTest(path=path):
                payload = self._load(path)
                self._assert_hash(payload, key)

    def test_no_downstream_holdout_or_deep_result_was_created(self):
        results = ROOT / "research" / "results"
        self.assertFalse(
            (results / "mcts-search-v4-holdout-result-20260717.json").exists()
        )
        self.assertFalse(
            (results / "mcts-search-v4-deep-ladder-20260717.json").exists()
        )
        self.assertFalse(
            (results / "mcts-search-v4-paired-diagnostic-20260717.json").exists()
        )


if __name__ == "__main__":
    unittest.main()
