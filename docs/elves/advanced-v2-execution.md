# Advanced V2 Execution Log

## Run Digest

- **Last updated:** 2026-07-12 22:18 CDT
- **Current phase:** In progress
- **Active batch:** Batch 4: Browser, documentation, and final review
- **Last completed batch:** Batch 3: Reproducible research and strength gate
- **Next exact batch:** Batch 4
- **Active PR:** unavailable; repository has no remote
- **Latest Elves Report:** not generated

## 2026-07-12 22:18 CDT

**Batch:** 3: Reproducible research and strength gate
**Contract status:** all criteria met

**Timing:** Implement 8m | Train/evaluate 87m | Review 4m | Total 99m

**What changed:** repository-relative parameterized harnesses replace temporary
monkeypatch scripts; historical checkpoints are isolated; exact V2 checkpoint
and aggregate report are retained.

**Evidence:** training completed 200/200 with zero discard. Held-out completed
200/200 legal games and failed the strength gate at 53.5% overall, 56.33% Toy,
45.0% Beginner, 47.75% bootstrap lower bound, +0.23 margin. No stronger claim.
Performance p95 28/56 ms Toy and 389/736 ms Full. Eight n=5/n=6 smoke games
completed, longest 1,701 actions.

**Regression attestation:** exact tracked checkpoint hash matches evaluated
model; `engine/cairn.py` unchanged; compilation and diff checks pass.

**Next:** browser proof, final test pass, cumulative review, report, cleanup.

## 2026-07-12 20:39 CDT

**Batch:** 2: Learning V2 and deterministic continuation
**Contract status:** all criteria met

**Timing:** Implement 5m | Validate 2m | Review 1m | Total 8m

**What changed:**
- `engine/learning.py`: format 2 migration, nine weights, evidence-backed recipe, global attempt cursor, seed continuity, and persistent discarded attempts.
- `engine/opponent.py`: bounded color-symmetric height, rim, and consolidation features.
- `engine/server.py`: omitted seeds continue the stored deterministic sequence.

**Commands:** focused tests 38 passed; full suite 71 passed; one real training game completed in 3.4s and persisted/reloaded nine weights.

**Review:** all consumers of model status, feature names, and training start were inspected. Historical research monkeypatches are intentionally deferred to Batch 3 repair.

**Decisions:** migrated models retain all old weights and remain marked `needs_retraining` even after mixed updates; only Reset establishes a clean V2 recipe.

**Regression attestation:** four shared files changed; test count 67 -> 71, none removed/skipped. Confidence HIGH for persistence/continuation because partitioned and single batches produce identical attempt streams and weights.

**Rollback tag:** `elves/pre-batch-2`

**Next:** make research reproducible and execute the predeclared strength gate.

## 2026-07-12 20:31 CDT

**Batch:** 1: Search and ending correctness
**Contract status:** all criteria met

**Timing:** Implement 3m | Validate 1m | Review 1m | Total 5m

**What changed:**
- `engine/opponent.py`: pass and opening takeover are explicit worst-case replies; pie swap includes pass.
- `engine/server.py`: persisted seat-identity acceptances replace the one-shot ending flag.
- Focused category tests cover search nodes, both acceptances, losing-side resumption, final acceptance, and round-trip state.

**Commands:** focused pytest 29 passed; full pytest 67 passed; JavaScript syntax and rules-engine no-diff gates passed.

**Review:** direct cumulative review found no blocker. Verified all consumers of the two shared search helpers and legacy `end_decided` compatibility.

**Decisions:** retained a derived `end_decided` property and save field for old callers while making `end_acceptances` authoritative.

**Regression attestation:** four shared files changed, all computer modes covered by full tests; test count 60 -> 67, none removed/skipped. Confidence HIGH because every added reply/end branch has a category test and `engine/cairn.py` is unchanged.

**Rollback tag:** `elves/pre-batch-1`

**Next:** implement Batch 2 Learning V2 and deterministic continuation.

## Session Setup: 2026-07-12 20:26 CDT

**Plan:** `docs/plans/advanced-learning-v2.md`
**Survival guide:** `docs/elves/advanced-v2-survival.md`
**Learnings:** `docs/elves/advanced-v2-learnings.md`
**Branch:** `feat/advanced-learning-v2`
**PR:** unavailable; direct local review is the configured review surface
**Run mode:** finite, eight-hour assumed budget
**Continuation guard:** stop_allowed=false; remaining_batches=4

**Batch breakdown:** search/end correctness; Learning V2; evidence gate; browser/final review.

**Preflight:**
- Git: branch created at `6fb779c`; no remote configured, so push/PR is unavailable.
- Validation: 60 pytest cases pass; JavaScript syntax passes.
- Workspace: Claude research and authorized snapshot residue are untracked and preserved.
- Elves advisory: v2.0.0 is available; run continues with installed v1.12.0.

## Batch 1 Contract: 2026-07-12 20:26 CDT

**Behaviors:** score every legal reply action; let both computer seats decide first resumption; persist partial acceptance.

**Build on:** `opponent._standard_scores`, `_swap_value`, `MatchConfig`, and current version-1 optional match fields.

**Acceptance criteria:** focused tests for pass/takeover/end paths; full baseline preserved; `engine/cairn.py` unchanged.

**Blast radius:** `engine/opponent.py` and `engine/server.py` are shared by all computer modes; risk high, requiring full regression and browser proof.

**Pre-implementation survey:** current two-ply and swap scans enumerate placements only; `end_decided` stops all computer decisions after one acceptance.
