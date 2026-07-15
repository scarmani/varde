# Varde Evidence Method Redesign

## Decision

The frozen 250/1,000/4,000 MCTS ladder is computationally infeasible on the
current engine and must not be relaunched. MCTS remains useful only as a shallow,
independent diagnostic family. Native search is the practical first screening
family. Neither is currently sufficient to establish strategic depth.

This decision is based on the outcome-blind artifact
`research/results/evidence-feasibility-gate-20260715.json`, payload SHA-256
`556b1f76ab8152abb3a7763de9f82d367224eb6f027132df18af2f11c51094d3`.
The run retained timings and random-game move counts only; it inspected no
decision, score, winner, margin, or other game outcome.

## Measured feasibility

The source-pinned run used n=4, ten repetitions per timing/length cell, six
frozen candidate revisions, both MCTS rollout policies, opening and deterministic
12-action mid-game positions, and fixed seed root 20260715. It finished in
134.65 seconds.

| Ruleset | Native Standard mean max | Uniform sim mean max | Light sim mean max | Random game mean moves |
|---|---:|---:|---:|---:|
| Classic 1.3 | 0.093s | 0.468s | 0.213s | 331.7 |
| Rosette 0.1 | 0.115s | 0.218s | 0.208s | 184.8 |
| Breath 0.1 | 0.187s | 0.203s | 0.233s | 145.9 |
| Breath-run 0.1 | 0.208s | 0.211s | 0.194s | 152.1 |
| Gjerde-breath 0.1 | 0.341s | 0.622s | 0.646s | 177.9 |
| Gjerde-Go 0.1 | 0.450s | 0.683s | 0.514s | 246.2 |

The common budget and full 480-game Stage-A projection at each tested decision
gate are:

| Mean decision gate | Common maximum budget | Projected p95 at that budget | Projected Stage A |
|---|---:|---:|---:|
| 2s | 2 | 2.18s | 1.71h |
| 10s | 14 | 15.28s | 9.63h |
| 30s | 43 | 46.93s | 28.76h |

The predeclared 16/32 ladder fits the mean-time and Stage-A limits at its high
rung (21.50h) but misses the p95 limit at 34.92s. It therefore fails its gate.

A timing-derived 12/24 ladder is the largest simple 2:1 ladder with useful
headroom on this sample: its high rung projects to 26.19s p95 and 16.23h for a
480-game stage on eight workers. Its low rung projects to 13.10s p95 and 8.31h.
These are scheduling estimates, not observed full-game timings. A comparable
480-game native-only workload projects to 0.78h.

## Revised screening sequence

### 1. Native operational screen

Run native ruleset evaluators first, with paired colors and the already declared
correctness, termination, stagnation, wipe, swap, margin and ruleset-specific
telemetry. Its purpose is to find crashes, contradictions, forced degeneracy and
obvious evaluator artifacts cheaply. Native-only results cannot establish a
headline conclusion because the independent agent-family requirement is unmet.

### 2. Shallow independent-search diagnostic

For native survivors only, predeclare uniform and light MCTS at 12 and 24
simulations. Use both colors and fresh paired seeds. Treat the two rungs as a
sensitivity check:

- agreement between native, uniform and light is evidence that a pathology is
  worth investigating, not proof that the game has or lacks depth;
- disagreement makes the conclusion provisional and routes the position to
  tactical fixtures or a stronger future agent;
- improvement from 12 to 24 is not the original search-depth indicator;
- no result from this round is pooled with the frozen v1 250-budget manifest.

Stage the ladder rather than launching 960 games at once: run the 12-simulation
screen first, audit operational correctness, then run 24 only for mechanically
eligible candidates. This preserves falsification value while bounding compute.

### 3. Engine optimization remains the depth prerequisite

The original strategic-depth test—monotonic strength across
250 → 1,000 → 4,000 simulations—remains blocked. A separate behavior-preserving
optimization of `legal_placements`, `resolve`, and `groups_of`, gated against the
frozen 96-fixture tree-stat corpus on PR #14, is required before reinstating a
high-budget ladder.

## What the revised method can support

- legality, crash, save/state and termination accounting;
- gross stagnation, wipe, opening-convergence and ruleset-specific pathology
  discovery;
- outcome-health estimates at their declared sample sizes;
- shallow agent-family disagreement and rollout-policy sensitivity;
- prioritization of tactical fixtures and engine work.

## What it cannot support

- the 250/1,000/4,000 monotonic skill-depth indicator;
- a claim that stronger search beats weaker search;
- reliable decisive-commitment, sacrifice or reversal estimates derived from
  high-budget win probabilities;
- balance, depth, elegance, emergence, beauty or flagship promotion;
- any headline conclusion based only on native or 12/24 MCTS evidence.

The standing rules in `ruleset-promise-evaluation.md` are not weakened. Where a
required gate cannot be measured, its status is `blocked`, never silently
treated as passing.

## Gate before any calibration relaunch

A new, separately versioned manifest may be frozen only after all of these pass:

1. The exact intended source, rules revisions, native hash and MCTS hash are
   settled and the feasibility artifact is regenerated from that source.
2. At least ten outcome-blind timing repetitions cover all six rulesets, both
   policies, and opening/mid-game positions.
3. The 24-simulation rung projects to p95 at most 30 seconds on every stratum.
4. Its 480-game Stage-A projection is at most 20 wall-hours on eight workers;
   the 12-simulation stage projects to at most 10 wall-hours.
5. The harness reports zero mutation, non-finite value, timeout or incomplete
   timing cell, and the artifact hash validates.
6. The new manifest states that 12/24 is diagnostic only and that no result is
   pooled across rules, agent or manifest revisions.

The merged v2 source meets the numeric 12/24 projections, but no calibration is
authorized by this document. The outcome-blind gate has been regenerated on the
settled MCTS agent hash; a new manifest must still be frozen before any run.

## Recommended next computer-only cycle

After user review settles PR ordering, regenerate this gate on the chosen MCTS
hash and freeze a new diagnostic manifest. Run the native operational screen
first. In parallel only after that source is stable, scope a behavior-preserving
incremental legal-generation design; do not resume high-budget MCTS until its
own exact-equivalence and throughput gates pass.
