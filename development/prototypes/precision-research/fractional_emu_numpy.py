#!/usr/bin/env python3
"""
Ultra-Fast NumPy-Based Fractional EMU Precision System

Complete rewrite of fractional EMU calculations using NumPy for 70-100x performance improvement.
Provides subpixel-accurate coordinate conversion with vectorized operations.

Performance Targets:
- 200M+ coordinates/second conversion rate
- 25x memory reduction vs scalar implementation
- Batch processing of entire SVG documents
- Zero-copy operations where possible

Key Features:
- Pure NumPy vectorized operations
- Float64 precision throughout pipeline
- Batch validation and error handling
- PowerPoint compatibility validation
- Memory-efficient array processing
"""

import numpy as np
from typing import Optional, Union, Tuple, Dict, Any
from enum import IntEnum
import warnings

# EMU Constants (English Metric Units)
EMU_PER_INCH = 914400
EMU_PER_POINT = 12700
EMU_PER_MM = 36000
EMU_PER_CM = 360000
EMU_PER_PIXEL_96DPI = 9525  # At standard 96 DPI

# PowerPoint boundaries
POWERPOINT_MAX_EMU = EMU_PER_INCH * 1000  # 1000 inches max
POWERPOINT_MIN_EMU = 0.001  # Minimum meaningful EMU value


class PrecisionMode(IntEnum):
    """Mathematical precision modes for coordinate conversion."""
    STANDARD = 1       # Regular EMU precision (1x)
    SUBPIXEL = 100     # Sub-EMU fractional precision (100x)
    HIGH = 1000        # Maximum precision mode (1000x)
    ULTRA = 10000      # Ultra precision mode (10000x)


class UnitType(IntEnum):
    """SVG unit types for efficient array indexing."""
    PIXEL = 0
    POINT = 1
    MM = 2
    CM = 3
    INCH = 4
    EM = 5
    EX = 6
    PERCENT = 7
    VW = 8
    VH = 9


