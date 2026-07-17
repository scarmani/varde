# Advanced AI research

This directory preserves Claude's original directional results and provides a
repository-relative harness for the corrected Advanced V2 implementation.
Everything is local and deterministic; operational watchdogs report incomplete
experiments and never alter live game rules.

## Historical evidence from commit 6fb779c

Claude trained the original pipeline and an experimental nine-feature recipe
for 120 Toy games, then ran 40-game Toy-only held-out evaluations:

| Variant | Score vs Standard | Average margin |
|---|---:|---:|
| Stock Advanced | 45% | -6.8 |
| Experimental V1 learner | 59% | +5.2 |
| Pass-aware reply scan | 66% | +12.5 |
| V1 plus pass-aware scan | 58% | +4.2 |

These numbers are directional, not release evidence. The old harness asked only
the side to move whether to resume after the first two-pass ending, evaluated
Toy only, and used hard-coded temporary paths. The corrected implementation now
scores pass in both reply paths, considers opening takeover, and gives both
computer seats their legal resumption opportunity before retraining.

The original small checkpoints remain in `models/`; see `models/MANIFEST.md`.
They are never loaded by the application.

## Reproducible V2 workflow

Run commands from the repository root. Output paths are explicit and default to
`/tmp/varde-v2`, keeping generated evidence out of the source tree.

```bash
python3 research/harness/train_v2.py \
  --games 200 --seed 20260712 --output-dir /tmp/varde-v2

python3 research/harness/evaluate_v2.py \
  /tmp/varde-v2/advanced-model-v2.json \
  --toy-pairs 75 --beginner-pairs 25 --seed 9102026 \
  --output-dir /tmp/varde-v2

python3 research/harness/benchmark_v2.py \
  /tmp/varde-v2/advanced-model-v2.json \
  --samples 20 --output /tmp/varde-v2/benchmark.json

python3 research/harness/smoke_v2.py \
  /tmp/varde-v2/advanced-model-v2.json \
  --pairs 2 --output /tmp/varde-v2/smoke.json
```

Training logs every global attempt to `training.jsonl`; evaluation logs every
paired seed to `heldout.jsonl`. Summary JSON records the source commit, complete
configuration, model SHA-256, counters, and gate criteria.

## Strength gate

The predeclared evaluation uses 100 paired seeds: 75 Toy and 25 Beginner. The
same seed is played twice with Advanced assigned each initial color. A stronger
claim requires all of the following:

- overall score at least 60%;
- Toy and Beginner strata each above 50%;
- one-sided 95% paired-bootstrap lower bound above 50%;
- positive average margin;
- zero illegal, crashed, or watchdog-incomplete games.

If any condition fails, Advanced remains explicitly experimental. Intermediate
and Full smoke matches are non-claim generalization checks because the learner
trains only on the deterministic 3:1 Toy/Beginner mix.

## V2 result (200 training games)

The fresh V2 run completed all 200 training attempts with no discard. The
frozen model (`SHA-256 a6f122d158b510db550f453623db3248ccd8f3e0c473eeaa0b7d756eb34a1f58`)
then completed all 200 held-out games:

| Measurement | Result | Gate |
|---|---:|---:|
| Overall score | 52.5% | fail (needs 60%) |
| Toy score | 56.33% | pass (above 50%) |
| Beginner score | 41.0% | fail (above 50%) |
| One-sided 95% paired-bootstrap lower bound | 47.0% | fail (above 50%) |
| Average margin | -1.15 | fail (positive) |
| Illegal, crashed, or incomplete games | 0 | pass |

Advanced V2 therefore does **not** earn a stronger-than-Standard claim and
remains experimental. Fresh-position p95 was 30/55 ms on Toy and 388/737 ms
on Full for Standard/Advanced, within both performance budgets. Two
Intermediate and two Full non-claim games all completed; the longest Full
game took 1,405 actions, further supporting the decision not to impose a live
game cutoff.

The exact checkpoint and compact aggregate are retained in `results/`. Raw
per-attempt and per-pair JSONL from this run was generated outside the tree at
`/tmp/varde-v2-final` and can be reproduced with the commands above.

## Evaluator Profiles V3 quality-diversity search

**Final outcome (2026-07-14).** The declared run is complete: 4,096 candidates,
32,768 games, 219/256 occupied cells, six watchdog rejections, one permitted
refinement consumed. Mason and Surveyor passed their 100-pair gates and ship in
the catalog; Raider (held-out engagement moved the wrong way) and Weaver (below
the strength floor) are recorded as unavailable with reasons. The compact
committed record is `research/results/v3-final-evidence-summary.json`; the raw
archive checkpoint is retained outside the repository and pinned by sha256 in
that summary. The commands below remain for reproduction.

The V3 harness searches evaluator weights, never search depth or public
difficulty. Its default run evaluates 512 deterministic calibration genomes
and 1,536 archive mutations with four paired seeds per candidate (three Toy,
one Beginner):

```bash
python3 research/harness/map_elites_v3.py \
  --output-dir /tmp/varde-map-elites-v3 \
  --seed 20260713 --workers 8 --checkpoint-interval 128
```

Resume the same canonical run after an interruption, optionally with a
different worker count:

