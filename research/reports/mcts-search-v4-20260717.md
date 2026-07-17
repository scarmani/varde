# MCTS Search V4 — Certified Tactics, Unpruning, and Settling

Date: 2026-07-17  
Status: complete negative architecture screen; no recipe selected  
Branch: `codex/mcts-search-v4`  
Stacked base: PR #20 head `315443366ddeb499d294f47221e89c2c1dbca4d7`

## Claim boundary

This run measures bounded local tactical admission and rollout mechanics. It
does not establish playing strength, ruleset balance, strategic depth,
elegance, beauty, or game promise. No product AI, rules, scoring, save format,
browser behavior, or live termination behavior changed.

## Frozen design

The V4 plan and holdout were frozen before candidate implementation. The
holdout contains 24 strict positive certificates—four each for capture,
sole-liberty defense, Breath-run rescue, fence completion, takeover, and ending
decisions—and 12 exact abstention decoys. Each positive category contains two
Toy and two Beginner positions, every root has 2–12 legal actions, and 20 of 24
positives replay from compact legal seeded trajectories. The four takeover
cases are explicitly labeled constructed decision-isolation states.

The common development screen reused V3's 16-position split corpus:

- 10 natural-width diagnostic positions;
- 6 small-root proof-grade admission positions;
- 4/16/64 simulations;
- uniform and epsilon-greedy fallback policies;
- four deterministic replicates per cell;
- 384 decisions per recipe.

Five separate manifests were committed before outcomes. Raw checkpoints and
per-decision JSONL remain outside the repository under
`~/varde-runs/mcts-search-v4-20260717/common/`; compact hash-linked audits are
committed under `research/results/`.

## Implemented candidates

### A. Certified local solver

The solver returns only `proven`, `disproven`, or `unknown`. It memoizes full
rules state, obligation, action, and horizon; stops at 10,000 nodes; and never
returns a heuristic value. It handles one-reply capture safety and defense,
Breath-run closure, one-reply fence durability, takeover, and accepted-ending
decisions. MCTS invokes it at the root and newly expanded nodes and overrides
normal selection only for one proven action with every alternative disproven.

Direct feasibility passed:

- 24/24 positive certificates reproduced;
- 0/12 decoy false overrides;
- zero mutation, illegality, certificate mismatch, or node-limit failure;
- observed p95 43.717 ms on Toy and 257.692 ms on Beginner.

### B. Ordered control and progressive unpruning

Both arms use identical immediate rule-fact order: administrative actions,
extensions, captures, defenses, fence completions, then other actions. Equal
tiers use a semantic seeded hash, not coordinate order. Unpruning exposes
`min(A, max(1, ceil(2 × sqrt(v))))` actions at every root and interior node.

Structural feasibility passed. A natural 54-action root at 64 visits exposed
16 actions, gave a median four visits per exposed child, and left all 38 hidden
actions unvisited. Across 128 seeds, 50 different points won the equal-tier
ordering.

### C. True-terminal settling

The policy retains its fallback before P, uses real immediate-progress
transitions from P to 2P, settles through legal pass/finish actions after 2P,
and gives a losing seat its one legal resumption plus at most one immediate
progress action. Every simulation still reaches `RulesState.terminal` and backs
up the accepted engine score.

Structural feasibility passed: 12/12 test rollouts reached accepted terminals,
used no more than 4P actions, exercised resumption, and did not mutate inputs.

## Common-screen results

| Recipe | High-rung hit rate | Complete admission | Overall p95 latency | Mean rollout actions |
|---|---:|---|---:|---:|
| V4 control | 52.083% | fail | 7,345.942 ms | 52.349 |
| Certified solver | **85.417%** | fail | 8,777.950 ms | 52.428 |
| Ordered control | 54.167% | fail | 7,548.661 ms | 52.162 |
| Progressive unpruning | 60.417% | fail | 6,931.704 ms | 51.496 |
| True-terminal settling | 45.833% | fail | 26,744.833 ms | 54.661 |

All 1,920 decisions completed with zero crashes, illegal actions, mutations, or
incomplete terminal backups.

The solver cleared the pooled 80% and monotonic gates but failed the required
3/4 floor in three high-rung cells:

- Breath-run rescue continuation with uniform rollout: 2/4;
- Gjerde-Go fence completion with uniform rollout: 2/4;
- Gjerde-Go fence completion with epsilon-greedy rollout: 2/4.

Progressive unpruning improved ordered control by 6.25 percentage points, below
the required 10 points, and did not pass pooled or cell admission.

Settling failed all three comparative gates:

- admission was 6.25 points below control, worse than the allowed -5 points;
- mean rollout length increased 4.42% instead of falling at least 50%;
- p95 latency increased 264.08% instead of falling at least 40%.

Its integrity claims remain valid: every backup was accepted-terminal and no
rollout exceeded 4P. The negative is about efficiency and tactical admission.

## Deterministic decision

No tactical component qualified and settling did not qualify. The selection is
therefore `none-qualified`. In accordance with the frozen plan:

- no combined recipe was implemented;
- the sealed holdout was not used for MCTS outcome selection;
- the 256/512/1,024/2,048 ladder was not launched;
- 4,096 was not considered;
- no paired ruleset diagnostic was launched.

Scaling any current candidate to 2,048 or 4,096 would violate the admission
gate and spend compute without resolving the observed obligation failures.

## Interpretation and next research boundary

The strongest result is diagnostic: exact local proofs can make a large pooled
improvement, but the current automatic obligation discovery does not reliably
select rescue and durable-fence obligations, and per-node invocation is too
expensive. Any follow-up should be a new predeclared plan, not an unrecorded V4
tuning pass. The most defensible next hypotheses are:

1. root-only or trigger-sparse certified solving with explicit conflict
   handling when capture, defense, and enclosure obligations coexist;
2. obligation-specific rescue/fence discovery tested on a new independent
   corpus before MCTS integration;
3. a cheaper incremental transition cache so proof work reuses tree expansion
   facts rather than regenerating local replies;
4. alternative widening exponents or tier quotas only after predeclaring a new
   calibration/holdout split;
5. settling triggered by measured absence of score-changing continuations,
   with transition-cost accounting, rather than the current P/2P clock alone.

The V4 holdout remains unspent as an outcome-selection corpus and can be reused
only under a newly frozen architecture-selection plan that does not tune on its
certificates or state hashes.

## Evidence index

- Plan: `docs/plans/mcts-search-v4.md`
- Holdout manifest: `research/manifests/mcts-search-v4-holdout-20260717.json`
- Common manifests: `research/manifests/mcts-search-v4-*-screen-20260717.json`
- Feasibility results: `research/results/mcts-search-v4-*-feasibility-20260717.json`
- Individual audits: `research/results/mcts-search-v4-*-screen-20260717.json`
- Deterministic comparison: `research/results/mcts-search-v4-common-screen-20260717.json`
