"""Interactive Nottingham Forest positional-map prototype."""

from pathlib import Path

import pandas as pd
import streamlit as st

from src.visualizations.positional_maps import (
    LAYOUT_BOTH,
    LAYOUT_OPTIONS,
    build_action_location_figure,
    close_figure,
)


PROJECT_ROOT = Path(__file__).resolve().parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
APPEARANCE_PATH = PROCESSED_DIR / "forest_eligible_defender_appearances.parquet"
ACTION_PATH = PROCESSED_DIR / "forest_eligible_positional_actions.parquet"


st.set_page_config(
    page_title="ScoutAgent | Forest positional maps",
    page_icon="⚽",
    layout="wide",
)


@st.cache_data
def load_prototype_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    appearances = pd.read_parquet(APPEARANCE_PATH)
    actions = pd.read_parquet(ACTION_PATH)
    appearances["match_date"] = pd.to_datetime(appearances["match_date"])
    actions["match_date"] = pd.to_datetime(actions["match_date"])
    return appearances, actions


st.title("ScoutAgent: Nottingham Forest defender positional maps")
st.caption(
    "Explore where Forest defenders recorded direct actions during eligible "
    "appearances of at least 60 minutes."
)

if not APPEARANCE_PATH.exists() or not ACTION_PATH.exists():
    st.error(
        "Processed prototype data is missing. Run "
        "`.venv/bin/python scripts/build_streamlit_data.py` from the project root."
    )
    st.stop()

appearances, actions = load_prototype_data()

control_col_1, control_col_2, control_col_3 = st.columns([1, 2, 1.4])

with control_col_1:
    player_names = sorted(appearances["player_name"].dropna().unique())
    default_player_index = player_names.index("Murillo") if "Murillo" in player_names else 0
    selected_player = st.selectbox(
        "Forest defender",
        player_names,
        index=default_player_index,
    )

player_appearances = appearances.loc[
    appearances["player_name"].eq(selected_player)
].sort_values("match_date")
player_appearances = player_appearances.assign(
    match_label=lambda frame: frame.apply(
        lambda row: f"{row['match_date']:%d %b %Y} — {row['match_description']}", axis=1
    )
)

with control_col_2:
    match_labels = player_appearances["match_label"].tolist()
    brentford_index = next(
        (index for index, label in enumerate(match_labels) if "Brentford" in label),
        0,
    )
    selected_match_label = st.selectbox(
        "Eligible match",
        match_labels,
        index=brentford_index,
    )

with control_col_3:
    selected_layout = st.selectbox(
        "Zone layout",
        LAYOUT_OPTIONS,
        index=LAYOUT_OPTIONS.index(LAYOUT_BOTH),
    )

selected_appearance = player_appearances.loc[
    player_appearances["match_label"].eq(selected_match_label)
].iloc[0]
selected_actions = actions.loc[
    actions["match_id"].eq(selected_appearance["match_id"])
    & actions["player_id"].eq(selected_appearance["player_id"])
].copy()

metric_col_1, metric_col_2, metric_col_3 = st.columns(3)
metric_col_1.metric("Minutes played", f"{selected_appearance['minutes_played']:.1f}")
metric_col_2.metric("Direct actions", f"{int(selected_appearance['action_count'])}")
metric_col_3.metric("Eligibility rule", "60+ minutes")

figure, positional_distribution, traditional_distribution = build_action_location_figure(
    selected_actions,
    selected_appearance,
    layout=selected_layout,
)
st.pyplot(figure, width="stretch")
close_figure(figure)

with st.expander("View underlying zone distributions"):
    positional_tab, traditional_tab = st.tabs(
        ["Positional 20-zone", "Traditional 18-zone"]
    )
    with positional_tab:
        st.dataframe(
            positional_distribution,
            hide_index=True,
            width="stretch",
        )
    with traditional_tab:
        st.dataframe(
            traditional_distribution,
            hide_index=True,
            width="stretch",
        )

with st.expander("Method and limitations"):
    st.markdown(
        """
        - An appearance is eligible when the defender played at least 60 provider minutes.
        - Percentages describe the starting locations of recorded direct actions.
        - They do **not** measure continuous time spent in each zone; that would require tracking data.
        - There is currently no minimum-action exclusion or low-sample warning.
        - Opta coordinates were validated as attacking toward `x = 100` for both teams and halves.
        """
    )
