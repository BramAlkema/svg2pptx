#!/usr/bin/env python3
"""
WordArt Gradient Mapper

Converts complex SVG gradients to PowerPoint-compatible DrawingML gradients.
Handles pattern fills, mesh gradients, and other advanced gradient types.
"""

from typing import Dict, List, Any, Optional, Tuple
from lxml import etree as ET
import math

from ..services.wordart_color_service import (
    WordArtColorMappingService,
    LinearGradientInfo,
    RadialGradientInfo,
    GradientStop
)


class WordArtGradientMapper:
    """
    Maps complex SVG gradients to PowerPoint DrawingML format.

    Provides approximation strategies for unsupported gradient types
    like mesh gradients and pattern fills.
    """

    def __init__(self):
        """Initialize gradient mapper."""
        self.color_service = WordArtColorMappingService()

    def map_gradient_reference(self, element: ET.Element, fill_url: str,
                              svg_defs: ET.Element) -> Optional[ET.Element]:
        """
        Map SVG gradient reference to DrawingML fill.

        Args:
            element: SVG element with gradient fill
            fill_url: Gradient reference URL (e.g., "url(#gradient1)")
            svg_defs: SVG defs element containing gradient definitions

        Returns:
            DrawingML fill element or None if not mappable
        """
        # Extract gradient ID from URL
        gradient_id = self._extract_gradient_id(fill_url)
        if not gradient_id:
            return None

        # Find gradient definition
        gradient = self._find_gradient(gradient_id, svg_defs)
        if gradient is None:
            return None

        # Check for gradient chaining (gradientUnits, xlink:href)
        gradient = self._resolve_gradient_chain(gradient, svg_defs)

        # Parse and map gradient
        try:
            gradient_info = self.color_service.parse_svg_gradient(gradient)

            if isinstance(gradient_info, LinearGradientInfo):
                # Apply gradient transform if present
                if gradient.get('gradientTransform'):
                    gradient_info = self._apply_gradient_transform(
                        gradient_info, gradient.get('gradientTransform')
                    )
                return self.color_service.map_linear_gradient(gradient_info)

            elif isinstance(gradient_info, RadialGradientInfo):
                # Apply gradient transform if present
                if gradient.get('gradientTransform'):
                    gradient_info = self._apply_gradient_transform(
                        gradient_info, gradient.get('gradientTransform')
                    )
                return self.color_service.map_radial_gradient(gradient_info)

        except Exception as e:
            # Log error and return None
            print(f"Failed to map gradient {gradient_id}: {e}")
            return None

        return None

    def approximate_mesh_gradient(self, mesh_element: ET.Element) -> ET.Element:
        """
        Approximate SVG mesh gradient as radial gradient.

        Mesh gradients are not supported in PowerPoint, so we create
        a radial gradient approximation based on the mesh corners.

        Args:
            mesh_element: SVG meshGradient element

        Returns:
            DrawingML gradFill approximation
        """
        # Extract corner colors from mesh patches
        corner_colors = self._extract_mesh_corners(mesh_element)

        if len(corner_colors) < 2:
            # Fallback to solid fill
            return self.color_service.map_solid_fill("#808080")

        # Create radial gradient from center to corners
        stops = []
        for i, color in enumerate(corner_colors[:4]):  # Max 4 corners
            position = i / (len(corner_colors) - 1)
            stops.append(GradientStop(position, color, 1.0))

        # Create radial gradient centered in shape
        radial_info = RadialGradientInfo(
            cx=0.5, cy=0.5, r=0.7,  # Slightly larger radius
            stops=stops
        )

        return self.color_service.map_radial_gradient(radial_info)

    def approximate_pattern_fill(self, pattern_element: ET.Element) -> ET.Element:
        """
        Approximate SVG pattern fill as solid or gradient fill.

        Patterns are not directly supported in PowerPoint WordArt,
        so we extract dominant colors and create an approximation.

        Args:
            pattern_element: SVG pattern element

        Returns:
            DrawingML fill approximation
        """
        # Extract dominant colors from pattern
        colors = self._extract_pattern_colors(pattern_element)

        if len(colors) == 0:
            # Fallback to gray
            return self.color_service.map_solid_fill("#808080")
        elif len(colors) == 1:
            # Single color pattern
            return self.color_service.map_solid_fill(colors[0])
        else:
            # Create linear gradient from pattern colors
            stops = []
            for i, color in enumerate(colors[:4]):  # Max 4 colors
                position = i / (len(colors) - 1) if len(colors) > 1 else 0
                stops.append(GradientStop(position, color, 1.0))

            linear_info = LinearGradientInfo(
                x1=0, y1=0, x2=1, y2=1,  # Diagonal gradient
                stops=stops
            )

            return self.color_service.map_linear_gradient(linear_info)

    def _extract_gradient_id(self, fill_url: str) -> Optional[str]:
        """Extract gradient ID from URL reference."""
        if fill_url.startswith('url(#') and fill_url.endswith(')'):
            return fill_url[5:-1]
        return None

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

    def _resolve_gradient_chain(self, gradient: ET.Element,
                               svg_defs: ET.Element) -> ET.Element:
        """
        Resolve gradient inheritance chain.

        SVG gradients can inherit from other gradients via xlink:href.

        Args:
            gradient: Gradient element to resolve
            svg_defs: SVG defs containing gradient definitions

        Returns:
            Fully resolved gradient element
        """
        # Check for xlink:href reference
        href = gradient.get('{http://www.w3.org/1999/xlink}href')
        if not href:
            href = gradient.get('href')

        if href and href.startswith('#'):
            # Find parent gradient
            parent_id = href[1:]
            parent = self._find_gradient(parent_id, svg_defs)

            if parent is not None:
                # Recursively resolve parent
                parent = self._resolve_gradient_chain(parent, svg_defs)

                # Merge attributes (child overrides parent)
                merged = ET.Element(gradient.tag)

                # Copy parent attributes
                for attr, value in parent.attrib.items():
                    merged.set(attr, value)

                # Override with child attributes
                for attr, value in gradient.attrib.items():
                    merged.set(attr, value)

                # Copy stops (use child stops if present, otherwise parent)
                child_stops = list(gradient.findall('.//{http://www.w3.org/2000/svg}stop'))
                if child_stops:
                    for stop in child_stops:
                        merged.append(stop)
                else:
                    parent_stops = list(parent.findall('.//{http://www.w3.org/2000/svg}stop'))
                    for stop in parent_stops:
                        merged.append(stop)

                return merged

        return gradient

    def _apply_gradient_transform(self, gradient_info: Any,
                                 transform_str: str) -> Any:
        """
        Apply gradientTransform to gradient coordinates.

        Note: This is a simplified implementation that handles
        common transforms like rotate and scale.

        Args:
            gradient_info: Gradient information object
            transform_str: SVG transform string

        Returns:
            Modified gradient information
        """
        # Parse transform (simplified - handles rotate primarily)
        if 'rotate(' in transform_str:
            # Extract rotation angle
            start = transform_str.index('rotate(') + 7
            end = transform_str.index(')', start)
            angle_str = transform_str[start:end].split(',')[0]
            angle = float(angle_str)

            if isinstance(gradient_info, LinearGradientInfo):
                # Apply rotation to linear gradient
                # Convert current vector to angle
                dx = gradient_info.x2 - gradient_info.x1
                dy = gradient_info.y2 - gradient_info.y1
                length = math.sqrt(dx*dx + dy*dy)

                if length > 0:
                    # Calculate new angle
                    current_angle = math.degrees(math.atan2(dy, dx))
                    new_angle = current_angle + angle

                    # Convert back to coordinates
                    new_angle_rad = math.radians(new_angle)
                    gradient_info.x2 = gradient_info.x1 + length * math.cos(new_angle_rad)
                    gradient_info.y2 = gradient_info.y1 + length * math.sin(new_angle_rad)

        return gradient_info

    def _extract_mesh_corners(self, mesh_element: ET.Element) -> List[str]:
        """Extract corner colors from mesh gradient patches."""
        colors = []

        # Look for meshpatch elements
        for patch in mesh_element.findall('.//{http://www.w3.org/2000/svg}meshpatch'):
            # Get stop colors from patch
            for stop in patch.findall('.//{http://www.w3.org/2000/svg}stop'):
                color = stop.get('stop-color')
                if color:
                    colors.append(color)

        # Limit to reasonable number
        return colors[:8]

    def _extract_pattern_colors(self, pattern_element: ET.Element) -> List[str]:
        """Extract dominant colors from pattern definition."""
        colors = []

        # Look for fill colors in pattern content
        for child in pattern_element.iter():
            fill = child.get('fill')
            if fill and not fill.startswith('url('):
                if fill not in colors:
                    colors.append(fill)

            stroke = child.get('stroke')
            if stroke and not stroke.startswith('url('):
                if stroke not in colors:
                    colors.append(stroke)

            # Check style attribute
            style = child.get('style', '')
            for prop in style.split(';'):
                if 'fill:' in prop:
                    color = prop.split(':')[1].strip()
                    if not color.startswith('url(') and color not in colors:
                        colors.append(color)
                elif 'stroke:' in prop:
                    color = prop.split(':')[1].strip()
                    if not color.startswith('url(') and color not in colors:
                        colors.append(color)

        # Limit to reasonable number
        return colors[:4]


def create_wordart_gradient_mapper() -> WordArtGradientMapper:
    """
    Factory function to create WordArt gradient mapper.

    Returns:
        WordArtGradientMapper instance
    """
    return WordArtGradientMapper()