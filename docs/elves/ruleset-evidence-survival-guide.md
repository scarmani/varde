# READ THIS FILE FIRST AFTER ANY COMPACTION OR RESTART

## Mission

Execute the approved computer-only Varde ruleset evaluation from frozen source
through calibration, survivor health/depth screens, adversarial search where
feasible, and honest evidence publication. Never turn computer play into a
claim of human emergence or beauty.

## Run Control

- Run mode: finite
- Stop policy: all feasible computer-only gates complete, or genuine blocker
- User authorization: merge reviewed PR #12, then execute all recommended
  computer-resource steps in evidence-led order
- Branch: `codex/ruleset-evidence-run`
- Collision tripwire/base: `565c08b0b0dae0ba3b9ec5bbdbd3ab8927cced6b`
- PR policy: open early; user reviews and merges the evidence PR
- Merge authorization: applied to reviewed PR #12 only; never merge this run's PR
- Time allocation: implement 20%, validate 40%, review/evidence audit 40%
- Runaway threshold: five edits to one file without meaningful progress

## Non-Negotiables

- Freeze every experimental configuration before inspecting its outcomes.
- No rules or evaluator changes inside a measurement round.
- No live-game watchdog or action ceiling.
- No deletion, weakening or skipping of tests.
- No balance/depth claim from fewer than 100 games or one agent family.
- No emergence/elegance/beauty claim from computer evidence.
- Preserve all negative, illegal, crash, watchdog and incomplete accounting.
- Raw runs live outside the repository; only compact manifests/summaries enter Git.
- No force push, destructive Git operation or automatic PR merge.

## Current Phase

Status: in progress

Active batch: Batch 2 — calibration stage A at 250 simulations

Just completed: manifest commit `0612369` passed exact-head CI; detached source
and all provenance hashes match it.

Single next action: monitor A-uniform-250 through its first eight-game
checkpoint and then to completion without inspecting partial outcomes.

## Active Compute

`A-uniform-250` launched 2026-07-15T15:41:25-05:00 from detached worktree
`/tmp/varde-calibration-source-20260715` at `0612369`. Managed session `86550`,
parent PID `48847`, eight active workers. Initial checkpoint is running with
zero records; provenance matches the manifest. No partial outcome is inspected.

## Stop Gate

- Planned batches remaining: 4
- Stop allowed right now: no
- Next required action: finish both Stage A policy jobs and audit accounting

## Validation Gates

- `pytest -q -o addopts=''`
- `python3 -m py_compile engine/*.py research/harness/*.py`
- `node --check web/game.js`
- Harness-specific deterministic/checkpoint tests
- Exact manifest/hash validation before each launch
- PR comments and checks after every push

## Recovery Order

Read this guide, `.elves-session.json`,
`docs/elves/ruleset-evaluation-learnings.md`,
`docs/plans/ruleset-computer-evaluation-run.md`, and
`docs/elves/ruleset-evidence-execution-log.md`. Reconcile active processes and
output checkpoints before launching or resuming any compute.
