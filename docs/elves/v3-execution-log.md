# V3 Execution Log

## Run Digest

- **Last updated:** 2026-07-14 00:55 CDT
- **Current phase:** Complete — awaiting user PR review
- **Active batch:** none
- **Last completed batch:** Batch 6 — Catalog freeze, final gates, and browser proof
- **Next exact batch:** none; do not merge PR #1 without user review
- **Active PR:** #1
- **Docs promoted this run:** `docs/plans/evaluator-profiles-v3.md`
- **Latest Elves Report:** not generated yet

## 2026-07-14 00:55 CDT

**Batch:** 5+6 — Audit, ablation, optimization, curation, gates, catalog freeze

**Contract status:** all criteria met; two of four curated styles shipped

**What changed:**

- Audit: 2,000 deterministic positions accepted five transition candidates
  (capturing moves, max capture, covers, hostile covers, summits) and kept five
  structural candidates as zero-weight telemetry after latency gates.
- Ablation: 180 pairs confirmed development (41.67%) and liberty (16.67%)
  contribute real strength; both-disabled scored 0.42%. Balanced unchanged.
- MAP-Elites: 4,096 candidates / 32,768 games / 219 occupied cells; six
  candidates rejected on watchdog-incomplete rollouts; one permitted
  refinement consumed. State hash `38136c95…3422`.
- Gates (100 paired seeds each, source `8cc09b7`): Mason 76.75% overall with
  verticality effect 1.264 — qualified. Surveyor 51.75% with edge-reach effect
  3.008 — qualified. Raider engagement moved the wrong way (−0.687) — omitted.
  Weaver 18.50% overall — omitted. Mason–Surveyor descriptor distance 3.132.
- Smoke: 464/464 games complete across all matchups, Intermediate, and Full.
- Catalog frozen at commit `84771d4` with stage hashes, availability reasons,
  and `strength_claim: false`; compact evidence summary committed at
  `research/results/v3-final-evidence-summary.json`; raw archive retained
  externally (sha256 `c0cd56f1…3c81`).
- Final-head benchmark: all eight profile/board configurations under limits
  (worst: untrained Personal Full p95 1,213 ms < 1,500 ms), recorded in
  `research/results/v3-final-benchmark.json`.
- Final browser pass on the frozen catalog: human vs Mason and vs Surveyor,
  independent spectator seats, human and AI pie takeover with complete seat
  exchange, paused spectator load, step/play/speed controls, capture-wave
  animation, save/load with legacy Advanced migration, trained and untrained
  Personal displays, profile-aware rationales, zero console errors. Fullscreen
  was verified by code and the earlier pass; the embedded test pane denies the
  Fullscreen API by policy.

**Review findings:**

- Fixed earlier: gate availability aggregation no longer lets an individually
  failing profile veto valid profiles through pairwise checks (`8cc09b7`).

**Regression attestation:**

- `engine/cairn.py` diff against `1da66f7` remains empty.
- Test baseline: 117 -> 118 with the new acceptance/rejection server test.
- Confidence: HIGH. Every shipped number traces to a hashed evidence file.

## 2026-07-13 12:16 CDT

**Batch:** 4 — Deterministic MAP-Elites research harness

**Contract status:** all criteria met

**Timing:** Implement 7m | Validate 4m | Review 1m | Total 12m

**What changed:**

- `research/harness/map_elites_v3.py`: repository-relative four-axis archive
  search with candidate-owned random streams, calibration, deterministic
  mutation, fixed paired schedules, frozen hall-of-fame batches, strict in-order
  reduction, atomic pending-task checkpoints, cancellation, and resume.
- `engine/test_quality_diversity.py`: archive primitives, worker scheduling,
  interruption, tamper, incomplete-result, and real-rollout coverage.
- `research/README.md`: exact initial and resume commands plus evidence semantics.

**Commands and results:**

- `CI=true python3 -m pytest engine -q` — PASS, 101/101.
- `python3 -m py_compile engine/*.py research/harness/*.py` and
  `node --check web/game.js` — PASS.
- Synthetic uninterrupted vs interrupted/resumed run — byte-identical final
  `state.json` with worker counts 1 then 4 and checkpoint interval 3.
