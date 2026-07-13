# Advanced V2 Run Learnings

## Repo Conventions

- Extend the dependency-free Python modules and unittest/pytest style already used under `engine/`.
- Keep all AI and match orchestration outside `engine/cairn.py`; it is the rules reference.

## Validation and Tooling

- Baseline is 60 passing pytest cases plus `node --check web/game.js`.
- Browser verification must use the bundled develop-web-game client and inspect its screenshot/state output.

## Product and Domain Invariants

- Full superko makes the rules finite; watchdogs are operational evidence boundaries only.
- Pie takeover swaps complete seat identities, including difficulty and seed.
- Either player may demand the first post-ending resumption, regardless of whose turn follows the second pass.

## Known Traps

- Claude's research harness hardcodes `/tmp/c2` and `/tmp/lab`; it is not reproducible in-place yet.
- The research evaluation only asked the current side about resumption, so its relative results are directional, not release evidence.
- The corrected V2 learner improved Toy results directionally but generalized poorly to Beginner (45%); identical evaluator terms plus three structural features are still insufficient for a strength claim.
- Full games can be long even under bounded search (1,701 actions observed), so larger-board smoke must stay small and must not be converted into a gameplay cutoff.
- Custom Chromium launches need SwiftShader flags in this environment; otherwise screenshots can contain black GPU artifacts even with correct semantic state and no console error.
