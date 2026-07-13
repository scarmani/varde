"""Persistent linear learning model and background trainer for Cairn."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import random
import threading

from cairn import BLACK, Game, other


FEATURE_NAMES = (
    "controlled",
    "skies",
    "liberties",
    "vulnerable",
    "development",
    "territory",
)
LEARNING_RATE = 0.03
L2_DECAY = 0.0005
WEIGHT_LIMIT = 4.0
LEARNED_SCALE = 20.0
TRAINING_BATCHES = frozenset((10, 50, 200))


def default_model_path():
    override = os.environ.get("CAIRN_MODEL_PATH")
    return Path(override).expanduser() if override else Path.home() / ".cairn" / "advanced-model.json"


@dataclass
class LearningModel:
    path: Path = field(default_factory=default_model_path)
    weights: dict = field(default_factory=lambda: {name: 0.0 for name in FEATURE_NAMES})
    games_trained: int = 0
    training_seed: int = 1
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
            if payload.get("format") != "cairn-linear-eval" or payload.get("version") != 1:
                raise ValueError("unsupported learning model")
            raw = payload.get("weights", {})
            if set(raw) != set(FEATURE_NAMES):
                raise ValueError("invalid learning weights")
            weights = {name: float(raw[name]) for name in FEATURE_NAMES}
            if any(
                not math.isfinite(value) or not -WEIGHT_LIMIT <= value <= WEIGHT_LIMIT
                for value in weights.values()
            ):
                raise ValueError("invalid learning weight")
            model.weights = weights
            model.games_trained = int(payload.get("games_trained", 0))
            model.training_seed = int(payload.get("training_seed", 1))
            model.updated_at = payload.get("updated_at")
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            model.load_error = str(exc)
        return model

    def to_dict(self):
        with self.lock:
            return {
                "format": "cairn-linear-eval",
                "version": 1,
                "weights": dict(self.weights),
                "games_trained": self.games_trained,
                "training_seed": self.training_seed,
                "updated_at": self.updated_at,
            }

    def status(self):
        payload = self.to_dict()
        payload.pop("format")
        payload.pop("version")
        payload["trained"] = payload["games_trained"] > 0
        payload["load_error"] = self.load_error
        return payload

    def correction(self, features, perspective):
        with self.lock:
            value = sum(self.weights[name] * features[name] for name in FEATURE_NAMES)
        return LEARNED_SCALE * value * (1 if perspective == BLACK else -1)

    def update(self, samples, outcome, seed):
        with self.lock:
            for features in samples:
                raw = sum(self.weights[name] * features[name] for name in FEATURE_NAMES)
                prediction = 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, raw))))
                error = outcome - prediction
                for name in FEATURE_NAMES:
                    gradient = error * features[name] - L2_DECAY * self.weights[name]
                    value = self.weights[name] + LEARNING_RATE * gradient
                    self.weights[name] = max(-WEIGHT_LIMIT, min(WEIGHT_LIMIT, value))
            self.games_trained += 1
            self.training_seed = seed
            self.updated_at = datetime.now(timezone.utc).isoformat()
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
            self.games_trained = 0
            self.training_seed = 1
            self.updated_at = None
            self.load_error = None
        if self.path.exists():
            self.path.unlink()


def play_training_game(model, seed, index, cancel_event):
    """Run one deterministic learner-vs-fixed game and return samples/outcome."""
    from opponent import choose_decision, normalized_features

    rng = random.Random((seed << 16) + index)
    n = 4 if index % 4 == 3 else 3
    game = Game(n)
    learner_color = BLACK if index % 2 == 0 else other(BLACK)
    samples = []
    turns = 0
    limit = 20 * len(game.board.points)
    completed = False
    while turns < limit and not cancel_event.is_set():
        if game.moves_played > 0 and game.moves_played % 4 == 0:
            samples.append(normalized_features(game.board, game.state, game.moves_played))
        color = game.to_move
        if not game.finished and rng.random() < 0.10:
            legal = game.legal_placements()
            decision = None
            if legal:
                point = rng.choice(legal)
                game.play(point)
            else:
                game.play_pass()
        else:
            difficulty = "advanced" if color == learner_color else "standard"
            decision = choose_decision(
                game,
                color,
                difficulty=difficulty,
                seed=seed + index,
                model=model,
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
            elif decision.action == "accept":
                completed = True
                break
        turns += 1
        if game.finished and game.resumption_used:
            completed = True
            break
    if not completed or cancel_event.is_set():
        return [], None, False
    score = game.score()
    outcome = 1.0 if score[BLACK] > score[other(BLACK)] else 0.0
    if score[BLACK] == score[other(BLACK)]:
        outcome = 0.5
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
                "model": self.model.status(),
            }

    def start(self, games, seed=1):
        if not isinstance(games, int) or games <= 0:
            raise ValueError("games must be a positive integer")
        with self.lock:
            if self.running:
                raise ValueError("training is already running")
            self.running = True
            self.total = games
            self.completed = 0
            self.discarded = 0
            self.error = None
            self.seed = int(seed)
            self.cancel_event.clear()
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()

    def _run(self):
        try:
            for index in range(self.total):
                if self.cancel_event.is_set():
                    break
                samples, outcome, completed = self.runner(
                    self.model, self.seed, index, self.cancel_event
                )
                if completed:
                    self.model.update(samples, outcome, self.seed)
                    self.model.save()
                    with self.lock:
                        self.completed += 1
                else:
                    with self.lock:
                        self.discarded += 1
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
            self.cancel_event.clear()
        self.model.reset()
