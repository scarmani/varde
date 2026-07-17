"""Frozen-development builders for the MCTS Search V5 corpora.

The development and holdout catalogs use different constructions, seeds, and
state hashes.  Each contains 24 positions: twelve Toy and twelve Beginner,
twelve narrow roots (2..12 actions) and twelve wide roots (at least 32), four
positions per tactical family, and one exact abstention decoy per family.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
import hashlib
import json
import random

from actions import RulesAction, RulesState, apply_action, legal_actions
from mcts_v5_oracle import action_id, certify_goal, goal, state_hash
from varde import BLACK, WHITE, Game, signature


CORPUS_FORMAT = "varde-mcts-search-v5-tactical-corpus"
CORPUS_VERSION = 1
FAMILIES = ("capture", "defense", "rescue", "fence", "takeover", "ending")
WIDTH_CLASSES = frozenset(("narrow", "wide"))


@dataclass(frozen=True)
class V5Position:
    id: str
    split: str
    family: str
    description: str
    state: RulesState
    goal: dict
    provenance: dict
    width_class: str
    decoy: bool = False
    tags: tuple[str, ...] = ()
    hand_audit: bool = False

    def certificate(self):
        return certify_goal(self.state, self.goal)

    @property
    def acceptable_actions(self):
        return self.certificate().proven_actions

    def public_dict(self):
        certificate = self.certificate()
        payload = {
            "id": self.id,
            "split": self.split,
            "family": self.family,
            "description": self.description,
            "rules": self.state.game.rules,
            "board_size": self.state.game.board.n,
            "actor_seat": self.state.actor_seat,
            "actor_color": self.state.actor_color,
            "root_legal_actions": len(legal_actions(self.state)),
            "width_class": self.width_class,
            "state_key_sha256": state_hash(self.state),
            "goal": self.goal,
            "acceptable_actions": [
                action_id(action) for action in certificate.proven_actions
            ],
            "certificate": certificate.to_dict(),
            "provenance": self.provenance,
            "decoy": self.decoy,
            "tags": list(self.tags),
            "hand_audit": self.hand_audit,
        }
        if self.hand_audit:
            trace_map = dict(certificate.traces)
            if certificate.proven_actions:
                audited = action_id(certificate.proven_actions[0])
            else:
                audited = action_id(legal_actions(self.state)[0])
            payload["hand_audit_trace"] = {
                "action": audited,
                "records": list(trace_map[audited]),
            }
        return payload


def _freeze(game, *, moves=8):
    game.moves_played = moves
    game.swap_decided = True
    game.history = {signature(game.board, game.state, game.to_move)}
    return RulesState.from_game(game)


def _replay(rules, n, seed, plies):
    rng = random.Random(seed)
    state = RulesState.from_game(Game(n, rules=rules))
    transcript = []
    for _ply in range(plies):
        actions = legal_actions(state)
        if state.terminal or not actions:
            raise AssertionError("seeded V5 trajectory ended before target")
        if state.game.finished:
            action = next(
                (item for item in actions if item.kind == "resume"),
                next(item for item in actions if item.kind == "accept"),
            )
        else:
            candidates = [
                item for item in actions
                if item.kind not in ("pass", "accept")
            ]
            action = rng.choice(candidates or list(actions))
        transcript.append(action_id(action))
        state = apply_action(state, action)
    return state, tuple(transcript)


def _seeded_provenance(rules, n, seed, plies, transcript, *, suffix=()):
    actions = (*transcript, *suffix)
    return {
        "kind": "reachable-seeded-play",
        "rules": rules,
        "board_size": n,
        "seed": seed,
        "seeded_plies": plies,
        "post_actions": list(suffix),
        "transcript_sha256": hashlib.sha256(
            json.dumps(actions, separators=(",", ":")).encode()
        ).hexdigest(),
    }


def _closed_neighborhood(game, point):
    return {point, *game.board.neighbors[point]}


def _pattern_centers(game, count, variant):
    candidates = sorted(
        point for point in game.board.points
        if len(game.board.neighbors[point]) == 3
    )
    if not candidates:
        raise AssertionError("fixture board has no degree-three point")
    rotated = candidates[variant % len(candidates):] + candidates[:variant % len(candidates)]
    selected = []
    occupied = set()
    for point in rotated:
        neighborhood = _closed_neighborhood(game, point)
        if neighborhood.isdisjoint(occupied):
            selected.append(point)
            occupied.update(neighborhood)
            if len(selected) == count:
                return tuple(selected)
    raise AssertionError("fixture board lacks disjoint local patterns")


def _install_capture(game, center):
    first, second, liberty = game.board.neighbors[center]
    game.state[center] = (WHITE,)
    game.state[first] = (BLACK,)
    game.state[second] = (BLACK,)
    return liberty


def _install_defense(game, center):
    first, second, liberty = game.board.neighbors[center]
    game.state[center] = (BLACK,)
    game.state[first] = (WHITE,)
    game.state[second] = (WHITE,)
    return liberty


def _capture_goal():
    return goal(
        "capture",
        "immediate capture remains controlled through every legal reply",
        "immediate-capture",
        "action-point-controlled",
        quantifier_schedule=({"quantifier": "forall", "actor": "any"},),
    )


def _defense_goal(anchor, liberty):
    return goal(
        "defense",
        "specified sole-liberty group survives every legal reply",
        "specified-defense",
        "anchor-controlled",
        quantifier_schedule=({"quantifier": "forall", "actor": "any"},),
        parameters={"anchor": list(anchor), "liberty": list(liberty)},
    )


def _rescue_goal(anchor):
    step = {
        "quantifier": "exists",
        "actor": "root-seat",
        "action_kinds": ["extend", "finish-extension"],
    }
    return goal(
        "rescue",
        "extension chain closes with the original target still controlled",
        "rescue-extension",
        "rescue-closed-alive",
        success_mode="closure",
        quantifier_schedule=(step, step, step, step),
        parameters={"anchor": list(anchor)},
    )


def _fence_goal(cell, completion, *, durable):
    return goal(
        "fence",
        (
            "specified fence remains owned through every legal reply"
            if durable else "specified fence is owned immediately"
        ),
        "specified-fence-completion",
        "fence-owned",
        quantifier_schedule=(
            ({"quantifier": "forall", "actor": "any"},) if durable else ()
        ),
        parameters={"cell": list(cell), "completion": list(completion)},
    )


def _takeover_goal():
    return goal(
        "takeover",
        "original acting seat owns the strictly leading color after choice",
        "takeover-choice",
        "root-seat-leading",
    )


def _ending_goal():
    return goal(
        "ending",
        "accept a strict lead or use the legal resumption while behind",
        "ending-choice",
        "ending-choice-rational",
    )


def _wide_capture(split, n, variant, *, double=False, conflict=False):
    game = Game(n, rules="breath")
    game.to_move = BLACK
    centers = _pattern_centers(game, 2 if double or conflict else 1, variant)
    liberties = [_install_capture(game, centers[0])]
    if double:
        liberties.append(_install_capture(game, centers[1]))
    elif conflict:
        _install_defense(game, centers[1])
    state = _freeze(game, moves=8 + variant)
    tags = []
    if double:
        tags.append("equivalent-proven-set")
    if conflict:
        tags.append("conflicting-capture-defense-obligations")
    return state, _capture_goal(), {
        "kind": "constructed-wide-local-pattern",
        "variant": variant,
        "centers": [list(point) for point in centers],
        "capture_liberties": [list(point) for point in liberties],
        "split": split,
    }, tuple(tags)


def _wide_defense(split, n, variant):
    game = Game(n, rules="breath")
    game.to_move = BLACK
    center = _pattern_centers(game, 1, variant)[0]
    liberty = _install_defense(game, center)
    state = _freeze(game, moves=10 + variant)
    return state, _defense_goal(center, liberty), {
        "kind": "constructed-wide-local-pattern",
        "variant": variant,
        "center": list(center),
        "liberty": list(liberty),
        "split": split,
    }


def _wide_rescue(split, n, variant):
    game = Game(n, rules="breath-run")
    game.to_move = BLACK
    center = _pattern_centers(game, 1, variant)[0]
    first, second, liberty = game.board.neighbors[center]
    onward = [
        point for point in game.board.neighbors[liberty] if point != center
    ]
    game.state[center] = (BLACK,)
    game.state[first] = (WHITE,)
    game.state[second] = (WHITE,)
    game.state[onward[variant % len(onward)]] = (WHITE,)
    state = _freeze(game, moves=12 + variant)
    if RulesAction("extend", liberty) not in legal_actions(state):
        raise AssertionError("wide rescue entry is not legal")
    return state, _rescue_goal(center), {
        "kind": "constructed-wide-rescue-entry",
        "variant": variant,
        "center": list(center),
        "entry": list(liberty),
        "split": split,
    }


def _narrow_rescue(split, n, variant):
    state, goal_spec, provenance = _wide_rescue(split, n, variant)
    entry = next(
        action for action in legal_actions(state) if action.kind == "extend"
    )
    state = apply_action(state, entry)
    provenance = {
        **provenance,
        "kind": "constructed-actor-changing-rescue-continuation",
        "prefix_action": action_id(entry),
    }
    return state, goal_spec, provenance


def _wide_fence(split, n, variant, *, durable=True):
    rules = "gjerde" if durable else "gjerde-go"
    game = Game(n, rules=rules)
    game.to_move = BLACK
    cells = sorted(game.board.cells)
    cell = cells[variant % len(cells)]
    edges = game.board.cell_edges[cell]
    for point in edges[:-1]:
        game.state[point] = (BLACK,)
    completion = edges[-1]
    state = _freeze(game, moves=14 + variant)
    return state, _fence_goal(cell, completion, durable=durable), {
        "kind": "constructed-wide-fence",
        "variant": variant,
        "cell": list(cell),
        "completion": list(completion),
        "durable": durable,
        "split": split,
    }


def _wide_takeover(split, n, variant):
    game = Game(n, rules="breath")
    points = sorted(game.board.points)
    opening = points[variant % len(points)]
    game.play(opening)
    state = RulesState.from_game(game)
    return state, _takeover_goal(), {
        "kind": "reachable-one-move-opening",
        "opening": list(opening),
        "variant": variant,
        "split": split,
    }


def _narrow_takeover(split, n, variant, *, balanced):
    rules = "breath" if balanced or variant % 2 == 0 else "gjerde"
    game = Game(n, rules=rules)
    points = list(game.board.points)
    random.Random(variant).shuffle(points)
    if balanced:
        split_at = len(points) // 2
        for index, point in enumerate(points):
            game.state[point] = (BLACK if index < split_at else WHITE,)
    else:
        white_points = 1 + variant % 3
        for index, point in enumerate(points):
            game.state[point] = (WHITE if index < white_points else BLACK,)
    game.to_move = WHITE
    game.moves_played = 1
    game.swap_decided = False
    state = _freeze(game, moves=1)
    state.game.swap_decided = False
    return state, _takeover_goal(), {
        "kind": "constructed-takeover-isolation",
        "balanced": balanced,
        "variant": variant,
        "rules": rules,
        "split": split,
    }


def _seeded_state(rules, n, seed, plies):
    state, transcript = _replay(rules, n, seed, plies)
    return state, _seeded_provenance(rules, n, seed, plies, transcript)


def _ending_state(n, seed, plies):
    state, transcript = _replay("breath", n, seed, plies)
    for action in (RulesAction("pass"), RulesAction("pass")):
        state = apply_action(state, action)
    provenance = _seeded_provenance(
        "breath",
        n,
        seed,
        plies,
        transcript,
        suffix=("pass", "pass"),
    )
    return state, _ending_goal(), provenance


def _position(
    split,
    family,
    suffix,
    description,
    state,
    goal_spec,
    provenance,
    width_class,
    *,
    decoy=False,
    tags=(),
    hand_audit=False,
):
    return V5Position(
        f"v5-{split}-{family}-{suffix}",
        split,
        family,
        description,
        state,
        goal_spec,
        provenance,
        width_class,
        decoy,
        tuple(tags),
        hand_audit,
    )


def _build_split(split):
    if split not in ("development", "holdout"):
        raise ValueError("unknown V5 corpus split")
    offset = 0 if split == "development" else 7
    decoy_seed = 20260820000 if split == "development" else 20260820001

    positions = []

    state, spec, provenance, tags = _wide_capture(split, 3, offset)
    positions.append(_position(
        split, "capture", "toy-wide", "Prove the safe local capture.",
        state, spec, provenance, "wide", tags=tags, hand_audit=True,
    ))
    state, provenance = _seeded_state("breath", 3, decoy_seed, 51 if offset == 0 else 48)
    positions.append(_position(
        split, "capture", "toy-narrow-decoy",
        "No legal action captures, so proof guidance must abstain.",
        state, _capture_goal(), provenance, "narrow", decoy=True,
        hand_audit=True,
    ))
    state, spec, provenance, tags = _wide_capture(
        split, 4, offset + 1, double=True
    )
    positions.append(_position(
        split, "capture", "beginner-wide-equivalent",
        "Retain every equivalent safe capture in the proven set.",
        state, spec, provenance, "wide", tags=tags,
    ))
    state, spec, provenance, tags = _wide_capture(
        split, 4, offset + 3, conflict=True
    )
    positions.append(_position(
        split, "capture", "beginner-wide-conflict",
        "Resolve capture guidance while a defense obligation also exists.",
        state, spec, provenance, "wide", tags=tags,
    ))

    state, spec, provenance = _wide_defense(split, 3, offset + 1)
    positions.append(_position(
        split, "defense", "toy-wide", "Defend the sole-liberty group.",
        state, spec, provenance, "wide", hand_audit=True,
    ))
    defense_decoy_seed = 20260820002 if split == "development" else 20260820003
    state, provenance = _seeded_state("breath", 3, defense_decoy_seed, 59)
    anchor = next(point for point in state.game.board.points if state.game.state[point])
    liberty = next(point for point in state.game.board.points if not state.game.state[point])
    positions.append(_position(
        split, "defense", "toy-narrow-decoy",
        "The specified group is not in sole-liberty danger.",
        state, _defense_goal(anchor, liberty), provenance, "narrow",
        decoy=True, hand_audit=True,
    ))
    state, spec, provenance = _wide_defense(split, 4, offset + 2)
    positions.append(_position(
        split, "defense", "beginner-wide",
        "Defend a wide-root Beginner group through every reply.",
        state, spec, provenance, "wide",
    ))
    defense_seed = 20260800001 if split == "development" else 20260800002
    defense_plies = 84 if split == "development" else 81
    defense_anchor = (-1, -5) if split == "development" else (-7, 5)
    defense_liberty = (2, -6) if split == "development" else (-8, 4)
    state, provenance = _seeded_state("breath", 4, defense_seed, defense_plies)
    positions.append(_position(
        split, "defense", "beginner-narrow",
        "Prove the seeded reply-safe Beginner defense.",
        state, _defense_goal(defense_anchor, defense_liberty), provenance,
        "narrow",
    ))

    state, spec, provenance = _wide_rescue(split, 3, offset)
    positions.append(_position(
        split, "rescue", "toy-wide",
        "Find an actor-preserving entry and existential closure.",
        state, spec, provenance, "wide", tags=("actor-preserving",),
        hand_audit=True,
    ))
    empty = Game(3, rules="breath-run")
    empty.play(sorted(empty.board.points)[offset % len(empty.board.points)])
    state = RulesState.from_game(empty)
    anchor = next(point for point in state.game.board.points if state.game.state[point])
    positions.append(_position(
        split, "rescue", "toy-wide-decoy",
        "No rescue extension exists, so the solver must abstain.",
        state, _rescue_goal(anchor), {
            "kind": "reachable-one-move-no-rescue",
            "opening": list(anchor),
            "split": split,
        }, "wide", decoy=True, hand_audit=True,
    ))
    state, spec, provenance = _wide_rescue(split, 4, offset + 1)
    positions.append(_position(
        split, "rescue", "beginner-wide",
        "Prove a Beginner rescue entry without crossing actor ownership.",
        state, spec, provenance, "wide", tags=("actor-preserving",),
    ))
    state, spec, provenance = _narrow_rescue(split, 4, offset + 2)
    positions.append(_position(
        split, "rescue", "beginner-narrow-closure",
        "Evaluate closure immediately when the extension changes actor.",
        state, spec, provenance, "narrow", tags=("actor-changing",),
    ))

    state, spec, provenance = _wide_fence(split, 3, offset, durable=True)
    positions.append(_position(
        split, "fence", "toy-wide-durable",
        "Prove a reply-durable fence on a wide root.",
        state, spec, provenance, "wide", tags=("durable-fence",),
        hand_audit=True,
    ))
    immediate_seed = 20260810000 if split == "development" else 20260812000
    immediate_plies = 74 if split == "development" else 85
    immediate_cell = (2, 0) if split == "development" else (1, 0)
    immediate_completion = (15, 3) if split == "development" else (3, 1)
    state, provenance = _seeded_state(
        "gjerde-go", 3, immediate_seed, immediate_plies
    )
    positions.append(_position(
        split, "fence", "toy-narrow-immediate",
        "Certify immediate completion without claiming reply durability.",
        state, _fence_goal(
            immediate_cell, immediate_completion, durable=False
        ), provenance, "narrow", tags=("immediate-not-durable",),
    ))
    state, spec, provenance = _wide_fence(split, 4, offset + 1, durable=True)
    positions.append(_position(
        split, "fence", "beginner-wide-durable",
        "Prove a second wide-root durable fence.",
        state, spec, provenance, "wide", tags=("durable-fence",),
    ))
    fence_decoy_seed = 20260820000 if split == "development" else 20260820001
    fence_decoy_plies = 131 if split == "development" else 126
    state, provenance = _seeded_state(
        "gjerde", 4, fence_decoy_seed, fence_decoy_plies
    )
    cell = sorted(state.game.board.cells)[0]
    completion = state.game.board.cell_edges[cell][0]
    positions.append(_position(
        split, "fence", "beginner-narrow-decoy",
        "The specified boundary is not one move from completion.",
        state, _fence_goal(cell, completion, durable=True), provenance,
        "narrow", decoy=True, hand_audit=True,
    ))

    state, spec, provenance = _wide_takeover(split, 3, offset)
    positions.append(_position(
        split, "takeover", "toy-wide",
        "Take the leading opening color from a natural wide pie root.",
        state, spec, provenance, "wide", hand_audit=True,
    ))
    state, spec, provenance = _narrow_takeover(
        split, 3, 20 + offset, balanced=True
    )
    positions.append(_position(
        split, "takeover", "toy-narrow-decoy",
        "A tied full board proves neither pie choice.",
        state, spec, provenance, "narrow", decoy=True, hand_audit=True,
    ))
    state, spec, provenance = _wide_takeover(split, 4, offset + 2)
    positions.append(_position(
        split, "takeover", "beginner-wide",
        "Take the leading opening color on Beginner.",
        state, spec, provenance, "wide",
    ))
    state, spec, provenance = _narrow_takeover(
        split, 4, 30 + offset, balanced=False
    )
    positions.append(_position(
        split, "takeover", "beginner-narrow",
        "Take the isolated overwhelmingly leading seat.",
        state, spec, provenance, "narrow",
    ))

    ending_specs = (
        (3, 20260830001, 6 + (2 if offset else 0), "toy-accept", False),
        (3, 20260830000, 2 + (2 if offset else 0), "toy-tie-decoy", True),
        (4, 20260830000, 3 + (2 if offset else 0), "beginner-resume", False),
        (4, 20260830001, 8 + (2 if offset else 0), "beginner-accept", False),
    )
    for index, (n, seed, plies, suffix, decoy) in enumerate(ending_specs):
        state, spec, provenance = _ending_state(n, seed, plies)
        positions.append(_position(
            split, "ending", suffix,
            (
                "A tied score proves neither ending choice."
                if decoy else "Choose accept or resumption from the real score."
            ),
            state, spec, provenance, "narrow", decoy=decoy,
            hand_audit=(decoy or index == 0),
        ))

    return _validate_split(tuple(positions), split)


def _validate_split(positions, split):
    if len(positions) != 24:
        raise AssertionError("V5 split must contain exactly 24 positions")
    if len({position.id for position in positions}) != 24:
        raise AssertionError("V5 position ids are not unique")
    if len({state_hash(position.state) for position in positions}) != 24:
        raise AssertionError("V5 position states are not unique")
    if sum(position.state.game.board.n == 3 for position in positions) != 12:
        raise AssertionError("V5 split must contain twelve Toy positions")
    if sum(position.state.game.board.n == 4 for position in positions) != 12:
        raise AssertionError("V5 split must contain twelve Beginner positions")
    if sum(position.width_class == "narrow" for position in positions) != 12:
        raise AssertionError("V5 split must contain twelve narrow roots")
    if sum(position.width_class == "wide" for position in positions) != 12:
        raise AssertionError("V5 split must contain twelve wide roots")
    for position in positions:
        width = len(legal_actions(position.state))
        if position.width_class == "narrow" and not 2 <= width <= 12:
            raise AssertionError(f"{position.id} is not a narrow root: {width}")
        if position.width_class == "wide" and width < 32:
            raise AssertionError(f"{position.id} is not a wide root: {width}")
    for family in FAMILIES:
        selected = [item for item in positions if item.family == family]
        if len(selected) != 4:
            raise AssertionError("V5 family stratification differs")
        if sum(item.decoy for item in selected) != 1:
            raise AssertionError("V5 requires one exact decoy per family")
        if not any(item.hand_audit and not item.decoy for item in selected):
            raise AssertionError("V5 family lacks a positive hand audit")
        if not any(item.hand_audit and item.decoy for item in selected):
            raise AssertionError("V5 family lacks a decoy hand audit")
    for position in positions:
        certificate = position.certificate()
        if position.decoy and certificate.proven_actions:
            raise AssertionError(f"{position.id} decoy has a proven action")
        if not position.decoy and not certificate.proven_actions:
            raise AssertionError(f"{position.id} positive has no proof")
        if certificate.limit_reached:
            raise AssertionError(f"{position.id} exceeded the oracle ceiling")
    return positions


@cache
def development_positions():
    return _build_split("development")


@cache
def holdout_positions():
    positions = _build_split("holdout")
    development_hashes = {
        state_hash(position.state) for position in development_positions()
    }
    if not {
        state_hash(position.state) for position in positions
    }.isdisjoint(development_hashes):
        raise AssertionError("V5 holdout overlaps development")
    return positions


def corpus_catalog(split):
    positions = (
        development_positions() if split == "development"
        else holdout_positions() if split == "holdout"
        else None
    )
    if positions is None:
        raise ValueError("unknown V5 corpus split")
    payload = {
        "format": CORPUS_FORMAT,
        "version": CORPUS_VERSION,
        "split": split,
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
