#!/usr/bin/env python3
"""
Industry-Standard Arc-to-Bezier Converter

This module implements the ArcConverter interface using the industry-standard
a2c (arc-to-cubic) algorithm from fontello/svgpath. It provides high-quality
conversion of SVG arc commands to cubic Bezier curves for PowerPoint compatibility.

Key Features:
- Industry-standard a2c algorithm implementation
- Proper handling of all SVG arc parameters
- Configurable quality settings for precision vs performance
- Comprehensive validation and error handling
"""

import logging
from math import sqrt
from typing import List, Tuple

from .a2c import ArcTooBigError, InvalidArcParametersError, arc_to_cubic_bezier
from .architecture import (
    ArcConversionError,
    BezierSegment,
    CoordinatePoint,
    PathCommand,
    PathCommandType,
)
from .interfaces import ArcConverter as BaseArcConverter

logger = logging.getLogger(__name__)


class ArcConverter(BaseArcConverter):
    """
    Industry-standard arc-to-cubic bezier converter.

    Uses the a2c algorithm from fontello/svgpath to convert SVG arc commands
    into cubic Bezier curves that are compatible with PowerPoint DrawingML.

    This implementation follows the SVG 1.1 specification for arc handling
    and provides configurable quality parameters for different use cases.

    Example Usage:
        ```python
        converter = ArcConverter()

        # Convert an arc command to bezier segments
        bezier_segments = converter.arc_to_bezier_segments(
            start_x=50, start_y=100,
            rx=50, ry=25, x_axis_rotation=30,
            large_arc_flag=0, sweep_flag=1,
            end_x=150, end_y=100
        )
        ```
    """

    def __init__(self, enable_logging: bool = True):
        """
        Initialize the arc converter with quality settings.

        Args:
            enable_logging: Whether to enable debug logging
        """
        super().__init__(enable_logging)

        # Quality parameters for arc conversion
        self.max_segment_angle = 90.0  # Maximum angle per segment in degrees
        self.error_tolerance = 0.01    # Maximum acceptable error in coordinate units

        # Statistics tracking
        self._arcs_converted = 0
        self._segments_generated = 0
        self._total_error = 0.0

        self.log_debug("ArcConverter initialized with industry-standard a2c algorithm")

    def _norm_flags(self, large_arc_flag: int, sweep_flag: int) -> tuple[int, int]:
        """Normalize arc flags to 0/1 values per SVG spec."""
        return (1 if large_arc_flag else 0, 1 if sweep_flag else 0)

    def _norm_rotation(self, deg: float) -> float:
        """Normalize rotation angle to [0,360) range."""
        if deg is None:
            return 0.0
        from math import fmod
        return fmod(fmod(deg, 360.0) + 360.0, 360.0)

    def _scale_radii_if_needed(self, rx: float, ry: float,
                               x0: float, y0: float, x1: float, y1: float,
                               phi_deg: float) -> tuple[float, float]:
        """Scale radii when the ellipse can't reach per SVG 1.1 §A.4.5."""
        if rx == 0 or ry == 0:
            return 0.0, 0.0

        rx, ry = abs(rx), abs(ry)
        phi = self._norm_rotation(phi_deg) * 3.14159265359 / 180.0  # Convert to radians

        # Transform to ellipse space (see SVG spec)
        from math import cos, sin, sqrt
        cos_phi, sin_phi = cos(phi), sin(phi)
        dx2 = (x0 - x1) / 2.0
        dy2 = (y0 - y1) / 2.0
        x1p =  cos_phi * dx2 + sin_phi * dy2
        y1p = -sin_phi * dx2 + cos_phi * dy2

        # Correct radii if needed
        lam = (x1p*x1p)/(rx*rx) + (y1p*y1p)/(ry*ry)
        if lam > 1.0:
            s = sqrt(lam)
            rx *= s
            ry *= s
        return rx, ry

    def _mid_error(self, seg: BezierSegment) -> float:
        """Calculate crude chord error upper bound per segment (straight-line vs cubic at t=0.5)."""
        # Straight-line midpoint
        mx = (seg.start_point.x + seg.end_point.x) * 0.5
        my = (seg.start_point.y + seg.end_point.y) * 0.5

        # Cubic midpoint using de Casteljau at t=0.5
        bx = (seg.start_point.x + 3*seg.control_point_1.x + 3*seg.control_point_2.x + seg.end_point.x) / 8.0
        by = (seg.start_point.y + 3*seg.control_point_1.y + 3*seg.control_point_2.y + seg.end_point.y) / 8.0

        # Distance between straight and curved midpoints
        dx, dy = (bx - mx), (by - my)
        return (dx*dx + dy*dy) ** 0.5

    def arc_to_bezier_segments(self, start_x: float, start_y: float, rx: float, ry: float,
                              x_axis_rotation: float, large_arc_flag: int, sweep_flag: int,
                              end_x: float, end_y: float) -> list[BezierSegment]:
        """
        Convert SVG arc to cubic bezier segments using a2c algorithm.

        Uses the industry-standard a2c algorithm from fontello/svgpath to generate
        accurate cubic Bezier curve approximations of SVG arcs.

        Args:
            start_x, start_y: Arc start point in SVG coordinates
            rx, ry: Arc radii
            x_axis_rotation: Rotation angle in degrees
            large_arc_flag: Large arc flag (0 or 1)
            sweep_flag: Sweep flag (0 or 1)
            end_x, end_y: Arc end point in SVG coordinates

        Returns:
            List of BezierSegment objects with SVG coordinates

        Raises:
            ArcConversionError: If arc parameters are invalid or conversion fails
        """
        try:
            # Spec-correct normalization
            large_arc_flag, sweep_flag = self._norm_flags(large_arc_flag, sweep_flag)
            x_axis_rotation = self._norm_rotation(x_axis_rotation)

            # Spec-correct scaling (no-op if not needed)
            rx, ry = self._scale_radii_if_needed(rx, ry, start_x, start_y, end_x, end_y, x_axis_rotation)

            self.log_debug(f"Converting arc (normalized): ({start_x}, {start_y}) → "
                          f"({end_x}, {end_y}), rx={rx}, ry={ry}, "
                          f"rotation={x_axis_rotation}°, large_arc={large_arc_flag}, sweep={sweep_flag}")

            # Handle degenerate cases per spec
            if rx == 0.0 or ry == 0.0:
                # Zero radius becomes straight line (spec: A with zero radius becomes L)
                return [BezierSegment(
                    start_point=CoordinatePoint(start_x, start_y, 'svg'),
                    control_point_1=CoordinatePoint(start_x + (end_x-start_x)/3.0, start_y + (end_y-start_y)/3.0, 'svg'),
                    control_point_2=CoordinatePoint(start_x + 2*(end_x-start_x)/3.0, start_y + 2*(end_y-start_y)/3.0, 'svg'),
                    end_point=CoordinatePoint(end_x, end_y, 'svg'),
                )]

            # If start == end, draw nothing (spec)
            if abs(start_x - end_x) < 1e-12 and abs(start_y - end_y) < 1e-12:
                return []

            # Handle other degenerate cases (legacy)
            if self._is_degenerate_arc(start_x, start_y, end_x, end_y, rx, ry):
                return self._handle_degenerate_arc(start_x, start_y, end_x, end_y)

            # Validate arc parameters (only for non-degenerate cases)
            if not self.validate_arc_parameters(rx, ry, start_x, start_y, end_x, end_y):
                raise ArcConversionError("Invalid arc parameters")

            # Use industry-standard a2c algorithm
            cubic_curves = arc_to_cubic_bezier(
                start_x=start_x,
                start_y=start_y,
                end_x=end_x,
                end_y=end_y,
                rx=rx,
                ry=ry,
                rotation=x_axis_rotation,
                large_arc_flag=bool(large_arc_flag),
                sweep_flag=bool(sweep_flag),
                max_segment_angle=self.max_segment_angle,
            )

            # Convert to BezierSegment objects
            bezier_segments = []
            for curve in cubic_curves:
                segment = BezierSegment(
                    start_point=CoordinatePoint(x=curve[0], y=curve[1], coordinate_system='svg'),
                    control_point_1=CoordinatePoint(x=curve[2], y=curve[3], coordinate_system='svg'),
                    control_point_2=CoordinatePoint(x=curve[4], y=curve[5], coordinate_system='svg'),
                    end_point=CoordinatePoint(x=curve[6], y=curve[7], coordinate_system='svg'),
                )
                bezier_segments.append(segment)

            # Calculate error metric for quality stats
            err = max((self._mid_error(s) for s in bezier_segments), default=0.0)
            self._total_error += err

            # Update statistics
            self._arcs_converted += 1
            self._segments_generated += len(bezier_segments)

            self.log_debug(f"Arc converted to {len(bezier_segments)} Bezier segments (max error: {err:.6f})")
            return bezier_segments

        except (ArcTooBigError, InvalidArcParametersError) as e:
            raise ArcConversionError(f"Arc conversion failed: {e}")
        except Exception as e:
            raise ArcConversionError(f"Unexpected error during arc conversion: {e}")

    def validate_arc_parameters(self, rx: float, ry: float, start_x: float, start_y: float,
                               end_x: float, end_y: float) -> bool:
        """
        Validate arc parameters for mathematical correctness.

        Checks that arc parameters are mathematically valid and within
        reasonable bounds for conversion to Bezier curves.

        Args:
            rx, ry: Arc radii (must be positive)
            start_x, start_y: Arc start point
            end_x, end_y: Arc end point

        Returns:
            True if parameters are valid, False otherwise
        """
        try:
            # Radii must be positive
            if rx <= 0 or ry <= 0:
                self.log_debug(f"Invalid radii: rx={rx}, ry={ry}")
                return False

            # Radii must be finite
            if not (abs(rx) < 1e6 and abs(ry) < 1e6):
                self.log_debug(f"Radii too large: rx={rx}, ry={ry}")
                return False

            # Coordinates must be finite
            coords = [start_x, start_y, end_x, end_y]
            if not all(abs(coord) < 1e6 for coord in coords):
                self.log_debug(f"Coordinates too large: {coords}")
                return False

            # Check for NaN or infinity
            all_values = [rx, ry, start_x, start_y, end_x, end_y]
            if not all(isinstance(val, (int, float)) and not (val != val or abs(val) == float('inf')) for val in all_values):
                self.log_debug("Arc parameters contain NaN or infinity")
                return False

            return True

        except Exception as e:
            self.log_error(f"Error validating arc parameters: {e}")
            return False

    def convert_arc_command(self, arc_command: PathCommand,
                          current_point: CoordinatePoint) -> list[PathCommand]:
        """
        Convert arc command to equivalent cubic Bezier commands.

        Args:
            arc_command: The arc command to convert
            current_point: Current path position

        Returns:
            List of cubic Bezier PathCommand objects

        Raises:
            ArcConversionError: If conversion fails
        """
        try:
            # Validate input
            if arc_command.command_type != PathCommandType.ARC:
                raise ArcConversionError("Command is not an arc command")

            if len(arc_command.parameters) < 7:
                raise ArcConversionError("Arc command missing required parameters (need 7: rx, ry, rotation, large_arc, sweep, x, y)")

            # Extract arc parameters from the parameters list
            # Arc parameters: [rx, ry, x_axis_rotation, large_arc_flag, sweep_flag, x, y]
            params = arc_command.parameters
            rx, ry = params[0], params[1]
            rotation = params[2] if len(params) > 2 else 0.0
            large_arc_flag = int(params[3]) if len(params) > 3 else 0
            sweep_flag = int(params[4]) if len(params) > 4 else 0
            end_x = params[5] if len(params) > 5 else 0.0
            end_y = params[6] if len(params) > 6 else 0.0

            # Convert relative A/a commands to absolute before a2c
            if arc_command.is_relative:
                end_x += current_point.x
                end_y += current_point.y

            # Convert to bezier segments
            bezier_segments = self.arc_to_bezier_segments(
                start_x=current_point.x, start_y=current_point.y,
                rx=rx, ry=ry, x_axis_rotation=rotation,
                large_arc_flag=large_arc_flag, sweep_flag=sweep_flag,
                end_x=end_x, end_y=end_y,
            )

            # Convert segments to PathCommand objects
            bezier_commands = []
            for segment in bezier_segments:
                # Create cubic curve command with control points and end point in parameters
                command = PathCommand(
                    command_type=PathCommandType.CUBIC_CURVE,
                    is_relative=arc_command.is_relative,
                    parameters=[
                        segment.control_point_1.x, segment.control_point_1.y,
                        segment.control_point_2.x, segment.control_point_2.y,
                        segment.end_point.x, segment.end_point.y,
                    ],
                    original_command='C',
                )
                bezier_commands.append(command)

            return bezier_commands

        except Exception as e:
            raise ArcConversionError(f"Failed to convert arc command: {e}")

    def set_quality_parameters(self, max_segment_angle: float = 90.0,
                             error_tolerance: float = 0.01):
        """
        Configure arc conversion quality parameters.

        Args:
            max_segment_angle: Maximum angle per arc segment in degrees (10-180)
            error_tolerance: Maximum acceptable error in coordinate units (0.001-1.0)
        """
        # Validate parameters
        if not (10.0 <= max_segment_angle <= 180.0):
            raise ValueError("max_segment_angle must be between 10 and 180 degrees")

        if not (0.001 <= error_tolerance <= 1.0):
            raise ValueError("error_tolerance must be between 0.001 and 1.0")

        self.max_segment_angle = max_segment_angle
        self.error_tolerance = error_tolerance

        self.log_debug(f"Arc quality configured: max_angle={max_segment_angle}°, "
                      f"tolerance={error_tolerance}")

    def is_arc_command(self, command: PathCommand) -> bool:
        """Check if a command is an arc command."""
        return command.command_type == PathCommandType.ARC

    def estimate_arc_complexity(self, start_x: float, start_y: float, rx: float, ry: float,
                              x_axis_rotation: float, large_arc_flag: int, sweep_flag: int,
                              end_x: float, end_y: float) -> dict:
        """
        Estimate the complexity of converting an arc.

        Args:
            Arc parameters (same as arc_to_bezier_segments)

        Returns:
            Dictionary with complexity metrics
        """
        try:
            # Calculate arc properties
            distance = sqrt((end_x - start_x)**2 + (end_y - start_y)**2)
            avg_radius = (rx + ry) / 2

            # Estimate number of segments needed
            # Based on arc length and max segment angle
            estimated_angle = 180.0  # Conservative estimate
            estimated_segments = max(1, int(estimated_angle / self.max_segment_angle))

            return {
                'estimated_segments': estimated_segments,
                'arc_distance': distance,
                'average_radius': avg_radius,
                'complexity_score': estimated_segments * (distance / 100),
                'is_degenerate': self._is_degenerate_arc(start_x, start_y, end_x, end_y, rx, ry),
            }

        except Exception as e:
            return {
                'estimated_segments': 1,
                'arc_distance': 0,
                'average_radius': 0,
                'complexity_score': 0,
                'is_degenerate': True,
                'error': str(e),
            }

    def get_conversion_statistics(self) -> dict:
        """Get arc conversion statistics."""
        avg_segments = (
            self._segments_generated / self._arcs_converted
            if self._arcs_converted > 0 else 0
        )

        return {
            'arcs_converted': self._arcs_converted,
            'segments_generated': self._segments_generated,
            'average_segments_per_arc': avg_segments,
            'total_approximation_error': self._total_error,
            'max_segment_angle': self.max_segment_angle,
            'error_tolerance': self.error_tolerance,
        }

    def reset_statistics(self):
        """Reset conversion statistics."""
        self._arcs_converted = 0
        self._segments_generated = 0
        self._total_error = 0.0
        self.log_debug("Arc conversion statistics reset")

    def _is_degenerate_arc(self, start_x: float, start_y: float, end_x: float, end_y: float,
                          rx: float, ry: float) -> bool:
        """Check if arc is degenerate (should be treated as line)."""
        # Same start and end points
        if abs(start_x - end_x) < 1e-6 and abs(start_y - end_y) < 1e-6:
            return True

        # Zero or very small radii
        if rx < 1e-6 or ry < 1e-6:
            return True

        # Distance between points is much larger than radii (should still be valid arc)
        distance = sqrt((end_x - start_x)**2 + (end_y - start_y)**2)
        min_radius = min(rx, ry)

        # Arc is degenerate if radii are much smaller than point distance
        # This is a heuristic - the a2c algorithm will handle most cases correctly
        if distance > (min_radius * 100):  # Very large ratio suggests degenerate case
            return True

        return False

    def _handle_degenerate_arc(self, start_x: float, start_y: float,
                             end_x: float, end_y: float) -> list[BezierSegment]:
        """Handle degenerate arc as a straight line."""
        self.log_debug("Handling degenerate arc as straight line")

        # Create a linear bezier segment (control points = 1/3 and 2/3 along line)
        dx = end_x - start_x
        dy = end_y - start_y

        control1 = CoordinatePoint(
            x=start_x + dx / 3,
            y=start_y + dy / 3,
            coordinate_system='svg',
        )
        control2 = CoordinatePoint(
            x=start_x + 2 * dx / 3,
            y=start_y + 2 * dy / 3,
            coordinate_system='svg',
        )

        segment = BezierSegment(
            start_point=CoordinatePoint(x=start_x, y=start_y, coordinate_system='svg'),
            control_point_1=control1,
            control_point_2=control2,
            end_point=CoordinatePoint(x=end_x, y=end_y, coordinate_system='svg'),
        )

        return [segment]