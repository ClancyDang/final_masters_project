"""Build side-specific and role-normalised full-back and wing-back templates."""

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


SUPPORTED_GROUPS = {
    "Full-back": ("Left full-back", "Right full-back"),
    "Wing-back": ("Left wing-back", "Right wing-back"),
}


@dataclass
class WideDefenderTemplateResult:
    """Tables produced for one full-back or wing-back position group."""

    position_group: str
    role_actions: pd.DataFrame
    appearance_profiles: pd.DataFrame
    player_profiles: pd.DataFrame
    league_templates: pd.DataFrame
    quality_checks: pd.DataFrame


def _validate_inputs(
    eligible_actions: pd.DataFrame,
    eligible_appearances: pd.DataFrame,
    position_group: str,
) -> pd.DataFrame:
    if position_group not in SUPPORTED_GROUPS:
        raise ValueError(
            f"Unsupported position group {position_group!r}; "
            f"expected one of {sorted(SUPPORTED_GROUPS)}"
        )
    required_appearance_columns = {
        *APPEARANCE_CONTEXT,
        "mapping_confidence",
    }
    required_action_columns = {*APPEARANCE_KEYS, "x", "y"}
    missing_appearances = required_appearance_columns.difference(
        eligible_appearances.columns
    )
    missing_actions = required_action_columns.difference(eligible_actions.columns)
    if missing_appearances:
        raise ValueError(
            "Eligible appearances are missing columns: "
            f"{sorted(missing_appearances)}"
        )
    if missing_actions:
        raise ValueError(
            f"Eligible actions are missing columns: {sorted(missing_actions)}"
        )

    left_role, right_role = SUPPORTED_GROUPS[position_group]
    role_appearances = eligible_appearances.loc[
        eligible_appearances["position_group"].eq(position_group)
        & eligible_appearances["mapping_confidence"].eq("high")
        & eligible_appearances["standardised_position"].isin(
            [left_role, right_role]
        )
    ].copy()
    if role_appearances.empty:
        raise ValueError(f"No high-confidence {position_group} appearances found")
    if role_appearances.duplicated(APPEARANCE_KEYS).any():
        raise ValueError(f"{position_group} appearance keys must be unique")
    observed_roles = set(role_appearances["standardised_position"])
    expected_roles = {left_role, right_role}
    if observed_roles != expected_roles:
        raise ValueError(
            f"Expected both {position_group} sides; found {sorted(observed_roles)}"
        )
    return role_appearances


def _role_actions(
    eligible_actions: pd.DataFrame,
    role_appearances: pd.DataFrame,
    right_role: str,
) -> pd.DataFrame:
    action_context = role_appearances[
        [*APPEARANCE_KEYS, "standardised_position"]
    ].rename(columns={"standardised_position": "role_standardised_position"})
    actions = eligible_actions.merge(
        action_context,
        on=APPEARANCE_KEYS,
        how="inner",
        validate="many_to_one",
    )
    if not actions["x"].between(0, 100).all() or not actions["y"].between(
        0, 100
    ).all():
        raise ValueError("Wide-defender actions contain out-of-range coordinates")
    actions["original_y"] = actions["y"].astype(float)
    actions["was_mirrored"] = actions["role_standardised_position"].eq(right_role)
    actions["role_normalised_y"] = np.where(
        actions["was_mirrored"],
        100 - actions["original_y"],
        actions["original_y"],
    )
    return actions


def _profiles_for_group(
    appearances: pd.DataFrame,
    actions: pd.DataFrame,
    *,
    template_group: str,
    template_scope: str,
) -> pd.DataFrame:
    profiles = _build_appearance_profiles(appearances, actions)
    profiles.insert(
        profiles.columns.get_loc("layout"),
        "template_group",
        template_group,
    )
    profiles.insert(
        profiles.columns.get_loc("layout") + 1,
        "template_scope",
        template_scope,
    )
    return profiles


