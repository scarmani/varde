# Varde MCTS Search V4

## Objective

Compare three separately versioned research architectures—certified tactical
subsearch, progressive unpruning, and true-terminal settling—against the MCTS
V4 `tie-margin` control. Use the burned V3 corpus only for development. Seal an
independent holdout before changing search behavior, admit at most one tactical
component and one efficiency component, and calibrate 2,048 versus 4,096 only
after every prerequisite passes.

## Verified starting point

- Stacked base: draft PR #20 at
  `315443366ddeb499d294f47221e89c2c1dbca4d7`.
- Product baseline: 268 passing tests; Python compilation and JavaScript syntax
  pass. Repository-wide Ruff has ten pre-existing findings, so every changed
  Python file must pass Ruff without broad cleanup.
- Search V3 completed five clean 384-decision runs. High-rung proof rates were
  60.42%, 54.17%, 52.08%, 54.17%, and 41.67%; no candidate was admitted.
- MCTS V4 `tie-margin` is the control. MCTS V5 guided rollout variants remain
  opt-in negative evidence.
- The V3 corpus is a development screen, not unbiased V4 admission evidence.

## Invariants

- Do not edit `engine/varde.py`, `server.py`, `web/game.js`, rules, scoring,
  saves, native opponents, or live-game termination.
- Every backed sample reaches `RulesState.terminal` and uses the accepted real
  score. No native evaluator or nonterminal heuristic leaf value is allowed.
- Use the real legal-action API, preserve superko, and never mutate analyzed
  state.
- Version and hash every behavior-changing recipe. Never pool versions.
- Commit every manifest before its output exists or any outcome is inspected.
- Holdout positions may be consulted only at their predeclared admission stage.
- Research watchdogs classify jobs only; they never alter live games or agent
  rollouts.
- Do not run deep or paired work before admission. The user reviews and merges;
  this branch is never self-merged.

## Batch 0 — Stage the stacked run

- Create a dedicated worktree and branch at the exact PR #20 head.
- Record this plan, recovery state, execution log, learnings, baseline, and
  collision guard.
- Push a documentation-only commit and open a draft PR based on
  `codex/mcts-search-v3`.

Gate: exact base, clean preflight, plan-only diff, draft/unmerged PR, and no
search process.

## Batch 1 — Seal the independent holdout

- Add 24 positive positions: four each for capture, sole-liberty defense,
  rescue continuation, fence completion, takeover, and ending decisions.
- Include two Toy and two Beginner positions per category, at least 12 positions
  derived from reachable seeded play, root width 2–12, and no V3 admission state
  hash.
- Add 12 exact decoys, two per category, where a tactical solver must abstain.
- Certify positives with an independent exhaustive legal-transition verifier.
  Store proof scope, horizon, action values, state hash, and claim limits.
- Freeze deterministic generation seeds, case hashes, corpus hash, and the
  later 16/64/256 schedule before search code changes.

Gate: 24 positives and 12 decoys, exact declared coverage, deterministic
regeneration, disjoint state hashes, legal/non-mutating proof verification, and
full validation. If the required corpus cannot be certified, stop before
Candidate A.

## Batch 2 — Candidate A: certified tactical subsearch

- Add a three-valued solver: `proven`, `disproven`, or `unknown`. It never
  returns a heuristic score.
- Search all legal replies for capture safety, one-reply group survival,
  rescue-turn closure, one-reply fence persistence, takeover, and ending
  decisions.
- Memoize by full rules-state key, obligation, and remaining horizon. At 10,000
  nodes return `unknown`.
- Invoke at the root and newly expanded tree nodes, never during rollouts.
- Override MCTS only when one action is proven and every alternative is
  disproven for that same local obligation.

Feasibility gates: all positive certificates reproduce; zero decoy overrides;
at least 90% positive resolution; p95 invocation below 100 ms Toy and 400 ms
Beginner; zero illegality, mutation, superko bypass, or mislabeled proof.

## Batch 3 — Candidate B: progressive unpruning

- Use V5 one-transition facts only to order expansion: administrative actions,
  extensions, captures, defenses, fence completions, then other actions.
  Seeded semantic hashes order equal tiers.
- Freeze `ordered-control` and `progressive-unpruning` together before outcomes.
- At a node with `v` visits and `A` legal actions expose
  `min(A, max(1, ceil(2 * sqrt(v))))` actions at root and interior nodes.
