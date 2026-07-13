import unittest

from research.harness.curate_v3 import (
    MIN_NORMALIZED_DISTANCE,
    normalized_distance,
    select_profiles,
)
from research.harness.map_elites_v3 import DESCRIPTORS, balanced_genome, stable_hash


def elite(candidate_id, quality, descriptors):
    genome = balanced_genome()
    return {
        "candidate_id": candidate_id,
        "quality": quality,
        "descriptors": descriptors,
        "genome": genome,
        "genome_hash": stable_hash(genome),
    }


class TestProfileCuration(unittest.TestCase):
    def test_normalized_descriptor_distance(self):
        zero = {name: 0.0 for name in DESCRIPTORS}
        one = dict(zero)
        one["engagement"] = 2.0
        scales = {name: 2.0 for name in DESCRIPTORS}
        self.assertEqual(normalized_distance(zero, one, scales), 1.0)

    def test_selects_highest_quality_distinct_eligible_elites(self):
        baseline = {name: 0.2 for name in DESCRIPTORS}
        attempts = []
        archive = {}
        profiles = [
            (1, 0.90, {"engagement": 0.50, "verticality": 0.1, "edge_reach": 0.1, "consolidation": 0.1}),
            (2, 0.80, {"engagement": 0.1, "verticality": 0.45, "edge_reach": 0.1, "consolidation": 0.1}),
            (3, 0.70, {"engagement": 0.1, "verticality": 0.1, "edge_reach": 0.50, "consolidation": 0.1}),
            (4, 0.60, {"engagement": 0.1, "verticality": 0.1, "edge_reach": 0.1, "consolidation": 0.50}),
        ]
        for candidate_id, quality, descriptors in profiles:
            item = elite(candidate_id, quality, descriptors)
            archive[str(candidate_id)] = item
            attempts.append({**item, "rejected": False})
        # Supply descriptor variation so one-unit normalized separation is strict.
        for index in range(5, 13):
            descriptors = {
                name: ((index + offset) % 7) / 10
                for offset, name in enumerate(DESCRIPTORS)
            }
            item = elite(index, 0.1, descriptors)
            attempts.append({**item, "rejected": False})
        state = {
            "status": "complete",
            "balanced_reference": {"descriptors": baseline},
            "attempts": attempts,
            "archive": archive,
        }
        audit = {
            "status": "complete",
            "analysis": {
                "candidate_decisions": {
                    name: {"accepted_for_optimization": True}
                    for name in (
                        "control_resilience",
                        "latent_reserves",
                        "sky_durability",
                        "connection",
                        "capturing_moves",
                        "max_capture",
                        "covers",
                        "hostile_covers",
                        "reinforcements",
                        "summits",
                    )
                }
            },
        }
        result = select_profiles(state, audit)
        self.assertEqual(set(result["selected"]), {"raider", "mason", "surveyor", "weaver"})
        self.assertFalse(result["needs_one_refinement"])
        for item in result["selected"].values():
            distance = item["minimum_distance_to_prior"]
            if distance is not None:
                self.assertGreaterEqual(distance, MIN_NORMALIZED_DISTANCE)

    def test_reports_missing_profile_without_relaxing_threshold(self):
        descriptors = {name: 0.2 for name in DESCRIPTORS}
        item = elite(1, 1.0, descriptors)
        state = {
            "status": "complete",
            "balanced_reference": {"descriptors": descriptors},
            "attempts": [{**item, "rejected": False}, {**elite(2, 0.5, {name: 0.3 for name in DESCRIPTORS}), "rejected": False}],
            "archive": {"0": item},
        }
        audit = {
            "status": "complete",
            "analysis": {
                "candidate_decisions": {
                    name: {"accepted_for_optimization": True}
                    for name in item["genome"]
                    if name not in ("controlled", "captured", "skies", "liberties", "vulnerable", "development", "territory")
                }
            },
        }
        result = select_profiles(state, audit)
        self.assertEqual(result["selected"], {})
        self.assertEqual(set(result["missing"]), {"raider", "mason", "surveyor", "weaver"})
        self.assertTrue(result["needs_one_refinement"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
