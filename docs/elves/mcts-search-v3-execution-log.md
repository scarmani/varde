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

Status: complete.

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

- [x] No coordinate or canonical action-order fallback remains in traversal,
  final selection, telemetry ranking, or selection-reason reporting.
- [x] Fixed seed/position/action ties are deterministic; changing seed or
  analyzed position reshuffles them; all play, pass, swap, extension, finish,
  resume, and acceptance actions have semantic identities.
- [x] Directional-orbit tests demonstrate that no fixed board direction wins
  all seeded ties.
- [x] Legality, non-mutation, superko, save compatibility, administrative
  actions, all rulesets, and both rollout policies remain covered.
- [x] A separate tie-only manifest is committed before outcomes and the
  4/16/64 result is audited without pooling with MCTS V2.
- [x] Full tests, Python compile, JavaScript syntax, and diff checks pass.

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

### Frozen evidence and result

- MCTS V3 hash:
  `fea77f2e4064a21abe763240822be7f2e4f1ff90a0cd12f677821b6bf6fbd0c3`.
  The tie-only manifest was committed at `adf69c1` before its output directory
  existed. Manifest payload SHA-256:
  `3f472bd7af76bf6376e859e6b7c105807db792edbd6fda0a95154a2a4310be82`.
- All 384 decisions completed with zero crash, illegal action, mutation, or
  missing record. Deterministic-record SHA-256:
  `4b5c1193276a8d1f81a3a2b3fbae84c9978ecd17bea8791426f9a626cb4068f9`.
- The isolated tie fix did **not** improve tactical admission. The proof-grade
  high-rung hit rate fell from MCTS V2's `60.4167%` to `54.1667%`; the
  nondecreasing-by-policy gate also failed. Small-defense improved only from
  `0/8` to `1/8`, while small-fence fell from `4/8` to `1/8` and the rescue
  continuation fell from `6/8` to `5/8`.
- Root coverage remained identical at `99.1795%` mean at 64 simulations. This
  isolates the regression to downstream choice/tie effects, not task coverage.
- Directional neutrality is retained as a correctness property despite the
  strength regression. Batch 3 may test whether terminal-only margin resolves
  the saturated comparisons; it must not reinterpret this result as positive.

### Regression attestation

Batch 2 intentionally changes only research-agent tie behavior and its
version/hash. Terminal W/D/L, rollout policies, expansion randomness,
exploration, legal actions, and telemetry accounting are unchanged. The full
260-test suite passed in 32.203 s before the frozen run; syntax and diff checks
also passed. Product rules, scoring, saves, server, browser, and live opponent
remain untouched. Confidence HIGH for directional-bias removal and evidence
isolation; confidence HIGH that tie randomization alone does not repair tactical
selection on this corpus.

## Batch 3 — Terminal-margin secondary backup

Status: complete.

### Contract

**Behaviors:** retain terminal W/D/L and UCT as the primary search value; add
terminal score margin normalized by the ruleset's scoreable area as the next
lexicographic comparison before the seeded hash. Record raw and normalized
terminal-margin aggregates. Do not alter rollout actions, expansion order,
exploration, legal transitions, or terminal completion.

**Build on:** MCTS V3 seeded-hash ties and Batch 1 telemetry. Version/hash the
combined tie-plus-margin semantics as a new agent. Preserve V2 and V3 manifests,
raw artifacts, and results byte-for-byte.

**Acceptance criteria:**

- [x] Vertex games normalize by board points and Gjerde games by scoreable
  cells; every sample is finite and in `[-1, 1]`.
- [x] Terminal margin is exactly color-symmetric for every candidate and board
  size and comes only from the accepted game score.
- [x] W/D/L remains primary in traversal and final choice; margin resolves only
  otherwise equal primary comparisons.
- [x] Raw and normalized root aggregates reconcile with visits and selected
  rank/reason remains exact.
- [x] A separate tie-plus-margin manifest is committed before outcomes and the
  identical 4/16/64 schedule is audited against both earlier agents.
- [x] Retain margin only if it improves admission or resolves documented
  saturation without material diagnostic regression.
- [x] Full tests, Python compile, JavaScript syntax, and diff checks pass.

**Blast radius:** research MCTS selection and telemetry plus the tactical
harness's normalized-margin validation. No native evaluator is imported. Rules,
scoring, live termination, server, browser, save schema, and native opponent are
out of scope.

### Pre-implementation survey

- `_terminal_sample()` already obtains the authoritative accepted score once;
  normalization can be calculated there without another rollout or evaluator.
- Vertex score totals are bounded by `len(board.points)`. Gjerde scores fenced
  fields, bounded by `len(board.cells)`; normalizing Gjerde by playable lines
  would understate its margin.
- Node backup already carries raw terminal margin for Batch 1 telemetry. A
  parallel normalized aggregate on the same backup walk adds no RNG calls and
  no game transitions.
- At opponent nodes, the secondary comparison must minimize the root seat's
  normalized margin just as primary exploitation uses `1 - mean`.

