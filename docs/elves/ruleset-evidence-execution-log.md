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
- [x] Manifest/status changes committed at `0612369`; exact-head CI passes.
- [x] Stage A launched only after the manifest commit existed remotely.

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

### Launch evidence

- PR #13 was clean at exact head `0612369`; both CI checks passed and no review
  feedback was outstanding.
- Detached source: `/tmp/varde-calibration-source-20260715` at exact commit
  `0612369d1d5e9739a57aa8859fb8cb49afd2eeca`.
- A-uniform-250 launched at 2026-07-15T15:41:25-05:00 in managed session
  `86550`, parent PID `48847`, with eight active worker processes.
- Initial `state.json` records the exact manifest code, registry, native-agent,
  MCTS-agent and source hashes; status `running`, next task 0.
- One attempted detached `nohup` launch was reaped by the shell before Python
  started. It created no checkpoint or game. The empty log was removed and the
  managed-session launch replaced it.

## Batch 2 — Calibration stage A at 250 simulations

### Contract

**Behaviors:** complete A-uniform-250 and A-light-250 from the frozen detached
source; preserve every record and failure; inspect outcomes only after each job
is complete; perform the predeclared operational advancement audit.

**Build on:** immutable manifest commit `0612369`, external atomic checkpoints,
ordered process reduction and cancel/resume support.

**Acceptance criteria:**

- [ ] First eight-game checkpoint appears with exact provenance.
- [ ] A-uniform-250 completes or records an explicit reproducible blocker.
- [ ] A-light-250 completes or records an explicit reproducible blocker.
- [ ] Zero hidden/cancelled attempts; accounting reconciles to schedule.
- [ ] Operational audit applies only predeclared advancement rules.
- [ ] Compact non-claim summary committed; raw artifacts remain external.

**Blast radius:** no repository behavior changes. Long-running external compute
uses eight workers and writes only under `/Users/armand/varde-runs/`.

### Predeclared operational audit

Before the first eight-game checkpoint existed, added
`research/harness/audit_calibration.py`. It refuses partial jobs, reconstructs
each exact manifest config, verifies checkpoint and provenance hashes, hashes
all raw artifacts, applies only the frozen correctness/termination advancement
gate, and always emits `promotion_blocked: true`. Diagnostic health gates are
retained without becoming small-sample elimination or promotion claims.

The synthetic two-policy audit fixture schedules the full frozen 480-record
shape and verifies that zero-failure candidates advance mechanically. Focused
suite: 10 passed. Full suite: 203 passed in 33.85s under concurrent calibration
load; Ruff, Python compilation and JavaScript syntax passed. No partial
calibration outcome was read while implementing or testing the audit.

### Feasibility stop

A-uniform-250 ran eight Classic games concurrently at sustained eight-core load
for more than 40 minutes without completing a single record. A separate
budget-1 opening decision took 1.05s and one terminal rollout traversed 343 real
actions. Linear scaling makes one budget-250 opening decision approximately
262.5 CPU seconds before the rest of the game.

Managed session `86550` was interrupted with `next_task: 0` and `records: []`.
The external zero-record state, empty JSONL and non-claim summary are preserved
and hash-pinned by
`research/results/ruleset-calibration-feasibility-20260715.json`. No game
outcome existed to inspect. This is an MCTS v1 throughput failure, not a
correctness, balance, depth or ruleset verdict.

The next measurement round requires a distinct MCTS agent hash and fresh
manifest. MCTS v1 and v2 evidence will never be pooled.

### Remediation handoff

PR #14 reproduced all 96 v1 decision/tree-stat fixtures exactly under MCTS v2,
but its matching outcome-blind uniform@250 timing improved only 0.58% and still
missed the two-second gate by 57.4x. PR #15 then measured every candidate and
predeclared a native-first 12/24 diagnostic method. The diagnostic is
operationally feasible but explicitly cannot support strategic-depth or
flagship claims.

This evidence run now waits at a user-review boundary. After PR ordering settles
the selected MCTS hash, the feasibility artifact must be regenerated and a new
manifest frozen. The original 250-budget job remains invalid to resume.
