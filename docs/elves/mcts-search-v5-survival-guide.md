# READ THIS FILE FIRST AFTER COMPACTION OR RESTART

## Mission

Execute the approved Varde MCTS Search V5 plan from exact draft PR #21 head
`808c317`: freeze independent corpora and an actually independent oracle,
implement three separately switchable search factors, run the full eight-arm
development factorial, and continue only through predeclared gates.

## Run Control

- **Run mode:** finite, seven batches (0–6), approximately twelve hours maximum.
- **Stop policy:** stop only for a completed finite run, the first failed
  mandatory gate, a branch collision, a forbidden/destructive requirement, an
  unrecoverable environment failure, or the hard time boundary.
- **User intent:** implement and execute the complete approved Varde MCTS
  Search V5 staged research plan, preserving negative results and leaving all
  involved PRs draft and unmerged.
- **Checkpoint due by:** 2026-07-18 01:06 America/Chicago.
- **Checkpoint semantics:** this is the hard boundary for launching new
  compute. Finish or safely cancel the active atomic job, persist evidence,
  and produce the final handoff.
- **May continue after checkpoint:** no.
- **Actual stop conditions:** completed Batch 6; first failed mandatory gate;
  branch collision; forbidden/destructive requirement; unrecoverable
  environment failure; or the hard time boundary.
- **Workspace ownership:** dedicated worktree `/private/tmp/varde-mcts-search-v5`
  and branch `codex/mcts-search-v5`; the shared checkout remains read-only.
- **Branch tip at start:** `808c31720730fcf23bbc02c4549bd7151bdab3ec`.
- **Branch/worktree:** `codex/mcts-search-v5` at
  `/private/tmp/varde-mcts-search-v5`.
- Stacked base: `808c31720730fcf23bbc02c4549bd7151bdab3ec`
  from draft PR #21.
- PR base: `codex/mcts-search-v4`; never modify or merge PRs #20 or #21.
- Merge policy: user merges; never self-merge or mark ready.
- **Final-response policy:** disallowed while the Stop Gate says no; allowed
  only at an actual stop condition.
- **Batch completion rule:** every completed batch ends with tests, review,
  execution-log/session updates, a commit, a push, and remote-state polling.
- **Re-read rule:** after every push, re-read this survival guide before doing
  anything else and verify the frozen plan hash.
- **Checkpoint rule:** do not launch work projected to cross the checkpoint;
  persist the latest completed atomic unit before the boundary.
- **Continuation rule:** if the Stop Gate still says
  `Stop allowed right now: no`, immediately begin the recorded next exact
  action after checkpoint control.
- Plan: `docs/plans/mcts-search-v5.md`, SHA-256
  `b476f08b3799babd96ee1f4187da4578b0fba161d11007bb539e16336d9767e0`.
- Time allocation: one third implementation, one third validation, one third
  review. Stop launching stages whose projected runtime exceeds the remaining
  envelope.

## Non-negotiables

- Preserve V4 code and evidence byte-for-byte.
- No diff in `engine/varde.py`, `server.py`, or `web/game.js`.
- Real legal actions, superko, accepted terminal outcomes, no heuristic leaves.
- Freeze manifests before outcomes; never pool recipe versions.
- V4 and V5 development states are regression/development evidence only.
- Stop at the first failed mandatory gate; do not tune after outcomes.
- No live-game cutoff, product API exposure, merge, force-push, or rebase.

## Current Phase

- **Status:** in progress.
- **Active batch:** Batch 3 of 6.
- **What was just finished:** Batch 2 committed at `f572f40`; all 24 oracle
  comparisons, one-scan/decay/parity checks, p95 ceilings, and 323 product tests
  passed without changing any V4 recipe hash.
- **Single next action:** implement obligation-reserved progressive unpruning
  with administrative/proven-set overflow and exact exposure telemetry.

## Stop Gate