### Frozen evidence and result

- MCTS V4 hash:
  `4224495eecc22ebedf3a199c04ff57b11446481f2e1218a6feffac4b09ad9adc`.
  The margin manifest was committed at `debb368` before its output directory
  existed. Manifest payload SHA-256:
  `6885d609ea68a54a3f46edacbaf8c68f5cbead32fd96f9c2572782d103002f37`.
- All 384 decisions completed with zero crash, illegal action, mutation, or
  missing record. Deterministic-record SHA-256:
  `59cbce15bcc3577360cafe9c5e476d3905a918308ea49fa56ba5883356331f0d`.
- Margin did not improve proof-grade admission: the 64-simulation rate moved
  from tie-only V3's `54.1667%` to `52.0833%`; the per-cell and monotonicity
  gates still failed.
- It did resolve documented saturation without a material natural-diagnostic
  regression. At the high rung, margin uniquely selected 45 of 80 diagnostic
  decisions, while diagnostic hit rate remained exactly `32.5%` before and
  after. Across all 128 high-rung decisions, `terminal-margin` was the final
  reason 49 times.
- The retention alternative is therefore met: keep terminal-only normalized
  margin in the combined candidate as an honest W/D/L tie discriminator, but
  make no strength or admission claim. Batch 4 must supply tactical proposal
  quality; simply increasing this agent's budget is still blocked.

### Regression attestation

Batch 3 changes only research-agent secondary comparisons and telemetry. Every
rollout still reaches the accepted real score; normalized values are bounded
and exactly color-symmetric across all six candidates and n=3..6. The full
262-test suite passed in 31.841 s before freezing; syntax, Ruff, and diff checks
also passed. No native evaluator, rule, scoring, save, server, browser, or live
opponent behavior changed. Confidence HIGH that margin resolves many saturated
ties; confidence HIGH that it is insufficient for tactical admission alone.

## Batch 4 — Minimal tactical proposal/rollout ablation

Status: complete — neither candidate admitted; deep calibration blocked.

### Contract

**Behaviors:** add one rules-layer transition-priority recipe for immediate
capture, sole-liberty defense, Breath-run continuation, fence completion, pie
takeover, and accept/resume decisions. Generate each legal transition once per
guided decision point and reuse the selected transition. Use the ranking for
tree proposal order and rollout choice; back up only real terminal W/D/L and,
for the combined variant, normalized terminal margin.

**Build on:** seeded-hash ties are the correctness foundation. Freeze and run
two separately hashed variants on the identical V2 corpus: `tactical-only`
disables terminal margin, while `combined` retains it. The existing
`tie-margin` default and MCTS V4 hash stay byte-identical until evidence chooses
a replacement.

**Acceptance criteria:**

- [x] The transition-priority recipe exactly selects every acceptable action
  in all six proof-grade fixtures and leaves the analyzed state unchanged.
- [x] Legal transitions cover every legal action exactly once and preserve
  superko, swap identity, extension, finish, pass, resume, and accept semantics.
- [x] Tactical-only, combined, and retained tie-margin agents have distinct
  immutable hashes; manifests and records name the exact variant.
- [x] Two manifests are committed before either outcome set is inspected.
- [x] Both 4/16/64 jobs completed legally and non-mutating with exact telemetry;
  neither met the admission gate, so no candidate was selected.
- [x] Admission required at least `80%` pooled high-rung hits, every high-rung
  position/policy cell at least `75%`, monotonic policy ladders, and zero
  integrity failure. Diagnostic fixtures cannot veto proof-grade admission.
- [x] Neither variant passed; both negatives are preserved and deep-budget
  calibration rather than raising simulations.
- [x] Full tests, Python compile, JavaScript syntax, and diff checks pass.

**Blast radius:** the research action adapter gains a non-mutating legal-
transition generator; MCTS gains opt-in tactical variants and the admission
harness records their identifiers/hashes. The existing default remains MCTS V4
until a passing variant is selected. `engine/varde.py`, native evaluators,
server, browser, saves, scoring, and live termination remain untouched.

### Pre-implementation survey

- The six proof metrics can all be recovered from one legal-transition set:
  capture waves, pre-move one-liberty groups, post-takeover seat score,
  extension action kind, nearly closed cell boundaries, and accepted ending
  state. No evaluator score or nested legal-move scan is required.
- Proposal order alone is unlikely to help after all small roots are expanded;
  the same minimal priority therefore guides terminal rollouts whenever a
  positive immediate rule fact exists. When no fact exists, the declared
  uniform or epsilon-greedy policy remains the fallback.
- Guided expansion shuffles equal-priority actions once, then stores the order.
  The selected already-generated transition is reused; later untried actions
  use the stored priority order.
- Historical and default consumers continue to use `tie-margin`. The tactical
  variants are explicit opt-ins so no product or old research behavior changes
  before the admission result exists.

### Frozen evidence and result

