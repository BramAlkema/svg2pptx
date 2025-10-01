"""
Service Integration Adapters for Boolean Operations

This module provides concrete adapters that integrate the boolean operation
backends with the existing SVG2PPTX path processing infrastructure.

These adapters bridge between:
- PathParser (src.paths.parser) for SVG d-string parsing
- DrawingMLGenerator for path serialization
- Existing curve approximation systems
"""

from __future__ import annotations
from typing import List, Any, Tuple, Optional
import logging

from .path_adapters import PathParser, PathSerializer, CurveApproximator
from .path_boolean_engine import FillRule

logger = logging.getLogger(__name__)


class SVG2PPTXPathParser:
    """Adapter for src.paths.parser.PathParser."""

    def __init__(self, path_parser):
        """
        Initialize with existing PathParser instance.

        Args:
            path_parser: Instance of src.paths.parser.PathParser
        """
        self.path_parser = path_parser

    def parse_path_commands(self, d_string: str) -> List[Any]:
        """
        Parse SVG d-string using existing PathParser.

        Args:
            d_string: SVG path d attribute value

        Returns:
            List of simplified command tuples for boolean operations
        """
        try:
            # Use existing PathParser to get structured PathCommand objects
            path_commands = self.path_parser.parse_path_data(d_string)

            # Convert to simplified format for boolean operations
            simplified_commands = []
            for cmd in path_commands:
                # Create simplified command tuple: [command_letter, *parameters]
                cmd_letter = cmd.original_command
                simplified_cmd = [cmd_letter] + list(cmd.parameters)
                simplified_commands.append(simplified_cmd)

            return simplified_commands

        except Exception as e:
            logger.warning(f"Path parsing failed with existing parser: {e}")
            return []


class SVG2PPTXPathSerializer:
    """Adapter for path serialization using existing infrastructure."""

    def __init__(self, drawingml_generator=None):
        """
        Initialize with optional DrawingML generator.

        Args:
            drawingml_generator: Optional existing DrawingML generator
        """
        self.drawingml_generator = drawingml_generator

    def serialize_path(self, path_data: Any) -> str:
        """
        Serialize path data back to SVG d-string.

        Args:
            path_data: Path data from boolean operations

        Returns:
            SVG d-string representation
        """
        try:
            if hasattr(path_data, 'asPath'):
                # Handle Skia paths - convert to d-string
                return self._serialize_skia_path(path_data)
            elif isinstance(path_data, list):
                # Handle polygon data - convert to path commands
                return self._serialize_polygon_list(path_data)
            else:
                # Fallback - convert to string
                return str(path_data)

        except Exception as e:
            logger.warning(f"Path serialization failed: {e}")
            return ""

    def _serialize_skia_path(self, skia_path: Any) -> str:
        """Convert Skia path to SVG d-string."""
        try:
            # Use Skia's built-in serialization
            # This is a simplified approach - real implementation would be more robust
            path_str = str(skia_path)

            # Basic conversion from Skia path representation to SVG
            # In practice, this would use proper Skia path iteration
            if 'empty' in path_str.lower():
                return ""

            # Placeholder implementation - would need proper Skia path iteration
            return "M 0 0"  # Fallback

        except Exception as e:
            logger.warning(f"Skia path serialization failed: {e}")
            return ""

    def _serialize_polygon_list(self, polygons: List[List[Tuple[float, float]]]) -> str:
        """Convert polygon list to SVG d-string."""
        if not polygons:
            return ""

        path_parts = []
        for polygon in polygons:
            if len(polygon) < 3:
                continue

            # Start with moveTo
            x, y = polygon[0]
            path_parts.append(f"M {x:.3f} {y:.3f}")

            # Add line segments
            for x, y in polygon[1:]:
                path_parts.append(f"L {x:.3f} {y:.3f}")

            # Close polygon
            path_parts.append("Z")

        return " ".join(path_parts)


