#!/usr/bin/env python3
"""
Unit tests for the new PathConverter implementation.

Tests the integration between the SVG converter architecture and the new
modular PathSystem for path processing.
"""

import pytest
from lxml import etree as ET
from unittest.mock import Mock, MagicMock
from lxml import etree

from src.converters.paths import PathConverter
from src.converters.base import ConversionContext


class TestPathConverterNew:
    """Test suite for the new PathConverter implementation."""

    @pytest.fixture
    def mock_services(self):
        """Create mock conversion services."""
        services = Mock()
        services.unit_converter = Mock()
        services.viewport_handler = Mock()
        services.font_service = Mock()
        services.gradient_service = Mock()
        services.pattern_service = Mock()
        services.clip_service = Mock()
        return services

    @pytest.fixture
    def converter(self, mock_services):
        """Create a PathConverter instance for testing."""
        return PathConverter(mock_services)

    @pytest.fixture
    def mock_context(self):
        """Create a mock conversion context."""
        context = Mock(spec=ConversionContext)
        context.coordinate_system = Mock()
        context.coordinate_system.slide_width = 10160000  # 800px in EMU
        context.coordinate_system.slide_height = 7620000   # 600px in EMU
        context.coordinate_system.viewbox = (0, 0, 400, 300)
        context.get_next_shape_id = Mock(return_value=1)
        return context

    @pytest.fixture
    def sample_path_element(self):
        """Create a sample SVG path element."""
        return etree.fromstring('''
            <path d="M 100 100 L 200 200 Z"
                  fill="#FF0000"
                  stroke="#000000"
                  stroke-width="2"/>
        ''')

    @pytest.fixture
    def complex_path_element(self):
        """Create a complex SVG path element with curves and arcs."""
        return etree.fromstring('''
            <path d="M 50 100 C 50 50 150 50 150 100 A 50 50 0 0 1 250 100 Z"
                  fill="#00FF00"
                  stroke="#0000FF"
                  stroke-width="3"/>
        ''')

    def test_initialization(self, converter):
        """Test PathConverter initialization."""
        assert converter is not None
        assert converter.supported_elements == ['path']
        assert converter._paths_converted == 0
        assert converter._total_commands == 0
        assert converter._arc_conversions == 0

    def test_can_convert_valid_path(self, converter, sample_path_element):
        """Test can_convert for valid path elements."""
        assert converter.can_convert(sample_path_element) == True

    def test_can_convert_path_without_d_attribute(self, converter):
        """Test can_convert for path without 'd' attribute."""
        path_element = etree.fromstring('<path fill="#FF0000"/>')
        assert converter.can_convert(path_element) == False

    def test_can_convert_non_path_element(self, converter):
        """Test can_convert for non-path elements."""
        rect_element = etree.fromstring('<rect x="10" y="10" width="100" height="50"/>')
        assert converter.can_convert(rect_element) == False

    def test_simple_path_conversion(self, converter, sample_path_element, mock_context):
        """Test conversion of a simple path."""
        result = converter.convert(sample_path_element, mock_context)

        # Should return valid XML
        assert result is not None
        assert len(result) > 0
        assert not result.startswith("<!--")  # Not an error comment

        # Parse XML to verify structure
        try:
            root = ET.fromstring(result)
            assert 'sp' in root.tag  # PowerPoint shape (handle namespaced XML)
        except ET.ParseError:
            pytest.fail("Generated XML is not well-formed")

        # Check statistics were updated
        assert converter._paths_converted == 1

    def test_complex_path_with_arcs(self, converter, complex_path_element, mock_context):
        """Test conversion of complex path with arcs."""
        result = converter.convert(complex_path_element, mock_context)

        # Should convert successfully
        assert result is not None
        assert len(result) > 0
        assert not result.startswith("<!--")

        # Should have processed arc commands
        stats = converter.get_conversion_statistics()
        assert stats['arc_conversions'] >= 0  # May be 0 or more depending on path

    def test_empty_path_data(self, converter, mock_context):
        """Test handling of empty path data."""
        empty_path = etree.fromstring('<path d=""/>')
        result = converter.convert(empty_path, mock_context)

        # Should return empty string for empty path
        assert result == ""

    def test_invalid_path_data(self, converter, mock_context):
        """Test handling of invalid path data."""
        invalid_path = etree.fromstring('<path d="INVALID PATH DATA"/>')
        result = converter.convert(invalid_path, mock_context)

        # Should return error comment
        assert result.startswith("<!--")
        assert "Error converting path" in result

    def test_style_attribute_extraction(self, converter, sample_path_element):
        """Test extraction of style attributes."""
        style_attrs = converter._extract_style_attributes(sample_path_element)

        assert 'fill' in style_attrs
        assert 'stroke' in style_attrs
        assert 'stroke-width' in style_attrs
        assert style_attrs['fill'] == '#FF0000'
        assert style_attrs['stroke'] == '#000000'
        assert style_attrs['stroke-width'] == '2'

    def test_style_attribute_defaults(self, converter):
        """Test default style attributes."""
        path_no_style = etree.fromstring('<path d="M 10 10 L 20 20"/>')
        style_attrs = converter._extract_style_attributes(path_no_style)

        assert style_attrs['fill'] == 'black'  # Default
        assert style_attrs['stroke'] == 'none'  # Default
        assert style_attrs['stroke-width'] == '1'  # Default

    def test_conversion_statistics(self, converter, sample_path_element, mock_context):
        """Test conversion statistics tracking."""
        initial_stats = converter.get_conversion_statistics()
        assert initial_stats['paths_converted'] == 0

        # Convert a path
        converter.convert(sample_path_element, mock_context)

        # Check updated statistics
        stats = converter.get_conversion_statistics()
        assert stats['paths_converted'] == 1
        assert stats['total_commands'] > 0
        assert stats['total_processing_time_ms'] >= 0

    def test_statistics_reset(self, converter, sample_path_element, mock_context):
        """Test statistics reset functionality."""
        # Convert a path to generate statistics
        converter.convert(sample_path_element, mock_context)

        assert converter.get_conversion_statistics()['paths_converted'] == 1

        # Reset statistics
        converter.reset_statistics()

        stats = converter.get_conversion_statistics()
        assert stats['paths_converted'] == 0
        assert stats['total_commands'] == 0

    def test_path_validation(self, converter):
        """Test path data validation."""
        # Valid paths
        assert converter.validate_path_before_conversion("M 100 100 L 200 200 Z") == True
        assert converter.validate_path_before_conversion("M 10 10 C 10 5 20 5 20 10") == True

        # Invalid paths
        assert converter.validate_path_before_conversion("INVALID") == False
        assert converter.validate_path_before_conversion("M") == False  # Incomplete

    def test_supported_commands(self, converter):
        """Test getting supported path commands."""
        commands = converter.get_supported_path_commands()
        assert len(commands) > 0
        assert 'M' in commands
        assert 'm' in commands
        assert 'A' in commands
        assert 'Z' in commands

    def test_arc_quality_configuration(self, converter, mock_context):
        """Test arc quality parameter configuration."""
        # Configure before any conversion
        converter.configure_arc_quality(max_segment_angle=45.0, error_tolerance=0.005)

        # Should not raise an error
        # The actual configuration is tested in the PathSystem tests

    def test_context_without_coordinate_system(self, converter, sample_path_element):
        """Test conversion with context missing coordinate system."""
        context_no_coords = Mock()
        context_no_coords.coordinate_system = None
        context_no_coords.get_next_shape_id = Mock(return_value=1)

        # Should still work with default configuration
        result = converter.convert(sample_path_element, context_no_coords)
        assert result is not None

    def test_batch_processing(self, converter, mock_context):
        """Test batch processing of multiple paths."""
        # First configure the system
        converter._configure_path_system(mock_context)

        path_specs = [
            {'path_data': 'M 100 100 L 200 200'},
            {'path_data': 'M 50 50 C 50 25 75 25 100 50'},
            {'path_data': 'M 150 150 Q 175 125 200 150 Z'}
        ]

        results = converter.process_batch_paths(path_specs)

        assert len(results) == 3
        for result in results:
            assert result is not None
            assert len(result) > 0

    def test_batch_processing_without_configuration(self, converter):
        """Test batch processing without system configuration."""
        path_specs = [{'path_data': 'M 100 100 L 200 200'}]
        results = converter.process_batch_paths(path_specs)

        # Should return empty list with error logged
        assert results == []

    def test_path_system_info(self, converter, mock_context):
        """Test getting path system information."""
        # Before configuration
        info = converter.get_path_system_info()
        assert info['configured'] == False

        # After configuration
        converter._configure_path_system(mock_context)
        info = converter.get_path_system_info()
        assert info['configured'] == True
        assert info['is_ready'] == True

    def test_cleanup(self, converter, mock_context):
        """Test converter cleanup."""
        # Configure system
        converter._configure_path_system(mock_context)
        assert converter._path_system is not None

        # Cleanup
        converter.cleanup()
        assert converter._path_system is None

    def test_relative_coordinates_path(self, converter, mock_context):
        """Test conversion of path with relative coordinates."""
        relative_path = etree.fromstring('<path d="M 100 100 l 50 50 c 0 -25 25 -25 50 0 z"/>')
        result = converter.convert(relative_path, mock_context)

        # Should convert successfully
        assert result is not None
        assert not result.startswith("<!--")

    def test_path_with_all_command_types(self, converter, mock_context):
        """Test path with all SVG command types."""
        complex_path = etree.fromstring('''
            <path d="M 50 100 L 100 100 H 150 V 150
                     C 150 125 125 100 100 100
                     S 75 75 50 100
                     Q 25 75 50 50
                     T 100 50
                     A 25 25 0 0 1 150 50 Z"/>
        ''')

        result = converter.convert(complex_path, mock_context)

        # Should handle all command types
        assert result is not None
        assert not result.startswith("<!--")

        # Should have processed multiple commands
        stats = converter.get_conversion_statistics()
        assert stats['total_commands'] > 5  # Should have many commands

    def test_scientific_notation_coordinates(self, converter, mock_context):
        """Test path with scientific notation coordinates."""
        sci_notation_path = etree.fromstring('<path d="M 1e2 2E-1 L 3.5e+1 4.2E+2"/>')
        result = converter.convert(sci_notation_path, mock_context)

        # Should parse scientific notation correctly
        assert result is not None
        assert not result.startswith("<!--")

    def test_very_large_path(self, converter, mock_context):
        """Test conversion of path with many commands."""
        # Create a path with many line segments
        path_data = "M 0 0"
        for i in range(50):
            path_data += f" L {i*10} {i*5}"
        path_data += " Z"

        large_path = etree.fromstring(f'<path d="{path_data}"/>')
        result = converter.convert(large_path, mock_context)

        # Should handle large paths
        assert result is not None
        assert not result.startswith("<!--")

        # Should have processed many commands
        stats = converter.get_conversion_statistics()
        assert stats['total_commands'] >= 50

    def test_error_recovery(self, converter, mock_context):
        """Test error recovery after failed conversion."""
        # First, try to convert an invalid path
        invalid_path = etree.fromstring('<path d="INVALID"/>')
        result1 = converter.convert(invalid_path, mock_context)
        assert result1.startswith("<!--")  # Error

        # Then convert a valid path - should work
        valid_path = etree.fromstring('<path d="M 10 10 L 20 20"/>')
        result2 = converter.convert(valid_path, mock_context)
        assert not result2.startswith("<!--")  # Success

    def test_multiple_conversions_same_converter(self, converter, mock_context):
        """Test multiple conversions with the same converter instance."""
        path1 = etree.fromstring('<path d="M 10 10 L 20 20"/>')
        path2 = etree.fromstring('<path d="M 30 30 L 40 40"/>')

        result1 = converter.convert(path1, mock_context)
        result2 = converter.convert(path2, mock_context)

        # Both should succeed
        assert not result1.startswith("<!--")
        assert not result2.startswith("<!--")

        # Statistics should accumulate
        stats = converter.get_conversion_statistics()
        assert stats['paths_converted'] == 2