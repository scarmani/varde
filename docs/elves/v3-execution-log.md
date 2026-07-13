# V3 Execution Log

## Run Digest

- **Last updated:** 2026-07-13 11:33 CDT
- **Current phase:** In progress
- **Active batch:** Batch 1 — Evaluator parity and V3 measurements
- **Last completed batch:** Session setup
- **Next exact batch:** Batch 1
- **Active PR:** not created yet
- **Docs promoted this run:** `docs/plans/evaluator-profiles-v3.md`
- **Latest Elves Report:** not generated yet

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
