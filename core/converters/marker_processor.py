#!/usr/bin/env python3
"""
SVG Marker Processor for Clean Slate Architecture

Processes SVG markers (arrowheads, line decorations) and generates PowerPoint
line cap properties. Integrates with the mapper pattern and template system.

Key Features:
- Marker definition parsing and processing
- PowerPoint line cap generation (headEnd, tailEnd)
- Template-based XML generation for safety
- Integration with path mapper for line decorations

This processor extracts marker definitions from SVG and provides utilities
for other mappers to apply markers to their elements.
"""

import re
import math
import logging
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass
from enum import Enum
from lxml import etree as ET

from ..utils.enhanced_xml_builder import EnhancedXMLBuilder

logger = logging.getLogger(__name__)


class MarkerPosition(Enum):
    """Marker position on path."""
    START = "marker-start"
    MID = "marker-mid"
    END = "marker-end"


class MarkerUnits(Enum):
    """Marker coordinate units."""
    STROKE_WIDTH = "strokeWidth"  # Scale with stroke width
    USER_SPACE_ON_USE = "userSpaceOnUse"  # Use user coordinates


@dataclass
class MarkerDefinition:
    """Parsed marker definition."""
    id: str
    ref_x: float
    ref_y: float
    marker_width: float
    marker_height: float
    orient: str  # "auto" or angle in degrees
    marker_units: MarkerUnits
    viewbox: Optional[Tuple[float, float, float, float]]
    overflow: str  # "visible" or "hidden"
    content_xml: str  # Inner content as XML

    def get_orientation_angle(self, path_angle: float) -> float:
        """Calculate marker orientation angle."""
        if self.orient == "auto":
            return path_angle
        elif self.orient == "auto-start-reverse":
            return path_angle + 180.0
        else:
            try:
                return float(self.orient)
            except ValueError:
                return 0.0


@dataclass
class SymbolDefinition:
    """Parsed symbol definition."""
    id: str
    viewbox: Optional[Tuple[float, float, float, float]]
    preserve_aspect_ratio: str
    width: Optional[float]
    height: Optional[float]
    content_xml: str


@dataclass
class MarkerInstance:
    """Instance of marker on a path."""
    definition: MarkerDefinition
    position: MarkerPosition
    x: float
    y: float
    angle: float  # Path tangent angle at position
    stroke_width: float
    color: Optional[str]


@dataclass
class PowerPointLineEnd:
    """PowerPoint line end properties."""
    type: str  # arrow, diamond, oval, stealth, triangle, etc.
    w: str  # width: sm, med, lg
    len: str  # length: sm, med, lg


