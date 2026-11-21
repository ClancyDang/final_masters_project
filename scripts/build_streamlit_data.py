"""Build the compact Nottingham Forest tables used by the Streamlit prototype."""

from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_PATH = PROJECT_ROOT / "notebooks" / "01_forest_defender_data_import.ipynb"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"


def execute_notebook_to_eligibility() -> dict[str, object]:
    """Execute notebook code through the eligibility cell in one namespace."""
    with NOTEBOOK_PATH.open(encoding="utf-8") as notebook_file:
        notebook = json.load(notebook_file)

    namespace: dict[str, object] = {"__name__": "__main__"}
    target_cell_found = False

    for cell in notebook["cells"]:
        if cell.get("cell_type") != "code":
            continue

        source = "".join(cell.get("source", []))
        exec(compile(source, f"{NOTEBOOK_PATH.name}:{cell.get('id', 'code-cell')}", "exec"), namespace)

        if cell.get("id") == "define-eligible-appearances":
            target_cell_found = True
            break

    if not target_cell_found:
        raise RuntimeError("Eligibility cell was not found in the source notebook")

    return namespace


def main() -> None:
    namespace = execute_notebook_to_eligibility()
    eligible_appearances = namespace["eligible_defender_appearances"]
    eligible_actions = namespace["eligible_positional_actions"]

    appearance_columns = [
        "match_id",
        "match_date",
        "match_description",
        "formation_code",
        "player_id",
        "player_name",
        "squad_position",
        "lineup_slot",
        "is_starter",
        "minute_on",
        "minute_off",
        "minutes_played",
        "action_count",
    ]
    action_columns = [
        "match_id",
        "match_date",
        "match_description",
        "player_id",
        "player_name",
        "provider_event_id",
        "type_id",
        "event_type",
        "match_minute",
        "x",
        "y",
        "outcome",
        "minutes_played",
        "action_count",
    ]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    appearance_path = OUTPUT_DIR / "forest_eligible_defender_appearances.parquet"
    action_path = OUTPUT_DIR / "forest_eligible_positional_actions.parquet"

    eligible_appearances[appearance_columns].to_parquet(appearance_path, index=False)
    eligible_actions[action_columns].to_parquet(action_path, index=False)

    print(f"Wrote {len(eligible_appearances):,} appearances to {appearance_path}")
    print(f"Wrote {len(eligible_actions):,} actions to {action_path}")


if __name__ == "__main__":
    main()
