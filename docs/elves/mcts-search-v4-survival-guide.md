# READ THIS FILE FIRST AFTER COMPACTION OR RESTART

## Mission

Execute MCTS Search V4 from exact PR #20 head `3154433`: seal an independent
holdout, isolate certified tactics, progressive unpruning, and true-terminal
settling, then continue only through predeclared admission gates. Preserve all
negative evidence and never merge.

## Run Control

- Mode: finite, seven batches (0–6).
- Branch/worktree: `codex/mcts-search-v4` at
  `/private/tmp/varde-mcts-search-v4`.
- Stacked base: `315443366ddeb499d294f47221e89c2c1dbca4d7` from draft PR #20.
- PR base: `codex/mcts-search-v3`; never modify or merge PR #20.
- Merge policy: user merges; never self-merge.
- Plan: `docs/plans/mcts-search-v4.md`.

## Non-negotiables

- No diff in `engine/varde.py`, `server.py`, or `web/game.js`.
- Real legal actions, superko, accepted terminal outcomes, no heuristic leaves.
- Freeze manifests before outcomes and never pool agent versions.
- V3 is development-only; sealed V4 holdout is consulted once at its gate.
- No deep or paired process before admission.

## Current Phase

Finite run complete. Batch 5 selected `none-qualified`; Batch 6 preserved the
negative, completed cumulative validation and review, and documented a fresh
V5 repair investigation. No downstream compute is authorized.

## Stop Gate

- Planned batches remaining: 0.
- Stop allowed right now: yes.
- Next exact action: generate the temporary Elves handoff report, remove only
  operational session artifacts, poll draft PR #21 once more, and hand control
  to the user without merging.

## Validation

- `CI=true python3 -m unittest discover -s engine -q`
- Ruff on every changed Python file
- `python3 -m py_compile engine/*.py research/harness/*.py`
- `node --check web/game.js`
- `git diff --check`
- Exact manifest regeneration, payload hashes, PR comments/checks

## Recovery Order

1. Read `.elves-session.json`, this guide, the plan, execution log, and learnings.
2. Verify branch, worktree, PR head, exact stacked base, and running processes.
3. Resume only the recorded next exact action; do not skip a gate.
