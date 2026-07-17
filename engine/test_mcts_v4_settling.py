from pathlib import Path
import random
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "engine"
HARNESS = ROOT / "research" / "harness"
for path in (ENGINE, HARNESS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from actions import RulesState, legal_actions, legal_transitions  # noqa: E402
from mcts import _rollout_action, choose_mcts_state_action  # noqa: E402
from mcts_settling import (  # noqa: E402
    immediate_progress_transitions,
    run_settling_rollout,
)
from mcts_tactical_fixtures import admission_positions  # noqa: E402
from mcts_v4_holdout import positive_positions  # noqa: E402
from varde import BLACK, Game, signature  # noqa: E402


def _fallback(policy, seed):
    rng = random.Random(seed)
    return lambda state, actions: _rollout_action(
        state,
        policy,
        rng,
        actions,
    )


class TestTrueTerminalSettling(unittest.TestCase):
    def test_every_rollout_reaches_accepted_terminal_within_4p(self):
        for position in admission_positions():
            for policy in ("uniform", "epsilon-greedy"):
                with self.subTest(position=position.id, policy=policy):
                    before = position.state.key()
                    result = run_settling_rollout(
                        position.state,
                        _fallback(policy, 31),
                    )
                    self.assertTrue(result.terminal_state.terminal)
                    self.assertLessEqual(
                        result.actions,
                        4 * len(position.state.game.board.points),
                    )
                    self.assertIn(result.terminal_reason, {
                        "accepted-two-pass",
                        "accepted-after-resumption",
                        "accepted-no-progress",
                    })
                    self.assertEqual(position.state.key(), before)

    def test_after_p_replies_to_an_opponent_pass(self):
        game = Game(3, rules="breath")
        point = game.board.points[0]
        game.state[point] = (BLACK,)
        game.moves_played = len(game.board.points)
        game.consecutive_passes = 1
        game.history = {signature(game.board, game.state, game.to_move)}
        state = RulesState.from_game(game)
        result = run_settling_rollout(state, _fallback("uniform", 7))
        phases = dict(result.phase_counts)
        self.assertGreaterEqual(phases.get("settle-reply-pass", 0), 1)
        self.assertTrue(result.terminal_state.terminal)

    def test_at_2p_passes_and_finishes_open_extensions(self):
        ordinary = Game(3, rules="breath")
        ordinary.state[ordinary.board.points[0]] = (BLACK,)
        ordinary.moves_played = 2 * len(ordinary.board.points)
        ordinary.history = {
            signature(ordinary.board, ordinary.state, ordinary.to_move)
        }
        result = run_settling_rollout(
            RulesState.from_game(ordinary),
            _fallback("uniform", 9),
        )
        self.assertGreaterEqual(
            dict(result.phase_counts).get("settle-pass", 0),
            1,
        )

        extension = next(
            item for item in admission_positions()
            if item.id == "admission-breath-run-small-continuation"
        ).state.clone()
        extension.game.moves_played = 2 * len(extension.game.board.points)
        result = run_settling_rollout(extension, _fallback("uniform", 9))
        self.assertGreaterEqual(
            dict(result.phase_counts).get("settle-finish-extension", 0),
            1,
        )

    def test_losing_seat_resumes_once_then_settles_again(self):
        position = next(
            item for item in positive_positions()
            if item.id == "v4-ending-toy-b"
        )
        result = run_settling_rollout(
            position.state,
            _fallback("uniform", 11),
        )
        phases = dict(result.phase_counts)
        self.assertTrue(result.resumption_used)
        self.assertEqual(phases.get("ending-resume"), 1)
        self.assertLessEqual(phases.get("post-resumption-progress", 0), 1)
        self.assertTrue(result.terminal_state.terminal)
        self.assertTrue(result.terminal_state.game.resumption_used)

    def test_progress_facts_use_one_supplied_transition_set(self):
        categories = ("capture", "defense", "fence")
        positions = positive_positions()
        for category in categories:
            position = next(
                item for item in positions if item.category == category
            )
            with self.subTest(category=category):
                transitions = legal_transitions(position.state)
                progress = immediate_progress_transitions(
                    position.state,
                    transitions,
                )
                self.assertIn(position.acceptable_actions[0], {
                    action for action, _advanced in progress
                })

    def test_mcts_reports_true_terminal_backup_telemetry(self):
        state = RulesState.from_game(Game(3, rules="breath"))
        decision = choose_mcts_state_action(
            state,
            BLACK,
            simulations=8,
            seed=19,
            rollout_policy="uniform",
            search_variant="v4-settling",
            include_root_telemetry=True,
        )
        self.assertIn(decision.action, legal_actions(state))
        self.assertEqual(decision.terminal_backups, 8)
        self.assertEqual(sum(dict(decision.terminal_reasons).values()), 8)
        self.assertTrue(decision.settling_phase_counts)
        self.assertLessEqual(
            decision.max_rollout_actions,
            4 * len(state.game.board.points),
        )


if __name__ == "__main__":
    unittest.main()
