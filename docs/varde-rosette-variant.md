# Varde: Rosette (experimental ruleset)

An engine-flagged variant (`Game(n, rules="rosette")`); classic rules
(rev 1.3) remain the default. The variant replaces ambient verticality
with a *last-breath* mechanic so that open play is pure degree-3 Go and
stacking exists only as the slow execution of sealed groups.

## The two rule changes

1. **Skies.** A group's liberties are the empty points adjacent to it.
   A group with no empty adjacent point instead breathes through skies —
   one above each of its columns whose top stone was not placed this
   turn — **provided its columns contain a closed ring** (equivalently:
   the group encircles at least one cell or point of the board). A
   suffocated group that encircles nothing has no liberties and is
   captured as usual.
2. **Stacking gate.** A stone may be placed on an occupied column only
   when that column belongs to an enemy group whose only liberties are
   skies. The terrain and summit rules then apply unchanged.

Everything else — board, capture waves and peeling, suicide, superko,
scoring, the pie rule, the two-pass ending with one resumption, and the
stagnation ending — is identical to rev 1.3.

## What emerges (no further rules required)

- **Life is enclosure.** On a trivalent lattice a group can only own a
  true eye by encircling it, so eyes and rings are one concept.
- **Two eyes live; one true eye also lives.** Filling the last eye
  captures nothing (ring-skies rescue the group), so the fill is
  suicide, and the stacking gate protects any group that keeps a
  horizontal liberty.
- **False eyes die.** Separate groups sharing an eye point are acyclic;
  when sealed they have no skies and are captured — including the
  three-stone "flower".
- **A lone 6-ring is a trap, not life.** Capping any ring column breaks
  the ring, strangling the remnant: the summit's capture branch makes
  the cap legal, and one stone kills six in a mass peel.
- **A theta (two cells) dies only at its two junction columns.** A
  bridged pair of disjoint rings dies at the bridge attachments, where
  a cap splits off an acyclic remnant.
- **Three cells make a fortress.** Any single-column removal from a
  three-cell cluster (line or triangle, 13–14 stones) leaves every
  remnant cyclic, so no cap ever captures and none is ever legal.
- **Sealed rosettes tax the attacker by area.** Branch columns are
  entombed one cap per move (each cap is a summit the attacker holds
  two-of-three on), and entombed towers beside a lone ring let it be
  unzipped. The kill of a sealed k-column group costs on the order of k
  moves beyond the Go-style seal — the "fourth liberty set".
- Heights effectively never exceed 2; captured stones still return, and
  buried stones still resurface through later peels.

## Exploratory probe (four uncalibrated classic-AI seeds)

| Matchup | classic 1.3 | rosette |
|---|---|---|
| Balanced mirror, Full, s11 | 704 acts, 172–44 | 429 acts, 101–115 |
| Mason–Surveyor, Full, s12 | 436 acts, 124–92 | 219 acts, 97–119 |
| Balanced mirror, Full, s13 | 766 acts, 139–77 | 386 acts, 121–95 |
| Mason–Surveyor, Int., s14 | 186 acts, 64–86 | 171 acts, 61–89 |

In this small probe, margins fell from wipe-scale to 6–12% of the board, mirror wins split
across colors, lengths approach Go's actions-per-point, and no game
needed the stagnation ending. The evaluator profiles were tuned for
classic rules; a fresh audit/curation cycle is required before any
strength, balance, or style claim under this variant.
