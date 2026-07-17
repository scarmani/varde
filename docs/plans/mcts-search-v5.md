# Varde MCTS Search V5

## Objective

Compare three independently switchable research factors—corrected root-only
proof guidance, obligation-reserved progressive unpruning, and redesigned
true-terminal settling—in a full eight-arm factorial. Freeze all corpora and
gates before candidate code, admit at most one deterministic recipe to the
fresh holdout, and calibrate 2,048 versus 4,096 only after every prerequisite
passes.

## Verified starting point

- Stacked base: draft PR #21 at
  `808c31720730fcf23bbc02c4549bd7151bdab3ec`, based on draft PR #20.
- V4 completed five clean 384-decision development screens and selected
  `none-qualified`; no composition, outcome holdout, deep ladder, or paired
  match diagnostic ran.
- V4 solver feasibility is implementation agreement, not independent rescue
  soundness evidence: the solver and verifier duplicate actor-changing rescue
  recursion. V4 positions are regression-only in V5.
- Product baseline: 299 passing tests, changed-file Ruff, Python compilation,
  JavaScript syntax, and CI are green at the stacked base.
- The approved compute envelope is a staged finite run of approximately twelve
  hours. Later stages do not launch when their projected cost exceeds the
  remaining envelope.

## Invariants

- Preserve every V4 code, manifest, result, and report byte-for-byte.
- Do not edit `engine/varde.py`, `server.py`, `web/game.js`, rules, scoring,
  saves, native opponents, public difficulties, or live-game termination.
- Every backed sample reaches `RulesState.terminal` and uses the accepted real
  score. No nonterminal evaluator or heuristic backup is permitted.
- Use the real legal-action API, preserve superko, and never mutate analyzed
  state.
- Version and hash every behavior-changing recipe. Never pool versions.
- Commit each corpus, manifest, seed assignment, and gate before its outcomes
  exist or are inspected.
- New holdout states remain unopened until the declared holdout stage. V4
  states and all V5 development states are ineligible as holdout evidence.
- Research watchdogs classify failed jobs only; they never create backed-up
  values or alter live play.
- Stop immediately at the first failed mandatory gate. The user reviews and
  merges; PRs #20, #21, and this branch remain draft and unmerged.

## Batch 0 — Stage the stacked run

- Create `codex/mcts-search-v5` in a dedicated worktree at exact PR #21 head.
- Record this plan, recovery state, execution log, learnings, baseline, time
  budget, and collision tripwire.
- Push a documentation-only commit and open a draft PR based on
  `codex/mcts-search-v4`.

Gate: exact base, clean preflight, plan/session-only diff, draft and unmerged
PR, no candidate code, no corpus output, and no search process.

## Batch 1 — Freeze independent corpora and oracle

- Freeze a 24-position development screen: 12 roots of width 2–12 and 12 roots
  of width at least 32, evenly split between Toy and Beginner, covering
  capture, defense, rescue, fence, takeover, and ending obligations.
- Freeze a hash-disjoint 24-position holdout with the same strata before any
  candidate implementation. Store its commitments without exposing outcome
  labels to the candidate-development path.
- Include actor-changing and actor-preserving rescues, equivalent proven sets,
  conflicting simultaneous obligations, immediate and reply-durable fences,
  and exact abstention decoys.
- Add a generic bounded exhaustive oracle driven by declarative goal predicates
  and quantifier schedules. It may use real legal transitions but shares no
  rescue, fence, override, or guidance implementation with the solver.
- Store actor seat and color at every proof ply. Hand-audit one positive and
  one decoy trace per obligation family.
- Convert all V4 positions to explicit regression-only inputs.

Gate: exact corpus counts and strata; deterministic regeneration; development,
holdout, and V4 hash separation; 100% oracle agreement with hand-audited
traces; legal, superko-aware, non-mutating transitions; and full validation.
Failure stops before candidate code.

## Batch 2 — Factor A: corrected root-only proof guidance

- Correct rescue closure before recursion. An actor change closes the current
  extension turn and evaluates the declared closure predicate immediately.
  Existential continuations are searched only while the original seat retains
  the turn; opponent actions are traversed only for obligations declaring a
  universal reply.
- Represent immediate fence completion and reply-durable fencing as distinct
  predicates and labels.
- Return complete `proven`, `unknown`, and `disproven` action sets, preserving
  equivalent proven actions.
- Invoke the solver exactly once at the root, reuse root transitions, and
  return `unknown` at the 10,000-node ceiling.
- Apply selection-only progressive bias at the root:
  `status_bias / (1 + action_visits)`, with proven/unknown/disproven mapped to
  `+1/0/-1`. The mapping and coefficient are immutable after this plan.
- Never exclude legal actions and never inject a backed-up value.

Gate: 100% solver/oracle action-set agreement, zero false positive guidance on
decoys, one scan per decision, identical control/guidance traces when every
action is unknown, p95 scan below 100 ms Toy and 400 ms Beginner, exact
determinism, no mutation, and full validation.

## Batch 3 — Factor B: obligation-reserved unpruning

- Retain the V4 exposure schedule
  `min(A, max(1, ceil(2 * sqrt(visits))))`.
- Expose legal administrative actions immediately.
- Reserve one exposed slot per detected urgent obligation before filling the
  remaining prefix with existing rule-fact tiers and semantic seeded ties.
- In proof-guided arms expose the complete proven set. Mandatory actions may
  raise exposure above the base schedule; record the overage.
- Preserve eventual full expansion, deterministic worker-independent order,
  and direction-neutral ties.

Gate: exact base and mandatory exposure counts; all administrative, reserved,
  and proven actions visible; eventual expansion; no fixed directional
