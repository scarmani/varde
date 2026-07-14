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
mechanic can never force self-harm. Effects on play:

- Every atari is answerable at zero tempo, so ladders and chases cost
  the attacker one move per step and the defender nothing.
- One placement removes at most one liberty, so every kill passes
  through atari — and therefore through an extension offer. Killing
  reduces to **herding a group into a dead end** where the extension
  is breath-illegal (rim corners, pre-sealed corridors).
- Double atari is largely answerable (extend one group, save the other
  with the normal move); only triple threats and sealed flight squares
  win material.
- A doomed group poses a real decision: crawling costs nothing but
  enlarges the eventual capture; abandoning early is often correct.

## Playtest evidence (same seeds as prior ruleset tests)

See `research` notes and the session evidence archive; summary:

| Matchup | classic 1.3 | rosette | breath | breath-extend |
|---|---|---|---|---|
| Balanced mirror, Full, s11 | 704 · 172–44 | 429 · 101–115 | 244 · 111–105 | (table filled from instrumented run) |

The rim's phantom neighbors remain the dominant newcomer trap in all
rulesets: rim stones carry two liberties, not three, and misreading
this loses stones in every variant. Any UI for these variants should
render phantom edges explicitly.
