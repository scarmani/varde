# Varde

*Formerly the working title "Cairn"; renamed 2026-07-13. Some file and
format identifiers retain the old name for compatibility.*

A game of territory for two players, Black and White, played with stackable stones on the intersections of a hexagonal board.

---

## The board

The board is a hexagon-shaped patch of the honeycomb lattice, *n* cells per side, played on its 6n² intersections (*points*). Every interior point has three neighbors. A point with a missing off-board neighbor is a **rim** point; each missing neighbor counts as a *phantom column* of permanent height zero — it affects heights, but is never occupied, never a liberty, never territory, and never borders a region. The board's visible edge alternates between rim points (6n of them) and ordinary three-neighbor points, except at the six corners, where two rim points sit side by side.

Board sizes: **Toy**, n = 3 (54 points); **Beginner**, n = 4 (96 points); **Intermediate**, n = 5 (150 points); and **Full**, n = 6 (216 points).

Stones are flat counters, stackable, their color visible from the side of a stack. Captured stones return to their owner. A supply of about one and a half stones per point, per color, covers practical play; the theoretical ceiling is higher (300 stones total at n = 4), so serious play may prefer a digital board.

## Columns

Every point carries a column of stones — possibly empty. A point is **occupied** when its column has height one or more. Each occupied column is **controlled** by the color of its top stone; stones beneath the top are buried, and buried stones do nothing until uncovered.

Placing a stone always adds to a column; it never removes what lies beneath. **Covering is not capture.** Stones leave the board only through the capture rule.

## Playing

Black moves first, then the players alternate. A move is one placement, or a pass.

**Terrain.** A stone may be placed on any column, yours or your opponent's, whose height is no greater than that of each of its neighbors. A placement never raises a column more than one above its lowest neighbor. (Captures may later lower the surroundings and leave cliffs standing; the terrain rule constrains placements only.)

**Summits.** A placement is a *summit* when the target column and all three of its neighbors are occupied at the same height. A summit is legal only if you control at least two of the three neighbors, or if it captures — that is, if it leaves some enemy group without a liberty the moment the stone lands, before any removal. No summit can arise on the rim, since a phantom column is never occupied. (This rule is what keeps a packed wall from being flipped, stone by stone, by an unsupported attacker.)

## Groups and liberties

A group is a maximal set of connected columns of one color. Connection runs along the board's lines only; height plays no part in it.

A group has a liberty at:

- every empty point adjacent to it, and
- every **sky** — the space above one of its own columns that stands strictly lower than all of its neighbors, *provided that column's top stone was not placed this turn*.

The rules never ask how many liberties a group has — only whether it has any.

## Resolving a placement

