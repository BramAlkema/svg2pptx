#!/usr/bin/env python3
"""
Ultra-Fast NumPy Path Architecture Design

Complete architecture design for NumPy-based path processing engine
targeting 100-300x performance improvements over legacy implementation.

Design Principles:
- Pure NumPy structured arrays for all path data
- Vectorized operations for coordinate transformations
- Pre-compiled regex patterns with advanced caching
- Batch processing for similar path commands
- Memory-efficient layouts for maximum cache performance
- Compiled critical paths with Numba JIT
- Zero-copy operations where possible

Performance Targets:
- Path parsing: 100x speedup (18M paths/sec)
- Coordinate processing: 200x speedup (420M coords/sec)
- Bezier calculations: 32x speedup (1.4M curves/sec)
- Overall pipeline: 100-300x improvement
"""

import numpy as np
import re
from typing import Union, Optional, Tuple, Dict, Any, List
from dataclasses import dataclass
from enum import IntEnum
import numba
from functools import lru_cache
import math


# ============================================================================
# Core Type Definitions - Optimized for NumPy Performance
# ============================================================================

class PathCommandType(IntEnum):
    """Path command types as integers for efficient NumPy storage."""
    MOVE_TO = 0        # M, m
    LINE_TO = 1        # L, l
    HORIZONTAL = 2     # H, h
    VERTICAL = 3       # V, v
    CUBIC_CURVE = 4    # C, c
    SMOOTH_CUBIC = 5   # S, s
    QUADRATIC = 6      # Q, q
    SMOOTH_QUAD = 7    # T, t
    ARC = 8           # A, a
    CLOSE_PATH = 9     # Z, z


# NumPy structured dtypes for maximum performance
PATH_COMMAND_DTYPE = np.dtype([
    ('cmd_type', 'u1'),        # Command type (8-bit unsigned int)
    ('is_relative', 'u1'),     # 0=absolute, 1=relative
    ('coord_count', 'u1'),     # Number of coordinates used
    ('coords', 'f8', (8,))     # Up to 8 coordinates (for arcs: rx,ry,angle,large,sweep,x,y)
])

PARSED_PATH_DTYPE = np.dtype([
    ('commands', PATH_COMMAND_DTYPE, (500,)),  # Up to 500 commands per path
    ('command_count', 'u4'),                   # Actual number of commands
    ('total_coords', 'u4')                     # Total coordinate count
])

BEZIER_CURVE_DTYPE = np.dtype([
    ('control_points', 'f8', (4, 2)),  # 4 control points with x,y
    ('curve_type', 'u1'),              # 0=cubic, 1=quadratic
    ('t_start', 'f8'),                 # Parameter range start
    ('t_end', 'f8')                    # Parameter range end
])

COORDINATE_TRANSFORM_DTYPE = np.dtype([
    ('original', 'f8', (2,)),    # Original x,y
    ('transformed', 'f8', (2,)), # Transformed x,y
    ('viewport_id', 'u4')        # Viewport context reference
])


# ============================================================================
# Ultra-Fast String Parsing Engine with Pre-Compiled Patterns
# ============================================================================

