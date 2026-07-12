# Cairn

Cairn is a two-player territory game on a honeycomb lattice. Players surround
territory, cover occupied columns, and use height-dependent sky liberties to
survive capture cascades.

This repository contains a tested Python reference engine, an instrumented
self-play harness, and a dependency-free local hotseat web client.

## Play locally

```bash
python3 engine/server.py
```

Open <http://127.0.0.1:8000>. The client supports learning, standard, and long
boards; legal-move highlighting; stack inspection; sky indicators; pie-rule
takeover; stepwise capture highlighting; passing and one-time resumption;
scoring; fullscreen; and versioned save/load files.

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

The executable suite currently has 35 tests covering geometry, terrain,
summits, flat capture, collar-dependent wells, wall stranding, eight-support
twin wells, multi-wave peeling, global mover-suicide, full-stack superko,
opening placement, pie-rule identity, resumption, scoring, serialization, and
the browser-facing public state.

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

## Layout

- `docs/cairn-rules.md` — standalone rules, revision 1.2
- `docs/design-history.md` — design lineage, retired claims, and playtest gates
- `engine/cairn.py` — reference rules engine and versioned snapshots
- `engine/test_cairn.py` — known-answer position and controller tests
- `engine/selfplay.py` — random, greedy, and epsilon-greedy telemetry
- `engine/server.py` — local JSON API and static-file server
- `web/` — responsive canvas hotseat client
- `progress.md` — implementation and handoff log

## What remains experimental

The software is playable, but the game design is not declared final. Human
playtests must still evaluate collar strategy, well life versus classical eyes,
the summit-rule variant, saturation avoidance, board size, and swap balance.
MCTS should follow human usability testing rather than precede it.
