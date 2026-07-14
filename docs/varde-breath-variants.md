# Varde: Breath and Breath-Extend (experimental rulesets)

Two engine-flagged flat variants (`Game(n, rules="breath")` and
`Game(n, rules="breath-extend")`); classic rev 1.3 remains the default.
Both are plain degree-3 Go on the hexagonal intersections — no
stacking, no skies, no explicit life rule.

## Breath

One change to Go's resolution order:

> Place the stone. If its group has no liberty — counted **before any
> removals** — the move is illegal. Otherwise remove enemy groups
> without liberties, as usual.

A capture can never legalize a breathless stone. Consequences, all
emergent:

- **Enclosure is life.** The last point of any enclosed cavity can
  never be filled: the filling group is confined to the cavity and has
  no pre-capture liberty. One enclosed point — or a well of any size —
  is unconditional life. There is no nakade.
- **Large loose rings are honest.** An opponent alive *inside* a ring
  borrows liberties from his own living group and may grind the ring
  down; a cavity confers life only if the opponent cannot live in it.
- **Bare face-rings die** (they enclose no point), snapbacks and
  classic ko recaptures are suicide-shaped and hence illegal, and
  open-field capture is exactly ordinary Go.

## Breath-Extend

Breath, plus one optional pre-move:

> On a player's turn, if at least one of their groups has exactly one
> liberty, they may first extend exactly one such group with a stone on
> that liberty, then make a normal move. The extension resolves as a
> normal breath-first placement.

Because the extension is optional and breath-checked, extending into a
dead end or into one's own last cavity point is simply illegal — the
mechanic can never force self-harm. Every atari is answerable at zero
tempo; killing reduces to herding a group into a dead end where the
extension is breath-illegal; a doomed group poses a real
abandon-or-crawl decision.

## Playtest evidence

Instrumented games, identical seeds across all four rulesets
(classic-tuned AIs; `a` = actions, `e` = free extensions B/W):

| Matchup | classic 1.3 | rosette | breath | breath-extend |
|---|---|---|---|---|
| Balanced mirror n=6 s11 | 704a · 172–44 | 429a · 101–115 | 244a · 111–105 | 247a · 96–120 · e46/35 |
| Mason–Surveyor n=6 s12 | 436a · 124–92 | 219a · 97–119 | 219a · 94–122 | 219a · 95–121 · e7/11 |
| Balanced mirror n=6 s13 | 766a · 139–77 | 386a · 121–95 | 244a · 113–103 | 219a · 116–100 · e25/25 |
| Mason–Surveyor n=5 s14 | 186a · 64–86 | 171a · 61–89 | 155a · 63–87 | 153a · 68–82 · e4/6 |
| Balanced mirror n=6 s15 | 940a · 94–122 | 333a · 97–119 | 256a · 124–91 | 224a · 114–102 · e33/30 |
| Surveyor–Mason n=6 s12 | 294a · 98–118 | 219a · 119–97 | 217a · 122–94 | 219a · 122–94 · e10/3 |
| **mean abs. margin** | **23.3 % of board** | 11.3 % | 10.8 % | **9.7 %** |
| **mean length** | 554 | 293 | 222 | **214** |
| **mean stones captured** | 219 | 99 | 18 | 44 |

Breath games run at Go-like density (~1 action per point) with the
closest margins measured in any ruleset. The extension mechanic roughly
doubles fighting relative to plain breath — the safety net encourages
contact play — while tightening margins further.

## Attack/defense balance probe

One-ply greedy duelists (`research/harness/duel_players.py`): the
attacker maximizes captures and starves enemy liberties; the defender
maximizes its own liberties and safety. Eight games per ruleset
(n=4 ×3 seeds and n=6 ×1, both color assignments):

| Ruleset | Attacker wins | Defender wins | Margins |
|---|---|---|---|
| classic | 3 | 5 | mostly total wipes (96–216) |
| rosette | 1 | 7 | all total wipes |
| breath | 2 | 6 | **2–40 points** |
| breath-extend | 0 | 8 | 2–84 points |

Reading: classic is coin-flip annihilation; rosette punishes pure
aggression but still ends in wipes; **breath is the closest to a real
attack/defense equilibrium** — tight margins, and the attacker role
wins both large-board games; breath-extend systematically favors
defense (pure aggression never wins), confirming that stacking two
attacker-dampeners on the same lattice overshoots.

A caveat and a recurring observation: the duelists are one-ply
caricatures, and in every ruleset the rim's phantom neighbors remain
the dominant trap — rim stones have two liberties, not three. Any UI
for these variants should render phantom edges explicitly.

## Extension-rule variants (second research cycle)

Six formulations of the free-extension idea, all engine-flagged:

| Ruleset | Extension rule |
|---|---|
| breath-extend | one group, once, then a normal move |
| breath-extend-multi | any number of distinct atari'd groups, once each, then a move |
| breath-extend-run | one group, chained while it stays at one liberty, then a move |
| breath-rescue | as multi, but the extensions replace the move |
| breath-run | as chain, but the run replaces the move |
| breath-cap | one extension on any space adjacent to the group, stacking allowed, then a move |

Attack/defense duels (8 per variant) and Balanced mirrors:

| Variant | Duels A–D | Duel margins | Verdict |
|---|---|---|---|
| breath (baseline) | 2–6 | 2–40 | near-equilibrium baseline |
| breath-extend | 0–8 | 2–84 | defense-favored |
| breath-extend-multi | 0–8 | 2–84 | indistinguishable from breath-extend; redundant |
| breath-extend-run | 0–8 | wipes | free corridor runs make defense degenerate |
| breath-rescue | **8–0** | 40–71 | balance fully inverts: every forced rescue costs a tempo |
| breath-run | **4–4** | 6–114 | the equilibrium point of the family |
| breath-cap | 0–8 | wipes | **broken: mutual cap-rescues never terminate** (heights unbounded without terrain; one mirror hit the move cap with ~2,900 extensions) |

The family forms a tunable dial: free extensions (defense) → no
extension (mild defense) → chain-as-turn (even) → rescue-as-turn
(attack). breath-run and breath-rescue are the interesting poles to
explore by hand; multi and the chain-with-move variant add nothing,
and breath-cap needs a height bound (i.e. the terrain rule back) to
even terminate, which defeats its simplicity.

Attacker and Defender are playable in the browser as computer
profiles under every ruleset.

## Discoveries from human play (breath-run vs Attacker)

Two properties surfaced in over-the-board play that the automated
probes had not named:

**Corner micro-life.** The board's six corners are pairs of degree-two
points. Two stones flanking such a point can never be captured: the
final fill would be a stone with zero pre-capture liberties, which
breath-first forbids even when it would capture. The flanked point is
an *eternal liberty* — a two-stone fortress, and the miniature form of
breath's cavity-life. The same construction protects a larger army
that shares the flanked point (three friendly neighbors around any
point make it unfillable). Corners therefore carry real value, as in
Go, and late-game "ataris" against eternal points are empty threats.

**The mutual squeeze.** Under breath-run, herding an enemy chain with
sequential ataris harvests whole rescue-turns of tempo — but every
forced rescue-extension is also a stone placed against the herder's
own walls. A chased chain traces the contour of the chaser: the
caterpillar strangles the shepherd. Chasing profits only a player who
keeps counting their own liberties while collecting tempi; in the
recorded game the herder (a 22-stone advantage in forced tempi) lost
a seven-stone group to exactly this and the game with it, 32–22.
Liberty bookkeeping is the game's central skill, which is why the
client now draws warning rings on one- and two-liberty groups and
marks every phantom edge on the rim.
