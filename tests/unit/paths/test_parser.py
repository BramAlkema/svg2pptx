#!/usr/bin/env python3
"""
Unit tests for PathParser implementation.

Tests the parsing of SVG path data into structured commands
without any coordinate transformations.
"""

import pytest
from core.paths.parser import PathParser
from core.paths.architecture import PathCommand, PathCommandType, PathParseError


class TestPathParser:
    """Test suite for PathParser implementation."""

    @pytest.fixture
    def parser(self):
        """Create a PathParser instance for testing."""
        return PathParser(enable_logging=False)

    def test_initialization(self, parser):
        """Test PathParser initialization."""
        assert parser is not None
        assert hasattr(parser, '_number_pattern')
        assert hasattr(parser, '_command_pattern')
        assert hasattr(parser, '_token_pattern')

    def test_simple_move_to(self, parser):
        """Test parsing simple MOVE_TO command."""
        path_data = "M 10 20"
        commands = parser.parse_path_data(path_data)

        assert len(commands) == 1
        command = commands[0]
        assert command.command_type == PathCommandType.MOVE_TO
        assert command.is_relative == False
        assert command.parameters == [10.0, 20.0]
        assert command.original_command == "M"

    def test_relative_move_to(self, parser):
        """Test parsing relative MOVE_TO command."""
        path_data = "m 10 20"
        commands = parser.parse_path_data(path_data)

        assert len(commands) == 1
        command = commands[0]
        assert command.command_type == PathCommandType.MOVE_TO
        assert command.is_relative == True
        assert command.parameters == [10.0, 20.0]
        assert command.original_command == "m"

    def test_line_to_command(self, parser):
        """Test parsing LINE_TO command."""
        path_data = "M 10 20 L 30 40"
        commands = parser.parse_path_data(path_data)

        assert len(commands) == 2
        assert commands[0].command_type == PathCommandType.MOVE_TO
        assert commands[1].command_type == PathCommandType.LINE_TO
        assert commands[1].parameters == [30.0, 40.0]

    def test_horizontal_line(self, parser):
        """Test parsing HORIZONTAL line command."""
        path_data = "M 10 20 H 50"
        commands = parser.parse_path_data(path_data)

        assert len(commands) == 2
        assert commands[1].command_type == PathCommandType.HORIZONTAL
        assert commands[1].parameters == [50.0]

    def test_vertical_line(self, parser):
        """Test parsing VERTICAL line command."""
        path_data = "M 10 20 V 60"
        commands = parser.parse_path_data(path_data)

        assert len(commands) == 2
        assert commands[1].command_type == PathCommandType.VERTICAL
        assert commands[1].parameters == [60.0]

    def test_cubic_bezier(self, parser):
        """Test parsing CUBIC_CURVE command."""
        path_data = "M 10 20 C 10 10 40 10 40 20"
        commands = parser.parse_path_data(path_data)

        assert len(commands) == 2
        assert commands[1].command_type == PathCommandType.CUBIC_CURVE
        assert commands[1].parameters == [10.0, 10.0, 40.0, 10.0, 40.0, 20.0]

    def test_smooth_cubic(self, parser):
        """Test parsing SMOOTH_CUBIC command."""
        path_data = "M 10 20 C 10 10 40 10 40 20 S 70 30 80 20"
        commands = parser.parse_path_data(path_data)

        assert len(commands) == 3
        assert commands[2].command_type == PathCommandType.SMOOTH_CUBIC
        assert commands[2].parameters == [70.0, 30.0, 80.0, 20.0]

    def test_quadratic_bezier(self, parser):
        """Test parsing QUADRATIC command."""
        path_data = "M 10 20 Q 25 10 40 20"
        commands = parser.parse_path_data(path_data)

        assert len(commands) == 2
        assert commands[1].command_type == PathCommandType.QUADRATIC
        assert commands[1].parameters == [25.0, 10.0, 40.0, 20.0]

    def test_smooth_quadratic(self, parser):
        """Test parsing SMOOTH_QUAD command."""
        path_data = "M 10 20 Q 25 10 40 20 T 60 20"
        commands = parser.parse_path_data(path_data)

        assert len(commands) == 3
        assert commands[2].command_type == PathCommandType.SMOOTH_QUAD
        assert commands[2].parameters == [60.0, 20.0]

    def test_arc_command(self, parser):
        """Test parsing ARC command."""
        path_data = "M 50 100 A 50 50 0 0 1 150 100"
        commands = parser.parse_path_data(path_data)

        assert len(commands) == 2
        assert commands[1].command_type == PathCommandType.ARC
        assert commands[1].parameters == [50.0, 50.0, 0.0, 0.0, 1.0, 150.0, 100.0]

    def test_close_path(self, parser):
        """Test parsing CLOSE_PATH command."""
        path_data = "M 10 20 L 30 40 Z"
        commands = parser.parse_path_data(path_data)

        assert len(commands) == 3
        assert commands[2].command_type == PathCommandType.CLOSE_PATH
        assert commands[2].parameters == []

    def test_implicit_line_commands(self, parser):
        """Test parsing implicit LINE_TO commands after MOVE_TO."""
        path_data = "M 10 20 30 40 50 60"
        commands = parser.parse_path_data(path_data)

        assert len(commands) == 3
        assert commands[0].command_type == PathCommandType.MOVE_TO
        assert commands[0].parameters == [10.0, 20.0]

        # Implicit LINE_TO commands
        assert commands[1].command_type == PathCommandType.LINE_TO
        assert commands[1].parameters == [30.0, 40.0]
        assert commands[2].command_type == PathCommandType.LINE_TO
        assert commands[2].parameters == [50.0, 60.0]

    def test_relative_implicit_lines(self, parser):
        """Test parsing relative implicit LINE_TO commands."""
        path_data = "m 10 20 30 40 50 60"
        commands = parser.parse_path_data(path_data)

        assert len(commands) == 3
        assert commands[0].command_type == PathCommandType.MOVE_TO
        assert commands[0].is_relative == True

        # Implicit LINE_TO commands should inherit relativity
        assert commands[1].command_type == PathCommandType.LINE_TO
        assert commands[1].is_relative == True
        assert commands[2].command_type == PathCommandType.LINE_TO
        assert commands[2].is_relative == True

    def test_mixed_case_commands(self, parser):
        """Test parsing mixed absolute and relative commands."""
        path_data = "M 10 20 l 30 40 L 80 90"
        commands = parser.parse_path_data(path_data)

        assert len(commands) == 3
        assert commands[0].is_relative == False  # M (absolute)
        assert commands[1].is_relative == True   # l (relative)
        assert commands[2].is_relative == False  # L (absolute)

    def test_floating_point_coordinates(self, parser):
        """Test parsing floating point coordinates."""
        path_data = "M 10.5 20.7 L 30.123 40.456"
        commands = parser.parse_path_data(path_data)

        assert len(commands) == 2
        assert commands[0].parameters == [10.5, 20.7]
        assert commands[1].parameters == [30.123, 40.456]

    def test_scientific_notation(self, parser):
        """Test parsing scientific notation coordinates."""
        path_data = "M 1e2 2E-3 L 3.5e+1 4.2E+2"
        commands = parser.parse_path_data(path_data)

        assert len(commands) == 2
        assert commands[0].parameters == [100.0, 0.002]
        assert commands[1].parameters == [35.0, 420.0]

    def test_negative_coordinates(self, parser):
        """Test parsing negative coordinates."""
        path_data = "M -10 -20 L -30.5 -40"
        commands = parser.parse_path_data(path_data)

        assert len(commands) == 2
        assert commands[0].parameters == [-10.0, -20.0]
        assert commands[1].parameters == [-30.5, -40.0]

    def test_comma_separated_coordinates(self, parser):
        """Test parsing comma-separated coordinates."""
        path_data = "M 10,20 L 30,40"
        commands = parser.parse_path_data(path_data)

        assert len(commands) == 2
        assert commands[0].parameters == [10.0, 20.0]
        assert commands[1].parameters == [30.0, 40.0]

    def test_compact_format(self, parser):
        """Test parsing compact path format."""
        path_data = "M10,20L30,40H50V60Z"
        commands = parser.parse_path_data(path_data)

        assert len(commands) == 5
        assert commands[0].command_type == PathCommandType.MOVE_TO
        assert commands[1].command_type == PathCommandType.LINE_TO
        assert commands[2].command_type == PathCommandType.HORIZONTAL
        assert commands[3].command_type == PathCommandType.VERTICAL
        assert commands[4].command_type == PathCommandType.CLOSE_PATH

    def test_whitespace_handling(self, parser):
        """Test parsing with various whitespace formats."""
        path_data = "  M   10    20   L  30   40  "
        commands = parser.parse_path_data(path_data)

        assert len(commands) == 2
        assert commands[0].parameters == [10.0, 20.0]
        assert commands[1].parameters == [30.0, 40.0]

    def test_empty_path_data(self, parser):
        """Test parsing empty path data."""
        commands = parser.parse_path_data("")
        assert commands == []

        commands = parser.parse_path_data("   ")
        assert commands == []

    def test_validation_success(self, parser):
        """Test path data validation for valid paths."""
        assert parser.validate_path_data("M 10 20 L 30 40") == True
        assert parser.validate_path_data("m 10 20 l 30 40 z") == True
        assert parser.validate_path_data("") == True
        assert parser.validate_path_data("   ") == True

    def test_validation_failure(self, parser):
        """Test path data validation for invalid paths."""
        assert parser.validate_path_data("10 20 L 30 40") == False  # Missing initial M
        assert parser.validate_path_data("X 10 20") == False        # Invalid command
        assert parser.validate_path_data("M") == False              # Incomplete command

    def test_error_invalid_command(self, parser):
        """Test error handling for invalid commands."""
        with pytest.raises(PathParseError, match="Expected command"):
            parser.parse_path_data("X 10 20")

    def test_error_insufficient_parameters(self, parser):
        """Test error handling for insufficient parameters."""
        with pytest.raises(PathParseError, match="requires.*parameters"):
            parser.parse_path_data("M 10")  # MOVE_TO needs 2 parameters

    def test_error_invalid_number(self, parser):
        """Test error handling for invalid numeric parameters."""
        with pytest.raises(PathParseError, match="requires.*parameters"):
            parser.parse_path_data("M 10 abc")

    def test_error_missing_initial_move(self, parser):
        """Test error handling for missing initial MOVE_TO."""
        with pytest.raises(PathParseError, match="must start with MOVE_TO"):
            parser.parse_path_data("L 10 20")

    def test_get_supported_commands(self, parser):
        """Test getting list of supported commands."""
        commands = parser.get_supported_commands()
        assert 'M' in commands
        assert 'm' in commands
        assert 'A' in commands
        assert 'Z' in commands
        assert len(commands) == 20  # 10 commands × 2 (upper/lower case)

    def test_get_command_info(self, parser):
        """Test getting command information."""
        # Test MOVE_TO
        info = parser.get_command_info('M')
        assert info == (PathCommandType.MOVE_TO, 2, False)

        info = parser.get_command_info('m')
        assert info == (PathCommandType.MOVE_TO, 2, True)

        # Test ARC
        info = parser.get_command_info('A')
        assert info == (PathCommandType.ARC, 7, False)

        # Test invalid command
        info = parser.get_command_info('X')
        assert info is None

    def test_complex_real_world_path(self, parser):
        """Test parsing a complex real-world SVG path."""
        path_data = "M 100,200 C 100,100 400,100 400,200 S 700,300 800,200 Q 900,100 1000,200 T 1100,150 A 50,50 0 0,1 1200,200 L 1300,250 H 1400 V 300 Z"
        commands = parser.parse_path_data(path_data)

        # Should parse all commands successfully
        assert len(commands) == 10
        assert commands[0].command_type == PathCommandType.MOVE_TO
        assert commands[1].command_type == PathCommandType.CUBIC_CURVE
        assert commands[2].command_type == PathCommandType.SMOOTH_CUBIC
        assert commands[3].command_type == PathCommandType.QUADRATIC
        assert commands[4].command_type == PathCommandType.SMOOTH_QUAD
        assert commands[5].command_type == PathCommandType.ARC
        assert commands[6].command_type == PathCommandType.LINE_TO
        assert commands[7].command_type == PathCommandType.HORIZONTAL
        assert commands[8].command_type == PathCommandType.VERTICAL
        assert commands[9].command_type == PathCommandType.CLOSE_PATH