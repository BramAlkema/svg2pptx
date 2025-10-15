"""Modernized viewbox package scaffolding for module slicing refactor."""

from __future__ import annotations

from .config import ViewBoxConfig
from .fluent import ViewBoxBuilder, ViewBoxPlan, ViewportBuilder
from .core import ViewBoxEngine, resolve_viewports
from .parsing import (
    normalize_inputs,
    parse_preserve_aspect_ratio,
    parse_preserve_aspect_ratio_batch,
    parse_viewbox_strings,
    parse_viewbox_token,
)
from .coordinate_transform import svg_to_emu
from .batch_ops import resolve_svg_viewports, extract_viewboxes, extract_par_settings
from .advanced_ops import (
    calculate_shape_bounding_box_and_relative_coords,
    vectorized_meet_slice_calculations,
)
from .benchmarks import benchmark_parsing, benchmark_batch
from .memory import get_memory_usage

__all__ = [
    "ViewBoxConfig",
    "ViewBoxBuilder",
    "ViewBoxPlan",
    "ViewportBuilder",
    "ViewBoxEngine",
    "resolve_viewports",
    "parse_viewbox_strings",
    "parse_viewbox_token",
    "parse_preserve_aspect_ratio",
    "parse_preserve_aspect_ratio_batch",
    "normalize_inputs",
    "svg_to_emu",
    "extract_viewboxes",
    "extract_par_settings",
    "resolve_svg_viewports",
    "calculate_shape_bounding_box_and_relative_coords",
    "vectorized_meet_slice_calculations",
    "benchmark_parsing",
    "benchmark_batch",
    "get_memory_usage",
]
