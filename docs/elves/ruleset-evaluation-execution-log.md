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
