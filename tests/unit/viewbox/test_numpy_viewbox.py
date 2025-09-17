#!/usr/bin/env python3
"""
Unit tests for NumPy-based ViewBox system.

Tests the high-performance NumPy viewport engine with vectorized operations,
structured arrays, and batch processing capabilities.
"""

import pytest
import numpy as np
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from src.viewbox.numpy_viewbox import (
    NumPyViewportEngine, ViewBoxArray, ViewportArray, ViewportMappingArray,
    AspectAlign, MeetOrSlice
)
from src.viewbox.legacy import ViewportMapping
from src.units import UnitEngine, ConversionContext, UnitType


class TestNumPyViewportEngineBasics:
    """Basic functionality tests for NumPy viewport engine."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = NumPyViewportEngine()
        self.unit_engine = UnitEngine()
        self.context = ConversionContext(dpi=96.0, viewport_width=800, viewport_height=600)

    def test_engine_initialization(self):
        """Test viewport engine initialization."""
        assert self.engine is not None
        assert hasattr(self.engine, 'unit_engine')
        assert hasattr(self.engine, 'alignment_factors')

        # Check alignment factors array shape
        assert self.engine.alignment_factors.shape == (9, 2)
        assert self.engine.alignment_factors.dtype == np.float64

    def test_viewbox_array_creation(self):
        """Test ViewBox structured array creation."""
        # Test single viewBox
        viewbox_data = np.array([(0.0, 0.0, 100.0, 75.0, 100.0/75.0)], dtype=ViewBoxArray)

        assert len(viewbox_data) == 1
        assert viewbox_data['min_x'][0] == 0.0
        assert viewbox_data['width'][0] == 100.0
        assert viewbox_data['height'][0] == 75.0
        assert abs(viewbox_data['aspect_ratio'][0] - 4.0/3.0) < 1e-10

    def test_viewport_array_creation(self):
        """Test Viewport structured array creation."""
        viewport_data = np.array([(800, 600, 800.0/600.0)], dtype=ViewportArray)

        assert len(viewport_data) == 1
        assert viewport_data['width'][0] == 800
        assert viewport_data['height'][0] == 600
        assert abs(viewport_data['aspect_ratio'][0] - 4.0/3.0) < 1e-10

    def test_viewport_mapping_creation(self):
        """Test ViewportMapping structured array creation."""
        mapping_data = np.array([
            (1.0, 1.0, 0.0, 0.0, 800, 600, 800, 600, False)
        ], dtype=ViewportMappingArray)

        assert len(mapping_data) == 1
        assert mapping_data['scale_x'][0] == 1.0
        assert mapping_data['clip_needed'][0] == False


class TestViewBoxParsing:
    """Test ViewBox string parsing functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = NumPyViewportEngine()

    def test_single_viewbox_parsing(self):
        """Test parsing single viewBox string."""
        viewbox_str = "0 0 100 75"
        result = self.engine.parse_viewbox_strings(np.array([viewbox_str]))

        assert len(result) == 1
        assert result['min_x'][0] == 0.0
        assert result['min_y'][0] == 0.0
        assert result['width'][0] == 100.0
        assert result['height'][0] == 75.0
        assert abs(result['aspect_ratio'][0] - 4.0/3.0) < 1e-10

    def test_batch_viewbox_parsing(self):
        """Test parsing multiple viewBox strings."""
        viewbox_strings = np.array([
            "0 0 100 75",
            "10 20 200 150",
            "0 0 300 300"
        ])

        result = self.engine.parse_viewbox_strings(viewbox_strings)

        assert len(result) == 3

        # First viewBox
        assert result['min_x'][0] == 0.0 and result['width'][0] == 100.0
        # Second viewBox
        assert result['min_x'][1] == 10.0 and result['min_y'][1] == 20.0
        assert result['width'][1] == 200.0 and result['height'][1] == 150.0
        # Third viewBox (square)
        assert result['aspect_ratio'][2] == 1.0

    def test_viewbox_parsing_with_commas(self):
        """Test viewBox parsing with comma separators."""
        viewbox_str = "0,0,100,75"
        result = self.engine.parse_viewbox_strings(np.array([viewbox_str]))

        assert result['width'][0] == 100.0
        assert result['height'][0] == 75.0

    def test_viewbox_parsing_mixed_separators(self):
        """Test viewBox parsing with mixed separators."""
        viewbox_str = "0, 0 100,75"
        result = self.engine.parse_viewbox_strings(np.array([viewbox_str]))

        assert result['width'][0] == 100.0
        assert result['height'][0] == 75.0

    def test_invalid_viewbox_handling(self):
        """Test handling of invalid viewBox strings."""
        invalid_strings = np.array([
            "invalid",
            "0 0 0 100",  # Zero width
            "0 0 100 0",  # Zero height
            "0 0 -100 100"  # Negative width
        ])

        with pytest.warns(UserWarning):
            result = self.engine.parse_viewbox_strings(invalid_strings)

        # Should handle gracefully with fallback values
        assert len(result) == 4
        assert np.all(result['width'] > 0)
        assert np.all(result['height'] > 0)


