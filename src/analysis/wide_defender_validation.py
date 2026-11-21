"""Validate Forest full-back and wing-back positional templates."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .centre_back_templates import (
    APPEARANCE_KEYS,
    POSITIONAL_LAYOUT,
    TRADITIONAL_LAYOUT,
)
from .centre_back_validation import (
    ACTION_FAMILIES,
    _bootstrap_player_layout,
)
from .player_template_comparison import (
    compare_player_to_template,
    total_variation_similarity,
)
from .wide_defender_templates import (
    SUPPORTED_GROUPS,
    WideDefenderTemplateResult,
    build_wide_defender_templates,
)


@dataclass
class WideDefenderValidationResult:
    """Validation tables for one full-back or wing-back position group."""

    position_group: str
    forest_summary: pd.DataFrame
    zone_interpretation: pd.DataFrame
    bootstrap_summary: pd.DataFrame
    bootstrap_zone_intervals: pd.DataFrame
    split_half_summary: pd.DataFrame
    layout_robustness: pd.DataFrame
    action_family_sensitivity: pd.DataFrame
    quality_checks: pd.DataFrame


def _forest_player_groups(
    player_profiles: pd.DataFrame,
    team_name: str,
) -> pd.DataFrame:
    players = (
        player_profiles.loc[
            player_profiles["teams"].str.contains(team_name, na=False),
            [
                "template_group",
                "template_scope",
                "player_id",
                "player_name",
            ],
        ]
        .drop_duplicates()
        .sort_values(["template_group", "player_name", "player_id"])
        .reset_index(drop=True)
    )
    if players.empty:
        raise ValueError(f"No wide-defender profiles found for {team_name}")
    return players


def _dominant_role(
    appearance_profiles: pd.DataFrame,
    player_id: str,
    template_group: str,
) -> tuple[str, int, float]:
    appearances = appearance_profiles.loc[
        appearance_profiles["player_id"].eq(player_id)
        & appearance_profiles["template_group"].eq(template_group)
    ].drop_duplicates(APPEARANCE_KEYS)
    counts = appearances["standardised_position"].value_counts()
    role = str(counts.index[0])
    return role, int(counts.iloc[0]), float(counts.iloc[0] / counts.sum())


def _expected_spatial_side(template_group: str, template_scope: str) -> str:
    if template_scope == "role_normalised":
        return "left"
    if template_group.startswith("Left"):
        return "left"
    return "right"


def _observed_spatial_side(lateral_centroid: float) -> str:
    if lateral_centroid > 50:
        return "left"
    if lateral_centroid < 50:
        return "right"
    return "central"


def _comparison_tables(
    template_result: WideDefenderTemplateResult,
    team_name: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    summary_rows: list[dict] = []
    zone_rows: list[pd.DataFrame] = []
    player_profiles = template_result.player_profiles
    appearance_profiles = template_result.appearance_profiles
    for player in _forest_player_groups(player_profiles, team_name).itertuples(
        index=False
    ):
        role, role_count, role_share = _dominant_role(
            appearance_profiles,
            player.player_id,
            player.template_group,
        )
        for layout in (POSITIONAL_LAYOUT, TRADITIONAL_LAYOUT):
            comparison = compare_player_to_template(
                player_profiles,
                player.player_id,
                layout,
                template_group=player.template_group,
            )
            zones = comparison.zone_comparison.copy()
            player_centroid = float((zones["center_y"] * zones["player_share"]).sum())
            baseline_centroid = float(
                (zones["center_y"] * zones["template_share"]).sum()
            )
            expected_side = _expected_spatial_side(
                player.template_group,
                player.template_scope,
            )
            observed_side = _observed_spatial_side(player_centroid)
            summary_rows.append(
                {
                    "position_group": template_result.position_group,
                    "template_group": player.template_group,
                    "template_scope": player.template_scope,
                    "player_id": player.player_id,
                    "player_name": player.player_name,
                    "layout": layout,
                    "dominant_provider_role": role,
                    "dominant_role_appearances": role_count,
                    "dominant_role_share": role_share,
                    "eligible_appearances": comparison.eligible_appearances,
                    "total_actions": comparison.total_actions,
                    "template_eligible": comparison.template_eligible,
                    "similarity_score": comparison.similarity_score,
                    "similarity_percentile": comparison.similarity_percentile,
                    "baseline_method": comparison.baseline_method,
                    "player_lateral_centroid": player_centroid,
                    "baseline_lateral_centroid": baseline_centroid,
                    "relative_lateral_shift": player_centroid - baseline_centroid,
                    "expected_spatial_side": expected_side,
                    "observed_spatial_side": observed_side,
                    "orientation_alignment": observed_side == expected_side,
                }
            )
            zones.insert(0, "template_group", player.template_group)
            zones.insert(0, "player_name", player.player_name)
            zones.insert(0, "player_id", player.player_id)
            zones["difference_direction"] = np.select(
                [zones["difference"].gt(0), zones["difference"].lt(0)],
                ["above baseline", "below baseline"],
                default="at baseline",
            )
            zone_rows.append(zones)
    return pd.DataFrame(summary_rows), pd.concat(zone_rows, ignore_index=True)


def _bootstrap_tables(
    template_result: WideDefenderTemplateResult,
    team_name: str,
    iterations: int,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    summary_rows: list[dict] = []
    interval_rows: list[pd.DataFrame] = []
    for player in _forest_player_groups(
        template_result.player_profiles,
        team_name,
    ).itertuples(index=False):
        for layout in (POSITIONAL_LAYOUT, TRADITIONAL_LAYOUT):
            comparison = compare_player_to_template(
                template_result.player_profiles,
                player.player_id,
                layout,
                template_group=player.template_group,
            )
            player_appearances = template_result.appearance_profiles.loc[
                template_result.appearance_profiles["player_id"].eq(player.player_id)
                & template_result.appearance_profiles["template_group"].eq(
                    player.template_group
                )
                & template_result.appearance_profiles["layout"].eq(layout)
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
                    "position_group": template_result.position_group,
                    "template_group": player.template_group,
                    "template_scope": player.template_scope,
                    "player_id": player.player_id,
                    "player_name": player.player_name,
                    "layout": layout,
                    **summary,
                }
            )
            intervals.insert(0, "template_group", player.template_group)
            intervals.insert(0, "player_name", player.player_name)
            intervals.insert(0, "player_id", player.player_id)
            interval_rows.append(intervals)
    return pd.DataFrame(summary_rows), pd.concat(interval_rows, ignore_index=True)


def _split_half_table(
    template_result: WideDefenderTemplateResult,
    team_name: str,
    iterations: int,
    seed: int,
    minimum_appearances: int = 10,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows: list[dict] = []
    for player in _forest_player_groups(
        template_result.player_profiles,
        team_name,
    ).itertuples(index=False):
        for layout in (POSITIONAL_LAYOUT, TRADITIONAL_LAYOUT):
            data = template_result.appearance_profiles.loc[
                template_result.appearance_profiles["player_id"].eq(player.player_id)
                & template_result.appearance_profiles["template_group"].eq(
                    player.template_group
                )
                & template_result.appearance_profiles["layout"].eq(layout)
            ]
            matrix = data.pivot(
                index=APPEARANCE_KEYS,
                columns="zone_id",
                values="action_share",
            ).sort_index(axis=1)
            base = {
                "position_group": template_result.position_group,
                "template_group": player.template_group,
                "template_scope": player.template_scope,
                "player_id": player.player_id,
                "player_name": player.player_name,
                "layout": layout,
                "appearance_count": len(matrix),
            }
            if len(matrix) < minimum_appearances:
                rows.append(
                    {
                        **base,
                        "split_half_status": "insufficient sample",
                        "split_half_iterations": 0,
                        "median_split_half_similarity": np.nan,
                        "split_half_p05": np.nan,
                        "split_half_p95": np.nan,
                    }
                )
                continue
            values = matrix.to_numpy(dtype=float)
            first_size = len(values) // 2
            similarities = []
            for _ in range(iterations):
                shuffled = rng.permutation(len(values))
                first = values[shuffled[:first_size]].mean(axis=0)
                second = values[shuffled[first_size:]].mean(axis=0)
                similarities.append(total_variation_similarity(first, second))
            rows.append(
                {
                    **base,
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
    rows: list[dict] = []
    for template_group, group_profiles in player_profiles.groupby("template_group"):
        scores = []
        players = group_profiles[["player_id", "player_name"]].drop_duplicates()
        for player in players.itertuples(index=False):
            positional = compare_player_to_template(
                player_profiles,
                player.player_id,
                POSITIONAL_LAYOUT,
                template_group=template_group,
            )
            traditional = compare_player_to_template(
                player_profiles,
                player.player_id,
                TRADITIONAL_LAYOUT,
                template_group=template_group,
            )
            scores.append(
                {
                    "template_eligible": positional.template_eligible,
                    "positional_20_similarity": positional.similarity_score,
                    "traditional_18_similarity": traditional.similarity_score,
                    "absolute_score_difference": abs(
                        positional.similarity_score
                        - traditional.similarity_score
                    ),
                }
            )
        score_table = pd.DataFrame(scores)
        for population_name, population in (
            ("all player profiles", score_table),
            (
                "template-qualified players",
                score_table.loc[score_table["template_eligible"]],
            ),
        ):
            rows.append(
                {
                    "template_group": template_group,
                    "population": population_name,
                    "player_count": len(population),
                    "pearson_score_correlation": population[
                        ["positional_20_similarity", "traditional_18_similarity"]
                    ]
                    .corr(method="pearson")
                    .iloc[0, 1],
                    "spearman_rank_correlation": population[
                        ["positional_20_similarity", "traditional_18_similarity"]
                    ]
                    .corr(method="spearman")
                    .iloc[0, 1],
                    "mean_absolute_score_difference": population[
                        "absolute_score_difference"
                    ].mean(),
                    "median_absolute_score_difference": population[
                        "absolute_score_difference"
                    ].median(),
                    "maximum_absolute_score_difference": population[
                        "absolute_score_difference"
                    ].max(),
                }
            )
    return pd.DataFrame(rows)


def _family_template_result(
    eligible_actions: pd.DataFrame,
    eligible_appearances: pd.DataFrame,
    position_group: str,
    type_ids: frozenset[int],
    minimum_player_appearances: int,
) -> WideDefenderTemplateResult:
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
        eligible_appearances.drop(columns=["action_count"])
        .merge(counts, on=APPEARANCE_KEYS, how="left", validate="one_to_one")
        .rename(columns={"family_action_count": "action_count"})
    )
    appearances["action_count"] = appearances["action_count"].fillna(0).astype(int)
    appearances = appearances.loc[appearances["action_count"].gt(0)].copy()
    return build_wide_defender_templates(
        family_actions,
        appearances,
        position_group,
        minimum_player_appearances=minimum_player_appearances,
    )


def _action_family_sensitivity(
    template_result: WideDefenderTemplateResult,
    eligible_actions: pd.DataFrame,
    eligible_appearances: pd.DataFrame,
    team_name: str,
) -> pd.DataFrame:
    minimum_appearances = int(
        template_result.player_profiles["minimum_template_appearances"].iloc[0]
    )
    results_by_family = {"all_direct_actions": template_result}
    for family, type_ids in ACTION_FAMILIES.items():
        if type_ids is not None:
            results_by_family[family] = _family_template_result(
                eligible_actions,
                eligible_appearances,
                template_result.position_group,
                type_ids,
                minimum_appearances,
            )

    original_forest = _forest_player_groups(
        template_result.player_profiles,
        team_name,
    )
    rows: list[dict] = []
    for family, family_result in results_by_family.items():
        profiles = family_result.player_profiles
        available = set(zip(profiles["template_group"], profiles["player_id"]))
        for player in original_forest.itertuples(index=False):
            if (player.template_group, player.player_id) not in available:
                continue
            for layout in (POSITIONAL_LAYOUT, TRADITIONAL_LAYOUT):
                comparison = compare_player_to_template(
                    profiles,
                    player.player_id,
                    layout,
                    template_group=player.template_group,
                )
                rows.append(
                    {
                        "position_group": template_result.position_group,
                        "action_family": family,
                        "template_group": player.template_group,
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


def _quality_checks(result: WideDefenderValidationResult) -> pd.DataFrame:
    checks = [
        ("Position group", result.position_group),
        ("Forest player-template profiles", len(result.forest_summary) // 2),
        ("Forest layout summary rows", len(result.forest_summary)),
        ("Forest zone interpretation rows", len(result.zone_interpretation)),
        ("Bootstrap summary rows", len(result.bootstrap_summary)),
        ("Bootstrap zone interval rows", len(result.bootstrap_zone_intervals)),
        ("Split-half summary rows", len(result.split_half_summary)),
        ("Layout robustness rows", len(result.layout_robustness)),
        ("Action-family sensitivity rows", len(result.action_family_sensitivity)),
        (
            "Orientation alignment failures",
            int((~result.forest_summary["orientation_alignment"]).sum()),
        ),
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


def build_wide_defender_validation(
    template_result: WideDefenderTemplateResult,
    eligible_actions: pd.DataFrame,
    eligible_appearances: pd.DataFrame,
    *,
    team_name: str = "Nottingham Forest",
    bootstrap_iterations: int = 1000,
    split_half_iterations: int = 500,
    random_seed: int = 42,
) -> WideDefenderValidationResult:
    """Build validation outputs for one wide-defender position group."""

    if bootstrap_iterations < 100:
        raise ValueError("bootstrap_iterations must be at least 100")
    if split_half_iterations < 100:
        raise ValueError("split_half_iterations must be at least 100")
    if template_result.position_group not in SUPPORTED_GROUPS:
        raise ValueError("Unsupported wide-defender position group")
    summary, zones = _comparison_tables(template_result, team_name)
    bootstrap, bootstrap_zones = _bootstrap_tables(
        template_result,
        team_name,
        bootstrap_iterations,
        random_seed,
    )
    result = WideDefenderValidationResult(
        position_group=template_result.position_group,
        forest_summary=summary,
        zone_interpretation=zones,
        bootstrap_summary=bootstrap,
        bootstrap_zone_intervals=bootstrap_zones,
        split_half_summary=_split_half_table(
            template_result,
            team_name,
            split_half_iterations,
            random_seed + 1,
        ),
        layout_robustness=_layout_robustness(template_result.player_profiles),
        action_family_sensitivity=_action_family_sensitivity(
            template_result,
            eligible_actions,
            eligible_appearances,
            team_name,
        ),
        quality_checks=pd.DataFrame(),
    )
    result.quality_checks = _quality_checks(result)
    failures = result.quality_checks.loc[
        result.quality_checks["check"].str.endswith("failures"), "value"
    ]
    if not failures.astype(int).eq(0).all():
        raise AssertionError(
            f"{result.position_group} validation quality checks failed"
        )
    return result


def write_wide_defender_validation_outputs(
    result: WideDefenderValidationResult,
    output_directory: str | Path,
) -> dict[str, Path]:
    """Write ignored validation tables for one wide-defender role."""

    output_directory = Path(output_directory).resolve()
    output_directory.mkdir(parents=True, exist_ok=True)
    prefix = result.position_group.lower().replace("-", "_").replace(" ", "_")
    outputs = {
        "forest_summary": output_directory / f"forest_{prefix}_validation_summary.csv",
        "zone_interpretation": output_directory
        / f"forest_{prefix}_zone_interpretation.parquet",
        "bootstrap_summary": output_directory
        / f"forest_{prefix}_bootstrap_summary.csv",
        "bootstrap_zone_intervals": output_directory
        / f"forest_{prefix}_bootstrap_zone_intervals.parquet",
        "split_half_summary": output_directory
        / f"forest_{prefix}_split_half_summary.csv",
        "layout_robustness": output_directory
        / f"{prefix}_layout_robustness.csv",
        "action_family_sensitivity": output_directory
        / f"forest_{prefix}_action_family_sensitivity.csv",
        "quality_checks": output_directory
        / f"forest_{prefix}_validation_quality_checks.csv",
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
