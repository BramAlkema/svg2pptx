#!/usr/bin/env python3
"""
FilterService for handling SVG filter definitions and conversions.

Provides filter registration, processing, and conversion to DrawingML.
Enhanced with comprehensive filter system integration.
"""

import logging
import math
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from lxml import etree as ET

if TYPE_CHECKING:
    from core.policy.engine import PolicyEngine

logger = logging.getLogger(__name__)


class FilterService:
    """
    Service for managing SVG filter definitions and conversions.

    This enhanced service integrates with the comprehensive filter system
    while maintaining backward compatibility with the minimal stub API.
    """

    def __init__(self, policy_engine: Optional['PolicyEngine'] = None, use_registry: bool = True):
        self._filter_cache: dict[str, ET.Element] = {}
        self._conversion_cache: dict[str, str] = {}
        self._policy_engine = policy_engine
        self._use_registry = use_registry
        self._registry = None

        # Initialize registry if requested
        if use_registry:
            try:
                from core.filters.registry import FilterRegistry
                self._registry = FilterRegistry()
                self._registry.register_default_filters()
                logger.info(f"FilterService initialized with {len(self._registry.list_filters())} filter types")
            except Exception as e:
                logger.warning(f"Failed to initialize filter registry: {e}. Falling back to stub mode.")
                self._use_registry = False

    def register_filter(self, filter_id: str, filter_element: ET.Element) -> None:
        """Register a filter definition for later resolution."""
        self._filter_cache[filter_id] = filter_element

    def get_filter_content(self, filter_id: str, context: Any = None) -> str | None:
        """
        Get filter content by ID.

        Args:
            filter_id: The ID of the filter to resolve
            context: Optional conversion context

        Returns:
            Filter content as DrawingML string, or None if not found
        """
        # Remove url() wrapper if present
        clean_id = filter_id.replace('url(#', '').replace(')', '').replace('#', '')

        # Check cache first
        if clean_id in self._conversion_cache:
            return self._conversion_cache[clean_id]

        # Look for filter in cache
        if clean_id in self._filter_cache:
            filter_element = self._filter_cache[clean_id]

            try:
                content = self._convert_filter_definition(filter_element, context)
                # Cache the result
                self._conversion_cache[clean_id] = content
                return content
            except Exception as e:
                logger.error(f"Filter conversion failed for {filter_id}: {e}")
                return None

        logger.warning(f"Filter not found: {filter_id}")
        return None

    def _convert_filter_definition(self, filter_element: ET.Element, context: Any = None) -> str:
        """Convert a filter definition element to DrawingML."""
        filter_id = filter_element.get('id', f'filter_{id(filter_element)}')

        # Count primitives and analyze filter type
        primitives = list(filter_element)
        primitive_count = len(primitives)

        # Determine filter type
        filter_type = self._analyze_filter_type(primitives)

        # Use policy engine if available
        if self._policy_engine:
            decision = self._policy_engine.decide_filter(
                filter_element=filter_element,
                filter_type=filter_type,
                primitive_count=primitive_count,
            )

            # Handle decision strategies
            if decision.use_rasterization:
                return self._rasterize_filter(filter_element, filter_id)
            elif decision.use_emf_fallback:
                return f'<!-- Filter {filter_id}: EMF fallback required (complex: {filter_type}, primitives: {primitive_count}) -->'
            elif not decision.use_native_effects:
                # Policy says skip or not supported
                return f'<!-- Filter {filter_id}: Not converted per policy -->'
            # Otherwise fall through to native conversion

        # Process child filter primitives with basic conversion
        drawingml_parts = []

        for child in filter_element:
            tag_name = child.tag.split('}')[-1] if '}' in child.tag else child.tag

            if tag_name == 'feGaussianBlur':
                std_deviation = child.get('stdDeviation', '1')
                try:
                    blur_radius = float(std_deviation) * 12700  # Convert to EMUs
                    drawingml_parts.append(f'<a:effectLst><a:blur rad="{int(blur_radius)}"/></a:effectLst>')
                except ValueError:
                    pass

            elif tag_name == 'feDropShadow':
                dx = child.get('dx', '3')
                dy = child.get('dy', '3')
                std_deviation = child.get('stdDeviation', '1')

                try:
                    dx_emu = int(float(dx) * 12700)
                    dy_emu = int(float(dy) * 12700)
                    blur_emu = int(float(std_deviation) * 12700)

                    drawingml_parts.append(f'''<a:effectLst>
  <a:outerShdw blurRad="{blur_emu}" dist="{int((dx_emu**2 + dy_emu**2)**0.5)}" dir="{int(math.atan2(dy_emu, dx_emu) * 180 / math.pi * 60000) % 21600000}">
    <a:srgbClr val="000000">
      <a:alpha val="50000"/>
    </a:srgbClr>
  </a:outerShdw>
</a:effectLst>''')
                except ValueError:
                    pass

        # Combine filter primitives into complete effect
        if drawingml_parts:
            return self._combine_filter_effects(drawingml_parts, filter_id)
        else:
            # Fallback for unsupported filter combinations
            return f'<!-- Filter {filter_id}: No supported primitives -->'

    def _combine_filter_effects(self, drawingml_parts: list[str], filter_id: str) -> str:
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
        combined = '<a:effectLst>\n'
        for part in drawingml_parts:
            if part and not part.strip().startswith('<!--'):
                combined += f'  {part}\n'
        combined += '</a:effectLst>'

        return combined

    def process_svg_filters(self, svg_root: ET.Element) -> None:
        """Process all filter definitions in an SVG document."""
        # Find and register all filters
        for filter_elem in svg_root.xpath('.//svg:defs//svg:filter',
                                          namespaces={'svg': 'http://www.w3.org/2000/svg'}):
            filter_id = filter_elem.get('id')
            if filter_id:
                self.register_filter(filter_id, filter_elem)

    def clear_cache(self) -> None:
        """Clear all cached filters and conversions."""
        self._filter_cache.clear()
        self._conversion_cache.clear()

    def get_supported_filters(self) -> list[str]:
        """
        Get list of supported filter types.

        Returns list from registry if available, otherwise returns stub list.
        """
        if self._use_registry and self._registry:
            # Return all registered filter types
            return self._registry.list_filters()
        else:
            # Fallback to minimal stub implementation
            return ['feGaussianBlur', 'feDropShadow']

    def _analyze_filter_type(self, primitives: list[ET.Element]) -> str:
        """
        Analyze filter primitives to determine filter type.

        Args:
            primitives: List of filter primitive elements

        Returns:
            Filter type string ('blur', 'shadow', 'chain', 'composite', etc.)
        """
        if not primitives:
            return 'empty'

        if len(primitives) == 1:
            tag_name = primitives[0].tag.split('}')[-1] if '}' in primitives[0].tag else primitives[0].tag
            if tag_name == 'feGaussianBlur':
                return 'blur'
            elif tag_name == 'feDropShadow':
                return 'shadow'
            elif tag_name == 'feColorMatrix':
                return 'color_matrix'
            elif tag_name == 'feComposite':
                return 'composite'
            else:
                return tag_name.replace('fe', '').lower()

        # Multiple primitives = chain
        return 'chain'

    def _rasterize_filter(self, filter_element: ET.Element, filter_id: str) -> str:
        """
        Rasterize a complex filter to an image.

        This is a fallback strategy for filters too complex for native DrawingML.

        Args:
            filter_element: The filter element to rasterize
            filter_id: Unique identifier for the filter

        Returns:
            Placeholder comment (actual rasterization would require rendering engine)
        """
        logger.info(f"Filter {filter_id} requires rasterization (not yet implemented)")
        return f'<!-- Filter {filter_id}: Rasterization fallback (not implemented) -->'