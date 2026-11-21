"""Interactive Nottingham Forest positional-profile prototype."""

from pathlib import Path

import pandas as pd
import streamlit as st

from src.analysis.player_template_comparison import compare_player_to_template
from src.visualizations.positional_maps import (
    LAYOUT_BOTH,
    LAYOUT_OPTIONS,
    build_action_location_figure,
    build_player_template_comparison_figure,
    close_figure,
)


PROJECT_ROOT = Path(__file__).resolve().parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
APPEARANCE_PATH = PROCESSED_DIR / "forest_eligible_defender_appearances.parquet"
ACTION_PATH = PROCESSED_DIR / "forest_eligible_positional_actions.parquet"
CB_PROFILE_PATH = PROCESSED_DIR / "centre_back_player_zone_profiles.parquet"

VIEW_MATCH = "Match explorer"
VIEW_COMPARISON = "League comparison"
COMPARISON_LAYOUTS = {
    "Positional 20-zone": "positional_20",
    "Traditional 18-zone": "traditional_18",
}


def format_ordinal(value: float) -> str:
    """Format a rounded percentile with the correct English suffix."""
    number = int(round(value))
    suffix = (
        "th"
        if 10 <= number % 100 <= 20
        else {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    )
    return f"{number}{suffix}"


st.set_page_config(
    page_title="ScoutAgent | Forest positional profiles",
    page_icon="⚽",
    layout="wide",
)


@st.cache_data
def load_match_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load the processed Forest match-level prototype tables."""
    appearances = pd.read_parquet(APPEARANCE_PATH)
    actions = pd.read_parquet(ACTION_PATH)
    appearances["match_date"] = pd.to_datetime(appearances["match_date"])
    actions["match_date"] = pd.to_datetime(actions["match_date"])
    return appearances, actions


@st.cache_data
def load_centre_back_profiles() -> pd.DataFrame:
    """Load league centre-back player profiles for comparison."""
    return pd.read_parquet(CB_PROFILE_PATH)


heading_col, view_col = st.columns([1.6, 1], vertical_alignment="bottom")
heading_col.header("ScoutAgent · Forest positional profiles")
with view_col:
    selected_view = st.segmented_control(
        "Analysis view",
        [VIEW_MATCH, VIEW_COMPARISON],
        default=VIEW_MATCH,
        required=True,
        key="analysis_view",
        width="stretch",
    )

if selected_view == VIEW_MATCH:
    if not APPEARANCE_PATH.exists() or not ACTION_PATH.exists():
        st.error(
            "Processed match data is missing. Run "
            "`.venv/bin/python scripts/build_streamlit_data.py` from the project root."
        )
        st.stop()

    appearances, actions = load_match_data()
    control_col_1, control_col_2, control_col_3 = st.columns(
        [1, 2, 1.4],
        vertical_alignment="bottom",
        gap="small",
    )

    with control_col_1:
        player_names = sorted(appearances["player_name"].dropna().unique())
        default_player_index = (
            player_names.index("Murillo") if "Murillo" in player_names else 0
        )
        selected_player = st.selectbox(
            "Forest defender",
            player_names,
            index=default_player_index,
            key="match_player",
        )

    player_appearances = appearances.loc[
        appearances["player_name"].eq(selected_player)
    ].sort_values("match_date")
    player_appearances = player_appearances.assign(
        match_label=lambda frame: frame.apply(
            lambda row: (
                f"{row['match_date']:%d %b %Y} — {row['match_description']}"
            ),
            axis=1,
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
            key="eligible_match",
        )

    with control_col_3:
        selected_layout = st.selectbox(
            "Zone layout",
            LAYOUT_OPTIONS,
            index=LAYOUT_OPTIONS.index(LAYOUT_BOTH),
            key="match_layout",
        )

    selected_appearance = player_appearances.loc[
        player_appearances["match_label"].eq(selected_match_label)
    ].iloc[0]
    selected_actions = actions.loc[
        actions["match_id"].eq(selected_appearance["match_id"])
        & actions["player_id"].eq(selected_appearance["player_id"])
    ].copy()

    metric_col_1, metric_col_2, metric_col_3 = st.columns(3, gap="small")
    metric_col_1.metric(
        "Minutes played",
        f"{selected_appearance['minutes_played']:.1f}",
        border=False,
    )
    metric_col_2.metric(
        "Direct actions",
        f"{int(selected_appearance['action_count'])}",
        border=False,
    )
    metric_col_3.metric("Eligibility rule", "60+ minutes", border=False)

    figure, positional_distribution, traditional_distribution = (
        build_action_location_figure(
            selected_actions,
            selected_appearance,
            layout=selected_layout,
        )
    )
    chart_width = 1100 if selected_layout == LAYOUT_BOTH else 560
    with st.container(horizontal_alignment="center"):
        st.pyplot(
            figure,
            width=chart_width,
            alt=f"Action-location maps for {selected_player} in the selected match",
        )
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
                alt="Positional 20-zone action distribution",
            )
        with traditional_tab:
            st.dataframe(
                traditional_distribution,
                hide_index=True,
                width="stretch",
                alt="Traditional 18-zone action distribution",
            )

    with st.expander("Method and limitations"):
        st.markdown(
            """
            - An appearance is eligible when the defender played at least 60 provider minutes.
            - Percentages describe the starting locations of recorded direct actions.
            - They do **not** measure continuous time spent in each zone; that would require tracking data.
            - Opta coordinates were validated as attacking toward `x = 100` for both teams and halves.
            """
        )

else:
    if not CB_PROFILE_PATH.exists():
        st.error(
            "Centre-back profiles are missing. Run "
            "`.venv/bin/python scripts/build_centre_back_templates.py` from the project root."
        )
        st.stop()

    player_profiles = load_centre_back_profiles()
    forest_profiles = player_profiles.loc[
        player_profiles["teams"].str.contains("Nottingham Forest", na=False)
    ]
    forest_players = (
        forest_profiles[["player_id", "player_name"]]
        .drop_duplicates()
        .sort_values("player_name")
    )
    player_lookup = dict(
        zip(forest_players["player_name"], forest_players["player_id"])
    )

    control_col_1, control_col_2 = st.columns(
        2,
        vertical_alignment="bottom",
        gap="small",
    )
    with control_col_1:
        comparison_player = st.selectbox(
            "Forest centre-back",
            list(player_lookup),
            index=(
                list(player_lookup).index("Murillo")
                if "Murillo" in player_lookup
                else 0
            ),
            key="comparison_player",
        )
    with control_col_2:
        comparison_layout_label = st.segmented_control(
            "Zone layout",
            list(COMPARISON_LAYOUTS),
            default="Positional 20-zone",
            required=True,
            key="comparison_layout",
            width="stretch",
        )

    comparison = compare_player_to_template(
        player_profiles,
        player_lookup[comparison_player],
        COMPARISON_LAYOUTS[comparison_layout_label],
    )

    if comparison.provisional:
        st.warning(
            (
                f"{comparison.player_name} has {comparison.eligible_appearances} eligible "
                f"centre-back appearances, below the {comparison.minimum_template_appearances}-"
                "appearance template threshold. The comparison is shown, but the player did "
                "not contribute to the league baseline."
            ),
            title="Provisional player profile",
            icon=":material/info:",
        )

    metric_col_1, metric_col_2, metric_col_3, metric_col_4 = st.columns(
        4,
        gap="small",
    )
    metric_col_1.metric(
        "Template similarity",
        f"{comparison.similarity_score:.1f}/100",
        border=False,
        help="100 means an identical zone distribution; 0 means no overlap.",
    )
    metric_col_2.metric(
        "Typicality percentile",
        format_ordinal(comparison.similarity_percentile),
        border=False,
        help="Rank of the similarity score among qualified league centre-backs.",
    )
    metric_col_3.metric(
        "Eligible appearances",
        comparison.eligible_appearances,
        border=False,
        help=(
            f"{format_ordinal(comparison.appearance_count_percentile)} percentile among all "
            "centre-back player profiles."
        ),
    )
    metric_col_4.metric(
        "Direct actions",
        comparison.total_actions,
        border=False,
        help=(
            f"{format_ordinal(comparison.action_count_percentile)} percentile among all "
            "centre-back player profiles."
        ),
    )
    comparison_figure = build_player_template_comparison_figure(
        comparison.zone_comparison,
        comparison.player_name,
        comparison.layout,
    )
    with st.container(horizontal_alignment="center"):
        st.pyplot(
            comparison_figure,
            width=1200,
            alt=(
                f"{comparison.player_name} action-location profile, league centre-back "
                "baseline, and zone differences"
            ),
        )
    close_figure(comparison_figure)

    table = comparison.zone_comparison[
        [
            "zone_id",
            "player_share",
            "template_share",
            "difference",
            "zone_percentile",
            "peer_p25",
            "peer_p75",
        ]
    ].copy()
    for column in [
        "player_share",
        "template_share",
        "difference",
        "peer_p25",
        "peer_p75",
    ]:
        table[column] = table[column] * 100
    table = table.rename(
        columns={
            "zone_id": "Zone",
            "player_share": "Player share (%)",
            "template_share": "Baseline share (%)",
            "difference": "Difference (pp)",
            "zone_percentile": "Zone percentile",
            "peer_p25": "Peer p25 (%)",
            "peer_p75": "Peer p75 (%)",
        }
    )

    with st.expander("View zone-by-zone comparison"):
        st.dataframe(
            table,
            hide_index=True,
            width="stretch",
            column_config={
                "Zone": st.column_config.NumberColumn(format="Z%02d"),
                "Player share (%)": st.column_config.NumberColumn(format="%.1f"),
                "Baseline share (%)": st.column_config.NumberColumn(format="%.1f"),
                "Difference (pp)": st.column_config.NumberColumn(format="%+.1f"),
                "Zone percentile": st.column_config.NumberColumn(format="%.0f"),
                "Peer p25 (%)": st.column_config.NumberColumn(format="%.1f"),
                "Peer p75 (%)": st.column_config.NumberColumn(format="%.1f"),
            },
            alt=f"Zone-by-zone centre-back template comparison for {comparison.player_name}",
        )

    with st.expander("How this comparison is calculated"):
        baseline_description = (
            f"the other {comparison.baseline_player_count} qualified league centre-backs"
            if comparison.baseline_method == "leave_one_out"
            else f"all {comparison.baseline_player_count} qualified league centre-backs"
        )
        st.markdown(
            f"""
            - A player's profile is the equal-weighted average of their eligible centre-back appearances.
            - This player's baseline is the equal-weighted mean of {baseline_description}.
            - Zone difference is `player share − baseline share`, shown in percentage points.
            - Similarity is `100 × (1 − total variation distance)` across all zones.
            - A higher similarity score means a more conventional spatial profile, not a better player.
            - Zone percentiles compare the player's share with the independent peer distribution.
            - Only high-confidence centre-back appearances of at least 60 minutes are used.
            """
        )
