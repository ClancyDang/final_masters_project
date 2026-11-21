"""Tests for side-specific and mirrored wide-defender templates."""

from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from src.analysis.player_template_comparison import compare_player_to_template
from src.analysis.wide_defender_templates import build_wide_defender_templates
from src.analysis.wide_defender_validation import build_wide_defender_validation


class WideDefenderTemplateTests(unittest.TestCase):
    def setUp(self) -> None:
        appearances = []
        actions = []
        for player_id, player_name in (("a", "Player A"), ("b", "Player B")):
            for side, y in (("Left", 80.0), ("Right", 20.0)):
                match_id = f"{player_id}-{side.lower()}"
                appearances.append(
                    {
                        "match_id": match_id,
                        "match_date": pd.Timestamp("2025-08-01"),
                        "match_description": "Example match",
                        "matchweek": 1,
                        "team_id": f"team-{player_id}",
                        "team_name": (
                            "Nottingham Forest"
                            if player_id == "a"
                            else "Team B"
                        ),
                        "team_code": f"TM{player_id.upper()}",
                        "home_away": "home",
                        "opponent_id": "opponent",
                        "opponent_name": "Opponent",
                        "player_id": player_id,
                        "player_name": player_name,
                        "formation_code": 8,
                        "formation_name": "4-2-3-1",
                        "lineup_slot": 2 if side == "Right" else 6,
                        "decoded_provider_position": f"{side}Back",
                        "standardised_position": f"{side} full-back",
                        "position_group": "Full-back",
                        "mapping_confidence": "high",
                        "minutes_played": 90.0,
                        "action_count": 2,
                    }
                )
                for action_number, type_id in enumerate((1, 7)):
                    actions.append(
                        {
                            "match_id": match_id,
                            "team_id": f"team-{player_id}",
                            "player_id": player_id,
                            "type_id": type_id,
                            "x": 60.0 + action_number,
                            "y": y,
                        }
                    )
        self.appearances = pd.DataFrame(appearances)
        self.actions = pd.DataFrame(actions)
        self.result = build_wide_defender_templates(
            self.actions,
            self.appearances,
            "Full-back",
            minimum_player_appearances=1,
        )

    def test_original_coordinates_are_preserved_and_right_side_is_mirrored(self) -> None:
        actions = self.result.role_actions
        right = actions.loc[actions["was_mirrored"]]
        left = actions.loc[~actions["was_mirrored"]]

        self.assertTrue(right["original_y"].eq(20).all())
        self.assertTrue(right["role_normalised_y"].eq(80).all())
        self.assertTrue(left["original_y"].eq(80).all())
        self.assertTrue(left["role_normalised_y"].eq(80).all())

    def test_side_specific_profiles_remain_on_opposite_sides(self) -> None:
        profiles = self.result.appearance_profiles
        nonzero = profiles.loc[
            profiles["layout"].eq("traditional_18")
            & profiles["action_share"].gt(0)
            & profiles["template_scope"].eq("side_specific")
        ]
        zones_by_group = nonzero.groupby("template_group")["zone_id"].unique()

        self.assertNotEqual(
            zones_by_group["Left full-back"].tolist(),
            zones_by_group["Right full-back"].tolist(),
        )

    def test_role_normalisation_aligns_equivalent_left_and_right_actions(self) -> None:
        profiles = self.result.appearance_profiles
        combined = profiles.loc[
            profiles["template_group"].eq("Full-back")
            & profiles["layout"].eq("traditional_18")
            & profiles["action_share"].gt(0)
        ]

        self.assertEqual(combined["zone_id"].nunique(), 1)
        self.assertEqual(len(combined), 4)
        combined_players = self.result.player_profiles.loc[
            self.result.player_profiles["template_group"].eq("Full-back")
            & self.result.player_profiles["layout"].eq("traditional_18")
        ]
        share_sums = combined_players.groupby("player_id")[
            "mean_action_share"
        ].sum()
        self.assertTrue(np.isclose(share_sums, 1).all())
        self.assertTrue(combined_players["eligible_appearances"].eq(2).all())

    def test_three_template_groups_are_built(self) -> None:
        self.assertEqual(
            set(self.result.league_templates["template_group"]),
            {"Left full-back", "Right full-back", "Full-back"},
        )
        failures = self.result.quality_checks.loc[
            self.result.quality_checks["check"].str.endswith("failures"),
            "value",
        ]
        self.assertTrue(failures.astype(int).eq(0).all())

    def test_player_can_be_compared_with_a_selected_template_group(self) -> None:
        comparison = compare_player_to_template(
            self.result.player_profiles,
            "a",
            "traditional_18",
            template_group="Full-back",
        )

        self.assertEqual(comparison.template_group, "Full-back")
        self.assertEqual(comparison.similarity_score, 100.0)
        with self.assertRaisesRegex(ValueError, "template_group is required"):
            compare_player_to_template(
                self.result.player_profiles,
                "a",
                "traditional_18",
            )

    def test_validation_covers_uncertainty_layouts_and_action_families(self) -> None:
        validation = build_wide_defender_validation(
            self.result,
            self.actions,
            self.appearances,
            bootstrap_iterations=100,
            split_half_iterations=100,
            random_seed=7,
        )

        self.assertEqual(len(validation.forest_summary), 6)
        self.assertTrue(validation.forest_summary["orientation_alignment"].all())
        self.assertEqual(len(validation.bootstrap_summary), 6)
        self.assertEqual(
            set(validation.split_half_summary["split_half_status"]),
            {"insufficient sample"},
        )
        self.assertEqual(len(validation.layout_robustness), 6)
        self.assertEqual(
            set(validation.action_family_sensitivity["action_family"]),
            {"all_direct_actions", "passes", "defensive_actions"},
        )
        failures = validation.quality_checks.loc[
            validation.quality_checks["check"].str.endswith("failures"),
            "value",
        ]
        self.assertTrue(failures.astype(int).eq(0).all())


if __name__ == "__main__":
    unittest.main()