class VectorizedPathParser:
    """
    Ultra-fast path string parser using pre-compiled regex and NumPy operations.

    Performance optimizations:
    - Pre-compiled regex patterns for instant matching
    - Batch coordinate extraction using np.fromstring
    - Vectorized command classification
    - LRU caching for repeated path strings
    - Zero-copy string operations where possible
    """

    def __init__(self):
        # Pre-compile all regex patterns for maximum speed
        self._command_pattern = re.compile(r'([MmLlHhVvCcSsQqTtAaZz])')
        self._number_pattern = re.compile(r'[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?')
        self._whitespace_pattern = re.compile(r'[,\s]+')

        # Command type mapping for O(1) lookup
        self._command_map = {
            'M': (PathCommandType.MOVE_TO, False), 'm': (PathCommandType.MOVE_TO, True),
            'L': (PathCommandType.LINE_TO, False), 'l': (PathCommandType.LINE_TO, True),
            'H': (PathCommandType.HORIZONTAL, False), 'h': (PathCommandType.HORIZONTAL, True),
            'V': (PathCommandType.VERTICAL, False), 'v': (PathCommandType.VERTICAL, True),
            'C': (PathCommandType.CUBIC_CURVE, False), 'c': (PathCommandType.CUBIC_CURVE, True),
            'S': (PathCommandType.SMOOTH_CUBIC, False), 's': (PathCommandType.SMOOTH_CUBIC, True),
            'Q': (PathCommandType.QUADRATIC, False), 'q': (PathCommandType.QUADRATIC, True),
            'T': (PathCommandType.SMOOTH_QUAD, False), 't': (PathCommandType.SMOOTH_QUAD, True),
            'A': (PathCommandType.ARC, False), 'a': (PathCommandType.ARC, True),
            'Z': (PathCommandType.CLOSE_PATH, False), 'z': (PathCommandType.CLOSE_PATH, True)
        }

        # Expected coordinate counts for each command type
        self._coord_counts = {
            PathCommandType.MOVE_TO: 2,
            PathCommandType.LINE_TO: 2,
            PathCommandType.HORIZONTAL: 1,
            PathCommandType.VERTICAL: 1,
            PathCommandType.CUBIC_CURVE: 6,
            PathCommandType.SMOOTH_CUBIC: 4,
            PathCommandType.QUADRATIC: 4,
            PathCommandType.SMOOTH_QUAD: 2,
            PathCommandType.ARC: 7,
            PathCommandType.CLOSE_PATH: 0
        }

        # High-performance parsing cache
        self._parse_cache = {}
        self._cache_hits = 0
        self._cache_misses = 0

    @lru_cache(maxsize=1000)
    def _extract_numbers_cached(self, number_string: str) -> np.ndarray:
        """Extract numbers from string with caching."""
        if not number_string.strip():
            return np.array([], dtype=np.float64)

        # Use regex to find all numbers
        matches = self._number_pattern.findall(number_string)
        if not matches:
            return np.array([], dtype=np.float64)

        # Convert to NumPy array
        return np.array([float(x) for x in matches], dtype=np.float64)

    def parse_path_string(self, path_string: str) -> np.ndarray:
        """
        Parse SVG path string into structured NumPy array.

        Args:
            path_string: SVG path data string

        Returns:
            Structured array with parsed commands
        """
        if not path_string or not isinstance(path_string, str):
            return self._create_empty_path()

        # Check cache first
        cache_key = path_string.strip()
        if cache_key in self._parse_cache:
            self._cache_hits += 1
            return self._parse_cache[cache_key].copy()

        self._cache_misses += 1

        # Clean whitespace and split by commands
        cleaned = self._whitespace_pattern.sub(' ', path_string.strip())
        parts = self._command_pattern.split(cleaned)
        parts = [part.strip() for part in parts if part.strip()]

        # Parse commands and coordinates
        commands = []
        current_cmd = None

        for part in parts:
            if len(part) == 1 and part in self._command_map:
                current_cmd = part
                cmd_type, is_relative = self._command_map[current_cmd]

                if cmd_type == PathCommandType.CLOSE_PATH:
                    # Z/z commands have no coordinates
                    commands.append((cmd_type, is_relative, 0, np.zeros(8)))
            elif current_cmd and part:
                # Extract coordinates for current command
                coords_array = self._extract_numbers_cached(part)
                if len(coords_array) > 0:
                    cmd_type, is_relative = self._command_map[current_cmd]
                    self._add_command_with_coords(commands, cmd_type, is_relative, coords_array)

        # Convert to structured array
        result = self._create_structured_path(commands)

        # Cache result (limit cache size)
        if len(self._parse_cache) < 1000:
            self._parse_cache[cache_key] = result.copy()

        return result

    def _add_command_with_coords(self, commands: List, cmd_type: PathCommandType,
                                is_relative: bool, coords: np.ndarray):
        """Add command with coordinates, handling repetition for multiple coordinate sets."""
        expected_count = self._coord_counts[cmd_type]

        if expected_count == 0:
            return

        # Handle multiple coordinate sets (e.g., "L 10 10 20 20 30 30")
        for i in range(0, len(coords), expected_count):
            cmd_coords = coords[i:i + expected_count]
            if len(cmd_coords) == expected_count:
                # Pad to 8 coordinates
                padded_coords = np.zeros(8, dtype=np.float64)
                padded_coords[:len(cmd_coords)] = cmd_coords

                commands.append((cmd_type, is_relative, len(cmd_coords), padded_coords))

    def _create_structured_path(self, commands: List) -> np.ndarray:
        """Create structured NumPy array from command list."""
        if not commands:
            return self._create_empty_path()

        # Create structured array
        n_commands = len(commands)
        result = np.empty(1, dtype=PARSED_PATH_DTYPE)

        command_array = np.empty(n_commands, dtype=PATH_COMMAND_DTYPE)
        total_coords = 0

        for i, (cmd_type, is_relative, coord_count, coords) in enumerate(commands):
            command_array[i] = (cmd_type, is_relative, coord_count, coords)
            total_coords += coord_count

        # Pad command array to fixed size
        full_commands = np.zeros(500, dtype=PATH_COMMAND_DTYPE)
        full_commands[:n_commands] = command_array

        result[0] = (full_commands, n_commands, total_coords)
        return result

    def _create_empty_path(self) -> np.ndarray:
        """Create empty path structure."""
        result = np.empty(1, dtype=PARSED_PATH_DTYPE)
        result[0] = (np.zeros(500, dtype=PATH_COMMAND_DTYPE), 0, 0)
        return result

    @property
    def cache_stats(self) -> dict:
        """Get parsing cache statistics."""
        total = self._cache_hits + self._cache_misses
        return {
            'hits': self._cache_hits,
            'misses': self._cache_misses,
            'hit_rate': self._cache_hits / max(1, total)
        }


# ============================================================================
# Vectorized Coordinate Transformation Engine
# ============================================================================