- UCT over exposed children remains unchanged and every action is eventually
  exposed.

Feasibility gates: exact exposure counts; forced administrative actions never
hidden; 16 actions exposed at 64 visits on natural-width roots; median at least
three visits per exposed child; directional neutrality; and at least a ten-point
high-rung gain over `ordered-control`.

## Batch 4 — Candidate C: true-terminal settling

Let `P` be the number of playable board points.

- Before `P` placements use the declared uniform or epsilon-greedy fallback.
- From `P` through `2P`, pass after an opponent pass; otherwise pass when no
  legal transition immediately captures, protects a one-liberty group,
  continues a required extension, completes a fence, or changes current
  control/score.
- At or after `2P`, pass whenever legal and finish an open extension turn.
- At a two-pass ending, the losing seat resumes once when permitted, receives
  at most one immediate-progress action, then both policies settle again.
- Every simulation must still reach accepted terminal score.

Feasibility gates against the identical MCTS V4 workload: 100% accepted-terminal
backups; mean rollout length reduced at least 50%; p95 decision latency reduced
at least 40%; no rollout above `4P`; proof admission no more than five points
below V4; zero integrity failures.

## Batch 5 — Development admission, composition, and sealed holdout

- Run A, `ordered-control`, B, and C independently on the frozen 384-decision
  V3 development screen at 4/16/64, two fallback policies, four replicates.
- Tactical qualification requires 80% pooled at 64, at least 3/4 in every
  position/policy cell, monotonic aggregate policy ladders, and zero integrity
  failures.
- If A and B qualify, select higher admission, then lower p95, then recipe ID.
- C qualifies only through its efficiency gate. Never combine A and B.
- If one tactical component and C qualify, freeze exactly one combined recipe.
  Otherwise test the qualifying standalone recipe. If none qualify, preserve
  negatives and stop downstream work.
- Consult the sealed 24-position holdout only for that selected recipe at
  16/64/256, two policies, four replicates.

Holdout gate: 80% pooled at 256; 3/4 per cell; at least 70% at 64; monotonic
16→64→256; zero decoy overrides; natural-diagnostic regression no greater than
five points; single-process p95 below two seconds Toy and five seconds Beginner
at 64; zero integrity failures.

## Batch 6 — Conditional deep tier, diagnostic, and handoff

- Only for a holdout-passing recipe, freeze a 12-position subset and run
  256/512/1,024/2,048, two policies, two seeds per cell, single-process.
- Select 2,048 only with passed admission in both policies, at least 85% top-one
  agreement from 1,024, mean top-three Jaccard at least 0.80, and total ladder
  time within 12 hours.
- Run 4,096 only when 2,048 is monotonic and at least 75% admitted but misses
  stability, and the extra run projects within 12 hours. Select it only for at
  least five admission points or ten stability points of gain while every gate
  passes. Otherwise select neither.
- After a tier is selected, permit one non-claim diagnostic: four paired n=4
  seeds per candidate ruleset against native Standard, both colors, using the
  faster qualifying fallback. Any illegal, crash, or watchdog incomplete stops
  the stage.
- Audit every artifact and hash; run full local and CI validation; perform the
  cumulative review; publish positive and negative evidence; generate the Elves
  report; remove operational session files; leave the draft PR unmerged.

## Interfaces and evidence

- Immutable recipe IDs cover control, solver, ordered control, unpruning,
  settling, and at most one composition. The full recipe is part of its hash.
- Telemetry records solver status/nodes/cache hits, exposed/hidden actions,
  widening threshold, settling phase, terminal reason, resumption use, rollout
  length, and terminal-backup confirmation.
- Raw output defaults outside the repository; compact manifests/results are
  repository-relative, atomic, resumable, deterministic across worker counts,
  and hash-linked.
- Unit and harness tests cover solver horizons and decoys, superko, color
  symmetry, takeover/endings/rescue, widening schedules, eventual expansion,
  settling/resumption, true-terminal backups, checkpoint/resume, tamper
  rejection, variant hashes, and historical compatibility.

## Claim limits

Tactical admission is not strength, strategic depth, balance, beauty, or
ruleset-promise evidence. A small paired diagnostic cannot support those claims.
Failed hypotheses and impractical runtimes are first-class completed results.
