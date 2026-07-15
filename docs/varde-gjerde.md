# Gjerde (experimental ruleset): claim the lines

`Game(n, rules="gjerde")` — Go-like play on the hex grid's **lines**
rather than its intersections. Mathematically this is breath-first Go
on the **kagome lattice** (the line graph of the honeycomb): each line
touches two lines at each endpoint, so interior lines have **four
liberties**, boundary lines three, and exactly six corner lines two.
The degree-3 pathology of the vertex game — two-contact atari,
unrunnable ladders — is repaired by geometry rather than by rules.

## Two resolution variants

`gjerde` uses breath-first resolution (suicide checked before
captures): any single enclosed line is unconditional life, so a
two-cell fence lives, there is no nakade, and ko shapes are illegal.
`gjerde-go` uses ordinary Go resolution (captures first): the
eye-fill capture returns, a two-cell fence dies, minimal life is a
three-cell fence with its two non-adjacent interior walls as eyes,
and cavity life-and-death plus ko come back (superko applies).

Breath-first was invented to repair the trivalent vertex game, where
eyes were nearly impossible to make; the kagome's four-liberty,
two-eye-capable geometry may not need the repair. Which variant plays
better is an open, empirical question — both are implemented, and
boards up to n=8 (169 cells) are available for either.

Historical exploratory probes of the split (same seeds, fence-aware Standard): under
`gjerde-go` the Standard still beat the greedy Attacker 8-0, but every
game was a **total wipe** — the greedy never builds two eyes, and
classic resolution kills everything eyeless, where breath had kept
margins to 1-13 cells. Standard mirrors came out sane in both
variants (gjerde-go 6 and 20 of 37; gjerde 5-8). Reading: breath acts
as Gjerde's wipe-dampener and forgiveness mechanism; classic
resolution restores nakade, ko, and Go's sterner life — sharper and
less forgiving. These results are **invalid as scoring evidence**: the scorer
then treated the unclaimed outer edge as closed and could award the entire
board after one exterior claim. They are retained only as design history and
must be rerun with the repaired scorer and independent agents.

## Rules

1. Players alternately claim empty lines. Lines meeting at a shared
   endpoint are one group; liberties are adjacent empty lines.
2. Breath-first resolution, as in the breath rulesets: a claim whose
   group has no liberty before removals is illegal; then opponent
   groups without liberties are removed.
3. **Score = fenced fields.** A connected region of hexagonal cells
   (cells adjacent through unclaimed lines) belongs to the player who
   claimed every line on its boundary. An unclaimed exterior line leaves
   the region open, so it scores nothing. Lines themselves score nothing.
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

## Historical exploratory probes (invalidated)

These 6-8-game conditions were hypothesis-generating probes, not balance
evidence. In addition, every score below predates the open-boundary repair and
is invalid for quantitative conclusions.

Greedy duels (attacker = capture/starve, defender = liberty-maximizer;
six per board size) and Balanced-mirror games:

| Probe | Result |
|---|---|
| Duels n=4 | attacker 6–0, margins 9–20 of 37 cells |
| Duels n=5 | attacker 6–0, margins 14–36 of 61 cells |
| Mirrors n=4 | margins 7–8 of 37 cells, 165–168 actions |
| Mirrors n=5 | margins 4–5 of 61 cells, 250–262 actions |

Caveats: the Toy board (19 cells) produced a mirror draw and is too
coarse to score — treat n=4 as the minimum real board. A second duel
round with a fence-aware greedy defender still lost 12-0: at one-ply
depth, killing outraces fencing.

The old two-ply fencer result was 8-0 across both colors and both board sizes,
but it consumed the defective score from move one. It therefore establishes
neither balance nor evaluator strength. No current Gjerde balance conclusion is
accepted. The qualitative observation that a heavy group can be starved by a
swarm remains a hypothesis for the repaired evaluation round.
