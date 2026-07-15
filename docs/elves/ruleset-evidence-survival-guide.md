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

Status: in progress — feasibility remediation

Active batch: Batch 2 — calibration stage A at 250 simulations

Just completed: PR #14 proved exact v1/v2 search equivalence but improved
uniform@250 by only 0.58%; PR #15 measured all six candidates outcome-blind and
predeclared a native-first, shallow 12/24 diagnostic redesign.

Single next action: await user review of PRs #14 and #15. After the selected
MCTS hash is settled, regenerate its feasibility artifact and freeze a new
12/24 diagnostic manifest. Do not resume the frozen 250-budget job.

## Active Compute

None. Managed session `86550` was interrupted cleanly; no evaluation process is
running. The external zero-record checkpoint is preserved. No score, winner,
margin or partial outcome was generated or inspected.

## Stop Gate

- Planned batches remaining: 4
- Stop allowed right now: yes — source/agent selection requires user review
- Next required action: after review, regenerate the gate and create a new
  diagnostic manifest; never pool with the frozen v1 round

## Validation Gates

- `pytest -q -o addopts=''`
- `python3 -m py_compile engine/*.py research/harness/*.py`
- `node --check web/game.js`
- Harness-specific deterministic/checkpoint tests
- Exact manifest/hash validation before each launch
- PR comments and checks after every push

## Recovery Order

Read this guide, `docs/elves/sessions/ruleset-evidence-session.json`,
`docs/elves/ruleset-evaluation-learnings.md`,
`docs/plans/ruleset-computer-evaluation-run.md`, and
`docs/elves/ruleset-evidence-execution-log.md`. Reconcile active processes and
output checkpoints before launching or resuming any compute.
