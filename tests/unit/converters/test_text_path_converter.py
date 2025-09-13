#!/usr/bin/env python3
"""
Focused tests for SVG textPath converter.

This test suite provides strategic coverage of the text_path module:
- Core data classes and enums
- Path sampling and character placement algorithms
- Font metrics calculations
- Main converter functionality
- PowerPoint output generation
"""

import pytest
import math
from unittest.mock import Mock, patch, MagicMock
from lxml import etree as ET
from typing import List, Optional

from src.converters.text_path import (
    TextPathConverter, PathSampler, FontMetrics,
    TextPathMethod, TextPathSpacing,
    PathPoint, CharacterPlacement, TextPathInfo
)
from src.converters.base import ConversionContext
from src.colors import ColorInfo


class TestTextPathEnums:
    """Test enum classes."""
    
    def test_text_path_method_values(self):
        """Test TextPathMethod enum values."""
        assert TextPathMethod.ALIGN.value == "align"
        assert TextPathMethod.STRETCH.value == "stretch"
    
    def test_text_path_spacing_values(self):
        """Test TextPathSpacing enum values."""
        assert TextPathSpacing.EXACT.value == "exact"
        assert TextPathSpacing.AUTO.value == "auto"


class TestPathPoint:
    """Test PathPoint dataclass."""
    
    def test_path_point_creation(self):
        """Test PathPoint creation."""
        point = PathPoint(x=10.0, y=20.0, angle=45.0, distance=100.0)
        assert point.x == 10.0
        assert point.y == 20.0
        assert point.angle == 45.0
        assert point.distance == 100.0
    
    def test_get_normal_point(self):
        """Test getting normal point perpendicular to path."""
        point = PathPoint(x=0.0, y=0.0, angle=0.0, distance=0.0)
        
        # Normal point with offset 10 should be at (0, 10) for 0° angle
        normal_x, normal_y = point.get_normal_point(10.0)
        assert abs(normal_x - 0.0) < 0.001
        assert abs(normal_y - 10.0) < 0.001
        
        # Test with 45° angle
        point_45 = PathPoint(x=0.0, y=0.0, angle=45.0, distance=0.0)
        normal_x, normal_y = point_45.get_normal_point(10.0)
        # Should be at approximately (-7.07, 7.07)
        expected_x = 10.0 * math.cos(math.radians(135))
        expected_y = 10.0 * math.sin(math.radians(135))
        assert abs(normal_x - expected_x) < 0.1
        assert abs(normal_y - expected_y) < 0.1


class TestCharacterPlacement:
    """Test CharacterPlacement dataclass."""
    
    def test_character_placement_creation(self):
        """Test CharacterPlacement creation."""
        placement = CharacterPlacement(
            character="A",
            x=50.0,
            y=100.0,
            rotation=30.0,
            advance=12.0,
            baseline_offset=2.0
        )
        
        assert placement.character == "A"
        assert placement.x == 50.0
        assert placement.y == 100.0
        assert placement.rotation == 30.0
        assert placement.advance == 12.0
        assert placement.baseline_offset == 2.0