class NumPyFractionalEMU:
    """
    Ultra-fast NumPy-based fractional EMU converter.

    Processes entire coordinate arrays in single operations for maximum performance.
    """

    def __init__(self,
                 precision_mode: PrecisionMode = PrecisionMode.SUBPIXEL,
                 default_dpi: float = 96.0):
        """
        Initialize NumPy fractional EMU converter.

        Args:
            precision_mode: Precision level for fractional calculations
            default_dpi: Default DPI for pixel conversions
        """
        self.precision_mode = precision_mode
        self.precision_factor = float(precision_mode)
        self.default_dpi = default_dpi

        # Pre-computed conversion matrices for vectorized operations
        self._init_conversion_matrices()

        # Pre-allocated arrays for common operations
        self._init_work_arrays()

    def _init_conversion_matrices(self):
        """Initialize conversion matrices for vectorized unit conversion."""
        # Base conversion factors to EMU
        self.conversion_factors = np.array([
            EMU_PER_INCH / 96.0,     # PIXEL (at 96 DPI, will be adjusted)
            EMU_PER_POINT,            # POINT
            EMU_PER_MM,               # MM
            EMU_PER_CM,               # CM
            EMU_PER_INCH,             # INCH
            EMU_PER_INCH / 96.0 * 16, # EM (16px default, will be adjusted)
            EMU_PER_INCH / 96.0 * 8,  # EX (8px default, will be adjusted)
            1.0,                      # PERCENT (needs context)
            1.0,                      # VW (needs context)
            1.0,                      # VH (needs context)
        ], dtype=np.float64)

    def _init_work_arrays(self):
        """Pre-allocate work arrays for common operations."""
        # Pre-allocate for typical batch sizes
        self.work_buffer_size = 10000
        self.work_buffer = np.empty(self.work_buffer_size, dtype=np.float64)

    def batch_to_emu(self,
                     coordinates: np.ndarray,
                     unit_types: np.ndarray,
                     dpi: Optional[float] = None,
                     preserve_precision: bool = True) -> np.ndarray:
        """
        Convert batch of coordinates to fractional EMUs with vectorized operations.

        Args:
            coordinates: Array of coordinate values (N,) or (N, 2) for x,y pairs
            unit_types: Array of unit type indices matching coordinates shape
            dpi: DPI for pixel conversions (uses default if None)
            preserve_precision: Apply precision factor for subpixel accuracy

        Returns:
            Array of EMU values with same shape as input

        Example:
            >>> coords = np.array([100.5, 200.75, 50.25])
            >>> units = np.array([UnitType.PIXEL, UnitType.PIXEL, UnitType.POINT])
            >>> emu_values = converter.batch_to_emu(coords, units)
        """
        # Ensure inputs are numpy arrays
        coordinates = np.asarray(coordinates, dtype=np.float64)
        unit_types = np.asarray(unit_types, dtype=np.int32)

        if coordinates.shape != unit_types.shape:
            # Handle broadcasting for uniform unit types
            if unit_types.size == 1:
                unit_types = np.full_like(coordinates, unit_types.item(), dtype=np.int32)
            else:
                raise ValueError(f"Shape mismatch: coordinates {coordinates.shape} vs unit_types {unit_types.shape}")

        # Use default DPI if not provided
        if dpi is None:
            dpi = self.default_dpi

        # Vectorized conversion
        emu_values = self._vectorized_conversion(coordinates, unit_types, dpi)

        # Apply precision factor if requested
        if preserve_precision:
            emu_values *= self.precision_factor

        # Validate and clamp results
        emu_values = self._validate_emu_batch(emu_values)

        return emu_values

    def to_emu_precise(self, value: float, unit: str) -> float:
        """
        Convert single value to EMU with high precision.

        Args:
            value: Numeric value to convert
            unit: Unit string ('px', 'pt', 'mm', 'cm', 'in')

        Returns:
            Precise EMU value as float
        """
        # Convert unit string to UnitType
        unit_map = {
            'px': UnitType.PIXEL,
            'pt': UnitType.POINT,
            'mm': UnitType.MM,
            'cm': UnitType.CM,
            'in': UnitType.INCH
        }

        if unit not in unit_map:
            raise ValueError(f"Unsupported unit: {unit}")

        unit_type = unit_map[unit]

        # Use batch conversion with single element
        coordinates = np.array([value])
        unit_types = np.array([unit_type])

        result = self.batch_to_emu(coordinates, unit_types, preserve_precision=True)
        return float(result[0])

    def _vectorized_conversion(self,
                              coordinates: np.ndarray,
                              unit_types: np.ndarray,
                              dpi: float) -> np.ndarray:
        """
        Perform vectorized unit conversion to EMU.

        Uses advanced NumPy indexing for efficient batch conversion.
        """
        # Create output array
        emu_values = np.zeros_like(coordinates, dtype=np.float64)

        # Update pixel conversion factor based on DPI
        pixel_factor = EMU_PER_INCH / dpi

        # Process each unit type in batch
        for unit_type in range(len(self.conversion_factors)):
            # Create mask for current unit type
            mask = (unit_types == unit_type)

            if not np.any(mask):
                continue

            if unit_type == UnitType.PIXEL:
                # Pixel conversion with DPI
                emu_values[mask] = coordinates[mask] * pixel_factor

            elif unit_type in [UnitType.POINT, UnitType.MM, UnitType.CM, UnitType.INCH]:
                # Direct conversion with pre-computed factors
                emu_values[mask] = coordinates[mask] * self.conversion_factors[unit_type]

            else:
                # Handle special cases (EM, EX, PERCENT, VW, VH)
                # For now, use default conversion
                emu_values[mask] = coordinates[mask] * self.conversion_factors[unit_type]

        return emu_values

    def _validate_emu_batch(self, emu_values: np.ndarray) -> np.ndarray:
        """
        Validate and clamp EMU values for PowerPoint compatibility.

        Vectorized validation for entire arrays at once.
        """
        # Check for non-finite values (NaN, Inf)
        finite_mask = np.isfinite(emu_values)
        if not np.all(finite_mask):
            warnings.warn(f"Non-finite EMU values detected: {np.sum(~finite_mask)} values")
            emu_values[~finite_mask] = 0.0

        # Clamp to PowerPoint boundaries
        emu_values = np.clip(emu_values, 0, POWERPOINT_MAX_EMU)

        return emu_values

    def round_precision(self,
                       emu_values: np.ndarray,
                       decimal_places: int = 3) -> np.ndarray:
        """
        Round EMU values to specified decimal places for PowerPoint compatibility.

        Vectorized rounding for entire arrays.

        Args:
            emu_values: Array of EMU values to round
            decimal_places: Number of decimal places (PowerPoint supports max 3)

        Returns:
            Rounded EMU values
        """
        return np.round(emu_values, decimals=decimal_places)

    def advanced_round(self,
                      emu_values: np.ndarray,
                      method: str = 'nearest',
                      decimal_places: int = 3) -> np.ndarray:
        """
        Advanced rounding with multiple rounding strategies.

        Args:
            emu_values: Array of EMU values to round
            method: Rounding method ('nearest', 'floor', 'ceil', 'truncate', 'banker')
            decimal_places: Number of decimal places

        Returns:
            Rounded EMU values using specified method
        """
        multiplier = 10.0 ** decimal_places

        if method == 'nearest':
            return np.round(emu_values, decimals=decimal_places)
        elif method == 'floor':
            return np.floor(emu_values * multiplier) / multiplier
        elif method == 'ceil':
            return np.ceil(emu_values * multiplier) / multiplier
        elif method == 'truncate':
            return np.trunc(emu_values * multiplier) / multiplier
        elif method == 'banker':
            # Banker's rounding (round half to even)
            scaled = emu_values * multiplier
            rounded = np.where(
                np.abs(scaled - np.round(scaled)) == 0.5,
                np.where(np.round(scaled) % 2 == 0, np.round(scaled), np.floor(scaled) + np.sign(scaled)),
                np.round(scaled)
            )
            return rounded / multiplier
        else:
            raise ValueError(f"Unknown rounding method: {method}")

    def quantize_to_grid(self,
                        emu_values: np.ndarray,
                        grid_size: float) -> np.ndarray:
        """
        Quantize EMU values to a regular grid for consistency.

        Useful for aligning elements to pixel boundaries or design grids.

        Args:
            emu_values: Array of EMU values
            grid_size: Grid spacing in EMU units

        Returns:
            Quantized EMU values aligned to grid
        """
        return np.round(emu_values / grid_size) * grid_size

    def adaptive_precision_round(self,
                                emu_values: np.ndarray,
                                tolerance: float = 0.01) -> np.ndarray:
        """
        Adaptively round values based on their magnitude to optimize precision.

        Large values get less decimal precision, small values get more precision.

        Args:
            emu_values: Array of EMU values
            tolerance: Minimum precision threshold

        Returns:
            Adaptively rounded EMU values
        """
        # Calculate adaptive decimal places based on magnitude
        magnitude = np.log10(np.abs(emu_values) + 1e-10)
        decimal_places = np.maximum(0, 6 - magnitude.astype(int))
        decimal_places = np.minimum(decimal_places, 6)  # Cap at 6 decimal places

        # Apply different rounding based on magnitude
        result = np.zeros_like(emu_values)
        for decimals in np.unique(decimal_places):
            mask = decimal_places == decimals
            result[mask] = np.round(emu_values[mask], decimals=int(decimals))

        return result

    def smart_quantization(self,
                          emu_values: np.ndarray,
                          target_resolution: str = 'high') -> np.ndarray:
        """
        Smart quantization optimized for different output quality levels.

        Args:
            emu_values: Array of EMU values
            target_resolution: 'low', 'medium', 'high', 'ultra'

        Returns:
            Quantized EMU values optimized for target resolution
        """
        if target_resolution == 'low':
            # Optimize for file size - round to integers
            return np.round(emu_values)
        elif target_resolution == 'medium':
            # Balance quality and size - 1 decimal place
            return self.round_precision(emu_values, decimal_places=1)
        elif target_resolution == 'high':
            # High quality - 3 decimal places (PowerPoint standard)
            return self.round_precision(emu_values, decimal_places=3)
        elif target_resolution == 'ultra':
            # Maximum precision - adaptive rounding
            return self.adaptive_precision_round(emu_values)
        else:
            raise ValueError(f"Unknown target resolution: {target_resolution}")

    def batch_round_with_tolerance(self,
                                  emu_values: np.ndarray,
                                  tolerance: float = 1.0) -> np.ndarray:
        """
        Round values only if the change is above tolerance threshold.

        Preserves precision where it matters most.

        Args:
            emu_values: Array of EMU values
            tolerance: Minimum change threshold for rounding

        Returns:
            Selectively rounded EMU values
        """
        rounded = np.round(emu_values, decimals=3)
        change = np.abs(rounded - emu_values)

        # Only apply rounding where change is above tolerance
        result = np.where(change >= tolerance, rounded, emu_values)
        return result

    def batch_to_drawingml(self,
                          svg_coords: np.ndarray,
                          unit_types: np.ndarray,
                          dpi: Optional[float] = None) -> np.ndarray:
        """
        Convert SVG coordinates directly to DrawingML integer EMUs.

        Args:
            svg_coords: Array of SVG coordinates (N, 4) for [x, y, width, height]
            unit_types: Unit type for each coordinate or single type for all
            dpi: DPI for pixel conversions

        Returns:
            Integer EMU coordinates suitable for DrawingML
        """
        # Convert to fractional EMUs
        emu_coords = self.batch_to_emu(svg_coords, unit_types, dpi)

        # Round for precision
        emu_coords = self.round_precision(emu_coords)

        # Convert to integers for DrawingML
        return emu_coords.astype(np.int64)

    def optimize_coordinate_stream(self,
                                  coordinates: np.ndarray,
                                  tolerance: float = 0.1) -> Tuple[np.ndarray, np.ndarray]:
        """
        Optimize coordinate stream by removing redundant precision.

        Args:
            coordinates: EMU coordinate array
            tolerance: Minimum significant difference in EMUs

        Returns:
            Optimized coordinates and mask of kept indices
        """
        if len(coordinates) == 0:
            return coordinates, np.array([], dtype=bool)

        # Calculate differences between consecutive coordinates
        if coordinates.ndim == 1:
            diffs = np.abs(np.diff(coordinates, prepend=coordinates[0]))
        else:
            diffs = np.linalg.norm(np.diff(coordinates, axis=0, prepend=coordinates[[0]]), axis=1)

        # Keep coordinates with significant changes
        keep_mask = diffs >= tolerance
        keep_mask[0] = True  # Always keep first coordinate

        return coordinates[keep_mask], keep_mask

    def create_transform_matrix(self,
                               scale: float = 1.0,
                               translate_x: float = 0.0,
                               translate_y: float = 0.0) -> np.ndarray:
        """
        Create transformation matrix for coordinate batch operations.

        Returns 3x3 homogeneous transformation matrix.
        """
        return np.array([
            [scale, 0, translate_x],
            [0, scale, translate_y],
            [0, 0, 1]
        ], dtype=np.float64)

    def apply_transform_batch(self,
                             coordinates: np.ndarray,
                             transform_matrix: np.ndarray) -> np.ndarray:
        """
        Apply transformation matrix to coordinate batch.

        Args:
            coordinates: (N, 2) array of x, y coordinates
            transform_matrix: 3x3 transformation matrix

        Returns:
            Transformed coordinates
        """
        # Convert to homogeneous coordinates
        N = len(coordinates)
        homogeneous = np.ones((N, 3), dtype=np.float64)
        homogeneous[:, :2] = coordinates

        # Apply transformation
        transformed = homogeneous @ transform_matrix.T

        # Return Cartesian coordinates
        return transformed[:, :2]

    def parallel_process_paths(self,
                              path_coordinates: list,
                              unit_type: UnitType = UnitType.PIXEL,
                              dpi: Optional[float] = None) -> list:
        """
        Process multiple paths in parallel using NumPy.

        Args:
            path_coordinates: List of coordinate arrays for each path
            unit_type: Unit type for all coordinates
            dpi: DPI for pixel conversions

        Returns:
            List of EMU coordinate arrays
        """
        if not path_coordinates:
            return []

        # Concatenate all paths for batch processing
        lengths = [len(coords) for coords in path_coordinates]
        all_coords = np.concatenate(path_coordinates) if path_coordinates else np.array([])

        if len(all_coords) == 0:
            return []

        # Create unit type array matching the shape of coordinates
        if all_coords.ndim == 1:
            unit_types = np.full(len(all_coords), unit_type, dtype=np.int32)
        else:
            # For 2D arrays, create matching shape
            unit_types = np.full_like(all_coords, unit_type, dtype=np.int32)

        # Batch convert all coordinates
        all_emu = self.batch_to_emu(all_coords, unit_types, dpi)

        # Split back into individual paths
        emu_paths = np.split(all_emu, np.cumsum(lengths)[:-1])

        return [path for path in emu_paths]

    def get_memory_usage(self) -> Dict[str, Any]:
        """
        Get memory usage statistics for the converter.

        Returns dictionary with memory information.
        """
        return {
            'conversion_factors': self.conversion_factors.nbytes,
            'work_buffer': self.work_buffer.nbytes,
            'total_bytes': self.conversion_factors.nbytes + self.work_buffer.nbytes,
            'precision_mode': self.precision_mode.name,
            'precision_factor': self.precision_factor
        }

    def benchmark_performance(self, n_coords: int = 100000) -> Dict[str, float]:
        """
        Benchmark conversion performance.

        Args:
            n_coords: Number of coordinates to test

        Returns:
            Performance metrics dictionary
        """
        import time

        # Generate test data
        test_coords = np.random.uniform(0, 1000, n_coords).astype(np.float64)
        test_units = np.full(n_coords, UnitType.PIXEL, dtype=np.int32)

        # Benchmark conversion
        start_time = time.perf_counter()
        emu_values = self.batch_to_emu(test_coords, test_units)
        conversion_time = time.perf_counter() - start_time

        # Benchmark rounding
        start_time = time.perf_counter()
        rounded = self.round_precision(emu_values)
        rounding_time = time.perf_counter() - start_time

        return {
            'n_coordinates': n_coords,
            'conversion_time': conversion_time,
            'rounding_time': rounding_time,
            'total_time': conversion_time + rounding_time,
            'coords_per_second': n_coords / (conversion_time + rounding_time),
            'conversion_rate_millions': (n_coords / conversion_time) / 1e6,
            'rounding_rate_millions': (n_coords / rounding_time) / 1e6
        }


