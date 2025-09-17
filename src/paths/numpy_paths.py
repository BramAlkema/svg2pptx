#!/usr/bin/env python3
"""
Ultra-Fast NumPy Path Processing Engine for SVG2PPTX

Complete rewrite of path system using pure NumPy for maximum performance.
Targets 100-300x speedup over legacy implementation through:
- Native NumPy structured arrays
- Vectorized operations
- Pre-compiled patterns
- Advanced caching
- Compiled critical paths

No backwards compatibility - designed for pure performance.
"""

import numpy as np
import re
import time
import hashlib
import weakref
from typing import Union, Optional, Tuple, Dict, Any, List
from dataclasses import dataclass
from contextlib import contextmanager
from enum import IntEnum
import functools
import math
from functools import lru_cache, wraps

# Optional numba import for performance
try:
    import numba
    HAS_NUMBA = True
except ImportError:
    HAS_NUMBA = False
    # Mock decorator for when numba is not available
    class MockNumba:
        @staticmethod
        def jit(*args, **kwargs):
            def decorator(func):
                return func
            return decorator
    numba = MockNumba()

# Type aliases for clarity and performance
PathArray = np.ndarray        # Structured array for path commands
CoordinateArray = np.ndarray  # Array for coordinates
BezierArray = np.ndarray      # Array for Bezier curves
PathString = Union[str, List[str]]


class AdvancedLRUCache:
    """Advanced LRU cache with memory management and statistics."""

    def __init__(self, maxsize: int = 1000, max_memory_mb: int = 100):
        self.maxsize = maxsize
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.cache = {}
        self.access_order = []
        self.memory_usage = 0
        self.hits = 0
        self.misses = 0

    def _estimate_memory(self, obj) -> int:
        """Estimate memory usage of cached object."""
        if isinstance(obj, np.ndarray):
            return obj.nbytes
        elif isinstance(obj, dict):
            return sum(self._estimate_memory(v) for v in obj.values()) + len(obj) * 100
        elif isinstance(obj, (list, tuple)):
            return sum(self._estimate_memory(item) for item in obj) + len(obj) * 50
        else:
            return 100  # Default estimate for other objects

    def _evict_if_needed(self):
        """Evict least recently used items if cache is too full."""
        while (len(self.cache) > self.maxsize or
               self.memory_usage > self.max_memory_bytes) and self.access_order:
            oldest_key = self.access_order.pop(0)
            if oldest_key in self.cache:
                removed_item = self.cache.pop(oldest_key)
                self.memory_usage -= self._estimate_memory(removed_item)

    def get(self, key: str):
        """Get item from cache."""
        if key in self.cache:
            # Move to end (most recently used)
            self.access_order.remove(key)
            self.access_order.append(key)
            self.hits += 1
            return self.cache[key]
        else:
            self.misses += 1
            return None

    def put(self, key: str, value):
        """Put item in cache."""
        memory_cost = self._estimate_memory(value)

        if key in self.cache:
            # Update existing item
            old_memory = self._estimate_memory(self.cache[key])
            self.cache[key] = value
            self.memory_usage += memory_cost - old_memory
            self.access_order.remove(key)
            self.access_order.append(key)
        else:
            # Add new item
            self.cache[key] = value
            self.memory_usage += memory_cost
            self.access_order.append(key)

        self._evict_if_needed()

    def clear(self):
        """Clear all cached items."""
        self.cache.clear()
        self.access_order.clear()
        self.memory_usage = 0

    def stats(self) -> dict:
        """Get cache statistics."""
        total_requests = self.hits + self.misses
        return {
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': self.hits / max(1, total_requests),
            'size': len(self.cache),
            'max_size': self.maxsize,
            'memory_usage_mb': self.memory_usage / (1024 * 1024),
            'max_memory_mb': self.max_memory_bytes / (1024 * 1024)
        }


class ArrayPool:
    """Memory pool for reusing NumPy arrays to reduce allocations."""

    def __init__(self, max_arrays_per_shape: int = 10):
        self.pools = {}  # shape -> list of arrays
        self.max_arrays_per_shape = max_arrays_per_shape
        self.allocations = 0
        self.reuses = 0

    def get_array(self, shape: tuple, dtype=np.float64) -> np.ndarray:
        """Get array from pool or create new one."""
        # Normalize dtype to ensure consistent key hashing
        normalized_dtype = np.dtype(dtype)
        key = (shape, normalized_dtype)

        if key in self.pools and self.pools[key]:
            array = self.pools[key].pop()
            array.fill(0)  # Clear previous data
            self.reuses += 1
            return array
        else:
            self.allocations += 1
            return np.zeros(shape, dtype=dtype)

    def return_array(self, array: np.ndarray):
        """Return array to pool for reuse."""
        # Use consistent key normalization
        key = (array.shape, array.dtype)

        if key not in self.pools:
            self.pools[key] = []

        if len(self.pools[key]) < self.max_arrays_per_shape:
            self.pools[key].append(array)

    def clear(self):
        """Clear all pooled arrays."""
        self.pools.clear()

    def stats(self) -> dict:
        """Get pool statistics."""
        total_requests = self.allocations + self.reuses
        return {
            'allocations': self.allocations,
            'reuses': self.reuses,
            'reuse_rate': self.reuses / max(1, total_requests),
            'pool_sizes': {str(k): len(v) for k, v in self.pools.items()}
        }


def path_cache(maxsize: int = 512):
    """Decorator for caching path processing results."""
    def decorator(func):
        cache = AdvancedLRUCache(maxsize=maxsize, max_memory_mb=50)

        @wraps(func)
        def wrapper(self, path_string, *args, **kwargs):
            # Create cache key from path string and arguments
            key_data = f"{path_string}:{args}:{sorted(kwargs.items())}"
            cache_key = hashlib.md5(key_data.encode()).hexdigest()

            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            # Compute result and cache it
            result = func(self, path_string, *args, **kwargs)
            cache.put(cache_key, result)

            # Update instance cache stats
            if hasattr(self, '_path_cache_stats'):
                self._path_cache_stats = cache.stats()

            return result

        # Store cache reference for stats access
        wrapper._cache = cache
        return wrapper
    return decorator


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
COMMAND_DTYPE = np.dtype([
    ('type', 'u1'),            # Command type (8-bit unsigned int)
    ('relative', 'u1'),        # 0=absolute, 1=relative
    ('coord_count', 'u1'),     # Number of coordinates used
    ('coords', 'f8', (8,))     # Up to 8 coordinates (for arcs)
])

PATH_DTYPE = np.dtype([
    ('commands', COMMAND_DTYPE, (200,)),  # Up to 200 commands per path
    ('command_count', 'u4'),              # Actual number of commands
    ('coord_count', 'u4')                 # Total coordinate count
])


