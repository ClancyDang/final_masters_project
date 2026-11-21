"""Tests for two-stage centre-back template averaging."""

from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from src.analysis.centre_back_templates import (
    POSITIONAL_LAYOUT,
    TRADITIONAL_LAYOUT,
    build_centre_back_templates,
)


class CentreBackTemplateTests(unittest.TestCase):
    def setUp(self) -> None:
        base = {
            "match_date": pd.Timestamp("2025-08-01"),
            "match_description": "Example match",
            "matchweek": 1,
            "team_id": "team-a",
            "team_name": "Team A",
            "team_code": "TMA",
            "home_away": "home",
            "opponent_id": "opponent",
            "opponent_name": "Opponent",
            "formation_code": 8,
            "formation_name": "4-2-3-1",
            "lineup_slot": 5,
            "decoded_provider_position": "RightCenterBack",
            "standardised_position": "Right centre-back",
            "position_group": "Centre-back",
            "mapping_confidence": "high",
            "minutes_played": 90.0,
        }
        rows = []
        for match_id, player_id, player_name, action_count in (
            ("a-1", "player-a", "Player A", 1),
            ("a-2", "player-a", "Player A", 1),
            ("b-1", "player-b", "Player B", 1),
        ):
            rows.append(
                {
                    **base,
                    "match_id": match_id,
                    "player_id": player_id,
                    "player_name": player_name,
                    "action_count": action_count,
                }
            )
        self.appearances = pd.DataFrame(rows)
        self.actions = pd.DataFrame(
            [
                {"match_id": "a-1", "team_id": "team-a", "player_id": "player-a", "x": 1.0, "y": 99.0},
                {"match_id": "a-2", "team_id": "team-a", "player_id": "player-a", "x": 1.0, "y": 99.0},
                {"match_id": "b-1", "team_id": "team-a", "player_id": "player-b", "x": 99.0, "y": 1.0},
            ]
        )

    def test_profiles_retain_both_layouts_and_all_actions(self) -> None:
        result = build_centre_back_templates(
            self.actions,
            self.appearances,
            minimum_player_appearances=1,
        )

        self.assertEqual(
            set(result.appearance_profiles["layout"]),
            {POSITIONAL_LAYOUT, TRADITIONAL_LAYOUT},
        )
        count_sums = result.appearance_profiles.groupby(
            ["match_id", "layout"]
        )["zone_action_count"].sum()
        self.assertTrue(count_sums.eq(1).all())
        share_sums = result.appearance_profiles.groupby(
            ["match_id", "layout"]
        )["action_share"].sum()
        self.assertTrue(np.isclose(share_sums, 1).all())

    def test_league_template_weights_players_not_appearances(self) -> None:
        result = build_centre_back_templates(
            self.actions,
            self.appearances,
            minimum_player_appearances=1,
        )

        traditional = result.league_templates.loc[
            result.league_templates["layout"].eq(TRADITIONAL_LAYOUT)
        ]
        nonzero = traditional.loc[traditional["mean_action_share"].gt(0)]
        self.assertEqual(len(nonzero), 2)
        self.assertTrue(np.isclose(nonzero["mean_action_share"], 0.5).all())
        self.assertTrue(traditional["player_count"].eq(2).all())

    def test_minimum_appearance_threshold_is_applied_per_player(self) -> None:
        result = build_centre_back_templates(
            self.actions,
            self.appearances,
            minimum_player_appearances=2,
        )

        eligibility = (
            result.player_profiles[["player_id", "template_eligible"]]
            .drop_duplicates()
            .set_index("player_id")["template_eligible"]
        )
        self.assertTrue(eligibility["player-a"])
        self.assertFalse(eligibility["player-b"])
        self.assertTrue(result.league_templates["player_count"].eq(1).all())
        player_summary = (
            result.player_profiles[
                ["player_id", "eligible_appearances", "total_actions"]
            ]
            .drop_duplicates()
            .set_index("player_id")
        )
        self.assertEqual(player_summary.loc["player-a", "eligible_appearances"], 2)
        self.assertEqual(player_summary.loc["player-a", "total_actions"], 2)


if __name__ == "__main__":
    unittest.main()
