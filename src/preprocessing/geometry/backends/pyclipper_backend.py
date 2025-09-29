"""
PyClipper Backend for Path Boolean Operations

This backend provides polygon-based boolean operations using the PyClipper library.
It operates by converting SVG paths to polygons, performing operations, then converting back.

Features:
- Robust polygon-based operations
- Wide compatibility (pure Python)
- Configurable precision/smoothness trade-off
- Batch operation support

Limitations:
- Curves are approximated as polygon segments
- Lower fidelity than curve-faithful operations

Dependencies:
- pyclipper (pip install pyclipper)
"""

from __future__ import annotations
from typing import List, Callable, Any, Tuple
import logging
import math

from ..path_boolean_engine import PathBooleanEngine, PathSpec, FillRule, normalize_fill_rule

logger = logging.getLogger(__name__)

# Import pyclipper with graceful fallback
try:
    import pyclipper
    PYCLIPPER_AVAILABLE = True
except ImportError as e:
    logger.debug(f"PyClipper not available: {e}")
    pyclipper = None
    PYCLIPPER_AVAILABLE = False


class PyClipperBackend(PathBooleanEngine):
    """
    PyClipper implementation of PathBooleanEngine.

    This backend converts SVG paths to polygons, performs boolean operations
    using PyClipper, then converts results back to SVG paths.
    """

    def __init__(self,
                 to_polygons: Callable[[str, FillRule], List[List[Tuple[float, float]]]],
                 from_polygons: Callable[[List[List[Tuple[float, float]]]], str],
                 scale_factor: float = 1000.0):
        """
        Initialize PyClipper backend with adapter functions.

        Args:
            to_polygons: Function to convert SVG d-string to polygon list
                        Signature: (d_string: str, fill_rule: FillRule) -> List[List[Tuple[float, float]]]
            from_polygons: Function to convert polygons to SVG d-string
                          Signature: (polygons: List[List[Tuple[float, float]]]) -> str
            scale_factor: Integer scaling factor for PyClipper precision (default: 1000.0)

        Raises:
            RuntimeError: If pyclipper is not available
        """
        if not PYCLIPPER_AVAILABLE:
            raise RuntimeError(
                "PyClipper backend requires pyclipper. "
                "Install with: pip install pyclipper"
            )

        self._to_polygons = to_polygons
        self._from_polygons = from_polygons
        self._scale_factor = scale_factor

    def _scale_polygons(self, polygons: List[List[Tuple[float, float]]]) -> List[List[Tuple[int, int]]]:
        """Scale floating point polygons to integers for PyClipper."""
        scaled = []
        for polygon in polygons:
            scaled_polygon = []
            for x, y in polygon:
                scaled_x = int(x * self._scale_factor)
                scaled_y = int(y * self._scale_factor)
                scaled_polygon.append((scaled_x, scaled_y))
            scaled.append(scaled_polygon)
        return scaled

    def _unscale_polygons(self, polygons: List[List[Tuple[int, int]]]) -> List[List[Tuple[float, float]]]:
        """Convert integer polygons back to floating point coordinates."""
        unscaled = []
        for polygon in polygons:
            unscaled_polygon = []
            for x, y in polygon:
                unscaled_x = x / self._scale_factor
                unscaled_y = y / self._scale_factor
                unscaled_polygon.append((unscaled_x, unscaled_y))
            unscaled.append(unscaled_polygon)
        return unscaled

    def _get_fill_type(self, fill_rule: FillRule) -> int:
        """Convert SVG fill rule to PyClipper fill type."""
        if fill_rule == "evenodd":
            return pyclipper.PFT_EVENODD
        else:  # nonzero
            return pyclipper.PFT_NONZERO

    def union(self, paths: List[PathSpec]) -> str:
        """
        Compute union of multiple paths using PyClipper.

        Args:
            paths: List of (d_string, fill_rule) tuples

        Returns:
            SVG path d-string representing the union

        Raises:
            ValueError: If paths are malformed or operation fails
        """
        if not paths:
            return ""

        if len(paths) == 1:
            return paths[0][0]

        try:
            # Convert all paths to polygons
            all_polygons = []
            for d_string, fill_rule in paths:
                polygons = self._to_polygons(d_string, normalize_fill_rule(fill_rule))
                all_polygons.extend(polygons)

            if not all_polygons:
                return ""

            # Scale for PyClipper
            scaled_polygons = self._scale_polygons(all_polygons)

            # Set up PyClipper
            pc = pyclipper.Pyclipper()

            # Add all polygons as subjects
            for polygon in scaled_polygons:
                if len(polygon) >= 3:  # Valid polygon needs at least 3 points
                    pc.AddPath(polygon, pyclipper.PT_SUBJECT, True)

            # Execute union operation
            fill_type = self._get_fill_type(normalize_fill_rule(paths[0][1]))
            solution = pc.Execute(pyclipper.CT_UNION, fill_type, fill_type)

            # Convert back to SVG
            unscaled_solution = self._unscale_polygons(solution)
            return self._from_polygons(unscaled_solution)

        except Exception as e:
            raise ValueError(f"Union operation failed: {e}") from e

    def intersect(self, subject: PathSpec, clips: List[PathSpec]) -> str:
        """
        Compute intersection of subject with clip paths.

        Args:
            subject: (d_string, fill_rule) for the element being clipped
            clips: List of (d_string, fill_rule) for clip paths

        Returns:
            SVG path d-string representing the intersection
            Empty string if no intersection exists

        Raises:
            ValueError: If paths are malformed or operation fails
        """
        if not clips:
            return subject[0]

        try:
            # Convert subject to polygons
            subject_polygons = self._to_polygons(subject[0], normalize_fill_rule(subject[1]))
            if not subject_polygons:
                return ""

            # Start with subject polygons as current result
            current_result = subject_polygons

            # Intersect with each clip path sequentially
            for d_string, fill_rule in clips:
                clip_polygons = self._to_polygons(d_string, normalize_fill_rule(fill_rule))
                if not clip_polygons:
                    return ""  # No intersection with empty clip

                # Scale polygons
                scaled_subjects = self._scale_polygons(current_result)
                scaled_clips = self._scale_polygons(clip_polygons)

                # Set up PyClipper
                pc = pyclipper.Pyclipper()

                # Add current result as subjects
                for polygon in scaled_subjects:
                    if len(polygon) >= 3:
                        pc.AddPath(polygon, pyclipper.PT_SUBJECT, True)

                # Add clips
                for polygon in scaled_clips:
                    if len(polygon) >= 3:
                        pc.AddPath(polygon, pyclipper.PT_CLIP, True)

                # Execute intersection
                subject_fill = self._get_fill_type(normalize_fill_rule(subject[1]))
                clip_fill = self._get_fill_type(normalize_fill_rule(fill_rule))
                solution = pc.Execute(pyclipper.CT_INTERSECTION, subject_fill, clip_fill)

                # Update current result
                current_result = self._unscale_polygons(solution)
                if not current_result:
                    return ""  # No intersection remaining

            # Convert final result to SVG
            return self._from_polygons(current_result)

        except Exception as e:
            raise ValueError(f"Intersect operation failed: {e}") from e

    def difference(self, subject: PathSpec, clips: List[PathSpec]) -> str:
        """
        Compute difference of subject minus clip paths.

        Args:
            subject: (d_string, fill_rule) for the base path
            clips: List of (d_string, fill_rule) to subtract

        Returns:
            SVG path d-string representing subject - clips

        Raises:
            ValueError: If paths are malformed or operation fails
        """
        if not clips:
            return subject[0]

        try:
            # Convert subject to polygons
            subject_polygons = self._to_polygons(subject[0], normalize_fill_rule(subject[1]))
            if not subject_polygons:
                return ""

            # Start with subject polygons as current result
            current_result = subject_polygons

            # Subtract each clip path sequentially
            for d_string, fill_rule in clips:
                clip_polygons = self._to_polygons(d_string, normalize_fill_rule(fill_rule))
                if not clip_polygons:
                    continue  # Nothing to subtract

                # Scale polygons
                scaled_subjects = self._scale_polygons(current_result)
                scaled_clips = self._scale_polygons(clip_polygons)

                # Set up PyClipper
                pc = pyclipper.Pyclipper()

                # Add current result as subjects
                for polygon in scaled_subjects:
                    if len(polygon) >= 3:
                        pc.AddPath(polygon, pyclipper.PT_SUBJECT, True)

                # Add clips
                for polygon in scaled_clips:
                    if len(polygon) >= 3:
                        pc.AddPath(polygon, pyclipper.PT_CLIP, True)

                # Execute difference
                subject_fill = self._get_fill_type(normalize_fill_rule(subject[1]))
                clip_fill = self._get_fill_type(normalize_fill_rule(fill_rule))
                solution = pc.Execute(pyclipper.CT_DIFFERENCE, subject_fill, clip_fill)

                # Update current result
                current_result = self._unscale_polygons(solution)
                if not current_result:
                    return ""  # Nothing remaining after subtraction

            # Convert final result to SVG
            return self._from_polygons(current_result)

        except Exception as e:
            raise ValueError(f"Difference operation failed: {e}") from e


