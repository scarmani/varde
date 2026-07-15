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
- **Batches remaining:** 6 of 6 product batches; setup complete

## Stop Gate

- **Planned batches remaining:** 6
- **Stop allowed right now:** no
- **Why:** the scoring repair and evaluation program are not implemented
- **Next required action:** complete Batch 1 scoring/registry/API/browser correctness

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

**Active batch:** Batch 1 — correctness, ruleset registry, and browser/API truth

**What was just finished:** Batch 0 is pushed and PR #12 is the active review surface.

**Single next action:** Repair Gjerde open-boundary scoring with failing edge-category tests.

## Active Compute

No active paid or long-running compute.

## Next Exact Batch

**Batch:** 1 — Correctness, ruleset registry, and browser/API truth

**Scope:**
- Fix Gjerde open-boundary scoring and add category-level edge tests.
- Centralize versioned ruleset metadata and derive compatibility tuples/limits.
- Add `/api/rulesets`, dynamic selector behavior, and archived/broken new-game rejection.
- Correct affected public documentation and invalidate old Gjerde conclusions.

**Acceptance criteria:**
- [ ] One outer Gjerde claim scores zero; complete fences score correctly in both resolutions.
- [ ] Current ruleset IDs and legacy saves remain compatible.
- [ ] Browser receives registry metadata and cannot start archived/broken rulesets.
- [ ] Full tests, syntax, API smoke, Playwright state/screenshots, and console review pass.

**Risk:** shared ruleset constants and scoring feed engine, server, AI, saves, research, and UI; regression proof must trace every consumer.

**Rollback tag:** `elves/ruleset-evaluation-pre-batch-1`

## Recovery Order

Read this guide, `.elves-session.json`, ruleset-evaluation learnings, the plan,
the execution log, `progress.md`, and the first incomplete batch. Confirm HEAD
has not moved outside this run and reconcile any active compute before acting.
