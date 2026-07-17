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
from mcts_v5_corpus import development_positions  # noqa: E402
from mcts_v5_oracle import (  # noqa: E402
    action_id,
    certify_goal,
    swapped_color_state,
)
from varde import signature  # noqa: E402


def _position(suffix):
    return next(
        position for position in development_positions()
        if position.id.endswith(suffix)
    )


class TestMCTSV5IndependentOracle(unittest.TestCase):
    def test_universal_capture_proof_and_non_mutation(self):
        position = _position("capture-toy-wide")
        before = position.state.key()
        certificate = certify_goal(position.state, position.goal)
        self.assertEqual(len(certificate.proven_actions), 1)
        self.assertGreater(certificate.nodes, len(legal_actions(position.state)))
        self.assertFalse(certificate.limit_reached)
        self.assertEqual(position.state.key(), before)

    def test_equivalent_proven_action_set_is_complete(self):
        position = _position("capture-beginner-wide-equivalent")
        certificate = certify_goal(position.state, position.goal)
        self.assertEqual(len(certificate.proven_actions), 2)
        self.assertEqual(
            {action_id(action) for action in certificate.proven_actions},
            set(position.public_dict()["acceptable_actions"]),
        )

    def test_actor_changing_rescue_closes_before_opponent_recursion(self):
        position = _position("rescue-beginner-narrow-closure")
        certificate = certify_goal(position.state, position.goal)
        self.assertEqual(len(certificate.proven_actions), 1)
        action = certificate.proven_actions[0]
        records = dict(certificate.traces)[action_id(action)]
        self.assertEqual(records[0]["actor_seat"], position.state.actor_seat)
        terminal_record = next(
            record for record in records if record["result"] == "proven"
        )
        self.assertNotEqual(
            terminal_record["actor_seat"], position.state.actor_seat
        )
        self.assertLessEqual(max(record["ply"] for record in records), 1)

    def test_actor_preserving_rescue_uses_existential_continuations(self):
        position = _position("rescue-toy-wide")
        certificate = certify_goal(position.state, position.goal)
        action = certificate.proven_actions[0]
        records = dict(certificate.traces)[action_id(action)]
        self.assertTrue(any(
            record["quantifier"] == "exists" for record in records
        ))
        self.assertTrue(any(
            record["ply"] >= 2 and record["result"] == "proven"
            for record in records
        ))

    def test_immediate_fence_is_not_mislabeled_durable(self):
        position = _position("fence-toy-narrow-immediate")
        immediate = certify_goal(position.state, position.goal)
        self.assertEqual(len(immediate.proven_actions), 1)
        durable_goal = {
            **position.goal,
            "scope": "same fence must survive every legal reply",
            "quantifier_schedule": [
                {"quantifier": "forall", "actor": "any"}
            ],
        }
        durable = certify_goal(position.state, durable_goal)
        action = immediate.proven_actions[0]
        statuses = dict(durable.action_statuses)
        self.assertEqual(statuses[action], "disproven")

    def test_exact_decoys_never_prove_an_action(self):
        decoys = [
            position for position in development_positions() if position.decoy
        ]
        self.assertEqual(len(decoys), 6)
        for position in decoys:
            with self.subTest(position=position.id):
                self.assertEqual(position.certificate().proven_actions, ())

    def test_node_ceiling_fails_closed(self):
        position = _position("capture-beginner-wide-equivalent")
        certificate = certify_goal(position.state, position.goal, node_limit=1)
        self.assertTrue(certificate.limit_reached)
        self.assertIn("unknown", dict(certificate.action_statuses).values())

    def test_capture_certificate_is_color_symmetric(self):
        position = _position("capture-toy-wide")
        original = certify_goal(position.state, position.goal)
        swapped = swapped_color_state(position.state)
        swapped.game.history = {signature(
            swapped.game.board,
            swapped.game.state,
            swapped.game.to_move,
        )}
        mirrored = certify_goal(swapped, position.goal)
        self.assertEqual(
            [(action_id(action), status) for action, status in original.action_statuses],
            [(action_id(action), status) for action, status in mirrored.action_statuses],
        )

    def test_superko_filtered_action_is_absent(self):
        position = _position("capture-toy-wide")
        state = position.state.clone()
        action = next(
            candidate for candidate in legal_actions(state)
            if candidate.kind == "play"
        )
        repeated, _captured = state.game.try_play(action.point)
        next_color = "W" if state.game.to_move == "B" else "B"
        state.game.history.add(signature(state.game.board, repeated, next_color))
        if action not in legal_actions(state):
            certificate = certify_goal(state, position.goal)
            self.assertNotIn(action, dict(certificate.action_statuses))


if __name__ == "__main__":
    unittest.main()