class TestViewportResolution:
    """Test viewport resolution and mapping calculations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = NumPyViewportEngine()
        self.context = ConversionContext(dpi=96.0, viewport_width=800, viewport_height=600)

    def test_basic_viewport_resolution(self):
        """Test basic viewport to viewBox mapping."""
        # Create test data
        viewboxes = np.array([
            (0.0, 0.0, 100.0, 75.0, 4.0/3.0)
        ], dtype=ViewBoxArray)

        viewports = np.array([
            (800, 600, 4.0/3.0)
        ], dtype=ViewportArray)

        # Perfect aspect ratio match
        mappings = self.engine.calculate_viewport_mappings(
            viewboxes, viewports,
            align=AspectAlign.X_MID_Y_MID,
            meet_or_slice=MeetOrSlice.MEET
        )

        assert len(mappings) == 1
        assert mappings['scale_x'][0] == 8.0  # 800/100
        assert mappings['scale_y'][0] == 8.0  # 600/75
        assert mappings['translate_x'][0] == 0.0
        assert mappings['translate_y'][0] == 0.0

    def test_aspect_ratio_mismatch_meet(self):
        """Test viewport mapping with aspect ratio mismatch using meet."""
        # Wide viewBox in tall viewport
        viewboxes = np.array([
            (0.0, 0.0, 200.0, 100.0, 2.0)
        ], dtype=ViewBoxArray)

        viewports = np.array([
            (400, 600, 2.0/3.0)
        ], dtype=ViewportArray)

        mappings = self.engine.calculate_viewport_mappings(
            viewboxes, viewports,
            align=AspectAlign.X_MID_Y_MID,
            meet_or_slice=MeetOrSlice.MEET
        )

        # Should scale to fit width (limiting dimension)
        expected_scale = 400.0 / 200.0  # 2.0
        assert abs(mappings['scale_x'][0] - expected_scale) < 1e-10
        assert abs(mappings['scale_y'][0] - expected_scale) < 1e-10

        # Should center vertically
        scaled_height = 100.0 * expected_scale  # 200
        extra_height = 600.0 - scaled_height    # 400
        expected_translate_y = extra_height / 2.0  # 200
        assert abs(mappings['translate_y'][0] - expected_translate_y) < 1e-10

    def test_aspect_ratio_mismatch_slice(self):
        """Test viewport mapping with aspect ratio mismatch using slice."""
        # Wide viewBox in tall viewport
        viewboxes = np.array([
            (0.0, 0.0, 200.0, 100.0, 2.0)
        ], dtype=ViewBoxArray)

        viewports = np.array([
            (400, 600, 2.0/3.0)
        ], dtype=ViewportArray)

        mappings = self.engine.calculate_viewport_mappings(
            viewboxes, viewports,
            align=AspectAlign.X_MID_Y_MID,
            meet_or_slice=MeetOrSlice.SLICE
        )

        # Should scale to fit height (fill viewport completely)
        expected_scale = 600.0 / 100.0  # 6.0
        assert abs(mappings['scale_x'][0] - expected_scale) < 1e-10
        assert abs(mappings['scale_y'][0] - expected_scale) < 1e-10

        # Should center horizontally (content will be clipped)
        scaled_width = 200.0 * expected_scale   # 1200
        extra_width = scaled_width - 400.0      # 800
        expected_translate_x = -extra_width / 2.0  # -400
        assert abs(mappings['translate_x'][0] - expected_translate_x) < 1e-10

    def test_batch_viewport_resolution(self):
        """Test batch processing of multiple viewports."""
        # Multiple viewBox/viewport pairs
        viewboxes = np.array([
            (0.0, 0.0, 100.0, 100.0, 1.0),  # Square
            (0.0, 0.0, 200.0, 100.0, 2.0),  # Wide
            (0.0, 0.0, 100.0, 200.0, 0.5),  # Tall
        ], dtype=ViewBoxArray)

        viewports = np.array([
            (400, 400, 1.0),   # Square viewport
            (800, 400, 2.0),   # Wide viewport
            (300, 600, 0.5),   # Tall viewport
        ], dtype=ViewportArray)

        mappings = self.engine.calculate_viewport_mappings(
            viewboxes, viewports,
            align=AspectAlign.X_MID_Y_MID,
            meet_or_slice=MeetOrSlice.MEET
        )

        assert len(mappings) == 3

        # All should have matching aspect ratios (perfect fit)
        assert abs(mappings['scale_x'][0] - 4.0) < 1e-10  # 400/100
        assert abs(mappings['scale_x'][1] - 4.0) < 1e-10  # 800/200
        assert abs(mappings['scale_x'][2] - 3.0) < 1e-10  # 300/100


class TestAlignmentCalculations:
    """Test alignment offset calculations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = NumPyViewportEngine()

    def test_alignment_factors_lookup(self):
        """Test pre-computed alignment factors."""
        # Test each alignment option
        align_cases = [
            (AspectAlign.X_MIN_Y_MIN, [0.0, 0.0]),
            (AspectAlign.X_MID_Y_MIN, [0.5, 0.0]),
            (AspectAlign.X_MAX_Y_MIN, [1.0, 0.0]),
            (AspectAlign.X_MIN_Y_MID, [0.0, 0.5]),
            (AspectAlign.X_MID_Y_MID, [0.5, 0.5]),  # Default
            (AspectAlign.X_MAX_Y_MID, [1.0, 0.5]),
            (AspectAlign.X_MIN_Y_MAX, [0.0, 1.0]),
            (AspectAlign.X_MID_Y_MAX, [0.5, 1.0]),
            (AspectAlign.X_MAX_Y_MAX, [1.0, 1.0]),
        ]

        for align, expected_factors in align_cases:
            factors = self.engine.alignment_factors[align.value]
            assert abs(factors[0] - expected_factors[0]) < 1e-10
            assert abs(factors[1] - expected_factors[1]) < 1e-10

    def test_alignment_offset_calculations(self):
        """Test alignment offset calculations."""
        extra_space = np.array([100.0, 50.0])  # Extra width and height

        # Test different alignments
        test_cases = [
            (AspectAlign.X_MIN_Y_MIN, [0.0, 0.0]),
            (AspectAlign.X_MID_Y_MID, [50.0, 25.0]),  # Center
            (AspectAlign.X_MAX_Y_MAX, [100.0, 50.0]),  # Bottom-right
        ]

        for align, expected_offsets in test_cases:
            offsets = self.engine._calculate_alignment_offsets(
                extra_space.reshape(1, 2),
                np.array([align])
            )

            assert abs(offsets[0, 0] - expected_offsets[0]) < 1e-10
            assert abs(offsets[0, 1] - expected_offsets[1]) < 1e-10

    def test_batch_alignment_calculations(self):
        """Test batch alignment calculations."""
        extra_space = np.array([
            [100.0, 50.0],
            [200.0, 100.0],
            [0.0, 0.0]
        ])

        alignments = np.array([
            AspectAlign.X_MIN_Y_MIN,
            AspectAlign.X_MID_Y_MID,
            AspectAlign.X_MAX_Y_MAX
        ])

        offsets = self.engine._calculate_alignment_offsets(extra_space, alignments)

        assert offsets.shape == (3, 2)

        # Check results
        assert offsets[0, 0] == 0.0 and offsets[0, 1] == 0.0  # Min align
        assert offsets[1, 0] == 100.0 and offsets[1, 1] == 50.0  # Mid align
        assert offsets[2, 0] == 0.0 and offsets[2, 1] == 0.0  # Max align (no extra space)


