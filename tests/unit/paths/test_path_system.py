#!/usr/bin/env python3
"""
Unit tests for integrated PathSystem implementation.

Tests the complete end-to-end path processing system that coordinates
all components to convert SVG paths to PowerPoint DrawingML.
"""

import pytest
from lxml import etree
from unittest.mock import Mock, patch

from core.paths.path_system import PathSystem, create_path_system, PathProcessingResult
from core.paths.architecture import (
    PathSystemError, PathParseError, CoordinateTransformError,
    XMLGenerationError, PathBounds
)


def q(tag: str) -> str:
    """Helper for namespace-agnostic XPath queries using lxml."""
    return f'.//*[local-name()="{tag}"]'


class TestPathSystem:
    """Test suite for integrated PathSystem."""

    @pytest.fixture
    def system(self):
        """Create a PathSystem instance for testing."""
        return PathSystem(enable_logging=False)

    @pytest.fixture
    def configured_system(self, system):
        """Create a configured PathSystem for testing."""
        system.configure_viewport(800, 600, viewbox=(0, 0, 400, 300))
        return system

    def test_initialization(self, system):
        """Test PathSystem initialization."""
        assert system is not None
        assert system._parser is not None
        assert system._coordinate_system is not None
        assert system._arc_converter is not None
        assert system._xml_generator is not None
        assert not system._viewport_configured
        assert system._processing_stats['paths_processed'] == 0

    def test_viewport_configuration(self, system):
        """Test viewport configuration."""
        # Test successful configuration
        system.configure_viewport(800, 600, viewbox=(0, 0, 400, 300), dpi=96.0)
        assert system._viewport_configured == True
        assert system.is_configured() == True

        # Test configuration without viewbox
        system2 = PathSystem(enable_logging=False)
        system2.configure_viewport(1024, 768)
        assert system2._viewport_configured == True

    def test_simple_path_processing(self, configured_system):
        """Test processing a simple SVG path."""
        path_data = "M 100 100 L 200 200 Z"
        style_attrs = {'fill': '#FF0000', 'stroke': '#000000'}

        result = configured_system.process_path(path_data, style_attrs)

        # Verify result structure
        assert isinstance(result, PathProcessingResult)
        assert result.path_xml is not None
        assert result.shape_xml is not None
        assert result.bounds is not None
        assert len(result.commands) == 3  # M, L, Z
        assert result.processing_stats['command_count'] == 3

        # Verify XML is well-formed using lxml
        path_root = etree.fromstring(result.path_xml.encode())
        assert 'pathLst' in path_root.tag  # Handle namespaced XML
        assert path_root.xpath(q('path')) is not None and len(path_root.xpath(q('path'))) > 0
        assert path_root.xpath(q('moveTo')) is not None and len(path_root.xpath(q('moveTo'))) > 0
        assert path_root.xpath(q('lnTo')) is not None and len(path_root.xpath(q('lnTo'))) > 0

        shape_root = etree.fromstring(result.shape_xml.encode())
        assert 'sp' in shape_root.tag  # Handle namespaced XML

    def test_complex_path_with_curves_and_arcs(self, configured_system):
        """Test processing complex path with curves and arcs."""
        path_data = "M 50 100 C 50 50 150 50 150 100 A 50 50 0 0 1 250 100 Q 300 50 350 100 Z"

        result = configured_system.process_path(path_data)

        # Should handle all command types
        assert len(result.commands) == 5  # M, C, A, Q, Z
        assert result.processing_stats['arc_count'] == 1  # One arc

        # XML should be valid
        assert configured_system._xml_generator.validate_xml_output(result.path_xml)

    def test_relative_coordinates_path(self, configured_system):
        """Test processing path with relative coordinates."""
        path_data = "M 100 100 l 50 50 c 0 -25 25 -25 50 0 z"

        result = configured_system.process_path(path_data)

        assert len(result.commands) == 4  # M, l, c, z
        # Should process successfully despite relative coordinates

    def test_processing_without_viewport_configuration(self, system):
        """Test that processing fails without viewport configuration."""
        path_data = "M 100 100 L 200 200"

        with pytest.raises(PathSystemError, match="Viewport must be configured"):
            system.process_path(path_data)

    def test_empty_path_data_error(self, configured_system):
        """Test error handling for empty path data."""
        with pytest.raises(PathSystemError, match="No path commands found"):
            configured_system.process_path("")

    def test_invalid_path_data_error(self, configured_system):
        """Test error handling for invalid path data."""
        with pytest.raises(PathSystemError, match="Path processing failed"):
            configured_system.process_path("INVALID PATH DATA")

    def test_processing_statistics(self, configured_system):
        """Test processing statistics tracking."""
        initial_stats = configured_system.get_processing_statistics()
        assert initial_stats['paths_processed'] == 0

        # Process some paths
        configured_system.process_path("M 100 100 L 200 200")
        configured_system.process_path("M 50 50 A 25 25 0 0 1 100 50")

        stats = configured_system.get_processing_statistics()
        assert stats['paths_processed'] == 2
        assert stats['commands_processed'] == 4  # 2 + 2 commands
        assert stats['arcs_converted'] == 1

        # Reset statistics
        configured_system.reset_statistics()
        reset_stats = configured_system.get_processing_statistics()
        assert reset_stats['paths_processed'] == 0

    def test_batch_processing(self, configured_system):
        """Test batch processing of multiple paths."""
        path_specs = [
            {'path_data': 'M 100 100 L 200 200'},
            {'path_data': 'M 50 50 C 50 25 75 25 100 50', 'style_attributes': {'fill': '#00FF00'}},
            {'path_data': 'M 150 150 Q 175 125 200 150 Z'}
        ]

        results = configured_system.process_multiple_paths(path_specs)

        assert len(results) == 3
        for result in results:
            assert isinstance(result, PathProcessingResult)
            assert result.path_xml is not None
            assert result.shape_xml is not None

    def test_batch_processing_with_errors(self, configured_system):
        """Test batch processing with some invalid paths."""
        path_specs = [
            {'path_data': 'M 100 100 L 200 200'},  # Valid
            {'path_data': 'INVALID'},               # Invalid
            {'path_data': 'M 150 150 Z'}            # Valid
        ]

        results = configured_system.process_multiple_paths(path_specs)

        # Should return results for valid paths only
        assert len(results) == 2

        # Error statistics should be updated
        stats = configured_system.get_processing_statistics()
        assert stats['errors_encountered'] >= 1

    def test_batch_processing_without_viewport(self, system):
        """Test that batch processing fails without viewport configuration."""
        path_specs = [{'path_data': 'M 100 100 L 200 200'}]

        with pytest.raises(PathSystemError, match="Viewport must be configured"):
            system.process_multiple_paths(path_specs)

    def test_path_validation(self, system):
        """Test path data validation."""
        assert system.validate_path_data("M 100 100 L 200 200 Z") == True
        assert system.validate_path_data("m 10 10 l 20 20 z") == True
        assert system.validate_path_data("") == True  # Empty is valid
        assert system.validate_path_data("INVALID") == False
        assert system.validate_path_data("M") == False  # Incomplete

    def test_arc_quality_configuration(self, system):
        """Test arc quality parameter configuration."""
        # Should not raise an error
        system.configure_arc_quality(max_segment_angle=45.0, error_tolerance=0.005)

        # Verify it was applied (through system components)
        components = system.get_system_components()
        assert components.arc_converter.max_segment_angle == 45.0
        assert components.arc_converter.error_tolerance == 0.005

    def test_get_system_components(self, system):
        """Test access to system components."""
        components = system.get_system_components()

        assert components.parser is not None
        assert components.coordinate_system is not None
        assert components.arc_converter is not None
        assert hasattr(components, 'xml_generator')

    def test_get_supported_commands(self, system):
        """Test getting supported path commands."""
        commands = system.get_supported_commands()
        assert len(commands) == 20  # 10 commands × 2 (upper/lower case)
        assert 'M' in commands
        assert 'm' in commands
        assert 'A' in commands
        assert 'Z' in commands

    def test_style_attributes_processing(self, configured_system):
        """Test processing with various style attributes."""
        path_data = "M 100 100 L 200 200 Z"

        # Test with fill and stroke
        style_attrs = {
            'fill': '#FF0000',
            'stroke': '#0000FF',
            'stroke-width': '3'
        }
        result = configured_system.process_path(path_data, style_attrs)

        # Parse shape XML and verify styling was applied
        shape_root = etree.fromstring(result.shape_xml.encode())
        sppr = shape_root.xpath(q('spPr'))
        assert sppr is not None and len(sppr) > 0

        # Should have solid fill
        solidfill = shape_root.xpath(q('solidFill'))
        assert solidfill is not None and len(solidfill) > 0

        # Should have stroke line
        ln = shape_root.xpath(q('ln'))
        assert ln is not None and len(ln) > 0

    def test_no_style_attributes(self, configured_system):
        """Test processing without style attributes."""
        path_data = "M 100 100 L 200 200 Z"

        result = configured_system.process_path(path_data)  # No style_attributes

        # Should process successfully with default styling
        assert result.shape_xml is not None

    def test_performance_measurement(self, configured_system):
        """Test that processing time is measured."""
        path_data = "M 100 100 C 100 50 200 50 200 100 Z"

        result = configured_system.process_path(path_data)

        # Should have processing time recorded
        assert 'processing_time_ms' in result.processing_stats
        assert result.processing_stats['processing_time_ms'] >= 0

    def test_bounds_calculation_integration(self, configured_system):
        """Test that bounds are properly calculated and included."""
        path_data = "M 50 50 L 150 150 Z"

        result = configured_system.process_path(path_data)

        # Bounds should be calculated
        assert result.bounds is not None
        assert result.bounds.width > 0
        assert result.bounds.height > 0

        # Bounds should be included in processing stats
        bounds_info = result.processing_stats['bounds_emu']
        assert bounds_info['width'] > 0
        assert bounds_info['height'] > 0

    @patch('core.paths.path_system.PathParser')
    def test_parser_error_handling(self, mock_parser_class, configured_system):
        """Test error handling when parser fails."""
        # Mock parser to raise an error
        mock_parser = Mock()
        mock_parser.parse_path_data.side_effect = PathParseError("Parser error")
        configured_system._parser = mock_parser

        with pytest.raises(PathSystemError, match="Path processing failed"):
            configured_system.process_path("M 100 100 L 200 200")

    @patch('core.paths.path_system.CoordinateSystem')
    def test_coordinate_system_error_handling(self, mock_cs_class, configured_system):
        """Test error handling when coordinate system fails."""
        # Mock coordinate system to raise an error
        mock_cs = Mock()
        mock_cs.calculate_path_bounds.side_effect = CoordinateTransformError("Coordinate error")
        configured_system._coordinate_system = mock_cs

        with pytest.raises(PathSystemError, match="Path processing failed"):
            configured_system.process_path("M 100 100 L 200 200")

    @patch('core.paths.path_system.DrawingMLGenerator')
    def test_xml_generator_error_handling(self, mock_gen_class, configured_system):
        """Test error handling when XML generator fails."""
        # Mock XML generator to raise an error
        mock_gen = Mock()
        mock_gen.generate_path_xml.side_effect = XMLGenerationError("XML error")
        configured_system._xml_generator = mock_gen

        with pytest.raises(PathSystemError, match="Path processing failed"):
            configured_system.process_path("M 100 100 L 200 200")


