"""Validate supported Forest goalkeeper, midfield and forward profiles."""

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.analysis import (
    build_position_group_templates,
    build_position_group_validation,
    write_position_group_validation_outputs,
)


PROCESSED_ROOT = PROJECT_ROOT / "data" / "processed"
SUPPORTED_VALIDATION_GROUPS = (
    "Goalkeeper",
    "Central midfield",
    "Attacking midfield",
    "Wide midfield",
    "Winger",
    "Forward",
)


def main() -> None:
    eligible_actions = pd.read_parquet(
        PROCESSED_ROOT / "premier_league_eligible_positional_actions.parquet"
    )
    eligible_appearances = pd.read_parquet(
        PROCESSED_ROOT / "premier_league_eligible_appearances.parquet"
    )
    summaries = []
    robustness_tables = []
    quality_tables = []
    for position_group in SUPPORTED_VALIDATION_GROUPS:
        templates = build_position_group_templates(
            eligible_actions,
            eligible_appearances,
            position_group,
        )
        validation = build_position_group_validation(
            templates,
            eligible_actions,
            eligible_appearances,
        )
        outputs = write_position_group_validation_outputs(
            validation,
            PROCESSED_ROOT,
        )
        summaries.append(validation.forest_summary)
        robustness_tables.append(validation.layout_robustness)
        quality_tables.append(validation.quality_checks)

        print(f"\n{position_group} quality checks")
        print(validation.quality_checks.to_string(index=False))
        print("\nWrote:")
        for label, path in outputs.items():
            print(f"- {label}: {path}")

    pd.concat(summaries, ignore_index=True).to_csv(
        PROCESSED_ROOT / "forest_remaining_position_validation_summary.csv",
        index=False,
    )
    pd.concat(robustness_tables, ignore_index=True).to_csv(
        PROCESSED_ROOT / "remaining_position_layout_robustness.csv",
        index=False,
    )
    pd.concat(quality_tables, ignore_index=True).to_csv(
        PROCESSED_ROOT / "remaining_position_validation_quality_checks.csv",
        index=False,
    )


if __name__ == "__main__":
    main()
