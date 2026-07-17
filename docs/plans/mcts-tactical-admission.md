# MCTS tactical admission and decision telemetry

This bounded research unit precedes any further paired-match computation. It
does not alter rules, scoring, legal actions, MCTS selection, or rollout
behavior.

## Question

Before asking whether a larger simulation budget wins more games, determine
whether terminal-score MCTS can recognize constructed decisions that exercise
the candidate rulesets' distinctive mechanics. Record enough work telemetry to
distinguish tactical failure from simple root under-sampling.

## Frozen corpus

The ten canonical positions cover all six candidate rulesets and six decision
types: immediate capture, sole-liberty defense, pie takeover, Rosette
entombment, both steps of a Breath-run rescue chain, Gjerde fence completion,
and sparse-score acceptance. The takeover position is explicitly a
synthetic-history decision-isolation state; it is not represented as a
reachable opening.

Every acceptable action must be legal under the real action API. Fixture
construction and telemetry must be non-mutating. Tactical labels are derived
from legal transitions rather than evaluator scores.

## Ladder and telemetry

- Rollout policies: uniform and the current epsilon-greedy light policy.
- Simulations per decision: 4, 16, and 64.
- Four independently derived deterministic seeds per position/policy/budget.
- Total: 240 decisions, no paired games and no game outcomes.
- Per decision: root width, action-kind counts, simulations, nodes, mean backed
  value, average and maximum rollout length, root coverage, latency, capture,
  defense, takeover, extension, finish-extension, and fence-completion labels.

Latency is inherently machine-observational. It is retained in the raw record
but excluded from the deterministic decision hash. Schedule, seeds, selected
actions, search work, and all tactical classifications remain hash-auditable.

## Predeclared admission gate

Admission requires all of the following:

1. Every decision completes legally without mutating its position.
2. Every fixture/policy cell hits its acceptable action in at least three of
   four high-budget trials.
3. The pooled high-budget hit rate is at least 80%.
4. Aggregate hit rate is nondecreasing across 4, 16, and 64 simulations for
   each rollout policy.

Failure is useful evidence: it keeps paired MCTS@24 and light-rollout match
stages blocked and directs the next unit toward the failed fixture/policy cells.
Passing permits a later stage to be frozen; it does not launch that stage or
establish strength, balance, strategic depth, or ruleset promise.
