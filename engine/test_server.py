import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from varde import BLACK, WHITE, Game, Illegal
from learning import LearningModel
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

    def test_profiles_default_and_legacy_advanced_migration(self):
        game = Game(3)
        balanced = MatchConfig.from_new_game(
            game,
            {"mode": "computer", "human_color": BLACK},
        )
        seat = balanced.seats[WHITE]
        self.assertEqual((seat.difficulty, seat.profile), ("standard", "balanced"))
        self.assertNotIn("profile", balanced.seats[BLACK].to_dict())

        personal = MatchConfig.from_new_game(
            Game(3),
            {
                "mode": "computer",
                "human_color": BLACK,
                "difficulty": "advanced",
            },
        )
        self.assertEqual(
            (personal.seats[WHITE].difficulty, personal.seats[WHITE].profile),
            ("standard", "personal"),
        )

        payload = snapshot_payload(Game(3), personal)
        payload["match"]["seats"][WHITE].pop("profile")
        payload["match"]["seats"][WHITE]["difficulty"] = "advanced"
        _, migrated = load_snapshot(payload)
        self.assertEqual(
            (migrated.seats[WHITE].difficulty, migrated.seats[WHITE].profile),
            ("standard", "personal"),
        )

        legacy = Game(3).to_dict()
        legacy["computer"] = {
            "enabled": True,
            "color": WHITE,
            "difficulty": "advanced",
            "seed": 19,
        }
        _, migrated_legacy = load_snapshot(legacy)
        self.assertEqual(
            (
                migrated_legacy.seats[WHITE].difficulty,
                migrated_legacy.seats[WHITE].profile,
            ),
            ("standard", "personal"),
        )

    def test_zero_weight_personal_is_visibly_balanced(self):
        with TemporaryDirectory() as directory:
            model = LearningModel(path=Path(directory) / "model.json")
            balanced_game = Game(3)
            personal_game = Game(3)
            balanced = MatchConfig.from_new_game(
                balanced_game,
                {
                    "mode": "computer",
                    "human_color": WHITE,
                    "difficulty": "standard",
                    "profile": "balanced",
                    "seed": 913,
                },
            )
            personal = MatchConfig.from_new_game(
                personal_game,
                {
                    "mode": "computer",
                    "human_color": WHITE,
                    "difficulty": "standard",
                    "profile": "personal",
                    "seed": 913,
                },
            )
            balanced_decision = apply_computer_action(
                balanced_game, balanced, model
            )
            personal_decision = apply_computer_action(
                personal_game, personal, model
            )
            self.assertEqual(
                (
                    personal_decision.action,
                    personal_decision.point,
                    personal_decision.score,
                    personal_decision.nodes,
                ),
                (
                    balanced_decision.action,
                    balanced_decision.point,
                    balanced_decision.score,
                    balanced_decision.nodes,
                ),
            )
            self.assertEqual(personal_game.to_dict(), balanced_game.to_dict())

    def test_profile_snapshot_remains_version_one(self):
        game = Game(3)
        match = MatchConfig.from_new_game(
            game,
            {
                "mode": "computer",
                "human_color": BLACK,
                "profile": "personal",
            },
        )
        payload = snapshot_payload(game, match)
        self.assertEqual(payload["version"], 1)
        self.assertEqual(payload["match"]["seats"][WHITE]["profile"], "personal")

    def test_unknown_and_unavailable_profiles_are_rejected(self):
        for profile in ("missing", "raider", "weaver"):
            with self.subTest(profile=profile), self.assertRaises(ValueError):
                MatchConfig.from_new_game(
                    Game(3),
                    {
                        "mode": "computer",
                        "human_color": BLACK,
                        "profile": profile,
                    },
                )

    def test_rosette_games_expose_rules_and_round_trip(self):
        game = Game(3, rules="rosette")
        match = MatchConfig.from_new_game(
            game,
            {"mode": "computer", "human_color": BLACK, "profile": "balanced"},
        )
        view = public_view(game, match)
        self.assertEqual(view["rules"], "rosette")
        payload = snapshot_payload(game, match)
        restored, _ = load_snapshot(payload)
        self.assertEqual(restored.rules, "rosette")
        classic_view = public_view(Game(3), match)
        self.assertEqual(classic_view["rules"], "classic")

    def test_curated_profiles_are_accepted_in_both_modes(self):
        for profile in ("mason", "surveyor"):
            with self.subTest(profile=profile, mode="computer"):
                match = MatchConfig.from_new_game(
                    Game(3),
                    {
                        "mode": "computer",
                        "human_color": BLACK,
                        "difficulty": "standard",
                        "profile": profile,
                    },
                )
                self.assertEqual(match.seats[WHITE].profile, profile)
        watch = MatchConfig.from_new_game(
            Game(3),
            {
                "mode": "watch",
                "black_difficulty": "standard",
                "black_profile": "surveyor",
                "white_difficulty": "casual",
                "white_profile": "mason",
                "seed": 41,
            },
        )
        self.assertEqual(watch.seats[BLACK].profile, "surveyor")
        self.assertEqual(watch.seats[WHITE].profile, "mason")
        for profile in ("raider", "weaver"):
            with self.subTest(profile=profile, mode="watch"), self.assertRaises(
                ValueError
            ):
                MatchConfig.from_new_game(
                    Game(3),
                    {
                        "mode": "watch",
                        "black_profile": profile,
                    },
                )

    def test_public_view_exposes_profile_without_raw_weights(self):
        game = Game(3)
        match = MatchConfig.from_new_game(
            game,
            {
                "mode": "computer",
                "human_color": BLACK,
                "profile": "personal",
            },
        )
        view = public_view(game, match)
        self.assertEqual(view["match"]["profile"], "personal")
        self.assertEqual(view["match"]["seats"][WHITE]["profile"], "personal")
        self.assertNotIn("weights", view["match"]["seats"][WHITE])

    def test_public_view_can_hide_rationale_text(self):
        game = Game(3)
        match = MatchConfig.from_new_game(
            game,
            {"mode": "computer", "human_color": WHITE, "explain": False},
        )
        decision = apply_computer_action(game, match)
        view = public_view(game, match, decision)
        self.assertEqual(view["computer_decision"]["reason_text"], "")
        self.assertNotIn("score", view["computer_decision"])

    def test_public_rationale_names_profile_without_raw_score(self):
        game = Game(3)
        match = MatchConfig.from_new_game(
            game,
            {
                "mode": "computer",
                "human_color": WHITE,
                "profile": "personal",
            },
        )
        decision = apply_computer_action(game, match)
        payload = public_view(game, match, decision)["computer_decision"]
        self.assertEqual(payload["profile"], "personal")
        self.assertTrue(payload["reason_text"].startswith("Personal: "))
        self.assertNotIn("score", payload)

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
        self.assertEqual(match.seats[BLACK].profile, "balanced")
        self.assertEqual(match.seats[WHITE].difficulty, "standard")
        self.assertEqual(match.seats[WHITE].profile, "personal")
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
        black_profile = match.seats[BLACK].profile
        white_profile = match.seats[WHITE].profile
        game.take_over()
        match.swap_owners(game)
        self.assertEqual(match.seats[BLACK].identity, white_identity)
        self.assertEqual(match.seats[WHITE].identity, black_identity)
        self.assertEqual(match.seats[BLACK].seed, white_seed)
        self.assertEqual(match.seats[WHITE].seed, black_seed)
        self.assertEqual(match.seats[BLACK].difficulty, "standard")
        self.assertEqual(match.seats[WHITE].difficulty, "casual")
        self.assertEqual(match.seats[BLACK].profile, white_profile)
        self.assertEqual(match.seats[WHITE].profile, black_profile)

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

    def test_ahead_computer_accepts_then_losing_computer_resumes(self):
        game = Game(3)
        match = MatchConfig.from_new_game(game, {"mode": "watch"})
        game.state[game.board.points[0]] = (BLACK,)
        game.finished = True
        game.to_move = BLACK

        accepted = apply_computer_action(game, match)
        self.assertEqual(accepted.action, "accept")
        self.assertTrue(match.computer_can_act(game))
        self.assertEqual(match.next_computer_color(game), WHITE)

        resumed = apply_computer_action(game, match)
        self.assertEqual(resumed.action, "resume")
        self.assertFalse(game.finished)
        self.assertTrue(game.resumption_used)
        self.assertEqual(match.end_acceptances, set())

    def test_both_computers_may_accept_a_draw(self):
        game = Game(3)
        match = MatchConfig.from_new_game(game, {"mode": "watch"})
        game.finished = True
        first = apply_computer_action(game, match)
        second = apply_computer_action(game, match)
        self.assertEqual((first.action, second.action), ("accept", "accept"))
        self.assertFalse(match.computer_can_act(game))
        self.assertTrue(match.end_decided)

    def test_partial_end_acceptance_round_trips(self):
        game = Game(3)
        match = MatchConfig.from_new_game(game, {"mode": "watch"})
        game.finished = True
        apply_computer_action(game, match)
        restored_game, restored = load_snapshot(snapshot_payload(game, match))
        self.assertEqual(restored.end_acceptances, match.end_acceptances)
        self.assertEqual(
            restored.next_computer_color(restored_game),
            match.next_computer_color(game),
        )

    def test_one_acceptance_finalizes_after_resumption_was_used(self):
        game = Game(3)
        match = MatchConfig.from_new_game(game, {"mode": "watch"})
        game.finished = True
        game.resumption_used = True
        decision = apply_computer_action(game, match)
        self.assertEqual(decision.action, "accept")
        self.assertTrue(match.end_decided)
        self.assertFalse(match.computer_can_act(game))


if __name__ == "__main__":
    unittest.main(verbosity=2)
