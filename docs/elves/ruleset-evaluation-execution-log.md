# Ruleset Promise Evaluation Execution Log

## Run Digest

- **Last updated:** 2026-07-15 13:31 CDT
- **Current phase:** In progress
- **Active batch:** Batch 2 — native ruleset evaluators and tactical admission
- **Last completed batch:** Batch 1 — correctness, registry, API, and browser truth
- **Next exact batch:** Batch 2 — native ruleset evaluators and tactical admission
- **Active PR:** #12
- **Docs promoted this run:** `docs/plans/ruleset-promise-evaluation.md`
- **Latest Elves Report:** not generated yet

## Session Setup: 2026-07-15 13:20 CDT

**Phase:** Launch started from the user's explicit implementation request

**Branch:** `feat/ruleset-promise-evaluation`

**Run mode:** finite | **Actual stop conditions:** complete and verified, user stop, or genuine blocker

**Batch breakdown:**

1. Correctness, versioned ruleset registry, API, and browser truth.
2. Native ruleset evaluators and tactical admission fixtures.
3. Deterministic rules-action abstraction and ruleset-neutral MCTS.
4. Reproducible computational falsification harness and statistical gates.
5. Human-study instruments, local records, and browser workflow.
6. Bounded evidence, cumulative proof, documentation, and PR handoff.

**Preflight:**

- Git/GitHub: PASS — clean main at `21b2efa`, authenticated `scarmani`, no open PR or competing worktree.
- Validation: PASS — 156/156 tests, Python compilation, and JavaScript syntax.
- Environment: PASS — `npx` available and `caffeinate` active.
- Elves advisory: v2.4.0 available; retained fully read v1.12.0 to avoid mid-run tooling changes.
- Goal cycle: PASS — recommended central registry first. Adopted the architecture but combined it with the mandatory scoring repair before any evidence work.
- Context gap: repository has no `docs/AGENT_OPERATING_CONTRACT.md`; global no-force/no-merge constraints remain binding.

**Launch readiness:** READY — setup commit `031c8d6` is pushed and PR #12 is open.

## 2026-07-15 13:22 CDT

**Batch:** 0 — Session setup and PR surface

**Contract status:** all criteria met

**What changed:** approved plan, compaction-safe run state, ignore rule for
goal-cycle artifacts, owned branch, and PR #12.

**Commands and results:** baseline 156/156 pytest cases, Python compilation,
and JavaScript syntax all passed; GitHub authentication and push passed.

**Review findings:** no PR comments; initial CI queued. The goal-cycle prompt
recommended metadata first, but correctness remains ahead of evidence and is
combined with the registry batch.

**Regression attestation:** operational documentation only; product behavior
is unchanged. Baseline remains 156 tests. Confidence HIGH.

**Commit:** `031c8d699106a4f12ee97274d99ce2f056b20a69`

**Next:** Batch 1 Gjerde scoring, registry, API, browser, and invalidation docs.

## Batch 0 Contract: 2026-07-15 13:20 CDT

**Behaviors:**
- Persist the approved plan and compaction-safe run state.
- Establish one owned branch and early PR review surface.

**Build on:**
- Existing `docs/plans` and `docs/elves` conventions from the completed V3 run.
- Existing GitHub Actions test workflow and `progress.md` history.

**Acceptance criteria:**
- [x] Baseline gates green and test count captured.
- [x] Branch/collision tripwire recorded.
- [ ] Setup committed, pushed, and PR opened.

**Blast radius:** operational documentation only; low product risk.

**Pre-implementation survey:** existing V3 session data on main is stale and will be replaced for this run, then removed during final operational cleanup.

## Batch 1 Contract: 2026-07-15 13:32 CDT

**Behaviors:**
- Treat every unclaimed exterior Gjerde line as an open cell-region boundary.
- Centralize stable ruleset revision, geometry, scoring, status, board limits,
  public availability, descriptions, and archival reasons.
- Derive API validation and browser choices from that registry while preserving
  every existing ruleset ID for saves and research.
- Invalidate pre-repair Gjerde conclusions and label small historical matches as
  exploratory probes.

**Build on:**
- Existing `Game` construction and version-1 `Game.from_dict` compatibility.
- Existing `/api/profiles` catalog/install pattern in the dependency-free client.
- Existing category tests for interior, mixed-color, and Gjerde-Go fences.

**Acceptance criteria:**
- [ ] Empty, singly claimed, partially fenced, fully fenced edge, interior, and
  mixed-boundary scoring pass for both Gjerde resolution orders.
