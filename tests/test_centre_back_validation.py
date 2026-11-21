"""Tests for the Forest centre-back validation stage."""

from __future__ import annotations

import unittest

import pandas as pd

from src.analysis.centre_back_templates import build_centre_back_templates
from src.analysis.centre_back_validation import build_centre_back_validation


class CentreBackValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        appearances = []
        actions = []
        players = (
            ("forest", "forest-player", "Forest Player", "Nottingham Forest", 80.0),
            ("peer-a", "peer-a-player", "Peer A", "Peer A FC", 50.0),
            ("peer-b", "peer-b-player", "Peer B", "Peer B FC", 20.0),
        )
        for team_id, player_id, player_name, team_name, y in players:
            for match_number in range(10):
                match_id = f"{team_id}-{match_number}"
                appearances.append(
                    {
                        "match_id": match_id,
                        "match_date": pd.Timestamp("2025-08-01")
                        + pd.Timedelta(days=match_number),
                        "match_description": f"Match {match_number}",
                        "matchweek": match_number + 1,
                        "team_id": team_id,
                        "team_name": team_name,
                        "team_code": team_id.upper(),
                        "home_away": "home",
                        "opponent_id": "opponent",
                        "opponent_name": "Opponent",
                        "player_id": player_id,
                        "player_name": player_name,
                        "formation_code": 8,
                        "formation_name": "4-2-3-1",
                        "lineup_slot": 4,
                        "decoded_provider_position": "LeftCenterBack",
                        "standardised_position": "Left centre-back",
                        "position_group": "Centre-back",
                        "mapping_confidence": "high",
                        "minutes_played": 90.0,
                        "action_count": 4,
                    }
                )
                for action_number, type_id in enumerate((1, 1, 7, 7)):
                    actions.append(
                        {
                            "match_id": match_id,
                            "team_id": team_id,
                            "player_id": player_id,
                            "type_id": type_id,
                            "x": 20.0 + action_number,
                            "y": y,
                        }
                    )
        cls.appearances = pd.DataFrame(appearances)
        cls.actions = pd.DataFrame(actions)
        templates = build_centre_back_templates(cls.actions, cls.appearances)
        cls.result = build_centre_back_validation(
            templates.appearance_profiles,
            templates.player_profiles,
            cls.actions,
            cls.appearances,
            bootstrap_iterations=100,
            split_half_iterations=100,
            random_seed=7,
        )

    def test_spatial_side_agrees_with_provider_role(self) -> None:
        summary = self.result.forest_summary

        self.assertEqual(len(summary), 2)
        self.assertTrue(summary["role_spatial_alignment"].all())
        self.assertTrue(summary["relative_lateral_shift"].gt(0).all())
        self.assertEqual(set(summary["spatial_side"]), {"left-shifted"})

    def test_bootstrap_and_split_half_outputs_are_valid(self) -> None:
        bootstrap = self.result.bootstrap_summary
        split_half = self.result.split_half_summary

        self.assertTrue(
            bootstrap["similarity_ci_low"].le(bootstrap["similarity_score"]).all()
        )
        self.assertTrue(
            bootstrap["similarity_score"].le(bootstrap["similarity_ci_high"]).all()
        )
        self.assertEqual(set(split_half["split_half_status"]), {"calculated"})
        self.assertTrue(split_half["median_split_half_similarity"].eq(100).all())

    def test_both_layouts_and_action_families_are_checked(self) -> None:
        sensitivity = self.result.action_family_sensitivity

        self.assertEqual(
            set(sensitivity["action_family"]),
            {"all_direct_actions", "passes", "defensive_actions"},
        )
        self.assertEqual(
            set(sensitivity["layout"]),
            {"positional_20", "traditional_18"},
        )
        self.assertEqual(len(sensitivity), 6)
        self.assertTrue(
            self.result.quality_checks.loc[
                self.result.quality_checks["check"].str.endswith("failures"),
                "value",
            ]
            .astype(int)
            .eq(0)
            .all()
        )


if __name__ == "__main__":
    unittest.main()