1. **Terrain.** The target column's height must not exceed that of any neighbor.
2. **Place** the stone provisionally. It controls its column at once. (By the sky rule, this stone's own column has no sky at any step below.)
3. **Summit.** If the placement is a summit, it must hold the two-of-three majority — or some enemy group must, at this moment, be without a liberty.
4. **Capture.** Remove the top stone of every column of every enemy group without a liberty, all such groups at once. Uncovered stones take control of their columns immediately. Recount heights, groups, and liberties, and repeat until every enemy group has a liberty.
5. **Suicide.** If any group of yours — any of them, not only the new stone's — is now without a liberty, the placement is illegal and the position is restored.
6. **Repetition.** If the resulting position (see below) has occurred before, the placement is illegal. Otherwise the move is complete and the turn passes.

## Repetition

A *position* is the complete ordered contents of every stack together with the player to move. Record the position at the start of the game and after every move, passes included. A placement is illegal if, after resolution and with the opponent to move, it would recreate a recorded position. Passes are always legal; the positions they produce simply enter the record.

*Casual over-the-board play* may replace this with: no placement may recreate the position that stood just before the opponent's last placement; and either player may claim a draw when any position is about to occur for the third time.

## The end

Two consecutive passes end the game.

Once per game, either player may then demand that play resume instead. Play continues in normal turn order — the player after the second pass moves — and the game ends finally upon the next two consecutive passes.

**Stagnation.** A move is *quiet* when it is a pass, or a placement that captures nothing and changes no column's control — that is, a placement onto a column the mover already controls. Twelve consecutive quiet moves end the game at once, and this ending is final: resumption may not be demanded, since twelve quiet moves are themselves the proof that neither player can make progress. (Placing on an empty point, covering an enemy column, and any capture all reset the count. Height alone scores nothing, so a game that has stopped exchanging control has stopped mattering; this rule merely writes that fact down. A player who believes progress is still possible need only make one progressing move every twelve.)

**Score.** One point for each point you control. Then take each *empty region* — a maximal connected set of empty points — and its *border*, the occupied points adjacent to it: if the border is not empty and belongs entirely to one color, that color scores every point of the region. Regions bordered by both colors, or by nothing, count for no one. Height is worth nothing; buried stones are worth nothing. The higher score wins; equal scores draw. (There is no komi and the board is even-sized, so draws are genuinely possible.)

There is no agreement about dead stones. If you believe stones are dead, prove it — play. Filling inside your own territory costs nothing under this scoring, so demonstration is always affordable.

## The first move

There is no komi. Black's first move must be a placement. White may then either reply, or take over Black — the players exchange colors, the stone on the board stays Black, and the original first player, now White, moves next.

---

## Three positions

Stacks are written bottom to top in brackets; heights beneath. A point's three neighbors are listed explicitly.

**Covering is not capture.**

```
point p: [W], height 1, with at least one empty neighbor.

Black plays p:   [W] → [W,B], height 2, Black's column.

White is buried, not removed. If Black's cap is ever captured,
the peel uncovers [W] and the point is White's again.
```

**A well is an eye.**

```
core c: [B], height 1.
c's neighbors x, y, z: each [B,B], height 2, all one Black group.

c stands strictly below x, y, z — its sky is the group's liberty.

White plays c:  [B,W], height 2 — tied with the walls, so no sky
even next turn; no empty neighbor; no White neighbor; and it
captures nothing while the Black group has any other liberty.
White's stone would have no liberty: the placement is illegal.

If c's sky is the group's LAST liberty, the result depends on the
collar beyond the walls. With outer neighbors at height 1, the walls
peel to height 1, gain no skies, and are erased in a second wave;
White's entry survives. With every outer neighbor at height 2 or
higher, the peeled walls land strictly below their surroundings and
regain skies. Capture stops, leaving White's cap without a liberty,
so the entry is illegal. A high collar can therefore make one well
unconditionally alive; life is determined by the full vertical shape,
not by a flat count of eyes.
```

**The peel that kills.**

```
point b: [B,B], height 2.
b's neighbors: [W,W,W], [W,W,W], [W,W,W] — all height 3.

b is strictly lower than all three: its sky is the lone Black
group's only liberty.

Black now plays elsewhere and captures a White group containing one
of b's neighbors. That neighbor peels from height 3 to height 1, where
it survives in a newly created well. It now stands BELOW b, so b no
longer stands strictly below every neighbor. Black's sky is gone;
if the Black group has no other liberty, step 5 makes Black's own
capturing move illegal.

Count your skies before you take the walls that make them.
```

---

## What the rules imply

Five consequences follow from the rules. None is obvious at the board, and all five shape the game.

**The board has three regions.** Rim columns, pinned by a phantom neighbor, can never be stacked, never hold a sky, and never make a summit: the rim plays as pure flat Go, two liberties to a stone. Their on-board neighbors can be stacked, but never deeply enough for skies. Only the points with no rim neighbor — 6(n−1)² of them, the majority of the standard board — carry the full vertical game. Height anywhere is capped at one more than the distance to the rim, reaching 2n−1 on the six central points; but a column of height 3 already demands, from unbroken terrain, a fifteen-stone pyramid built beneath and around it at some stage — for a single point of score. Height is a weapon, never wealth.

**Openness is armor.** A stone beside an empty point can never be capped. Stacking needs a locally packed neighborhood, so broad, open play stays flat, and the vertical game ignites first wherever the board saturates — usually as territory closes. Sealing your territory is what scoring demands, and it is also what arms the vertical game along your walls: the timing of closure is a decision, not a formality.

**Height difference creates the sky.** Enclosure alone does not: a stone walled in at its own height has no liberty left and dies, exactly as in Go. A column breathes upward only when everything around it stands strictly taller. Entry into a well is suicide while the defending group has another liberty. When the well is its last liberty, the surrounding collar decides whether peeled walls regain skies or collapse. Pits of two or more empty points are fought over classically, with the defender filling from the walls.

**Spacing rules the stacks.** When a stacked group is captured, only its surface is peeled away, and a survivor lives only where it lands strictly below everything around it. Columns of equal height shade each other's skies and fall together in the next wave; a lone stack, peeled, lands in a hollow and breathes. Build your towers apart — and remember the peel that kills: capturing the walls around you can erase your own sky, and the rules will call it suicide.

**Escalation throttles itself.** Recapping a contested column one level higher first requires raising every one of its neighbors, each of which requires its own neighbors raised in turn — and each new plateau faces the summit test besides. The cost of a cap war grows geometrically with height; the terrain, not the repetition rule, is what ends them.
