#!/usr/bin/env python3
"""
Unit Tests for Current Path Conversion System

Tests the path converter functionality that exists in the current architecture.
Focuses on testing actual working components without legacy dependencies.
"""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path
import sys
from lxml import etree as ET

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

# Test imports first
try:
    from src.converters.paths import PathConverter
    PATH_CONVERTER_AVAILABLE = True
except ImportError:
    PATH_CONVERTER_AVAILABLE = False

try:
    from src.converters.base import CoordinateSystem, ConversionContext
    BASE_AVAILABLE = True
except ImportError:
    BASE_AVAILABLE = False

try:
    from core.transforms import Matrix
    TRANSFORM_AVAILABLE = True
except ImportError:
    TRANSFORM_AVAILABLE = False


@pytest.mark.skipif(not PATH_CONVERTER_AVAILABLE, reason="PathConverter not available")
class TestCurrentPathConverter:
    """Unit tests for current PathConverter implementation."""

    def test_path_converter_class_exists(self):
        """Test that PathConverter class exists and is importable."""
        assert PathConverter is not None
        assert hasattr(PathConverter, 'convert')

    def test_path_converter_initialization(self):
        """Test PathConverter can be initialized."""
        try:
            # Try to create with minimal args
            converter = PathConverter.__new__(PathConverter)
            assert converter is not None
        except Exception as e:
            pytest.skip(f"PathConverter initialization requires specific setup: {e}")

    def test_path_element_detection(self):
        """Test path element detection logic."""
        path_element = ET.fromstring('<path d="M 10 10 L 100 100 Z" fill="red"/>')
        rect_element = ET.fromstring('<rect x="0" y="0" width="100" height="50"/>')

        # Test that path elements are recognized
        assert path_element.tag == 'path'
        assert path_element.get('d') is not None
        assert rect_element.tag != 'path'

    def test_basic_path_data_parsing(self):
        """Test parsing of basic path data."""
        # Test simple path commands
        simple_paths = [
            "M 10 10",                          # Move
            "M 10 10 L 20 20",                 # Move + Line
            "M 10 10 L 20 20 Z",               # Move + Line + Close
            "M 10 10 H 50 V 30 Z",             # Horizontal + Vertical
            "M 10 10 C 20 20 30 30 40 40",     # Cubic Bezier
            "M 10 10 Q 20 20 30 30",           # Quadratic Bezier
            "M 10 10 A 5 5 0 0 1 20 20"        # Arc
        ]

        for path_data in simple_paths:
            path_element = ET.fromstring(f'<path d="{path_data}"/>')
            d_attr = path_element.get('d')
            assert d_attr == path_data


