"""SVG validation utilities for the sliced parser."""

from __future__ import annotations

from typing import Iterable

from lxml import etree as ET


class SVGValidator:
    """Performs basic structural validation on an SVG element tree."""

    def __init__(self, logger, attribute_checker) -> None:
        self.logger = logger
        self._has_valid_svg_attributes = attribute_checker

    def validate(self, svg_root: ET.Element) -> None:
        root_tag = self._get_local_tag(svg_root.tag)
        if root_tag != 'svg':
            raise ValueError(f"Root element is '{root_tag}', expected 'svg'")

        if 'http://www.w3.org/2000/svg' not in str(getattr(svg_root, 'nsmap', {}) or {}):
            self.logger.warning("SVG namespace not found, adding default namespace")

        if not self._has_valid_svg_attributes(svg_root):
            self.logger.warning("SVG element missing standard attributes (width, height, viewBox)")

    def _get_local_tag(self, tag: str) -> str:
        return tag.split('}', 1)[-1] if '}' in tag else tag
