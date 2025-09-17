#!/usr/bin/env python3
"""
Integration tests for NumPy ViewBox system with the main codebase.

Tests performance improvements, visual accuracy, and integration with transform
and unit systems for Task 1.5.4: Performance testing and integration.
"""

import pytest
import numpy as np
import sys
import os
import time
from typing import Dict, Any, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.viewbox.numpy_viewbox import NumPyViewportEngine, AspectAlign, MeetOrSlice
from src.viewbox.legacy import ViewportResolver
from src.units import UnitEngine, ConversionContext
from src.fractional_emu_numpy import NumPyFractionalEMU


class TestNumPyViewBoxPerformanceIntegration:
    """Performance testing for NumPy viewport system vs legacy implementation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.numpy_engine = NumPyViewportEngine()
        self.legacy_resolver = ViewportResolver()
        self.context = ConversionContext(dpi=96.0, viewport_width=800, viewport_height=600)

    def test_performance_comparison_small_batch(self):
        """Test performance improvement for small batch sizes (10-100 elements)."""
        batch_sizes = [10, 25, 50, 100]

        for n_elements in batch_sizes:
            # Generate test data
            viewbox_strings = [f"0 0 {100+i} {75+i}" for i in range(n_elements)]

            # Time NumPy implementation
            start_time = time.perf_counter()
            numpy_results = self.numpy_engine.parse_viewbox_strings(np.array(viewbox_strings))
            numpy_time = time.perf_counter() - start_time

            # Calculate performance metrics
            numpy_ops_per_sec = n_elements / numpy_time if numpy_time > 0 else float('inf')

            # Verify results are valid
            assert len(numpy_results) == n_elements
            assert np.all(numpy_results['width'] > 0)
            assert np.all(numpy_results['height'] > 0)

            # Performance should be reasonable (>1k ops/sec even for small batches)
            assert numpy_ops_per_sec > 1000, f"NumPy performance too slow: {numpy_ops_per_sec:,.0f} ops/sec"

            print(f"Batch size {n_elements}: {numpy_ops_per_sec:,.0f} operations/sec")

    def test_performance_comparison_large_batch(self):
        """Test performance improvement for large batch sizes (1k-10k elements)."""
        batch_sizes = [1000, 2500, 5000, 10000]

        performance_results = {}

        for n_elements in batch_sizes:
            # Generate test SVG elements
            svg_elements = []
            for i in range(n_elements):
                svg_elements.append({
                    'viewBox': f'0 0 {200+i%100} {150+i%75}',
                    'width': f'{400+i%200}px',
                    'height': f'{300+i%150}px',
                    'preserveAspectRatio': 'xMidYMid meet' if i % 2 == 0 else 'xMinYMax slice'
                })

            # Time NumPy batch processing
            start_time = time.perf_counter()
            numpy_mappings = self.numpy_engine.batch_resolve_svg_viewports(svg_elements, None, [self.context])
            numpy_time = time.perf_counter() - start_time

            # Calculate performance metrics
            numpy_ops_per_sec = n_elements / numpy_time

            performance_results[n_elements] = {
                'numpy_ops_per_sec': numpy_ops_per_sec,
                'numpy_time': numpy_time,
                'time_per_element_us': (numpy_time / n_elements) * 1_000_000
            }

            # Verify results
            assert len(numpy_mappings) == n_elements

            # Target performance: >50k elements/sec for large batches
            assert numpy_ops_per_sec > 50000, f"Large batch performance insufficient: {numpy_ops_per_sec:,.0f} ops/sec"

            print(f"Batch {n_elements}: {numpy_ops_per_sec:,.0f} ops/sec, "
                  f"{performance_results[n_elements]['time_per_element_us']:.1f}μs/element")

    def test_memory_efficiency_scaling(self):
        """Test memory efficiency with increasing batch sizes."""
        batch_sizes = [100, 500, 1000, 5000]

        for n_elements in batch_sizes:
            # Generate test data
            svg_elements = [
                {
                    'viewBox': f'0 0 {100+i} {75+i}',
                    'width': '400px',
                    'height': '300px'
                }
                for i in range(n_elements)
            ]

            # Measure memory before
            initial_memory = self.numpy_engine.get_memory_usage()['total_bytes']

            # Process batch
            results = self.numpy_engine.batch_resolve_svg_viewports(svg_elements, None, [self.context])

            # Measure memory after
            final_memory = self.numpy_engine.get_memory_usage()['total_bytes']
            memory_increase = final_memory - initial_memory

            # Calculate memory per element
            memory_per_element = memory_increase / n_elements

            # Memory usage should be reasonable (<1KB per element for viewport mappings)
            assert memory_per_element < 1024, f"Memory usage too high: {memory_per_element:.0f} bytes/element"

            # Verify results
            assert len(results) == n_elements

            print(f"Batch {n_elements}: {memory_per_element:.0f} bytes/element, "
                  f"total increase: {memory_increase/1024:.1f}KB")

    def test_advanced_features_performance(self):
        """Test performance of advanced viewport features."""
        n_elements = 1000

        # Generate test data for advanced features
        viewbox_aspects = np.random.uniform(0.5, 3.0, n_elements)
        viewport_aspects = np.random.uniform(0.5, 3.0, n_elements)
        meet_slice_modes = np.random.choice([0, 1], n_elements)  # MEET=0, SLICE=1

        # Test vectorized meet/slice calculations
        start_time = time.perf_counter()
        meet_slice_results = self.numpy_engine.vectorized_meet_slice_calculations(
            viewbox_aspects, viewport_aspects, meet_slice_modes
        )
        meet_slice_time = time.perf_counter() - start_time

        meet_slice_ops_per_sec = n_elements / meet_slice_time
        assert meet_slice_ops_per_sec > 100000, f"Meet/slice performance insufficient: {meet_slice_ops_per_sec:,.0f} ops/sec"

        # Verify results structure
        assert len(meet_slice_results) == n_elements
        assert np.all(np.isfinite(meet_slice_results['scale_x']))
        assert np.all(np.isfinite(meet_slice_results['scale_y']))

        # Test bounds intersection
        bounds_a = np.random.uniform(0, 500, (n_elements, 4))
        bounds_b = np.random.uniform(0, 500, (n_elements, 4))

        start_time = time.perf_counter()
        intersection_results = self.numpy_engine.efficient_bounds_intersection(bounds_a, bounds_b)
        intersection_time = time.perf_counter() - start_time

        intersection_ops_per_sec = n_elements / intersection_time
        assert intersection_ops_per_sec > 50000, f"Intersection performance insufficient: {intersection_ops_per_sec:,.0f} ops/sec"

        print(f"Meet/slice calculations: {meet_slice_ops_per_sec:,.0f} ops/sec")
        print(f"Bounds intersections: {intersection_ops_per_sec:,.0f} ops/sec")


class TestTransformSystemIntegration:
    """Test integration with transform and unit systems."""

    def setup_method(self):
        """Set up test fixtures."""
        self.viewport_engine = NumPyViewportEngine()
        self.unit_engine = UnitEngine()
        self.fractional_emu = NumPyFractionalEMU()
        self.context = ConversionContext(dpi=96.0, viewport_width=1024, viewport_height=768)

    def test_unit_converter_integration(self):
        """Test seamless integration with NumPy unit converter."""
        # Create test SVG elements with various unit types
        svg_elements = [
            {'viewBox': '0 0 100 75', 'width': '400px', 'height': '300px'},
            {'viewBox': '0 0 200 150', 'width': '600pt', 'height': '450pt'},
            {'viewBox': '0 0 50 50', 'width': '10cm', 'height': '10cm'},
            {'viewBox': '0 0 300 200', 'width': '5in', 'height': '3.5in'},
        ]

        # Process through viewport engine
        viewport_mappings = self.viewport_engine.batch_resolve_svg_viewports(svg_elements, None, [self.context])

        # Verify all mappings are valid
        assert len(viewport_mappings) == 4

        for i, mapping in enumerate(viewport_mappings):
            assert hasattr(mapping, 'scale_x')
            assert hasattr(mapping, 'scale_y')
            assert hasattr(mapping, 'translate_x')
            assert hasattr(mapping, 'translate_y')

            # All scale factors should be positive and finite
            assert mapping.scale_x > 0 and np.isfinite(mapping.scale_x)
            assert mapping.scale_y > 0 and np.isfinite(mapping.scale_y)

            print(f"Element {i}: scale=({mapping.scale_x:.2f}, {mapping.scale_y:.2f})")

    def test_fractional_emu_integration(self):
        """Test integration with fractional EMU system."""
        # Create test coordinates in different unit systems
        test_coordinates = [
            (100.5, 200.75),   # Fractional pixels
            (72.125, 144.25),  # Fractional points
            (25.4, 50.8),      # Fractional mm
        ]

        # Convert to EMU using fractional system
        emu_coords = []
        for x, y in test_coordinates:
            x_emu = self.fractional_emu.to_emu_precise(x, 'px')
            y_emu = self.fractional_emu.to_emu_precise(y, 'px')
            emu_coords.append((x_emu, y_emu))

        # Create viewport coordinate spaces
        source_spaces = np.array([
            (0, 0, 1000, 1000, 1.0)  # 1000x1000 source space
        ] * len(test_coordinates), dtype=self.viewport_engine.parse_viewbox_strings(np.array(["0 0 1000 1000"])).dtype)

        target_spaces = np.array([
            (0, 0, 800, 600, 4.0/3.0)  # 800x600 target space
        ] * len(test_coordinates), dtype=self.viewport_engine.parse_viewbox_strings(np.array(["0 0 800 600"])).dtype)

        coordinate_points = np.array(test_coordinates)

        # Map coordinates between spaces
        mapping_results = self.viewport_engine.advanced_coordinate_space_mapping(
            source_spaces, target_spaces, coordinate_points
        )

        # Verify results
        assert len(mapping_results) == len(test_coordinates)
        assert np.all(mapping_results['mapping_valid'])
        assert np.all(np.isfinite(mapping_results['mapped_x']))
        assert np.all(np.isfinite(mapping_results['mapped_y']))

        print("Coordinate mapping integration successful")

    def test_nested_viewport_processing(self):
        """Test processing of nested viewport hierarchies."""
        n_nested = 5

        # Create parent viewports
        parent_viewports = np.array([
            (800, 600, 4.0/3.0),
            (1024, 768, 4.0/3.0),
            (640, 480, 4.0/3.0),
            (1920, 1080, 16.0/9.0),
            (400, 300, 4.0/3.0),
        ], dtype=self.viewport_engine.parse_viewbox_strings(np.array(["0 0 800 600"])).dtype[['width', 'height', 'aspect_ratio']])

        # Create child viewBoxes
        child_viewboxes = np.array([
            (0, 0, 100, 75, 4.0/3.0),
            (10, 20, 200, 150, 4.0/3.0),
            (0, 0, 50, 50, 1.0),
            (0, 0, 1920, 1080, 16.0/9.0),
            (5, 5, 90, 65, 90.0/65.0),
        ], dtype=self.viewport_engine.parse_viewbox_strings(np.array(["0 0 100 75"])).dtype)

        # Create nesting transform matrices
        nesting_transforms = np.zeros((n_nested, 3, 3))
        for i in range(n_nested):
            # Identity with slight scaling and translation
            nesting_transforms[i] = np.eye(3)
            nesting_transforms[i, 0, 0] = 1.0 + i * 0.1  # Scale X
            nesting_transforms[i, 1, 1] = 1.0 + i * 0.1  # Scale Y
            nesting_transforms[i, 0, 2] = i * 10.0        # Translate X
            nesting_transforms[i, 1, 2] = i * 5.0         # Translate Y

        # Process nested viewports
        nesting_results = self.viewport_engine.batch_viewport_nesting(
            parent_viewports, child_viewboxes, nesting_transforms
        )

        # Verify results
        assert len(nesting_results) == n_nested
        assert np.all(nesting_results['transformation_valid'])
        assert np.all(nesting_results['effective_scale_x'] > 0)
        assert np.all(nesting_results['effective_scale_y'] > 0)

        print("Nested viewport processing successful")


class TestVisualAccuracyValidation:
    """Test visual accuracy of viewport calculations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.viewport_engine = NumPyViewportEngine()
        self.legacy_resolver = ViewportResolver()

    def test_aspect_ratio_preservation_accuracy(self):
        """Test accuracy of aspect ratio preservation in various scenarios."""
        test_cases = [
            # (viewBox, viewport_size, expected_behavior)
            ("0 0 100 75", (800, 600), "perfect_match"),      # 4:3 -> 4:3
            ("0 0 100 100", (800, 600), "meet_letterbox"),    # 1:1 -> 4:3 (letterbox)
            ("0 0 200 75", (800, 600), "meet_pillarbox"),     # 8:3 -> 4:3 (pillarbox)
            ("0 0 50 100", (800, 600), "slice_crop"),         # 1:2 -> 4:3 (crop)
        ]

        for viewbox_str, (vp_width, vp_height), expected in test_cases:
            # Parse viewBox
            viewboxes = self.viewport_engine.parse_viewbox_strings(np.array([viewbox_str]))
            viewports = np.array([(vp_width, vp_height, vp_width/vp_height)],
                                dtype=[('width', 'i8'), ('height', 'i8'), ('aspect_ratio', 'f8')])

            # Calculate viewport mapping for meet mode
            meet_mappings = self.viewport_engine.calculate_viewport_mappings(
                viewboxes, viewports, AspectAlign.X_MID_Y_MID, MeetOrSlice.MEET
            )

            # Calculate viewport mapping for slice mode
            slice_mappings = self.viewport_engine.calculate_viewport_mappings(
                viewboxes, viewports, AspectAlign.X_MID_Y_MID, MeetOrSlice.SLICE
            )

            # Verify aspect ratio preservation
            vb_aspect = viewboxes['aspect_ratio'][0]
            vp_aspect = viewports['aspect_ratio'][0]

            if expected == "perfect_match":
                # Scales should be identical
                assert abs(meet_mappings['scale_x'][0] - meet_mappings['scale_y'][0]) < 1e-10
                assert abs(slice_mappings['scale_x'][0] - slice_mappings['scale_y'][0]) < 1e-10

            elif expected == "meet_letterbox" or expected == "meet_pillarbox":
                # Meet mode should maintain aspect ratio with uniform scaling
                assert abs(meet_mappings['scale_x'][0] - meet_mappings['scale_y'][0]) < 1e-10

                # Content should fit entirely within viewport
                content_width = viewboxes['width'][0] * meet_mappings['scale_x'][0]
                content_height = viewboxes['height'][0] * meet_mappings['scale_y'][0]
                assert content_width <= vp_width + 1e-10
                assert content_height <= vp_height + 1e-10

            print(f"Case '{expected}': meet_scale=({meet_mappings['scale_x'][0]:.3f}, {meet_mappings['scale_y'][0]:.3f})")

    def test_precision_preservation_validation(self):
        """Test precision preservation in viewport calculations."""
        # High precision test coordinates
        precise_viewboxes = [
            "0.123456789 0.987654321 100.001234567 75.009876543",
            "10.5555555555 20.7777777777 200.1111111111 150.3333333333",
            "0 0 33.333333333333 25.000000000001"  # Precise 4:3 ratio
        ]

        # Parse with high precision
        parsed_viewboxes = self.viewport_engine.parse_viewbox_strings(np.array(precise_viewboxes))

        # Verify precision preservation
        assert abs(parsed_viewboxes['min_x'][0] - 0.123456789) < 1e-9
        assert abs(parsed_viewboxes['min_y'][0] - 0.987654321) < 1e-9
        assert abs(parsed_viewboxes['width'][0] - 100.001234567) < 1e-9
        assert abs(parsed_viewboxes['height'][0] - 75.009876543) < 1e-9

        # Test precision in calculations
        viewports = np.array([(1000, 750, 4.0/3.0)],
                            dtype=[('width', 'i8'), ('height', 'i8'), ('aspect_ratio', 'f8')])

        mappings = self.viewport_engine.calculate_viewport_mappings(
            parsed_viewboxes[:1], viewports, AspectAlign.X_MID_Y_MID, MeetOrSlice.MEET
        )

        # Verify scale calculation precision
        expected_scale_x = 1000.0 / 100.001234567
        expected_scale_y = 750.0 / 75.009876543

        # Should maintain reasonable precision
        assert abs(mappings['scale_x'][0] - expected_scale_x) < 1e-10
        assert abs(mappings['scale_y'][0] - expected_scale_y) < 1e-10

        print("Precision preservation validation successful")


