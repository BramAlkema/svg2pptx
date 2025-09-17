#!/usr/bin/env python3
"""
Path Processing Performance Analysis

Analyzes current bottlenecks in the SVG path processing system to identify
areas for NumPy optimization targeting 100-300x speedup.
"""

import time
import sys
import os
import numpy as np
import re
from typing import List, Dict, Any

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from converters.paths import PathData, PathConverter
    from services.conversion_services import ConversionServices
    from converters.base import ConversionContext
except ImportError as e:
    print(f"Import error: {e}")
    print("Running without converter imports - analyzing parsing only")


def benchmark_path_parsing_performance():
    """Benchmark SVG path parsing performance."""
    print("=== Path Parsing Performance Analysis ===")

    # Generate realistic SVG path data for testing
    test_paths = []

    # Simple paths
    test_paths.extend([
        "M 10 10 L 90 90",
        "M 10 10 L 90 10 L 90 90 L 10 90 Z",
        "M 50 50 A 25 25 0 1 1 50 49 Z"
    ] * 200)

    # Complex paths with curves
    complex_paths = [
        "M 100 200 C 100 100 400 100 400 200 S 600 300 600 200",
        "M 10 80 Q 95 10 180 80 T 340 80",
        "M 200 300 L 400 50 Q 600 300 800 50 L 1000 300 Z",
        "M 0 0 L 50 0 A 25 25 0 0 1 100 25 L 100 75 A 25 25 0 0 1 50 100 L 0 100 Z"
    ]
    test_paths.extend(complex_paths * 100)

    # Very complex paths (simulating real SVG graphics)
    very_complex = [
        "M 300 150 C 300 67 233 0 150 0 S 0 67 0 150 67 300 150 300 300 233 300 150 Z M 150 50 C 194 50 230 86 230 130 C 230 174 194 210 150 210 C 106 210 70 174 70 130 C 70 86 106 50 150 50 Z",
        "M 50 50 Q 100 0 150 50 T 250 50 L 300 100 A 50 50 0 1 0 200 150 Q 150 200 100 150 T 50 150 Z M 200 75 C 225 75 250 100 250 125 C 250 150 225 175 200 175 C 175 175 150 150 150 125 C 150 100 175 75 200 75 Z"
    ]
    test_paths.extend(very_complex * 50)

    print(f"Testing with {len(test_paths)} path strings")

    # Benchmark parsing
    start_time = time.time()
    parsed_paths = []

    for path_string in test_paths:
        try:
            path_data = PathData(path_string)
            parsed_paths.append(path_data)
        except Exception as e:
            print(f"Error parsing path: {e}")
            continue

    parsing_time = time.time() - start_time

    print(f"Parsed {len(parsed_paths)} paths in {parsing_time:.4f}s")
    print(f"Parsing rate: {len(parsed_paths)/parsing_time:,.0f} paths/sec")
    print(f"Per-path time: {parsing_time/len(parsed_paths)*1000:.3f}ms")

    # Analyze command distribution
    command_counts = {}
    total_commands = 0
    total_coordinates = 0

    for path in parsed_paths:
        for command, coords in path.commands:
            command_counts[command] = command_counts.get(command, 0) + 1
            total_commands += 1
            total_coordinates += len(coords)

    print(f"\nCommand distribution:")
    for cmd, count in sorted(command_counts.items()):
        print(f"  {cmd}: {count} ({count/total_commands*100:.1f}%)")

    print(f"Total commands: {total_commands}")
    print(f"Total coordinates: {total_coordinates}")

    return parsing_time, len(test_paths), total_commands, total_coordinates


def analyze_regex_parsing_bottlenecks():
    """Analyze regex parsing performance bottlenecks."""
    print("\n=== Regex Parsing Analysis ===")

    # Current PathData regex patterns
    test_paths = [
        "M 100 200 C 100 100 400 100 400 200 S 600 300 600 200",
        "M 10 80 Q 95 10 180 80 T 340 80",
        "M 200 300 L 400 50 Q 600 300 800 50 L 1000 300 Z"
    ] * 1000

    # Current approach (from PathData.parse)
    current_pattern = r'([MmLlHhVvCcSsQqTtAaZz])'
    clean_pattern = r'[,\s]+'

    start_time = time.time()
    for path_string in test_paths:
        # Clean and tokenize (current approach)
        cleaned = re.sub(clean_pattern, ' ', path_string.strip())
        parts = re.split(current_pattern, cleaned)
        parts = [p.strip() for p in parts if p.strip()]

        current_command = None
        for part in parts:
            if re.match(r'[MmLlHhVvCcSsQqTtAaZz]', part):
                current_command = part
            elif current_command and part:
                coords = [float(x) for x in part.split() if x]

    current_time = time.time() - start_time

    # Alternative approach (compiled regex)
    compiled_command_pattern = re.compile(current_pattern)
    compiled_clean_pattern = re.compile(clean_pattern)

    start_time = time.time()
    for path_string in test_paths:
        cleaned = compiled_clean_pattern.sub(' ', path_string.strip())
        parts = compiled_command_pattern.split(cleaned)
        parts = [p.strip() for p in parts if p.strip()]

        # Process parts (same logic)
        current_command = None
        for part in parts:
            if re.match(r'[MmLlHhVvCcSsQqTtAaZz]', part):
                current_command = part
            elif current_command and part:
                coords = [float(x) for x in part.split() if x]

    compiled_time = time.time() - start_time

    print(f"Current regex parsing: {current_time:.4f}s")
    print(f"Compiled regex parsing: {compiled_time:.4f}s")
    print(f"Compiled speedup: {current_time/compiled_time:.2f}x")

    return current_time, compiled_time


