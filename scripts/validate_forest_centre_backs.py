"""Build local validation outputs for Nottingham Forest centre-backs."""

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.analysis import (
    build_centre_back_validation,
    write_centre_back_validation_outputs,
)


PROCESSED_ROOT = PROJECT_ROOT / "data" / "processed"


def main() -> None:
    appearance_profiles = pd.read_parquet(
        PROCESSED_ROOT / "centre_back_appearance_zone_profiles.parquet"
    )
    player_profiles = pd.read_parquet(
        PROCESSED_ROOT / "centre_back_player_zone_profiles.parquet"
    )
    eligible_actions = pd.read_parquet(
        PROCESSED_ROOT / "premier_league_eligible_positional_actions.parquet"
    )
    centre_back_appearances = pd.read_parquet(
        PROCESSED_ROOT / "premier_league_centre_back_appearances.parquet"
    )
    result = build_centre_back_validation(
        appearance_profiles,
        player_profiles,
        eligible_actions,
        centre_back_appearances,
    )
    outputs = write_centre_back_validation_outputs(result, PROCESSED_ROOT)

    display_columns = [
        "player_name",
        "layout",
        "dominant_provider_role",
        "similarity_score",
        "relative_lateral_shift",
        "spatial_side",
        "eligible_appearances",
    ]
    print("\nForest centre-back summary")
    print(result.forest_summary[display_columns].to_string(index=False))
    print("\nLayout robustness")
    print(result.layout_robustness.to_string(index=False))
    print("\nQuality checks")
    print(result.quality_checks.to_string(index=False))
    print("\nWrote:")
    for label, path in outputs.items():
        print(f"- {label}: {path}")


if __name__ == "__main__":
    main()