def _build_all_appearance_profiles(
    role_appearances: pd.DataFrame,
    role_actions: pd.DataFrame,
    position_group: str,
) -> pd.DataFrame:
    left_role, right_role = SUPPORTED_GROUPS[position_group]
    profiles = []
    for side_role in (left_role, right_role):
        side_appearances = role_appearances.loc[
            role_appearances["standardised_position"].eq(side_role)
        ]
        side_actions = role_actions.merge(
            side_appearances[APPEARANCE_KEYS],
            on=APPEARANCE_KEYS,
            how="inner",
            validate="many_to_one",
        )
        profiles.append(
            _profiles_for_group(
                side_appearances,
                side_actions,
                template_group=side_role,
                template_scope="side_specific",
            )
        )

    normalised_actions = role_actions.copy()
    normalised_actions["y"] = normalised_actions["role_normalised_y"]
    profiles.append(
        _profiles_for_group(
            role_appearances,
            normalised_actions,
            template_group=position_group,
            template_scope="role_normalised",
        )
    )
    return pd.concat(profiles, ignore_index=True)


def _build_player_profiles(
    appearance_profiles: pd.DataFrame,
    minimum_appearances: int,
) -> pd.DataFrame:
    summary_keys = ["template_group", "template_scope", "player_id", "player_name"]
    player_summary = (
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
    player_summary["template_eligible"] = player_summary[
        "eligible_appearances"
    ].ge(minimum_appearances)
    player_summary["minimum_template_appearances"] = minimum_appearances

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
        player_summary,
        on=summary_keys,
        how="left",
        validate="many_to_one",
    )


def _build_league_templates(player_profiles: pd.DataFrame) -> pd.DataFrame:
    included = player_profiles.loc[player_profiles["template_eligible"]].copy()
    missing_groups = set(player_profiles["template_group"]) - set(
        included["template_group"]
    )
    if missing_groups:
        raise ValueError(
            "No players meet the template threshold for: "
            f"{sorted(missing_groups)}"
        )
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
        included["minimum_template_appearances"].iloc[0]
    )
    return templates


def _build_quality_checks(
    position_group: str,
    role_appearances: pd.DataFrame,
    role_actions: pd.DataFrame,
    appearance_profiles: pd.DataFrame,
    player_profiles: pd.DataFrame,
    league_templates: pd.DataFrame,
) -> pd.DataFrame:
    appearance_group_keys = ["template_group", *APPEARANCE_KEYS, "layout"]
    appearance_share_sums = appearance_profiles.groupby(appearance_group_keys)[
        "action_share"
    ].sum()
    appearance_count_sums = appearance_profiles.groupby(appearance_group_keys)[
        "zone_action_count"
    ].sum()
    expected_counts = (
        appearance_profiles.drop_duplicates(appearance_group_keys)
        .set_index(appearance_group_keys)["action_count"]
        .reindex(appearance_count_sums.index)
    )
    player_share_sums = player_profiles.groupby(
        ["template_group", "player_id", "layout"]
    )["mean_action_share"].sum()
    template_share_sums = league_templates.groupby(
        ["template_group", "layout"]
    )["mean_action_share"].sum()
    mirrored = role_actions.loc[role_actions["was_mirrored"]]
    mirror_failures = int(
        (~np.isclose(mirrored["role_normalised_y"], 100 - mirrored["original_y"])).sum()
    )
    expected_profile_appearances = len(role_appearances) * 2
    observed_profile_appearances = len(
        appearance_profiles[
            ["template_group", *APPEARANCE_KEYS]
        ].drop_duplicates()
    )
    checks = [
        ("Position group", position_group),
        ("Eligible appearances", len(role_appearances)),
        ("Players", role_appearances["player_id"].nunique()),
        ("Direct actions", len(role_actions)),
        ("Template groups", appearance_profiles["template_group"].nunique()),
        (
            "Players meeting threshold across groups",
            player_profiles.loc[player_profiles["template_eligible"]]
            [["template_group", "player_id"]]
            .drop_duplicates()
            .shape[0],
        ),
        (
            "Appearance coverage failures",
            abs(observed_profile_appearances - expected_profile_appearances),
        ),
        (
            "Duplicate appearance profile keys",
            int(
                appearance_profiles.duplicated(
                    [*appearance_group_keys, "zone_id"]
                ).sum()
            ),
        ),
        (
            "Duplicate player profile keys",
            int(
                player_profiles.duplicated(
                    ["template_group", "player_id", "layout", "zone_id"]
                ).sum()
            ),
        ),
        (
            "Appearance share-sum failures",
            int((~np.isclose(appearance_share_sums, 1)).sum()),
        ),
        (
            "Appearance action-count failures",
            int((appearance_count_sums != expected_counts).sum()),
        ),
        (
            "Player share-sum failures",
            int((~np.isclose(player_share_sums, 1)).sum()),
        ),
        (
            "Template share-sum failures",
            int((~np.isclose(template_share_sums, 1)).sum()),
        ),
        ("Mirror transform failures", mirror_failures),
    ]
    return pd.DataFrame(checks, columns=["check", "value"])


