#!/usr/bin/env python3
"""
Unit tests for NumPy Linear Gradient Engine.

Tests vectorized linear gradient calculations, batch color stop interpolation,
and efficient gradient direction handling implemented in the linear gradient engine.
"""

import numpy as np
import pytest
from typing import List
import xml.etree.ElementTree as ET
import sys
import os
import time

# Add source path for direct imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../../../'))

from src.converters.gradients.linear_gradient_engine import (
    LinearGradientEngine,
    LinearGradientParams,
    create_linear_gradient_engine,
    process_linear_gradients_fast
)
from src.converters.gradients.numpy_gradient_engine import (
    NumPyColorProcessor,
    NumPyTransformProcessor
)


class TestLinearGradientEngine:
    """Test suite for Linear Gradient Engine vectorized operations."""

    @pytest.fixture
    def color_processor(self):
        """Create color processor for testing."""
        return NumPyColorProcessor()

    @pytest.fixture
    def transform_processor(self):
        """Create transform processor for testing."""
        return NumPyTransformProcessor()

    @pytest.fixture
    def gradient_engine(self, color_processor, transform_processor):
        """Create linear gradient engine for testing."""
        return LinearGradientEngine(color_processor, transform_processor)

    @pytest.fixture
    def simple_linear_gradients(self):
        """Create simple linear gradient elements for testing."""
        gradients = []

        # Simple horizontal gradient
        grad1 = ET.Element('linearGradient')
        grad1.set('id', 'grad1')
        grad1.set('x1', '0%')
        grad1.set('y1', '0%')
        grad1.set('x2', '100%')
        grad1.set('y2', '0%')

        stop1a = ET.SubElement(grad1, 'stop')
        stop1a.set('offset', '0%')
        stop1a.set('stop-color', '#ff0000')

        stop1b = ET.SubElement(grad1, 'stop')
        stop1b.set('offset', '100%')
        stop1b.set('stop-color', '#0000ff')

        gradients.append(grad1)

        # Simple vertical gradient
        grad2 = ET.Element('linearGradient')
        grad2.set('id', 'grad2')
        grad2.set('x1', '0%')
        grad2.set('y1', '0%')
        grad2.set('x2', '0%')
        grad2.set('y2', '100%')

        stop2a = ET.SubElement(grad2, 'stop')
        stop2a.set('offset', '0%')
        stop2a.set('stop-color', '#00ff00')

        stop2b = ET.SubElement(grad2, 'stop')
        stop2b.set('offset', '100%')
        stop2b.set('stop-color', '#ffff00')

        gradients.append(grad2)

        # Diagonal gradient
        grad3 = ET.Element('linearGradient')
        grad3.set('id', 'grad3')
        grad3.set('x1', '0%')
        grad3.set('y1', '0%')
        grad3.set('x2', '100%')
        grad3.set('y2', '100%')

        stop3a = ET.SubElement(grad3, 'stop')
        stop3a.set('offset', '0%')
        stop3a.set('stop-color', 'black')

        stop3b = ET.SubElement(grad3, 'stop')
        stop3b.set('offset', '50%')
        stop3b.set('stop-color', 'gray')

        stop3c = ET.SubElement(grad3, 'stop')
        stop3c.set('offset', '100%')
        stop3c.set('stop-color', 'white')

        gradients.append(grad3)

        return gradients

    @pytest.fixture
    def complex_linear_gradients(self):
        """Create complex linear gradient elements for testing."""
        gradients = []

        # Gradient with transform
        grad1 = ET.Element('linearGradient')
        grad1.set('id', 'complex1')
        grad1.set('x1', '0')
        grad1.set('y1', '0')
        grad1.set('x2', '1')
        grad1.set('y2', '0')
        grad1.set('gradientTransform', 'rotate(45) scale(2)')

        stop1a = ET.SubElement(grad1, 'stop')
        stop1a.set('offset', '0')
        stop1a.set('stop-color', '#ff6600')
        stop1a.set('stop-opacity', '0.8')

        stop1b = ET.SubElement(grad1, 'stop')
        stop1b.set('offset', '0.5')
        stop1b.set('stop-color', 'hsl(120, 100%, 50%)')

        stop1c = ET.SubElement(grad1, 'stop')
        stop1c.set('offset', '1')
        stop1c.set('stop-color', 'rgba(0, 100, 200, 0.6)')

        gradients.append(grad1)

        # Gradient with style attributes
        grad2 = ET.Element('linearGradient')
        grad2.set('id', 'complex2')
        grad2.set('x1', '0.2')
        grad2.set('y1', '0.3')
        grad2.set('x2', '0.8')
        grad2.set('y2', '0.7')

        stop2a = ET.SubElement(grad2, 'stop')
        stop2a.set('offset', '10%')
        stop2a.set('style', 'stop-color: #336699; stop-opacity: 0.9')

        stop2b = ET.SubElement(grad2, 'stop')
        stop2b.set('offset', '90%')
        stop2b.set('style', 'stop-color: rgb(255, 128, 64); stop-opacity: 0.7')

        gradients.append(grad2)

        return gradients

    # ==================== Coordinate Parsing Tests ====================

    def test_parse_coordinates_basic(self, gradient_engine, simple_linear_gradients):
        """Test basic coordinate parsing functionality."""
        coordinates = gradient_engine._parse_coordinates_batch(simple_linear_gradients)

        assert coordinates.shape == (3, 4)
        assert coordinates.dtype == np.float64

        # Check horizontal gradient (grad1): 0%, 0%, 100%, 0%
        np.testing.assert_array_almost_equal(coordinates[0], [0.0, 0.0, 1.0, 0.0])

        # Check vertical gradient (grad2): 0%, 0%, 0%, 100%
        np.testing.assert_array_almost_equal(coordinates[1], [0.0, 0.0, 0.0, 1.0])

        # Check diagonal gradient (grad3): 0%, 0%, 100%, 100%
        np.testing.assert_array_almost_equal(coordinates[2], [0.0, 0.0, 1.0, 1.0])

    def test_parse_coordinates_decimal_values(self, gradient_engine):
        """Test coordinate parsing with decimal values."""
        grad = ET.Element('linearGradient')
        grad.set('x1', '0.25')
        grad.set('y1', '0.75')
        grad.set('x2', '0.8')
        grad.set('y2', '0.2')

        coordinates = gradient_engine._parse_coordinates_batch([grad])

        expected = np.array([[0.25, 0.75, 0.8, 0.2]])
        np.testing.assert_array_almost_equal(coordinates, expected)

    def test_parse_coordinates_missing_values(self, gradient_engine):
        """Test coordinate parsing with missing values (uses defaults)."""
        grad = ET.Element('linearGradient')
        grad.set('x2', '50%')  # Only set x2, others should use defaults

        coordinates = gradient_engine._parse_coordinates_batch([grad])

        # Expected: x1=0%, y1=0%, x2=50%, y2=0% (defaults)
        expected = np.array([[0.0, 0.0, 0.5, 0.0]])
        np.testing.assert_array_almost_equal(coordinates, expected)

    def test_parse_coordinates_invalid_values(self, gradient_engine):
        """Test coordinate parsing with invalid values."""
        grad = ET.Element('linearGradient')
        grad.set('x1', 'invalid')
        grad.set('y1', '')
        grad.set('x2', 'NaN')
        grad.set('y2', '200%')  # Valid but will be clamped

        coordinates = gradient_engine._parse_coordinates_batch([grad])

        # Invalid values should use defaults, 200% should be clamped
        assert coordinates.shape == (1, 4)
        assert np.isfinite(coordinates).all()  # All values should be finite
        assert coordinates[0, 3] == 2.0  # 200% = 2.0, within clamp range

    # ==================== Angle Calculation Tests ====================

    def test_calculate_angles_basic_directions(self, gradient_engine):
        """Test angle calculation for basic gradient directions."""
        # Test coordinates for different directions
        coordinates = np.array([
            [0, 0, 1, 0],    # Horizontal right (0°)
            [0, 0, 0, 1],    # Vertical down (90°)
            [0, 0, -1, 0],   # Horizontal left (180°)
            [0, 0, 0, -1],   # Vertical up (270°)
            [0, 0, 1, 1],    # Diagonal down-right (45°)
        ])

        angles = gradient_engine._calculate_angles_batch(coordinates)

        assert len(angles) == 5
        assert angles.dtype == np.int32

        # DrawingML angles are in units of 1/60000 degrees
        # and start from 3 o'clock going clockwise

        # Horizontal right: should be 90° in DrawingML (90 * 60000 = 5400000)
        assert abs(angles[0] - 5400000) < 60000  # Allow small tolerance

        # Vertical down: should be 0° in DrawingML (0 * 60000 = 0)
        assert abs(angles[1] - 0) < 60000

        # All angles should be in valid range [0, 21600000)
        assert np.all(angles >= 0)
        assert np.all(angles < 21600000)

    def test_calculate_angles_zero_length(self, gradient_engine):
        """Test angle calculation for zero-length gradients."""
        # Zero-length gradient (same start and end points)
        coordinates = np.array([
            [0.5, 0.5, 0.5, 0.5],  # Same point
            [0, 0, 0, 0],          # Origin
        ])

        angles = gradient_engine._calculate_angles_batch(coordinates)

        assert len(angles) == 2
        # Should default to horizontal (right direction)
        assert np.all(angles == 5400000)  # 90° in DrawingML

    # ==================== Stop Processing Tests ====================

    def test_process_stops_basic(self, gradient_engine, simple_linear_gradients):
        """Test basic gradient stop processing."""
        all_stops = gradient_engine._process_stops_batch(simple_linear_gradients)

        assert len(all_stops) == 3

        # Check first gradient stops (red to blue)
        stops1 = all_stops[0]
        assert len(stops1) == 2
        assert stops1.dtype.names == ('position', 'rgb', 'opacity')

        # Check positions
        assert stops1[0]['position'] == 0.0
        assert stops1[1]['position'] == 1.0

        # Check colors
        np.testing.assert_array_equal(stops1[0]['rgb'], [255, 0, 0])  # Red
        np.testing.assert_array_equal(stops1[1]['rgb'], [0, 0, 255])  # Blue

        # Check opacities
        assert stops1[0]['opacity'] == 1.0
        assert stops1[1]['opacity'] == 1.0

    def test_process_stops_with_opacity(self, gradient_engine, complex_linear_gradients):
        """Test stop processing with opacity values."""
        all_stops = gradient_engine._process_stops_batch(complex_linear_gradients)

        # Check first complex gradient
        stops = all_stops[0]
        assert len(stops) >= 2

        # Should have some stops with opacity < 1.0
        has_transparency = np.any(stops['opacity'] < 1.0)
        assert has_transparency

    def test_process_stops_empty_gradient(self, gradient_engine):
        """Test stop processing for gradient with no stops."""
        grad = ET.Element('linearGradient')
        grad.set('id', 'empty')

        all_stops = gradient_engine._process_stops_batch([grad])

        assert len(all_stops) == 1
        stops = all_stops[0]

        # Should create default stops
        assert len(stops) == 2
        assert stops[0]['position'] == 0.0
        assert stops[1]['position'] == 1.0

    def test_process_stops_single_stop(self, gradient_engine):
        """Test stop processing for gradient with single stop."""
        grad = ET.Element('linearGradient')
        grad.set('id', 'single')

        stop = ET.SubElement(grad, 'stop')
        stop.set('offset', '50%')
        stop.set('stop-color', '#ff0000')

        all_stops = gradient_engine._process_stops_batch([grad])

        stops = all_stops[0]
        # Should expand to two stops at positions 0.0 and 1.0
        assert len(stops) == 2
        assert stops[0]['position'] == 0.0
        assert stops[1]['position'] == 1.0
        # Both should have the same color
        np.testing.assert_array_equal(stops[0]['rgb'], stops[1]['rgb'])

    def test_process_stops_sorting(self, gradient_engine):
        """Test that stops are properly sorted by position."""
        grad = ET.Element('linearGradient')

        # Add stops in reverse order
        stop3 = ET.SubElement(grad, 'stop')
        stop3.set('offset', '100%')
        stop3.set('stop-color', '#0000ff')

        stop1 = ET.SubElement(grad, 'stop')
        stop1.set('offset', '0%')
        stop1.set('stop-color', '#ff0000')

        stop2 = ET.SubElement(grad, 'stop')
        stop2.set('offset', '50%')
        stop2.set('stop-color', '#00ff00')

        all_stops = gradient_engine._process_stops_batch([grad])

        stops = all_stops[0]
        assert len(stops) == 3

        # Should be sorted by position
        assert stops[0]['position'] == 0.0  # Red
        assert stops[1]['position'] == 0.5  # Green
        assert stops[2]['position'] == 1.0  # Blue

        np.testing.assert_array_equal(stops[0]['rgb'], [255, 0, 0])    # Red
        np.testing.assert_array_equal(stops[1]['rgb'], [0, 255, 0])    # Green
        np.testing.assert_array_equal(stops[2]['rgb'], [0, 0, 255])    # Blue

    # ==================== XML Generation Tests ====================

    def test_generate_xml_basic(self, gradient_engine, simple_linear_gradients):
        """Test basic XML generation functionality."""
        # Process gradients to get angles and stops
        coordinates = gradient_engine._parse_coordinates_batch(simple_linear_gradients)
        angles = gradient_engine._calculate_angles_batch(coordinates)
        all_stops = gradient_engine._process_stops_batch(simple_linear_gradients)

        xml_results = gradient_engine._generate_xml_batch(angles, all_stops, simple_linear_gradients)

        assert len(xml_results) == 3

        for xml in xml_results:
            assert isinstance(xml, str)
            assert '<a:gradFill' in xml
            assert '<a:gsLst>' in xml
            assert '<a:gs pos=' in xml
            assert '<a:srgbClr val=' in xml
            assert '<a:lin ang=' in xml
            assert '</a:gradFill>' in xml

    def test_generate_xml_with_opacity(self, gradient_engine, complex_linear_gradients):
        """Test XML generation with opacity attributes."""
        coordinates = gradient_engine._parse_coordinates_batch(complex_linear_gradients)
        angles = gradient_engine._calculate_angles_batch(coordinates)
        all_stops = gradient_engine._process_stops_batch(complex_linear_gradients)

        xml_results = gradient_engine._generate_xml_batch(angles, all_stops, complex_linear_gradients)

        # Should contain alpha attributes for transparent stops
        has_alpha = any('alpha=' in xml for xml in xml_results)
        assert has_alpha

    # ==================== Integration Tests ====================

    def test_process_linear_gradients_batch_complete(self, gradient_engine, simple_linear_gradients):
        """Test complete batch processing pipeline."""
        xml_results = gradient_engine.process_linear_gradients_batch(simple_linear_gradients)

        assert len(xml_results) == 3

        for xml in xml_results:
            # Validate XML structure
            assert '<a:gradFill' in xml
            assert '</a:gradFill>' in xml
            assert '<a:lin ang=' in xml

    def test_process_linear_gradients_batch_complex(self, gradient_engine, complex_linear_gradients):
        """Test batch processing with complex gradients."""
        xml_results = gradient_engine.process_linear_gradients_batch(complex_linear_gradients)

        assert len(xml_results) == len(complex_linear_gradients)

        for xml in xml_results:
            # Should be valid DrawingML
            assert xml.startswith('<a:gradFill')
            assert xml.endswith('</a:gradFill>')

    def test_process_empty_list(self, gradient_engine):
        """Test processing empty gradient list."""
        xml_results = gradient_engine.process_linear_gradients_batch([])
        assert xml_results == []

    # ==================== Transform Integration Tests ====================

    def test_transform_integration(self, gradient_engine):
        """Test gradient processing with transformations."""
        grad = ET.Element('linearGradient')
        grad.set('x1', '0')
        grad.set('y1', '0')
        grad.set('x2', '1')
        grad.set('y2', '0')
        grad.set('gradientTransform', 'rotate(45)')

        stop1 = ET.SubElement(grad, 'stop')
        stop1.set('offset', '0%')
        stop1.set('stop-color', '#ff0000')

        stop2 = ET.SubElement(grad, 'stop')
        stop2.set('offset', '100%')
        stop2.set('stop-color', '#0000ff')

        xml_results = gradient_engine.process_linear_gradients_batch([grad])

        assert len(xml_results) == 1
        # Should have processed the transform and generated valid XML
        assert '<a:lin ang=' in xml_results[0]

    def test_matrix_transform_integration(self, gradient_engine):
        """Test gradient processing with matrix transforms."""
        grad = ET.Element('linearGradient')
        grad.set('x1', '0')
        grad.set('y1', '0')
        grad.set('x2', '1')
        grad.set('y2', '0')
        grad.set('gradientTransform', 'matrix(1.5, 0, 0, 2, 10, 20)')

        stop1 = ET.SubElement(grad, 'stop')
        stop1.set('offset', '0%')
        stop1.set('stop-color', 'red')

        stop2 = ET.SubElement(grad, 'stop')
        stop2.set('offset', '100%')
        stop2.set('stop-color', 'blue')

        xml_results = gradient_engine.process_linear_gradients_batch([grad])

        assert len(xml_results) == 1
        assert '<a:gradFill' in xml_results[0]

    # ==================== Performance Tests ====================

    def test_batch_processing_performance(self, gradient_engine):
        """Test performance scaling of batch processing."""
        # Create many similar gradients
        n_gradients = 100
        gradients = []

        for i in range(n_gradients):
            grad = ET.Element('linearGradient')
            grad.set('id', f'perf_grad_{i}')
            grad.set('x1', f'{i%100}%')
            grad.set('y1', '0%')
            grad.set('x2', f'{(i+50)%100}%')
            grad.set('y2', '100%')

            stop1 = ET.SubElement(grad, 'stop')
            stop1.set('offset', '0%')
            stop1.set('stop-color', f'#{(i*123)%255:02x}{(i*45)%255:02x}{(i*67)%255:02x}')

            stop2 = ET.SubElement(grad, 'stop')
            stop2.set('offset', '100%')
            stop2.set('stop-color', f'#{(i*89)%255:02x}{(i*156)%255:02x}{(i*234)%255:02x}')

            gradients.append(grad)

        # Measure batch processing time
        start_time = time.perf_counter()
        xml_results = gradient_engine.process_linear_gradients_batch(gradients)
        elapsed = time.perf_counter() - start_time

        assert len(xml_results) == n_gradients
        assert elapsed < 1.0  # Should process 100 gradients in under 1 second
        print(f"Processed {n_gradients} linear gradients in {elapsed:.3f}s ({n_gradients/elapsed:.0f} gradients/sec)")

    def test_coordinate_parsing_performance(self, gradient_engine):
        """Test coordinate parsing performance scaling."""
        # Create gradients with various coordinate formats
        n_gradients = 500
        gradients = []

        coord_formats = ['0%', '50%', '100%', '0.0', '0.5', '1.0', '0', '50', '100']

        for i in range(n_gradients):
            grad = ET.Element('linearGradient')
            grad.set('x1', coord_formats[i % len(coord_formats)])
            grad.set('y1', coord_formats[(i+1) % len(coord_formats)])
            grad.set('x2', coord_formats[(i+2) % len(coord_formats)])
            grad.set('y2', coord_formats[(i+3) % len(coord_formats)])
            gradients.append(grad)

        start_time = time.perf_counter()
        coordinates = gradient_engine._parse_coordinates_batch(gradients)
        elapsed = time.perf_counter() - start_time

        assert coordinates.shape == (n_gradients, 4)
        assert elapsed < 0.1  # Should be very fast
        print(f"Parsed {n_gradients} coordinate sets in {elapsed:.4f}s ({n_gradients/elapsed:.0f} sets/sec)")

    # ==================== Enhancement Tests ====================

    def test_gradient_smoothness_enhancement_basic(self, gradient_engine):
        """Test basic gradient smoothness enhancement."""
        # Create simple gradient with 2 stops
        stop_dtype = np.dtype([
            ('position', 'f4'),
            ('rgb', '3u1'),
            ('opacity', 'f4')
        ])

        original_stops = np.array([
            (0.0, [255, 0, 0], 1.0),    # Red
            (1.0, [0, 0, 255], 1.0)     # Blue
        ], dtype=stop_dtype)

        # Enhance with basic level
        enhanced_stops = gradient_engine.enhance_gradient_smoothness(original_stops, enhancement_level=1)

        assert len(enhanced_stops) > len(original_stops)
        assert enhanced_stops[0]['position'] == 0.0
        assert enhanced_stops[-1]['position'] == 1.0

        # All positions should be sorted
        positions = enhanced_stops['position']
        assert np.all(positions[:-1] <= positions[1:])

    def test_gradient_smoothness_enhancement_advanced(self, gradient_engine):
        """Test advanced gradient smoothness enhancement."""
        stop_dtype = np.dtype([
            ('position', 'f4'),
            ('rgb', '3u1'),
            ('opacity', 'f4')
        ])

        original_stops = np.array([
            (0.0, [255, 0, 0], 1.0),      # Red
            (0.5, [0, 255, 0], 0.8),      # Green with transparency
            (1.0, [0, 0, 255], 1.0)       # Blue
        ], dtype=stop_dtype)

        # Enhance with advanced level
        enhanced_stops = gradient_engine.enhance_gradient_smoothness(original_stops, enhancement_level=2)

        assert len(enhanced_stops) > len(original_stops)

        # Check that intermediate stops were properly interpolated
        mid_stops = enhanced_stops[1:-1]  # Exclude first and last
        assert len(mid_stops) > 0

        # All positions should be in valid range
        assert np.all(enhanced_stops['position'] >= 0.0)
        assert np.all(enhanced_stops['position'] <= 1.0)

        # All opacities should be in valid range
        assert np.all(enhanced_stops['opacity'] >= 0.0)
        assert np.all(enhanced_stops['opacity'] <= 1.0)

    # ==================== Convenience Function Tests ====================

    def test_process_linear_gradients_fast(self, simple_linear_gradients):
        """Test convenience function for fast processing."""
        xml_results = process_linear_gradients_fast(simple_linear_gradients)

        assert len(xml_results) == len(simple_linear_gradients)

        for xml in xml_results:
            assert '<a:gradFill' in xml
            assert '</a:gradFill>' in xml

    def test_create_linear_gradient_engine(self):
        """Test factory function for creating linear gradient engine."""
        color_processor = NumPyColorProcessor()
        transform_processor = NumPyTransformProcessor()

        engine = create_linear_gradient_engine(color_processor, transform_processor)

        assert isinstance(engine, LinearGradientEngine)
        assert engine.color_processor is color_processor
        assert engine.transform_processor is transform_processor

    # ==================== Error Handling Tests ====================

    def test_malformed_gradient_handling(self, gradient_engine):
        """Test handling of malformed gradient elements."""
        # Create malformed gradient
        grad = ET.Element('linearGradient')
        # No attributes, no stops

        xml_results = gradient_engine.process_linear_gradients_batch([grad])

        assert len(xml_results) == 1
        # Should generate valid XML with defaults
        assert '<a:gradFill' in xml_results[0]

    def test_invalid_color_handling(self, gradient_engine):
        """Test handling of invalid color values in stops."""
        grad = ET.Element('linearGradient')

        stop1 = ET.SubElement(grad, 'stop')
        stop1.set('offset', '0%')
        stop1.set('stop-color', 'invalid-color')

        stop2 = ET.SubElement(grad, 'stop')
        stop2.set('offset', '100%')
        stop2.set('stop-color', '#$%^&*')  # Invalid hex

        xml_results = gradient_engine.process_linear_gradients_batch([grad])

        assert len(xml_results) == 1
        # Should handle invalid colors gracefully
        assert '<a:gradFill' in xml_results[0]

    def test_invalid_transform_handling(self, gradient_engine):
        """Test handling of invalid transformation strings."""
        grad = ET.Element('linearGradient')
        grad.set('gradientTransform', 'invalid-transform-string')

        stop1 = ET.SubElement(grad, 'stop')
        stop1.set('offset', '0%')
        stop1.set('stop-color', 'red')

        stop2 = ET.SubElement(grad, 'stop')
        stop2.set('offset', '100%')
        stop2.set('stop-color', 'blue')

        xml_results = gradient_engine.process_linear_gradients_batch([grad])

        assert len(xml_results) == 1
        # Should handle invalid transforms gracefully (use identity)
        assert '<a:gradFill' in xml_results[0]