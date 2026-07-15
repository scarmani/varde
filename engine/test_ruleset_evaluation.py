import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from research.harness.evaluate_rulesets import (
    AgentSpec,
    _depth_ladder,
    build_schedule,
    code_hash,
    evaluate_task,
    parse_agents,
    run_evaluation,
    stable_hash,
)
from mcts import MCTS_AGENT_HASH
from native_evaluators import NATIVE_EVALUATOR_HASH
from varde import BLACK, WHITE, rulesets_public


def _config(*, agents=None, pairs=2, telemetry=False):
    agents = agents or (
        AgentSpec("native-casual", "native", difficulty="casual", hash="n"),
        AgentSpec("native-standard", "native", difficulty="standard", hash="n"),
    )
    return {
        "rulesets": ["classic"],
        "board_sizes": [3],
        "agents": [agent.__dict__ for agent in agents],
        "pairs": pairs,
        "seed": 314159,
        "telemetry": telemetry,
        "include_mirrors": False,
        "watchdog_multiplier": 20,
    }


def synthetic_game(task):
    """Fast canonical record used to exercise orchestration, not game rules."""
    a_wins = (task["pair_index"] + task["leg"]) % 3 != 0
    score = {BLACK: 30, WHITE: 24}
    final_a = task["initial_a_color"]
    if (final_a == BLACK) != a_wins:
        score = {BLACK: 24, WHITE: 30}
    counters = {
        "placements": 30,
        "passes": 2,
        "swaps": task["leg"],
        "extensions": 0,
        "resumptions": 0,
        "acceptances": 2,
        "captures": 2,
        "contact_placements": 8,
        "friendly_placements": 10,
        "tenuki_placements": 12,
        "covers": 4,
        "late_covers": 2,
        "group_splits": 1,
        "lead_changes": 2,
    }
    return {
        key: task[key]
        for key in (
            "task_id", "rules", "rules_revision", "board_size", "matchup",
            "pair_index", "leg", "seed", "agent_a", "agent_b",
            "initial_a_color",
        )
    } | {
        "status": "complete",
        "error": None,
        "actions": 34,
        "watchdog": 1080,
        "ending": "accepted-score",
        "score": score,
        "scoreable_area": 54,
        "scored_area": 54,
        "final_a_color": final_a,
        "final_b_color": WHITE if final_a == BLACK else BLACK,
        "agent_a_result": 1.0 if a_wins else 0.0,
        "agent_a_margin": 6 if a_wins else -6,
        "margin_fraction": 6 / 54,
        "wipe": False,
        "counters": counters,
        "opening": [["agent-a", [0, 0, 1]]],
        "moves": [] if task["telemetry"] else None,
    }


def incomplete_game(task):
    record = synthetic_game(task)
    record["status"] = "incomplete"
    record["error"] = "watchdog_incomplete"
    record["agent_a_result"] = None
    return record


class TestRulesetEvaluationSchedule(unittest.TestCase):
    def test_agent_parsing_and_paired_color_schedule(self):
        agents = parse_agents(
            ("native-casual", "mcts-uniform", "mcts-light@7"),
            (1, 3),
        )
        self.assertEqual(
            [agent.id for agent in agents],
            [
                "native-casual",
                "mcts-uniform@1",
                "mcts-uniform@3",
                "mcts-light@7",
            ],
        )
        tasks = build_schedule(_config(pairs=3))
        self.assertEqual(len(tasks), 6)
        for pair in range(3):
            legs = [item for item in tasks if item["pair_index"] == pair]
            self.assertEqual([item["leg"] for item in legs], [0, 1])
            self.assertEqual(
                [item["initial_a_color"] for item in legs], [BLACK, WHITE]
            )
            self.assertEqual(legs[0]["seed"], legs[1]["seed"])

    def test_only_frozen_candidates_can_be_scheduled(self):
        config = _config()
        config["rulesets"] = ["breath-cap"]
        with self.assertRaisesRegex(ValueError, "frozen candidate"):
            build_schedule(config)

    def test_depth_ladder_scores_the_high_budget_agent(self):
        agents = (
            AgentSpec("mcts-uniform@1", "mcts", budget=1,
                      rollout_policy="uniform", hash="m"),
            AgentSpec("mcts-uniform@2", "mcts", budget=2,
                      rollout_policy="uniform", hash="m"),
        )
        tasks = build_schedule(_config(agents=agents, pairs=2))
        records = [synthetic_game(task) for task in tasks]
        ladder = _depth_ladder(records)
        result = next(iter(ladder.values()))
        self.assertEqual(result["paired_samples"], 2)
        self.assertTrue(result["adjacent_rungs"])
        self.assertGreaterEqual(result["high_budget_score_rate"], 0.0)
        self.assertLessEqual(result["high_budget_score_rate"], 1.0)