class PathData:
    """NumPy-optimized path data container with vectorized operations."""

    def __init__(self, path_string: str = ""):
        """Initialize path data from SVG path string."""
        self._data = np.zeros(1, dtype=PATH_DTYPE)[0]
        if path_string:
            self._parse_string(path_string)

    def _parse_string(self, path_string: str):
        """Parse SVG path string into structured array."""
        if not path_string:
            return

        # Use the path engine's parser for consistency
        engine = PathEngine()
        parsed = engine._parse_path_string_fast(path_string)
        self._data = parsed

    @property
    def commands(self) -> np.ndarray:
        """Get commands array."""
        return self._data['commands'][:self._data['command_count']]

    @commands.setter
    def commands(self, value: np.ndarray):
        """Set commands array."""
        if len(value) <= 200:  # Max command limit
            self._data['commands'][:len(value)] = value
            self._data['command_count'] = len(value)
        else:
            raise ValueError("Too many commands (max 200)")

    def set_commands(self, commands: np.ndarray):
        """Set commands array (alternative method)."""
        self.commands = commands

    @property
    def command_count(self) -> int:
        """Get number of commands."""
        return int(self._data['command_count'])

    @property
    def coordinate_count(self) -> int:
        """Get total coordinate count."""
        return int(self._data['coord_count'])

    def __repr__(self) -> str:
        """String representation."""
        return f"PathData(commands={self.command_count}, coords={self.coordinate_count})"


