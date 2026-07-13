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
- **Average batch time so far:** 9.7 minutes
- **Batches remaining:** 3 of 6

## Stop Gate

- **Planned batches remaining:** 3
- **Stop allowed right now:** no
- **Why:** research harness, evidence/curation, and final gates remain
- **Next required action:** run the three-batch entropy check, then start deterministic MAP-Elites

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

**Active batch:** Entropy check after Batch 3, then Batch 4 — Deterministic MAP-Elites

**What was just finished:** Batch 3 dynamic profile UI, profile rationales, and Playwright verification

**Single next action:** audit cumulative patterns and begin the resumable archive harness

## Active Compute

No active paid or long-running compute. Full research jobs must be recorded here
when started and stopped when complete or canceled.

## Next Exact Batch

**Batch:** 4 — Deterministic MAP-Elites research harness

**Scope:**

- Implement explicit output/seed/workers/checkpoint/resume research CLI.
- Add four-axis calibration, archive replacement, mutation, and frozen hall of fame.
- Persist a deterministic evidence ledger with atomic checkpoints and rejection accounting.

**Acceptance criteria:**

- [ ] Candidate IDs fix seeds/opponents independent of scheduling.
- [ ] Resume and worker-count results are bit-for-bit equivalent.
- [ ] Binning, replacement, mutation, hall of fame, cancellation, and incomplete attempts pass.

**Risk:** parallel completion order and checkpoint boundaries must not alter floating reductions or archive state.

**Rollback tag:** `elves/v3-pre-batch-4`

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
