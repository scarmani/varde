# Native Screening V2

## Purpose

Run a frozen native-only operational screen across the six candidate Varde
rulesets before spending resources on shallow independent search. This stage is
designed to expose illegality, crashes, incomplete games, stagnation, wipes,
color sensitivity, opening convergence, and evaluator-specific artifacts.

It cannot establish strategic depth, balance, emergence, beauty, or flagship
fitness. Both agents use the same native evaluator family.

## Frozen design

- Source: merged MCTS v2 main `78fae9d30e03f603496af7b1af7e423b58facfc4`.
- Rulesets: Classic 1.3, Rosette 0.1, Breath 0.1, Breath-run 0.1,
  Gjerde-breath 0.1, and Gjerde-Go 0.1.
- Board: n=4.
- Jobs:
  - native Casual versus native Standard;
  - matched native Standard self-play.
- Each job uses 20 paired seeds per ruleset and two color legs: 240 games per
  job, 480 games total.
- Pair legs share their seed. The deterministic schedule and every derived seed
  are frozen by a SHA-256 hash in the manifest.
- Eight workers, checkpoint every eight records, telemetry enabled, and a 20N
  research-only watchdog.
- Raw state, games, and summaries remain under `/private/tmp`; only a compact,
  hash-linked audit may enter the repository.

The mixed matchup tests whether shallow versus bounded two-ply native search
changes operational pathologies. Standard self-play provides the matched-agent
health stratum. Casual self-play is omitted because it adds another 240 games
without an independent evaluator family or a stronger falsification gate.

## Integrity gates

The manifest must be committed before any real game runs. Tests reconstruct its
schedule and verify source, engine, evaluator, and registry hashes. The existing
evaluation harness writes atomic checkpoints, rejects configuration or source
drift on resume, preserves task ordering across worker counts, and records every
illegal action, crash, and watchdog incomplete.

The audit publishes a compact artifact only when both jobs have complete,
hash-valid state, exact configs and schedules, and matching runtime provenance.
Gameplay health failures remain publishable negative evidence; corrupted or
incomparable runs do not.

## Advancement

No 12/24 MCTS job launches in this run. After the native audit, a separate
pre-outcome decision may select mechanically eligible rulesets for the shallow
independent-family diagnostic. Native results are never pooled with the frozen
historical 250-simulation attempt.
