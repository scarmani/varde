# MCTS v2 Performance Run — Execution Log

## Metadata

- Started: 2026-07-15
- Branch: `codex/mcts-fast-clone-v2`
- Base: `565c08b0b0dae0ba3b9ec5bbdbd3ab8927cced6b`
- Product baseline: 201 passing tests
- Evidence dependency: PR #13, manifest v1 blocked before results

## Batch 0 — Isolated performance run setup

### Contract

**Behaviors:** establish a dedicated branch/worktree and PR; carry forward the
terminal-score, equivalence, versioning and no-calibration invariants.

**Build on:** merged MCTS v1, legal-action adapter, deterministic tests, native
evaluators and feasibility artifact on evidence PR #13.

**Acceptance criteria:**

- [x] Dedicated branch from exact merged main.
- [x] Run-control artifacts committed and pushed at `ffee5ba`.
- [x] Dedicated PR #14 open and linked from evidence PR #13.
- [x] No MCTS or engine behavior modified during staging.

**Blast radius:** temporary session metadata and plan documentation only.

### Decisions

- Fable's shared-checkout/quorum assumptions do not exist in Varde; the useful
  golden/profile/performance sequence is retained in a dedicated worktree.
- Golden root-child statistics will be captured with Python frame tracing so v1
  does not need instrumentation before the baseline is frozen.

### Regression attestation

No product code changed. PR #14 branches from exact merged main; setup adds only
run-control documents. Evidence PR #13 comment:
https://github.com/scarmani/varde/pull/13#issuecomment-4985447457.

## Batch 1 — Golden fixtures and baseline profile

### Contract

**Behaviors:** capture deterministic v1 action/tree-stat fixtures without
editing MCTS; profile representative terminal rollouts; identify measured hot
paths and freeze baseline artifacts before optimization.

**Build on:** `engine/mcts.py`, `RulesState`, the six candidate registry entries,
stable legal-action ordering and fixed seeded action application.

**Acceptance criteria:**

- [x] Fixtures cover all six candidates, both policies, two seeds, opening and
  deterministic mid-game positions.
- [x] Root-child visits/value sums, selected decision and rollout counters are
  captured from unmodified v1.
- [x] Fixture regeneration is deterministic and schema-validated.
- [x] Baseline profile names the actual cumulative-time hot paths.
- [x] Baseline artifacts committed before any engine hot-path edit.

**Blast radius:** research-only generator, fixtures and profile artifacts. No
engine changes are permitted in this batch.

### Golden baseline

`research/fixtures/mcts-v1-golden.json` contains 96 fixtures: six rulesets,
two seeds, budgets 8/32, uniform/light policies, and opening/12-action seeded
mid-game states. Each fixture records the selected decision, root visits and
value sum, every root child's visits/value sum, node count, rollout counters,
setup actions and state-key hash. Fixture payload hash:
`ddc5732655e05244f7b29fdbd68ccfc8bd98fe766b0d7197bd25c4b419d18d2f`.
An immediate full regeneration matched byte-for-byte.

### Baseline profile

Classic n=4, uniform, 250 simulations took 352.685s under cProfile and executed
2.158 billion calls. Of that:

- `_rollout`: 351.453s cumulative;
- `resolve`: 345.224s across 8,215,625 calls;
- `legal_actions`: 340.655s across 85,228 calls;
- `legal_placements`: 338.191s across 84,743 calls;
- `groups_of`: 271.281s across 6,380,583 calls.

The measured dominant cost is full legal-placement resolution at every rollout
step. Serialization-based cloning and final action sorting do not appear in the
top-30 cumulative costs. The implementation pass will still replace structural
cloning as a safe focused improvement, but must not claim it addresses the
orders-of-magnitude legal-enumeration cost.

### Regression attestation

No engine or MCTS file changed. The generator captures the existing internal
root by a temporary behavior-neutral subclass and restores `_Node` after each
call. The profiler intentionally omits the chosen action. Confidence HIGH: two
independent full generations matched and all artifacts identify the v1 hash.
The immutable baseline was committed as `5b876d6` before any engine edit.

## Batch 2 — Hot-path implementation

### Contract

**Behaviors:** add direct structural cloning, remove only demonstrably redundant
final action sorting, and identify the result as MCTS v2 while reproducing the
entire frozen v1 decision/tree-stat corpus exactly.

**Build on:** committed golden corpus `5b876d6`, profile evidence that legal
placement resolution dominates, and the existing stable rules-action order.

**Acceptance criteria:**

- [x] Structural clones are equal but do not alias mutable game/action state.
- [x] Legal-action order exactly matches the v1 sorted order on all fixtures.
- [x] All 96 golden decisions and root statistics reproduce, excluding only the
  intentionally changed agent hash.
- [x] MCTS version/hash changes; terminal backup and rollout semantics do not.

