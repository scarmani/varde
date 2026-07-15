# Varde Ruleset Promise Evaluation Program

## Mission

Build a trustworthy, reproducible funnel for selecting one flagship Varde
ruleset. Repair correctness before measurement, keep rule variants and search
agents versioned and independent, use computation to falsify weak designs, and
reserve claims about emergence or beauty for structured human play.

## Non-negotiables

- No comparative Gjerde evidence is admissible until open-boundary scoring is
  repaired and regression-tested.
- Live games receive no research watchdog or action ceiling.
- Existing version-1 saves remain loadable, including archived rulesets.
- Archived and broken rulesets cannot start new public games.
- No strength, balance, depth, elegance, or beauty claim rests on one agent
  family or fewer than 100 games.
- Rules are frozen within an evidence round; one refinement is allowed after a
  declared gate failure.
- The user reviews and merges; this run never merges its own pull request.

## Batches

### 1. Correctness, ruleset registry, and browser/API truth

- Repair fenced-cell scoring at unclaimed exterior lines for both Gjerde
  resolutions and invalidate the old probes.
- Add one immutable, versioned ruleset catalog. Derive compatibility tuples,
  board limits, public availability, and descriptions from it.
- Add `GET /api/rulesets`; populate the browser selector dynamically while
  retaining static fallback options.
- Candidate IDs remain the existing save IDs. Stable evaluation revisions are
  metadata: classic-1.3, rosette-0.1, breath-0.1, breath-run-0.1,
  gjerde-breath-0.1, and gjerde-go-0.1.
- Breath-rescue is a research control. Breath-extend, multi, and extend-run are
  archived; breath-cap is broken. Old saves still load all of them.

### 2. Native ruleset evaluators and tactical admission

- Extend the current evaluator with bounded native terms for each candidate's
  objective and mechanics, without changing Balanced Classic parity.
- Add constructed tactical fixtures proving the native evaluators recognize
  their declared concepts.
- Keep profiles/search difficulty independent from ruleset evaluation.

### 3. Deterministic ruleset-neutral MCTS

- Add a common rules-action layer covering placement, pass, takeover,
  extensions, finish-extension, and resumption.
- Implement seeded UCT MCTS using the real controller and terminal score only,
  with uniform and light epsilon-greedy rollouts and fixed simulation budgets.
- Prove determinism, legality, non-mutation, superko, save compatibility, and
  support for every candidate ruleset and special action.

### 4. Reproducible computational falsification harness

- Add one repository-relative CLI for calibration, health screens, depth
  ladders, paired colors, telemetry, checkpoints, cancellation, and resume.
- Store per-game JSONL plus a hash-pinned compact summary containing rules,
  agent, source, seed, configuration, legality, endings, score, margins,
  swaps, action/motif telemetry, and gate results.
- Extend MAP-Elites only through the existing deterministic infrastructure and
  use it adversarially to seek dominant one-dimensional policies.

### 5. Human-study instruments and product workflow

- Add neutral ruleset briefing sheets, two call-your-shot puzzles per finalist,
  crossover schedules, game logs, post-game surveys, motif prompts, and a
  one-week retention form for 8-12 testers.
- Add local export/import support for human playtest records without external
  services or personal information.
- Browser-test candidate selection, archived save loading, descriptions,
  explanations, spectator play, and telemetry export.

### 6. Bounded evidence, final proof, and handoff

- Run calibration/smoke evidence feasible on the local machine; never fabricate
  the later human panel or multi-night confirmation results.
- Publish negative results and explicit provisional status. Actual aesthetic
  promotion remains blocked until the human protocol is completed.
- Run full unit, syntax, performance, browser, save/load, and deterministic
  resume proof; perform cumulative regression review; deliver a green PR and
  an Elves report without merging.

## Admission gates

- Zero illegal actions, crashes, corrupted saves, or unexplained incomplete
  games; no live termination defect; stagnation endings at most 5%.
- Wipes at most 15%; original-player and post-swap color rates within 40-60%;
  median absolute margin under 15% of scoreable area; swap 25-75%.
- High-budget search beats low-budget search at least 55% on held-out pairs and
  improves monotonically across 250/1000/4000 simulations.
- No one-purpose policy exceeds 60% against the high-budget baseline; at least
  three held-out styles remain distinct and score at least 45%.
- Classic: late caps >=10%, median length <=2.5N, non-wipe play.
- Rosette: at least 30% non-forced entombment positions.
- Breath-run: mutual-squeeze/rescue chains survive native and MCTS play.
- Gjerde: fenced area >=30% and denial-only play does not dominate.
- Gjerde-Go: wipe rate below 15% under native life-and-death evaluation.

## Human promotion gate

Only the best two or three computational survivors enter a counterbalanced
8-12-player study. By game three, local resolution prediction must reach 80%
and misunderstood rules must affect fewer than 20% of games. A finalist needs
two independently rediscovered motifs, median agency/beauty/replay ratings of
at least 5/7, and at least 70% optional-rematch acceptance. Select one flagship
lexicographically: correctness, exploit resistance, depth, readability,
emergence, aesthetics, then rule economy.
