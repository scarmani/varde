# Historical model checkpoints

These four small files preserve Claude's directional experiments against
commit `6fb779c`. They are evidence artifacts, not production defaults and are
never loaded automatically by Cairn.

- `stock-80.json`, `stock.json`: six-feature outcome learner at 80/120 Toy games.
- `v1-80.json`, `v1.json`: experimental nine-feature margin learner at 80/120 Toy games.

The historical V1 files intentionally retain their original version-1 envelope
even though they contain nine weights. Production model migration accepts only
the shipped six-weight version-1 schema, so these checkpoints cannot be mistaken
for a user model. Current reproducible V2 runs use `harness/train_v2.py` and
write format-2 models to an explicit output directory.
