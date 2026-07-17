"""Frozen, independently certified holdout positions for MCTS Search V4.

The certificates in this module describe bounded local obligations only.  They
are deliberately produced without importing :mod:`mcts` so the search code
cannot certify itself.  A positive is override-eligible only when at least one
legal action is locally proven and every other legal action is locally
disproven.  Decoys exercise the mandatory abstention path.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
import hashlib
import json
import random

from actions import RulesAction, RulesState, apply_action, legal_actions
from mcts_telemetry import action_key
from varde import BLACK, WHITE, Game, control, groups_of, other, signature


HOLDOUT_FORMAT = "varde-mcts-v4-certified-holdout"
HOLDOUT_VERSION = 1
CERTIFICATE_FORMAT = "varde-bounded-local-obligation-certificate"
CERTIFICATE_VERSION = 1
CATEGORIES = (
    "capture",
    "defense",
    "rescue",
    "fence",
    "takeover",
    "ending",
)
STATUSES = frozenset(("proven", "disproven", "unknown"))
MAX_ROOT_ACTIONS = 12


@dataclass(frozen=True)
class HoldoutPosition:
    id: str
    category: str
    description: str
    state: RulesState
    obligation: dict
    acceptable_actions: tuple[RulesAction, ...]
    certificate: dict
    provenance: dict
    decoy: bool = False

    def public_dict(self):
        return {
            "id": self.id,
            "category": self.category,
            "description": self.description,
            "rules": self.state.game.rules,
            "board_size": self.state.game.board.n,
            "actor_color": self.state.actor_color,
            "root_legal_actions": len(legal_actions(self.state)),
            "state_key_sha256": state_hash(self.state),
            "obligation": self.obligation,
            "acceptable_actions": [
                action_key(action) for action in self.acceptable_actions
            ],
            "certificate": self.certificate,
            "provenance": self.provenance,
            "decoy": self.decoy,
        }


def state_hash(state):
    return hashlib.sha256(repr(state.key()).encode()).hexdigest()


def _color_at(state, point, color):
    return control(state.game.state, point) == color


def _threatened_groups(state):
    if state.game.finished:
        return ()
    threatened = []
    color = state.actor_color
    for component in groups_of(state.game.board, state.game.state, color):
        liberties = {
            neighbor
            for point in component
            for neighbor in state.game.board.neighbors[point]
            if not state.game.state[neighbor]
        }
        if len(liberties) == 1:
            threatened.append((tuple(sorted(component)), next(iter(liberties))))
    return tuple(threatened)


def _capture_status(state, action, obligation, counter):
    del obligation
    if action.kind not in ("play", "extend"):
        return "disproven"
    advanced = apply_action(state, action)
    counter[0] += 1
    captured = sum(len(wave) for wave in advanced.game.last_capture_waves)
    if captured < 1 or not _color_at(advanced, action.point, state.actor_color):
        return "disproven"
    actor = state.actor_color
    for reply in legal_actions(advanced):
        replied = apply_action(advanced, reply)
        counter[0] += 1
        if not _color_at(replied, action.point, actor):
            return "disproven"
    return "proven"


def _defense_status(state, action, obligation, counter):
    anchor = tuple(obligation["anchor"])
    liberty = tuple(obligation["liberty"])
    if action.kind not in ("play", "extend") or action.point != liberty:
        return "disproven"
    actor = state.actor_color
    advanced = apply_action(state, action)
    counter[0] += 1
    if not _color_at(advanced, anchor, actor):
        return "disproven"
    for reply in legal_actions(advanced):
        replied = apply_action(advanced, reply)
        counter[0] += 1
        if not _color_at(replied, anchor, actor):
            return "disproven"
    return "proven"


def _rescue_can_close(state, actor, anchor, horizon, counter, memo):
    key = (state.key(), actor, anchor, horizon)
    if key in memo:
        return memo[key]
    if horizon < 0:
        return None
    actions = legal_actions(state)
    finish = next(
        (action for action in actions if action.kind == "finish-extension"),
        None,
    )
    if finish is not None:
        closed = apply_action(state, finish)
        counter[0] += 1
        if _color_at(closed, anchor, actor):
            memo[key] = True
            return True
    if horizon == 0:
        memo[key] = None
        return None
    unknown = False
    for action in actions:
        if action.kind != "extend":
            continue
        advanced = apply_action(state, action)
        counter[0] += 1
        result = _rescue_can_close(
            advanced,
            actor,
            anchor,
            horizon - 1,
            counter,
            memo,
        )
        if result is True:
            memo[key] = True
            return True
        unknown = unknown or result is None
    memo[key] = None if unknown else False
    return memo[key]


def _rescue_status(state, action, obligation, counter):
    if action.kind != "extend":
        return "disproven"
    anchor = tuple(obligation["anchor"])
    actor = state.actor_color
    advanced = apply_action(state, action)
    counter[0] += 1
    result = _rescue_can_close(
        advanced,
        actor,
        anchor,
        obligation["horizon"] - 1,
        counter,
        {},
    )
    if result is True:
        return "proven"
    if result is False:
        return "disproven"
    return "unknown"


def _fence_owner(game, cell):
    owners = {
        control(game.state, point) for point in game.board.cell_edges[cell]
    }
    return next(iter(owners)) if len(owners) == 1 else None


def _fence_status(state, action, obligation, counter):
    cell = tuple(obligation["cell"])
    actor = state.actor_color
    advanced = apply_action(state, action)
    counter[0] += 1
    if _fence_owner(advanced.game, cell) != actor:
        return "disproven"
    for reply in legal_actions(advanced):
        replied = apply_action(advanced, reply)
        counter[0] += 1
        if _fence_owner(replied.game, cell) != actor:
            return "disproven"
    return "proven"


def _takeover_status(state, action, obligation, counter):
    del obligation
    root_seat = state.actor_seat
    advanced = apply_action(state, action)
    counter[0] += 1
    color = advanced.color_for_seat(root_seat)
    margin = advanced.game.score()[color] - advanced.game.score()[other(color)]
    if margin > 0:
        return "proven"
    if margin < 0:
        return "disproven"
    return "unknown"


def _ending_status(state, action, obligation, counter):
    del obligation
    score = state.game.score()
    actor = state.actor_color
    margin = score[actor] - score[other(actor)]
    counter[0] += 1
    if margin < 0:
        if action.kind == "resume":
            return "proven"
        if action.kind == "accept":
            return "disproven"
    elif margin > 0:
        if action.kind == "accept":
            return "proven"
        if action.kind == "resume":
            return "disproven"
    return "unknown"


_VERIFIERS = {
    "capture": _capture_status,
    "defense": _defense_status,
    "rescue": _rescue_status,
    "fence": _fence_status,
    "takeover": _takeover_status,
    "ending": _ending_status,
}


def certify_obligation(state, obligation, *, node_limit=100_000):
    """Exhaustively classify legal root actions for one bounded obligation."""
    category = obligation["category"]
    if category not in _VERIFIERS:
        raise ValueError("unknown V4 holdout obligation")
    counter = [0]
    statuses = {}
    for action in legal_actions(state):
        if counter[0] >= node_limit:
            status = "unknown"
        else:
            status = _VERIFIERS[category](state, action, obligation, counter)
        if status not in STATUSES:
            raise AssertionError("invalid verifier status")
        statuses[action_key(action)] = status
    proven = tuple(
        action
        for action in legal_actions(state)
        if statuses[action_key(action)] == "proven"
    )
    alternatives = [
        status
        for key, status in statuses.items()
        if key not in {action_key(action) for action in proven}
    ]
    override_eligible = len(proven) == 1 and all(
        status == "disproven" for status in alternatives
    )
    return proven, {
        "format": CERTIFICATE_FORMAT,
        "version": CERTIFICATE_VERSION,
        "scope": obligation["scope"],
        "horizon": obligation["horizon"],
        "root_actions": len(statuses),
        "action_statuses": dict(sorted(statuses.items())),
        "nodes": counter[0],
        "node_limit": node_limit,
        "override_eligible": override_eligible,
        "claim_limit": (
            "bounded local obligation only; not a game-theoretic result"
        ),
    }


def _freeze(game):
    game.history = {signature(game.board, game.state, game.to_move)}
    return RulesState.from_game(game)


def replay_seeded_state(rules, n, seed, plies):
    """Replay a compact, deterministic legal trajectory used by the corpus."""
    rng = random.Random(seed)
    state = RulesState.from_game(Game(n, rules=rules))
    transcript = []
    for _ply in range(plies):
        actions = legal_actions(state)
        if state.terminal or not actions:
            raise AssertionError("seeded trajectory ended before requested state")
        if state.game.finished:
            action = next(
                (item for item in actions if item.kind == "resume"),
                next(item for item in actions if item.kind == "accept"),
            )
        else:
            candidates = [
                item
                for item in actions
                if item.kind not in ("pass", "accept")
            ]
            action = rng.choice(candidates or list(actions))
        transcript.append(action_key(action))
        state = apply_action(state, action)
    return state, tuple(transcript)


def _make_position(
    position_id,
    category,
    description,
    state,
    obligation,
    provenance,
    *,
    decoy=False,
):
    before = state.key()
    actions = legal_actions(state)
    if not 2 <= len(actions) <= MAX_ROOT_ACTIONS:
        raise AssertionError(f"{position_id} root width is outside 2..12")
    proven, certificate = certify_obligation(state, obligation)
    if decoy:
        if certificate["override_eligible"]:
            raise AssertionError(f"{position_id} decoy permits an override")
        acceptable = ()
    else:
        if not certificate["override_eligible"]:
            raise AssertionError(f"{position_id} positive is not strict")
        acceptable = proven
    if state.key() != before:
        raise AssertionError("holdout verifier mutated a position")
    return HoldoutPosition(
        position_id,
        category,
        description,
        state,
        obligation,
        acceptable,
        certificate,
        provenance,
        decoy,
    )


def _obligation(category, **details):
    scopes = {
        "capture": "capture remains safe through every immediate reply",
        "defense": "threatened friendly group survives every immediate reply",
        "rescue": "rescue reaches extension-turn closure with target alive",
        "fence": "completed fence remains complete through every immediate reply",
        "takeover": "original seat owns the strictly leading color after choice",
        "ending": (
            "seat accepts a lead or uses its one legal resumption while behind"
        ),
    }
    return {
        "category": category,
        "scope": scopes[category],
        "horizon": 4 if category == "rescue" else (0 if category in (
            "takeover", "ending"
        ) else 1),
        **details,
    }


def _seeded_provenance(rules, n, seed, plies, transcript, *, suffix=()):
    rendered = (*transcript, *suffix)
    return {
        "kind": "reachable-seeded-play",
        "rules": rules,
        "board_size": n,
        "seed": seed,
        "seeded_plies": plies,
        "post_actions": list(suffix),
        "plies": plies + len(suffix),
        "transcript_sha256": hashlib.sha256(
            json.dumps(rendered, separators=(",", ":")).encode()
        ).hexdigest(),
    }


def _seeded_position(
    position_id,
    category,
    description,
    rules,
    n,
    seed,
    plies,
    obligation,
    *,
    decoy=False,
):
    state, transcript = replay_seeded_state(rules, n, seed, plies)
    return _make_position(
        position_id,
        category,
        description,
        state,
        obligation,
        _seeded_provenance(rules, n, seed, plies, transcript),
        decoy=decoy,
    )


def _ending_position(
    position_id,
    description,
    n,
    seed,
    plies,
    *,
    decoy=False,
):
    state, transcript = replay_seeded_state("breath", n, seed, plies)
    passes = (RulesAction("pass"), RulesAction("pass"))
    for action in passes:
        state = apply_action(state, action)
    return _make_position(
        position_id,
        "ending",
        description,
        state,
        _obligation("ending"),
        _seeded_provenance(
            "breath",
            n,
            seed,
            plies,
            transcript,
            suffix=("pass", "pass"),
        ),
        decoy=decoy,
    )


def _takeover_state(rules, n, *, balanced=False):
    game = Game(n, rules=rules)
    points = list(game.board.points)
    if balanced:
        random.Random(0).shuffle(points)
        split = len(points) // 2
        for index, point in enumerate(points):
            game.state[point] = (BLACK if index < split else WHITE,)
    else:
        for point in points:
            game.state[point] = (BLACK,)
    game.to_move = WHITE
    game.moves_played = 1
    game.swap_decided = False
    return _freeze(game)


def _takeover_position(
    position_id,
    description,
    rules,
    n,
    *,
    decoy=False,
):
    return _make_position(
        position_id,
        "takeover",
        description,
        _takeover_state(rules, n, balanced=decoy),
        _obligation("takeover"),
        {
            "kind": "constructed-decision-isolation",
            "construction": (
                "seed-0 balanced full board" if decoy else "full Black board"
            ),
            "rules": rules,
            "board_size": n,
        },
        decoy=decoy,
    )


@cache
def positive_positions():
    """Return the sealed 24-position positive corpus."""
    positions = (
        _seeded_position(
            "v4-capture-toy-a", "capture",
            "The sole safe capture remains alive through the reply.",
            "breath", 3, 20260728000, 52, _obligation("capture"),
        ),
        _seeded_position(
            "v4-capture-toy-b", "capture",
            "A later root preserves the same unique safe capture.",
            "breath", 3, 20260728000, 54, _obligation("capture"),
        ),
        _seeded_position(
            "v4-capture-beginner-a", "capture",
            "Find the unique safe capture on the wider board.",
            "breath", 4, 20260729000, 93, _obligation("capture"),
        ),
        _seeded_position(
            "v4-capture-beginner-b", "capture",
            "Preserve the only capture that survives an immediate reply.",
            "breath", 4, 20260729000, 95, _obligation("capture"),
        ),
        _seeded_position(
            "v4-defense-toy-a", "defense",
            "Fill the sole liberty and survive every immediate reply.",
            "breath", 3, 20260749001, 43,
            _obligation("defense", anchor=[-8, 0], liberty=[-7, 1]),
        ),
        _seeded_position(
            "v4-defense-toy-b", "defense",
            "Defend the threatened edge group through one reply.",
            "breath", 3, 20260749002, 41,
            _obligation("defense", anchor=[-8, 2], liberty=[-5, 3]),
        ),
        _seeded_position(
            "v4-defense-beginner-a", "defense",
            "Find the only reply-safe defense on Beginner.",
            "breath", 4, 20260750001, 82,
            _obligation("defense", anchor=[5, 5], liberty=[4, 6]),
        ),
        _seeded_position(
            "v4-defense-beginner-b", "defense",
            "Save the opposite-edge group through the reply horizon.",
            "breath", 4, 20260750002, 86,
            _obligation("defense", anchor=[4, -6], liberty=[5, -5]),
        ),
        _seeded_position(
            "v4-rescue-toy-a", "rescue",
            "Continue the rescue and close with the target alive.",
            "breath-run", 3, 20260720000, 45,
            _obligation("rescue", anchor=[-5, 3], liberty=[-5, 1]),
        ),
        _seeded_position(
            "v4-rescue-toy-b", "rescue",
            "The later extension root still has one certified continuation.",
            "breath-run", 3, 20260720000, 47,
            _obligation("rescue", anchor=[-5, 3], liberty=[-5, 1]),
        ),
        _seeded_position(
            "v4-rescue-beginner-a", "rescue",
            "Close a seeded Beginner rescue with the target alive.",
            "breath-run", 4, 20260721000, 95,
            _obligation("rescue", anchor=[-10, 4], liberty=[-5, 5]),
        ),
        _seeded_position(
            "v4-rescue-beginner-b", "rescue",
            "Resolve a second seeded Beginner rescue obligation.",
            "breath-run", 4, 20260721000, 97,
            _obligation("rescue", anchor=[-11, -3], liberty=[-2, -4]),
        ),
        _seeded_position(
            "v4-fence-toy-a", "fence",
            "Complete the center fence so it survives one reply.",
            "gjerde", 3, 20260722000, 67,
            _obligation("fence", cell=[0, 0]),
        ),
        _seeded_position(
            "v4-fence-toy-b", "fence",
            "Complete a neighboring durable fence.",
            "gjerde", 3, 20260722000, 68,
            _obligation("fence", cell=[0, -1]),
        ),
        _seeded_position(
            "v4-fence-beginner-a", "fence",
            "Seal a durable boundary on the Beginner board.",
            "gjerde", 4, 20260723000, 131,
            _obligation("fence", cell=[-3, 3]),
        ),
        _seeded_position(
            "v4-fence-beginner-b", "fence",
            "Choose the sole completion that remains fenced after reply.",
            "gjerde", 4, 20260723000, 132,
            _obligation("fence", cell=[-3, 0]),
        ),
        _takeover_position(
            "v4-takeover-toy-a", "Take the strictly leading Black seat.",
            "breath-run", 3,
        ),
        _takeover_position(
            "v4-takeover-toy-b", "Take the fenced Black lead.",
            "gjerde", 3,
        ),
        _takeover_position(
            "v4-takeover-beginner-a", "Take the larger Black lead.",
            "breath", 4,
        ),
        _takeover_position(
            "v4-takeover-beginner-b", "Take the larger fenced lead.",
            "gjerde", 4,
        ),
        _ending_position(
            "v4-ending-toy-a", "Accept the seeded one-point lead.",
            3, 20260724300, 12,
        ),
        _ending_position(
            "v4-ending-toy-b", "Use the legal resumption while behind.",
            3, 20260724301, 13,
        ),
        _ending_position(
            "v4-ending-beginner-a", "Resume the seeded losing score.",
            4, 20260724400, 12,
        ),
        _ending_position(
            "v4-ending-beginner-b", "Resume a second losing score.",
            4, 20260724401, 13,
        ),
    )
    return _validate_corpus(positions, positives=True)


@cache
def decoy_positions():
    """Return twelve exact abstention cases, two per obligation category."""
    positions = (
        _seeded_position(
            "v4-decoy-capture-toy", "capture",
            "Several captures survive, so no unique override is certified.",
            "breath", 3, 20260720000, 42, _obligation("capture"), decoy=True,
        ),
        _seeded_position(
            "v4-decoy-capture-beginner", "capture",
            "The wider root has several locally safe captures.",
            "breath", 4, 20260721000, 89, _obligation("capture"), decoy=True,
        ),
        _seeded_position(
            "v4-decoy-defense-toy", "defense",
            "The apparent sole-liberty defense fails the reply proof.",
            "breath", 3, 20260734001, 43,
            _obligation("defense", anchor=[-7, 3], liberty=[-8, 2]),
            decoy=True,
        ),
        _seeded_position(
            "v4-decoy-defense-beginner", "defense",
            "The apparent Beginner defense is refuted immediately.",
            "breath", 4, 20260735000, 89,
            _obligation("defense", anchor=[-11, 3], liberty=[-10, 2]),
            decoy=True,
        ),
        _seeded_position(
            "v4-decoy-rescue-toy", "rescue",
            "The extension cannot be certified inside the declared horizon.",
            "breath-run", 3, 20260739002, 28,
            _obligation("rescue", anchor=[-8, -2], liberty=[-7, -3]),
            decoy=True,
        ),
        _seeded_position(
            "v4-decoy-rescue-beginner", "rescue",
            "The longer rescue remains unknown at the fixed horizon.",
            "breath-run", 4, 20260740000, 85,
            _obligation("rescue", anchor=[-7, -5], liberty=[1, -5]),
            decoy=True,
        ),
        _seeded_position(
            "v4-decoy-fence-toy", "fence",
            "The fence is already durable under every action; abstain.",
            "gjerde", 3, 20260744000, 70,
            _obligation("fence", cell=[0, 0]), decoy=True,
        ),
        _seeded_position(
            "v4-decoy-fence-beginner", "fence",
            "No unique action owns an already durable fence.",
            "gjerde", 4, 20260745000, 128,
            _obligation("fence", cell=[-2, -1]), decoy=True,
        ),
        _takeover_position(
            "v4-decoy-takeover-toy", "A tied full board gives no proven swap.",
            "breath", 3, decoy=True,
        ),
        _takeover_position(
            "v4-decoy-takeover-beginner",
            "A tied Beginner board makes takeover locally ambiguous.",
            "breath", 4, decoy=True,
        ),
        _ending_position(
            "v4-decoy-ending-toy", "A tied score proves neither ending choice.",
            3, 20260729000, 2, decoy=True,
        ),
        _ending_position(
            "v4-decoy-ending-beginner",
            "A tied Beginner score requires solver abstention.",
            4, 20260730000, 2, decoy=True,
        ),
    )
    return _validate_corpus(positions, positives=False)


def _validate_corpus(positions, *, positives):
    positions = tuple(positions)
    expected = 24 if positives else 12
    if len(positions) != expected:
        raise AssertionError("unexpected V4 holdout corpus size")
    if len({position.id for position in positions}) != expected:
        raise AssertionError("V4 holdout ids are not unique")
    if len({state_hash(position.state) for position in positions}) != expected:
        raise AssertionError("V4 holdout state hashes are not unique")
    expected_per_category = 4 if positives else 2
    for category in CATEGORIES:
        selected = [item for item in positions if item.category == category]
        if len(selected) != expected_per_category:
            raise AssertionError("V4 holdout category count differs")
        if positives and sorted(item.state.game.board.n for item in selected) != [
            3, 3, 4, 4
        ]:
            raise AssertionError("positive size stratification differs")
    return positions


@cache
def holdout_positions():
    positions = (*positive_positions(), *decoy_positions())
    if len({state_hash(position.state) for position in positions}) != len(positions):
        raise AssertionError("positive and decoy state hashes overlap")
    return positions


def holdout_catalog(positions=None):
    positions = holdout_positions() if positions is None else tuple(positions)
    payload = {
        "format": HOLDOUT_FORMAT,
        "version": HOLDOUT_VERSION,
        "positions": [position.public_dict() for position in positions],
    }
    payload["payload_sha256"] = hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
    ).hexdigest()
    return payload
