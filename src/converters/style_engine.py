"""
StyleEngine - Modern replacement for StyleProcessor

This module provides a functional style processing engine with comprehensive
error handling, graceful fallback behavior, and proper dependency injection.

Key Features:
- Clean dependency injection through ConversionServices
- Immutable result types for thread-safe operations
- Graceful fallback behavior for invalid gradient URLs
- Type-safe error handling with comprehensive context
- Backward compatibility adapter for existing code
"""

from typing import Dict, Any, List, Optional, Union
from lxml import etree as ET

from .result_types import (
    StyleResult, FillResult, ConversionError, ConversionStatus,
    create_gradient_fallback_fill
)
from ..services.conversion_services import ConversionServices


class StyleEngine:
    """
    Functional style processing engine with dependency injection.

    Replaces StyleProcessor with clean architecture that provides:
    - Consistent error handling through result types
    - Graceful fallback behavior for all edge cases
    - Proper service dependency injection
    - Immutable operation results
    """

    def __init__(self, services: ConversionServices):
        """
        Initialize StyleEngine with injected services.

        Args:
            services: ConversionServices instance providing all required dependencies
        """
        self._services = services
        self._gradient_service = services.gradient_service
        self._color_parser = services.color_parser
        self._unit_converter = services.unit_converter

    def process_element_styles(self, element: ET.Element, context: Any) -> StyleResult:
        """
        Process all styles for an SVG element with comprehensive error handling.

        Args:
            element: SVG element to process styles for
            context: Conversion context with current state

        Returns:
            StyleResult with processed properties and any errors/warnings
        """
        properties = {}
        errors = []
        warnings = []
        fallbacks_used = []

        try:
            # Process fill attribute
            fill_attr = element.get('fill')
            if fill_attr:
                fill_result = self._process_fill_attribute(fill_attr, context)
                if fill_result.has_content:
                    properties['fill'] = fill_result.content
                    if fill_result.is_fallback:
                        fallbacks_used.append(f"fill_fallback: {fill_result.fallback_reason}")

            # Process stroke attribute
            stroke_attr = element.get('stroke')
            if stroke_attr:
                stroke_result = self._process_stroke_attribute(stroke_attr, context)
                if stroke_result.has_content:
                    properties['stroke'] = stroke_result.content
                    if stroke_result.is_fallback:
                        fallbacks_used.append(f"stroke_fallback: {stroke_result.fallback_reason}")

            # Process style attribute
            style_attr = element.get('style')
            if style_attr:
                style_props = self._parse_style_attribute(style_attr, context)
                properties.update(style_props)

            # Process other style-related attributes
            for attr_name in ['opacity', 'fill-opacity', 'stroke-opacity', 'stroke-width']:
                attr_value = element.get(attr_name)
                if attr_value:
                    properties[attr_name] = attr_value

            # Determine status based on results
            if errors:
                status = ConversionStatus.ERROR_WITH_FALLBACK if fallbacks_used else ConversionStatus.CRITICAL_ERROR
            elif fallbacks_used:
                status = ConversionStatus.SUCCESS_WITH_FALLBACK
            else:
                status = ConversionStatus.SUCCESS

            return StyleResult(
                properties=properties,
                errors=errors,
                warnings=warnings,
                fallbacks_used=fallbacks_used,
                status=status
            )

        except Exception as e:
            error = ConversionError(
                message=f"Failed to process element styles: {str(e)}",
                error_type="StyleProcessingError",
                context={"element_tag": element.tag}
            )
            return StyleResult(
                properties={},
                errors=[error],
                status=ConversionStatus.CRITICAL_ERROR
            )

    def resolve_gradient_fill(self, url: str, context: Any) -> FillResult:
        """
        Resolve gradient URL with graceful fallback for invalid references.

        Args:
            url: Gradient URL (e.g., "url(#gradient1)")
            context: Conversion context with gradient definitions

        Returns:
            FillResult with gradient content or fallback
        """
        try:
            # Extract gradient ID from URL
            if not url.startswith('url(#') or not url.endswith(')'):
                return create_gradient_fallback_fill(
                    url, "Invalid gradient URL format"
                )

            gradient_id = url[5:-1]  # Remove 'url(#' and ')'

            # Attempt to resolve gradient through service
            if hasattr(self._gradient_service, 'get_gradient_content'):
                gradient_content = self._gradient_service.get_gradient_content(gradient_id, context)
                if gradient_content:
                    return FillResult.success(gradient_content, gradient_id)

            # Fallback for missing or invalid gradient
            return create_gradient_fallback_fill(
                url, f"Gradient '{gradient_id}' not found or invalid"
            )

        except Exception as e:
            return create_gradient_fallback_fill(
                url, f"Error resolving gradient: {str(e)}"
            )

    def _process_fill_attribute(self, fill_value: str, context: Any) -> FillResult:
        """Process fill attribute value with fallback support."""
        if fill_value.startswith('url(#'):
            return self.resolve_gradient_fill(fill_value, context)
        elif fill_value == 'none':
            return FillResult.success('<a:noFill/>')
        else:
            # Attempt color parsing
            try:
                if hasattr(self._color_parser, 'parse_color'):
                    color_hex = self._color_parser.parse_color(fill_value)
                    if color_hex:
                        content = f'<a:solidFill><a:srgbClr val="{color_hex}"/></a:solidFill>'
                        return FillResult.success(content)

                # Fallback for unparseable colors
                return FillResult.fallback(
                    '<a:solidFill><a:srgbClr val="000000"/></a:solidFill>',
                    fill_value,
                    "Color parsing failed, using black fallback"
                )

            except Exception as e:
                return FillResult.fallback(
                    '<a:solidFill><a:srgbClr val="808080"/></a:solidFill>',
                    fill_value,
                    f"Color processing error: {str(e)}"
                )

    def _process_stroke_attribute(self, stroke_value: str, context: Any) -> FillResult:
        """Process stroke attribute value with fallback support."""
        if stroke_value == 'none':
            return FillResult.success('')  # No stroke
        else:
            # Similar to fill processing but for stroke colors
            try:
                if hasattr(self._color_parser, 'parse_color'):
                    color_hex = self._color_parser.parse_color(stroke_value)
                    if color_hex:
                        content = f'<a:ln><a:solidFill><a:srgbClr val="{color_hex}"/></a:solidFill></a:ln>'
                        return FillResult.success(content)

                # Fallback for unparseable stroke colors
                return FillResult.fallback(
                    '<a:ln><a:solidFill><a:srgbClr val="000000"/></a:solidFill></a:ln>',
                    stroke_value,
                    "Stroke color parsing failed, using black fallback"
                )

            except Exception as e:
                return FillResult.fallback(
                    '<a:ln><a:solidFill><a:srgbClr val="808080"/></a:solidFill></a:ln>',
                    stroke_value,
                    f"Stroke processing error: {str(e)}"
                )

    def _parse_style_attribute(self, style_value: str, context: Any) -> Dict[str, str]:
        """Parse CSS-style attribute string into property dictionary."""
        properties = {}

        try:
            # Split style declarations
            declarations = [decl.strip() for decl in style_value.split(';') if decl.strip()]

            for declaration in declarations:
                if ':' in declaration:
                    prop, value = declaration.split(':', 1)
                    properties[prop.strip()] = value.strip()

        except Exception:
            # If parsing fails, return empty dict - caller handles fallback
            pass

        return properties


# StyleProcessor has been replaced by StyleEngine
# Import StyleEngine directly for all style processing needs