- **Planned batches remaining:** 4.
- **Stop allowed right now:** no.
- **Why:** the user authorized the full finite V5 run and no mandatory gate or
  other actual stop condition has fired.
- **Next required action:** execute Batch 3's reserved-unpruning contract and
  prove mandatory exposure, schedule counts, neutrality, eventual expansion,
  and exact V4 behavior/hash preservation.

## Effort Standard

- Work as hard as you can within the frozen plan and finite time boundary.
- Do not be lazy: inspect evidence, tests, hashes, traces, and review state.
- The minimum acceptable change is one complete, verified atomic batch, never
  an implementation-only patch.
- After each checkpoint, take the next highest-value action permitted by the
  plan and current gates.
- Sustain equal attention to implementation, validation, and review through
  the final gate. A clean intermediate commit is not completion.
- Prefer verified negative evidence over relaxed thresholds or post-hoc tuning.

## Forbidden Stop Reasons

- A clean commit is a false completion signal; checkpoints require push,
  polling, guide re-read, and continuation.
- An open draft PR is a false completion signal; it is a checkpoint, not the
  requested research outcome.
- Green tests are a false completion signal when planned gated batches remain.
- A tidy report or session file is a false completion signal; documentation is
  only a resumability checkpoint.
- A large or expensive downstream batch is a false blocker unless measured
  projection crosses the hard time boundary.
- Stop only at a failed mandatory gate, collision, unrecoverable environment
  failure, forbidden/destructive requirement, or completed finite run.

## Launch Readiness

- [x] Exact PR #21 base and collision tripwire verified.
- [x] Dedicated branch/worktree created without modifying prior PRs.
- [x] Full baseline product suite and syntax checks passed.
- [x] Frozen plan and finite batch contract recorded.
- [x] Stop Gate initialized with `Stop allowed right now: no`.
- [x] Draft V5 PR opened against `codex/mcts-search-v4` as PR #22.

## Next Exact Batch

- **Batch:** Batch 3 — obligation-reserved progressive unpruning.
- **Scope:** retain `ceil(2 × sqrt(visits))`, expose every administrative action,
  reserve one slot per urgent obligation, expose the full proven set in guided
  arms, and fill remaining slots by existing fact order and semantic hash.
- **Acceptance criteria:** exact schedules and overflow; administrative and
  urgent actions never hidden; eventual full expansion; deterministic neutral
  ties; at 64 visits, wide roots expose mandatory actions with median at least
  three visits; V4 decisions/hashes unchanged.
- **Risk:** unordered set iteration or post-hoc quota changes would break
  determinism; mandatory overflow must not become forced action exclusion.

## Post-Checkpoint Control Loop

Every completed batch must end with a commit and push. After the push,
re-read this survival guide before doing anything else, verify the plan hash,
inspect active compute, poll all PR comments/reviews/checks, and update session
state. Does the Stop Gate still say `Stop allowed right now: no`, or does
`.elves-session.json` still forbid stopping? If yes, continue immediately with
the recorded next exact action.

## After Any Compaction

Read the Run Control section and Stop Gate first, then follow the Recovery
Order below. Trust the collision tripwire, `.elves-session.json`
`continuation_guard`, frozen hashes, and current PR state over conversational
memory. Do not infer completion from a compacted transcript.

## Validation

- `CI=true python3 -m unittest discover -s engine -q`
- Ruff on every changed Python file
- `python3 -m py_compile engine/*.py research/harness/*.py`
- `node --check web/game.js`
- `git diff --check`
- Exact manifest regeneration, artifact hashes, PR comments/checks

## Active Compute

- No active paid or long-running compute.
- No research search process is authorized before Batch 1 corpus freeze and
  oracle acceptance.

## Recovery Order

1. Read this guide, `.elves-session.json`, learnings, plan, and execution log.
2. Verify branch/worktree, PR head, exact stacked base, and active processes.
3. Resume only the recorded next exact action; never skip a gate or redo a
   completed batch.
