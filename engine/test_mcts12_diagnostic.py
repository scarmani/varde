import copy
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "research" / "harness"
if str(HARNESS) not in sys.path:
    sys.path.insert(0, str(HARNESS))

from actions import RulesAction, RulesState, apply_action, legal_actions
from test_ruleset_evaluation import _config, synthetic_game
from evaluate_rulesets import build_schedule, is_wipe, summarize
from varde import (
    BLACK,
    WHITE,
    Game,
    control,
    empty_state,
    score_cells,
    signature,
)


class TestClassicStagnationFixture(unittest.TestCase):
    def _position(self):
        game = Game(3, rules="classic")
        target = (-5, -1)
        neighbors = game.board.neighbors[target]
        game.state[target] = (BLACK,)
        game.state[neighbors[0]] = (BLACK,)
        game.state[neighbors[1]] = (BLACK,)
        game.state[neighbors[2]] = (WHITE,)
        game.to_move = BLACK
        game.moves_played = 6
        game.swap_decided = True
        game.quiet_moves = 11
        game.history = {signature(game.board, game.state, game.to_move)}
        return game, target

    def test_quiet_cover_triggers_final_stagnation(self):
        game, target = self._position()
        before = game.clone()
        self.assertEqual(control(game.state, target), BLACK)
        self.assertIn(target, game.legal_placements())

        captured = game.play(target)

        self.assertEqual(captured, 0)
        self.assertEqual(game.quiet_moves, 12)
        self.assertTrue(game.finished)
        self.assertTrue(game.no_progress_end)
        self.assertFalse(game.resumption_available)
        self.assertEqual(before.quiet_moves, 11)
        self.assertFalse(before.finished)

    def test_control_changing_placement_resets_the_quiet_clock(self):
        game, _target = self._position()
        empty = next(
            point for point in game.legal_placements() if not game.state[point]
        )

        game.play(empty)

        self.assertEqual(game.quiet_moves, 0)
        self.assertFalse(game.finished)
        self.assertFalse(game.no_progress_end)


class TestGjerdeGoWipeFixture(unittest.TestCase):
    def test_sparse_tie_has_no_loser_and_is_not_a_wipe(self):
        game = Game(4, rules="gjerde-go")
        state = empty_state(game.board)
        black_cell = (-3, 3)
        white_cell = (3, -3)
        for line in game.board.cell_edges[black_cell]:
            state[line] = (BLACK,)
        for line in game.board.cell_edges[white_cell]:
            state[line] = (WHITE,)

        score = score_cells(game.board, state)

        self.assertEqual(score, {BLACK: 1, WHITE: 1})
        self.assertFalse(is_wipe(score, len(game.board.cells)))

    def test_decisive_zero_score_loser_meets_the_declared_threshold(self):
        game = Game(4, rules="gjerde-go")
        state = empty_state(game.board)
        for line in game.board.cell_edges[(-3, 3)]:
            state[line] = (BLACK,)

        score = score_cells(game.board, state)

        self.assertEqual(score, {BLACK: 1, WHITE: 0})
        self.assertTrue(is_wipe(score, len(game.board.cells)))


class TestBreathColorAndPieFixture(unittest.TestCase):
    def _final_colors(self, initial_a_color, *, swap):
        initial_b_color = WHITE if initial_a_color == BLACK else BLACK
        state = RulesState(
            Game(3, rules="breath"),
            seats={initial_a_color: "agent-a", initial_b_color: "agent-b"},
        )
        opening = next(
            action for action in legal_actions(state) if action.kind == "play"
        )
        state = apply_action(state, opening)
        if swap:
            takeover = RulesAction("swap")
            self.assertIn(takeover, legal_actions(state))
            state = apply_action(state, takeover)
        return (
            state.color_for_seat("agent-a"),
            state.color_for_seat("agent-b"),
        )

    def test_paired_summary_separates_board_color_from_player_identity(self):
        config = _config(pairs=1)
        config["rulesets"] = ["breath"]
        tasks = build_schedule(config)
        records = []
        for task in tasks:
            record = synthetic_game(task)
            swap = task["leg"] == 0
            final_a, final_b = self._final_colors(
                task["initial_a_color"], swap=swap
            )
            record.update({
                "score": {BLACK: 40, WHITE: 14},
                "final_a_color": final_a,
                "final_b_color": final_b,
                "agent_a_result": 1.0 if final_a == BLACK else 0.0,
                "agent_a_margin": 26 if final_a == BLACK else -26,
                "margin_fraction": 26 / 54,
                "wipe": False,
            })
            record["counters"] = copy.deepcopy(record["counters"])
            record["counters"]["swaps"] = int(swap)
            records.append(record)

        result = summarize(
            records,
            config,
            provenance={"fixture": "breath-color-pie"},
            status="complete",
        )
        stratum = result["strata"][
            "breath|n=3|native-casual__vs__native-standard"
        ]

        self.assertEqual(records[0]["initial_a_color"], BLACK)
        self.assertEqual(records[0]["final_a_color"], WHITE)
        self.assertEqual(records[1]["initial_a_color"], WHITE)
        self.assertEqual(records[1]["final_a_color"], WHITE)
        self.assertEqual(stratum["black_score_rate"], 1.0)
        self.assertEqual(stratum["agent_a_score_rate"], 0.0)
        self.assertEqual(stratum["original_black_player_score_rate"], 0.5)
        self.assertEqual(stratum["post_swap_original_player_score_rate"], 0.0)
        self.assertEqual(stratum["swap_rate"], 0.5)


if __name__ == "__main__":
    unittest.main()