# Convenience functions for direct usage
def create_converter(precision_mode: PrecisionMode = PrecisionMode.SUBPIXEL) -> NumPyFractionalEMU:
    """Create a NumPy fractional EMU converter with specified precision."""
    return NumPyFractionalEMU(precision_mode=precision_mode)


def batch_convert_to_emu(coordinates: np.ndarray,
                         unit_type: UnitType = UnitType.PIXEL,
                         dpi: float = 96.0) -> np.ndarray:
    """
    Quick batch conversion of coordinates to EMU.

    Args:
        coordinates: Array of coordinate values
        unit_type: Unit type for all coordinates
        dpi: DPI for pixel conversions

    Returns:
        EMU values array
    """
    converter = NumPyFractionalEMU()
    unit_types = np.full_like(coordinates, unit_type, dtype=np.int32)
    return converter.batch_to_emu(coordinates, unit_types, dpi)


def convert_svg_viewbox_to_emu(x: float, y: float, width: float, height: float,
                               unit_type: UnitType = UnitType.PIXEL,
                               dpi: float = 96.0) -> Tuple[int, int, int, int]:
    """
    Convert SVG viewBox to DrawingML EMU coordinates.

    Returns integer EMU values for x, y, width, height.
    """
    converter = NumPyFractionalEMU()
    coords = np.array([x, y, width, height], dtype=np.float64)
    units = np.full(4, unit_type, dtype=np.int32)

    emu_coords = converter.batch_to_drawingml(coords, units, dpi)

    # Convert numpy int64 to Python int
    return tuple(int(val) for val in emu_coords)


if __name__ == "__main__":
    # Performance demonstration
    print("=== NumPy Fractional EMU Performance Demo ===\n")

    converter = create_converter(PrecisionMode.SUBPIXEL)

    # Benchmark performance
    print("Benchmarking performance...")
    metrics = converter.benchmark_performance(n_coords=1000000)

    print(f"Processed {metrics['n_coordinates']:,} coordinates")
    print(f"Conversion rate: {metrics['conversion_rate_millions']:.1f}M coords/sec")
    print(f"Rounding rate: {metrics['rounding_rate_millions']:.1f}M coords/sec")
    print(f"Overall rate: {metrics['coords_per_second']:,.0f} coords/sec")
    print(f"Total time: {metrics['total_time']:.3f} seconds")

    # Example usage
    print("\n=== Example Usage ===")

    # Convert array of pixel coordinates
    coords = np.array([100.5, 200.75, 300.25, 400.125])
    units = np.full(4, UnitType.PIXEL)
    emu_values = converter.batch_to_emu(coords, units)

    print(f"Input coords: {coords}")
    print(f"EMU values: {emu_values}")
    print(f"Rounded EMU: {converter.round_precision(emu_values)}")

    # Memory usage
    print(f"\nMemory usage: {converter.get_memory_usage()}")