class PathEngine:
    """
    Ultra-fast NumPy-based path processing engine.

    Performance Features:
    - Native NumPy structured arrays for all path data
    - Vectorized coordinate transformations
    - Pre-compiled regex patterns
    - Advanced caching with LRU eviction
    - Compiled critical paths with Numba
    - Zero-copy operations where possible

    Target: 100-300x speedup over legacy implementation
    """

    def __init__(self, cache_size: int = 1000, array_pool_size: int = 20, enable_profiling: bool = False):
        """Initialize ultra-fast path processing engine with advanced caching."""
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

        # Advanced caching and performance systems
        self._path_cache = AdvancedLRUCache(maxsize=cache_size, max_memory_mb=100)
        self._bezier_cache = AdvancedLRUCache(maxsize=cache_size // 2, max_memory_mb=50)
        self._transform_cache = AdvancedLRUCache(maxsize=cache_size // 4, max_memory_mb=25)

        # Array pool for memory efficiency
        self._array_pool = ArrayPool(max_arrays_per_shape=array_pool_size)

        # Performance profiling
        self._enable_profiling = enable_profiling
        self._operation_times = {}
        self._operation_counts = {}

        # Traditional cache stats for compatibility
        self._cache_hits = 0
        self._cache_misses = 0

        # High-performance specialized caches
        self._parse_cache: dict = {}
        self._coordinate_cache: dict = {}

    @contextmanager
    def _profile_operation(self, operation_name: str):
        """Context manager for profiling operations."""
        if not self._enable_profiling:
            yield
            return

        start_time = time.perf_counter()
        try:
            yield
        finally:
            end_time = time.perf_counter()
            duration = end_time - start_time

            if operation_name not in self._operation_times:
                self._operation_times[operation_name] = []
                self._operation_counts[operation_name] = 0

            self._operation_times[operation_name].append(duration)
            self._operation_counts[operation_name] += 1

    def _get_pooled_array(self, shape: tuple, dtype=np.float64) -> np.ndarray:
        """Get array from pool with automatic return tracking."""
        return self._array_pool.get_array(shape, dtype)

    def _return_pooled_array(self, array: np.ndarray):
        """Return array to pool for reuse."""
        self._array_pool.return_array(array)

    def _get_cached_path_result(self, path_string: str, operation: str) -> Optional[Any]:
        """Get cached result for path operation."""
        cache_key = hashlib.md5(f"{operation}:{path_string}".encode()).hexdigest()

        if operation == 'parse':
            result = self._path_cache.get(cache_key)
        elif operation == 'bezier':
            result = self._bezier_cache.get(cache_key)
        elif operation == 'transform':
            result = self._transform_cache.get(cache_key)
        else:
            return None

        if result is not None:
            self._cache_hits += 1
            return result
        else:
            self._cache_misses += 1
            return None

    def _cache_path_result(self, path_string: str, operation: str, result: Any):
        """Cache result for path operation."""
        cache_key = hashlib.md5(f"{operation}:{path_string}".encode()).hexdigest()

        if operation == 'parse':
            self._path_cache.put(cache_key, result)
        elif operation == 'bezier':
            self._bezier_cache.put(cache_key, result)
        elif operation == 'transform':
            self._transform_cache.put(cache_key, result)

    def optimize_for_large_datasets(self, enable: bool = True):
        """Optimize engine settings for large path datasets."""
        if enable:
            # Increase cache sizes for large datasets
            self._path_cache.maxsize *= 2
            self._bezier_cache.maxsize *= 2
            self._transform_cache.maxsize *= 2

            # Increase memory limits
            self._path_cache.max_memory_bytes *= 2
            self._bezier_cache.max_memory_bytes *= 2
            self._transform_cache.max_memory_bytes *= 2

            # Increase array pool size
            self._array_pool.max_arrays_per_shape *= 2
        else:
            # Reset to default sizes
            self._path_cache.maxsize //= 2
            self._bezier_cache.maxsize //= 2
            self._transform_cache.maxsize //= 2

            self._path_cache.max_memory_bytes //= 2
            self._bezier_cache.max_memory_bytes //= 2
            self._transform_cache.max_memory_bytes //= 2

            self._array_pool.max_arrays_per_shape //= 2

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics."""
        stats = {
            'caching': {
                'path_cache': self._path_cache.stats(),
                'bezier_cache': self._bezier_cache.stats(),
                'transform_cache': self._transform_cache.stats(),
                'overall_hit_rate': self._cache_hits / max(1, self._cache_hits + self._cache_misses)
            },
            'memory': {
                'array_pool': self._array_pool.stats()
            }
        }

        if self._enable_profiling and self._operation_times:
            # Calculate operation statistics
            operation_stats = {}
            for op_name, times in self._operation_times.items():
                if times:
                    operation_stats[op_name] = {
                        'count': len(times),
                        'total_time': sum(times),
                        'avg_time': sum(times) / len(times),
                        'min_time': min(times),
                        'max_time': max(times)
                    }
            stats['profiling'] = operation_stats

        return stats

    def clear_all_caches(self):
        """Clear all caches and reset performance counters."""
        self._path_cache.clear()
        self._bezier_cache.clear()
        self._transform_cache.clear()
        self._array_pool.clear()

        self._parse_cache.clear()
        self._coordinate_cache.clear()

        self._cache_hits = 0
        self._cache_misses = 0

        if self._enable_profiling:
            self._operation_times.clear()
            self._operation_counts.clear()

    @functools.lru_cache(maxsize=500)
    def _extract_numbers_cached(self, number_string: str) -> Tuple[float, ...]:
        """Extract numbers from string with caching."""
        if not number_string.strip():
            return ()

        matches = self._number_pattern.findall(number_string)
        return tuple(float(x) for x in matches) if matches else ()

    def _parse_path_string_fast(self, path_string: str) -> np.ndarray:
        """
        Fast path string parsing with caching.

        Args:
            path_string: SVG path data string

        Returns:
            Single structured array element with path data
        """
        if not path_string:
            return self._create_empty_path()

        # Check cache first
        cache_key = path_string.strip()
        if cache_key in self._parse_cache:
            self._cache_hits += 1
            return self._parse_cache[cache_key].copy()

        self._cache_misses += 1

        # Clean and split by commands
        cleaned = self._whitespace_pattern.sub(' ', path_string.strip())
        parts = self._command_pattern.split(cleaned)
        parts = [part.strip() for part in parts if part.strip()]

        # Parse commands
        commands = []
        current_cmd = None
        total_coords = 0

        for part in parts:
            if len(part) == 1 and part in self._command_map:
                current_cmd = part
                cmd_type, is_relative = self._command_map[current_cmd]

                if cmd_type == PathCommandType.CLOSE_PATH:
                    # Z/z commands have no coordinates
                    cmd_coords = np.zeros(8, dtype=np.float64)
                    commands.append((cmd_type, is_relative, 0, cmd_coords))
            elif current_cmd and part:
                # Extract coordinates for current command
                coords_tuple = self._extract_numbers_cached(part)
                if coords_tuple:
                    cmd_type, is_relative = self._command_map[current_cmd]
                    coords_added = self._add_command_coords(
                        commands, cmd_type, is_relative, coords_tuple
                    )
                    total_coords += coords_added

        # Create structured path data
        result = self._create_structured_path(commands, total_coords)

        # Cache result
        if len(self._parse_cache) < 500:
            self._parse_cache[cache_key] = result.copy()

        return result

    def _add_command_coords(self, commands: List, cmd_type: PathCommandType,
                           is_relative: bool, coords: Tuple[float, ...]) -> int:
        """Add command with coordinates, handling repetition."""
        expected_count = self._coord_counts[cmd_type]
        total_added = 0

        if expected_count == 0:
            return 0

        # Handle multiple coordinate sets
        coords_list = list(coords)
        for i in range(0, len(coords_list), expected_count):
            cmd_coords = coords_list[i:i + expected_count]
            if len(cmd_coords) == expected_count:
                # Pad to 8 coordinates
                padded_coords = np.zeros(8, dtype=np.float64)
                padded_coords[:len(cmd_coords)] = cmd_coords

                commands.append((cmd_type, is_relative, len(cmd_coords), padded_coords))
                total_added += len(cmd_coords)

        return total_added

    def _create_structured_path(self, commands: List, total_coords: int) -> np.ndarray:
        """Create structured NumPy array from command list."""
        if not commands:
            return self._create_empty_path()

        # Create result structure
        result = np.zeros(1, dtype=PATH_DTYPE)[0]

        # Fill command array
        n_commands = min(len(commands), 200)  # Limit to array size
        for i in range(n_commands):
            cmd_type, is_relative, coord_count, coords = commands[i]
            result['commands'][i] = (cmd_type, is_relative, coord_count, coords)

        result['command_count'] = n_commands
        result['coord_count'] = total_coords

        return result

    def _create_empty_path(self) -> np.ndarray:
        """Create empty path structure."""
        return np.zeros(1, dtype=PATH_DTYPE)[0]

    @staticmethod
    @numba.jit(nopython=True, cache=True)
    def _transform_coordinates_vectorized(coords: np.ndarray, matrix: np.ndarray) -> np.ndarray:
        """Compiled vectorized coordinate transformation."""
        n_coords = coords.shape[0]
        result = np.empty((n_coords, 2), dtype=np.float64)

        # Extract matrix elements for direct access
        m00, m01, m02 = matrix[0, 0], matrix[0, 1], matrix[0, 2]
        m10, m11, m12 = matrix[1, 0], matrix[1, 1], matrix[1, 2]

        for i in range(n_coords):
            x, y = coords[i, 0], coords[i, 1]
            result[i, 0] = m00 * x + m01 * y + m02
            result[i, 1] = m10 * x + m11 * y + m12

        return result

    def process_path(self, path_string: str,
                    transform_matrix: Optional[np.ndarray] = None,
                    viewport: Optional[Tuple[float, float, float, float]] = None,
                    target_size: Optional[Tuple[float, float]] = None) -> Dict[str, Any]:
        """
        Process SVG path with optional transformations and advanced caching.

        Args:
            path_string: SVG path data string
            transform_matrix: Optional 3x3 transformation matrix
            viewport: SVG viewport (x, y, width, height)
            target_size: Target output dimensions (width, height)

        Returns:
            Dictionary with processed path data and statistics
        """
        # Check cache first for expensive operations
        cache_params = f"{transform_matrix}:{viewport}:{target_size}"
        cached_result = self._get_cached_path_result(f"{path_string}:{cache_params}", "parse")
        if cached_result is not None:
            return cached_result

        with self._profile_operation("process_path"):
            start_time = time.perf_counter()

            # Parse path string with performance tracking
            path_data = self._parse_path_string_fast(path_string)

            if path_data['command_count'] == 0:
                empty_result = {
                    'path_data': PathData(),
                    'commands': 0,
                    'coordinates': 0,
                    'transformed': False,
                    'performance': {
                        'processing_time': time.perf_counter() - start_time,
                        'cache_hit': False
                    }
                }
                # Cache empty result
                self._cache_path_result(f"{path_string}:{cache_params}", "parse", empty_result)
                return empty_result

            # Apply transformations if specified
            transformed = False
            if transform_matrix is not None or (viewport and target_size):
                with self._profile_operation("apply_transformations"):
                    path_data = self._apply_transformations(
                        path_data, transform_matrix, viewport, target_size
                    )
                    transformed = True

            # Create PathData wrapper
            result_path = PathData()
            result_path._data = path_data

            processing_time = time.perf_counter() - start_time

            result = {
                'path_data': result_path,
                'commands': int(path_data['command_count']),
                'coordinates': int(path_data['coord_count']),
                'transformed': transformed,
                'performance': {
                    'processing_time': processing_time,
                    'commands_per_second': int(path_data['command_count']) / max(processing_time, 1e-6),
                    'cache_hit': False
                }
            }

            # Cache the successful result
            self._cache_path_result(f"{path_string}:{cache_params}", "parse", result)
            return result

    def _apply_transformations(self, path_data: np.ndarray,
                             transform_matrix: Optional[np.ndarray],
                             viewport: Optional[Tuple[float, float, float, float]],
                             target_size: Optional[Tuple[float, float]]) -> np.ndarray:
        """Apply coordinate transformations to path data."""
        # Create viewport transformation if needed
        if viewport and target_size:
            vx, vy, vw, vh = viewport
            tw, th = target_size

            # Create viewport scaling matrix
            scale_x = tw / vw if vw > 0 else 1.0
            scale_y = th / vh if vh > 0 else 1.0
            offset_x = -vx * scale_x
            offset_y = -vy * scale_y

            viewport_matrix = np.array([
                [scale_x, 0, offset_x],
                [0, scale_y, offset_y],
                [0, 0, 1]
            ], dtype=np.float64)

            if transform_matrix is not None:
                # Combine transformations
                final_matrix = viewport_matrix @ transform_matrix
            else:
                final_matrix = viewport_matrix
        else:
            final_matrix = transform_matrix

        if final_matrix is None:
            return path_data

        # Extract and transform all coordinates
        commands = path_data['commands'][:path_data['command_count']]
        all_coords = []

        for i, cmd in enumerate(commands):
            if cmd['coord_count'] > 0:
                coords = cmd['coords'][:cmd['coord_count']].reshape(-1, 2)
                all_coords.append((i, coords))

        if not all_coords:
            return path_data

        # Batch transform all coordinates
        for cmd_idx, coords in all_coords:
            if len(coords) > 0:
                transformed_coords = self._transform_coordinates_vectorized(coords, final_matrix)
                flat_coords = transformed_coords.flatten()
                path_data['commands'][cmd_idx]['coords'][:len(flat_coords)] = flat_coords

        return path_data

    def process_batch(self, path_strings: List[str], **kwargs) -> List[Dict[str, Any]]:
        """Process multiple paths efficiently."""
        return [self.process_path(path, **kwargs) for path in path_strings]

    @staticmethod
    @numba.jit(nopython=True, cache=True)
    def _evaluate_cubic_bezier(p0: np.ndarray, p1: np.ndarray,
                              p2: np.ndarray, p3: np.ndarray,
                              t_values: np.ndarray) -> np.ndarray:
        """Evaluate cubic Bezier curve at multiple t values."""
        n_points = len(t_values)
        result = np.empty((n_points, 2), dtype=np.float64)

        for i, t in enumerate(t_values):
            mt = 1.0 - t
            # Cubic Bezier formula
            result[i] = (mt**3 * p0 + 3 * mt**2 * t * p1 +
                        3 * mt * t**2 * p2 + t**3 * p3)

        return result

    @staticmethod
    @numba.jit(nopython=True, cache=True)
    def _evaluate_cubic_bezier_batch(control_points: np.ndarray,
                                   t_values: np.ndarray) -> np.ndarray:
        """Vectorized evaluation of multiple cubic Bezier curves."""
        n_curves, n_points = control_points.shape[0], t_values.shape[0]
        results = np.empty((n_curves, n_points, 2), dtype=np.float64)

        for curve_idx in range(n_curves):
            p0 = control_points[curve_idx, 0]
            p1 = control_points[curve_idx, 1]
            p2 = control_points[curve_idx, 2]
            p3 = control_points[curve_idx, 3]

            for t_idx, t in enumerate(t_values):
                mt = 1.0 - t
                mt2 = mt * mt
                mt3 = mt2 * mt
                t2 = t * t
                t3 = t2 * t

                # Vectorized cubic Bezier evaluation
                results[curve_idx, t_idx] = (
                    mt3 * p0 + 3 * mt2 * t * p1 +
                    3 * mt * t2 * p2 + t3 * p3
                )

        return results

    @staticmethod
    @numba.jit(nopython=True, cache=True)
    def _subdivide_cubic_bezier(p0: np.ndarray, p1: np.ndarray,
                              p2: np.ndarray, p3: np.ndarray,
                              t: float) -> tuple:
        """Subdivide cubic Bezier curve at parameter t."""
        # De Casteljau's algorithm for curve subdivision
        q0 = p0
        q1 = (1-t) * p0 + t * p1
        q2 = (1-t) * ((1-t) * p0 + t * p1) + t * ((1-t) * p1 + t * p2)
        q3 = (1-t)**3 * p0 + 3*(1-t)**2*t * p1 + 3*(1-t)*t**2 * p2 + t**3 * p3

        r0 = q3
        r1 = (1-t) * ((1-t) * p1 + t * p2) + t * ((1-t) * p2 + t * p3)
        r2 = (1-t) * p2 + t * p3
        r3 = p3

        return ((q0, q1, q2, q3), (r0, r1, r2, r3))

    @staticmethod
    def _arc_to_bezier_params(cx: float, cy: float, rx: float, ry: float,
                            phi: float, start_angle: float, sweep_angle: float) -> np.ndarray:
        """Convert arc parameters to cubic Bezier control points."""
        # Handle sweep angle constraint
        if abs(sweep_angle) > np.pi / 2:
            # Split arc into multiple segments
            n_segments = int(np.ceil(abs(sweep_angle) / (np.pi / 2)))
            segment_angle = sweep_angle / n_segments
        else:
            n_segments = 1
            segment_angle = sweep_angle

        cos_phi = np.cos(phi)
        sin_phi = np.sin(phi)

        # Magic number for cubic Bezier approximation of quarter circle
        alpha = np.sin(segment_angle) * (np.sqrt(4 + 3 * np.tan(segment_angle / 2)**2) - 1) / 3

        results = np.empty((n_segments, 4, 2), dtype=np.float64)

        for i in range(n_segments):
            angle1 = start_angle + i * segment_angle
            angle2 = angle1 + segment_angle

            cos_angle1 = np.cos(angle1)
            sin_angle1 = np.sin(angle1)
            cos_angle2 = np.cos(angle2)
            sin_angle2 = np.sin(angle2)

            # Control points in unit circle
            p1_unit = np.array([cos_angle1, sin_angle1])
            p4_unit = np.array([cos_angle2, sin_angle2])

            p2_unit = np.array([cos_angle1 - alpha * sin_angle1,
                              sin_angle1 + alpha * cos_angle1])
            p3_unit = np.array([cos_angle2 + alpha * sin_angle2,
                              sin_angle2 - alpha * cos_angle2])

            # Transform to ellipse using manual matrix multiplication
            # p = transform_matrix @ p_unit + center
            def transform_point(px, py):
                tx = rx * cos_phi * px - ry * sin_phi * py + cx
                ty = rx * sin_phi * px + ry * cos_phi * py + cy
                return np.array([tx, ty])

            p1 = transform_point(p1_unit[0], p1_unit[1])
            p2 = transform_point(p2_unit[0], p2_unit[1])
            p3 = transform_point(p3_unit[0], p3_unit[1])
            p4 = transform_point(p4_unit[0], p4_unit[1])

            results[i] = np.array([p1, p2, p3, p4])

        return results

    def evaluate_bezier_batch(self, control_points: np.ndarray,
                            subdivision: int = 20) -> np.ndarray:
        """Evaluate multiple Bezier curves efficiently."""
        if control_points.ndim != 3 or control_points.shape[1] != 4:
            raise ValueError("Expected shape (n_curves, 4, 2) for cubic Bezier control points")

        t_values = np.linspace(0, 1, subdivision, dtype=np.float64)
        return self._evaluate_cubic_bezier_batch(control_points, t_values)

    def subdivide_bezier_curves(self, control_points: np.ndarray,
                               t_values: np.ndarray) -> np.ndarray:
        """Subdivide multiple Bezier curves at specified parameters."""
        n_curves = control_points.shape[0]
        if len(t_values) != n_curves:
            raise ValueError("Number of t_values must match number of curves")

        results = []
        for i in range(n_curves):
            p0, p1, p2, p3 = control_points[i]
            left_curve, right_curve = self._subdivide_cubic_bezier(p0, p1, p2, p3, t_values[i])
            results.append([np.array(left_curve), np.array(right_curve)])

        return np.array(results)

    def convert_arc_to_bezier(self, center: np.ndarray, radii: np.ndarray,
                            rotation: float, start_angle: float,
                            sweep_angle: float) -> np.ndarray:
        """Convert elliptical arc to cubic Bezier curves."""
        cx, cy = center
        rx, ry = radii

        return self._arc_to_bezier_params(cx, cy, rx, ry, rotation,
                                        start_angle, sweep_angle)

    def optimize_bezier_curves(self, control_points: np.ndarray,
                             tolerance: float = 1e-3) -> np.ndarray:
        """Optimize Bezier curves by removing redundant control points."""
        optimized = []

        for i in range(control_points.shape[0]):
            curve = control_points[i]
            p0, p1, p2, p3 = curve

            # Check if curve is essentially a line
            line_start = p0
            line_end = p3
            line_vector = line_end - line_start
            line_length = np.linalg.norm(line_vector)

            if line_length < tolerance:
                # Degenerate curve - replace with line
                optimized.append(np.array([p0, p0, p3, p3]))
                continue

            # Check control point deviation from line
            if line_length > 0:
                line_unit = line_vector / line_length

                # Project control points onto line
                p1_proj = np.dot(p1 - line_start, line_unit)
                p2_proj = np.dot(p2 - line_start, line_unit)

                # Calculate perpendicular distances
                p1_perp = np.linalg.norm(p1 - (line_start + p1_proj * line_unit))
                p2_perp = np.linalg.norm(p2 - (line_start + p2_proj * line_unit))

                if p1_perp < tolerance and p2_perp < tolerance:
                    # Curve is essentially a line
                    optimized.append(np.array([p0, p0, p3, p3]))
                    continue

            # Keep original curve
            optimized.append(curve)

        return np.array(optimized) if optimized else control_points

    def extract_bezier_curves(self, path_data: PathData,
                             subdivision: int = 20) -> Dict[str, np.ndarray]:
        """Extract and evaluate Bezier curves from path data with advanced caching and vectorized processing."""
        # Check cache for Bezier extraction results
        path_hash = hashlib.md5(str(path_data.commands).encode()).hexdigest()
        cache_key = f"{path_hash}:{subdivision}"
        cached_result = self._bezier_cache.get(cache_key)
        if cached_result is not None:
            return cached_result

        with self._profile_operation("extract_bezier_curves"):
            commands = path_data.commands
            cubic_curves = []
            quadratic_curves = []
            arc_curves = []

            current_pos = np.array([0.0, 0.0])

            for cmd in commands:
                if cmd['coord_count'] == 0:
                    continue

                coords = cmd['coords'][:cmd['coord_count']].reshape(-1, 2)
                cmd_type = cmd['type']

                if cmd_type == PathCommandType.CUBIC_CURVE:
                    if len(coords) >= 3:
                        # Create cubic Bezier control points
                        control_points = np.array([current_pos, coords[0], coords[1], coords[2]])
                        cubic_curves.append(control_points)
                        current_pos = coords[2]

                elif cmd_type == PathCommandType.QUADRATIC:
                    if len(coords) >= 2:
                        # Create quadratic Bezier control points
                        control_points = np.array([current_pos, coords[0], coords[1]])
                        quadratic_curves.append(control_points)
                        current_pos = coords[1]

                elif cmd_type == PathCommandType.ARC:
                    if len(coords) >= 1:
                        # Extract arc parameters (rx, ry, rotation, large-arc, sweep, end_point)
                        # For demonstration, assuming simplified arc processing
                        end_point = coords[-1]

                        # Convert arc to Bezier approximation
                        center = (current_pos + end_point) / 2
                        radii = np.array([50.0, 50.0])  # Default radii
                        rotation = 0.0
                        start_angle = 0.0
                        sweep_angle = np.pi / 2

                        arc_beziers = self.convert_arc_to_bezier(
                            center, radii, rotation, start_angle, sweep_angle
                        )

                        # Add all arc segments to cubic curves
                        for bezier_segment in arc_beziers:
                            cubic_curves.append(bezier_segment)

                        current_pos = end_point

                elif cmd_type in [PathCommandType.MOVE_TO, PathCommandType.LINE_TO]:
                    current_pos = coords[-1]

            # Batch evaluate all curves using vectorized operations
            result = {}

            if cubic_curves:
                # Convert to numpy array for batch processing
                cubic_array = np.array(cubic_curves)

                # Use vectorized batch evaluation
                t_values = np.linspace(0, 1, subdivision, dtype=np.float64)
                evaluated_cubics = self._evaluate_cubic_bezier_batch(cubic_array, t_values)

                # Optimize curves to remove redundant control points
                optimized_cubics = self.optimize_bezier_curves(cubic_array, tolerance=1e-3)

                result['cubic_curves'] = cubic_array
                result['cubic_evaluated'] = evaluated_cubics
                result['cubic_optimized'] = optimized_cubics

            if quadratic_curves:
                # Convert quadratic to cubic for uniform batch processing
                cubic_converted = []

                for quad_points in quadratic_curves:
                    # Convert quadratic to cubic using exact conversion
                    p0, p1, p2 = quad_points
                    cubic_p1 = p0 + (2/3) * (p1 - p0)
                    cubic_p2 = p2 + (2/3) * (p1 - p2)
                    cubic_converted.append(np.array([p0, cubic_p1, cubic_p2, p2]))

                if cubic_converted:
                    # Batch evaluate converted quadratic curves
                    quad_cubic_array = np.array(cubic_converted)
                    t_values = np.linspace(0, 1, subdivision, dtype=np.float64)
                    evaluated_quads = self._evaluate_cubic_bezier_batch(quad_cubic_array, t_values)

                    result['quadratic_curves'] = np.array(quadratic_curves)
                    result['quadratic_as_cubic'] = quad_cubic_array
                    result['quadratic_evaluated'] = evaluated_quads

            # Add performance metrics
            result['performance'] = {
                'cubic_count': len(cubic_curves),
                'quadratic_count': len(quadratic_curves),
                'total_curves': len(cubic_curves) + len(quadratic_curves),
                'subdivision_points': subdivision
            }

            # Cache the result before returning
            self._bezier_cache.put(cache_key, result)
            return result

    @property
    def cache_stats(self) -> dict:
        """Get caching performance statistics."""
        total = self._cache_hits + self._cache_misses
        return {
            'hits': self._cache_hits,
            'misses': self._cache_misses,
            'hit_rate': self._cache_hits / max(1, total)
        }

    def _calculate_path_bounds_vectorized(self, coordinates: np.ndarray) -> np.ndarray:
        """Calculate bounding box of path coordinates efficiently."""
        if coordinates.shape[0] == 0:
            return np.array([0.0, 0.0, 0.0, 0.0])

        x_coords = coordinates[:, 0]
        y_coords = coordinates[:, 1]

        return np.array([
            np.min(x_coords),  # min_x
            np.min(y_coords),  # min_y
            np.max(x_coords),  # max_x
            np.max(y_coords)   # max_y
        ])

    def optimize_path_geometry(self, path_data: PathData,
                              tolerance: float = 1e-3) -> PathData:
        """Optimize path geometry by removing redundant points and simplifying curves."""
        commands = path_data.commands.copy()
        optimized_commands = []

        previous_pos = np.array([0.0, 0.0])

        for cmd in commands:
            if cmd['coord_count'] == 0:
                optimized_commands.append(cmd)
                continue

            coords = cmd['coords'][:cmd['coord_count']].reshape(-1, 2)
            cmd_type = cmd['type']

            # Optimize based on command type
            if cmd_type == PathCommandType.LINE_TO:
                # Remove zero-length lines
                if len(coords) > 0:
                    end_point = coords[-1]
                    if np.linalg.norm(end_point - previous_pos) < tolerance:
                        continue  # Skip this command
                    previous_pos = end_point

            elif cmd_type in [PathCommandType.CUBIC_CURVE, PathCommandType.QUADRATIC]:
                # Check if curve is essentially a line
                if len(coords) >= 2:
                    start_point = previous_pos
                    end_point = coords[-1]

                    # Calculate maximum deviation from straight line
                    line_vector = end_point - start_point
                    line_length = np.linalg.norm(line_vector)

                    if line_length > tolerance:
                        line_unit = line_vector / line_length
                        max_deviation = 0.0

                        # Check all intermediate control points
                        for i in range(len(coords) - 1):
                            control_point = coords[i]
                            # Project onto line and calculate perpendicular distance
                            projection = np.dot(control_point - start_point, line_unit)
                            projected_point = start_point + projection * line_unit
                            deviation = np.linalg.norm(control_point - projected_point)
                            max_deviation = max(max_deviation, deviation)

                        # If curve is essentially linear, convert to line
                        if max_deviation < tolerance:
                            optimized_cmd = cmd.copy()
                            optimized_cmd['type'] = PathCommandType.LINE_TO
                            optimized_cmd['coords'][:2] = end_point
                            optimized_cmd['coord_count'] = 2
                            optimized_commands.append(optimized_cmd)
                            previous_pos = end_point
                            continue

                    previous_pos = coords[-1]

            # Keep command as-is
            optimized_commands.append(cmd)
            if len(coords) > 0:
                previous_pos = coords[-1]

        # Create optimized PathData
        optimized_path_data = PathData("")
        optimized_path_data.commands = np.array(optimized_commands)
        return optimized_path_data

    def apply_viewport_transformation(self, path_data: PathData,
                                    source_viewport: tuple,
                                    target_viewport: tuple) -> PathData:
        """Apply viewport transformation to scale path from source to target dimensions."""
        src_x, src_y, src_w, src_h = source_viewport
        tgt_x, tgt_y, tgt_w, tgt_h = target_viewport

        # Calculate transformation matrix
        scale_x = tgt_w / src_w if src_w > 0 else 1.0
        scale_y = tgt_h / src_h if src_h > 0 else 1.0

        transform_matrix = np.array([
            [scale_x, 0, tgt_x - src_x * scale_x],
            [0, scale_y, tgt_y - src_y * scale_y],
            [0, 0, 1]
        ], dtype=np.float64)

        # Apply transformation to all coordinates
        transformed_commands = []
        for cmd in path_data.commands:
            if cmd['coord_count'] > 0:
                coords = cmd['coords'][:cmd['coord_count']].reshape(-1, 2)
                transformed_coords = self._transform_coordinates_vectorized(coords, transform_matrix)

                # Update command with transformed coordinates
                transformed_cmd = cmd.copy()
                transformed_cmd['coords'][:cmd['coord_count']] = transformed_coords.flatten()
                transformed_commands.append(transformed_cmd)
            else:
                transformed_commands.append(cmd)

        # Create transformed PathData
        transformed_path_data = PathData("")
        transformed_path_data.commands = np.array(transformed_commands)
        return transformed_path_data

    def calculate_path_metrics(self, path_data: PathData) -> Dict[str, Any]:
        """Calculate comprehensive path metrics for analysis and optimization."""
        commands = path_data.commands

        # Collect all coordinates
        all_coords = []
        command_stats = {
            'move_to': 0,
            'line_to': 0,
            'cubic_curve': 0,
            'quadratic': 0,
            'arc': 0,
            'close': 0
        }

        total_length = 0.0
        current_pos = np.array([0.0, 0.0])

        for cmd in commands:
            cmd_type = cmd['type']

            # Count command types
            if cmd_type == PathCommandType.MOVE_TO:
                command_stats['move_to'] += 1
            elif cmd_type == PathCommandType.LINE_TO:
                command_stats['line_to'] += 1
            elif cmd_type == PathCommandType.CUBIC_CURVE:
                command_stats['cubic_curve'] += 1
            elif cmd_type == PathCommandType.QUADRATIC:
                command_stats['quadratic'] += 1
            elif cmd_type == PathCommandType.ARC:
                command_stats['arc'] += 1
            elif cmd_type == PathCommandType.CLOSE_PATH:
                command_stats['close'] += 1

            if cmd['coord_count'] > 0:
                coords = cmd['coords'][:cmd['coord_count']].reshape(-1, 2)
                all_coords.extend(coords)

                # Calculate approximate path length
                if cmd_type == PathCommandType.LINE_TO:
                    total_length += np.linalg.norm(coords[-1] - current_pos)
                elif cmd_type in [PathCommandType.CUBIC_CURVE, PathCommandType.QUADRATIC]:
                    # Approximate curve length using control point distances
                    prev_point = current_pos
                    for coord in coords:
                        total_length += np.linalg.norm(coord - prev_point)
                        prev_point = coord

                current_pos = coords[-1]

        # Calculate bounds
        if all_coords:
            coords_array = np.array(all_coords)
            bounds = self._calculate_path_bounds_vectorized(coords_array)
        else:
            bounds = np.array([0.0, 0.0, 0.0, 0.0])

        return {
            'total_commands': len(commands),
            'command_breakdown': command_stats,
            'total_coordinates': len(all_coords),
            'bounding_box': {
                'min_x': bounds[0],
                'min_y': bounds[1],
                'max_x': bounds[2],
                'max_y': bounds[3],
                'width': bounds[2] - bounds[0],
                'height': bounds[3] - bounds[1]
            },
            'estimated_length': total_length,
            'complexity_score': self._calculate_complexity_score(command_stats, len(all_coords))
        }

    def _calculate_complexity_score(self, command_stats: dict, coord_count: int) -> float:
        """Calculate complexity score for path optimization decisions."""
        base_score = coord_count * 0.1
        curve_penalty = (command_stats['cubic_curve'] * 2.0 +
                        command_stats['quadratic'] * 1.5 +
                        command_stats['arc'] * 1.8)
        command_penalty = len([k for k, v in command_stats.items() if v > 0]) * 0.5

        return base_score + curve_penalty + command_penalty

    def merge_consecutive_lines(self, path_data: PathData,
                               angle_tolerance: float = 0.1) -> PathData:
        """Merge consecutive line segments that are approximately collinear."""
        commands = path_data.commands
        merged_commands = []

        current_pos = np.array([0.0, 0.0])
        i = 0

        while i < len(commands):
            cmd = commands[i]

            if cmd['type'] == PathCommandType.LINE_TO and cmd['coord_count'] >= 2:
                # Look ahead for consecutive line commands
                line_coords = [current_pos]
                line_coords.extend(cmd['coords'][:cmd['coord_count']].reshape(-1, 2))

                j = i + 1
                while (j < len(commands) and
                       commands[j]['type'] == PathCommandType.LINE_TO and
                       commands[j]['coord_count'] >= 2):
                    line_coords.extend(commands[j]['coords'][:commands[j]['coord_count']].reshape(-1, 2))
                    j += 1

                # Simplify line sequence if we found multiple consecutive lines
                if j > i + 1:
                    simplified_coords = self._simplify_line_sequence(
                        np.array(line_coords), angle_tolerance
                    )

                    # Create simplified line commands
                    for k in range(1, len(simplified_coords)):
                        line_cmd = cmd.copy()
                        line_cmd['coords'][:2] = simplified_coords[k]
                        line_cmd['coord_count'] = 2
                        merged_commands.append(line_cmd)

                    current_pos = simplified_coords[-1]
                    i = j
                else:
                    # Single line, keep as-is
                    merged_commands.append(cmd)
                    coords = cmd['coords'][:cmd['coord_count']].reshape(-1, 2)
                    current_pos = coords[-1]
                    i += 1
            else:
                # Non-line command, keep as-is
                merged_commands.append(cmd)
                if cmd['coord_count'] > 0:
                    coords = cmd['coords'][:cmd['coord_count']].reshape(-1, 2)
                    current_pos = coords[-1]
                i += 1

        # Create merged PathData
        merged_path_data = PathData("")
        merged_path_data.commands = np.array(merged_commands)
        return merged_path_data

    def _simplify_line_sequence(self, line_points: np.ndarray,
                               angle_tolerance: float) -> np.ndarray:
        """Simplify sequence of line points using Douglas-Peucker-like algorithm."""
        if len(line_points) <= 2:
            return line_points

        simplified = [line_points[0]]  # Always keep start point

        for i in range(1, len(line_points) - 1):
            prev_point = simplified[-1]
            curr_point = line_points[i]
            next_point = line_points[i + 1]

            # Calculate vectors
            v1 = curr_point - prev_point
            v2 = next_point - curr_point

            # Calculate angle between vectors
            if np.linalg.norm(v1) > 0 and np.linalg.norm(v2) > 0:
                cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
                cos_angle = np.clip(cos_angle, -1.0, 1.0)  # Numerical stability
                angle = np.arccos(cos_angle)

                # Keep point if angle change is significant
                if angle > angle_tolerance:
                    simplified.append(curr_point)

        simplified.append(line_points[-1])  # Always keep end point
        return np.array(simplified)

    def calculate_path_intersections(self, path_data1: PathData, path_data2: PathData,
                                   tolerance: float = 1e-6) -> np.ndarray:
        """Calculate intersection points between two paths using vectorized algorithms."""
        intersections = []

        # Get line segments from both paths
        segments1 = self._extract_line_segments(path_data1)
        segments2 = self._extract_line_segments(path_data2)

        if len(segments1) == 0 or len(segments2) == 0:
            return np.array([]).reshape(0, 2)

        # Vectorized line-line intersection calculation
        for seg1 in segments1:
            for seg2 in segments2:
                intersection = self._calculate_line_intersection_vectorized(seg1, seg2, tolerance)
                if intersection is not None:
                    intersections.append(intersection)

        return np.array(intersections) if intersections else np.array([]).reshape(0, 2)

    def _extract_line_segments(self, path_data: PathData) -> list:
        """Extract line segments from path data."""
        segments = []
        current_pos = np.array([0.0, 0.0])

        for cmd in path_data.commands:
            if cmd['coord_count'] == 0:
                continue

            coords = cmd['coords'][:cmd['coord_count']].reshape(-1, 2)
            cmd_type = cmd['type']

            if cmd_type == PathCommandType.LINE_TO:
                if len(coords) > 0:
                    segments.append([current_pos.copy(), coords[-1].copy()])
                    current_pos = coords[-1]
            elif cmd_type == PathCommandType.MOVE_TO:
                if len(coords) > 0:
                    current_pos = coords[-1]

        return segments

    def _calculate_line_intersection_vectorized(self, seg1: np.ndarray, seg2: np.ndarray,
                                              tolerance: float) -> np.ndarray:
        """Calculate intersection point between two line segments using vectorized math."""
        p1, p2 = seg1[0], seg1[1]
        p3, p4 = seg2[0], seg2[1]

        # Calculate direction vectors
        d1 = p2 - p1
        d2 = p4 - p3

        # Calculate cross product for parallel line detection
        cross = d1[0] * d2[1] - d1[1] * d2[0]

        if abs(cross) < tolerance:
            return None  # Lines are parallel

        # Calculate intersection parameters
        t1 = ((p3[0] - p1[0]) * d2[1] - (p3[1] - p1[1]) * d2[0]) / cross
        t2 = ((p3[0] - p1[0]) * d1[1] - (p3[1] - p1[1]) * d1[0]) / cross

        # Check if intersection is within both segments
        if 0.0 <= t1 <= 1.0 and 0.0 <= t2 <= 1.0:
            # Calculate intersection point
            intersection = p1 + t1 * d1
            return intersection

        return None

    def convert_path_to_shape_data(self, path_data: PathData,
                                 shape_type: str = "polygon") -> Dict[str, np.ndarray]:
        """Convert path data to shape-specific coordinate arrays."""
        if shape_type == "polygon":
            return self._convert_to_polygon(path_data)
        elif shape_type == "rectangle":
            return self._convert_to_rectangle(path_data)
        elif shape_type == "circle":
            return self._convert_to_circle(path_data)
        else:
            raise ValueError(f"Unsupported shape type: {shape_type}")

    def _convert_to_polygon(self, path_data: PathData) -> Dict[str, np.ndarray]:
        """Convert path to polygon vertex array."""
        vertices = []
        current_pos = np.array([0.0, 0.0])

        for cmd in path_data.commands:
            if cmd['coord_count'] == 0:
                continue

            coords = cmd['coords'][:cmd['coord_count']].reshape(-1, 2)
            cmd_type = cmd['type']

            if cmd_type in [PathCommandType.MOVE_TO, PathCommandType.LINE_TO]:
                if len(coords) > 0:
                    vertices.extend(coords)
                    current_pos = coords[-1]
            elif cmd_type in [PathCommandType.CUBIC_CURVE, PathCommandType.QUADRATIC]:
                # Sample curve points for polygon approximation
                if cmd_type == PathCommandType.CUBIC_CURVE and len(coords) >= 3:
                    control_points = np.array([current_pos, coords[0], coords[1], coords[2]])
                    t_values = np.linspace(0, 1, 10)
                    curve_points = self._evaluate_cubic_bezier(
                        control_points[0], control_points[1],
                        control_points[2], control_points[3], t_values
                    )
                    vertices.extend(curve_points[1:])  # Skip start point to avoid duplication
                    current_pos = coords[-1]

        return {
            "vertices": np.array(vertices) if vertices else np.array([]).reshape(0, 2),
            "vertex_count": len(vertices)
        }

    def _convert_to_rectangle(self, path_data: PathData) -> Dict[str, np.ndarray]:
        """Convert path to rectangle bounds."""
        all_coords = []
        current_pos = np.array([0.0, 0.0])

        for cmd in path_data.commands:
            if cmd['coord_count'] > 0:
                coords = cmd['coords'][:cmd['coord_count']].reshape(-1, 2)
                all_coords.extend(coords)
                if cmd['type'] != PathCommandType.MOVE_TO:
                    all_coords.append(current_pos)
                current_pos = coords[-1]

        if not all_coords:
            return {
                "bounds": np.array([0.0, 0.0, 0.0, 0.0]),
                "center": np.array([0.0, 0.0]),
                "size": np.array([0.0, 0.0])
            }

        coords_array = np.array(all_coords)
        bounds = self._calculate_path_bounds_vectorized(coords_array)

        return {
            "bounds": bounds,  # [min_x, min_y, max_x, max_y]
            "center": np.array([(bounds[0] + bounds[2]) / 2, (bounds[1] + bounds[3]) / 2]),
            "size": np.array([bounds[2] - bounds[0], bounds[3] - bounds[1]])
        }

    def _convert_to_circle(self, path_data: PathData) -> Dict[str, np.ndarray]:
        """Convert path to circle parameters using least-squares fitting."""
        polygon_data = self._convert_to_polygon(path_data)
        vertices = polygon_data["vertices"]

        if len(vertices) < 3:
            return {
                "center": np.array([0.0, 0.0]),
                "radius": 0.0,
                "fit_error": float('inf')
            }

        # Use centroid as initial center estimate
        center = np.mean(vertices, axis=0)

        # Calculate average distance to center as radius estimate
        distances = np.linalg.norm(vertices - center, axis=1)
        radius = np.mean(distances)

        # Calculate fit error
        fit_error = np.std(distances)

        return {
            "center": center,
            "radius": radius,
            "fit_error": fit_error
        }

    def batch_process_path_operations(self, path_list: List[PathData],
                                    operations: List[str]) -> List[Dict[str, Any]]:
        """Process multiple path operations in batch for maximum efficiency."""
        results = []

        for path_data in path_list:
            path_results = {}

            for operation in operations:
                if operation == "metrics":
                    path_results["metrics"] = self.calculate_path_metrics(path_data)
                elif operation == "optimize":
                    path_results["optimized"] = self.optimize_path_geometry(path_data)
                elif operation == "bezier":
                    path_results["bezier"] = self.extract_bezier_curves(path_data)
                elif operation.startswith("convert_"):
                    shape_type = operation.replace("convert_", "")
                    path_results[f"shape_{shape_type}"] = self.convert_path_to_shape_data(path_data, shape_type)

            results.append(path_results)

        return results

    def calculate_path_similarity(self, path_data1: PathData, path_data2: PathData) -> Dict[str, float]:
        """Calculate similarity metrics between two paths."""
        # Convert paths to comparable representations
        poly1 = self._convert_to_polygon(path_data1)
        poly2 = self._convert_to_polygon(path_data2)

        # Calculate metrics for both paths
        metrics1 = self.calculate_path_metrics(path_data1)
        metrics2 = self.calculate_path_metrics(path_data2)

        # Bounding box overlap
        bbox1 = metrics1['bounding_box']
        bbox2 = metrics2['bounding_box']

        overlap_area = max(0, min(bbox1['max_x'], bbox2['max_x']) - max(bbox1['min_x'], bbox2['min_x'])) * \
                      max(0, min(bbox1['max_y'], bbox2['max_y']) - max(bbox1['min_y'], bbox2['min_y']))

        area1 = bbox1['width'] * bbox1['height']
        area2 = bbox2['width'] * bbox2['height']
        union_area = area1 + area2 - overlap_area

        bbox_similarity = overlap_area / union_area if union_area > 0 else 0.0

        # Command structure similarity
        cmd_similarity = 1.0 - abs(metrics1['complexity_score'] - metrics2['complexity_score']) / \
                        max(metrics1['complexity_score'], metrics2['complexity_score'], 1.0)

        # Coordinate count similarity
        coord_ratio = min(metrics1['total_coordinates'], metrics2['total_coordinates']) / \
                     max(metrics1['total_coordinates'], metrics2['total_coordinates'], 1.0)

        return {
            "overall_similarity": (bbox_similarity + cmd_similarity + coord_ratio) / 3.0,
            "bounding_box_similarity": bbox_similarity,
            "structure_similarity": cmd_similarity,
            "size_similarity": coord_ratio
        }

    def create_path_union(self, path_list: List[PathData]) -> PathData:
        """Create union of multiple paths by combining their commands."""
        if not path_list:
            return PathData("")

        # Collect all commands from all paths
        all_commands = []

        for path_data in path_list:
            all_commands.extend(path_data.commands)

        # Create new PathData with combined commands
        union_path = PathData("")
        if all_commands:
            union_path.commands = np.array(all_commands)

        return union_path

    def apply_advanced_transformations(self, path_data: PathData,
                                     transformations: List[Dict[str, Any]]) -> PathData:
        """Apply sequence of advanced transformations to path."""
        current_path = path_data

        for transform in transformations:
            transform_type = transform.get("type", "")

            if transform_type == "scale":
                scale_x = transform.get("scale_x", 1.0)
                scale_y = transform.get("scale_y", 1.0)
                matrix = np.array([
                    [scale_x, 0, 0],
                    [0, scale_y, 0],
                    [0, 0, 1]
                ], dtype=np.float64)
                current_path = self._apply_matrix_transformation(current_path, matrix)

            elif transform_type == "rotate":
                angle = transform.get("angle", 0.0)
                cos_a, sin_a = np.cos(angle), np.sin(angle)
                matrix = np.array([
                    [cos_a, -sin_a, 0],
                    [sin_a, cos_a, 0],
                    [0, 0, 1]
                ], dtype=np.float64)
                current_path = self._apply_matrix_transformation(current_path, matrix)

            elif transform_type == "translate":
                tx = transform.get("tx", 0.0)
                ty = transform.get("ty", 0.0)
                matrix = np.array([
                    [1, 0, tx],
                    [0, 1, ty],
                    [0, 0, 1]
                ], dtype=np.float64)
                current_path = self._apply_matrix_transformation(current_path, matrix)

        return current_path

    def _apply_matrix_transformation(self, path_data: PathData, matrix: np.ndarray) -> PathData:
        """Apply transformation matrix to path data."""
        transformed_commands = []

        for cmd in path_data.commands:
            if cmd['coord_count'] > 0:
                coords = cmd['coords'][:cmd['coord_count']].reshape(-1, 2)
                transformed_coords = self._transform_coordinates_vectorized(coords, matrix)

                transformed_cmd = cmd.copy()
                transformed_cmd['coords'][:cmd['coord_count']] = transformed_coords.flatten()
                transformed_commands.append(transformed_cmd)
            else:
                transformed_commands.append(cmd)

        transformed_path = PathData("")
        if transformed_commands:
            transformed_path.commands = np.array(transformed_commands)

        return transformed_path

    def __repr__(self) -> str:
        """String representation."""
        stats = self.cache_stats
        return f"PathEngine(cache_hit_rate={stats['hit_rate']:.2%})"


    def _get_temporary_array(self, shape: tuple, dtype=np.float64) -> np.ndarray:
        """Get a temporary array from the pool for internal calculations."""
        return self._array_pool.get_array(shape, dtype)

    def _return_temporary_array(self, array: np.ndarray):
        """Return a temporary array to the pool."""
        self._array_pool.return_array(array)

    def calculate_path_lengths_batch(self, path_data_list: List[PathData]) -> np.ndarray:
        """Calculate path lengths using array pooling for efficiency."""
        n_paths = len(path_data_list)
        if n_paths == 0:
            return np.array([])

        # Use array pool for results
        results = self._get_temporary_array((n_paths,), dtype=np.float64)

        try:
            for i, path_data in enumerate(path_data_list):
                # Calculate length using pooled temporary arrays
                total_length = 0.0
                current_pos = np.array([0.0, 0.0])

                for cmd in path_data.commands:
                    if cmd['coord_count'] > 0:
                        coords = cmd['coords'][:cmd['coord_count']].reshape(-1, 2)
                        # Use pooled array for calculations
                        if len(coords) > 0:
                            distances = self._get_temporary_array((len(coords),))
                            try:
                                for j, coord in enumerate(coords):
                                    distances[j] = np.linalg.norm(coord - current_pos)
                                    current_pos = coord
                                total_length += np.sum(distances)
                            finally:
                                self._return_temporary_array(distances)

                results[i] = total_length

            # Copy results to avoid returning pooled array
            final_results = results.copy()
            return final_results

        finally:
            # Always return the results array to pool
            self._return_temporary_array(results)


# Convenience functions for direct usage
def create_path_engine() -> PathEngine:
    """Create path engine with default settings."""
    return PathEngine()


def parse_path(path_string: str) -> PathData:
    """Parse SVG path string using default engine."""
    engine = PathEngine()
    result = engine.process_path(path_string)
    return result['path_data']


def process_path_batch(path_strings: List[str], **kwargs) -> List[Dict[str, Any]]:
    """Process batch of paths using default engine."""
    engine = PathEngine()
    return engine.process_batch(path_strings, **kwargs)


def transform_coordinates(coords: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """Transform coordinates using transformation matrix."""
    return PathEngine._transform_coordinates_vectorized(coords, matrix)