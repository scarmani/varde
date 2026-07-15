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

- [x] CLI exposes every required option and focused harness tests pass.
- [x] Timing-only sample produced a documented resource lower bound.
- [x] Sample outcomes were not inspected and sample outputs were removed.
- [x] Manifest validates against exact commands and committed agent/code hashes.
- [ ] Manifest/status changes committed and exact-head CI passes.
- [ ] Stage A launches only after the manifest commit exists remotely.

**Blast radius:** research manifest and evidence documentation only unless CLI
validation exposes a real harness defect. Any harness fix requires a regression
test and a new source/hash pin before launch.

### Timing feasibility result

The declared n=4 Classic sample scheduled six games at budget 250. Its first
two games used two full CPU cores for 667.77 wall seconds and 1321.04 user CPU
seconds without completing a record. The sample was interrupted because this
already established the feasibility lower bound; no score/outcome existed to
inspect. The temporary run and profiler output were removed.

The naive three-agent cross-product would schedule 720 games per budget and
would also let `checkpoint_interval=2` cap active process work at two games.
The frozen manifest instead declares separate native-vs-uniform and
native-vs-light jobs, 480 games total per rung, eight workers, and checkpoints
of eight. The resulting ideal lower bound is 11.01 hours for stage A and 44.03
hours for stage B. Budget 4,000 is survivor-only; projections are explicitly
lower bounds, not promises.

### Prelaunch corrections

- A changed budget is a changed checkpoint configuration; each rung uses a
  separate output directory. `--resume` applies only inside one job.
- Compute runs from a detached worktree at the manifest commit. Later evidence
  documentation therefore cannot invalidate checkpoint source provenance.
- Small-sample health observations do not eliminate candidates between A and B;
  only correctness, termination, state-corruption, score-contradiction, or
  unexplained-incomplete failures do.

### Validation

- CLI help exposes rulesets, agents, budgets, pairs, board sizes, seed, workers,
  output directory, checkpoint interval, resume, cancel file and telemetry.
- Focused harness suite: 9 passed.
- Full suite: 202 passed in 14.83s.
- Python compilation and JavaScript syntax passed.

### Regression attestation

The only executable change is one manifest-contract test. No engine, rule,
evaluator, MCTS or harness behavior changed. Test count increased from 201 to
202. Confidence HIGH: hashes are checked against live modules, commands are
data-only, and all previous tests pass.
