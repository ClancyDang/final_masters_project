"""Build role-specific and overarching templates for remaining positions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .centre_back_templates import (
    APPEARANCE_CONTEXT,
    APPEARANCE_KEYS,
    MIN_PLAYER_APPEARANCES,
    POSITIONAL_LAYOUT,
    TRADITIONAL_LAYOUT,
    _build_appearance_profiles,
    _percentile_25,
    _percentile_75,
)


POSITION_GROUP_ROLES: dict[str, tuple[str, ...]] = {
    "Goalkeeper": ("Goalkeeper",),
    "Defensive midfield": (
        "Defensive midfielder",
        "Left defensive midfielder",
        "Right defensive midfielder",
    ),
    "Central midfield": (
        "Central midfielder",
        "Left central midfielder",
        "Right central midfielder",
    ),
    "Attacking midfield": (
        "Attacking midfielder",
        "Left attacking midfielder",
        "Right attacking midfielder",
    ),
    "Wide midfield": ("Left midfielder", "Right midfielder"),
    "Winger": ("Left winger", "Right winger"),
    "Forward": ("Centre-forward", "Left forward", "Right forward"),
}


@dataclass
class PositionGroupTemplateResult:
    """Template tables for one provider-mapped position group."""

    position_group: str
    role_actions: pd.DataFrame
    appearance_profiles: pd.DataFrame
    player_profiles: pd.DataFrame
    league_templates: pd.DataFrame
    template_coverage: pd.DataFrame
    quality_checks: pd.DataFrame


def _validate_inputs(
    eligible_actions: pd.DataFrame,
    eligible_appearances: pd.DataFrame,
    position_group: str,
) -> pd.DataFrame:
    if position_group not in POSITION_GROUP_ROLES:
        raise ValueError(
            f"Unsupported position group {position_group!r}; expected one of "
            f"{sorted(POSITION_GROUP_ROLES)}"
        )
    required_appearances = {*APPEARANCE_CONTEXT, "mapping_confidence"}
    required_actions = {*APPEARANCE_KEYS, "x", "y"}
    missing_appearances = required_appearances.difference(
        eligible_appearances.columns
    )
    missing_actions = required_actions.difference(eligible_actions.columns)
    if missing_appearances:
        raise ValueError(
            "Eligible appearances are missing columns: "
            f"{sorted(missing_appearances)}"
        )
    if missing_actions:
        raise ValueError(
            f"Eligible actions are missing columns: {sorted(missing_actions)}"
        )
    roles = POSITION_GROUP_ROLES[position_group]
    appearances = eligible_appearances.loc[
        eligible_appearances["position_group"].eq(position_group)
        & eligible_appearances["mapping_confidence"].eq("high")
        & eligible_appearances["standardised_position"].isin(roles)
    ].copy()
    if appearances.empty:
        raise ValueError(f"No high-confidence {position_group} appearances found")
    if appearances.duplicated(APPEARANCE_KEYS).any():
        raise ValueError(f"{position_group} appearance keys must be unique")
    unexpected = set(appearances["standardised_position"]) - set(roles)
    if unexpected:
        raise ValueError(f"Unexpected roles found: {sorted(unexpected)}")
    return appearances


def _role_actions(
    eligible_actions: pd.DataFrame,
    appearances: pd.DataFrame,
) -> pd.DataFrame:
    context = appearances[
        [*APPEARANCE_KEYS, "standardised_position"]
    ].rename(columns={"standardised_position": "role_standardised_position"})
    actions = eligible_actions.merge(
        context,
        on=APPEARANCE_KEYS,
        how="inner",
        validate="many_to_one",
    )
    if not actions["x"].between(0, 100).all() or not actions["y"].between(
        0, 100
    ).all():
        raise ValueError("Position-group actions contain out-of-range coordinates")
    actions["original_y"] = actions["y"].astype(float)
    actions["was_mirrored"] = actions["role_standardised_position"].str.startswith(
        "Right"
    )
    actions["role_normalised_y"] = np.where(
        actions["was_mirrored"],
        100 - actions["original_y"],
        actions["original_y"],
    )
    return actions


def _profile_group(
    appearances: pd.DataFrame,
    actions: pd.DataFrame,
    template_group: str,
    template_scope: str,
) -> pd.DataFrame:
    profiles = _build_appearance_profiles(appearances, actions)
    profiles.insert(
        profiles.columns.get_loc("layout"), "template_group", template_group
    )
    profiles.insert(
        profiles.columns.get_loc("layout") + 1,
        "template_scope",
        template_scope,
    )
    return profiles


def _appearance_profiles(
    appearances: pd.DataFrame,
    actions: pd.DataFrame,
    position_group: str,
) -> pd.DataFrame:
    roles = POSITION_GROUP_ROLES[position_group]
    if len(roles) == 1 and roles[0] == position_group:
        return _profile_group(
            appearances,
            actions,
            position_group,
            "position_group",
        )

    profiles = []
    for role in roles:
        role_appearances = appearances.loc[
            appearances["standardised_position"].eq(role)
        ]
        if role_appearances.empty:
            continue
        role_actions = actions.merge(
            role_appearances[APPEARANCE_KEYS],
            on=APPEARANCE_KEYS,
            how="inner",
            validate="many_to_one",
        )
        profiles.append(
            _profile_group(
                role_appearances,
                role_actions,
                role,
                "role_specific",
            )
        )

    normalised_actions = actions.copy()
    normalised_actions["y"] = normalised_actions["role_normalised_y"]
    profiles.append(
        _profile_group(
            appearances,
            normalised_actions,
            position_group,
            "position_group",
        )
    )
    return pd.concat(profiles, ignore_index=True)


def _player_profiles(
    appearance_profiles: pd.DataFrame,
    minimum_appearances: int,
) -> pd.DataFrame:
    summary_keys = ["template_group", "template_scope", "player_id", "player_name"]
    summary = (
        appearance_profiles.drop_duplicates(
            ["template_group", *APPEARANCE_KEYS]
        )
        .groupby(summary_keys, as_index=False)
        .agg(
            eligible_appearances=("match_id", "nunique"),
            total_actions=("action_count", "sum"),
            mean_actions_per_appearance=("action_count", "mean"),
            total_minutes=("minutes_played", "sum"),
            teams=("team_name", lambda values: " / ".join(sorted(set(values)))),
        )
    )
    summary["template_eligible"] = summary["eligible_appearances"].ge(
        minimum_appearances
    )
    summary["minimum_template_appearances"] = minimum_appearances
    group_keys = [
        *summary_keys,
        "layout",
        "zone_id",
        "zone_name",
        "center_x",
        "center_y",
    ]
    profiles = (
        appearance_profiles.groupby(group_keys, as_index=False)["action_share"]
        .agg(
            mean_action_share="mean",
            median_action_share="median",
            std_action_share="std",
            p25_action_share=_percentile_25,
            p75_action_share=_percentile_75,
        )
    )
    return profiles.merge(
        summary,
        on=summary_keys,
        how="left",
        validate="many_to_one",
    )


def _league_templates(
    player_profiles: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    profile_groups = player_profiles[
        ["template_group", "template_scope"]
    ].drop_duplicates()
    player_counts = (
        player_profiles[
            [
                "template_group",
                "template_scope",
                "player_id",
                "template_eligible",
            ]
        ]
        .drop_duplicates()
        .groupby(["template_group", "template_scope"], as_index=False)
        .agg(
            player_profiles=("player_id", "nunique"),
            qualifying_players=("template_eligible", "sum"),
        )
    )
    coverage = profile_groups.merge(
        player_counts,
        on=["template_group", "template_scope"],
        validate="one_to_one",
    )
    coverage["template_available"] = coverage["qualifying_players"].ge(2)

    available_groups = set(
        coverage.loc[coverage["template_available"], "template_group"]
    )
    included = player_profiles.loc[
        player_profiles["template_eligible"]
        & player_profiles["template_group"].isin(available_groups)
    ].copy()
    group_keys = [
        "template_group",
        "template_scope",
        "layout",
        "zone_id",
        "zone_name",
        "center_x",
        "center_y",
    ]
    templates = (
        included.groupby(group_keys, as_index=False)["mean_action_share"]
        .agg(
            mean_action_share="mean",
            median_player_share="median",
            std_player_share="std",
            p25_player_share=_percentile_25,
            p75_player_share=_percentile_75,
            player_count="count",
        )
    )
    templates["weighting_method"] = "equal_player_weight"
    templates["player_profile_method"] = "equal_appearance_weight"
    templates["minimum_player_appearances"] = int(
        player_profiles["minimum_template_appearances"].iloc[0]
    )
    return templates, coverage


def _quality_checks(
    position_group: str,
    appearances: pd.DataFrame,
    actions: pd.DataFrame,
    appearance_profiles: pd.DataFrame,
    player_profiles: pd.DataFrame,
    league_templates: pd.DataFrame,
    template_coverage: pd.DataFrame,
) -> pd.DataFrame:
    appearance_keys = ["template_group", *APPEARANCE_KEYS, "layout"]
    share_sums = appearance_profiles.groupby(appearance_keys)["action_share"].sum()
    count_sums = appearance_profiles.groupby(appearance_keys)[
        "zone_action_count"
    ].sum()
    expected_counts = (
        appearance_profiles.drop_duplicates(appearance_keys)
        .set_index(appearance_keys)["action_count"]
        .reindex(count_sums.index)
    )
    player_sums = player_profiles.groupby(
        ["template_group", "player_id", "layout"]
    )["mean_action_share"].sum()
    template_sums = league_templates.groupby(
        ["template_group", "layout"]
    )["mean_action_share"].sum()
    mirrored = actions.loc[actions["was_mirrored"]]
    mirror_failures = int(
        (~np.isclose(mirrored["role_normalised_y"], 100 - mirrored["original_y"])).sum()
    )
    checks = [
        ("Position group", position_group),
        ("Eligible appearances", len(appearances)),
        ("Players", appearances["player_id"].nunique()),
        ("Direct actions", len(actions)),
        ("Template groups", len(template_coverage)),
        (
            "Unavailable template groups",
            int((~template_coverage["template_available"]).sum()),
        ),
        (
            "Duplicate appearance profile keys",
            int(appearance_profiles.duplicated([*appearance_keys, "zone_id"]).sum()),
        ),
        (
            "Duplicate player profile keys",
            int(
                player_profiles.duplicated(
                    ["template_group", "player_id", "layout", "zone_id"]
                ).sum()
            ),
        ),
        ("Appearance share-sum failures", int((~np.isclose(share_sums, 1)).sum())),
        (
            "Appearance action-count failures",
            int((count_sums != expected_counts).sum()),
        ),
        ("Player share-sum failures", int((~np.isclose(player_sums, 1)).sum())),
        (
            "Template share-sum failures",
            int((~np.isclose(template_sums, 1)).sum()),
        ),
        ("Mirror transform failures", mirror_failures),
    ]
    return pd.DataFrame(checks, columns=["check", "value"])


def _validate_result(result: PositionGroupTemplateResult) -> None:
    failures = result.quality_checks.loc[
        result.quality_checks["check"].str.endswith("failures"), "value"
    ]
    if not failures.astype(int).eq(0).all():
        raise AssertionError(
            f"{result.position_group} template quality checks failed"
        )
    available = set(
        result.template_coverage.loc[
            result.template_coverage["template_available"], "template_group"
        ]
    )
    observed = set(result.league_templates["template_group"])
    if observed != available:
        raise AssertionError("League template availability does not match coverage")
    expected_zones = {POSITIONAL_LAYOUT: 20, TRADITIONAL_LAYOUT: 18}
    zone_counts = result.league_templates.groupby(
        ["template_group", "layout"]
    )["zone_id"].nunique()
    for template_group in observed:
        if zone_counts.loc[template_group].to_dict() != expected_zones:
            raise AssertionError(
                f"Unexpected zone coverage for {template_group}"
            )


def build_position_group_templates(
    eligible_actions: pd.DataFrame,
    eligible_appearances: pd.DataFrame,
    position_group: str,
    minimum_player_appearances: int = MIN_PLAYER_APPEARANCES,
) -> PositionGroupTemplateResult:
    """Build role-specific and overarching templates for one position group."""

    if minimum_player_appearances < 1:
        raise ValueError("minimum_player_appearances must be at least one")
    appearances = _validate_inputs(
        eligible_actions,
        eligible_appearances,
        position_group,
    )
    actions = _role_actions(eligible_actions, appearances)
    appearance_profiles = _appearance_profiles(
        appearances,
        actions,
        position_group,
    )
    player_profiles = _player_profiles(
        appearance_profiles,
        minimum_player_appearances,
    )
    league_templates, template_coverage = _league_templates(player_profiles)
    result = PositionGroupTemplateResult(
        position_group=position_group,
        role_actions=actions,
        appearance_profiles=appearance_profiles,
        player_profiles=player_profiles,
        league_templates=league_templates,
        template_coverage=template_coverage,
        quality_checks=pd.DataFrame(),
    )
    result.quality_checks = _quality_checks(
        position_group,
        appearances,
        actions,
        appearance_profiles,
        player_profiles,
        league_templates,
        template_coverage,
    )
    _validate_result(result)
    return result


def write_position_group_template_outputs(
    result: PositionGroupTemplateResult,
    output_directory: str | Path,
) -> dict[str, Path]:
    """Write ignored outputs for one position group."""

    output_directory = Path(output_directory).resolve()
    output_directory.mkdir(parents=True, exist_ok=True)
    prefix = result.position_group.lower().replace("-", "_").replace(" ", "_")
    paths = {
        "role_actions": output_directory / f"{prefix}_role_actions.parquet",
        "appearance_profiles": output_directory
        / f"{prefix}_appearance_zone_profiles.parquet",
        "player_profiles": output_directory
        / f"{prefix}_player_zone_profiles.parquet",
        "league_templates": output_directory / f"{prefix}_league_templates.parquet",
        "template_coverage": output_directory / f"{prefix}_template_coverage.csv",
        "quality_checks": output_directory / f"{prefix}_template_quality_checks.csv",
    }
    result.role_actions.to_parquet(paths["role_actions"], index=False)
    result.appearance_profiles.to_parquet(paths["appearance_profiles"], index=False)
    result.player_profiles.to_parquet(paths["player_profiles"], index=False)
    result.league_templates.to_parquet(paths["league_templates"], index=False)
    result.template_coverage.to_csv(paths["template_coverage"], index=False)
    result.quality_checks.to_csv(paths["quality_checks"], index=False)
    return paths
