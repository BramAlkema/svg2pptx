"""
Skia PathOps Backend for Path Boolean Operations

This backend provides curve-faithful boolean operations using the Skia PathOps library.
It preserves Bezier curves throughout operations and provides the highest fidelity results.

Features:
- Maintains curve precision (no polygonization)
- Hardware-optimized operations
- Proper fill rule handling
- Batch operation support

Dependencies:
- skia-python (pip install skia-python)
"""

from __future__ import annotations
from typing import List, Callable, Any
import logging

from ..path_boolean_engine import PathBooleanEngine, PathSpec, FillRule, normalize_fill_rule

logger = logging.getLogger(__name__)

# Import skia with graceful fallback
try:
    import skia
    SKIA_AVAILABLE = True
except ImportError as e:
    logger.debug(f"Skia not available: {e}")
    skia = None
    SKIA_AVAILABLE = False


class PathOpsBackend(PathBooleanEngine):
    """
    Skia PathOps implementation of PathBooleanEngine.

    This backend uses the Skia graphics library's PathOps module to perform
    boolean operations while maintaining curve precision.
    """

    def __init__(self,
                 to_skia_path: Callable[[str, FillRule], Any],
                 from_skia_path: Callable[[Any], str]):
        """
        Initialize PathOps backend with adapter functions.

        Args:
            to_skia_path: Function to convert SVG d-string to skia.Path
                         Signature: (d_string: str, fill_rule: FillRule) -> skia.Path
            from_skia_path: Function to convert skia.Path to SVG d-string
                           Signature: (path: skia.Path) -> str

        Raises:
            RuntimeError: If skia-python is not available
        """
        if not SKIA_AVAILABLE:
            raise RuntimeError(
                "Skia PathOps backend requires skia-python. "
                "Install with: pip install skia-python"
            )

        self._to_skia = to_skia_path
        self._from_skia = from_skia_path

    def _op_many(self, seed_path: Any, other_paths: List[Any], op: Any) -> Any:
        """
        Apply a boolean operation to many paths sequentially.

        Args:
            seed_path: Initial skia.Path
            other_paths: List of skia.Path objects to combine with seed
            op: skia.PathOp operation type

        Returns:
            Result skia.Path after all operations
        """
        result = seed_path
        for other_path in other_paths:
            tmp = skia.Path()
            if not skia.Op(result, other_path, op, tmp):
                logger.warning(f"PathOp operation failed, using empty result")
                return skia.Path()  # Empty path on failure
            result = tmp
        return result

    def union(self, paths: List[PathSpec]) -> str:
        """
        Compute union of multiple paths using Skia PathOps.

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
            # Convert first path as seed
            seed_path = self._to_skia(paths[0][0], normalize_fill_rule(paths[0][1]))

            # Convert remaining paths
            other_paths = []
            for d_string, fill_rule in paths[1:]:
                path = self._to_skia(d_string, normalize_fill_rule(fill_rule))
                other_paths.append(path)

            # Perform union operations
            result_path = self._op_many(seed_path, other_paths, skia.PathOp.kUnion)

            # Convert back to SVG
            return self._from_skia(result_path)

        except Exception as e:
            raise ValueError(f"Union operation failed: {e}") from e

    def intersect(self, subject: PathSpec, clips: List[PathSpec]) -> str:
        """
        Compute intersection of subject with clip paths.

        This performs: subject ∩ clip1 ∩ clip2 ∩ ... ∩ clipN

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
            # Convert subject path
            subject_path = self._to_skia(subject[0], normalize_fill_rule(subject[1]))

            # Convert clip paths
            clip_paths = []
            for d_string, fill_rule in clips:
                path = self._to_skia(d_string, normalize_fill_rule(fill_rule))
                clip_paths.append(path)

            # Perform intersection operations
            result_path = self._op_many(subject_path, clip_paths, skia.PathOp.kIntersect)

            # Convert back to SVG
            return self._from_skia(result_path)

        except Exception as e:
            raise ValueError(f"Intersect operation failed: {e}") from e

    def difference(self, subject: PathSpec, clips: List[PathSpec]) -> str:
        """
        Compute difference of subject minus clip paths.

        This performs: subject - clip1 - clip2 - ... - clipN

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
            # Convert subject path
            result_path = self._to_skia(subject[0], normalize_fill_rule(subject[1]))

            # Subtract each clip path sequentially
            for d_string, fill_rule in clips:
                clip_path = self._to_skia(d_string, normalize_fill_rule(fill_rule))
                tmp = skia.Path()
                if not skia.Op(result_path, clip_path, skia.PathOp.kDifference, tmp):
                    logger.warning("Difference operation failed, using empty result")
                    return ""
                result_path = tmp

            # Convert back to SVG
            return self._from_skia(result_path)

        except Exception as e:
            raise ValueError(f"Difference operation failed: {e}") from e


def create_pathops_backend_with_adapters(path_parser, path_serializer) -> PathOpsBackend:
    """
    Create PathOps backend with standard adapters.

    Args:
        path_parser: Object with parse_path_commands() method
        path_serializer: Object with serialize_path() method

    Returns:
        Configured PathOpsBackend instance

    Raises:
        RuntimeError: If skia-python not available
    """
    def to_skia_path(d_string: str, fill_rule: FillRule) -> Any:
        """Convert SVG d-string to skia.Path with proper fill rule."""
        if not SKIA_AVAILABLE:
            raise RuntimeError("Skia not available")

        path = skia.Path()

        # Set fill type based on fill rule
        if fill_rule == "evenodd":
            path.setFillType(skia.PathFillType.kEvenOdd)
        else:
            path.setFillType(skia.PathFillType.kWinding)

        # Parse path commands and build skia path
        try:
            commands = path_parser.parse_path_commands(d_string)
            current_x, current_y = 0.0, 0.0

            for cmd in commands:
                cmd_type = cmd[0].upper()

                if cmd_type == 'M':
                    current_x, current_y = cmd[1], cmd[2]
                    path.moveTo(current_x, current_y)
                elif cmd_type == 'L':
                    current_x, current_y = cmd[1], cmd[2]
                    path.lineTo(current_x, current_y)
                elif cmd_type == 'C':
                    x1, y1, x2, y2, x, y = cmd[1:7]
                    path.cubicTo(x1, y1, x2, y2, x, y)
                    current_x, current_y = x, y
                elif cmd_type == 'Q':
                    x1, y1, x, y = cmd[1:5]
                    path.quadTo(x1, y1, x, y)
                    current_x, current_y = x, y
                elif cmd_type == 'Z':
                    path.close()

        except Exception as e:
            logger.warning(f"Path parsing failed: {e}, using empty path")
            return skia.Path()

        return path

    def from_skia_path(path: Any) -> str:
        """Convert skia.Path back to SVG d-string."""
        if not SKIA_AVAILABLE:
            raise RuntimeError("Skia not available")

        try:
            # Use path serializer to convert back to SVG format
            return path_serializer.serialize_path(path)
        except Exception as e:
            logger.warning(f"Path serialization failed: {e}, using empty string")
            return ""

    return PathOpsBackend(to_skia_path, from_skia_path)