class TestTextPathInfo:
    """Test TextPathInfo dataclass."""
    
    def test_text_path_info_creation(self):
        """Test TextPathInfo creation."""
        color_info = ColorInfo(red=255, green=0, blue=0, alpha=1.0)
        
        info = TextPathInfo(
            path_id="path1",
            text_content="Hello World",
            start_offset=10.0,
            method=TextPathMethod.ALIGN,
            spacing=TextPathSpacing.EXACT,
            href="#path1",
            font_family="Arial",
            font_size=14.0,
            fill=color_info
        )
        
        assert info.path_id == "path1"
        assert info.text_content == "Hello World"
        assert info.start_offset == 10.0
        assert info.method == TextPathMethod.ALIGN
        assert info.spacing == TextPathSpacing.EXACT
        assert info.href == "#path1"
        assert info.font_family == "Arial"
        assert info.font_size == 14.0
        assert info.fill == color_info
    
    def test_get_effective_start_offset_absolute(self):
        """Test effective start offset calculation for absolute values."""
        info = TextPathInfo(
            path_id="path1", text_content="test", start_offset=25.0,
            method=TextPathMethod.ALIGN, spacing=TextPathSpacing.EXACT,
            href="#path1", font_family="Arial", font_size=12.0, fill=None
        )
        
        result = info.get_effective_start_offset(100.0)
        assert result == 25.0
    
    def test_get_effective_start_offset_percentage(self):
        """Test effective start offset calculation for percentage values."""
        info = TextPathInfo(
            path_id="path1", text_content="test", start_offset="25%",
            method=TextPathMethod.ALIGN, spacing=TextPathSpacing.EXACT,
            href="#path1", font_family="Arial", font_size=12.0, fill=None
        )
        
        result = info.get_effective_start_offset(200.0)
        assert result == 50.0  # 25% of 200


class TestFontMetrics:
    """Test FontMetrics functionality."""
    
    def test_font_metrics_initialization(self):
        """Test FontMetrics initialization."""
        metrics = FontMetrics("Times New Roman", 16.0)
        
        assert metrics.font_family == "Times New Roman"
        assert metrics.font_size == 16.0
        assert metrics.ascent == 16.0 * 0.8
        assert metrics.descent == 16.0 * 0.2
        assert metrics.avg_char_width == 16.0 * 0.6
    
    def test_get_character_advance_space(self):
        """Test character advance for space."""
        metrics = FontMetrics("Arial", 12.0)
        advance = metrics.get_character_advance(' ')
        assert advance == metrics.space_width
    
    def test_get_character_advance_narrow_chars(self):
        """Test character advance for narrow characters."""
        metrics = FontMetrics("Arial", 12.0)
        for char in 'il1|!':
            advance = metrics.get_character_advance(char)
            assert advance == metrics.avg_char_width * 0.3
    
    def test_get_character_advance_wide_chars(self):
        """Test character advance for wide characters."""
        metrics = FontMetrics("Arial", 12.0)
        for char in 'MW':
            advance = metrics.get_character_advance(char)
            assert advance == metrics.avg_char_width * 1.2
    
    def test_get_text_length(self):
        """Test total text length calculation."""
        metrics = FontMetrics("Arial", 12.0)
        length = metrics.get_text_length("Hi!")
        
        # Should be sum of individual character advances
        expected = (metrics.get_character_advance('H') + 
                   metrics.get_character_advance('i') + 
                   metrics.get_character_advance('!'))
        assert length == expected


