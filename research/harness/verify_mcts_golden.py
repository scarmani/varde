#!/usr/bin/env python3
"""Verify current MCTS behavior against a frozen golden fixture corpus."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
ENGINE_ROOT = REPO_ROOT / "engine"
HARNESS_ROOT = REPO_ROOT / "research" / "harness"
for import_root in (ENGINE_ROOT, HARNESS_ROOT):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

import mcts  # noqa: E402
from actions import RulesAction, RulesState, apply_action  # noqa: E402
from mcts_golden import _capture_decision, stable_hash  # noqa: E402
from varde import Game  # noqa: E402


def _action_from_dict(payload):
    point = payload.get("point")
    return RulesAction(payload["action"], tuple(point) if point is not None else None)


def _normalize_decision(payload):
    normalized = dict(payload)
    normalized.pop("agent_hash", None)
    return normalized


def _verify_fixture(index_and_fixture):
    index, fixture = index_and_fixture
    state = RulesState.from_game(
        Game(fixture["board_size"], rules=fixture["rules"])
    )
    for action_payload in fixture["setup_actions"]:
        apply_action(
            state,
            _action_from_dict(action_payload),
            copy=False,
            validate=True,
        )
    observed_key_hash = stable_hash(repr(state.key()))
    if observed_key_hash != fixture["state_key_hash"]:
        return index, "state-key hash differs"

    observed = _capture_decision(
        state,
        fixture["simulations"],
        fixture["seed"],
        fixture["policy"],
    )
    if _normalize_decision(observed["decision"]) != _normalize_decision(
        fixture["decision"]
    ):
        return index, "decision differs"
    if observed["root"] != fixture["root"]:
        return index, "root tree statistics differ"
    return index, None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture", type=Path)
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("--workers must be positive")

    payload = json.loads(args.fixture.read_text())
    if payload.get("format") != "varde-mcts-golden" or payload.get("version") != 1:
        raise SystemExit("unsupported golden fixture corpus")
    if payload.get("mcts_agent_hash") == mcts.MCTS_AGENT_HASH:
        raise SystemExit("current MCTS hash must differ from frozen v1 hash")

    jobs = list(enumerate(payload["fixtures"]))
    if args.workers == 1:
        results = [_verify_fixture(job) for job in jobs]
    else:
        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            results = list(executor.map(_verify_fixture, jobs))
    failures = [(index, error) for index, error in results if error is not None]
    if failures:
        for index, error in failures:
            fixture = payload["fixtures"][index]
            print(
                f"fixture {index} {fixture['rules']} {fixture['position']} "
                f"{fixture['policy']} budget={fixture['simulations']} "
                f"seed={fixture['seed']}: {error}",
                file=sys.stderr,
            )
        raise SystemExit(f"{len(failures)} of {len(jobs)} golden fixtures differ")
    print(
        f"verified {len(jobs)} fixtures: exact decisions and tree statistics; "
        "agent hash intentionally differs"
    )


if __name__ == "__main__":
    main()
