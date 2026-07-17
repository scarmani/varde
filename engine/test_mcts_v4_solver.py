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

from actions import RulesAction, RulesState, legal_actions  # noqa: E402
from mcts import choose_mcts_state_action, mcts_agent_hash  # noqa: E402
from mcts_tactical_solver import (  # noqa: E402
    DEFAULT_NODE_LIMIT,
    find_tactical_override,
    solve_local_obligation,
)
from mcts_v4_holdout import (  # noqa: E402
    decoy_positions,
    positive_positions,
)
from varde import BLACK, WHITE, signature  # noqa: E402


def _action_statuses(result):
    return {
        (
            action.kind if action.point is None
            else f"{action.kind}:{action.point[0]},{action.point[1]}"
        ): status
        for action, status in result.action_statuses
    }


def _swapped_state(state):
    game = state.game.clone()
    game.state = {
        point: tuple(WHITE if color == BLACK else BLACK for color in stack)
        for point, stack in game.state.items()
    }
    game.to_move = WHITE if game.to_move == BLACK else BLACK
    game.history = {signature(game.board, game.state, game.to_move)}
    return RulesState(
        game,
        seats=dict(state.seats),
        end_acceptances=set(state.end_acceptances),
        end_decider=(
            None if state.end_decider is None
            else (WHITE if state.end_decider == BLACK else BLACK)
        ),
        accepted=state.accepted,
    )


class TestCertifiedTacticalSolver(unittest.TestCase):
    def test_all_positive_certificates_are_reproduced(self):
        elapsed = {3: [], 4: []}
        for position in positive_positions():
            with self.subTest(position=position.id):
                before = position.state.key()
                started = time.perf_counter()
                result = solve_local_obligation(
                    position.state,
                    position.obligation,
                )
                elapsed[position.state.game.board.n].append(
                    (time.perf_counter() - started) * 1000
                )
                self.assertEqual(
                    _action_statuses(result),
                    position.certificate["action_statuses"],
                )
                self.assertEqual(
                    result.override_action,
                    position.acceptable_actions[0],
                )
                self.assertLessEqual(result.nodes, DEFAULT_NODE_LIMIT)
                self.assertFalse(result.limit_reached)
                self.assertEqual(position.state.key(), before)
        # These are generous regression ceilings; the batch report records the
        # measured p95 separately from deterministic correctness evidence.
        self.assertLess(statistics.quantiles(elapsed[3], n=20)[18], 100)
        self.assertLess(statistics.quantiles(elapsed[4], n=20)[18], 400)

    def test_all_decoys_force_exact_abstention(self):
        for position in decoy_positions():
            with self.subTest(position=position.id):
                result = solve_local_obligation(
                    position.state,
                    position.obligation,
                )
                self.assertEqual(
                    _action_statuses(result),
                    position.certificate["action_statuses"],
                )
                self.assertIsNone(result.override_action)

    def test_node_limit_fails_closed_as_unknown(self):
        position = next(
            item for item in decoy_positions()
            if item.id == "v4-decoy-rescue-toy"
        )
        result = solve_local_obligation(
            position.state,
            position.obligation,
            node_limit=1,
        )
        self.assertTrue(result.limit_reached)
        self.assertIn("unknown", _action_statuses(result).values())
        self.assertIsNone(result.override_action)

    def test_capture_proof_is_exactly_color_symmetric(self):
        position = next(
            item for item in positive_positions()
            if item.id == "v4-capture-toy-a"
        )
        original = solve_local_obligation(position.state, position.obligation)
        swapped_state = _swapped_state(position.state)
        swapped = solve_local_obligation(swapped_state, position.obligation)
        self.assertEqual(_action_statuses(swapped), _action_statuses(original))
        self.assertEqual(swapped.override_action, original.override_action)

    def test_automatic_scan_handles_every_obligation_family(self):
        ids = (
            "v4-capture-toy-a",
            "v4-defense-toy-a",
            "v4-rescue-toy-a",
            "v4-fence-toy-a",
            "v4-takeover-toy-a",
            "v4-ending-toy-a",
        )
        positions = {item.id: item for item in positive_positions()}
        for position_id in ids:
            with self.subTest(position=position_id):
                position = positions[position_id]
                scan = find_tactical_override(position.state)
                self.assertIn(
                    scan.override_action,
                    position.acceptable_actions,
                )
                self.assertGreaterEqual(scan.obligations_checked, 1)
                self.assertGreater(scan.nodes, 0)

    def test_solver_recipe_overrides_root_and_reports_telemetry(self):
        position = next(
            item for item in positive_positions()
            if item.id == "v4-ending-toy-a"
        )
        decision = choose_mcts_state_action(
            position.state,
            position.state.actor_color,
            simulations=4,
            seed=37,
            rollout_policy="uniform",
            search_variant="v4-solver",
            include_root_telemetry=True,
        )
        self.assertEqual(decision.action, RulesAction("accept"))
        self.assertEqual(decision.selection_reason, "certified-local-obligation")
        self.assertEqual(decision.solver_status, "override")
        self.assertGreaterEqual(decision.solver_invocations, 1)
        self.assertGreaterEqual(decision.solver_overrides, 1)
        self.assertTrue(any(
            item["solver_override"] for item in decision.root_actions
        ))

    def test_v4_control_preserves_tie_margin_decisions(self):
        for position in positive_positions()[-4:]:
            with self.subTest(position=position.id):
                control = choose_mcts_state_action(
                    position.state,
                    position.state.actor_color,
                    simulations=3,
                    seed=91,
                    rollout_policy="uniform",
                    search_variant="v4-control",
                )
                historical = choose_mcts_state_action(
                    position.state,
                    position.state.actor_color,
                    simulations=3,
                    seed=91,
                    rollout_policy="uniform",
                    search_variant="tie-margin",
                )
                self.assertEqual(control.action, historical.action)
                self.assertEqual(control.mean_value, historical.mean_value)
        self.assertNotEqual(
            mcts_agent_hash("v4-control"),
            mcts_agent_hash("v4-solver"),
        )

    def test_superko_filtered_actions_never_enter_solver_statuses(self):
        position = positive_positions()[0]
        state = position.state.clone()
        action = legal_actions(state)[0]
        if action.kind == "play":
            repeated, _captured = state.game.try_play(action.point)
            state.game.history.add(signature(
                state.game.board,
                repeated,
                state.game.to_move,
            ))
            if action not in legal_actions(state):
                result = solve_local_obligation(state, position.obligation)
                self.assertNotIn(
                    action,
                    {candidate for candidate, _status in result.action_statuses},
                )


if __name__ == "__main__":
    unittest.main()
