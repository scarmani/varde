# READ THIS FILE FIRST AFTER ANY COMPACTION OR RESTART

## Mission

Implement the approved Varde Ruleset Promise Evaluation Program on an owned
branch, beginning with the verified Gjerde scoring defect and ending with a
reproducible computational/human evaluation surface. Never substitute bot
probes for evidence of beauty or human strategic depth.

## Run Control

- **Run mode:** finite
- **Stop policy:** complete-and-verified or genuine blocker
- **User intent:** "PLEASE IMPLEMENT THIS PLAN"
- **Checkpoint due by:** none
- **Checkpoint semantics:** none
- **May continue after checkpoint:** yes
- **Actual stop conditions:** all six batches complete and review-ready, an explicit user stop, or a genuine blocker with no safe workaround
- **Workspace ownership:** owned branch `feat/ruleset-promise-evaluation` in the main Varde checkout
- **Branch tip at start:** `21b2efa40a2decc58ddff86f2df20ea84a709e9d`
- **Merge policy:** user-merges; never merge this PR
- **Final-response policy:** disallowed until the Stop Gate permits it
- **Batch completion rule:** update log and guide, commit, push, poll PR, re-read this guide, continue
- **Time allocation:** implement 34%, validate 33%, review 33%
- **Runaway threshold:** five edits to the same file without meaningful progress triggers a redesign pause

## Session Budget

- **Started:** 2026-07-15 13:20 CDT
- **User returns:** assume approximately 8 hours
- **Checkpoint expectation:** a reviewable PR with honest local evidence and explicit deferred human gates
- **Time budget:** approximately 8 hours, finite scope rather than a hard deadline
- **Average batch time so far:** not yet measured
- **Batches remaining:** 0 of 6 product batches

## Stop Gate

- **Planned batches remaining:** 0
- **Stop allowed right now:** no
- **Why:** mandatory final readiness review, Elves report, and cleanup remain
- **Next required action:** finish remote CI/review, generate report, then remove operational artifacts

## Non-Negotiables

- Repair Gjerde scoring before generating or trusting new Gjerde evidence.
- No live-game move, time, or watchdog cutoff.
- Preserve version-1 saves and archived-ruleset load compatibility.
- Never expose a broken/archived ruleset for a new public game.
- Never overwrite the user's Personal model.
- Never claim balance, depth, elegance, or beauty from shallow or single-agent evidence.
- Never use destructive Git commands, rewrite remote history, or merge the PR.
- Never weaken, skip, or delete tests to clear a gate.

## Launch Readiness

- [x] Approved plan saved
- [x] Survival guide, learnings, execution log, and structured session initialized
- [x] Owned branch created from clean `origin/main`
- [x] Workspace ownership and collision tripwire confirmed
- [x] PR #12 opened after Batch 0 commit
- [x] Baseline gates pass: 156 tests, Python compile, JavaScript syntax
- [x] Run controls and non-negotiables recorded
- [x] Stop Gate initialized to no

## Current Phase

**Status:** In progress

**Active batch:** Final readiness review

**What was just finished:** Batch 6 published non-claim smoke evidence and the exact unrun-gates matrix; 201 tests and final browser checks pass.

**Single next action:** poll PR #12 checks and perform the mandatory clean-tip review.

## Active Compute

No active paid or long-running compute.

## Next Exact Batch

**Batch:** Final completion

**Scope:**
- Poll every PR check, comment, and review at the exact head.
- Re-read the full diff, plan, execution log, session state, and evidence matrix.
- Generate the Elves report, remove operational session artifacts, push, and
  poll the cleanup head before final handoff.

**Acceptance criteria:**
- [x] Compact evidence is generated from committed source and explicitly non-claim.
- [x] Every deferred overnight and human gate is visible, not implied complete.
- [x] Full local tests, syntax, whitespace, browser, and review pass.
- [ ] Exact-head PR checks pass and operational cleanup is pushed.

**Risk:** cleanup can hide a stale CI or review state; do it only after the report is regenerated and the exact head is green.

**Rollback tag:** `elves/ruleset-evaluation-pre-final-cleanup`

## Recovery Order

Read this guide, `.elves-session.json`, ruleset-evaluation learnings, the plan,
the execution log, `progress.md`, and the first incomplete batch. Confirm HEAD
has not moved outside this run and reconcile any active compute before acting.
