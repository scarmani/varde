# READ THIS FILE FIRST AFTER ANY COMPACTION OR RESTART

## Mission

Deliver one behavior-preserving MCTS v2 performance pass that clears or
honestly measures the calibration throughput blocker. Never change game rules,
use heuristic leaf values, truncate rollouts, or relabel v1 evidence as v2.

## Run Control

- Mode: finite
- Branch/worktree: `codex/mcts-fast-clone-v2` at `/tmp/varde-mcts-fast-clone-v2`
- Base/collision tripwire: `565c08b0b0dae0ba3b9ec5bbdbd3ab8927cced6b`
- PR policy: open early; user reviews and merges; never merge this PR
- Time allocation: implement 30%, validate 40%, review/profile 30%
- Stop after: one focused optimization pass, full equivalence/timing report, and
  review-ready PR; if gates fail, report remaining gap instead of redesigning
  the rollout policy.

## Non-Negotiables

- Terminal-score-only backup and real legal actions.
- No rollout or game cutoff added to MCTS.
- No rules, scoring, save-format or browser changes.
- Golden fixtures generated from v1 before hot-path edits.
- Exact seeded action/tree-stat equivalence across fixtures.
- New version/hash; no evidence pooling.
- No calibration launch in this performance run.
- No destructive Git operation, force push, test weakening or automatic merge.

## Current Phase

Status: in progress

Active batch: Batch 2 — hot-path implementation

Just completed: all 96 v1 fixtures reproduced exactly under v2 and the full
204-test suite, lint, compilation and diff checks passed.

Single next action: commit the equivalence-proven implementation, then measure
the fresh-position and complete-game throughput gates without reading outcomes.

## Active Compute

None.

## Stop Gate

- Planned batches remaining: 3
- Stop allowed right now: no
- Next required action: complete one behavior-preserving hot-path pass

## Validation Gates

- `pytest -q -o addopts=''`
- Exact golden fixture reproduction
- `ruff check` on changed Python
- `python3 -m py_compile engine/*.py research/harness/*.py`
- Focused timing probes with outcomes uninspected
- PR comments and exact-head CI after every push

## Recovery Order

Read this guide, `.elves-session.json`,
`docs/elves/ruleset-evaluation-learnings.md`,
`docs/plans/mcts-v2-performance.md`, and
`docs/elves/mcts-v2-execution-log.md`. Reconcile any profiling/timing process
before editing or relaunching.
