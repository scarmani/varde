Original prompt: yes to all in best order proceed and execute according to your recommendation

## 2026-07-12

- Preserved the imported prototype as Git baseline `9e14357`.
- Stabilization in progress: rules/engine truth, capture-wave telemetry, serialization,
  player identity, reproducible tests, then a locally playable web interface.
- Engine now rejects an opening pass, models swap ownership, round-trips versioned
  snapshots, and records capture cascades wave by wave.
- Rules prose has been rewritten to incorporate the collar and peel findings directly.
- Added a dependency-free local HTTP API and responsive canvas hotseat client.
- First browser pass found and fixed horizontal board centering; opening state exposed
  all 54 legal n=3 points with no console errors.
- Browser flow verified opening placement, pie-rule takeover, two-pass ending,
  resumption, save/load across board sizes, fullscreen, and capture highlighting.
  Full-flow and capture screenshots showed no console errors.
- Instrumented 100-game n=3 baselines completed for random, greedy, and 15%
  epsilon-greedy policies; exact results are recorded in README and design history.
- Final verification: 35 unittest and pytest cases pass; editable installation works;
  final Playwright opening-move state and screenshot have no console errors.

## TODO

- Human playtest the n=3 client and record usability/strategy observations.
- After human validation, add MCTS for the summit and saturation experiments.
