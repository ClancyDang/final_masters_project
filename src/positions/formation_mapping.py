"""Decode Stats Perform formation slots and standardise scouting positions.

The provider-decoding values are based on Kloppy's Stats Perform mapping at
commit a9651eba7c4dbbe2d2fc6d4cffb4aea63fadac11. Our project-standardisation
rules are intentionally separate from that reference mapping.

Reference:
https://github.com/PySport/kloppy/blob/a9651eba7c4dbbe2d2fc6d4cffb4aea63fadac11/kloppy/infra/serializers/event/statsperform/formation_mapping.py
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Any


# Each position tuple is indexed by the provider lineup slot (0 through 11).
# Slot 0 denotes a bench player and therefore has no starting position.
FORMATION_SPECS: dict[int, tuple[str, tuple[str | None, ...]]] = {
    2: ("4-4-2", (None, "Goalkeeper", "RightBack", "LeftBack", "RightCentralMidfield", "RightCenterBack", "LeftCenterBack", "RightMidfield", "LeftCentralMidfield", "LeftForward", "RightForward", "LeftMidfield")),
    3: ("4-1-2-1-2", (None, "Goalkeeper", "RightBack", "LeftBack", "CenterDefensiveMidfield", "RightCenterBack", "LeftCenterBack", "RightMidfield", "CenterAttackingMidfield", "LeftForward", "RightForward", "LeftMidfield")),
    4: ("4-3-3", (None, "Goalkeeper", "RightBack", "LeftBack", "CenterMidfield", "RightCenterBack", "LeftCenterBack", "RightMidfield", "LeftMidfield", "Striker", "RightWing", "LeftWing")),
    5: ("4-5-1", (None, "Goalkeeper", "RightBack", "LeftBack", "RightCentralMidfield", "RightCenterBack", "LeftCenterBack", "RightMidfield", "LeftCentralMidfield", "Striker", "CenterMidfield", "LeftMidfield")),
    6: ("4-4-1-1", (None, "Goalkeeper", "RightBack", "LeftBack", "RightCentralMidfield", "RightCenterBack", "LeftCenterBack", "RightMidfield", "LeftCentralMidfield", "Striker", "CenterAttackingMidfield", "LeftMidfield")),
    7: ("4-1-4-1", (None, "Goalkeeper", "RightBack", "LeftBack", "CenterDefensiveMidfield", "RightCenterBack", "LeftCenterBack", "RightMidfield", "RightCentralMidfield", "Striker", "LeftCentralMidfield", "LeftMidfield")),
    8: ("4-2-3-1", (None, "Goalkeeper", "RightBack", "LeftBack", "RightCentralMidfield", "RightCenterBack", "LeftCenterBack", "RightAttackingMidfield", "LeftCentralMidfield", "Striker", "CenterAttackingMidfield", "LeftAttackingMidfield")),
    9: ("4-3-2-1", (None, "Goalkeeper", "RightBack", "LeftBack", "CenterMidfield", "RightCenterBack", "LeftCenterBack", "LeftMidfield", "RightMidfield", "Striker", "RightAttackingMidfield", "LeftAttackingMidfield")),
    10: ("5-3-2", (None, "Goalkeeper", "RightBack", "LeftBack", "LeftCenterBack", "CenterBack", "RightCenterBack", "RightCentralMidfield", "CenterMidfield", "LeftForward", "RightForward", "LeftCentralMidfield")),
    11: ("5-4-1", (None, "Goalkeeper", "RightBack", "LeftBack", "LeftCenterBack", "CenterBack", "RightCenterBack", "RightMidfield", "RightCentralMidfield", "Striker", "LeftCentralMidfield", "LeftMidfield")),
    12: ("3-5-2", (None, "Goalkeeper", "RightMidfield", "LeftMidfield", "LeftCenterBack", "CenterBack", "RightCenterBack", "RightCentralMidfield", "LeftCentralMidfield", "LeftForward", "RightForward", "CenterMidfield")),
    13: ("3-4-3", (None, "Goalkeeper", "RightMidfield", "LeftMidfield", "LeftCenterBack", "CenterBack", "RightCenterBack", "RightCentralMidfield", "LeftCentralMidfield", "Striker", "RightWing", "LeftWing")),
    14: ("3-1-3-1-2", (None, "Goalkeeper", "Unknown", "Unknown", "Unknown", "Unknown", "Unknown", "Unknown", "Unknown", "Unknown", "Unknown", "Unknown")),
    15: ("4-2-2-2", (None, "Goalkeeper", "RightBack", "LeftBack", "RightDefensiveMidfield", "RightCenterBack", "LeftCenterBack", "RightCentralMidfield", "LeftDefensiveMidfield", "LeftForward", "RightForward", "LeftCentralMidfield")),
    16: ("3-5-1-1", (None, "Goalkeeper", "RightMidfield", "LeftMidfield", "LeftCenterBack", "CenterBack", "RightCenterBack", "RightDefensiveMidfield", "LeftDefensiveMidfield", "Striker", "CenterAttackingMidfield", "CenterDefensiveMidfield")),
    17: ("3-4-2-1", (None, "Goalkeeper", "RightMidfield", "LeftMidfield", "LeftCenterBack", "CenterBack", "RightCenterBack", "RightCentralMidfield", "LeftCentralMidfield", "Striker", "RightForward", "LeftForward")),
    18: ("3-4-1-2", (None, "Goalkeeper", "RightMidfield", "LeftMidfield", "LeftCenterBack", "CenterBack", "RightCenterBack", "RightCentralMidfield", "LeftCentralMidfield", "CenterAttackingMidfield", "RightForward", "LeftForward")),
    19: ("3-1-4-2", (None, "Goalkeeper", "RightMidfield", "LeftMidfield", "CenterBack", "RightCenterBack", "LeftCenterBack", "RightCentralMidfield", "CenterDefensiveMidfield", "RightForward", "LeftWing", "LeftCentralMidfield")),
    20: ("3-1-2-1-3", (None, "Goalkeeper", "RightMidfield", "LeftMidfield", "LeftCenterBack", "CenterBack", "RightCenterBack", "CenterAttackingMidfield", "CenterDefensiveMidfield", "Striker", "RightWing", "LeftWing")),
    21: ("4-1-3-2", (None, "Goalkeeper", "RightBack", "LeftBack", "CenterDefensiveMidfield", "RightCenterBack", "LeftCenterBack", "RightWing", "CenterAttackingMidfield", "RightForward", "LeftForward", "LeftWing")),
    22: ("4-2-4-0", (None, "Goalkeeper", "RightBack", "LeftBack", "RightCentralMidfield", "RightCenterBack", "LeftCenterBack", "RightWing", "LeftCentralMidfield", "RightForward", "LeftForward", "LeftWing")),
    23: ("4-3-1-2", (None, "Goalkeeper", "RightBack", "LeftBack", "CenterMidfield", "RightCenterBack", "LeftCenterBack", "RightMidfield", "CenterAttackingMidfield", "RightForward", "LeftForward", "LeftMidfield")),
    24: ("3-2-4-1", (None, "Goalkeeper", "RightDefensiveMidfield", "LeftDefensiveMidfield", "LeftCenterBack", "CenterBack", "RightCenterBack", "RightCentralMidfield", "LeftCentralMidfield", "Striker", "RightWing", "LeftWing")),
    25: ("3-3-3-1", (None, "Goalkeeper", "RightDefensiveMidfield", "LeftDefensiveMidfield", "LeftCenterBack", "CenterBack", "RightCenterBack", "CenterAttackingMidfield", "CenterDefensiveMidfield", "Striker", "RightWing", "LeftWing")),
}


STANDARD_POSITION_MAP: dict[str, tuple[str, str]] = {
    "Goalkeeper": ("Goalkeeper", "Goalkeeper"),
    "RightCenterBack": ("Right centre-back", "Centre-back"),
    "CenterBack": ("Centre-back", "Centre-back"),
    "LeftCenterBack": ("Left centre-back", "Centre-back"),
    "RightDefensiveMidfield": ("Right defensive midfielder", "Defensive midfield"),
    "CenterDefensiveMidfield": ("Defensive midfielder", "Defensive midfield"),
    "LeftDefensiveMidfield": ("Left defensive midfielder", "Defensive midfield"),
    "RightCentralMidfield": ("Right central midfielder", "Central midfield"),
    "CenterMidfield": ("Central midfielder", "Central midfield"),
    "LeftCentralMidfield": ("Left central midfielder", "Central midfield"),
    "RightMidfield": ("Right midfielder", "Wide midfield"),
    "LeftMidfield": ("Left midfielder", "Wide midfield"),
    "RightAttackingMidfield": ("Right attacking midfielder", "Attacking midfield"),
    "CenterAttackingMidfield": ("Attacking midfielder", "Attacking midfield"),
    "LeftAttackingMidfield": ("Left attacking midfielder", "Attacking midfield"),
    "RightWing": ("Right winger", "Winger"),
    "LeftWing": ("Left winger", "Winger"),
    "RightForward": ("Right forward", "Forward"),
    "LeftForward": ("Left forward", "Forward"),
    "Striker": ("Centre-forward", "Forward"),
}


@dataclass(frozen=True)
class PositionClassification:
    """Decoded provider position plus the project's standardised position."""

    formation_name: str | None
    decoded_provider_position: str | None
    standardised_position: str | None
    position_group: str | None
    mapping_confidence: str
    mapping_status: str


