"""Compare a player's zone profile with a league positional template."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


PROFILE_KEY = ["player_id", "layout", "zone_id"]
SUMMARY_COLUMNS = [
    "player_id",
    "player_name",
    "eligible_appearances",
    "total_actions",
    "teams",
    "template_eligible",
    "minimum_template_appearances",
]


@dataclass(frozen=True)
class PlayerTemplateComparison:
    """Zone differences and summary measures for one player and layout."""

    player_id: str
    player_name: str
    layout: str
    zone_comparison: pd.DataFrame
    similarity_score: float
    similarity_percentile: float
    eligible_appearances: int
    total_actions: int
    appearance_count_percentile: float
    action_count_percentile: float
    baseline_player_count: int
    baseline_method: str
    template_eligible: bool
    minimum_template_appearances: int

    @property
    def provisional(self) -> bool:
        """Return whether the player falls below the template sample threshold."""
        return not self.template_eligible


def total_variation_similarity(
    player_shares: np.ndarray | pd.Series,
    baseline_shares: np.ndarray | pd.Series,
) -> float:
    """Return a bounded 0–100 similarity based on total variation distance."""
    player = np.asarray(player_shares, dtype=float)
    baseline = np.asarray(baseline_shares, dtype=float)
    if player.shape != baseline.shape:
        raise ValueError("Player and baseline profiles must have the same shape")
    if not np.isclose(player.sum(), 1.0) or not np.isclose(baseline.sum(), 1.0):
        raise ValueError("Player and baseline zone shares must each sum to one")
    distance = 0.5 * np.abs(player - baseline).sum()
    return float(np.clip(100.0 * (1.0 - distance), 0.0, 100.0))


def empirical_percentile(value: float, population: pd.Series | np.ndarray) -> float:
    """Return a midpoint empirical percentile from 0 to 100, including ties."""
    values = np.asarray(population, dtype=float)
    values = values[np.isfinite(values)]
    if values.size == 0:
        return float("nan")
    equal_mask = np.isclose(values, value, rtol=1e-12, atol=1e-12)
    below = np.count_nonzero((values < value) & ~equal_mask)
    equal = np.count_nonzero(equal_mask)
    return float(100.0 * (below + 0.5 * equal) / values.size)


def _validate_profiles(player_profiles: pd.DataFrame) -> None:
    required = {
        *SUMMARY_COLUMNS,
        "layout",
        "zone_id",
        "zone_name",
        "center_x",
        "center_y",
        "mean_action_share",
    }
    missing = required.difference(player_profiles.columns)
    if missing:
        raise ValueError(f"Player profiles are missing columns: {sorted(missing)}")
    if player_profiles.duplicated(PROFILE_KEY).any():
        raise ValueError("Player profile keys must be unique")
    share_sums = player_profiles.groupby(["player_id", "layout"])[
        "mean_action_share"
    ].sum()
    if not np.isclose(share_sums, 1.0).all():
        raise ValueError("Every player-layout profile must sum to one")


def _layout_matrix(layout_profiles: pd.DataFrame) -> pd.DataFrame:
    matrix = layout_profiles.pivot(
        index="player_id",
        columns="zone_id",
        values="mean_action_share",
    ).sort_index(axis=1)
    if matrix.isna().any().any():
        raise ValueError("Every player must have a value for every layout zone")
    return matrix


def _qualifying_similarity_scores(
    qualifying_matrix: pd.DataFrame,
) -> pd.Series:
    if len(qualifying_matrix) < 2:
        raise ValueError("At least two qualifying players are required")
    total = qualifying_matrix.sum(axis=0)
    scores = {}
    for player_id, profile in qualifying_matrix.iterrows():
        leave_one_out = (total - profile) / (len(qualifying_matrix) - 1)
        scores[player_id] = total_variation_similarity(profile, leave_one_out)
    return pd.Series(scores, name="similarity_score", dtype=float)


def compare_player_to_template(
    player_profiles: pd.DataFrame,
    player_id: str,
    layout: str,
) -> PlayerTemplateComparison:
    """Compare one player profile with an independent league CB baseline."""
    _validate_profiles(player_profiles)
    layout_profiles = player_profiles.loc[player_profiles["layout"].eq(layout)].copy()
    if layout_profiles.empty:
        raise ValueError(f"Unknown layout: {layout}")

    selected_rows = layout_profiles.loc[layout_profiles["player_id"].eq(player_id)]
    if selected_rows.empty:
        raise ValueError(f"Player {player_id!r} has no profile for {layout!r}")

    matrix = _layout_matrix(layout_profiles)
    qualifying_ids = (
        layout_profiles.loc[layout_profiles["template_eligible"], "player_id"]
        .drop_duplicates()
        .tolist()
    )
    qualifying_matrix = matrix.loc[qualifying_ids]
    selected_summary = selected_rows[SUMMARY_COLUMNS].drop_duplicates().iloc[0]
    template_eligible = bool(selected_summary["template_eligible"])

    if template_eligible:
        peer_matrix = qualifying_matrix.drop(index=player_id)
        baseline_method = "leave_one_out"
    else:
        peer_matrix = qualifying_matrix
        baseline_method = "full_qualified_template"
    if peer_matrix.empty:
        raise ValueError("No peer players remain to form the comparison baseline")

    selected_profile = pd.Series(
        matrix.loc[[player_id]].iloc[0],
        index=matrix.columns,
        dtype=float,
    )
    baseline_profile = peer_matrix.mean(axis=0)
    similarity_score = total_variation_similarity(
        selected_profile,
        baseline_profile,
    )

    zone_context = (
        selected_rows[
            ["zone_id", "zone_name", "center_x", "center_y", "mean_action_share"]
        ]
        .rename(columns={"mean_action_share": "player_share"})
        .sort_values("zone_id")
        .reset_index(drop=True)
    )
    peer_zone_percentiles = peer_matrix.quantile([0.25, 0.75], axis=0).T
    peer_zone_percentiles.columns = ["peer_p25", "peer_p75"]
    zone_comparison = zone_context.copy()
    zone_comparison["template_share"] = zone_comparison["zone_id"].map(
        baseline_profile
    )
    zone_comparison["peer_p25"] = zone_comparison["zone_id"].map(
        peer_zone_percentiles["peer_p25"]
    )
    zone_comparison["peer_p75"] = zone_comparison["zone_id"].map(
        peer_zone_percentiles["peer_p75"]
    )
    zone_comparison["difference"] = (
        zone_comparison["player_share"] - zone_comparison["template_share"]
    )
    zone_comparison["absolute_difference"] = zone_comparison["difference"].abs()
    zone_comparison["zone_percentile"] = [
        empirical_percentile(selected_profile.loc[zone_id], peer_matrix[zone_id])
        for zone_id in zone_comparison["zone_id"]
    ]

    qualifying_scores = _qualifying_similarity_scores(qualifying_matrix)
    similarity_percentile = empirical_percentile(
        similarity_score,
        qualifying_scores,
    )

    player_summaries = player_profiles[SUMMARY_COLUMNS].drop_duplicates("player_id")
    eligible_appearances = int(selected_summary["eligible_appearances"])
    total_actions = int(selected_summary["total_actions"])

    return PlayerTemplateComparison(
        player_id=str(player_id),
        player_name=str(selected_summary["player_name"]),
        layout=layout,
        zone_comparison=zone_comparison,
        similarity_score=similarity_score,
        similarity_percentile=similarity_percentile,
        eligible_appearances=eligible_appearances,
        total_actions=total_actions,
        appearance_count_percentile=empirical_percentile(
            eligible_appearances,
            player_summaries["eligible_appearances"],
        ),
        action_count_percentile=empirical_percentile(
            total_actions,
            player_summaries["total_actions"],
        ),
        baseline_player_count=len(peer_matrix),
        baseline_method=baseline_method,
        template_eligible=template_eligible,
        minimum_template_appearances=int(
            selected_summary["minimum_template_appearances"]
        ),
    )
