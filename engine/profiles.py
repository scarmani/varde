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
    "source_commit": "bb82da31067a4e69db6cc91dea4165fd022be6a9",
    "recipe": "map-elites-v3-audit-gated-4096",
    "validation": {
        "status": "validated-partial",
        "audit_positions": 2000,
        "audit_report_hash": "c17b291dcc0ee7c767daef55c3a1cbf0be7d83fee46215c1e3a972c099f0d9a1",
        "optimizer_candidates": 4096,
        "optimizer_games": 32768,
        "optimizer_rejected": 6,
        "archive_cells": 219,
        "optimizer_state_hash": "38136c9585127a8fe9412dfa9d085df90199de3b2f79fa78c9ab30b274433422",
        "curation_hash": "ca3efec8a71d7095a241ca5c478e16d4737fb1ad4251dca048261b6f0204253a",
        "gate_pairs": 100,
        "gate_source_commit": "8cc09b730df668830bf038880dc557b0842bd2dd",
        "gate_hash": "070cd30a2a3be769c7a62663dcf6b025ec71abc12daf9da6327637296e31f5c0",
        "smoke_games": 464,
        "smoke_hash": "349c95e52a92c0d26eef94a252832553ed5a6088a1b6a52e8d5456bfc1480a78",
        "available_profiles": ["mason", "surveyor"],
        "strength_claim": False,
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
            "model_hash": "34e186dbc639af9a58ba0ecbc927b4cf18c48f459d6de27f0daa9085e8075291",
            "measurements": {
                "descriptors": {
                    "engagement": 0.535031847133758,
                    "verticality": 0.2757475083056478,
                    "edge_reach": 0.4607218683651804,
                    "consolidation": 0.3375796178343949,
                },
                "seeded_decision_parity": True,
            },
            "availability_reason": None,
        },
        {
            "id": "raider",
            "label": "Raider",
            "description": "Seeks enemy contact and capture pressure.",
            "available": False,
            "experimental": True,
            "dynamic": False,
            "weights": None,
            "model_hash": "7eef6e75ac2e8121b9549badfcd2bbf2deab5ba60a1df62622def09a3220701e",
            "measurements": {
                "candidate_id": 1784,
                "primary_descriptor": "engagement",
                "archive_shift": 0.16749979843586227,
                "gate_score": 0.5475,
                "gate_effect_size": -0.6870570604421322,
                "gate_passed": False,
            },
            "availability_reason": "Held-out games did not reproduce increased engagement.",
        },
        {
            "id": "mason",
            "label": "Mason",
            "description": "Builds vertically through covers, stacks, and durable skies.",
            "available": True,
            "experimental": False,
            "dynamic": False,
            "weights": {
                "controlled": 11.816159198817,
                "captured": 19.321995843245,
                "skies": 11.471548800733,
                "liberties": 4.558121979028,
                "vulnerable": -28.0,
                "development": 3.506049434987,
                "territory": 2.555731577515,
                "control_resilience": 0.0,
                "latent_reserves": 0.0,
                "sky_durability": 0.0,
                "connection": 0.0,
                "capturing_moves": 23.716300843509,
                "max_capture": -24.0,
                "covers": 23.240317347726,
                "hostile_covers": 14.771916733797,
                "reinforcements": 0.0,
                "summits": 11.432768104378,
            },
            "model_hash": "9bce1f5cb18c0ccefbbe25df8e2ff40b8499fe77ad4aed300ad885557988fca7",
            "measurements": {
                "candidate_id": 2652,
                "primary_descriptor": "verticality",
                "archive_shift": 0.2412737682900969,
                "gate_score": 0.7675,
                "gate_effect_size": 1.2642819627408186,
                "gate_passed": True,
            },
            "availability_reason": None,
        },
        {
            "id": "surveyor",
            "label": "Surveyor",
            "description": "Uses the rim and reaches broadly across territory.",
            "available": True,
            "experimental": False,
            "dynamic": False,
            "weights": {
                "controlled": 17.650848604326,
                "captured": 23.223917108821,
                "skies": 14.878973860211,
                "liberties": 7.221077261122,
                "vulnerable": -7.222205090375,
                "development": -0.904943055776,
                "territory": 4.178008612043,
                "control_resilience": 0.0,
                "latent_reserves": 0.0,
                "sky_durability": 0.0,
                "connection": 0.0,
                "capturing_moves": -5.987670045628,
                "max_capture": -12.245609075146,
                "covers": 11.219138212064,
                "hostile_covers": -9.687547573899,
                "reinforcements": 0.0,
                "summits": 8.880558399418,
            },
            "model_hash": "38d994c87a0a5667d95164a02258bf84da17a4151cd7f11a4fbc19195fe8a9d8",
            "measurements": {
                "candidate_id": 2112,
                "primary_descriptor": "edge_reach",
                "archive_shift": 0.25882941368610174,
                "gate_score": 0.5175,
                "gate_effect_size": 3.0080988061833347,
                "gate_passed": True,
            },
            "availability_reason": None,
        },
        {
            "id": "weaver",
            "label": "Weaver",
            "description": "Connects friendly groups into consolidated structures.",
            "available": False,
            "experimental": True,
            "dynamic": False,
            "weights": None,
            "model_hash": "712b36c480bc199fb306a21a9ca6e86f8a459724cfe9af87874bcb8bd9fddd14",
            "measurements": {
                "candidate_id": 1587,
                "primary_descriptor": "consolidation",
                "archive_shift": 0.18773683786180767,
                "gate_score": 0.185,
                "gate_effect_size": 3.5834165411494387,
                "gate_passed": False,
            },
            "availability_reason": "Held-out play fell below the required strength floor.",
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
            "availability_reason": None,
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
    availability_reason: str | None

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
        if self.availability_reason:
            payload["availability_reason"] = self.availability_reason
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
        reason = item.get("availability_reason")
        if reason is not None and not isinstance(reason, str):
            raise ValueError("invalid profile availability reason")
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
            availability_reason=item.get("availability_reason"),
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