- [ ] Compatibility tuples retain their current IDs and ordering.
- [ ] Public new-game API rejects control, archived, and broken variants with
  explicit registry reasons; old saves for every variant still load.
- [ ] `/api/rulesets`, static fallback, dynamic browser install, allowed board
  sizes, public descriptions, and semantic browser state agree.
- [ ] Full unit, compile, JS syntax, API smoke, and Playwright screenshot/console
  checks pass.

**Blast radius:** scorer -> Gjerde score, native evaluation, match outcomes;
registry -> `engine/varde.py`, `engine/server.py`, research imports, saves, and
`web/index.html`/`web/game.js`. Three Python consumers import the compatibility
tuples; the browser has one startup catalog path and one new-game submission.

## 2026-07-15 13:31 CDT

**Batch:** 1 — Correctness, ruleset registry, API, and browser truth

**Contract status:** all criteria met

**What changed:** Gjerde scoring now treats every unclaimed exterior line as
open. A frozen versioned registry derives all compatibility tuples and exposes
candidate/control/archived/broken status, evaluation revision, geometry,
scoring, board limits, descriptions, and public availability. The server has
`GET /api/rulesets`, rejects nonpublic new games, and loads old saves (including
n=8 Gjerde and broken/archived variants). The browser installs the registry,
disables nonpublic choices, preserves archived loaded choices, constrains board
sizes, and exposes semantic ruleset state.

**Category proof:** the old scorer failed exactly as reported: one Black outer
line scored 37-0 on n=4 and five White lines of an incomplete edge fence scored
0-37. After repair, empty, single exterior, partial edge, closed edge, interior,
mixed, breath-first, and Go-order cases all pass.

**Documentation truth:** old Gjerde results are explicitly invalidated; 4-8
game variant results are exploratory probes; Breath cap is documented broken;
the twelve-quiet ending is an operational closure/design smell rather than a
proof of strategic impossibility; README naming, Personal profile behavior,
and test count are current.

**Commands and results:** 167/167 engine tests; Python compilation; JavaScript
syntax; diff whitespace check; live API catalog 200, Breath cap new-game 400,
n=8 Gjerde new-game 200; Playwright static/dynamic catalog, Full new game,
broken selection lock, archived save reload, semantic state, opened canvas and
full-page screenshots, and zero console errors all pass.

**Regression attestation:** all previous 156 tests remain, 11 category/registry
tests were added, no skips or weakened assertions. Existing IDs and tuple order
are exact. Version-1 snapshots remain the persistence surface. Confidence HIGH.

**Next:** native evaluators and distinctive-mechanic tactical admission.

**Commit:** `a3f645e`

## Batch 2 Contract: 2026-07-15 13:34 CDT

**Behaviors:**
- Preserve the literal Classic Balanced path and every seeded parity fixture.
- Route each non-Classic candidate through a frozen evaluator using only terms
  meaningful under that ruleset's geometry, life, and scoring objective.
- Keep Personal/curated Classic static corrections outside native ruleset
  evaluation; allow only already-generated transition-style bonuses in public
  profile play.
- Pin evaluator format, revision, schema, and hash for later evidence records.

**Build on:** existing bounded one/two-ply legality and reply scans, V3
transition reuse, `group_has_ring`, strict sky/collar primitives, corrected
`score_cells`, and exact profile-parity fixtures.

**Acceptance criteria:**
- [x] Classic action/score/reason/node parity is unchanged.
- [x] All native evaluators are deterministic, finite, bounded,
  color-symmetric, non-mutating, superko-aware, and save-compatible.
- [x] Constructed admission fixtures distinguish every declared mechanic.
- [x] Evaluator metadata is hash-pinned without exposing raw weights to the UI.
- [x] Full tests, compile, JS syntax, and representative performance pass.

**Blast radius:** `engine/opponent.py` search evaluation and rationales;
non-Classic computer decisions intentionally change. Classic play, rules,
saves, model files, and live-game termination remain untouched.

## 2026-07-15 13:46 CDT

**Batch:** 2 — Native ruleset evaluators and tactical admission

**Contract status:** all criteria met

**What changed:** added `native_evaluators.py` with six frozen evaluator
revisions and a deterministic catalog hash. Rosette values cycles, ring mass,
legal entombment opportunities, captures, and late territory; Breath values
liberties, local cavities, cuts, captures, and late territory; Breath-run adds
opponent rescue pressure, chase length, and self-squeeze; Gjerde values repaired
fenced cells, nearly closed fences, denial, liberties, and vulnerable groups;
Gjerde-Go adds eye space, capture-first weight, and singleton ko exposure.
Classic metadata covers control, collars/skies, captures, vulnerability, and
territory, while actual Classic search remains on the historical literal path.

