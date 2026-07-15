# Native Screening V2 Recovery Guide

## Mission

Freeze and execute the native-only Varde diagnostic screen without inspecting
outcomes before the freeze commit or making balance, depth, or flagship claims.

## Run control

- Mode: finite.
- Worktree: `/private/tmp/varde-native-screening-v2-20260715`.
- Branch: `codex/native-screening-v2`.
- Base: `78fae9d30e03f603496af7b1af7e423b58facfc4`.
- Raw output: `/private/tmp/varde-native-screening-v2-results-20260715`.
- User authorized best computer-only next steps; normal PR review gates remain.

## Non-negotiables

- Manifest freeze precedes every real game.
- Pair legs share deterministic seeds.
- No rule, scoring, evaluator, or live-game change.
- The 20N watchdog is research-only.
- No 12/24 MCTS run in this cycle.
- No balance, depth, emergence, beauty, or flagship claim.
- No force push or self-merge.

## Current phase

Status: in progress.

Active batch: freeze commit and native job launch.

Next action: make the freeze commit, record its SHA, then launch the two frozen
jobs without changing their configs or inspecting partial outcomes.

## Recovery order

Read this guide, `docs/plans/native-screening-v2.md`, the execution log, the
frozen manifest, and `research/harness/audit_native_screening.py`. Reconcile
`state.json` and any live evaluator process before using `--resume`.