- Real two-process Casual smoke — 4 candidates, 32 games, 0 illegal/incomplete,
  4 occupied archive cells; immediate completed-state resume preserved exact
  SHA-256 `6a0d769f01fd462d3581b80e9c0c550b7dfa7d0b0cd2f491d8a2f570960a84d5`.

**Review findings:**

- Fixed: sorted JSON genome keys originally conflicted with insertion-order
  validation after resume; checkpoint schemas now compare exact key sets.
- Fixed: exact Balanced research genomes now use the literal immutable
  `BALANCED_WEIGHTS` mapping and therefore the parity-locked live search path.
- Confirmed: search difficulty is configuration, never a genome gene; the 20N
  watchdog only rejects and records research attempts.

**Regression attestation:**

- Cumulative diff: 21 files, +3540/-97 including operational docs.
- Shared surfaces: none; the harness consumes public Game/opponent APIs and
  writes only to its explicit out-of-repository directory.
- Test baseline: 72 -> 101, delta +29, no removals or skips.
- Confidence: HIGH. Unit, real-process, real-game, resume, and canonical hash
  evidence cover the principal determinism and safety risks.

**Commit:** `79c5c6214bb01e9763d790eec0746dfba3a586ec`

**Rollback tag:** `elves/v3-pre-batch-4`

**Next:** Batch 5 audit, ablations, full archive search, and gated catalog freeze.

## 2026-07-13 12:03 CDT

**Batch:** 3 — Browser profile experience

**Contract status:** all criteria met

**Timing:** Implement 3m | Validate 4m | Review 1m | Total 8m

**What changed:**

- `web/index.html` / `web/game.js` / `web/styles.css`: dynamic profile selectors,
  disabled unavailable entries, independent watch profiles, descriptions,
  Personal learning labels, and semantic profile state.
- `engine/server.py` / `engine/opponent.py`: attach profile identity to a decision,
  prefix rationale text, and remove raw evaluator score from public state.

**Commands and results:**

- `CI=true python3 -m pytest engine -q` — PASS, 91/91.
- `node --check web/game.js`, Python compile, and diff checks — PASS.
- Bundled Playwright client — paused Step, actual selector state, human takeover
  with automatic continuation, computer takeover, and legacy Advanced load all pass.
- Full-page Playwright — one-computer Personal and independent watch selectors,
  four disabled unavailable entries, paused watch, and no console errors.
- Screenshots opened: profile controls and board layout clean at 1280x1000;
  canvas captures clean after one isolated capture artifact did not reproduce.

**Review findings:**

- Fixed: public decision still exposed evaluator score; server now strips it
  while direct research decisions retain internal score data.
- Fixed: BotDecision's new profile field moved to the end to preserve positional
  compatibility for external constructors.
- Investigated: one bundled canvas capture contained black quadrants. Immediate
  bundled and full-page reproductions were clean with identical semantic geometry,
  establishing an isolated capture artifact rather than a render defect.

**Docs:** UI labels are self-documenting; README remains deferred until frozen
profile availability is known in Batch 5.

**Regression attestation:**

- Cumulative diff: 18 files, +2280/-97 including operational docs.
- Shared surfaces: public decision payload and browser initialization. Existing
  scheduling, capture animation, playback speed, and load logic remain intact.
- Test baseline: 72 -> 91, delta +19, no removals or skips.
- Confidence: HIGH. Unit/API proof is paired with semantic and visual browser
  evidence for both ownership paths, migration, selector availability, and pause.

**Commit:** `9c0085ebf47e4989a75466a225a4a457cbe258a6`

**Rollback tag:** `elves/v3-pre-batch-3`

**Next:** three-batch entropy check, then Batch 4 deterministic MAP-Elites.

## 2026-07-13 12:06 CDT

**Three-batch entropy check:** clean

- Reviewed the cumulative 18-file diff for duplicated authorities, naming drift,
  avoidable abstractions, and shared-surface regressions.
- `engine/profiles.py` remains the sole catalog authority and
  `engine/opponent.py` remains the sole evaluator/search authority.