class SVG2PPTXCurveApproximator:
    """Adapter for curve approximation using existing infrastructure."""

    def __init__(self, arc_converter=None, tolerance: float = 1.0):
        """
        Initialize with optional existing arc converter.

        Args:
            arc_converter: Optional existing ArcConverter instance
            tolerance: Approximation tolerance
        """
        self.arc_converter = arc_converter
        self.tolerance = tolerance

    def approximate_curves(self, commands: List[Any], tolerance: float = None) -> List[Any]:
        """
        Approximate curved commands with linear segments.

        Args:
            commands: List of path commands
            tolerance: Optional override for approximation tolerance

        Returns:
            List of commands with curves approximated as line segments
        """
        if tolerance is None:
            tolerance = self.tolerance

        linear_commands = []
        current_x, current_y = 0.0, 0.0

        for cmd in commands:
            if not cmd or len(cmd) == 0:
                continue

            cmd_type = cmd[0].upper()

            if cmd_type in ('M', 'L', 'Z'):
                # Keep linear commands as-is
                linear_commands.append(cmd)
                if cmd_type in ('M', 'L') and len(cmd) >= 3:
                    current_x, current_y = cmd[1], cmd[2]

            elif cmd_type == 'C':
                # Convert cubic bezier to line segments
                linear_segments = self._approximate_cubic_bezier(
                    current_x, current_y, cmd[1:], tolerance
                )
                linear_commands.extend(linear_segments)
                if len(cmd) >= 7:
                    current_x, current_y = cmd[5], cmd[6]

            elif cmd_type == 'Q':
                # Convert quadratic bezier to line segments
                linear_segments = self._approximate_quadratic_bezier(
                    current_x, current_y, cmd[1:], tolerance
                )
                linear_commands.extend(linear_segments)
                if len(cmd) >= 5:
                    current_x, current_y = cmd[3], cmd[4]

            elif cmd_type == 'A':
                # Convert arc to line segments
                if self.arc_converter:
                    linear_segments = self._approximate_arc_with_converter(
                        current_x, current_y, cmd[1:], tolerance
                    )
                else:
                    linear_segments = self._approximate_arc_simple(
                        current_x, current_y, cmd[1:], tolerance
                    )
                linear_commands.extend(linear_segments)
                if len(cmd) >= 8:
                    current_x, current_y = cmd[6], cmd[7]

            elif cmd_type in ('H', 'V'):
                # Convert horizontal/vertical lines to regular lines
                if cmd_type == 'H' and len(cmd) >= 2:
                    linear_commands.append(['L', cmd[1], current_y])
                    current_x = cmd[1]
                elif cmd_type == 'V' and len(cmd) >= 2:
                    linear_commands.append(['L', current_x, cmd[1]])
                    current_y = cmd[1]

            else:
                # Keep other commands as-is
                linear_commands.append(cmd)

        return linear_commands

    def _approximate_cubic_bezier(self, start_x: float, start_y: float,
                                params: List[float], tolerance: float) -> List[List[Any]]:
        """Approximate cubic bezier curve with line segments."""
        if len(params) < 6:
            return []

        x1, y1, x2, y2, x, y = params[:6]

        # Simple subdivision approach
        segments = []
        num_segments = max(2, int(10 / tolerance))  # More segments for higher accuracy

        for i in range(1, num_segments + 1):
            t = i / num_segments
            # Cubic bezier formula
            t_inv = 1 - t
            t_inv2 = t_inv * t_inv
            t_inv3 = t_inv2 * t_inv
            t2 = t * t
            t3 = t2 * t

            px = (t_inv3 * start_x + 3 * t_inv2 * t * x1 +
                  3 * t_inv * t2 * x2 + t3 * x)
            py = (t_inv3 * start_y + 3 * t_inv2 * t * y1 +
                  3 * t_inv * t2 * y2 + t3 * y)

            segments.append(['L', px, py])

        return segments

    def _approximate_quadratic_bezier(self, start_x: float, start_y: float,
                                    params: List[float], tolerance: float) -> List[List[Any]]:
        """Approximate quadratic bezier curve with line segments."""
        if len(params) < 4:
            return []

        x1, y1, x, y = params[:4]

        # Simple subdivision approach
        segments = []
        num_segments = max(2, int(8 / tolerance))  # Fewer segments than cubic

        for i in range(1, num_segments + 1):
            t = i / num_segments
            t_inv = 1 - t

            # Quadratic bezier formula
            px = t_inv * t_inv * start_x + 2 * t_inv * t * x1 + t * t * x
            py = t_inv * t_inv * start_y + 2 * t_inv * t * y1 + t * t * y

            segments.append(['L', px, py])

        return segments

    def _approximate_arc_with_converter(self, start_x: float, start_y: float,
                                      params: List[float], tolerance: float) -> List[List[Any]]:
        """Approximate arc using existing arc converter."""
        if len(params) < 7:
            return []

        try:
            rx, ry, x_axis_rotation, large_arc_flag, sweep_flag, end_x, end_y = params[:7]

            # Use existing arc converter to get bezier segments
            bezier_segments = self.arc_converter.arc_to_bezier_segments(
                start_x, start_y, rx, ry, x_axis_rotation,
                int(large_arc_flag), int(sweep_flag), end_x, end_y
            )

            # Convert bezier segments to line segments
            linear_segments = []
            current_x, current_y = start_x, start_y

            for segment in bezier_segments:
                # Each bezier segment has control points and end point
                cubic_params = [segment.x1, segment.y1, segment.x2, segment.y2,
                              segment.end_x, segment.end_y]
                lines = self._approximate_cubic_bezier(current_x, current_y, cubic_params, tolerance)
                linear_segments.extend(lines)
                current_x, current_y = segment.end_x, segment.end_y

            return linear_segments

        except Exception as e:
            logger.warning(f"Arc conversion with converter failed: {e}")
            return self._approximate_arc_simple(start_x, start_y, params, tolerance)

    def _approximate_arc_simple(self, start_x: float, start_y: float,
                               params: List[float], tolerance: float) -> List[List[Any]]:
        """Simple arc approximation without arc converter."""
        if len(params) < 7:
            return []

        end_x, end_y = params[5], params[6]

        # Very simple approximation - just draw a line
        # Real implementation would calculate arc points
        return [['L', end_x, end_y]]


def create_service_adapters(services):
    """
    Create boolean operation adapters from ConversionServices.

    Args:
        services: ConversionServices instance

    Returns:
        Tuple of (path_parser, path_serializer, curve_approximator)
    """
    # Extract path processing components from services
    path_parser_service = getattr(services, 'path_parser', None)
    arc_converter_service = getattr(services, 'arc_converter', None)
    drawingml_generator_service = getattr(services, 'drawingml_generator', None)

    # Create adapters
    path_parser = SVG2PPTXPathParser(path_parser_service) if path_parser_service else None
    path_serializer = SVG2PPTXPathSerializer(drawingml_generator_service)
    curve_approximator = SVG2PPTXCurveApproximator(arc_converter_service)

    return path_parser, path_serializer, curve_approximator