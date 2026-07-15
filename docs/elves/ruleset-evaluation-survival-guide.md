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
- **Batches remaining:** 4 of 6 product batches

## Stop Gate

- **Planned batches remaining:** 4
- **Stop allowed right now:** no
- **Why:** independent MCTS, falsification, and human-study surfaces remain
- **Next required action:** complete Batch 3 common action layer and neutral MCTS

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

**Active batch:** Batch 3 — deterministic ruleset-neutral MCTS

**What was just finished:** Batch 2 added hash-pinned native evaluators, tactical admission fixtures, exact Classic parity, and a green 177-test gate.

**Single next action:** Define one immutable action vocabulary over every Game special phase before implementing tree search.

## Active Compute

No active paid or long-running compute.

## Next Exact Batch

**Batch:** 3 — Deterministic ruleset-neutral MCTS

**Scope:**
- Add a common legal-action adapter for play, pass, swap, extension,
  finish-extension, resumption, and ending acceptance.
- Add seeded UCT using only terminal score, fixed simulation budgets, and
  uniform or light epsilon-greedy rollouts.
- Keep research watchdogs outside live agents.

**Acceptance criteria:**
- [ ] Action enumeration/application is deterministic, legal, and complete.
- [ ] MCTS is deterministic, legal, non-mutating, superko-aware, and save-compatible.
- [ ] Pass, takeover, extension, finish, resumption, and acceptance have fixtures.
- [ ] 250-simulation smoke covers every candidate and both rollout policies.

**Risk:** rollout length and special ending decisions can dominate runtime or silently introduce a research-only cutoff into live rules.

**Rollback tag:** `elves/ruleset-evaluation-pre-batch-3`

## Recovery Order

Read this guide, `.elves-session.json`, ruleset-evaluation learnings, the plan,
the execution log, `progress.md`, and the first incomplete batch. Confirm HEAD
has not moved outside this run and reconcile any active compute before acting.
