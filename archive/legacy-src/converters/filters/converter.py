#!/usr/bin/env python3
"""
FilterConverter - Main converter integration for SVG filter effects.

This module provides the FilterConverter class that integrates the filter system
with the main SVG2PPTX converter architecture, enabling filter effects processing
as part of the conversion pipeline.

TODO: Issue 6 - Fix Filter Processing Stack
===========================================
PRIORITY: HIGH
STATUS: Needs implementation

Problems:
- Filter service is not integrated with ConversionServices
- Filter processing is not wired up in the main conversion pipeline
- Filter effects are not being applied during SVG to PPTX conversion

Required Changes:
1. Create FilterService class for dependency injection
2. Add filter_service to ConversionServices container
3. Wire up filter processing in SVGToDrawingMLConverter
4. Ensure filter effects are properly applied during conversion
5. Add proper error handling and fallbacks for unsupported filters

Files to modify:
- src/services/filter_service.py (create)
- src/services/conversion_services.py (add filter_service)
- src/svg2drawingml.py (integrate filter processing)
- src/converters/filters/converter.py (this file - update initialization)

Test:
- Create SVG with filter effects (blur, drop shadow, etc.)
- Verify filters are processed and converted to DrawingML
- Ensure fallback behavior for unsupported filters
"""

import logging
from typing import Dict, Any, Optional, List
from lxml import etree

from ..base import BaseConverter, ConversionContext
from ...services.conversion_services import ConversionServices

from .core.base import FilterContext, FilterResult
from .core.registry import FilterRegistry
from .core.chain import FilterChain

logger = logging.getLogger(__name__)


class FilterConverter(BaseConverter):
    """
    Main converter for SVG filter effects.

    Integrates the modular filter system with the SVG2PPTX conversion pipeline,
    providing seamless processing of SVG filter effects and their conversion
    to PowerPoint DrawingML.

    Supported Elements:
        - filter (container element)
        - feGaussianBlur
        - feDropShadow
        - feColorMatrix
        - feFlood
        - feComposite
        - feOffset
        - And all other filter primitives in the filter registry
    """

    # Filter elements this converter handles
    supported_elements = [
        'filter',
        'feGaussianBlur',
        'feDropShadow',
        'feColorMatrix',
        'feFlood',
        'feComposite',
        'feOffset',
        'feMorphology',
        'feConvolveMatrix',
        'feTurbulence',
        'feImage',
        'feTile',
        'feComponentTransfer',
        'feDiffuseLighting',
        'feSpecularLighting'
    ]

    def __init__(self, services: ConversionServices) -> None:
        """
        Initialize FilterConverter with dependency injection.

        Args:
            services: ConversionServices container with initialized services
        """
        super().__init__(services)
        self.filter_registry = FilterRegistry()
        self.filter_registry.register_default_filters()

        # Cache for filter definitions
        self._filter_definitions = {}

    def can_convert(self, element: etree.Element) -> bool:
        """
        Check if this converter can handle the given element.

        Args:
            element: SVG element to check

        Returns:
            True if element is a filter-related element
        """
        if element is None:
            return False

        tag = element.tag

        # Handle namespace-qualified tags
        if '}' in tag:
            tag = tag.split('}')[1]

        return tag in self.supported_elements

    def convert(self, element: etree.Element, context: ConversionContext) -> str:
        """
        Convert SVG filter element to PowerPoint DrawingML.

        Args:
            element: SVG filter element
            context: Conversion context with state and services

        Returns:
            DrawingML string
        """
        try:
            tag = element.tag
            if '}' in tag:
                tag = tag.split('}')[1]

            if tag == 'filter':
                return self._convert_filter_definition(element, context)
            else:
                return self._convert_filter_primitive(element, context)

        except Exception as e:
            self.logger.error(f"Filter conversion failed for {element.tag}: {e}")
            return f'<!-- Filter conversion failed: {e} -->'

    def _convert_filter_definition(self, element: etree.Element, context: ConversionContext) -> str:
        """
        Convert a filter definition element.

        Filter definitions contain multiple filter primitives that work together
        to create complex visual effects.

        Args:
            element: SVG filter element
            context: Conversion context

        Returns:
            DrawingML string with complete filter
        """
        filter_id = element.get('id', f'filter_{id(element)}')

        # Store filter definition for later reference
        self._filter_definitions[filter_id] = element

        # Process child filter primitives
        drawingml_parts = []

        for child in element:
            if self.can_convert(child):
                result = self._convert_filter_primitive(child, context)
                if result and result.strip() and not result.strip().startswith('<!-- Unsupported'):
                    drawingml_parts.append(result)

        # Combine filter primitives into complete effect
        if drawingml_parts:
            return self._combine_filter_effects(drawingml_parts, filter_id)
        else:
            # Fallback for unsupported filter combinations
            return f'<!-- Filter {filter_id}: No supported primitives -->'

    def _convert_filter_primitive(self, element: etree.Element, context: ConversionContext) -> str:
        """
        Convert a single filter primitive element.

        Args:
            element: SVG filter primitive element
            context: Conversion context

        Returns:
            DrawingML string for the primitive
        """
        # Create filter context from conversion context
        filter_context = FilterContext(
            element=element,
            dpi=96.0,  # Default DPI
            unit_converter=self.services.unit_converter,
            color_factory=self.services.color_factory
        )

        # Get appropriate filter from registry
        filter_obj = self.filter_registry.get_filter(element)

        if filter_obj is None:
            # No specific filter found, create fallback comment
            tag = element.tag.split('}')[1] if '}' in element.tag else element.tag
            return f'<!-- Unsupported filter primitive: {tag} -->'

        # Apply filter
        filter_result = filter_obj.apply(element, filter_context)

        # Return the DrawingML string
        if filter_result.success:
            return filter_result.drawingml
        else:
            return f'<!-- Filter primitive {element.tag} failed -->'

    def _combine_filter_effects(self, drawingml_parts: List[str], filter_id: str) -> str:
        """
        Combine multiple filter primitive DrawingML into a complete effect.

        Args:
            drawingml_parts: List of DrawingML strings from filter primitives
            filter_id: Unique identifier for the filter

        Returns:
            Combined DrawingML string
        """
        if not drawingml_parts:
            return ""

        if len(drawingml_parts) == 1:
            return drawingml_parts[0]

        # For multiple effects, wrap in effect group
        combined = f'<a:effectLst>\n'
        for part in drawingml_parts:
            if part and not part.strip().startswith('<!--'):
                combined += f'  {part}\n'
        combined += '</a:effectLst>'

        return combined

    def get_filter_definition(self, filter_id: str) -> Optional[etree.Element]:
        """
        Get a filter definition by ID.

        Args:
            filter_id: Filter identifier

        Returns:
            Filter element or None if not found
        """
        return self._filter_definitions.get(filter_id)

    def supports_native_rendering(self, element: etree.Element) -> bool:
        """
        Check if the filter can be rendered natively in PowerPoint.

        Args:
            element: SVG filter element

        Returns:
            True if native PowerPoint rendering is supported
        """
        filter_obj = self.filter_registry.get_filter(element)
        if filter_obj is None:
            return False

        # Check if filter has native support metadata
        return getattr(filter_obj, 'has_native_support', False)