**Admission proof:** constructed positions detect collar clearance, intact vs
broken rings, legal entombment caps and the five-stone unzip, local Breath
cavities and cut points, immediate flat capture, Breath-run chase/self-squeeze,
five-of-six Gjerde fence completion, mixed-color denial, Gjerde-Go eye space,
and singleton ko exposure. Native search is repeated across both difficulties,
all rulesets, superko, serialization, and non-mutation.

**Performance:** fresh Standard medians/p95 in milliseconds: Classic Toy
27.1/28.1, Classic Full 386.5/387.7, Rosette Full 435.2/444.3, Breath Full
893.1/894.1, Breath-run Full 949.4/961.0, Gjerde n=4 330.8/332.1, and
Gjerde-Go n=4 443.1/445.8. These are small local acceptance samples, not
comparative strength evidence.

**Validation:** 177 engine tests after this batch (176 before the final API
metadata assertion), Python compilation, JS syntax, whitespace, evaluator
hash/schema, focused 61-test search/server suite, and the full 176-test product
gate before metadata wiring all pass. No skips or weakened tests.

**Regression attestation:** seeded Classic fixtures across Toy through Full,
pie, pass, ending/resumption, and superko remain exact. Non-Classic changes are
the intended firewall repair. Confidence HIGH.

**Next:** deterministic common action layer and terminal-score-only MCTS.

**Commit:** `cc0517c`

## Batch 3 Contract: 2026-07-15 13:48 CDT

**Behaviors:**
- Represent every legal rules phase through one stable action vocabulary.
- Carry seat identity through pie takeover and separate first-ending decisions.
- Run seeded adversarial UCT with terminal win/draw/loss from the actual game
  score as the only backed-up value.
- Offer action-uniform and light epsilon-greedy rollout policies without a
  live move/rollout cutoff; report rollout length explicitly.

**Build on:** `Game` legality, version-1 cloning, fixed superko history,
extension APIs, corrected server ending semantics, and candidate registry.

**Acceptance criteria:**
- [x] Play, pass, swap, extend, finish-extension, resume, and accept enumerate
  and apply legally without mutating the source state.
- [x] MCTS is deterministic, legal, non-mutating, superko-aware,
  save-compatible, and terminal-score-only.
- [x] Both first-ending decisions and the once-only resumption have fixtures.
- [x] 250-simulation smoke completes for six candidates and both rollout
  policies with no illegal, crash, or incomplete simulation.

**Blast radius:** new research modules only; no server difficulty, rules,
snapshot, profile, or live action path changes.

## 2026-07-15 14:02 CDT

**Batch:** 3 — Deterministic ruleset-neutral MCTS

**Contract status:** all criteria met

**What changed:** `actions.py` provides stable immutable actions plus a cloned
rules state carrying color-to-seat identity, end acceptances, and next ending
decider. `mcts.py` provides seeded UCT, position-derived RNG seeds, adversarial
selection across seat takeover, robust-child choice, action-uniform and light
epsilon-greedy rollouts, and terminal score reward only. Every result pins the
agent hash and reports simulations, nodes, mean value, average rollout length,
and maximum rollout length.

**Ending proof:** after two passes, the first seat may accept and the other may
still resume; either may resume first; two acceptances end the first ending;
resumption clears acceptances; after resumption, one acceptance finalizes.
Takeover swaps complete seat identity while White remains to act.

**Rollout correction:** the first light policy always sought contact and a
Gjerde-Go smoke rollout ground for several minutes. It was canceled and not
reported as completed evidence. The corrected light policy treats a late
opponent pass as an invitation to score and samples a legal pass at 35% after
one board-point count of actions. This is agent policy, not a forced ending:
every backed-up simulation still reaches the engine's actual terminal score.

**250-simulation smoke:** all 12 corrected-hash conditions completed with
`ok=true`, 251 tree nodes, legal placements, source-state equality, zero crash,
and zero incomplete rollout. Single-process-equivalent elapsed times under four
concurrent subprocesses ranged 12.2-48.2 seconds. Average rollout lengths ranged
62.096-188.58 actions; maximums ranged 74-521. Policy-dependent opening choices
already occur and will be treated as provisional evidence by the harness.

**Validation:** 185/185 tests, Python compilation, JS syntax, and whitespace
pass. Unit fixtures cover all actions, superko, snapshot equivalence, fixed
seed/policy determinism, every candidate, both rollout policies, and ending
actions. No old tests were removed or weakened.

