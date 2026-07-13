# Cairn

Cairn is a two-player territory game on a honeycomb lattice. Players surround
territory, cover occupied columns, and use height-dependent sky liberties to
survive capture cascades.

This repository contains a tested Python reference engine, an instrumented
self-play harness, and a dependency-free local web client for human and
computer play.

## Play locally

```bash
python3 engine/server.py
```

Open <http://127.0.0.1:8000>. The client supports Toy (54), Beginner (96),
Intermediate (150), and Full (216) point boards; proportional stones; legal-move
highlighting; stack inspection; sky indicators; pie-rule takeover; stepwise
capture highlighting; passing and one-time resumption; scoring; fullscreen;
and versioned save/load files.

### Play against the computer

Choose **Vs computer**, select Black or White, choose **Casual**, **Standard**,
or **Advanced**, and start a new game. Casual uses varied one-ply choices;
Standard uses bounded two-ply minimax. Advanced uses the same bounded search
with a persistent learned linear correction. All levels use the rules engine's
real legality, skies, capture cascades, superko, pie rule, passing, and
resumption. Move explanations are optional and all computation stays local.

Choose **Watch two computers** for independent Black and White difficulties.
Spectator games start paused and provide Play/Pause, exactly-one-action Step,
and Slow/Normal/Fast playback. A loaded spectator save also starts paused.

Advanced begins with zero learned weights, so it initially behaves exactly like
Standard. The learning panel runs separate deterministic background self-play
batches of 10, 50, or 200 games and supports progress, cancellation, and reset.
The model is saved atomically at `~/.cairn/advanced-model.json`. Training uses a
20N operational watchdog and discards incomplete training games; playable games
have no move or turn cutoff. Version-1 models are retained, identified in the
UI, and require Reset before clean V2 retraining. Training count is not a
strength claim.

For installed commands:

```bash
python3 -m pip install -e . --no-deps
cairn-server
```

## Verify

```bash
python3 -m unittest discover -s engine -v
python3 -m pytest
python3 engine/selfplay.py 3 100 random
python3 engine/selfplay.py 3 100 greedy
python3 engine/selfplay.py 3 100 epsilon
```

The executable suite currently has 72 tests covering geometry, terrain,
summits, flat capture, collar-dependent wells, wall stranding, eight-support
twin wells, multi-wave peeling, global mover-suicide, full-stack superko,
opening placement, pie-rule identity, resumption, scoring, serialization, and
the browser-facing public state, two computer seats, legacy saves, deterministic
Advanced evaluation, model persistence, and training cancellation.

The `8N` limit used by diagnostic self-play is a watchdog for comparing
policies, not a game rule or playable-program ceiling. Full-superko Cairn is
mathematically finite because terrain bounds every stack height and placements
cannot repeat a recorded position. A policy that reaches the watchdog is
reported as a long game; the application does not force it to end.

## Current diagnostic baseline

Seeded n=3 runs, 100 games per policy, cutoff at 8N turns:

| Policy | Finished | Placements | Cap share | Wave depth | Largest wave |
|---|---:|---:|---:|---:|---:|
| Random | 46% | 6.23N mean | 48.2% | max 5 | 53 |
| Greedy | 100% | 2.31N mean | 4.3% | max 1 | 11 |
| 15% epsilon-greedy | 100% | 3.02N mean | 13.6% | max 2 | 37 |

These policies diagnose engine behavior; they do not establish balance or
strategic quality. Greedy termination is partly induced by its rule to pass
when no placement immediately improves area score. Epsilon-greedy is the most
useful current smoke-test baseline: it activates stacking without producing
the random policy's cap-heavy grind.

### Computer-opponent validation

Twenty seeded n=3 computer-vs-computer games per level produced no illegal
actions or crashes. Casual finished 20/20 before the 8N watchdog (median 181.5,
maximum 236 turns). Standard also finished 20/20 naturally; 19 finished before
8N and one finished at 489 turns (9.06N), demonstrating why 8N is reported as
a measurement boundary rather than enforced as a rule. Standard decision p95
was about 30 ms during complete games; fresh-position p95 was about 27 ms at
n=3 and 196 ms at n=5, below the 500/1500 ms targets.

Fresh-position checks after adding Full and Advanced measured p95 decision times
of about 26 ms (Standard) and 44 ms (Advanced) on Toy, and 411 ms / 682 ms on
Full. A small held-out diagnostic after eight training games produced 3 wins and
5 losses for Advanced against Standard with colors alternated. That sample is
deliberately reported as evidence that the learning loop runs—not as evidence
that Advanced is stronger.

After correcting the reply search and retraining V2 from zero for 200 games, a
fresh 200-game paired gate scored 52.5% overall: 56.33% on Toy, 41.0% on
Beginner, one-sided 95% paired-bootstrap lower bound 47.0%, and average margin
-1.15. All games completed legally, but four strength criteria failed, so
Advanced remains experimental. Current fresh-position p95 is about 30/55 ms on
Toy and 388/737 ms on Full for Standard/Advanced. Reproduction commands and
the exact model checkpoint are in `research/`.

## Layout

- `docs/cairn-rules.md` — standalone rules, revision 1.2
- `docs/design-history.md` — design lineage, retired claims, and playtest gates
- `engine/cairn.py` — reference rules engine and versioned snapshots
- `engine/opponent.py` — local Casual, Standard, and Advanced computer opponent
- `engine/learning.py` — persistent linear model and background self-play trainer
- `engine/test_cairn.py` — known-answer position and controller tests
- `engine/selfplay.py` — random, greedy, and epsilon-greedy telemetry
- `engine/server.py` — local JSON API and static-file server
- `research/` — reproducible V2 training, paired evaluation, and checkpoints
- `web/` — responsive canvas hotseat client
- `progress.md` — implementation and handoff log

## What remains experimental

The software is playable, but the game design is not declared final. Human
playtests must still evaluate collar strategy, well life versus classical eyes,
the summit-rule variant, saturation avoidance, board size, and swap balance.
MCTS should follow human usability testing rather than precede it.
