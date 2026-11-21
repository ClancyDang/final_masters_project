"""Reusable football-analysis calculations."""

from .centre_back_templates import (
    CentreBackTemplateResult,
    build_centre_back_templates,
    write_centre_back_template_outputs,
)
from .centre_back_validation import (
    CentreBackValidationResult,
    build_centre_back_validation,
    write_centre_back_validation_outputs,
)
from .player_template_comparison import (
    PlayerTemplateComparison,
    compare_player_to_template,
    empirical_percentile,
    total_variation_similarity,
)
from .wide_defender_templates import (
    WideDefenderTemplateResult,
    build_wide_defender_templates,
    write_wide_defender_template_outputs,
)
from .wide_defender_validation import (
    WideDefenderValidationResult,
    build_wide_defender_validation,
    write_wide_defender_validation_outputs,
)

__all__ = [
    "CentreBackTemplateResult",
    "build_centre_back_templates",
    "write_centre_back_template_outputs",
    "CentreBackValidationResult",
    "build_centre_back_validation",
    "write_centre_back_validation_outputs",
    "PlayerTemplateComparison",
    "compare_player_to_template",
    "empirical_percentile",
    "total_variation_similarity",
    "WideDefenderTemplateResult",
    "build_wide_defender_templates",
    "write_wide_defender_template_outputs",
    "WideDefenderValidationResult",
    "build_wide_defender_validation",
    "write_wide_defender_validation_outputs",
]
