import copy
import unittest

from opponent import BALANCED_WEIGHTS, DIFFICULTIES
from profiles import (
    CATALOG_HASH,
    CATALOG_VERSION,
    FEATURE_SCHEMA,
    PROFILES,
    get_profile,
    normalize_computer_settings,
    profiles_public,
    validate_catalog,
    _RAW_CATALOG,
)


class TestProfileCatalog(unittest.TestCase):
    def test_catalog_is_versioned_complete_and_immutable(self):
        self.assertEqual(CATALOG_VERSION, 3)
        self.assertEqual(tuple(FEATURE_SCHEMA), tuple(BALANCED_WEIGHTS))
        self.assertEqual(
            tuple(PROFILES),
            ("balanced", "raider", "mason", "surveyor", "weaver", "personal"),
        )
        self.assertEqual(len(CATALOG_HASH), 64)
        self.assertIs(PROFILES["balanced"].weights, BALANCED_WEIGHTS)
        self.assertIs(PROFILES["personal"].weights, BALANCED_WEIGHTS)
        with self.assertRaises(TypeError):
            PROFILES["balanced"] = None
        with self.assertRaises(TypeError):
            PROFILES["balanced"].weights["controlled"] = 0

    def test_catalog_validation_fails_closed(self):
        invalid = copy.deepcopy(_RAW_CATALOG)
        invalid["profiles"][0]["weights"]["controlled"] = 11
        with self.assertRaisesRegex(ValueError, "Balanced weights changed"):
            validate_catalog(invalid)

        invalid = copy.deepcopy(_RAW_CATALOG)
        invalid["profiles"][1]["available"] = True
        with self.assertRaisesRegex(ValueError, "invalid profile weights"):
            validate_catalog(invalid)

        invalid = copy.deepcopy(_RAW_CATALOG)
        invalid["feature_schema"].append("unknown")
        with self.assertRaisesRegex(ValueError, "feature schema"):
            validate_catalog(invalid)

    def test_unknown_and_unavailable_profiles_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "unknown"):
            get_profile("missing")
        with self.assertRaisesRegex(ValueError, "not available"):
            get_profile("raider")
        self.assertFalse(get_profile("raider", require_available=False).available)
        self.assertTrue(get_profile("mason").available)
        self.assertTrue(get_profile("surveyor").available)
        self.assertEqual(len(get_profile("mason").model_hash), 64)

    def test_difficulty_and_style_are_orthogonal_with_legacy_migration(self):
        self.assertEqual(DIFFICULTIES, {"casual", "standard"})
        self.assertEqual(
            normalize_computer_settings("casual", None),
            ("casual", "balanced"),
        )
        self.assertEqual(
            normalize_computer_settings("standard", "personal"),
            ("standard", "personal"),
        )
        self.assertEqual(
            normalize_computer_settings("advanced", None),
            ("standard", "personal"),
        )
        with self.assertRaisesRegex(ValueError, "cannot use another"):
            normalize_computer_settings("advanced", "balanced")

    def test_public_catalog_hides_weights_and_reports_personal_training(self):
        payload = profiles_public(
            {"games_trained": 17, "needs_retraining": True}
        )
        self.assertEqual(payload["version"], 3)
        self.assertEqual(payload["catalog_hash"], CATALOG_HASH)
        by_id = {item["id"]: item for item in payload["profiles"]}
        self.assertNotIn("weights", by_id["balanced"])
        self.assertEqual(by_id["personal"]["training_count"], 17)
        self.assertTrue(by_id["personal"]["needs_retraining"])
        self.assertFalse(by_id["raider"]["available"])
        self.assertIn("availability_reason", by_id["raider"])
        self.assertTrue(by_id["mason"]["available"])
        self.assertTrue(by_id["surveyor"]["available"])
        self.assertNotIn("weights", by_id["mason"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
