# ScoutAgent

ScoutAgent is a football scouting and recruitment-analysis application being developed as a Final Master Project for the Master's programme in Sport Analysis & Analytics at Universidad Europea de Madrid and the Real Madrid Graduate School.

The current prototype uses Nottingham Forest as its initial club context. It creates interactive defender action-location maps and compares Forest players with validated 2025/26 Premier League positional templates.

## Prototype status

The application currently allows a user to:

- Select a Nottingham Forest defender.
- Select one of that player's appearances of at least 60 minutes.
- View a positional 20-zone map, a traditional 18-zone map or both.
- Inspect minutes played and the number of direct actions.
- View zone-level counts and normalized action shares.
- Compare Forest players with available role-specific or overarching league templates in either zone layout.
- Inspect zone differences, peer percentiles, sample size and an overall similarity score.
- Validate the Forest comparison with appearance-level bootstrap intervals, split-half stability, layout robustness and separate pass/defensive-action profiles.
- Read the current methodology and limitations.

The maps describe the locations where recorded direct actions began. They do **not** measure continuous player occupancy, which would require tracking data.

## Data availability and licensing

The event data used by this project is licensed and is **not included in this repository**. Raw files and processed event-level Parquet files are excluded from Git.

To reproduce the full local prototype, an authorized user must place the supplied package at:

```text
data/raw/eventing_FMP/
```

The current Forest dataset contains 38 indexed fixtures and 36 available event payloads. Two match payloads are missing.

Do not publish, redistribute or deploy the supplied data without confirming the provider and university permissions.

## Repository structure

```text
.
├── data/
│   └── README.md
├── documentation/
│   ├── archive/
│   │   └── strategy_v1.txt
│   ├── day_1.md
│   └── initial_plan_and_goal.md
├── notebooks/
│   ├── 01_forest_defender_data_import.ipynb
│   ├── 02_position_mapping_validation.ipynb
│   ├── 03_premier_league_pipeline_validation.ipynb
│   ├── 04_centre_back_template_validation.ipynb
│   ├── 05_forest_centre_back_results_validation.ipynb
│   ├── 06_wide_defender_results_validation.ipynb
│   ├── 07_remaining_position_template_coverage.ipynb
│   └── 08_remaining_position_results_validation.ipynb
├── scripts/
│   ├── build_centre_back_templates.py
│   ├── build_league_data.py
│   ├── build_remaining_position_templates.py
│   ├── build_streamlit_data.py
│   ├── build_wide_defender_templates.py
│   ├── validate_forest_centre_backs.py
│   ├── validate_forest_position_groups.py
│   └── validate_forest_wide_defenders.py
├── src/
│   ├── analysis/
│   │   ├── centre_back_templates.py
│   │   ├── centre_back_validation.py
│   │   ├── player_template_comparison.py
│   │   ├── position_group_templates.py
│   │   ├── position_group_validation.py
│   │   ├── wide_defender_templates.py
│   │   └── wide_defender_validation.py
│   ├── data/
│   │   └── premier_league_pipeline.py
│   ├── positions/
│   │   └── formation_mapping.py
│   └── visualizations/
│       └── positional_maps.py
├── tests/
│   ├── test_formation_mapping.py
│   ├── test_centre_back_templates.py
│   ├── test_centre_back_validation.py
│   ├── test_player_template_comparison.py
│   ├── test_position_group_templates.py
│   ├── test_premier_league_pipeline.py
│   ├── test_positional_maps.py
│   └── test_wide_defender_templates.py
├── THIRD_PARTY_NOTICES.md
├── .python-version
├── requirements.txt
├── requirements-dev.txt
└── streamlit_app.py
```

Local-only directories such as `.venv/`, `tmp/`, `data/processed/` and the licensed raw-data package are intentionally ignored.

## Environment setup

The initial environment was developed with Python 3.14.6. Create a virtual environment from the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

`requirements.txt` contains the pinned application dependencies. `requirements-dev.txt` adds the packages used for notebooks and exploratory analysis.

## Build the local processed data

After placing the licensed package in the expected local directory, run:

```bash
.venv/bin/python scripts/build_streamlit_data.py
```

This creates the following ignored local files:

```text
data/processed/forest_eligible_defender_appearances.parquet
data/processed/forest_eligible_positional_actions.parquet
```

