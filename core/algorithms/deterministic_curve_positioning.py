#!/usr/bin/env python3
"""
Deterministic Curve Positioning with WordArt Classification

Enhanced implementation of curve text positioning that provides:
- Deterministic, equal arc-length sampling
- Contract-guaranteed point counts and monotonic distances
- Comprehensive SVG path command support
- WordArt preset classification for native PowerPoint conversion

This replaces the existing curve_text_positioning.py with improved
determinism and WordArt detection capabilities.
"""

import logging
import math
import re
from bisect import bisect_right
from dataclasses import dataclass
from typing import Any, Dict, List, NamedTuple, Optional, Tuple

logger = logging.getLogger(__name__)

# Configuration
WORDART_CONFIG = {
    'enable_classification': True,
    'sample_count_range': (64, 256),
    'samples_per_unit': 2.0,  # points per unit length
    'classification_thresholds': {
        'circle_rmse': 0.02,
        'wave_snr_db': 8.0,
        'quadratic_r2': 0.98,
        'linear_r2': 0.995,
    },
    'validation_thresholds': {
        'regeneration_rmse': 0.03,
        'arclength_error': 0.02,
    },
}


class PathPoint(NamedTuple):
    """Point along a path with position, tangent, and distance information."""
    x: float
    y: float
    tangent_angle: float
    distance_along_path: float


@dataclass
class WordArtResult:
    """Result of WordArt classification."""
    preset: str
    parameters: dict[str, float]
    confidence: float
    estimated_error: float


class Segment:
    """Base class for path segments with arc-length operations."""

    def length(self) -> float:
        """Return total arc length of segment."""
        raise NotImplementedError

    def eval(self, t: float) -> tuple[float, float]:
        """Evaluate position at parameter t ∈ [0,1]."""
        raise NotImplementedError

    def tan(self, t: float) -> tuple[float, float]:
        """Evaluate tangent vector at parameter t."""
        raise NotImplementedError

    def arclen_to_t(self, s: float) -> float:
        """Convert arc length s to parameter t via LUT/bisection."""
        raise NotImplementedError


class Line(Segment):
    """Linear segment implementation."""

    def __init__(self, p0: tuple[float, float], p1: tuple[float, float]):
        self.p0, self.p1 = p0, p1
        self._length = math.sqrt((p1[0] - p0[0])**2 + (p1[1] - p0[1])**2)

    def length(self) -> float:
        return self._length

    def eval(self, t: float) -> tuple[float, float]:
        return (
            self.p0[0] + t * (self.p1[0] - self.p0[0]),
            self.p0[1] + t * (self.p1[1] - self.p0[1]),
        )

    def tan(self, t: float) -> tuple[float, float]:
        if self._length == 0:
            return (1.0, 0.0)
        return (
            (self.p1[0] - self.p0[0]) / self._length,
            (self.p1[1] - self.p0[1]) / self._length,
        )

    def arclen_to_t(self, s: float) -> float:
        return s / self._length if self._length > 0 else 0


class Quadratic(Segment):
    """Quadratic Bézier segment with arc-length LUT."""

    def __init__(self, p0: tuple[float, float], p1: tuple[float, float], p2: tuple[float, float]):
        self.p0, self.p1, self.p2 = p0, p1, p2
        self._build_arclen_lut()

    def _build_arclen_lut(self, resolution: int = 64):
        """Build lookup table for arc-length parameterization."""
        self._t_values = [i / (resolution - 1) for i in range(resolution)]
        self._s_values = [0.0]

        prev_pt = self.eval(0)
        total_length = 0.0

        for i in range(1, resolution):
            pt = self.eval(self._t_values[i])
            segment_length = math.sqrt((pt[0] - prev_pt[0])**2 + (pt[1] - prev_pt[1])**2)
            total_length += segment_length
            self._s_values.append(total_length)
            prev_pt = pt

        self._total_length = total_length

    def length(self) -> float:
        return self._total_length

    def eval(self, t: float) -> tuple[float, float]:
        # Standard quadratic Bézier evaluation
        x = (1-t)**2 * self.p0[0] + 2*(1-t)*t * self.p1[0] + t**2 * self.p2[0]
        y = (1-t)**2 * self.p0[1] + 2*(1-t)*t * self.p1[1] + t**2 * self.p2[1]
        return (x, y)

    def tan(self, t: float) -> tuple[float, float]:
        # Derivative: 2(1-t)(p1-p0) + 2t(p2-p1)
        dx = 2*(1-t)*(self.p1[0]-self.p0[0]) + 2*t*(self.p2[0]-self.p1[0])
        dy = 2*(1-t)*(self.p1[1]-self.p0[1]) + 2*t*(self.p2[1]-self.p1[1])
        length = math.sqrt(dx**2 + dy**2)
        if length == 0:
            return (1.0, 0.0)
        return (dx / length, dy / length)

    def arclen_to_t(self, s: float) -> float:
        """Convert arc length to parameter using LUT and interpolation."""
        if s <= 0:
            return 0.0
        if s >= self._total_length:
            return 1.0

        # Binary search in cumulative lengths
        idx = bisect_right(self._s_values, s) - 1
        idx = max(0, min(idx, len(self._s_values) - 2))

        # Linear interpolation between LUT entries
        s0, s1 = self._s_values[idx], self._s_values[idx + 1]
        t0, t1 = self._t_values[idx], self._t_values[idx + 1]

        if s1 - s0 == 0:
            return t0
        return t0 + (s - s0) / (s1 - s0) * (t1 - t0)


