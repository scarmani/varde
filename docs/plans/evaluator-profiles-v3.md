# Varde Evaluator Profiles V3 and Quality-Diversity Search

## Mission

Ship legal, recognizably different computer personalities while keeping search
strength independent from style. Balanced must preserve the current seeded
Casual and Standard behavior exactly; Personal must preserve the existing local
learner; curated profiles must be backed by reproducible offline evidence.

## Scope

### In scope

- A named evaluator weight schema and six new color-symmetric measurements.
- Balanced, Raider, Mason, Surveyor, Weaver, and Personal profile semantics.
- Profile-aware seats, APIs, version-1 saves, pie takeover, rationales, and UI.
- Deterministic audit, ablation, MAP-Elites, curation, and evaluation harnesses.
- Packaged, versioned profile catalog with validation evidence.

### Out of scope

- Changes to `engine/cairn.py` or the rules.
- Search depth as part of a profile genome.
- Live-game move or time cutoffs.
- Overwriting a user's Personal model.
- Claims that a curated profile is stronger merely because it is different.

## Batches

### Batch 1: Evaluator parity and V3 measurements

**Tasks**

- Refactor fixed evaluator constants into a named immutable weight map.
- Add bounded, finite, color-symmetric structural measurements for control
  resilience, latent reserves, sky durability, and connection/cut leverage.
- Add transition telemetry for capture initiative and vertical mobility without
  nested move generation.
- Capture seeded decision fixtures before changing evaluator plumbing.

**Acceptance criteria**

- Balanced reproduces every captured Casual and Standard action, point, score,
  and node count across all board sizes plus swap, pass, resumption, and superko.
- Every new measurement is finite, bounded, exactly color-symmetric, and does
  not mutate its input.
- Constructed resilience, reserves, sky, connection/cut, cover, hostile-cover,
  reinforcement, summit, and capture cases pass.
- `engine/cairn.py` has no diff.

**Risk:** evaluator plumbing is a high-fan-out surface where even algebraically
equivalent ordering could change seeded ties.

### Batch 2: Profile model, API, saves, and Personal migration

**Tasks**

- Add a validated versioned profile catalog and profile lookup module.
- Store `profile` on computer seats only; swap full seat identities under pie.
- Normalize legacy `difficulty: "advanced"` to Standard + Personal.
- Add profile fields to `/api/new`, `GET /api/profiles`, public state, and saves.
- Keep the V1/V2 Personal model format and path unchanged.

**Acceptance criteria**

- Unknown or unavailable profiles are rejected; missing profiles default to
  Balanced; human seats never expose a profile.
- Legacy requests and saves load, Advanced migrates to Personal, and version-1
  snapshots remain version 1.
- A zero-weight Personal profile is decision-equivalent to Balanced.
- Profile and deterministic seed travel with the complete seat on takeover.

**Risk:** compatibility normalization must occur exactly once and cannot mutate
or discard user model data.

### Batch 3: Browser profile experience

**Tasks**

- Add one profile selector for human/computer and independent Black/White
  selectors for spectator games.
- Rename the panel to Personal learning and show trained/untrained equivalence.
- Show profile descriptions and profile-aware rationales without raw weights.
- Preserve watch pause, playback speed, animations, save/load, and fullscreen.

**Acceptance criteria**

- Every available profile can be selected in human/computer mode and in either
  spectator seat; invalid combinations cannot be submitted.
- Loaded spectator games start paused and both pie takeover directions preserve
  the selected identities.
- `render_game_to_text`, screenshots, and console inspection are clean for the
  required interaction chains.

**Risk:** asynchronous autoplay must not issue an action for stale seat state
after takeover or load.

### Batch 4: Deterministic MAP-Elites research harness

**Tasks**

- Implement repository-relative, resumable MAP-Elites with explicit output,
  seed, workers, and checkpoint interval.
- Optimize only evaluator weights over engagement, verticality, edge reach,
  and consolidation descriptors using four bins per axis.
