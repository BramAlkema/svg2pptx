#!/usr/bin/env python3
"""
WordArt Color Mapping Service

Lightweight service that leverages existing gradient and color infrastructure
to map SVG fills/strokes to PowerPoint DrawingML for WordArt.
"""

from typing import Dict, Any, Optional
from lxml import etree as ET

from ..color import Color
from ..converters.gradients.converter import GradientConverter
from ..converters.gradients.core import GradientEngine
from ..services.conversion_services import ConversionServices
from ..converters.base import ConversionContext


class WordArtColorMappingService:
    """
    Maps SVG colors and gradients to PowerPoint DrawingML format for WordArt.

    Leverages existing gradient infrastructure while providing WordArt-specific
    optimizations and simplifications.
    """

    def __init__(self, services: ConversionServices):
        """
        Initialize with conversion services.

        Args:
            services: ConversionServices container
        """
        self.services = services
        self.gradient_converter = GradientConverter(services)
        self.gradient_engine = GradientEngine(optimization_level=2)

    def map_solid_fill(self, color: str, opacity: float = 1.0) -> ET.Element:
        """
        Map solid color to DrawingML solidFill element.

        Args:
            color: Color value (hex, rgb, named color, etc.)
            opacity: Opacity value (0.0 to 1.0)

        Returns:
            XML element for <a:solidFill>
        """
        a_ns = "{http://schemas.openxmlformats.org/drawingml/2006/main}"

        # Parse color using existing color system
        try:
            parsed_color = Color(color)
            hex_color = parsed_color.hex().upper()
        except Exception:
            # Fallback to black if parsing fails
            hex_color = "000000"

        # Create solidFill element
        solid_fill = ET.Element(f"{a_ns}solidFill")
        srgb_clr = ET.SubElement(solid_fill, f"{a_ns}srgbClr")
        srgb_clr.set("val", hex_color)

        # Add alpha if not fully opaque
        if opacity < 1.0:
            alpha = ET.SubElement(srgb_clr, f"{a_ns}alpha")
            # PowerPoint uses percentage (0-100000)
            alpha_val = int(opacity * 100000)
            alpha.set("val", str(alpha_val))

        return solid_fill

    def map_gradient_fill(self, gradient_element: ET.Element,
                         context: ConversionContext) -> Optional[ET.Element]:
        """
        Map SVG gradient to DrawingML gradient using existing infrastructure.

        Args:
            gradient_element: SVG gradient element
            context: Conversion context

        Returns:
            DrawingML gradient element or None if conversion fails
        """
        try:
            # Use existing gradient converter
            if self.gradient_converter.can_convert(gradient_element, context):
                # Convert using existing infrastructure
                gradient_xml = self.gradient_converter.convert(gradient_element, context)

                # Parse the XML string back to element
                if gradient_xml and gradient_xml.strip():
                    return ET.fromstring(gradient_xml)

        except Exception as e:
            # Log error and return None for fallback
            print(f"Gradient conversion failed: {e}")

        return None

    def map_fill_reference(self, fill_url: str, svg_defs: ET.Element,
                          context: ConversionContext) -> Optional[ET.Element]:
        """
        Map SVG fill reference (url(#id)) to DrawingML fill.

        Args:
            fill_url: Fill reference URL (e.g., "url(#gradient1)")
            svg_defs: SVG defs element containing definitions
            context: Conversion context

        Returns:
            DrawingML fill element or None if not mappable
        """
        # Extract ID from URL
        if not fill_url.startswith('url(#') or not fill_url.endswith(')'):
            return None

        gradient_id = fill_url[5:-1]

        # Find gradient definition
        gradient = self._find_gradient(gradient_id, svg_defs)
        if gradient is None:
            return None

        # Map using existing gradient infrastructure
        return self.map_gradient_fill(gradient, context)

    def simplify_for_wordart(self, gradient_element: ET.Element) -> ET.Element:
        """
        Simplify gradient for WordArt compatibility.

        WordArt has limitations on gradient complexity, so we apply
        simplifications to ensure compatibility.

        Args:
            gradient_element: Original gradient element

        Returns:
            Simplified gradient element
        """
        # Clone element for modification
        simplified = ET.Element(gradient_element.tag, gradient_element.attrib)

        # Copy and limit gradient stops (max 8 for WordArt)
        stops = list(gradient_element.findall('.//{http://www.w3.org/2000/svg}stop'))

        if len(stops) <= 8:
            # Use all stops if within limit
            for stop in stops:
                simplified.append(stop)
        else:
            # Reduce stops using intelligent selection
            simplified_stops = self._reduce_gradient_stops(stops, max_stops=8)
            for stop in simplified_stops:
                simplified.append(stop)

        return simplified

    def _find_gradient(self, gradient_id: str, svg_defs: ET.Element) -> Optional[ET.Element]:
        """Find gradient definition by ID."""
        # Try to find in defs
        gradient = svg_defs.find(f".//*[@id='{gradient_id}']")

        if gradient is not None:
            return gradient

        # Try without namespace
        for child in svg_defs.iter():
            if child.get('id') == gradient_id:
                return child

        return None

    def _reduce_gradient_stops(self, stops: list, max_stops: int = 8) -> list:
        """
        Reduce gradient stops to maximum count using intelligent selection.

        Args:
            stops: Original gradient stops
            max_stops: Maximum number of stops to keep

        Returns:
            Reduced list of gradient stops
        """
        if len(stops) <= max_stops:
            return stops

        # Always keep first and last stops
        if max_stops < 2:
            return stops[:max_stops]

        reduced = [stops[0]]
        remaining_slots = max_stops - 2  # Reserve slots for first and last

        if remaining_slots > 0:
            # Select intermediate stops with even spacing
            step = (len(stops) - 2) / (remaining_slots + 1)
            for i in range(1, remaining_slots + 1):
                index = int(round(i * step))
                if index < len(stops) - 1:
                    reduced.append(stops[index])

        # Add last stop
        reduced.append(stops[-1])

        return reduced


def create_wordart_color_mapping_service(services: ConversionServices) -> WordArtColorMappingService:
    """
    Factory function to create WordArt color mapping service.

    Args:
        services: ConversionServices container

    Returns:
        WordArtColorMappingService instance
    """
    return WordArtColorMappingService(services)