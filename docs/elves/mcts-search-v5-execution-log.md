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

Status: completed at `e828a1d`.

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

### Outcome

- Added a generic predicate/schedule oracle that imports neither MCTS nor the
  tactical solver. It produces complete action-status sets and bounded actor
  traces, and fails closed at 10,000 nodes.
- Froze development and holdout manifests at source `1204de9`; each contains
  24 positions, twelve per board stratum, twelve per root-width stratum, four
  per tactical family, and six exact decoys.
- Development, holdout, and all 51 historical V3/V4 state hashes are pairwise
  disjoint. Oracle certificates completed without a node-limit hit.
- Dedicated 15-test suite covered quantifiers, actor ownership, equivalent
  proofs, fence semantics, decoys, superko, symmetry, non-mutation, exact
  regeneration, and hash separation. Full product suite: 313 tests passed in
  76.166 seconds. Changed-file Ruff, compilation, and diff checks passed.
- Frozen manifest file SHA-256 values:
  - development: `290e5f7625a4536113a2f8ae52c128581fdc488a72552f284bca43103e75e8b3`;
  - holdout: `af6bbab0fb1a88c147758a83f291e4042f54e407e973e46707d8b8d23e82f8d0`.

## Batch 2 — Correct root-only proof guidance

Status: completed at `f572f40`.

### Contract

**Behavior**

- Correct rescue closure and fence predicates in a set-valued solver result.
- Scan once at the root, reuse root transitions, and add only decaying
  `+1/0/-1` selection guidance. Never exclude an action or back up proof value.

**Acceptance criteria**

- Exact development oracle agreement and zero false positive decoy guidance.
- One root scan per decision, equivalent sets preserved, unknown-only parity,
  p95 ceilings, legality, superko, determinism, and non-mutation.

**Blast radius**

- V5 research solver/search variants and their tests only; V4 recipes retain
  exact behavior and hashes.

### Outcome

- Added an oracle-independent set-valued solver and two immutable V5 recipe
  IDs for unchanged control and guidance-only search.
- Solver statuses match the independent oracle action-for-action on all 24
  development positions; all declared decoys have zero proven actions.
- Integration reuses one generated root transition set, invokes exactly one
  root scan, applies `+1/0/-1 ÷ (1 + visits)` only to expansion/UCT selection,
  retains every action, and records only accepted-terminal backups.
- Unknown-only guidance reproduces the control action, value, visits, and root
  trace exactly. Existing V4 control agent hash remains
  `b1349822959ab4968503208d1fc48d3dfb1c6a900914b95519a5e73693ff49cf`.
- Observed scan p95: approximately 19 ms Toy and 101 ms Beginner. Full suite:
  323 tests passed in 111.137 seconds; changed-file Ruff, compilation, and diff
  checks passed. Initial full run exposed only a stale expected-variant count;
  that regression assertion was updated and the complete suite reran green.

## Batch 3 — Obligation-reserved progressive unpruning

Status: completed at `f1b4fe8`.

### Contract

**Behavior**

- Reserve visible capacity for administrative actions and each detected urgent
  obligation; guided arms additionally expose every proven action.
- Fill the remaining square-root exposure budget with unchanged V4 rule-fact
  ordering and semantic ties; overflow may exceed but never shrink the base.

**Acceptance criteria**

- Exact schedule/overflow, mandatory visibility, eventual expansion,
  determinism, neutrality, median visit allocation, and V4 parity tests.

**Blast radius**

- V5 unpruning module/integration/tests only; historical V4 order and recipes
  remain byte-behavior compatible.

### Outcome

- Added an independent V5 exposure-plan module. Administrative actions, one
  rule-ordered action per detected obligation, and the complete guided proven
  set are mandatory; they can overflow but never reduce the base schedule.
- Exact base exposure remains 4/8/16/32/64 at 4/16/64/256/1,024 visits and
  reaches every action. Next-threshold telemetry accounts for overflow.
- A natural 52-action root exposed 16 at 64 visits and gave mandatory actions
  median visits at least three. Across 128 seeds, equal-tier first exposure
  reached over 40 distinct points.
- Four V5 factor hashes are distinct; the V4-unpruning hash remains
  `17ec848552b44894fa44cf3fe8296346129f28aa96518a264e60ed3be76b3c0e`.
- Seven dedicated unpruning tests and all 330 product tests passed in 110.769
  seconds. Changed-file Ruff, compilation, diff, forbidden-file, and CI checks
  passed.

## Batch 4 — True-terminal Settling V2

Status: completed at `427081f`.

### Contract

**Behavior**

- Apply the frozen four-event policy from half-P, force finish/pass at P, and
  preserve the real two-pass acceptance/resumption protocol.
- Reuse one transition/event set per state and treat any action beyond 4P as an
  integrity failure rather than a heuristic value.

**Acceptance criteria**

- Exact event/phase/resumption tests, 100% accepted-terminal backups,
  deterministic/non-mutating recipes, and historical Settling V1 parity.

**Blast radius**

- New V5 settling module plus research-only MCTS recipe combinations/tests.

### Outcome

- Added Settling V2 alongside unchanged V1. It uses exactly capture,
  extension/closure, surviving sole-liberty defense, and immediate fence
  completion events from one transition batch.
- Half-P no-event and opponent-pass states settle immediately; P forces finish
  or pass. A losing seat resumes once and receives at most one event action.
- Every test rollout terminates through accepted rules state. A deliberately
  reduced action ceiling raises `SettlingIntegrityError`, never a value.
- All eight factorial hashes are unique; V4 settling remains
  `d37e2c5fdeb1d95a245bcdb441192c02e77983a6931f9b1b88ef5be108f7a014`.
- Eight focused settling tests and all 338 product tests passed in 113.604
  seconds; changed-file Ruff, compilation, forbidden-file, diff, and CI checks
  passed.

## Batch 5 — Eight-arm development factorial

Status: in progress.

### Contract

**Behavior**

- Freeze and run all eight combinations over 24 development positions,
  4/16/64 simulations, both rollout policies, and four deterministic replicates.
- Add only the registered high-rung ordered-control wide-root instrument needed
  to isolate unpruning's ten-point delta.

**Acceptance criteria**

- Atomic resume/worker invariance, complete integrity, exact component gates,
  deterministic selection, and no holdout access before qualification.

**Blast radius**

- New V5 research harness/manifests and repository-external raw evidence;
  compact generated audit only after the frozen run.