- Calibrate with 512 deterministic genomes, evaluate 1,536 archive mutations,
  and freeze a deterministic hall of fame every 128 candidates.
- Persist attempts, games, descriptors, replacements, hashes, and source commit
  atomically; keep the 20N watchdog research-only.

**Acceptance criteria**

- Candidate IDs determine seeds/opponents and results are scheduling-invariant.
- Checkpoint/resume is bit-for-bit equivalent to uninterrupted execution.
- Binning, replacement, mutation, hall-of-fame freezing, cancellation, rejected
  attempts, and incomplete accounting have focused tests.
- Worker-count changes do not change the archive or evidence ledger.

**Risk:** nondeterministic reduction order or checkpoint boundaries could make
the research evidence irreproducible.

### Batch 5: Audit, ablation, optimization, and catalog freeze

**Tasks**

- Generate the 2,000-position deterministic audit with the declared board and
  policy mix, correlations, grouped prediction, ablations, heat maps, action
  rates, captures, and decision latency.
- Run paired development/liberty ablations and use them only to bound mutations.
- Run the initial archive and one refinement if any required profile is absent.
- Select eligible Raider, Mason, Surveyor, and Weaver elites with the declared
  descriptor shifts and separation; omit an unavailable profile rather than
  relaxing its definition.
- Package the catalog's schema, weights, measurements, commit, hashes, and
  validation evidence.

**Acceptance criteria**

- Optimization retains only candidate features that pass symmetry/bounds and
  the correlation-or-prediction rule plus the latency budget.
- Rejected evaluator features remain zero-weight telemetry descriptors.
- Packaged entries reproduce their recorded hashes and descriptor bins.
- No profile is described as stronger based on archive quality alone.

**Risk:** the declared search budget may not discover all four eligible styles;
the honest result is an unavailable catalog entry, not threshold weakening.

### Batch 6: Final gates, browser proof, and documentation

**Tasks**

- Run 100 paired profile-vs-Balanced gates per curated profile, pairwise profile
  matchups, and Intermediate/Full smokes.
- Check descriptor shifts by color and board stratum, effect size, pairwise
  distance, legality, completion, and fresh-position latency.
- Complete the Playwright interaction and visual inspection loop.
- Update README, research documentation, design history, and progress evidence.
- Perform a cumulative regression review and exact no-diff check on rules.

**Acceptance criteria**

- Each shipped non-Balanced curated profile meets the 45% overall, 40% per
  stratum, 35% one-sided paired-bootstrap lower bound, zero-failure strength
  floor and its descriptor-shift/separation gates.
- Standard and Personal p95 stay below 500 ms on Toy and 1.5 s on Full.
- All unit, syntax, API, save/load, research determinism, and browser gates pass.
- `git diff 1da66f7...HEAD -- engine/cairn.py` is empty.

**Risk:** full evidence runs are compute-heavy; incomplete runs are failures,
not license to publish provisional profiles as validated.

## Non-negotiables

- Do not modify `engine/cairn.py` or the game rules.
- Do not add a move or time cutoff to live games.
- Do not overwrite or silently migrate away a user's Personal model.
- Balanced remains behaviorally identical; profiles change style, not depth.
- Never claim strength without a separately predeclared strength gate.
- Do not merge; the user reviews and merges the feature branch.

## Test strategy

- Primary: `CI=true python3 -m pytest engine -q`
- Syntax: `node --check web/game.js` and `python3 -m py_compile engine/*.py research/harness/*.py`
- Research: focused deterministic smoke tests, then declared full audit/archive/gates
- Browser: bundled develop-web-game Playwright client, semantic state,
  screenshots opened for visual inspection, and console-error review
- Performance: fresh-position p95 below 500 ms Toy and 1.5 s Full

## Notes

- Public name is Varde. Existing Cairn modules, save identifiers, preferences,
  model paths, and historical evidence remain for compatibility.
- Curated profiles are immutable browser choices. Personal is the only local
  profile changed by background learning.
- The packaged catalog may mark a profile unavailable if the declared search
  does not find an eligible elite after the one permitted refinement.
