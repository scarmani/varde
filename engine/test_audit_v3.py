import math
import unittest

from learning import FEATURE_NAMES
from research.harness.audit_v3 import (
    BOARD_POSITION_TOTALS,
    POLICIES,
    V3_CANDIDATES,
    audit_jobs,
    grouped_log_loss,
    play_audit_game,
    spearman,
)


class TestEvaluatorAudit(unittest.TestCase):
    def test_job_schedule_has_exact_declared_mix(self):
        jobs = audit_jobs(91)
        self.assertEqual(len(jobs), 200)
        for n, positions in BOARD_POSITION_TOTALS.items():
            self.assertEqual(
                sum(job["n"] == n for job in jobs), positions // 10
            )
        for policy in POLICIES:
            self.assertEqual(sum(job["policy"] == policy for job in jobs), 50)
        self.assertEqual(jobs, audit_jobs(91))
        self.assertNotEqual(
            [job["seed"] for job in jobs],
            [job["seed"] for job in audit_jobs(92)],
        )

    def test_real_random_game_yields_ten_symmetric_bounded_rows(self):
        job = next(
            job
            for job in audit_jobs(19)
            if job["n"] == 3 and job["policy"] == "random"
        )
        result = play_audit_game(job)
        self.assertTrue(result["complete"], result.get("error"))
        self.assertEqual(len(result["rows"]), 10)
        expected = set(FEATURE_NAMES) | set(V3_CANDIDATES)
        for row in result["rows"]:
            self.assertEqual(set(row["features"]), expected)
            self.assertEqual(row["symmetry_error"], 0.0)
            self.assertTrue(
                all(
                    math.isfinite(value) and -1 <= value <= 1
                    for value in row["features"].values()
                )
            )
        behavior = result["behavior"]
        self.assertGreater(behavior["placements"], 0)
        self.assertEqual(
            sum(behavior["heat"].values()), behavior["placements"]
        )

    def test_spearman_handles_order_reversal_and_ties(self):
        self.assertEqual(spearman([1, 2, 3], [1, 2, 3]), 1.0)
        self.assertEqual(spearman([1, 2, 3], [3, 2, 1]), -1.0)
        self.assertEqual(spearman([1, 1, 1], [2, 3, 4]), 0.0)

    def test_game_grouped_prediction_rewards_informative_feature(self):
        rows = []
        for group in range(50):
            label = float(group % 2)
            for _sample in range(2):
                rows.append(
                    {
                        "group_id": f"g{group}",
                        "outcome": label,
                        "features": {"signal": 1.0 if label else -1.0},
                    }
                )
        intercept = grouped_log_loss(rows, [], 44)
        informed = grouped_log_loss(rows, ["signal"], 44)
        self.assertLess(informed, intercept * 0.5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
