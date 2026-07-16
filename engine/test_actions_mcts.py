import unittest

from actions import RulesAction, RulesState, apply_action, legal_actions
from mcts import (
    MCTS_AGENT_HASH,
    MCTS_VERSION,
    choose_mcts_action,
    choose_mcts_state_action,
)
from varde import BLACK, WHITE, Game, Illegal, signature


CANDIDATES = ("classic", "rosette", "breath", "breath-run", "gjerde", "gjerde-go")


class TestRulesActions(unittest.TestCase):
    def test_structural_clone_is_equal_without_mutable_aliases(self):
        for rules in CANDIDATES:
            with self.subTest(rules=rules):
                game = Game(4, rules=rules)
                game.play(game.legal_placements()[0])
                game.last_capture_waves = [((999, 999),)]
                clone = game.clone()

                self.assertIs(clone.board, game.board)
                self.assertEqual(clone.to_dict(), game.to_dict())
                self.assertIsNot(clone.state, game.state)
                self.assertIsNot(clone.history, game.history)
                self.assertIsNot(clone.players, game.players)
                self.assertIsNot(clone.extension_points, game.extension_points)
                self.assertIsNot(clone.last_capture_waves, game.last_capture_waves)
                self.assertEqual(clone.last_capture_waves, game.last_capture_waves)

                point = game.board.points[0]
                clone.state[point] = clone.state[point] + (clone.to_move,)
                clone.history.clear()
                clone.players[BLACK] = "Changed"
                clone.extension_points.append(point)
                clone.last_capture_waves.append((point,))
                self.assertNotEqual(clone.state, game.state)
                self.assertTrue(game.history)
                self.assertNotEqual(clone.players, game.players)
                self.assertEqual(game.extension_points, [])
                self.assertEqual(game.last_capture_waves, [((999, 999),)])

    def test_rules_state_clone_is_equal_without_mutable_aliases(self):
        state = RulesState.from_game(Game(4, rules="breath-run"))
        clone = state.clone()
        self.assertEqual(clone.key(), state.key())
        self.assertIsNot(clone.game, state.game)
        self.assertIsNot(clone.seats, state.seats)
        self.assertIsNot(clone.end_acceptances, state.end_acceptances)
        clone.seats[BLACK] = "changed-seat"
        clone.end_acceptances.add("changed-seat")
        self.assertNotEqual(clone.seats, state.seats)
        self.assertNotEqual(clone.end_acceptances, state.end_acceptances)

    def test_emitted_action_order_is_the_existing_canonical_order(self):
        for rules in CANDIDATES:
            with self.subTest(rules=rules, position="opening"):
                state = RulesState.from_game(Game(4, rules=rules))
                actions = legal_actions(state)
                self.assertEqual(actions, tuple(sorted(actions, key=RulesAction.sort_key)))
            with self.subTest(rules=rules, position="after-opening"):
                state = apply_action(state, legal_actions(state)[0])
                actions = legal_actions(state)
                self.assertEqual(actions, tuple(sorted(actions, key=RulesAction.sort_key)))

    def test_opening_pass_is_absent_then_pie_and_pass_are_present(self):
        state = RulesState.from_game(Game(3))
        actions = legal_actions(state)
        self.assertTrue(actions)
        self.assertEqual({action.kind for action in actions}, {"play"})
        opening = actions[0]
        replied = apply_action(state, opening)
        kinds = {action.kind for action in legal_actions(replied)}
        self.assertEqual(kinds, {"play", "pass", "swap"})
        self.assertEqual(state.game.moves_played, 0)

    def test_takeover_swaps_complete_seat_identity_without_changing_turn(self):
        game = Game(3)
        game.play(game.legal_placements()[0])
        state = RulesState.from_game(game)
        before = dict(state.seats)
        swapped = apply_action(state, RulesAction("swap"))
        self.assertEqual(swapped.game.to_move, WHITE)
        self.assertEqual(swapped.seats[BLACK], before[WHITE])
        self.assertEqual(swapped.seats[WHITE], before[BLACK])
        self.assertEqual(state.seats, before)

    def test_extension_and_finish_are_explicit_actions(self):
        game = Game(3, rules="breath-run")
        center = max(game.board.deep)
        first, second, liberty = game.board.neighbors[center]
        onward = [q for q in game.board.neighbors[liberty] if q != center]
        game.state[center] = (BLACK,)
        game.state[first] = (WHITE,)
        game.state[second] = (WHITE,)
        game.state[onward[0]] = (WHITE,)
        game.to_move = BLACK
        game.moves_played = 6
        game.history = {signature(game.board, game.state, BLACK)}
        state = RulesState.from_game(game)
        extension = RulesAction("extend", liberty)
        self.assertIn(extension, legal_actions(state))
        extended = apply_action(state, extension)
        self.assertTrue(extended.game.extension_only_turn)
        self.assertIn(
            RulesAction("finish-extension"), legal_actions(extended)
        )
        finished = apply_action(extended, RulesAction("finish-extension"))
        self.assertEqual(finished.game.to_move, WHITE)
        self.assertFalse(finished.game.extension_only_turn)

    def test_exhausted_breath_run_omits_forced_finish_action(self):
        game = Game(3, rules="breath-run")
        center = max(game.board.deep)
        first, second, liberty = game.board.neighbors[center]
        game.state[center] = (BLACK,)
        game.state[first] = (WHITE,)
        game.state[second] = (WHITE,)
        game.to_move = BLACK
        game.moves_played = 6
        game.history = {signature(game.board, game.state, BLACK)}

        extended = apply_action(
            RulesState.from_game(game), RulesAction("extend", liberty)
        )

        self.assertEqual(extended.game.to_move, WHITE)
        self.assertFalse(extended.game.extension_only_turn)
        self.assertNotIn(
            RulesAction("finish-extension"), legal_actions(extended)
        )

    def test_both_first_end_decisions_and_one_resumption_are_represented(self):
        game = Game(3)
        game.play(game.legal_placements()[0])
        game.play_pass()
        game.play_pass()
        state = RulesState.from_game(game)
        self.assertEqual(
            {action.kind for action in legal_actions(state)},
            {"resume", "accept"},
        )

        first_accepts = apply_action(state, RulesAction("accept"))
        self.assertFalse(first_accepts.terminal)
        self.assertNotEqual(first_accepts.end_decider, state.end_decider)
        resumed = apply_action(first_accepts, RulesAction("resume"))
        self.assertFalse(resumed.game.finished)
        self.assertTrue(resumed.game.resumption_used)
        self.assertEqual(resumed.end_acceptances, set())

        both_accept = apply_action(first_accepts, RulesAction("accept"))
        self.assertTrue(both_accept.terminal)
        self.assertEqual(legal_actions(both_accept), ())

        resumed.game.play_pass()
        resumed.game.play_pass()
        resumed.end_decider = resumed.game.to_move
        self.assertEqual(legal_actions(resumed), (RulesAction("accept"),))
        final = apply_action(resumed, RulesAction("accept"))
        self.assertTrue(final.terminal)
        with self.assertRaises(Illegal):
            apply_action(final, RulesAction("resume"))

    def test_superko_filtered_action_and_state_key_round_trip(self):
        game = Game(3, rules="breath")
        game.play(game.legal_placements()[0])
        blocked = game.legal_placements()[0]
        repeated, _captured = game.try_play(blocked)
        game.history.add(signature(game.board, repeated, BLACK))
        first = RulesState.from_game(game)
        second = RulesState.from_game(Game.from_dict(game.to_dict()))
        self.assertEqual(first.key(), second.key())
        self.assertNotIn(RulesAction("play", blocked), legal_actions(first))


