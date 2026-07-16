# Native Screening V2 Results

## Scope and provenance

The frozen native-only screen completed 480 n=4 games from source commit
`c31a6986001c5a09e97d023162229d8ffbee838e`: 20 paired seeds per ruleset in
Casual-versus-Standard and Standard-self-play matchups. The manifest was
committed before any real game. All raw state, game, and summary files remain
outside the repository and are linked by SHA-256 from the compact
[audit artifact](../research/results/native-screening-v2-20260715.json).

All 480 games completed. There were zero illegal actions, crashes, watchdog
incompletes, or pending records. This establishes operational integrity for the
frozen jobs, not game quality.

The sample contains 20 paired seeds per stratum and only one evaluator family.
It is diagnostic/falsification evidence, not independent-agent, balance, depth,
emergence, beauty, or flagship evidence.

## Diagnostic results

| Ruleset | Standard score vs Casual | Standard-self Black score | Standard-self stagnation | Standard-self wipes | Standard-self median margin |
|---|---:|---:|---:|---:|---:|
| Classic 1.3 | 97.5% | 45.0% | 80.0% | 15.0% | 18.2% |
| Rosette 0.1 | 97.5% | 50.0% | 0.0% | 7.5% | 14.6% |
| Breath 0.1 | 90.0% | 51.2% | 0.0% | 0.0% | 5.2% |
| Breath-run 0.1 | 51.2% | 45.0% | 0.0% | 32.5% | 42.2% |
| Gjerde-breath 0.1 | 67.5% | 47.5% | 0.0% | 12.5% | 5.4% |
| Gjerde-Go 0.1 | 68.8% | 46.3% | 0.0% | 70.0% | 10.8% |

Every Standard-self game invoked takeover because identical native agents make
the swap policy symmetric. Its 100% swap rate is therefore a mirror-match
artifact, not a candidate balance result. The mixed matchup had a 50% swap rate
for every ruleset.

Opening diversity remained high: five strata had 40 distinct 12-action
openings in 40 games; mixed Breath-run had 39. No top opening exceeded 5%.
This is evidence against immediate deterministic opening collapse under these
agents, but not under strong play.

## Candidate-specific reading

- **Breath** has the cleanest matched-agent health: no stagnation or wipes and
  a 5.2% median margin. Its mixed matchup was 90% Black and the Standard agent
  scored 90%, so pie/color/search interactions remain unresolved.
- **Gjerde** also has a healthy Standard-self stratum: 12.5% wipes, 5.4% median
  margin, and 38.0% mean scored area, above its 30% admission threshold. The
  mixed stratum had 67.5% Black and 27.5% wipes, so the conclusion is provisional.
- **Rosette** numerically passes the matched Standard health limits apart from
  the inapplicable mirror swap rate. Casual was almost completely dominated by
  Standard, and the required competitive-entombment test still needs stronger
  position analysis.
- **Classic** is the strongest negative diagnostic: 80% of Standard-self games
  and 22.5% of mixed games ended through the twelve-quiet-move rule. Standard
  self-play also reached 2.57N median length; mixed play had 77.5% wipes and a
  100% median margin. Independent search must determine whether this is a game
  pathology or a native-evaluator failure.
- **Breath-run** retained its rescue-chain activity, but both matchups had
  wipes above 30% and median margins above 42%. Standard did not materially
  outperform Casual, which weakens the current search-depth signal.
- **Gjerde-Go** had 70% wipes and only 29.8% mean scored area in Standard
  self-play. That reproduces the capture-first severity concern under the
  corrected scorer and is the clearest candidate-level wipe warning.

## What follows

Do not archive or promote a ruleset from this one-family sample. The next
computer-only unit should first add constructed regression positions for the
Classic stagnation, Gjerde-Go wipe, and mixed Breath color/pie signatures. Then
freeze a separate 12-simulation uniform-MCTS diagnostic against native Standard
using paired colors and fresh seeds. Run the light rollout and 24-simulation
rung only after the preceding job passes correctness and provenance audit.

No result from this screen may be pooled with the historical 250-simulation
attempt or a future 12/24 manifest.
