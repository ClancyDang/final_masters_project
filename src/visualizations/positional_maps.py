"""Reusable 18-zone and 20-zone defender action-location maps."""

from __future__ import annotations

import matplotlib.patheffects as path_effects
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from mplsoccer import VerticalPitch


LAYOUT_BOTH = "Both layouts"
LAYOUT_POSITIONAL = "Positional 20-zone"
LAYOUT_TRADITIONAL = "Traditional 18-zone"
LAYOUT_OPTIONS = (LAYOUT_BOTH, LAYOUT_POSITIONAL, LAYOUT_TRADITIONAL)
PROFILE_LAYOUT_LABELS = {
    "positional_20": LAYOUT_POSITIONAL,
    "traditional_18": LAYOUT_TRADITIONAL,
}


def _validate_actions(actions: pd.DataFrame, appearance: pd.Series) -> None:
    required_columns = {"x", "y"}
    missing_columns = required_columns.difference(actions.columns)
    if missing_columns:
        raise ValueError(f"Action table is missing columns: {sorted(missing_columns)}")
    if actions.empty:
        raise ValueError("The selected appearance has no positional actions")
    if not actions["x"].between(0, 100).all() or not actions["y"].between(0, 100).all():
        raise ValueError("All action coordinates must be inside the Opta 0–100 pitch")
    if len(actions) != int(appearance["action_count"]):
        raise ValueError("Filtered actions do not match the appearance action count")


def _build_distributions(
    pitch: VerticalPitch,
    actions: pd.DataFrame,
) -> tuple[dict, dict, pd.DataFrame, pd.DataFrame]:
    positional_bins = pitch.bin_statistic_positional(
        actions["x"],
        actions["y"],
        statistic="count",
        positional="full",
        normalize=True,
    )
    positional_distribution = pd.DataFrame(
        {
            "zone_id": np.arange(1, 21),
            "zone_name": positional_bins["names"],
            "center_x": positional_bins["cx"],
            "center_y": positional_bins["cy"],
            "action_count": positional_bins["count"].astype(int),
            "action_share": positional_bins["statistic"],
        }
    )

    traditional_bins = pitch.bin_statistic(
        actions["x"],
        actions["y"],
        statistic="count",
        bins=(6, 3),
        normalize=True,
    )

    traditional_actions = actions[["x", "y"]].copy()
    traditional_actions["length_band"] = np.minimum(
        np.floor(traditional_actions["x"] / (100 / 6)).astype(int), 5
    )
    traditional_actions["raw_width_band"] = np.minimum(
        np.floor(traditional_actions["y"] / (100 / 3)).astype(int), 2
    )
    traditional_actions["zone_id"] = (
        traditional_actions["length_band"] * 3
        + (2 - traditional_actions["raw_width_band"])
        + 1
    )

    traditional_distribution = (
        traditional_actions.groupby("zone_id")
        .size()
        .reindex(range(1, 19), fill_value=0)
        .rename("action_count")
        .reset_index()
    )
    traditional_distribution["action_share"] = (
        traditional_distribution["action_count"]
        / traditional_distribution["action_count"].sum()
    )
    traditional_distribution["length_band"] = (
        (traditional_distribution["zone_id"] - 1) // 3
    )
    traditional_distribution["width_band"] = (
        (traditional_distribution["zone_id"] - 1) % 3
    )
    traditional_distribution["center_x"] = (
        traditional_distribution["length_band"] + 0.5
    ) * (100 / 6)
    traditional_distribution["center_y"] = (
        2.5 - traditional_distribution["width_band"]
    ) * (100 / 3)

    if positional_distribution["action_count"].sum() != len(actions):
        raise ValueError("The positional layout did not retain every action")
    if traditional_distribution["action_count"].sum() != len(actions):
        raise ValueError("The traditional layout did not retain every action")
    if not np.isclose(positional_distribution["action_share"].sum(), 1):
        raise ValueError("The positional action shares do not sum to one")
    if not np.isclose(traditional_distribution["action_share"].sum(), 1):
        raise ValueError("The traditional action shares do not sum to one")

    return positional_bins, traditional_bins, positional_distribution, traditional_distribution


