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

Status: complete at `9dcd4e1`.

### Evidence

- Frozen before candidate implementation: 24 strict positive certificates and
  12 exact abstention decoys across capture, defense, rescue, fence, takeover,
  and ending decisions.
- Each positive category contains two Toy and two Beginner positions; all roots
  contain 2–12 legal actions.
- Twenty of 24 positives replay from compact seeded legal transcripts. The four
  takeover decisions are explicitly constructed decision-isolation states.
- Certificates enumerate real legal transitions, record their bounded scope,
  state hash, action statuses, horizons, nodes, and claim limit.
- Corpus hashes are disjoint from all V3 fixture state hashes. The sealed
  manifest is `research/manifests/mcts-search-v4-holdout-20260717.json`.
- Full gate: 273 tests pass in 59.226 s; changed-file Ruff, compilation, and
  diff checks pass. No search behavior or forbidden product file changed.

## Batch 2 — Certified tactical subsearch

Status: complete at `48ee0b6`.

### Evidence

- Added a three-valued, memoized, fail-closed local solver with a 10,000-node
  ceiling and explicit bounded claim scopes. It is invoked only by the
  research-only `v4-solver` recipe at roots and newly expanded nodes.
- Exact feasibility: 24/24 positives reproduced, 12/12 decoys abstained, zero
  illegal actions, mutations, certificate mismatches, or node-limit failures.
- Observed p95 invocation: 43.717 ms on Toy and 257.692 ms on Beginner, below
  the predeclared 100/400 ms ceilings.
- Candidate A qualifies for the common 384-decision development screen. It is
  not admitted, selected, strength-tested, or exposed through product APIs.
- Full gate: 281 tests pass in 61.436 s; changed-file Ruff and compilation pass.

## Batch 3 — Progressive unpruning

Status: complete at `2561071`; high-rung delta remains pending Batch 5.

### Evidence

- Added separately hashed `v4-ordered-control` and `v4-unpruning` recipes. Both
  use one generated legal-transition set ordered by administrative actions,
  extensions, captures, defenses, fence completions, then other actions.
- Progressive exposure exactly matches 4/8/16/32/64 actions at
  4/16/64/256/1,024 visits and eventually exposes every action at root and
  interior nodes.
- At a natural 54-action root and 64 visits, exactly 16 actions were exposed,
  median visits per exposed child was 4, and all 38 hidden actions had zero
  visits. Across 128 semantic seeds, 50 different first points won equal-tier
  ordering, rejecting a fixed board-direction fallback.
- Forced single administrative actions remain visible. Structural feasibility
  passes; the required +10 percentage-point high-rung admission improvement
  over ordered control is intentionally unresolved until the common screen.
- Full gate: 288 tests pass in 63.818 s; changed-file Ruff and compilation pass.

## Batch 4 — True-terminal settling

Status: complete at `4722d21`; efficiency gates remain pending Batch 5.

### Evidence

- Added a separately hashed `v4-settling` recipe. Before P it retains the
  selected fallback; P–2P uses one transition set to detect immediate progress;
  at 2P it finishes extensions and passes; ending logic uses the losing seat's
  one legal resumption and at most one immediate-progress action.
- Every backed value is a real accepted terminal score. Telemetry records phase
  counts, terminal reason, resumption use, rollout length, and terminal-backup
  confirmation.
- All 12 structural rollouts reached accepted terminals, remained within 4P,
  exercised resumption, and left analyzed states unchanged.
- Structural feasibility passes. The 50% mean-length reduction, 40% p95
  latency reduction, and no-worse-than-five-point admission gates are reserved
  for the identical common workload.
- Full gate: 294 tests pass in 65.825 s; changed-file Ruff and compilation pass.

## Batch 5 — Admission, composition, and holdout

Status: complete at `f2cc98c`; downstream stages gated off.

### Common-screen evidence

All five isolated 384-decision runs completed with zero crashes, illegal
actions, mutations, or incomplete backups.

| Recipe | High-rung admission | Complete gate |
|---|---:|---|
| V4 control | 52.083% | fail |
| Certified solver | 85.417% | fail: three position/policy cells below 3/4 |
| Ordered control | 54.167% | fail |
| Progressive unpruning | 60.417% | fail |
| True-terminal settling | 45.833% | fail |

- Candidate A passes pooled and monotonic gates but fails complete cell
  admission. Its overall p95 latency across the screen is 8.778 s; its
  policy-specific p95 at 64 exceeds 10 s.
- Candidate B improves ordered control by 6.25 percentage points, below the
  required 10 points, and also fails complete admission.
- Candidate C backs up 100% accepted terminals and stays within 4P, but is
  6.25 points worse than control, increases mean rollout length by 4.42%, and
  makes p95 latency 3.64 times slower rather than 40% faster.
- Deterministic selection returns `none-qualified`. Per plan, no composition is
  implemented and the sealed holdout, 256–2,048 ladder, 4,096 contingency, and
  paired diagnostics are not launched.

## Batch 6 — Conditional deep tier and handoff

Status: in progress; deep tier blocked by the Batch 5 gate.
