from pathlib import Path
import statistics
import sys
import time
import unittest


ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "engine"
HARNESS = ROOT / "research" / "harness"
for path in (ENGINE, HARNESS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from actions import legal_actions, legal_transitions  # noqa: E402
from mcts import choose_mcts_state_action, mcts_agent_hash  # noqa: E402
from mcts_v5_corpus import development_positions  # noqa: E402
from mcts_v5_solver import (  # noqa: E402
    scan_root_guidance,
    solve_root_obligation,
)


def _position(suffix):
    return next(
        position for position in development_positions()
        if position.id.endswith(suffix)
    )


def _trace_without_guidance_fields(decision):
    ignored = {"proof_guidance_status", "proof_guidance_bias"}
    return tuple(
        {key: value for key, value in record.items() if key not in ignored}
        for record in decision.root_actions
    )


class TestMCTSV5CorrectedRootGuidance(unittest.TestCase):
    def test_solver_agrees_with_independent_oracle_on_every_development_action(self):
        for position in development_positions():
            with self.subTest(position=position.id):
                before = position.state.key()
                oracle = position.certificate()
                solver = solve_root_obligation(position.state, position.goal)
                self.assertEqual(
                    dict(solver.action_statuses),
                    dict(oracle.action_statuses),
                )
                self.assertEqual(solver.proven_actions, oracle.proven_actions)
                self.assertEqual(solver.unknown_actions, oracle.unknown_actions)
                self.assertEqual(
                    solver.disproven_actions, oracle.disproven_actions
                )
                self.assertFalse(solver.limit_reached)
                self.assertEqual(position.state.key(), before)

    def test_exact_decoy_obligations_have_zero_false_positive_guidance(self):
        for position in development_positions():
            if not position.decoy:
                continue
            with self.subTest(position=position.id):
                result = solve_root_obligation(position.state, position.goal)
                self.assertEqual(result.proven_actions, ())

    def test_actor_changing_rescue_and_equivalent_sets_are_preserved(self):
        closure = _position("rescue-beginner-narrow-closure")
        result = solve_root_obligation(closure.state, closure.goal)
        self.assertEqual(len(result.proven_actions), 1)
        equivalent = _position("capture-beginner-wide-equivalent")
        result = solve_root_obligation(equivalent.state, equivalent.goal)
        self.assertEqual(len(result.proven_actions), 2)

    def test_root_scan_reuses_supplied_transitions_and_runs_once(self):
        position = _position("capture-beginner-wide-conflict")
        transitions = legal_transitions(position.state)
        before = position.state.key()
        scan = scan_root_guidance(position.state, transitions=transitions)
        self.assertEqual(scan.root_scans, 1)
        self.assertGreaterEqual(len(scan.obligations), 2)
        self.assertTrue(scan.proven_actions)
        self.assertEqual(position.state.key(), before)

    def test_bias_is_exact_and_decays_without_exclusion(self):
        position = _position("capture-toy-wide")
        scan = scan_root_guidance(position.state)
        proven = scan.proven_actions[0]
        disproven = next(
            action for action in legal_actions(position.state)
            if scan.status_for(action) == "disproven"
        )
        self.assertEqual(scan.bias_for(proven, 0), 1.0)
        self.assertEqual(scan.bias_for(proven, 3), 0.25)
        self.assertEqual(scan.bias_for(disproven, 0), -1.0)
        self.assertEqual(scan.bias_for(disproven, 3), -0.25)
        self.assertEqual(
            set(dict(scan.action_statuses)), set(legal_actions(position.state))
        )

    def test_unknown_only_guidance_preserves_control_decision_and_trace(self):
        position = _position("takeover-toy-narrow-decoy")
        control = choose_mcts_state_action(
            position.state,
            position.state.actor_color,
            simulations=16,
            seed=7001,
            rollout_policy="uniform",
            search_variant="v5-g0-u0-s0",
            include_root_telemetry=True,
        )
        guided = choose_mcts_state_action(
            position.state,
            position.state.actor_color,
            simulations=16,
            seed=7001,
            rollout_policy="uniform",
            search_variant="v5-g1-u0-s0",
            include_root_telemetry=True,
        )
        self.assertEqual(guided.solver_invocations, 1)
        self.assertEqual(guided.solver_status, "abstain")
        self.assertEqual(control.action, guided.action)
        self.assertEqual(control.mean_value, guided.mean_value)
        self.assertEqual(
            _trace_without_guidance_fields(control),
            _trace_without_guidance_fields(guided),
        )

    def test_guidance_is_deterministic_legal_non_mutating_and_root_only(self):
        position = _position("rescue-beginner-narrow-closure")
        before = position.state.key()
        first = choose_mcts_state_action(
            position.state,
            position.state.actor_color,
            simulations=16,
            seed=8128,
            search_variant="v5-g1-u0-s0",
            include_root_telemetry=True,
        )
        second = choose_mcts_state_action(
            position.state,
            position.state.actor_color,
            simulations=16,
            seed=8128,
            search_variant="v5-g1-u0-s0",
            include_root_telemetry=True,
        )
        self.assertEqual(first.to_dict(), second.to_dict())
        self.assertIn(first.action, legal_actions(position.state))
        self.assertEqual(first.solver_invocations, 1)
        self.assertEqual(first.solver_overrides, 0)
        self.assertEqual(first.terminal_backups, first.simulations)
        self.assertEqual(position.state.key(), before)

    def test_root_scan_latency_feasibility(self):
        elapsed = {3: [], 4: []}
        for position in development_positions():
            transitions = legal_transitions(position.state)
            started = time.perf_counter()
            scan_root_guidance(position.state, transitions=transitions)
            elapsed[position.state.game.board.n].append(
                (time.perf_counter() - started) * 1000
            )
        self.assertLess(statistics.quantiles(elapsed[3], n=20)[18], 100)
        self.assertLess(statistics.quantiles(elapsed[4], n=20)[18], 400)

    def test_v5_recipe_hashes_are_distinct_and_v4_hash_is_unchanged(self):
        self.assertNotEqual(
            mcts_agent_hash("v5-g0-u0-s0"),
            mcts_agent_hash("v5-g1-u0-s0"),
        )
        self.assertEqual(
            mcts_agent_hash("v4-control"),
            "b1349822959ab4968503208d1fc48d3dfb1c6a900914b95519a5e73693ff49cf",
        )


if __name__ == "__main__":
    unittest.main()
