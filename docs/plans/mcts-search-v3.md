# MCTS Search V3 and Meaningful-Budget Calibration

## Objective

Repair the independent, ruleset-neutral MCTS research agent using isolated,
reproducible ablations, require tactical admission before match evidence, and
then freeze either 2,048 or 4,096 simulations as the named deep-research tier
from measured root coverage and single-process latency. This run does not
change Varde's rules or silently replace the live browser opponent.

## Verified starting point

- Base commit: `b620a11a72097f22e5addbfaf58b56073f9612cd`.
- Product baseline: 254 passing Python tests plus clean Python and JavaScript
  syntax checks.
- The frozen 4/16/64 tactical run completed all 240 decisions legally and
  without mutation, but failed admission at a pooled 26.25% hit rate at 64.
- Wide diagnostic roots contain 49--69 actions. At 64 simulations they receive
  roughly one sample per action, backed win/draw/loss values saturate, and
  coordinate ordering decides many final ties.
- MCTS remains an independent research surface. The live browser opponent uses
  bounded native search.

## Run invariants

- Do not edit `engine/varde.py`, rules, scoring, save semantics, or live-game
  termination.
- Every MCTS simulation uses the real legal-action API, respects superko, and
  reaches a real terminal result. Research watchdogs may stop a job, never a
  live game or rollout inside the agent.
- Do not use native evaluator values as MCTS leaf values. Terminal results and
  rules-layer transition facts are the only admissible search signals.
- Version and hash every behavior-changing search variant. Never pool evidence
  across versions or rewrite the failed 2026-07-16 evidence.
- Freeze manifests before reading outcomes. Keep seeds, source hashes, per-run
  records, cancellation, crashes, and incomplete work explicit.
- Do not run paired matches until a candidate passes tactical admission.
- The user reviews and merges. This branch is never self-merged.

## Batch 0 — Stage the isolated run

- Create a dedicated branch/worktree from the exact merged base.
- Record the plan, recovery state, execution log, and launch guard.
- Run the full product and syntax preflight.
- Push the setup-only commit and open a draftable review surface before search
  behavior changes.

Acceptance: a clean, launch-ready PR whose diff contains only run-control
documentation and whose baseline is reproducible.

## Batch 1 — Measurement substrate and admission corpus V2

- Add behavior-neutral per-root-action telemetry: stable action identity,
  visits, terminal win/draw/loss counts, terminal score-margin observations,
  backed mean, final rank, and selection reason. Node and rollout totals must
  remain exact.
- Preserve every existing seeded MCTS v2 decision and tree statistic when the
  new telemetry is disabled or ignored.
- Retain the ten existing natural-width fixtures as behavior diagnostics.
- Add small-root admission puzzles with machine-checkable dominance proofs.
  Prefer exact terminal enumeration; when exact enumeration is infeasible, the
  fixture is diagnostic rather than admission evidence. Cover capture,
  sole-liberty defense, score acceptance, takeover, rescue continuation, and
  fence completion where the real legal-action surface permits a bounded
  proof.
- Commit the manifest before running the frozen 4/16/64 pre-fix baseline.

Gate: corpus construction, proof validation, deterministic regeneration,
legacy-decision parity, legality, non-mutation, and complete telemetry all pass.

## Batch 2 — Geometry-neutral deterministic ties

- Remove coordinate-ordered tie preferences from traversal and final root
  choice.
- Use a SHA-256 tie value derived from the search seed, the analyzed position,
  the node path/position, and the candidate action. It must be reproducible and
  must not privilege a fixed board direction.
- Bump the search version/hash and run this change alone on the frozen V2
  corpus.
- Add tests for determinism, color symmetry, transformed-position directional
  neutrality, legality, non-mutation, superko, pass, takeover, extension, and
  resumption actions.

Gate: no fixed coordinate preference remains and the isolated variant is fully
auditable. Tactical improvement is evidence, not a prerequisite for continuing
to the next isolated ablation.

## Batch 3 — Terminal-margin secondary backup

- Preserve terminal win/draw/loss as the primary backed result.
- Add a bounded, ruleset-neutral terminal score margin normalized by the
  ruleset's scoreable area as a secondary statistic, rather than importing a
  native evaluator or heuristic leaf value.
- Compare tie-only with tie-plus-margin on the frozen admission and diagnostic
  corpus. Record root rank changes, saturation, hit rate, rollout length, node
  count, and latency.
- Version/hash the combined semantics separately.

Gate: values are finite, bounded, color-symmetric, deterministic, and terminal
only. Retain the margin signal only if it improves admission or resolves
documented saturation without a material diagnostic regression.

## Batch 4 — Minimal tactical proposal/rollout ablation

- Add the smallest rules-layer-only action proposal or rollout bias capable of
  recognizing immediate captures, sole-liberty defense, legal extension
  continuation, immediate score/fence completion, and administrative actions.
- Reuse already-generated legal transitions. Do not call native evaluators or
  introduce nested full move scans.
- Test tactical guidance alone first, then with the retained tie/margin changes.
- Predeclare the admission threshold in the manifest and choose the simplest
  passing search variant. If none passes, preserve the negative evidence and do
  not disguise failure by increasing the budget.

Gate: at least 80% pooled hit rate at the declared high admission rung, every
admission cell at least 75%, no material regression on deterministic
administrative fixtures, and zero illegal, mutated, crashed, or incomplete
decisions. Diagnostic fixtures remain interpretive and cannot fail a proven
admission result by themselves.

## Batch 5 — Calibrate the 2,048/4,096 deep tier

- Only after Batch 4 admission, run single-process decision measurements at
  256, 512, 1,024, and 2,048 simulations on the frozen corpus. Run 4,096 only
  when 2,048 leaves inadequate root revisits or the admission result is not
  stable and the projected job still fits the finite compute budget.
- Record per-action visit distributions, effective root samples, rank
  stability, hit rate, wall time, rollout actions, and peak memory.
- Select 2,048 when it gives stable admission and useful repeated sampling of
  all natural-width roots. Select 4,096 only when it produces a material,
  reproducible gain over 2,048 that justifies approximately double the work.
- Publish the chosen value as a named deep **research** tier in the evaluator
  CLI and frozen manifests. Do not expose it as a live browser difficulty
  unless separate interactive p95 acceptance is met.

Meaningful-budget gate: the selected tier passes admission in both rollout
policy strata, has stable root rankings across adjacent seeds/budgets, completes
the declared corpus within the run's compute envelope, and has no legality or
integrity failures. If neither budget clears those conditions, report that
honestly instead of naming one by preference.

## Batch 6 — Conditional paired diagnostic and final handoff

- If and only if Batch 5 passes, freeze a small paired, both-color diagnostic
  using the selected tier. Keep it distinct from the later 50-pair health
  screen and make no balance/depth claim from this small sample.
- If admission or feasibility fails, skip paired games and publish complete
  negative evidence.
- Run the full product suite, syntax checks, research auditors, deterministic
  regeneration, and exact-head CI. Review the diff and reconcile all compute.
- Update research documentation with exact hashes, commands, limitations, and
  the next bounded recommendation.

Acceptance: a clean review-ready PR, no active child processes, immutable raw
evidence outside the repository with hash-pinned compact artifacts inside it,
and no claim stronger than the evidence permits.

## Stop conditions

Stop immediately and preserve state on a scoring/rules contradiction, illegal
action, unexplained mutation, non-deterministic replay, manifest drift, or
evidence contamination. A failed admission or impractical 2,048/4,096 runtime
is a valid completed result, not permission to weaken the gate or add heuristic
leaf evaluation.
