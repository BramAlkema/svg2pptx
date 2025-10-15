"""Curve text algorithms refactor package."""

from .curve_sampling import (
    PathSamplingMethod,
    PathSegment,
    fallback_horizontal_line,
    parse_path_segments,
    sample_path_deterministic,
    sample_path_proportional,
)
from .bezier_utils import (
    evaluate_line_segment,
    evaluate_cubic_segment,
    evaluate_quadratic_segment,
    interpolate_angle,
)
from .positioning import CurveTextPositioner, create_curve_text_positioner
from .rotation import rotation_angles, normalize_angle
from .collision import detect_collisions
from .warp_fitting import PathWarpFitter, WarpFitResult, create_path_warp_fitter

__all__ = [
    "CurveTextPositioner",
    "create_curve_text_positioner",
    "PathSamplingMethod",
    "PathSegment",
    "parse_path_segments",
    "sample_path_deterministic",
    "sample_path_proportional",
    "fallback_horizontal_line",
    "evaluate_line_segment",
    "evaluate_cubic_segment",
    "evaluate_quadratic_segment",
    "interpolate_angle",
    "rotation_angles",
    "normalize_angle",
    "detect_collisions",
    "PathWarpFitter",
    "WarpFitResult",
    "create_path_warp_fitter",
]
