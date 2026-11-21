"""Build validated Premier League appearance and positional-action outputs."""

from __future__ import annotations

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data import build_league_tables, write_league_outputs


SEASON_ROOT = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "eventing_FMP"
    / "europa"
    / "England_Premier_League"
    / "2025-2026"
)
OUTPUT_DIRECTORY = PROJECT_ROOT / "data" / "processed"


def main() -> None:
    result = build_league_tables(SEASON_ROOT)
    output_paths = write_league_outputs(result, OUTPUT_DIRECTORY)

    print(result.quality_checks.to_string(index=False))
    print("\nWrote:")
    for label, path in output_paths.items():
        print(f"- {label}: {path}")


if __name__ == "__main__":
    main()