class TestRulesetEvaluationRun(unittest.TestCase):
    def test_calibration_manifest_is_frozen_and_matches_agent_specs(self):
        path = (
            Path(__file__).resolve().parents[1]
            / "research/manifests/ruleset-calibration-20260715.json"
        )
        payload = json.loads(path.read_text())
        source = payload["source"]
        registry = rulesets_public()
        expected_candidates = {
            item["id"]: item["evaluation_id"]
            for item in registry["rulesets"]
            if item["status"] == "candidate"
        }

        self.assertEqual(payload["status"], "frozen-before-outcomes")
        self.assertEqual(
            {item["id"]: item["evaluation_id"] for item in payload["candidates"]},
            expected_candidates,
        )
        self.assertEqual(source["code_hash"], code_hash())
        self.assertEqual(source["ruleset_registry_hash"], stable_hash(registry))
        self.assertEqual(source["native_evaluator_hash"], NATIVE_EVALUATOR_HASH)
        self.assertEqual(source["mcts_agent_hash"], MCTS_AGENT_HASH)
        self.assertTrue(payload["claim_limits"]["flagship_promotion_blocked"])
        self.assertFalse(
            payload["timing_feasibility"]["outcomes_inspected"]
        )

        jobs = payload["jobs"]
        self.assertEqual(len({job["output_dir"] for job in jobs}), len(jobs))
        for job in jobs[:2]:
            argv = job["argv"]
            workers = int(argv[argv.index("--workers") + 1])
            checkpoint = int(argv[argv.index("--checkpoint-interval") + 1])
            self.assertGreaterEqual(checkpoint, workers)
            self.assertNotIn("--resume", argv)

    def test_committed_smoke_is_explicitly_non_claim_and_hash_pinned(self):
        path = (
            Path(__file__).resolve().parents[1]
            / "research/results/ruleset-promise-operational-smoke.json"
        )
        payload = json.loads(path.read_text())
        self.assertEqual(payload["claim_status"], "non-claim operational smoke")
        self.assertTrue(payload["accounting"]["promotion_blocked"])
        self.assertEqual(payload["accounting"]["games_complete"], 12)
        self.assertEqual(payload["accounting"]["illegal"], 0)
        self.assertTrue(all(
            not item["headline_eligible"]
            for item in payload["strata"].values()
        ))
        for value in payload["raw_artifact_hashes"].values():
            self.assertEqual(len(value), 64)
            int(value, 16)

    def test_resume_and_worker_count_are_byte_equivalent(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            full = root / "full"
            resumed = root / "resumed"
            config = _config(pairs=4)
            run_evaluation(
                full,
                config=config,
                workers=1,
                checkpoint_interval=3,
                evaluator=synthetic_game,
            )
            paused = run_evaluation(
                resumed,
                config=config,
                workers=3,
                checkpoint_interval=2,
                max_games=5,
                evaluator=synthetic_game,
            )
            self.assertEqual(paused["status"], "paused")
            completed = run_evaluation(
                resumed,
                config=config,
                workers=4,
                checkpoint_interval=4,
                resume=True,
                evaluator=synthetic_game,
            )
            self.assertEqual(completed["status"], "complete")
            for name in ("state.json", "games.jsonl", "summary.json"):
                self.assertEqual(
                    (full / name).read_bytes(), (resumed / name).read_bytes()
                )

    def test_cancel_resume_and_checkpoint_tamper_detection(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            cancel = root / "cancel"
            cancel.touch()
            config = _config()
            state = run_evaluation(
                root / "run",
                config=config,
                cancel_file=cancel,
                evaluator=synthetic_game,
            )
            self.assertEqual(state["status"], "cancelled")
            summary = json.loads((root / "run" / "summary.json").read_text())
            self.assertTrue(summary["accounting"]["cancelled"])
            self.assertEqual(summary["accounting"]["attempted"], 0)

            cancel.unlink()
            state = run_evaluation(
                root / "run",
                config=config,
                cancel_file=cancel,
                resume=True,
                evaluator=synthetic_game,
            )
            self.assertEqual(state["status"], "complete")

            path = root / "run" / "state.json"
            payload = json.loads(path.read_text())
            payload["next_task"] = 0
            path.write_text(json.dumps(payload))
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                run_evaluation(
                    root / "run",
                    config=config,
                    resume=True,
                    evaluator=synthetic_game,
                )

    def test_incomplete_attempt_is_preserved_and_blocks_promotion(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            run_evaluation(
                root,
                config=_config(pairs=1),
                evaluator=incomplete_game,
            )
            games = [
                json.loads(line)
                for line in (root / "games.jsonl").read_text().splitlines()
            ]
            summary = json.loads((root / "summary.json").read_text())
            self.assertEqual(len(games), 2)
            self.assertEqual(summary["accounting"]["watchdog_incomplete"], 2)
            self.assertEqual(summary["failure_task_ids"], [0, 1])
            self.assertTrue(summary["promotion_blocked"])

    def test_real_native_leg_is_legal_complete_and_telemetric(self):
        task = build_schedule(_config(pairs=1, telemetry=True))[0]
        result = evaluate_task(task)
        self.assertEqual(result["status"], "complete", result["error"])
        self.assertLessEqual(result["actions"], result["watchdog"])
        self.assertEqual(
            result["actions"],
            sum(
                result["counters"][name]
                for name in (
                    "placements", "passes", "swaps", "extensions",
                    "resumptions", "acceptances",
                )
            ),
        )
        self.assertEqual(len(result["moves"]), result["actions"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
