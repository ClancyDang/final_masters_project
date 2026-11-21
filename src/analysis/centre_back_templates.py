"""Create appearance, player and league centre-back zone profiles."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from mplsoccer import VerticalPitch


MIN_PLAYER_APPEARANCES = 5
POSITIONAL_LAYOUT = "positional_20"
TRADITIONAL_LAYOUT = "traditional_18"

APPEARANCE_KEYS = ["match_id", "team_id", "player_id"]
APPEARANCE_CONTEXT = [
    "match_id",
    "match_date",
    "match_description",
    "matchweek",
    "team_id",
    "team_name",
    "team_code",
    "home_away",
    "opponent_id",
    "opponent_name",
    "player_id",
    "player_name",
    "formation_code",
    "formation_name",
    "lineup_slot",
    "decoded_provider_position",
    "standardised_position",
    "position_group",
    "minutes_played",
    "action_count",
]


@dataclass
class CentreBackTemplateResult:
    """All tables produced by the two-stage template calculation."""

    centre_back_actions: pd.DataFrame
    appearance_profiles: pd.DataFrame
    player_profiles: pd.DataFrame
    league_templates: pd.DataFrame
    quality_checks: pd.DataFrame


def _validate_inputs(
    eligible_actions: pd.DataFrame,
    centre_back_appearances: pd.DataFrame,
) -> None:
    required_appearance_columns = set(APPEARANCE_CONTEXT)
    required_action_columns = {*APPEARANCE_KEYS, "x", "y"}
    missing_appearance = required_appearance_columns.difference(
        centre_back_appearances.columns
    )
    missing_action = required_action_columns.difference(eligible_actions.columns)
    if missing_appearance:
        raise ValueError(
            f"Centre-back appearances are missing columns: {sorted(missing_appearance)}"
        )
    if missing_action:
        raise ValueError(
            f"Eligible actions are missing columns: {sorted(missing_action)}"
        )
    if centre_back_appearances.duplicated(APPEARANCE_KEYS).any():
        raise ValueError("Centre-back appearance keys must be unique")
    if not centre_back_appearances["position_group"].eq("Centre-back").all():
        raise ValueError("Appearance input contains a non-centre-back position")
    if not centre_back_appearances["mapping_confidence"].eq("high").all():
        raise ValueError("Appearance input contains a low-confidence position label")


def _centre_back_actions(
    eligible_actions: pd.DataFrame,
    centre_back_appearances: pd.DataFrame,
) -> pd.DataFrame:
    appearance_keys = centre_back_appearances[APPEARANCE_KEYS]
    actions = eligible_actions.merge(
        appearance_keys,
        on=APPEARANCE_KEYS,
        how="inner",
        validate="many_to_one",
    )
    if not actions["x"].between(0, 100).all() or not actions["y"].between(0, 100).all():
        raise ValueError("Centre-back actions contain out-of-range coordinates")
    return actions


def _zone_assignments(
    actions: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    zoned = actions.copy()
    pitch = VerticalPitch(pitch_type="opta")

    positional_bins = pitch.bin_statistic_positional(
        zoned["x"],
        zoned["y"],
        statistic="count",
        positional="full",
        normalize=False,
    )
    if not positional_bins["inside"].all():
        raise ValueError("The positional layout rejected one or more actions")
    zoned[POSITIONAL_LAYOUT] = positional_bins["binnumber"].astype(int) + 1
    positional_zones = pd.DataFrame(
        {
            "zone_id": np.arange(1, 21),
            "zone_name": positional_bins["names"],
            "center_x": positional_bins["cx"],
            "center_y": positional_bins["cy"],
        }
    )

    length_band = np.minimum(np.floor(zoned["x"] / (100 / 6)).astype(int), 5)
    width_band = np.minimum(np.floor(zoned["y"] / (100 / 3)).astype(int), 2)
    zoned[TRADITIONAL_LAYOUT] = length_band * 3 + (2 - width_band) + 1
    traditional_zones = pd.DataFrame({"zone_id": np.arange(1, 19)})
    traditional_zones["zone_name"] = traditional_zones["zone_id"].map(
        lambda zone_id: f"traditional-{zone_id:02d}"
    )
    traditional_zones["length_band"] = (
        traditional_zones["zone_id"] - 1
    ) // 3
    traditional_zones["width_band"] = (
        traditional_zones["zone_id"] - 1
    ) % 3
    traditional_zones["center_x"] = (
        traditional_zones["length_band"] + 0.5
    ) * (100 / 6)
    traditional_zones["center_y"] = (
        2.5 - traditional_zones["width_band"]
    ) * (100 / 3)
    traditional_zones = traditional_zones.drop(
        columns=["length_band", "width_band"]
    )

    return zoned, {
        POSITIONAL_LAYOUT: positional_zones,
        TRADITIONAL_LAYOUT: traditional_zones,
    }


def _appearance_profile_for_layout(
    appearances: pd.DataFrame,
    zoned_actions: pd.DataFrame,
    layout: str,
    zones: pd.DataFrame,
) -> pd.DataFrame:
    appearance_base = appearances[APPEARANCE_CONTEXT].copy()
    complete_grid = appearance_base.merge(zones, how="cross")
    counts = (
        zoned_actions.groupby([*APPEARANCE_KEYS, layout])
        .size()
        .rename("zone_action_count")
        .reset_index()
        .rename(columns={layout: "zone_id"})
    )
    profile = complete_grid.merge(
        counts,
        on=[*APPEARANCE_KEYS, "zone_id"],
        how="left",
        validate="one_to_one",
    )
    profile["zone_action_count"] = (
        profile["zone_action_count"].fillna(0).astype(int)
    )
    profile["action_share"] = (
        profile["zone_action_count"] / profile["action_count"]
    )
    profile.insert(len(APPEARANCE_CONTEXT), "layout", layout)
    return profile


def _build_appearance_profiles(
    appearances: pd.DataFrame,
    actions: pd.DataFrame,
) -> pd.DataFrame:
    zoned_actions, zone_tables = _zone_assignments(actions)
    profiles = [
        _appearance_profile_for_layout(
            appearances,
            zoned_actions,
            layout,
            zone_table,
        )
        for layout, zone_table in zone_tables.items()
    ]
    return pd.concat(profiles, ignore_index=True)


def _percentile_25(values: pd.Series) -> float:
    return float(values.quantile(0.25))


def _percentile_75(values: pd.Series) -> float:
    return float(values.quantile(0.75))


def _build_player_profiles(
    appearance_profiles: pd.DataFrame,
    minimum_appearances: int,
) -> pd.DataFrame:
    player_summary = (
        appearance_profiles.drop_duplicates(APPEARANCE_KEYS)
        .groupby(["player_id", "player_name"], as_index=False)
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

    player_profiles = (
        appearance_profiles.groupby(
            [
                "player_id",
                "player_name",
                "layout",
                "zone_id",
                "zone_name",
                "center_x",
                "center_y",
            ],
            as_index=False,
        )["action_share"]
        .agg(
            mean_action_share="mean",
            median_action_share="median",
            std_action_share="std",
            p25_action_share=_percentile_25,
            p75_action_share=_percentile_75,
        )
    )
    return player_profiles.merge(
        player_summary,
        on=["player_id", "player_name"],
        how="left",
        validate="many_to_one",
    )


def _build_league_templates(player_profiles: pd.DataFrame) -> pd.DataFrame:
    included = player_profiles.loc[player_profiles["template_eligible"]].copy()
    templates = (
        included.groupby(
            ["layout", "zone_id", "zone_name", "center_x", "center_y"],
            as_index=False,
        )["mean_action_share"]
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
    appearances: pd.DataFrame,
    actions: pd.DataFrame,
    appearance_profiles: pd.DataFrame,
    player_profiles: pd.DataFrame,
    league_templates: pd.DataFrame,
) -> pd.DataFrame:
    appearance_share_sums = appearance_profiles.groupby(
        [*APPEARANCE_KEYS, "layout"]
    )["action_share"].sum()
    appearance_count_sums = appearance_profiles.groupby(
        [*APPEARANCE_KEYS, "layout"]
    )["zone_action_count"].sum()
    expected_counts = (
        appearances.set_index(APPEARANCE_KEYS)["action_count"]
        .reindex(appearance_count_sums.index.droplevel("layout"))
        .to_numpy()
    )
    player_share_sums = player_profiles.groupby(["player_id", "layout"])[
        "mean_action_share"
    ].sum()
    template_share_sums = league_templates.groupby("layout")[
        "mean_action_share"
    ].sum()
    qualifying_players = player_profiles.loc[
        player_profiles["template_eligible"], "player_id"
    ].nunique()

    checks = [
        ("Centre-back appearances", len(appearances)),
        ("Centre-back players", appearances["player_id"].nunique()),
        ("Centre-back direct actions", len(actions)),
        ("Appearance profile rows", len(appearance_profiles)),
        ("Player profile rows", len(player_profiles)),
        ("Players meeting template threshold", qualifying_players),
        ("League template rows", len(league_templates)),
        ("Duplicate appearance profile keys", int(appearance_profiles.duplicated([*APPEARANCE_KEYS, "layout", "zone_id"]).sum())),
        ("Duplicate player profile keys", int(player_profiles.duplicated(["player_id", "layout", "zone_id"]).sum())),
        ("Appearance share-sum failures", int((~np.isclose(appearance_share_sums, 1)).sum())),
        ("Appearance action-count failures", int((appearance_count_sums.to_numpy() != expected_counts).sum())),
        ("Player share-sum failures", int((~np.isclose(player_share_sums, 1)).sum())),
        ("Template share-sum failures", int((~np.isclose(template_share_sums, 1)).sum())),
    ]
    return pd.DataFrame(checks, columns=["check", "value"])


def _validate_result(result: CentreBackTemplateResult) -> None:
    checks = result.quality_checks.set_index("check")["value"]
    for check in (
        "Duplicate appearance profile keys",
        "Duplicate player profile keys",
        "Appearance share-sum failures",
        "Appearance action-count failures",
        "Player share-sum failures",
        "Template share-sum failures",
    ):
        if checks[check] != 0:
            raise AssertionError(f"Template quality check failed: {check} = {checks[check]}")
    expected_zones = {POSITIONAL_LAYOUT: 20, TRADITIONAL_LAYOUT: 18}
    observed_zones = result.league_templates.groupby("layout")["zone_id"].nunique()
    if observed_zones.to_dict() != expected_zones:
        raise AssertionError(
            f"Unexpected league-template zone coverage: {observed_zones.to_dict()}"
        )
    player_counts = result.league_templates.groupby("layout")["player_count"].nunique()
    if not player_counts.eq(1).all():
        raise AssertionError("Every zone must use the same number of player profiles")


def build_centre_back_templates(
    eligible_actions: pd.DataFrame,
    centre_back_appearances: pd.DataFrame,
    minimum_player_appearances: int = MIN_PLAYER_APPEARANCES,
) -> CentreBackTemplateResult:
    """Build two-stage, equal-weighted centre-back zone templates."""

    if minimum_player_appearances < 1:
        raise ValueError("minimum_player_appearances must be at least one")
    _validate_inputs(eligible_actions, centre_back_appearances)
    actions = _centre_back_actions(eligible_actions, centre_back_appearances)
    appearance_profiles = _build_appearance_profiles(
        centre_back_appearances,
        actions,
    )
    player_profiles = _build_player_profiles(
        appearance_profiles,
        minimum_player_appearances,
    )
    league_templates = _build_league_templates(player_profiles)
    quality_checks = _build_quality_checks(
        centre_back_appearances,
        actions,
        appearance_profiles,
        player_profiles,
        league_templates,
    )
    result = CentreBackTemplateResult(
        centre_back_actions=actions,
        appearance_profiles=appearance_profiles,
        player_profiles=player_profiles,
        league_templates=league_templates,
        quality_checks=quality_checks,
    )
    _validate_result(result)
    return result


def write_centre_back_template_outputs(
    result: CentreBackTemplateResult,
    output_directory: str | Path,
) -> dict[str, Path]:
    """Write ignored centre-back profile and template outputs."""

    output_directory = Path(output_directory).resolve()
    output_directory.mkdir(parents=True, exist_ok=True)
    paths = {
        "appearance_profiles": output_directory
        / "centre_back_appearance_zone_profiles.parquet",
        "player_profiles": output_directory
        / "centre_back_player_zone_profiles.parquet",
        "league_templates": output_directory
        / "centre_back_league_templates.parquet",
        "quality_checks": output_directory
        / "centre_back_template_quality_checks.csv",
    }
    result.appearance_profiles.to_parquet(paths["appearance_profiles"], index=False)
    result.player_profiles.to_parquet(paths["player_profiles"], index=False)
    result.league_templates.to_parquet(paths["league_templates"], index=False)
    result.quality_checks.to_csv(paths["quality_checks"], index=False)
    return paths
