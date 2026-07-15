# READ THIS FILE FIRST AFTER ANY COMPACTION OR RESTART

## Mission

Build an outcome-blind feasibility gate and evidence-method redesign across all
six frozen Varde candidates. Do not launch calibration or inspect outcomes.

## Run Control

- Mode: finite
- Branch/worktree: `codex/evidence-method-feasibility` at
  `/tmp/varde-evidence-method-feasibility`
- Base: `565c08b0b0dae0ba3b9ec5bbdbd3ab8927cced6b`
- PR policy: open early; user reviews and merges; never self-merge
- Goal-cycle input:
  `/Users/armand/Development/varde/.aragora/goal_cycles/20260715T221513Z`

## Non-Negotiables

- No changes to `engine/varde.py`, `engine/mcts.py`, rules or scoring.
- No calibration, result inspection, or old/new evidence pooling.
- Timing artifacts omit decisions, scores, winners and margins.
- Total measurement wall time stays below 30 minutes.
- No destructive Git operations, force push or test weakening.

## Current Phase

Status: complete

Active batch: none — finite run complete

Just completed: review-ready redesign head `8fc2236`; both exact-head CI runs
passed and the measured handoff is published on PR #15.

Single next action: none. Await user review; do not launch calibration from this
branch.

## Active Compute

None.

## Stop Gate

- Planned batches remaining: 0
- Stop allowed right now: yes
- Next required action: none; await user review

## Recovery Order

Read this guide, `.elves-session.json`, the run plan, execution log,
`docs/plans/ruleset-promise-evaluation.md`, and the frozen manifest on PR #13.
Reconcile any timing process before relaunching.