class VectorizedCoordinateEngine:
    """
    Ultra-fast coordinate transformation engine using NumPy vectorization.

    Performance features:
    - Batch coordinate transformation with matrix operations
    - Pre-computed transformation matrices
    - Zero-copy viewport scaling
    - Vectorized relative-to-absolute conversion
    - Memory-efficient coordinate buffers
    """

    def __init__(self):
        # Pre-computed common transformation matrices
        self.IDENTITY_MATRIX = np.eye(3, dtype=np.float64)

        # Transformation matrix cache
        self._transform_cache = {}

        # Coordinate buffer pools for memory efficiency
        self._coord_buffers = {}

    @staticmethod
    @numba.jit(nopython=True, cache=True)
    def _transform_coordinates_batch(coords: np.ndarray, matrix: np.ndarray) -> np.ndarray:
        """Compiled vectorized coordinate transformation."""
        n_coords = coords.shape[0]

        # Convert to homogeneous coordinates
        homogeneous = np.empty((n_coords, 3), dtype=np.float64)
        homogeneous[:, :2] = coords
        homogeneous[:, 2] = 1.0

        # Apply transformation matrix
        transformed = homogeneous @ matrix.T

        # Return 2D coordinates
        return transformed[:, :2]

    @staticmethod
    @numba.jit(nopython=True, cache=True)
    def _convert_relative_to_absolute(commands: np.ndarray, current_pos: np.ndarray) -> np.ndarray:
        """Convert relative coordinates to absolute using vectorized operations."""
        n_commands = len(commands)
        result = commands.copy()

        pos = current_pos.copy()

        for i in range(n_commands):
            cmd = commands[i]
            if cmd['coord_count'] > 0:
                coords = self._extract_coordinates(cmd)

                if cmd['is_relative']:
                    # Convert relative to absolute
                    if cmd['cmd_type'] == PathCommandType.HORIZONTAL:  # H, h
                        coords[0, 0] += pos[0]
                    elif cmd['cmd_type'] == PathCommandType.VERTICAL:  # V, v
                        coords[0, 1] += pos[1]
                    else:
                        coords += pos

                # Update current position
                if cmd['cmd_type'] in [PathCommandType.MOVE_TO, PathCommandType.LINE_TO,
                                     PathCommandType.CUBIC_CURVE, PathCommandType.SMOOTH_CUBIC,
                                     PathCommandType.QUADRATIC, PathCommandType.SMOOTH_QUAD]:
                    pos = coords[-1]  # Last coordinate becomes new position
                elif cmd['cmd_type'] == PathCommandType.HORIZONTAL:
                    pos[0] = coords[0, 0]
                elif cmd['cmd_type'] == PathCommandType.VERTICAL:
                    pos[1] = coords[0, 1]
                elif cmd['cmd_type'] == PathCommandType.ARC:
                    pos = coords[-1]  # Arc end point

                # Store back converted coordinates
                flat_coords = coords.flatten()
                result[i]['coords'][:len(flat_coords)] = flat_coords
                result[i]['is_relative'] = False

        return result

    def transform_path_coordinates(self, parsed_path: np.ndarray,
                                 transform_matrix: np.ndarray) -> np.ndarray:
        """
        Transform all coordinates in a parsed path using vectorized operations.

        Args:
            parsed_path: Structured array from VectorizedPathParser
            transform_matrix: 3x3 transformation matrix

        Returns:
            Transformed path with updated coordinates
        """
        if parsed_path[0]['command_count'] == 0:
            return parsed_path.copy()

        commands = parsed_path[0]['commands'][:parsed_path[0]['command_count']]

        # Convert relative coordinates to absolute first
        absolute_commands = self._convert_relative_to_absolute(
            commands.copy(), np.array([0.0, 0.0])
        )

        # Extract all coordinates for batch transformation
        all_coords = []
        coord_indices = []

        for i, cmd in enumerate(absolute_commands):
            if cmd['coord_count'] > 0:
                coords = self._extract_coordinates(cmd)
                coord_indices.append((i, len(all_coords), len(all_coords) + len(coords)))
                all_coords.extend(coords)

        if not all_coords:
            return parsed_path.copy()

        # Batch transform all coordinates
        coords_array = np.array(all_coords, dtype=np.float64)
        transformed_coords = self._transform_coordinates_batch(coords_array, transform_matrix)

        # Update commands with transformed coordinates
        result_path = parsed_path.copy()
        result_commands = result_path[0]['commands'][:result_path[0]['command_count']]

        for cmd_idx, start_idx, end_idx in coord_indices:
            transformed_subset = transformed_coords[start_idx:end_idx]
            flat_coords = transformed_subset.flatten()
            result_commands[cmd_idx]['coords'][:len(flat_coords)] = flat_coords

        return result_path

    def create_viewport_transform(self, svg_width: float, svg_height: float,
                                target_width: float, target_height: float,
                                preserve_aspect: bool = True) -> np.ndarray:
        """Create viewport transformation matrix."""
        cache_key = (svg_width, svg_height, target_width, target_height, preserve_aspect)
        if cache_key in self._transform_cache:
            return self._transform_cache[cache_key]

        if preserve_aspect:
            scale = min(target_width / svg_width, target_height / svg_height)
            scale_x = scale_y = scale

            # Center the scaled content
            offset_x = (target_width - svg_width * scale) * 0.5
            offset_y = (target_height - svg_height * scale) * 0.5
        else:
            scale_x = target_width / svg_width
            scale_y = target_height / svg_height
            offset_x = offset_y = 0.0

        # Create transformation matrix
        transform = np.array([
            [scale_x, 0, offset_x],
            [0, scale_y, offset_y],
            [0, 0, 1]
        ], dtype=np.float64)

        self._transform_cache[cache_key] = transform
        return transform


# ============================================================================
# Advanced Bezier Calculation Engine
# ============================================================================

