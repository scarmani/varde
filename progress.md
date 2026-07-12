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

## Computer opponent implementation

- Approved plan: local Casual and Standard rule-aware opponents, color choice,
  optional rationales, pie-rule handling, and computer-game save/load support.
- Opponent engine implementation in progress; MCTS remains intentionally deferred.
- Opponent engine and server integration now pass focused tests: automatic computer
  opening, turn locking, swap ownership, rationale visibility, and compatible saves.
- Browser controls and automatic computer-turn sequencing implemented; visual and
  end-to-end interaction verification remains.
- The 8N boundary remains a self-play watchdog only. A temporary 6N forced-pass
  policy was rejected because full-superko Cairn already terminates mathematically;
  long bot games must be measured honestly, not shortened by an extra rule.
- Browser verification completed for both human colors, human and computer swap
  paths, thinking-state locking, rationales, capture animation, automatic
  resumption, compatible save/load, and unchanged hotseat play.
- Bot audit: Casual 20/20 ended below 8N; Standard 20/20 ended naturally, with
  19 below 8N and one at 489 turns. Decision latency stayed inside both budgets.