class TestPathSampler:
    """Test PathSampler functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.sampler = PathSampler()
    
    def test_sample_line_path(self):
        """Test sampling a simple line path."""
        path_data = "M 0 0 L 100 0"
        points = self.sampler.sample_path(path_data, 5)
        
        assert len(points) > 0
        # First point should be near (0, 0)
        assert abs(points[0].x - 0.0) < 0.1
        assert abs(points[0].y - 0.0) < 0.1
        # Last point should be near (100, 0)
        assert abs(points[-1].x - 100.0) < 10.0
        assert abs(points[-1].y - 0.0) < 0.1
    
    def test_sample_empty_path(self):
        """Test sampling empty path."""
        points = self.sampler.sample_path("", 10)
        assert len(points) == 0
        
        points = self.sampler.sample_path("   ", 10)
        assert len(points) == 0
    
    def test_parse_path_commands_simple(self):
        """Test parsing simple path commands."""
        commands = self.sampler._parse_path_commands("M 10 20 L 30 40")
        
        assert len(commands) >= 2
        assert commands[0][0] == 'M'
        # Should have extracted numeric parameters
        assert len(commands[0]) >= 3  # Command + x + y
    
    def test_parse_path_commands_empty(self):
        """Test parsing empty path."""
        commands = self.sampler._parse_path_commands("")
        assert commands == []
    
    def test_sample_line_points(self):
        """Test line point sampling."""
        points = self.sampler._sample_line(0.0, 0.0, 10.0, 10.0, 3)
        
        assert len(points) == 3
        assert points[0] == (0.0, 0.0)
        assert points[-1] == (10.0, 10.0)
        # Middle point should be approximately (5, 5)
        assert abs(points[1][0] - 5.0) < 0.1
        assert abs(points[1][1] - 5.0) < 0.1
    
    def test_sample_cubic_bezier(self):
        """Test cubic Bézier curve sampling."""
        points = self.sampler._sample_cubic_bezier(
            0.0, 0.0,  # Start
            10.0, 0.0,  # Control 1
            10.0, 10.0,  # Control 2
            0.0, 10.0,  # End
            5
        )
        
        assert len(points) == 5
        assert points[0] == (0.0, 0.0)
        assert points[-1] == (0.0, 10.0)
    
    def test_calculate_angle(self):
        """Test angle calculation between points."""
        # Horizontal line (0 degrees)
        angle = self.sampler._calculate_angle((0.0, 0.0), (10.0, 0.0))
        assert abs(angle - 0.0) < 0.1
        
        # Vertical line up (90 degrees)
        angle = self.sampler._calculate_angle((0.0, 0.0), (0.0, 10.0))
        assert abs(angle - 90.0) < 0.1
        
        # Diagonal (45 degrees)
        angle = self.sampler._calculate_angle((0.0, 0.0), (10.0, 10.0))
        assert abs(angle - 45.0) < 0.1


class TestTextPathConverter:
    """Test TextPathConverter main functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.converter = TextPathConverter()
        self.context = Mock()
        self.context.get_next_shape_id.return_value = 1000
        
        # Mock dependencies
        self.converter.unit_converter = Mock()
        self.converter.unit_converter.convert_to_emu.return_value = 914400  # 1 inch in EMU
        self.converter.color_parser = Mock()
        self.converter.color_parser.parse.return_value = ColorInfo(255, 0, 0, 1.0)
        self.converter.color_parser.to_drawingml.return_value = "<a:srgbClr val='FF0000'/>"
    
    def test_can_convert_textpath_element(self):
        """Test can_convert with textPath element."""
        textpath = ET.Element("textPath")
        result = self.converter.can_convert(textpath, self.context)
        assert result is True
    
    def test_can_convert_text_with_textpath(self):
        """Test can_convert with text element containing textPath."""
        text = ET.Element("text")
        textpath_child = ET.SubElement(text, "textPath")
        
        result = self.converter.can_convert(text, self.context)
        assert result is True
    
    def test_can_convert_unsupported_element(self):
        """Test can_convert with unsupported element."""
        rect = ET.Element("rect")
        result = self.converter.can_convert(rect, self.context)
        assert result is False
    
    def test_has_text_path(self):
        """Test _has_text_path method."""
        text_without_path = ET.Element("text")
        assert self.converter._has_text_path(text_without_path) is False
        
        text_with_path = ET.Element("text")
        ET.SubElement(text_with_path, "textPath")
        assert self.converter._has_text_path(text_with_path) is True
    
    def test_extract_textpath_info_basic(self):
        """Test basic textPath info extraction."""
        textpath = ET.Element("textPath")
        textpath.set("href", "#path1")
        textpath.text = "Hello World"
        textpath.set("font-family", "Arial")
        textpath.set("font-size", "14px")
        
        info = self.converter._extract_textpath_info(textpath)
        
        assert info is not None
        assert info.path_id == "path1"
        assert info.text_content == "Hello World"
        assert info.font_family == "Arial"
        assert info.font_size == 14.0
        assert info.method == TextPathMethod.ALIGN  # default
        assert info.spacing == TextPathSpacing.EXACT  # default
    
    def test_extract_textpath_info_with_attributes(self):
        """Test textPath info extraction with all attributes."""
        textpath = ET.Element("textPath")
        textpath.set("href", "#mypath")
        textpath.text = "Test Text"
        textpath.set("startOffset", "25%")
        textpath.set("method", "stretch")
        textpath.set("spacing", "auto")
        textpath.set("font-family", "Times")
        textpath.set("font-size", "16")
        textpath.set("fill", "red")
        
        info = self.converter._extract_textpath_info(textpath)
        
        assert info.path_id == "mypath"
        assert info.start_offset == "25%"
        assert info.method == TextPathMethod.STRETCH
        assert info.spacing == TextPathSpacing.AUTO
        assert info.font_family == "Times"
        assert info.font_size == 16.0
    
    def test_extract_textpath_info_no_href(self):
        """Test textPath info extraction without href."""
        textpath = ET.Element("textPath")
        textpath.text = "Some text"
        
        info = self.converter._extract_textpath_info(textpath)
        assert info is None
    
    def test_extract_textpath_info_no_text(self):
        """Test textPath info extraction without text content."""
        textpath = ET.Element("textPath")
        textpath.set("href", "#path1")
        # No text content
        
        info = self.converter._extract_textpath_info(textpath)
        assert info is None
    
    def test_get_path_definition_from_context(self):
        """Test getting path definition from context."""
        # Mock SVG root with path element
        path_element = ET.Element("path")
        path_element.set("id", "testpath")
        path_element.set("d", "M 0 0 L 100 100")
        
        svg_root = ET.Element("svg")
        svg_root.append(path_element)
        
        self.context.svg_root = svg_root
        
        path_data = self.converter._get_path_definition("testpath", self.context)
        assert path_data == "M 0 0 L 100 100"
    
    def test_get_path_definition_not_found(self):
        """Test getting path definition that doesn't exist."""
        self.context.svg_root = ET.Element("svg")  # Empty root
        
        path_data = self.converter._get_path_definition("nonexistent", self.context)
        assert path_data is None
    
    def test_interpolate_path_point_middle(self):
        """Test path point interpolation in middle of path."""
        points = [
            PathPoint(0.0, 0.0, 0.0, 0.0),
            PathPoint(10.0, 0.0, 0.0, 10.0),
            PathPoint(20.0, 0.0, 0.0, 20.0)
        ]
        
        # Interpolate at distance 5 (middle of first segment)
        result = self.converter._interpolate_path_point(points, 5.0)
        
        assert result is not None
        assert abs(result.x - 5.0) < 0.1
        assert abs(result.y - 0.0) < 0.1
        assert result.distance == 5.0
    
    def test_interpolate_path_point_beyond_path(self):
        """Test path point interpolation beyond path end."""
        points = [
            PathPoint(0.0, 0.0, 0.0, 0.0),
            PathPoint(10.0, 0.0, 0.0, 10.0)
        ]
        
        result = self.converter._interpolate_path_point(points, 50.0)
        assert result == points[-1]  # Should return last point
    
    def test_interpolate_path_point_before_path(self):
        """Test path point interpolation before path start."""
        points = [
            PathPoint(0.0, 0.0, 0.0, 0.0),
            PathPoint(10.0, 0.0, 0.0, 10.0)
        ]
        
        result = self.converter._interpolate_path_point(points, -5.0)
        assert result == points[0]  # Should return first point
    
    def test_angle_difference_simple(self):
        """Test angle difference calculation."""
        # Simple case: 10° to 20°
        diff = self.converter._angle_difference(10.0, 20.0)
        assert diff == 10.0
        
        # Wrapping case: 350° to 10°
        diff = self.converter._angle_difference(350.0, 10.0)
        assert diff == 20.0
        
        # Negative wrapping: 10° to 350°
        diff = self.converter._angle_difference(10.0, 350.0)
        assert diff == -20.0
    
    def test_has_complex_path_simple(self):
        """Test complex path detection for simple paths."""
        simple_path = "M 0 0 L 100 0"
        assert self.converter._has_complex_path(simple_path) is False
        
        empty_path = ""
        assert self.converter._has_complex_path(empty_path) is False
    
    def test_has_complex_path_complex(self):
        """Test complex path detection for complex paths."""
        # Path with many curves
        complex_path = "M 0 0 C 10 10 20 20 30 30 C 40 40 50 50 60 60 C 70 70 80 80 90 90"
        assert self.converter._has_complex_path(complex_path) is True
        
        # Very long path
        long_path = "M " + " L ".join([f"{i} {i}" for i in range(50)])
        assert self.converter._has_complex_path(long_path) is True
    
    def test_calculate_character_placements_simple(self):
        """Test character placement calculation."""
        textpath_info = TextPathInfo(
            path_id="path1", text_content="Hi", start_offset=0.0,
            method=TextPathMethod.ALIGN, spacing=TextPathSpacing.EXACT,
            href="#path1", font_family="Arial", font_size=12.0, fill=None
        )
        
        # Simple straight path
        path_points = [
            PathPoint(0.0, 0.0, 0.0, 0.0),
            PathPoint(50.0, 0.0, 0.0, 50.0),
            PathPoint(100.0, 0.0, 0.0, 100.0)
        ]
        
        placements = self.converter._calculate_character_placements(textpath_info, path_points)
        
        assert len(placements) == 2  # "H" and "i"
        assert placements[0].character == "H"
        assert placements[1].character == "i"
        
        # First character should be at start of path
        assert abs(placements[0].x - 0.0) < 1.0
        assert abs(placements[0].y - 0.0) < 1.0
    
    def test_generate_character_shape(self):
        """Test character shape generation."""
        placement = CharacterPlacement(
            character="A", x=10.0, y=20.0, rotation=45.0,
            advance=8.0, baseline_offset=0.0
        )
        
        textpath_info = TextPathInfo(
            path_id="path1", text_content="A", start_offset=0.0,
            method=TextPathMethod.ALIGN, spacing=TextPathSpacing.EXACT,
            href="#path1", font_family="Arial", font_size=12.0,
            fill=ColorInfo(255, 0, 0, 1.0)
        )
        
        result = self.converter._generate_character_shape(placement, textpath_info, 1001)
        
        assert "<p:sp>" in result
        assert "char_A" in result
        assert "id=\"1001\"" in result
        assert "Arial" in result
        assert "A" in result  # Character content
        # Rotation should be converted to DrawingML format (degrees * 60000)
        assert str(int(45.0 * 60000)) in result
    
    def test_generate_rasterized_textpath(self):
        """Test rasterized textPath generation."""
        textpath_info = TextPathInfo(
            path_id="path1", text_content="Complex Text Path", start_offset=0.0,
            method=TextPathMethod.STRETCH, spacing=TextPathSpacing.AUTO,
            href="#path1", font_family="Times", font_size=14.0, fill=None
        )
        
        result = self.converter._generate_rasterized_textpath(textpath_info, self.context)
        
        assert "<p:sp>" in result
        assert "textPath_raster" in result
        assert "Complex Text Path" in result
        assert "requires rasterization" in result
    
    def test_convert_textpath_element(self):
        """Test converting textPath element."""
        textpath = ET.Element("textPath")
        textpath.set("href", "#simplepath")
        textpath.text = "Test"
        
        # Mock path definition
        self.converter.path_definitions["simplepath"] = "M 0 0 L 100 0"
        
        with patch.object(self.converter, '_generate_positioned_text') as mock_gen:
            mock_gen.return_value = "<positioned text output>"
            
            result = self.converter.convert(textpath, self.context)
            
            assert result == "<positioned text output>"
            mock_gen.assert_called_once()
    
    def test_convert_text_with_textpath(self):
        """Test converting text element containing textPath."""
        text = ET.Element("text")
        textpath = ET.SubElement(text, "textPath")
        textpath.set("href", "#testpath")
        textpath.text = "Hello"
        
        # Mock path definition
        self.converter.path_definitions["testpath"] = "M 0 0 L 50 50"
        
        with patch.object(self.converter, '_generate_positioned_text') as mock_gen:
            mock_gen.return_value = "<text with path output>"
            
            result = self.converter.convert(text, self.context)
            
            assert result == "<text with path output>"
    
    def test_convert_unsupported_element(self):
        """Test converting unsupported element."""
        rect = ET.Element("rect")
        result = self.converter.convert(rect, self.context)
        assert result == ""