def _annotate_zones(
    pitch: VerticalPitch,
    axis,
    distribution: pd.DataFrame,
    label_effects: list,
) -> None:
    for zone in distribution.itertuples(index=False):
        pitch.annotate(
            f"Z{zone.zone_id:02d}\n{zone.action_share:.1%}",
            xy=(zone.center_x, zone.center_y),
            ax=axis,
            color="white",
            fontsize=8.5,
            fontweight="bold",
            ha="center",
            va="center",
            path_effects=label_effects,
            zorder=4,
        )


def build_action_location_figure(
    actions: pd.DataFrame,
    appearance: pd.Series,
    layout: str = LAYOUT_BOTH,
):
    """Return the selected map figure and both underlying zone tables."""
    if layout not in LAYOUT_OPTIONS:
        raise ValueError(f"Unknown layout: {layout}")
    _validate_actions(actions, appearance)

    pitch = VerticalPitch(
        pitch_type="opta",
        pitch_color="#22312b",
        line_color="white",
        line_zorder=2,
    )
    (
        positional_bins,
        traditional_bins,
        positional_distribution,
        traditional_distribution,
    ) = _build_distributions(pitch, actions)

    shared_vmax = max(
        np.nanmax(positional_bins["statistic"]),
        np.nanmax(traditional_bins["statistic"]),
    )
    label_effects = [
        path_effects.Stroke(linewidth=2.5, foreground="black"),
        path_effects.Normal(),
    ]

    plots: list[tuple[str, dict, pd.DataFrame]] = []
    if layout in (LAYOUT_BOTH, LAYOUT_POSITIONAL):
        plots.append((LAYOUT_POSITIONAL, positional_bins, positional_distribution))
    if layout in (LAYOUT_BOTH, LAYOUT_TRADITIONAL):
        plots.append((LAYOUT_TRADITIONAL, traditional_bins, traditional_distribution))

    figure_width = 12 if len(plots) == 2 else 6
    figure, axes = pitch.draw(nrows=1, ncols=len(plots), figsize=(figure_width, 8))
    axes = np.atleast_1d(axes)

    for axis, (plot_name, bins, distribution) in zip(axes, plots):
        if plot_name == LAYOUT_POSITIONAL:
            pitch.heatmap_positional(
                bins,
                ax=axis,
                cmap="cividis",
                edgecolors="#22312b",
                vmin=0,
                vmax=shared_vmax,
            )
        else:
            pitch.heatmap(
                bins,
                ax=axis,
                cmap="cividis",
                edgecolors="#22312b",
                vmin=0,
                vmax=shared_vmax,
            )

        pitch.scatter(
            actions["x"],
            actions["y"],
            ax=axis,
            color="white",
            s=8,
            alpha=0.35,
            zorder=3,
        )
        _annotate_zones(pitch, axis, distribution, label_effects)
        axis.set_title(f"{plot_name} layout", color="white", fontsize=14, pad=10)

    match_date = pd.Timestamp(appearance["match_date"])
    figure.patch.set_facecolor("#22312b")
    figure.suptitle(
        f"{appearance['player_name']} — {appearance['match_description']}",
        color="white",
        fontsize=17,
        y=0.98,
    )
    figure.text(
        0.5,
        0.94,
        (
            f"{match_date:%d %B %Y} | "
            f"{appearance['minutes_played']:.1f} minutes | "
            f"{int(appearance['action_count'])} direct actions"
        ),
        color="#d9e2df",
        fontsize=11,
        ha="center",
    )
    figure.text(
        0.5,
        0.02,
        "Values show each zone's share of recorded direct-action start locations.",
        color="#d9e2df",
        fontsize=10,
        ha="center",
    )
    figure.subplots_adjust(top=0.88, bottom=0.07, wspace=0.08)

    return figure, positional_distribution, traditional_distribution


def close_figure(figure) -> None:
    """Release a Matplotlib figure after Streamlit has rendered it."""
    plt.close(figure)


def _profile_bins(
    pitch: VerticalPitch,
    zone_comparison: pd.DataFrame,
    value_column: str,
    layout: str,
) -> dict:
    if layout == "positional_20":
        return pitch.bin_statistic_positional(
            zone_comparison["center_x"],
            zone_comparison["center_y"],
            values=zone_comparison[value_column],
            statistic="sum",
            positional="full",
            normalize=False,
        )
    if layout == "traditional_18":
        return pitch.bin_statistic(
            zone_comparison["center_x"],
            zone_comparison["center_y"],
            values=zone_comparison[value_column],
            statistic="sum",
            bins=(6, 3),
            normalize=False,
        )
    raise ValueError(f"Unknown profile layout: {layout}")


