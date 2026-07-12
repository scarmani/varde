# Cairn

A Go variant on the intersections of a hexagonal board, with stacking,
terrain-limited height, and vertical liberties ("skies"). Designed through an
adversarial exchange between two AI systems; every rule survived multiple
rounds of counterexample hunting, and the engine's test suite encodes the
known-answer positions from that history.

## Layout

- `docs/cairn-rules.md` — the current rules (rev 1.2), standalone
- `docs/design-history.md` — the annotated design document (Grounded Cairn
  1.0.1 lineage): proofs, retired folklore, playtest protocol
- `engine/cairn.py` — reference rules engine (pure Python, no dependencies)
- `engine/test_cairn.py` — 27-test position suite, all known-answer positions
- `engine/selfplay.py` — random and greedy self-play with metric logging

## Run

```
cd engine
python3 -m unittest test_cairn -v      # position suite (27 tests)
python3 selfplay.py 3 40               # random self-play, n=3 board
python3 selfplay.py 3 12 greedy        # greedy self-play (natural endings)
```

## Status

Rules are stable and machine-verified; the engine implements the six-step
resolution exactly as written. Greedy self-play terminates naturally at
~2.1–2.5N moves with cap share ~4% (just under the 5% "decorative"
threshold — the number to watch once real search replaces greed).

## Open findings from engine verification (2026-07-12)

Building the test suite broke four claims in the rules document's commentary
(the rules themselves held):

1. **The collar condition.** "One well is not life" is false in general: if
   a well's walls have their outer neighbors ("collar") at height ≥ 2, the
   peeled walls regenerate wells mid-cascade and the killing entry is
   suicide — a single well with a high collar is unconditional life. The
   twin-well theorem inherits the same premise (low-collar twin wells are
   breachable core by core). The life doctrine is collar-conditional.
2. **Wall stranding.** Walls connect only through the core; capping the core
   disconnects them, and low-collar disconnected walls are erased even when
   the rest of the group survives.
3. **Twin wells have 8 collar supports, not 9** — the hexagonal face through
   the two cores forces exactly one shared point (verified across all 96
   sites at n = 3).
4. **The peel-that-kills** operates by the wall dropping *below* your column
   (a capture-created pit under you kills your sky), not by tying it; the
   tie version is nearly unconstructible because full erasure frees
   rescuing empties.

All four are encoded as passing tests. Next steps: independent verification
of these findings against the rules text; fold the collar condition into the
rules commentary; then a web UI over this engine, then MCTS for the gate
experiments (k_well vs k_eye, summit-rule variants, saturation equilibrium).
