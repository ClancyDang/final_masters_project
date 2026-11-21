"""Build appearance, player and league centre-back zone profiles."""

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.analysis import build_centre_back_templates, write_centre_back_template_outputs


PROCESSED_ROOT = PROJECT_ROOT / "data" / "processed"


def main() -> None:
    eligible_actions = pd.read_parquet(
        PROCESSED_ROOT / "premier_league_eligible_positional_actions.parquet"
    )
    centre_back_appearances = pd.read_parquet(
        PROCESSED_ROOT / "premier_league_centre_back_appearances.parquet"
    )
    result = build_centre_back_templates(
        eligible_actions,
        centre_back_appearances,
    )
    output_paths = write_centre_back_template_outputs(result, PROCESSED_ROOT)

    print(result.quality_checks.to_string(index=False))
    print("\nWrote:")
    for label, path in output_paths.items():
        print(f"- {label}: {path}")


if __name__ == "__main__":
    main()