class TestSVGIntegration:
    """Test integration with SVG element processing."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = NumPyViewportEngine()
        self.context = ConversionContext(dpi=96.0, viewport_width=800, viewport_height=600)

    def test_svg_element_batch_processing(self):
        """Test batch processing of SVG elements."""
        # Simulate SVG elements with different viewBox attributes
        svg_elements = [
            {'viewBox': '0 0 100 75', 'width': '400px', 'height': '300px'},
            {'viewBox': '10 20 200 150', 'width': '800px', 'height': '600px'},
            {'viewBox': '0 0 300 300', 'width': '600px', 'height': '600px'},
        ]

        result = self.engine.batch_resolve_svg_viewports(svg_elements, None, [self.context])

        assert len(result) == 3
        assert all(isinstance(mapping, ViewportMapping) for mapping in result)

        # Check first element (perfect aspect ratio match)
        first_mapping = result[0]
        assert first_mapping.scale_x == 4.0  # 400/100
        assert first_mapping.scale_y == 4.0  # 300/75

    def test_svg_element_without_viewbox(self):
        """Test SVG elements without viewBox attribute."""
        svg_elements = [
            {'width': '400px', 'height': '300px'},  # No viewBox
            {'viewBox': '0 0 100 75', 'width': '400px', 'height': '300px'},
        ]

        result = self.engine.batch_resolve_svg_viewports(svg_elements, None, [self.context])

        assert len(result) == 2

        # First should use identity mapping
        assert result[0].scale_x == 1.0
        assert result[0].scale_y == 1.0
        assert result[0].translate_x == 0.0
        assert result[0].translate_y == 0.0

    def test_preserve_aspect_ratio_parsing(self):
        """Test preserveAspectRatio parsing."""
        test_cases = [
            ('xMidYMid meet', AspectAlign.X_MID_Y_MID, MeetOrSlice.MEET),
            ('xMinYMax slice', AspectAlign.X_MIN_Y_MAX, MeetOrSlice.SLICE),
            ('none', AspectAlign.NONE, MeetOrSlice.MEET),
            ('', AspectAlign.X_MID_Y_MID, MeetOrSlice.MEET),  # Default
        ]

        for preserve_str, expected_align, expected_meet_slice in test_cases:
            align, meet_slice = self.engine._parse_preserve_aspect_ratio(preserve_str)
            assert align == expected_align
            assert meet_slice == expected_meet_slice


class TestPerformanceBenchmarking:
    """Test performance benchmarking capabilities."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = NumPyViewportEngine()
        self.context = ConversionContext(dpi=96.0, viewport_width=800, viewport_height=600)

    def test_benchmark_single_operations(self):
        """Test benchmarking of individual operations."""
        n_operations = 1000

        # Generate test data
        viewbox_strings = np.array([f"0 0 {100+i} {75+i}" for i in range(n_operations)])

        # Benchmark parsing
        benchmark_result = self.engine.benchmark_parsing_performance(viewbox_strings)

        assert 'operations_per_second' in benchmark_result
        assert 'total_time_seconds' in benchmark_result
        assert 'memory_usage_mb' in benchmark_result

        # Should achieve reasonable performance (>10k ops/sec)
        assert benchmark_result['operations_per_second'] > 10000

    def test_benchmark_batch_operations(self):
        """Test benchmarking of batch viewport resolution."""
        n_elements = 5000

        # Generate test SVG elements
        svg_elements = []
        for i in range(n_elements):
            svg_elements.append({
                'viewBox': f'0 0 {100+i%100} {75+i%75}',
                'width': f'{400+i%200}px',
                'height': f'{300+i%150}px'
            })

        # Benchmark batch processing
        benchmark_result = self.engine.benchmark_batch_performance(svg_elements, self.context)

        assert 'elements_per_second' in benchmark_result
        assert 'total_time_seconds' in benchmark_result
        assert 'average_time_per_element_us' in benchmark_result

        # Should achieve target performance (>50k elements/sec)
        assert benchmark_result['elements_per_second'] > 50000

    def test_memory_usage_tracking(self):
        """Test memory usage tracking during operations."""
        n_elements = 1000

        # Process elements and track memory
        svg_elements = [
            {'viewBox': f'0 0 {100+i} {75+i}', 'width': '400px', 'height': '300px'}
            for i in range(n_elements)
        ]

        memory_info = self.engine.get_memory_usage()
        initial_memory = memory_info['total_bytes']

        # Process batch
        result = self.engine.batch_resolve_svg_viewports(svg_elements, None, [self.context])

        final_memory = self.engine.get_memory_usage()['total_bytes']
        memory_increase = final_memory - initial_memory

        # Memory increase should be reasonable (<10MB for 1k elements)
        assert memory_increase < 10 * 1024 * 1024
        assert len(result) == n_elements


