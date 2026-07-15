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
- **Batches remaining:** 2 of 6 product batches

## Stop Gate

- **Planned batches remaining:** 2
- **Stop allowed right now:** no
- **Why:** the human-study workflow and final evidence/handoff remain
- **Next required action:** complete Batch 5 human-study instruments and browser export

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

**Active batch:** Batch 5 — human-study instruments and product workflow

**What was just finished:** Batch 4 added the paired, byte-stable falsification CLI; 193 tests and real native/MCTS process-worker smokes pass.

**Single next action:** specify the local playtest record schema and browser action-capture seam.

## Active Compute

No active paid or long-running compute.

## Next Exact Batch

**Batch:** 5 — Human-study instruments and product workflow

**Scope:**
- Add neutral rules briefs, resolution/call-your-shot puzzles, crossover
  scheduling, game and post-game forms, and the one-week retention instrument.
- Capture local human actions and time-to-action in the browser, with explicit
  JSON export and no network submission or personal identifiers.
- Validate schema, schedule balance, browser export, save/load, and console state.

**Acceptance criteria:**
- [ ] Human records are versioned, locally exportable, and contain no PII fields.
- [ ] Crossover schedules counterbalance ruleset order, opponent, and color.
- [ ] Briefs and puzzles are neutral and do not teach designer-supplied motifs.
- [ ] Browser screenshots, semantic state, save/load, and console checks pass.

**Risk:** instrumentation can prime players or turn designer vocabulary into false emergence evidence; prompts must stay neutral and records must separate prediction, understanding, and aesthetics.

**Rollback tag:** `elves/ruleset-evaluation-pre-batch-5`

## Recovery Order

Read this guide, `.elves-session.json`, ruleset-evaluation learnings, the plan,
the execution log, `progress.md`, and the first incomplete batch. Confirm HEAD
has not moved outside this run and reconcile any active compute before acting.
