"""Build templates for every mapped position not covered by defender scripts."""

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.analysis import (
    POSITION_GROUP_ROLES,
    build_position_group_templates,
    write_position_group_template_outputs,
)


PROCESSED_ROOT = PROJECT_ROOT / "data" / "processed"


def main() -> None:
    eligible_actions = pd.read_parquet(
        PROCESSED_ROOT / "premier_league_eligible_positional_actions.parquet"
    )
    eligible_appearances = pd.read_parquet(
        PROCESSED_ROOT / "premier_league_eligible_appearances.parquet"
    )
    coverage_tables = []
    for position_group in POSITION_GROUP_ROLES:
        result = build_position_group_templates(
            eligible_actions,
            eligible_appearances,
            position_group,
        )
        outputs = write_position_group_template_outputs(result, PROCESSED_ROOT)
        coverage_tables.append(
            result.template_coverage.assign(position_group=position_group)
        )
        print(f"\n{position_group} quality checks")
        print(result.quality_checks.to_string(index=False))
        print("\nTemplate coverage")
        print(result.template_coverage.to_string(index=False))
        print("\nWrote:")
        for label, path in outputs.items():
            print(f"- {label}: {path}")

    coverage = pd.concat(coverage_tables, ignore_index=True)
    coverage.to_csv(
        PROCESSED_ROOT / "remaining_position_template_coverage.csv",
        index=False,
    )


if __name__ == "__main__":
    main()