class MarkerProcessor:
    """
    Processes SVG markers and converts them to PowerPoint line ends.

    This processor integrates with the clean slate architecture by providing
    utilities for mappers to handle marker-decorated paths.
    """

    def __init__(self):
        """Initialize marker processor."""
        self.markers: Dict[str, MarkerDefinition] = {}
        self.symbols: Dict[str, SymbolDefinition] = {}
        self.xml_builder = EnhancedXMLBuilder()

        # Standard PowerPoint arrow types
        self.powerpoint_arrows = {
            'arrow': PowerPointLineEnd('triangle', 'med', 'med'),
            'stealth': PowerPointLineEnd('stealth', 'med', 'med'),
            'diamond': PowerPointLineEnd('diamond', 'med', 'med'),
            'oval': PowerPointLineEnd('oval', 'med', 'med'),
            'square': PowerPointLineEnd('square', 'med', 'med'),
        }

        # Common arrowhead geometries for PowerPoint compatibility
        self.standard_arrows = {
            'arrow': self._create_arrow_path(),
            'circle': self._create_circle_path(),
            'square': self._create_square_path(),
            'diamond': self._create_diamond_path(),
        }

    def process_marker_definitions(self, svg_root: ET.Element) -> None:
        """
        Extract marker definitions from SVG document.

        Args:
            svg_root: Root SVG element
        """
        # Find all marker definitions (namespace-aware)
        namespaces = {'svg': 'http://www.w3.org/2000/svg'}
        markers = svg_root.xpath('.//svg:marker', namespaces=namespaces)

        # Fallback: try without namespace
        if not markers:
            markers = [elem for elem in svg_root.iter() if elem.tag.endswith('marker')]

        for marker_elem in markers:
            definition = self._parse_marker_definition(marker_elem)
            if definition:
                self.markers[definition.id] = definition
                logger.debug(f"Processed marker definition: {definition.id}")

        # Also process symbol definitions
        symbols = svg_root.xpath('.//svg:symbol', namespaces=namespaces)
        if not symbols:
            symbols = [elem for elem in svg_root.iter() if elem.tag.endswith('symbol')]

        for symbol_elem in symbols:
            definition = self._parse_symbol_definition(symbol_elem)
            if definition:
                self.symbols[definition.id] = definition
                logger.debug(f"Processed symbol definition: {definition.id}")

    def get_marker_for_element(self, element: ET.Element, position: MarkerPosition) -> Optional[MarkerDefinition]:
        """
        Get marker definition for element at specified position.

        Args:
            element: SVG element with marker properties
            position: Marker position (start, mid, end)

        Returns:
            MarkerDefinition if found, None otherwise
        """
        marker_attr = element.get(position.value)
        if not marker_attr:
            return None

        # Parse marker reference: url(#marker-id)
        match = re.match(r'url\(#([^)]+)\)', marker_attr)
        if match:
            marker_id = match.group(1)
            return self.markers.get(marker_id)

        return None

    def generate_powerpoint_line_end(self, marker: MarkerDefinition, position: MarkerPosition) -> Optional[str]:
        """
        Generate PowerPoint line end XML for marker.

        Args:
            marker: Marker definition
            position: Position on path

        Returns:
            XML string for PowerPoint line end
        """
        # Analyze marker content to determine best PowerPoint equivalent
        powerpoint_type = self._analyze_marker_geometry(marker)

        if not powerpoint_type:
            return None

        # Generate appropriate XML based on position
        if position == MarkerPosition.START:
            return f'<a:headEnd type="{powerpoint_type.type}" w="{powerpoint_type.w}" len="{powerpoint_type.len}"/>'
        elif position == MarkerPosition.END:
            return f'<a:tailEnd type="{powerpoint_type.type}" w="{powerpoint_type.w}" len="{powerpoint_type.len}"/>'

        # PowerPoint doesn't support mid-markers directly
        return None

    def apply_markers_to_path_xml(self, path_element: ET.Element, line_xml: str) -> str:
        """
        Apply markers to path line XML.

        Args:
            path_element: SVG path element with marker properties
            line_xml: Current line XML

        Returns:
            Enhanced line XML with marker properties
        """
        enhanced_xml_parts = [line_xml]

        # Check for start marker
        start_marker = self.get_marker_for_element(path_element, MarkerPosition.START)
        if start_marker:
            start_xml = self.generate_powerpoint_line_end(start_marker, MarkerPosition.START)
            if start_xml:
                enhanced_xml_parts.append(start_xml)

        # Check for end marker
        end_marker = self.get_marker_for_element(path_element, MarkerPosition.END)
        if end_marker:
            end_xml = self.generate_powerpoint_line_end(end_marker, MarkerPosition.END)
            if end_xml:
                enhanced_xml_parts.append(end_xml)

        return ''.join(enhanced_xml_parts)

    def _parse_marker_definition(self, marker_elem: ET.Element) -> Optional[MarkerDefinition]:
        """Parse marker element into definition."""
        marker_id = marker_elem.get('id')
        if not marker_id:
            return None

        # Parse marker attributes
        ref_x = float(marker_elem.get('refX', '0'))
        ref_y = float(marker_elem.get('refY', '0'))
        marker_width = float(marker_elem.get('markerWidth', '3'))
        marker_height = float(marker_elem.get('markerHeight', '3'))
        orient = marker_elem.get('orient', 'auto')

        marker_units_str = marker_elem.get('markerUnits', 'strokeWidth')
        marker_units = MarkerUnits.STROKE_WIDTH if marker_units_str == 'strokeWidth' else MarkerUnits.USER_SPACE_ON_USE

        overflow = marker_elem.get('overflow', 'hidden')

        # Parse viewBox if present
        viewbox = None
        viewbox_str = marker_elem.get('viewBox')
        if viewbox_str:
            try:
                values = [float(v) for v in viewbox_str.split()]
                if len(values) == 4:
                    viewbox = tuple(values)
            except ValueError:
                pass

        # Extract inner content as XML
        content_xml = ''.join(ET.tostring(child, encoding='unicode') for child in marker_elem)

        return MarkerDefinition(
            id=marker_id,
            ref_x=ref_x,
            ref_y=ref_y,
            marker_width=marker_width,
            marker_height=marker_height,
            orient=orient,
            marker_units=marker_units,
            viewbox=viewbox,
            overflow=overflow,
            content_xml=content_xml
        )

    def _analyze_marker_geometry(self, marker: MarkerDefinition) -> Optional[PowerPointLineEnd]:
        """
        Analyze marker geometry to determine best PowerPoint equivalent.

        Args:
            marker: Marker definition

        Returns:
            PowerPoint line end configuration
        """
        content = marker.content_xml.lower()

        # Simple heuristics for common marker types
        if 'path' in content and ('triangle' in content or 'arrow' in content):
            return self.powerpoint_arrows['arrow']
        elif 'circle' in content or 'ellipse' in content:
            return self.powerpoint_arrows['oval']
        elif 'rect' in content or 'square' in content:
            return self.powerpoint_arrows['square']
        elif 'diamond' in content or 'rhombus' in content:
            return self.powerpoint_arrows['diamond']
        elif 'stealth' in content:
            return self.powerpoint_arrows['stealth']

        # Default to triangle arrow
        return self.powerpoint_arrows['arrow']

    def _parse_symbol_definition(self, symbol_elem: ET.Element) -> Optional[SymbolDefinition]:
        """Parse symbol definition from SVG element."""
        symbol_id = symbol_elem.get('id')
        if not symbol_id:
            return None

        # Parse viewBox if present
        viewbox = None
        viewbox_str = symbol_elem.get('viewBox')
        if viewbox_str:
            try:
                parts = re.split(r'[,\s]+', viewbox_str.strip())
                if len(parts) == 4:
                    viewbox = tuple(float(p) for p in parts)
            except ValueError:
                pass

        preserve_aspect_ratio = symbol_elem.get('preserveAspectRatio', 'xMidYMid meet')

        # Parse dimensions
        width = None
        height = None
        if symbol_elem.get('width'):
            try:
                width = float(symbol_elem.get('width'))
            except ValueError:
                pass
        if symbol_elem.get('height'):
            try:
                height = float(symbol_elem.get('height'))
            except ValueError:
                pass

        # Extract inner content as XML
        content_xml = ''.join(ET.tostring(child, encoding='unicode') for child in symbol_elem)

        return SymbolDefinition(
            id=symbol_id,
            viewbox=viewbox,
            preserve_aspect_ratio=preserve_aspect_ratio,
            width=width,
            height=height,
            content_xml=content_xml
        )

    def process_use_element(self, use_elem: ET.Element) -> Optional[str]:
        """
        Process <use> element and generate appropriate XML.

        Args:
            use_elem: SVG use element

        Returns:
            Generated XML for the instantiated symbol/element
        """
        href = use_elem.get('href') or use_elem.get('{http://www.w3.org/1999/xlink}href')
        if not href or not href.startswith('#'):
            return None

        symbol_id = href[1:]  # Remove '#' prefix

        # Check if it references a symbol
        if symbol_id in self.symbols:
            symbol = self.symbols[symbol_id]
            return self._instantiate_symbol(symbol, use_elem)

        return None

    def _instantiate_symbol(self, symbol: SymbolDefinition, use_elem: ET.Element) -> str:
        """Instantiate a symbol definition with use element transforms."""
        # Get use element transforms
        x = float(use_elem.get('x', '0'))
        y = float(use_elem.get('y', '0'))
        width = use_elem.get('width')
        height = use_elem.get('height')
        transform = use_elem.get('transform', '')

        # Build transformation matrix
        transform_parts = []
        if x != 0 or y != 0:
            transform_parts.append(f"translate({x},{y})")

        if width and height and symbol.viewbox:
            # Calculate scaling based on viewbox vs use dimensions
            try:
                use_width = float(width)
                use_height = float(height)
                vb_width = symbol.viewbox[2] - symbol.viewbox[0]
                vb_height = symbol.viewbox[3] - symbol.viewbox[1]

                scale_x = use_width / vb_width if vb_width != 0 else 1
                scale_y = use_height / vb_height if vb_height != 0 else 1

                if scale_x != 1 or scale_y != 1:
                    transform_parts.append(f"scale({scale_x},{scale_y})")
            except ValueError:
                pass

        if transform:
            transform_parts.append(transform)

        # Generate group with transforms and symbol content
        if transform_parts:
            transform_attr = ' '.join(transform_parts)
            return f'<g transform="{transform_attr}">{symbol.content_xml}</g>'
        else:
            return f'<g>{symbol.content_xml}</g>'

    def _create_arrow_path(self) -> str:
        """Create standard arrow path."""
        return "M 0,0 L 10,3 L 0,6 z"

    def _create_circle_path(self) -> str:
        """Create circle marker path."""
        return "M 0,3 A 3,3 0 0,0 6,3 A 3,3 0 0,0 0,3 z"

    def _create_square_path(self) -> str:
        """Create square marker path."""
        return "M 0,0 L 6,0 L 6,6 L 0,6 z"

    def _create_diamond_path(self) -> str:
        """Create diamond marker path."""
        return "M 3,0 L 6,3 L 3,6 L 0,3 z"

    def get_symbol(self, symbol_id: str) -> Optional[SymbolDefinition]:
        """Get symbol definition by ID."""
        return self.symbols.get(symbol_id)

    def has_marker(self, marker_id: str) -> bool:
        """Check if marker definition exists."""
        return marker_id in self.markers

    def has_symbol(self, symbol_id: str) -> bool:
        """Check if symbol definition exists."""
        return symbol_id in self.symbols


def create_marker_processor() -> MarkerProcessor:
    """Create marker processor for use in mappers."""
    return MarkerProcessor()