def _coerce_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        if isinstance(value, float) and math.isnan(value):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def decode_provider_position(
    formation_code: Any,
    lineup_slot: Any,
) -> tuple[str | None, str | None]:
    """Return the provider formation name and decoded formation position."""

    code = _coerce_int(formation_code)
    slot = _coerce_int(lineup_slot)
    if code not in FORMATION_SPECS or slot is None or not 0 <= slot <= 11:
        return None, None

    formation_name, slot_positions = FORMATION_SPECS[code]
    return formation_name, slot_positions[slot]


def _standardise_position(
    formation_name: str,
    decoded_provider_position: str,
) -> tuple[str | None, str | None]:
    """Apply the project's documented formation-aware position rules."""

    defensive_line_size = int(formation_name.split("-", maxsplit=1)[0])

    if decoded_provider_position == "RightBack":
        if defensive_line_size == 5:
            return "Right wing-back", "Wing-back"
        return "Right full-back", "Full-back"

    if decoded_provider_position == "LeftBack":
        if defensive_line_size == 5:
            return "Left wing-back", "Wing-back"
        return "Left full-back", "Full-back"

    if defensive_line_size == 3:
        if decoded_provider_position == "RightMidfield":
            return "Right wing-back", "Wing-back"
        if decoded_provider_position == "LeftMidfield":
            return "Left wing-back", "Wing-back"

    return STANDARD_POSITION_MAP.get(decoded_provider_position, (None, None))


