"""Tests for remaining-position role and overarching templates."""

from __future__ import annotations

import unittest

import pandas as pd

from src.analysis.position_group_templates import build_position_group_templates
from src.analysis.position_group_validation import build_position_group_validation


class PositionGroupTemplateTests(unittest.TestCase):
    def setUp(self) -> None:
        appearances = []
        actions = []
        roles = (
            ("Left central midfielder", 80.0),
            ("Right central midfielder", 20.0),
            ("Central midfielder", 50.0),
        )
        for player_id in ("a", "b"):
            for role_number, (role, y) in enumerate(roles):
                match_id = f"{player_id}-{role_number}"
                appearances.append(
                    {
                        "match_id": match_id,
                        "match_date": pd.Timestamp("2025-08-01"),
                        "match_description": "Example match",
                        "matchweek": role_number + 1,
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
                        "player_name": f"Player {player_id.upper()}",
                        "formation_code": 8,
                        "formation_name": "4-2-3-1",
                        "lineup_slot": role_number + 7,
                        "decoded_provider_position": role.replace(" ", ""),
                        "standardised_position": role,
                        "position_group": "Central midfield",
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
                            "x": 50.0 + action_number,
                            "y": y,
                        }
                    )
        self.appearances = pd.DataFrame(appearances)
        self.actions = pd.DataFrame(actions)

    def test_role_specific_and_overarching_groups_are_built(self) -> None:
        result = build_position_group_templates(
            self.actions,
            self.appearances,
            "Central midfield",
            minimum_player_appearances=1,
        )

        self.assertEqual(
            set(result.template_coverage["template_group"]),
            {
                "Central midfielder",
                "Left central midfielder",
                "Right central midfielder",
                "Central midfield",
            },
        )
        self.assertTrue(result.template_coverage["template_available"].all())

    def test_right_role_is_mirrored_only_in_overarching_profile(self) -> None:
        result = build_position_group_templates(
            self.actions,
            self.appearances,
            "Central midfield",
            minimum_player_appearances=1,
        )
        actions = result.role_actions
        right = actions.loc[
            actions["role_standardised_position"].eq("Right central midfielder")
        ]
        self.assertTrue(right["original_y"].eq(20).all())
        self.assertTrue(right["role_normalised_y"].eq(80).all())

        profiles = result.appearance_profiles
        role_specific = profiles.loc[
            profiles["template_group"].eq("Right central midfielder")
            & profiles["layout"].eq("traditional_18")
            & profiles["action_share"].gt(0)
        ]
        overarching = profiles.loc[
            profiles["template_group"].eq("Central midfield")
            & profiles["standardised_position"].eq("Right central midfielder")
            & profiles["layout"].eq("traditional_18")
            & profiles["action_share"].gt(0)
        ]
        self.assertNotEqual(
            role_specific["zone_id"].iloc[0],
            overarching["zone_id"].iloc[0],
        )

    def test_unsupported_subrole_templates_are_reported_not_fabricated(self) -> None:
        result = build_position_group_templates(
            self.actions,
            self.appearances,
            "Central midfield",
            minimum_player_appearances=2,
        )
        coverage = result.template_coverage.set_index("template_group")

        self.assertFalse(coverage.loc["Left central midfielder", "template_available"])
        self.assertFalse(coverage.loc["Right central midfielder", "template_available"])
        self.assertFalse(coverage.loc["Central midfielder", "template_available"])
        self.assertTrue(coverage.loc["Central midfield", "template_available"])
        self.assertEqual(set(result.league_templates["template_group"]), {"Central midfield"})

    def test_validation_covers_all_supported_checks(self) -> None:
        templates = build_position_group_templates(
            self.actions,
            self.appearances,
            "Central midfield",
            minimum_player_appearances=1,
        )
        validation = build_position_group_validation(
            templates,
            self.actions,
            self.appearances,
            bootstrap_iterations=100,
            split_half_iterations=100,
            random_seed=7,
        )

        self.assertEqual(len(validation.forest_summary), 8)
        self.assertTrue(validation.forest_summary["orientation_alignment"].all())
        self.assertEqual(len(validation.bootstrap_summary), 8)
        self.assertEqual(
            set(validation.split_half_summary["split_half_status"]),
            {"insufficient sample"},
        )
        self.assertEqual(len(validation.layout_robustness), 8)
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
