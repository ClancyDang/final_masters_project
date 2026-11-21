"""Tests for player-to-template comparison calculations."""

from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from src.analysis.player_template_comparison import (
    compare_player_to_template,
    empirical_percentile,
    total_variation_similarity,
)


def _profile_rows(
    player_id: str,
    player_name: str,
    shares: tuple[float, float],
    *,
    eligible: bool,
    appearances: int,
    actions: int,
) -> list[dict]:
    rows = []
    for zone_id, share in enumerate(shares, start=1):
        rows.append(
            {
                "player_id": player_id,
                "player_name": player_name,
                "layout": "test_layout",
                "zone_id": zone_id,
                "zone_name": f"zone-{zone_id}",
                "center_x": zone_id * 25.0,
                "center_y": 50.0,
                "mean_action_share": share,
                "eligible_appearances": appearances,
                "total_actions": actions,
                "teams": "Example FC",
                "template_eligible": eligible,
                "minimum_template_appearances": 5,
            }
        )
    return rows


class SimilarityCalculationTests(unittest.TestCase):
    def test_identical_profiles_score_100(self) -> None:
        self.assertEqual(
            total_variation_similarity([0.4, 0.6], [0.4, 0.6]),
            100.0,
        )

    def test_disjoint_profiles_score_zero(self) -> None:
        self.assertEqual(total_variation_similarity([1, 0], [0, 1]), 0.0)

    def test_half_overlap_scores_50_and_is_symmetric(self) -> None:
        forward = total_variation_similarity([0.5, 0.5], [1, 0])
        reverse = total_variation_similarity([1, 0], [0.5, 0.5])
        self.assertEqual(forward, 50.0)
        self.assertEqual(forward, reverse)

    def test_percentile_uses_midpoint_for_ties(self) -> None:
        self.assertEqual(empirical_percentile(2, [1, 2, 2, 3]), 50.0)


class PlayerTemplateComparisonTests(unittest.TestCase):
    def setUp(self) -> None:
        self.profiles = pd.DataFrame(
            _profile_rows(
                "a", "Player A", (1.0, 0.0), eligible=True, appearances=10, actions=500
            )
            + _profile_rows(
                "b", "Player B", (0.0, 1.0), eligible=True, appearances=8, actions=400
            )
            + _profile_rows(
                "c", "Player C", (0.5, 0.5), eligible=True, appearances=6, actions=300
            )
            + _profile_rows(
                "d", "Player D", (0.75, 0.25), eligible=False, appearances=2, actions=80
            )
        )

    def test_qualified_player_uses_leave_one_out_baseline(self) -> None:
        result = compare_player_to_template(self.profiles, "a", "test_layout")

        self.assertEqual(result.baseline_method, "leave_one_out")
        self.assertEqual(result.baseline_player_count, 2)
        np.testing.assert_allclose(
            result.zone_comparison["template_share"],
            [0.25, 0.75],
        )
        self.assertEqual(result.similarity_score, 25.0)

    def test_provisional_player_uses_full_qualified_baseline(self) -> None:
        result = compare_player_to_template(self.profiles, "d", "test_layout")

        self.assertTrue(result.provisional)
        self.assertEqual(result.baseline_method, "full_qualified_template")
        self.assertEqual(result.baseline_player_count, 3)
        np.testing.assert_allclose(
            result.zone_comparison["template_share"],
            [0.5, 0.5],
        )
        self.assertEqual(result.similarity_score, 75.0)

    def test_zone_differences_sum_to_zero(self) -> None:
        result = compare_player_to_template(self.profiles, "c", "test_layout")

        self.assertTrue(np.isclose(result.zone_comparison["difference"].sum(), 0))
        self.assertTrue(result.zone_comparison["zone_percentile"].between(0, 100).all())
        self.assertGreaterEqual(result.similarity_percentile, 0)
        self.assertLessEqual(result.similarity_percentile, 100)


if __name__ == "__main__":
    unittest.main()