The Forest-only Streamlit build script still executes the validated preparation cells from the source notebook. The league-wide build uses the reusable `src/data/premier_league_pipeline.py` module; migrating the remaining Forest-only build onto that module is a later refactor.

## Build the league-wide processed data

To rebuild the validated Premier League appearance and positional-action tables, run:

```bash
.venv/bin/python scripts/build_league_data.py
```

This reads each available match payload once, reconstructs appearances for all 20 teams, applies the formation-position mapping and writes:

```text
data/processed/premier_league_eligible_appearances.parquet
data/processed/premier_league_eligible_positional_actions.parquet
data/processed/premier_league_centre_back_appearances.parquet
data/processed/premier_league_pipeline_quality_checks.csv
```

All four outputs remain local and ignored by Git. The current package contains 380 indexed fixtures and 361 available event payloads; missing payloads are reported rather than silently dropped.

## Build the centre-back templates

After building the league-wide data, run:

```bash
.venv/bin/python scripts/build_centre_back_templates.py
```

This creates one normalized zone profile per appearance, one equal-appearance-weighted profile per centre-back and equal-player-weighted league templates for both layouts. Players need at least five eligible centre-back appearances to define the league template. The ignored outputs are:

```text
data/processed/centre_back_appearance_zone_profiles.parquet
data/processed/centre_back_player_zone_profiles.parquet
data/processed/centre_back_league_templates.parquet
data/processed/centre_back_template_quality_checks.csv
```

## Validate the Forest centre-back results

After building the centre-back templates, run:

```bash
.venv/bin/python scripts/validate_forest_centre_backs.py
```

This creates ignored local tables covering provider-role agreement, zone-level
differences, appearance-level bootstrap intervals, repeated split-half stability,
league-wide 18-versus-20-zone robustness and pass/defensive-action sensitivity.
Review the results in
`notebooks/05_forest_centre_back_results_validation.ipynb`.

## Build the full-back and wing-back templates

After building the league-wide appearance and action tables, run:

```bash
.venv/bin/python scripts/build_wide_defender_templates.py
```

This creates three template groups for each wide-defender role:

- Left full-back, right full-back and overarching full-back.
- Left wing-back, right wing-back and overarching wing-back.

Side-specific profiles retain the original coordinates. For each overarching
profile, right-sided actions use `role_normalised_y = 100 - original_y`, while
left-sided actions remain unchanged. This aligns tactically equivalent actions
without overwriting the source coordinates. The ignored `*_role_actions.parquet`
outputs retain both `original_y` and `role_normalised_y` for auditing.
Appearance profiles are averaged equally within each player and qualifying
players are averaged equally within each league template, using the same
five-appearance threshold as centre-backs.

## Validate the Forest full-back and wing-back results

After building the wide-defender templates, run:

```bash
.venv/bin/python scripts/validate_forest_wide_defenders.py
```

This validates original-side and mirrored orientation, appearance-level bootstrap
uncertainty, repeated split-half stability, 18-versus-20-zone sensitivity and
pass/defensive-action sensitivity. Review the outputs in
`notebooks/06_wide_defender_results_validation.ipynb`.

## Build the remaining position templates

After building the league-wide appearance and action tables, run:

```bash
.venv/bin/python scripts/build_remaining_position_templates.py
```

This creates role-specific and overarching templates for goalkeepers, defensive
midfielders, central midfielders, attacking midfielders, wide midfielders,
wingers and forwards. Right-sided roles are mirrored only in the overarching
profiles; original coordinates remain available in the role-specific profiles.
A league template requires at least two players with five eligible appearances,
so leave-one-out comparison remains possible. Review coverage in
`notebooks/07_remaining_position_template_coverage.ipynb`.

## Validate the remaining supported positions

Run:

```bash
.venv/bin/python scripts/validate_forest_position_groups.py
```

This validates Forest goalkeeper, central-midfield, attacking-midfield,
wide-midfield, winger and forward profiles using bootstrap uncertainty,
split-half stability, layout robustness and separate pass/defensive-action
templates. Defensive midfield is excluded because no valid peer baseline exists.
Review the findings in
`notebooks/08_remaining_position_results_validation.ipynb`.

## Run the Streamlit application

```bash
.venv/bin/streamlit run streamlit_app.py
```

