#!/usr/bin/env python3
"""Generate or verify deterministic MCTS v1 behavior fixtures."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import random
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
ENGINE_ROOT = REPO_ROOT / "engine"
if str(ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(ENGINE_ROOT))

import mcts  # noqa: E402
from actions import RulesState, apply_action, legal_actions  # noqa: E402
from varde import Game, get_ruleset_spec  # noqa: E402


FORMAT = "varde-mcts-golden"
VERSION = 1
RULESETS = ("classic", "rosette", "breath", "breath-run", "gjerde", "gjerde-go")
SEEDS = (20260715, 20260716)
BUDGETS = (8, 32)
POLICIES = ("uniform", "epsilon-greedy")
POSITION_ACTIONS = 12


def canonical_bytes(payload):
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()


def stable_hash(payload):
    return hashlib.sha256(canonical_bytes(payload)).hexdigest()


def source_commit():
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, check=True,
        capture_output=True, text=True,
    ).stdout.strip()


def _midgame_state(rules):
    state = RulesState.from_game(Game(4, rules=rules))
    rng = random.Random(int.from_bytes(
        hashlib.sha256(f"midgame|{rules}|20260714".encode()).digest()[:8],
        "big",
    ))
    actions_applied = []
    for _index in range(POSITION_ACTIONS):
        actions = [
            action for action in legal_actions(state)
            if action.kind not in ("pass", "accept", "resume")
        ]
        if not actions:
            raise ValueError(f"no non-ending midgame action for {rules}")
        action = actions[rng.randrange(len(actions))]
        actions_applied.append(action.to_dict())
        apply_action(state, action, copy=False, validate=False)
    if state.terminal or state.game.finished:
        raise ValueError(f"midgame construction ended {rules}")
    return state, actions_applied


def _capture_decision(state, simulations, seed, policy):
    original_node = mcts._Node
    roots = []

    class CapturingNode(original_node):
        def __init__(self, node_state, parent=None, action=None):
            super().__init__(node_state, parent=parent, action=action)
            if parent is None:
                roots.append(self)

    mcts._Node = CapturingNode
    try:
        decision = mcts.choose_mcts_state_action(
            state,
            state.actor_color,
            simulations=simulations,
            seed=seed,
            rollout_policy=policy,
        )
    finally:
        mcts._Node = original_node
    if len(roots) != 1:
        raise AssertionError("golden capture did not observe exactly one root")
    root = roots[0]
    children = sorted(root.children, key=lambda item: item.action.sort_key())
    return {
        "decision": decision.to_dict(),
        "root": {
            "visits": root.visits,
            "value_sum": root.value_sum,
            "children": [
                {
                    **child.action.to_dict(),
                    "visits": child.visits,
                    "value_sum": child.value_sum,
                }
                for child in children
            ],
        },
    }


def generate():
    fixtures = []
    for rules in RULESETS:
        opening = RulesState.from_game(Game(4, rules=rules))
        midgame, position_actions = _midgame_state(rules)
        for position_name, state, setup in (
            ("opening", opening, []),
            ("midgame", midgame, position_actions),
        ):
            state_key_hash = stable_hash(repr(state.key()))
            for policy in POLICIES:
                for budget in BUDGETS:
                    for seed in SEEDS:
                        fixtures.append({
                            "rules": rules,
                            "rules_revision": get_ruleset_spec(rules).evaluation_id,
                            "board_size": 4,
                            "position": position_name,
                            "setup_actions": setup,
                            "state_key_hash": state_key_hash,
                            "policy": policy,
                            "simulations": budget,
                            "seed": seed,
                            **_capture_decision(state, budget, seed, policy),
                        })
    payload = {
        "format": FORMAT,
        "version": VERSION,
        "source_commit": source_commit(),
        "mcts_agent_hash": mcts.MCTS_AGENT_HASH,
        "matrix": {
            "rulesets": list(RULESETS),
            "seeds": list(SEEDS),
            "budgets": list(BUDGETS),
            "policies": list(POLICIES),
            "positions": ["opening", "midgame"],
            "fixture_count": len(fixtures),
        },
        "fixtures": fixtures,
    }
    payload["fixture_hash"] = stable_hash(payload)
    return payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = generate()
    rendered = json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.check:
        if not args.output.exists() or args.output.read_text() != rendered:
            raise SystemExit("MCTS golden fixtures differ")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered)
    print(args.output)


if __name__ == "__main__":
    main()