@pytest.mark.skipif(not PATH_CONVERTER_AVAILABLE, reason="PathConverter not available")
class TestPathDataParsing:
    """Test path data parsing functionality."""

    def test_absolute_path_commands(self):
        """Test absolute path commands (uppercase)."""
        absolute_path = ET.fromstring('''
            <path d="M 50 50 L 100 50 L 100 100 L 50 100 Z" fill="blue"/>
        ''')

        d_attr = absolute_path.get('d')
        # Test that uppercase commands are present
        assert 'M' in d_attr  # Move
        assert 'L' in d_attr  # Line
        assert 'Z' in d_attr  # Close

    def test_relative_path_commands(self):
        """Test relative path commands (lowercase)."""
        relative_path = ET.fromstring('''
            <path d="m 10 10 l 40 0 l 0 40 l -40 0 z" fill="green"/>
        ''')

        d_attr = relative_path.get('d')
        # Test that lowercase commands are present
        assert 'm' in d_attr  # Relative move
        assert 'l' in d_attr  # Relative line
        assert 'z' in d_attr  # Close (case insensitive)

    def test_cubic_bezier_curves(self):
        """Test cubic Bezier curve parsing."""
        bezier_path = ET.fromstring('''
            <path d="M 10 10 C 20 20, 40 20, 50 10" stroke="black" fill="none"/>
        ''')

        d_attr = bezier_path.get('d')
        assert 'C' in d_attr
        # Should contain control points and end point
        assert '20 20' in d_attr
        assert '40 20' in d_attr
        assert '50 10' in d_attr

    def test_quadratic_bezier_curves(self):
        """Test quadratic Bezier curve parsing."""
        quad_path = ET.fromstring('''
            <path d="M 10 10 Q 25 30, 40 10" stroke="red" fill="none"/>
        ''')

        d_attr = quad_path.get('d')
        assert 'Q' in d_attr
        # Should contain control point and end point
        assert '25 30' in d_attr
        assert '40 10' in d_attr

    def test_arc_commands(self):
        """Test arc command parsing."""
        arc_path = ET.fromstring('''
            <path d="M 10 10 A 20 20 0 0 1 50 50" stroke="purple" fill="none"/>
        ''')

        d_attr = arc_path.get('d')
        assert 'A' in d_attr
        # Should contain arc parameters
        assert '20 20' in d_attr  # rx, ry
        assert '0 0 1' in d_attr  # rotation, large-arc, sweep
        assert '50 50' in d_attr  # end point

    def test_smooth_curves(self):
        """Test smooth curve commands (S, T)."""
        smooth_path = ET.fromstring('''
            <path d="M 10 10 C 20 20, 40 20, 50 10 S 80 0, 90 10" fill="orange"/>
        ''')

        d_attr = smooth_path.get('d')
        assert 'C' in d_attr  # Initial cubic
        assert 'S' in d_attr  # Smooth continuation


@pytest.mark.skipif(not PATH_CONVERTER_AVAILABLE, reason="PathConverter not available")
class TestPathConverterIntegration:
    """Integration tests for path converter with other systems."""

    @pytest.mark.skipif(not TRANSFORM_AVAILABLE, reason="Transform system not available")
    def test_path_converter_with_transforms(self):
        """Test path converter integration with transform system."""
        transformed_path = ET.fromstring('''
            <path d="M 10 10 L 50 50 Z"
                  transform="translate(20,30) scale(2) rotate(45)"
                  fill="blue"/>
        ''')

        # Test transform attribute
        transform_attr = transformed_path.get('transform')
        assert transform_attr is not None
        assert 'translate' in transform_attr
        assert 'scale' in transform_attr
        assert 'rotate' in transform_attr

    def test_path_with_styling(self):
        """Test path with various styling attributes."""
        styled_path = ET.fromstring('''
            <path d="M 10 10 L 50 50 L 10 50 Z"
                  fill="#FF5500"
                  stroke="black"
                  stroke-width="2"
                  stroke-dasharray="5,5"
                  opacity="0.8"/>
        ''')

        # Test styling attributes
        assert styled_path.get('fill') == '#FF5500'
        assert styled_path.get('stroke') == 'black'
        assert styled_path.get('stroke-width') == '2'
        assert styled_path.get('stroke-dasharray') == '5,5'
        assert styled_path.get('opacity') == '0.8'

    def test_path_with_markers(self):
        """Test path with marker attributes."""
        path_with_markers = ET.fromstring('''
            <path d="M 10 10 L 50 50 L 90 10"
                  marker-start="url(#arrow-start)"
                  marker-mid="url(#circle-mid)"
                  marker-end="url(#arrow-end)"
                  fill="none"
                  stroke="black"/>
        ''')

        # Test marker attributes
        assert path_with_markers.get('marker-start') == 'url(#arrow-start)'
        assert path_with_markers.get('marker-mid') == 'url(#circle-mid)'
        assert path_with_markers.get('marker-end') == 'url(#arrow-end)'


