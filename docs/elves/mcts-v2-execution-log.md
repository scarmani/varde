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