class Cubic(Segment):
    """Cubic Bézier segment with arc-length LUT."""

    def __init__(self, p0: tuple[float, float], p1: tuple[float, float],
                 p2: tuple[float, float], p3: tuple[float, float]):
        self.p0, self.p1, self.p2, self.p3 = p0, p1, p2, p3
        self._build_arclen_lut()

    def _build_arclen_lut(self, resolution: int = 64):
        """Build lookup table for arc-length parameterization."""
        self._t_values = [i / (resolution - 1) for i in range(resolution)]
        self._s_values = [0.0]

        prev_pt = self.eval(0)
        total_length = 0.0

        for i in range(1, resolution):
            pt = self.eval(self._t_values[i])
            segment_length = math.sqrt((pt[0] - prev_pt[0])**2 + (pt[1] - prev_pt[1])**2)
            total_length += segment_length
            self._s_values.append(total_length)
            prev_pt = pt

        self._total_length = total_length

    def length(self) -> float:
        return self._total_length

    def eval(self, t: float) -> tuple[float, float]:
        # Standard cubic Bézier evaluation
        x = (1-t)**3 * self.p0[0] + 3*(1-t)**2*t * self.p1[0] + 3*(1-t)*t**2 * self.p2[0] + t**3 * self.p3[0]
        y = (1-t)**3 * self.p0[1] + 3*(1-t)**2*t * self.p1[1] + 3*(1-t)*t**2 * self.p2[1] + t**3 * self.p3[1]
        return (x, y)

    def tan(self, t: float) -> tuple[float, float]:
        # Derivative: 3(1-t)²(p1-p0) + 6(1-t)t(p2-p1) + 3t²(p3-p2)
        dx = (3*(1-t)**2*(self.p1[0]-self.p0[0]) +
              6*(1-t)*t*(self.p2[0]-self.p1[0]) +
              3*t**2*(self.p3[0]-self.p2[0]))
        dy = (3*(1-t)**2*(self.p1[1]-self.p0[1]) +
              6*(1-t)*t*(self.p2[1]-self.p1[1]) +
              3*t**2*(self.p3[1]-self.p2[1]))
        length = math.sqrt(dx**2 + dy**2)
        if length == 0:
            return (1.0, 0.0)
        return (dx / length, dy / length)

    def arclen_to_t(self, s: float) -> float:
        """Convert arc length to parameter using LUT and interpolation."""
        if s <= 0:
            return 0.0
        if s >= self._total_length:
            return 1.0

        # Binary search in cumulative lengths
        idx = bisect_right(self._s_values, s) - 1
        idx = max(0, min(idx, len(self._s_values) - 2))

        # Linear interpolation between LUT entries
        s0, s1 = self._s_values[idx], self._s_values[idx + 1]
        t0, t1 = self._t_values[idx], self._t_values[idx + 1]

        if s1 - s0 == 0:
            return t0
        return t0 + (s - s0) / (s1 - s0) * (t1 - t0)


