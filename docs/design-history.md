# Cairn — design history and playtest protocol

This document preserves the design lineage (formerly "Grounded Cairn"),
including retired claims and the playtest protocol. The rules in
`cairn-rules.md` are authoritative; this file explains why they are what
they are, and what remains open.

## How the design was reached

The game emerged from an adversarial exchange between two AI systems, each
round attacking the other's ruleset with concrete positions. Major stages:

1. **Cairn v1–v2** — global height-3 cap, surface control, universal skies.
   Broken: only full-height groups were capturable; capping was
   unconditionally legal; endgame cap–recap grind.
2. **Terrain ceiling (v3)** — "place only while the column is ≤ every
   neighbor" (human-proposed). Fixed unsupported capping; introduced
   capture-timing ambiguity (burial vs capture).
3. **Covered-stone priority / three-phase resolution (v4)** — later deleted
   whole: the [enemy, cap] removal ambiguity and a supported-boundary-cap
   erosion line broke two-eye life. An impossibility argument was framed:
   surface readability + enemy capping + classical life seemed jointly
   unsatisfiable.
4. **Dormant sky + majority summits (Grounded Cairn)** — both human-proposed.
   The dormant sky (a newborn stone cannot breathe through the sky it just
   created) made eye invasion suicide, deleting the phase machinery; the
   majority summit rule made capping shape-dependent. The "impossibility"
   was thereby refuted: the door never tried was regulating what a newborn
   stone may breathe.
5. **Well skies** — skies only where a column stands *strictly lower* than
   every neighbor (reviewer-proposed). Killed the Tripod (three stones
   around an empty point were unconditionally alive under plateau skies)
   and restored classical flat capture.
6. **Drafting rounds** — no-legal-first-move bug in the summit rule (fixed:
   ground placements exempt); pass/repetition interaction (fixed:
   placements only); resumption loop (fixed: once per game, normal turn
   order); plateau restatement of the summit rule; dormancy folded into the
   sky definition; formal territory regions; completed swap.

## Retired folklore (false claims — do not re-derive)

- **The Tripod**: three stones around an empty interior point are immortal —
  true under plateau skies, killed by well skies.
- **The pit-invasion burial line**: an invader in a one-point pit inside
  raised walls becomes a buried seed — false; it is illegal on the spot.
- **The six-column equal-core fortress**: premise void under well skies.
- **The n height ceiling**: true ceiling is 2n−1 (cell rings are not graph
  distance).
- **"Stacked groups are peeled, not erased"**: spacing-conditional; adjacent
  equal-height stacks shade each other's skies and cascade to erasure.
- **"Two eyes give classical life" / "one well is not life"** (2026-07-12,
  engine-verified): both are **collar-conditional**. A single well whose
  walls' outer neighbors stand at height ≥ 2 is unconditional life (peeled
  walls regenerate wells mid-cascade; the killing entry is suicide). The
  twin-well theorem requires the same high collar; low-collar twin wells
  are breachable core by core, erasing the breached core's private walls.
- **"Twin wells need 9 supports"**: exactly 8 — the hexagonal face through
  the two cores forces one shared collar point (verified across all 96
  sites at n = 3).
- **The peel-that-kills by tying**: nearly unconstructible (full erasure
  frees rescuing empties); the realizable mechanism is the doomed column
  stopping in a capture-created pit *below* the mover's column.

## What was tried and abandoned

Plateau skies (one eye suffices → collapse). Universal skies without
dormancy (every eye invadable). Hard height caps (parity discontinuity).
Finite stone reserves (exhaustion cliff: a player out of stones passes while
the opponent plays freely). Foundation scoring (contradicts surface
control; physically unreadable). Full 3D level-matched connectivity
(unreadable cascades). Tallest-neighbor terrain (unbounded ratchet).
Turn-forfeit caps (global tempo for a local act; turn-debt state).
Movement-based capping ("Crest" rules) — promising, but a separate game.
Square (degree-4) boards — both reviewers independently concluded degree 3
is load-bearing: tie-free majority, cheaper skies and pyramids, earlier
vertical ignition; a square version strengthens exactly the phase where the
game cannot beat Go.

## Open questions (playtest gates)

1. **Collar strategy** (new, from engine verification): either player can
   contest a well's collar — raising it makes the defender immortal, so the
   collar fight is a new strategic layer. Who profits, and does single-well-
   plus-collar life dominate all other life forms?
2. **k_well vs k_eye**: minimum enclosed region size for life under
   eye-only vs well-permitted defense (run at n = 4 — n = 3 underreports).
3. **Summit-rule variant**: "raise a plateau only if you already control
   it, or if it captures" — drops neighbor counting but deletes the
   supported hostile cap. A/B in self-play.
4. **Saturation equilibrium**: does optimal play avoid packing (openness is
   armor), starving the vertical game?
5. **Cap frequency**: greedy self-play sits at ~4%, just under the 5%
   decorative threshold — re-measure with real search.

## Metrics (operational definitions)

N = points on the board. *Opening phase* = first ⌊0.6N⌋ moves (move-count,
not occupancy). *Cap* = any placement on an occupied column. *Fight* =
maximal move sequence within graph distance 3 containing a capture or
atari. Rim capture *rate* = captures ÷ rim-stone-turns of exposure.

