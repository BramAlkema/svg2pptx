#!/usr/bin/env python3
"""
CSS Style Resolver

Provides helpers to parse inline CSS, compute inherited styles, and normalize
property values (colors, fonts, units). Designed to be extended with broader
CSS support as the pipeline evolves.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, Optional, Tuple

import tinycss2

from ..color.css_colors import get_css_color
from ..units.core import ConversionContext, UnitConverter

# --------------------------------------------------------------------------- #
# Utility parsers                                                            #
# --------------------------------------------------------------------------- #


def parse_color(value: str | None, default: str = "000000") -> str:
    """Parse CSS color tokens into an RRGGBB hex string."""
    if not value:
        return default

    raw = value.strip()
    if not raw or raw.lower() == "none":
        return default

    if raw.startswith("#"):
        hex_part = raw[1:]
        if len(hex_part) == 3 and re.fullmatch(r"[0-9a-fA-F]{3}", hex_part):
            expanded = "".join(c * 2 for c in hex_part)
            return expanded.upper()
        if len(hex_part) == 6 and re.fullmatch(r"[0-9a-fA-F]{6}", hex_part):
            return hex_part.upper()
        return default

    rgb_match = re.fullmatch(
        r"rgba?\(\s*([0-9.+%-]+)\s*,\s*([0-9.+%-]+)\s*,\s*([0-9.+%-]+)(?:\s*,\s*([0-9.+%-]+))?\s*\)",
        raw,
        flags=re.IGNORECASE,
    )
    if rgb_match:
        def channel(token: str) -> int:
            token = token.strip()
            if token.endswith("%"):
                pct = float(token[:-1])
                return max(0, min(255, int(round(pct / 100.0 * 255))))
            return max(0, min(255, int(round(float(token)))))

        try:
            r = channel(rgb_match.group(1))
            g = channel(rgb_match.group(2))
            b = channel(rgb_match.group(3))
            return f"{r:02X}{g:02X}{b:02X}"
        except (TypeError, ValueError):
            return default

    named = get_css_color(raw)
    if named:
        r, g, b = named
        return f"{r:02X}{g:02X}{b:02X}"

    return default


def parse_font_size(value: str | None, base_pt: float = 12.0) -> float:
    """Normalize CSS font-size to points."""
    if not value:
        return base_pt

    token = value.strip().lower()
    try:
        if token.endswith("px"):
            return float(token[:-2]) * 0.75  # Assuming 96dpi
        if token.endswith("pt"):
            return float(token[:-2])
        if token.endswith("em"):
            return float(token[:-2]) * base_pt
        if token.endswith("%"):
            return base_pt * float(token[:-1]) / 100.0
        return float(token)
    except ValueError:
        return base_pt


def normalize_font_weight(value: str | None) -> str:
    """Normalize CSS font-weight into canonical tokens used in the pipeline."""
    if not value:
        return "normal"

    token = value.strip().lower()
    weight_map = {
        "100": "lighter",
        "200": "lighter",
        "300": "light",
        "400": "normal",
        "500": "normal",
        "600": "semibold",
        "700": "bold",
        "800": "bolder",
        "900": "bolder",
    }
    return weight_map.get(token, token)


# --------------------------------------------------------------------------- #
# Style resolver                                                             #
# --------------------------------------------------------------------------- #


PropertyHandler = Callable[[str], object]


@dataclass(frozen=True)
class PropertyDescriptor:
    """Maps CSS property names to resolver keys and parsers."""

    key: str
    parser: PropertyHandler


@dataclass(frozen=True)
class StyleContext:
    """Context information for resolving CSS lengths and percentages."""

    conversion: ConversionContext
    viewport_width: float
    viewport_height: float


class StyleResolver:
    """Compute styles for SVG elements with basic inheritance."""

    _TEXT_DEFAULTS: Dict[str, object] = {
        "font_family": "Arial",
        "font_size_pt": 12.0,
        "font_weight": "normal",
        "font_style": "normal",
        "text_decoration": "none",
        "fill": "000000",
    }

    _TEXT_ATTRIBUTE_MAP: Dict[str, PropertyDescriptor] = {
        "font-family": PropertyDescriptor("font_family", lambda v: v.strip('"\'')),
        "font-size": PropertyDescriptor("font_size_pt", parse_font_size),
        "font-weight": PropertyDescriptor("font_weight", normalize_font_weight),
        "font-style": PropertyDescriptor("font_style", lambda v: v.strip()),
        "text-decoration": PropertyDescriptor("text_decoration", lambda v: v.strip()),
        "fill": PropertyDescriptor("fill", parse_color),
    }

    _TEXT_CSS_MAP: Dict[str, PropertyDescriptor] = {
        "font-family": PropertyDescriptor("font_family", lambda v: v.strip('"\'')),
        "font-size": PropertyDescriptor("font_size_pt", parse_font_size),
        "font-weight": PropertyDescriptor("font_weight", normalize_font_weight),
        "font-style": PropertyDescriptor("font_style", lambda v: v.strip()),
        "text-decoration": PropertyDescriptor("text_decoration", lambda v: v.strip()),
        "fill": PropertyDescriptor("fill", parse_color),
    }

    def __init__(self, unit_converter: UnitConverter | None = None) -> None:
        self.unit_converter = unit_converter or UnitConverter()

    # ------------------------------------------------------------------ #
    # Text styling                                                       #
    # ------------------------------------------------------------------ #

    def default_text_style(self) -> Dict[str, object]:
        return dict(self._TEXT_DEFAULTS)

    def compute_text_style(
        self,
        element,
        parent_style: Optional[Dict[str, object]] = None,
    ) -> Dict[str, object]:
        style = dict(parent_style) if parent_style else self.default_text_style()

        for attr, descriptor in self._TEXT_ATTRIBUTE_MAP.items():
            if attr in element.attrib:
                value = element.get(attr)
                if value is not None:
                    self._apply_text_property(style, descriptor, value)

        inline = element.get("style")
        if inline:
            for name, value, _important in self._parse_inline_declarations(inline):
                descriptor = self._TEXT_CSS_MAP.get(name)
                if descriptor and value is not None:
                    self._apply_text_property(style, descriptor, value)

        return style

    # ------------------------------------------------------------------ #
    # Presentation styling                                               #
    # ------------------------------------------------------------------ #

    def compute_paint_style(
        self,
        element,
        context: Optional[StyleContext] = None,
        parent_style: Optional[Dict[str, object]] = None,
    ) -> Dict[str, object]:
        style = dict(parent_style) if parent_style else {
            "fill": "000000",
            "fill_opacity": 1.0,
            "stroke": None,
            "stroke_opacity": 1.0,
            "stroke_width_px": 1.0,
            "opacity": 1.0,
        }

        def apply_fill(value: str | None) -> None:
            if value is None:
                return
            style["fill"] = None if value.strip().lower() == "none" else parse_color(value, style.get("fill", "000000"))

        def apply_stroke(value: str | None) -> None:
            if value is None:
                return
            style["stroke"] = None if value.strip().lower() == "none" else parse_color(value, "000000")

        apply_fill(element.get("fill"))
        apply_stroke(element.get("stroke"))

        fill_opacity = element.get("fill-opacity")
        if fill_opacity is not None:
            style["fill_opacity"] = self._parse_float(fill_opacity, default=style.get("fill_opacity", 1.0))

        stroke_opacity = element.get("stroke-opacity")
        if stroke_opacity is not None:
            style["stroke_opacity"] = self._parse_float(stroke_opacity, default=style.get("stroke_opacity", 1.0))

        stroke_width = element.get("stroke-width")
        if stroke_width is not None:
            style["stroke_width_px"] = self._length_to_px(stroke_width, context, axis="x")

        opacity = element.get("opacity")
        if opacity is not None:
            style["opacity"] = self._parse_float(opacity, default=style.get("opacity", 1.0))

        inline = element.get("style")
        if inline:
            for name, value, _important in self._parse_inline_declarations(inline):
                lname = name.lower()
                if lname == "fill":
                    apply_fill(value)
                elif lname == "fill-opacity":
                    style["fill_opacity"] = self._parse_float(value, default=style.get("fill_opacity", 1.0))
                elif lname == "stroke":
                    apply_stroke(value)
                elif lname == "stroke-opacity":
                    style["stroke_opacity"] = self._parse_float(value, default=style.get("stroke_opacity", 1.0))
                elif lname == "stroke-width":
                    style["stroke_width_px"] = self._length_to_px(value, context, axis="x")
                elif lname == "opacity":
                    style["opacity"] = self._parse_float(value, default=style.get("opacity", 1.0))

        return style

    # ------------------------------------------------------------------ #
    # Internal helpers                                                   #
    # ------------------------------------------------------------------ #

    def _parse_inline_declarations(
        self,
        style_str: str,
    ) -> Iterable[Tuple[str, str, bool]]:
        if not style_str:
            return []

        try:
            declarations = tinycss2.parse_declaration_list(
                style_str,
                skip_whitespace=True,
                skip_comments=True,
            )
        except Exception:
            return []

        result = []
        for decl in declarations:
            if decl.type != "declaration":
                continue
            name = decl.name.lower()
            value = tinycss2.serialize(decl.value).strip()
            result.append((name, value, bool(decl.important)))
        return result

    def _apply_text_property(
        self,
        style: Dict[str, object],
        descriptor: PropertyDescriptor,
        raw_value: str,
    ) -> None:
        if descriptor.parser is parse_font_size:
            current = float(style.get("font_size_pt", 12.0))
            style[descriptor.key] = parse_font_size(raw_value, current)
        else:
            style[descriptor.key] = descriptor.parser(raw_value)

    def _length_to_px(
        self,
        value: str | None,
        context: Optional[StyleContext],
        axis: str = "x",
    ) -> float:
        if value is None:
            return 0.0

        try:
            return float(value)
        except (TypeError, ValueError):
            pass

        if context is None:
            return self._parse_float(value, default=1.0)

        conv = context.conversion
        conversion_ctx = ConversionContext(
            width=context.viewport_width,
            height=context.viewport_height,
            font_size=conv.font_size,
            dpi=conv.dpi,
            parent_width=conv.parent_width or context.viewport_width,
            parent_height=conv.parent_height or context.viewport_height,
        )
        return self.unit_converter.to_pixels(value, conversion_ctx, axis)

    @staticmethod
    def _parse_float(value: str, default: float = 1.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default
