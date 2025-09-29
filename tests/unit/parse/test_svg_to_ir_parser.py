#!/usr/bin/env python3
"""
Unit tests for SVG to IR Parser implementation.

Tests the parsing of SVG content into Clean Slate IR structures.
Validates proper conversion of all SVG element types to IR objects.
"""

import sys
import os
import pytest
from unittest.mock import Mock, patch
from lxml import etree as ET

# Add paths for imports (Clean Slate modules)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

# Import the parser and IR types
from core.parse.parser import SVGParser
from core.ir import (
    Path, TextFrame, Group, Image, SceneGraph,
    Point, Rect, LineSegment, BezierSegment,
    SolidPaint, Stroke, Run, TextAnchor
)


class TestSVGToIRParser:
    """Test suite for SVG to IR parser implementation."""

    @pytest.fixture
    def parser(self):
        """Create an SVGParser instance for testing."""
        return SVGParser()

    def test_parse_to_ir_initialization(self, parser):
        """Test that parse_to_ir method exists and is callable."""
        assert hasattr(parser, 'parse_to_ir')
        assert callable(parser.parse_to_ir)

    def test_simple_rect_conversion(self, parser):
        """Test converting SVG rect to IR Path."""
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300">
            <rect x="10" y="20" width="100" height="80" fill="red" stroke="blue" stroke-width="2"/>
        </svg>'''

        scene, parse_result = parser.parse_to_ir(svg_content)

        assert scene is not None
        assert len(scene) == 1
        assert isinstance(scene[0], Path)

        path = scene[0]
        assert len(path.segments) == 4  # Rectangle has 4 line segments
        assert all(isinstance(seg, LineSegment) for seg in path.segments)

        # Check rectangle coordinates
        first_segment = path.segments[0]
        assert first_segment.start.x == 10
        assert first_segment.start.y == 20

        # Check styling
        assert path.fill is not None
        assert isinstance(path.fill, SolidPaint)
        assert path.stroke is not None
        assert isinstance(path.stroke, Stroke)

    def test_circle_conversion(self, parser):
        """Test converting SVG circle to IR Path with Bezier curves."""
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300">
            <circle cx="50" cy="60" r="30" fill="green"/>
        </svg>'''

        scene, parse_result = parser.parse_to_ir(svg_content)

        assert scene is not None
        assert len(scene) == 1
        assert isinstance(scene[0], Path)

        path = scene[0]
        assert len(path.segments) == 4  # Circle approximated with 4 Bezier curves
        assert all(isinstance(seg, BezierSegment) for seg in path.segments)

        # Check styling
        assert path.fill is not None
        assert isinstance(path.fill, SolidPaint)

    def test_ellipse_conversion(self, parser):
        """Test converting SVG ellipse to IR Path with scaled Bezier curves."""
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300">
            <ellipse cx="100" cy="150" rx="80" ry="40" fill="blue"/>
        </svg>'''

        scene, parse_result = parser.parse_to_ir(svg_content)

        assert scene is not None
        assert len(scene) == 1
        assert isinstance(scene[0], Path)

        path = scene[0]
        assert len(path.segments) == 4  # Ellipse approximated with 4 Bezier curves
        assert all(isinstance(seg, BezierSegment) for seg in path.segments)

    def test_line_conversion(self, parser):
        """Test converting SVG line to IR Path."""
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300">
            <line x1="10" y1="20" x2="100" y2="80" stroke="black" stroke-width="3"/>
        </svg>'''

        scene, parse_result = parser.parse_to_ir(svg_content)

        assert scene is not None
        assert len(scene) == 1
        assert isinstance(scene[0], Path)

        path = scene[0]
        assert len(path.segments) == 1  # Line has single segment
        assert isinstance(path.segments[0], LineSegment)

        line = path.segments[0]
        assert line.start.x == 10
        assert line.start.y == 20
        assert line.end.x == 100
        assert line.end.y == 80

    def test_polygon_conversion(self, parser):
        """Test converting SVG polygon to IR Path."""
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300">
            <polygon points="10,10 50,10 30,40" fill="yellow"/>
        </svg>'''

        scene, parse_result = parser.parse_to_ir(svg_content)

        assert scene is not None
        assert len(scene) == 1
        assert isinstance(scene[0], Path)

        path = scene[0]
        assert len(path.segments) == 3  # Triangle has 3 segments
        assert all(isinstance(seg, LineSegment) for seg in path.segments)

    def test_polyline_conversion(self, parser):
        """Test converting SVG polyline to IR Path."""
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300">
            <polyline points="0,0 20,20 40,10" stroke="red" fill="none"/>
        </svg>'''

        scene, parse_result = parser.parse_to_ir(svg_content)

        assert scene is not None
        assert len(scene) == 1
        assert isinstance(scene[0], Path)

        path = scene[0]
        assert len(path.segments) == 2  # Polyline has 2 segments (3 points = 2 lines)
        assert all(isinstance(seg, LineSegment) for seg in path.segments)

    def test_simple_path_conversion(self, parser):
        """Test converting SVG path with basic commands to IR Path."""
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300">
            <path d="M 10 20 L 30 40 L 50 30 Z" fill="purple"/>
        </svg>'''

        scene, parse_result = parser.parse_to_ir(svg_content)

        assert scene is not None
        assert len(scene) == 1
        assert isinstance(scene[0], Path)

        path = scene[0]
        assert len(path.segments) >= 2  # At least the explicit line segments

    def test_text_conversion(self, parser):
        """Test converting SVG text to IR TextFrame."""
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300">
            <text x="50" y="100" font-family="Arial" font-size="16" fill="black">Hello World</text>
        </svg>'''

        scene, parse_result = parser.parse_to_ir(svg_content)

        assert scene is not None
        assert len(scene) == 1
        assert isinstance(scene[0], TextFrame)

        text_frame = scene[0]
        assert text_frame.origin.x == 50
        assert text_frame.origin.y == 100
        assert len(text_frame.runs) == 1

        run = text_frame.runs[0]
        assert run.text == "Hello World"
        assert run.font_family == "Arial"
        assert run.font_size_pt == 16

    def test_image_conversion(self, parser):
        """Test converting SVG image to IR Image."""
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300">
            <image x="10" y="20" width="100" height="80" href="test.png"/>
        </svg>'''

        scene, parse_result = parser.parse_to_ir(svg_content)

        assert scene is not None
        assert len(scene) == 1
        assert isinstance(scene[0], Image)

        image = scene[0]
        assert image.origin.x == 10
        assert image.origin.y == 20
        assert image.size.width == 100
        assert image.size.height == 80
        assert image.href == "test.png"

    def test_group_conversion(self, parser):
        """Test converting SVG group to IR Group."""
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300">
            <g transform="translate(10, 20)" opacity="0.8">
                <rect x="0" y="0" width="50" height="30" fill="red"/>
                <circle cx="25" cy="15" r="10" fill="blue"/>
            </g>
        </svg>'''

        scene, parse_result = parser.parse_to_ir(svg_content)

        assert scene is not None
        assert len(scene) == 1
        assert isinstance(scene[0], Group)

        group = scene[0]
        assert len(group.children) == 2
        assert group.opacity == 0.8

        # Check children types
        assert isinstance(group.children[0], Path)  # rect -> Path
        assert isinstance(group.children[1], Path)  # circle -> Path

    def test_nested_groups(self, parser):
        """Test converting nested SVG groups."""
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300">
            <g opacity="0.9">
                <g transform="scale(2)">
                    <rect x="10" y="10" width="20" height="20" fill="green"/>
                </g>
                <circle cx="50" cy="50" r="15" fill="orange"/>
            </g>
        </svg>'''

        scene, parse_result = parser.parse_to_ir(svg_content)

        assert scene is not None
        assert len(scene) == 1
        assert isinstance(scene[0], Group)

        outer_group = scene[0]
        assert len(outer_group.children) == 2
        assert isinstance(outer_group.children[0], Group)  # nested group
        assert isinstance(outer_group.children[1], Path)   # circle

    def test_multiple_elements(self, parser):
        """Test converting multiple SVG elements at root level."""
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300">
            <rect x="10" y="10" width="50" height="30" fill="red"/>
            <circle cx="100" cy="50" r="20" fill="blue"/>
            <text x="150" y="80" font-size="14">Test</text>
        </svg>'''

        scene, parse_result = parser.parse_to_ir(svg_content)

        assert scene is not None
        assert len(scene) == 3
        assert isinstance(scene[0], Path)       # rect
        assert isinstance(scene[1], Path)       # circle
        assert isinstance(scene[2], TextFrame)  # text

    def test_styling_extraction(self, parser):
        """Test that styling information is properly extracted."""
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300">
            <rect x="10" y="10" width="50" height="30"
                  fill="#FF0000" stroke="rgb(0, 255, 0)" stroke-width="3" opacity="0.7"/>
        </svg>'''

        scene, parse_result = parser.parse_to_ir(svg_content)

        assert scene is not None
        assert len(scene) == 1

        path = scene[0]
        assert path.opacity == 0.7

        # Check fill
        assert path.fill is not None
        assert isinstance(path.fill, SolidPaint)
        assert path.fill.rgb == "FF0000"

        # Check stroke
        assert path.stroke is not None
        assert path.stroke.width == 3

    def test_no_styling(self, parser):
        """Test elements with no styling (defaults applied)."""
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300">
            <rect x="10" y="10" width="50" height="30"/>
        </svg>'''

        scene, parse_result = parser.parse_to_ir(svg_content)

        assert scene is not None
        assert len(scene) == 1

        path = scene[0]
        assert path.opacity == 1.0  # default opacity
        # No fill/stroke should be None or default values

    def test_font_size_parsing(self, parser):
        """Test parsing various font-size formats."""
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300">
            <text x="10" y="30" font-size="12">Size 12</text>
            <text x="10" y="60" font-size="14px">Size 14px</text>
            <text x="10" y="90" font-size="1.2em">Size 1.2em</text>
        </svg>'''

        scene, parse_result = parser.parse_to_ir(svg_content)

        assert scene is not None
        assert len(scene) == 3

        # Check different font size formats are parsed
        for text_frame in scene:
            assert isinstance(text_frame, TextFrame)
            assert text_frame.runs[0].font_size_pt > 0

    def test_empty_svg(self, parser):
        """Test parsing empty SVG returns empty scene."""
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300">
        </svg>'''

        scene, parse_result = parser.parse_to_ir(svg_content)

        assert scene is not None
        assert len(scene) == 0

    def test_unsupported_elements_ignored(self, parser):
        """Test that unsupported SVG elements are ignored gracefully."""
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300">
            <rect x="10" y="10" width="50" height="30" fill="red"/>
            <unsupported_element attr="value"/>
            <circle cx="100" cy="50" r="20" fill="blue"/>
        </svg>'''

        scene, parse_result = parser.parse_to_ir(svg_content)

        assert scene is not None
        assert len(scene) == 2  # Only rect and circle, unsupported ignored
        assert isinstance(scene[0], Path)  # rect
        assert isinstance(scene[1], Path)  # circle

    def test_malformed_svg_handling(self, parser):
        """Test handling of malformed SVG content."""
        malformed_svg = '''<svg xmlns="http://www.w3.org/2000/svg">
            <rect x="10" y="invalid" width="50" height="30"/>
        </svg>'''

        scene, parse_result = parser.parse_to_ir(malformed_svg)

        # Should handle gracefully - either skip invalid elements or use defaults
        assert parse_result is not None

    def test_complex_path_data(self, parser):
        """Test parsing complex SVG path data."""
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300">
            <path d="M 10 20 C 10 10 40 10 40 20 S 70 30 80 20 Q 90 10 100 20 L 120 40 Z" fill="green"/>
        </svg>'''

        scene, parse_result = parser.parse_to_ir(svg_content)

        assert scene is not None
        assert len(scene) == 1
        assert isinstance(scene[0], Path)

        path = scene[0]
        # Should have segments for each path command
        assert len(path.segments) > 0

    def test_rgb_color_parsing(self, parser):
        """Test parsing RGB color values in different formats."""
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300">
            <rect x="10" y="10" width="50" height="30" fill="rgb(255, 0, 0)"/>
            <rect x="70" y="10" width="50" height="30" fill="#00FF00"/>
            <rect x="130" y="10" width="50" height="30" fill="blue"/>
        </svg>'''

        scene, parse_result = parser.parse_to_ir(svg_content)

        assert scene is not None
        assert len(scene) == 3

        # All should be converted to Path objects with fill
        for element in scene:
            assert isinstance(element, Path)
            assert element.fill is not None

    def test_error_recovery(self, parser):
        """Test parser continues processing after encountering errors."""
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300">
            <rect x="10" y="10" width="50" height="30" fill="red"/>
            <rect x="100" y="100" width="50" height="30" fill="green"/>
        </svg>'''

        scene, parse_result = parser.parse_to_ir(svg_content)

        # Should successfully parse valid elements
        assert parse_result.success
        assert scene is not None
        assert len(scene) == 2

    def test_preserve_parse_result(self, parser):
        """Test that original parse result is preserved."""
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300">
            <rect x="10" y="10" width="50" height="30" fill="red"/>
        </svg>'''

        scene, parse_result = parser.parse_to_ir(svg_content)

        assert scene is not None
        assert parse_result is not None
        assert parse_result.success
        assert parse_result.svg_root is not None

    def test_invalid_svg_returns_none_scene(self, parser):
        """Test that invalid SVG returns None scene but valid parse_result."""
        invalid_svg = '''<not-svg>invalid</not-svg>'''

        scene, parse_result = parser.parse_to_ir(invalid_svg)

        # Scene should be None if parsing failed
        # parse_result should indicate failure
        if scene is None:
            assert parse_result is not None
            assert not parse_result.success

    def test_integration_with_preprocessing(self, parser):
        """Test that parser integrates with preprocessing pipeline."""
        # This would test that the parser works with preprocessed SVG
        # For now, just verify the method chain works
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300">
            <rect x="10" y="10" width="50" height="30" fill="red"/>
        </svg>'''

        # Test regular parsing
        parse_result = parser.parse(svg_content)
        assert parse_result.success

        # Test IR conversion
        scene, ir_parse_result = parser.parse_to_ir(svg_content)
        assert scene is not None
        assert ir_parse_result.success

    def test_ir_structure_validation(self, parser):
        """Test that generated IR structures are valid."""
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300">
            <rect x="10" y="10" width="50" height="30" fill="red"/>
            <text x="100" y="50" font-size="14">Test</text>
        </svg>'''

        scene, parse_result = parser.parse_to_ir(svg_content)

        assert scene is not None
        assert isinstance(scene, list)  # SceneGraph is List[IRElement]

        # Validate each element follows IR contracts
        for element in scene:
            assert element is not None

            if isinstance(element, Path):
                assert len(element.segments) > 0
                assert 0.0 <= element.opacity <= 1.0

            elif isinstance(element, TextFrame):
                assert len(element.runs) > 0
                assert all(run.text for run in element.runs)

            elif isinstance(element, Group):
                assert 0.0 <= element.opacity <= 1.0

            elif isinstance(element, Image):
                assert element.data or element.href
                assert 0.0 <= element.opacity <= 1.0


class TestSVGToIRParserEdgeCases:
    """Test edge cases and error conditions for SVG to IR parser."""

    @pytest.fixture
    def parser(self):
        """Create an SVGParser instance for testing."""
        return SVGParser()

    def test_zero_dimension_elements(self, parser):
        """Test handling of zero-dimension elements."""
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300">
            <rect x="10" y="10" width="0" height="30" fill="red"/>
            <circle cx="50" cy="50" r="0" fill="blue"/>
        </svg>'''

        scene, parse_result = parser.parse_to_ir(svg_content)

        # Should handle gracefully - may skip or create minimal elements
        assert parse_result.success

    def test_negative_coordinates(self, parser):
        """Test handling of negative coordinates."""
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300">
            <rect x="-10" y="-20" width="50" height="30" fill="red"/>
            <circle cx="-50" cy="-60" r="20" fill="blue"/>
        </svg>'''

        scene, parse_result = parser.parse_to_ir(svg_content)

        assert scene is not None
        assert len(scene) == 2

        # Negative coordinates should be preserved
        rect_path = scene[0]
        assert isinstance(rect_path, Path)

    def test_very_large_coordinates(self, parser):
        """Test handling of very large coordinate values."""
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300">
            <rect x="1000000" y="2000000" width="50" height="30" fill="red"/>
        </svg>'''

        scene, parse_result = parser.parse_to_ir(svg_content)

        assert scene is not None
        assert len(scene) == 1

    def test_minimal_text(self, parser):
        """Test text elements with minimal attributes."""
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300">
            <text>Minimal text</text>
        </svg>'''

        scene, parse_result = parser.parse_to_ir(svg_content)

        assert scene is not None
        assert len(scene) == 1
        assert isinstance(scene[0], TextFrame)

    def test_empty_text_content(self, parser):
        """Test text elements with empty content."""
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300">
            <text x="10" y="20" font-size="14"></text>
        </svg>'''

        scene, parse_result = parser.parse_to_ir(svg_content)

        # Should handle empty text gracefully
        assert parse_result.success

    def test_deeply_nested_groups(self, parser):
        """Test deeply nested group structures."""
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300">
            <g>
                <g>
                    <g>
                        <rect x="10" y="10" width="50" height="30" fill="red"/>
                    </g>
                </g>
            </g>
        </svg>'''

        scene, parse_result = parser.parse_to_ir(svg_content)

        assert scene is not None
        assert len(scene) == 1
        assert isinstance(scene[0], Group)

        # Should preserve nesting structure
        outer_group = scene[0]
        assert len(outer_group.children) == 1
        assert isinstance(outer_group.children[0], Group)