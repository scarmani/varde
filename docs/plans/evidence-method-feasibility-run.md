# Evidence Method Feasibility Gate Run

## Objective

Measure, without observing decisions or outcomes, what independent-search
budgets are computationally feasible across all six frozen Varde candidates.
Use the measurements to predeclare a revised evidence method or prove that no
scientifically useful MCTS ladder is currently feasible.

## Constraints

- Branch from merged main `565c08b`; do not alter PR #13 or PR #14.
- Do not change rules, scoring, MCTS, native evaluators or live behavior.
- Do not launch calibration or inspect any action, score, winner or margin.
- Results are timing/length feasibility evidence only and always carry
  `evidence_eligible: false` and `outcomes_inspected: false`.
- Keep measurement wall time below 30 minutes and record actual repetitions.
- Never pool old and redesigned evidence rounds.

## Batches

1. Establish the isolated branch, recovery state and baseline.
2. Implement and test pure budget/projection arithmetic plus outcome-blind
   native, one-simulation and random-length probes.
3. Run all six candidates at n=4 with fixed seeds and atomically record the
   source/hash-pinned measurement artifact.
4. Document the supported and unsupported claims, declare the next feasibility
   gate, validate, open a PR and stop without calibration.

## Stop rule

Finite run. Stop after a review-ready PR with measured feasibility evidence and
one bounded next recommendation. User review is required before merge.
