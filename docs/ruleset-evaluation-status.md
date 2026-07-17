# Ruleset promise evaluation status

## Decision state

No Varde ruleset is promoted as the flagship. The native-only screen, first
independent uniform-MCTS@12 diagnostic, and staged Search V3 tactical admission
program are complete. Every tested independent agent failed tactical admission,
and
adversarial and human evidence remain unrun. This is a deliberate blocked
decision, not a negative verdict on the candidates.

The current branch repairs the known Gjerde scoring defect, freezes six
candidate revisions, separates each native evaluator from other rulesets'
artifacts, adds independent terminal-score MCTS, and makes both machine and
human evidence reproducible. It does not turn operational smoke into claims of
balance, depth, emergence, elegance, or beauty.

## Implemented and verified

| Surface | Current evidence |
|---|---|
| Rules correctness | Gjerde open-boundary scoring repaired; edge, partial, complete, interior, mixed, and Gjerde-Go parity fixtures pass. |
| Candidate freeze | `classic-1.3`, `rosette-0.1`, `breath-0.1`, `breath-run-0.1`, `gjerde-breath-0.1`, and `gjerde-go-0.1` are public candidates. |
| Research-only variants | Breath rescue is a control; extension variants are archived; Breath cap is broken. Old saves still load. |
| Evaluator firewall | Six hash-pinned native evaluators pass constructed mechanics fixtures; literal Classic seeded behavior is unchanged. |
| Independent agent | Seeded terminal-score UCT supports every rules action. Search V3 removed coordinate ties, added terminal-margin telemetry, and tested two opt-in tactical-guidance variants; the best proof-grade high-rung result was 60.42%, below the 80% gate. |
| Decision telemetry | Research records every root action's visits, W/D/L, raw and normalized terminal margin, rank, selection reason, rollout length, nodes, latency, and tactical choice without mutating analyzed positions. |
| Falsification CLI | Paired colors, budgets, sizes, seeds, workers, telemetry, cancellation, watchdog classification, JSONL, summary, checkpoint, and resume are implemented. |
| Reproducibility | Schedules and decisions are deterministic after excluding observational latency; checkpoints resume in order and fail closed on tampering. |
| Human study | Counterbalanced 8/10/12-player schedule, neutral briefs, engine-derived puzzles, post-game ratings, motif coding, and retention prompts are implemented. |
| Browser telemetry | Opt-in hotseat action/timing records export locally; no direct identifiers, wall-clock time, or server collection endpoint exist. |
| Product regression | 268 Python tests pass; Python and JavaScript syntax checks pass. Existing browser export/save/load/resumption/watch evidence is unchanged because this unit has no browser or live-game behavior change. |

## Native screening v2

The frozen [native manifest](../research/manifests/native-screening-v2-20260715.json)
completed 480 n=4 games: 20 paired seeds per candidate for Casual-versus-Standard
and matched Standard self-play. All games completed with zero illegal actions,
crashes, watchdog incompletes, or pending records. The compact
[audit](../research/results/native-screening-v2-20260715.json) is hash-linked to
raw artifacts outside the repository and keeps flagship promotion blocked.

The [diagnostic report](native-screening-v2-results.md) identifies Breath and
Gjerde as the cleanest matched-agent strata, severe Classic stagnation,
Breath-run and Gjerde-Go wipe concerns, and strong Casual/Standard asymmetry.
These are one-family, 20-pair findings. They do not establish balance, depth, or
candidate elimination.

## Generated operational smoke

The committed [operational smoke](../research/results/ruleset-promise-operational-smoke.json)
used one paired Toy seed per candidate: Casual native search versus uniform MCTS
with one simulation per action. All 12 games completed with zero illegal action,
crash, or research-watchdog incomplete. Every stratum has only one pair and
`headline_eligible=false`; `promotion_blocked=true`.

The extreme outcomes in this smoke are reasons not to interpret it. Native
Casual scored 100% against a one-simulation opponent, wipe rates were 50–100%,
and one Classic leg ended through the twelve-quiet-move rule. These observations
say that the harness records adverse telemetry and that one-simulation MCTS is
not a useful opponent. They say nothing reliable about the candidates.

## Uniform MCTS@12 diagnostic

The separately frozen
[manifest](../research/manifests/uniform-mcts12-20260716.json) completed 240 n=4
games: native Standard versus uniform terminal-score MCTS@12 over 20 paired
seeds per candidate. All games completed with zero illegal actions, crashes,
watchdog incompletes, or pending records. The compact
[audit](../research/results/uniform-mcts12-20260716.json) verifies exact config,
schedule, provenance, ordered records, and raw artifact hashes.

The [diagnostic report](uniform-mcts12-results.md) rejects the agent as a
strategic comparison surface: native Standard scored 88.75-100% in every
stratum and 97.7% overall. This does not prove the native evaluator is strong or
that any candidate is weak. It proves that simply increasing this uniform
terminal UCT's budget is not yet a justified evidence program.

## Evidence matrix

