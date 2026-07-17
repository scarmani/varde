# MCTS Search V5 Development Factorial

Status: complete mandatory gated stop. No recipe qualified, so no holdout,
deep calibration, or paired ruleset diagnostic was run.

## Frozen run

- Source: `0a1063cfb6f586f1d8bfb22773cfea021e830d15`
- Manifest payload: `c159b4444596ecdc3fae0aa9a267f8a3ffdc66698708738691086495efece912`
- Schedule: 4,608 factorial decisions plus 96 ordered-control instrument
  decisions, 4,704 total
- Corpus: 24 frozen development positions; the independent holdout remained
  sealed
- Arms: every combination of proof guidance, reserved unpruning, and
  Settling V2
- Budgets: 4, 16, and 64 simulations; uniform and epsilon-greedy rollouts;
  four deterministic replicates
- Runtime: 5,133.86 seconds with eight workers

The raw repository-external evidence is at
`~/varde-runs/mcts-search-v5-20260717/development`. Its complete audit was
regenerated from `decisions.jsonl` and the frozen manifest with byte-identical
output.

## Integrity

All 4,704 decisions completed. There were zero illegal actions, mutations,
crashes, nonterminal backups, incomplete rollouts, oracle/solver
disagreements, or false-positive proof-guidance records. The 135,168 expected
simulation backups all came from accepted terminal scores.

Proof guidance performed exactly one scan per guided decision. Its worst
observed scan p95 across guided arms was 19.339 ms on Toy and 88.476 ms on
Beginner, inside the 100/400 ms gates.

## Admission outcome

| Recipe | Guidance | Unpruning | Settling | Hit rate at 64 |
|---|---:|---:|---:|---:|
| `v5-g0-u0-s0` | no | no | no | 27.08% |
| `v5-g0-u0-s1` | no | no | yes | 25.69% |
| `v5-g0-u1-s0` | no | yes | no | 32.64% |
| `v5-g0-u1-s1` | no | yes | yes | 43.06% |
| `v5-g1-u0-s0` | yes | no | no | 31.25% |
| `v5-g1-u0-s1` | yes | no | yes | 30.56% |
| `v5-g1-u1-s0` | yes | yes | no | 47.22% |
| `v5-g1-u1-s1` | yes | yes | yes | 54.17% |

Every arm failed all three mandatory admission conditions:

- pooled 64-simulation admission was below 80%;
- at least one positive position/policy cell was below 3/4; and
- neither rollout policy was monotonically nondecreasing across the full
  ladder for any arm.

The best arm, all three factors together, still failed 18 of its 36 positive
position/policy cells. It therefore cannot advance even though every factor
had positive within-factorial attribution in that particular combination.

## Component findings

### Corrected proof guidance

The proof mechanism passed its correctness and scan-latency feasibility gates,
but guidance alone added only 4.17 admission points over unchanged control at
64 simulations. In combination with reserved unpruning it added 14.58 points.
This is useful directional evidence for interaction, not tactical admission.

### Obligation-reserved unpruning

The registered wide-root instrument passed: reserved unpruning scored 15.91%
against ordered control's 2.27%, a 13.64-point improvement. Mandatory actions
received median 4 visits without guidance and 5 with guidance, exceeding the
three-visit floor.

This validates the exposure mechanism and the instrument, but does not rescue
the architecture: unpruning-only admitted 32.64%, and guidance plus unpruning
admitted 47.22%.

### Settling V2

Settling V2 reduced mean rollout action count by 56.34–57.48% in every matched
comparison and all rollouts stayed within 4P. However, p95 decision latency
became 70.91–101.87% worse rather than 40% better. Fewer actions did not mean
cheaper simulations because event classification and legal-transition work
made each settled action substantially more expensive.

Admission changes were mixed: -1.39 and -0.69 points without unpruning, but
+10.42 and +6.94 points with unpruning. None of the four settling arms passed
the efficiency gate.

## Gated decision

Eligible recipes: none. Selected recipe: none. `holdout_may_run` is false.

Per the frozen plan, the independent holdout, 256/512/1,024/2,048 ladder,
conditional 4,096 tier, and paired ruleset diagnostic were not launched. A
future search redesign requires a new predeclared plan; V5 results must not be
reinterpreted as strength, balance, strategic depth, beauty, or ruleset-promise
evidence.
