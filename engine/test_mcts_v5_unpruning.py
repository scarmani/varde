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
from mcts import choose_mcts_state_action, mcts_agent_hash  # noqa: E402
from mcts_unpruning import ordered_rule_transitions  # noqa: E402
from mcts_v5_corpus import development_positions  # noqa: E402
from mcts_v5_solver import detect_root_obligations, scan_root_guidance  # noqa: E402
from mcts_v5_unpruning import (  # noqa: E402
    build_reserved_exposure_plan,
    next_reserved_exposure_visit,
)
from varde import Game  # noqa: E402


def _position(suffix):
    return next(
        position for position in development_positions()
        if position.id.endswith(suffix)
    )


def _plan(position, *, seed=1, guided=False):
    ordered = ordered_rule_transitions(position.state, seed)
    transitions = tuple((item.action, item.state) for item in ordered)
    scan = scan_root_guidance(position.state, transitions=transitions)
    obligations = scan.obligations if guided else detect_root_obligations(
        position.state, transitions
    )
    return build_reserved_exposure_plan(
        ordered,
        obligations,
        proven_actions=scan.proven_actions if guided else (),
    ), scan


class TestMCTSV5ReservedUnpruning(unittest.TestCase):
    def test_base_schedule_and_eventual_full_expansion_are_exact(self):
        position = _position("capture-beginner-wide-equivalent")
        plan, _scan = _plan(position)
        self.assertEqual(
            [plan.base_count(visits) for visits in (4, 16, 64, 256, 1024)],
            [4, 8, 16, 32, 64],
        )
        self.assertEqual(
            set(plan.exposed_actions(10000)), set(plan.ordered_actions)
        )
        self.assertIsNone(next_reserved_exposure_visit(plan, 10000))

    def test_administrative_actions_overflow_the_base_and_are_never_hidden(self):
        position = _position("takeover-toy-wide")
        plan, _scan = _plan(position)
        self.assertEqual(plan.base_count(0), 1)
        self.assertGreaterEqual(len(plan.mandatory_actions), 2)
        self.assertTrue(
            set(plan.administrative_actions).issubset(plan.exposed_actions(0))
        )
        self.assertGreaterEqual(
            len(plan.exposed_actions(0)), len(plan.mandatory_actions)
        )

    def test_one_action_per_obligation_is_reserved(self):
        position = _position("capture-beginner-wide-conflict")
        plan, scan = _plan(position)
        self.assertGreaterEqual(len(scan.obligations), 2)
        self.assertGreaterEqual(len(plan.obligation_actions), 2)
        self.assertTrue(
            set(plan.obligation_actions).issubset(plan.exposed_actions(0))
        )

    def test_guided_arm_exposes_the_complete_proven_set(self):
        position = _position("capture-beginner-wide-equivalent")
        plan, scan = _plan(position, guided=True)
        self.assertGreaterEqual(len(scan.proven_actions), 2)
        self.assertTrue(
            set(scan.proven_actions).issubset(plan.mandatory_actions)
        )
        self.assertTrue(
            set(scan.proven_actions).issubset(plan.exposed_actions(0))
        )

    def test_semantic_ties_have_no_fixed_directional_preference(self):
        state = RulesState.from_game(Game(3, rules="breath"))
        first_points = set()
        for seed in range(128):
            ordered = ordered_rule_transitions(state, seed)
            plan = build_reserved_exposure_plan(ordered, ())
            first = plan.exposed_actions(0)[0]
            self.assertEqual(first.kind, "play")
            first_points.add(first.point)
        self.assertGreaterEqual(len(first_points), 40)

    def test_wide_root_mandatory_actions_receive_median_three_visits(self):
        position = _position("capture-toy-wide")
        before = position.state.key()
        decision = choose_mcts_state_action(
            position.state,
            position.state.actor_color,
            simulations=64,
            seed=3,
            rollout_policy="uniform",
            search_variant="v5-g0-u1-s0",
            include_root_telemetry=True,
        )
        mandatory_visits = [
            record["visits"] for record in decision.root_actions
            if record["mandatory_exposure"]
        ]
        self.assertTrue(mandatory_visits)
        self.assertGreaterEqual(statistics.median(mandatory_visits), 3)
        self.assertEqual(decision.exposed_actions, 16)
        self.assertEqual(decision.base_exposed_actions, 16)
        self.assertIn(decision.action, legal_actions(position.state))
        self.assertEqual(position.state.key(), before)

    def test_reserved_recipes_are_deterministic_distinct_and_terminal(self):
        position = _position("rescue-beginner-narrow-closure")
        for variant in ("v5-g0-u1-s0", "v5-g1-u1-s0"):
            with self.subTest(variant=variant):
                first = choose_mcts_state_action(
                    position.state,
                    position.state.actor_color,
                    simulations=8,
                    seed=771,
                    search_variant=variant,
                    include_root_telemetry=True,
                )
                second = choose_mcts_state_action(
                    position.state,
                    position.state.actor_color,
                    simulations=8,
                    seed=771,
                    search_variant=variant,
                    include_root_telemetry=True,
                )
                self.assertEqual(first.to_dict(), second.to_dict())
                self.assertEqual(first.terminal_backups, 8)
        hashes = {
            mcts_agent_hash(variant) for variant in (
                "v5-g0-u0-s0",
                "v5-g1-u0-s0",
                "v5-g0-u1-s0",
                "v5-g1-u1-s0",
            )
        }
        self.assertEqual(len(hashes), 4)
        self.assertEqual(
            mcts_agent_hash("v4-unpruning"),
            "17ec848552b44894fa44cf3fe8296346129f28aa96518a264e60ed3be76b3c0e",
        )


if __name__ == "__main__":
    unittest.main()