**Regression attestation:** modules are not wired into live server play; all
existing behavior stays behind its prior tests. Confidence HIGH.

**Next:** paired evaluation CLI, game telemetry, statistics, checkpoints,
cancellation, worker determinism, and declared gates.

**Commit:** `868ea8a`

## Batch 4 Contract: 2026-07-15 14:02 CDT

**Behaviors:**
- Schedule fixed paired seeds with each agent assigned both initial colors.
- Run native and terminal-score MCTS families with explicit budgets and rollout
  policies through the complete action controller.
- Preserve every complete, illegal, crashed, or research-watchdog-incomplete
  attempt in canonical JSONL plus an atomic hash-pinned checkpoint.
- Produce byte-identical final state, games, and summary after resume or worker
  count changes.

**Acceptance criteria:**
- [x] Paired scheduling and statistics are deterministic and color-correct.
- [x] JSONL, summary, and checkpoint artifacts are atomic and hash-pinned.
- [x] Resume and worker scheduling produce byte-equivalent final artifacts.
- [x] Cancellation and watchdog attempts are preserved, never dropped.

**Blast radius:** research harness plus an MCTS rules-state entry point; the
plain-game MCTS API and all live server behavior remain compatible.

## 2026-07-15 14:22 CDT

**Batch:** 4 — Computational falsification harness

**Contract status:** all criteria met

**What changed:** `evaluate_rulesets.py` is a repository-relative paired CLI
covering the six frozen candidates, native Casual/Standard and seeded
uniform/light MCTS, arbitrary budget ladders, board sizes, workers, explicit
output, checkpoints, resume, cancellation, optional move telemetry, and a
research-only watchdog. `choose_mcts_state_action` preserves seat identity and
first-ending acceptances while the historical plain-game wrapper remains.

**Evidence discipline:** source, registry, native evaluator, MCTS, and harness
hashes are pinned. Summaries expose paired bootstrap bounds, color/pie/ending
health gates, wipes, margins, opening convergence warnings, strategic telemetry,
and direct adjacent-budget comparisons. Headline claims remain blocked until
both rollout policies have 100-pair cross-family evidence, two 100-pair
adjacent-budget comparisons, and passing health gates. Unmeasured commitment
and sacrifice fields remain explicit nulls.

**Determinism proof:** injected orchestration tests compare uninterrupted
one-worker output with a run paused after five games and resumed with four
workers; `state.json`, `games.jsonl`, and `summary.json` are byte-identical.
Cancellation resumes cleanly, checkpoint tampering fails closed, and incomplete
attempts remain in JSONL and failure accounting.

**Real-agent smoke:** two candidate/native strata completed four games through
the process pool with telemetry; a separate native/MCTS pair completed both
colors. Both had zero illegal, crash, or watchdog-incomplete games and retained
`promotion_blocked=true`. A post-commit smoke pins source `adeba1c` and completes
both colors with clean accounting.

**Validation:** 193 tests, Python compilation, JavaScript syntax, ruff on the
new surfaces, whitespace, direct MCTS ending-state preservation, and actual CLI
process workers pass. No tests were removed or weakened.

**Regression attestation:** no live-game action ceiling exists; the watchdog
only classifies research records. Confidence HIGH.

**Next:** local human-study instruments, playtest recording/export, and browser
verification.

**Commit:** `adeba1c`

## Batch 5 Contract: 2026-07-15 14:22 CDT

**Behaviors:**
- Generate neutral, versioned study instruments for an 8–12-player panel.
- Counterbalance fixed opponent pairs, ruleset order, and exact within-pair color.
- Capture hotseat actions and monotonic thinking intervals in browser memory,
  then export locally without direct identifiers or network submission.
- Preserve two-pass/resumption action history and keep game saves separate.

**Acceptance criteria:**
- [x] Human records are versioned, locally exportable, and reject PII fields.
- [x] Crossover schedules balance ruleset order, opponent, and color.
- [x] Briefs and puzzles are neutral and do not seed designer motif names.
- [x] Screenshots, semantic state, save/load, and console checks pass.

**Blast radius:** browser hotseat instrumentation and offline research package;
no server collection endpoint, live rule, save format, or computer path changes.

## 2026-07-15 14:40 CDT

**Batch:** 5 — Human-study instruments and product workflow

**Contract status:** all criteria met

