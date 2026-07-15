# Ruleset Evaluation Learnings

## Durable truths

- Passing rules-engine tests proves implementation conformance, not game depth.
- A ruleset's evaluator is part of the experimental condition. Cross-ruleset
  evaluators may falsify obvious failures but cannot support comparative claims.
- Gjerde edge scoring must treat an unclaimed exterior line as an open boundary;
  otherwise one claimed edge can incorrectly award the whole cell region.
- Human beauty evidence requires actual human records. The repository may ship
  instruments and a blocked promotion gate, never invented panel results.

## Validation conventions

- Primary gates: `CI=true python3 -m pytest engine -q`,
  `python3 -m py_compile engine/*.py research/harness/*.py`, and
  `node --check web/game.js`.
- Browser changes use the installed develop-web-game Playwright client,
  `window.render_game_to_text`, opened screenshots, and console inspection.

## Computational falsification harness

- Paired seeds belong to candidate, size, matchup, and pair identity; ordered
  reduction makes process scheduling irrelevant to canonical output. Completed
  resumed runs remain byte-identical when worker count and checkpoints differ.
- Configured agents are not evidence. Headline readiness requires completed
  100-pair native/MCTS strata for both rollout policies, two completed adjacent
  budget comparisons per policy, and passing health gates.
- Batch 4 validation reaches 193 tests. Actual native and MCTS process-worker
  smokes complete legally and keep promotion blocked; research-watchdog
  incompletes and cancellations remain recorded rather than becoming results.
