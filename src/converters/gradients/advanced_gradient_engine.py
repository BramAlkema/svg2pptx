#!/usr/bin/env python3
"""
Advanced Gradient Features Engine for SVG2PPTX

Implements advanced gradient processing capabilities including:
- Batch gradient transformations with coordinate system conversions
- Multi-color space support (RGB, HSL, LAB) with vectorized conversions
- Gradient optimization and intelligent caching system
- Advanced interpolation techniques (cubic, hermite splines)
- Gradient quality enhancement and adaptive sampling

Features:
- Vectorized color space conversions using pre-computed matrices
- LRU caching with memory-efficient gradient storage
- Batch transformation pipeline with coordinate normalization
- Advanced interpolation methods for smooth color transitions
- Gradient compression and optimization algorithms

Performance Targets:
- Color space conversions: >2M operations/second
- Batch transformations: >50,000 gradients/second
- Cache hit ratio: >85% for typical workloads
- Memory efficiency: 60-80% reduction vs unoptimized

Example Usage:
    >>> engine = AdvancedGradientEngine()
    >>> gradients = engine.optimize_gradients_batch(gradient_data)
    >>> transformed = engine.apply_transformations_batch(gradients, transforms)
    >>> lab_colors = engine.convert_colorspace_batch(rgb_colors, 'RGB', 'LAB')
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple, Union, Literal
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import time
import warnings
from collections import OrderedDict
import json

try:
    from .core import ColorProcessor, TransformProcessor
    from .linear_gradient_engine import LinearGradientEngine, LinearGradientData
    from .radial_gradient_engine import RadialGradientEngine, RadialGradientData
except ImportError:
    # For direct testing, create stub classes
    class ColorProcessor:
        def parse_color_single(self, color_str):
            return np.array([0.0, 0.0, 0.0])
        def rgb_to_lab_single(self, rgb):
            return rgb
        def lab_to_rgb_batch(self, lab):
            return lab

    class TransformProcessor:
        def apply_transform_batch(self, points, transforms):
            return points

    class LinearGradientEngine:
        pass
    class LinearGradientData:
        pass
    class RadialGradientEngine:
        pass
    class RadialGradientData:
        pass


class ColorSpace(Enum):
    """Supported color spaces for gradient processing"""
    RGB = "rgb"
    HSL = "hsl"
    LAB = "lab"
    XYZ = "xyz"
    LCH = "lch"  # Polar LAB


class InterpolationMethod(Enum):
    """Advanced interpolation methods for gradients"""
    LINEAR = "linear"
    CUBIC = "cubic"
    HERMITE = "hermite"
    CATMULL_ROM = "catmull_rom"
    BEZIER = "bezier"


@dataclass
class OptimizedGradientData:
    """Optimized gradient data structure with caching metadata"""
    gradient_id: str
    gradient_type: str  # 'linear' or 'radial'
    coordinates: np.ndarray
    stops: np.ndarray
    transform_matrix: np.ndarray
    color_space: ColorSpace = ColorSpace.RGB
    interpolation_method: InterpolationMethod = InterpolationMethod.LINEAR
    optimization_level: int = 1  # 0=none, 1=basic, 2=advanced
    cache_key: Optional[str] = None
    quality_score: float = 1.0
    compression_ratio: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TransformationBatch:
    """Batch transformation configuration"""
    transforms: np.ndarray  # (N, 6) transform matrices
    coordinate_systems: np.ndarray  # Source coordinate systems
    target_coordinate_system: str = "objectBoundingBox"
    viewport_dimensions: Optional[Tuple[float, float]] = None
    normalization_factors: Optional[np.ndarray] = None


class GradientCache:
    """High-performance LRU cache for gradient operations"""

    def __init__(self, max_size: int = 1000, memory_limit_mb: int = 100):
        self.max_size = max_size
        self.memory_limit_bytes = memory_limit_mb * 1024 * 1024
        self.cache = OrderedDict()
        self.memory_usage = 0
        self.hits = 0
        self.misses = 0

    def _estimate_size(self, data: Any) -> int:
        """Estimate memory usage of cached data"""
        if isinstance(data, np.ndarray):
            return data.nbytes
        elif isinstance(data, (list, tuple)):
            return sum(self._estimate_size(item) for item in data)
        elif isinstance(data, dict):
            return sum(self._estimate_size(v) for v in data.values())
        else:
            return 64  # Default estimate

    def get(self, key: str) -> Optional[Any]:
        """Retrieve cached item"""
        if key in self.cache:
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            self.hits += 1
            return self.cache[key]
        self.misses += 1
        return None

    def put(self, key: str, value: Any):
        """Store item in cache with memory management"""
        value_size = self._estimate_size(value)

        # Check if value is too large
        if value_size > self.memory_limit_bytes // 2:
            return  # Don't cache extremely large values

        # Remove old entries if necessary
        while (len(self.cache) >= self.max_size or
               self.memory_usage + value_size > self.memory_limit_bytes):
            if not self.cache:
                break
            old_key, old_value = self.cache.popitem(last=False)
            self.memory_usage -= self._estimate_size(old_value)

        # Add new entry
        self.cache[key] = value
        self.memory_usage += value_size

    def get_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        total_requests = self.hits + self.misses
        hit_rate = self.hits / total_requests if total_requests > 0 else 0.0

        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'memory_usage_mb': self.memory_usage / (1024 * 1024),
            'memory_limit_mb': self.memory_limit_bytes / (1024 * 1024),
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': hit_rate,
            'total_requests': total_requests
        }

    def clear(self):
        """Clear cache"""
        self.cache.clear()
        self.memory_usage = 0
        self.hits = 0
        self.misses = 0


class AdvancedGradientEngine:
    """
    Advanced gradient processing engine with optimization and caching.

    Provides batch transformations, multi-color space support, and
    intelligent caching for high-performance gradient operations.
    """

    def __init__(self, cache_size: int = 1000, memory_limit_mb: int = 100):
        """Initialize advanced gradient engine"""
        self.color_processor = ColorProcessor()
        self.transform_processor = TransformProcessor()
        self.linear_engine = LinearGradientEngine()
        self.radial_engine = RadialGradientEngine()

        # Caching system
        self.cache = GradientCache(cache_size, memory_limit_mb)

        # Color space conversion matrices (sRGB to XYZ)
        self.rgb_to_xyz_matrix = np.array([
            [0.4124564, 0.3575761, 0.1804375],
            [0.2126729, 0.7151522, 0.0721750],
            [0.0193339, 0.1191920, 0.9503041]
        ], dtype=np.float64)

        self.xyz_to_rgb_matrix = np.linalg.inv(self.rgb_to_xyz_matrix)

        # LAB conversion constants
        self.xyz_white_point = np.array([0.95047, 1.00000, 1.08883], dtype=np.float64)
        self.lab_epsilon = 216.0 / 24389.0
        self.lab_kappa = 24389.0 / 27.0

        # Performance optimization settings
        self.vectorization_threshold = 100  # Minimum batch size for vectorization
        self.interpolation_quality = 8  # Interpolation samples per gradient segment

    def convert_colorspace_batch(self, colors: np.ndarray,
                                source_space: Union[str, ColorSpace],
                                target_space: Union[str, ColorSpace]) -> np.ndarray:
        """
        Convert colors between different color spaces using vectorized operations.

        Args:
            colors: (N, 3) array of colors in source color space
            source_space: Source color space ('RGB', 'HSL', 'LAB', 'XYZ')
            target_space: Target color space ('RGB', 'HSL', 'LAB', 'XYZ')

        Returns:
            np.ndarray: (N, 3) array of colors in target color space
        """
        if isinstance(source_space, str):
            source_space = ColorSpace(source_space.lower())
        if isinstance(target_space, str):
            target_space = ColorSpace(target_space.lower())

        if source_space == target_space:
            return colors.copy()

        # Generate cache key
        cache_key = f"colorconv_{source_space.value}_{target_space.value}_{colors.shape}_{hash(colors.tobytes())}"
        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            return cached_result

        # Conversion pipeline
        if source_space == ColorSpace.RGB and target_space == ColorSpace.LAB:
            result = self._rgb_to_lab_batch(colors)
        elif source_space == ColorSpace.LAB and target_space == ColorSpace.RGB:
            result = self._lab_to_rgb_batch(colors)
        elif source_space == ColorSpace.RGB and target_space == ColorSpace.HSL:
            result = self._rgb_to_hsl_batch(colors)
        elif source_space == ColorSpace.HSL and target_space == ColorSpace.RGB:
            result = self._hsl_to_rgb_batch(colors)
        elif source_space == ColorSpace.RGB and target_space == ColorSpace.XYZ:
            result = self._rgb_to_xyz_batch(colors)
        elif source_space == ColorSpace.XYZ and target_space == ColorSpace.RGB:
            result = self._xyz_to_rgb_batch(colors)
        else:
            # Multi-step conversion via RGB
            if source_space != ColorSpace.RGB:
                colors = self.convert_colorspace_batch(colors, source_space, ColorSpace.RGB)
            if target_space != ColorSpace.RGB:
                colors = self.convert_colorspace_batch(colors, ColorSpace.RGB, target_space)
            result = colors

        # Cache result if reasonable size
        if result.nbytes < 1024 * 1024:  # 1MB limit
            self.cache.put(cache_key, result)

        return result

    def _rgb_to_xyz_batch(self, rgb: np.ndarray) -> np.ndarray:
        """Convert RGB to XYZ color space"""
        # Gamma correction
        rgb_linear = np.where(rgb > 0.04045,
                             np.power((rgb + 0.055) / 1.055, 2.4),
                             rgb / 12.92)

        # Apply transformation matrix
        xyz = np.dot(rgb_linear, self.rgb_to_xyz_matrix.T)
        return xyz

    def _xyz_to_rgb_batch(self, xyz: np.ndarray) -> np.ndarray:
        """Convert XYZ to RGB color space"""
        # Apply transformation matrix
        rgb_linear = np.dot(xyz, self.xyz_to_rgb_matrix.T)

        # Gamma correction
        rgb = np.where(rgb_linear > 0.0031308,
                      1.055 * np.power(rgb_linear, 1.0 / 2.4) - 0.055,
                      12.92 * rgb_linear)

        return np.clip(rgb, 0.0, 1.0)

    def _rgb_to_lab_batch(self, rgb: np.ndarray) -> np.ndarray:
        """Convert RGB to LAB color space"""
        # RGB -> XYZ
        xyz = self._rgb_to_xyz_batch(rgb)

        # Normalize by white point
        xyz_normalized = xyz / self.xyz_white_point

        # Apply LAB transformation
        f_xyz = np.where(xyz_normalized > self.lab_epsilon,
                        np.power(xyz_normalized, 1.0 / 3.0),
                        (self.lab_kappa * xyz_normalized + 16.0) / 116.0)

        L = 116.0 * f_xyz[:, 1] - 16.0
        a = 500.0 * (f_xyz[:, 0] - f_xyz[:, 1])
        b = 200.0 * (f_xyz[:, 1] - f_xyz[:, 2])

        return np.column_stack([L, a, b])

    def _lab_to_rgb_batch(self, lab: np.ndarray) -> np.ndarray:
        """Convert LAB to RGB color space"""
        L, a, b = lab[:, 0], lab[:, 1], lab[:, 2]

        # Convert to XYZ
        fy = (L + 16.0) / 116.0
        fx = a / 500.0 + fy
        fz = fy - b / 200.0

        xyz = np.column_stack([
            np.where(np.power(fx, 3) > self.lab_epsilon, np.power(fx, 3), (116.0 * fx - 16.0) / self.lab_kappa),
            np.where(L > self.lab_kappa * self.lab_epsilon, np.power((L + 16.0) / 116.0, 3), L / self.lab_kappa),
            np.where(np.power(fz, 3) > self.lab_epsilon, np.power(fz, 3), (116.0 * fz - 16.0) / self.lab_kappa)
        ])

        # Denormalize by white point
        xyz *= self.xyz_white_point

        # XYZ -> RGB
        return self._xyz_to_rgb_batch(xyz)

    def _rgb_to_hsl_batch(self, rgb: np.ndarray) -> np.ndarray:
        """Convert RGB to HSL color space"""
        r, g, b = rgb[:, 0], rgb[:, 1], rgb[:, 2]

        max_val = np.maximum(np.maximum(r, g), b)
        min_val = np.minimum(np.minimum(r, g), b)
        diff = max_val - min_val

        # Lightness
        l = (max_val + min_val) / 2.0

        # Saturation
        s = np.where(diff == 0, 0,
                    np.where(l < 0.5, diff / (max_val + min_val),
                            diff / (2.0 - max_val - min_val)))

        # Hue
        h = np.zeros_like(l)
        mask = diff != 0

        # Red maximum
        red_max = mask & (max_val == r)
        h[red_max] = (60 * ((g[red_max] - b[red_max]) / diff[red_max]) + 360) % 360

        # Green maximum
        green_max = mask & (max_val == g)
        h[green_max] = 60 * ((b[green_max] - r[green_max]) / diff[green_max]) + 120

        # Blue maximum
        blue_max = mask & (max_val == b)
        h[blue_max] = 60 * ((r[blue_max] - g[blue_max]) / diff[blue_max]) + 240

        return np.column_stack([h / 360.0, s, l])  # Normalize hue to [0,1]

    def _hsl_to_rgb_batch(self, hsl: np.ndarray) -> np.ndarray:
        """Convert HSL to RGB color space"""
        h, s, l = hsl[:, 0] * 360, hsl[:, 1], hsl[:, 2]  # Denormalize hue

        def hue_to_rgb(p, q, t):
            t = np.where(t < 0, t + 1, t)
            t = np.where(t > 1, t - 1, t)
            return np.where(t < 1/6, p + (q - p) * 6 * t,
                          np.where(t < 1/2, q,
                                  np.where(t < 2/3, p + (q - p) * (2/3 - t) * 6, p)))

        q = np.where(l < 0.5, l * (1 + s), l + s - l * s)
        p = 2 * l - q

        h_norm = h / 360.0
        r = hue_to_rgb(p, q, h_norm + 1/3)
        g = hue_to_rgb(p, q, h_norm)
        b = hue_to_rgb(p, q, h_norm - 1/3)

        return np.column_stack([r, g, b])

    def apply_transformations_batch(self, gradient_data: List[OptimizedGradientData],
                                  transformation_batch: TransformationBatch) -> List[OptimizedGradientData]:
        """
        Apply batch transformations to multiple gradients.

        Args:
            gradient_data: List of optimized gradient data
            transformation_batch: Batch transformation configuration

        Returns:
            List[OptimizedGradientData]: Transformed gradients
        """
        if len(gradient_data) != len(transformation_batch.transforms):
            raise ValueError("Gradient data and transform count must match")

        transformed_gradients = []

        # Batch coordinate transformation
        for i, (gradient, transform) in enumerate(zip(gradient_data, transformation_batch.transforms)):
            cache_key = f"transform_{gradient.cache_key}_{hash(transform.tobytes())}"
            cached_result = self.cache.get(cache_key)

            if cached_result is not None:
                transformed_gradients.append(cached_result)
                continue

            # Apply transformation based on gradient type
            if gradient.gradient_type == 'linear':
                transformed_coords = self._transform_linear_coordinates(gradient.coordinates, transform)
            elif gradient.gradient_type == 'radial':
                transformed_coords = self._transform_radial_coordinates(gradient.coordinates, transform)
            else:
                transformed_coords = gradient.coordinates.copy()

            # Create transformed gradient
            transformed = OptimizedGradientData(
                gradient_id=f"{gradient.gradient_id}_transformed",
                gradient_type=gradient.gradient_type,
                coordinates=transformed_coords,
                stops=gradient.stops.copy(),
                transform_matrix=transform,
                color_space=gradient.color_space,
                interpolation_method=gradient.interpolation_method,
                optimization_level=gradient.optimization_level,
                cache_key=cache_key,
                quality_score=gradient.quality_score,
                compression_ratio=gradient.compression_ratio,
                metadata=gradient.metadata.copy()
            )

            self.cache.put(cache_key, transformed)
            transformed_gradients.append(transformed)

        return transformed_gradients

    def _transform_linear_coordinates(self, coords: np.ndarray, transform: np.ndarray) -> np.ndarray:
        """Transform linear gradient coordinates"""
        x1, y1, x2, y2 = coords
        points = np.array([[x1, y1], [x2, y2]])

        # Apply transformation matrix
        a, b, c, d, e, f = transform
        transform_matrix = np.array([[a, c, e], [b, d, f], [0, 0, 1]])

        # Transform points
        homogeneous_points = np.column_stack([points, np.ones(2)])
        transformed_points = (transform_matrix @ homogeneous_points.T).T
        transformed_points = transformed_points[:, :2] / transformed_points[:, 2:3]

        return np.array([transformed_points[0, 0], transformed_points[0, 1],
                        transformed_points[1, 0], transformed_points[1, 1]])

    def _transform_radial_coordinates(self, coords: np.ndarray, transform: np.ndarray) -> np.ndarray:
        """Transform radial gradient coordinates"""
        if len(coords) == 5:
            cx, cy, r, fx, fy = coords
            focal_offset = np.array([fx - cx, fy - cy])
        else:
            cx, cy, r = coords[:3]
            focal_offset = np.array([0.0, 0.0])

        # Transform center and focal point
        center = np.array([[cx, cy]])
        a, b, c, d, e, f = transform
        transform_matrix = np.array([[a, c, e], [b, d, f], [0, 0, 1]])

        # Transform center
        homogeneous_center = np.array([[cx, cy, 1.0]])
        transformed_center = (transform_matrix @ homogeneous_center.T).T
        transformed_center = transformed_center[:, :2] / transformed_center[:, 2:3]

        # Transform radius (scale factor)
        scale_x = np.sqrt(a*a + b*b)
        scale_y = np.sqrt(c*c + d*d)
        avg_scale = (scale_x + scale_y) / 2.0
        transformed_r = r * avg_scale

        # Transform focal point if exists
        if len(coords) == 5:
            focal = center + focal_offset.reshape(1, -1)
            homogeneous_focal = np.column_stack([focal, np.ones(1)])
            transformed_focal = (transform_matrix @ homogeneous_focal.T).T
            transformed_focal = transformed_focal[:, :2] / transformed_focal[:, 2:3]

            return np.array([transformed_center[0, 0], transformed_center[0, 1], transformed_r,
                           transformed_focal[0, 0], transformed_focal[0, 1]])
        else:
            return np.array([transformed_center[0, 0], transformed_center[0, 1], transformed_r])

    def optimize_gradients_batch(self, gradients: List[OptimizedGradientData],
                               optimization_level: int = 2) -> List[OptimizedGradientData]:
        """
        Optimize gradients for performance and quality.

        Args:
            gradients: List of gradients to optimize
            optimization_level: 0=none, 1=basic, 2=advanced

        Returns:
            List[OptimizedGradientData]: Optimized gradients
        """
        optimized = []

        for gradient in gradients:
            cache_key = f"optimize_{gradient.cache_key}_{optimization_level}"
            cached_result = self.cache.get(cache_key)

            if cached_result is not None:
                optimized.append(cached_result)
                continue

            if optimization_level == 0:
                optimized.append(gradient)
                continue

            # Basic optimization
            optimized_stops = self._optimize_gradient_stops(gradient.stops, optimization_level)
            quality_score = self._calculate_quality_score(gradient, optimized_stops)
            compression_ratio = len(gradient.stops) / len(optimized_stops) if len(optimized_stops) > 0 else 1.0

            optimized_gradient = OptimizedGradientData(
                gradient_id=f"{gradient.gradient_id}_opt{optimization_level}",
                gradient_type=gradient.gradient_type,
                coordinates=gradient.coordinates.copy(),
                stops=optimized_stops,
                transform_matrix=gradient.transform_matrix.copy() if gradient.transform_matrix is not None else None,
                color_space=gradient.color_space,
                interpolation_method=gradient.interpolation_method,
                optimization_level=optimization_level,
                cache_key=cache_key,
                quality_score=quality_score,
                compression_ratio=compression_ratio,
                metadata={**gradient.metadata, 'original_stops': len(gradient.stops)}
            )

            self.cache.put(cache_key, optimized_gradient)
            optimized.append(optimized_gradient)

        return optimized

    def _optimize_gradient_stops(self, stops: np.ndarray, level: int) -> np.ndarray:
        """Optimize gradient stops by removing redundant entries"""
        if len(stops) <= 2:
            return stops

        if level == 1:  # Basic optimization
            # Remove stops that are very close in position
            unique_indices = [0]
            for i in range(1, len(stops)):
                if stops[i, 0] - stops[unique_indices[-1], 0] > 0.01:  # 1% threshold
                    unique_indices.append(i)

            # Always include last stop
            if unique_indices[-1] != len(stops) - 1:
                unique_indices.append(len(stops) - 1)

            return stops[unique_indices]

        elif level == 2:  # Advanced optimization
            # Analyze color gradients and remove unnecessary intermediate stops
            optimized_stops = [stops[0]]  # Always keep first

            for i in range(1, len(stops) - 1):
                # Check if this stop is necessary for color interpolation
                prev_stop = optimized_stops[-1]
                curr_stop = stops[i]
                next_stop = stops[i + 1]

                # Calculate expected interpolated color at current position
                t = (curr_stop[0] - prev_stop[0]) / (next_stop[0] - prev_stop[0])
                expected_color = prev_stop[1:4] + t * (next_stop[1:4] - prev_stop[1:4])

                # Compare with actual color
                color_diff = np.linalg.norm(expected_color - curr_stop[1:4])

                # Keep stop if color difference is significant
                if color_diff > 0.05:  # 5% color difference threshold
                    optimized_stops.append(curr_stop)

            optimized_stops.append(stops[-1])  # Always keep last
            return np.array(optimized_stops)

        return stops

    def _calculate_quality_score(self, original: OptimizedGradientData,
                               optimized_stops: np.ndarray) -> float:
        """Calculate quality score for optimized gradient"""
        if len(original.stops) == 0:
            return 1.0

        # Base quality from stop count ratio
        stop_ratio = len(optimized_stops) / len(original.stops)
        base_score = min(1.0, stop_ratio + 0.5)  # Penalize excessive reduction

        # Adjust for color space
        if original.color_space == ColorSpace.LAB:
            base_score += 0.1  # Bonus for perceptual uniformity
        elif original.color_space == ColorSpace.HSL:
            base_score += 0.05

        # Adjust for interpolation method
        if original.interpolation_method in [InterpolationMethod.CUBIC, InterpolationMethod.HERMITE]:
            base_score += 0.05

        return min(1.0, base_score)

    def interpolate_advanced_batch(self, gradient_data: List[OptimizedGradientData],
                                 sample_positions: np.ndarray,
                                 method: InterpolationMethod = InterpolationMethod.LINEAR) -> np.ndarray:
        """
        Advanced interpolation for gradients using various methods.

        Args:
            gradient_data: List of optimized gradients
            sample_positions: (N, M) positions to sample [0,1]
            method: Interpolation method to use

        Returns:
            np.ndarray: (N, M, 3) interpolated colors
        """
        n_gradients = len(gradient_data)
        n_samples = sample_positions.shape[1]
        colors = np.zeros((n_gradients, n_samples, 3), dtype=np.float64)

        for i, gradient in enumerate(gradient_data):
            positions = sample_positions[i] if sample_positions.ndim > 1 else sample_positions
            stops = gradient.stops

            if method == InterpolationMethod.LINEAR:
                colors[i] = self._interpolate_linear(stops, positions)
            elif method == InterpolationMethod.CUBIC:
                colors[i] = self._interpolate_cubic(stops, positions)
            elif method == InterpolationMethod.HERMITE:
                colors[i] = self._interpolate_hermite(stops, positions)
            else:
                # Fallback to linear
                colors[i] = self._interpolate_linear(stops, positions)

            # Convert color space if needed
            if gradient.color_space != ColorSpace.RGB:
                colors[i] = self.convert_colorspace_batch(colors[i], gradient.color_space, ColorSpace.RGB)

        return colors

    def _interpolate_linear(self, stops: np.ndarray, positions: np.ndarray) -> np.ndarray:
        """Linear interpolation between gradient stops"""
        colors = np.zeros((len(positions), 3))

        for i, pos in enumerate(positions):
            # Find surrounding stops
            idx = np.searchsorted(stops[:, 0], pos)
            if idx == 0:
                colors[i] = stops[0, 1:4]
            elif idx >= len(stops):
                colors[i] = stops[-1, 1:4]
            else:
                # Interpolate between stops
                t = (pos - stops[idx-1, 0]) / (stops[idx, 0] - stops[idx-1, 0])
                colors[i] = stops[idx-1, 1:4] + t * (stops[idx, 1:4] - stops[idx-1, 1:4])

        return colors

    def _interpolate_cubic(self, stops: np.ndarray, positions: np.ndarray) -> np.ndarray:
        """Cubic spline interpolation between gradient stops"""
        from scipy import interpolate

        if len(stops) < 3:
            return self._interpolate_linear(stops, positions)

        colors = np.zeros((len(positions), 3))

        # Interpolate each color channel separately
        for channel in range(3):
            spline = interpolate.CubicSpline(stops[:, 0], stops[:, channel + 1],
                                           bc_type='natural')
            colors[:, channel] = spline(np.clip(positions, stops[0, 0], stops[-1, 0]))

        return np.clip(colors, 0.0, 1.0)

    def _interpolate_hermite(self, stops: np.ndarray, positions: np.ndarray) -> np.ndarray:
        """Hermite spline interpolation with automatic tangent calculation"""
        if len(stops) < 3:
            return self._interpolate_linear(stops, positions)

        colors = np.zeros((len(positions), 3))

        # Calculate tangents for each stop
        tangents = np.zeros_like(stops[:, 1:4])
        for i in range(1, len(stops) - 1):
            # Central difference
            dt_prev = stops[i, 0] - stops[i-1, 0]
            dt_next = stops[i+1, 0] - stops[i, 0]
            tangents[i] = ((stops[i+1, 1:4] - stops[i, 1:4]) / dt_next +
                          (stops[i, 1:4] - stops[i-1, 1:4]) / dt_prev) * 0.5

        # Boundary conditions
        tangents[0] = (stops[1, 1:4] - stops[0, 1:4]) / (stops[1, 0] - stops[0, 0])
        tangents[-1] = (stops[-1, 1:4] - stops[-2, 1:4]) / (stops[-1, 0] - stops[-2, 0])

        # Hermite interpolation
        for i, pos in enumerate(positions):
            idx = np.searchsorted(stops[:, 0], pos)
            if idx == 0:
                colors[i] = stops[0, 1:4]
            elif idx >= len(stops):
                colors[i] = stops[-1, 1:4]
            else:
                # Hermite basis functions
                dt = stops[idx, 0] - stops[idx-1, 0]
                t = (pos - stops[idx-1, 0]) / dt
                t2, t3 = t*t, t*t*t

                h00 = 2*t3 - 3*t2 + 1
                h10 = t3 - 2*t2 + t
                h01 = -2*t3 + 3*t2
                h11 = t3 - t2

                colors[i] = (h00 * stops[idx-1, 1:4] +
                           h10 * tangents[idx-1] * dt +
                           h01 * stops[idx, 1:4] +
                           h11 * tangents[idx] * dt)

        return np.clip(colors, 0.0, 1.0)

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics"""
        cache_stats = self.cache.get_stats()

        return {
            'cache_statistics': cache_stats,
            'color_space_conversions': {
                'supported_spaces': [space.value for space in ColorSpace],
                'conversion_methods': 12  # RGB<->XYZ<->LAB, RGB<->HSL, etc.
            },
            'interpolation_methods': [method.value for method in InterpolationMethod],
            'optimization_levels': [0, 1, 2],
            'vectorization_threshold': self.vectorization_threshold,
            'interpolation_quality': self.interpolation_quality
        }


