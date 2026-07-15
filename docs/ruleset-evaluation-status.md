# Ruleset promise evaluation status

## Decision state

No Varde ruleset is promoted as the flagship. The implementation and evidence
pipeline are ready; the declared computational screens and human panel have not
been run. This is a deliberate blocked decision, not a negative verdict on the
candidates.

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
| Independent agent | Seeded terminal-score UCT supports play, pass, swap, extension, finish, both end decisions, and resumption with uniform and light rollouts. |
| Falsification CLI | Paired colors, budgets, sizes, seeds, workers, telemetry, cancellation, watchdog classification, JSONL, summary, checkpoint, and resume are implemented. |
| Reproducibility | Final artifacts are byte-identical after interruption and worker-count changes; tampered checkpoints fail closed. |
| Human study | Counterbalanced 8/10/12-player schedule, neutral briefs, engine-derived puzzles, post-game ratings, motif coding, and retention prompts are implemented. |
| Browser telemetry | Opt-in hotseat action/timing records export locally; no direct identifiers, wall-clock time, or server collection endpoint exist. |
| Product regression | 201 tests, Python syntax, JavaScript syntax, browser export/save/load/resumption/watch flows, and opened screenshots pass locally. |

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

## Evidence matrix

| Required stage | Status | Promotion use |
|---|---|---|
| Constructed tactical admission | Complete for both agent surfaces where applicable | Necessary implementation gate only |
| Cross-family operational smoke | Complete: one Toy pair per candidate | None |
| Calibration: 20 paired n=4 seeds | [Manifest frozen](../research/manifests/ruleset-calibration-20260715.json); timing feasibility measured, stage A awaiting exact-commit launch | None until complete |
| Health screen: 50 fresh paired seeds | Not run | None until complete |
| Confirmation: 100 fresh paired seeds | Not run | None until complete |
| MCTS 250 → 1,000 → 4,000 depth ladder | Not run | No depth claim |
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

Run the primary n=4 calibration outside the repository. The following expands
the two MCTS policies over all declared budgets and schedules every pair of
agents; choose an output path with adequate space:

```bash
python3 research/harness/evaluate_rulesets.py \
  --rulesets classic,rosette,breath,breath-run,gjerde,gjerde-go \
  --agents native-standard,mcts-uniform,mcts-light \
  --budgets 250,1000,4000 --pairs 20 --board-sizes 4 \
  --seed 20260715 --workers 8 --checkpoint-interval 2 \
  --output-dir /path/to/varde-calibration
```

This full cross-product is expensive. A staged operator may first run separate
native-versus-MCTS policy jobs at 250 and only launch the adjacent budget ladder
for candidates that pass basic correctness and health. Do not combine staged
jobs after inspecting outcomes unless the complete seed/configuration plan was
fixed before launch.

Resume the exact same job after interruption:

```bash
python3 research/harness/evaluate_rulesets.py \
  --rulesets classic,rosette,breath,breath-run,gjerde,gjerde-go \
  --agents native-standard,mcts-uniform,mcts-light \
  --budgets 250,1000,4000 --pairs 20 --board-sizes 4 \
  --seed 20260715 --workers 8 --checkpoint-interval 2 \
  --output-dir /path/to/varde-calibration --resume
```

Generate the panel package only for the best two or three computational
survivors:

```bash
python3 research/harness/human_study.py \
  --participants 8 --rulesets RULESET_A,RULESET_B \
  --games-per-ruleset 6 --output-dir /path/to/varde-human-study
```

## Best next steps

1. Freeze a predeclared calibration manifest with exact candidates, pair seeds,
   agent matchups, budgets, output path, and compute estimate.
2. Run 20-pair n=4 calibration first. Treat crashes, illegality, score
   contradictions, and incompletes as immediate failures; use other signals only
   to decide which measurements need scrutiny.
3. Review agent disagreement and position telemetry before spending the 50-pair
   screen. Improve an evaluator only through a new declared revision; never edit
   a candidate inside a measurement round.
4. Run the 50-pair health screen for survivors, then the adjacent-budget ladder.
   Archive variants that fail termination, wipe, opening, or ruleset-specific
   gates according to the one-refinement rule.
5. Use ruleset-native MAP-Elites adversarially on the remaining candidates.
6. Take only the best two or three computational survivors to the human protocol.
7. Promote one flagship only after the final high-budget, outside-play, forced-win,
   and complete negative-evidence publication gates pass.

The first operator decision is therefore not “which game wins?” It is “which
exact calibration manifest and compute window do we authorize?”
