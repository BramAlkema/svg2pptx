"""Style and viewport helpers for the sliced parser."""

from __future__ import annotations

import re
from typing import Tuple

from lxml import etree as ET

from ..css import StyleContext


class StyleContextBuilder:
    """Builds style contexts and resolves viewport dimensions."""

    def __init__(self, unit_converter) -> None:
        self.unit_converter = unit_converter

    def build(self, svg_root: ET.Element) -> StyleContext:
        width_px, height_px = self.resolve_viewport(svg_root)

        conversion_ctx = self.unit_converter.create_context(
            width=width_px,
            height=height_px,
            font_size=12.0,
            dpi=96.0,
            parent_width=width_px,
            parent_height=height_px,
        )

        return StyleContext(
            conversion=conversion_ctx,
            viewport_width=width_px,
            viewport_height=height_px,
        )

    def resolve_viewport(self, svg_root: ET.Element) -> Tuple[float, float]:
        width_attr = svg_root.get('width')
        height_attr = svg_root.get('height')
        viewbox_attr = svg_root.get('viewBox')

        vb_width = vb_height = None
        if viewbox_attr:
            parts = re.split(r'[\s,]+', viewbox_attr.strip())
            if len(parts) == 4:
                try:
                    _, _, vbw, vbh = map(float, parts)
                    vb_width, vb_height = vbw, vbh
                except ValueError:
                    vb_width = vb_height = None

        default_ctx = self.unit_converter.default_context

        width_px = self._to_pixels(width_attr, default_ctx, 'x')
        height_px = self._to_pixels(height_attr, default_ctx, 'y')

        if width_px is None:
            width_px = vb_width if vb_width is not None else 800.0
        if height_px is None:
            height_px = vb_height if vb_height is not None else 600.0

        return width_px, height_px

    def _to_pixels(self, value: str | None, context, axis: str) -> float | None:
        if not value:
            return None
        try:
            return self.unit_converter.to_pixels(value, context, axis=axis)
        except Exception:
            return None
