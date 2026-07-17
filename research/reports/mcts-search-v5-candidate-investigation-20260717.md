# Varde MCTS Search V5 candidate investigation

Date: 2026-07-17

Status: diagnostic and proposed preregistration only. No Search V5 candidate
was implemented or run, and no V4 gate was changed after outcomes were known.

## Outcome

The most defensible next experiment is a four-arm factorial comparison of:

1. unchanged V4 control;
2. corrected root-only proof guidance;
3. obligation-reserved progressive unpruning; and
4. their combination.

True-terminal settling should not be included in that comparison. Its V4
failure has a direct implementation-level explanation and requires a separate
redesign feasibility study before it can be combined with anything.

This recommendation does not rehabilitate any failed V4 candidate. It uses the
negative records to define new falsifiable mechanisms and requires a fresh
holdout.

## What the decision records show

### Certified tactical subsearch

The pooled high-rung result, 85.417%, shows that exact root facts can strongly
affect tactical choice. The architecture nevertheless failed its registered
cell floor and was unnecessarily expensive:

- V4 constructed a new solver scan at every expanded node. A 64-simulation
  decision recorded 65 invocations, commonly thousands of solver transitions,
  and policy-specific p95 latency above ten seconds.
- Repeating the automatic scan three times on each of the 16 frozen positions
  produced a median root-only latency of about 7.1 ms. The slowest position was
  the 49-action Rosette root at about 456 ms. This is observational timing, not
  a release gate, but it isolates repeated interior scans as the avoidable
  cost.
- The automatic rescue recursion is semantically unsound when an `extend`
  action closes the extension turn. It continues searching legal extensions
  without first checking that the actor still owns the turn. The independent
  certificate module duplicates the same recursion.
- The small Breath-run continuation fixture exposes the mismatch directly:
  the required `extend:-7,-3` changes the actor and leaves the original anchor
  controlled, but the solver follows the new actor's legal actions and reports
  both root actions disproven.
- The small Gjerde-Go fixture has two immediate fence-completion actions. Its
  admission label accepts either, but the solver asks whether one completed
  fence survives every reply. Neither action proves that stronger predicate.
- The Rosette entombment fixture has several equivalent cap actions. V4 can
  override only when exactly one action is proven, so a proven action set is
  represented as abstention.

The repair is therefore not a larger node budget. It is a sound declarative
obligation model, a set-valued result, and one root scan per decision.

### Progressive unpruning

The registered admission roots had widths from one through eight. At 64 visits
all expected tactical actions were exposed, so the required ten-point delta
mostly tested noisy value allocation rather than wide-root starvation.

The exploratory wide-root records do exercise the intended mechanism. On the
seven diagnostic roots with 49--69 legal actions, at the 64-simulation rung:

| Recipe | Tactical hits | Rate |
|---|---:|---:|
| V4 control | 4/56 | 7.143% |
| Ordered control | 2/56 | 3.571% |
| Progressive unpruning | 12/56 | 21.429% |
| Certified solver | 48/56 | 85.714% |

These positions were diagnostic rather than registered admission evidence, so
the table cannot reverse the V4 failure. It does show that the next widening
test must contain mandatory wide roots. Merely changing the square-root
constant on the observed corpus would be post-hoc tuning.

All expected rescue and fence actions on the failed small-root cells were
already exposed. Widening cannot repair an incorrect obligation predicate or
rollout values by itself.

### True-terminal settling

Settling generated 198,485 `progress` actions across the common screen and made
mean rollouts 4.42% longer. Its p95 decision latency was 264.08% worse than
control. The cause is structural:

- every ordinary placement changes the full control key, so nearly every
  placement is called progress between P and 2P; and
- every settling step generates all legal transitions and recomputes full
  score and control data for each candidate.

The accepted-terminal and 4P integrity properties remain valid. A replacement
must remove vacuous control change from its progress definition, reuse
transition facts, and prove efficiency independently. It should not be hidden
inside a solver/widening composition.

## Proposed Search V5 mechanisms

### Factor A: corrected root-only proof guidance

The solver returns a status for every action and a **set** of proven actions.
It never injects a backed-up value and never suppresses eventual legal-action
exploration.

Required semantic corrections:

- Rescue closure is checked before recursion. If the action changes the acting
  seat, the extension turn is closed and the declared closure predicate is
  evaluated immediately. If the seat remains the same, only that seat's legal
  continuations are existential. An actor change is never traversed as a
  helpful continuation unless the declared obligation explicitly includes a
  universal opponent reply.
- Immediate fence completion and reply-durable fencing are separate
  obligations with separate labels. A fixture cannot use one as the oracle for
  the other.
- Equivalent proven actions remain a set. Guidance promotes all of them rather
  than treating multiplicity as failure.
- Capture opportunities are not assumed globally mandatory. Proof status is
  root guidance that decays with visits, not a game-theoretic override.
- The root's already generated legal transitions and rule facts are reused.
  Interior nodes do not invoke the local solver in V5.

The initial guidance rule should be frozen before results. A minimal option is
progressive bias: add `status_bias / (1 + action_visits)` to root UCT, where
proven, unknown, and disproven map to `+1`, `0`, and `-1`. The bias affects
selection only; all backed-up results remain accepted-terminal game scores.
The coefficient and mapping must not be tuned on the development outcomes.

### Factor B: obligation-reserved progressive unpruning

Keep the V4 exposure schedule as the control schedule. Change only membership
of the exposed prefix:

- expose forced administrative actions immediately;
- reserve an exposed slot for each distinct detected urgent obligation before
  filling remaining slots by the existing rule-fact tiers and semantic hash;
