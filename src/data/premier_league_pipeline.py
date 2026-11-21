"""Build league-wide appearance and positional-action tables.

The first league-wide version deliberately classifies the starting role recorded
by the provider. Substitute slot 0 and later formation changes remain visible as
unresolved cases and do not enter the high-confidence centre-back population.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.positions import add_position_mapping


MIN_ELIGIBLE_MINUTES = 60.0

# This is the same direct-action taxonomy used by the Forest prototype.
DIRECT_ACTION_TYPE_NAMES: dict[int, str] = {
    1: "Pass",
    2: "Offside Pass",
    3: "Take On",
    4: "Foul",
    7: "Tackle",
    8: "Interception",
    10: "Save",
    12: "Clearance",
    44: "Aerial",
    45: "Challenge",
    49: "Ball Recovery",
    50: "Dispossessed",
    56: "Shield Ball",
    61: "Ball Touch",
    74: "Blocked Pass",
    83: "Attempted Tackle",
}


@dataclass
class LeaguePipelineResult:
    """All useful intermediate and output tables from one league build."""

    fixture_coverage: pd.DataFrame
    squad_players: pd.DataFrame
    lineup_slots: pd.DataFrame
    appearance_samples: pd.DataFrame
    eligible_appearances: pd.DataFrame
    eligible_actions: pd.DataFrame
    centre_back_appearances: pd.DataFrame
    quality_checks: pd.DataFrame


def qualifiers_to_dict(qualifiers: list[dict[str, Any]] | None) -> dict[int, Any]:
    """Convert a provider qualifier list to an integer-keyed dictionary."""

    return {
        int(item["qualifierId"]): item.get("value", True)
        for item in (qualifiers or [])
    }


def split_qualifier_values(value: Any) -> list[str]:
    """Split the comma-separated parallel arrays in a team-setup event."""

    if value is None or value is True:
        return []
    return [item.strip() for item in str(value).split(",")]


def _nullable_int(value: Any) -> Any:
    if value is None or value is True or value == "":
        return pd.NA
    try:
        return int(value)
    except (TypeError, ValueError):
        return pd.NA


def _load_squad_players(season_root: Path) -> pd.DataFrame:
    squad_path = season_root / "jsons" / "squads.json"
    with squad_path.open(encoding="utf-8") as squad_file:
        payload = json.load(squad_file)

    rows: list[dict[str, Any]] = []
    for squad in payload["squad"]:
        team_id = squad["contestantId"]
        team_name = squad["contestantName"]
        team_code = squad.get("contestantCode")
        for person in squad.get("person", []):
            if person.get("type") != "player":
                continue
            rows.append(
                {
                    "team_id": team_id,
                    "team_name": team_name,
                    "team_code": team_code,
                    "player_id": person["id"],
                    "player_name": (
                        person.get("knownName")
                        or person.get("matchName")
                        or person.get("lastName")
                    ),
                    "squad_position": person.get("position"),
                    "squad_position_side": person.get("positionSide"),
                    "shirt_number_squad": person.get("shirtNumber"),
                    "active": person.get("active"),
                }
            )

    squad_players = pd.DataFrame(rows)
    duplicate_keys = squad_players.duplicated(["team_id", "player_id"]).sum()
    if duplicate_keys:
        raise ValueError(f"Squad data contains {duplicate_keys} duplicate team/player rows")
    return squad_players


def _match_file_index(match_directory: Path) -> dict[str, Path]:
    paths_by_id: dict[str, Path] = {}
    for path in sorted(match_directory.glob("*.json")):
        match_id = path.stem.rsplit("_", 1)[-1]
        if match_id in paths_by_id:
            raise ValueError(f"Duplicate event payloads found for match {match_id}")
        paths_by_id[match_id] = path
    return paths_by_id


def _team_context(
    contestants: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    context: dict[str, dict[str, Any]] = {}
    for contestant in contestants:
        opponent = next(
            item for item in contestants if item["id"] != contestant["id"]
        )
        context[contestant["id"]] = {
            "team_name_match": contestant.get("name"),
            "team_code_match": contestant.get("code"),
            "home_away": contestant.get("position"),
            "opponent_id": opponent["id"],
            "opponent_name": opponent.get("name"),
        }
    return context


def _read_provider_rows(
    fixture_coverage: pd.DataFrame,
    squad_players: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    squad_lookup = squad_players.set_index(["team_id", "player_id"])
    fallback_name = (
        squad_players.drop_duplicates("player_id").set_index("player_id")["player_name"]
    )
    fallback_position = (
        squad_players.drop_duplicates("player_id")
        .set_index("player_id")["squad_position"]
    )

    lineup_rows: list[dict[str, Any]] = []
    timeline_rows: list[dict[str, Any]] = []
    action_rows: list[dict[str, Any]] = []
    match_rows: list[dict[str, Any]] = []

    available_fixtures = fixture_coverage.loc[
        fixture_coverage["event_payload_available"]
    ]
    for fixture in available_fixtures.itertuples(index=False):
        path = Path(fixture.event_file)
        with path.open(encoding="utf-8") as match_file:
            match = json.load(match_file)

        match_info = match["matchInfo"]
        match_id = match_info["id"]
        match_date = pd.to_datetime(
            match_info.get("localDate", match_info.get("date")),
            errors="coerce",
        )
        match_description = match_info.get("description")
        contestants = match_info["contestant"]
        context_by_team = _team_context(contestants)
        match_details = match["liveData"]["matchDetails"]
        match_end_minute = (
            float(match_details.get("matchLengthMin", 0))
            + float(match_details.get("matchLengthSec", 0)) / 60
        )
        match_rows.append(
            {
                "match_id": match_id,
                "match_date": match_date,
                "match_description": match_description,
                "matchweek": match_info.get("week"),
                "match_end_minute": match_end_minute,
            }
        )

        for event in match["liveData"].get("event", []):
            type_id = _nullable_int(event.get("typeId"))
            team_id = event.get("contestantId")
            player_id = event.get("playerId")
            qualifier_map = qualifiers_to_dict(event.get("qualifier"))
            match_minute = (
                pd.to_numeric(event.get("timeMin"), errors="coerce")
                + pd.to_numeric(event.get("timeSec"), errors="coerce") / 60
            )

            if type_id == 34:
                player_ids = split_qualifier_values(qualifier_map.get(30))
                broad_positions = split_qualifier_values(qualifier_map.get(44))
                shirt_numbers = split_qualifier_values(qualifier_map.get(59))
                lineup_slots = split_qualifier_values(qualifier_map.get(131))
                formation_code = _nullable_int(qualifier_map.get(130))
                team_context = context_by_team[team_id]

                for index, setup_player_id in enumerate(player_ids):
                    key = (team_id, setup_player_id)
                    if key in squad_lookup.index:
                        squad_row = squad_lookup.loc[key]
                        player_name = squad_row["player_name"]
                        squad_position = squad_row["squad_position"]
                    else:
                        player_name = fallback_name.get(setup_player_id)
                        squad_position = fallback_position.get(setup_player_id)

                    lineup_slot = _nullable_int(
                        lineup_slots[index] if index < len(lineup_slots) else None
                    )
                    lineup_rows.append(
                        {
                            "match_id": match_id,
                            "match_date": match_date,
                            "match_description": match_description,
                            "matchweek": match_info.get("week"),
                            "team_id": team_id,
                            "team_name": team_context["team_name_match"],
                            "team_code": team_context["team_code_match"],
                            "home_away": team_context["home_away"],
                            "opponent_id": team_context["opponent_id"],
                            "opponent_name": team_context["opponent_name"],
                            "formation_code": formation_code,
                            "player_id": setup_player_id,
                            "player_name": player_name,
                            "broad_position_code": _nullable_int(
                                broad_positions[index]
                                if index < len(broad_positions)
                                else None
                            ),
                            "squad_position": squad_position,
                            "shirt_number": _nullable_int(
                                shirt_numbers[index]
                                if index < len(shirt_numbers)
                                else None
                            ),
                            "lineup_slot": lineup_slot,
                            "is_starter": bool(pd.notna(lineup_slot) and lineup_slot != 0),
                        }
                    )

            if type_id in {17, 18, 19} and player_id is not None:
                timeline_rows.append(
                    {
                        "match_id": match_id,
                        "team_id": team_id,
                        "player_id": player_id,
                        "type_id": type_id,
                        "match_minute": float(match_minute),
                        "is_dismissal": type_id == 17
                        and (32 in qualifier_map or 33 in qualifier_map),
                    }
                )

            if type_id in DIRECT_ACTION_TYPE_NAMES and player_id is not None:
                x = pd.to_numeric(event.get("x"), errors="coerce")
                y = pd.to_numeric(event.get("y"), errors="coerce")
                if pd.isna(x) or pd.isna(y) or not (0 <= x <= 100 and 0 <= y <= 100):
                    continue

                team_context = context_by_team[team_id]
                action_rows.append(
                    {
                        "match_id": match_id,
                        "match_date": match_date,
                        "match_description": match_description,
                        "matchweek": match_info.get("week"),
                        "team_id": team_id,
                        "team_name": team_context["team_name_match"],
                        "team_code": team_context["team_code_match"],
                        "home_away": team_context["home_away"],
                        "opponent_id": team_context["opponent_id"],
                        "opponent_name": team_context["opponent_name"],
                        "player_id": player_id,
                        "player_name": event.get("playerName")
                        or fallback_name.get(player_id),
                        "event_id": event.get("eventId"),
                        "provider_event_id": event.get("id"),
                        "type_id": type_id,
                        "event_type": DIRECT_ACTION_TYPE_NAMES[type_id],
                        "period_id": _nullable_int(event.get("periodId")),
                        "match_minute": float(match_minute),
                        "x": float(x),
                        "y": float(y),
                        "outcome": _nullable_int(event.get("outcome")),
                    }
                )

    lineup_slots = pd.DataFrame(lineup_rows)
    timeline = pd.DataFrame(timeline_rows)
    direct_actions = pd.DataFrame(action_rows)
    match_metadata = pd.DataFrame(match_rows)

    for frame, columns in (
        (lineup_slots, ["formation_code", "broad_position_code", "shirt_number", "lineup_slot"]),
        (direct_actions, ["type_id", "period_id", "outcome"]),
    ):
        for column in columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce").astype("Int64")

    return lineup_slots, timeline, direct_actions, match_metadata


def _calculate_appearances(
    lineup_slots: pd.DataFrame,
    timeline: pd.DataFrame,
    direct_actions: pd.DataFrame,
    match_metadata: pd.DataFrame,
) -> pd.DataFrame:
    keys = ["match_id", "team_id", "player_id"]

    sub_on = (
        timeline.loc[timeline["type_id"].eq(19)]
        .groupby(keys, as_index=False)["match_minute"]
        .min()
        .rename(columns={"match_minute": "sub_on_minute"})
    )
    sub_off = (
        timeline.loc[timeline["type_id"].eq(18)]
        .groupby(keys, as_index=False)["match_minute"]
        .min()
        .rename(columns={"match_minute": "sub_off_minute"})
    )
    dismissals = (
        timeline.loc[timeline["is_dismissal"]]
        .groupby(keys, as_index=False)["match_minute"]
        .min()
        .rename(columns={"match_minute": "dismissal_minute"})
    )

    appearances = (
        lineup_slots.merge(sub_on, on=keys, how="left", validate="one_to_one")
        .loc[lambda frame: frame["is_starter"] | frame["sub_on_minute"].notna()]
        .merge(
            match_metadata[["match_id", "match_end_minute"]],
            on="match_id",
            how="left",
            validate="many_to_one",
        )
        .merge(sub_off, on=keys, how="left", validate="one_to_one")
        .merge(dismissals, on=keys, how="left", validate="one_to_one")
    )

    appearances["minute_on"] = appearances["sub_on_minute"].where(
        ~appearances["is_starter"],
        0.0,
    )
    appearances["minute_off"] = appearances[
        ["match_end_minute", "sub_off_minute", "dismissal_minute"]
    ].min(axis=1, skipna=True)
    appearances["minutes_played"] = (
        appearances["minute_off"] - appearances["minute_on"]
    ).clip(lower=0)
    appearances["was_dismissed"] = appearances["dismissal_minute"].notna()
    appearances = add_position_mapping(appearances)

    action_counts = (
        direct_actions.groupby(keys)
        .size()
        .rename("action_count")
        .reset_index()
    )
    appearances = appearances.merge(
        action_counts,
        on=keys,
        how="left",
        validate="one_to_one",
    )
    appearances["action_count"] = appearances["action_count"].fillna(0).astype(int)
    appearances["is_eligible_appearance"] = appearances["minutes_played"].ge(
        MIN_ELIGIBLE_MINUTES
    )
    return appearances


def _build_quality_checks(
    fixture_coverage: pd.DataFrame,
    squad_players: pd.DataFrame,
    lineup_slots: pd.DataFrame,
    direct_actions: pd.DataFrame,
    appearance_samples: pd.DataFrame,
    eligible_appearances: pd.DataFrame,
    eligible_actions: pd.DataFrame,
    centre_back_appearances: pd.DataFrame,
) -> pd.DataFrame:
    lineup_duplicates = lineup_slots.duplicated(
        ["match_id", "team_id", "player_id"]
    ).sum()
    appearance_duplicates = appearance_samples.duplicated(
        ["match_id", "team_id", "player_id"]
    ).sum()
    provider_event_duplicates = direct_actions["provider_event_id"].duplicated().sum()
    team_event_duplicates = direct_actions.duplicated(
        ["match_id", "team_id", "event_id"]
    ).sum()
    available_matches = int(fixture_coverage["event_payload_available"].sum())
    setup_match_teams = lineup_slots[["match_id", "team_id"]].drop_duplicates()

    expected_counts = eligible_appearances.set_index(
        ["match_id", "team_id", "player_id"]
    )["action_count"].sort_index()
    observed_counts = (
        eligible_actions.groupby(["match_id", "team_id", "player_id"])
        .size()
        .reindex(expected_counts.index, fill_value=0)
        .sort_index()
    )
    action_count_mismatches = int((expected_counts != observed_counts).sum())

    checks = [
        ("Indexed league fixtures", len(fixture_coverage)),
        ("Available event payloads", available_matches),
        ("Missing event payloads", int((~fixture_coverage["event_payload_available"]).sum())),
        ("Squad teams", squad_players["team_id"].nunique()),
        ("Teams represented in lineups", lineup_slots["team_id"].nunique()),
        ("Initial team setups", len(setup_match_teams)),
        ("Matches missing one or more initial setups", available_matches - setup_match_teams["match_id"].value_counts().eq(2).sum()),
        ("Lineup team/player duplicates", int(lineup_duplicates)),
        ("Reconstructed appearances", len(appearance_samples)),
        ("Appearance key duplicates", int(appearance_duplicates)),
        ("Non-positive appearance minutes", int(appearance_samples["minutes_played"].le(0).sum())),
        ("Eligible appearances (60+ minutes)", len(eligible_appearances)),
        ("High-confidence mapped eligible appearances", int(eligible_appearances["mapping_confidence"].eq("high").sum())),
        ("Unresolved eligible appearances", int(eligible_appearances["mapping_status"].ne("mapped").sum())),
        ("High-confidence centre-back appearances", len(centre_back_appearances)),
        ("Direct positional actions", len(direct_actions)),
        ("Eligible positional actions", len(eligible_actions)),
        ("Duplicate provider event IDs", int(provider_event_duplicates)),
        ("Duplicate match/team event IDs", int(team_event_duplicates)),
        ("Eligible action-count mismatches", action_count_mismatches),
        ("Out-of-range eligible action coordinates", int((~eligible_actions["x"].between(0, 100) | ~eligible_actions["y"].between(0, 100)).sum())),
    ]
    return pd.DataFrame(checks, columns=["check", "value"])


def _validate_result(result: LeaguePipelineResult) -> None:
    checks = result.quality_checks.set_index("check")["value"]
    if checks["Squad teams"] != 20:
        raise AssertionError("Expected 20 Premier League squads")
    if checks["Teams represented in lineups"] != 20:
        raise AssertionError("Expected all 20 teams in lineup records")
    if checks["Matches missing one or more initial setups"] != 0:
        raise AssertionError("Every available match must contain two initial team setups")
    for check in (
        "Lineup team/player duplicates",
        "Appearance key duplicates",
        "Non-positive appearance minutes",
        "Duplicate provider event IDs",
        "Duplicate match/team event IDs",
        "Eligible action-count mismatches",
        "Out-of-range eligible action coordinates",
    ):
        if checks[check] != 0:
            raise AssertionError(f"Quality check failed: {check} = {checks[check]}")
    if not result.eligible_appearances["minutes_played"].ge(
        MIN_ELIGIBLE_MINUTES
    ).all():
        raise AssertionError("Every eligible appearance must satisfy the minute rule")
    if not result.centre_back_appearances["position_group"].eq("Centre-back").all():
        raise AssertionError("Centre-back output contains another position group")
    if not result.centre_back_appearances["mapping_confidence"].eq("high").all():
        raise AssertionError("Centre-back output contains a low-confidence label")


def build_league_tables(
    season_root: str | Path,
) -> LeaguePipelineResult:
    """Build validated league-wide appearance and direct-action tables."""

    season_root = Path(season_root).resolve()
    fixture_index = pd.read_csv(season_root / "matches_ids.csv")
    files_by_id = _match_file_index(season_root / "partidos")
    fixture_coverage = fixture_index.copy()
    fixture_coverage["event_file"] = fixture_coverage["id"].map(files_by_id)
    fixture_coverage["event_payload_available"] = fixture_coverage["event_file"].notna()

    squad_players = _load_squad_players(season_root)
    lineup_slots, timeline, direct_actions, match_metadata = _read_provider_rows(
        fixture_coverage,
        squad_players,
    )
    appearance_samples = _calculate_appearances(
        lineup_slots,
        timeline,
        direct_actions,
        match_metadata,
    )
    eligible_appearances = appearance_samples.loc[
        appearance_samples["is_eligible_appearance"]
    ].copy()

    appearance_context = [
        "match_id",
        "team_id",
        "player_id",
        "formation_code",
        "lineup_slot",
        "is_starter",
        "minute_on",
        "minute_off",
        "minutes_played",
        "action_count",
        "formation_name",
        "decoded_provider_position",
        "standardised_position",
        "position_group",
        "mapping_confidence",
        "mapping_status",
    ]
    eligible_actions = direct_actions.merge(
        eligible_appearances[appearance_context],
        on=["match_id", "team_id", "player_id"],
        how="inner",
        validate="many_to_one",
    )
    centre_back_appearances = eligible_appearances.loc[
        eligible_appearances["position_group"].eq("Centre-back")
        & eligible_appearances["mapping_confidence"].eq("high")
    ].copy()

    quality_checks = _build_quality_checks(
        fixture_coverage,
        squad_players,
        lineup_slots,
        direct_actions,
        appearance_samples,
        eligible_appearances,
        eligible_actions,
        centre_back_appearances,
    )
    result = LeaguePipelineResult(
        fixture_coverage=fixture_coverage,
        squad_players=squad_players,
        lineup_slots=lineup_slots,
        appearance_samples=appearance_samples,
        eligible_appearances=eligible_appearances,
        eligible_actions=eligible_actions,
        centre_back_appearances=centre_back_appearances,
        quality_checks=quality_checks,
    )
    _validate_result(result)
    return result


def write_league_outputs(
    result: LeaguePipelineResult,
    output_directory: str | Path,
) -> dict[str, Path]:
    """Write the compact ignored outputs used by later analysis."""

    output_directory = Path(output_directory).resolve()
    output_directory.mkdir(parents=True, exist_ok=True)
    paths = {
        "eligible_appearances": output_directory
        / "premier_league_eligible_appearances.parquet",
        "eligible_actions": output_directory
        / "premier_league_eligible_positional_actions.parquet",
        "centre_back_appearances": output_directory
        / "premier_league_centre_back_appearances.parquet",
        "quality_checks": output_directory
        / "premier_league_pipeline_quality_checks.csv",
    }
    result.eligible_appearances.to_parquet(paths["eligible_appearances"], index=False)
    result.eligible_actions.to_parquet(paths["eligible_actions"], index=False)
    result.centre_back_appearances.to_parquet(
        paths["centre_back_appearances"],
        index=False,
    )
    result.quality_checks.to_csv(paths["quality_checks"], index=False)
    return paths
