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
- [x] Setup documents committed and pushed at `afe0a1f`.
- [x] Draft PR #20 opened; exact setup head is mergeable and its two test jobs
  started with no comments or reviews present.

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
declared local baseline is green. Draft review surface:
https://github.com/scarmani/varde/pull/20.

## Batch 1 — Measurement substrate and corpus V2

Status: complete.

### Contract

**Behaviors:** add optional per-root terminal telemetry without changing any
seeded MCTS v2 choice or tree statistic; split the existing ten natural-width
positions into diagnostics and add a small-root corpus whose acceptable actions
are certified by exhaustive rule-transition proofs; freeze and run a new
4/16/64 pre-fix baseline before any search-semantic change.

**Build on:**

- Extend `MCTSDecision` and `_Node` in `engine/mcts.py`; preserve the public
  wrapper defaults, RNG calls, legal-action ordering, UCT arithmetic, and final
  selection key.
- Extend `research/harness/mcts_telemetry.py` for rule-transition facts instead
  of duplicating evaluator logic.
- Extend the existing fixture, schedule, atomic checkpoint/resume, summary, and
  audit machinery. Preserve the immutable version-1 manifest/result surface.
- Use `research/fixtures/mcts-v1-golden.json` and
  `research/harness/verify_mcts_golden.py` for exact legacy choice/tree parity.

**Acceptance criteria:**

- [x] Default MCTS decision dictionaries and all current-state seeded choices
  remain exact; MCTS agent version/hash stay unchanged in this behavior-neutral
  batch. The historical golden corpus is 80/96 because all 16 Breath-run
  fixtures were already stale at the untouched base; it was preserved rather
  than silently rewritten.
- [x] Optional root telemetry covers every legal root action with unique stable
  identity, rank, visits, W/D/L counts, terminal-margin aggregates, mean, and
  the selected action/reason; totals reconcile exactly with simulations.
- [x] The ten existing positions remain diagnostic, byte-stable in setup and
  acceptable actions, while new admission positions have at most eight legal
  root actions and machine-validated strict transition proofs.
- [x] Historical manifest version 1 still rebuilds its exact 240-task schedule;
  V2 regeneration, checkpoint/resume, audit, and provenance checks are
  deterministic.
- [x] A version-2 manifest is committed before outcomes, then the frozen
  4/16/64 run completes legally and non-mutating with full telemetry.
- [x] Full tests, Python compile, JavaScript syntax, and diff checks pass.

**Blast radius:** medium. `engine/mcts.py` has ten direct engine/research
consumers; its additions must be optional and its defaults exactly compatible.
The tactical fixture/schedule schema is shared by the admission tests and
auditor, so version-1 schedule reconstruction must be explicit rather than
silently adopting V2 fields. No product UI/server or rules engine is touched.

### Pre-implementation survey

- `_Node` currently backs only `visits` and `value_sum`; adding outcome counters
  on the same backup walk can observe results without another rollout or RNG
  call.
- `_terminal_reward` already calls the authoritative terminal score once. It
  can return the same W/D/L reward plus the root-seat margin without evaluator
  input.
- `MCTSDecision.to_dict()` is used as a deterministic artifact. Optional root
  telemetry must be omitted entirely at the default so old dictionaries remain
  exact.
- `mcts_telemetry.action_key()` is the established stable research identity;
  engine telemetry will emit action dictionaries/identities without importing
  research code.
- The current fixture catalog constructs fresh mutable states and has ten
  positions. V2 can add explicit `diagnostic`/`admission` classification and a
  validated proof payload while retaining a legacy ten-position accessor.
- Full terminal minimax was explored first, but even roots with few legal
  actions expand into large capture/resumption trees. The bounded alternative
  is exhaustive enumeration of every legal **root transition** under a named
  rule fact (capture count, sole-liberty defense, seat-score takeover, rescue
  continuation, fence completion, forced acceptance). These proofs establish
  local tactical dominance only and will say so explicitly.
- Existing atomic writers, ordered worker mapping, deterministic-record hashes,
  and manifest auditor are the patterns to extend; no parallel harness will be
  created.

### Implementation checkpoint

- Added optional root telemetry on the existing backup path. With telemetry
  omitted, decision dictionaries, RNG use, UCT selection, and the MCTS v2 agent
  hash are unchanged. With telemetry enabled, every legal root action reports
  visits, W/D/L, terminal-margin aggregates, final rank, and selection reason.
- Added six synthetic-history, small-root positions (root widths 1, 2, 2, 4,
  7, and 8) with reproducible exhaustive root-transition proofs. The original
  ten positions remain a separate diagnostic class. Proofs explicitly do not
  claim a forced game outcome.
- Extended the existing schedule/checkpoint/audit machinery to V2 while the V1
  manifest still rebuilds its exact 240-task schedule.
- Full product validation after implementation: 257 tests passed. A later
  candidate-parity test raises the expected current total to 258.
- The historical 96-fixture golden verifier passes 80 fixtures and fails all 16
  Breath-run fixtures. A detached worktree at untouched base `b620a11` reproduces
  the same failures for fixture indices 48 and 49, proving that automatic
  Breath-run extension finishing made that old corpus stale before this branch.
  The corpus is preserved unchanged. Current-state telemetry-on/off parity is
  instead tested across all six candidates and both rollout policies.