| Question | Metric | Healthy band | Failure |
|---|---|---|---|
| Stacking meaningful (late) | caps / moves after opening | 10–40% | <5% or >50% |
| Stacking restrained (early) | caps / opening moves | 0–10% | >20% |
| Well skies too generous | captures leaving a well survivor | 5–25% | >30% |
| Races readable | semeai reversals via post-peel skies | occasional | >25% |
| Waves manageable | capture waves per move | median 1, p95 ≤ 3 | p95 > 3 |
| Rim too hostile | rim vs interior capture rate | ≤ 2× | > 2× |
| Rim life too cheap | opening moves on rim+middle | < 60% | crowds interior |
| Simple ko sufficient OTB | long cycles / 100 games | <1 | ≥2 |
| Game length | total placements | 1.2N–2.5N | >3.5N |
| Board size | fights per game | ≥3 | <3 → n=5 |
| Swap balance | swap frequency; post-swap win rate | 35–65%; 45–55% | outside 25–75%; 40–60% |

Sample-size note: bands assume ≥100 games per condition.

## Engine status (2026-07-12)

`engine/cairn.py` implements the rules procedure and exposes each capture wave
separately. The executable suite covers the known collar-condition,
wall-stranding, eight-support twin-well, peel-that-kills, opening-placement,
swap-identity, and serialization cases. Self-play results are diagnostic only:
random, greedy, and epsilon-greedy policies do not establish strategic quality.
Run the harness to produce current placement counts, true per-wave size/depth,
superko blocks, and cap-frequency measurements.

Seeded n=3 runs on 2026-07-12 (100 games each, 8N-turn cutoff): random
terminated 46%, averaged 6.23N placements, and capped 48.2% of placements;
greedy terminated 100%, averaged 2.31N, and capped 4.3%; 15% epsilon-greedy
terminated 100%, averaged 3.02N, and capped 13.6%. Maximum cascade depth was
five waves under random play, and the largest single wave contained 53 stones.
These are policy baselines, not evidence of balance or fun.

## Local computer opponent (2026-07-12)

The playable client now includes Casual one-ply and Standard bounded two-ply
opponents. Both use fixed, inspectable features for controlled points, captures,
strict well skies, ordinary liberties, vulnerable groups, early development,
and late territory. They use the real resolver for legality and support the pie
rule, superko, passing, resumption, explanations, and compatible saves.

In 20 seeded n=3 mirror games per level, Casual ended all games before the 8N
test watchdog. Standard ended all games naturally, but one took 489 turns
(9.06N); no gameplay cutoff was added. This is an intentional distinction:
finite-state superko proves eventual termination, while the watchdog measures
whether a policy terminates within a practical experimental budget.

## Expanded playtest surface (2026-07-12)

The client now names the four supported lattices Toy (54 points), Beginner
(96), Intermediate (150), and Full (216). The projected lattice is 10% larger
than the original rendering and all stones and annotations share the original
Intermediate diameter-to-spacing ratio. This is a presentation change, not a
rules change.

Computer seats are now symmetric saved identities, enabling paused
computer-vs-computer playback with independent difficulty and speed controls.
Pie-rule takeover exchanges the complete seats, including seeds and difficulty.

Advanced adds a versioned, persistent linear correction to Standard's bounded
search. It begins at zero, trains in cancellable background self-play, and is
explicitly experimental. In the first small held-out diagnostic after eight
training games it scored 3 wins and 5 losses against Standard with colors
alternated. This does not demonstrate improvement and is not a release gate;
larger held-out samples should guide later feature and training changes.

## Corrected search and Advanced V2 (2026-07-12)

Standard's two-ply reply scan now treats pass as a legal opponent reply, both
after ordinary candidates and while evaluating a pie-rule takeover. Black
opening search also includes White's legal takeover as a reply. These are
search corrections, not rule changes; `engine/cairn.py` remains unchanged.

Computer-vs-computer endings now ask both persisted seat identities whether to
accept the first two-pass result. The first acceptance does not deny the other
seat its one legal resumption opportunity. Resuming clears both acceptances;
after that opportunity has been used, one acceptance finalizes the result.

Advanced V2 retains the six normalized evaluator terms and adds bounded stack
height, rim control, and group-consolidation features. It learns a margin-based
target from every second position after move six, weights later samples more,
and explores only on the learner's early moves. Training is deterministic over
a global attempt cursor, so split batches neither replay games nor change the
result. Version-1 models are retained and visibly marked for retraining rather
than silently discarded. Strength remains an empirical question governed by
the paired gate documented in `research/README.md`.

## Lineage and prior art (2026-07-13)

Cairn is a descendant of Go: groups, liberties, capture by surround, suicide,
positional superko, area scoring, and the pie rule are all inherited, and the
design should always say so plainly. Research into neighboring designs found
no game combining Cairn's terrain rule, summit majority, strict skies,
top-layer peeling with recursive capture waves, and collar-conditional life —
but it did find genuine neighbors that deserve acknowledgment:

- **Margo** (Cameron Browne) is the closest mechanical ancestor: Go-like
  connected groups and freedom-based capture played with stackable pieces,
  including buried pieces that outlive capture, suicide-with-capture, ko, and
  a swap rule. Cairn arrived at columns, skies, and peeling independently, but
  Margo owns the broad idea of "Go liberties plus vertical stacking."
- **Rosette** (Abstract Games issue 13, 2003) is a Go variant played on the
  intersections of a hexagonal tessellation — the same three-neighbor
  honeycomb topology as Cairn's board, with ordinary flat stones.
- **Tumbleweed** (Mike Zapawa) shares the hexagonal board, variable-height
  stacks, pie rule, and territorial scoring, though its line-of-sight
  mechanics involve no groups or liberties.

There is also a **naming collision**: *Cairn* (Christian Martinez, Matagot,
2019) is an existing two-player abstract strategy game. Its mechanics are
unrelated, but it occupies the same shelf. The working title will change
before any public promotion; until then this repository knowingly carries a
provisional name.
