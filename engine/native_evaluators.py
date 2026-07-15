"""Versioned, objective-aligned static evaluators for Varde rulesets.

These features are search guidance, not evidence that a ruleset is deep or
balanced.  Classic continues to use its historical literal evaluator path;
its entry here documents the admission schema without changing seeded play.
"""

from collections import deque
from dataclasses import asdict, dataclass
import hashlib
import json
import math
from types import MappingProxyType

from varde import (
    BLACK,
    WHITE,
    control,
    groups_of,
    group_has_ring,
    has_sky,
    is_summit,
    nb_heights,
    other,
    score_cells,
    terrain_ok,
)


NATIVE_EVALUATOR_FORMAT = "varde-native-evaluators"
NATIVE_EVALUATOR_VERSION = 1
NATIVE_VALUE_PER_POINT_BOUND = 1000.0


@dataclass(frozen=True)
class NativeFeatures:
    controlled: int = 0
    liberties: int = 0
    vulnerable: int = 0
    territory: int = 0
    collar_stability: int = 0
    covers: int = 0
    summits: int = 0
    cyclic_groups: int = 0
    ring_stones: int = 0
    entombment_caps: int = 0
    cavities: int = 0
    cavity_points: int = 0
    cut_points: int = 0
    pressure: int = 0
    chase_length: int = 0
    self_squeeze: int = 0
    near_fences: int = 0
    denial_lines: int = 0
    eye_space: int = 0
    ko_exposure: int = 0


FEATURE_NAMES = tuple(NativeFeatures.__dataclass_fields__)


def _weights(**overrides):
    values = {name: 0.0 for name in FEATURE_NAMES}
    values.update(overrides)
    return MappingProxyType(values)


_RAW_SPECS = {
    "classic": {
        "revision": "classic-native-1 (parity protected)",
        "capture": 35.0,
        "weights": _weights(
            controlled=12,
            liberties=3,
            vulnerable=-15,
            territory=1,
            collar_stability=18,
        ),
    },
    "rosette": {
        "revision": "rosette-native-1",
        "capture": 30.0,
        "weights": _weights(
            controlled=10,
            liberties=4,
            vulnerable=-18,
            territory=2,
            cyclic_groups=24,
            ring_stones=2,
            entombment_caps=8,
        ),
    },
    "breath": {
        "revision": "breath-native-1",
        "capture": 32.0,
        "weights": _weights(
            controlled=10,
            liberties=6,
            vulnerable=-20,
            territory=3,
            cavities=24,
            cavity_points=8,
            cut_points=6,
        ),
    },
    "breath-run": {
        "revision": "breath-run-native-1",
        "capture": 30.0,
        "weights": _weights(
            controlled=9,
            liberties=5,
            vulnerable=-18,
            territory=3,
            cavities=20,
            cavity_points=7,
            cut_points=6,
            pressure=10,
            chase_length=4,
            self_squeeze=-8,
        ),
    },
    "gjerde": {
        "revision": "gjerde-breath-native-1",
        "capture": 28.0,
        "weights": _weights(
            controlled=1,
            liberties=4,
            vulnerable=-18,
            territory=30,
            near_fences=10,
            denial_lines=3,
        ),
    },
    "gjerde-go": {
        "revision": "gjerde-go-native-1",
        "capture": 36.0,
        "weights": _weights(
            controlled=1,
            liberties=4,
            vulnerable=-22,
            territory=28,
            near_fences=8,
            denial_lines=2,
            eye_space=18,
            ko_exposure=-8,
        ),
    },
}
NATIVE_EVALUATORS = MappingProxyType(
    {rules: MappingProxyType(spec) for rules, spec in _RAW_SPECS.items()}
)
NATIVE_RULESET_ALIASES = MappingProxyType(
    {
        "breath-extend": "breath",
        "breath-extend-multi": "breath",
        "breath-extend-run": "breath-run",
        "breath-rescue": "breath-run",
        "breath-cap": "breath",
    }
)


def canonical_native_rules(rules):
    return NATIVE_RULESET_ALIASES.get(rules, rules)


