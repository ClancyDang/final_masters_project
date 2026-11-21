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
from .position_group_templates import (
    POSITION_GROUP_ROLES,
    PositionGroupTemplateResult,
    build_position_group_templates,
    write_position_group_template_outputs,
)
from .position_group_validation import (
    PositionGroupValidationResult,
    build_position_group_validation,
    write_position_group_validation_outputs,
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
    "POSITION_GROUP_ROLES",
    "PositionGroupTemplateResult",
    "build_position_group_templates",
    "write_position_group_template_outputs",
    "PositionGroupValidationResult",
    "build_position_group_validation",
    "write_position_group_validation_outputs",
    "WideDefenderTemplateResult",
    "build_wide_defender_templates",
    "write_wide_defender_template_outputs",
    "WideDefenderValidationResult",
    "build_wide_defender_validation",
    "write_wide_defender_validation_outputs",
]
