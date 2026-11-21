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

Do not publish or redistribute raw or processed event data without explicit permission from the provider and the university.
