# Varde Ruleset Evidence Run — Execution Log

## Run metadata

- Started: 2026-07-15
- Mode: finite
- Branch: `codex/ruleset-evidence-run`
- Source base: `565c08b0b0dae0ba3b9ec5bbdbd3ab8927cced6b`
- Baseline: 201 passing tests
- Human gates: out of scope and never inferred

## Batch 0 — Run staging and settlement

### Contract

**Behaviors:** settle reviewed infrastructure; establish an owned evidence
branch, recovery state and PR; carry forward all evidence restrictions.

**Build on:** merged ruleset registry, native evaluators, MCTS, deterministic
harness, status matrix and durable learnings from PR #12.

**Acceptance criteria:**

- [x] PR #12 merged with a regular merge commit.
- [x] Merge commit `565c08b` passed exact-main CI.
- [x] Feature head passed 201 tests plus Python/JavaScript syntax.
- [x] Operational smoke remains promotion-blocked and headline-ineligible.
- [ ] Run-control artifacts committed and pushed.
- [ ] Evidence PR open.

**Blast radius:** documentation and temporary session metadata only; no rules,
engine, evaluator, harness or runtime behavior changes.

### Decisions

- The user's explicit “yes to all” authorized settlement of the already-reviewed
  PR #12. The evidence PR created by this new run remains user-merged.
- Fable's imported Aragora quorum/shared-checkout assumptions were rejected as
  stale for Varde; its bounded settlement and predeclaration advice was retained.
- Calibration will predeclare 250/1,000/4,000 stages but launch 250 first.

### Verification

- `pytest -q -o addopts=''`: 201 passed in 14.72s.
- Python compilation, JavaScript syntax and diff whitespace checks passed.
- Main workflow run `29447627409`: success.

### Regression attestation

No product code changed in Batch 0. Confidence HIGH: source equals the reviewed
merge head and the only new files are run-control documentation.
