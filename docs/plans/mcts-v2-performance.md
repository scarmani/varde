# MCTS v2 Behavior-Preserving Performance Pass

## Objective

Make Varde's independent terminal-score MCTS fast enough to support the
computer-only n=4 evaluation funnel while preserving its exact seeded search
behavior. MCTS v2 remains ruleset-neutral, uses real legal actions, backs up
terminal game score only, and introduces no rollout or live-game cutoff.

## Verified blocker

- MCTS v1 budget-1 Classic n=4 opening: 1.05 seconds, 343 rollout actions.
- MCTS v1 A-uniform-250: eight games used eight cores for more than 40 minutes
  and produced zero completed records.
- No game outcome was generated or inspected; this is agent-performance
  evidence, not a ruleset result.

## Batches

### 0. Stage isolated performance run

- Branch from merged `main` and open a dedicated PR.
- Record invariants, baseline test count and recovery state.

### 1. Golden behavior fixtures and baseline profile

- Instrument v1 non-invasively to capture chosen action, root child visits and
  value sums, node count and rollout counters.
- Cover six candidates, both policies, two seeds, opening and seeded mid-game
  positions at bounded fixture budgets.
- Profile representative uniform decisions and publish top cumulative costs.

### 2. Hot-path implementation

- Implement direct structural `Game` and `RulesState` cloning without a
  serialization round trip.
- Remove only redundant key/action work proven by the profile.
- Preserve action ordering, RNG consumption, legality, superko and resolution.
- Bump the MCTS format/version/hash so v1 and v2 can never pool evidence.

### 3. Equivalence and timing gates

- Require exact reproduction of all golden fixtures.
- Run the full product suite plus mutation, determinism and save checks.
- Measure fresh n=4 250/1,000-simulation decisions and one complete
  native-standard vs uniform@250 game without inspecting its outcome.
- Gates: decision at 250 <=2s, complete game <=20 minutes, projected 240-game
  policy job <=24 hours. Record honest failures and stop optimization after one
  focused pass if still outside the gates.

### 4. Review and evidence handoff

- Publish timing/equivalence tables and full negative evidence.
- Open a distinct MCTS v2 PR and link it from evidence PR #13.
- Do not merge or refreeze calibration until the user reviews MCTS v2.

## Non-negotiables

- Engine rules and scoring do not change.
- Terminal score is the only backed-up value.
- Every rollout uses real legal actions and reaches a real terminal result.
- No heuristic leaf evaluation, rollout truncation or live cutoff.
- Exact fixed-seed behavior is required across the performance pass.
- MCTS agent version/hash changes even when decisions remain equivalent.
- V1 and v2 results are never pooled.
