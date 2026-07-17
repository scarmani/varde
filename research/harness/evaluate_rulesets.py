#!/usr/bin/env python3
"""Reproducible paired falsification harness for frozen Varde rulesets.

This is research infrastructure.  Its watchdog classifies an attempt as
incomplete; it never alters the live-game rules or forces a result.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from dataclasses import asdict, dataclass
import hashlib
from itertools import combinations
import json
import os
from pathlib import Path
import random
import statistics
import subprocess
import sys
import tempfile
import time


REPO_ROOT = Path(__file__).resolve().parents[2]
ENGINE_ROOT = REPO_ROOT / "engine"
HARNESS_ROOT = Path(__file__).resolve().parent
if str(ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(ENGINE_ROOT))
if str(HARNESS_ROOT) not in sys.path:
    sys.path.insert(0, str(HARNESS_ROOT))

from actions import RulesAction, RulesState, apply_action, legal_actions  # noqa: E402
from mcts import MCTS_AGENT_HASH, choose_mcts_state_action  # noqa: E402
from native_evaluators import NATIVE_EVALUATOR_HASH  # noqa: E402
from opponent import choose_decision  # noqa: E402
from mcts_telemetry import annotate_choice, tactical_context  # noqa: E402
from varde import (  # noqa: E402
    BLACK,
    WHITE,
    Game,
    Illegal,
    control,
    get_ruleset_spec,
    groups_of,
    other,
    rulesets_public,
)


FORMAT = "varde-ruleset-evaluation"
VERSION = 1
RECIPE = "paired-native-terminal-mcts-v1"
DEFAULT_OUTPUT = Path(tempfile.gettempdir()) / "varde-ruleset-evaluation"
DEFAULT_WATCHDOG_MULTIPLIER = 20


def canonical_bytes(payload):
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()


def stable_hash(payload):
    return hashlib.sha256(canonical_bytes(payload)).hexdigest()


def derive_seed(master_seed, *parts):
    digest = hashlib.sha256(canonical_bytes([int(master_seed), *parts])).digest()
    return int.from_bytes(digest[:8], "big")


def source_commit():
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def code_hash():
    paths = (
        Path(__file__),
        ENGINE_ROOT / "actions.py",
        ENGINE_ROOT / "mcts.py",
        ENGINE_ROOT / "native_evaluators.py",
        ENGINE_ROOT / "opponent.py",
        ENGINE_ROOT / "varde.py",
        HARNESS_ROOT / "mcts_telemetry.py",
    )
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def write_json_atomic(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n"
    )
    temporary.replace(path)


def write_jsonl_atomic(path, records):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(
        b"".join(canonical_bytes(record) + b"\n" for record in records)
    )
    temporary.replace(path)


@dataclass(frozen=True)
class AgentSpec:
    id: str
    family: str
    difficulty: str | None = None
    budget: int | None = None
    rollout_policy: str | None = None
    hash: str | None = None


def parse_agents(raw_agents, budgets):
    parsed = []
    seen = set()
    for raw in raw_agents:
        token = raw.strip().lower()
        if token in ("native", "native-standard", "native-casual"):
            difficulty = "casual" if token == "native-casual" else "standard"
            specs = [
                AgentSpec(
                    id=f"native-{difficulty}",
                    family="native",
                    difficulty=difficulty,
                    hash=NATIVE_EVALUATOR_HASH,
                )
            ]
        elif token.startswith("mcts-uniform") or token.startswith("mcts-light"):
            policy = "uniform" if token.startswith("mcts-uniform") else "epsilon-greedy"
            explicit = token.split("@", 1)[1] if "@" in token else None
            active_budgets = (int(explicit),) if explicit else budgets
            specs = [
                AgentSpec(
                    id=f"mcts-{'uniform' if policy == 'uniform' else 'light'}@{budget}",
                    family="mcts",
                    budget=budget,
                    rollout_policy=policy,
                    hash=MCTS_AGENT_HASH,
                )
                for budget in active_budgets
            ]
        else:
            raise ValueError(f"unknown agent: {raw}")
        for spec in specs:
            if not spec.budget and spec.family == "mcts":
                raise ValueError("MCTS budget must be positive")
            if spec.id not in seen:
                parsed.append(spec)
                seen.add(spec.id)
    if not parsed:
        raise ValueError("at least one agent is required")
    return tuple(parsed)


def build_matchups(agents, include_mirrors=False):
    matchups = list(combinations(agents, 2))
    if include_mirrors or len(agents) == 1:
        matchups.extend((agent, agent) for agent in agents)
    if not matchups:
        raise ValueError("at least two agents or --include-mirrors is required")
    return tuple(matchups)


def build_schedule(config):
    tasks = []
    task_id = 0
    agents = tuple(AgentSpec(**item) for item in config["agents"])
    matchups = build_matchups(agents, config["include_mirrors"])
    for rules in config["rulesets"]:
        spec = get_ruleset_spec(rules)
        if spec.status != "candidate":
            raise ValueError(f"evaluation requires a frozen candidate: {rules}")
        for board_size in config["board_sizes"]:
            if not spec.min_size <= board_size <= spec.max_size:
                raise ValueError(f"board size {board_size} is invalid for {rules}")
            for agent_a, agent_b in matchups:
                matchup = f"{agent_a.id}__vs__{agent_b.id}"
                for pair_index in range(config["pairs"]):
                    pair_seed = derive_seed(
                        config["seed"], rules, board_size, matchup, pair_index
                    )
                    for leg in (0, 1):
                        tasks.append(
                            {
                                "task_id": task_id,
                                "rules": rules,
                                "rules_revision": spec.evaluation_id,
                                "board_size": board_size,
                                "matchup": matchup,
                                "pair_index": pair_index,
                                "leg": leg,
                                "seed": pair_seed,
                                "agent_a": asdict(agent_a),
                                "agent_b": asdict(agent_b),
                                "initial_a_color": BLACK if leg == 0 else WHITE,
                                "telemetry": config["telemetry"],
                                "watchdog_multiplier": config["watchdog_multiplier"],
                            }
                        )
                        task_id += 1
    return tasks


def _native_action(state, agent, seed):
    actions = legal_actions(state)
    extensions = [action for action in actions if action.kind == "extend"]
    if extensions:
        action = extensions[
            derive_seed(seed, state.game.moves_played) % len(extensions)
        ]
        return action, {
            "agent_family": "native",
            "difficulty": agent["difficulty"],
            "nodes": 0,
            "reason_code": "extension",
        }
    finish = next(
        (action for action in actions if action.kind == "finish-extension"), None
    )
    if finish is not None:
        return finish, {
            "agent_family": "native",
            "difficulty": agent["difficulty"],
            "nodes": 0,
            "reason_code": "finish-extension",
        }
    decision = choose_decision(
        state.game,
        state.actor_color,
        difficulty=agent["difficulty"],
        seed=seed,
    )
    action = RulesAction(decision.action, decision.point)
    if action not in actions:
        raise Illegal("native agent returned an illegal action")
    return action, {
        "agent_family": "native",
        "difficulty": agent["difficulty"],
        "nodes": decision.nodes,
        "elapsed_ms": round(decision.elapsed_ms, 3),
        "reason_code": decision.reason_code,
    }


def _agent_action(state, agent, seed):
    if agent["family"] == "native":
        return _native_action(state, agent, seed)
    started = time.perf_counter()
    decision = choose_mcts_state_action(
        state,
        state.actor_color,
        simulations=agent["budget"],
        seed=seed,
        rollout_policy=agent["rollout_policy"],
    )
    if decision.action not in legal_actions(state):
        raise Illegal("MCTS returned an illegal action")
    elapsed_ms = (time.perf_counter() - started) * 1000
    return decision.action, {
        "agent_family": "mcts",
        "simulations": decision.simulations,
        "nodes": decision.nodes,
        "mean_value": round(decision.mean_value, 6),
        "rollout_policy": decision.rollout_policy,
        "average_rollout_actions": round(
            decision.average_rollout_actions, 3
        ),
        "max_rollout_actions": decision.max_rollout_actions,
        "elapsed_ms": round(elapsed_ms, 3),
    }


def _outcome_for_color(score, color):
    enemy = other(color)
    if score[color] > score[enemy]:
        return 1.0
    if score[color] < score[enemy]:
        return 0.0
    return 0.5


def is_wipe(score, scoreable_area):
    """Return whether a decisive result meets the declared wipe threshold.

    A wipe is defined in terms of the *loser's* score.  Tied sparse Gjerde
    positions have no loser, so they cannot be wipes even when both scores are
    below ten percent of the fenced-cell area.
    """
    if score[BLACK] == score[WHITE]:
        return False
    return min(score.values()) < 0.1 * scoreable_area


def evaluate_task(task):
    """Play one scheduled leg; all failures become canonical records."""
    record = {
        key: task[key]
        for key in (
            "task_id", "rules", "rules_revision", "board_size", "matchup",
            "pair_index", "leg", "seed", "agent_a", "agent_b",
            "initial_a_color",
        )
    }
    game = Game(task["board_size"], rules=task["rules"])
    initial_a = task["initial_a_color"]
    initial_b = other(initial_a)
    state = RulesState(
        game,
        seats={initial_a: "agent-a", initial_b: "agent-b"},
    )
    agents = {"agent-a": task["agent_a"], "agent-b": task["agent_b"]}
    agent_seeds = {
        "agent-a": derive_seed(task["seed"], "agent-a"),
        "agent-b": derive_seed(task["seed"], "agent-b"),
    }
    point_count = len(game.board.points)
    scoreable = len(game.board.cells) if hasattr(game.board, "cells") else point_count
    watchdog = task["watchdog_multiplier"] * point_count
    counters = {
        "placements": 0,
        "passes": 0,
        "swaps": 0,
        "extensions": 0,
        "resumptions": 0,
        "acceptances": 0,
        "captures": 0,
        "contact_placements": 0,
        "friendly_placements": 0,
        "tenuki_placements": 0,
        "covers": 0,
        "late_covers": 0,
        "group_splits": 0,
        "lead_changes": 0,
    }
    opening = []
    moves = []
    last_lead = 0
    status = "complete"
    error = None
    actions_played = 0
    try:
        while not state.terminal and actions_played < watchdog:
            actor_color = state.actor_color
            actor_seat = state.actor_seat
            before_state = dict(state.game.state)
            before_enemy_groups = len(groups_of(game.board, game.state, other(actor_color)))
            before_score = game.score()
            context = tactical_context(state) if task["telemetry"] else None
            action, decision_telemetry = _agent_action(
                state, agents[actor_seat], agent_seeds[actor_seat]
            )
            occupied = bool(
                action.point is not None and before_state[action.point]
            )
            friendly = enemy = 0
            if action.point is not None:
                friendly = sum(
                    control(before_state, neighbor) == actor_color
                    for neighbor in game.board.neighbors[action.point]
                )
                enemy = sum(
                    control(before_state, neighbor) == other(actor_color)
                    for neighbor in game.board.neighbors[action.point]
                )
            apply_action(state, action, copy=False, validate=False)
            actions_played += 1
            captured = sum(len(wave) for wave in game.last_capture_waves)
            counters["captures"] += captured
            if action.kind == "play":
                counters["placements"] += 1
                counters["contact_placements"] += enemy > 0
                counters["friendly_placements"] += friendly > 0
                counters["tenuki_placements"] += not friendly and not enemy
                counters["covers"] += occupied
                counters["late_covers"] += occupied and actions_played >= 0.6 * point_count
                if len(opening) < 12:
                    opening.append([actor_seat, list(action.point)])
                after_enemy_groups = len(
                    groups_of(game.board, game.state, other(actor_color))
                )
                counters["group_splits"] += after_enemy_groups > before_enemy_groups
            elif action.kind == "pass":
                counters["passes"] += 1
            elif action.kind == "swap":
                counters["swaps"] += 1
            elif action.kind == "extend":
                counters["extensions"] += 1
            elif action.kind == "resume":
                counters["resumptions"] += 1
            elif action.kind == "accept":
                counters["acceptances"] += 1
            after_score = game.score()
            lead = (after_score[BLACK] > after_score[WHITE]) - (
                after_score[BLACK] < after_score[WHITE]
            )
            if last_lead and lead and lead != last_lead:
                counters["lead_changes"] += 1
            if lead:
                last_lead = lead
            if task["telemetry"]:
                moves.append(
                    {
                        "action_index": actions_played - 1,
                        "actor_color": actor_color,
                        "actor_seat": actor_seat,
                        **action.to_dict(),
                        "captured": captured,
                        "score_before": before_score,
                        "score_after": after_score,
                        "decision": decision_telemetry,
                        "tactical_context": context,
                        "tactical_choice": annotate_choice(context, action),
                    }
                )
        if not state.terminal:
            status = "incomplete"
            error = "watchdog_incomplete"
    except Illegal as exc:
        status = "illegal"
        error = str(exc)
    except Exception as exc:  # research records must preserve every crash
        status = "crash"
        error = f"{type(exc).__name__}: {exc}"

    score = game.score()
    final_a_color = state.color_for_seat("agent-a")
    final_b_color = state.color_for_seat("agent-b")
    a_result = _outcome_for_color(score, final_a_color) if status == "complete" else None
    margin = score[final_a_color] - score[final_b_color]
    record.update(
        {
            "status": status,
            "error": error,
            "actions": actions_played,
            "watchdog": watchdog,
            "ending": (
                "stagnation"
                if game.no_progress_end
                else "accepted-score" if state.terminal else "incomplete"
            ),
            "score": score,
            "scoreable_area": scoreable,
            "scored_area": score[BLACK] + score[WHITE],
            "final_a_color": final_a_color,
            "final_b_color": final_b_color,
            "agent_a_result": a_result,
            "agent_a_margin": margin,
            "margin_fraction": abs(margin) / max(1, scoreable),
            "wipe": is_wipe(score, scoreable),
            "counters": counters,
            "opening": opening,
            "moves": moves if task["telemetry"] else None,
        }
    )
    return record


def one_sided_bootstrap_lower(pair_scores, seed, samples=4000):
    if not pair_scores:
        return None
    rng = random.Random(seed)
    means = []
    for _ in range(samples):
        sample = [pair_scores[rng.randrange(len(pair_scores))] for _ in pair_scores]
        means.append(sum(sample) / len(sample))
    means.sort()
    return means[max(0, int(0.05 * samples) - 1)]


def _rate(values):
    return sum(values) / len(values) if values else None


def _paired_scores(records, value):
    pairs = {}
    for record in records:
        if record["status"] == "complete":
            pairs.setdefault(record["pair_index"], []).append(record)
    return [
        sum(value(item) for item in legs) / 2
        for _pair, legs in sorted(pairs.items())
        if len(legs) == 2
    ]


def _depth_ladder(records):
    """Summarize direct MCTS budget comparisons without inferring strength."""
    grouped = {}
    for record in records:
        agent_a = record["agent_a"]
        agent_b = record["agent_b"]
        if (
            agent_a["family"] != "mcts"
            or agent_b["family"] != "mcts"
            or agent_a["rollout_policy"] != agent_b["rollout_policy"]
            or agent_a["budget"] == agent_b["budget"]
        ):
            continue
        low, high = sorted((agent_a["budget"], agent_b["budget"]))
        key = (
            record["rules"],
            record["board_size"],
            agent_a["rollout_policy"],
            low,
            high,
        )
        grouped.setdefault(key, []).append(record)

    results = {}
    for key, games in sorted(grouped.items()):
        rules, board_size, policy, low, high = key

        def high_result(item):
            if item["agent_a"]["budget"] == high:
                return item["agent_a_result"]
            return 1.0 - item["agent_a_result"]

        pair_scores = _paired_scores(games, high_result)
        budgets = sorted({
            agent["budget"]
            for item in records
            for agent in (item["agent_a"], item["agent_b"])
            if agent["family"] == "mcts"
            and agent["rollout_policy"] == policy
        })
        name = f"{rules}|n={board_size}|{policy}|{low}->{high}"
        results[name] = {
            "paired_samples": len(pair_scores),
            "high_budget_score_rate": _rate(pair_scores),
            "one_sided_95_paired_bootstrap_lower": one_sided_bootstrap_lower(
                pair_scores, derive_seed(0, "depth", name)
            ),
            "adjacent_rungs": budgets.index(high) == budgets.index(low) + 1,
            "passes_55_percent_indicator": bool(pair_scores)
            and _rate(pair_scores) >= 0.55,
            "interpretation": (
                "depth signal only; require held-out adjacent rungs and both "
                "rollout policies before a strategic-depth claim"
            ),
        }
    return results


def _ruleset_evidence_status(strata, depth_ladder, config):
    statuses = {}
    policy_budgets = {}
    for item in config["agents"]:
        if item["family"] == "mcts":
            policy_budgets.setdefault(item["rollout_policy"], set()).add(
                item["budget"]
            )
    configured_policies = set(policy_budgets)
    required_policies = {"uniform", "epsilon-greedy"}
    for rules in config["rulesets"]:
        relevant = {
            key: value for key, value in strata.items()
            if key.startswith(f"{rules}|")
        }
        cross_by_policy = {
            policy: [
                value for key, value in relevant.items()
                if "native-" in key
                and (
                    "mcts-uniform" in key if policy == "uniform"
                    else "mcts-light" in key
                )
                and value["headline_eligible"]
            ]
            for policy in required_policies
        }
        depth_by_policy = {}
        for policy in required_policies:
            budgets = sorted(policy_budgets.get(policy, ()))
            expected = list(zip(budgets, budgets[1:]))
            found = {
                (int(key.rsplit("|", 1)[1].split("->")[0]),
                 int(key.rsplit("->", 1)[1]))
                for key, value in depth_ladder.items()
                if key.startswith(f"{rules}|")
                and f"|{policy}|" in key
                and value["adjacent_rungs"]
                and value["paired_samples"] >= 100
            }
            depth_by_policy[policy] = {
                "configured_budgets": budgets,
                "required_adjacent_comparisons": [list(item) for item in expected],
                "complete_adjacent_comparisons": [
                    list(item) for item in sorted(found)
                ],
                "two_adjacent_rungs_complete": len(expected) >= 2
                and set(expected).issubset(found),
            }
        eligible_cross = [
            item for values in cross_by_policy.values() for item in values
        ]
        health_pass = bool(eligible_cross) and all(
            all(item["health_gates"].values()) for item in eligible_cross
        )
        both_cross = all(cross_by_policy.values())
        both_depth = all(
            value["two_adjacent_rungs_complete"]
            for value in depth_by_policy.values()
        )
        statuses[rules] = {
            "cross_family_100_pair_by_policy": {
                policy: bool(values)
                for policy, values in sorted(cross_by_policy.items())
            },
            "depth_ladder_by_policy": depth_by_policy,
            "uniform_and_light_configured": required_policies.issubset(
                configured_policies
            ),
            "eligible_health_gates_pass": health_pass,
            "headline_claim_ready": both_cross
            and both_depth
            and required_policies.issubset(configured_policies)
            and health_pass,
        }
    return statuses


def summarize(records, config, provenance, status):
    complete = [record for record in records if record["status"] == "complete"]
    failures = [record for record in records if record["status"] != "complete"]
    strata = {}
    keys = sorted({
        (record["rules"], record["board_size"], record["matchup"])
        for record in records
    })
    for rules, board_size, matchup in keys:
        games = [
            record for record in records
            if (record["rules"], record["board_size"], record["matchup"])
            == (rules, board_size, matchup)
        ]
        done = [record for record in games if record["status"] == "complete"]
        pairs = {}
        for record in done:
            pairs.setdefault(record["pair_index"], []).append(record)
        pair_scores = [
            sum(item["agent_a_result"] for item in legs) / len(legs)
            for _pair, legs in sorted(pairs.items())
            if len(legs) == 2
        ]
        black_results = [
            _outcome_for_color(item["score"], BLACK) for item in done
        ]
        original_black_results = {
            item["task_id"]: _outcome_for_color(
                item["score"],
                item["final_a_color"] if item["initial_a_color"] == BLACK
                else item["final_b_color"],
            )
            for item in done
        }
        swapped = [item for item in done if item["counters"]["swaps"]]
        placements = sum(item["counters"]["placements"] for item in done)
        opening_counts = {}
        for item in done:
            opening_hash = stable_hash(item["opening"])
            opening_counts[opening_hash] = opening_counts.get(opening_hash, 0) + 1
        top_opening_rate = (
            max(opening_counts.values()) / len(done) if done else None
        )
        key = f"{rules}|n={board_size}|{matchup}"
        strata[key] = {
            "games_attempted": len(games),
            "games_complete": len(done),
            "paired_samples": len(pair_scores),
            "agent_a_score_rate": _rate(
                [item["agent_a_result"] for item in done]
            ),
            "paired_score_rate": _rate(pair_scores),
            "one_sided_95_paired_bootstrap_lower": one_sided_bootstrap_lower(
                pair_scores,
                derive_seed(config["seed"], "bootstrap", key),
            ),
            "black_score_rate": _rate(black_results),
            "original_black_player_score_rate": _rate(
                list(original_black_results.values())
            ),
            "post_swap_original_player_score_rate": _rate([
                original_black_results[item["task_id"]] for item in swapped
            ]),
            "swap_rate": _rate([
                item["counters"]["swaps"] > 0 for item in done
            ]),
            "stagnation_rate": _rate([
                item["ending"] == "stagnation" for item in done
            ]),
            "wipe_rate": _rate([item["wipe"] for item in done]),
            "median_absolute_margin_fraction": (
                statistics.median(item["margin_fraction"] for item in done)
                if done else None
            ),
            "median_actions": (
                statistics.median(item["actions"] for item in done)
                if done else None
            ),
            "mean_scored_area_fraction": (
                statistics.fmean(
                    item["scored_area"] / max(1, item["scoreable_area"])
                    for item in done
                ) if done else None
            ),
            "strategic_telemetry": {
                "contact_rate": sum(
                    item["counters"]["contact_placements"] for item in done
                ) / max(1, placements),
                "friendly_connection_rate": sum(
                    item["counters"]["friendly_placements"] for item in done
                ) / max(1, placements),
                "tenuki_rate": sum(
                    item["counters"]["tenuki_placements"] for item in done
                ) / max(1, placements),
                "cover_rate": sum(
                    item["counters"]["covers"] for item in done
                ) / max(1, placements),
                "captures_per_game": sum(
                    item["counters"]["captures"] for item in done
                ) / max(1, len(done)),
                "lead_changes_per_game": sum(
                    item["counters"]["lead_changes"] for item in done
                ) / max(1, len(done)),
                "group_splits_per_game": sum(
                    item["counters"]["group_splits"] for item in done
                ) / max(1, len(done)),
                "unique_openings": len({
                    stable_hash(item["opening"]) for item in done
                }),
                "top_opening_family_rate": top_opening_rate,
                "opening_convergence_warning": bool(done)
                and top_opening_rate > 0.50,
                "opening_gate_status": (
                    "warning only; failure requires a demonstrated pie-rule "
                    "defeat, not frequency alone"
                ),
                "decisive_commitment_point": None,
                "decisive_commitment_status": (
                    "requires per-position held-out win-probability estimates"
                ),
                "sacrifice_frequency": None,
                "sacrifice_status": "requires group-identity move telemetry",
            },
            "health_gates": {
                "zero_failures": len(done) == len(games),
                "stagnation_at_most_5_percent": bool(done) and _rate([
                    item["ending"] == "stagnation" for item in done
                ]) <= 0.05,
                "wipes_at_most_15_percent": bool(done) and _rate([
                    item["wipe"] for item in done
                ]) <= 0.15,
                "black_score_rate_40_to_60": bool(done) and 0.40 <= _rate(black_results) <= 0.60,
                "original_black_player_rate_40_to_60": bool(done)
                and 0.40 <= _rate(list(original_black_results.values())) <= 0.60,
                "post_swap_original_player_rate_40_to_60": bool(swapped)
                and 0.40 <= _rate([
                    original_black_results[item["task_id"]] for item in swapped
                ]) <= 0.60,
                "median_margin_below_15_percent": bool(done) and statistics.median(
                    item["margin_fraction"] for item in done
                ) < 0.15,
                "swap_rate_25_to_75": bool(done) and 0.25 <= _rate([
                    item["counters"]["swaps"] > 0 for item in done
                ]) <= 0.75,
            },
            "headline_eligible": (
                len(pair_scores) >= 100
                and len(done) == len(games)
                and len({
                    item["agent_a"]["family"] for item in done
                } | {
                    item["agent_b"]["family"] for item in done
                }) >= 2
            ),
        }

    rules_specific = {}
    for rules in config["rulesets"]:
        games = [item for item in complete if item["rules"] == rules]
        placements = sum(item["counters"]["placements"] for item in games)
        if rules == "classic":
            rules_specific[rules] = {
                "late_cap_rate": sum(item["counters"]["late_covers"] for item in games) / max(1, placements),
                "median_length_over_points": statistics.median(
                    item["actions"] / (6 * item["board_size"] ** 2)
                    for item in games
                ) if games else None,
            }
        elif rules == "rosette":
            rules_specific[rules] = {
                "entombment_competitive_continuations": None,
                "status": "requires high-budget position analysis",
            }
        elif rules == "breath-run":
            rules_specific[rules] = {
                "rescue_extensions": sum(item["counters"]["extensions"] for item in games),
                "lead_changes": sum(item["counters"]["lead_changes"] for item in games),
            }
        elif rules == "gjerde":
            rules_specific[rules] = {
                "mean_scored_area_fraction": statistics.fmean(
                    item["scored_area"] / item["scoreable_area"] for item in games
                ) if games else None,
            }
        elif rules == "gjerde-go":
            rules_specific[rules] = {
                "wipe_rate": _rate([item["wipe"] for item in games]),
            }

    depth_ladder = _depth_ladder(records)
    evidence_status = _ruleset_evidence_status(
        strata, depth_ladder, config
    )
    return {
        "format": FORMAT,
        "version": VERSION,
        "recipe": RECIPE,
        "status": status,
        "config_hash": stable_hash(config),
        "provenance": provenance,
        "accounting": {
            "attempted": len(records),
            "complete": len(complete),
            "illegal": sum(item["status"] == "illegal" for item in records),
            "crash": sum(item["status"] == "crash" for item in records),
            "watchdog_incomplete": sum(
                item["error"] == "watchdog_incomplete" for item in records
            ),
            "pending": len(build_schedule(config)) - len(records),
            "cancelled": status == "cancelled",
        },
        "strata": strata,
        "depth_ladder": depth_ladder,
        "ruleset_evidence_status": evidence_status,
        "rules_specific": rules_specific,
        "standing_evidence_rules": {
            "no_claim_under_100_pairs": True,
            "two_agent_families_required": True,
            "adjacent_budget_stability_required": True,
            "rollout_policy_disagreement_is_provisional": True,
        },
        "promotion_blocked": not evidence_status or not all(
            item["headline_claim_ready"]
            for item in evidence_status.values()
        ),
        "failure_task_ids": [item["task_id"] for item in failures],
    }


def _checkpoint_payload(state):
    payload = dict(state)
    payload.pop("checkpoint_hash", None)
    payload["checkpoint_hash"] = stable_hash(payload)
    return payload


def _write_artifacts(output_dir, state):
    output_dir = Path(output_dir)
    payload = _checkpoint_payload(state)
    write_json_atomic(output_dir / "state.json", payload)
    write_jsonl_atomic(output_dir / "games.jsonl", state["records"])
    summary = summarize(
        state["records"], state["config"], state["provenance"], state["status"]
    )
    write_json_atomic(output_dir / "summary.json", summary)


def _load_state(path):
    payload = json.loads(Path(path).read_text())
    expected = payload.pop("checkpoint_hash", None)
    if not isinstance(expected, str) or stable_hash(payload) != expected:
        raise ValueError("evaluation checkpoint hash mismatch")
    payload["checkpoint_hash"] = expected
    return payload


def _ordered_results(tasks, evaluator, workers):
    if workers == 1:
        return [evaluator(task) for task in tasks]
    executor_type = ProcessPoolExecutor if evaluator is evaluate_task else ThreadPoolExecutor
    with executor_type(max_workers=workers) as executor:
        return list(executor.map(evaluator, tasks))


def run_evaluation(
    output_dir,
    *,
    config,
    workers=1,
    checkpoint_interval=1,
    resume=False,
    cancel_file=None,
    max_games=None,
    evaluator=evaluate_task,
):
    if workers < 1 or checkpoint_interval < 1:
        raise ValueError("workers and checkpoint interval must be positive")
    output_dir = Path(output_dir)
    state_path = output_dir / "state.json"
    provenance = {
        "source_commit": source_commit(),
        "code_hash": code_hash(),
        "ruleset_registry_hash": stable_hash(rulesets_public()),
        "native_evaluator_hash": NATIVE_EVALUATOR_HASH,
        "mcts_agent_hash": MCTS_AGENT_HASH,
    }
    tasks = build_schedule(config)
    if resume:
        if not state_path.exists():
            raise ValueError("no evaluation checkpoint to resume")
        state = _load_state(state_path)
        state.pop("checkpoint_hash", None)
        if state["config"] != config:
            raise ValueError("resume configuration does not match checkpoint")
        if state["provenance"] != provenance:
            raise ValueError("source or agent code changed since checkpoint")
    else:
        if state_path.exists():
            raise ValueError("output already contains a checkpoint; use --resume")
        output_dir.mkdir(parents=True, exist_ok=True)
        state = {
            "format": FORMAT,
            "version": VERSION,
            "recipe": RECIPE,
            "config": config,
            "provenance": provenance,
            "status": "running",
            "next_task": 0,
            "records": [],
        }
        _write_artifacts(output_dir, state)

    cancel_path = Path(cancel_file) if cancel_file else None
    if cancel_path and cancel_path.exists():
        state["status"] = "cancelled"
        _write_artifacts(output_dir, state)
        return state

    state["status"] = "running"
    start = state["next_task"]
    stop = len(tasks)
    if max_games is not None:
        stop = min(stop, start + max_games)
    while state["next_task"] < stop:
        if cancel_path and cancel_path.exists():
            state["status"] = "cancelled"
            break
        batch_end = min(stop, state["next_task"] + checkpoint_interval)
        batch = tasks[state["next_task"]:batch_end]
        results = _ordered_results(batch, evaluator, workers)
        for task, result in zip(batch, results):
            if result.get("task_id") != task["task_id"]:
                raise ValueError("evaluator returned an out-of-order task")
            state["records"].append(result)
            state["next_task"] += 1
        _write_artifacts(output_dir, state)
    if state["next_task"] == len(tasks):
        state["status"] = "complete"
    elif state["status"] != "cancelled":
        state["status"] = "paused"
    _write_artifacts(output_dir, state)
    return state


def _csv(value, cast=str):
    return tuple(cast(item.strip()) for item in value.split(",") if item.strip())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--rulesets",
        default="classic,rosette,breath,breath-run,gjerde,gjerde-go",
    )
    parser.add_argument(
        "--agents", default="native-standard,mcts-uniform,mcts-light"
    )
    parser.add_argument("--budgets", default="250")
    parser.add_argument("--pairs", type=int, default=1)
    parser.add_argument("--board-sizes", default="4")
    parser.add_argument("--seed", type=int, default=20260715)
    parser.add_argument("--workers", type=int, default=max(1, os.cpu_count() or 1))
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--checkpoint-interval", type=int, default=1)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--cancel-file", type=Path)
    parser.add_argument("--telemetry", action="store_true")
    parser.add_argument("--include-mirrors", action="store_true")
    parser.add_argument(
        "--watchdog-multiplier", type=int, default=DEFAULT_WATCHDOG_MULTIPLIER
    )
    parser.add_argument("--max-games", type=int, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.pairs < 1 or args.watchdog_multiplier < 1:
        parser.error("pairs and watchdog multiplier must be positive")
    budgets = _csv(args.budgets, int)
    if not budgets or any(budget < 1 for budget in budgets):
        parser.error("budgets must be positive")
    try:
        agents = parse_agents(_csv(args.agents), budgets)
        config = {
            "rulesets": list(_csv(args.rulesets)),
            "board_sizes": list(_csv(args.board_sizes, int)),
            "agents": [asdict(agent) for agent in agents],
            "pairs": args.pairs,
            "seed": args.seed,
            "telemetry": args.telemetry,
            "include_mirrors": args.include_mirrors,
            "watchdog_multiplier": args.watchdog_multiplier,
        }
        run_evaluation(
            args.output_dir,
            config=config,
            workers=args.workers,
            checkpoint_interval=args.checkpoint_interval,
            resume=args.resume,
            cancel_file=args.cancel_file,
            max_games=args.max_games,
        )
    except ValueError as exc:
        parser.error(str(exc))
    print(args.output_dir / "summary.json")


if __name__ == "__main__":
    main()
