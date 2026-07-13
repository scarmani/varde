"""Versioned immutable evaluator profile catalog for Varde."""

from dataclasses import dataclass
import hashlib
import json
import math
from types import MappingProxyType

from opponent import BALANCED_WEIGHTS, DIFFICULTIES


CATALOG_FORMAT = "varde-evaluator-profiles"
CATALOG_VERSION = 3
FEATURE_SCHEMA = tuple(BALANCED_WEIGHTS)
CURATED_PROFILE_IDS = ("balanced", "raider", "mason", "surveyor", "weaver")
PROFILE_IDS = CURATED_PROFILE_IDS + ("personal",)


_RAW_CATALOG = {
    "format": CATALOG_FORMAT,
    "version": CATALOG_VERSION,
    "feature_schema": list(FEATURE_SCHEMA),
    "source_commit": "1da66f7a40bd6c336d2a5fd5bc472ff2ddf040bc",
    "recipe": "map-elites-v3-pending",
    "validation": {
        "status": "pending",
        "audit_positions": 0,
        "optimizer_candidates": 0,
        "gate_pairs": 0,
    },
    "profiles": [
        {
            "id": "balanced",
            "label": "Balanced",
            "description": "The original general-purpose Varde evaluator.",
            "available": True,
            "experimental": False,
            "dynamic": False,
            "weights": dict(BALANCED_WEIGHTS),
            "model_hash": None,
            "measurements": None,
        },
        {
            "id": "raider",
            "label": "Raider",
            "description": "Seeks enemy contact and capture pressure.",
            "available": False,
            "experimental": True,
            "dynamic": False,
            "weights": None,
            "model_hash": None,
            "measurements": None,
        },
        {
            "id": "mason",
            "label": "Mason",
            "description": "Builds vertically through covers, stacks, and durable skies.",
            "available": False,
            "experimental": True,
            "dynamic": False,
            "weights": None,
            "model_hash": None,
            "measurements": None,
        },
        {
            "id": "surveyor",
            "label": "Surveyor",
            "description": "Uses the rim and reaches broadly across territory.",
            "available": False,
            "experimental": True,
            "dynamic": False,
            "weights": None,
            "model_hash": None,
            "measurements": None,
        },
        {
            "id": "weaver",
            "label": "Weaver",
            "description": "Connects friendly groups into consolidated structures.",
            "available": False,
            "experimental": True,
            "dynamic": False,
            "weights": None,
            "model_hash": None,
            "measurements": None,
        },
        {
            "id": "personal",
            "label": "Personal",
            "description": "Balanced play plus your persistent local learned correction.",
            "available": True,
            "experimental": True,
            "dynamic": True,
            "weights": dict(BALANCED_WEIGHTS),
            "model_hash": None,
            "measurements": None,
        },
    ],
}


@dataclass(frozen=True)
class EvaluatorProfile:
    id: str
    label: str
    description: str
    available: bool
    experimental: bool
    dynamic: bool
    weights: MappingProxyType | None
    model_hash: str | None
    measurements: dict | None

    def public(self, learning_status=None):
        payload = {
            "id": self.id,
            "label": self.label,
            "description": self.description,
            "availability": "available" if self.available else "unavailable",
            "available": self.available,
            "experimental": self.experimental,
        }
        if self.id == "personal":
            status = learning_status or {}
            payload["training_count"] = int(status.get("games_trained", 0))
            payload["trained"] = payload["training_count"] > 0
            payload["needs_retraining"] = bool(
                status.get("needs_retraining", False)
            )
        return payload


def _validate_catalog(payload):
    if payload.get("format") != CATALOG_FORMAT:
        raise ValueError("invalid profile catalog format")
    if payload.get("version") != CATALOG_VERSION:
        raise ValueError("unsupported profile catalog version")
    if tuple(payload.get("feature_schema", ())) != FEATURE_SCHEMA:
        raise ValueError("invalid profile feature schema")
    raw_profiles = payload.get("profiles")
    if not isinstance(raw_profiles, list):
        raise ValueError("invalid profile catalog")
    ids = [item.get("id") for item in raw_profiles if isinstance(item, dict)]
    if tuple(ids) != PROFILE_IDS:
        raise ValueError("invalid profile catalog ids")
    for item in raw_profiles:
        for field in (
            "label",
            "description",
            "available",
            "experimental",
            "dynamic",
        ):
            if field not in item:
                raise ValueError("incomplete profile catalog entry")
        if not isinstance(item["available"], bool):
            raise ValueError("invalid profile availability")
        weights = item.get("weights")
        if item["available"]:
            if not isinstance(weights, dict) or tuple(weights) != FEATURE_SCHEMA:
                raise ValueError("invalid profile weights")
            if any(
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                for value in weights.values()
            ):
                raise ValueError("invalid profile weight")
        elif weights is not None:
            raise ValueError("unavailable profile must not contain weights")
    balanced = raw_profiles[0]
    if balanced["weights"] != dict(BALANCED_WEIGHTS):
        raise ValueError("Balanced weights changed")
    personal = raw_profiles[-1]
    if personal["weights"] != dict(BALANCED_WEIGHTS):
        raise ValueError("Personal must correct Balanced")
    return payload


def validate_catalog(payload):
    """Validate a catalog payload and return it unchanged."""
    return _validate_catalog(payload)


def _build_profiles(payload):
    _validate_catalog(payload)
    profiles = {}
    for item in payload["profiles"]:
        weights = item["weights"]
        profiles[item["id"]] = EvaluatorProfile(
            id=item["id"],
            label=item["label"],
            description=item["description"],
            available=item["available"],
            experimental=item["experimental"],
            dynamic=item["dynamic"],
            weights=(
                BALANCED_WEIGHTS
                if item["id"] in ("balanced", "personal")
                else MappingProxyType(dict(weights)) if weights else None
            ),
            model_hash=item.get("model_hash"),
            measurements=item.get("measurements"),
        )
    return MappingProxyType(profiles)


PROFILES = _build_profiles(_RAW_CATALOG)
CATALOG_HASH = hashlib.sha256(
    json.dumps(_RAW_CATALOG, sort_keys=True, separators=(",", ":")).encode()
).hexdigest()


def get_profile(profile_id, require_available=True):
    if not isinstance(profile_id, str) or profile_id not in PROFILES:
        raise ValueError("unknown computer profile")
    profile = PROFILES[profile_id]
    if require_available and not profile.available:
        raise ValueError("computer profile is not available")
    return profile


def normalize_computer_settings(difficulty="standard", profile=None):
    """Normalize public and legacy difficulty/profile request data."""
    if difficulty == "advanced":
        if profile not in (None, "personal"):
            raise ValueError("legacy Advanced cannot use another profile")
        difficulty = "standard"
        profile = "personal"
    if difficulty not in DIFFICULTIES:
        raise ValueError("invalid computer difficulty")
    profile = "balanced" if profile is None else profile
    selected = get_profile(profile)
    return difficulty, selected.id


def profiles_public(learning_status=None):
    return {
        "format": CATALOG_FORMAT,
        "version": CATALOG_VERSION,
        "catalog_hash": CATALOG_HASH,
        "source_commit": _RAW_CATALOG["source_commit"],
        "recipe": _RAW_CATALOG["recipe"],
        "validation": dict(_RAW_CATALOG["validation"]),
        "profiles": [
            PROFILES[profile_id].public(learning_status)
            for profile_id in PROFILE_IDS
        ],
    }
