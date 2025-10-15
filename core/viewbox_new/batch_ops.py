"""Batch operations for viewbox transformations."""

from __future__ import annotations

from typing import Iterable, Sequence

import numpy as np
from lxml import etree as ET

from ..units import ConversionContext
from ..viewbox.content_bounds import calculate_content_bounds
from .config import ViewBoxArray, ViewportMappingArray
from .parsing import parse_preserve_aspect_ratio_batch, parse_viewbox_strings


def extract_viewboxes(svg_elements: list[ET.Element]) -> np.ndarray:
    viewboxes = np.zeros(len(svg_elements), dtype=ViewBoxArray)
    for i, svg in enumerate(svg_elements):
        try:
            min_x, min_y, max_x, max_y = calculate_content_bounds(svg)
            width = max_x - min_x
            height = max_y - min_y
            if width > 0 and height > 0:
                aspect_ratio = width / height
                viewboxes[i] = (min_x, min_y, width, height, aspect_ratio)
                continue
        except Exception:
            pass

        viewbox_str = svg.get('viewBox', '0 0 100 100')
        parsed = parse_viewbox_strings(np.array([viewbox_str], dtype=object))[0]
        viewboxes[i] = parsed
    return viewboxes


def extract_par_settings(svg_elements: list[ET.Element]) -> tuple[np.ndarray, np.ndarray]:
    par_strings = np.array(
        [svg.get('preserveAspectRatio', 'xMidYMid meet') for svg in svg_elements],
        dtype=object,
    )
    return parse_preserve_aspect_ratio_batch(par_strings)


def resolve_svg_viewports(
    engine,
    svg_elements: list[ET.Element],
    target_sizes: list[tuple[int, int]] | None = None,
    contexts: list[ConversionContext] | None = None,
) -> np.ndarray:
    viewboxes = extract_viewboxes(svg_elements)
    alignments, meet_slices = extract_par_settings(svg_elements)
    viewports = engine.extract_viewport_dimensions_batch(svg_elements, contexts)

    if target_sizes:
        for i, (width, height) in enumerate(target_sizes):
            if i < len(viewports):
                viewports[i]['width'] = width
                viewports[i]['height'] = height
                viewports[i]['aspect_ratio'] = width / height if height > 0 else 1.0

    return engine.calculate_viewport_mappings_batch(viewboxes, viewports, alignments, meet_slices)


__all__ = [
    "extract_viewboxes",
    "extract_par_settings",
    "resolve_svg_viewports",
]
