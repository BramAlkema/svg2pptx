#!/usr/bin/env python3
"""
Unit tests for DrawingMLGenerator.

Tests the generation of PowerPoint DrawingML XML from SVG path commands,
focusing on the main interface methods.
"""

import pytest
from unittest.mock import Mock
from lxml import etree as ET

from src.paths.drawingml_generator import DrawingMLGenerator
from src.paths.architecture import (
    PathCommand, CoordinatePoint, PathCommandType, PathBounds,
    XMLGenerationError
)


class TestDrawingMLGenerator:
    """Test suite for DrawingMLGenerator implementation."""

    @pytest.fixture
    def mock_coordinate_system(self):
        """Create mock coordinate system."""
        coord_system = Mock()
        coord_system.transform_to_pptx = Mock()
        coord_system.get_slide_dimensions = Mock(return_value=(10160000, 7620000))  # EMU
        return coord_system

    @pytest.fixture
    def mock_arc_converter(self):
        """Create mock arc converter."""
        converter = Mock()
        converter.convert_arc_command = Mock()
        return converter

    @pytest.fixture
    def generator(self):
        """Create DrawingMLGenerator instance for testing."""
        return DrawingMLGenerator(enable_logging=False)

    @pytest.fixture
    def sample_move_command(self):
        """Create sample MOVE_TO command."""
        return PathCommand(
            command_type=PathCommandType.MOVE_TO,
            is_relative=False,
            parameters=[100.0, 150.0],  # x, y coordinates
            original_command='M'
        )

    @pytest.fixture
    def sample_line_command(self):
        """Create sample LINE_TO command."""
        return PathCommand(
            command_type=PathCommandType.LINE_TO,
            is_relative=False,
            parameters=[200.0, 250.0],  # x, y coordinates
            original_command='L'
        )

    @pytest.fixture
    def sample_cubic_command(self):
        """Create sample CUBIC_CURVE command."""
        return PathCommand(
            command_type=PathCommandType.CUBIC_CURVE,
            is_relative=False,
            parameters=[120.0, 140.0, 180.0, 160.0, 200.0, 200.0],  # cp1_x, cp1_y, cp2_x, cp2_y, end_x, end_y
            original_command='C'
        )

    @pytest.fixture
    def sample_bounds(self):
        """Create sample path bounds."""
        return PathBounds(
            min_x=0, min_y=0, max_x=400, max_y=300,
            width=400, height=300, coordinate_system='svg'
        )

    def test_initialization(self, generator):
        """Test DrawingMLGenerator initialization."""
        assert generator is not None
        assert len(generator._command_handlers) == 10

    def test_initialization_with_logging_disabled(self):
        """Test initialization with logging disabled."""
        generator = DrawingMLGenerator(enable_logging=False)
        assert generator is not None

    def test_command_handlers_mapping(self, generator):
        """Test that all command types have handlers."""
        expected_commands = [
            PathCommandType.MOVE_TO,
            PathCommandType.LINE_TO,
            PathCommandType.HORIZONTAL,
            PathCommandType.VERTICAL,
            PathCommandType.CUBIC_CURVE,
            PathCommandType.SMOOTH_CUBIC,
            PathCommandType.QUADRATIC,
            PathCommandType.SMOOTH_QUAD,
            PathCommandType.ARC,
            PathCommandType.CLOSE_PATH
        ]

        for command_type in expected_commands:
            assert command_type in generator._command_handlers
            assert callable(generator._command_handlers[command_type])

    def test_generate_path_xml_with_move_command(self, generator, sample_move_command, sample_bounds, mock_coordinate_system, mock_arc_converter):
        """Test generation of path XML with MOVE_TO command."""
        # Mock coordinate transformation
        mock_coordinate_system.transform_to_pptx.return_value = CoordinatePoint(
            x=12700, y=19050, coordinate_system='pptx'
        )

        xml = generator.generate_path_xml([sample_move_command], sample_bounds, mock_coordinate_system, mock_arc_converter)

        assert '<a:path w="100000" h="100000">' in xml
        assert '<a:moveTo>' in xml
        assert '<a:pt x="12700" y="19050"/>' in xml
        assert '</a:moveTo>' in xml
        mock_coordinate_system.transform_to_pptx.assert_called()

    def test_generate_path_xml_simple_path(self, generator, sample_move_command, sample_line_command, sample_bounds, mock_coordinate_system, mock_arc_converter):
        """Test generation of complete path XML with move and line."""
        commands = [sample_move_command, sample_line_command]

        # Mock coordinate transformations
        def transform_side_effect(point):
            if point.x == 100:
                return CoordinatePoint(x=12700, y=19050, coordinate_system='pptx')
            elif point.x == 200:
                return CoordinatePoint(x=25400, y=31750, coordinate_system='pptx')

        mock_coordinate_system.transform_to_pptx.side_effect = transform_side_effect

        xml = generator.generate_path_xml(commands, sample_bounds, mock_coordinate_system, mock_arc_converter)

        # Verify XML structure
        assert '<a:path w="100000" h="100000">' in xml
        assert '<a:pathLst>' in xml
        assert '<a:moveTo>' in xml
        assert '<a:lnTo>' in xml
        assert '</a:pathLst>' in xml
        assert '</a:path>' in xml

        # Verify coordinates
        assert 'x="12700" y="19050"' in xml
        assert 'x="25400" y="31750"' in xml

    def test_generate_path_xml_empty_commands(self, generator, sample_bounds, mock_coordinate_system, mock_arc_converter):
        """Test path XML generation with empty command list."""
        xml = generator.generate_path_xml([], sample_bounds, mock_coordinate_system, mock_arc_converter)

        assert '<a:path w="100000" h="100000">' in xml
        assert '<a:pathLst>' in xml
        assert '</a:pathLst>' in xml
        assert '</a:path>' in xml

    def test_generate_path_xml_with_cubic_curve(self, generator, sample_cubic_command, sample_bounds, mock_coordinate_system, mock_arc_converter):
        """Test generation of path XML with cubic bezier curve."""
        # Mock transformations for all three points
        def transform_side_effect(point):
            if point.x == 120:
                return CoordinatePoint(x=15240, y=17780, coordinate_system='pptx')
            elif point.x == 180:
                return CoordinatePoint(x=22860, y=20320, coordinate_system='pptx')
            elif point.x == 200:
                return CoordinatePoint(x=25400, y=25400, coordinate_system='pptx')

        mock_coordinate_system.transform_to_pptx.side_effect = transform_side_effect

        xml = generator.generate_path_xml([sample_cubic_command], sample_bounds, mock_coordinate_system, mock_arc_converter)

        assert '<a:cubicBezTo>' in xml
        assert '<a:pt x="15240" y="17780"/>' in xml  # cp1
        assert '<a:pt x="22860" y="20320"/>' in xml  # cp2
        assert '<a:pt x="25400" y="25400"/>' in xml  # end
        assert '</a:cubicBezTo>' in xml

    def test_generate_path_xml_with_arc_conversion(self, generator, sample_bounds, mock_coordinate_system, mock_arc_converter):
        """Test arc command conversion to bezier curves."""
        arc_command = PathCommand(
            command_type=PathCommandType.ARC,
            absolute=True,
            coordinates=[CoordinatePoint(x=200, y=200, coordinate_system='svg')],
            parameters=[50, 50, 0, 0, 1]  # rx, ry, rotation, large_arc, sweep
        )

        # Mock arc converter to return bezier commands
        bezier_commands = [
            PathCommand(
                command_type=PathCommandType.CUBIC_CURVE,
                absolute=True,
                coordinates=[
                    CoordinatePoint(x=120, y=140, coordinate_system='svg'),
                    CoordinatePoint(x=180, y=160, coordinate_system='svg'),
                    CoordinatePoint(x=200, y=200, coordinate_system='svg')
                ],
                parameters=[]
            )
        ]

        mock_arc_converter.convert_arc_command.return_value = bezier_commands

        # Mock coordinate transformation
        mock_coordinate_system.transform_to_pptx.side_effect = [
            CoordinatePoint(x=15240, y=17780, coordinate_system='pptx'),
            CoordinatePoint(x=22860, y=20320, coordinate_system='pptx'),
            CoordinatePoint(x=25400, y=25400, coordinate_system='pptx')
        ]

        xml = generator.generate_path_xml([arc_command], sample_bounds, mock_coordinate_system, mock_arc_converter)

        assert '<a:cubicBezTo>' in xml
        mock_arc_converter.convert_arc_command.assert_called_once()

    def test_generate_shape_xml_basic(self, generator, sample_bounds):
        """Test generation of complete shape XML."""
        path_xml = '<a:path w="100000" h="100000"><a:pathLst><a:path><a:moveTo><a:pt x="12700" y="19050"/></a:moveTo></a:path></a:pathLst></a:path>'
        style_attrs = {'fill': '#FF0000', 'stroke': '#000000', 'stroke-width': '2'}

        xml = generator.generate_shape_xml(path_xml, sample_bounds, style_attrs)

        # Verify shape structure
        assert '<p:sp>' in xml
        assert '<p:nvSpPr>' in xml
        assert '<p:spPr>' in xml
        assert '<a:custGeom>' in xml
        assert '<a:pathLst>' in xml

    def test_generate_shape_xml_with_styling(self, generator, sample_bounds):
        """Test shape XML generation with fill and stroke styling."""
        path_xml = '<a:path w="100000" h="100000"><a:pathLst><a:path></a:path></a:pathLst></a:path>'
        style_attrs = {
            'fill': '#FF0000',
            'stroke': '#0000FF',
            'stroke-width': '3'
        }

        xml = generator.generate_shape_xml(path_xml, sample_bounds, style_attrs)

        # Should contain fill and stroke elements
        assert '<a:solidFill>' in xml
        assert '<a:ln>' in xml
        assert 'w="38100"' in xml  # 3pt in EMU

    def test_validate_xml_output_valid(self, generator):
        """Test XML validation for valid XML."""
        valid_xml = '<a:moveTo><a:pt x="100" y="200"/></a:moveTo>'
        assert generator.validate_xml_output(valid_xml) == True

    def test_validate_xml_output_invalid(self, generator):
        """Test XML validation for invalid XML."""
        invalid_xml = '<a:moveTo><a:pt x="100" y="200">'  # Missing closing tags
        assert generator.validate_xml_output(invalid_xml) == False

    def test_escape_xml_attribute(self, generator):
        """Test XML attribute escaping."""
        assert generator._escape_xml_attribute('normal') == 'normal'
        assert generator._escape_xml_attribute('test&value') == 'test&amp;value'
        assert generator._escape_xml_attribute('test<value') == 'test&lt;value'
        assert generator._escape_xml_attribute('test>value') == 'test&gt;value'
        assert generator._escape_xml_attribute('test"value') == 'test&quot;value'

    def test_format_coordinate(self, generator):
        """Test coordinate formatting."""
        assert generator._format_coordinate(12345) == '12345'
        assert generator._format_coordinate(12345.67) == '12346'  # Rounded
        assert generator._format_coordinate(-123) == '-123'

    def test_error_handling_coordinate_transformation_failure(self, generator, sample_move_command, sample_bounds, mock_coordinate_system, mock_arc_converter):
        """Test error handling when coordinate transformation fails."""
        # Mock coordinate system to raise exception
        mock_coordinate_system.transform_to_pptx.side_effect = Exception("Transform failed")

        with pytest.raises(XMLGenerationError):
            generator.generate_path_xml([sample_move_command], sample_bounds, mock_coordinate_system, mock_arc_converter)

    def test_statistics_tracking(self, generator, sample_move_command, sample_line_command, sample_bounds, mock_coordinate_system, mock_arc_converter):
        """Test that statistics are properly tracked."""
        commands = [sample_move_command, sample_line_command]

        mock_coordinate_system.transform_to_pptx.side_effect = [
            CoordinatePoint(x=12700, y=19050, coordinate_system='pptx'),
            CoordinatePoint(x=25400, y=31750, coordinate_system='pptx')
        ]

        generator.generate_path_xml(commands, sample_bounds, mock_coordinate_system, mock_arc_converter)

        stats = generator.get_generation_statistics()
        assert stats['paths_generated'] == 1
        assert stats['commands_processed'] == 2
        assert stats['total_generation_time_ms'] >= 0

    def test_statistics_reset(self, generator, sample_move_command, sample_bounds, mock_coordinate_system, mock_arc_converter):
        """Test statistics reset functionality."""
        mock_coordinate_system.transform_to_pptx.return_value = CoordinatePoint(
            x=12700, y=19050, coordinate_system='pptx'
        )

        # Generate some statistics
        generator.generate_path_xml([sample_move_command], sample_bounds, mock_coordinate_system, mock_arc_converter)
        assert generator.get_generation_statistics()['paths_generated'] == 1

        # Reset and verify
        generator.reset_statistics()
        stats = generator.get_generation_statistics()
        assert stats['paths_generated'] == 0
        assert stats['commands_processed'] == 0

    def test_complex_path_generation(self, generator, sample_bounds, mock_coordinate_system, mock_arc_converter):
        """Test generation of complex path with multiple command types."""
        complex_commands = [
            PathCommand(
                command_type=PathCommandType.MOVE_TO,
                absolute=True,
                coordinates=[CoordinatePoint(x=50, y=50, coordinate_system='svg')],
                parameters=[]
            ),
            PathCommand(
                command_type=PathCommandType.LINE_TO,
                absolute=True,
                coordinates=[CoordinatePoint(x=100, y=50, coordinate_system='svg')],
                parameters=[]
            ),
            PathCommand(
                command_type=PathCommandType.CUBIC_CURVE,
                absolute=True,
                coordinates=[
                    CoordinatePoint(x=120, y=40, coordinate_system='svg'),
                    CoordinatePoint(x=140, y=60, coordinate_system='svg'),
                    CoordinatePoint(x=150, y=100, coordinate_system='svg')
                ],
                parameters=[]
            ),
            PathCommand(
                command_type=PathCommandType.CLOSE_PATH,
                absolute=True,
                coordinates=[],
                parameters=[]
            )
        ]

        # Mock coordinate transformations
        def transform_side_effect(point):
            return CoordinatePoint(
                x=int(point.x * 127),  # Mock conversion
                y=int(point.y * 127),
                coordinate_system='pptx'
            )

        mock_coordinate_system.transform_to_pptx.side_effect = transform_side_effect

        xml = generator.generate_path_xml(complex_commands, sample_bounds, mock_coordinate_system, mock_arc_converter)

        # Verify all command types are present
        assert '<a:moveTo>' in xml
        assert '<a:lnTo>' in xml
        assert '<a:cubicBezTo>' in xml
        assert '<a:close/>' in xml

        # Verify XML is well-formed
        assert generator.validate_xml_output(xml) == True

    def test_performance_with_many_commands(self, generator, sample_bounds, mock_coordinate_system, mock_arc_converter):
        """Test performance with a large number of commands."""
        # Create many line commands
        commands = []
        for i in range(100):
            commands.append(PathCommand(
                command_type=PathCommandType.LINE_TO,
                absolute=True,
                coordinates=[CoordinatePoint(x=i*10, y=i*10, coordinate_system='svg')],
                parameters=[]
            ))

        # Mock coordinate transformation
        def transform_side_effect(point):
            return CoordinatePoint(
                x=int(point.x * 127),
                y=int(point.y * 127),
                coordinate_system='pptx'
            )

        mock_coordinate_system.transform_to_pptx.side_effect = transform_side_effect

        xml = generator.generate_path_xml(commands, sample_bounds, mock_coordinate_system, mock_arc_converter)

        # Should complete without errors
        assert len(xml) > 0
        assert xml.count('<a:lnTo>') == 100

        # Check statistics
        stats = generator.get_generation_statistics()
        assert stats['commands_processed'] == 100