def create_pyclipper_backend_with_adapters(path_parser, path_serializer,
                                          curve_approximator,
                                          scale_factor: float = 1000.0) -> PyClipperBackend:
    """
    Create PyClipper backend with standard adapters.

    Args:
        path_parser: Object with parse_path_commands() method
        path_serializer: Object with serialize_path() method
        curve_approximator: Object with approximate_curves() method
        scale_factor: Precision scaling factor (default: 1000.0)

    Returns:
        Configured PyClipperBackend instance

    Raises:
        RuntimeError: If pyclipper not available
    """
    def to_polygons(d_string: str, fill_rule: FillRule) -> List[List[Tuple[float, float]]]:
        """Convert SVG d-string to list of polygons."""
        if not PYCLIPPER_AVAILABLE:
            raise RuntimeError("PyClipper not available")

        try:
            # Parse path commands
            commands = path_parser.parse_path_commands(d_string)

            # Approximate curves as line segments
            linear_commands = curve_approximator.approximate_curves(commands)

            # Convert to polygon points
            polygons = []
            current_polygon = []
            current_x, current_y = 0.0, 0.0

            for cmd in linear_commands:
                cmd_type = cmd[0].upper()

                if cmd_type == 'M':
                    # Start new polygon
                    if current_polygon:
                        polygons.append(current_polygon)
                        current_polygon = []
                    current_x, current_y = cmd[1], cmd[2]
                    current_polygon.append((current_x, current_y))

                elif cmd_type == 'L':
                    current_x, current_y = cmd[1], cmd[2]
                    current_polygon.append((current_x, current_y))

                elif cmd_type == 'Z':
                    # Close current polygon
                    if current_polygon and len(current_polygon) >= 3:
                        polygons.append(current_polygon)
                    current_polygon = []

            # Add final polygon if not closed
            if current_polygon and len(current_polygon) >= 3:
                polygons.append(current_polygon)

            return polygons

        except Exception as e:
            logger.warning(f"Polygon conversion failed: {e}, using empty result")
            return []

    def from_polygons(polygons: List[List[Tuple[float, float]]]) -> str:
        """Convert list of polygons to SVG d-string."""
        if not PYCLIPPER_AVAILABLE:
            raise RuntimeError("PyClipper not available")

        try:
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

        except Exception as e:
            logger.warning(f"SVG conversion failed: {e}, using empty string")
            return ""

    return PyClipperBackend(to_polygons, from_polygons, scale_factor)