```bash
python3 research/harness/map_elites_v3.py \
  --output-dir /tmp/varde-map-elites-v3 \
  --seed 20260713 --workers 4 --checkpoint-interval 128 --resume
```

Candidate ids determine genomes, parents, opponents, and paired game seeds.
The hall of fame is frozen for each deterministic 128-candidate batch, worker
results are committed in candidate-id order, and pending tasks are included in
the atomic checkpoint. Consequently, a resumed run and an uninterrupted run
produce byte-identical `state.json` evidence. The state includes every game,
descriptor, rejection, archive replacement, source/code hash, genome/result
hash, and the four calibrated bin boundaries.

Create the optional cancel file passed with `--cancel-file` to stop at a safe
checkpoint. A later `--resume` continues the same scheduled tasks. The 20N
watchdog is research-only: an incomplete rollout rejects its candidate and is
recorded; it never changes a live game.

### V3 audit, ablation, curation, and gates

Generate the declared 2,000-position audit and the three paired evaluator
ablations before starting the archive. Rejected V3 candidates remain telemetry
with immutable zero search weight:

```bash
python3 research/harness/audit_v3.py \
  --output-dir /tmp/varde-audit-v3 --seed 20260713 --workers 8

python3 research/harness/ablate_v3.py \
  --output-dir /tmp/varde-ablation-v3 --seed 20260713 --workers 8 \
  --toy-pairs 40 --beginner-pairs 20 --difficulty standard

python3 research/harness/map_elites_v3.py \
  --output-dir /tmp/varde-map-elites-v3 --seed 20260713 --workers 16 \
  --checkpoint-interval 128 \
  --audit-report /tmp/varde-audit-v3/audit-v3.json

python3 research/harness/curate_v3.py \
  /tmp/varde-map-elites-v3/state.json \
  /tmp/varde-audit-v3/audit-v3.json \
  --output /tmp/varde-map-elites-v3/curation-v3.json
```

If and only if curation reports a missing profile, perform the plan's one
additional 2,048-mutation refinement by extending the total mutation target
from 1,536 to 3,584:

```bash
python3 research/harness/map_elites_v3.py \
  --output-dir /tmp/varde-map-elites-v3 --seed 20260713 --workers 16 \
  --checkpoint-interval 128 --mutations 3584 --resume \
  --audit-report /tmp/varde-audit-v3/audit-v3.json
```

After rerunning curation, the final paired release gate is:

```bash
python3 research/harness/gate_profiles_v3.py \
  /tmp/varde-map-elites-v3/curation-v3.json \
  --output /tmp/varde-map-elites-v3/profile-gates-v3.json \
  --seed 20260713 --workers 16 --toy-pairs 75 --beginner-pairs 25
```

The curator never relaxes the declared descriptor shifts or normalized-distance
threshold. It reports a profile missing when no eligible elite exists. The gate
uses separate Balanced reference games on the same seeds and requires the
strength floors, descriptor shifts in both colors and strata, effect size, and
pairwise diversity before a curated profile can be exposed by the application.

## Frozen-ruleset falsification harness

`evaluate_rulesets.py` compares the six frozen candidate revisions with paired
colors. It supports ruleset-native bounded search and terminal-score-only MCTS
with uniform or light epsilon-greedy rollouts. Generated output stays outside
the repository by default. A small explicit run is:

```bash
python3 research/harness/evaluate_rulesets.py \
  --rulesets classic,breath \
  --agents native-standard,mcts-uniform,mcts-light \
  --budgets 250,1000 --pairs 20 --board-sizes 4 \
  --workers 8 --checkpoint-interval 4 \
  --output-dir /path/to/varde-screening
```

Pass `--telemetry` when per-move actions and score changes are needed. Create
the path supplied to `--cancel-file` to stop safely, then remove it and repeat
the same command with `--resume`. Candidate and paired-game ids own every seed;
worker count and checkpoint interval do not affect the canonical result. A
completed resumed run is byte-identical to one uninterrupted run in
`state.json`, `games.jsonl`, and `summary.json`.

The summary reports failures, research-watchdog incompletes, paired confidence,
color/swap/ending health gates, behavior telemetry, and direct adjacent-budget
MCTS comparisons. It blocks headline claims until both rollout policies have a
100-pair cross-family stratum and two complete 100-pair adjacent-budget
comparisons, and the declared health gates pass. Empty strategic fields are
explicit measurement gaps rather than inferred evidence. The watchdog
classifies research attempts only and is never applied to a live game.

The committed `results/ruleset-promise-operational-smoke.json` is a deliberately
non-claim integration check: one paired Toy seed per frozen candidate, Casual
native search, and uniform MCTS with one simulation per action. All 12 games
completed legally, but every stratum is headline-ineligible and promotion stays
blocked. The exact implemented/unrun evidence matrix and next commands are in
`docs/ruleset-evaluation-status.md`.

## Search V3 tactical admission

The staged Search V3 follow-up is summarized in
`docs/mcts-tactical-admission-results.md`. Its split proof corpus and isolated
tie, terminal-margin, tactical-only, and combined agents all failed admission.
The compact `results/mcts-deep-tier-calibration-20260717.json` therefore selects
neither 2,048 nor 4,096 and records that no deep or paired job was launched.
These are negative agent results, not ruleset evidence.
