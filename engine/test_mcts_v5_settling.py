import math
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "engine"
HARNESS = ROOT / "research" / "harness"
for path in (ENGINE, HARNESS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from actions import RulesState, apply_action, legal_actions  # noqa: E402
from mcts import choose_mcts_state_action, mcts_agent_hash  # noqa: E402
from mcts_v5_corpus import development_positions  # noqa: E402
from mcts_v5_settling import (  # noqa: E402
    SettlingIntegrityError,
    classify_event_transitions,
    run_settling_v2_rollout,
)
from varde import Game  # noqa: E402


def _position(suffix):
    return next(
        position for position in development_positions()
        if position.id.endswith(suffix)
    )


def _first(_state, actions):
    return actions[0]


class TestMCTSV5TrueTerminalSettling(unittest.TestCase):
    def test_event_classifier_recognizes_only_the_four_declared_families(self):
        cases = (
            ("capture-toy-wide", "capture"),
            ("defense-toy-wide", "sole-liberty-defense"),
            ("rescue-beginner-narrow-closure", "extension-closure"),
            ("fence-toy-narrow-immediate", "fence-completion"),
        )
        for suffix, expected in cases:
            with self.subTest(position=suffix):
                position = _position(suffix)
                events = classify_event_transitions(position.state)
                self.assertTrue(any(
                    expected in item.events for item in events
                ))

        state = RulesState.from_game(Game(3, rules="breath"))
        events = classify_event_transitions(state)
        self.assertEqual(events, ())

    def test_defense_event_requires_the_group_to_remain_controlled(self):
        positive = _position("defense-toy-wide")
        events = classify_event_transitions(positive.state)
        defense_actions = {
            item.action for item in events
            if "sole-liberty-defense" in item.events
        }
        self.assertEqual(defense_actions, set(positive.acceptable_actions))
        decoy = _position("defense-toy-narrow-decoy")
        self.assertFalse(any(
            "sole-liberty-defense" in item.events
            for item in classify_event_transitions(decoy.state)
        ))

    def test_half_p_no_event_and_opponent_pass_settle_immediately(self):
        game = Game(3, rules="breath")
        game.play(game.legal_placements()[0])
        game.swap_decided = True
        game.moves_played = math.ceil(0.5 * len(game.board.points))
        state = RulesState.from_game(game)
        before = state.key()
        result = run_settling_v2_rollout(state, _first)
        phases = dict(result.phase_counts)
        self.assertGreaterEqual(phases.get("settle-no-event-pass", 0), 1)
        self.assertTrue(result.terminal_state.terminal)
        self.assertEqual(state.key(), before)

        passed = state.clone()
        pass_action = next(
            action for action in legal_actions(passed) if action.kind == "pass"
        )
        passed = apply_action(passed, pass_action)
        passed.game.moves_played = math.ceil(0.5 * len(game.board.points))
        result = run_settling_v2_rollout(passed, _first)
        self.assertGreaterEqual(
            dict(result.phase_counts).get("settle-reply-pass", 0), 1
        )

    def test_p_clock_finishes_open_extension_instead_of_placing(self):
        position = _position("rescue-beginner-narrow-closure")
        state = position.state.clone()
        state.game.moves_played = len(state.game.board.points)
        result = run_settling_v2_rollout(state, _first)
        self.assertGreaterEqual(
            dict(result.phase_counts).get("p-finish-extension", 0), 1
        )
        self.assertTrue(result.terminal_state.terminal)

    def test_losing_seat_resumes_once_then_gets_at_most_one_event(self):
        position = _position("ending-beginner-resume")
        result = run_settling_v2_rollout(position.state, _first)
        phases = dict(result.phase_counts)
        self.assertTrue(result.resumption_used)
        self.assertEqual(phases.get("ending-resume", 0), 1)
        self.assertLessEqual(phases.get("post-resumption-event", 0), 1)
        self.assertTrue(result.terminal_state.terminal)

    def test_4p_limit_is_integrity_failure_not_a_value(self):
        state = RulesState.from_game(Game(3, rules="breath"))
        with self.assertRaises(SettlingIntegrityError):
            run_settling_v2_rollout(state, _first, action_limit=1)

    def test_mcts_v2_backups_are_terminal_deterministic_and_non_mutating(self):
        position = _position("capture-toy-wide")
        before = position.state.key()
        first = choose_mcts_state_action(
            position.state,
            position.state.actor_color,
            simulations=8,
            seed=9901,
            rollout_policy="uniform",
            search_variant="v5-g0-u0-s1",
            include_root_telemetry=True,
        )
        second = choose_mcts_state_action(
            position.state,
            position.state.actor_color,
            simulations=8,
            seed=9901,
            rollout_policy="uniform",
            search_variant="v5-g0-u0-s1",
            include_root_telemetry=True,
        )
        self.assertEqual(first.to_dict(), second.to_dict())
        self.assertEqual(first.terminal_backups, first.simulations)
        self.assertLessEqual(first.max_rollout_actions, 4 * len(
            position.state.game.board.points
        ))
        self.assertEqual(position.state.key(), before)

    def test_all_eight_factor_hashes_are_unique_and_v4_is_unchanged(self):
        variants = tuple(
            f"v5-g{guidance}-u{unpruning}-s{settling}"
            for guidance in (0, 1)
            for unpruning in (0, 1)
            for settling in (0, 1)
        )
        self.assertEqual(len({mcts_agent_hash(item) for item in variants}), 8)
        self.assertEqual(
            mcts_agent_hash("v4-settling"),
            "d37e2c5fdeb1d95a245bcdb441192c02e77983a6931f9b1b88ef5be108f7a014",
        )


if __name__ == "__main__":
    unittest.main()
