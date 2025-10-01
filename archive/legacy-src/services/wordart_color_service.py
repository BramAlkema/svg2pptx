#!/usr/bin/env python3
"""
WordArt Color and Fill Mapping Service

Maps SVG fills, strokes, and gradients to PowerPoint DrawingML color elements.
Handles gradient simplification and unsupported gradient type approximation.
"""

from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass
from lxml import etree as ET
import math

from ..color import Color
from ..utils.xml_builder import XMLBuilder


@dataclass
class GradientStop:
    """Represents a gradient stop with position and color."""

    position: float  # 0.0 to 1.0
    color: str      # Hex color value
    opacity: float  # 0.0 to 1.0


@dataclass
class LinearGradientInfo:
    """Linear gradient definition."""

    x1: float = 0.0
    y1: float = 0.0
    x2: float = 1.0
    y2: float = 0.0
    stops: List[GradientStop] = None

    def __post_init__(self):
        if self.stops is None:
            self.stops = []

    @property
    def angle_degrees(self) -> float:
        """Calculate gradient angle in degrees."""
        dx = self.x2 - self.x1
        dy = self.y2 - self.y1
        # PowerPoint angles are clockwise from right (0° = right)
        angle = math.degrees(math.atan2(dy, dx))
        # Normalize to 0-360 range
        return (angle + 360) % 360


@dataclass
class RadialGradientInfo:
    """Radial gradient definition."""

    cx: float = 0.5  # Center X (0.0 to 1.0)
    cy: float = 0.5  # Center Y (0.0 to 1.0)
    r: float = 0.5   # Radius (0.0 to 1.0)
    fx: float = None  # Focal X (defaults to cx)
    fy: float = None  # Focal Y (defaults to cy)
    stops: List[GradientStop] = None

    def __post_init__(self):
        if self.fx is None:
            self.fx = self.cx
        if self.fy is None:
            self.fy = self.cy
        if self.stops is None:
            self.stops = []