class TestTerminalMCTS(unittest.TestCase):
    def test_agent_hash_and_request_validation(self):
        self.assertEqual(MCTS_VERSION, 2)
        self.assertEqual(len(MCTS_AGENT_HASH), 64)
        int(MCTS_AGENT_HASH, 16)
        with self.assertRaises(ValueError):
            choose_mcts_action(Game(3), BLACK, simulations=0)
        with self.assertRaises(ValueError):
            choose_mcts_action(Game(3), BLACK, rollout_policy="native")

    def test_mcts_is_legal_deterministic_nonmutating_and_save_compatible(self):
        for rules in CANDIDATES:
            for policy in ("uniform", "epsilon-greedy"):
                with self.subTest(rules=rules, policy=policy):
                    game = Game(3, rules=rules)
                    before = game.to_dict()
                    legal = set(game.legal_placements())
                    first = choose_mcts_action(
                        game,
                        BLACK,
                        simulations=3,
                        seed=917,
                        rollout_policy=policy,
                    )
                    second = choose_mcts_action(
                        Game.from_dict(before),
                        BLACK,
                        simulations=3,
                        seed=917,
                        rollout_policy=policy,
                    )
                    self.assertEqual(first.to_dict(), second.to_dict())
                    self.assertEqual(first.action.kind, "play")
                    self.assertIn(first.action.point, legal)
                    self.assertEqual(game.to_dict(), before)

    def test_mcts_respects_superko_and_can_decide_swap_and_end_actions(self):
        game = Game(3)
        game.play(game.legal_placements()[0])
        blocked = game.legal_placements()[0]
        repeated, _captured = game.try_play(blocked)
        game.history.add(signature(game.board, repeated, BLACK))
        decision = choose_mcts_action(
            game, WHITE, simulations=5, seed=44, rollout_policy="uniform"
        )
        self.assertIn(decision.action, legal_actions(RulesState.from_game(game)))
        self.assertNotEqual(decision.action, RulesAction("play", blocked))

        ended = Game(3)
        ended.play(ended.legal_placements()[0])
        ended.play_pass()
        ended.play_pass()
        end_decision = choose_mcts_action(
            ended,
            ended.to_move,
            simulations=3,
            seed=9,
            rollout_policy="epsilon-greedy",
        )
        self.assertIn(end_decision.action.kind, {"accept", "resume"})

    def test_mcts_preserves_rules_state_between_first_end_acceptances(self):
        game = Game(3)
        game.play(game.legal_placements()[0])
        game.play_pass()
        game.play_pass()
        state = apply_action(RulesState.from_game(game), RulesAction("accept"))
        before = state.key()
        decision = choose_mcts_state_action(
            state,
            state.actor_color,
            simulations=1,
            seed=811,
            rollout_policy="uniform",
        )
        self.assertIn(decision.action, legal_actions(state))
        self.assertEqual(state.key(), before)


if __name__ == "__main__":
    unittest.main()