def simulate_coordinate_processing():
    """Simulate coordinate processing bottlenecks."""
    print("\n=== Coordinate Processing Simulation ===")

    # Simulate processing a complex path with many coordinates
    n_coordinates = 10000
    coordinates = np.random.random(n_coordinates * 2) * 1000  # Random coordinates

    # Current approach - individual coordinate processing
    start_time = time.time()
    transformed_coords = []
    for i in range(0, len(coordinates), 2):
        x, y = coordinates[i], coordinates[i + 1]
        # Simulate coordinate transformation (SVG to EMU)
        transformed_x = int((x / 1000.0) * 21600)  # Scale to DrawingML space
        transformed_y = int((y / 1000.0) * 21600)
        transformed_coords.extend([transformed_x, transformed_y])

    scalar_time = time.time() - start_time

    # NumPy vectorized approach
    start_time = time.time()
    coords_array = coordinates.reshape(-1, 2)  # Shape to (N, 2)
    # Vectorized transformation
    scale_factor = 21600 / 1000.0
    transformed_vectorized = (coords_array * scale_factor).astype(np.int32)

    vectorized_time = time.time() - start_time

    print(f"Scalar coordinate processing: {scalar_time:.4f}s")
    print(f"Vectorized coordinate processing: {vectorized_time:.6f}s")
    print(f"NumPy speedup potential: {scalar_time/vectorized_time:.1f}x")

    return scalar_time, vectorized_time


def simulate_bezier_calculations():
    """Simulate Bezier curve calculation performance."""
    print("\n=== Bezier Calculation Simulation ===")

    # Generate test Bezier curves
    n_curves = 1000
    curves = []

    for i in range(n_curves):
        # Each cubic Bezier has 4 control points (8 coordinates)
        curve = np.random.random(8) * 1000
        curves.append(curve)

    # Current approach - individual curve processing
    start_time = time.time()

    for curve in curves:
        x1, y1, cx1, cy1, cx2, cy2, x2, y2 = curve

        # Simulate Bezier evaluation at multiple t values
        for t in np.linspace(0, 1, 10):
            # Cubic Bezier formula: B(t) = (1-t)³P₀ + 3(1-t)²tP₁ + 3(1-t)t²P₂ + t³P₃
            mt = 1 - t
            x = (mt**3 * x1 + 3 * mt**2 * t * cx1 +
                 3 * mt * t**2 * cx2 + t**3 * x2)
            y = (mt**3 * y1 + 3 * mt**2 * t * cy1 +
                 3 * mt * t**2 * cy2 + t**3 * y2)

    scalar_bezier_time = time.time() - start_time

    # NumPy vectorized approach
    start_time = time.time()

    # Convert curves to numpy array (n_curves, 8)
    curves_array = np.array(curves)

    # Reshape to (n_curves, 4, 2) - 4 control points with x,y coordinates
    control_points = curves_array.reshape(n_curves, 4, 2)

    # Evaluate all curves at multiple t values vectorized
    t_values = np.linspace(0, 1, 10)

    for t in t_values:
        mt = 1 - t
        # Vectorized Bezier evaluation for all curves
        bezier_points = (mt**3 * control_points[:, 0] +
                        3 * mt**2 * t * control_points[:, 1] +
                        3 * mt * t**2 * control_points[:, 2] +
                        t**3 * control_points[:, 3])

    vectorized_bezier_time = time.time() - start_time

    print(f"Scalar Bezier calculations: {scalar_bezier_time:.4f}s")
    print(f"Vectorized Bezier calculations: {vectorized_bezier_time:.4f}s")
    print(f"Bezier NumPy speedup potential: {scalar_bezier_time/vectorized_bezier_time:.1f}x")

    return scalar_bezier_time, vectorized_bezier_time


def identify_path_bottlenecks():
    """Identify specific performance bottlenecks in path processing."""
    print("\n=== Path Processing Bottleneck Analysis ===")

    print("\n1. String Parsing Bottlenecks:")
    print("   - Regex compilation on every path parse")
    print("   - Multiple string splits and regex operations")
    print("   - Individual coordinate parsing with float() calls")
    print("   - No caching of parsed path data")

    print("\n2. Coordinate Processing Bottlenecks:")
    print("   - Individual coordinate transformation loops")
    print("   - Repeated scaling calculations (viewport mapping)")
    print("   - Manual coordinate system conversions")
    print("   - No vectorized coordinate operations")

    print("\n3. Bezier Curve Bottlenecks:")
    print("   - Individual curve evaluation with scalar math")
    print("   - Repeated quadratic-to-cubic conversions")
    print("   - Manual arc-to-bezier approximations")
    print("   - No curve subdivision optimization")

    print("\n4. Memory Allocation Bottlenecks:")
    print("   - List-based coordinate storage")
    print("   - String concatenation for XML output")
    print("   - Repeated object creation in loops")
    print("   - No structured array usage")


