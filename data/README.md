# Local data directory

The raw and processed football data used by ScoutAgent is licensed and is not committed to Git.

Authorized users should place the supplied raw package at the project root as:

```text
data/raw/eventing_FMP
```

Running `scripts/build_streamlit_data.py` creates local application files under `data/processed/`. That directory is intentionally ignored by Git.

Running `scripts/build_league_data.py` creates the league-wide appearance,
positional-action, centre-back and quality-check outputs under the same ignored
`data/processed/` directory.

Running `scripts/build_centre_back_templates.py` creates ignored appearance-zone,
player-zone and league-template outputs for the 18-zone and 20-zone layouts.

Running `scripts/validate_forest_centre_backs.py` creates ignored Forest validation
tables for spatial interpretation, bootstrap uncertainty, split-half stability,
zone-layout robustness and action-family sensitivity.

Running `scripts/build_wide_defender_templates.py` creates ignored appearance,
player and league-template tables for left, right and role-normalised overarching
full-back and wing-back groups. Original coordinates remain available in the
side-specific profiles; right-sided width coordinates are mirrored only for the
overarching role-normalised profiles.

Running `scripts/validate_forest_wide_defenders.py` creates ignored validation
tables for Forest full-backs and wing-backs, covering orientation, bootstrap
uncertainty, split-half stability, zone-layout robustness and action-family
sensitivity.

Do not publish or redistribute raw or processed event data without explicit permission from the provider and the university.
