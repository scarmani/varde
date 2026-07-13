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

    def test_full_board_is_exposed_through_public_view(self):
        view = public_view(Game(6))
        self.assertEqual(len(view["points"]), 216)
        self.assertEqual(sum(point["legal"] for point in view["points"]), 216)

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
        game.players = {BLACK: "Ada", WHITE: "Grace"}
        _, old_match = load_snapshot(game.to_dict())
        self.assertEqual(old_match.mode, "hotseat")
        self.assertEqual(old_match.seats[BLACK].name, "Ada")
        self.assertEqual(old_match.seats[WHITE].name, "Grace")

    def test_legacy_computer_save_is_accepted(self):
        game = Game(3)
        payload = game.to_dict()
        payload["computer"] = {
            "enabled": True,
            "color": WHITE,
            "difficulty": "casual",
            "explain": False,
            "seed": 43,
        }
        _, match = load_snapshot(payload)
        self.assertEqual(match.mode, "computer")
        self.assertEqual(match.computer_color, WHITE)
        self.assertEqual(match.seed, 43)

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


class TestWatchMatch(unittest.TestCase):
    def test_independent_computers_each_take_one_atomic_action(self):
        game = Game(3)
        match = MatchConfig.from_new_game(
            game,
            {
                "mode": "watch",
                "black_difficulty": "casual",
                "white_difficulty": "advanced",
                "seed": 18,
            },
        )
        self.assertEqual(match.seats[BLACK].difficulty, "casual")
        self.assertEqual(match.seats[WHITE].difficulty, "advanced")
        first = apply_computer_action(game, match)
        self.assertEqual(first.action, "play")
        self.assertEqual(game.moves_played, 1)
        apply_computer_action(game, match)
        self.assertTrue(game.swap_decided or game.moves_played == 2)

    def test_takeover_swaps_complete_seat_identities(self):
        game = Game(3)
        match = MatchConfig.from_new_game(
            game,
            {
                "mode": "watch",
                "black_difficulty": "casual",
                "white_difficulty": "advanced",
                "seed": 75,
            },
        )
        opening = game.board.points[0]
        game.play(opening)
        black_identity = match.seats[BLACK].identity
        white_identity = match.seats[WHITE].identity
        black_seed = match.seats[BLACK].seed
        white_seed = match.seats[WHITE].seed
        game.take_over()
        match.swap_owners(game)
        self.assertEqual(match.seats[BLACK].identity, white_identity)
        self.assertEqual(match.seats[WHITE].identity, black_identity)
        self.assertEqual(match.seats[BLACK].seed, white_seed)
        self.assertEqual(match.seats[WHITE].seed, black_seed)
        self.assertEqual(match.seats[BLACK].difficulty, "advanced")
        self.assertEqual(match.seats[WHITE].difficulty, "casual")

    def test_watch_save_round_trip_preserves_both_seats(self):
        game = Game(6)
        match = MatchConfig.from_new_game(
            game,
            {
                "mode": "watch",
                "black_difficulty": "advanced",
                "white_difficulty": "standard",
                "seed": 101,
            },
        )
        restored_game, restored = load_snapshot(snapshot_payload(game, match))
        self.assertEqual(restored_game.board.n, 6)
        self.assertEqual(restored.snapshot_data(), match.snapshot_data())

    def test_watch_match_never_accepts_a_human_action(self):
        game = Game(3)
        match = MatchConfig.from_new_game(game, {"mode": "watch"})
        with self.assertRaisesRegex(Illegal, "wait for the computer"):
            assert_human_action(game, match)
        game.finished = True
        with self.assertRaisesRegex(Illegal, "no human player"):
            assert_human_action(game, match)


if __name__ == "__main__":
    unittest.main(verbosity=2)
