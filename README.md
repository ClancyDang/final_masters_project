# ScoutAgent

ScoutAgent is a football scouting and recruitment-analysis application being developed as a Final Master Project for the Master's programme in Sport Analysis & Analytics at Universidad Europea de Madrid and the Real Madrid Graduate School.

The current prototype uses Nottingham Forest as its initial club context. It creates interactive defender action-location maps from 2025/26 Premier League event data.

## Prototype status

The application currently allows a user to:

- Select a Nottingham Forest defender.
- Select one of that player's appearances of at least 60 minutes.
- View a positional 20-zone map, a traditional 18-zone map or both.
- Inspect minutes played and the number of direct actions.
- View zone-level counts and normalized action shares.
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
│   └── 02_position_mapping_validation.ipynb
├── scripts/
│   └── build_streamlit_data.py
├── src/
│   ├── positions/
│   │   └── formation_mapping.py
│   └── visualizations/
│       └── positional_maps.py
├── tests/
│   ├── test_formation_mapping.py
│   └── test_positional_maps.py
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

The current build script executes the validated preparation cells from the source notebook. Moving this cleaning logic into a reusable `src/data/` module is planned as a future refactor.

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

They validate coordinate handling, zone counts, normalized shares and traditional zone orientation without requiring the licensed data.

## Method summary

- Provider coordinates use an Opta-style 0–100 pitch.
- Shot locations were checked to confirm that teams consistently attack toward `x = 100`.
- Administrative and invalid spatial records are excluded.
- The initial eligibility rule is at least 60 provider minutes.
- There is currently no minimum-action exclusion or low-sample warning.
- Zone values represent shares of direct-action starting locations.
- The positional map contains 20 tactical zones.
- The traditional map contains 18 equal zones arranged as six length bands by three width bands.
- Provider formation codes and lineup slots are decoded separately from the project's standardised position rules.
- Unknown formations, unknown provider positions and bench slot `0` remain explicitly unresolved rather than being guessed.

## Current limitations

- The initial analysis includes Nottingham Forest defenders only.
- The position mapping currently classifies starting formation slots; substitute slot `0` and later in-match role changes still need additional provider events.
- Two Forest match payloads are missing.
- Carries have not been inferred.
- High-volume passes may dominate the combined direct-action map.
- No league-wide positional templates or role clusters have been created yet.
- Public deployment is blocked until data-sharing permissions are confirmed.

## Documentation

- [Initial plan and end goal](documentation/initial_plan_and_goal.md)
- [Day 1 progress and learning log](documentation/day_1.md)
- [Source notebook](notebooks/01_forest_defender_data_import.ipynb)
- [Position-mapping validation notebook](notebooks/02_position_mapping_validation.ipynb)
- [Third-party mapping attribution](THIRD_PARTY_NOTICES.md)

## Project direction

The long-term objective is a transparent scouting workflow covering club requirements, player search, comparison, shortlisting and evidence-backed reporting. AI assistance is intentionally deferred until the data pipeline and analytical methods are reliable and understood.

## License

No open-source license has been selected for the code. The football data remains subject to its provider and university licensing conditions and is not part of this repository.