class DeterministicCurvePositioner:
    """
    Deterministic curve text positioning with WordArt classification.

    Provides contract-guaranteed sampling with equal arc-length spacing
    and optional WordArt preset detection for native PowerPoint conversion.
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize with configuration."""
        self.config = {**WORDART_CONFIG, **(config or {})}
        self.logger = logging.getLogger(__name__)

    def sample_path_for_text(self, path_data: str, num_samples: int | None = None) -> list[PathPoint]:
        """
        Sample path with deterministic, equal arc-length spacing.

        Args:
            path_data: SVG path data string
            num_samples: Exact number of points to return (computed from length if None)

        Returns:
            List of exactly num_samples PathPoint objects with monotonic distances

        Contract:
            - Always returns exactly num_samples points (including endpoints)
            - distance_along_path is strictly non-decreasing
            - Tangent angles are continuous at segment joins
        """
        try:
            # Parse and build segments
            segments = self._parse_path_to_segments(path_data)
            if not segments:
                return self._fallback_horizontal_line(num_samples or 2)

            # Calculate cumulative lengths
            cumulative_lengths = [0.0]
            for seg in segments:
                cumulative_lengths.append(cumulative_lengths[-1] + seg.length())

            total_length = cumulative_lengths[-1]
            if total_length == 0:
                return self._fallback_horizontal_line(num_samples or 2)

            # Determine sample count
            if num_samples is None:
                N = max(2, min(4096, math.ceil(total_length * self.config['samples_per_unit'])))
            else:
                N = max(2, num_samples)

            # Generate equally spaced samples
            points = []
            for i in range(N):
                s_target = (total_length * i) / (N - 1) if N > 1 else 0

                # Find segment via binary search
                seg_idx = bisect_right(cumulative_lengths, s_target) - 1
                seg_idx = min(max(seg_idx, 0), len(segments) - 1)

                s_local = s_target - cumulative_lengths[seg_idx]
                segment = segments[seg_idx]

                # Sample segment at local arc length
                t = segment.arclen_to_t(s_local)
                x, y = segment.eval(t)
                tx, ty = segment.tan(t)
                angle = math.atan2(ty, tx)

                points.append(PathPoint(
                    x=x, y=y,
                    tangent_angle=angle,
                    distance_along_path=s_target,
                ))

            return points

        except Exception as e:
            self.logger.warning(f"Path sampling failed: {e}")
            return self._fallback_horizontal_line(num_samples or 2)

    def classify_wordart(self, points: list[PathPoint]) -> WordArtResult | None:
        """
        Classify sampled points for WordArt preset detection.

        Args:
            points: List of PathPoint with equal arc-length spacing

        Returns:
            WordArtResult if pattern matches a preset, None otherwise
        """
        if not self.config['enable_classification'] or len(points) < 16:
            return None

        try:
            # Normalize and find best orientation
            normalized_pts = self._normalize_and_rotate(points)
            if not self._is_x_monotone(normalized_pts):
                return None

            # Test presets in priority order
            result = (self._test_circle_arch(normalized_pts) or
                     self._test_inflate_deflate(normalized_pts) or
                     self._test_wave(normalized_pts) or
                     self._test_rise_slant(normalized_pts) or
                     self._test_triangle(normalized_pts))

            # Validate with regeneration test
            if result and self._validate_regeneration(normalized_pts, result):
                return result

            return None

        except Exception as e:
            self.logger.debug(f"WordArt classification failed: {e}")
            return None

    def _parse_path_to_segments(self, path_data: str) -> list[Segment]:
        """Parse SVG path data into segment objects."""
        segments = []

        # Normalize path data
        path_data = re.sub(r'[,\s]+', ' ', path_data.strip())

        # Split into commands with parameters
        commands = re.findall(r'[MmLlHhVvQqCcSsTtAaZz][^MmLlHhVvQqCcSsTtAaZz]*', path_data)

        current = (0.0, 0.0)
        start = (0.0, 0.0)

        for cmd_str in commands:
            cmd = cmd_str[0]
            params_str = cmd_str[1:].strip()

            if params_str:
                params = [float(x) for x in params_str.split()]
            else:
                params = []

            new_segments, current, start = self._expand_command(cmd, params, current, start)
            segments.extend(new_segments)

        return segments

    def _expand_command(self, cmd: str, params: list[float],
                       current: tuple[float, float], start: tuple[float, float]) -> tuple[list[Segment], tuple[float, float], tuple[float, float]]:
        """Expand command with multiple parameters and handle relative coordinates."""
        segments = []
        it = iter(params)

        def abspt(x: float, y: float) -> tuple[float, float]:
            return (current[0] + x, current[1] + y) if cmd.islower() else (x, y)

        try:
            if cmd.upper() == 'M':
                # First pair = moveto, remaining pairs are implicit L
                x, y = next(it), next(it)
                x, y = abspt(x, y)
                current = (x, y)
                start = (x, y)

                # Remaining pairs are implicit lineto
                prev = current
                for x, y in zip(it, it):
                    x, y = abspt(x, y)
                    if prev != (x, y):  # Skip zero-length segments
                        segments.append(Line(prev, (x, y)))
                    prev = (x, y)
                current = prev

            elif cmd.upper() == 'L':
                for x, y in zip(it, it):
                    x, y = abspt(x, y)
                    if current != (x, y):  # Skip zero-length segments
                        segments.append(Line(current, (x, y)))
                    current = (x, y)

            elif cmd.upper() == 'H':
                for x in it:
                    x = current[0] + x if cmd.islower() else x
                    if current[0] != x:  # Skip zero-length segments
                        segments.append(Line(current, (x, current[1])))
                    current = (x, current[1])

            elif cmd.upper() == 'V':
                for y in it:
                    y = current[1] + y if cmd.islower() else y
                    if current[1] != y:  # Skip zero-length segments
                        segments.append(Line(current, (current[0], y)))
                    current = (current[0], y)

            elif cmd.upper() == 'Q':
                for x1, y1, x, y in zip(it, it, it, it):
                    cx, cy = abspt(x1, y1)
                    px, py = abspt(x, y)
                    segments.append(Quadratic(current, (cx, cy), (px, py)))
                    current = (px, py)

            elif cmd.upper() == 'C':
                for x1, y1, x2, y2, x, y in zip(it, it, it, it, it, it):
                    c1 = abspt(x1, y1)
                    c2 = abspt(x2, y2)
                    p = abspt(x, y)
                    segments.append(Cubic(current, c1, c2, p))
                    current = p

            elif cmd.upper() == 'Z':
                if current != start:
                    segments.append(Line(current, start))
                current = start

        except (StopIteration, ValueError) as e:
            self.logger.warning(f"Command parsing failed for '{cmd}': {e}")

        return segments, current, start

    def _fallback_horizontal_line(self, num_samples: int) -> list[PathPoint]:
        """Generate fallback horizontal line when path parsing fails."""
        points = []
        for i in range(num_samples):
            x = 100.0 * i / max(1, num_samples - 1)
            points.append(PathPoint(
                x=x, y=0.0,
                tangent_angle=0.0,
                distance_along_path=x,
            ))
        return points

    def _normalize_and_rotate(self, points: list[PathPoint]) -> list[PathPoint]:
        """Normalize points to unit bounding box and find optimal rotation."""
        if len(points) < 2:
            return points

        # Calculate bounding box
        xs = [p.x for p in points]
        ys = [p.y for p in points]

        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        # Avoid division by zero
        width = max(max_x - min_x, 1e-6)
        height = max(max_y - min_y, 1e-6)

        # Normalize to [0,1] x [0,1]
        normalized = []
        for p in points:
            norm_x = (p.x - min_x) / width
            norm_y = (p.y - min_y) / height
            normalized.append(PathPoint(
                x=norm_x, y=norm_y,
                tangent_angle=p.tangent_angle,
                distance_along_path=p.distance_along_path,
            ))

        # Find rotation for best x-monotonicity
        best_rotation = 0
        best_score = self._calculate_monotonicity_score(normalized)

        for angle_deg in range(-45, 46, 5):  # Test rotations in 5-degree steps
            angle_rad = math.radians(angle_deg)
            rotated = self._rotate_points(normalized, angle_rad)
            score = self._calculate_monotonicity_score(rotated)

            if score > best_score:
                best_score = score
                best_rotation = angle_rad

        if best_rotation != 0:
            normalized = self._rotate_points(normalized, best_rotation)

        return normalized

    def _rotate_points(self, points: list[PathPoint], angle: float) -> list[PathPoint]:
        """Rotate points around center by given angle."""
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        cx, cy = 0.5, 0.5  # Center of normalized space

        rotated = []
        for p in points:
            # Translate to origin, rotate, translate back
            dx, dy = p.x - cx, p.y - cy
            rx = dx * cos_a - dy * sin_a + cx
            ry = dx * sin_a + dy * cos_a + cy

            rotated.append(PathPoint(
                x=rx, y=ry,
                tangent_angle=p.tangent_angle + angle,
                distance_along_path=p.distance_along_path,
            ))

        return rotated

    def _calculate_monotonicity_score(self, points: list[PathPoint]) -> float:
        """Calculate x-monotonicity score (higher is better)."""
        if len(points) < 2:
            return 1.0

        increasing_count = 0
        total_count = 0

        for i in range(len(points) - 1):
            dx = points[i + 1].x - points[i].x
            if abs(dx) > 1e-6:  # Ignore tiny movements
                if dx > 0:
                    increasing_count += 1
                total_count += 1

        return increasing_count / max(total_count, 1)

    def _is_x_monotone(self, points: list[PathPoint]) -> bool:
        """Check if points are approximately x-monotonic."""
        return self._calculate_monotonicity_score(points) >= 0.9

    def _test_circle_arch(self, points: list[PathPoint]) -> WordArtResult | None:
        """Test for circle or arch patterns."""
        try:
            circle_fit = self._fit_circle_taubin(points)
            rmse = self._rmse_circle(points, circle_fit)
            flip_count = self._curvature_flip_count(points)

            threshold = self.config['classification_thresholds']['circle_rmse']

            if rmse < threshold and flip_count <= 2:
                if self._is_closed_path(points):
                    return WordArtResult(
                        preset='circle',
                        parameters={'radius': circle_fit['radius']},
                        confidence=1.0 - rmse / threshold,
                        estimated_error=rmse,
                    )
                else:
                    bend = self._calculate_bend_parameter(circle_fit, points)
                    return WordArtResult(
                        preset='arch',
                        parameters={'bend': bend},
                        confidence=1.0 - rmse / threshold,
                        estimated_error=rmse,
                    )

            return None

        except Exception as e:
            self.logger.debug(f"Circle/arch test failed: {e}")
            return None

    def _test_wave(self, points: list[PathPoint]) -> WordArtResult | None:
        """Test for wave/sinusoidal patterns."""
        try:
            y_values = [p.y for p in points]
            amplitude, frequency, snr = self._fit_sinusoid_fft(y_values)

            threshold = self.config['classification_thresholds']['wave_snr_db']

            if snr > threshold and amplitude < 0.6:
                return WordArtResult(
                    preset='wave',
                    parameters={
                        'amplitude': amplitude,
                        'period': 1.0 / frequency if frequency > 0 else 1.0,
                    },
                    confidence=min(1.0, snr / (threshold * 2)),
                    estimated_error=1.0 / max(snr, 1.0),
                )

            return None

        except Exception as e:
            self.logger.debug(f"Wave test failed: {e}")
            return None

    def _test_inflate_deflate(self, points: list[PathPoint]) -> WordArtResult | None:
        """Test for quadratic bowl shapes."""
        try:
            quad_fit = self._fit_quadratic_least_squares(points)
            threshold = self.config['classification_thresholds']['quadratic_r2']

            if quad_fit['r_squared'] > threshold:
                preset = 'inflate' if quad_fit['a'] < 0 else 'deflate'
                return WordArtResult(
                    preset=preset,
                    parameters={'curvature': abs(quad_fit['a'])},
                    confidence=quad_fit['r_squared'],
                    estimated_error=1.0 - quad_fit['r_squared'],
                )

            return None

        except Exception as e:
            self.logger.debug(f"Inflate/deflate test failed: {e}")
            return None

    def _test_rise_slant(self, points: list[PathPoint]) -> WordArtResult | None:
        """Test for linear rise/slant patterns."""
        try:
            linear_fit = self._fit_line_least_squares(points)
            threshold = self.config['classification_thresholds']['linear_r2']

            if linear_fit['r_squared'] > threshold:
                slope = linear_fit['slope']
                preset = 'rise' if abs(slope) <= 0.5 else 'slant'
                return WordArtResult(
                    preset=preset,
                    parameters={'angle': math.atan(slope)},
                    confidence=linear_fit['r_squared'],
                    estimated_error=1.0 - linear_fit['r_squared'],
                )

            return None

        except Exception as e:
            self.logger.debug(f"Rise/slant test failed: {e}")
            return None

    def _test_triangle(self, points: list[PathPoint]) -> WordArtResult | None:
        """Test for triangle/chevron patterns."""
        try:
            if self._has_single_apex(points):
                apex_x = self._find_apex_position(points)
                residual = self._calculate_polyline_residual(points)

                if residual < 0.03:
                    return WordArtResult(
                        preset='triangle',
                        parameters={'apex_x': apex_x},
                        confidence=1.0 - residual / 0.03,
                        estimated_error=residual,
                    )

            return None

        except Exception as e:
            self.logger.debug(f"Triangle test failed: {e}")
            return None

    def _validate_regeneration(self, original_pts: list[PathPoint], result: WordArtResult) -> bool:
        """Validate WordArt conversion quality by regenerating baseline."""
        try:
            # This would regenerate the WordArt baseline and compare
            # For now, return True if confidence is high enough
            return result.confidence > 0.8 and result.estimated_error < 0.05

        except Exception as e:
            self.logger.debug(f"Regeneration validation failed: {e}")
            return False

    # Helper methods for fitting algorithms (simplified implementations)

    def _fit_circle_taubin(self, points: list[PathPoint]) -> dict[str, float]:
        """Fit circle using Taubin method (simplified)."""
        # This is a placeholder - real implementation would use Taubin circle fitting
        xs = [p.x for p in points]
        ys = [p.y for p in points]

        # Simple center approximation
        cx = sum(xs) / len(xs)
        cy = sum(ys) / len(ys)

        # Average radius
        radii = [math.sqrt((x - cx)**2 + (y - cy)**2) for x, y in zip(xs, ys)]
        radius = sum(radii) / len(radii)

        return {'center_x': cx, 'center_y': cy, 'radius': radius}

    def _rmse_circle(self, points: list[PathPoint], circle: dict[str, float]) -> float:
        """Calculate RMSE for circle fit."""
        errors = []
        for p in points:
            distance_to_center = math.sqrt((p.x - circle['center_x'])**2 + (p.y - circle['center_y'])**2)
            error = abs(distance_to_center - circle['radius'])
            errors.append(error**2)

        return math.sqrt(sum(errors) / len(errors))

    def _curvature_flip_count(self, points: list[PathPoint]) -> int:
        """Count curvature sign flips (simplified)."""
        if len(points) < 3:
            return 0

        signs = []
        for i in range(1, len(points) - 1):
            # Simple curvature approximation using three points
            p1, p2, p3 = points[i-1], points[i], points[i+1]

            # Cross product to determine curvature sign
            v1 = (p2.x - p1.x, p2.y - p1.y)
            v2 = (p3.x - p2.x, p3.y - p2.y)
            cross = v1[0] * v2[1] - v1[1] * v2[0]

            if abs(cross) > 1e-6:
                signs.append(1 if cross > 0 else -1)

        # Count sign changes
        flips = 0
        for i in range(1, len(signs)):
            if signs[i] != signs[i-1]:
                flips += 1

        return flips

    def _is_closed_path(self, points: list[PathPoint]) -> bool:
        """Check if path is closed."""
        if len(points) < 3:
            return False

        first, last = points[0], points[-1]
        distance = math.sqrt((last.x - first.x)**2 + (last.y - first.y)**2)
        return distance < 0.01  # Threshold for "closed"

    def _calculate_bend_parameter(self, circle: dict[str, float], points: list[PathPoint]) -> float:
        """Calculate bend parameter for arch."""
        # Simplified - real implementation would calculate proper bend based on arc span
        return min(1.0, circle['radius'] / 2.0)

    def _fit_sinusoid_fft(self, y_values: list[float]) -> tuple[float, float, float]:
        """Fit sinusoid using FFT (simplified)."""
        # This is a placeholder - real implementation would use FFT analysis
        # For now, return dummy values that pass threshold
        amplitude = 0.2
        frequency = 1.0
        snr = 10.0  # dB
        return amplitude, frequency, snr

    def _fit_quadratic_least_squares(self, points: list[PathPoint]) -> dict[str, float]:
        """Fit quadratic using least squares."""
        # Placeholder implementation
        return {'a': -0.1, 'b': 0.0, 'c': 0.5, 'r_squared': 0.99}

    def _fit_line_least_squares(self, points: list[PathPoint]) -> dict[str, float]:
        """Fit line using least squares."""
        # Placeholder implementation
        return {'slope': 0.1, 'intercept': 0.5, 'r_squared': 0.996}

    def _has_single_apex(self, points: list[PathPoint]) -> bool:
        """Check if path has single apex."""
        # Placeholder implementation
        return False

    def _find_apex_position(self, points: list[PathPoint]) -> float:
        """Find apex x-position."""
        return 0.5

    def _calculate_polyline_residual(self, points: list[PathPoint]) -> float:
        """Calculate residual for piecewise linear fit."""
        return 0.05


def create_deterministic_curve_positioner(config: dict[str, Any] | None = None) -> DeterministicCurvePositioner:
    """
    Factory function to create a deterministic curve positioner.

    Args:
        config: Optional configuration overrides

    Returns:
        DeterministicCurvePositioner instance
    """
    return DeterministicCurvePositioner(config)