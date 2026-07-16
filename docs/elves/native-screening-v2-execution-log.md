# Native Screening V2 Execution Log

## Batch 0 — Provenance and isolation

- [x] Fetched live `origin/main`; the local remote ref advanced from
  `dc6d997` to `78fae9d`.
- [x] Verified merge parents `dc6d997` and `7cda82b`.
- [x] Recomputed and verified feasibility payload hash
  `556b1f76ab8152abb3a7763de9f82d367224eb6f027132df18af2f11c51094d3`.
- [x] Created isolated branch/worktree `codex/native-screening-v2` at
  `/private/tmp/varde-native-screening-v2-20260715`.

## Batch 1 — Pre-outcome freeze

- [x] Added and tested the compact auditor with synthetic records only.
- [x] Froze exact source, configs, schedules, outputs, gates, and claim limits.
- [x] Five focused tests and the full 226-test suite pass before the freeze.
- [ ] Commit before running a real game.

## Batch 2 — Native jobs

- [x] Mixed Casual/Standard: 240/240 complete, zero illegal, crash, watchdog
  incomplete, or pending records; approximately 11 minutes.
- [x] Matched Standard self-play: 240/240 complete with the same zero-failure
  accounting; approximately 18 minutes.
- [x] Raw results remain under
  `/private/tmp/varde-native-screening-v2-results-20260715` (about 47 MB),
  outside the repository.

## Batch 3 — Audit and handoff

- [x] Predeclared audit accepted exact configs, schedules, provenance, counts,
  and raw hashes. Compact payload hash:
  `addf2aaa3220b8542100dcbd948b399d480a37a958eaf73d86e0e154e37f239d`.
- [x] Seven focused tests, Python compilation, diff checks, and all 228 engine
  tests pass in 24.584 seconds.
- [ ] Push, open the PR, and validate exact-head CI/review.
- [ ] Remove transient Elves recovery files after preserving the final report.
- [ ] Open a non-draft PR and stop without self-merging.

## Diagnostic findings

- Operational correctness passed for all 480 games.
- Breath and Gjerde are the cleanest Standard-self health strata, but mixed
  results remain color/pie/search sensitive.
- Classic reached 80% stagnation under Standard self-play.
- Breath-run reached 32.5% wipes and a 42.2% median margin.
- Gjerde-Go reached 70% wipes under Standard self-play.
- Rosette passed the numerical Standard-self health limits apart from the
  inapplicable mirror-match swap rate; entombment remains unmeasured.
- These are one-family, 20-pair diagnostics and do not eliminate or promote a
  candidate.

## Regression attestation

- Cumulative product surfaces: one research-only auditor, one frozen manifest,
  one compact evidence artifact, one focused test module, and evidence docs.
- Engine, rules, scoring, evaluators, server, browser, and live-game behavior
  are unchanged.
- Test baseline increased from 221 to 228; no test was removed or skipped.
- Raw runs are external and provenance-linked; resume/config gates fail closed.
- Confidence: high for orchestration and accounting, moderate for the reported
  native diagnostic signals, and deliberately none for depth or beauty.
