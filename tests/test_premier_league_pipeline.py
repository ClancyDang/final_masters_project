"""Unit tests for league-pipeline parsing helpers."""

from __future__ import annotations

import unittest

from src.data.premier_league_pipeline import (
    DIRECT_ACTION_TYPE_NAMES,
    qualifiers_to_dict,
    split_qualifier_values,
)


class PremierLeaguePipelineTests(unittest.TestCase):
    def test_qualifiers_are_integer_keyed(self) -> None:
        qualifiers = [
            {"qualifierId": 130, "value": "10"},
            {"qualifierId": 131, "value": "1,2,3"},
            {"qualifierId": 194},
        ]

        result = qualifiers_to_dict(qualifiers)

        self.assertEqual(result[130], "10")
        self.assertEqual(result[131], "1,2,3")
        self.assertIs(result[194], True)

    def test_parallel_qualifier_arrays_are_trimmed(self) -> None:
        self.assertEqual(
            split_qualifier_values("one, two,three"),
            ["one", "two", "three"],
        )
        self.assertEqual(split_qualifier_values(None), [])
        self.assertEqual(split_qualifier_values(True), [])

    def test_direct_action_taxonomy_matches_forest_prototype(self) -> None:
        self.assertEqual(DIRECT_ACTION_TYPE_NAMES[1], "Pass")
        self.assertEqual(DIRECT_ACTION_TYPE_NAMES[12], "Clearance")
        self.assertEqual(DIRECT_ACTION_TYPE_NAMES[83], "Attempted Tackle")
        self.assertNotIn(16, DIRECT_ACTION_TYPE_NAMES)


if __name__ == "__main__":
    unittest.main()