class WordArtColorMappingService:
    """
    Maps SVG colors and gradients to PowerPoint DrawingML format.

    Handles solid fills, linear/radial gradients, and gradient simplification
    for PowerPoint compatibility.
    """

    # PowerPoint gradient stop limits
    MAX_GRADIENT_STOPS = 8

    # Common gradient angles to snap to (for better PowerPoint rendering)
    SNAP_ANGLES = [0, 45, 90, 135, 180, 225, 270, 315, 360]
    ANGLE_SNAP_THRESHOLD = 5  # Degrees

    def __init__(self):
        """Initialize color mapping service."""
        self.xml_builder = XMLBuilder()

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

        # Parse color to standardized hex format
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

    def map_linear_gradient(self, gradient: LinearGradientInfo) -> ET.Element:
        """
        Map linear gradient to DrawingML gradFill element.

        Args:
            gradient: Linear gradient information

        Returns:
            XML element for <a:gradFill>
        """
        a_ns = "{http://schemas.openxmlformats.org/drawingml/2006/main}"

        # Simplify gradient if needed
        simplified_stops = self._simplify_gradient_stops(gradient.stops)

        # Create gradFill element
        grad_fill = ET.Element(f"{a_ns}gradFill")
        grad_fill.set("flip", "none")
        grad_fill.set("rotWithShape", "1")

        # Add gradient stops
        gs_lst = ET.SubElement(grad_fill, f"{a_ns}gsLst")
        for stop in simplified_stops:
            gs = ET.SubElement(gs_lst, f"{a_ns}gs")
            # Position as percentage (0-100000)
            gs.set("pos", str(int(stop.position * 100000)))

            # Parse and add color
            try:
                parsed_color = Color(stop.color)
                hex_color = parsed_color.hex().upper()
            except Exception:
                hex_color = "000000"

            srgb_clr = ET.SubElement(gs, f"{a_ns}srgbClr")
            srgb_clr.set("val", hex_color)

            # Add opacity if not fully opaque
            if stop.opacity < 1.0:
                alpha = ET.SubElement(srgb_clr, f"{a_ns}alpha")
                alpha.set("val", str(int(stop.opacity * 100000)))

        # Add linear gradient path
        lin = ET.SubElement(grad_fill, f"{a_ns}lin")

        # Calculate and snap angle
        angle = gradient.angle_degrees
        snapped_angle = self._snap_angle(angle)

        # Convert to PowerPoint angle units (1/60000 degrees)
        angle_units = int(snapped_angle * 60000)
        lin.set("ang", str(angle_units))
        lin.set("scaled", "0")

        return grad_fill

    def map_radial_gradient(self, gradient: RadialGradientInfo) -> ET.Element:
        """
        Map radial gradient to DrawingML gradFill element.

        PowerPoint's radial gradients are center-based, so we approximate
        focal point offsets using the tile rect.

        Args:
            gradient: Radial gradient information

        Returns:
            XML element for <a:gradFill>
        """
        a_ns = "{http://schemas.openxmlformats.org/drawingml/2006/main}"

        # Simplify gradient if needed
        simplified_stops = self._simplify_gradient_stops(gradient.stops)

        # Create gradFill element
        grad_fill = ET.Element(f"{a_ns}gradFill")
        grad_fill.set("flip", "none")
        grad_fill.set("rotWithShape", "1")

        # Add gradient stops (reverse order for radial)
        gs_lst = ET.SubElement(grad_fill, f"{a_ns}gsLst")
        for stop in reversed(simplified_stops):
            gs = ET.SubElement(gs_lst, f"{a_ns}gs")
            # Invert position for radial (PowerPoint goes from center out)
            pos = 1.0 - stop.position
            gs.set("pos", str(int(pos * 100000)))

            # Parse and add color
            try:
                parsed_color = Color(stop.color)
                hex_color = parsed_color.hex().upper()
            except Exception:
                hex_color = "000000"

            srgb_clr = ET.SubElement(gs, f"{a_ns}srgbClr")
            srgb_clr.set("val", hex_color)

            # Add opacity if not fully opaque
            if stop.opacity < 1.0:
                alpha = ET.SubElement(srgb_clr, f"{a_ns}alpha")
                alpha.set("val", str(int(stop.opacity * 100000)))

        # Add path type for radial/circular gradient
        path = ET.SubElement(grad_fill, f"{a_ns}path")
        path.set("path", "circle")

        # Fill the entire shape
        fill_to_rect = ET.SubElement(path, f"{a_ns}fillToRect")

        # Calculate tile rect based on center and focal point offset
        # This approximates SVG focal point behavior
        fx_offset = (gradient.fx - gradient.cx) * 0.5
        fy_offset = (gradient.fy - gradient.cy) * 0.5

        # PowerPoint tile rect values (percentages)
        left = int((0.5 - gradient.r + fx_offset) * 100000)
        top = int((0.5 - gradient.r + fy_offset) * 100000)
        right = int((0.5 + gradient.r + fx_offset) * 100000)
        bottom = int((0.5 + gradient.r + fy_offset) * 100000)

        # Clamp to valid range
        left = max(-100000, min(100000, left))
        top = max(-100000, min(100000, top))
        right = max(-100000, min(100000, right))
        bottom = max(-100000, min(100000, bottom))

        fill_to_rect.set("l", str(left))
        fill_to_rect.set("t", str(top))
        fill_to_rect.set("r", str(right))
        fill_to_rect.set("b", str(bottom))

        return grad_fill

    def _simplify_gradient_stops(self, stops: List[GradientStop]) -> List[GradientStop]:
        """
        Simplify gradient stops to PowerPoint's maximum of 8 stops.

        Uses intelligent stop selection to preserve gradient appearance.

        Args:
            stops: Original gradient stops

        Returns:
            Simplified list of gradient stops (max 8)
        """
        if len(stops) <= self.MAX_GRADIENT_STOPS:
            return stops

        # Always keep first and last stops
        simplified = [stops[0]]

        # Calculate importance scores for middle stops
        # based on color difference from neighbors
        scores = []
        for i in range(1, len(stops) - 1):
            prev_color = Color(stops[i-1].color)
            curr_color = Color(stops[i].color)
            next_color = Color(stops[i+1].color)

            # Calculate color distances
            dist_prev = self._color_distance(prev_color, curr_color)
            dist_next = self._color_distance(curr_color, next_color)

            # Higher score = more important to keep
            score = dist_prev + dist_next
            scores.append((score, i, stops[i]))

        # Sort by importance and keep most important stops
        scores.sort(reverse=True)
        keep_count = self.MAX_GRADIENT_STOPS - 2  # Minus first and last

        for _, _, stop in scores[:keep_count]:
            simplified.append(stop)

        # Add last stop
        simplified.append(stops[-1])

        # Sort by position
        simplified.sort(key=lambda s: s.position)

        return simplified

    def _color_distance(self, color1: Color, color2: Color) -> float:
        """
        Calculate perceptual distance between two colors.

        Uses simple RGB Euclidean distance.

        Args:
            color1: First color
            color2: Second color

        Returns:
            Distance value (0 = identical)
        """
        r1, g1, b1 = color1.rgb()
        r2, g2, b2 = color2.rgb()

        # Normalize to 0-1 range
        r1, g1, b1 = r1/255, g1/255, b1/255
        r2, g2, b2 = r2/255, g2/255, b2/255

        # Euclidean distance
        return math.sqrt((r2-r1)**2 + (g2-g1)**2 + (b2-b1)**2)

    def _snap_angle(self, angle: float) -> float:
        """
        Snap gradient angle to common angles for better PowerPoint rendering.

        Args:
            angle: Original angle in degrees

        Returns:
            Snapped angle if within threshold, original otherwise
        """
        for snap_angle in self.SNAP_ANGLES:
            if abs(angle - snap_angle) <= self.ANGLE_SNAP_THRESHOLD:
                return snap_angle

        return angle

    def parse_svg_gradient(self, gradient_element: ET.Element) -> Union[LinearGradientInfo, RadialGradientInfo]:
        """
        Parse SVG gradient element to gradient info.

        Args:
            gradient_element: SVG linearGradient or radialGradient element

        Returns:
            Parsed gradient information
        """
        if gradient_element.tag.endswith('linearGradient'):
            return self._parse_linear_gradient(gradient_element)
        elif gradient_element.tag.endswith('radialGradient'):
            return self._parse_radial_gradient(gradient_element)
        else:
            raise ValueError(f"Unsupported gradient type: {gradient_element.tag}")

    def _parse_linear_gradient(self, element: ET.Element) -> LinearGradientInfo:
        """Parse SVG linearGradient element."""
        # Get coordinates (default to 0,0 -> 1,0 for horizontal)
        x1 = float(element.get('x1', '0'))
        y1 = float(element.get('y1', '0'))
        x2 = float(element.get('x2', '1'))
        y2 = float(element.get('y2', '0'))

        # Parse stops
        stops = self._parse_gradient_stops(element)

        return LinearGradientInfo(x1=x1, y1=y1, x2=x2, y2=y2, stops=stops)

    def _parse_radial_gradient(self, element: ET.Element) -> RadialGradientInfo:
        """Parse SVG radialGradient element."""
        # Get center and radius (defaults to 0.5 for centered)
        cx = float(element.get('cx', '0.5'))
        cy = float(element.get('cy', '0.5'))
        r = float(element.get('r', '0.5'))

        # Get focal point (defaults to center)
        fx = element.get('fx')
        fy = element.get('fy')
        fx = float(fx) if fx else cx
        fy = float(fy) if fy else cy

        # Parse stops
        stops = self._parse_gradient_stops(element)

        return RadialGradientInfo(cx=cx, cy=cy, r=r, fx=fx, fy=fy, stops=stops)

    def _parse_gradient_stops(self, gradient_element: ET.Element) -> List[GradientStop]:
        """Parse stop elements from gradient."""
        stops = []

        for stop in gradient_element.findall('.//{http://www.w3.org/2000/svg}stop'):
            # Get offset (position)
            offset = stop.get('offset', '0')
            if offset.endswith('%'):
                position = float(offset[:-1]) / 100
            else:
                position = float(offset)

            # Get color from stop-color or style
            color = stop.get('stop-color')
            opacity = float(stop.get('stop-opacity', '1'))

            if not color:
                # Try to parse from style attribute
                style = stop.get('style', '')
                for prop in style.split(';'):
                    if 'stop-color:' in prop:
                        color = prop.split(':')[1].strip()
                    elif 'stop-opacity:' in prop:
                        opacity = float(prop.split(':')[1].strip())

            if color:
                stops.append(GradientStop(
                    position=position,
                    color=color,
                    opacity=opacity
                ))

        # Ensure at least 2 stops
        if len(stops) == 0:
            stops = [
                GradientStop(0.0, "#000000", 1.0),
                GradientStop(1.0, "#FFFFFF", 1.0)
            ]
        elif len(stops) == 1:
            # Duplicate single stop
            stops.append(GradientStop(1.0, stops[0].color, stops[0].opacity))

        return stops


def create_wordart_color_service() -> WordArtColorMappingService:
    """
    Factory function to create WordArt color mapping service.

    Returns:
        WordArtColorMappingService instance
    """
    return WordArtColorMappingService()