#!/usr/bin/env python3
"""
Unit tests for CoordinateSystem implementation.

Tests the integration with ViewportEngine and UnitConverter,
and validates coordinate transformation accuracy.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch

from core.paths.coordinate_system import CoordinateSystem
from core.paths.architecture import (
    PathCommand, PathBounds, PathCommandType,
    CoordinateTransformError
)


class TestCoordinateSystem:
    """Test suite for CoordinateSystem implementation."""

    @pytest.fixture
    def coordinate_system(self):
        """Create a CoordinateSystem instance for testing."""
        return CoordinateSystem(enable_logging=False)

    @pytest.fixture
    def mock_viewport_engine(self):
        """Mock ViewportEngine for testing."""
        mock = Mock()
        mock.resolve_viewport.return_value = Mock(
            viewbox_x=0,
            viewbox_y=0,
            scale_x=1.0,
            scale_y=1.0
        )
        return mock

    @pytest.fixture
    def mock_unit_converter(self):
        """Mock UnitConverter for testing."""
        mock = Mock()
        mock.create_context.return_value = Mock()
        mock.to_emu.side_effect = lambda value, context=None: float(value.replace('px', '')) * 9525  # 96 DPI conversion
        return mock

    @pytest.fixture
    def test_path_bounds(self):
        """Create test PathBounds for coordinate transformation."""
        return PathBounds(
            min_x=0,
            min_y=0,
            max_x=1905000,  # 200px * 9525 EMU/px
            max_y=1905000,  # 200px * 9525 EMU/px
            width=1905000,
            height=1905000,
            coordinate_system="emu"
        )

    def test_initialization(self, coordinate_system):
        """Test CoordinateSystem initialization."""
        assert coordinate_system is not None
        assert coordinate_system.precision == 6
        assert not coordinate_system.is_initialized()

    def test_initialize_with_services(self, coordinate_system, mock_viewport_engine, mock_unit_converter):
        """Test initialization with provided services."""
        coordinate_system.initialize_with_services(mock_viewport_engine, mock_unit_converter)

        assert coordinate_system.get_viewport_engine() == mock_viewport_engine
        assert coordinate_system.get_unit_converter() == mock_unit_converter
        assert coordinate_system._initialized

    def test_create_conversion_context(self, coordinate_system, mock_unit_converter):
        """Test conversion context creation."""
        coordinate_system.initialize_with_services(unit_converter=mock_unit_converter)

        coordinate_system.create_conversion_context(200, 200, None, 96.0)

        mock_unit_converter.create_context.assert_called_once_with(
            width=200,
            height=200,
            dpi=96.0
        )
        assert coordinate_system.get_conversion_context() is not None

    def test_create_conversion_context_with_viewbox(self, coordinate_system, mock_unit_converter):
        """Test conversion context creation with viewBox."""
        coordinate_system.initialize_with_services(unit_converter=mock_unit_converter)

        viewbox = (0, 0, 100, 100)
        coordinate_system.create_conversion_context(200, 200, viewbox, 96.0)

        assert coordinate_system._viewport_mapping is not None

    def test_svg_to_relative_basic(self, coordinate_system, mock_unit_converter, test_path_bounds):
        """Test basic SVG to relative coordinate conversion."""
        coordinate_system.initialize_with_services(unit_converter=mock_unit_converter)
        coordinate_system.create_conversion_context(200, 200)

        # Test corner points
        x_rel, y_rel = coordinate_system.svg_to_relative(0, 0, test_path_bounds)
        assert x_rel == 0
        assert y_rel == 0

        x_rel, y_rel = coordinate_system.svg_to_relative(200, 200, test_path_bounds)
        assert x_rel == 100000
        assert y_rel == 100000

        # Test center point
        x_rel, y_rel = coordinate_system.svg_to_relative(100, 100, test_path_bounds)
        assert x_rel == 50000
        assert y_rel == 50000

    def test_svg_to_relative_arc_coordinates(self, coordinate_system, mock_unit_converter):
        """Test the specific arc coordinates that were failing."""
        coordinate_system.initialize_with_services(unit_converter=mock_unit_converter)
        coordinate_system.create_conversion_context(200, 200)

        # Create bounds for arc from (50,100) to (150,100)
        arc_bounds = PathBounds(
            min_x=476250,   # 50px * 9525
            min_y=952500,   # 100px * 9525
            max_x=1428750,  # 150px * 9525
            max_y=952500,   # 100px * 9525
            width=952500,   # 100px width
            height=0,       # Horizontal arc
            coordinate_system="emu"
        )

        # Test arc start point (50, 100)
        x_rel, y_rel = coordinate_system.svg_to_relative(50, 100, arc_bounds)
        assert x_rel == 0  # Left edge
        assert y_rel == 0 or y_rel == 100000  # Handle zero height case

        # Test arc end point (150, 100)
        x_rel, y_rel = coordinate_system.svg_to_relative(150, 100, arc_bounds)
        assert x_rel == 100000  # Right edge
        assert y_rel == 0 or y_rel == 100000  # Handle zero height case

    def test_calculate_path_bounds_simple_path(self, coordinate_system, mock_unit_converter):
        """Test path bounds calculation for simple path."""
        coordinate_system.initialize_with_services(unit_converter=mock_unit_converter)
        coordinate_system.create_conversion_context(200, 200)

        commands = [
            PathCommand(PathCommandType.MOVE_TO, False, [50, 100], "M"),
            PathCommand(PathCommandType.LINE_TO, False, [150, 100], "L")
        ]

        bounds = coordinate_system.calculate_path_bounds(commands)

        assert bounds.coordinate_system == "emu"
        assert bounds.min_x == 476250   # 50px * 9525
        assert bounds.max_x == 1428750  # 150px * 9525
        assert bounds.width == 952500   # 100px width

    def test_calculate_path_bounds_arc_command(self, coordinate_system, mock_unit_converter):
        """Test path bounds calculation with arc command."""
        coordinate_system.initialize_with_services(unit_converter=mock_unit_converter)
        coordinate_system.create_conversion_context(200, 200)

        commands = [
            PathCommand(PathCommandType.MOVE_TO, False, [50, 100], "M"),
            PathCommand(PathCommandType.ARC, False, [50, 50, 0, 0, 1, 150, 100], "A")
        ]

        bounds = coordinate_system.calculate_path_bounds(commands)

        assert bounds.coordinate_system == "emu"
        # Should include both start point (50,100) and end point (150,100)
        assert bounds.min_x == 476250   # 50px * 9525
        assert bounds.max_x == 1428750  # 150px * 9525

    def test_calculate_path_bounds_relative_commands(self, coordinate_system, mock_unit_converter):
        """Test path bounds calculation with relative commands."""
        coordinate_system.initialize_with_services(unit_converter=mock_unit_converter)
        coordinate_system.create_conversion_context(200, 200)

        commands = [
            PathCommand(PathCommandType.MOVE_TO, False, [50, 50], "M"),
            PathCommand(PathCommandType.LINE_TO, True, [100, 50], "l")  # Relative line
        ]

        bounds = coordinate_system.calculate_path_bounds(commands)

        # Should include start (50,50) and end (150,100)
        assert bounds.min_x == 476250   # 50px * 9525
        assert bounds.max_x == 1428750  # 150px * 9525
        assert bounds.min_y == 476250   # 50px * 9525
        assert bounds.max_y == 952500   # 100px * 9525

    def test_extract_coordinate_points_move_to(self, coordinate_system):
        """Test coordinate point extraction for MOVE_TO command."""
        command = PathCommand(PathCommandType.MOVE_TO, False, [50, 100], "M")
        current_pos = [0, 0]

        points = coordinate_system._extract_coordinate_points(command, current_pos)

        assert len(points) == 1
        assert points[0] == (50, 100)

    def test_extract_coordinate_points_relative_line(self, coordinate_system):
        """Test coordinate point extraction for relative LINE_TO command."""
        command = PathCommand(PathCommandType.LINE_TO, True, [50, 25], "l")
        current_pos = [100, 75]

        points = coordinate_system._extract_coordinate_points(command, current_pos)

        assert len(points) == 1
        assert points[0] == (150, 100)  # 100+50, 75+25

    def test_extract_coordinate_points_horizontal(self, coordinate_system):
        """Test coordinate point extraction for HORIZONTAL command."""
        command = PathCommand(PathCommandType.HORIZONTAL, False, [150], "H")
        current_pos = [50, 100]

        points = coordinate_system._extract_coordinate_points(command, current_pos)

        assert len(points) == 1
        assert points[0] == (150, 100)  # x changes, y stays same

    def test_extract_coordinate_points_vertical(self, coordinate_system):
        """Test coordinate point extraction for VERTICAL command."""
        command = PathCommand(PathCommandType.VERTICAL, True, [25], "v")
        current_pos = [50, 75]

        points = coordinate_system._extract_coordinate_points(command, current_pos)

        assert len(points) == 1
        assert points[0] == (50, 100)  # x stays same, y = 75+25

    def test_extract_coordinate_points_arc(self, coordinate_system):
        """Test coordinate point extraction for ARC command."""
        command = PathCommand(PathCommandType.ARC, False, [50, 50, 0, 0, 1, 150, 100], "A")
        current_pos = [50, 100]

        points = coordinate_system._extract_coordinate_points(command, current_pos)

        assert len(points) == 1
        assert points[0] == (150, 100)  # Arc end point

    def test_extract_coordinate_points_cubic_curve(self, coordinate_system):
        """Test coordinate point extraction for CUBIC_CURVE command."""
        command = PathCommand(PathCommandType.CUBIC_CURVE, False, [75, 75, 125, 75, 150, 100], "C")
        current_pos = [50, 100]

        points = coordinate_system._extract_coordinate_points(command, current_pos)

        assert len(points) == 3
        assert points[0] == (75, 75)    # Control point 1
        assert points[1] == (125, 75)   # Control point 2
        assert points[2] == (150, 100)  # End point

    def test_emu_to_relative_conversion(self, coordinate_system, test_path_bounds):
        """Test EMU to relative coordinate conversion."""
        # Test corner points
        x_rel = coordinate_system._emu_to_relative_x(0, test_path_bounds)
        assert x_rel == 0

        x_rel = coordinate_system._emu_to_relative_x(1905000, test_path_bounds)
        assert x_rel == 100000

        # Test center point
        x_rel = coordinate_system._emu_to_relative_x(952500, test_path_bounds)
        assert x_rel == 50000

    def test_emu_to_relative_zero_width_bounds(self, coordinate_system):
        """Test EMU to relative conversion with zero width bounds."""
        zero_width_bounds = PathBounds(
            min_x=952500, min_y=952500, max_x=952500, max_y=1905000,
            width=0, height=952500, coordinate_system="emu"
        )

        x_rel = coordinate_system._emu_to_relative_x(952500, zero_width_bounds)
        assert x_rel == 0  # Should handle zero width gracefully

    def test_coordinate_transform_error_handling(self, coordinate_system):
        """Test error handling in coordinate transformations."""
        # Test without initialization
        bounds = PathBounds(0, 0, 100, 100, 100, 100, "emu")

        with pytest.raises(CoordinateTransformError):
            coordinate_system.svg_to_relative(50, 50, bounds)

    def test_calculate_bounds_empty_commands(self, coordinate_system, mock_unit_converter):
        """Test bounds calculation with empty command list."""
        coordinate_system.initialize_with_services(unit_converter=mock_unit_converter)
        coordinate_system.create_conversion_context(200, 200)

        with pytest.raises(CoordinateTransformError):
            coordinate_system.calculate_path_bounds([])

    def test_precision_setting(self, coordinate_system):
        """Test coordinate precision setting."""
        coordinate_system.set_precision(3)
        assert coordinate_system.precision == 3

        coordinate_system.set_precision(-1)
        assert coordinate_system.precision == 0  # Clamped to minimum

        coordinate_system.set_precision(15)
        assert coordinate_system.precision == 10  # Clamped to maximum