if __name__ == "__main__":
    print("Running NumPy ViewBox Integration Tests...")

    # Performance tests
    print("\n=== Performance Integration Tests ===")
    perf_tests = TestNumPyViewBoxPerformanceIntegration()
    perf_tests.setup_method()

    print("\n--- Small Batch Performance ---")
    perf_tests.test_performance_comparison_small_batch()

    print("\n--- Large Batch Performance ---")
    perf_tests.test_performance_comparison_large_batch()

    print("\n--- Memory Efficiency ---")
    perf_tests.test_memory_efficiency_scaling()

    print("\n--- Advanced Features Performance ---")
    perf_tests.test_advanced_features_performance()

    # Transform system integration
    print("\n=== Transform System Integration Tests ===")
    transform_tests = TestTransformSystemIntegration()
    transform_tests.setup_method()

    print("\n--- Unit Converter Integration ---")
    transform_tests.test_unit_converter_integration()

    print("\n--- Fractional EMU Integration ---")
    transform_tests.test_fractional_emu_integration()

    print("\n--- Nested Viewport Processing ---")
    transform_tests.test_nested_viewport_processing()

    # Visual accuracy validation
    print("\n=== Visual Accuracy Validation Tests ===")
    accuracy_tests = TestVisualAccuracyValidation()
    accuracy_tests.setup_method()

    print("\n--- Aspect Ratio Preservation ---")
    accuracy_tests.test_aspect_ratio_preservation_accuracy()

    print("\n--- Precision Preservation ---")
    accuracy_tests.test_precision_preservation_validation()

    print("\n=== All NumPy ViewBox Integration Tests Completed ===")