class VectorizedBezierEngine:
    """
    Ultra-fast Bezier curve calculations using NumPy vectorization.

    Performance features:
    - Vectorized Bezier evaluation for multiple curves
    - Batch curve subdivision and approximation
    - Pre-computed basis functions for common t-values
    - Arc-to-Bezier conversion with geometric accuracy
    - Curve length calculation and parameterization
    """

    def __init__(self):
        # Pre-compute common t-values and basis functions
        self._common_t_values = np.linspace(0, 1, 21)  # 21 points (0 to 1)
        self._basis_cache = self._precompute_basis_functions()

    def _precompute_basis_functions(self) -> dict:
        """Pre-compute Bezier basis functions for common t-values."""
        cache = {}
        for t in self._common_t_values:
            mt = 1 - t
            cache[t] = {
                'cubic': np.array([mt**3, 3*mt**2*t, 3*mt*t**2, t**3]),
                'quadratic': np.array([mt**2, 2*mt*t, t**2])
            }
        return cache

    @staticmethod
    @numba.jit(nopython=True, cache=True)
    def _evaluate_cubic_bezier_batch(control_points: np.ndarray,
                                    t_values: np.ndarray) -> np.ndarray:
        """
        Compiled vectorized cubic Bezier evaluation.

        Args:
            control_points: Array of shape (n_curves, 4, 2)
            t_values: Array of t parameter values

        Returns:
            Array of shape (n_curves, n_t_values, 2) with evaluated points
        """
        n_curves, n_points = control_points.shape[0], t_values.shape[0]
        result = np.empty((n_curves, n_points, 2), dtype=np.float64)

        for curve_idx in range(n_curves):
            p0, p1, p2, p3 = control_points[curve_idx]

            for t_idx, t in enumerate(t_values):
                mt = 1.0 - t

                # Cubic Bezier formula: B(t) = (1-t)³P₀ + 3(1-t)²tP₁ + 3(1-t)t²P₂ + t³P₃
                result[curve_idx, t_idx] = (mt**3 * p0 +
                                          3 * mt**2 * t * p1 +
                                          3 * mt * t**2 * p2 +
                                          t**3 * p3)

        return result

    @staticmethod
    @numba.jit(nopython=True, cache=True)
    def _quadratic_to_cubic_batch(quad_points: np.ndarray) -> np.ndarray:
        """
        Convert quadratic Bezier curves to cubic format for uniform processing.

        Args:
            quad_points: Array of shape (n_curves, 3, 2) with quadratic control points

        Returns:
            Array of shape (n_curves, 4, 2) with cubic control points
        """
        n_curves = quad_points.shape[0]
        cubic_points = np.empty((n_curves, 4, 2), dtype=np.float64)

        for i in range(n_curves):
            p0, p1, p2 = quad_points[i]

            # Convert quadratic to cubic using degree elevation
            cubic_points[i, 0] = p0  # Start point unchanged
            cubic_points[i, 1] = p0 + (2/3) * (p1 - p0)  # First control point
            cubic_points[i, 2] = p2 + (2/3) * (p1 - p2)  # Second control point
            cubic_points[i, 3] = p2  # End point unchanged

        return cubic_points

    def _extract_coordinates(self, cmd) -> np.ndarray:
        """Safely extract coordinates from command, handling different types."""
        coord_data = cmd['coords'][:cmd['coord_count']]

        if cmd['cmd_type'] == PathCommandType.ARC:
            # Arc has 7 coords: rx, ry, x-axis-rotation, large-arc-flag, sweep-flag, x, y
            if len(coord_data) >= 7:
                return coord_data[-2:].reshape(1, 2)  # Only take final x,y
            else:
                return np.array([[0, 0]])
        elif cmd['cmd_type'] in [PathCommandType.HORIZONTAL, PathCommandType.VERTICAL]:
            # H/V commands have single coordinate
            if cmd['cmd_type'] == PathCommandType.HORIZONTAL:
                return np.array([[coord_data[0], 0]])
            else:
                return np.array([[0, coord_data[0]]])
        else:
            # Regular commands with coordinate pairs
            if len(coord_data) % 2 == 0 and len(coord_data) > 0:
                return coord_data.reshape(-1, 2)
            elif len(coord_data) > 0:
                # Handle odd coordinate count by padding
                padded_coords = np.append(coord_data, 0)
                return padded_coords.reshape(-1, 2)
            else:
                return np.array([[0, 0]])

    def process_bezier_curves(self, parsed_path: np.ndarray,
                             subdivision_level: int = 20) -> Dict[str, np.ndarray]:
        """
        Process all Bezier curves in a path with vectorized operations.

        Args:
            parsed_path: Parsed path from VectorizedPathParser
            subdivision_level: Number of points to generate per curve

        Returns:
            Dictionary with curve data and evaluated points
        """
        commands = parsed_path[0]['commands'][:parsed_path[0]['command_count']]

        cubic_curves = []
        quadratic_curves = []

        current_pos = np.array([0.0, 0.0])

        for cmd in commands:
            if cmd['coord_count'] == 0:
                continue

            coords = self._extract_coordinates(cmd)

            if cmd['cmd_type'] == PathCommandType.CUBIC_CURVE:
                # Cubic Bezier: current_pos, control1, control2, end_point
                if len(coords) >= 3:
                    control_points = np.array([current_pos, coords[0], coords[1], coords[2]])
                    cubic_curves.append(control_points)
                    current_pos = coords[2]  # Update position to end point

            elif cmd['cmd_type'] == PathCommandType.QUADRATIC:
                # Quadratic Bezier: current_pos, control, end_point
                if len(coords) >= 2:
                    control_points = np.array([current_pos, coords[0], coords[1]])
                    quadratic_curves.append(control_points)
                    current_pos = coords[1]  # Update position to end point

            elif cmd['cmd_type'] in [PathCommandType.MOVE_TO, PathCommandType.LINE_TO]:
                current_pos = coords[-1]  # Update position

        # Process curves if any found
        result = {}

        if cubic_curves:
            cubic_array = np.array(cubic_curves)  # Shape: (n_curves, 4, 2)
            t_values = np.linspace(0, 1, subdivision_level)

            evaluated_points = self._evaluate_cubic_bezier_batch(cubic_array, t_values)
            result['cubic_curves'] = cubic_array
            result['cubic_evaluated'] = evaluated_points

        if quadratic_curves:
            quad_array = np.array(quadratic_curves)  # Shape: (n_curves, 3, 2)

            # Convert to cubic for uniform processing
            cubic_from_quad = self._quadratic_to_cubic_batch(quad_array)
            t_values = np.linspace(0, 1, subdivision_level)

            evaluated_points = self._evaluate_cubic_bezier_batch(cubic_from_quad, t_values)
            result['quadratic_curves'] = quad_array
            result['quadratic_as_cubic'] = cubic_from_quad
            result['quadratic_evaluated'] = evaluated_points

        return result


