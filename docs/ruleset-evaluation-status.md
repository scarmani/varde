# Ruleset promise evaluation status

## Decision state

No Varde ruleset is promoted as the flagship. The native-only diagnostic screen
is complete; independent-search, adversarial, and human evidence remain unrun.
This is a deliberate blocked decision, not a negative verdict on the candidates.

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
| Product regression | 228 tests, Python syntax, JavaScript syntax, browser export/save/load/resumption/watch flows, and opened screenshots pass locally. |

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

## Evidence matrix

| Required stage | Status | Promotion use |
|---|---|---|
| Constructed tactical admission | Complete for both agent surfaces where applicable | Necessary implementation gate only |
| Cross-family operational smoke | Complete: one Toy pair per candidate | None |
| Native operational screen: 20 paired n=4 seeds | Complete: 480 games across mixed and matched native jobs; zero operational failures; [diagnostic report](native-screening-v2-results.md) | Falsification and evaluator-artifact triage only |
| Independent shallow calibration | Historical [MCTS v1 manifest](../research/manifests/ruleset-calibration-20260715.json) produced no result; [v2 feasibility](../research/results/evidence-feasibility-gate-20260715.json) supports only a separately frozen 12/24 diagnostic | None until complete |
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

1. Add constructed regression positions for the Classic stagnation, Gjerde-Go
   wipe, and mixed Breath color/pie signatures before changing an evaluator.
2. Freeze a separate uniform-MCTS@12 versus native-Standard diagnostic with
   fresh paired seeds and the current source hashes. Do not pool its results.
3. Audit that job before launching light rollouts or the 24-simulation rung.
4. Review agent disagreement and position telemetry before spending the 50-pair
   screen. Improve an evaluator only through a new declared revision.
5. Run the 50-pair health screen and ruleset-native MAP-Elites only for
   computational survivors.
6. Take only the best two or three computational survivors to the human protocol.
7. Promote one flagship only after the final high-budget, outside-play,
   forced-win, and complete negative-evidence publication gates pass.

The next operator decision is the exact fresh-seed uniform-MCTS@12 diagnostic
manifest and compute window; it is not a choice of flagship.
