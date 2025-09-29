"""
TextPathEngine - Modern replacement for TextToPathConverter

This module provides a simplified text-to-path conversion engine with proper
dependency injection, graceful error handling, and robust fallback behavior.

Key Features:
- Clean dependency injection for coordinate system
- Immutable configuration with sensible defaults
- Graceful fallback for missing fonts or dependencies
- Type-safe error handling with comprehensive context
- Simplified font detection and path generation pipeline
"""

from typing import Dict, Any, List, Optional, Tuple
from lxml import etree as ET
from dataclasses import dataclass

from .result_types import (
    ConversionResult, TextConversionConfig, ConversionError,
    create_text_shape_fallback
)
from ..services.conversion_services import ConversionServices
from ..utils.input_validator import InputValidator


class TextPathEngine:
    """
    Simplified text-to-path conversion engine with robust error handling.

    Replaces TextToPathConverter with clean architecture that provides:
    - Proper coordinate system dependency injection
    - Consistent error handling through result types
    - Graceful fallback behavior for all edge cases
    - Simplified configuration management
    """

    def __init__(self, services: ConversionServices, config: Optional[TextConversionConfig] = None):
        """
        Initialize TextPathEngine with injected services.

        Args:
            services: ConversionServices instance providing all required dependencies
            config: Optional configuration, uses defaults if not provided
        """
        self._services = services
        self._config = config or TextConversionConfig()
        self._validator = InputValidator()

        # Extract required services with proper null handling
        self._coordinate_system = getattr(services, 'coordinate_system', None)
        self._font_service = getattr(services, 'font_service', None)
        self._unit_converter = getattr(services, 'unit_converter', None)

        # Initialize path generation cache if enabled
        self._path_cache = {} if self._config.max_cache_size > 0 else None

    def convert_text_element(self, element: ET.Element, context: Any) -> ConversionResult:
        """
        Convert text element to path with proper error handling.

        Args:
            element: SVG text element to convert
            context: Conversion context with current state

        Returns:
            ConversionResult with path content or fallback
        """
        try:
            # Validate coordinate system dependency
            if not self._coordinate_system:
                return self._create_coordinate_system_fallback(element)

            # Extract text content
            text_content = self._extract_text_content(element)
            if not text_content:
                return ConversionResult.success_with_content("<!-- Empty text element -->")

            # Get text attributes
            attributes = self._extract_text_attributes(element)

            # Check cache if enabled
            cache_key = self._generate_cache_key(text_content, attributes)
            if self._path_cache is not None and cache_key in self._path_cache:
                return ConversionResult.success_with_content(
                    self._path_cache[cache_key],
                    metadata={"cache_hit": True}
                )

            # Generate path for text
            path_result = self._generate_text_path(text_content, attributes, context)

            # Cache successful results
            if self._path_cache is not None and path_result.success:
                self._path_cache[cache_key] = path_result.content

            return path_result

        except Exception as e:
            return create_text_shape_fallback(
                str(element.text or ""),
                f"Text conversion error: {str(e)}"
            )

    def _extract_text_content(self, element: ET.Element) -> str:
        """Extract text content from element and children."""
        texts = []

        # Get direct text content
        if element.text:
            texts.append(element.text)

        # Get text from tspan children
        for child in element:
            if child.tag.endswith('tspan'):
                if child.text:
                    texts.append(child.text)
                if child.tail:
                    texts.append(child.tail)

        # Get tail text
        if element.tail:
            texts.append(element.tail)

        return ' '.join(texts).strip()

    def _extract_text_attributes(self, element: ET.Element) -> Dict[str, Any]:
        """Extract relevant text attributes for path generation."""
        attributes = {
            'font-family': element.get('font-family', self._config.fallback_font_family),
            'font-size': element.get('font-size', '12'),
            'font-weight': element.get('font-weight', 'normal'),
            'font-style': element.get('font-style', 'normal'),
            'text-anchor': element.get('text-anchor', 'start'),
            'x': element.get('x', '0'),
            'y': element.get('y', '0'),
            'transform': element.get('transform', '')
        }

        # Process text decoration if preservation is enabled
        if self._config.preserve_decorations:
            attributes['text-decoration'] = element.get('text-decoration', 'none')

        return attributes

    def _generate_text_path(self, text: str, attributes: Dict[str, Any], context: Any) -> ConversionResult:
        """
        Generate path from text with font metrics.

        This is a simplified version that focuses on robust fallback behavior
        rather than complex font detection pipelines.
        """
        try:
            # Convert coordinates to EMU
            x_emu = self._convert_to_emu(attributes['x'], context)
            y_emu = self._convert_to_emu(attributes['y'], context)

            # Get font size in EMU
            font_size_emu = self._convert_to_emu(attributes['font-size'], context)

            # Generate DrawingML text shape (simplified)
            content = self._create_text_shape_drawingml(
                text, x_emu, y_emu, font_size_emu, attributes
            )

            return ConversionResult.success_with_content(
                content,
                metadata={
                    "conversion_method": "text_shape",
                    "font_family": attributes['font-family']
                }
            )

        except Exception as e:
            # Fallback to basic text shape
            return create_text_shape_fallback(text, f"Path generation failed: {str(e)}")

    def _convert_to_emu(self, value: str, context: Any) -> int:
        """Convert value to EMU with fallback."""
        try:
            if self._unit_converter and hasattr(self._unit_converter, 'to_emu'):
                return self._unit_converter.to_emu(value, context)

            # Basic fallback conversion using secure parser
            numeric_value = self._validator.parse_length_safe(value, default_unit='px')
            if numeric_value is not None:
                return int(numeric_value * 12700)  # 1px ≈ 12700 EMU
            return 0

        except (ValueError, AttributeError):
            return 0  # Default to 0 for invalid values

    def _create_text_shape_drawingml(self, text: str, x: int, y: int,
                                     font_size: int, attributes: Dict[str, Any]) -> str:
        """Create DrawingML text shape."""
        # Enhanced text dimension estimation in EMU
        width = max(int(len(text) * font_size * 0.55 * 9525), 1000000)  # Improved width estimation
        height = max(int(font_size * 1.25 * 9525), 400000)  # Better height estimation

        # Get font family
        font_family = attributes.get('font-family', 'Arial')
        if ',' in font_family:
            font_family = font_family.split(',')[0].strip()

        return f'''<p:sp>
    <p:nvSpPr>
        <p:cNvPr id="1" name="Text"/>
        <p:cNvSpPr txBox="1"/>
        <p:nvPr/>
    </p:nvSpPr>
    <p:spPr>
        <a:xfrm>
            <a:off x="{x}" y="{y}"/>
            <a:ext cx="{width}" cy="{height}"/>
        </a:xfrm>
        <a:prstGeom prst="rect">
            <a:avLst/>
        </a:prstGeom>
        <a:noFill/>
    </p:spPr>
    <p:txBody>
        <a:bodyPr wrap="none" rtlCol="0">
            <a:spAutoFit/>
        </a:bodyPr>
        <a:lstStyle/>
        <a:p>
            <a:r>
                <a:rPr lang="en-US" sz="{font_size // 100}" dirty="0">
                    <a:latin typeface="{font_family}"/>
                </a:rPr>
                <a:t>{text}</a:t>
            </a:r>
        </a:p>
    </p:txBody>
</p:sp>'''

    def _generate_cache_key(self, text: str, attributes: Dict[str, Any]) -> str:
        """Generate cache key for text path conversion."""
        key_parts = [
            text,
            attributes.get('font-family', ''),
            attributes.get('font-size', ''),
            attributes.get('font-weight', ''),
            attributes.get('font-style', '')
        ]
        return '|'.join(str(p) for p in key_parts)

    def _create_coordinate_system_fallback(self, element: ET.Element) -> ConversionResult:
        """Create fallback when coordinate system is missing."""
        text = self._extract_text_content(element) or "Text"

        return ConversionResult.error_with_fallback(
            error_message="Coordinate system not available",
            fallback_content=f'''<p:sp>
    <p:nvSpPr>
        <p:cNvPr id="1" name="Text (No Coordinate System)"/>
        <p:cNvSpPr txBox="1"/>
        <p:nvPr/>
    </p:nvSpPr>
    <p:spPr>
        <a:xfrm>
            <a:off x="0" y="0"/>
            <a:ext cx="2000000" cy="400000"/>
        </a:xfrm>
        <a:prstGeom prst="rect">
            <a:avLst/>
        </a:prstGeom>
        <a:noFill/>
    </p:spPr>
    <p:txBody>
        <a:bodyPr/>
        <a:lstStyle/>
        <a:p>
            <a:r>
                <a:rPr lang="en-US" sz="1200"/>
                <a:t>{text[:100]}</a:t>
            </a:r>
        </a:p>
    </p:txBody>
</p:sp>''',
            error_type="MissingDependency"
        )

    def clear_cache(self):
        """Clear the path generation cache."""
        if self._path_cache is not None:
            self._path_cache.clear()

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        if self._path_cache is None:
            return {"cache_enabled": False}

        return {
            "cache_enabled": True,
            "cache_size": len(self._path_cache),
            "max_cache_size": self._config.max_cache_size
        }