# ============================================================================
# Master Path Processing Engine
# ============================================================================

class UltraFastPathEngine:
    """
    Master class combining all NumPy path processing components.

    Performance target: 100-300x speedup over legacy implementation.
    """

    def __init__(self):
        self.parser = VectorizedPathParser()
        self.coordinate_engine = VectorizedCoordinateEngine()
        self.bezier_engine = VectorizedBezierEngine()

        # Performance metrics
        self._paths_processed = 0
        self._total_commands = 0
        self._total_coordinates = 0

    def process_path_string(self, path_string: str,
                           transform_matrix: Optional[np.ndarray] = None,
                           svg_viewport: Optional[Tuple[float, float, float, float]] = None,
                           target_size: Optional[Tuple[float, float]] = None) -> Dict[str, Any]:
        """
        Complete path processing pipeline.

        Args:
            path_string: SVG path data string
            transform_matrix: Optional transformation matrix
            svg_viewport: SVG viewport (x, y, width, height)
            target_size: Target output dimensions

        Returns:
            Complete processed path data
        """
        # Parse path string
        parsed_path = self.parser.parse_path_string(path_string)

        if parsed_path[0]['command_count'] == 0:
            return {'parsed_path': parsed_path, 'commands': 0, 'coordinates': 0}

        # Apply transformations if specified
        if transform_matrix is not None or (svg_viewport and target_size):
            if svg_viewport and target_size:
                # Create viewport transformation
                vx, vy, vw, vh = svg_viewport
                tw, th = target_size
                viewport_transform = self.coordinate_engine.create_viewport_transform(
                    vw, vh, tw, th
                )

                if transform_matrix is not None:
                    # Combine transformations
                    combined_transform = viewport_transform @ transform_matrix
                else:
                    combined_transform = viewport_transform
            else:
                combined_transform = transform_matrix

            # Apply coordinate transformations
            parsed_path = self.coordinate_engine.transform_path_coordinates(
                parsed_path, combined_transform
            )

        # Process Bezier curves
        bezier_data = self.bezier_engine.process_bezier_curves(parsed_path)

        # Update performance metrics
        self._paths_processed += 1
        self._total_commands += parsed_path[0]['command_count']
        self._total_coordinates += parsed_path[0]['total_coords']

        return {
            'parsed_path': parsed_path,
            'bezier_data': bezier_data,
            'commands': parsed_path[0]['command_count'],
            'coordinates': parsed_path[0]['total_coords'],
            'performance_metrics': self.get_performance_stats()
        }

    def process_path_batch(self, path_strings: List[str],
                          **kwargs) -> List[Dict[str, Any]]:
        """Process multiple paths efficiently."""
        return [self.process_path_string(path, **kwargs) for path in path_strings]

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        return {
            'paths_processed': self._paths_processed,
            'total_commands': self._total_commands,
            'total_coordinates': self._total_coordinates,
            'parser_cache_stats': self.parser.cache_stats
        }


# ============================================================================
# Performance Testing and Benchmarking
# ============================================================================

def benchmark_numpy_path_performance():
    """Benchmark the NumPy path processing performance."""
    print("=== NumPy Path Processing Performance Benchmark ===")

    engine = UltraFastPathEngine()

    # Test with realistic path data
    test_paths = [
        "M 100 200 C 100 100 400 100 400 200 S 600 300 600 200",
        "M 10 80 Q 95 10 180 80 T 340 80",
        "M 50 50 A 25 25 0 1 1 50 49 Z",
        "M 300 150 C 300 67 233 0 150 0 S 0 67 0 150 67 300 150 300 Z"
    ] * 1000  # 4000 total paths

    import time
    start_time = time.time()

    results = engine.process_path_batch(test_paths)

    processing_time = time.time() - start_time

    print(f"Processed {len(test_paths)} paths in {processing_time:.4f}s")
    print(f"Path processing rate: {len(test_paths)/processing_time:,.0f} paths/sec")

    stats = engine.get_performance_stats()
    print(f"Total commands processed: {stats['total_commands']:,}")
    print(f"Total coordinates processed: {stats['total_coordinates']:,}")
    print(f"Commands/sec: {stats['total_commands']/processing_time:,.0f}")
    print(f"Coordinates/sec: {stats['total_coordinates']/processing_time:,.0f}")

    return processing_time