class TestIntegrationScenarios:
    """Test integration scenarios combining multiple components."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.converter = TextPathConverter()
        self.context = Mock()
        self.context.get_next_shape_id.side_effect = range(2000, 3000)
        
        # Mock dependencies
        self.converter.unit_converter = Mock()
        self.converter.unit_converter.convert_to_emu.return_value = 914400
        self.converter.color_parser = Mock()
        self.converter.color_parser.parse.return_value = ColorInfo(0, 0, 255, 1.0)
        self.converter.color_parser.to_drawingml.return_value = "<a:srgbClr val='0000FF'/>"
    
    def test_complete_textpath_workflow(self):
        """Test complete textPath processing workflow."""
        # Create textPath element
        textpath = ET.Element("textPath")
        textpath.set("href", "#mypath")
        textpath.text = "Hello"
        textpath.set("font-family", "Verdana")
        textpath.set("font-size", "16")
        textpath.set("fill", "blue")
        
        # Mock SVG root with path
        path = ET.Element("path")
        path.set("id", "mypath")
        path.set("d", "M 0 0 L 200 0")  # Simple horizontal line
        
        svg_root = ET.Element("svg")
        svg_root.append(path)
        self.context.svg_root = svg_root
        
        # Convert
        result = self.converter.convert(textpath, self.context)
        
        # Should generate positioned text (not rasterized for simple case)
        assert "<p:grpSp>" in result or "<p:sp>" in result
        assert "Hello" in result or "char_" in result  # Character content
    
    def test_textpath_with_percentage_offset(self):
        """Test textPath with percentage start offset."""
        textpath = ET.Element("textPath")
        textpath.set("href", "#percentpath")
        textpath.set("startOffset", "50%")
        textpath.text = "Middle"
        
        # Mock path definition
        self.converter.path_definitions["percentpath"] = "M 0 0 L 100 0"
        
        # Should process without errors
        result = self.converter.convert(textpath, self.context)
        
        # Should generate some output (positioned or rasterized)
        assert result != ""
    
    def test_complex_textpath_rasterization(self):
        """Test that complex textPath triggers rasterization."""
        textpath = ET.Element("textPath")
        textpath.set("href", "#complexpath")
        textpath.text = "Very Long Text That Should Trigger Rasterization Due To Length And Complexity Of Path"
        
        # Mock complex path with many curves
        complex_path = "M 0 0 " + " ".join([f"C {i*10} {i*5} {i*10+5} {i*5+5} {i*10+10} {i*5}" for i in range(10)])
        self.converter.path_definitions["complexpath"] = complex_path
        
        result = self.converter.convert(textpath, self.context)
        
        # Should generate rasterized output
        assert "textPath_raster" in result
        assert "requires rasterization" in result
    
    def test_textpath_with_no_path_definition(self):
        """Test textPath with missing path definition."""
        textpath = ET.Element("textPath")
        textpath.set("href", "#missingpath")
        textpath.text = "No Path"
        
        self.context.svg_root = ET.Element("svg")  # Empty root
        
        result = self.converter.convert(textpath, self.context)
        assert result == ""  # Should return empty string for missing path


if __name__ == "__main__":
    pytest.main([__file__, "-v"])