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

from actions import legal_actions  # noqa: E402
from freeze_mcts_v5_corpora import build_manifest, stable_hash  # noqa: E402
from mcts_tactical_fixtures import tactical_positions  # noqa: E402
from mcts_v4_holdout import holdout_positions as v4_positions  # noqa: E402
from mcts_v5_corpus import (  # noqa: E402
    FAMILIES,
    corpus_catalog,
    development_positions,
    holdout_positions,
)
from mcts_v5_oracle import state_hash  # noqa: E402


class TestMCTSV5FrozenCorpora(unittest.TestCase):
    def test_each_split_has_exact_size_board_width_and_family_strata(self):
        for split, positions in (
            ("development", development_positions()),
            ("holdout", holdout_positions()),
        ):
            with self.subTest(split=split):
                self.assertEqual(len(positions), 24)
                self.assertEqual(
                    sum(item.state.game.board.n == 3 for item in positions), 12
                )
                self.assertEqual(
                    sum(item.state.game.board.n == 4 for item in positions), 12
                )
                self.assertEqual(
                    sum(item.width_class == "narrow" for item in positions), 12
                )
                self.assertEqual(
                    sum(item.width_class == "wide" for item in positions), 12
                )
                for family in FAMILIES:
                    selected = [
                        item for item in positions if item.family == family
                    ]
                    self.assertEqual(len(selected), 4)
                    self.assertEqual(sum(item.decoy for item in selected), 1)
                    self.assertTrue(any(
                        item.hand_audit and item.decoy for item in selected
                    ))
                    self.assertTrue(any(
                        item.hand_audit and not item.decoy for item in selected
                    ))
                for position in positions:
                    width = len(legal_actions(position.state))
                    if position.width_class == "narrow":
                        self.assertLessEqual(width, 12)
                        self.assertGreaterEqual(width, 2)
                    else:
                        self.assertGreaterEqual(width, 32)

    def test_all_splits_are_hash_disjoint_from_each_other_and_v4(self):
        development = {
            state_hash(position.state) for position in development_positions()
        }
        holdout = {
            state_hash(position.state) for position in holdout_positions()
        }
        historical = {
            state_hash(position.state) for position in tactical_positions()
        } | {state_hash(position.state) for position in v4_positions()}
        self.assertTrue(development.isdisjoint(holdout))
        self.assertTrue(development.isdisjoint(historical))
        self.assertTrue(holdout.isdisjoint(historical))

    def test_certificates_and_hand_audit_actor_records_are_complete(self):
        for position in (*development_positions(), *holdout_positions()):
            with self.subTest(position=position.id):
                certificate = position.certificate()
                self.assertFalse(certificate.limit_reached)
                self.assertEqual(
                    len(certificate.action_statuses),
                    len(legal_actions(position.state)),
                )
                if position.hand_audit:
                    audit = position.public_dict()["hand_audit_trace"]
                    self.assertTrue(audit["records"])
                    self.assertTrue(all(
                        "actor_seat" in record and "actor_color" in record
                        for record in audit["records"]
                    ))

    def test_catalog_and_manifest_builds_are_deterministic(self):
        for split in ("development", "holdout"):
            with self.subTest(split=split):
                first = corpus_catalog(split)
                second = corpus_catalog(split)
                self.assertEqual(first, second)
                self.assertEqual(len(first["positions"]), 24)
                manifest = build_manifest(
                    split,
                    output_dir="/tmp/varde-mcts-v5-test",
                    created_date="2026-07-17",
                    source_commit_value="8f3a966",
                )
                self.assertEqual(manifest, build_manifest(
                    split,
                    output_dir="/tmp/varde-mcts-v5-test",
                    created_date="2026-07-17",
                    source_commit_value="8f3a966",
                ))
                expected = manifest.pop("payload_sha256")
                self.assertEqual(stable_hash(manifest), expected)
                self.assertTrue(
                    manifest["independence"]["historical_state_hashes_disjoint"]
                )
                self.assertTrue(
                    manifest["independence"][
                        "other_v5_split_state_hashes_disjoint"
                    ]
                )

    def test_catalog_hash_is_self_consistent(self):
        payload = corpus_catalog("development")
        expected = payload.pop("payload_sha256")
        self.assertEqual(stable_hash(payload), expected)
        json.dumps(payload, allow_nan=False)

    def test_frozen_manifests_regenerate_exactly(self):
        for split in ("development", "holdout"):
            with self.subTest(split=split):
                path = (
                    ROOT / "research" / "manifests"
                    / f"mcts-search-v5-{split}-20260717.json"
                )
                payload = json.loads(path.read_text())
                expected = build_manifest(
                    split,
                    output_dir=payload["execution"]["output_dir"],
                    created_date=payload["created_date"],
                    source_commit_value=payload["source"]["source_commit"],
                )
                self.assertEqual(payload, expected)


if __name__ == "__main__":
    unittest.main()