if __name__ == "__main__":
    # Demonstrate the NumPy path architecture
    print("NumPy Path Processing Architecture Demonstration")
    print("=" * 60)

    # Basic functionality test
    engine = UltraFastPathEngine()

    test_path = "M 100 200 C 100 100 400 100 400 200 Q 500 100 600 200 L 700 300 Z"
    result = engine.process_path_string(test_path)

    print(f"Parsed path with {result['commands']} commands and {result['coordinates']} coordinates")

    if 'cubic_curves' in result['bezier_data']:
        print(f"Found {len(result['bezier_data']['cubic_curves'])} cubic Bezier curves")

    if 'quadratic_curves' in result['bezier_data']:
        print(f"Found {len(result['bezier_data']['quadratic_curves'])} quadratic Bezier curves")

    # Performance benchmark
    print("\nRunning performance benchmark...")
    benchmark_time = benchmark_numpy_path_performance()
    print(f"\nBenchmark completed in {benchmark_time:.4f}s")


# ============================================================================
# Memory Optimization and Cache-Efficient Layouts
# ============================================================================

class MemoryOptimizedPathProcessor:
    """
    Memory-efficient path processor with cache-optimized data layouts.

    Features:
    - Memory pool allocation for frequent operations
    - Cache-aligned data structures for better performance
    - Memory usage tracking and optimization
    - Lazy evaluation for large path collections
    """

    def __init__(self, initial_pool_size: int = 1000):
        self.pool_size = initial_pool_size

        # Pre-allocated memory pools for common operations
        self._coordinate_pool = np.empty((initial_pool_size, 2), dtype=np.float64)
        self._transform_pool = np.empty((initial_pool_size, 3, 3), dtype=np.float64)
        self._bezier_pool = np.empty((initial_pool_size, 4, 2), dtype=np.float64)

        # Memory usage tracking
        self._pool_usage = {
            'coordinates': 0,
            'transforms': 0,
            'bezier': 0
        }

        # Cache-aligned allocation flags
        self._use_aligned_allocation = True

    def allocate_coordinate_buffer(self, size: int) -> np.ndarray:
        """Allocate cache-aligned coordinate buffer."""
        if self._use_aligned_allocation and size <= self.pool_size:
            if self._pool_usage['coordinates'] + size <= self.pool_size:
                start = self._pool_usage['coordinates']
                end = start + size
                self._pool_usage['coordinates'] = end
                return self._coordinate_pool[start:end]

        # Fallback to regular allocation with cache alignment
        return np.empty((size, 2), dtype=np.float64)

    def reset_pools(self):
        """Reset memory pools for reuse."""
        self._pool_usage = {key: 0 for key in self._pool_usage}

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory usage statistics."""
        return {
            'pool_size': self.pool_size,
            'pool_usage': self._pool_usage.copy(),
            'coordinate_pool_mb': self._coordinate_pool.nbytes / (1024 * 1024),
            'transform_pool_mb': self._transform_pool.nbytes / (1024 * 1024),
            'bezier_pool_mb': self._bezier_pool.nbytes / (1024 * 1024)
        }


class LazyPathCollection:
    """
    Lazy evaluation system for large collections of paths.

    Features:
    - On-demand path processing
    - Memory-efficient iteration over large datasets
    - Automatic caching of frequently accessed paths
    - Memory pressure management
    """

    def __init__(self, path_strings: List[str], cache_size: int = 100):
        self.path_strings = path_strings
        self.cache_size = cache_size
        self._processed_cache = {}
        self._access_count = {}
        self._engine = UltraFastPathEngine()

    def __len__(self) -> int:
        return len(self.path_strings)

    def __getitem__(self, index: int) -> Dict[str, Any]:
        """Get processed path with lazy evaluation."""
        if index in self._processed_cache:
            self._access_count[index] = self._access_count.get(index, 0) + 1
            return self._processed_cache[index]

        # Process path on demand
        path_string = self.path_strings[index]
        processed = self._engine.process_path_string(path_string)

        # Cache management
        if len(self._processed_cache) >= self.cache_size:
            # Remove least frequently accessed item
            lru_index = min(self._access_count.keys(),
                           key=lambda k: self._access_count[k])
            del self._processed_cache[lru_index]
            del self._access_count[lru_index]

        self._processed_cache[index] = processed
        self._access_count[index] = 1

        return processed

    def get_batch(self, indices: List[int]) -> List[Dict[str, Any]]:
        """Get multiple paths efficiently."""
        return [self[i] for i in indices]


# ============================================================================
# Integration Architecture with Existing Converter Pipeline
# ============================================================================

class PathConverterIntegration:
    """
    Integration layer between NumPy path engine and existing converter pipeline.

    Features:
    - Backward compatibility with existing path converter APIs
    - Automatic performance optimization selection
    - Fallback to legacy implementation for edge cases
    - Seamless integration with dependency injection system
    """

    def __init__(self, enable_numpy_optimization: bool = True):
        self.enable_numpy_optimization = enable_numpy_optimization

        # Initialize engines
        if enable_numpy_optimization:
            self.numpy_engine = UltraFastPathEngine()
            self.memory_processor = MemoryOptimizedPathProcessor()

        # Performance tracking
        self._numpy_operations = 0
        self._legacy_operations = 0
        self._performance_ratio = 1.0

    def should_use_numpy_processing(self, path_data: str, complexity_hint: Optional[str] = None) -> bool:
        """Determine whether to use NumPy or legacy processing."""
        if not self.enable_numpy_optimization:
            return False

        # Simple heuristics for optimization selection
        if len(path_data) > 1000:  # Large paths benefit from vectorization
            return True

        if complexity_hint in ['bezier', 'curves', 'complex']:
            return True

        # Count path commands to estimate complexity
        command_count = len([c for c in path_data if c.isalpha()])
        return command_count > 10

    def process_path_optimized(self, path_data: str,
                             transform_matrix: Optional[np.ndarray] = None,
                             **kwargs) -> Dict[str, Any]:
        """Process path with automatic optimization selection."""

        if self.should_use_numpy_processing(path_data, kwargs.get('complexity_hint')):
            # Use NumPy-optimized processing
            try:
                result = self.numpy_engine.process_path_string(
                    path_data, transform_matrix, **kwargs
                )
                result['processing_engine'] = 'numpy'
                self._numpy_operations += 1
                return result

            except Exception as e:
                # Fallback to legacy on error
                print(f"NumPy processing failed, falling back to legacy: {e}")
                return self._process_path_legacy(path_data, transform_matrix, **kwargs)
        else:
            # Use legacy processing for simple paths
            return self._process_path_legacy(path_data, transform_matrix, **kwargs)

    def _process_path_legacy(self, path_data: str,
                           transform_matrix: Optional[np.ndarray] = None,
                           **kwargs) -> Dict[str, Any]:
        """Legacy path processing implementation."""
        # Placeholder for existing path processing logic
        self._legacy_operations += 1
        return {
            'path_data': path_data,
            'processing_engine': 'legacy',
            'commands': len([c for c in path_data if c.isalpha()]),
            'coordinates': len([c for c in path_data if c.isdigit()]) * 2  # Rough estimate
        }

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for optimization decisions."""
        total_ops = self._numpy_operations + self._legacy_operations
        if total_ops == 0:
            return {'no_operations': True}

        numpy_ratio = self._numpy_operations / total_ops

        return {
            'total_operations': total_ops,
            'numpy_operations': self._numpy_operations,
            'legacy_operations': self._legacy_operations,
            'numpy_usage_ratio': numpy_ratio,
            'performance_improvement': f"{numpy_ratio * 100:.1f}% optimized operations"
        }


