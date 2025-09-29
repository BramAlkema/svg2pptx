#!/usr/bin/env python3
"""
PatternService for handling SVG pattern definitions and conversions.

Provides pattern resolution, caching, and conversion to DrawingML patterns.
"""

from typing import Dict, Optional, List, Any
from lxml import etree as ET
import logging

logger = logging.getLogger(__name__)


class PatternService:
    """Service for managing SVG pattern definitions and conversions."""

    def __init__(self):
        self._pattern_cache: Dict[str, ET.Element] = {}
        self._conversion_cache: Dict[str, str] = {}

    def register_pattern(self, pattern_id: str, pattern_element: ET.Element) -> None:
        """Register a pattern definition for later resolution."""
        self._pattern_cache[pattern_id] = pattern_element

    def get_pattern_content(self, pattern_id: str, context: Any = None) -> Optional[str]:
        """
        Get pattern content by ID.

        Args:
            pattern_id: The ID of the pattern to resolve
            context: Optional conversion context

        Returns:
            Pattern content as string, or None if not found
        """
        # Remove url() wrapper if present
        clean_id = pattern_id.replace('url(#', '').replace(')', '').replace('#', '')

        # Check cache first
        if clean_id in self._conversion_cache:
            return self._conversion_cache[clean_id]

        # Look for pattern in cache
        if clean_id in self._pattern_cache:
            pattern_element = self._pattern_cache[clean_id]

            # Simple pattern conversion to DrawingML-like content
            content = self._convert_pattern(pattern_element)

            # Cache the result
            self._conversion_cache[clean_id] = content
            return content

        logger.warning(f"Pattern not found: {pattern_id}")
        return None

    def _convert_pattern(self, pattern_element: ET.Element) -> str:
        """Convert SVG pattern to basic DrawingML pattern representation."""
        # Get pattern dimensions
        width = pattern_element.get('width', '10')
        height = pattern_element.get('height', '10')

        # For now, convert patterns to simple preset patterns
        # This is a placeholder - real implementation would analyze pattern content
        pattern_type = self._detect_pattern_type(pattern_element)

        if pattern_type == 'dots':
            return '<a:pattFill prst="dotGrid"><a:fgClr><a:srgbClr val="000000"/></a:fgClr><a:bgClr><a:srgbClr val="FFFFFF"/></a:bgClr></a:pattFill>'
        elif pattern_type == 'lines':
            return '<a:pattFill prst="horz"><a:fgClr><a:srgbClr val="000000"/></a:fgClr><a:bgClr><a:srgbClr val="FFFFFF"/></a:bgClr></a:pattFill>'
        elif pattern_type == 'diagonal':
            return '<a:pattFill prst="dnDiag"><a:fgClr><a:srgbClr val="000000"/></a:fgClr><a:bgClr><a:srgbClr val="FFFFFF"/></a:bgClr></a:pattFill>'
        else:
            # Fallback to solid fill
            return '<a:solidFill><a:srgbClr val="000000"/></a:solidFill>'

    def _detect_pattern_type(self, pattern_element: ET.Element) -> str:
        """Detect the type of pattern for conversion to PowerPoint presets."""
        # Simple pattern detection based on child elements
        children = list(pattern_element)

        if not children:
            return 'solid'

        # Look for common pattern shapes
        for child in children:
            tag = child.tag.split('}')[-1]  # Remove namespace

            if tag == 'circle':
                return 'dots'
            elif tag == 'line':
                return 'lines'
            elif tag == 'rect':
                # Could be lines or solid depending on dimensions
                width = float(child.get('width', '1'))
                height = float(child.get('height', '1'))
                if width > height * 3 or height > width * 3:
                    return 'lines'
                else:
                    return 'solid'
            elif tag == 'path':
                # Analyze path for diagonal lines
                d = child.get('d', '')
                if 'L' in d and ('M' in d):
                    return 'diagonal'

        return 'solid'

    def process_svg_patterns(self, svg_root: ET.Element) -> None:
        """Process all pattern definitions in an SVG document."""
        # Find and register all patterns
        for pattern in svg_root.xpath('.//svg:defs//svg:pattern',
                                     namespaces={'svg': 'http://www.w3.org/2000/svg'}):
            pattern_id = pattern.get('id')
            if pattern_id:
                self.register_pattern(pattern_id, pattern)

    def clear_cache(self) -> None:
        """Clear all cached patterns and conversions."""
        self._pattern_cache.clear()
        self._conversion_cache.clear()