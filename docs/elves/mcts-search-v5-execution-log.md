# MCTS Search V5 — Execution Log

## Metadata

- Started: 2026-07-17 13:06 America/Chicago.
- Mode/budget: finite, approximately twelve hours.
- Branch/worktree: `codex/mcts-search-v5` at
  `/private/tmp/varde-mcts-search-v5`.
- Stacked base/collision tripwire:
  `808c31720730fcf23bbc02c4549bd7151bdab3ec`.
- PR base: `codex/mcts-search-v4`; merge policy: user merges.
- Baseline: 299 tests passed in 108.988 s, zero skips.

## Batch map

0. Stage stacked run and draft PR.
1. Freeze development/holdout corpora and independent oracle.
2. Correct root-only proof guidance.
3. Add obligation-reserved unpruning.
4. Add true-terminal settling V2.
5. Run the frozen eight-arm development factorial.
6. Conditional holdout, deep tier, paired diagnostic, and handoff.

## Batch 0 — Stage the stacked run

Status: completed at `aa88748`; launch-readiness update follows in the same
batch.

### Contract

**Behavior**

- Record the exact approved V5 scope, recovery state, evidence gates, time
  budget, and collision guard.
- Open a draft PR stacked on PR #21 before candidate code or corpus generation.

**Build on**

- Mirror the durable structure and validation surfaces of
  `docs/plans/mcts-search-v4.md`.
- Preserve the V4 report and candidate investigation as immutable inputs.

**Acceptance criteria**

- Exact base `808c317`, draft/open/green PR #21, clean dedicated worktree.
- Full baseline, compilation, JavaScript syntax, Ruff policy, and diff checks
  recorded.
- Staging diff contains only plan and Elves session documents.
- Draft PR targets `codex/mcts-search-v4`; no search process exists.

**Blast radius**

- Documentation and session metadata only. No shared code or product behavior.

### Pre-implementation survey

- PR #21 is open, draft, mergeable, CI-green, and exactly at `808c317`.
- No local/remote V5 branch, worktree, or PR existed before staging.
- `.gitignore` already covers `.aragora/`, Playwright, audit, Python cache, and
  other ephemeral paths; no ignore edit is needed.
- The shared checkout remains untouched; V5 owns a dedicated worktree.
- AC power is attached and `caffeinate` is active.
- The bounded goal-cycle recommended a plan-only first unit. Its stale
  four-arm/no-settling scope was rejected because the approved user plan binds
  the eight-arm factorial including Settling V2.

### Timing

- Implement: staging documents complete.
- Validate: 299 tests pass in 108.988 s; Python compilation, JavaScript syntax,
  JSON, and diff checks pass. Repository-wide Ruff reports the same ten
  pre-existing findings inherited from V4; changed-file Ruff is binding.
- Review: survival-guide validator initially found five missing operational
  headings; the guide was expanded to the exact resumability contract and then
  passed validation. The staging diff contained only five plan/session files.
- Push/PR: `aa88748` pushed; draft PR #22 opened against
  `codex/mcts-search-v4`. Exact head/base, mergeability, and draft state were
  verified. Both CI jobs started; there were no comments or reviews.

## Batch 1 — Freeze corpora and independent oracle

Status: in progress.

### Contract

**Behavior**

- Freeze new, hash-disjoint 24-position development and 24-position holdout
  corpora covering six tactical families, both board strata, narrow/wide roots,
  actor-changing and actor-preserving rescues, equivalent proofs, conflicting
  obligations, fence semantics, and exact decoys.
- Add a generic exhaustive oracle driven only by explicit goal predicates and
  quantifier schedules, sharing legal transitions but no solver obligation
  logic.

**Acceptance criteria**

- Exact deterministic regeneration, hashes, stratum validation, and V4
  artifact preservation.
- Oracle quantifier, closure, abstention, superko, ceiling, non-mutation, and
  hand-audited trace fixtures pass.

**Blast radius**

- New V5 research modules, manifests, fixtures, and tests only.
