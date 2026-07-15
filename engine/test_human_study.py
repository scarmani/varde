import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from research.harness.human_study import (
    CANDIDATES,
    PII_KEYS,
    build_crossover,
    build_resolution_puzzles,
    instruments,
    validate_playtest_record,
    write_package,
    stable_hash,
)
from varde import BLACK, WHITE, Game


def sample_record():
    return {
        "format": "varde-human-playtest",
        "version": 1,
        "session_id": "11111111-1111-4111-8111-111111111111",
        "source": "browser-local-hotseat",
        "rules": {"id": "classic", "revision": "classic-1.3"},
        "board_size": 3,
        "catalog_version": 1,
        "native_evaluator_hash": "a" * 64,
        "status": "active",
        "actions": [{
            "index": 0,
            "kind": "play",
            "point": [-2, -2],
            "actor_color": BLACK,
            "elapsed_ms": 1200,
            "move_before": 0,
            "move_after": 1,
            "captured": 0,
            "capture_waves": [],
            "score_after": {BLACK: 1, WHITE: 0},
        }],
        "final_score": None,
        "resumption_used": False,
        "ended_by_stagnation": False,
    }


class TestHumanStudySchedule(unittest.TestCase):
    def test_crossover_balances_color_opponent_and_order(self):
        for participants in (8, 10, 12):
            with self.subTest(participants=participants):
                schedule = build_crossover(
                    participants, ("breath", "gjerde", "rosette")
                )
                self.assertEqual(len(schedule["pairs"]), participants // 2)
                first_rules = [pair["ruleset_order"][0] for pair in schedule["pairs"]]
                first_counts = {rules: first_rules.count(rules) for rules in schedule["rulesets"]}
                self.assertLessEqual(max(first_counts.values()) - min(first_counts.values()), 1)
                for pair in schedule["pairs"]:
                    self.assertEqual(len(pair["players"]), 2)
                    for rules in schedule["rulesets"]:
                        games = [item for item in pair["games"] if item["rules"] == rules]
                        self.assertEqual(len(games), 6)
                        for player in pair["players"]:
                            self.assertEqual(sum(item["black"] == player for item in games), 3)
                            self.assertEqual(sum(item["white"] == player for item in games), 3)

    def test_schedule_rejects_non_panel_shapes_and_non_candidates(self):
        with self.assertRaises(ValueError):
            build_crossover(6, ("classic", "breath"))
        with self.assertRaises(ValueError):
            build_crossover(8, ("classic",))
        with self.assertRaises(ValueError):
            build_crossover(8, ("classic", "breath-cap"))

    def test_instruments_keep_ratings_separate_and_do_not_seed_motif_names(self):
        payload = instruments()
        self.assertEqual(len(payload["ratings"]["items"]), 9)
        self.assertIn("surprise", payload["ratings"]["items"])
        self.assertIn("inevitable_in_retrospect", payload["ratings"]["items"])
        rendered = json.dumps(payload).lower()
        for priming_term in ("micro-life", "mutual squeeze", "swarm starvation"):
            self.assertNotIn(priming_term, rendered)


class TestHumanStudyPuzzlesAndRecords(unittest.TestCase):
    def test_two_engine_derived_puzzles_per_candidate_round_trip(self):
        puzzles = build_resolution_puzzles(CANDIDATES)
        self.assertEqual(len(puzzles), 2 * len(CANDIDATES))
        for rules in CANDIDATES:
            self.assertEqual(sum(item["rules"] == rules for item in puzzles), 2)
        for puzzle in puzzles:
            game = Game.from_dict(puzzle["snapshot"])
            point = tuple(puzzle["action"]["point"])
            self.assertEqual(point in game.legal_placements(), puzzle["answer"]["legal"])
            if puzzle["answer"]["legal"]:
                captured = game.play(point)
                self.assertEqual(captured, puzzle["answer"]["captured"])
                self.assertEqual(
                    [[list(item) for item in wave] for wave in game.last_capture_waves],
                    puzzle["answer"]["capture_waves"],
                )
        for rules in ("gjerde", "gjerde-go"):
            fence, boundary = [
                item for item in puzzles if item["rules"] == rules
            ]
            self.assertEqual(fence["answer"]["score_delta"][BLACK], 1)
            self.assertEqual(boundary["answer"]["score_delta"], {BLACK: 0, WHITE: 0})

    def test_browser_record_schema_accepts_local_actions_and_rejects_pii(self):
        record = sample_record()
        self.assertTrue(validate_playtest_record(record))
        record["status"] = "complete"
        record["final_score"] = {BLACK: 30, WHITE: 24}
        self.assertTrue(validate_playtest_record(record))
        for key in sorted(PII_KEYS):
            tainted = sample_record()
            tainted[key] = "forbidden"
            with self.assertRaisesRegex(ValueError, "PII field"):
                validate_playtest_record(tainted)

    def test_record_rejects_unknown_fields_bad_timing_and_revision_drift(self):
        record = sample_record()
        record["notes"] = "free text"
        with self.assertRaisesRegex(ValueError, "unknown record fields"):
            validate_playtest_record(record)
        record = sample_record()
        record["actions"][0]["elapsed_ms"] = -1
        with self.assertRaisesRegex(ValueError, "elapsed"):
            validate_playtest_record(record)
        record = sample_record()
        record["rules"]["revision"] = "classic-future"
        with self.assertRaisesRegex(ValueError, "revision mismatch"):
            validate_playtest_record(record)

    def test_package_is_hash_pinned_private_and_repository_relative(self):
        with TemporaryDirectory() as directory:
            path = write_package(
                Path(directory), 8, ("breath", "gjerde"), 6
            )
            payload = json.loads(path.read_text())
            self.assertEqual(payload["format"], "varde-human-study-package")
            self.assertEqual(len(payload["source_commit"]), 40)
            self.assertFalse(payload["privacy"]["network_submission"])
            self.assertFalse(payload["privacy"]["direct_identifiers"])
            self.assertNotIn("/tmp", path.read_text())
            package_hash = payload.pop("package_hash")
            self.assertEqual(package_hash, stable_hash(payload))
            self.assertEqual(payload["browser_record_schema"]["version"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