# Factory functions
def create_advanced_gradient_engine(cache_size: int = 1000, memory_limit_mb: int = 100) -> AdvancedGradientEngine:
    """Create optimized advanced gradient engine"""
    return AdvancedGradientEngine(cache_size, memory_limit_mb)


def process_advanced_gradients_batch(gradients: List[OptimizedGradientData],
                                   transforms: Optional[TransformationBatch] = None,
                                   optimization_level: int = 1) -> Dict[str, Any]:
    """
    Process gradients with advanced features and optimization.

    Args:
        gradients: List of gradient data to process
        transforms: Optional transformation batch
        optimization_level: Optimization level (0-2)

    Returns:
        Dict containing processed gradients and performance metrics
    """
    engine = create_advanced_gradient_engine()

    import time
    start_time = time.perf_counter()

    # Optimize gradients
    optimized = engine.optimize_gradients_batch(gradients, optimization_level)

    # Apply transformations if provided
    if transforms is not None:
        optimized = engine.apply_transformations_batch(optimized, transforms)

    total_time = time.perf_counter() - start_time

    return {
        'optimized_gradients': optimized,
        'performance_metrics': {
            'total_time': total_time,
            'gradients_processed': len(gradients),
            'gradients_per_second': len(gradients) / total_time,
            'optimization_level': optimization_level,
            'average_compression_ratio': np.mean([g.compression_ratio for g in optimized]),
            'average_quality_score': np.mean([g.quality_score for g in optimized])
        },
        'engine_stats': engine.get_performance_stats()
    }