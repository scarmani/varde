# MCTS Search V3 — Execution Log

## Metadata

- Started: 2026-07-16 America/Chicago
- User intent: proceed in the best evidence-led order, then make the meaningful
  MCTS tier 2,048 or 4,096 simulations.
- Branch/worktree: `codex/mcts-search-v3` at
  `/private/tmp/varde-mcts-search-v3`
- Base: `b620a11a72097f22e5addbfaf58b56073f9612cd`
- Merge policy: user merges
- Product baseline: 254 passing tests

## Batch 0 — Isolated run staging

### Contract

**Behaviors:** create a dedicated exact-main worktree; establish the six-batch
search/evidence contract; verify the product baseline; open a review surface
without changing MCTS behavior.

**Build on:** merged MCTS tactical admission evidence and its documented
negative result.

**Acceptance criteria:**

- [x] Dedicated worktree and branch start at exact remote main.
- [x] No pre-existing open PR collides with this branch.
- [x] GitHub authentication and remote are usable.
- [x] Full 254-test baseline passes.
- [x] Python compilation, JavaScript syntax, and Git diff checks pass.
- [x] Existing keep-awake processes are identified and left untouched.
- [ ] Setup documents committed and pushed.
- [ ] Pull request opened and exact PR/check state recorded.

**Blast radius:** plan and Elves run-control documents only. No engine, browser,
research harness, manifest, result, or test behavior changes.

### Decisions

- Use six finite batches so the 2,048/4,096 calibration cannot precede
  instrumentation, isolated ablations, and tactical admission.
- Treat 2,048 as the default candidate and 4,096 as conditional on demonstrable
  root-coverage/admission gain and feasible runtime.
- Keep the selected high budget research-only unless it independently meets an
  interactive latency gate; do not silently replace the browser opponent.
- The Elves two-call protocol makes this setup turn staging only. A fresh launch
  call is required before Batch 1 edits.

### Preflight evidence

- `CI=true python3 -m unittest discover -s engine -v`: 254 passed in 29.629s.
- `python3 -m py_compile engine/*.py research/harness/*.py`: passed.
- `node --check web/game.js`: passed.
- `git diff --check`: passed before setup documents.
- `gh auth status`: active account `scarmani`, required repository scopes
  present.
- `caffeinate`: PIDs 16495 and 21008 predate this run; do not terminate them.

### Regression attestation

No product or research behavior has been changed in Batch 0. Confidence HIGH:
the branch starts from the exact merged tactical-admission head and the complete
declared baseline is green.

## Batch 1 — Measurement substrate and corpus V2

Status: not started. Start only in the fresh launch call after rereading the
survival guide and reconciling the PR head.
