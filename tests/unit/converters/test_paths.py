#!/usr/bin/env python3
"""
Unit tests for path converter classes and functionality.

Tests the SVG path converter including PathData parsing and PathConverter
with support for all SVG path commands: M, L, H, V, C, S, Q, T, A, Z.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import xml.etree.ElementTree as ET
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

# Import with correct module path
import src.converters.paths as paths
from src.converters.paths import (
    PathData,
    PathConverter
)
from src.converters.base import ConversionContext


class TestPathData:
    """Test PathData parsing functionality."""
    
    def test_init_empty_path(self):
        """Test PathData initialization with empty path."""
        path = PathData("")
        assert path.commands == []
    
    def test_init_none_path(self):
        """Test PathData initialization with None path."""
        path = PathData(None)
        assert path.commands == []
    
    def test_parse_simple_move_line(self):
        """Test parsing simple move and line commands."""
        path = PathData("M10,20 L30,40")
        expected = [
            ('M', [10.0, 20.0]),
            ('L', [30.0, 40.0])
        ]
        assert path.commands == expected
    
    def test_parse_mixed_separators(self):
        """Test parsing with mixed separators (commas and spaces)."""
        path = PathData("M 10 20 L30,40 50 60")
        expected = [
            ('M', [10.0, 20.0]),
            ('L', [30.0, 40.0, 50.0, 60.0])
        ]
        assert path.commands == expected
    
    def test_parse_multiple_coordinates(self):
        """Test parsing commands with multiple coordinate pairs."""
        path = PathData("L10,20 30,40 50,60")
        expected = [
            ('L', [10.0, 20.0, 30.0, 40.0, 50.0, 60.0])
        ]
        assert path.commands == expected
    
    def test_parse_cubic_curve(self):
        """Test parsing cubic Bezier curve commands."""
        path = PathData("C10,20 30,40 50,60")
        expected = [
            ('C', [10.0, 20.0, 30.0, 40.0, 50.0, 60.0])
        ]
        assert path.commands == expected
    
    def test_parse_quadratic_curve(self):
        """Test parsing quadratic Bezier curve commands."""
        path = PathData("Q10,20 30,40")
        expected = [
            ('Q', [10.0, 20.0, 30.0, 40.0])
        ]
        assert path.commands == expected
    
    def test_parse_arc_command(self):
        """Test parsing arc commands."""
        path = PathData("A25,25 0 0,1 50,25")
        expected = [
            ('A', [25.0, 25.0, 0.0, 0.0, 1.0, 50.0, 25.0])
        ]
        assert path.commands == expected
    
    def test_parse_close_path(self):
        """Test parsing close path commands."""
        path = PathData("M10,10 L20,20 Z")
        expected = [
            ('M', [10.0, 10.0]),
            ('L', [20.0, 20.0]),
            ('Z', [])
        ]
        # Z command should have empty coordinates
        assert len(path.commands) == 3
        assert path.commands[2][0] == 'Z'
    
    def test_parse_lowercase_commands(self):
        """Test parsing relative (lowercase) commands."""
        path = PathData("m10,20 l30,40")
        expected = [
            ('m', [10.0, 20.0]),
            ('l', [30.0, 40.0])
        ]
        assert path.commands == expected
    
    def test_parse_complex_path(self):
        """Test parsing complex path with multiple command types."""
        path = PathData("M10,10 L20,10 Q25,5 30,10 C35,5 45,5 50,10 Z")
        assert len(path.commands) == 5
        assert path.commands[0][0] == 'M'
        assert path.commands[1][0] == 'L'
        assert path.commands[2][0] == 'Q'
        assert path.commands[3][0] == 'C'
        assert path.commands[4][0] == 'Z'
    
    def test_parse_horizontal_vertical_lines(self):
        """Test parsing horizontal and vertical line commands."""
        path = PathData("M10,10 H50 V30 h20 v10")
        commands = [cmd[0] for cmd in path.commands]
        assert commands == ['M', 'H', 'V', 'h', 'v']
        
        # Check coordinate counts
        assert len(path.commands[1][1]) == 1  # H should have 1 coordinate
        assert len(path.commands[2][1]) == 1  # V should have 1 coordinate
    
    def test_parse_smooth_curves(self):
        """Test parsing smooth curve commands."""
        path = PathData("C10,10 20,20 30,30 S40,40 50,50")
        expected = [
            ('C', [10.0, 10.0, 20.0, 20.0, 30.0, 30.0]),
            ('S', [40.0, 40.0, 50.0, 50.0])
        ]
        assert path.commands == expected


class TestPathConverter:
    """Test PathConverter functionality."""
    
    def test_can_convert_path(self):
        """Test that converter recognizes path elements."""
        converter = PathConverter()
        
        element = ET.fromstring('<path d="M10,10 L20,20"/>')
        assert converter.can_convert(element) is True
    
    def test_can_convert_other_elements(self):
        """Test that converter rejects non-path elements."""
        converter = PathConverter()
        
        element = ET.fromstring('<rect width="100" height="50"/>')
        assert converter.can_convert(element) is False
        
        element = ET.fromstring('<circle r="50"/>')
        assert converter.can_convert(element) is False
    
    def test_supported_elements(self):
        """Test that converter declares correct supported elements."""
        converter = PathConverter()
        assert converter.supported_elements == ['path']
    
    def test_init_state(self):
        """Test converter initialization state."""
        converter = PathConverter()
        assert converter.current_pos == [0.0, 0.0]
        assert converter.last_control is None
        assert converter.start_pos == [0.0, 0.0]
    
    def test_convert_empty_path(self):
        """Test converting path with empty d attribute."""
        converter = PathConverter()
        element = ET.fromstring('<path d=""/>')
        context = Mock(spec=ConversionContext)
        
        result = converter.convert(element, context)
        assert result == ""
    
    def test_convert_missing_d_attribute(self):
        """Test converting path without d attribute."""
        converter = PathConverter()
        element = ET.fromstring('<path/>')
        context = Mock(spec=ConversionContext)
        
        result = converter.convert(element, context)
        assert result == ""
    
    def test_convert_simple_path(self):
        """Test converting simple path with move and line."""
        converter = PathConverter()
        element = ET.fromstring('<path d="M10,10 L20,20"/>')
        
        # Mock context with required attributes
        context = Mock(spec=ConversionContext)
        context.get_next_shape_id.return_value = 1001
        context.viewport_context = Mock()  # Add missing viewport_context
        mock_coord_system = Mock()
        mock_coord_system.page_width = 21600
        mock_coord_system.page_height = 21600
        mock_coord_system.svg_width = 100
        mock_coord_system.svg_height = 100
        context.coordinate_system = mock_coord_system
        
        # Mock style attributes method
        converter._get_style_attributes = Mock(return_value='<mock-styles/>')
        
        result = converter.convert(element, context)
        
        # Check basic structure
        assert '<a:sp>' in result
        assert 'id="1001"' in result
        assert 'name="Path"' in result
        assert '<a:custGeom>' in result
        assert '<a:pathLst>' in result
        
        # Should contain move and line commands
        assert '<a:moveTo>' in result
        assert '<a:lnTo>' in result
        
        # Check that context methods were called
        context.get_next_shape_id.assert_called_once()
    
    def test_handle_move_absolute(self):
        """Test handling absolute move commands."""
        converter = PathConverter()
        
        # Use UnitConverter for EMU calculations
        from src.converters.base import BaseConverter
        class MockConverter(BaseConverter):
            def can_convert(self, element): return True
            def convert(self, element, context): return ""
        mock_converter = MockConverter()
        
        # Calculate expected coordinates using standardized tool
        expected_x = int((10.0 / 100) * 21600)  # SVG coordinate system scaling
        expected_y = int((20.0 / 100) * 21600)
        
        context = Mock(spec=ConversionContext)
        mock_coord_system = Mock()
        mock_coord_system.svg_width = 100
        mock_coord_system.svg_height = 100
        context.coordinate_system = mock_coord_system
        
        commands = converter._handle_move('M', [10.0, 20.0], context)
        
        assert len(commands) == 1
        assert '<a:moveTo>' in commands[0]
        assert f'x="{expected_x}"' in commands[0]  # Tool-based calculation
        assert f'y="{expected_y}"' in commands[0]  # Tool-based calculation
        
        # Check state updates
        assert converter.current_pos == [10.0, 20.0]
        assert converter.start_pos == [10.0, 20.0]
        assert converter.last_control is None
    
    def test_handle_move_relative(self):
        """Test handling relative move commands."""
        converter = PathConverter()
        converter.current_pos = [5.0, 10.0]  # Set current position
        
        context = Mock(spec=ConversionContext)
        mock_coord_system = Mock()
        mock_coord_system.svg_width = 100
        mock_coord_system.svg_height = 100
        context.coordinate_system = mock_coord_system
        
        commands = converter._handle_move('m', [10.0, 15.0], context)
        
        assert len(commands) == 1
        # Should add to current position: 5+10=15, 10+15=25
        assert converter.current_pos == [15.0, 25.0]
    
    def test_handle_multiple_moves(self):
        """Test handling move command with multiple coordinate pairs."""
        converter = PathConverter()
        context = Mock(spec=ConversionContext)
        mock_coord_system = Mock()
        mock_coord_system.svg_width = 100
        mock_coord_system.svg_height = 100
        context.coordinate_system = mock_coord_system
        
        # Multiple coordinates: first is moveTo, rest are lineTo
        commands = converter._handle_move('M', [10.0, 10.0, 20.0, 20.0], context)
        
        assert len(commands) == 2
        assert '<a:moveTo>' in commands[0]
        assert '<a:lnTo>' in commands[1]
    
    def test_handle_line_absolute(self):
        """Test handling absolute line commands."""
        converter = PathConverter()
        converter.current_pos = [10.0, 10.0]
        
        # Use tool-based coordinate calculations
        expected_x = int((30.0 / 100) * 21600)  # SVG coordinate system scaling
        expected_y = int((40.0 / 100) * 21600)
        
        context = Mock(spec=ConversionContext)
        mock_coord_system = Mock()
        mock_coord_system.svg_width = 100
        mock_coord_system.svg_height = 100
        context.coordinate_system = mock_coord_system
        
        commands = converter._handle_line('L', [30.0, 40.0], context)
        
        assert len(commands) == 1
        assert '<a:lnTo>' in commands[0]
        assert f'x="{expected_x}"' in commands[0]  # Tool-based calculation
        assert f'y="{expected_y}"' in commands[0]  # Tool-based calculation
        
        # Check state updates
        assert converter.current_pos == [30.0, 40.0]
        assert converter.last_control is None
    
    def test_handle_line_relative(self):
        """Test handling relative line commands."""
        converter = PathConverter()
        converter.current_pos = [10.0, 20.0]
        
        context = Mock(spec=ConversionContext)
        mock_coord_system = Mock()
        mock_coord_system.svg_width = 100
        mock_coord_system.svg_height = 100
        context.coordinate_system = mock_coord_system
        
        commands = converter._handle_line('l', [15.0, 25.0], context)
        
        # Should add to current position: 10+15=25, 20+25=45
        assert converter.current_pos == [25.0, 45.0]
    
    def test_handle_horizontal_line_absolute(self):
        """Test handling absolute horizontal line commands."""
        converter = PathConverter()
        converter.current_pos = [10.0, 20.0]
        
        # Use tool-based coordinate calculations
        expected_x = int((50.0 / 100) * 21600)  # New X position
        expected_y = int((20.0 / 100) * 21600)  # Y unchanged from current position
        
        context = Mock(spec=ConversionContext)
        mock_coord_system = Mock()
        mock_coord_system.svg_width = 100
        mock_coord_system.svg_height = 100
        context.coordinate_system = mock_coord_system
        
        commands = converter._handle_horizontal_line('H', [50.0], context)
        
        assert len(commands) == 1
        assert '<a:lnTo>' in commands[0]
        assert f'x="{expected_x}"' in commands[0]  # Tool-based calculation
        assert f'y="{expected_y}"' in commands[0]  # Y unchanged from current position
        
        # X position should change, Y should stay the same
        assert converter.current_pos == [50.0, 20.0]
    
    def test_handle_vertical_line_absolute(self):
        """Test handling absolute vertical line commands."""
        converter = PathConverter()
        converter.current_pos = [10.0, 20.0]
        
        # Use tool-based coordinate calculations
        expected_x = int((10.0 / 100) * 21600)  # X unchanged from current position
        expected_y = int((60.0 / 100) * 21600)  # New Y position
        
        context = Mock(spec=ConversionContext)
        mock_coord_system = Mock()
        mock_coord_system.svg_width = 100
        mock_coord_system.svg_height = 100
        context.coordinate_system = mock_coord_system
        
        commands = converter._handle_vertical_line('V', [60.0], context)
        
        assert len(commands) == 1
        assert '<a:lnTo>' in commands[0]
        assert f'x="{expected_x}"' in commands[0]  # X unchanged from current position
        assert f'y="{expected_y}"' in commands[0]  # Tool-based calculation
        
        # Y position should change, X should stay the same
        assert converter.current_pos == [10.0, 60.0]
    
    def test_handle_cubic_curve_absolute(self):
        """Test handling absolute cubic Bezier curve commands."""
        converter = PathConverter()
        converter.current_pos = [0.0, 0.0]
        
        context = Mock(spec=ConversionContext)
        mock_coord_system = Mock()
        mock_coord_system.svg_width = 100
        mock_coord_system.svg_height = 100
        context.coordinate_system = mock_coord_system
        
        # C x1,y1 x2,y2 x,y
        commands = converter._handle_cubic_curve('C', [10.0, 20.0, 30.0, 40.0, 50.0, 60.0], context)
        
        assert len(commands) == 1
        assert '<a:cubicBezTo>' in commands[0]
        
        # Should contain all three control points
        assert commands[0].count('<a:pt') == 3
        
        # Check final position and control point
        assert converter.current_pos == [50.0, 60.0]
        assert converter.last_control == [30.0, 40.0]  # Second control point
    
    def test_handle_cubic_curve_relative(self):
        """Test handling relative cubic Bezier curve commands."""
        converter = PathConverter()
        converter.current_pos = [10.0, 10.0]
        
        context = Mock(spec=ConversionContext)
        mock_coord_system = Mock()
        mock_coord_system.svg_width = 100
        mock_coord_system.svg_height = 100
        context.coordinate_system = mock_coord_system
        
        # c dx1,dy1 dx2,dy2 dx,dy (relative to current position)
        commands = converter._handle_cubic_curve('c', [5.0, 10.0, 15.0, 20.0, 25.0, 30.0], context)
        
        # Final position should be current + relative: 10+25=35, 10+30=40
        assert converter.current_pos == [35.0, 40.0]
        # Last control should be current + relative: 10+15=25, 10+20=30
        assert converter.last_control == [25.0, 30.0]
    
    def test_handle_smooth_cubic(self):
        """Test handling smooth cubic Bezier curve commands."""
        converter = PathConverter()
        converter.current_pos = [20.0, 30.0]
        converter.last_control = [15.0, 25.0]  # Previous control point
        
        context = Mock(spec=ConversionContext)
        mock_coord_system = Mock()
        mock_coord_system.svg_width = 100
        mock_coord_system.svg_height = 100
        context.coordinate_system = mock_coord_system
        
        # S x2,y2 x,y (first control point is calculated automatically)
        commands = converter._handle_smooth_cubic('S', [35.0, 45.0, 40.0, 50.0], context)
        
        assert len(commands) == 1
        assert '<a:cubicBezTo>' in commands[0]
        
        # Check final position and new control point
        assert converter.current_pos == [40.0, 50.0]
        assert converter.last_control == [35.0, 45.0]
    
    def test_handle_smooth_cubic_no_previous_control(self):
        """Test smooth cubic when there's no previous control point."""
        converter = PathConverter()
        converter.current_pos = [20.0, 30.0]
        converter.last_control = None
        
        context = Mock(spec=ConversionContext)
        mock_coord_system = Mock()
        mock_coord_system.svg_width = 100
        mock_coord_system.svg_height = 100
        context.coordinate_system = mock_coord_system
        
        commands = converter._handle_smooth_cubic('S', [35.0, 45.0, 40.0, 50.0], context)
        
        # Should still work, using current position as first control point
        assert len(commands) == 1
        assert converter.current_pos == [40.0, 50.0]
    
    def test_handle_quadratic_curve(self):
        """Test handling quadratic Bezier curve commands."""
        converter = PathConverter()
        converter.current_pos = [10.0, 10.0]
        
        context = Mock(spec=ConversionContext)
        mock_coord_system = Mock()
        mock_coord_system.svg_width = 100
        mock_coord_system.svg_height = 100
        context.coordinate_system = mock_coord_system
        
        # Q x1,y1 x,y (converted to cubic)
        commands = converter._handle_quadratic_curve('Q', [20.0, 5.0, 30.0, 10.0], context)
        
        assert len(commands) == 1
        assert '<a:cubicBezTo>' in commands[0]  # Quadratic converted to cubic
        
        # Check final position and control point storage
        assert converter.current_pos == [30.0, 10.0]
        assert converter.last_control == [20.0, 5.0]  # Quadratic control point
    
    def test_handle_smooth_quadratic(self):
        """Test handling smooth quadratic Bezier curve commands."""
        converter = PathConverter()
        converter.current_pos = [20.0, 20.0]
        converter.last_control = [15.0, 10.0]  # Previous quadratic control
        
        context = Mock(spec=ConversionContext)
        mock_coord_system = Mock()
        mock_coord_system.svg_width = 100
        mock_coord_system.svg_height = 100
        context.coordinate_system = mock_coord_system
        
        # T x,y (control point calculated automatically)
        commands = converter._handle_smooth_quadratic('T', [30.0, 25.0], context)
        
        assert len(commands) == 1
        assert '<a:cubicBezTo>' in commands[0]  # Converted to cubic
        
        assert converter.current_pos == [30.0, 25.0]
    
    def test_handle_arc_command(self):
        """Test handling arc commands (simplified implementation)."""
        converter = PathConverter()
        converter.current_pos = [10.0, 10.0]
        
        context = Mock(spec=ConversionContext)
        mock_coord_system = Mock()
        mock_coord_system.svg_width = 100
        mock_coord_system.svg_height = 100
        context.coordinate_system = mock_coord_system
        
        # A rx,ry rotation large-arc-flag,sweep-flag x,y
        commands = converter._handle_arc('A', [25.0, 25.0, 0.0, 0.0, 1.0, 50.0, 25.0], context)
        
        # Current implementation falls back to line
        assert len(commands) == 1
        assert '<a:lnTo>' in commands[0]
        
        assert converter.current_pos == [50.0, 25.0]
        assert converter.last_control is None  # Arcs reset control point
    
    def test_close_path_command(self):
        """Test close path command handling."""
        converter = PathConverter()
        path_data = PathData("M10,10 L20,20 Z")
        
        context = Mock(spec=ConversionContext)
        mock_coord_system = Mock()
        mock_coord_system.svg_width = 100
        mock_coord_system.svg_height = 100
        context.coordinate_system = mock_coord_system
        
        geometry = converter._create_custom_geometry(path_data, context)
        
        assert '<a:close/>' in geometry
    
    def test_coordinate_scaling(self):
        """Test coordinate scaling to DrawingML 21600 coordinate system."""
        converter = PathConverter()
        
        # Use tool-based coordinate calculations for different SVG dimensions
        expected_x = int((100.0 / 200) * 21600)  # (100/200)*21600=10800
        expected_y = int((50.0 / 100) * 21600)   # (50/100)*21600=10800
        
        context = Mock(spec=ConversionContext)
        mock_coord_system = Mock()
        mock_coord_system.svg_width = 200  # SVG is 200 units wide
        mock_coord_system.svg_height = 100  # SVG is 100 units tall
        context.coordinate_system = mock_coord_system
        
        # Point at (100, 50) should be center
        commands = converter._handle_move('M', [100.0, 50.0], context)
        
        assert f'x="{expected_x}"' in commands[0]  # Center X (tool-based)
        assert f'y="{expected_y}"' in commands[0]  # Center Y (tool-based)
    
    def test_state_reset_on_convert(self):
        """Test that converter state is reset on each convert call."""
        converter = PathConverter()
        
        # Set some state
        converter.current_pos = [50.0, 50.0]
        converter.last_control = [25.0, 25.0]
        converter.start_pos = [10.0, 10.0]
        
        element = ET.fromstring('<path d="M0,0 L10,10"/>')
        context = Mock(spec=ConversionContext)
        context.get_next_shape_id.return_value = 1001
        context.viewport_context = Mock()  # Add missing viewport_context
        mock_coord_system = Mock()
        mock_coord_system.page_width = 21600
        mock_coord_system.page_height = 21600
        mock_coord_system.svg_width = 100
        mock_coord_system.svg_height = 100
        context.coordinate_system = mock_coord_system
        converter._get_style_attributes = Mock(return_value='')
        
        converter.convert(element, context)
        
        # State should be reset to initial values before processing
        # After processing M0,0 L10,10, current_pos should be [10, 10]
        assert converter.current_pos == [10.0, 10.0]
        assert converter.last_control is None
        assert converter.start_pos == [0.0, 0.0]