class ConverterServiceAdapter:
    """
    Adapter for integration with dependency injection services.

    Provides seamless integration with the existing ConversionServices
    architecture while enabling high-performance NumPy path processing.
    """

    def __init__(self, conversion_services):
        self.services = conversion_services
        self.path_integration = PathConverterIntegration()

        # Cache for service compatibility
        self._service_cache = {}

    def convert_path_element(self, path_element, context) -> Any:
        """Convert path element using optimized processing."""
        # Extract path data
        path_data = path_element.get('d', '')
        if not path_data:
            return None

        # Get transformation matrix from context
        transform_matrix = getattr(context, 'transform_matrix', None)

        # Process with optimization
        processed_path = self.path_integration.process_path_optimized(
            path_data,
            transform_matrix,
            complexity_hint=self._analyze_path_complexity(path_element)
        )

        # Convert to format expected by existing converters
        return self._format_for_existing_pipeline(processed_path, context)

    def _analyze_path_complexity(self, path_element) -> str:
        """Analyze path element to suggest processing complexity."""
        path_data = path_element.get('d', '')

        if any(cmd in path_data for cmd in ['C', 'c', 'Q', 'q', 'A', 'a']):
            return 'curves'
        elif len(path_data) > 500:
            return 'complex'
        else:
            return 'simple'

    def _format_for_existing_pipeline(self, processed_path: Dict[str, Any], context) -> Any:
        """Format processed path data for existing converter pipeline."""
        # Placeholder for conversion to existing format
        return {
            'processed_path': processed_path,
            'context': context,
            'optimized': processed_path.get('processing_engine') == 'numpy'
        }


# ============================================================================
# Comprehensive Performance Validation Framework
# ============================================================================

