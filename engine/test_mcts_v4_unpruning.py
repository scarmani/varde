from pathlib import Path
import statistics
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "engine"
HARNESS = ROOT / "research" / "harness"
for path in (ENGINE, HARNESS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from actions import RulesState, legal_actions  # noqa: E402
from mcts import _Node, choose_mcts_state_action  # noqa: E402
from mcts_tactical_fixtures import admission_positions  # noqa: E402
from mcts_unpruning import (  # noqa: E402
    next_exposure_visit,
    ordered_rule_transitions,
    progressive_exposure_count,
)
from varde import BLACK, Game  # noqa: E402


class TestProgressiveUnpruning(unittest.TestCase):
    def test_exact_exposure_schedule_and_eventual_full_expansion(self):
        expected = {4: 4, 16: 8, 64: 16, 256: 32, 1024: 64}
        for visits, exposed in expected.items():
            self.assertEqual(
                progressive_exposure_count(visits, 100),
                exposed,
            )
        self.assertEqual(progressive_exposure_count(0, 100), 1)
        self.assertEqual(progressive_exposure_count(10_000, 73), 73)
        self.assertIsNone(next_exposure_visit(10_000, 73))
        self.assertEqual(next_exposure_visit(64, 100), 65)
        with self.assertRaises(ValueError):
            progressive_exposure_count(-1, 10)
        with self.assertRaises(ValueError):
            progressive_exposure_count(1, -1)

    def test_rule_fact_order_is_deterministic_nonmutating_and_tiered(self):
        positions = admission_positions()
        observed = set()
        for position in positions:
            with self.subTest(position=position.id):
                before = position.state.key()
                first = ordered_rule_transitions(position.state, 71)
                second = ordered_rule_transitions(position.state, 71)
                self.assertEqual(first, second)
                self.assertEqual(
                    tuple(item.state.key() for item in first),
                    tuple(item.state.key() for item in second),
                )
                self.assertEqual(
                    tuple(item.action for item in first),
                    tuple(sorted(
                        legal_actions(position.state),
                        key=lambda action: next(
                            (
                                item.tier,
                                item.tie_value,
                            )
                            for item in first if item.action == action
                        ),
                    )),
                )
                self.assertEqual(position.state.key(), before)
                observed.update(item.tier_label for item in first)
        self.assertTrue({
            "administrative",
            "extension",
            "capture",
            "defense",
            "fence-completion",
            "other",
        }.issubset(observed))

    def test_semantic_seed_breaks_equal_tiers_without_fixed_direction(self):
        state = RulesState.from_game(Game(3, rules="breath"))
        winners = set()
        for seed in range(128):
            ordered = ordered_rule_transitions(state, seed)
            winners.add(ordered[0].action.point)
        self.assertGreaterEqual(len(winners), 20)
        self.assertNotEqual(
            ordered_rule_transitions(state, 1),
            ordered_rule_transitions(state, 2),
        )

    def test_node_exposes_scheduled_prefix_at_root_and_interior(self):
        state = RulesState.from_game(Game(4, rules="breath"))
        root = _Node(
            state,
            ordered_expansion=True,
            progressive_unpruning=True,
            expansion_seed=9,
        )
        root.visits = 64
        from mcts import _expansion_candidates, _node_exposure_count

        self.assertEqual(_node_exposure_count(root), 16)
        self.assertEqual(len(_expansion_candidates(root)), 16)
        interior_state = root.transition_states[root.ordered_actions[0]]
        interior = _Node(
            interior_state,
            ordered_expansion=True,
            progressive_unpruning=True,
            expansion_seed=9,
        )
        interior.visits = 16
        self.assertEqual(_node_exposure_count(interior), 8)

    def test_forced_administrative_action_is_never_hidden(self):
        forced = next(
            item for item in admission_positions()
            if item.id == "admission-gjerde-go-forced-acceptance"
        )
        decision = choose_mcts_state_action(
            forced.state,
            forced.state.actor_color,
            simulations=1,
            seed=5,
            search_variant="v4-unpruning",
            include_root_telemetry=True,
        )
        self.assertEqual(decision.action.kind, "accept")
        self.assertEqual(decision.exposed_actions, 1)
        self.assertEqual(decision.hidden_actions, 0)
        self.assertTrue(decision.root_actions[0]["exposed"])
        self.assertEqual(
            decision.root_actions[0]["ordering_tier"],
            "administrative",
        )

    def test_unpruning_has_exact_16_visit_root_telemetry(self):
        state = RulesState.from_game(Game(3, rules="breath"))
        before = state.key()
        decision = choose_mcts_state_action(
            state,
            BLACK,
            simulations=16,
            seed=101,
            rollout_policy="uniform",
            search_variant="v4-unpruning",
            include_root_telemetry=True,
        )
        self.assertEqual(decision.exposed_actions, 8)
        self.assertEqual(decision.hidden_actions, 46)
        exposed = [item for item in decision.root_actions if item["exposed"]]
        hidden = [item for item in decision.root_actions if not item["exposed"]]
        self.assertEqual(len(exposed), 8)
        self.assertEqual(len(hidden), 46)
        self.assertGreaterEqual(statistics.median(
            item["visits"] for item in exposed
        ), 1)
        self.assertTrue(all(item["visits"] == 0 for item in hidden))
        self.assertEqual(state.key(), before)

    def test_ordered_control_exposes_all_actions_but_expands_in_order(self):
        state = RulesState.from_game(Game(3, rules="breath"))
        expected = [
            item.action for item in ordered_rule_transitions(state, 103)[:4]
        ]
        decision = choose_mcts_state_action(
            state,
            BLACK,
            simulations=4,
            seed=103,
            rollout_policy="uniform",
            search_variant="v4-ordered-control",
            include_root_telemetry=True,
        )
        visited = {
            item["action_id"] for item in decision.root_actions
            if item["visits"]
        }
        expected_ids = {
            f"play:{action.point[0]},{action.point[1]}" for action in expected
        }
        self.assertEqual(visited, expected_ids)
        self.assertEqual(decision.exposed_actions, 54)
        self.assertEqual(decision.hidden_actions, 0)


if __name__ == "__main__":
    unittest.main()
