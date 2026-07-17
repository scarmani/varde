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

## Batch 1 evidence

- Behavior-neutral root telemetry can be collected on the existing backup walk
  without another rollout or RNG call. Telemetry-on/off seeded action parity
  holds across every candidate ruleset and both rollout policies.
- The historical 96-fixture golden corpus is stale specifically for all 16
  Breath-run cases. The same failures reproduce at the untouched base commit,
  after automatic extension finishing changed that rules surface. Preserve the
  corpus as historical evidence; use current-state parity for this batch.
- The frozen split V2 run completed 384/384 decisions with a clean provenance
  audit but failed proof-grade admission at `60.4167%` on the 64-simulation
  rung. The high-budget per-position/policy floor also failed.
- Mean root coverage reached `99.18%` at 64, yet sole-liberty defense scored
  `0/8`; complete enumeration is not sufficient when most children have only
  shallow or tied terminal samples.
- The unmodified agent's 64-simulation p95 decision latency was about 7.0 s for
  uniform and 7.2 s for epsilon-greedy on this mixed corpus. A deep research
  tier must therefore be calibrated from measured single-process feasibility,
  not presented as an interactive opponent by default.

## Batch 2 evidence

- Replacing both canonical action/coordinate fallbacks with seeded SHA-256 ties
  removes a real directional artifact but reduces proof-grade admission from
  `60.4167%` to `54.1667%` at 64 simulations on the identical schedule.
- Root coverage was unchanged (`99.1795%` mean). The prior coordinate ordering
  was sometimes accidentally aligned with the synthetic proof actions; removing
  it exposes rather than creates the underlying lack of terminal discrimination.
- Tie-only MCTS V3 failed the per-cell and monotonicity gates. It is retained as
  a correctness foundation, not claimed as a stronger agent.
- Search semantics and research evidence must remain separately versioned:
  historical MCTS V2 timing and tactical results cannot be validated against a
  current-agent hash after a behavior change.

## Batch 3 evidence

- Terminal margin normalized by scoreable area is finite, bounded, exactly
  color-symmetric, and can be backed on the existing terminal-result walk.
- Tie-plus-margin MCTS V4 scored `52.0833%` on proof-grade admission at 64,
  below tie-only V3's `54.1667%`; it remains tactically inadmissible.
- Margin nevertheless resolved 45/80 high-budget natural-diagnostic final ties
  with diagnostic hit rate unchanged at `32.5%`. This satisfies the explicit
  saturation-without-material-regression retention path.
- A terminal-only secondary signal can distinguish equal W/D/L samples, but it
  does not recognize immediate defense, capture, or fence completion reliably.
  Batch 4 needs proposal-level rules facts rather than more terminal sampling of
  uniformly expanded roots.

## Update rule

Append only evidence-backed findings after each batch. Record failed hypotheses
and operational costs as carefully as successful changes.
