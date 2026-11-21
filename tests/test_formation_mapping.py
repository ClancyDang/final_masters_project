"""Tests for provider formation decoding and project position rules."""

from __future__ import annotations

import unittest

import pandas as pd

from src.positions.formation_mapping import (
    FORMATION_SPECS,
    add_position_mapping,
    classify_appearance,
    decode_provider_position,
)


class FormationMappingTests(unittest.TestCase):
    def test_five_three_two_right_back_becomes_wing_back(self) -> None:
        result = classify_appearance(10, 2)

        self.assertEqual(result.formation_name, "5-3-2")
        self.assertEqual(result.decoded_provider_position, "RightBack")
        self.assertEqual(result.standardised_position, "Right wing-back")
        self.assertEqual(result.position_group, "Wing-back")
        self.assertEqual(result.mapping_confidence, "high")
        self.assertEqual(result.mapping_status, "mapped")

    def test_five_three_two_centre_back_stays_centre_back(self) -> None:
        result = classify_appearance(10, 5)

        self.assertEqual(result.decoded_provider_position, "CenterBack")
        self.assertEqual(result.standardised_position, "Centre-back")
        self.assertEqual(result.position_group, "Centre-back")

    def test_back_four_right_back_becomes_full_back(self) -> None:
        result = classify_appearance(8, 2)

        self.assertEqual(result.formation_name, "4-2-3-1")
        self.assertEqual(result.standardised_position, "Right full-back")
        self.assertEqual(result.position_group, "Full-back")

    def test_three_four_three_wide_midfielder_becomes_wing_back(self) -> None:
        result = classify_appearance(13, 2)

        self.assertEqual(result.decoded_provider_position, "RightMidfield")
        self.assertEqual(result.standardised_position, "Right wing-back")
        self.assertEqual(result.position_group, "Wing-back")

    def test_bench_slot_is_retained_as_unresolved(self) -> None:
        result = classify_appearance(8, 0)

        self.assertEqual(result.formation_name, "4-2-3-1")
        self.assertIsNone(result.decoded_provider_position)
        self.assertEqual(result.mapping_confidence, "low")
        self.assertEqual(result.mapping_status, "bench_slot_unresolved")

    def test_unknown_formation_is_not_guessed(self) -> None:
        result = classify_appearance(999, 2)

        self.assertIsNone(result.formation_name)
        self.assertIsNone(result.standardised_position)
        self.assertEqual(result.mapping_status, "unmapped_provider_combination")

    def test_all_reference_slots_can_be_decoded(self) -> None:
        for formation_code, (_, positions) in FORMATION_SPECS.items():
            for lineup_slot in range(1, 12):
                formation_name, provider_position = decode_provider_position(
                    formation_code,
                    lineup_slot,
                )
                self.assertIsNotNone(formation_name)
                self.assertEqual(provider_position, positions[lineup_slot])

    def test_dataframe_mapping_preserves_rows_and_adds_columns(self) -> None:
        appearances = pd.DataFrame(
            {
                "player_name": ["Example CB", "Example WB", "Example sub"],
                "formation_code": [10, 13, 8],
                "lineup_slot": [5, 2, 0],
            }
        )

        mapped = add_position_mapping(appearances)

        self.assertEqual(len(mapped), len(appearances))
        self.assertEqual(
            mapped.loc[:1, "position_group"].tolist(),
            ["Centre-back", "Wing-back"],
        )
        self.assertTrue(pd.isna(mapped.loc[2, "position_group"]))
        self.assertEqual(mapped.loc[2, "mapping_status"], "bench_slot_unresolved")


if __name__ == "__main__":
    unittest.main()
