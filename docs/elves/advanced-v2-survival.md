# READ THIS FILE FIRST AFTER ANY COMPACTION OR RESTART

## Mission

Implement `docs/plans/advanced-learning-v2.md`: correct search/end semantics,
ship Learning V2 persistence/training, reproduce the evidence, and complete
browser/final review without touching `engine/cairn.py`.

## Run Control

- **Run mode:** finite
- **Stop policy:** all four batches complete or genuine blocker
- **User intent:** "PLEASE IMPLEMENT THIS PLAN"
- **Checkpoint due by:** 2026-07-13 04:26 CDT
- **Checkpoint semantics:** hard stop boundary
- **May continue after checkpoint:** no
- **Actual stop conditions:** all planned work verified, or a hard blocker with no safe workaround
- **Workspace ownership:** owned branch `feat/advanced-learning-v2` in main checkout
- **Branch tip at start:** `6fb779c8a1c610b5e82b0b6238f58b0fc343b1e2`
- **Merge policy:** user-merges; no remote exists
- **Final-response policy:** allowed only after Stop Gate becomes yes
- **Batch completion rule:** update log and survival guide, commit, re-read, continue
- **Re-read rule:** re-read this file after every batch commit

## Session Budget

- **Started:** 2026-07-12 20:26 CDT
- **User returns:** approximately 2026-07-13 04:26 CDT
- **Time budget:** approximately 8 hours
- **Batches remaining:** 4 of 4

## Stop Gate

- **Planned batches remaining:** 4
- **Stop allowed right now:** no
- **Why:** implementation has not started
- **Next required action:** start Batch 1 search and ending correctness

## Non-Negotiables

- Never modify `engine/cairn.py`.
- No live move/turn cutoff.
- Preserve legacy saves and version-1 user models.
- No stronger claim without the full paired gate.
- Preserve Claude's `research/` evidence; remove only the explicitly authorized snapshot.
- Never use destructive git commands or merge.

## Current Phase

**Status:** In progress

**Active batch:** Batch 1: Search and ending correctness

**What was just finished:** Baseline preflight passed 60 tests and JavaScript syntax.

**Single next action:** implement pass/takeover reply scoring and per-seat ending acceptance.

## Active Compute

No active paid or long-running compute.

## Next Exact Batch

**Batch:** 1: Search and ending correctness

**Scope:** pass replies, opening takeover reply, persisted seat acceptances.

**Acceptance criteria:** focused/full tests green; old match saves load; both watch seats decide.

**Risk:** changing shared opponent search and saved match orchestration can alter every computer mode.

**Rollback tag:** `elves/pre-batch-1`
