# READ THIS FILE FIRST AFTER ANY COMPACTION OR RESTART

## Mission

Implement `docs/plans/evaluator-profiles-v3.md` completely on an owned feature
branch. Preserve exact Balanced decisions, all compatibility surfaces, the
Personal model, and `engine/cairn.py`; publish only profiles that pass the
predeclared evidence gates.

## Run Control

- **Run mode:** finite
- **Stop policy:** blocker-only until all six batches and final readiness review complete
- **User intent:** "PLEASE IMPLEMENT THIS PLAN"
- **Checkpoint due by:** none
- **Checkpoint semantics:** none
- **May continue after checkpoint:** yes
- **Actual stop conditions:** all batches complete and verified, explicit user stop, or a genuine blocker with no safe workaround
- **Workspace ownership:** `feat/evaluator-profiles-v3` in `/Users/armand/Development/cairn`; no other active writer
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
- **Average batch time so far:** 9 minutes
- **Batches remaining:** 5 of 6

## Stop Gate

- **Planned batches remaining:** 5
- **Stop allowed right now:** no
- **Why:** compatibility, browser, research, evidence, and final gates remain
- **Next required action:** start Batch 2 profile catalog and seat/API migration

## Non-Negotiables

- Never modify `engine/cairn.py` or live game rules.
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

**Status:** In progress

**Active batch:** Batch 2 — Profile model, API, saves, and Personal migration

**What was just finished:** Batch 1 exact parity, V3 telemetry, all-board tests, and latency recovery

**Single next action:** add the versioned catalog and normalize seat difficulty/profile data

## Active Compute

No active paid or long-running compute. Full research jobs must be recorded here
when started and stopped when complete or canceled.

## Next Exact Batch

**Batch:** 2 — Profile model, API, saves, and Personal migration

**Scope:**

- Add a versioned packaged catalog and immutable profile lookup.
- Add profile to computer seats, APIs, state, saves, and takeover identity.
- Normalize legacy Advanced to Standard + Personal without changing the model.

**Acceptance criteria:**

- [ ] Catalog validation and unknown/unavailable rejection pass.
- [ ] Legacy Advanced and missing-profile saves/requests migrate correctly.
- [ ] Zero-weight Personal equals Balanced and complete-seat takeover is preserved.

**Risk:** normalization must preserve every old request/save while keeping human seats profile-free.

**Rollback tag:** `elves/v3-pre-batch-2`

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
unknown commit and `engine/cairn.py` still has no diff before resuming.

# READ THIS FILE FIRST AFTER ANY COMPACTION OR RESTART