preference; median at least three visits per promoted wide-root action at 64;
and full validation. Outcome improvement remains reserved for Batch 5.

## Batch 4 — Factor C: true-terminal settling V2

Let `P` be the number of playable board points.

- Begin settlement eligibility after `ceil(0.5P)` placements.
- Generate legal transitions and event facts once per rollout state.
- Recognize only immediate capture, required extension or closure, a
  sole-liberty defense that leaves the group controlled, and immediate fence
  completion. Generic score and control changes are not progress.
- After eligibility, pass after an opponent pass when legal; otherwise choose
  among event transitions, or pass when none exists.
- At `P` placements finish an open extension or pass regardless of ordinary
  placements.
- Preserve the losing seat's one legal resumption, allow at most one event
  action after it, then settle again.
- Every rollout must reach a real terminal. More than `4P` actions is an
  integrity failure, not a cutoff value.

Gate against the identical frozen workload: 100% accepted-terminal backups;
mean rollout length at least 50% shorter and p95 latency at least 40% lower
than the matched non-settling arm; no rollout above `4P`; admission no more
than five points lower; zero integrity failures; and full validation.

## Batch 5 — Eight-arm development factorial

- Freeze immutable recipe IDs for all combinations of guidance, reserved
  unpruning, and settling: control, each singleton, each two-factor pair, and
  the three-factor combination.
- Run all eight arms on the frozen 24-position development screen at 4/16/64
  simulations, uniform and epsilon-greedy rollouts, and four deterministic
  replicates.
- Require at 64: at least 80% pooled admission, at least 3/4 in every
  position/policy cell, monotonic aggregate results for both policies, and zero
  integrity failures.
- Require reserved unpruning to exceed ordered control by at least ten
  admission points on mandatory wide roots. If ordered control succeeds on
  more than half of hiding cells, the instrument is invalid and the run stops
  before candidate outcomes are used.
- Settling-containing arms must independently pass Batch 4 efficiency and
  no-worse-than-five-point admission gates.
- Rank eligible recipes by high-rung admission, then lower p95 latency, then
  recipe ID. No arm advances merely because it is numerically best.
- Attribution is strict: a component earns no demonstrated value if removing
  it matches or improves the combined arm; a combination trailing either
  constituent records a harmful interaction.

Gate: every factor-specific and pooled gate passes for exactly one
deterministically selected recipe. If none qualify, preserve all negatives and
stop. Only the selected recipe may access the holdout.

## Batch 6 — Fresh holdout, conditional deep tier, and handoff

- Compare only the selected recipe and unchanged control on the fresh holdout
  at 16/64/256, both policies, fixed seeds, eight replicates for rescue and
  fence cells, and four elsewhere.
- Require selected-recipe admission of at least 70% at 64 and 80% at 256;
  monotonic aggregate results; at least 6/8 in every rescue/fence policy cell
  and 3/4 elsewhere; at least a ten-point paired improvement over control;
  p95 below two seconds Toy and five seconds Beginner at 64; zero false
  guidance on decoys; and zero integrity failures.
- Only after that gate, freeze a 12-position subset and run
  256/512/1,024/2,048, two policies, two seeds per cell, single-process.
- Select 2,048 only with passed admission in both policies, at least 85% top-one
  agreement from 1,024, mean top-three Jaccard at least 0.80, and total staged
  runtime within twelve hours.
- Run 4,096 only when 2,048 is monotonic and at least 75% admitted but misses
  stability, and the projected extra run fits the remaining envelope. Select
  it only for at least five admission points or ten stability points while all
  integrity and latency gates pass.
- After a tier is selected, permit one non-claim diagnostic: four paired n=4
  seeds per candidate ruleset against native Standard, both colors, using the
  faster qualifying fallback. Any illegal, crash, or watchdog incomplete stops
  the stage.
- Audit hashes and artifacts; run full local and CI validation; perform
  cumulative review; publish positive and negative evidence; generate the
  Elves report; remove operational session files; leave every PR unmerged.

## Interfaces and evidence

- The complete three-factor tuple, solver/oracle version, guidance mapping,
  exposure policy, and settling policy are part of each immutable agent hash.
- Root telemetry records action status sets, oracle/solver nodes, cache hits,
  invocation count, bias contribution, exposed and mandatory actions,
  exposure overage, event class, settling phase, terminal reason, resumption,
  rollout length, and terminal-backup confirmation.
- Raw output defaults outside the repository. Compact manifests, results, and
  reports are repository-relative, atomic, resumable, deterministic across
  worker counts, and hash-linked to exact source, corpus, and configuration.
- Every run accounts for complete, illegal, mutated, crashed, cancelled,
  watchdog, nonterminal, and tamper-rejected work separately.

## Validation

- Unit-test oracle quantifiers, actor-changing rescue closure, equivalent proof
  sets, immediate/durable fences, decoys, superko, color symmetry, node
  ceilings, and non-mutation.
- Test reserved exposure, mandatory overflow, eventual expansion, seeded
  neutrality, worker ordering, and checkpoint/resume equivalence.
- Test settling eligibility, event classification, pass response, extension
  closure, resumption, true-terminal backups, and `4P` failure accounting.
- Validate manifests, recipe hashes, holdout separation, tamper rejection,
  cancellation, and historical V4 compatibility.
- At every frozen stage run touched-surface tests, changed-file Ruff, Python
  compilation, JavaScript syntax, manifest regeneration, and CI. Run the full
  product suite at entropy checks and final readiness.

## Claim limits

Tactical admission is not strength, strategic depth, balance, beauty, or
ruleset-promise evidence. A small paired diagnostic cannot support those
claims. Failed hypotheses, invalid instruments, and impractical runtimes are
first-class completed results. No V5 candidate is exposed through the browser
or public opponent API.
