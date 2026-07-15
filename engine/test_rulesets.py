import unittest
from dataclasses import FrozenInstanceError

from varde import (
    BREATH_RULESETS,
    FLAT_RULESETS,
    GJERDE_RULESETS,
    RULESETS,
    RULESET_CATALOG_VERSION,
    RULESET_REGISTRY,
    RULESET_SPECS,
    Game,
    get_ruleset_spec,
    rulesets_public,
)


EXPECTED_RULESETS = (
    "classic",
    "rosette",
    "breath",
    "breath-extend",
    "breath-extend-multi",
    "breath-extend-run",
    "breath-rescue",
    "breath-run",
    "breath-cap",
    "gjerde",
    "gjerde-go",
)


class TestRulesetRegistry(unittest.TestCase):
    def test_compatibility_ids_and_order_are_unchanged(self):
        self.assertEqual(RULESETS, EXPECTED_RULESETS)
        self.assertEqual(
            BREATH_RULESETS,
            EXPECTED_RULESETS[2:10],
        )
        self.assertEqual(FLAT_RULESETS, EXPECTED_RULESETS[2:])
        self.assertEqual(GJERDE_RULESETS, ("gjerde", "gjerde-go"))

    def test_catalog_is_versioned_unique_and_immutable(self):
        self.assertEqual(RULESET_CATALOG_VERSION, 1)
        self.assertEqual(len(RULESET_SPECS), len(RULESET_REGISTRY))
        self.assertEqual(set(RULESET_REGISTRY), set(EXPECTED_RULESETS))
        self.assertEqual(
            len({spec.evaluation_id for spec in RULESET_SPECS}),
            len(RULESET_SPECS),
        )
        with self.assertRaises(TypeError):
            RULESET_REGISTRY["new"] = RULESET_SPECS[0]
        with self.assertRaises(FrozenInstanceError):
            RULESET_SPECS[0].status = "broken"

    def test_candidate_freeze_and_nonpublic_controls_are_explicit(self):
        expected_candidates = {
            "classic",
            "rosette",
            "breath",
            "breath-run",
            "gjerde",
            "gjerde-go",
        }
        candidates = {
            spec.id for spec in RULESET_SPECS if spec.status == "candidate"
        }
        self.assertEqual(candidates, expected_candidates)
        self.assertEqual(get_ruleset_spec("breath-rescue").status, "control")
        for rules in (
            "breath-extend",
            "breath-extend-multi",
            "breath-extend-run",
            "breath-rescue",
            "breath-cap",
        ):
            spec = get_ruleset_spec(rules)
            self.assertFalse(spec.public_new_game)
            self.assertTrue(spec.archival_reason)

    def test_public_payload_contains_required_metadata_without_aliasing(self):
        payload = rulesets_public()
        self.assertEqual(payload["version"], RULESET_CATALOG_VERSION)
        self.assertEqual(
            [item["id"] for item in payload["rulesets"]],
            list(EXPECTED_RULESETS),
        )
        required = {
            "id", "revision", "evaluation_id", "label", "status",
            "family", "geometry", "scoring", "min_size", "max_size",
            "public_new_game", "description", "archival_reason",
        }
        self.assertTrue(all(required <= set(item) for item in payload["rulesets"]))
        payload["rulesets"][0]["status"] = "broken"
        self.assertEqual(get_ruleset_spec("classic").status, "candidate")

    def test_every_legacy_ruleset_still_constructs_and_round_trips(self):
        for rules in EXPECTED_RULESETS:
            with self.subTest(rules=rules):
                game = Game(3, rules=rules)
                restored = Game.from_dict(game.to_dict())
                self.assertEqual(restored.rules, rules)
                self.assertEqual(restored.to_dict(), game.to_dict())


if __name__ == "__main__":
    unittest.main()
