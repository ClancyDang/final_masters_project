"""Reusable football-analysis calculations."""

from .centre_back_templates import (
    CentreBackTemplateResult,
    build_centre_back_templates,
    write_centre_back_template_outputs,
)
from .player_template_comparison import (
    PlayerTemplateComparison,
    compare_player_to_template,
    empirical_percentile,
    total_variation_similarity,
)

__all__ = [
    "CentreBackTemplateResult",
    "build_centre_back_templates",
    "write_centre_back_template_outputs",
    "PlayerTemplateComparison",
    "compare_player_to_template",
    "empirical_percentile",
    "total_variation_similarity",
]