- Legacy `advanced` references are confined to explicit compatibility tests,
  historical V2 research artifacts, and the unchanged Personal model path.
- README terminology is intentionally deferred until Batch 5 determines which
  curated profiles satisfy their immutable availability gates.
- `git diff --check 1da66f7...HEAD` passed and `engine/cairn.py` is absent from
  the cumulative changed-file list.

**Decision:** no entropy repair is warranted; proceed to Batch 4.

## 2026-07-13 11:55 CDT

**Batch:** 2 — Profile model, API, saves, and Personal migration

**Contract status:** all criteria met

**Timing:** Implement 6m | Validate 4m | Review 2m | Total 12m

**What changed:**

- `engine/profiles.py`: packaged V3 catalog, immutable lookups, validation,
  public metadata, unavailable-profile fail-closed behavior, and legacy normalization.
- `engine/server.py`: profile-aware computer seats, requests, public state,
  version-1 saves, and `GET /api/profiles`.
- `engine/opponent.py`: independent style weights with a literal historical
  Balanced/Personal hot path and transition scoring for non-Balanced profiles.
- `engine/learning.py`: learner now explicitly means Standard search + Personal
  model while the fixed opponent receives no learned correction.

**Commands and results:**

- `CI=true python3 -m pytest engine -q` — PASS, 90/90.
- Editable install/import — PASS; catalog version/hash accessible.
- Live HTTP smoke — profiles 200, Advanced migration 200, independent watch
  profiles 200, unavailable Raider 400 with explicit error.
- Exact-head A/B and corrected benchmark — Standard about 27/398 ms,
  Personal about 55/752 ms on Toy/Full.
- JavaScript/Python syntax and rules no-diff checks — PASS.

**Review findings:**

- Fixed: generic profile plumbing appeared to double Standard latency. Exact
  A/B showed the old benchmark supplied the model to both arms; the new API
  correctly interpreted Standard + model as Personal. Benchmark now supplies
  the model only to its Personal arm.
- Fixed: preserved a literal Balanced/Personal search path so style branching
  cannot tax the default evaluator at each reply node.
- Intentional: curated archive profiles remain unavailable until Batch 5
  evidence freezes eligible weights; the API exposes this state honestly.

**Docs:** run docs and progress updated; user-facing README deferred to the
browser/final documentation batches so instructions match the completed UI.

**Regression attestation:**

- Cumulative diff: 15 files, +2080/-86 including operational docs.
- Shared surfaces: opponent (server, learner, research and tests), server
  seat/save API, and packaging module list. All direct consumers and editable
  install were exercised.
- Test baseline: 72 -> 90, delta +18, no removals or skips.
- Confidence: HIGH. Compatibility paths, live HTTP shapes, exact model behavior,
  and performance were checked independently; the rules engine is untouched.

**Commit:** `cbe1fd7da2111123f3260efb559eebb96b2743bb`

**Rollback tag:** `elves/v3-pre-batch-2`

**Next:** Batch 3 browser profile controls and Personal learning presentation.

## 2026-07-13 11:43 CDT

**Batch:** 1 — Evaluator parity and V3 measurements

**Contract status:** all criteria met

**Timing:** Implement 4m | Validate 3m | Review 2m | Total 9m

**What changed:**

- `engine/opponent.py`: immutable Balanced weight map, four structural V3
  measurements, six transition measurements, and zero-cost disabled fast path.
- `engine/test_evaluator_v3.py`: exact pre-refactor decision fixtures and
  constructed/all-board symmetry, bounds, legality, and non-mutation coverage.

**Commands and results:**

- `CI=true python3 -m pytest engine -q` — PASS, 79/79.
- `node --check web/game.js` and Python compilation — PASS.
- V2 benchmark smoke — approximately 28/52 ms Toy and 397/742 ms Full for
  Standard/Personal after fast-path repair, within the historical envelope.
- `git diff -- engine/cairn.py` — empty.

**Review findings:**

- Fixed: initial zero-weight structural computation raised Full Standard to
  about 1.38 s and violated the 15% overhead rule. Disabled V3 work is now skipped.
