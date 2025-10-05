#!/usr/bin/env python3
"""
FontProcessor utility service for SVG2PPTX.

This module provides centralized font processing functionality,
eliminating duplicate font handling implementations across text converters.
"""

import re
from typing import List, Dict, Any
from dataclasses import dataclass
from lxml import etree as ET


@dataclass
class FontProperties:
    """Structured font properties."""
    family: str
    size: float
    weight: int
    style: str  # 'normal' or 'italic'
    decoration: List[str]


class FontProcessor:
    """
    Centralized font processing service.

    Provides unified font property extraction and processing functionality
    to replace duplicate implementations across text converters.
    """

    def __init__(self):
        """Initialize FontProcessor with font mappings."""
        # Font weight mapping for common values
        self._weight_map = {
            'normal': 400, 'bold': 700, 'bolder': 700, 'lighter': 300,
            '100': 100, '200': 200, '300': 300, '400': 400, '500': 500,
            '600': 600, '700': 700, '800': 800, '900': 900
        }

        # Common font size unit conversions (to points)
        self._size_units = {
            'px': 0.75,    # 1px = 0.75pt
            'pt': 1.0,     # 1pt = 1pt
            'em': 12.0,    # 1em = 12pt (default)
            'rem': 12.0,   # 1rem = 12pt (default)
            'pc': 12.0,    # 1pc = 12pt
            'in': 72.0,    # 1in = 72pt
            'cm': 28.35,   # 1cm = 28.35pt
            'mm': 2.835    # 1mm = 2.835pt
        }

    def extract_font_properties(self, element: ET.Element,
                              style_parser=None, context=None) -> FontProperties:
        """
        Extract comprehensive font properties from SVG element.

        Args:
            element: SVG element
            style_parser: StyleParser service instance
            context: ConversionContext for unit conversion

        Returns:
            FontProperties with all font attributes
        """
        return FontProperties(
            family=self.get_font_family(element, style_parser),
            size=self.get_font_size(element, style_parser, context),
            weight=self.get_font_weight_numeric(element, style_parser),
            style=self.get_font_style(element, style_parser),
            decoration=self.get_text_decoration(element, style_parser)
        )

    def get_font_family(self, element: ET.Element, style_parser=None) -> str:
        """
        Extract font family from element attributes and style.

        Args:
            element: SVG element
            style_parser: StyleParser service instance

        Returns:
            Primary font family name
        """
        # Check direct attribute first
        font_family = element.get('font-family')
        if font_family:
            return self._clean_font_family(font_family)

        # Check style attribute using StyleParser
        if style_parser:
            style = element.get('style', '')
            if 'font-family:' in style:
                font_family = style_parser.extract_font_family(style)
                if font_family:
                    return font_family

        return 'Arial'  # Default font

    def get_font_family_list(self, element: ET.Element, style_parser=None) -> List[str]:
        """
        Extract font family list from element.

        Args:
            element: SVG element
            style_parser: StyleParser service instance

        Returns:
            List of font family names in priority order
        """
        families = []

        # Check direct attribute first
        font_family = element.get('font-family')
        if font_family:
            families.extend(self._parse_font_family_list(font_family))

        # Check style attribute using StyleParser
        if style_parser and not families:
            style = element.get('style', '')
            if 'font-family:' in style:
                font_family = style_parser.extract_font_family(style)
                if font_family:
                    families.extend(self._parse_font_family_list(font_family))

        return families if families else ['Arial']

    def get_font_size(self, element: ET.Element, style_parser=None, context=None) -> float:
        """
        Extract font size in points.

        Args:
            element: SVG element
            style_parser: StyleParser service instance
            context: ConversionContext for unit conversion

        Returns:
            Font size in points
        """
        # Check direct attribute first
        font_size = element.get('font-size')
        if font_size:
            return self._parse_font_size(font_size, context)

        # Check style attribute using StyleParser
        if style_parser:
            style = element.get('style', '')
            if 'font-size:' in style:
                font_size = style_parser.get_property_value(style, 'font-size')
                if font_size:
                    return self._parse_font_size(font_size, context)

        return 12.0  # Default font size

    def get_font_weight_numeric(self, element: ET.Element, style_parser=None) -> int:
        """
        Extract font weight as numeric value.

        Args:
            element: SVG element
            style_parser: StyleParser service instance

        Returns:
            Font weight (100-900)
        """
        # Check direct attribute first
        font_weight = element.get('font-weight')
        if font_weight:
            return self._weight_map.get(font_weight, 400)

        # Check style attribute using StyleParser
        if style_parser:
            style = element.get('style', '')
            if 'font-weight:' in style:
                weight = style_parser.get_property_value(style, 'font-weight')
                if weight:
                    return self._weight_map.get(weight, 400)

        return 400  # Default normal weight

    def get_font_style(self, element: ET.Element, style_parser=None) -> str:
        """
        Extract font style (normal/italic).

        Args:
            element: SVG element
            style_parser: StyleParser service instance

        Returns:
            Font style: 'normal' or 'italic'
        """
        # Check direct attribute first
        font_style = element.get('font-style')
        if font_style in ['italic', 'oblique']:
            return 'italic'

        # Check style attribute using StyleParser
        if style_parser:
            style = element.get('style', '')
            if 'font-style:' in style:
                style_val = style_parser.get_property_value(style, 'font-style')
                if style_val and style_val in ['italic', 'oblique']:
                    return 'italic'

        return 'normal'

    def get_text_decoration(self, element: ET.Element, style_parser=None) -> List[str]:
        """
        Extract text decoration properties.

        Args:
            element: SVG element
            style_parser: StyleParser service instance

        Returns:
            List of decoration styles
        """
        decorations = []

        # Check direct attribute first
        decoration = element.get('text-decoration')
        if decoration:
            decorations.extend(decoration.split())

        # Check style attribute using StyleParser
        if style_parser and not decorations:
            style = element.get('style', '')
            if 'text-decoration:' in style:
                decoration_val = style_parser.get_property_value(style, 'text-decoration')
                if decoration_val:
                    decorations.extend(decoration_val.split())

        return decorations

    def _clean_font_family(self, font_family: str) -> str:
        """Clean and extract primary font family name."""
        # Take first font in family list
        if ',' in font_family:
            font_family = font_family.split(',')[0].strip()

        # Remove quotes
        font_family = font_family.strip('\'"')

        return font_family

    def _parse_font_family_list(self, font_family: str) -> List[str]:
        """Parse comma-separated font family list."""
        families = []
        for family in font_family.split(','):
            clean_family = family.strip().strip('"\'')
            if clean_family:
                families.append(clean_family)
        return families

    def _parse_font_size(self, font_size: str, context=None) -> float:
        """Parse font size with units to points."""
        try:
            # Extract numeric value and unit
            match = re.match(r'^([+-]?(?:\d*\.)?\d+)\s*([a-zA-Z%]*)$', font_size.strip())
            if not match:
                return 12.0

            value = float(match.group(1))
            unit = match.group(2).lower() or 'px'

            # Convert to points
            if unit in self._size_units:
                return value * self._size_units[unit]
            elif unit == '%':
                # Percentage of parent font size (assume 12pt default)
                return (value / 100) * 12.0
            else:
                # Unknown unit, treat as pixels
                return value * 0.75

        except (ValueError, AttributeError):
            return 12.0

    def determine_font_strategy(self, family: str, weight: int, italic: bool) -> str:
        """
        Determine the best font rendering strategy.

        Args:
            family: Font family name
            weight: Font weight (100-900)
            italic: Whether font is italic

        Returns:
            Strategy: 'embedded', 'system', or 'fallback'
        """
        # This is a simplified implementation
        # In a real system, this would check font availability
        common_system_fonts = {
            'arial', 'helvetica', 'times', 'times new roman',
            'courier', 'courier new', 'verdana', 'georgia',
            'tahoma', 'trebuchet ms', 'comic sans ms'
        }

        family_lower = family.lower()
        if family_lower in common_system_fonts:
            return 'system'
        else:
            return 'fallback'

    def get_font_variant_name(self, weight: int, italic: bool) -> str:
        """
        Get font variant name for font selection.

        Args:
            weight: Font weight (100-900)
            italic: Whether font is italic

        Returns:
            Font variant name
        """
        if weight >= 700 and italic:
            return "Bold Italic"
        elif weight >= 700:
            return "Bold"
        elif italic:
            return "Italic"
        else:
            return "Regular"

    def validate_font_properties(self, properties: FontProperties) -> List[str]:
        """
        Validate font properties and return list of issues.

        Args:
            properties: FontProperties to validate

        Returns:
            List of validation issues (empty if valid)
        """
        issues = []

        if not properties.family:
            issues.append("Missing font family")

        if properties.size <= 0:
            issues.append(f"Invalid font size: {properties.size}")

        if properties.weight < 100 or properties.weight > 900:
            issues.append(f"Invalid font weight: {properties.weight}")

        if properties.style not in ['normal', 'italic']:
            issues.append(f"Invalid font style: {properties.style}")

        return issues

    def process_font_attributes(self, element: Any) -> Dict[str, Any]:
        """
        Process font attributes from element - adapter compatibility alias.

        Args:
            element: SVG element to process

        Returns:
            Dictionary of font attribute data
        """
        properties = self.extract_font_properties(element)
        return {
            'family': properties.family,
            'size': properties.size_px,
            'weight': properties.weight,
            'style': properties.style,
            'variant': properties.variant,
            'decoration': properties.decoration
        }


# Global font processor instance for convenience
font_processor = FontProcessor()


def extract_font_properties(element: ET.Element, style_parser=None, context=None) -> FontProperties:
    """Convenience function for font property extraction."""
    return font_processor.extract_font_properties(element, style_parser, context)