def classify_appearance(
    formation_code: Any,
    lineup_slot: Any,
) -> PositionClassification:
    """Decode and standardise one appearance's starting formation slot."""

    code = _coerce_int(formation_code)
    slot = _coerce_int(lineup_slot)

    if slot == 0:
        formation_name = FORMATION_SPECS.get(code, (None, ()))[0]
        return PositionClassification(
            formation_name=formation_name,
            decoded_provider_position=None,
            standardised_position=None,
            position_group=None,
            mapping_confidence="low",
            mapping_status="bench_slot_unresolved",
        )

    formation_name, provider_position = decode_provider_position(code, slot)
    if formation_name is None or provider_position is None:
        return PositionClassification(
            formation_name=formation_name,
            decoded_provider_position=provider_position,
            standardised_position=None,
            position_group=None,
            mapping_confidence="low",
            mapping_status="unmapped_provider_combination",
        )

    if provider_position == "Unknown":
        return PositionClassification(
            formation_name=formation_name,
            decoded_provider_position=provider_position,
            standardised_position=None,
            position_group=None,
            mapping_confidence="low",
            mapping_status="provider_position_unknown",
        )

    standardised_position, position_group = _standardise_position(
        formation_name,
        provider_position,
    )
    if standardised_position is None:
        return PositionClassification(
            formation_name=formation_name,
            decoded_provider_position=provider_position,
            standardised_position=None,
            position_group=None,
            mapping_confidence="low",
            mapping_status="project_rule_missing",
        )

    return PositionClassification(
        formation_name=formation_name,
        decoded_provider_position=provider_position,
        standardised_position=standardised_position,
        position_group=position_group,
        mapping_confidence="high",
        mapping_status="mapped",
    )


def add_position_mapping(
    frame: Any,
    formation_column: str = "formation_code",
    slot_column: str = "lineup_slot",
) -> Any:
    """Return a copy of a DataFrame with decoded position columns appended."""

    import pandas as pd

    missing_columns = {
        formation_column,
        slot_column,
    }.difference(frame.columns)
    if missing_columns:
        raise KeyError(f"Missing position-mapping columns: {sorted(missing_columns)}")

    classifications = [
        asdict(classify_appearance(formation_code, lineup_slot))
        for formation_code, lineup_slot in zip(
            frame[formation_column],
            frame[slot_column],
        )
    ]
    mapped_columns = pd.DataFrame(classifications, index=frame.index)
    return frame.copy().join(mapped_columns)