| Required stage | Status | Promotion use |
|---|---|---|
| Constructed tactical admission | Search V3 completed four clean 384-decision split-corpus runs; proof-grade high-rung rates were 60.42%, 54.17%, 52.08%, 54.17%, and 41.67% across the behavior-neutral baseline and isolated/combined variants | Necessary implementation gate only; blocks further paired MCTS |
| Cross-family operational smoke | Complete: one Toy pair per candidate | None |
| Native operational screen: 20 paired n=4 seeds | Complete: 480 games across mixed and matched native jobs; zero operational failures; [diagnostic report](native-screening-v2-results.md) | Falsification and evaluator-artifact triage only |
| Independent shallow calibration | Uniform MCTS@12 completed 240 games and audited cleanly, but failed strategic admission: native scored 97.7% overall | Operational/action-plumbing evidence only; repair agent before another match batch |
| Health screen: 50 fresh paired seeds | Not run | None until complete |
| Confirmation: 100 fresh paired seeds | Not run | None until complete |
| MCTS 2,048 / 4,096 deep calibration | Neither selected; both jobs were blocked before launch by failed admission and severe 64-simulation rollout-cost tails | No named tier or depth claim |
| Uniform versus light rollout stability | Not run at admissible sample | All outcomes provisional |
| Single-purpose exploit policies | Not run under the frozen revisions | No degeneration-resistance claim |
| Ruleset-native MAP-Elites exploit search | Not run; the deterministic V3 archive is retained, while native descriptors/adapters are instantiated only after a ruleset survives health screening | No strategic-diversity claim |
| Intermediate/n=5 confirmation | Not run | No size-generalization claim |
| Human panel of 8–12 players | Instrumented, not recruited or run | No readability, emergence, or beauty claim |
| One-week retention | Instrumented, not run | No memorability claim |
| Final 100-pair high-budget gate | Not run | No flagship promotion |
| Twenty outside-project games | Not run | No public promotion |

Existing 6–8-game reports remain exploratory historical probes. All Gjerde
numbers from before the open-boundary scorer repair remain quantitatively
invalid.

## Reproduction commands

The exact completed native commands are frozen in
`research/manifests/native-screening-v2-20260715.json`. Inspect their argv,
schedule hashes, and external output paths before reproducing them:

```bash
jq '.jobs[] | {id, argv, config_sha256, schedule_sha256}' \
  research/manifests/native-screening-v2-20260715.json
```

Run each recorded argv only from a clean output root. If interrupted, append
`--resume` to that same job without changing any other argument. Audit both
complete jobs with the frozen command:

```bash
python3 research/harness/audit_native_screening.py \
  --manifest research/manifests/native-screening-v2-20260715.json \
  --output research/results/native-screening-v2-20260715.json
```

Reproduce or inspect the uniform-MCTS@12 diagnostic through its frozen manifest:

```bash
jq '.jobs[0] | {argv, config_sha256, schedule_sha256}' \
  research/manifests/uniform-mcts12-20260716.json

python3 research/harness/audit_uniform_mcts12.py \
  --manifest research/manifests/uniform-mcts12-20260716.json \
  --output research/results/uniform-mcts12-20260716.json
```

Inspect and audit the tactical-admission decision ladder through its separately
frozen manifest:

```bash
jq '{config, config_sha256, schedule_sha256, execution}' \
  research/manifests/mcts-tactical-admission-20260716.json

python3 research/harness/audit_mcts_tactical_admission.py \
  --manifest research/manifests/mcts-tactical-admission-20260716.json \
  --output research/results/mcts-tactical-admission-20260716.json
```

The 24/250/1,000/4,000 MCTS ladder is not yet a reproduction command. Although
the @12 operational audit is clean, the agent failed strategic admission. Any
later match work requires a new manifest, fresh seeds, a separate raw output
root, and a search policy that first passes constructed tactical fixtures.

Validate the compact artifact and the rest of the engine with:

```bash
python3 -m unittest discover -s engine -v
```

Generate the panel package only for the best two or three computational
survivors:

```bash
python3 research/harness/human_study.py \
  --participants 8 --rulesets RULESET_A,RULESET_B \
  --games-per-ruleset 6 --output-dir /path/to/varde-human-study
```

## Best next steps

1. Expose per-root-action visits, outcome counts, terminal margin, and selected
   rank; the existing aggregate telemetry has localized root under-sampling but
   cannot show each acceptable action's backed evidence.
2. Split the fixture corpus into dominance-proven small-root admission puzzles
   and the current natural-width behavior diagnostics.
3. Remove coordinate-biased final ties with a deterministic position/action
   hash, then ablate terminal-margin backup and a minimal rules-layer tactical
   proposal policy separately on held-out fixtures.
4. Freeze another paired job only after one version passes admission and a
   single-process timing check; current uniform @24 and light matches remain
   blocked.
5. Review agent disagreement before spending the 50-pair screen. Improve a
   native evaluator only through a new declared revision.
6. Run the 50-pair health screen and ruleset-native MAP-Elites only for
   computational survivors.
7. Take only the best two or three computational survivors to the human protocol.
8. Promote one flagship only after the final high-budget, outside-play,
   forced-win, and complete negative-evidence publication gates pass.

The next operator decision is whether to fund a different MCTS architecture.
The tested tie, terminal-margin, and myopic tactical-guidance repairs are
insufficient; neither 2,048 nor 4,096 is justified. It is not a choice of
flagship or a larger simulation budget.
