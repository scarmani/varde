# MCTS Search V4 — Learnings

## Carried evidence

- Five V3 agents completed 1,920 decisions without integrity failures but none
  passed tactical admission.
- Near-complete root coverage did not imply tactical competence.
- Terminal margin resolves ties without improving proof admission.
- Myopic tactical rollouts can create strategically incoherent chains of more
  than 3,000 actions.
- Scaling to 2,048 or 4,096 before admission is prohibited and wasteful.
- The V3 corpus is useful development evidence but is burned as an unbiased V4
  holdout.

## Update rule

Append only evidence-backed findings after each batch. Distinguish rule facts,
agent results, performance observations, and any later match diagnostics.
- Small-root reachable positions are plentiful late in seeded Breath,
  Breath-run, and Gjerde trajectories; administrative takeover is inherently
  wide at a real opening, so its small-root holdout cases are explicitly
  synthetic and labeled rather than misrepresented as natural positions.
- A strict override must require exactly one proven action, not merely one or
  more proven actions. Multi-proof capture and durable-fence positions are
  useful decoys because they force correct abstention.
- The V3 fixture set contains 16 records but 15 unique state hashes because its
  diagnostic and admission takeover cases share a state. V4 records both
  counts explicitly and remains disjoint from those 15 hashes.
- Exact local proofs are feasible at the declared horizons: all 36 cases
  completed under the 10,000-node limit, with p95 below the Toy/Beginner gates.
  This establishes implementation feasibility only; automatic obligation
  detection and whole-decision admission remain separate tests.
- Progressive unpruning redistributes a 64-simulation wide root from roughly
  one visit per sampled action to a median of four visits across 16 exposed
  actions. Whether that improves tactical admission by the required ten points
  is an outcome question reserved for the common screen.
- True-terminal settling cleanly enforces phase and resumption semantics, but
  small spot checks were not faster than V4 control. The predeclared common
  workload, not those probes, will decide the efficiency gate.
- The common screen confirms the solver is the only candidate with a large
  pooled tactical gain (85.4%), yet it still misses rescue and fence cells and
  is too slow for the later 64-simulation latency gate. Pooled accuracy cannot
  substitute for the predeclared cell floor.
- Progressive unpruning produces a modest +6.25-point gain, not the required
  +10. True-terminal settling is a clean negative: longer rollouts, much worse
  latency, and lower admission. No composition or scale-up is justified.
