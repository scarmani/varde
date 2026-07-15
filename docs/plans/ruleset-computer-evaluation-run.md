# Varde Computer-Only Ruleset Evaluation Run

## Objective

Execute every currently authorized computer-only step of the ruleset-promise
program in evidence-led order. Freeze configurations before observing outcomes,
use calibration to falsify broken or agent-dependent candidates, spend larger
budgets only through declared gates, and publish complete positive and negative
evidence. Human emergence and aesthetic gates remain explicitly unrun.

## Frozen source

- Base merge: `565c08b0b0dae0ba3b9ec5bbdbd3ab8927cced6b`
- Candidate revisions: `classic-1.3`, `rosette-0.1`, `breath-0.1`,
  `breath-run-0.1`, `gjerde-breath-0.1`, `gjerde-go-0.1`
- Primary size: n=4
- Secondary size: n=5 only after the primary screen
- Calibration seed root: `20260715`
- Rules and evaluators do not change inside a measurement round.

## Batches

### 0. Run staging and settlement

- Confirm PR #12 is merged by a regular merge commit and exact-main CI passes.
- Establish the owned evidence branch, recovery documents, and PR.
- Validate the real CLI before freezing any command.

### 1. Timing and immutable calibration manifest

- Run timing-only one-pair samples at 250, 1,000, and 4,000 simulations.
- Do not inspect their outcomes; retain elapsed time only and remove outputs.
- Pin source, harness, registry, evaluator and MCTS hashes; exact matchups,
  budgets, sizes, pair seeds, workers, checkpoints, output and cancel paths.
- Predeclare stage order and advancement gates before evidence is inspected.

### 2. Calibration stage A — 250 simulations

- Run all six candidates for 20 paired n=4 seeds using native Standard and
  both MCTS rollout policies as declared by the manifest.
- Preserve raw JSONL, telemetry, checkpoints, accounting and hashes outside
  the repository.
- Reject any candidate with illegality, crash, scoring contradiction,
  corrupted state, or unexplained incomplete game.

### 3. Calibration stages B and C — 1,000 and 4,000 simulations

- Resume the predeclared adjacent budget ladder without changing rules,
  evaluator specifications, seeds or outcome definitions.
- Record directional stability and agent disagreement; do not select favorable
  agent results when families disagree.
- Stage C may be withheld from candidates already rejected by a correctness or
  termination gate, but the omission and reason must be reported.

### 4. Fresh health, depth and adversarial screens

- Predeclare fresh seeds before inspecting their games.
- Run the 50-pair health screen only for calibration survivors.
- Run the necessary held-out depth comparisons and n=5 smoke/confirmation.
- Instantiate ruleset-native adversarial profiles/MAP-Elites only for health
  survivors; use them to find degenerate policies rather than to advertise AI
  personalities.
- A candidate failing two declared gates receives at most one declared
  refinement and one fresh rerun.

### 5. Evidence publication and computer-only decision

- Commit compact manifests and generated summaries, never large raw runs.
- Publish negative results and every missing gate.
- Rank computer-screen survivors provisionally, or report that none survive.
- Do not select a flagship or claim emergence, elegance or beauty without the
  separately authorized human protocol.

## Advancement gates

The standing gates from `docs/plans/ruleset-promise-evaluation.md` control:
zero illegal/crash/corruption/unexplained incomplete games; stagnation at most
5%; wipes at most 15%; color results within 40–60%; median absolute margin
below 15% of scoreable area; swap rate 25–75%; adjacent-budget improvement;
rollout-policy stability; and each ruleset-specific admission gate.

Calibration is diagnostic and cannot by itself support a balance or depth
claim. Any rule, evaluator or harness correction creates a new revision and a
fresh round; old and new results are never pooled.

## Stop conditions

Finite run. Stop only after all feasible computer-only batches finish and the
evidence PR is review-ready, or after a genuine resource/correctness blocker
has been reproduced and documented. Human recruitment, human play, retention
interviews, and aesthetic promotion are outside this run.