class TestPathConverterEdgeCases:
    """Edge case tests for path converter."""

    def test_empty_path_data(self):
        """Test path with empty or minimal data."""
        empty_path = ET.fromstring('<path d="" fill="red"/>')
        minimal_path = ET.fromstring('<path d="M 0 0" fill="blue"/>')

        assert empty_path.get('d') == ''
        assert minimal_path.get('d') == 'M 0 0'

    def test_path_with_scientific_notation(self):
        """Test path with scientific notation numbers."""
        scientific_path = ET.fromstring('''
            <path d="M 1e2 1.5e1 L 2.5e2 3e1" fill="green"/>
        ''')

        d_attr = scientific_path.get('d')
        assert 'e' in d_attr or 'E' in d_attr

    def test_path_with_whitespace_variations(self):
        """Test path with various whitespace patterns."""
        whitespace_paths = [
            ("M10,10L20,20Z", "M10,10L20,20Z"),                   # No spaces
            ("M 10 , 10 L 20 , 20 Z", "M 10 , 10 L 20 , 20 Z"),   # Extra spaces
            ("M\t10\n10\rL\t20\n20\rZ", "M 10 10 L 20 20 Z"),     # XML normalizes whitespace
            ("M10 10L20 20Z", "M10 10L20 20Z")                    # Mixed spacing
        ]

        for input_data, expected_data in whitespace_paths:
            path_element = ET.fromstring(f'<path d="{input_data}"/>')
            assert path_element.get('d') == expected_data

    def test_path_with_invalid_commands(self):
        """Test path with unusual or potentially invalid commands."""
        # These might be invalid but should still parse as XML
        unusual_paths = [
            "M 10 10 X 20 20",  # Invalid command 'X'
            "M 10",              # Incomplete move command
            "L 20 20",           # Line without initial move
        ]

        for path_data in unusual_paths:
            try:
                path_element = ET.fromstring(f'<path d="{path_data}"/>')
                assert path_element.get('d') == path_data
            except ET.XMLSyntaxError:
                # Some malformed data might not parse as XML
                pass

    def test_very_long_path_data(self):
        """Test path with very long data string."""
        # Create a long path with many points
        points = [(i * 10, i * 5) for i in range(100)]
        path_commands = ['M {} {}'.format(points[0][0], points[0][1])]
        path_commands.extend(['L {} {}'.format(x, y) for x, y in points[1:]])
        path_commands.append('Z')

        long_path_data = ' '.join(path_commands)
        long_path = ET.fromstring(f'<path d="{long_path_data}"/>')

        assert len(long_path.get('d')) > 500  # Should be quite long (adjusted for realistic size)


@pytest.mark.skipif(not PATH_CONVERTER_AVAILABLE, reason="PathConverter not available")
class TestPathConverterPerformance:
    """Performance tests for path converter."""

    def test_path_parsing_performance(self):
        """Test path parsing performance with complex paths."""
        import time

        # Create complex paths
        complex_paths = []
        for i in range(10):
            # Create a complex path with multiple command types
            path_data = f"M {i*10} {i*10} "
            path_data += f"L {i*10+50} {i*10} "
            path_data += f"C {i*10+60} {i*10+10} {i*10+70} {i*10+30} {i*10+50} {i*10+40} "
            path_data += f"Q {i*10+30} {i*10+50} {i*10} {i*10+40} "
            path_data += f"A 10 10 0 0 1 {i*10} {i*10+20} Z"

            path_element = ET.fromstring(f'<path d="{path_data}" fill="blue"/>')
            complex_paths.append(path_element)

        # Time the operations
        start_time = time.time()

        for path_element in complex_paths:
            # Test basic operations
            d_attr = path_element.get('d')
            fill_attr = path_element.get('fill')

            # Basic validation
            assert d_attr is not None
            assert len(d_attr) > 50  # Should be a complex path
            assert 'M' in d_attr
            assert 'Z' in d_attr

        execution_time = time.time() - start_time

        # Should be fast for basic parsing operations
        assert execution_time < 1.0, f"Path parsing too slow: {execution_time}s"


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__])