Open the local URL printed in the terminal, normally `http://localhost:8501`. Keep the terminal running while using the application and press `Ctrl+C` to stop it.

## Run the tests

The initial tests use Python's standard-library test runner:

```bash
MPLBACKEND=Agg .venv/bin/python -m unittest discover -s tests -v
```

They validate coordinate handling, zone counts, normalized shares, traditional zone orientation, template averaging, leave-one-out baselines, similarity calculations and the validation workflow without requiring the licensed data.

## Method summary

- Provider coordinates use an Opta-style 0–100 pitch.
- Shot locations were checked to confirm that teams consistently attack toward `x = 100`.
- Administrative and invalid spatial records are excluded.
- The initial eligibility rule is at least 60 provider minutes.
- There is currently no minimum-action exclusion. Profiles below five eligible appearances are flagged as provisional and do not contribute to the league template.
- Zone values represent shares of direct-action starting locations.
- The positional map contains 20 tactical zones.
- The traditional map contains 18 equal zones arranged as six length bands by three width bands.
- Provider formation codes and lineup slots are decoded separately from the project's standardised position rules.
- Unknown formations, unknown provider positions and bench slot `0` remain explicitly unresolved rather than being guessed.
- Each match profile is normalized to 100%; matches are averaged equally within a player, and qualifying players are averaged equally within each positional league template.
- Qualified Forest players are compared with a leave-one-out template; provisional players are compared with the full qualified template.
- Overall similarity is `100 × (1 − total variation distance)` and describes spatial typicality, not player quality.
- Bootstrap intervals resample complete match appearances rather than individual actions; the league baseline remains fixed, so the interval represents uncertainty in the player's appearance sample rather than uncertainty in the template itself.
- Split-half stability is reported only for players with at least ten eligible appearances.
- Pass-only and defensive-action profiles are recalculated separately to show how action selection affects the result.
- Full-back and wing-back outputs retain side-specific templates and add a role-normalised overarching template by mirroring right-sided width coordinates onto the left.

## Current limitations

- The Streamlit match explorer displays Nottingham Forest defenders; the comparison view covers centre-backs, full-backs, wing-backs, goalkeepers, supported midfield roles, wingers and forwards.
- The position mapping currently classifies starting formation slots; substitute slot `0` and later in-match role changes still need additional provider events.
- Two Forest match payloads are missing.
- Carries have not been inferred.
- High-volume passes may dominate the combined direct-action map, so separate action-family results should accompany interpretation.
- Jair Cunha has only three eligible appearances and remains provisional; his profile cannot yet support split-half validation.
- No Forest player currently has five eligible wing-back appearances, so all Forest wing-back comparisons will initially be provisional.
- The full-back zone layouts broadly agree but are less interchangeable than the centre-back layouts; both should remain available in interpretation.
- The current data cannot support a defensive-midfield league template: only one player reaches five overarching appearances.
- Positional-template comparison is available across the supported groups; role clusters and scouting-performance measures have not yet been added.
- Public deployment is blocked until data-sharing permissions are confirmed.

## Documentation

- [Initial plan and end goal](documentation/initial_plan_and_goal.md)
- [Day 1 progress and learning log](documentation/day_1.md)
- [Source notebook](notebooks/01_forest_defender_data_import.ipynb)
- [Position-mapping validation notebook](notebooks/02_position_mapping_validation.ipynb)
- [Premier League pipeline validation notebook](notebooks/03_premier_league_pipeline_validation.ipynb)
- [Centre-back template validation notebook](notebooks/04_centre_back_template_validation.ipynb)
- [Forest centre-back results validation notebook](notebooks/05_forest_centre_back_results_validation.ipynb)
- [Wide-defender results validation notebook](notebooks/06_wide_defender_results_validation.ipynb)
- [Remaining position-template coverage notebook](notebooks/07_remaining_position_template_coverage.ipynb)
- [Remaining position results validation notebook](notebooks/08_remaining_position_results_validation.ipynb)
- [Third-party mapping attribution](THIRD_PARTY_NOTICES.md)

## Project direction

The long-term objective is a transparent scouting workflow covering club requirements, player search, comparison, shortlisting and evidence-backed reporting. AI assistance is intentionally deferred until the data pipeline and analytical methods are reliable and understood.

## License

No open-source license has been selected for the code. The football data remains subject to its provider and university licensing conditions and is not part of this repository.
