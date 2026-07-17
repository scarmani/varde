import hashlib
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

from actions import RulesAction, apply_action, legal_actions  # noqa: E402
from freeze_mcts_v4_holdout import build_manifest  # noqa: E402
from mcts_tactical_fixtures import tactical_positions  # noqa: E402
from mcts_v4_holdout import (  # noqa: E402
    CATEGORIES,
    CERTIFICATE_FORMAT,
    CERTIFICATE_VERSION,
    certify_obligation,
    decoy_positions,
    holdout_catalog,
    holdout_positions,
    positive_positions,
    replay_seeded_state,
    state_hash,
)


class TestMCTSV4Holdout(unittest.TestCase):
    def test_positive_corpus_is_stratified_small_and_independent(self):
        positions = positive_positions()
        self.assertEqual(len(positions), 24)
        self.assertEqual(sum(
            item.provenance["kind"] == "reachable-seeded-play"
            for item in positions
        ), 20)
        for category in CATEGORIES:
            selected = [item for item in positions if item.category == category]
            self.assertEqual(len(selected), 4)
            self.assertEqual(
                sorted(item.state.game.board.n for item in selected),
                [3, 3, 4, 4],
            )
        self.assertTrue(all(
            2 <= len(legal_actions(item.state)) <= 12 for item in positions
        ))
        historical = {state_hash(item.state) for item in tactical_positions()}
        self.assertTrue(
            {state_hash(item.state) for item in positions}.isdisjoint(historical)
        )

    def test_every_positive_certificate_reproduces_exactly(self):
        for position in positive_positions():
            with self.subTest(position=position.id):
                before = position.state.key()
                proven, certificate = certify_obligation(
                    position.state,
                    position.obligation,
                )
                self.assertEqual(proven, position.acceptable_actions)
                self.assertEqual(certificate, position.certificate)
                self.assertTrue(certificate["override_eligible"])
                self.assertEqual(
                    sum(
                        status == "proven"
                        for status in certificate["action_statuses"].values()
                    ),
                    1,
                )
                self.assertEqual(certificate["format"], CERTIFICATE_FORMAT)
                self.assertEqual(certificate["version"], CERTIFICATE_VERSION)
                self.assertIn("not a game-theoretic", certificate["claim_limit"])
                self.assertEqual(position.state.key(), before)

    def test_decoys_reproduce_and_require_abstention(self):
        positions = decoy_positions()
        self.assertEqual(len(positions), 12)
        for category in CATEGORIES:
            self.assertEqual(
                sum(item.category == category for item in positions),
                2,
            )
        for position in positions:
            with self.subTest(position=position.id):
                proven, certificate = certify_obligation(
                    position.state,
                    position.obligation,
                )
                self.assertEqual(certificate, position.certificate)
                self.assertFalse(certificate["override_eligible"])
                self.assertEqual(position.acceptable_actions, ())
                self.assertTrue(
                    len(proven) != 1
                    or any(
                        status != "disproven"
                        for key, status in certificate["action_statuses"].items()
                        if key not in {
                            action.kind if action.point is None else (
                                f"{action.kind}:{action.point[0]},{action.point[1]}"
                            )
                            for action in proven
                        }
                    )
                )

    def test_reachable_provenance_replays_to_the_same_hash(self):
        for position in holdout_positions():
            provenance = position.provenance
            if provenance["kind"] != "reachable-seeded-play":
                continue
            with self.subTest(position=position.id):
                state, transcript = replay_seeded_state(
                    provenance["rules"],
                    provenance["board_size"],
                    provenance["seed"],
                    provenance["seeded_plies"],
                )
                for kind in provenance["post_actions"]:
                    state = apply_action(state, RulesAction(kind))
                rendered = (*transcript, *provenance["post_actions"])
                digest = hashlib.sha256(
                    json.dumps(rendered, separators=(",", ":")).encode()
                ).hexdigest()
                self.assertEqual(digest, provenance["transcript_sha256"])
                self.assertEqual(state_hash(state), state_hash(position.state))

    def test_catalog_and_manifest_are_deterministic(self):
        first = holdout_catalog()
        second = holdout_catalog()
        self.assertEqual(first, second)
        self.assertEqual(len(first["positions"]), 36)
        manifest = build_manifest(
            output_dir="/tmp/varde-mcts-v4-test",
            created_date="2026-07-17",
            source_commit_value="3154433",
        )
        self.assertEqual(manifest, build_manifest(
            output_dir="/tmp/varde-mcts-v4-test",
            created_date="2026-07-17",
            source_commit_value="3154433",
        ))
        self.assertEqual(manifest["positive_positions"], 24)
        self.assertEqual(manifest["decoy_positions"], 12)
        self.assertEqual(manifest["reachable_positive_positions"], 20)
        self.assertTrue(manifest["independence"]["v3_state_hashes_disjoint"])
        self.assertFalse(manifest["freeze_gate"]["candidate_code_present"])


if __name__ == "__main__":
    unittest.main()
