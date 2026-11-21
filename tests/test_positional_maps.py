"""Tests for the reusable positional-map calculations."""

from __future__ import annotations

import os
import unittest

os.environ.setdefault("MPLBACKEND", "Agg")

import numpy as np
import pandas as pd

from src.visualizations.positional_maps import (
    LAYOUT_BOTH,
    build_action_location_figure,
    close_figure,
)


class PositionalMapTests(unittest.TestCase):
    def setUp(self) -> None:
        self.actions = pd.DataFrame(
            {
                "x": [1, 1, 20, 35, 50, 65, 80, 99],
                "y": [99, 1, 50, 20, 80, 50, 20, 99],
            }
        )
        self.appearance = pd.Series(
            {
                "player_name": "Test defender",
                "match_description": "Test match",
                "match_date": pd.Timestamp("2025-08-17"),
                "minutes_played": 90.0,
                "action_count": len(self.actions),
            }
        )

    def test_both_distributions_retain_all_actions(self) -> None:
        figure, positional, traditional = build_action_location_figure(
            self.actions,
            self.appearance,
            layout=LAYOUT_BOTH,
        )
        self.addCleanup(close_figure, figure)

        self.assertEqual(len(positional), 20)
        self.assertEqual(len(traditional), 18)
        self.assertEqual(positional["action_count"].sum(), len(self.actions))
        self.assertEqual(traditional["action_count"].sum(), len(self.actions))
        self.assertTrue(np.isclose(positional["action_share"].sum(), 1))
        self.assertTrue(np.isclose(traditional["action_share"].sum(), 1))

    def test_traditional_zone_numbering_runs_left_to_right(self) -> None:
        figure, _, traditional = build_action_location_figure(
            self.actions,
            self.appearance,
            layout=LAYOUT_BOTH,
        )
        self.addCleanup(close_figure, figure)

        self.assertEqual(traditional.loc[0, "zone_id"], 1)
        self.assertAlmostEqual(traditional.loc[0, "center_y"], 100 * 5 / 6)
        self.assertEqual(traditional.loc[2, "zone_id"], 3)
        self.assertAlmostEqual(traditional.loc[2, "center_y"], 100 / 6)

    def test_rejects_invalid_coordinates(self) -> None:
        invalid_actions = self.actions.copy()
        invalid_actions.loc[0, "x"] = 101

        with self.assertRaisesRegex(ValueError, "inside the Opta 0–100 pitch"):
            build_action_location_figure(
                invalid_actions,
                self.appearance,
                layout=LAYOUT_BOTH,
            )

    def test_rejects_action_count_mismatch(self) -> None:
        mismatched_appearance = self.appearance.copy()
        mismatched_appearance["action_count"] = len(self.actions) + 1

        with self.assertRaisesRegex(ValueError, "do not match"):
            build_action_location_figure(
                self.actions,
                mismatched_appearance,
                layout=LAYOUT_BOTH,
            )


if __name__ == "__main__":
    unittest.main()
