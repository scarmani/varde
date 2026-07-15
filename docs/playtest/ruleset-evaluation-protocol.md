# Varde ruleset evaluation protocol

This is the field protocol for the human stage of the ruleset-promise program.
It is used only after computational screening leaves two or three candidates.
Computer opponents are not used in scored human games.

## Prepare the study

Recruit 8, 10, or 12 people with Go or modern abstract-game experience. Assign
pseudonyms `P01` through `P12`; the Varde record contains no name, email,
demographic, device, IP, or free-text identity field. Keep any recruitment and
consent records outside the Varde data package.

Generate the frozen package from the exact source revision used to play:

```bash
python3 research/harness/human_study.py \
  --participants 8 --rulesets breath,breath-run \
  --games-per-ruleset 6 --output-dir /path/to/study-package
```

The package pins the source commit and rules revisions. It includes a
counterbalanced fixed-pair schedule, two engine-derived call-your-shot puzzles
per ruleset, separate survey items, privacy declaration, and a package hash.
Do not change a rule after generating the package. If a rule changes, increment
its revision and begin a new measurement round.

## Neutral rules briefs

Give only the applicable brief. Do not mention designer hypotheses, reported
computer results, candidate rankings, or names for shapes players have not
discovered themselves.

### Classic 1.3

Players place their color on a vertex or cover an occupied vertex. Connected
top stones resolve together. Ordinary liberties and sufficiently clear sky
above a stack can keep a group alive; groups without either are removed in the
engine's deterministic wave order. The final score is controlled vertices.

### Rosette 0.1

Play is flat. A connected group that contains a cycle survives ordinary
surrounding. A fully sealed group can instead be removed through the legal cap
and entombment resolution. The final score is controlled vertices.

### Breath 0.1

Play is flat. The placed stone's group must have breath before opponent captures
are removed. Connected groups without breath are removed by the deterministic
resolution. The final score is controlled vertices.

### Breath-run 0.1

Use the Breath rules. When the player to move has an eligible one-liberty group,
the marked rescue action may extend that group and replaces the normal placement
for that turn. Finish the extension turn explicitly. The final score is
controlled vertices.

### Gjerde-breath 0.1

Players claim line intersections on the Kagome display using the Breath
resolution. A cell field scores only when it has no unclaimed exterior boundary
and every claimed boundary line belongs to one color. Mixed or open fields do
not score.

### Gjerde-Go 0.1

Players claim line intersections on the same display. Captures resolve before
self-capture legality, as in the capture-first order. Cell fields use the same
fully closed, single-color fence scoring as Gjerde-breath.

All briefs also state the common pie rule, passing and ending procedure,
once-only resumption, superko restriction, and displayed score. The explanation
must take under ten minutes; five minutes is preferred.

## Comprehension and practice

For each ruleset, show both generated puzzles before scored games. The player
must call whether the marked action is legal, which stones are removed and in
what waves, how the displayed score changes, and which color acts next. Keep the
embedded `answer` hidden until both answers are locked. Record correctness per
component; do not reduce a partially correct prediction to an unexplained
binary judgment.

Then play one unscored practice game. Answer rules questions without suggesting
a move. For Classic, include at least one separate collar call-your-shot review.
For each Gjerde candidate, include at least one separate line-adjacency and open
outer-boundary call-your-shot review.

## Scored games and local records

Follow the generated pair order. Each pair plays six scored games per ruleset;
each player has three games as each color. Before move one:

1. Start a fresh two-player hotseat game at the declared size and rules revision.
2. Select **Start local record**.
3. Play without computer assistance.
4. At the end, choose **Export JSON** before starting or loading another game.

The recorder stores action kind, actor color, point, thinking interval since the
last completed action, move numbers, capture waves, score after each action,
resumption, and ending type. It stores no absolute clock time and submits
nothing over the network. Game saves and playtest records are intentionally
separate artifacts. **Import JSON** locally validates and reopens a prior
playtest record for inspection or re-export; imported records are read-only and
are never attached to the currently displayed game.

The facilitator separately records rules questions, whether a misunderstanding
materially affected the game, and whether the players correctly understood the
decisive event. Do not add identifying fields to the browser record.

## Post-game instrument

Ask independently, before discussion:

1. What decided the game?
2. Which move changed your plan?
3. Did you discover a reusable shape or strategic principle?
4. What would you do differently next time?
5. Did you understand the decisive event when it happened: yes, partly, or no?
6. Did a rules misunderstanding materially affect the game: yes or no?
7. Would you accept an optional immediate rematch: yes or no?

Then collect nine separate 1–7 ratings, anchored at 1 very low, 4 neutral, and
7 very high:

- agency;
- clarity;
- tension;
- strategic variety;
- surprise;
- inevitable-in-retrospect understanding;
- visual beauty;
- satisfying closure;
- desire to play again.

Never collapse these into one score. In particular, treat surprise followed by
comprehension differently from confusion.

## One-week retention

Seven days later ask, without showing the game record:

- Describe any position you still remember.
- Describe any reusable pattern or principle you remember.
- Did you voluntarily think about, discuss, or analyze the game afterward?
- Would you choose to play this ruleset again?

Code a motif only when at least two different player pairs describe it
independently. Designer-supplied words do not count as discovery. Preserve both
negative and positive observations.

## Admission gates

By the third scored game, local resolution prediction must reach 80% and fewer
than 20% of games may be materially affected by misunderstanding. A finalist
needs median agency, visual beauty, and replay ratings of at least 5/7, at least
70% optional-rematch acceptance, no severe readability failure, and at least
two independently rediscovered motifs. These gates supplement rather than
override rules correctness and computational degeneration checks.
