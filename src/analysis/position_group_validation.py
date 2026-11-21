"""Validate remaining Nottingham Forest positional-template comparisons."""

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
from .centre_back_validation import ACTION_FAMILIES, _bootstrap_player_layout
from .player_template_comparison import compare_player_to_template
from .position_group_templates import (
    POSITION_GROUP_ROLES,
    PositionGroupTemplateResult,
    build_position_group_templates,
)


@dataclass
class PositionGroupValidationResult:
    """Validation outputs for one remaining position group."""

    position_group: str
    forest_summary: pd.DataFrame
    zone_interpretation: pd.DataFrame
    bootstrap_summary: pd.DataFrame
    bootstrap_zone_intervals: pd.DataFrame
    split_half_summary: pd.DataFrame
    layout_robustness: pd.DataFrame
    action_family_sensitivity: pd.DataFrame
    quality_checks: pd.DataFrame


def _available_groups(result: PositionGroupTemplateResult) -> set[str]:
    return set(
        result.template_coverage.loc[
            result.template_coverage["template_available"], "template_group"
        ]
    )


def _forest_player_groups(
    result: PositionGroupTemplateResult,
    team_name: str,
) -> pd.DataFrame:
    available = _available_groups(result)
    players = (
        result.player_profiles.loc[
            result.player_profiles["template_group"].isin(available)
            & result.player_profiles["teams"].str.contains(team_name, na=False),
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
        raise ValueError(
            f"No {team_name} profiles have an available {result.position_group} template"
        )
    return players


def _dominant_role(
    result: PositionGroupTemplateResult,
    player_id: str,
    template_group: str,
) -> tuple[str, int, float]:
    appearances = result.appearance_profiles.loc[
        result.appearance_profiles["player_id"].eq(player_id)
        & result.appearance_profiles["template_group"].eq(template_group)
    ].drop_duplicates(APPEARANCE_KEYS)
    counts = appearances["standardised_position"].value_counts()
    return (
        str(counts.index[0]),
        int(counts.iloc[0]),
        float(counts.iloc[0] / counts.sum()),
    )


def _orientation_expectation(
    position_group: str,
    template_group: str,
    template_scope: str,
) -> str:
    if template_scope == "role_specific":
        if template_group.startswith("Left"):
            return "left"
        if template_group.startswith("Right"):
            return "right"
        return "not_applicable"
    roles = POSITION_GROUP_ROLES[position_group]
    if all(role.startswith(("Left", "Right")) for role in roles):
        return "left"
    return "not_applicable"


def _observed_side(centroid: float) -> str:
    if centroid > 50:
        return "left"
    if centroid < 50:
        return "right"
    return "central"


def _comparison_tables(
    result: PositionGroupTemplateResult,
    team_name: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    summaries: list[dict] = []
    zone_tables: list[pd.DataFrame] = []
    for player in _forest_player_groups(result, team_name).itertuples(index=False):
        role, role_count, role_share = _dominant_role(
            result,
            player.player_id,
            player.template_group,
        )
        for layout in (POSITIONAL_LAYOUT, TRADITIONAL_LAYOUT):
            comparison = compare_player_to_template(
                result.player_profiles,
                player.player_id,
                layout,
                template_group=player.template_group,
            )
            zones = comparison.zone_comparison.copy()
            player_centroid = float((zones["center_y"] * zones["player_share"]).sum())
            baseline_centroid = float(
                (zones["center_y"] * zones["template_share"]).sum()
            )
            expected = _orientation_expectation(
                result.position_group,
                player.template_group,
                player.template_scope,
            )
            observed = _observed_side(player_centroid)
            summaries.append(
                {
                    "position_group": result.position_group,
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
                    "expected_spatial_side": expected,
                    "observed_spatial_side": observed,
                    "orientation_alignment": (
                        True if expected == "not_applicable" else observed == expected
                    ),
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
            zone_tables.append(zones)
    return pd.DataFrame(summaries), pd.concat(zone_tables, ignore_index=True)


def _bootstrap_tables(
    result: PositionGroupTemplateResult,
    team_name: str,
    iterations: int,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    summaries: list[dict] = []
    intervals: list[pd.DataFrame] = []
    for player in _forest_player_groups(result, team_name).itertuples(index=False):
        for layout in (POSITIONAL_LAYOUT, TRADITIONAL_LAYOUT):
            comparison = compare_player_to_template(
                result.player_profiles,
                player.player_id,
                layout,
                template_group=player.template_group,
            )
            appearances = result.appearance_profiles.loc[
                result.appearance_profiles["player_id"].eq(player.player_id)
                & result.appearance_profiles["template_group"].eq(
                    player.template_group
                )
                & result.appearance_profiles["layout"].eq(layout)
            ]
            baseline = comparison.zone_comparison.set_index("zone_id")[
                "template_share"
            ]
            summary, zone_intervals = _bootstrap_player_layout(
                appearances,
                baseline,
                iterations,
                rng,
            )
            summaries.append(
                {
                    "position_group": result.position_group,
                    "template_group": player.template_group,
                    "template_scope": player.template_scope,
                    "player_id": player.player_id,
                    "player_name": player.player_name,
                    "layout": layout,
                    **summary,
                }
            )
            zone_intervals.insert(0, "template_group", player.template_group)
            zone_intervals.insert(0, "player_name", player.player_name)
            zone_intervals.insert(0, "player_id", player.player_id)
            intervals.append(zone_intervals)
    return pd.DataFrame(summaries), pd.concat(intervals, ignore_index=True)


def _split_half_table(
    result: PositionGroupTemplateResult,
    team_name: str,
    iterations: int,
    seed: int,
    minimum_appearances: int = 10,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for player in _forest_player_groups(result, team_name).itertuples(index=False):
        for layout in (POSITIONAL_LAYOUT, TRADITIONAL_LAYOUT):
            data = result.appearance_profiles.loc[
                result.appearance_profiles["player_id"].eq(player.player_id)
                & result.appearance_profiles["template_group"].eq(
                    player.template_group
                )
                & result.appearance_profiles["layout"].eq(layout)
            ]
            matrix = data.pivot(
                index=APPEARANCE_KEYS,
                columns="zone_id",
                values="action_share",
            ).sort_index(axis=1)
            base = {
                "position_group": result.position_group,
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
                similarities.append(
                    100 * (1 - 0.5 * np.abs(first - second).sum())
                )
            rows.append(
                {
                    **base,
                    "split_half_status": "calculated",
                    "split_half_iterations": iterations,
                    "median_split_half_similarity": float(np.median(similarities)),
                    "split_half_p05": float(np.quantile(similarities, 0.05)),
                    "split_half_p95": float(np.quantile(similarities, 0.95)),
                }
            )
    return pd.DataFrame(rows)


def _layout_scores(group_profiles: pd.DataFrame, layout: str) -> pd.DataFrame:
    layout_profiles = group_profiles.loc[group_profiles["layout"].eq(layout)]
    matrix = layout_profiles.pivot(
        index="player_id", columns="zone_id", values="mean_action_share"
    ).sort_index(axis=1)
    eligible = (
        layout_profiles[["player_id", "template_eligible"]]
        .drop_duplicates()
        .set_index("player_id")["template_eligible"]
        .reindex(matrix.index)
    )
    qualifying = matrix.loc[eligible]
    qualifying_total = qualifying.sum(axis=0)
    qualifying_mean = qualifying.mean(axis=0)
    scores = []
    for player_id, profile in matrix.iterrows():
        if eligible.loc[player_id]:
            baseline = (qualifying_total - profile) / (len(qualifying) - 1)
        else:
            baseline = qualifying_mean
        scores.append(
            {
                "player_id": player_id,
                "template_eligible": bool(eligible.loc[player_id]),
                f"{layout}_similarity": float(
                    100 * (1 - 0.5 * np.abs(profile - baseline).sum())
                ),
            }
        )
    return pd.DataFrame(scores)


def _layout_robustness(result: PositionGroupTemplateResult) -> pd.DataFrame:
    rows = []
    for template_group in sorted(_available_groups(result)):
        group_profiles = result.player_profiles.loc[
            result.player_profiles["template_group"].eq(template_group)
        ]
        scores = _layout_scores(group_profiles, POSITIONAL_LAYOUT).merge(
            _layout_scores(group_profiles, TRADITIONAL_LAYOUT),
            on=["player_id", "template_eligible"],
            validate="one_to_one",
        )
        scores["absolute_score_difference"] = (
            scores[f"{POSITIONAL_LAYOUT}_similarity"]
            - scores[f"{TRADITIONAL_LAYOUT}_similarity"]
        ).abs()
        for population_name, population in (
            ("all player profiles", scores),
            (
                "template-qualified players",
                scores.loc[scores["template_eligible"]],
            ),
        ):
            score_columns = [
                f"{POSITIONAL_LAYOUT}_similarity",
                f"{TRADITIONAL_LAYOUT}_similarity",
            ]
            rows.append(
                {
                    "position_group": result.position_group,
                    "template_group": template_group,
                    "population": population_name,
                    "player_count": len(population),
                    "pearson_score_correlation": population[score_columns]
                    .corr(method="pearson")
                    .iloc[0, 1],
                    "spearman_rank_correlation": population[score_columns]
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


def _family_result(
    eligible_actions: pd.DataFrame,
    eligible_appearances: pd.DataFrame,
    position_group: str,
    type_ids: frozenset[int],
    minimum_appearances: int,
) -> PositionGroupTemplateResult:
    actions = eligible_actions.loc[eligible_actions["type_id"].isin(type_ids)].copy()
    counts = (
        actions.groupby(APPEARANCE_KEYS)
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
    return build_position_group_templates(
        actions,
        appearances,
        position_group,
        minimum_player_appearances=minimum_appearances,
    )


def _action_family_sensitivity(
    result: PositionGroupTemplateResult,
    eligible_actions: pd.DataFrame,
    eligible_appearances: pd.DataFrame,
    team_name: str,
) -> pd.DataFrame:
    minimum = int(result.player_profiles["minimum_template_appearances"].iloc[0])
    family_results = {"all_direct_actions": result}
    for family, type_ids in ACTION_FAMILIES.items():
        if type_ids is not None:
            family_results[family] = _family_result(
                eligible_actions,
                eligible_appearances,
                result.position_group,
                type_ids,
                minimum,
            )
    forest = _forest_player_groups(result, team_name)
    rows = []
    for family, family_result in family_results.items():
        available_groups = _available_groups(family_result)
        available_profiles = set(
            zip(
                family_result.player_profiles["template_group"],
                family_result.player_profiles["player_id"],
            )
        )
        for player in forest.itertuples(index=False):
            if player.template_group not in available_groups:
                continue
            if (player.template_group, player.player_id) not in available_profiles:
                continue
            for layout in (POSITIONAL_LAYOUT, TRADITIONAL_LAYOUT):
                comparison = compare_player_to_template(
                    family_result.player_profiles,
                    player.player_id,
                    layout,
                    template_group=player.template_group,
                )
                rows.append(
                    {
                        "position_group": result.position_group,
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


def _quality_checks(result: PositionGroupValidationResult) -> pd.DataFrame:
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
            "Orientation alignment observations",
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


def build_position_group_validation(
    template_result: PositionGroupTemplateResult,
    eligible_actions: pd.DataFrame,
    eligible_appearances: pd.DataFrame,
    *,
    team_name: str = "Nottingham Forest",
    bootstrap_iterations: int = 1000,
    split_half_iterations: int = 500,
    random_seed: int = 42,
) -> PositionGroupValidationResult:
    """Validate one supported position group against its league templates."""

    if bootstrap_iterations < 100 or split_half_iterations < 100:
        raise ValueError("Validation iterations must each be at least 100")
    if not _available_groups(template_result):
        raise ValueError(
            f"{template_result.position_group} has no available league templates"
        )
    summary, zones = _comparison_tables(template_result, team_name)
    bootstrap, bootstrap_zones = _bootstrap_tables(
        template_result,
        team_name,
        bootstrap_iterations,
        random_seed,
    )
    validation = PositionGroupValidationResult(
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
        layout_robustness=_layout_robustness(template_result),
        action_family_sensitivity=_action_family_sensitivity(
            template_result,
            eligible_actions,
            eligible_appearances,
            team_name,
        ),
        quality_checks=pd.DataFrame(),
    )
    validation.quality_checks = _quality_checks(validation)
    failures = validation.quality_checks.loc[
        validation.quality_checks["check"].str.endswith("failures"), "value"
    ]
    if not failures.astype(int).eq(0).all():
        raise AssertionError(
            f"{validation.position_group} validation quality checks failed"
        )
    return validation


def write_position_group_validation_outputs(
    result: PositionGroupValidationResult,
    output_directory: str | Path,
) -> dict[str, Path]:
    """Write ignored validation outputs for one position group."""

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
