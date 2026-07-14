# Corrected Search and Advanced Learning V2

## Mission

Correct the bounded computer search and two-computer ending protocol, then train
and evaluate a versioned nine-feature Advanced model against that corrected
Standard baseline. Keep `engine/varde.py` unchanged and retain local-only play.

## Batches

### Batch 1: Search and ending correctness

- Score pass in the two-ply reply scan and pie-rule reply evaluation.
- Include takeover as a legal reply to a computer Black opening.
- Replace one global ending decision with persisted seat-identity acceptances.
- Preserve hotseat, human/computer, save/load, superko, and live no-cutoff behavior.

Acceptance: focused and full tests pass; both watch seats receive the first
resumption opportunity; existing version-1 saves load.

### Batch 2: Learning V2 and deterministic continuation

- Add bounded height, rim, and group-consolidation features.
- Add margin labels, later-weighted sampling, learner-only exploration, and the
  two-stage learning-rate schedule.
- Persist model format 2, migrate format 1, and track global attempts separately
  from completed games.
- Make batch partitioning invariant and prevent repeated games across batches.

Acceptance: migration, symmetry, bounds, persistence, cancellation, reset,
continuation, determinism, and active-game isolation tests pass.

### Batch 3: Reproducible research and strength gate

- Repair the research harness to use repository-relative imports and CLI paths.
- Preserve historical reports/models with source/config metadata; integrate the
  search fix and remove the obsolete patch artifact.
- Train one fresh 200-game V2 model and run the 100-pair Toy/Beginner held-out gate.
- Run Intermediate/Full smoke and fresh-position performance checks.

Acceptance: all runs are reproducible, incomplete games fail the gate, and no
strength claim is made unless every predeclared threshold passes.

### Batch 4: Browser, documentation, and final review

- Expose migration/attempt information without breaking training API requests.
- Browser-test watch resumption, migrated status, continuation, save/load, and
  console state with the provided Playwright client.
- Update README, research report, design history, and progress log.
- Perform a cumulative direct review because this repository has no remote/PR.

Acceptance: unit suite, JavaScript check, browser state/screenshots, and final
cumulative review are clean on the current branch tip.

## Non-Negotiables

- Do not modify `engine/varde.py`.
- Do not enforce a move cutoff in live games.
- Do not silently discard or overwrite a version-1 user model.
- Do not claim Advanced is stronger unless the paired gate passes.
- Do not merge; leave a committed local feature branch for user review.

## Test Strategy

- Primary: `python3 -m pytest -q`
- JavaScript: `node --check web/game.js`
- Browser: bundled `develop-web-game` Playwright client plus targeted interaction chains
- Gate: 100 paired held-out seeds, 75 Toy and 25 Beginner; Advanced plays both colors
- Performance: p95 below 500 ms Toy and 1.5 s Full

## Gate

A stronger claim requires overall score at least 60%, each board stratum above
50%, one-sided 95% paired-bootstrap lower bound above 50%, positive average
margin, and zero illegal, crashed, or incomplete games. Operational watchdogs
never become game rules.