- in the combined arm, place the full proven set in reserved slots;
- preserve eventual full expansion and direction-neutral deterministic ties.

This tests whether widening fails because tactical classes compete for a
single prefix, without tuning the growth constant. A separate ordered-control
arm remains necessary to attribute gains to visit-gated exposure rather than
action ordering.

### Combination rule

Run the two factors as a factorial, not as a sequence of opportunistic patches:

| Arm | Root proof guidance | Reserved unpruning |
|---|---|---|
| Control | no | no |
| Guidance | yes | no |
| Unpruning | no | yes |
| Combined | yes | yes |

Predeclare the attribution:

- if Combined does not exceed Guidance, widening adds no demonstrated value;
- if Combined does not exceed Unpruning, solver guidance adds no demonstrated
  value;
- if Combined trails either standalone arm, the interaction is harmful;
- no arm advances merely because it is numerically best.

Proof-number MCTS is a later option, not the first repair. Its proof/disproof
selection machinery is attractive after obligation soundness exists, but V4
does not yet justify embedding local claims deeper in the tree. Implicit
minimax backups are also deferred because they would reintroduce a nonterminal
evaluator before the evaluator-artifact firewall has validated one.

## Preregistered evidence design

### Phase 0: oracle and corpus freeze

Before candidate implementation:

1. Convert the V4 corpus to regression-only status.
2. Freeze a new development corpus and a hash-separated untouched holdout.
3. Include narrow roots for obligation semantics and wide roots of at least 32
   actions for expansion behavior.
4. Include actor-changing and actor-preserving rescue closures, equivalent
   proven sets, conflicting simultaneous obligations, durable and merely
   immediate fences, and abstention decoys.
5. Use a generic bounded exhaustive oracle parameterized by an explicit goal
   predicate and quantifier schedule. It may use the real legal transition API
   but must share no rescue, fence, or override implementation with the solver.
6. Store actor seat/color at every proof ply and hand-audit at least one proof
   and one decoy per obligation family.

The old failed cells are regressions, not holdout positions.

### Development gates

All must pass before the holdout is opened:

- 100% solver/oracle agreement, including action-status sets, on the labeled
  development corpus;
- zero false positive guidance on decoys;
- exactly one solver invocation per decision;
- root state unchanged, every action legal, and superko preserved;
- solver-guidance traces identical to control when every action is `unknown`;
- common-screen p95 no greater than 1.05 times control;
- on mandatory wide roots, median visits per promoted action at least three and
  at least ten percentage points more tactical admission than ordered control;
- no mandatory narrow-root cell below 3/4 at the high rung;
- nondecreasing pooled admission for both rollout policies.

If ordered control succeeds on more than half of the wide-root hiding cells,
the instrument has not isolated starvation and must be replaced before any
candidate outcome is examined.

### Fresh holdout gates

Use the same four arms, 16/64/256 simulations, both fallback policies, and
fixed seeds. Use eight replicates for rescue and fence cells and four elsewhere
to reduce the one-result jump from 2/4 to 3/4.

An arm advances only with:

- at least 80% pooled tactical admission at 256;
- at least 70% already at 64 and monotonic aggregate results;
- at least 6/8 in every rescue/fence policy cell and 3/4 elsewhere;
- at least a five-decision improvement over control in a predeclared 48-cell
  high-rung comparison block;
- no diagnostic regression greater than five percentage points;
- p95 at most 1.05 times control;
- zero false solver guidance on decoys;
- zero illegal actions, mutations, crashes, incomplete rollouts, nonterminal
  backups, or determinism failures.

Only a holdout-passing arm may enter a new 256/512/1,024/2,048 calibration
ladder. The V4 `none-qualified` result remains unchanged, and no 4,096 run is
authorized by this investigation.

## Separate settling V2 feasibility study

Settling should be revisited only after the factorial, with no tactical outcome
claim. A predeclared V2 should:

- define immediate progress only as capture, required extension closure,
  demonstrated sole-liberty protection, or a declared fence event;
- remove generic score/control change from the progress predicate;
- reuse one legal-transition generation per state and count full-score/control
  calls;
- pass immediately after an opponent pass when no mandatory administrative
  action intervenes;
- require 100% accepted-terminal backups, at least 50% shorter mean rollouts,
  at least 40% lower p95 latency, no action beyond 4P, and no more than a
  five-point admission loss against control.

Only after that standalone gate should settling be tested with the selected
tactical architecture.

## Claim limits

This investigation supports a next experiment, not a stronger agent. It makes
no claim about match strength, ruleset balance, strategic depth, elegance, or
the appropriate 2,048/4,096 tier. The draft V4 pull request remains unmerged.

## Primary references

- Chaslot et al., [Progressive Strategies for Monte-Carlo Tree
  Search](https://doi.org/10.1142/S1793005708001094), introduces progressive
  bias and progressive unpruning as separate, combinable mechanisms.
- Winands, Bjornsson, and Saito, [Monte-Carlo Tree Search
  Solver](https://doi.org/10.1007/978-3-540-87608-3_3), motivates retaining
  explicit solved information in simulation search.
- Doe et al., [Combining Monte-Carlo Tree Search with Proof-Number
  Search](https://arxiv.org/abs/2206.03965), is the relevant later path if
  sound local facts justify proof-number-guided selection.
- Lanctot et al., [MCTS with Heuristic Evaluations using Implicit Minimax
  Backups](https://arxiv.org/abs/1406.0486), keeps heuristic and rollout values
  separate; Varde defers this until it has an independently validated
  nonterminal evaluator.
