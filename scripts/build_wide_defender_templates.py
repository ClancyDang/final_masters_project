"""Build full-back and wing-back side-specific and mirrored templates."""

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.analysis import (
    build_wide_defender_templates,
    write_wide_defender_template_outputs,
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
        result = build_wide_defender_templates(
            eligible_actions,
            eligible_appearances,
            position_group,
        )
        output_paths = write_wide_defender_template_outputs(
            result,
            PROCESSED_ROOT,
        )
        print(f"\n{position_group} quality checks")
        print(result.quality_checks.to_string(index=False))
        print("\nWrote:")
        for label, path in output_paths.items():
            print(f"- {label}: {path}")


if __name__ == "__main__":
    main()
