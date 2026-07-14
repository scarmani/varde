"""Persistent linear learning model and background trainer for Varde."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import random
import threading

from varde import BLACK, Game, other


LEGACY_FEATURE_NAMES = (
    "controlled",
    "skies",
    "liberties",
    "vulnerable",
    "development",
    "territory",
)
FEATURE_NAMES = LEGACY_FEATURE_NAMES + ("height", "rim", "groups")
MODEL_FORMAT = "varde-linear-eval"
LEGACY_MODEL_FORMAT = "cairn-linear-eval"
MODEL_VERSION = 2
RECIPE = "margin-v2"
EARLY_LEARNING_RATE = 0.05
LATE_LEARNING_RATE = 0.02
LEARNING_RATE_SWITCH = 60
L2_DECAY = 0.0005
WEIGHT_LIMIT = 4.0
LEARNED_SCALE = 20.0
TRAINING_BATCHES = frozenset((10, 50, 200))
TRAINING_BOARD_MIX = (3, 3, 3, 4)
EXPLORATION_RATE = 0.08
EXPLORATION_PLACEMENT_FRACTION = 0.6
SAMPLE_START_MOVE = 6
SAMPLE_INTERVAL = 2
SAMPLE_INITIAL_WEIGHT = 0.4
MARGIN_SCALE = 0.15
TRAINING_WATCHDOG_MULTIPLIER = 20


def default_model_path():
    override = os.environ.get("VARDE_MODEL_PATH") or os.environ.get("CAIRN_MODEL_PATH")
    if override:
        return Path(override).expanduser()
    new = Path.home() / ".varde" / "advanced-model.json"
    legacy = Path.home() / ".cairn" / "advanced-model.json"
    if not new.exists() and legacy.exists():
        return legacy
    return new


def training_board_size(attempt_index):
    return TRAINING_BOARD_MIX[attempt_index % len(TRAINING_BOARD_MIX)]


def sample_weights(count):
    if count <= 0:
        return []
    if count == 1:
        return [SAMPLE_INITIAL_WEIGHT]
    return [
        SAMPLE_INITIAL_WEIGHT
        + (1.0 - SAMPLE_INITIAL_WEIGHT) * index / (count - 1)
        for index in range(count)
    ]


@dataclass
class LearningModel:
    path: Path = field(default_factory=default_model_path)
    weights: dict = field(default_factory=lambda: {name: 0.0 for name in FEATURE_NAMES})
    games_attempted: int = 0
    games_trained: int = 0
    training_seed: int = 1
    recipe: str = RECIPE
    needs_retraining: bool = False
    updated_at: str | None = None
    load_error: str | None = None
    lock: threading.RLock = field(default_factory=threading.RLock, repr=False)

    @classmethod
    def load(cls, path=None):
        model = cls(path=Path(path) if path else default_model_path())
        if not model.path.exists():
            return model
        try:
            payload = json.loads(model.path.read_text())
            if payload.get("format") not in (MODEL_FORMAT, LEGACY_MODEL_FORMAT):
                raise ValueError("unsupported learning model")
            version = payload.get("version")
            raw = payload.get("weights", {})
            if version == 1 and set(raw) == set(LEGACY_FEATURE_NAMES):
                weights = {
                    name: float(raw[name]) if name in raw else 0.0
                    for name in FEATURE_NAMES
                }
                model.recipe = "outcome-v1"
                model.needs_retraining = True
            elif version == MODEL_VERSION and set(raw) == set(FEATURE_NAMES):
                weights = {name: float(raw[name]) for name in FEATURE_NAMES}
                model.recipe = str(payload.get("recipe", RECIPE))
                raw_retraining = payload.get(
                    "needs_retraining", model.recipe != RECIPE
                )
                if not isinstance(raw_retraining, bool):
                    raise ValueError("invalid retraining flag")
                model.needs_retraining = raw_retraining
            else:
                raise ValueError("unsupported learning model")
            if any(
                not math.isfinite(value) or not -WEIGHT_LIMIT <= value <= WEIGHT_LIMIT
                for value in weights.values()
            ):
                raise ValueError("invalid learning weight")
            model.weights = weights
            model.games_trained = int(payload.get("games_trained", 0))
            model.games_attempted = int(
                payload.get("games_attempted", model.games_trained)
            )
            if (
                model.games_trained < 0
                or model.games_attempted < model.games_trained
            ):
                raise ValueError("invalid learning counters")
            model.training_seed = int(payload.get("training_seed", 1))
            model.updated_at = payload.get("updated_at")
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            model.load_error = str(exc)
        return model

    def to_dict(self):
        with self.lock:
            return {
                "format": MODEL_FORMAT,
                "version": MODEL_VERSION,
                "recipe": self.recipe,
                "weights": dict(self.weights),
                "games_attempted": self.games_attempted,
                "games_trained": self.games_trained,
                "training_seed": self.training_seed,
                "updated_at": self.updated_at,
                "needs_retraining": self.needs_retraining,
            }

    def status(self):
        payload = self.to_dict()
        payload.pop("format")
        payload["model_version"] = payload.pop("version")
        payload["trained"] = payload["games_trained"] > 0
        payload["load_error"] = self.load_error
        return payload

    def correction(self, features, perspective):
        with self.lock:
            value = sum(self.weights[name] * features[name] for name in FEATURE_NAMES)
        return LEARNED_SCALE * value * (1 if perspective == BLACK else -1)

    def record_attempt(self, seed, attempt_index):
        with self.lock:
            if attempt_index != self.games_attempted:
                raise ValueError("training attempt cursor is out of sequence")
            if self.games_attempted and seed != self.training_seed:
                raise ValueError("reset the model before changing training seed")
            self.training_seed = seed
            self.games_attempted += 1
            self.updated_at = datetime.now(timezone.utc).isoformat()

    def update(self, samples, outcome, seed):
        with self.lock:
            requires_reset = self.needs_retraining
            if self.games_attempted == self.games_trained:
                if self.games_attempted and seed != self.training_seed:
                    raise ValueError("reset the model before changing training seed")
                self.training_seed = seed
                self.games_attempted += 1
            if self.games_attempted < self.games_trained + 1:
                raise ValueError("record a training attempt before updating")
            learning_rate = (
                EARLY_LEARNING_RATE
                if self.games_trained < LEARNING_RATE_SWITCH
                else LATE_LEARNING_RATE
            )
            for sample in samples:
                if isinstance(sample, tuple):
                    features, sample_weight = sample
                else:
                    features, sample_weight = sample, 1.0
                raw = sum(self.weights[name] * features[name] for name in FEATURE_NAMES)
                prediction = 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, raw))))
                error = (outcome - prediction) * sample_weight
                for name in FEATURE_NAMES:
                    gradient = error * features[name] - L2_DECAY * self.weights[name]
                    value = self.weights[name] + learning_rate * gradient
                    self.weights[name] = max(-WEIGHT_LIMIT, min(WEIGHT_LIMIT, value))
            self.games_trained += 1
            self.training_seed = seed
            self.updated_at = datetime.now(timezone.utc).isoformat()
            self.recipe = "mixed-v1-v2" if requires_reset else RECIPE
            self.needs_retraining = requires_reset
            self.load_error = None

    def save(self):
        payload = self.to_dict()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        os.replace(temporary, self.path)

    def reset(self):
        with self.lock:
            self.weights = {name: 0.0 for name in FEATURE_NAMES}
            self.games_attempted = 0
            self.games_trained = 0
            self.training_seed = 1
            self.recipe = RECIPE
            self.needs_retraining = False
            self.updated_at = None
            self.load_error = None
        if self.path.exists():
            self.path.unlink()


def play_training_game(model, seed, index, cancel_event):
    """Run one deterministic learner-vs-fixed game and return samples/outcome."""
    from opponent import choose_decision, normalized_features

    rng = random.Random((seed << 16) + index)
    n = training_board_size(index)
    game = Game(n)
    learner_color = BLACK if index % 2 == 0 else other(BLACK)
    feature_samples = []
    turns = 0
    limit = TRAINING_WATCHDOG_MULTIPLIER * len(game.board.points)
    completed = False
    while turns < limit and not cancel_event.is_set():
        if game.finished:
            if not game.resumption_used:
                score = game.score()
                if score[BLACK] != score[other(BLACK)]:
                    game.demand_resumption()
                    turns += 1
                    continue
            completed = True
            break
        if (
            game.moves_played >= SAMPLE_START_MOVE
            and game.moves_played % SAMPLE_INTERVAL == 0
        ):
            feature_samples.append(
                normalized_features(game.board, game.state, game.moves_played)
            )
        color = game.to_move
        exploring = (
            color == learner_color
            and game.moves_played
            < EXPLORATION_PLACEMENT_FRACTION * len(game.board.points)
            and rng.random() < EXPLORATION_RATE
        )
        if exploring:
            legal = game.legal_placements()
            if legal:
                point = rng.choice(legal)
                game.play(point)
            else:
                game.play_pass()
        else:
            decision = choose_decision(
                game,
                color,
                difficulty="standard",
                seed=seed + index,
                model=model if color == learner_color else None,
            )
            if decision.action == "play":
                game.play(decision.point)
            elif decision.action == "pass":
                game.play_pass()
            elif decision.action == "swap":
                game.take_over()
                learner_color = other(learner_color)
            elif decision.action == "resume":
                game.demand_resumption()
        turns += 1
    if not completed or cancel_event.is_set():
        return [], None, False
    score = game.score()
    margin = score[BLACK] - score[other(BLACK)]
    outcome = 0.5 + 0.5 * math.tanh(
        margin / (MARGIN_SCALE * len(game.board.points))
    )
    weights = sample_weights(len(feature_samples))
    samples = [
        (features, weight)
        for features, weight in zip(feature_samples, weights)
    ]
    return samples, outcome, True


class TrainingService:
    def __init__(self, model, runner=play_training_game):
        self.model = model
        self.runner = runner
        self.lock = threading.RLock()
        self.cancel_event = threading.Event()
        self.thread = None
        self.running = False
        self.total = 0
        self.completed = 0
        self.discarded = 0
        self.error = None
        self.seed = 1
        self.starting_attempt = 0

    def status(self):
        with self.lock:
            return {
                "running": self.running,
                "total": self.total,
                "completed": self.completed,
                "discarded": self.discarded,
                "cancel_requested": self.cancel_event.is_set(),
                "error": self.error,
                "seed": self.seed,
                "starting_attempt": self.starting_attempt,
                "model": self.model.status(),
            }

    def start(self, games, seed=None):
        if not isinstance(games, int) or games <= 0:
            raise ValueError("games must be a positive integer")
        with self.lock:
            if self.running:
                raise ValueError("training is already running")
            chosen_seed = self.model.training_seed if seed is None else int(seed)
            if self.model.games_attempted and chosen_seed != self.model.training_seed:
                raise ValueError("reset the model before changing training seed")
            self.running = True
            self.total = games
            self.completed = 0
            self.discarded = 0
            self.error = None
            self.seed = chosen_seed
            self.starting_attempt = self.model.games_attempted
            self.cancel_event.clear()
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()

    def _run(self):
        try:
            for offset in range(self.total):
                if self.cancel_event.is_set():
                    break
                index = self.starting_attempt + offset
                samples, outcome, completed = self.runner(
                    self.model, self.seed, index, self.cancel_event
                )
                self.model.record_attempt(self.seed, index)
                if completed:
                    self.model.update(samples, outcome, self.seed)
                    with self.lock:
                        self.completed += 1
                else:
                    with self.lock:
                        self.discarded += 1
                self.model.save()
        except Exception as exc:
            with self.lock:
                self.error = str(exc)
        finally:
            with self.lock:
                self.running = False

    def cancel(self):
        with self.lock:
            if self.running:
                self.cancel_event.set()

    def reset(self):
        with self.lock:
            if self.running:
                raise ValueError("cancel training before reset")
            self.total = 0
            self.completed = 0
            self.discarded = 0
            self.error = None
            self.seed = 1
            self.starting_attempt = 0
            self.cancel_event.clear()
        self.model.reset()