def _validate_result(result: WideDefenderTemplateResult) -> None:
    failures = result.quality_checks.loc[
        result.quality_checks["check"].str.endswith("failures"), "value"
    ]
    if not failures.astype(int).eq(0).all():
        raise AssertionError(
            f"{result.position_group} template quality checks failed"
        )
    expected_groups = {
        *SUPPORTED_GROUPS[result.position_group],
        result.position_group,
    }
    if set(result.league_templates["template_group"]) != expected_groups:
        raise AssertionError("Unexpected template-group coverage")
    expected_zones = {POSITIONAL_LAYOUT: 20, TRADITIONAL_LAYOUT: 18}
    observed = result.league_templates.groupby(
        ["template_group", "layout"]
    )["zone_id"].nunique()
    for template_group in expected_groups:
        if observed.loc[template_group].to_dict() != expected_zones:
            raise AssertionError(
                f"Unexpected zone coverage for {template_group}: "
                f"{observed.loc[template_group].to_dict()}"
            )


def build_wide_defender_templates(
    eligible_actions: pd.DataFrame,
    eligible_appearances: pd.DataFrame,
    position_group: str,
    minimum_player_appearances: int = MIN_PLAYER_APPEARANCES,
) -> WideDefenderTemplateResult:
    """Build side-specific and mirrored overarching positional templates."""

    if minimum_player_appearances < 1:
        raise ValueError("minimum_player_appearances must be at least one")
    role_appearances = _validate_inputs(
        eligible_actions,
        eligible_appearances,
        position_group,
    )
    _, right_role = SUPPORTED_GROUPS[position_group]
    role_actions = _role_actions(
        eligible_actions,
        role_appearances,
        right_role,
    )
    appearance_profiles = _build_all_appearance_profiles(
        role_appearances,
        role_actions,
        position_group,
    )
    player_profiles = _build_player_profiles(
        appearance_profiles,
        minimum_player_appearances,
    )
    league_templates = _build_league_templates(player_profiles)
    result = WideDefenderTemplateResult(
        position_group=position_group,
        role_actions=role_actions,
        appearance_profiles=appearance_profiles,
        player_profiles=player_profiles,
        league_templates=league_templates,
        quality_checks=pd.DataFrame(),
    )
    result.quality_checks = _build_quality_checks(
        position_group,
        role_appearances,
        role_actions,
        appearance_profiles,
        player_profiles,
        league_templates,
    )
    _validate_result(result)
    return result


def write_wide_defender_template_outputs(
    result: WideDefenderTemplateResult,
    output_directory: str | Path,
) -> dict[str, Path]:
    """Write ignored full-back or wing-back template outputs."""

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
        "quality_checks": output_directory / f"{prefix}_template_quality_checks.csv",
    }
    result.role_actions.to_parquet(paths["role_actions"], index=False)
    result.appearance_profiles.to_parquet(paths["appearance_profiles"], index=False)
    result.player_profiles.to_parquet(paths["player_profiles"], index=False)
    result.league_templates.to_parquet(paths["league_templates"], index=False)
    result.quality_checks.to_csv(paths["quality_checks"], index=False)
    return paths
