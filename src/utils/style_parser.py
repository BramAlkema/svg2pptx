#!/usr/bin/env python3
"""
StyleParser utility service for SVG2PPTX.

This module provides centralized CSS style parsing functionality,
eliminating duplicate style processing implementations across the codebase.
"""

import re
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass
# Removed circular import - StyleParser is now a standalone service


@dataclass
class StyleDeclaration:
    """Represents a parsed CSS style declaration."""
    property: str
    value: str
    priority: str = ""  # !important flag


@dataclass
class StyleResult:
    """Result of style parsing operation."""
    declarations: Dict[str, StyleDeclaration]
    raw_text: str
    parsing_errors: List[str]


class StyleParser:
    """
    Centralized CSS style parsing service.

    Provides unified style parsing functionality to replace duplicate
    implementations across converters, preprocessing, and utilities.
    """

    def __init__(self):
        """Initialize StyleParser with optimization settings."""
        # Cache frequently used regex patterns
        self._style_split_pattern = re.compile(r';(?![^()]*\))')
        self._declaration_pattern = re.compile(r'^([^:]+):(.*)$')
        self._important_pattern = re.compile(r'!\s*important\s*$', re.IGNORECASE)

        # Common CSS properties for validation
        self._known_properties = {
            'color', 'background', 'background-color', 'fill', 'stroke',
            'stroke-width', 'opacity', 'font-family', 'font-size', 'font-weight',
            'font-style', 'text-decoration', 'text-align', 'width', 'height',
            'margin', 'padding', 'border', 'display', 'position', 'top', 'left',
            'right', 'bottom', 'z-index', 'transform', 'visibility'
        }

    def parse_style_string(self, style_string: str) -> StyleResult:
        """
        Parse CSS style string into structured declarations.

        Args:
            style_string: CSS style string (e.g., "color: red; font-size: 12px")

        Returns:
            StyleResult with parsed declarations and metadata
        """
        if not style_string or not style_string.strip():
            return StyleResult(
                declarations={},
                raw_text=style_string,
                parsing_errors=[]
            )

        declarations = {}
        errors = []

        # Split style string by semicolons (avoiding splitting inside functions)
        style_parts = self._style_split_pattern.split(style_string)

        for part in style_parts:
            part = part.strip()
            if not part:
                continue

            try:
                declaration = self._parse_declaration(part)
                if declaration:
                    declarations[declaration.property] = declaration
            except Exception as e:
                errors.append(f"Failed to parse '{part}': {str(e)}")

        return StyleResult(
            declarations=declarations,
            raw_text=style_string,
            parsing_errors=errors
        )

    def _parse_declaration(self, declaration_text: str) -> Optional[StyleDeclaration]:
        """Parse a single CSS declaration."""
        match = self._declaration_pattern.match(declaration_text.strip())
        if not match:
            return None

        property_name = match.group(1).strip().lower()
        value_text = match.group(2).strip()

        # Check for !important
        priority = ""
        if self._important_pattern.search(value_text):
            priority = "important"
            value_text = self._important_pattern.sub('', value_text).strip()

        return StyleDeclaration(
            property=property_name,
            value=value_text,
            priority=priority
        )

    def parse_style_to_dict(self, style_string: str) -> Dict[str, str]:
        """
        Parse style string to simple property:value dictionary.

        Args:
            style_string: CSS style string

        Returns:
            Dictionary mapping property names to values
        """
        result = self.parse_style_string(style_string)
        return {
            prop: decl.value
            for prop, decl in result.declarations.items()
        }

    def get_property_value(self, style_string: str, property_name: str,
                          default: str = "") -> str:
        """
        Extract a specific property value from style string.

        Args:
            style_string: CSS style string
            property_name: Property to extract (case-insensitive)
            default: Default value if property not found

        Returns:
            Property value or default
        """
        result = self.parse_style_string(style_string)
        property_name = property_name.lower()

        declaration = result.declarations.get(property_name)
        return declaration.value if declaration else default

    def extract_font_family(self, style_string: str) -> str:
        """
        Extract font-family from style string.

        Args:
            style_string: CSS style string

        Returns:
            Font family name or empty string
        """
        font_family = self.get_property_value(style_string, 'font-family')
        if font_family:
            # Clean up font family (remove quotes, handle fallbacks)
            font_family = font_family.strip('\'"')
            # Take first font in family list
            if ',' in font_family:
                font_family = font_family.split(',')[0].strip().strip('\'"')

        return font_family

    def merge_styles(self, *style_strings: str) -> str:
        """
        Merge multiple style strings, with later styles taking precedence.

        Args:
            *style_strings: Variable number of CSS style strings

        Returns:
            Merged CSS style string
        """
        all_declarations = {}

        for style_string in style_strings:
            if not style_string:
                continue

            result = self.parse_style_string(style_string)
            all_declarations.update(result.declarations)

        # Convert back to CSS string
        parts = []
        for declaration in all_declarations.values():
            value_with_priority = declaration.value
            if declaration.priority:
                value_with_priority += f" !{declaration.priority}"
            parts.append(f"{declaration.property}: {value_with_priority}")

        return "; ".join(parts)

    def minify_style(self, style_string: str) -> str:
        """
        Minify CSS style string by removing unnecessary whitespace.

        Args:
            style_string: CSS style string

        Returns:
            Minified CSS style string
        """
        result = self.parse_style_string(style_string)

        parts = []
        for declaration in result.declarations.values():
            # Normalize spacing in values
            normalized_value = re.sub(r'\s+', ' ', declaration.value.strip())
            parts.append(f"{declaration.property}:{normalized_value}")

        return ";".join(parts)

    def validate_style(self, style_string: str) -> List[str]:
        """
        Validate CSS style string and return list of issues.

        Args:
            style_string: CSS style string

        Returns:
            List of validation issues (empty if valid)
        """
        result = self.parse_style_string(style_string)
        issues = list(result.parsing_errors)

        # Check for unknown properties
        for prop in result.declarations:
            if prop not in self._known_properties and not prop.startswith('-'):
                issues.append(f"Unknown CSS property: {prop}")

        return issues

    def parse_style_attribute(self, style_attr: str) -> Dict[str, str]:
        """
        Parse style attribute to dictionary - adapter compatibility alias.

        Args:
            style_attr: CSS style attribute string

        Returns:
            Dictionary of style properties
        """
        return self.parse_style_to_dict(style_attr)


# Global parser instance for convenience
_style_parser_instance = None

def get_style_parser():
    """Get or create global StyleParser instance with ConversionServices awareness."""
    global _style_parser_instance
    if _style_parser_instance is None:
        # Service-aware fallback: try ConversionServices first
        try:
            from ..services.conversion_services import ConversionServices
            services = ConversionServices.get_default_instance()
            _style_parser_instance = services.style_parser
        except (ImportError, RuntimeError, AttributeError):
            # Final fallback to direct instantiation
            _style_parser_instance = StyleParser()
    return _style_parser_instance


def parse_style_string(style_string: str) -> Dict[str, str]:
    """Convenience function for simple style parsing."""
    return get_style_parser().parse_style_to_dict(style_string)


def get_style_property(style_string: str, property_name: str, default: str = "") -> str:
    """Convenience function for property extraction."""
    return style_parser.get_property_value(style_string, property_name, default)