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

## Expanded boards, spectator mode, and learning AI

- Approved plan recorded in the task: Toy/Beginner/Intermediate/Full boards,
  proportional rendering at the former n=5 ratio, 10% larger lattice, two-computer
  playback, and a persistent Advanced linear evaluator trained by background self-play.
- Added n=6/216-point support and exact renamed labels. Canvas geometry now derives
  stones, glyphs, rings, line widths, fonts, and hit targets from projected spacing.
- Replaced one computer owner with two serializable seats. Complete identities,
  difficulty, and deterministic seed move together under pie-rule takeover; legacy
  version-1 saves with a top-level `computer` section still load.
- Added Advanced search, normalized color-symmetric features, atomic model persistence,
  background training/cancel/reset service, and training-only 20N watchdog. Live games
  still have no turn cutoff.
- Added paused spectator Play/Pause/Step and 1200/500/100 ms speed controls plus
  independent Black/White difficulty selectors. Loaded spectator saves start paused.
- Final automated checkpoint: 60 pytest cases and `node --check web/game.js` pass.
  Playwright covered all four board sizes, paused load, exact Step, Play/Pause and
  speed, both human colors, takeover, hit-testing, training/cancel/reset, fullscreen,
  and a two-wave Fast capture in 155 ms with no console errors.
- Fresh-position p95 was 26/44 ms on Toy and 411/682 ms on Full for
  Standard/Advanced. Eight deterministic training games persisted finite weights;
  a small color-alternated held-out sample was 3 wins and 5 losses versus Standard,
  so no strength improvement is claimed.
- Final evaluator audit separated strict skies from capped ordinary empty-point
  liberties, preventing a real sky from being counted twice while retaining its
  group-life and dedicated sky-weight effects.

## Corrected search and Advanced Learning V2

- Corrected every shared two-ply path to score an opponent pass, including the
  pie-rule value, and added legal White takeover as a Black-opening reply.
- Replaced the global computer-ending decision with persisted per-seat
  acceptances. In spectator games the first accepting AI no longer prevents the
  other seat from using the rules' one permitted resumption.
- Added the bounded height, rim, and group-consolidation features and migrated
  the model format to nine-weight V2 without deleting legacy six-weight models.
- Made training use margin targets, time-weighted samples, learner-only opening
  exploration, a global attempt ordinal, and a fixed master seed. Split batches
  are reproducibly equivalent to a single batch and discarded attempts still
  advance the cursor.
- Replaced the temporary-path research scripts with repository-relative,
  parameterized training, paired evaluation, benchmark, and larger-board smoke
  harnesses. Historical checkpoints are clearly isolated from production.

## Evaluator Profiles V3 and quality-diversity search

- Began the approved finite implementation on `feat/evaluator-profiles-v3`.
- Baseline is clean at `1da66f7`: 72 pytest cases, JavaScript syntax, and Python
  compilation pass; `engine/cairn.py` is protected as an explicit no-change surface.
- Decomposed the run into evaluator parity/features, profile compatibility/API,
  browser experience, deterministic MAP-Elites, evidence/curation, and final gates.
- A bounded Fable goal cycle reinforced parity-first architecture. Its unrelated
  direct-to-main suggestion was rejected; product work remains on the owned branch.
- Batch 1 complete: Balanced now uses a named immutable weight map while exact
  seeded actions, scores, and node counts remain unchanged on all board sizes and
  special actions. Ten V3 structural/transition measurements are bounded,
  color-symmetric, non-mutating, and reuse supplied transitions without nested scans.
- A first implementation paid V3 telemetry cost at every node; focused latency
  evidence caught it and the disabled fast path restored roughly 28 ms Toy / 397 ms
  Full Standard decisions. The Personal nine-feature schema remains exact.
- Batch 2 complete: computer seats now store independent Casual/Standard
  difficulty and evaluator profile, legacy Advanced normalizes to Standard +
  Personal, version-1 saves and complete-seat takeover remain compatible, and
  `GET /api/profiles` exposes catalog availability without raw weights.
- The packaged catalog starts with Balanced and Personal available; Raider,
  Mason, Surveyor, and Weaver remain explicitly unavailable until the declared
  archive/evidence run freezes eligible weights. No provisional style is shipped
  by weakening its descriptor gate.
- Batch 3 complete: dynamic browser selectors separate Casual/Standard search
  from profile style, independent spectator choices remain paused, unavailable
  archive profiles are visibly disabled, and Personal learning reports untrained
  equivalence or its local training count.
- Browser evidence covers actual selector submission, both pie-rule takeover
  directions, automatic continuation, legacy Advanced migration, profile-aware
  rationales without raw score, semantic state, opened screenshots, and zero
  console errors.
- Batch 4 complete: the repository-relative four-axis MAP-Elites harness uses
  candidate-owned random streams, 128-candidate frozen halls, strict in-order
  reduction, and atomic checkpoints containing pending work and complete evidence.
- Ten harness tests prove deterministic mutation/binning/replacement, hall
  selection, byte-identical interruption/resume across worker counts,
  cancellation, tamper detection, and incomplete accounting. A real two-process
  smoke completed 4 candidates / 32 games with no illegal or incomplete result.