**What changed:** `human_study.py` generates fixed-pair Latin rotations for 8,
10, or 12 pseudonymous participants, six alternating-color games per ruleset,
two engine-derived call-your-shot puzzles per candidate, nine separate aesthetic
ratings, emergence prompts, readability checks, and a one-week retention form.
Gjerde fixtures explicitly cover closing an interior fence and the repaired
unclaimed outer boundary. Packages pin source, rules revisions, privacy policy,
browser schema, and a deterministic hash.

The browser adds a hotseat-only local recorder before move one. It records only
action kind, point, actor color, monotonic elapsed time, move indices, captured
stone count, ordered capture waves, score, resumption, and ending type. It uses
a generated pseudonymous UUID, contains no wall-clock time or identity fields,
and has no server submission. New/load prompts prevent accidental loss; game
saves remain separate.

**Browser proof:** the required web-game client recorded a live Breath move and
produced semantic state plus an opened canvas screenshot. A full-page Playwright
chain recorded play/pass, downloaded JSON, passed the Python validator, saved
and reloaded the game, cleared the separate record, and produced the inspected
`/tmp/varde-playtest-full.png`. A second chain recorded play/pass/pass/resume,
changed complete back to active, preserved `resumption_used`, and had zero
console errors. Watch mode starts paused and disables recording.

**Validation:** 200 tests, Python/JavaScript syntax, ruff on new Python, package
hash verification, candidate puzzle replay, 8/10/12 schedule balance, strict
PII/schema rejection, screenshot inspection, download validation, save/load,
resumption, watch mode, and zero console errors pass. The post-commit package
pins source `fe58b9e`.

**Regression attestation:** all data remains local and opt-in. No live action
ceiling or hidden collection was introduced. Confidence HIGH.

**Next:** bounded generated smoke evidence, full final gates, documentation of
unrun computational/human promotion gates, and PR handoff.

**Commit:** `fe58b9e`

## Batch 6 Contract: 2026-07-15 14:40 CDT

**Behaviors:**
- Generate a committed operational smoke from a fixed source/configuration.
- Keep every game-design and promotion conclusion blocked at inadequate sample.
- Publish one exact matrix separating implemented, verified, provisional, and
  unrun work with reproduction commands and next authorization.
- Complete cumulative code, test, browser, PR, and workspace review.

**Acceptance criteria:**
- [x] Compact evidence is source-pinned and explicitly non-claim.
- [x] Deferred overnight and human gates are visible and not implied complete.
- [x] Full tests, syntax, whitespace, and browser checks pass locally.
- [ ] Final PR checks and readiness review pass before cleanup/handoff.

**Blast radius:** documentation, compact evidence, record import, and its
validation test; no rules, live AI, scoring, or collection endpoint changes.

## 2026-07-15 14:51 CDT

**Batch:** 6 — Bounded evidence and final handoff

**Contract status:** product criteria met; final readiness review in progress

**Generated evidence:** source `064d93d` ran all six candidates at n=3 with one
paired seed, Casual native search, and one-simulation uniform MCTS. All 12 games
completed with zero illegal actions, crashes, or incompletes. The compact record
stores raw artifact hashes, 50–100% wipe rates, a Classic stagnation leg, one
pair per stratum, `headline_eligible=false`, and `promotion_blocked=true`. It
does not publish the meaningless 1–0 native-versus-one-simulation score as a
candidate result.

**Decision truth:** `docs/ruleset-evaluation-status.md` states that no flagship
is selected. The 20-pair calibration, 50-pair screen, 100-pair confirmation,
250/1000/4000 ladder, rollout stability, exploit policies, ruleset-native
MAP-Elites, n=5 confirmation, human panel, retention, outside games, and final
promotion gate are all explicitly unrun.

**Import completion:** local JSON import now validates the version, candidate
revision, pseudonymous id, hashes, complete action fields, timing, score shape,
and forbidden identity keys. Imported records are read-only and remain outside
the server. A valid record reopened with two actions; an `email` field was
rejected with zero console errors.

**Validation:** 201 tests, targeted ruff, Python compilation, JavaScript syntax,
JSON validation, whitespace, final official web-game client Gjerde action,
semantic record state, local import/rejection, and opened full-page Gjerde UI
screenshot pass. Cumulative diff review found no live cutoff, external
collection, old-save break, Classic seeded drift, or claim escalation.

**Regression attestation:** the only generated match evidence is labeled
non-claim at file, summary, and documentation surfaces. Archived/broken loading,
public candidate filtering, Classic parity, Personal isolation, and live-game
uncapped behavior remain covered. Confidence HIGH pending remote CI.

**Commit:** `21ebff3`