### Launch reconciliation

- Launched: 2026-07-16T23:40:50-05:00.
- Local HEAD, `origin/codex/mcts-search-v3`, and PR #20 head all equal
  `9c141a1a2338afdbba8a50638c175f5b37f91e39`; PR remains open and draft.
- Plan SHA-256 still equals
  `219ea42829e92de50027a4563a0e40b67291d20d35919df6e250a26d9e6a87ef`.
- The bounded Fable cycle reinforced measurement-first Batch 1 and the rule
  that corpus proofs must not be weakened to manufacture admission. Its
  reference to `docs/AGENT_OPERATING_CONTRACT.md` and an incorrect base hash
  were discarded because live Varde state disproves them.
- Global `elves/pre-batch-N` tags already belong to prior runs. This run uses
  branch-qualified rollback tags and does not move or delete historical tags.

### Frozen evidence and result

- The V2 manifest was committed at `26db89b` before the output directory
  existed. It predeclares 384 decisions over 16 positions, two rollout
  policies, three budgets, and four replicates. Manifest payload SHA-256:
  `deea290ae9ab2653f77e1447e1300eb7bbd17db14db7b3358e2fb5c12f5cc7bf`.
- All 384 decisions completed with zero crash, mutation, illegal action, or
  missing record. The exact provenance audit passed; deterministic-record
  SHA-256 is
  `1260e383a7240aa9d3b2b085689b31a4947ecaf1b992e558da6e65d1c7724de0`.
- The proof-grade corpus failed admission at 64 simulations: pooled hit rate
  `60.4167%`, below the predeclared `80%` threshold. The per-cell `75%` gate
  also failed. Notably, sole-liberty defense was `0/8`, small capture `3/8`,
  and small fence completion `4/8` across the two policy strata.
- Root coverage was essentially complete by 64 simulations (`99.18%` mean
  over the combined corpus), but full coverage did not produce reliable
  tactical selection. This falsifies the idea that missing root enumeration
  alone explains the poor choices.
- The negative gate correctly blocks paired matches. No balance, strength,
  strategic-depth, or forced-outcome claim is made.

### Regression attestation

Batch 1 changes research observation and evidence machinery only. The public
decision dictionary remains byte-compatible when telemetry is disabled, and
telemetry-on/off action parity is exercised across all six rulesets and both
rollout policies. `engine/varde.py`, server, browser, rules, scoring, saves, and
live termination were untouched. Confidence HIGH for instrumentation and
evidence integrity; confidence LOW that unchanged MCTS V2 has adequate tactical
quality, as the preserved negative result demonstrates.

## Batch 2 — Geometry-neutral deterministic ties

Status: in progress.

### Contract

**Behaviors:** replace both coordinate/action-order fallbacks—UCT child
selection and final root choice—with a SHA-256 value derived from the stored
search seed, analyzed root position, current node position, and semantic action
identity. Change no expansion RNG, exploration arithmetic, terminal value,
rollout policy, margin use, or tactical proposal behavior.

**Build on:** Batch 1's exact root telemetry and frozen split corpus. Bump the
MCTS agent version/hash because seeded choices may change. Preserve the Batch 1
manifest, raw artifacts, and compact result byte-for-byte.

**Acceptance criteria:**

- [ ] No coordinate or canonical action-order fallback remains in traversal,
  final selection, telemetry ranking, or selection-reason reporting.
- [ ] Fixed seed/position/action ties are deterministic; changing seed or
  analyzed position reshuffles them; all play, pass, swap, extension, finish,
  resume, and acceptance actions have semantic identities.
- [ ] Directional-orbit tests demonstrate that no fixed board direction wins
  all seeded ties.
- [ ] Legality, non-mutation, superko, save compatibility, administrative
  actions, all rulesets, and both rollout policies remain covered.
- [ ] A separate tie-only manifest is committed before outcomes and the
  4/16/64 result is audited without pooling with MCTS V2.
- [ ] Full tests, Python compile, JavaScript syntax, and diff checks pass.

**Blast radius:** `engine/mcts.py` selection semantics and all consumers that
verify its version/hash. The browser opponent remains unrelated native search;
rules, scoring, server, saves, and live termination stay untouched. Historical
evidence tests must validate their recorded agent hashes rather than falsely
equating them to the new runtime agent.

### Pre-implementation survey

- `_select_child()` used action-kind order followed by raw point coordinates
  after equal UCT scores. `_final_selection_key()` repeated the same two
  fallbacks after visits and mean value.
- Root telemetry used the final selection key and labeled unresolved ties
  `legacy-action-order`, so it must share the new tie key to keep selected rank
  one and explain the decision honestly.
- The seeded hash adds no RNG calls. Existing expansion and rollout streams
  therefore change only after a formerly ordered tie selects a different node.
- The old performance artifact is immutable MCTS V2 evidence. Its regression
  test must pin internal historical consistency and assert that its hash differs
  from MCTS V3, rather than requiring current-agent equality.