- Both manifests were committed together at `062a69b` before either output
  directory existed. Tactical-only manifest SHA-256:
  `69c3ee6870019a2ba3800bb9b9ade4ba877d5b8d0b1f09af76847835b04f0ce9`;
  combined manifest SHA-256:
  `408e56d76ae8fdda879021a91b83894495342aa609d1ae5e6e0709ed722fbb20`.
- Tactical-only hash
  `e5a41b98d09d11df9f82e86515f93f7c0e6eea7eb9882ab9656d2bdd4fe60786`
  completed 384/384 decisions cleanly but scored only `54.1667%` at the
  high admission rung. Deterministic-record SHA-256:
  `168e473fab3c56c4861613eb61ebf9a6cf719a0574ba05ef34e9ae0be9540838`.
- Combined hash
  `431a03275d6c8bcff8613395c982b58791f1e6352409fdc00c556522bd1dfa64`
  also completed 384/384 cleanly and regressed to `41.6667%` admission.
  Deterministic-record SHA-256:
  `4e00a3dbc80795da5e430a7912cc3263a74c3ac1a96996778642261f65092816`.
- Both variants failed the `80%` pooled gate, the `75%` per-cell floor, and
  policy-ladder monotonicity. Sole-liberty defense remained `1/8` in both;
  combined fence completion fell to `0/8`.
- Guidance also created severe operational tails. At only 64 simulations,
  tactical-only uniform p95 was 91.3 s and combined uniform p95 146.2 s under
  the eight-worker run; a rollout reached 3,111 rules actions. Timing is
  observational, but rollout length is deterministic evidence of the cost
  mechanism.
- The exact proof priorities succeeding as unit facts while MCTS admission
  fails shows that proposal order and myopic rollout preference do not create a
  reliable terminal policy. More simulations would scale a failed and costly
  search, not repair it.
- Per the frozen plan, Batch 5 must record 2,048/4,096 calibration as blocked.
  No paired match, strength, balance, depth, or promotion claim is permitted.

### Regression attestation

Batch 4 adds opt-in research variants only. The retained default agent hash is
still MCTS V4 `4224495e…`, and its public decision dictionaries remain
compatible. The full 266-test suite passed in 31.993 s before the frozen jobs;
syntax, Ruff, and diff checks passed. No illegal action, mutation, crash, or
incomplete record occurred. Rules, scoring, native opponents, server, browser,
saves, and live termination are unchanged. Confidence HIGH that the tested
tactical guidance is inadmissible and operationally unsuitable for deep
scaling.

## Batch 5 — Calibrate the 2,048 or 4,096 deep tier

Status: complete — neither budget selected; deep jobs not run.

### Contract

**Behaviors:** apply the meaningful-budget prerequisite exactly as frozen. A
single-process 256/512/1,024/2,048 ladder is permitted only after Batch 4
admission; 4,096 is conditional on an admitted but unstable 2,048 result. When
admission fails, calculate and preserve the blocked decision from audited inputs
without launching deep searches or naming a tier.

**Acceptance criteria:**

- [x] Consume only hash-pinned Batch 4 compact results.
- [x] Record admission, integrity, feasibility, and rank-stability prerequisites
  separately rather than collapsing them into preference.
- [x] Record both candidate budgets explicitly as not run and why.
- [x] Preserve observational linear cost projections as warnings, not benchmark
  claims.
- [x] Select `neither`, expose no deep CLI/browser tier, and launch no process.
- [x] Add a payload-hash regression test and rerun all product checks.

**Blast radius:** compact research evidence, tests, and documentation only. No
MCTS behavior, evaluator CLI, product API, browser option, rule, save, or live
termination change.

### Evidence and decision

- Both prerequisite agents were integrity-clean but inadmissible:
  tactical-only `54.1667%`, combined `41.6667%`. This alone prohibits deep
  calibration under the frozen order.
- The deterministic cost mechanism reinforces the block. Both variants observed
  a 3,111-action uniform rollout at 64 simulations. Observational eight-worker
  uniform@64 p95 was 91.3 s and 146.2 s respectively.
- A deliberately simple linear projection—*not a benchmark*—puts uniform p95 at
  roughly 48.7/78.0 minutes per 2,048-simulation decision and 97.4/156.0 minutes
  per 4,096-simulation decision for tactical-only/combined. Search-tree growth
  and single-process scheduling could differ, so these numbers are warning
  scale only.
- The hash-pinned calibration artifact selects `neither` and records both deep
  jobs as `not-run-failed-admission-prerequisite`. Payload SHA-256:
  `92d07bb3dffe6bdd2a76983597fc036c8e116de6279a10ed51dc1ece13d3d62a`.
- No named deep research tier, CLI exposure, browser difficulty, paired match,
  or strength claim is created. This is the meaningful result required by the
  evidence: neither 2,048 nor 4,096 is justified for the tested search.

### Regression attestation

Batch 5 changes no executable behavior. The selected budget is null by design,
all blocked prerequisites are explicit, and no Varde research process was
launched. Confidence HIGH that the staged gate requires `neither`; no claim is
made about a future differently designed MCTS.
