#!/usr/bin/env python3
"""
Text Layout Preparation Preprocessor

Prepares text elements for conversion by applying the documented fixes
and normalizing text layout complexity.

Features:
- Multi-tspan layout preparation
- Text anchor normalization
- Baseline calculation setup
- Font cascade resolution
"""

import logging
from typing import Optional
from lxml import etree as ET

from .base import BasePreprocessor


class TextLayoutPrepPreprocessor(BasePreprocessor):
    """
    Preprocessor that prepares text elements for optimal conversion.

    Applies the documented text fixes during preprocessing to ensure
    clean text layout before IR conversion.
    """

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)

    def process(self, svg_root: ET.Element) -> ET.Element:
        """
        Prepare text layout in the SVG.

        Args:
            svg_root: SVG root element

        Returns:
            SVG with prepared text layout
        """
        self.logger.debug("Starting text layout preparation")

        # Process all text elements
        text_elements = svg_root.xpath(".//svg:text",
                                     namespaces={'svg': 'http://www.w3.org/2000/svg'})

        for text_elem in text_elements:
            self._prepare_text_element(text_elem)

        self.logger.debug(f"Prepared {len(text_elements)} text elements")
        return svg_root

    def _prepare_text_element(self, text_elem: ET.Element) -> None:
        """Prepare a single text element for conversion."""
        try:
            # 1. Normalize text anchor attribute
            self._normalize_text_anchor(text_elem)

            # 2. Prepare tspan layout
            self._prepare_tspan_layout(text_elem)

            # 3. Calculate baseline positioning metadata
            self._add_baseline_metadata(text_elem)

            # 4. Normalize coordinate attributes
            self._normalize_text_coordinates(text_elem)

            # 5. Resolve font cascade
            self._resolve_font_cascade(text_elem)

        except Exception as e:
            self.logger.warning(f"Text preparation failed for element: {e}")

    def _normalize_text_anchor(self, text_elem: ET.Element) -> None:
        """Normalize text-anchor attribute (Fix #1: Raw anchor handling)."""
        anchor = text_elem.get('text-anchor', 'start')

        # Ensure valid anchor values
        valid_anchors = {'start', 'middle', 'end'}
        if anchor not in valid_anchors:
            text_elem.set('text-anchor', 'start')
            self.logger.debug(f"Normalized invalid text-anchor '{anchor}' to 'start'")

        # Add metadata for downstream processing
        text_elem.set('data-original-anchor', anchor)

    def _prepare_tspan_layout(self, text_elem: ET.Element) -> None:
        """Prepare tspan layout (Fix #2: Per-tspan styling)."""
        # Find all tspan children
        tspan_elements = text_elem.xpath("./svg:tspan",
                                       namespaces={'svg': 'http://www.w3.org/2000/svg'})

        if not tspan_elements:
            # No tspans - add metadata for single run
            text_elem.set('data-text-layout', 'single-run')
            return

        # Process positioned tspans (create line breaks)
        line_break_count = 0
        for i, tspan in enumerate(tspan_elements):
            # Check if tspan has positioning (creates new line)
            if tspan.get('x') is not None or tspan.get('y') is not None:
                tspan.set('data-line-break', 'true')
                line_break_count += 1

            # Add run index for ordering
            tspan.set('data-run-index', str(i))

            # Ensure style inheritance is explicit
            self._ensure_explicit_styling(tspan, text_elem)

        text_elem.set('data-text-layout', 'multi-run')
        text_elem.set('data-line-breaks', str(line_break_count))

    def _add_baseline_metadata(self, text_elem: ET.Element) -> None:
        """Add baseline calculation metadata (Fix #3: Conservative baseline)."""
        # Extract font information for baseline calculation
        font_family = self._get_font_family(text_elem)
        font_size = self._get_font_size(text_elem)

        # Add metadata for conservative baseline calculation
        text_elem.set('data-font-family', font_family)
        text_elem.set('data-font-size', str(font_size))

        # Calculate conservative baseline shift (5% of font size)
        baseline_shift = font_size * 0.05
        text_elem.set('data-baseline-shift', str(baseline_shift))

        # Detect if element has complex positioning
        has_complex_positioning = (
            text_elem.get('dx') is not None or
            text_elem.get('dy') is not None or
            text_elem.get('rotate') is not None
        )
        text_elem.set('data-complex-positioning', str(has_complex_positioning))

    def _normalize_text_coordinates(self, text_elem: ET.Element) -> None:
        """Normalize text coordinate attributes (Fix #4: Coordinate pipeline)."""
        # Ensure x,y attributes are present and numeric
        x = text_elem.get('x', '0')
        y = text_elem.get('y', '0')

        try:
            x_val = float(x)
            y_val = float(y)
        except ValueError:
            x_val, y_val = 0.0, 0.0
            self.logger.warning(f"Invalid text coordinates, defaulting to (0,0)")

        text_elem.set('x', str(x_val))
        text_elem.set('y', str(y_val))

        # Add coordinate system metadata
        text_elem.set('data-coord-system', 'svg-user')

        # Mark for ConversionContext transformation
        text_elem.set('data-needs-coord-transform', 'true')

    def _resolve_font_cascade(self, text_elem: ET.Element) -> None:
        """Resolve font cascade and add fallback metadata."""
        font_family = self._get_font_family(text_elem)

        # Parse font family list
        font_families = [f.strip().strip('"\'') for f in font_family.split(',')]

        # Add primary and fallback fonts
        if font_families:
            text_elem.set('data-primary-font', font_families[0])
            if len(font_families) > 1:
                text_elem.set('data-fallback-fonts', ','.join(font_families[1:]))

        # Add generic fallback
        generic_fallbacks = ['Arial', 'Helvetica', 'sans-serif']
        for fallback in generic_fallbacks:
            if fallback.lower() not in [f.lower() for f in font_families]:
                font_families.append(fallback)

        text_elem.set('data-font-cascade', ','.join(font_families))

    def _ensure_explicit_styling(self, tspan: ET.Element, parent_text: ET.Element) -> None:
        """Ensure tspan has explicit styling (inherits from parent)."""
        # Style attributes that should be inherited
        style_attrs = [
            'font-family', 'font-size', 'font-weight', 'font-style',
            'text-decoration', 'fill', 'stroke', 'opacity'
        ]

        for attr in style_attrs:
            if tspan.get(attr) is None:
                # Check if parent has this attribute
                parent_value = parent_text.get(attr)
                if parent_value:
                    tspan.set(f'data-inherited-{attr}', parent_value)

        # Check CSS style attribute inheritance
        parent_style = parent_text.get('style', '')
        tspan_style = tspan.get('style', '')

        if parent_style and not tspan_style:
            tspan.set('data-inherited-style', parent_style)

    def _get_font_family(self, element: ET.Element) -> str:
        """Extract font family with fallback."""
        # Check attribute first
        font_family = element.get('font-family')
        if font_family:
            return font_family

        # Check CSS style
        style = element.get('style', '')
        if style:
            font_family = self._extract_css_property(style, 'font-family')
            if font_family:
                return font_family

        # Default fallback
        return 'Arial'

    def _get_font_size(self, element: ET.Element) -> float:
        """Extract font size with fallback."""
        # Check attribute first
        font_size = element.get('font-size')
        if font_size:
            return self._parse_font_size(font_size)

        # Check CSS style
        style = element.get('style', '')
        if style:
            font_size = self._extract_css_property(style, 'font-size')
            if font_size:
                return self._parse_font_size(font_size)

        # Default fallback
        return 12.0

    def _parse_font_size(self, size_str: str) -> float:
        """Parse font size string to points."""
        try:
            size_str = size_str.strip().lower()

            if size_str.endswith('pt'):
                return float(size_str[:-2])
            elif size_str.endswith('px'):
                return float(size_str[:-2]) * 0.75  # px to pt approximation
            elif size_str.endswith('em'):
                return float(size_str[:-2]) * 12.0  # em to pt approximation
            elif size_str.endswith('%'):
                return float(size_str[:-1]) / 100.0 * 12.0  # % to pt approximation
            else:
                return float(size_str)
        except ValueError:
            return 12.0

    def _extract_css_property(self, css_style: str, property_name: str) -> Optional[str]:
        """Extract CSS property value from style string."""
        if not css_style:
            return None

        for rule in css_style.split(';'):
            if ':' in rule:
                key, value = rule.split(':', 1)
                if key.strip() == property_name:
                    return value.strip()

        return None


def prepare_text_layout(svg_root: ET.Element) -> ET.Element:
    """
    Convenience function to prepare text layout.

    Args:
        svg_root: SVG root element

    Returns:
        SVG with prepared text layout
    """
    preprocessor = TextLayoutPrepPreprocessor()
    return preprocessor.process(svg_root)