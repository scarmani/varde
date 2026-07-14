# Gjerde (experimental ruleset): claim the lines

`Game(n, rules="gjerde")` — Go-like play on the hex grid's **lines**
rather than its intersections. Mathematically this is breath-first Go
on the **kagome lattice** (the line graph of the honeycomb): each line
touches two lines at each endpoint, so interior lines have **four
liberties**, boundary lines three, and exactly six corner lines two.
The degree-3 pathology of the vertex game — two-contact atari,
unrunnable ladders — is repaired by geometry rather than by rules.

## Rules

1. Players alternately claim empty lines. Lines meeting at a shared
   endpoint are one group; liberties are adjacent empty lines.
2. Breath-first resolution, as in the breath rulesets: a claim whose
   group has no liberty before removals is illegal; then opponent
   groups without liberties are removed.
3. **Score = fenced fields.** A connected region of hexagonal cells
   (cells adjacent through unclaimed lines) belongs to the player who
   claimed every line on its boundary. Lines themselves score nothing.
4. Pie rule, superko, two-pass ending, and the stagnation rule apply
   unchanged.

## Structure (verified on the engine's boards)

| n | lines | cells | line degrees |
|---|---|---|---|
| 3 | 72 | 19 | 2×6 · 3×24 · 4×42 |
| 4 | 132 | 37 | 2×6 · 3×36 · 4×90 |
| 5 | 210 | 61 | 2×6 · 3×48 · 4×156 |
| 6 | 306 | 91 | 2×6 · 3×60 · 4×240 |

Emergent properties, tested:

- **A one-cell fence (6 lines) is a trap** — it encloses no line, so
  it has no eye and dies to an ordinary seal.
- **A two-cell fence (10 lines) is unconditional life** — the shared
  wall is an enclosed empty line, and under breath-first the last
  cavity point can never be filled. Life and territory are the same
  object and grow together.
- The three lines at any hex vertex are mutually adjacent: two of your
  lines meeting at a vertex are **uncuttable**. Connection is cheap;
  fighting shifts to blocking extension paths and weaving nets.
- One claimed line inside any prospective field poisons the whole
  region: **denial is far cheaper than enclosure**, so fences must be
  fought for, not just drawn.

## First playtest evidence

Greedy duels (attacker = capture/starve, defender = liberty-maximizer;
six per board size) and Balanced-mirror games:

| Probe | Result |
|---|---|
| Duels n=4 | attacker 6–0, margins 9–20 of 37 cells |
| Duels n=5 | attacker 6–0, margins 14–36 of 61 cells |
| Mirrors n=4 | margins 7–8 of 37 cells, 165–168 actions |
| Mirrors n=5 | margins 4–5 of 61 cells, 250–262 actions |

Caveats: the greedy defender's objective ignores fencing entirely, so
the duel sweep overstates the attack bias; the Toy board (19 cells)
produced a mirror draw and is too coarse to score — treat n=4 as the
minimum real board. In over-the-board play against the Attacker
profile, a single heavy group was netted and annihilated despite the
four-liberty geometry: liberties are shared resources, and a swarm of
cheap contact stones starves one big group faster than it can capture
back. Solidity (uncuttable stars) is not life; only enclosure is.
