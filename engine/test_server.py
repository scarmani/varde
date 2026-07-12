import unittest

from cairn import BLACK, WHITE, Game, Illegal
from server import (
    MatchConfig,
    apply_computer_action,
    assert_human_action,
    load_snapshot,
    public_view,
    snapshot_payload,
)


class TestPublicView(unittest.TestCase):
    def test_fresh_view_exposes_playable_geometry(self):
        view = public_view(Game(3))
        self.assertEqual(len(view["points"]), 54)
        self.assertEqual(sum(point["legal"] for point in view["points"]), 54)
        self.assertFalse(view["swap_available"])
        self.assertEqual(view["score"], {BLACK: 0, WHITE: 0})
        self.assertEqual(view["match"]["mode"], "hotseat")

    def test_opening_exposes_swap_and_identity(self):
        game = Game(3)
        game.play(game.board.points[0])
        view = public_view(game)
        self.assertTrue(view["swap_available"])
        self.assertEqual(view["current_player"], "Player 2")
        game.take_over()
        view = public_view(game)
        self.assertEqual(view["current_player"], "Player 1")
        self.assertEqual(view["players"], {BLACK: "Player 2", WHITE: "Player 1"})


class TestComputerMatch(unittest.TestCase):
    def test_computer_opens_when_human_is_white(self):
        game = Game(3)
        match = MatchConfig.from_new_game(
            game,
            {
                "mode": "computer",
                "human_color": WHITE,
                "difficulty": "casual",
                "seed": 8,
            },
        )
        self.assertTrue(match.computer_can_act(game))
        decision = apply_computer_action(game, match)
        self.assertEqual(decision.action, "play")
        self.assertEqual(game.moves_played, 1)
        self.assertEqual(game.to_move, WHITE)
        self.assertFalse(match.computer_can_act(game))

    def test_human_actions_are_blocked_on_computer_turn(self):
        game = Game(3)
        match = MatchConfig.from_new_game(
            game,
            {"mode": "computer", "human_color": WHITE},
        )
        with self.assertRaisesRegex(Illegal, "wait for the computer"):
            assert_human_action(game, match)

    def test_human_swap_transfers_computer_color_and_turn(self):
        game = Game(3)
        match = MatchConfig.from_new_game(
            game,
            {"mode": "computer", "human_color": WHITE, "difficulty": "casual"},
        )
        apply_computer_action(game, match)
        self.assertTrue(game.swap_available)
        game.take_over()
        match.swap_owners()
        self.assertEqual(match.human_color, BLACK)
        self.assertEqual(match.computer_color, WHITE)
        self.assertTrue(match.computer_can_act(game))

    def test_computer_configuration_round_trips_and_old_saves_stay_hotseat(self):
        game = Game(3)
        match = MatchConfig.from_new_game(
            game,
            {
                "mode": "computer",
                "human_color": BLACK,
                "difficulty": "casual",
                "explain": False,
                "seed": 91,
            },
        )
        restored_game, restored_match = load_snapshot(snapshot_payload(game, match))
        self.assertEqual(restored_game.to_dict(), game.to_dict())
        self.assertEqual(restored_match.computer_color, WHITE)
        self.assertEqual(restored_match.difficulty, "casual")
        self.assertFalse(restored_match.explain)
        self.assertEqual(restored_match.seed, 91)
        _, old_match = load_snapshot(game.to_dict())
        self.assertEqual(old_match.mode, "hotseat")

    def test_public_view_can_hide_rationale_text(self):
        game = Game(3)
        match = MatchConfig.from_new_game(
            game,
            {"mode": "computer", "human_color": WHITE, "explain": False},
        )
        decision = apply_computer_action(game, match)
        view = public_view(game, match, decision)
        self.assertEqual(view["computer_decision"]["reason_text"], "")

    def test_computer_resumes_when_behind_and_accepts_when_ahead(self):
        game = Game(2)
        match = MatchConfig.from_new_game(
            game,
            {"mode": "computer", "human_color": BLACK},
        )
        game.play(game.board.points[0])
        game.play_pass()
        game.play_pass()
        resumed = apply_computer_action(game, match)
        self.assertEqual(resumed.action, "resume")
        self.assertTrue(game.resumption_used)
        game.finished = True
        match.computer_color = BLACK
        match.human_color = WHITE
        accepted = apply_computer_action(game, match)
        self.assertEqual(accepted.action, "accept")
        self.assertTrue(match.end_decided)


if __name__ == "__main__":
    unittest.main(verbosity=2)
