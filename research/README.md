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
`/tmp/cairn-v2`, keeping generated evidence out of the source tree.

```bash
python3 research/harness/train_v2.py \
  --games 200 --seed 20260712 --output-dir /tmp/cairn-v2

python3 research/harness/evaluate_v2.py \
  /tmp/cairn-v2/advanced-model-v2.json \
  --toy-pairs 75 --beginner-pairs 25 --seed 9102026 \
  --output-dir /tmp/cairn-v2

python3 research/harness/benchmark_v2.py \
  /tmp/cairn-v2/advanced-model-v2.json \
  --samples 20 --output /tmp/cairn-v2/benchmark.json

python3 research/harness/smoke_v2.py \
  /tmp/cairn-v2/advanced-model-v2.json \
  --pairs 2 --output /tmp/cairn-v2/smoke.json
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
`/tmp/cairn-v2-final` and can be reproduced with the commands above.
