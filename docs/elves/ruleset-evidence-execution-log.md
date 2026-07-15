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
- [x] Run-control artifacts committed and pushed at `7a0aed1`.
- [x] Evidence PR #13 open.

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

## Batch 1 — Timing and immutable calibration manifest

### Contract

**Behaviors:** validate every required harness option; run non-evidence timing
samples without reading outcomes; freeze source, hashes, candidates, matchups,
budgets, seeds, worker count, stages, paths and gates before calibration launch.

**Build on:** `research/harness/evaluate_rulesets.py`, its deterministic tests,
the registry/evaluator/MCTS hash helpers and the external-output convention.

**Acceptance criteria:**

- [ ] CLI exposes every required option and focused harness tests pass.
- [ ] Timing-only samples finish or produce a documented resource estimate.
- [ ] Sample outcomes are not inspected and sample outputs are removed.
- [ ] Manifest validates against the exact command and committed hashes.
- [ ] Manifest/status changes committed and exact-head CI passes.
- [ ] Stage A launches only after the manifest commit exists remotely.

**Blast radius:** research manifest and evidence documentation only unless CLI
validation exposes a real harness defect. Any harness fix requires a regression
test and a new source/hash pin before launch.
