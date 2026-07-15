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

- [ ] Run mixed Casual/Standard job.
- [ ] Run matched Standard self-play job.
- [ ] Preserve raw results outside the repository.

## Batch 3 — Audit and handoff

- [ ] Run the predeclared compact audit.
- [ ] Validate the full suite and exact-head CI.
- [ ] Remove transient Elves recovery files after preserving the final report.
- [ ] Open a non-draft PR and stop without self-merging.