def _draw_profile_heatmap(
    pitch: VerticalPitch,
    bins: dict,
    axis,
    layout: str,
    cmap: str,
    vmin: float,
    vmax: float,
) -> None:
    if layout == "positional_20":
        pitch.heatmap_positional(
            bins,
            ax=axis,
            cmap=cmap,
            edgecolors="#22312b",
            vmin=vmin,
            vmax=vmax,
        )
    else:
        pitch.heatmap(
            bins,
            ax=axis,
            cmap=cmap,
            edgecolors="#22312b",
            vmin=vmin,
            vmax=vmax,
        )


def build_player_template_comparison_figure(
    zone_comparison: pd.DataFrame,
    player_name: str,
    layout: str,
):
    """Return player, independent baseline, and difference pitch maps."""
    required = {
        "zone_id",
        "center_x",
        "center_y",
        "player_share",
        "template_share",
        "difference",
    }
    missing = required.difference(zone_comparison.columns)
    if missing:
        raise ValueError(f"Zone comparison is missing columns: {sorted(missing)}")
    if layout not in PROFILE_LAYOUT_LABELS:
        raise ValueError(f"Unknown profile layout: {layout}")
    expected_zones = 20 if layout == "positional_20" else 18
    if len(zone_comparison) != expected_zones:
        raise ValueError(f"{layout} requires exactly {expected_zones} zones")

    pitch = VerticalPitch(
        pitch_type="opta",
        pitch_color="#22312b",
        line_color="white",
        line_zorder=2,
    )
    player_bins = _profile_bins(pitch, zone_comparison, "player_share", layout)
    template_bins = _profile_bins(pitch, zone_comparison, "template_share", layout)
    difference_bins = _profile_bins(pitch, zone_comparison, "difference", layout)

    sequential_max = max(
        float(zone_comparison["player_share"].max()),
        float(zone_comparison["template_share"].max()),
    )
    difference_max = max(float(zone_comparison["difference"].abs().max()), 0.01)
    label_effects = [
        path_effects.Stroke(linewidth=2.5, foreground="black"),
        path_effects.Normal(),
    ]

    figure, axes = pitch.draw(nrows=1, ncols=3, figsize=(15, 8.5))
    axes = np.atleast_1d(axes)
    panels = [
        ("Player profile", player_bins, "player_share", "cividis", 0, sequential_max),
        (
            "League CB baseline",
            template_bins,
            "template_share",
            "cividis",
            0,
            sequential_max,
        ),
        (
            "Difference from baseline",
            difference_bins,
            "difference",
            "RdBu_r",
            -difference_max,
            difference_max,
        ),
    ]

    for axis, (title, bins, value_column, cmap, vmin, vmax) in zip(axes, panels):
        _draw_profile_heatmap(pitch, bins, axis, layout, cmap, vmin, vmax)
        for zone in zone_comparison.itertuples(index=False):
            value = getattr(zone, value_column)
            value_label = f"{value:+.1%}" if value_column == "difference" else f"{value:.1%}"
            pitch.annotate(
                f"Z{zone.zone_id:02d}\n{value_label}",
                xy=(zone.center_x, zone.center_y),
                ax=axis,
                color="white",
                fontsize=7.5,
                fontweight="bold",
                ha="center",
                va="center",
                path_effects=label_effects,
                zorder=4,
            )
        axis.set_title(title, color="white", fontsize=13, pad=8)

    figure.patch.set_facecolor("#22312b")
    figure.suptitle(
        f"{player_name} compared with the Premier League centre-back template",
        color="white",
        fontsize=16,
        y=0.985,
    )
    figure.text(
        0.5,
        0.015,
        "Difference map: red = higher share than the baseline; blue = lower share.",
        color="#d9e2df",
        fontsize=10,
        ha="center",
    )
    figure.subplots_adjust(top=0.79, bottom=0.07, wspace=0.06)
    return figure
