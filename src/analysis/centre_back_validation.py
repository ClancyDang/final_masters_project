"""Validate Forest centre-back profiles before expanding to other positions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .centre_back_templates import (
    APPEARANCE_KEYS,
    POSITIONAL_LAYOUT,
    TRADITIONAL_LAYOUT,
    build_centre_back_templates,
)
from .player_template_comparison import compare_player_to_template


PASS_TYPE_IDS = frozenset({1, 2, 74})
DEFENSIVE_TYPE_IDS = frozenset({7, 8, 10, 12, 44, 45, 49, 56, 83})
ACTION_FAMILIES = {
    "all_direct_actions": None,
    "passes": PASS_TYPE_IDS,
    "defensive_actions": DEFENSIVE_TYPE_IDS,
}


@dataclass
class CentreBackValidationResult:
    """Tables produced by the Forest centre-back validation stage."""

    forest_summary: pd.DataFrame
    zone_interpretation: pd.DataFrame
    bootstrap_summary: pd.DataFrame
    bootstrap_zone_intervals: pd.DataFrame
    split_half_summary: pd.DataFrame
    layout_robustness: pd.DataFrame
    action_family_sensitivity: pd.DataFrame
    quality_checks: pd.DataFrame


def _forest_players(player_profiles: pd.DataFrame, team_name: str) -> pd.DataFrame:
    players = (
        player_profiles.loc[
            player_profiles["teams"].str.contains(team_name, na=False),
            ["player_id", "player_name"],
        ]
        .drop_duplicates()
        .sort_values(["player_name", "player_id"])
        .reset_index(drop=True)
    )
    if players.empty:
        raise ValueError(f"No player profiles found for {team_name}")
    return players


def _dominant_roles(
    appearance_profiles: pd.DataFrame,
    team_name: str,
) -> pd.DataFrame:
    appearances = appearance_profiles.loc[
        appearance_profiles["team_name"].eq(team_name)
    ].drop_duplicates(APPEARANCE_KEYS)
    counts = (
        appearances.groupby(
            ["player_id", "player_name", "standardised_position"],
            as_index=False,
        )
        .size()
        .rename(columns={"size": "role_appearances"})
    )
    totals = counts.groupby("player_id")["role_appearances"].transform("sum")
    counts["role_share"] = counts["role_appearances"] / totals
    return (
        counts.sort_values(
            ["player_id", "role_appearances", "standardised_position"],
            ascending=[True, False, True],
        )
        .drop_duplicates("player_id")
        .rename(
            columns={
                "standardised_position": "dominant_provider_role",
                "role_appearances": "dominant_role_appearances",
                "role_share": "dominant_role_share",
            }
        )
    )


def _spatial_side(relative_lateral_shift: float, tolerance: float = 1.0) -> str:
    if relative_lateral_shift > tolerance:
        return "left-shifted"
    if relative_lateral_shift < -tolerance:
        return "right-shifted"
    return "near baseline"


def _role_side(role: str) -> str:
    if role.startswith("Left"):
        return "left-shifted"
    if role.startswith("Right"):
        return "right-shifted"
    return "near baseline"


def _comparison_tables(
    appearance_profiles: pd.DataFrame,
    player_profiles: pd.DataFrame,
    team_name: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    roles = _dominant_roles(appearance_profiles, team_name).set_index("player_id")
    summary_rows: list[dict] = []
    zone_rows: list[pd.DataFrame] = []
    for player in _forest_players(player_profiles, team_name).itertuples(index=False):
        role = roles.loc[player.player_id]
        for layout in (POSITIONAL_LAYOUT, TRADITIONAL_LAYOUT):
            comparison = compare_player_to_template(
                player_profiles,
                player.player_id,
                layout,
            )
            zones = comparison.zone_comparison.copy()
            player_centroid = float((zones["center_y"] * zones["player_share"]).sum())
            baseline_centroid = float(
                (zones["center_y"] * zones["template_share"]).sum()
            )
            lateral_shift = player_centroid - baseline_centroid
            spatial_side = _spatial_side(lateral_shift)
            expected_side = _role_side(str(role["dominant_provider_role"]))
            summary_rows.append(
                {
                    "player_id": player.player_id,
                    "player_name": player.player_name,
                    "layout": layout,
                    "dominant_provider_role": role["dominant_provider_role"],
                    "dominant_role_appearances": int(
                        role["dominant_role_appearances"]
                    ),
                    "dominant_role_share": float(role["dominant_role_share"]),
                    "eligible_appearances": comparison.eligible_appearances,
                    "total_actions": comparison.total_actions,
                    "template_eligible": comparison.template_eligible,
                    "similarity_score": comparison.similarity_score,
                    "similarity_percentile": comparison.similarity_percentile,
                    "baseline_method": comparison.baseline_method,
                    "player_lateral_centroid": player_centroid,
                    "baseline_lateral_centroid": baseline_centroid,
                    "relative_lateral_shift": lateral_shift,
                    "spatial_side": spatial_side,
                    "role_expected_side": expected_side,
                    "role_spatial_alignment": spatial_side == expected_side,
                }
            )
            zones.insert(0, "layout", layout)
            zones.insert(0, "player_name", player.player_name)
            zones.insert(0, "player_id", player.player_id)
            zones["difference_direction"] = np.select(
                [zones["difference"].gt(0), zones["difference"].lt(0)],
                ["above baseline", "below baseline"],
                default="at baseline",
            )
            zone_rows.append(zones)
    return pd.DataFrame(summary_rows), pd.concat(zone_rows, ignore_index=True)


def _bootstrap_player_layout(
    player_appearances: pd.DataFrame,
    baseline: pd.Series,
    iterations: int,
    rng: np.random.Generator,
) -> tuple[dict, pd.DataFrame]:
    context = (
        player_appearances[
            ["zone_id", "zone_name", "center_x", "center_y"]
        ]
        .drop_duplicates("zone_id")
        .sort_values("zone_id")
        .reset_index(drop=True)
    )
    matrix = player_appearances.pivot(
        index=APPEARANCE_KEYS,
        columns="zone_id",
        values="action_share",
    ).sort_index(axis=1)
    if matrix.isna().any().any():
        raise ValueError("Appearance-zone profile contains missing shares")
    sample_count = len(matrix)
    sample_indices = rng.integers(
        0,
        sample_count,
        size=(iterations, sample_count),
    )
    bootstrap_profiles = matrix.to_numpy()[sample_indices].mean(axis=1)
    baseline_values = baseline.reindex(matrix.columns).to_numpy(dtype=float)
    similarities = 100 * (
        1 - 0.5 * np.abs(bootstrap_profiles - baseline_values).sum(axis=1)
    )
    center_y = context.set_index("zone_id").reindex(matrix.columns)[
        "center_y"
    ].to_numpy(dtype=float)
    lateral_centroids = bootstrap_profiles @ center_y
    point_profile = matrix.mean(axis=0).to_numpy(dtype=float)
    point_similarity = float(
        100 * (1 - 0.5 * np.abs(point_profile - baseline_values).sum())
    )
    summary = {
        "appearance_count": sample_count,
        "bootstrap_iterations": iterations,
        "similarity_score": point_similarity,
        "similarity_ci_low": float(np.quantile(similarities, 0.025)),
        "similarity_ci_high": float(np.quantile(similarities, 0.975)),
        "similarity_bootstrap_sd": float(similarities.std(ddof=1)),
        "lateral_centroid": float(point_profile @ center_y),
        "lateral_centroid_ci_low": float(np.quantile(lateral_centroids, 0.025)),
        "lateral_centroid_ci_high": float(np.quantile(lateral_centroids, 0.975)),
    }
    zone_intervals = context.copy()
    zone_intervals["mean_action_share"] = point_profile
    zone_intervals["bootstrap_ci_low"] = np.quantile(
        bootstrap_profiles,
        0.025,
        axis=0,
    )
    zone_intervals["bootstrap_ci_high"] = np.quantile(
        bootstrap_profiles,
        0.975,
        axis=0,
    )
    zone_intervals["bootstrap_ci_width"] = (
        zone_intervals["bootstrap_ci_high"] - zone_intervals["bootstrap_ci_low"]
    )
    return summary, zone_intervals


def _bootstrap_tables(
    appearance_profiles: pd.DataFrame,
    player_profiles: pd.DataFrame,
    team_name: str,
    iterations: int,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    summary_rows: list[dict] = []
    interval_rows: list[pd.DataFrame] = []
    for player in _forest_players(player_profiles, team_name).itertuples(index=False):
        for layout in (POSITIONAL_LAYOUT, TRADITIONAL_LAYOUT):
            comparison = compare_player_to_template(
                player_profiles,
                player.player_id,
                layout,
            )
            player_appearances = appearance_profiles.loc[
                appearance_profiles["player_id"].eq(player.player_id)
                & appearance_profiles["layout"].eq(layout)
            ]
            baseline = comparison.zone_comparison.set_index("zone_id")[
                "template_share"
            ]
            summary, intervals = _bootstrap_player_layout(
                player_appearances,
                baseline,
                iterations,
                rng,
            )
            summary_rows.append(
                {
                    "player_id": player.player_id,
                    "player_name": player.player_name,
                    "layout": layout,
                    **summary,
                }
            )
            intervals.insert(0, "layout", layout)
            intervals.insert(0, "player_name", player.player_name)
            intervals.insert(0, "player_id", player.player_id)
            interval_rows.append(intervals)
    return pd.DataFrame(summary_rows), pd.concat(interval_rows, ignore_index=True)


def _split_half_tables(
    appearance_profiles: pd.DataFrame,
    player_profiles: pd.DataFrame,
    team_name: str,
    iterations: int,
    seed: int,
    minimum_appearances: int = 10,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows: list[dict] = []
    for player in _forest_players(player_profiles, team_name).itertuples(index=False):
        for layout in (POSITIONAL_LAYOUT, TRADITIONAL_LAYOUT):
            data = appearance_profiles.loc[
                appearance_profiles["player_id"].eq(player.player_id)
                & appearance_profiles["layout"].eq(layout)
            ]
            matrix = data.pivot(
                index=APPEARANCE_KEYS,
                columns="zone_id",
                values="action_share",
            ).sort_index(axis=1)
            if len(matrix) < minimum_appearances:
                rows.append(
                    {
                        "player_id": player.player_id,
                        "player_name": player.player_name,
                        "layout": layout,
                        "appearance_count": len(matrix),
                        "split_half_status": "insufficient sample",
                        "split_half_iterations": 0,
                        "median_split_half_similarity": np.nan,
                        "split_half_p05": np.nan,
                        "split_half_p95": np.nan,
                    }
                )
                continue
            values = matrix.to_numpy(dtype=float)
            first_half_size = len(values) // 2
            similarities = []
            for _ in range(iterations):
                shuffled = rng.permutation(len(values))
                first = values[shuffled[:first_half_size]].mean(axis=0)
                second = values[shuffled[first_half_size:]].mean(axis=0)
                similarities.append(
                    100 * (1 - 0.5 * np.abs(first - second).sum())
                )
            rows.append(
                {
                    "player_id": player.player_id,
                    "player_name": player.player_name,
                    "layout": layout,
                    "appearance_count": len(matrix),
                    "split_half_status": "calculated",
                    "split_half_iterations": iterations,
                    "median_split_half_similarity": float(
                        np.median(similarities)
                    ),
                    "split_half_p05": float(np.quantile(similarities, 0.05)),
                    "split_half_p95": float(np.quantile(similarities, 0.95)),
                }
            )
    return pd.DataFrame(rows)


def _layout_robustness(player_profiles: pd.DataFrame) -> pd.DataFrame:
    scores: list[dict] = []
    players = player_profiles[["player_id", "player_name"]].drop_duplicates()
    for player in players.itertuples(index=False):
        positional = compare_player_to_template(
            player_profiles,
            player.player_id,
            POSITIONAL_LAYOUT,
        )
        traditional = compare_player_to_template(
            player_profiles,
            player.player_id,
            TRADITIONAL_LAYOUT,
        )
        scores.append(
            {
                "player_id": player.player_id,
                "player_name": player.player_name,
                "template_eligible": positional.template_eligible,
                "positional_20_similarity": positional.similarity_score,
                "traditional_18_similarity": traditional.similarity_score,
                "absolute_score_difference": abs(
                    positional.similarity_score - traditional.similarity_score
                ),
            }
        )
    score_table = pd.DataFrame(scores)
    rows = []
    for population_name, population in (
        ("all player profiles", score_table),
        ("template-qualified players", score_table.loc[score_table["template_eligible"]]),
    ):
        rows.append(
            {
                "population": population_name,
                "player_count": len(population),
                "pearson_score_correlation": population[
                    ["positional_20_similarity", "traditional_18_similarity"]
                ].corr(method="pearson").iloc[0, 1],
                "spearman_rank_correlation": population[
                    ["positional_20_similarity", "traditional_18_similarity"]
                ].corr(method="spearman").iloc[0, 1],
                "mean_absolute_score_difference": population[
                    "absolute_score_difference"
                ].mean(),
                "median_absolute_score_difference": population[
                    "absolute_score_difference"
                ].median(),
                "p90_absolute_score_difference": population[
                    "absolute_score_difference"
                ].quantile(0.90),
                "maximum_absolute_score_difference": population[
                    "absolute_score_difference"
                ].max(),
            }
        )
    return pd.DataFrame(rows)


def _family_profiles(
    eligible_actions: pd.DataFrame,
    centre_back_appearances: pd.DataFrame,
    type_ids: frozenset[int],
) -> pd.DataFrame:
    family_actions = eligible_actions.loc[
        eligible_actions["type_id"].isin(type_ids)
    ].copy()
    counts = (
        family_actions.groupby(APPEARANCE_KEYS)
        .size()
        .rename("family_action_count")
        .reset_index()
    )
    appearances = (
        centre_back_appearances.drop(columns=["action_count"])
        .merge(counts, on=APPEARANCE_KEYS, how="left", validate="one_to_one")
        .rename(columns={"family_action_count": "action_count"})
    )
    appearances["action_count"] = appearances["action_count"].fillna(0).astype(int)
    appearances = appearances.loc[appearances["action_count"].gt(0)].copy()
    return build_centre_back_templates(
        family_actions,
        appearances,
    ).player_profiles


def _action_family_sensitivity(
    eligible_actions: pd.DataFrame,
    centre_back_appearances: pd.DataFrame,
    player_profiles: pd.DataFrame,
    team_name: str,
) -> pd.DataFrame:
    profiles_by_family = {"all_direct_actions": player_profiles}
    for family, type_ids in ACTION_FAMILIES.items():
        if type_ids is not None:
            profiles_by_family[family] = _family_profiles(
                eligible_actions,
                centre_back_appearances,
                type_ids,
            )
    rows: list[dict] = []
    forest_players = _forest_players(player_profiles, team_name)
    for family, family_profiles in profiles_by_family.items():
        available_ids = set(family_profiles["player_id"])
        for player in forest_players.itertuples(index=False):
            if player.player_id not in available_ids:
                continue
            for layout in (POSITIONAL_LAYOUT, TRADITIONAL_LAYOUT):
                comparison = compare_player_to_template(
                    family_profiles,
                    player.player_id,
                    layout,
                )
                rows.append(
                    {
                        "action_family": family,
                        "player_id": player.player_id,
                        "player_name": player.player_name,
                        "layout": layout,
                        "eligible_family_appearances": comparison.eligible_appearances,
                        "family_action_count": comparison.total_actions,
                        "family_template_eligible": comparison.template_eligible,
                        "similarity_score": comparison.similarity_score,
                        "similarity_percentile": comparison.similarity_percentile,
                        "baseline_player_count": comparison.baseline_player_count,
                    }
                )
    return pd.DataFrame(rows)


def _quality_checks(
    result: CentreBackValidationResult,
    team_name: str,
) -> pd.DataFrame:
    summary = result.forest_summary
    checks = [
        ("Validated club", team_name),
        ("Forest centre-backs", summary["player_id"].nunique()),
        ("Forest layout summary rows", len(summary)),
        ("Forest zone interpretation rows", len(result.zone_interpretation)),
        ("Bootstrap summary rows", len(result.bootstrap_summary)),
        ("Bootstrap zone interval rows", len(result.bootstrap_zone_intervals)),
        ("Split-half summary rows", len(result.split_half_summary)),
        ("Layout robustness populations", len(result.layout_robustness)),
        ("Action-family sensitivity rows", len(result.action_family_sensitivity)),
        (
            "Bootstrap interval order failures",
            int(
                (
                    result.bootstrap_summary["similarity_ci_low"]
                    > result.bootstrap_summary["similarity_ci_high"]
                ).sum()
            ),
        ),
        (
            "Zone interval order failures",
            int(
                (
                    result.bootstrap_zone_intervals["bootstrap_ci_low"]
                    > result.bootstrap_zone_intervals["bootstrap_ci_high"]
                ).sum()
            ),
        ),
    ]
    return pd.DataFrame(checks, columns=["check", "value"])


def build_centre_back_validation(
    appearance_profiles: pd.DataFrame,
    player_profiles: pd.DataFrame,
    eligible_actions: pd.DataFrame,
    centre_back_appearances: pd.DataFrame,
    *,
    team_name: str = "Nottingham Forest",
    bootstrap_iterations: int = 1000,
    split_half_iterations: int = 500,
    random_seed: int = 42,
) -> CentreBackValidationResult:
    """Build spatial, sampling, zoning and action-family validation tables."""
    if bootstrap_iterations < 100:
        raise ValueError("bootstrap_iterations must be at least 100")
    if split_half_iterations < 100:
        raise ValueError("split_half_iterations must be at least 100")
    forest_summary, zone_interpretation = _comparison_tables(
        appearance_profiles,
        player_profiles,
        team_name,
    )
    bootstrap_summary, bootstrap_zone_intervals = _bootstrap_tables(
        appearance_profiles,
        player_profiles,
        team_name,
        bootstrap_iterations,
        random_seed,
    )
    split_half_summary = _split_half_tables(
        appearance_profiles,
        player_profiles,
        team_name,
        split_half_iterations,
        random_seed + 1,
    )
    result = CentreBackValidationResult(
        forest_summary=forest_summary,
        zone_interpretation=zone_interpretation,
        bootstrap_summary=bootstrap_summary,
        bootstrap_zone_intervals=bootstrap_zone_intervals,
        split_half_summary=split_half_summary,
        layout_robustness=_layout_robustness(player_profiles),
        action_family_sensitivity=_action_family_sensitivity(
            eligible_actions,
            centre_back_appearances,
            player_profiles,
            team_name,
        ),
        quality_checks=pd.DataFrame(),
    )
    result.quality_checks = _quality_checks(result, team_name)
    failures = result.quality_checks.loc[
        result.quality_checks["check"].str.endswith("failures"), "value"
    ]
    if not failures.eq(0).all():
        raise AssertionError("Centre-back validation quality checks failed")
    return result


def write_centre_back_validation_outputs(
    result: CentreBackValidationResult,
    output_directory: str | Path,
) -> dict[str, Path]:
    """Write ignored validation tables for notebooks and the web app."""
    output_directory = Path(output_directory).resolve()
    output_directory.mkdir(parents=True, exist_ok=True)
    outputs = {
        "forest_summary": output_directory / "forest_cb_validation_summary.csv",
        "zone_interpretation": output_directory
        / "forest_cb_zone_interpretation.parquet",
        "bootstrap_summary": output_directory
        / "forest_cb_bootstrap_summary.csv",
        "bootstrap_zone_intervals": output_directory
        / "forest_cb_bootstrap_zone_intervals.parquet",
        "split_half_summary": output_directory
        / "forest_cb_split_half_summary.csv",
        "layout_robustness": output_directory
        / "centre_back_layout_robustness.csv",
        "action_family_sensitivity": output_directory
        / "forest_cb_action_family_sensitivity.csv",
        "quality_checks": output_directory
        / "forest_cb_validation_quality_checks.csv",
    }
    result.forest_summary.to_csv(outputs["forest_summary"], index=False)
    result.zone_interpretation.to_parquet(
        outputs["zone_interpretation"], index=False
    )
    result.bootstrap_summary.to_csv(outputs["bootstrap_summary"], index=False)
    result.bootstrap_zone_intervals.to_parquet(
        outputs["bootstrap_zone_intervals"], index=False
    )
    result.split_half_summary.to_csv(outputs["split_half_summary"], index=False)
    result.layout_robustness.to_csv(outputs["layout_robustness"], index=False)
    result.action_family_sensitivity.to_csv(
        outputs["action_family_sensitivity"], index=False
    )
    result.quality_checks.to_csv(outputs["quality_checks"], index=False)
    return outputs
