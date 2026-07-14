# READ THIS FILE FIRST AFTER ANY COMPACTION OR RESTART

## Mission

Implement `docs/plans/evaluator-profiles-v3.md` completely on an owned feature
branch. Preserve exact Balanced decisions, all compatibility surfaces, the
Personal model, and `engine/varde.py`; publish only profiles that pass the
predeclared evidence gates.

## Run Control

- **Run mode:** finite
- **Stop policy:** blocker-only until all six batches and final readiness review complete
- **User intent:** "PLEASE IMPLEMENT THIS PLAN"
- **Checkpoint due by:** none
- **Checkpoint semantics:** none
- **May continue after checkpoint:** yes
- **Actual stop conditions:** all batches complete and verified, explicit user stop, or a genuine blocker with no safe workaround
- **Workspace ownership:** `feat/evaluator-profiles-v3` in `/Users/armand/Development/varde`; no other active writer
- **Branch tip at start:** `1da66f7a40bd6c336d2a5fd5bc472ff2ddf040bc`
- **Merge policy:** user-merges; never merge this run
- **Final-response policy:** disallowed while planned work remains
- **Batch completion rule:** update run docs, commit, push, poll PR/checks, and re-read this guide before the next batch
- **Re-read rule:** immediately after every commit and push
- **Continuation rule:** if work remains and no hard stop exists, continue

## Session Budget

- **Started:** 2026-07-13 11:33 CDT
- **User returns:** unknown; assume offline
- **Time budget:** finite plan, no artificial research shortcut
- **Average batch time so far:** 10.5 minutes
- **Batches remaining:** 2 of 6

## Stop Gate

- **Planned batches remaining:** 2
- **Stop allowed right now:** no
- **Why:** evidence/curation and final gates remain
- **Next required action:** run the evaluator audit, ablations, archive search, and evidence-gated catalog freeze

## Non-Negotiables

- Never modify `engine/varde.py` or live game rules.
- Never add live-game cutoffs or optimize search depth as style.
- Never overwrite the Personal model or weaken legacy compatibility.
- Never weaken, skip, or delete tests to clear a gate.
- Never relax a profile evidence threshold or make an unearned strength claim.
- Never merge, force-push, rebase, reset hard, checkout-dot, or clean the tree.

## Launch Readiness

- [x] User plan saved and decomposed
- [x] Survival guide, learnings, execution log, and session JSON initialized
- [x] Owned branch and collision tripwire established
- [x] GitHub remote/auth verified; local main settled without force
- [x] Baseline validation green: 72 Python tests, JS syntax, Python compile
- [x] Run mode, stop gate, and non-negotiables recorded
- [x] Feature-branch PR #1 opened and recorded after setup commit

## Current Phase

**Status:** Complete — PR #1 awaits user review; do not merge automatically

**Active batch:** none

**What was just finished:** Batch 6 catalog freeze, final gates, benchmark, and
browser proof. Mason and Surveyor ship; Raider and Weaver are omitted with
recorded reasons (engagement did not reproduce held-out; strength floor failed).

**Single next action:** none. Any future Raider/Weaver work requires a new,
separately declared research cycle with redefined descriptors or optimizer.

## Active Compute

No active compute. All evidence jobs are complete.

- Committed summary: `research/results/v3-final-evidence-summary.json`
  (stage hashes, gate metrics, omission reasons, candidate and model hashes).
- Committed benchmark: `research/results/v3-final-benchmark.json`.
- Raw evidence (including the 197 MB archive `state.json`, sha256
  `c0cd56f1b73744ebe731f11dc64f50af2ebeffddbe85d9f28da4ff0b7c3b3c81`) is
  retained durably at `~/varde-v3-evidence/varde-v3-evidence-bb82da3/` with a
  transient copy at `/tmp/varde-v3-evidence-bb82da3/`.

The single permitted 2,048-mutation refinement has been consumed. Do not run
further MAP-Elites refinements under this plan.

## Next Exact Batch

None. The plan's six batches are complete. The remaining human step is user
review of PR #1; the task contract forbids automatic merge.

## Tool Configuration

```yaml
lint: python3 -m py_compile engine/*.py research/harness/*.py
typecheck: node --check web/game.js
build: none
test: CI=true python3 -m pytest engine -q
e2e: develop-web-game Playwright client against engine/server.py
review: GitHub PR comments plus direct cumulative review
notification: final task response
```

## Plan and Log Paths

- **Plan:** `docs/plans/evaluator-profiles-v3.md`
- **Learnings:** `docs/elves/v3-learnings.md`
- **Execution log:** `docs/elves/v3-execution-log.md`
- **Branch:** `feat/evaluator-profiles-v3`
- **PR number:** #1
- **Plan hash at session start:** `401dcf7a54e4bfaae42f7cf9a21b673b`

## Recovery Order

Read this guide, `.elves-session.json`, learnings, plan, execution log,
`progress.md`, then the first incomplete batch. Confirm HEAD has not moved to an
unknown commit and `engine/varde.py` still has no diff before resuming.

# READ THIS FILE FIRST AFTER ANY COMPACTION OR RESTART
