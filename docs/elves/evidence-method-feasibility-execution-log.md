# Evidence Method Feasibility Gate — Execution Log

## Metadata

- Started: 2026-07-15
- Branch: `codex/evidence-method-feasibility`
- Base: `565c08b0b0dae0ba3b9ec5bbdbd3ab8927cced6b`
- Fable goal cycle:
  `/Users/armand/Development/varde/.aragora/goal_cycles/20260715T221513Z`

## Batch 0 — Isolated feasibility run setup

### Contract

**Behaviors:** create a clean branch/worktree from merged main, record the
outcome-blind contract, and verify that PRs #13/#14 remain untouched.

**Acceptance criteria:**

- [x] Dedicated branch from exact merged main.
- [x] No evidence/calibration process active.
- [x] Separate finite run-control and recovery documents exist.
- [x] Baseline 201-test suite passed before harness work.

**Blast radius:** run-control documents only.

### Decision

The completed MCTS v2 pass proves that a reduced ladder small enough to fit the
two-second decision gate would be scientifically inadequate. This run measures
all candidates and explicitly downgrades unsupported search-depth claims rather
than relaunching the frozen v1 manifest.

Setup commit `2bad7de` is pushed on PR #15:
https://github.com/scarmani/varde/pull/15

## Batch 1 — Harness and arithmetic

### Contract

**Behaviors:** implement pure budget/projection functions and outcome-blind
native, single-simulation and random-playout-length probes with fixed seeds.

**Acceptance criteria:**

- [x] Budget and projection arithmetic is deterministic and unit-tested.
- [x] Probe payloads cannot contain actions, scores, winners or margins.
- [x] Mid-game prefixes are deterministic, legal and non-terminal.
- [x] Atomic output pins source and agent hashes and always blocks evidence use.

**Blast radius:** one repository-relative research harness and focused tests.

### Implementation

The sequential harness measures opening and deterministic 12-action mid-game
positions without timing contention. It uses ten repetitions per timing cell,
one real terminal rollout per MCTS simulation, and deterministic random full
games for length only. The predeclared diagnostic feasibility gate requires a
common 16/32-simulation ladder, projected Stage A at most 24 hours on eight
workers, and projected decision p95 at most 30 seconds.

Ten focused tests cover percentile/budget arithmetic, full-game and Stage-A
projection, gate pass/fail, deterministic prefixes across all six candidates,
and rejection of forbidden measurement fields. Ruff, `py_compile`, and diff
checks pass.

The source-pinned harness was committed as `9d701b5` before measurement.

## Batch 2 — Outcome-blind measurements

### Contract

**Behaviors:** run the committed harness across all six candidates, retain only
timings and random-game move counts, and atomically write the generated JSON.

**Acceptance criteria:**

- [x] All configured timing and length cells completed in 134.65 seconds.
- [x] Artifact pins commit and code hashes and validates payload hash
  `556b1f76ab8152abb3a7763de9f82d367224eb6f027132df18af2f11c51094d3`.
- [x] `evidence_eligible`, `outcomes_inspected`, and `decisions_inspected` are
  all false.
- [x] Per-ruleset budgets and aggregate Stage-A projections are finite.

**Blast radius:** one generated research result; no game-evidence output.

### Pre-measurement correction

An initial two-repetition dry run produced no outcomes and was discarded before
commit. Review found that the aggregate gate projected at the maximum common
budget rather than at the declared ladder's high rung. A focused regression
test reproduced the error; the caller now separately reports common-maximum
cost and evaluates the 16/32 ladder at exactly 32 simulations. Repetitions were
raised from two to ten so the reported p95 is not based on only two samples.

### Official measurement

The refreshed retained run used MCTS v2 source `06b7263`, harness SHA-256
`771b166fff81400c58e2ae0711b475b09f5e5d25b6fc4b8cf633a469da89fd48`,
ten repetitions per cell, and 134.65 seconds total wall time.

| Ruleset | Native mean max | Uniform sim mean max | Light sim mean max | Random moves mean |
|---|---:|---:|---:|---:|
| Classic | 0.093s | 0.468s | 0.213s | 331.7 |
| Rosette | 0.115s | 0.218s | 0.208s | 184.8 |
| Breath | 0.187s | 0.203s | 0.233s | 145.9 |
| Breath-run | 0.208s | 0.211s | 0.194s | 152.1 |
| Gjerde | 0.341s | 0.622s | 0.646s | 177.9 |
| Gjerde-Go | 0.450s | 0.683s | 0.514s | 246.2 |

Aggregate common maximum budgets are 2 at the 2-second gate, 14 at the
10-second gate, and 43 at the 30-second gate. At those maxima, projected Stage
A is respectively 1.71h, 9.63h and 28.76h; p95 is 2.18s, 15.28s and 46.93s.

The predeclared 16/32 diagnostic ladder is available at the 30-second mean
gate and projects to 21.50h, but fails because p95 is 34.92s. A post-measurement
timing derivation shows 12/24 would project to 16.23h and 26.19s p95. That is an
operationally feasible diagnostic ladder, not strategic-depth evidence. A
480-game native-only workload projects to 0.78h on eight workers.

The measurement artifact was committed as `2decf82`.

## Batch 3 — Method redesign and validation

### Contract

**Behaviors:** distinguish operationally feasible shallow diagnostics from
unsupported depth claims, declare the numeric relaunch gate, validate the full
branch, and publish a review-ready PR without launching calibration.

**Acceptance criteria:**

- [x] Redesign records measured values, supported claims and blocked claims.
- [x] The derived 12/24 diagnostic ladder is explicitly non-depth and never
  pooled with another manifest or agent revision.
- [x] Refreshed local 221-test suite, compilation and diff checks pass on the
  merged MCTS v2 baseline; exact-head CI follows the refresh push.
- [x] PR #15 received the result and bounded next recommendation:
  https://github.com/scarmani/varde/pull/15#issuecomment-4985930518

**Blast radius:** plan/evidence documentation, validation and PR handoff only.

### Closure

PR #15 now carries the regenerated MCTS v2 timing artifact. No rule, scoring,
MCTS, evaluator, live game or calibration state changed. No calibration outcome
was generated or inspected. A new manifest must still freeze before any run.
