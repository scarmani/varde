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
- **Average batch time so far:** 57m
- **Batches remaining:** 1 of 4

## Stop Gate

- **Planned batches remaining:** 1
- **Stop allowed right now:** no
- **Why:** final cumulative review and cleanup remain
- **Next required action:** finish Batch 4 and satisfy the Stop Gate

## Non-Negotiables

- Never modify `engine/cairn.py`.
- No live move/turn cutoff.
- Preserve legacy saves and version-1 user models.
- No stronger claim without the full paired gate.
- Preserve Claude's `research/` evidence; remove only the explicitly authorized snapshot.
- Never use destructive git commands or merge.

## Current Phase

**Status:** In progress

**Active batch:** Batch 4: Browser, documentation, and final review

**What was just finished:** Batch 3 trained 200/200 games, ran all 100 paired seeds, recorded an honest failed strength gate, passed both latency budgets, and completed eight larger-board smoke games.

**Single next action:** complete final browser evidence, cumulative diff review, report, and cleanup.

## Active Compute

| Resource | Purpose | Current status | Last verified | Stop / repurpose trigger |
| --- | --- | --- | --- | --- |
No active long-running compute. The raw completed evidence remains in `/tmp/cairn-v2-final`.

## Next Exact Batch

**Batch:** 4: Browser, documentation, and final review

**Scope:** UI migration/status messaging, Playwright proof, full regression, cumulative review, and run cleanup.

**Acceptance criteria:** required browser interactions and screenshots, no console errors, all tests and integrity gates green, clean branch, Elves report generated.

**Risk:** direct API browser checks must be paired with rendered UI/state inspection; failed strength gate must not be worded as improvement.

**Rollback tag:** `elves/pre-batch-4`