class TestPathConverterIntegration:
    """Test integration and edge cases for PathConverter."""
    
    def test_complex_path_integration(self):
        """Test converting a complex path with multiple command types."""
        converter = PathConverter()
        
        # Complex path: move, line, curve, close
        element = ET.fromstring('<path d="M10,10 L20,10 Q25,5 30,10 C35,5 45,5 50,10 Z"/>')
        
        context = Mock(spec=ConversionContext)
        context.get_next_shape_id.return_value = 2001
        context.viewport_context = Mock()  # Add missing viewport_context
        mock_coord_system = Mock()
        mock_coord_system.page_width = 21600
        mock_coord_system.page_height = 21600
        mock_coord_system.svg_width = 100
        mock_coord_system.svg_height = 100
        context.coordinate_system = mock_coord_system
        converter._get_style_attributes = Mock(return_value='<fill>red</fill>')
        
        result = converter.convert(element, context)
        
        # Check that all command types are present
        assert '<a:moveTo>' in result
        assert '<a:lnTo>' in result
        assert '<a:cubicBezTo>' in result  # Both Q and C convert to cubic
        assert '<a:close/>' in result
        
        # Check structure
        assert '<a:custGeom>' in result
        assert '<a:pathLst>' in result
        assert '<fill>red</fill>' in result
    
    def test_relative_vs_absolute_commands(self):
        """Test that relative and absolute commands produce different results."""
        converter = PathConverter()
        
        context = Mock(spec=ConversionContext)
        mock_coord_system = Mock()
        mock_coord_system.svg_width = 100
        mock_coord_system.svg_height = 100
        context.coordinate_system = mock_coord_system
        
        # Start at (10, 10)
        converter.current_pos = [10.0, 10.0]
        
        # Absolute move to (20, 20)
        abs_commands = converter._handle_move('M', [20.0, 20.0], context)
        abs_pos = list(converter.current_pos)
        
        # Reset and do relative move by (20, 20) from (10, 10)
        converter.current_pos = [10.0, 10.0]
        rel_commands = converter._handle_move('m', [20.0, 20.0], context)
        rel_pos = list(converter.current_pos)
        
        # Results should be different - absolute goes to (20,20), relative goes to (10+20,10+20)=(30,30)
        assert abs_pos == [20.0, 20.0]
        assert rel_pos == [30.0, 30.0]
        
        # But try different starting position
        converter.current_pos = [5.0, 5.0]
        rel_commands2 = converter._handle_move('m', [20.0, 20.0], context)
        
        # Now relative should be different: (5+20, 5+20) = (25, 25)
        assert converter.current_pos == [25.0, 25.0]
    
    def test_error_handling_insufficient_coordinates(self):
        """Test handling of commands with insufficient coordinates."""
        converter = PathConverter()
        context = Mock(spec=ConversionContext)
        mock_coord_system = Mock()
        mock_coord_system.svg_width = 100
        mock_coord_system.svg_height = 100
        context.coordinate_system = mock_coord_system
        
        # Line command with only one coordinate (needs 2)
        commands = converter._handle_line('L', [10.0], context)
        assert commands == []  # Should handle gracefully
        
        # Cubic curve with insufficient coordinates (needs 6)
        commands = converter._handle_cubic_curve('C', [10.0, 20.0, 30.0], context)
        assert commands == []  # Should handle gracefully
    
    def test_inheritance_from_base_converter(self):
        """Test that PathConverter inherits from BaseConverter."""
        from src.converters.base import BaseConverter
        
        converter = PathConverter()
        assert isinstance(converter, BaseConverter)
        assert hasattr(converter, 'can_convert')
        assert hasattr(converter, 'get_element_tag')
        assert hasattr(converter, 'parse_style_attribute')
    
    def test_can_convert_method(self):
        """Test the can_convert method implementation."""
        converter = PathConverter()
        
        # Should accept path elements
        path_element = ET.fromstring('<path d="M0,0 L10,10"/>')
        assert converter.can_convert(path_element) is True
        
        # Should reject other elements
        rect_element = ET.fromstring('<rect width="10" height="10"/>')
        assert converter.can_convert(rect_element) is False