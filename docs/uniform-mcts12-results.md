# Uniform MCTS@12 Diagnostic Results

## Scope and provenance

The frozen [manifest](../research/manifests/uniform-mcts12-20260716.json)
committed the source hashes, six candidate revisions, n=4 board, 20 paired
seeds per candidate, both color legs, native Standard opponent, terminal-score
uniform MCTS with exactly 12 simulations, telemetry, eight workers, and the
research-only 20N whole-game watchdog before any outcome was generated.

The exact 240-game job ran from source commit
`22b2176731d2ca4b98def08c8321a8f88870453e`. It took approximately 2 hours 34
minutes on the development machine. All 240 games completed; there were zero
illegal actions, crashes, watchdog incompletes, or pending records. The compact
[audit artifact](../research/results/uniform-mcts12-20260716.json) passed its
schedule, config, provenance, record-order, and accounting checks. Hash-linked
raw state, JSONL telemetry, and summary files remain outside the repository.

This is a clean operational result and a negative agent-admission result. It is
not balance, strategic-depth, candidate-elimination, emergence, beauty, or
flagship evidence.

## Constructed warning fixtures

Three fixtures were required before launch:

- **Classic stagnation:** from eleven quiet actions, a legal own-column cover
  captures nothing, changes no control, and triggers the final twelve-quiet
  ending; a legal empty placement changes control and resets the clock.
- **Gjerde-Go wipes:** a sparse 1-1 fenced tie has no loser and is not a wipe;
  a decisive 1-0 result meets the declared loser-below-10% threshold. The
  harness now checks that a loser exists before labeling a wipe.
- **Breath color/pie accounting:** paired summaries follow complete seat
  identity through takeover and separately report board color, original Black
  player, and post-swap results.

These fixtures explain the recorded metrics; they do not prove that the
observed warning signatures are properties of strong play.

## Results

Native score is the native Standard agent's score rate against uniform
MCTS@12. Margins and scored area are fractions of the ruleset's scoreable area.

| Ruleset | Native score | Black score | Swap | Stagnation | Wipe | Median margin | Median actions | Mean scored area |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Classic 1.3 | 100.0% | 75.0% | 25.0% | 2.5% | 100.0% | 100.0% | 197.0 | 100.0% |
| Rosette 0.1 | 100.0% | 75.0% | 35.0% | 0.0% | 57.5% | 100.0% | 150.0 | 99.6% |
| Breath 0.1 | 100.0% | 65.0% | 20.0% | 0.0% | 85.0% | 100.0% | 122.0 | 100.0% |
| Breath-run 0.1 | 100.0% | 75.0% | 25.0% | 0.0% | 82.5% | 100.0% | 137.5 | 99.9% |
| Gjerde-breath 0.1 | 88.8% | 86.2% | 47.5% | 0.0% | 50.0% | 32.4% | 175.0 | 52.5% |
| Gjerde-Go 0.1 | 97.5% | 97.5% | 50.0% | 0.0% | 97.5% | 51.4% | 215.5 | 55.1% |

Across the complete job, native Standard scored 97.7%, 189 of 240 games
(78.8%) were wipes, Black scored 79.0%, and only one game ended by Classic's
stagnation rule. Breath-run exercised 704 extension actions without an illegal
or state-machine failure.

The original-Black-player score was close to 50% in every stratum because the
paired schedule alternated which agent identity began as Black while native
Standard overwhelmingly won both legs. That statistic verifies identity
accounting here; it must not be mistaken for evidence of balanced play.

## What the diagnostic establishes

The independent implementation is mechanically sound at this sample:

- legal play, takeover, pass, extension, automatic extension completion,
  resumption, and acceptance all survived real games;
- deterministic paired scheduling and checkpoint ordering held;
- the repaired Gjerde scorer produced 52.5% mean fenced area and Gjerde-Go
  produced 55.1%; and
- sparse draws no longer inflate the wipe count.

Uniform MCTS@12 is nevertheless not a strategically credible comparison agent.
It lost every game in four rulesets, scored only 2.5% in Gjerde-Go, and 11.25%
in Gjerde. Doubling this unchanged search to 24 simulations would spend roughly
twice the already substantial line-board compute without first demonstrating
basic tactical competence. A light rollout may change behavior, but running it
immediately would confound rollout-policy repair with the intended adjacent
budget comparison.

Therefore the clean operational audit unlocks later manifests mechanically,
but the evidence-quality review keeps both uniform MCTS@24 and the light rollout
unlaunched.

## Recommended next computational unit

Before another match batch:

1. Add ruleset-specific MCTS admission positions for immediate capture,
   immediate defense, takeover, extension-chain tempo, fence completion, fence
   denial, and sparse-score acceptance. Require a small budget ladder to choose
   the correct action increasingly often.
2. Record decision-level simulation, node, rollout-length, and latency telemetry
   in research jobs so Classic and line-board costs can be localized without
   changing live rules.
3. Compare uniform, current light, and one minimal rules-neutral tactical rollout
   on those held-out fixtures and a tiny outcome-blind timing sample.
4. Freeze the next paired match job only after one policy passes the tactical
   admission gate and its projected n=4 runtime is acceptable.

If the repaired policy is still non-competitive at 12 and 24 simulations, stop
scaling plain terminal UCT and evaluate a transposition-aware or value-guided
search as a separately versioned agent. Do not use the native evaluator's
ruleset scores as MCTS leaf values; that would collapse the evaluator-artifact
firewall this experiment is meant to provide.
