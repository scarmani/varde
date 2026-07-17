# MCTS tactical admission results

## Scope and integrity

The frozen [manifest](../research/manifests/mcts-tactical-admission-20260716.json)
committed ten canonical decision positions, both existing rollout policies,
4/16/64 simulations, four deterministic seeds per cell, the acceptable-action
sets, source hashes, and the admission thresholds before any result was read.
The run made 240 decisions and played no paired games.

All 240 decisions completed legally. There were no crashes, pending records,
or input mutations. The compact [audit artifact](../research/results/mcts-tactical-admission-20260716.json)
rebuilds the exact schedule, checks ordered records and provenance, and links
the external raw state, JSONL, and summary by hash. Wall-clock timings are kept
as machine observations and excluded from the deterministic decision hash.

The correctness audit is clean. Tactical admission fails.

## Aggregate result

| Policy | 4 simulations | 16 simulations | 64 simulations |
|---|---:|---:|---:|
| Uniform | 25.0% | 20.0% | 22.5% |
| Current light / epsilon-greedy | 27.5% | 27.5% | 30.0% |

The pooled 64-simulation hit rate is **26.25%**, far below the predeclared 80%
gate. Uniform is not monotonic across the ladder. The light policy rises only
2.5 percentage points from 4 to 64 simulations. Not every high-budget
fixture/policy cell reaches 75%; most wide-root tactical cells remain at zero.

## High-budget decisions

Each cell contains four fixed seeds.

| Position | Uniform @64 | Light @64 | Root actions |
|---|---:|---:|---:|
| Classic immediate capture | 0/4 | 0/4 | 52 |
| Breath immediate capture | 0/4 | 0/4 | 52 |
| Breath sole-liberty defense | 0/4 | 0/4 | 52 |
| Pie takeover | 4/4 | 4/4 | 2 |
| Rosette entombment cap | 0/4 | 0/4 | 49 |
| Breath-run rescue entry | 0/4 | 0/4 | 52 |
| Breath-run rescue continuation | 2/4 | 3/4 | 2 |
| Gjerde fence completion | 0/4 | 0/4 | 68 |
| Gjerde-Go immediate capture | 0/4 | 1/4 | 69 |
| Gjerde-Go score acceptance | 3/4 | 4/4 | 2 |

The agent reliably handles the isolated pie decision and usually accepts a
known favorable score. It is inconsistent even on the two-action rescue-chain
continuation. It does not reliably select any of the natural-width capture,
defense, rescue-entry, entombment, or fence-completion actions.

## What the work telemetry explains

At 64 simulations the wide positions report 65 total nodes: the root plus one
node per simulation. Root widths are 49, 52, 68, or 69. The current UCT expands
an untried root action before revisiting any tried action. Consequently:

- 16 simulations cover only 23–33% of a wide root;
- 64 simulations give every 49/52-action root one sample but only 12–15 total
  revisits, and cover only 93–94% of a 68/69-action root;
- terminal win/draw/loss feedback is extremely coarse: the selected action's
  backed mean is exactly 1.0 in every high-budget wide-root trial; and
- when visits and mean values tie, the current final key prefers the
  lexicographically largest point. The observed high-budget misses cluster on
  positive-rim coordinates, so coordinate ordering is a real search artifact,
  not strategic evidence about edge play.

The light policy shortens high-budget rollouts from a mean 89.2 actions under
uniform to 56.5, but does not supply a useful tactical signal. Under the
eight-process run, median 64-simulation latency was roughly 3.1 seconds for
uniform and 3.0 seconds for light; observed p95 was 7.3 and 8.0 seconds. These
contention-affected timings localize cost and must not be treated as a
single-process product benchmark. Classic uniform rollouts were especially
long: mean 196.6 actions in its high-budget capture fixture, with a maximum of
612.

## Interpretation limits

This is negative **agent-admission** evidence, not negative ruleset evidence.
The run contains no match outcomes and cannot rank Classic, Rosette, Breath,
Breath-run, Gjerde, or Gjerde-Go.

The wide fixtures predeclare locally urgent actions, but they do not prove a
complete-game forced win for every acceptable action. Preserve them as useful
behavior diagnostics. A second admission corpus should add small-root or
exhaustively verified dominance puzzles before its results are called tactical
correctness evidence.

## Decision and next unit

Uniform MCTS@24, the paired light-rollout stage, and all larger match batches
remain blocked. Increasing the same search budget would mostly buy a second
noisy sample for a minority of root actions.

The next bounded unit should:

1. expose per-root-action visits, win/draw/loss counts, terminal margin, and
   rank in research telemetry;
2. split the corpus into dominance-proven admission puzzles and natural-width
   behavior diagnostics;
3. remove coordinate-biased final ties with a seeded position/action hash;
4. compare three separately versioned changes—tie fix only, terminal-margin
   secondary backup, and a minimal rules-layer tactical proposal policy—using
   held-out fixtures before combining them; and
5. freeze paired play only if one version passes the new admission gate and a
   single-process latency check.

Native evaluator values must not be used as MCTS leaf values; that would break
the evaluator-artifact firewall.
