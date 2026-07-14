import unittest

from research.harness.gate_profiles_v3 import (
    game_descriptors,
    one_sided_bootstrap_lower,
    pooled_effect_size,
    profile_gate_jobs,
    summarize_gates,
)
from research.harness.map_elites_v3 import balanced_genome


class TestProfileGate(unittest.TestCase):
    def test_schedule_shares_seeds_across_profiles_and_colors(self):
        curation = {
            "selected": {
                "raider": {"weights": balanced_genome()},
                "mason": {"weights": balanced_genome()},
            }
        }
        jobs = profile_gate_jobs(curation, 12, toy_pairs=2, beginner_pairs=1)
        self.assertEqual(len(jobs), 3 * 3 * 2)
        for pair in range(3):
            selected = [job for job in jobs if job["pair"] == pair]
            self.assertEqual(len({job["seed"] for job in selected}), 1)
            self.assertEqual(
                {job["profile"] for job in selected},
                {"balanced", "raider", "mason"},
            )
            self.assertEqual({job["color"] for job in selected}, {"B", "W"})

    def test_descriptor_normalization(self):
        game = {
            "engagement": 2,
            "early_placements": 4,
            "verticality": 3,
            "all_placements": 6,
            "edge_reach_sum": 1.0,
            "consolidation": 1,
        }
        self.assertEqual(
            game_descriptors(game),
            {
                "engagement": 0.5,
                "verticality": 0.5,
                "edge_reach": 0.25,
                "consolidation": 0.25,
            },
        )

    def test_bootstrap_and_effect_size_are_deterministic(self):
        scores = [0.0, 0.5, 1.0, 1.0]
        self.assertEqual(
            one_sided_bootstrap_lower(scores, 9, samples=1000),
            one_sided_bootstrap_lower(scores, 9, samples=1000),
        )
        self.assertGreater(
            pooled_effect_size([0.8, 0.9, 1.0], [0.0, 0.1, 0.2]),
            0.8,
        )

    def test_failed_profile_does_not_poison_pairwise_gate_for_passers(self):
        curation = {
            "selected": {
                "raider": {},
                "mason": {},
                "surveyor": {},
            },
            "descriptor_scales": {
                "engagement": 1.0,
                "verticality": 1.0,
                "edge_reach": 1.0,
                "consolidation": 1.0,
            },
        }
        profiles = {
            "raider": {
                "passed_individual_gates": False,
                "mean_descriptors": {
                    "engagement": 0.0,
                    "verticality": 0.0,
                    "edge_reach": 2.0,
                    "consolidation": 0.0,
                },
            },
            "mason": {
                "passed_individual_gates": True,
                "mean_descriptors": {
                    "engagement": 0.0,
                    "verticality": 2.0,
                    "edge_reach": 0.0,
                    "consolidation": 0.0,
                },
            },
            "surveyor": {
                "passed_individual_gates": True,
                "mean_descriptors": {
                    "engagement": 0.0,
                    "verticality": 0.0,
                    "edge_reach": 2.0,
                    "consolidation": 0.0,
                },
            },
        }

        import research.harness.gate_profiles_v3 as gate

        original = gate.summarize_profile
        gate.summarize_profile = lambda profile_id, *_args: dict(profiles[profile_id])
        try:
            summary = summarize_gates(curation, [], seed=9)
        finally:
            gate.summarize_profile = original

        self.assertFalse(summary["profiles"]["raider"]["passed"])
        self.assertTrue(summary["profiles"]["mason"]["passed"])
        self.assertTrue(summary["profiles"]["surveyor"]["passed"])
        self.assertEqual(summary["available_profiles"], ["mason", "surveyor"])
        self.assertTrue(summary["pairwise_gate_passed"])
        self.assertFalse(
            summary["pairwise_normalized_descriptor_distance"]["raider-surveyor"][
                "eligible_pair"
            ]
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
