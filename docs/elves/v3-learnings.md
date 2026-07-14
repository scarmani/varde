# V3 Run Learnings

## Repo Conventions

- 2026-07-13: Varde is the public name; Cairn module names, save format, browser
  preferences, and `~/.cairn/advanced-model.json` remain compatibility surfaces.
- 2026-07-13: The rules engine is isolated in `engine/cairn.py`; opponent work
  must consume its legality and resolution APIs without editing it.
- 2026-07-13: Profile selection normalizes at the seat boundary. Legacy
  Advanced is Standard + Personal; direct opponent calls retain Advanced only
  as an alias for old research code.

## Validation and Tooling

- 2026-07-13: The clean baseline is 72 pytest cases plus `node --check
  web/game.js` and Python compilation. The web game exposes
  `window.render_game_to_text` for browser verification.
- 2026-07-13: Zero-weight V3 features must have a true evaluator fast path.
  Computing them at every node raised Full Standard latency from roughly 397 ms
  to 1.38 s even though the absolute performance cap still passed.
- 2026-07-13: The bundled web-game client captures the canvas and semantic state;
  use a full-page Playwright capture as the complementary check for controls and
  treat isolated canvas artifacts as unresolved until an immediate reproduction.
- 2026-07-13: Bit-for-bit archive resume requires persisting the unexecuted task
  batch and its frozen hall, not merely the latest archive. Worker results can
  then be reduced strictly in candidate-id order regardless of completion order.

## Product and Domain Invariants

- 2026-07-13: Live games have no operational watchdog. Research and training
  watchdogs report or reject incomplete runs and never become rules.
- 2026-07-13: Balanced style and search difficulty are orthogonal. Personal is
  a learned correction to Balanced and must not be represented as a deeper
  search level.

- 2026-07-14: Archive descriptors are optimizer-side estimates. Raider looked
  sufficiently engaging inside the archive but reversed direction under
  held-out gate games; behavior claims must always be re-measured on held-out
  play before shipping a profile.
- 2026-07-14: Behavioral distinctness and playable strength are independent
  failures. Weaver maximized its descriptor shift (effect 3.58) while scoring
  18.5%; a style that always loses is not a product feature.

## Known Traps

- 2026-07-13: Any refactor of evaluator arithmetic can change deterministic tie
  outcomes; capture exact fixtures before moving constants into a map.
- 2026-07-13: `normalized_features()` is the exact nine-key Personal V2 schema.
  Additional evaluator telemetry belongs in a separate API, not that function.
- 2026-07-13: Performance harnesses must not pass the Personal model into their
  Standard arm. Under the orthogonal interface, Standard + model intentionally
  means Personal rather than an ignored argument.
- 2026-07-13: Full archive and gate runs are evidence jobs, not unit tests. Their
  outputs need explicit paths, source hashes, checkpoints, and honest incomplete
  accounting.
- 2026-07-13: JSON checkpoints sort mapping keys. Schema validation must compare
  key sets rather than insertion order, while evaluator catalog construction can
  retain its stronger ordered-schema check for packaged immutable data.
- 2026-07-14: Pairwise eligibility gates must only compare profiles that passed
  their individual gates; otherwise one failing profile can veto valid ones
  through aggregation (fixed in `8cc09b7`).
- 2026-07-14: Evidence stored under `/tmp` does not survive macOS cleanup.
  Copy raw archives to a durable location and commit a hashed compact summary
  before ending a research cycle.
