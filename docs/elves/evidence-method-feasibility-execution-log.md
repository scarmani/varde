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
positions without timing contention. It uses two repetitions per timing cell,
one real terminal rollout per MCTS simulation, and deterministic random full
games for length only. The predeclared diagnostic feasibility gate requires a
common 16/32-simulation ladder, projected Stage A at most 24 hours on eight
workers, and projected decision p95 at most 30 seconds.

Five focused tests cover percentile/budget arithmetic, full-game and Stage-A
projection, gate pass/fail, deterministic prefixes across all six candidates,
and rejection of forbidden measurement fields. Ruff, `py_compile`, and diff
checks pass.

The source-pinned harness was committed as `9d701b5` before measurement.

## Batch 2 — Outcome-blind measurements

### Contract

**Behaviors:** run the committed harness across all six candidates, retain only
timings and random-game move counts, and atomically write the generated JSON.

**Acceptance criteria:**

- [ ] All configured timing and length cells complete within 30 minutes.
- [ ] Artifact pins commit and code hashes and validates its payload hash.
- [ ] `evidence_eligible`, `outcomes_inspected`, and `decisions_inspected` are
  all false.
- [ ] Per-ruleset budgets and aggregate Stage-A projections are finite.

**Blast radius:** one generated research result; no game-evidence output.

### Pre-measurement correction

An initial two-repetition dry run produced no outcomes and was discarded before
commit. Review found that the aggregate gate projected at the maximum common
budget rather than at the declared ladder's high rung. A focused regression
test reproduced the error; the caller now separately reports common-maximum
cost and evaluates the 16/32 ladder at exactly 32 simulations. Repetitions were
raised from two to ten so the reported p95 is not based on only two samples.