def _serializable_specs():
    return {
        rules: {
            "revision": spec["revision"],
            "capture": spec["capture"],
            "weights": dict(spec["weights"]),
        }
        for rules, spec in sorted(NATIVE_EVALUATORS.items())
    }


NATIVE_EVALUATOR_HASH = hashlib.sha256(
    json.dumps(
        {
            "format": NATIVE_EVALUATOR_FORMAT,
            "version": NATIVE_EVALUATOR_VERSION,
            "evaluators": _serializable_specs(),
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
).hexdigest()


def native_evaluators_public():
    """Return reproducibility metadata for research artifacts."""
    return {
        "format": NATIVE_EVALUATOR_FORMAT,
        "version": NATIVE_EVALUATOR_VERSION,
        "hash": NATIVE_EVALUATOR_HASH,
        "evaluators": _serializable_specs(),
    }


def _group_metrics(board, state, color, *, include_cycles=False):
    liberties = 0
    vulnerable = 0
    pressure = 0
    chase_length = 0
    self_squeeze = 0
    cyclic_groups = 0
    ring_stones = 0
    for group in groups_of(board, state, color):
        empty = {
            neighbor
            for point in group
            for neighbor in board.neighbors[point]
            if not state[neighbor]
        }
        liberty_count = len(empty)
        liberties += min(4, liberty_count)
        if liberty_count == 1:
            vulnerable += len(group)
            pressure += 1
            chase_length = max(chase_length, len(group))
        self_squeeze += max(0, 2 - liberty_count) * len(group)
        if include_cycles and group_has_ring(board, group):
            cyclic_groups += 1
            ring_stones += len(group)
    return {
        "liberties": liberties,
        "vulnerable": vulnerable,
        "pressure": pressure,
        "chase_length": chase_length,
        "self_squeeze": self_squeeze,
        "cyclic_groups": cyclic_groups,
        "ring_stones": ring_stones,
    }


def _empty_regions(board, state):
    seen = set()
    for start in board.points:
        if state[start] or start in seen:
            continue
        region = []
        border = set()
        queue = deque([start])
        seen.add(start)
        while queue:
            point = queue.popleft()
            region.append(point)
            for neighbor in board.neighbors[point]:
                top = control(state, neighbor)
                if top:
                    border.add(top)
                elif neighbor not in seen:
                    seen.add(neighbor)
                    queue.append(neighbor)
        yield region, border


def _cavity_metrics(board, state, color):
    cavities = 0
    points = 0
    for region, border in _empty_regions(board, state):
        # A local cavity is tactical potential, not the whole still-open board.
        # The size cap retains corner micro-life while preventing one opening
        # stone from treating every other point as an established cavity.
        if border == {color} and len(region) <= max(6, len(board.points) // 6):
            cavities += 1
            points += len(region)
    return cavities, points


def _area_territory(board, state, color):
    score = sum(control(state, point) == color for point in board.points)
    for region, border in _empty_regions(board, state):
        if border == {color}:
            score += len(region)
    return score


def _cut_points(board, state, color):
    enemy = other(color)
    group_index = {}
    for index, group in enumerate(groups_of(board, state, enemy)):
        for point in group:
            group_index[point] = index
    return sum(
        len({group_index[nb] for nb in board.neighbors[p] if nb in group_index})
        >= 2
        for p in board.points
        if not state[p]
    )


def _entombment_caps(board, state, color):
    enemy = other(color)
    groups = groups_of(board, state, enemy)
    sky_bound = {
        point
        for group in groups
        if not any(not state[nb] for point in group for nb in board.neighbors[point])
        for point in group
    }
    return sum(
        point in sky_bound and terrain_ok(board, state, point)
        for point in board.points
    )


def _fence_metrics(board, state, color):
    near = 0
    denial = 0
    for cell in board.cells:
        tops = [control(state, line) for line in board.cell_edges[cell]]
        claimed = {top for top in tops if top}
        if all(top in (None, color) for top in tops):
            near += tops.count(color) == 5 and tops.count(None) == 1
        if claimed == {BLACK, WHITE}:
            denial += tops.count(color)
    return near, denial


def _eye_space(board, state, color):
    return sum(
        not state[point]
        and bool(board.neighbors[point])
        and all(control(state, neighbor) == color for neighbor in board.neighbors[point])
        for point in board.points
    )


def native_features(board, state, rules, color):
    """Compute bounded structural measurements for one color, without mutation."""
    rules = canonical_native_rules(rules)
    if rules not in NATIVE_EVALUATORS:
        raise ValueError(f"no native evaluator for {rules}")
    groups = _group_metrics(
        board, state, color, include_cycles=rules == "rosette"
    )
    enemy_groups = (
        _group_metrics(board, state, other(color))
        if rules == "breath-run"
        else None
    )
    controlled = sum(control(state, point) == color for point in board.points)
    collar_stability = 0
    covers = 0
    summits = 0
    if rules == "classic":
        collar_stability = sum(
            control(state, point) == color
            and has_sky(board, state, point, None)
            and min(nb_heights(board, state, point)) - len(state[point]) >= 1
            for point in board.points
        )
        covers = sum(
            control(state, point) == color and len(state[point]) > 1
            for point in board.points
        )
        summits = sum(
            control(state, point) == color and is_summit(board, state, point)
            for point in board.points
        )
    cavities, cavity_points = (0, 0)
    if rules in ("breath", "breath-run"):
        cavities, cavity_points = _cavity_metrics(board, state, color)
    territory = 0
    near_fences = 0
    denial_lines = 0
    if hasattr(board, "cells"):
        territory = score_cells(board, state)[color]
        near_fences, denial_lines = _fence_metrics(board, state, color)
    elif controlled + sum(
        control(state, point) == other(color) for point in board.points
    ) >= 0.55 * len(board.points):
        territory = _area_territory(board, state, color)
    return NativeFeatures(
        controlled=controlled,
        liberties=groups["liberties"],
        vulnerable=groups["vulnerable"],
        territory=territory,
        collar_stability=collar_stability,
        covers=covers,
        summits=summits,
        cyclic_groups=groups["cyclic_groups"],
        ring_stones=groups["ring_stones"],
        entombment_caps=(
            _entombment_caps(board, state, color) if rules == "rosette" else 0
        ),
        cavities=cavities,
        cavity_points=cavity_points,
        cut_points=(
            _cut_points(board, state, color)
            if rules in ("breath", "breath-run")
            else 0
        ),
        pressure=enemy_groups["pressure"] if enemy_groups else 0,
        chase_length=enemy_groups["chase_length"] if enemy_groups else 0,
        self_squeeze=groups["self_squeeze"],
        near_fences=near_fences,
        denial_lines=denial_lines,
        eye_space=(
            _eye_space(board, state, color) if rules == "gjerde-go" else 0
        ),
        ko_exposure=(
            sum(
                len(group) == 1
                and len({
                    nb for point in group for nb in board.neighbors[point]
                    if not state[nb]
                }) == 1
                for group in groups_of(board, state, color)
            )
            if rules == "gjerde-go"
            else 0
        ),
    )


def native_capture_weight(rules):
    rules = canonical_native_rules(rules)
    try:
        return NATIVE_EVALUATORS[rules]["capture"]
    except KeyError as exc:
        raise ValueError(f"no native evaluator for {rules}") from exc


def native_evaluate_state(board, state, perspective, moves_played, rules):
    """Return a finite color-symmetric native value from ``perspective``."""
    del moves_played  # reserved in the versioned call surface
    rules = canonical_native_rules(rules)
    spec = NATIVE_EVALUATORS.get(rules)
    if spec is None:
        raise ValueError(f"no native evaluator for {rules}")
    mine = native_features(board, state, rules, perspective)
    theirs = native_features(board, state, rules, other(perspective))
    value = sum(
        spec["weights"][name] * (getattr(mine, name) - getattr(theirs, name))
        for name in FEATURE_NAMES
    )
    if not math.isfinite(value):
        raise ValueError("non-finite native evaluation")
    bound = NATIVE_VALUE_PER_POINT_BOUND * len(board.points)
    return max(-bound, min(bound, value))