def numpy_path_optimization_potential():
    """Show NumPy optimization potential with path-specific examples."""
    print("\n=== NumPy Path Optimization Potential ===")

    # Simulate parsing many path commands
    n_commands = 5000

    # Current approach simulation
    start_time = time.time()
    commands = []
    for i in range(n_commands):
        # Simulate parsing individual path commands
        command_type = ['M', 'L', 'C', 'Q'][i % 4]
        coords = [float(j) for j in range(i % 6 + 2)]  # Variable coordinate count
        commands.append((command_type, coords))

    current_approach_time = time.time() - start_time

    # NumPy structured array approach
    start_time = time.time()

    # Define structured array for path commands
    path_dtype = np.dtype([
        ('cmd', 'U1'),           # Command type
        ('coords', 'f8', (6,))   # Up to 6 coordinates (for cubic curves)
    ])

    # Create structured array
    structured_commands = np.empty(n_commands, dtype=path_dtype)

    for i in range(n_commands):
        cmd = ['M', 'L', 'C', 'Q'][i % 4]
        coords = np.array([float(j) for j in range(6)], dtype=np.float64)
        structured_commands[i] = (cmd, coords)

    numpy_approach_time = time.time() - start_time

    print(f"Current list-based approach: {current_approach_time:.4f}s")
    print(f"NumPy structured array approach: {numpy_approach_time:.4f}s")
    print(f"Structured array speedup: {current_approach_time/numpy_approach_time:.1f}x")

    # Path processing pipeline simulation
    print(f"\nPath Processing Pipeline Simulation:")

    # Current approach - process each command individually
    start_time = time.time()
    for cmd, coords in commands:
        if cmd == 'C':  # Cubic curve
            # Process 6 coordinates individually
            for i in range(0, 6, 2):
                x, y = coords[i], coords[i+1] if i+1 < len(coords) else 0
                # Transform coordinates
                transformed = (x * 21600 / 1000, y * 21600 / 1000)

    current_pipeline_time = time.time() - start_time

    # NumPy approach - batch process all coordinates
    start_time = time.time()

    # Extract all cubic curve coordinates
    cubic_coords = structured_commands[structured_commands['cmd'] == 'C']['coords']
    if len(cubic_coords) > 0:
        # Reshape and process all coordinates at once
        all_coords = cubic_coords.reshape(-1, 2)  # Flatten to (N, 2)
        transformed_coords = all_coords * (21600 / 1000)  # Vectorized transformation

    numpy_pipeline_time = time.time() - start_time

    print(f"Current individual processing: {current_pipeline_time:.4f}s")
    print(f"NumPy batch processing: {numpy_pipeline_time:.6f}s")
    print(f"Pipeline speedup potential: {current_pipeline_time/numpy_pipeline_time:.0f}x")


def main():
    """Run comprehensive path processing performance analysis."""
    print("SVG Path Processing Performance Analysis")
    print("=" * 50)

    # Core performance benchmarks
    parsing_time, n_paths, n_commands, n_coords = benchmark_path_parsing_performance()
    current_regex, compiled_regex = analyze_regex_parsing_bottlenecks()
    scalar_coord, vectorized_coord = simulate_coordinate_processing()
    scalar_bezier, vectorized_bezier = simulate_bezier_calculations()

    # Identify bottlenecks and potential
    identify_path_bottlenecks()
    numpy_path_optimization_potential()

    # Summary
    print("\n" + "=" * 50)
    print("PATH PROCESSING ANALYSIS SUMMARY")
    print("=" * 50)
    print(f"Current parsing rate: {n_paths/parsing_time:,.0f} paths/sec")
    print(f"Commands per second: {n_commands/parsing_time:,.0f}")
    print(f"Coordinates per second: {n_coords/parsing_time:,.0f}")
    print(f"Regex optimization potential: {current_regex/compiled_regex:.1f}x speedup")
    print(f"Coordinate vectorization potential: {scalar_coord/vectorized_coord:.1f}x speedup")
    print(f"Bezier vectorization potential: {scalar_bezier/vectorized_bezier:.1f}x speedup")

    print(f"\nNUMPY PATH ENGINE TARGETS:")
    print(f"- Target parsing rate: {n_paths/parsing_time*100:,.0f} paths/sec (100x)")
    print(f"- Target command processing: {n_commands/parsing_time*200:,.0f} commands/sec (200x)")
    print(f"- Target coordinate processing: {n_coords/parsing_time*300:,.0f} coords/sec (300x)")


if __name__ == "__main__":
    main()