**Blast radius:** `Game.clone`, `RulesState.clone`, redundant final ordering in
the action adapter, MCTS version metadata, and focused equivalence tests only.

### Equivalence result

The process-parallel verifier reconstructed and replayed all 96 frozen v1
fixtures under v2. Selected decisions, node counts, rollout action statistics,
root visits/value sums, and every root-child visit/value sum matched exactly.
Only `agent_hash` was excluded, because v2 must never pool evidence with v1.

`Game.clone()` shares immutable board geometry and tuple stack values while
copying every mutable container. `RulesState.clone()` now uses it directly.
The final action sort was removed only after the emitted sequence was proven to
already follow `ACTION_ORDER`; exact tree-stat equivalence additionally proves
that RNG consumption and rollout semantics are unchanged.

### Validation

- 204 tests passed in 14.84s.
- Changed Python passed Ruff and `py_compile`.
- `git diff --check` passed.
- Confidence HIGH: the corpus covers all six candidates, both rollout policies,
  two budgets, two seeds, and opening plus deterministic mid-game states.

The equivalence-proven implementation was committed as `e4f6d43`.

## Batch 3 — Equivalence and timing gates

### Contract

**Behaviors:** time v2 on the declared fresh n=4 decision and complete-game
surfaces while omitting actions, scores, winners and margins from artifacts.

**Build on:** exact v1/v2 fixture equivalence and the profile-directed single
optimization pass.

**Acceptance criteria:**

- [x] Fresh Classic n=4 uniform@250 decision was measured; it failed the
  two-second gate at 114.804s.
- [x] uniform@1,000 was intentionally skipped after the prerequisite failed.
- [x] The native-standard versus uniform@250 game was intentionally skipped
  after the prerequisite failed, so neither its outcome nor a misleading
  completion projection was produced.
- [x] Failed gates are recorded as negative evidence without further rollout
  redesign or calibration launch.

**Blast radius:** research-only timing artifacts and run-control documents. No
ruleset outcome may be inspected or recorded.

### Timing result

The exact same unprofiled Classic n=4 uniform@250 probe took 115.471s under v1
and 114.804s under v2. Both produced an average 339.908 rollout actions and a
maximum 800, confirming the workload was identical. The structural-clone and
ordering cleanup improved wall time by only 0.58% (`1.0058x`) and v2 remains
`57.4x` over the two-second gate.

The 1,000-simulation and complete-game probes were not launched. Once the
smallest declared decision gate failed by two orders of magnitude, those jobs
could not establish viability and would only consume computer time. No action,
score, winner, margin, or ruleset outcome was emitted by either timing probe.

### Gate decision

MCTS v2 is behaviorally correct but does not clear the evaluation blocker.
The earlier cProfile attribution stands: legal placement resolution and
`groups_of` dominate, while serialization-based cloning was negligible. Per
the run contract, optimization stops after this focused pass; calibration is
not relaunched and v1/v2 evidence remains unpooled.

The negative timing evidence was committed as `52c56d0`.

## Batch 4 — Review and evidence handoff

### Contract

**Behaviors:** independently inspect the focused diff, run the complete exact
head validation surface, publish the blocker to both PRs, and leave a clean,
review-ready branch without launching calibration.

**Build on:** immutable v1 baseline, exact 96-fixture equivalence, and the
reproducible v1/v2 timing artifact.

**Acceptance criteria:**

- [x] The full 207-test suite and syntax checks pass; changed-file Ruff and
  diff checks pass. Repository-wide Ruff reports six pre-existing unused
  imports outside this PR and was not broadened into this performance change.
- [x] Diff review finds no rule, terminal-value, RNG or rollout-policy change.
- [x] PR #14 and evidence PR #13 received the exact negative result and next
  bounded recommendation.
- [ ] Exact-head CI passes and all local processes/worktrees are reconciled.

**Blast radius:** documentation, PR comments, validation and cleanup only.

### Review result

The product diff is confined to structural clone plumbing, removal of a final
sort whose canonical order is proven, the MCTS version/hash, tests and research
artifacts. Terminal reward, UCT selection, random calls, rollout policies,
rules, scoring, saves and browser code are unchanged. The 96-fixture exact
tree-stat replay is stronger than selected-move parity and passed under eight
worker processes.

Local validation passed with 207 tests in 14.83s, changed-file Ruff,
`py_compile`, JSON parsing and diff checks. The whole-repository Ruff command
also identified six unrelated pre-existing unused imports; they are recorded
but intentionally not fixed in this scoped PR.

Evidence handoff comments:

- PR #14: https://github.com/scarmani/varde/pull/14#issuecomment-4985771263
- PR #13: https://github.com/scarmani/varde/pull/13#issuecomment-4985771340

No evaluation, profiling or timing process remains. The detached frozen-source
worktree and both active PR worktrees are preserved intentionally for review;
none is mistaken for an active compute job.
