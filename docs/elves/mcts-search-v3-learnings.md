# MCTS Search V3 — Learnings

## Durable findings carried into the run

- The 2026-07-16 4/16/64 ladder is clean negative agent evidence: 240/240
  decisions were legal, complete, deterministic, and non-mutating, but pooled
  high-budget admission was only 26.25%.
- Natural-width roots contain 49--69 actions. Sixty-four simulations mostly
  enumerate each root action once and therefore cannot estimate action value
  reliably.
- Terminal W/D/L feedback saturates: selected wide-root actions commonly tie at
  a backed mean of 1.0. The existing coordinate key then turns a statistical tie
  into a fixed directional preference.
- The current light rollout shortens games but does not supply enough tactical
  signal. Increasing the unchanged budget alone is not an adequate repair.
- Existing wide fixtures are valuable behavior diagnostics but generally do not
  prove forced game-theoretic dominance. Admission needs a separate small-root,
  machine-verifiable corpus.
- MCTS v2 is research-only. The live browser opponent is a different bounded
  native-search system; silently replacing it with thousands of terminal
  rollouts would be a product behavior and latency change.

## Advisory input retained

The bounded Fable goal-cycle agreed that the next unit should be measurement
first: root-action outcome telemetry, a split between wide diagnostics and
dominance-proven admission puzzles, and a frozen pre-fix baseline before search
changes. Its references to an Aragora operating contract and tier/quorum
machinery were discarded because those files and governance rules do not exist
in Varde.

## Open hypotheses

- A seeded hash tie removes the visible coordinate artifact but may not improve
  tactical hit rate by itself.
- Normalized terminal margin may separate W/D/L-saturated actions without
  violating the evaluator-artifact firewall.
- A minimal rules-layer tactical proposal policy may be necessary to allocate
  useful samples before all 49--69 actions receive uniform attention.
- 2,048 simulations should revisit a 69-action root roughly 29 times per action
  before deeper-tree effects; 4,096 roughly doubles that opportunity. Actual
  visit distributions and latency, not this arithmetic, decide the named tier.

## Update rule

Append only evidence-backed findings after each batch. Record failed hypotheses
and operational costs as carefully as successful changes.
