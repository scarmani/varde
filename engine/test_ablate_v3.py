import unittest

from research.harness.ablate_v3 import (
    VARIANTS,
    ablation_jobs,
    play_ablation_pair,
    summarize_pairs,
    variant_genome,
)


class TestEvaluatorAblations(unittest.TestCase):
    def test_variants_disable_only_declared_weights(self):
        development = variant_genome("development_disabled")
        liberty = variant_genome("liberty_disabled")
        both = variant_genome("both_disabled")
        self.assertEqual(development["development"], 0.0)
        self.assertNotEqual(development["liberties"], 0.0)
        self.assertEqual(liberty["liberties"], 0.0)
        self.assertNotEqual(liberty["development"], 0.0)
        self.assertEqual(both["development"], 0.0)
        self.assertEqual(both["liberties"], 0.0)

    def test_schedule_is_paired_and_stratified_for_every_variant(self):
        jobs = ablation_jobs(4, toy_pairs=2, beginner_pairs=1)
        self.assertEqual(len(jobs), 9)
        for variant in VARIANTS:
            selected = [job for job in jobs if job["variant"] == variant]
            self.assertEqual([job["n"] for job in selected], [3, 3, 4])
            self.assertEqual([job["pair"] for job in selected], [0, 1, 2])

    def test_real_casual_pair_and_behavior_summary_are_complete(self):
        task = ablation_jobs(15, toy_pairs=1, beginner_pairs=1)[0]
        task["difficulty"] = "casual"
        pair = play_ablation_pair(task)
        self.assertTrue(pair["complete"])
        self.assertEqual(len(pair["games"]), 2)
        summary = summarize_pairs([pair])
        overall = summary[f"{task['variant']}-overall"]
        self.assertEqual(overall["games"], 2)
        self.assertEqual(overall["incomplete_games"], 0)
        self.assertGreater(sum(overall["heat_map"].values()), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
