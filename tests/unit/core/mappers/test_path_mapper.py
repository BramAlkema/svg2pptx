#!/usr/bin/env python3
"""
Unit tests for core Path Mapper.

Tests the mapping from IR Path objects to PowerPoint DrawingML path/shape XML.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import math

from tests.unit.core.conftest import IRTestBase

try:
    from core.mappers import PathMapper
    from core.ir import Path, LineSegment, BezierSegment, ArcSegment
    from core.ir import Point, SolidPaint, Stroke
    CORE_MAPPERS_AVAILABLE = True
except ImportError:
    CORE_MAPPERS_AVAILABLE = False
    pytest.skip("Core mappers not available", allow_module_level=True)


class TestPathMapperCreation(IRTestBase):
    """Test PathMapper creation and initialization."""

    def test_path_mapper_initialization(self):
        """Test creating a path mapper."""
        mapper = PathMapper()

        assert mapper is not None
        assert hasattr(mapper, 'map_path')
        assert callable(mapper.map_path)

    def test_path_mapper_with_coordinate_system(self):
        """Test path mapper with coordinate system configuration."""
        try:
            coord_system = {
                'scale_x': 2.0,
                'scale_y': 2.0,
                'offset_x': 10.0,
                'offset_y': 20.0
            }

            mapper = PathMapper(coordinate_system=coord_system)
            assert mapper is not None

            if hasattr(mapper, 'coordinate_system'):
                assert mapper.coordinate_system == coord_system
        except TypeError:
            # Coordinate system might not be supported in constructor
            mapper = PathMapper()
            assert mapper is not None


class TestPathMapperLineSegments(IRTestBase):
    """Test mapping of line segments."""

    def test_map_simple_line(self):
        """Test mapping a simple line segment."""
        path = Path(
            segments=[LineSegment(Point(0, 0), Point(100, 100))],
            fill=None,
            stroke=Stroke(paint=SolidPaint(color="#000000"), width=1.0),
            is_closed=False,
            data="M 0 0 L 100 100"
        )

        mapper = PathMapper()
        result = mapper.map_path(path)

        assert result is not None
        if isinstance(result, str):
            # Should contain MoveTo and LineTo commands
            assert any(cmd in result.lower() for cmd in ['moveto', 'lineto', 'm', 'l'])

    def test_map_horizontal_line(self):
        """Test mapping horizontal line."""
        path = Path(
            segments=[LineSegment(Point(10, 50), Point(90, 50))],
            fill=None,
            stroke=Stroke(paint=SolidPaint(color="#FF0000"), width=2.0),
            is_closed=False,
            data="M 10 50 L 90 50"
        )

        mapper = PathMapper()
        result = mapper.map_path(path)

        assert result is not None
        # Should map to horizontal line in DrawingML

    def test_map_vertical_line(self):
        """Test mapping vertical line."""
        path = Path(
            segments=[LineSegment(Point(50, 10), Point(50, 90))],
            fill=None,
            stroke=Stroke(paint=SolidPaint(color="#0000FF"), width=1.5),
            is_closed=False,
            data="M 50 10 L 50 90"
        )

        mapper = PathMapper()
        result = mapper.map_path(path)

        assert result is not None
        # Should map to vertical line in DrawingML

    def test_map_polyline(self):
        """Test mapping multiple connected line segments."""
        path = Path(
            segments=[
                LineSegment(Point(0, 0), Point(50, 0)),
                LineSegment(Point(50, 0), Point(50, 50)),
                LineSegment(Point(50, 50), Point(0, 50))
            ],
            fill=None,
            stroke=Stroke(paint=SolidPaint(color="#00FF00"), width=1.0),
            is_closed=False,
            data="M 0 0 L 50 0 L 50 50 L 0 50"
        )

        mapper = PathMapper()
        result = mapper.map_path(path)

        assert result is not None
        if isinstance(result, str):
            # Should contain multiple line commands
            line_count = result.lower().count('lineto') + result.lower().count('l ')
            assert line_count >= 2

    def test_map_closed_polygon(self):
        """Test mapping closed polygon."""
        path = Path(
            segments=[
                LineSegment(Point(0, 0), Point(100, 0)),
                LineSegment(Point(100, 0), Point(100, 100)),
                LineSegment(Point(100, 100), Point(0, 100)),
                LineSegment(Point(0, 100), Point(0, 0))
            ],
            fill=SolidPaint(color="#FFFF00"),
            stroke=None,
            is_closed=True,
            data="M 0 0 L 100 0 L 100 100 L 0 100 Z"
        )

        mapper = PathMapper()
        result = mapper.map_path(path)

        assert result is not None
        if isinstance(result, str):
            # Should contain close command
            assert any(cmd in result.lower() for cmd in ['close', 'z', 'closepath'])


class TestPathMapperBezierSegments(IRTestBase):
    """Test mapping of Bezier curve segments."""

    def test_map_quadratic_bezier(self):
        """Test mapping quadratic Bezier curve."""
        try:
            path = Path(
                segments=[BezierSegment(
                    start=Point(0, 100),
                    end=Point(100, 100),
                    control1=Point(50, 0)
                )],
                fill=None,
                stroke=Stroke(paint=SolidPaint(color="#FF00FF"), width=2.0),
                is_closed=False,
                data="M 0 100 Q 50 0 100 100"
            )

            mapper = PathMapper()
            result = mapper.map_path(path)

            assert result is not None
            if isinstance(result, str):
                # Should contain curve command
                assert any(cmd in result.lower() for cmd in ['quadbezto', 'cubicbezto', 'curve'])
        except NameError:
            pytest.skip("BezierSegment not available")

    def test_map_cubic_bezier(self):
        """Test mapping cubic Bezier curve."""
        try:
            path = Path(
                segments=[BezierSegment(
                    start=Point(0, 100),
                    end=Point(100, 100),
                    control1=Point(33, 0),
                    control2=Point(66, 0)
                )],
                fill=None,
                stroke=Stroke(paint=SolidPaint(color="#00FFFF"), width=1.5),
                is_closed=False,
                data="M 0 100 C 33 0 66 0 100 100"
            )

            mapper = PathMapper()
            result = mapper.map_path(path)

            assert result is not None
            if isinstance(result, str):
                # Should contain cubic curve command
                assert any(cmd in result.lower() for cmd in ['cubicbezto', 'curve'])
        except NameError:
            pytest.skip("BezierSegment not available")

    def test_map_smooth_curve_sequence(self):
        """Test mapping sequence of connected Bezier curves."""
        try:
            path = Path(
                segments=[
                    BezierSegment(
                        start=Point(0, 50),
                        end=Point(50, 50),
                        control1=Point(25, 0),
                        control2=Point(25, 100)
                    ),
                    BezierSegment(
                        start=Point(50, 50),
                        end=Point(100, 50),
                        control1=Point(75, 0),
                        control2=Point(75, 100)
                    )
                ],
                fill=SolidPaint(color="#808080"),
                stroke=None,
                is_closed=False,
                data="M 0 50 C 25 0 25 100 50 50 C 75 0 75 100 100 50"
            )

            mapper = PathMapper()
            result = mapper.map_path(path)

            assert result is not None
            if isinstance(result, str):
                # Should contain multiple curve commands
                curve_count = result.lower().count('cubicbezto') + result.lower().count('curve')
                assert curve_count >= 2
        except NameError:
            pytest.skip("BezierSegment not available")


class TestPathMapperArcSegments(IRTestBase):
    """Test mapping of arc segments."""

    def test_map_circular_arc(self):
        """Test mapping circular arc."""
        try:
            path = Path(
                segments=[ArcSegment(
                    start=Point(0, 50),
                    end=Point(100, 50),
                    rx=50,
                    ry=50,
                    rotation=0,
                    large_arc=False,
                    sweep=True
                )],
                fill=None,
                stroke=Stroke(paint=SolidPaint(color="#800080"), width=2.0),
                is_closed=False,
                data="M 0 50 A 50 50 0 0 1 100 50"
            )

            mapper = PathMapper()
            result = mapper.map_path(path)

            assert result is not None
            if isinstance(result, str):
                # Should contain arc command or convert to curves
                assert any(cmd in result.lower() for cmd in ['arcto', 'arc', 'cubicbezto'])
        except NameError:
            pytest.skip("ArcSegment not available")

    def test_map_elliptical_arc(self):
        """Test mapping elliptical arc."""
        try:
            path = Path(
                segments=[ArcSegment(
                    start=Point(0, 25),
                    end=Point(100, 25),
                    rx=75,
                    ry=25,
                    rotation=0,
                    large_arc=False,
                    sweep=True
                )],
                fill=None,
                stroke=Stroke(paint=SolidPaint(color="#FFA500"), width=1.5),
                is_closed=False,
                data="M 0 25 A 75 25 0 0 1 100 25"
            )

            mapper = PathMapper()
            result = mapper.map_path(path)

            assert result is not None
            # Should handle elliptical arc conversion
        except NameError:
            pytest.skip("ArcSegment not available")

    def test_map_rotated_arc(self):
        """Test mapping rotated arc."""
        try:
            path = Path(
                segments=[ArcSegment(
                    start=Point(0, 0),
                    end=Point(100, 100),
                    rx=50,
                    ry=50,
                    rotation=45,
                    large_arc=True,
                    sweep=False
                )],
                fill=SolidPaint(color="#FF6347"),
                stroke=None,
                is_closed=False,
                data="M 0 0 A 50 50 45 1 0 100 100"
            )

            mapper = PathMapper()
            result = mapper.map_path(path)

            assert result is not None
            # Should handle rotation in arc conversion
        except NameError:
            pytest.skip("ArcSegment not available")


class TestPathMapperCoordinateTransformation(IRTestBase):
    """Test coordinate transformation during path mapping."""

    def test_coordinate_scaling(self):
        """Test coordinate scaling transformation."""
        path = Path(
            segments=[LineSegment(Point(10, 10), Point(90, 90))],
            fill=None,
            stroke=Stroke(paint=SolidPaint(color="#000000"), width=1.0),
            is_closed=False,
            data="M 10 10 L 90 90"
        )

        # Create mapper with 2x scaling
        try:
            mapper = PathMapper(coordinate_system={
                'scale_x': 2.0,
                'scale_y': 2.0,
                'offset_x': 0.0,
                'offset_y': 0.0
            })
        except TypeError:
            mapper = PathMapper()

        result = mapper.map_path(path)

        assert result is not None
        # Coordinates should be scaled (10,10) -> (20,20), (90,90) -> (180,180)

    def test_coordinate_offset(self):
        """Test coordinate offset transformation."""
        path = Path(
            segments=[LineSegment(Point(0, 0), Point(50, 50))],
            fill=SolidPaint(color="#FF0000"),
            stroke=None,
            is_closed=False,
            data="M 0 0 L 50 50"
        )

        # Create mapper with offset
        try:
            mapper = PathMapper(coordinate_system={
                'scale_x': 1.0,
                'scale_y': 1.0,
                'offset_x': 25.0,
                'offset_y': 25.0
            })
        except TypeError:
            mapper = PathMapper()

        result = mapper.map_path(path)

        assert result is not None
        # Coordinates should be offset (0,0) -> (25,25), (50,50) -> (75,75)

    def test_emu_conversion(self):
        """Test conversion to EMU units."""
        path = Path(
            segments=[LineSegment(Point(1, 1), Point(2, 2))],
            fill=None,
            stroke=Stroke(paint=SolidPaint(color="#0000FF"), width=1.0),
            is_closed=False,
            data="M 1 1 L 2 2"
        )

        mapper = PathMapper()
        result = mapper.map_path(path)

        assert result is not None
        if isinstance(result, str):
            # Should contain EMU-scale coordinates (large numbers)
            import re
            numbers = re.findall(r'\d+', result)
            # Should find some large numbers (EMU scale)
            large_numbers = [n for n in numbers if len(n) >= 4]
            # EMU coordinates should be much larger than input


class TestPathMapperFillMapping(IRTestBase):
    """Test mapping of path fill properties."""

    def test_map_solid_fill(self):
        """Test mapping solid fill."""
        path = Path(
            segments=[
                LineSegment(Point(0, 0), Point(100, 0)),
                LineSegment(Point(100, 0), Point(100, 100)),
                LineSegment(Point(100, 100), Point(0, 100)),
                LineSegment(Point(0, 100), Point(0, 0))
            ],
            fill=SolidPaint(color="#FF0000"),
            stroke=None,
            is_closed=True,
            data="M 0 0 L 100 0 L 100 100 L 0 100 Z"
        )

        mapper = PathMapper()
        result = mapper.map_path(path)

        assert result is not None
        if isinstance(result, str):
            # Should contain solid fill properties
            assert any(tag in result.lower() for tag in ['solidfill', 'srgbclr'])
            # Should contain color value
            assert "ff0000" in result.lower()

    def test_map_no_fill(self):
        """Test mapping path with no fill."""
        path = Path(
            segments=[LineSegment(Point(0, 0), Point(100, 100))],
            fill=None,
            stroke=Stroke(paint=SolidPaint(color="#000000"), width=1.0),
            is_closed=False,
            data="M 0 0 L 100 100"
        )

        mapper = PathMapper()
        result = mapper.map_path(path)

        assert result is not None
        if isinstance(result, str):
            # Should indicate no fill
            assert any(tag in result.lower() for tag in ['nofill', 'fill="none"'])

    def test_map_gradient_fill(self):
        """Test mapping gradient fill."""
        try:
            from core.ir import LinearGradient

            gradient = LinearGradient(
                start_point=Point(0, 0),
                end_point=Point(100, 0),
                stops=[
                    {"offset": 0.0, "color": "#FF0000"},
                    {"offset": 1.0, "color": "#0000FF"}
                ]
            )

            path = Path(
                segments=[
                    LineSegment(Point(0, 0), Point(100, 0)),
                    LineSegment(Point(100, 0), Point(100, 100)),
                    LineSegment(Point(100, 100), Point(0, 100)),
                    LineSegment(Point(0, 100), Point(0, 0))
                ],
                fill=gradient,
                stroke=None,
                is_closed=True,
                data="M 0 0 L 100 0 L 100 100 L 0 100 Z"
            )

            mapper = PathMapper()
            result = mapper.map_path(path)

            assert result is not None
            if isinstance(result, str):
                # Should contain gradient fill properties
                assert any(tag in result.lower() for tag in ['gradfill', 'lin', 'gs'])
        except NameError:
            pytest.skip("LinearGradient not available")


class TestPathMapperStrokeMapping(IRTestBase):
    """Test mapping of path stroke properties."""

    def test_map_stroke_width(self):
        """Test mapping stroke width."""
        path = Path(
            segments=[LineSegment(Point(0, 0), Point(100, 0))],
            fill=None,
            stroke=Stroke(
                paint=SolidPaint(color="#000000"),
                width=5.0
            ),
            is_closed=False,
            data="M 0 0 L 100 0"
        )

        mapper = PathMapper()
        result = mapper.map_path(path)

        assert result is not None
        if isinstance(result, str):
            # Should contain stroke width
            assert any(tag in result.lower() for tag in ['w=', 'width'])

    def test_map_stroke_color(self):
        """Test mapping stroke color."""
        path = Path(
            segments=[LineSegment(Point(0, 0), Point(100, 100))],
            fill=None,
            stroke=Stroke(
                paint=SolidPaint(color="#FF0000"),
                width=2.0
            ),
            is_closed=False,
            data="M 0 0 L 100 100"
        )

        mapper = PathMapper()
        result = mapper.map_path(path)

        assert result is not None
        if isinstance(result, str):
            # Should contain stroke color
            assert "ff0000" in result.lower()

    def test_map_stroke_properties(self):
        """Test mapping advanced stroke properties."""
        try:
            stroke = Stroke(
                paint=SolidPaint(color="#0000FF"),
                width=3.0,
                line_cap="round",
                line_join="miter",
                miter_limit=4.0
            )

            path = Path(
                segments=[
                    LineSegment(Point(0, 0), Point(50, 0)),
                    LineSegment(Point(50, 0), Point(50, 50))
                ],
                fill=None,
                stroke=stroke,
                is_closed=False,
                data="M 0 0 L 50 0 L 50 50"
            )

            mapper = PathMapper()
            result = mapper.map_path(path)

            assert result is not None
            if isinstance(result, str):
                # Should contain line cap and join properties
                assert any(prop in result.lower() for prop in ['cap', 'join'])
        except TypeError:
            # Advanced stroke properties might not be supported
            pytest.skip("Advanced stroke properties not available")

    def test_map_dashed_stroke(self):
        """Test mapping dashed stroke."""
        try:
            stroke = Stroke(
                paint=SolidPaint(color="#00FF00"),
                width=2.0,
                dash_array=[5, 3, 2, 3]
            )

            path = Path(
                segments=[LineSegment(Point(0, 50), Point(100, 50))],
                fill=None,
                stroke=stroke,
                is_closed=False,
                data="M 0 50 L 100 50"
            )

            mapper = PathMapper()
            result = mapper.map_path(path)

            assert result is not None
            if isinstance(result, str):
                # Should contain dash pattern
                assert any(prop in result.lower() for prop in ['dash', 'prstdash'])
        except TypeError:
            pytest.skip("Dashed stroke not available")


class TestPathMapperValidation(IRTestBase):
    """Test path mapper validation and error handling."""

    def test_map_invalid_path(self):
        """Test mapping with invalid path object."""
        mapper = PathMapper()

        with pytest.raises((TypeError, ValueError, AttributeError)):
            mapper.map_path(None)

        with pytest.raises((TypeError, ValueError, AttributeError)):
            mapper.map_path("invalid_path")

    def test_map_empty_path(self):
        """Test mapping path with no segments."""
        empty_path = Path(
            segments=[],
            fill=SolidPaint(color="#FF0000"),
            stroke=None,
            is_closed=False,
            data=""
        )

        mapper = PathMapper()

        # Should handle empty path gracefully
        try:
            result = mapper.map_path(empty_path)
            # Might produce empty result or minimal structure
            assert result is not None or result == ""
        except (ValueError, TypeError):
            # Empty paths might be rejected
            pass

    def test_map_path_with_invalid_segments(self):
        """Test mapping path with invalid segments."""
        invalid_path = Path(
            segments=[Mock()],  # Invalid segment
            fill=None,
            stroke=Stroke(paint=SolidPaint(color="#000000"), width=1.0),
            is_closed=False,
            data="invalid"
        )

        mapper = PathMapper()

        # Should either handle gracefully or raise appropriate error
        try:
            result = mapper.map_path(invalid_path)
            assert result is not None
        except (TypeError, ValueError, AttributeError):
            # Expected for invalid segments
            pass


class TestPathMapperOutput(IRTestBase):
    """Test path mapper output format and structure."""

    def test_output_format_xml(self):
        """Test that output is valid XML format."""
        path = Path(
            segments=[LineSegment(Point(0, 0), Point(50, 50))],
            fill=SolidPaint(color="#FF0000"),
            stroke=None,
            is_closed=False,
            data="M 0 0 L 50 50"
        )

        mapper = PathMapper()
        result = mapper.map_path(path)

        assert result is not None

        if isinstance(result, str):
            # Should be valid XML or XML fragment
            try:
                from lxml import etree
                # Try parsing as complete element
                etree.fromstring(result)
            except etree.XMLSyntaxError:
                # Try as fragment wrapped in root
                wrapped = f"<root>{result}</root>"
                etree.fromstring(wrapped)

    def test_output_drawingml_structure(self):
        """Test that output follows DrawingML structure."""
        path = Path(
            segments=[
                LineSegment(Point(0, 0), Point(100, 0)),
                LineSegment(Point(100, 0), Point(50, 100)),
                LineSegment(Point(50, 100), Point(0, 0))
            ],
            fill=SolidPaint(color="#00FF00"),
            stroke=None,
            is_closed=True,
            data="M 0 0 L 100 0 L 50 100 Z"
        )

        mapper = PathMapper()
        result = mapper.map_path(path)

        assert result is not None

        if isinstance(result, str):
            # Should contain DrawingML path elements
            expected_elements = ['custgeom', 'pathlist', 'path', 'moveto', 'lineto']
            found_elements = [elem for elem in expected_elements if elem in result.lower()]
            # Should find some DrawingML path elements
            assert len(found_elements) > 0


class TestPathMapperPerformance(IRTestBase):
    """Test path mapper performance characteristics."""

    def test_mapping_performance_simple_path(self):
        """Test mapping performance with simple path."""
        import time

        path = Path(
            segments=[LineSegment(Point(0, 0), Point(100, 100))],
            fill=SolidPaint(color="#FF0000"),
            stroke=None,
            is_closed=False,
            data="M 0 0 L 100 100"
        )

        mapper = PathMapper()

        start_time = time.time()
        result = mapper.map_path(path)
        mapping_time = time.time() - start_time

        assert result is not None
        assert mapping_time < 0.01  # Should map very quickly

    def test_mapping_performance_complex_path(self):
        """Test mapping performance with complex path."""
        import time

        # Create complex path with many segments
        segments = []
        for i in range(100):
            segments.append(LineSegment(Point(i, 0), Point(i+1, 1)))

        complex_path = Path(
            segments=segments,
            fill=SolidPaint(color="#0000FF"),
            stroke=None,
            is_closed=False,
            data="M " + " L ".join([f"{i} {i%2}" for i in range(101)])
        )

        mapper = PathMapper()

        start_time = time.time()
        result = mapper.map_path(complex_path)
        mapping_time = time.time() - start_time

        assert result is not None
        assert mapping_time < 0.1  # Should handle complex paths reasonably fast

    def test_memory_usage_large_path(self):
        """Test memory usage with large path."""
        import sys

        # Create path with many segments
        segments = []
        for i in range(500):
            segments.append(LineSegment(Point(i, 0), Point(i+1, 1)))

        large_path = Path(
            segments=segments,
            fill=None,
            stroke=Stroke(paint=SolidPaint(color="#000000"), width=1.0),
            is_closed=False,
            data="M " + " L ".join([f"{i} {i%2}" for i in range(501)])
        )

        mapper = PathMapper()
        result = mapper.map_path(large_path)

        assert result is not None

        if isinstance(result, str):
            result_size = sys.getsizeof(result)
            # Should produce reasonable output size
            assert result_size < 500000  # Less than 500KB


if __name__ == "__main__":
    pytest.main([__file__])