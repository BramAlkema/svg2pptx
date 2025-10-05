#!/usr/bin/env python3
"""
Animation Interpolation and Easing Engine for SVG2PPTX

This module provides value interpolation, easing functions, and keyframe
calculation for animations. Following ADR-006 animation system architecture.

Key Features:
- Numeric and color value interpolation
- Bezier easing curve evaluation
- Transform matrix interpolation
- Path data interpolation for motion animations
- Keyframe generation with timing functions
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .core import TransformType


@dataclass
class InterpolationResult:
    """Result of value interpolation."""
    value: str
    progress: float
    easing_applied: bool = False


class ColorInterpolator:
    """Handles color value interpolation between keyframes."""

    @staticmethod
    def interpolate_color(from_color: str, to_color: str, progress: float, services=None) -> str:
        """
        Interpolate between two color values.

        Args:
            from_color: Starting color (hex, rgb, or named)
            to_color: Ending color (hex, rgb, or named)
            progress: Interpolation progress (0.0 to 1.0)
            services: Optional ConversionServices for color parsing

        Returns:
            Interpolated color as hex string
        """
        try:
            # Convert colors to RGB tuples
            from_rgb = ColorInterpolator._parse_color(from_color, services)
            to_rgb = ColorInterpolator._parse_color(to_color, services)

            if not from_rgb or not to_rgb:
                # Fallback to discrete interpolation
                return from_color if progress < 0.5 else to_color

            # Linear interpolation in RGB space
            r = int(from_rgb[0] + (to_rgb[0] - from_rgb[0]) * progress)
            g = int(from_rgb[1] + (to_rgb[1] - from_rgb[1]) * progress)
            b = int(from_rgb[2] + (to_rgb[2] - from_rgb[2]) * progress)

            # Clamp values and convert to hex
            r = max(0, min(255, r))
            g = max(0, min(255, g))
            b = max(0, min(255, b))

            return f"#{r:02x}{g:02x}{b:02x}"

        except Exception:
            # Fallback to discrete interpolation on any error
            return from_color if progress < 0.5 else to_color

    @staticmethod
    def _parse_color(color_str: str, services=None) -> tuple[int, int, int] | None:
        """Parse color string to RGB tuple."""
        # Use ConversionServices for color parsing when available
        if not color_str:
            return None

        try:
            if services and hasattr(services, 'color_parser'):
                # Use ConversionServices color parser
                color = services.color_parser(color_str)
            else:
                # Fallback to direct Color import for backward compatibility
                from ..color import Color
                color = Color(color_str)

            return color.rgb()
        except (ValueError, TypeError):
            # Fallback for any parsing errors
            return None


class NumericInterpolator:
    """Handles numeric value interpolation with unit awareness."""

    @staticmethod
    def interpolate_numeric(from_value: str, to_value: str, progress: float) -> str:
        """
        Interpolate between numeric values with units.

        Args:
            from_value: Starting value (e.g., "10px", "50%", "1.5")
            to_value: Ending value with same units
            progress: Interpolation progress (0.0 to 1.0)

        Returns:
            Interpolated value with appropriate units
        """
        try:
            # Parse values and units
            from_num, from_unit = NumericInterpolator._parse_numeric(from_value)
            to_num, to_unit = NumericInterpolator._parse_numeric(to_value)

            if from_num is None or to_num is None:
                # Fallback to discrete interpolation
                return from_value if progress < 0.5 else to_value

            # Units must match for interpolation
            if from_unit != to_unit:
                return from_value if progress < 0.5 else to_value

            # Linear interpolation
            result_num = from_num + (to_num - from_num) * progress

            # Format result with appropriate precision
            if from_unit:
                if '.' in from_value or '.' in to_value:
                    return f"{result_num:.3f}{from_unit}".rstrip('0').rstrip('.')
                else:
                    return f"{result_num:.0f}{from_unit}"
            else:
                if '.' in from_value or '.' in to_value:
                    return f"{result_num:.3f}".rstrip('0').rstrip('.')
                else:
                    return f"{result_num:.0f}"

        except Exception:
            # Fallback to discrete interpolation
            return from_value if progress < 0.5 else to_value

    @staticmethod
    def _parse_numeric(value_str: str) -> tuple[float | None, str | None]:
        """Parse numeric value with optional unit."""
        if not value_str:
            return None, None

        value_str = value_str.strip()

        # Extract numeric part and unit
        match = re.match(r'^([-+]?(?:\d+\.?\d*|\.\d+))(.*)$', value_str)
        if match:
            try:
                number = float(match.group(1))
                unit = match.group(2).strip()
                return number, unit if unit else None
            except ValueError:
                pass

        return None, None


class TransformInterpolator:
    """Handles transform value interpolation."""

    @staticmethod
    def interpolate_transform(from_transform: str, to_transform: str, progress: float, transform_type: TransformType) -> str:
        """
        Interpolate between transform values.

        Args:
            from_transform: Starting transform value
            to_transform: Ending transform value
            progress: Interpolation progress (0.0 to 1.0)
            transform_type: Type of transform

        Returns:
            Interpolated transform value
        """
        try:
            from_values = TransformInterpolator._parse_transform_values(from_transform)
            to_values = TransformInterpolator._parse_transform_values(to_transform)

            if not from_values or not to_values or len(from_values) != len(to_values):
                # Fallback to discrete interpolation
                return from_transform if progress < 0.5 else to_transform

            # Interpolate each value
            result_values = []
            for from_val, to_val in zip(from_values, to_values):
                interpolated = from_val + (to_val - from_val) * progress
                result_values.append(interpolated)

            # Format according to transform type
            return TransformInterpolator._format_transform_values(result_values, transform_type)

        except Exception:
            # Fallback to discrete interpolation
            return from_transform if progress < 0.5 else to_transform

    @staticmethod
    def _parse_transform_values(transform_str: str) -> list[float] | None:
        """Parse transform string to numeric values."""
        if not transform_str:
            return None

        # Extract numeric values using regex
        numbers = re.findall(r'[-+]?(?:\d+\.?\d*|\.\d+)', transform_str)
        try:
            return [float(n) for n in numbers]
        except ValueError:
            return None

    @staticmethod
    def _format_transform_values(values: list[float], transform_type: TransformType) -> str:
        """Format numeric values back to transform string."""
        if transform_type == TransformType.TRANSLATE:
            if len(values) == 1:
                return f"translate({values[0]:.3f})"
            elif len(values) == 2:
                return f"translate({values[0]:.3f}, {values[1]:.3f})"
        elif transform_type == TransformType.SCALE:
            if len(values) == 1:
                return f"scale({values[0]:.3f})"
            elif len(values) == 2:
                return f"scale({values[0]:.3f}, {values[1]:.3f})"
        elif transform_type == TransformType.ROTATE:
            if len(values) == 1:
                return f"rotate({values[0]:.3f})"
            elif len(values) == 3:
                return f"rotate({values[0]:.3f}, {values[1]:.3f}, {values[2]:.3f})"
        elif transform_type == TransformType.SKEWX:
            if len(values) == 1:
                return f"skewX({values[0]:.3f})"
        elif transform_type == TransformType.SKEWY:
            if len(values) == 1:
                return f"skewY({values[0]:.3f})"
        elif transform_type == TransformType.MATRIX:
            if len(values) == 6:
                formatted = [f"{v:.6f}" for v in values]
                return f"matrix({', '.join(formatted)})"

        # Fallback: join with spaces
        return ' '.join(f"{v:.3f}" for v in values)


class BezierEasing:
    """Bezier curve easing evaluation for keySplines."""

    @staticmethod
    def evaluate_bezier(t: float, control_points: list[float]) -> float:
        """
        Evaluate cubic Bezier curve at parameter t.

        Args:
            t: Parameter value (0.0 to 1.0)
            control_points: [x1, y1, x2, y2] control points

        Returns:
            Y value of Bezier curve at parameter t
        """
        if len(control_points) != 4:
            return t  # Linear fallback

        x1, y1, x2, y2 = control_points

        # Clamp input
        t = max(0.0, min(1.0, t))

        # Handle edge cases
        if t == 0.0:
            return 0.0
        if t == 1.0:
            return 1.0

        # Find parameter value that gives target x value
        # Use binary search for efficiency
        target_x = t
        param_t = BezierEasing._solve_bezier_x(target_x, x1, x2)

        # Calculate y value at found parameter
        return BezierEasing._bezier_y(param_t, y1, y2)

    @staticmethod
    def _solve_bezier_x(target_x: float, x1: float, x2: float, precision: float = 1e-6) -> float:
        """Solve for parameter t that gives target x coordinate."""
        # Binary search for parameter value
        t_min, t_max = 0.0, 1.0

        for _ in range(50):  # Maximum iterations
            t = (t_min + t_max) / 2.0
            x = BezierEasing._bezier_x(t, x1, x2)

            if abs(x - target_x) < precision:
                return t

            if x < target_x:
                t_min = t
            else:
                t_max = t

        return (t_min + t_max) / 2.0

    @staticmethod
    def _bezier_x(t: float, x1: float, x2: float) -> float:
        """Calculate x coordinate of cubic Bezier curve."""
        # Cubic Bezier: B(t) = (1-t)³P₀ + 3(1-t)²tP₁ + 3(1-t)t²P₂ + t³P₃
        # For unit curve: P₀=(0,0), P₃=(1,1), so:
        # x(t) = 3(1-t)²t*x1 + 3(1-t)t²*x2 + t³
        return 3 * (1 - t) * (1 - t) * t * x1 + 3 * (1 - t) * t * t * x2 + t * t * t

    @staticmethod
    def _bezier_y(t: float, y1: float, y2: float) -> float:
        """Calculate y coordinate of cubic Bezier curve."""
        # Same formula as x, but with y control points
        return 3 * (1 - t) * (1 - t) * t * y1 + 3 * (1 - t) * t * t * y2 + t * t * t


class InterpolationEngine:
    """Main interpolation engine coordinating all interpolation types."""

    def __init__(self, services=None):
        """Initialize interpolation engine with optional services."""
        self.services = services
        self.color_interpolator = ColorInterpolator()
        self.numeric_interpolator = NumericInterpolator()
        self.transform_interpolator = TransformInterpolator()

    def interpolate_value(
        self,
        from_value: str,
        to_value: str,
        progress: float,
        attribute_name: str,
        transform_type: TransformType | None = None,
        easing: list[float] | None = None,
    ) -> InterpolationResult:
        """
        Interpolate between two values with appropriate strategy.

        Args:
            from_value: Starting value
            to_value: Ending value
            progress: Base progress (0.0 to 1.0)
            attribute_name: Name of attribute being animated
            transform_type: Transform type if applicable
            easing: Optional Bezier control points for easing

        Returns:
            InterpolationResult with interpolated value
        """
        # Apply easing if provided
        easing_applied = False
        if easing and len(easing) == 4:
            progress = BezierEasing.evaluate_bezier(progress, easing)
            easing_applied = True

        # Determine interpolation strategy based on attribute
        if self._is_color_attribute(attribute_name):
            value = self.color_interpolator.interpolate_color(from_value, to_value, progress, self.services)
        elif transform_type:
            value = self.transform_interpolator.interpolate_transform(
                from_value, to_value, progress, transform_type,
            )
        elif self._is_numeric_attribute(attribute_name):
            value = self.numeric_interpolator.interpolate_numeric(from_value, to_value, progress)
        else:
            # Discrete interpolation for unknown types
            value = from_value if progress < 0.5 else to_value

        return InterpolationResult(
            value=value,
            progress=progress,
            easing_applied=easing_applied,
        )

    def interpolate_keyframes(
        self,
        values: list[str],
        key_times: list[float] | None,
        key_splines: list[list[float]] | None,
        progress: float,
        attribute_name: str,
        transform_type: TransformType | None = None,
    ) -> InterpolationResult:
        """
        Interpolate through multiple keyframes.

        Args:
            values: List of keyframe values
            key_times: Optional explicit key times
            key_splines: Optional easing curves
            progress: Overall progress (0.0 to 1.0)
            attribute_name: Name of attribute being animated
            transform_type: Transform type if applicable

        Returns:
            InterpolationResult with interpolated value
        """
        if not values:
            return InterpolationResult(value="", progress=progress)

        if len(values) == 1:
            return InterpolationResult(value=values[0], progress=progress)

        # Use explicit key times or generate uniform distribution
        if key_times and len(key_times) == len(values):
            times = key_times
        else:
            times = [i / (len(values) - 1) for i in range(len(values))]

        # Find the keyframe segment
        for i in range(len(times) - 1):
            if times[i] <= progress <= times[i + 1]:
                # Calculate local progress within this segment
                segment_start = times[i]
                segment_end = times[i + 1]
                segment_duration = segment_end - segment_start

                if segment_duration == 0:
                    local_progress = 0.0
                else:
                    local_progress = (progress - segment_start) / segment_duration

                # Get easing for this segment
                easing = None
                if key_splines and i < len(key_splines):
                    easing = key_splines[i]

                # Interpolate between keyframes
                return self.interpolate_value(
                    values[i], values[i + 1], local_progress,
                    attribute_name, transform_type, easing,
                )

        # Handle edge cases
        if progress <= times[0]:
            return InterpolationResult(value=values[0], progress=progress)
        else:
            return InterpolationResult(value=values[-1], progress=progress)

    def _is_color_attribute(self, attribute_name: str) -> bool:
        """Check if attribute represents a color value."""
        color_attributes = {
            'fill', 'stroke', 'stop-color', 'flood-color',
            'lighting-color', 'color', 'background-color',
        }
        return attribute_name.lower() in color_attributes

    def _is_numeric_attribute(self, attribute_name: str) -> bool:
        """Check if attribute represents a numeric value."""
        numeric_attributes = {
            'opacity', 'fill-opacity', 'stroke-opacity',
            'stroke-width', 'r', 'cx', 'cy', 'x', 'y',
            'width', 'height', 'rx', 'ry', 'x1', 'y1',
            'x2', 'y2', 'dx', 'dy', 'offset', 'font-size',
        }
        return attribute_name.lower() in numeric_attributes

    def get_supported_attributes(self) -> dict[str, str]:
        """Get list of supported animation attributes and their types."""
        return {
            # Color attributes
            'fill': 'color',
            'stroke': 'color',
            'stop-color': 'color',
            'flood-color': 'color',
            'lighting-color': 'color',

            # Numeric attributes
            'opacity': 'numeric',
            'fill-opacity': 'numeric',
            'stroke-opacity': 'numeric',
            'stroke-width': 'numeric',
            'r': 'numeric',
            'cx': 'numeric',
            'cy': 'numeric',
            'x': 'numeric',
            'y': 'numeric',
            'width': 'numeric',
            'height': 'numeric',
            'font-size': 'numeric',

            # Transform attributes (handled specially)
            'transform': 'transform',
        }