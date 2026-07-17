# READ THIS FILE FIRST AFTER ANY COMPACTION OR RESTART

## Mission

Deliver a correctly instrumented and tactically admitted MCTS v3, then choose
2,048 or 4,096 simulations as a meaningful deep-research tier from measured
root coverage and latency. Preserve negative evidence and never change game
rules or import native evaluator leaf values.

## Run control

- Mode: finite
- Assumed unattended budget: approximately eight hours per launched cycle;
  expensive evidence stages may require later finite continuations.
- Branch: `codex/mcts-search-v3`
- Worktree: `/private/tmp/varde-mcts-search-v3`
- Base/collision tripwire: `b620a11a72097f22e5addbfaf58b56073f9612cd`
- Pull request: draft PR #20, https://github.com/scarmani/varde/pull/20
- PR/merge policy: open early; user reviews and merges; never self-merge
- Plan: `docs/plans/mcts-search-v3.md`
- Stop after: six implementation/evidence batches, or the first true integrity
  blocker that prevents a valid negative result.

## Non-negotiables

- Do not edit `engine/varde.py`, rules, scoring, save semantics, or live-game
  termination.
- MCTS uses real legal actions, superko, and real terminal outcomes.
- No native evaluator leaf values, rollout truncation, or live cutoff.
- Version/hash every behavior change and never pool versions.
- Freeze manifests before outcomes; do not rewrite historical results.
- No paired games before tactical admission.
- No destructive Git operation, force push, test weakening, or automatic merge.
- Keep the shared checkout and all unrelated worktrees untouched.

## Current phase

Status: all six batches complete; mechanical report/cleanup closeout remains

Active batch: none

Just completed: Batch 6 reconciled all five negative 384-decision runs, skipped
the gated paired diagnostic, passed the full 268-test suite and static checks,
and completed direct review with no blocking finding. At reviewed head
`a03a723f65c68acbfaa036f5db600df343c64fe2`, both GitHub checks pass and PR #20
is open, mergeable, draft, and unreviewed. Neither 2,048 nor 4,096 was selected.

Single next action: generate the temporary Elves HTML report, remove this guide,
the execution log, and `.elves-session.json` from the PR while retaining their
Git history, then poll post-cleanup exact-head CI and hand off without merging.

## Active compute

No Varde research or test process is active. Two pre-existing system
`caffeinate` processes are present and must not be killed by this run.

## Stop gate

- Planned implementation/evidence batches remaining: 0
- Stop allowed right now: yes, after mechanical report/cleanup closeout
- Next required action: generate report, remove operational files, verify final
  exact head, and hand off
- Continue automatically through valid batches; do not merge.

## Validation gates

- `CI=true python3 -m unittest discover -s engine -v`
- `python3 -m py_compile engine/*.py research/harness/*.py`
- `node --check web/game.js`
- `git diff --check`
- Deterministic corpus regeneration and search-version/hash verification
- Legality, non-mutation, superko, save/action compatibility tests
- Exact manifest/audit checks for every frozen evidence job
- PR comments/checks and exact-head reconciliation after each push

## Recovery order

1. Read this guide and `.elves-session.json`.
2. Read `docs/plans/mcts-search-v3.md`, then
   `docs/elves/mcts-search-v3-execution-log.md` and
   `docs/elves/mcts-search-v3-learnings.md`.
3. Run `git status --short --branch`, confirm the base tripwire and inspect the
   PR head/check state.
4. Reconcile running Varde processes before launching compute.
5. Resume the single recorded next action; do not skip an admission gate.
