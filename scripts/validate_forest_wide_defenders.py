"""Validate Nottingham Forest full-back and wing-back profiles."""

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.analysis import (
    build_wide_defender_templates,
    build_wide_defender_validation,
    write_wide_defender_validation_outputs,
)


PROCESSED_ROOT = PROJECT_ROOT / "data" / "processed"


def main() -> None:
    eligible_actions = pd.read_parquet(
        PROCESSED_ROOT / "premier_league_eligible_positional_actions.parquet"
    )
    eligible_appearances = pd.read_parquet(
        PROCESSED_ROOT / "premier_league_eligible_appearances.parquet"
    )
    for position_group in ("Full-back", "Wing-back"):
        templates = build_wide_defender_templates(
            eligible_actions,
            eligible_appearances,
            position_group,
        )
        validation = build_wide_defender_validation(
            templates,
            eligible_actions,
            eligible_appearances,
        )
        outputs = write_wide_defender_validation_outputs(
            validation,
            PROCESSED_ROOT,
        )
        display_columns = [
            "player_name",
            "template_group",
            "layout",
            "eligible_appearances",
            "similarity_score",
            "relative_lateral_shift",
            "orientation_alignment",
        ]
        print(f"\n{position_group} Forest summary")
        print(validation.forest_summary[display_columns].to_string(index=False))
        print("\nLayout robustness")
        print(validation.layout_robustness.to_string(index=False))
        print("\nQuality checks")
        print(validation.quality_checks.to_string(index=False))
        print("\nWrote:")
        for label, path in outputs.items():
            print(f"- {label}: {path}")


if __name__ == "__main__":
    main()