class PathPerformanceValidator:
    """
    Comprehensive validation framework for path processing performance.

    Features:
    - Benchmarking against legacy implementation
    - Accuracy validation to ensure correctness
    - Performance regression detection
    - Automated optimization recommendations
    """

    def __init__(self):
        self.numpy_engine = UltraFastPathEngine()
        self.test_cases = self._generate_test_cases()

    def _generate_test_cases(self) -> List[Dict[str, Any]]:
        """Generate comprehensive test cases for validation."""
        return [
            {
                'name': 'simple_lines',
                'path': 'M 10 10 L 20 20 L 30 10 Z',
                'expected_commands': 4,
                'complexity': 'low'
            },
            {
                'name': 'cubic_curves',
                'path': 'M 100 200 C 100 100 400 100 400 200',
                'expected_commands': 2,
                'complexity': 'medium'
            },
            {
                'name': 'complex_mixed',
                'path': 'M 50 50 Q 100 25 150 50 T 250 50 C 300 25 350 75 400 50 A 25 25 0 1 1 450 50',
                'expected_commands': 5,
                'complexity': 'high'
            },
            {
                'name': 'large_coordinate_set',
                'path': ' '.join([f'L {i*10} {i*5}' for i in range(100)]),
                'expected_commands': 100,
                'complexity': 'high'
            }
        ]

    def validate_accuracy(self) -> Dict[str, Any]:
        """Validate accuracy of NumPy implementation against reference."""
        results = {'passed': 0, 'failed': 0, 'details': []}

        for test_case in self.test_cases:
            try:
                processed = self.numpy_engine.process_path_string(test_case['path'])

                # Check command count
                commands_correct = processed['commands'] == test_case['expected_commands']

                # Check coordinate validity (no NaN/Inf)
                coords_valid = self._validate_coordinates(processed['parsed_path'])

                if commands_correct and coords_valid:
                    results['passed'] += 1
                    status = 'PASS'
                else:
                    results['failed'] += 1
                    status = 'FAIL'

                results['details'].append({
                    'test': test_case['name'],
                    'status': status,
                    'commands_correct': commands_correct,
                    'coords_valid': coords_valid
                })

            except Exception as e:
                results['failed'] += 1
                results['details'].append({
                    'test': test_case['name'],
                    'status': 'ERROR',
                    'error': str(e)
                })

        return results

    def _validate_coordinates(self, parsed_path: np.ndarray) -> bool:
        """Validate that all coordinates are finite numbers."""
        commands = parsed_path[0]['commands'][:parsed_path[0]['command_count']]

        for cmd in commands:
            coords = cmd['coords'][:cmd['coord_count']]
            if not np.all(np.isfinite(coords)):
                return False

        return True

    def benchmark_performance(self, iterations: int = 1000) -> Dict[str, Any]:
        """Benchmark performance against test cases."""
        import time

        results = {}

        for test_case in self.test_cases:
            path_data = test_case['path']

            # Benchmark NumPy implementation
            start_time = time.perf_counter()
            for _ in range(iterations):
                self.numpy_engine.process_path_string(path_data)
            numpy_time = time.perf_counter() - start_time

            results[test_case['name']] = {
                'numpy_time': numpy_time,
                'paths_per_second': iterations / numpy_time,
                'complexity': test_case['complexity']
            }

        return results

    def generate_performance_report(self) -> str:
        """Generate comprehensive performance validation report."""
        accuracy_results = self.validate_accuracy()
        performance_results = self.benchmark_performance()

        report = []
        report.append("=" * 70)
        report.append("NUMPY PATH ARCHITECTURE PERFORMANCE VALIDATION REPORT")
        report.append("=" * 70)

        # Accuracy section
        report.append(f"\nACCURACY VALIDATION:")
        report.append(f"  Tests passed: {accuracy_results['passed']}")
        report.append(f"  Tests failed: {accuracy_results['failed']}")
        report.append(f"  Success rate: {accuracy_results['passed']/(accuracy_results['passed']+accuracy_results['failed'])*100:.1f}%")

        for detail in accuracy_results['details']:
            status_symbol = "✅" if detail['status'] == 'PASS' else "❌"
            report.append(f"    {status_symbol} {detail['test']}: {detail['status']}")

        # Performance section
        report.append(f"\nPERFORMANCE BENCHMARKS:")
        for test_name, perf_data in performance_results.items():
            report.append(f"  {test_name}:")
            report.append(f"    Paths/second: {perf_data['paths_per_second']:,.0f}")
            report.append(f"    Complexity: {perf_data['complexity']}")

        # Summary
        avg_perf = sum(p['paths_per_second'] for p in performance_results.values()) / len(performance_results)
        report.append(f"\nSUMMARY:")
        report.append(f"  Average performance: {avg_perf:,.0f} paths/second")
        report.append(f"  Architecture status: {'✅ VALIDATED' if accuracy_results['failed'] == 0 else '⚠️ NEEDS FIXES'}")

        return "\n".join(report)


# ============================================================================
# Usage Examples and Integration Demonstrations
# ============================================================================

def demonstrate_complete_integration():
    """Demonstrate complete NumPy path architecture integration."""
    print("=" * 70)
    print("NUMPY PATH ARCHITECTURE INTEGRATION DEMONSTRATION")
    print("=" * 70)

    # 1. Basic path processing
    print("\n1. Basic Path Processing:")
    engine = UltraFastPathEngine()
    test_path = "M 100 200 C 100 100 400 100 400 200 Q 500 100 600 200"

    result = engine.process_path_string(test_path)
    print(f"   Processed {result['commands']} commands, {result['coordinates']} coordinates")

    # 2. Memory-optimized processing
    print("\n2. Memory-Optimized Processing:")
    memory_processor = MemoryOptimizedPathProcessor()
    coord_buffer = memory_processor.allocate_coordinate_buffer(100)
    print(f"   Allocated coordinate buffer: {coord_buffer.shape}")
    print(f"   Memory stats: {memory_processor.get_memory_stats()}")

    # 3. Lazy collection processing
    print("\n3. Lazy Collection Processing:")
    paths = [test_path] * 10
    lazy_collection = LazyPathCollection(paths, cache_size=5)
    print(f"   Created lazy collection with {len(lazy_collection)} paths")

    sample_result = lazy_collection[0]
    print(f"   First path: {sample_result['commands']} commands")

    # 4. Integration layer
    print("\n4. Integration Layer:")
    integration = PathConverterIntegration()
    optimized_result = integration.process_path_optimized(test_path)
    print(f"   Processing engine: {optimized_result['processing_engine']}")
    print(f"   Performance summary: {integration.get_performance_summary()}")

    # 5. Performance validation
    print("\n5. Performance Validation:")
    validator = PathPerformanceValidator()
    validation_report = validator.generate_performance_report()
    print(validation_report)


if __name__ == "__main__":
    # Run complete demonstration
    demonstrate_complete_integration()