class TestEdgeCases:
    """Test edge cases and error handling."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = NumPyViewportEngine()

    def test_zero_dimension_handling(self):
        """Test handling of zero dimensions."""
        viewboxes = np.array([
            (0.0, 0.0, 0.0, 100.0, 0.0),  # Zero width
            (0.0, 0.0, 100.0, 0.0, np.inf),  # Zero height
        ], dtype=ViewBoxArray)

        viewports = np.array([
            (400, 300, 4.0/3.0),
            (400, 300, 4.0/3.0),
        ], dtype=ViewportArray)

        with pytest.warns(UserWarning):
            mappings = self.engine.calculate_viewport_mappings(
                viewboxes, viewports,
                align=AspectAlign.X_MID_Y_MID,
                meet_or_slice=MeetOrSlice.MEET
            )

        # Should handle gracefully with identity transform
        assert len(mappings) == 2
        assert np.all(np.isfinite(mappings['scale_x']))
        assert np.all(np.isfinite(mappings['scale_y']))

    def test_extreme_values_handling(self):
        """Test handling of extreme coordinate values."""
        viewboxes = np.array([
            (-1e6, -1e6, 2e6, 2e6, 1.0),  # Very large coordinates
            (1e-10, 1e-10, 1e-10, 1e-10, 1.0),  # Very small coordinates
        ], dtype=ViewBoxArray)

        viewports = np.array([
            (400, 400, 1.0),
            (400, 400, 1.0),
        ], dtype=ViewportArray)

        mappings = self.engine.calculate_viewport_mappings(
            viewboxes, viewports,
            align=AspectAlign.X_MID_Y_MID,
            meet_or_slice=MeetOrSlice.MEET
        )

        # Should handle without errors
        assert len(mappings) == 2
        assert np.all(np.isfinite(mappings['scale_x']))
        assert np.all(np.isfinite(mappings['scale_y']))

    def test_invalid_aspect_ratio_handling(self):
        """Test handling of invalid aspect ratios."""
        with pytest.warns(UserWarning):
            result = self.engine._parse_preserve_aspect_ratio("invalid_value")

        # Should return default values
        assert result[0] == AspectAlign.X_MID_Y_MID
        assert result[1] == MeetOrSlice.MEET


if __name__ == "__main__":
    print("Running NumPy ViewBox System Tests...")

    # Run basic functionality tests
    test_basics = TestNumPyViewportEngineBasics()
    test_basics.setup_method()

    print("✓ Testing engine initialization...")
    test_basics.test_engine_initialization()

    print("✓ Testing structured array creation...")
    test_basics.test_viewbox_array_creation()
    test_basics.test_viewport_array_creation()
    test_basics.test_viewport_mapping_creation()

    # Run ViewBox parsing tests
    test_parsing = TestViewBoxParsing()
    test_parsing.setup_method()

    print("✓ Testing ViewBox parsing...")
    test_parsing.test_single_viewbox_parsing()
    test_parsing.test_batch_viewbox_parsing()
    test_parsing.test_viewbox_parsing_with_commas()

    # Run viewport resolution tests
    test_resolution = TestViewportResolution()
    test_resolution.setup_method()

    print("✓ Testing viewport resolution...")
    test_resolution.test_basic_viewport_resolution()
    test_resolution.test_aspect_ratio_mismatch_meet()
    test_resolution.test_batch_viewport_resolution()

    print("=== All NumPy ViewBox Tests Passed ===")