- Fixed: adding V3 keys to `normalized_features()` broke the persisted learner's
  exact nine-key contract. Added separate `normalized_v3_features()` instead.
- Fixed: a capture construction was incorrectly asserted to contain a legal
  cover. Split capture and legal summit/cover constructions.
- Intentional: connection leverage uses the terrain-playable precondition, not
  full history-sensitive legality, to remain a structural non-nested feature.

**Docs:** plan, survival guide, execution log, learnings, and progress updated.

**Regression attestation:**

- Cumulative diff through product commit: 8 files, +1070/-25 including run docs.
- Shared surface: `engine/opponent.py`; seven direct consumers found across
  server, learner, research harnesses, and tests. Public signatures remain
  compatible and the learner's exact feature set is preserved.
- Test baseline: 72 -> 79, delta +7, no removals or skips.
- Confidence: HIGH. Exact seeded actions/scores/nodes cover every board and
  special action, performance returned to baseline, all consumers are green,
  and the rules engine is untouched.

**Commit:** `6c358e59215896ba26df67f52550e93376110d1b`

**Rollback tag:** `elves/v3-pre-batch-1`

**Next:** Batch 2 catalog, seat/API compatibility, and Personal migration.

## Session Setup: 2026-07-13 11:33 CDT

**Phase:** Launch started from the user's explicit implementation request

**Branch:** `feat/evaluator-profiles-v3`

**Run mode:** finite | **Actual stop conditions:** complete and verified, user
stop, or genuine blocker

**Batch breakdown:**

1. Evaluator parity and V3 measurements.
2. Profile compatibility, API, saves, and Personal migration.
3. Browser profile selection and explanations.
4. Deterministic MAP-Elites harness.
5. Full audit, ablations, optimization, curation, and packaged evidence.
6. Strength/behavior/performance/browser gates and final documentation.

**Preflight:**

- Git/GitHub: PASS — public `scarmani/cairn`, authenticated, non-force main
  settlement `57e9e1a..1da66f7` completed.
- Ownership: PASS — one checkout, one feature branch, no competing process;
  collision tripwire `1da66f7`.
- Validation: PASS — 72 pytest cases, JavaScript syntax, Python compilation.
- Fable goal cycle: PASS — adopted parity-first advice; rejected unrelated
  direct-to-main implementation/push recommendation in favor of owned branch.
- Elves install doctor: WARN — v2.0.0 is available; current fully read skill is
  retained for this run and no installed tooling is changed mid-session.
- Review surface: PASS — PR #1 opened on the owned feature branch.

**Decision:** The user supplied a decision-complete plan and explicitly asked
for implementation. Staging and launch are continuous in this task; the durable
files preserve the normal fresh-call recovery boundary.

## Batch 1 Contract: 2026-07-13 11:33 CDT

**Behaviors:**

- Balanced decisions remain byte-for-byte reproducible at the public decision
  surface after evaluator constants move into a named map.
- Six new V3 candidates are bounded, symmetric, non-mutating measurements;
  tactical ones reuse generated transitions.

**Build on:**

- `engine/opponent.py` `_features`, `normalized_features`, `_root_candidates`,
  and `_standard_scores` are the shared evaluator/search seams.
- Existing `engine/test_opponent.py` determinism, legality, pass, swap, and
  non-mutation conventions will be extended.

**Acceptance criteria:**

- [ ] Seeded parity fixtures cover four boards and special actions.
- [ ] Constructed and seeded feature tests prove symmetry/bounds/non-mutation.
- [ ] Existing tests remain green and rules engine has no diff.

**Blast radius:**

- `engine/opponent.py` is consumed by server, learner, research harnesses, and
  opponent/server/learning tests; modified but public call compatibility is
  preserved. Risk: high due to tie and search-score sensitivity.

**Pre-implementation survey:**

- Existing fixed constants are used only in `engine/opponent.py`.
- Learning V2 consumes a nine-key normalized subset and must ignore added V3
  telemetry keys rather than changing its persisted model schema.
- Root candidates already contain next state and capture count; transition
  descriptors can be computed there without recursive legal scans.

---
<!-- New entries go above Session Setup after each completed batch. -->