class TestCreatePathSystemFactory:
    """Test suite for create_path_system factory function."""

    def test_create_basic_system(self):
        """Test creating basic system without configuration."""
        system = create_path_system(enable_logging=False)

        assert isinstance(system, PathSystem)
        assert not system.is_configured()

    def test_create_configured_system(self):
        """Test creating system with viewport configuration."""
        system = create_path_system(
            viewport_width=800,
            viewport_height=600,
            viewbox=(0, 0, 400, 300),
            enable_logging=False
        )

        assert isinstance(system, PathSystem)
        assert system.is_configured()

    def test_create_system_partial_viewport(self):
        """Test creating system with partial viewport configuration."""
        # Should not configure if only width is provided
        system = create_path_system(viewport_width=800, enable_logging=False)
        assert not system.is_configured()

        # Should configure if both width and height are provided
        system2 = create_path_system(viewport_width=800, viewport_height=600, enable_logging=False)
        assert system2.is_configured()

    def test_end_to_end_integration(self):
        """Test complete end-to-end integration."""
        # Create and configure system
        system = create_path_system(800, 600, (0, 0, 400, 300), enable_logging=False)

        # Process a complex path
        path_data = "M 100 150 C 100 100 200 100 200 150 A 50 25 0 0 1 300 150 L 350 200 Z"
        style_attrs = {
            'fill': '#FF6600',
            'stroke': '#003366',
            'stroke-width': '2'
        }

        result = system.process_path(path_data, style_attrs)

        # Verify complete result
        assert result.path_xml is not None
        assert result.shape_xml is not None
        assert len(result.commands) == 5  # M, C, A, L, Z
        assert result.processing_stats['arc_count'] == 1

        # Verify XML structure
        path_root = etree.fromstring(result.path_xml.encode())
        assert 'pathLst' in path_root.tag  # Should be pathLst
        # Find the actual path element
        path_elem = path_root.xpath(q('path'))
        assert path_elem is not None and len(path_elem) > 0
        assert 'w' in path_elem[0].attrib
        assert 'h' in path_elem[0].attrib

        shape_root = etree.fromstring(result.shape_xml.encode())
        assert 'sp' in shape_root.tag

        # Should have various path elements using namespace-agnostic search
        assert len(path_root.xpath(q('moveTo'))) == 1
        assert len(path_root.xpath(q('cubicBezTo'))) >= 1  # At least one from C command (arc may add more)
        assert len(path_root.xpath(q('lnTo'))) == 1
        assert len(path_root.xpath(q('close'))) == 1