# MCTS Search V4 — Execution Log

## Metadata

- Started: 2026-07-17 America/Chicago
- Branch/worktree: `codex/mcts-search-v4` at
  `/private/tmp/varde-mcts-search-v4`
- Stacked base: `315443366ddeb499d294f47221e89c2c1dbca4d7`
- Merge policy: user merges
- Baseline: 268 tests passed in 47.362 s

## Batch 0 — Staged run

Status: complete at `dddbaf4`; draft PR #21 opened.

### Contract

**Behavior:** record the complete V4 experiment, recovery state, exact stacked
base, and preflight; open a draft review surface before search changes.

**Acceptance:** exact PR #20 head; no collision; 268 tests; compile and
JavaScript syntax pass; changed-file Ruff policy records ten pre-existing
repository-wide findings; documentation-only setup diff; draft/unmerged PR.

**Blast radius:** plan and operational run-control documents only.

### Launch evidence

- PR #20 is open, draft, mergeable, CI-green, and exactly at `3154433`.
- No V4 branch, worktree, or open PR existed before launch.
- The bounded Fable cycle reinforced sealing the independent holdout before
  search changes and treating V3 only as development evidence. Its one-cycle
  stop recommendation does not override the user's explicit full-run launch.
- Full baseline: 268 tests passed in 47.362 s.
- Python compilation, JavaScript syntax, and diff checks pass.
- Repository-wide Ruff reports ten pre-existing errors; this run requires every
  changed Python file to pass Ruff and will not broaden into unrelated cleanup.
- Documentation-only head `dddbaf4` was pushed and draft PR #21 opened against
  `codex/mcts-search-v3`; the PR is open, mergeable, unreviewed, and unmerged.

## Batch 1 — Independent holdout

Status: in progress.

## Batch 2 — Certified tactical subsearch

Status: pending.

## Batch 3 — Progressive unpruning

Status: pending.

## Batch 4 — True-terminal settling

Status: pending.

## Batch 5 — Admission, composition, and holdout

Status: pending.

## Batch 6 — Conditional deep tier and handoff

Status: pending.
