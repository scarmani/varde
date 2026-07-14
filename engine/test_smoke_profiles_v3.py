import unittest

from research.harness.map_elites_v3 import balanced_genome
from research.harness.smoke_profiles_v3 import smoke_jobs


class TestProfileSmokeSchedule(unittest.TestCase):
    def test_all_matchups_and_larger_boards_are_paired(self):
        curation = {
            "selected": {
                "raider": {"weights": balanced_genome()},
                "mason": {"weights": balanced_genome()},
            }
        }
        jobs = smoke_jobs(curation, 8, matchup_pairs=4, larger_pairs=2)
        matchup = [job for job in jobs if job["kind"] == "matchup"]
        larger = [job for job in jobs if job["kind"] == "larger"]
        # Three profiles have three pairwise matchups, four pairs, two colors.
        self.assertEqual(len(matchup), 3 * 4 * 2)
        # Two curated profiles, two boards, two pairs, two colors.
        self.assertEqual(len(larger), 2 * 2 * 2 * 2)
        for label in {job["label"] for job in jobs}:
            selected = [job for job in jobs if job["label"] == label]
            for pair in {job["pair"] for job in selected}:
                legs = [job for job in selected if job["pair"] == pair]
                self.assertEqual({job["color"] for job in legs}, {"B", "W"})
                self.assertEqual(len({job["seed"] for job in legs}), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
