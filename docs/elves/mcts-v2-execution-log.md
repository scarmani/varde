# MCTS v2 Performance Run — Execution Log

## Metadata

- Started: 2026-07-15
- Branch: `codex/mcts-fast-clone-v2`
- Base: `565c08b0b0dae0ba3b9ec5bbdbd3ab8927cced6b`
- Product baseline: 201 passing tests
- Evidence dependency: PR #13, manifest v1 blocked before results

## Batch 0 — Isolated performance run setup

### Contract

**Behaviors:** establish a dedicated branch/worktree and PR; carry forward the
terminal-score, equivalence, versioning and no-calibration invariants.

**Build on:** merged MCTS v1, legal-action adapter, deterministic tests, native
evaluators and feasibility artifact on evidence PR #13.

**Acceptance criteria:**

- [x] Dedicated branch from exact merged main.
- [ ] Run-control artifacts committed and pushed.
- [ ] Dedicated PR open and linked from evidence PR #13.
- [ ] No MCTS or engine behavior modified during staging.

**Blast radius:** temporary session metadata and plan documentation only.

### Decisions

- Fable's shared-checkout/quorum assumptions do not exist in Varde; the useful
  golden/profile/performance sequence is retained in a dedicated worktree.
- Golden root-child statistics will be captured with Python frame tracing so v1
  does not need instrumentation before the baseline is frozen.
