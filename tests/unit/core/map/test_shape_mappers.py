#!/usr/bin/env python3
"""
Unit tests for native shape mappers (CircleMapper, EllipseMapper, RectangleMapper)

Tests coverage:
- Preset output for simple shapes (native PowerPoint shapes)
- Custom geometry fallback for complex shapes
- XML structure validation
- Fill and stroke handling
- Transform complexity detection
- Filter and clipping effects
"""

import pytest
import numpy as np
from unittest.mock import Mock

from core.ir.shapes import Circle, Ellipse, Rectangle
from core.map.base import OutputFormat
from core.ir.geometry import Point, Rect
from core.ir.paint import SolidPaint, LinearGradientPaint, GradientStop, Stroke, StrokeCap, StrokeJoin
from core.map.circle_mapper import CircleMapper
from core.map.ellipse_mapper import EllipseMapper
from core.map.rect_mapper import RectangleMapper
from core.policy.shape_policy import ShapeDecision
from core.policy.targets import DecisionReason


class TestCircleMapperPreset:
    """Test CircleMapper with native preset shapes"""

    def test_simple_circle_uses_preset(self):
        """Simple circle should use native PowerPoint ellipse preset"""
        circle = Circle(center=Point(100, 100), radius=50)
        mapper = CircleMapper()

        result = mapper.map(circle)

        assert result.output_format == OutputFormat.NATIVE_DML
        assert result.policy_decision.use_preset is True
        assert result.policy_decision.preset_name == 'ellipse'
        assert '<p:sp>' in result.xml_content
        assert '<a:prstGeom prst="ellipse">' in result.xml_content

    def test_circle_preset_xml_structure(self):
        """Verify complete XML structure for preset circle"""
        circle = Circle(
            center=Point(100, 100),
            radius=50,
            fill=SolidPaint(rgb="FF0000"),
            stroke=Stroke(width=2.0, paint=SolidPaint(rgb="000000")),
        )
        mapper = CircleMapper()

        result = mapper.map(circle)
        xml = result.xml_content

        # Verify all required elements
        assert '<p:nvSpPr>' in xml
        assert '<p:cNvPr id=' in xml
        assert 'name="Circle"' in xml
        assert '<p:cNvSpPr/>' in xml
        assert '<p:nvPr/>' in xml
        assert '<p:spPr>' in xml
        assert '<a:xfrm>' in xml
        assert '<a:off x=' in xml
        assert '<a:ext cx=' in xml
        assert '<a:prstGeom prst="ellipse">' in xml
        assert '<a:avLst/>' in xml
        assert '<a:solidFill><a:srgbClr val="FF0000"/></a:solidFill>' in xml
        assert '<a:ln w=' in xml
        assert '<p:style>' in xml
        assert '<p:txBody>' in xml

    def test_circle_emu_conversion(self):
        """Test coordinate conversion to EMU units"""
        circle = Circle(center=Point(100, 100), radius=50)
        mapper = CircleMapper()

        result = mapper.map(circle)
        xml = result.xml_content

        # Center at (100, 100), radius 50
        # Top-left should be (50, 50), diameter 100
        # In EMU: 50 * 12700 = 635000, 100 * 12700 = 1270000
        expected_x = 635000
        expected_y = 635000
        expected_diameter = 1270000

        assert f'x="{expected_x}"' in xml
        assert f'y="{expected_y}"' in xml
        assert f'cx="{expected_diameter}"' in xml
        assert f'cy="{expected_diameter}"' in xml

    def test_circle_with_gradient_fill(self):
        """Test circle with linear gradient fill"""
        gradient = LinearGradientPaint(
            stops=[
                GradientStop(offset=0.0, rgb="FF0000"),
                GradientStop(offset=1.0, rgb="0000FF"),
            ],
            start=(100, 50),  # Top of circle
            end=(100, 150),   # Bottom of circle
        )
        circle = Circle(center=Point(100, 100), radius=50, fill=gradient)
        mapper = CircleMapper()

        result = mapper.map(circle)
        xml = result.xml_content

        assert '<a:gradFill' in xml
        assert '<a:gsLst>' in xml
        assert 'pos="0"' in xml
        assert 'val="FF0000"' in xml
        assert 'pos="100000"' in xml
        assert 'val="0000FF"' in xml

    def test_circle_with_stroke_properties(self):
        """Test circle with detailed stroke properties"""
        stroke = Stroke(
            width=2.5,
            paint=SolidPaint(rgb="00FF00"),
            cap=StrokeCap.ROUND,
            join=StrokeJoin.MITER,
        )
        circle = Circle(center=Point(100, 100), radius=50, stroke=stroke)
        mapper = CircleMapper()

        result = mapper.map(circle)
        xml = result.xml_content

        # Width: 2.5 * 12700 = 31750 EMU
        assert 'w="31750"' in xml
        assert 'val="00FF00"' in xml
        assert '<a:cap val="rnd"/>' in xml  # ROUND -> rnd
        assert '<a:miter/>' in xml


class TestCircleMapperCustomGeometry:
    """Test CircleMapper fallback to custom geometry"""

    @pytest.mark.skip(reason="Phase 2: Shapes no longer have transform fields - transforms are baked during parsing")
    def test_circle_with_rotation_uses_custom_geometry(self):
        """Circle with rotation should fall back to custom geometry"""
        angle = np.pi / 4  # 45 degrees
        rotation = np.array([
            [np.cos(angle), -np.sin(angle), 0],
            [np.sin(angle), np.cos(angle), 0],
            [0, 0, 1],
        ])
        circle = Circle(center=Point(100, 100), radius=50, transform=rotation)
        mapper = CircleMapper()

        result = mapper.map(circle)

        assert result.output_format == OutputFormat.NATIVE_DML  # Custom geometry
        assert result.policy_decision.use_preset is False
        assert result.policy_decision.has_complex_transform is True
        assert 'path' in result.metadata
        assert result.metadata['path'] is not None

    def test_circle_with_filters_uses_custom_geometry(self):
        """Circle with filters should fall back to custom geometry"""
        circle = Circle(center=Point(100, 100), radius=50)
        context = Mock()
        context.filters = ['blur', 'drop-shadow']
        mapper = CircleMapper()

        result = mapper.map(circle, context)

        assert result.output_format == OutputFormat.NATIVE_DML  # Custom geometry
        assert result.policy_decision.use_preset is False
        assert result.policy_decision.has_filters is True

    def test_circle_with_clipping_uses_custom_geometry(self):
        """Circle with clipping path should fall back to custom geometry"""
        circle = Circle(center=Point(100, 100), radius=50)
        context = Mock()
        context.clip = Mock()
        context.filters = None
        mapper = CircleMapper()

        result = mapper.map(circle, context)

        assert result.output_format == OutputFormat.NATIVE_DML  # Custom geometry
        assert result.policy_decision.use_preset is False
        assert result.policy_decision.has_clipping is True

    @pytest.mark.skip(reason="Phase 2: Shapes no longer have transform fields - transforms are baked during parsing")
    def test_custom_geometry_path_structure(self):
        """Verify Path structure for custom geometry fallback"""
        angle = np.pi / 2
        rotation = np.array([
            [np.cos(angle), -np.sin(angle), 0],
            [np.sin(angle), np.cos(angle), 0],
            [0, 0, 1],
        ])
        circle = Circle(
            center=Point(100, 100),
            radius=50,
            fill=SolidPaint(rgb="FF0000"),
            stroke=Stroke(width=2.0, paint=SolidPaint(rgb="000000")),
            transform=rotation,
        )
        mapper = CircleMapper()

        result = mapper.map(circle)
        path = result.metadata['path']

        # Path should have 4 Bezier segments (one per quadrant)
        assert len(path.segments) == 4
        assert all(hasattr(seg, 'control1') for seg in path.segments)
        assert all(hasattr(seg, 'control2') for seg in path.segments)

        # Path should preserve fill and stroke
        assert path.fill.rgb == "FF0000"
        assert path.stroke.width == 2.0


class TestEllipseMapperPreset:
    """Test EllipseMapper with native preset shapes"""

    def test_simple_ellipse_uses_preset(self):
        """Simple ellipse should use native PowerPoint ellipse preset"""
        ellipse = Ellipse(center=Point(100, 100), radius_x=60, radius_y=40)
        mapper = EllipseMapper()

        result = mapper.map(ellipse)

        assert result.output_format == OutputFormat.NATIVE_DML
        assert result.policy_decision.use_preset is True
        assert result.policy_decision.preset_name == 'ellipse'
        assert '<a:prstGeom prst="ellipse">' in result.xml_content

    def test_ellipse_emu_conversion(self):
        """Test ellipse coordinate conversion to EMU"""
        ellipse = Ellipse(center=Point(100, 100), radius_x=60, radius_y=40)
        mapper = EllipseMapper()

        result = mapper.map(ellipse)
        xml = result.xml_content

        # Center at (100, 100), rx=60, ry=40
        # Top-left: (40, 60), width=120, height=80
        # In EMU: 40*12700=508000, 60*12700=762000, 120*12700=1524000, 80*12700=1016000
        assert 'x="508000"' in xml
        assert 'y="762000"' in xml
        assert 'cx="1524000"' in xml
        assert 'cy="1016000"' in xml

    def test_circle_detected_as_ellipse(self):
        """Circle (rx ≈ ry) should map to ellipse with equal dimensions"""
        # Create ellipse with equal radii (circle)
        ellipse = Ellipse(center=Point(100, 100), radius_x=50, radius_y=50)
        mapper = EllipseMapper()

        result = mapper.map(ellipse)
        xml = result.xml_content

        # Should have equal width and height
        # Diameter: 50 * 2 * 12700 = 1270000
        assert 'cx="1270000"' in xml
        assert 'cy="1270000"' in xml

    def test_ellipse_xml_structure(self):
        """Verify complete XML structure for preset ellipse"""
        ellipse = Ellipse(
            center=Point(100, 100),
            radius_x=60,
            radius_y=40,
            fill=SolidPaint(rgb="0000FF"),
        )
        mapper = EllipseMapper()

        result = mapper.map(ellipse)
        xml = result.xml_content

        assert '<p:sp>' in xml
        assert 'name="Ellipse"' in xml
        assert '<p:nvSpPr>' in xml
        assert '<p:spPr>' in xml
        assert '<a:xfrm>' in xml
        assert '<a:prstGeom prst="ellipse">' in xml
        assert 'val="0000FF"' in xml


class TestEllipseMapperCustomGeometry:
    """Test EllipseMapper fallback to custom geometry"""

    @pytest.mark.skip(reason="Phase 2: Shapes no longer have transform fields - transforms are baked during parsing")
    def test_ellipse_with_skew_uses_custom_geometry(self):
        """Ellipse with skew transform should fall back to custom geometry"""
        skew = np.array([
            [1.0, 0.5, 0],  # Non-zero off-diagonal = skew
            [0.0, 1.0, 0],
            [0, 0, 1],
        ])
        ellipse = Ellipse(center=Point(100, 100), radius_x=60, radius_y=40, transform=skew)
        mapper = EllipseMapper()

        result = mapper.map(ellipse)

        assert result.output_format == OutputFormat.NATIVE_DML  # Custom geometry
        assert result.policy_decision.use_preset is False
        assert result.policy_decision.has_complex_transform is True

    @pytest.mark.skip(reason="Phase 2: Shapes no longer have transform fields - transforms are baked during parsing")
    def test_custom_geometry_ellipse_path(self):
        """Verify Path structure for ellipse custom geometry"""
        rotation = np.array([
            [0, -1, 0],
            [1, 0, 0],
            [0, 0, 1],
        ])
        ellipse = Ellipse(center=Point(100, 100), radius_x=60, radius_y=40, transform=rotation)
        mapper = EllipseMapper()

        result = mapper.map(ellipse)
        path = result.metadata['path']

        # Should have 4 Bezier segments
        assert len(path.segments) == 4
        # Should preserve ellipse properties
        assert path.fill == ellipse.fill
        assert path.stroke == ellipse.stroke


class TestRectangleMapperPreset:
    """Test RectangleMapper with native preset shapes"""

    def test_simple_rectangle_uses_rect_preset(self):
        """Rectangle with sharp corners should use rect preset"""
        rect = Rectangle(bounds=Rect(x=10, y=20, width=100, height=80))
        mapper = RectangleMapper()

        result = mapper.map(rect)

        assert result.output_format == OutputFormat.NATIVE_DML
        assert result.policy_decision.use_preset is True
        assert result.policy_decision.preset_name == 'rect'
        assert '<a:prstGeom prst="rect">' in result.xml_content

    def test_rounded_rectangle_uses_roundrect_preset(self):
        """Rectangle with corner_radius should use roundRect preset"""
        rect = Rectangle(
            bounds=Rect(x=10, y=20, width=100, height=80),
            corner_radius=5.0,
        )
        mapper = RectangleMapper()

        result = mapper.map(rect)

        assert result.output_format == OutputFormat.NATIVE_DML
        assert result.policy_decision.use_preset is True
        assert result.policy_decision.preset_name == 'roundRect'
        assert '<a:prstGeom prst="roundRect">' in result.xml_content

    def test_rectangle_emu_conversion(self):
        """Test rectangle coordinate conversion to EMU"""
        rect = Rectangle(bounds=Rect(x=10, y=20, width=100, height=80))
        mapper = RectangleMapper()

        result = mapper.map(rect)
        xml = result.xml_content

        # Position (10, 20), size (100, 80)
        # In EMU: 10*12700=127000, 20*12700=254000, 100*12700=1270000, 80*12700=1016000
        assert 'x="127000"' in xml
        assert 'y="254000"' in xml
        assert 'cx="1270000"' in xml
        assert 'cy="1016000"' in xml

    def test_rectangle_xml_structure(self):
        """Verify complete XML structure for preset rectangle"""
        rect = Rectangle(
            bounds=Rect(x=10, y=20, width=100, height=80),
            fill=SolidPaint(rgb="00FF00"),
            stroke=Stroke(width=1.0, paint=SolidPaint(rgb="000000")),
        )
        mapper = RectangleMapper()

        result = mapper.map(rect)
        xml = result.xml_content

        assert '<p:sp>' in xml
        assert 'name="Rectangle"' in xml
        assert '<p:nvSpPr>' in xml
        assert '<p:spPr>' in xml
        assert '<a:xfrm>' in xml
        assert '<a:prstGeom prst="rect">' in xml
        assert 'val="00FF00"' in xml
        assert '<a:ln w=' in xml


class TestRectangleMapperCustomGeometry:
    """Test RectangleMapper fallback to custom geometry"""

    @pytest.mark.skip(reason="Phase 2: Shapes no longer have transform fields - transforms are baked during parsing")
    def test_rectangle_with_rotation_uses_custom_geometry(self):
        """Rectangle with rotation should fall back to custom geometry"""
        angle = np.pi / 6  # 30 degrees
        rotation = np.array([
            [np.cos(angle), -np.sin(angle), 0],
            [np.sin(angle), np.cos(angle), 0],
            [0, 0, 1],
        ])
        rect = Rectangle(bounds=Rect(x=10, y=20, width=100, height=80), transform=rotation)
        mapper = RectangleMapper()

        result = mapper.map(rect)

        assert result.output_format == OutputFormat.NATIVE_DML  # Custom geometry
        assert result.policy_decision.use_preset is False
        assert result.policy_decision.has_complex_transform is True

    @pytest.mark.skip(reason="Phase 2: Shapes no longer have transform fields - transforms are baked during parsing")
    def test_custom_geometry_rectangle_path(self):
        """Verify Path structure for rectangle custom geometry"""
        rotation = np.array([
            [0, -1, 0],
            [1, 0, 0],
            [0, 0, 1],
        ])
        rect = Rectangle(bounds=Rect(x=10, y=20, width=100, height=80), transform=rotation)
        mapper = RectangleMapper()

        result = mapper.map(rect)
        path = result.metadata['path']

        # Should have 4 LineSegments (one per edge)
        assert len(path.segments) == 4
        assert all(hasattr(seg, 'start') for seg in path.segments)
        assert all(hasattr(seg, 'end') for seg in path.segments)


class TestMapperQualityMetrics:
    """Test quality and performance metrics in mapper output"""

    def test_native_preset_quality_metrics(self):
        """Native presets should report perfect quality"""
        circle = Circle(center=Point(100, 100), radius=50)
        mapper = CircleMapper()

        result = mapper.map(circle)

        assert result.estimated_quality == 1.0
        assert result.estimated_performance == 1.0

    @pytest.mark.skip(reason="Phase 2: Shapes no longer have transform fields - transforms are baked during parsing")
    def test_custom_geometry_decision_metadata(self):
        """Custom geometry should include decision metadata"""
        rotation = np.array([
            [0, -1, 0],
            [1, 0, 0],
            [0, 0, 1],
        ])
        circle = Circle(center=Point(100, 100), radius=50, transform=rotation)
        mapper = CircleMapper()

        result = mapper.map(circle)

        assert hasattr(result, 'policy_decision')
        assert result.policy_decision.complexity_score > 0
        assert len(result.policy_decision.reasons) > 0


class TestMapperEdgeCases:
    """Test edge cases and error handling"""

    def test_circle_with_very_small_radius(self):
        """Circle with very small radius should still map"""
        circle = Circle(center=Point(100, 100), radius=0.1)
        mapper = CircleMapper()

        result = mapper.map(circle)

        # Should still produce valid XML (even if tiny)
        assert hasattr(result, 'xml_content')
        assert '<p:sp>' in result.xml_content

    def test_rectangle_with_very_small_dimensions(self):
        """Rectangle with very small width/height should still map"""
        rect = Rectangle(bounds=Rect(x=10, y=20, width=0.1, height=0.1))
        mapper = RectangleMapper()

        result = mapper.map(rect)

        assert hasattr(result, 'xml_content')
        assert '<p:sp>' in result.xml_content

    def test_ellipse_with_very_different_radii(self):
        """Ellipse with very different radii should still map correctly"""
        ellipse = Ellipse(center=Point(100, 100), radius_x=100, radius_y=1)
        mapper = EllipseMapper()

        result = mapper.map(ellipse)

        # Should produce valid ellipse (very stretched)
        assert hasattr(result, 'xml_content')
        assert result.output_format == OutputFormat.NATIVE_DML

    def test_mapper_without_context(self):
        """Mappers should work with context=None"""
        circle = Circle(center=Point(100, 100), radius=50)
        mapper = CircleMapper()

        result = mapper.map(circle, context=None)

        assert result.output_format == OutputFormat.NATIVE_DML

    def test_shape_without_fill_or_stroke(self):
        """Shapes without fill/stroke should produce valid XML"""
        circle = Circle(center=Point(100, 100), radius=50)
        mapper = CircleMapper()

        result = mapper.map(circle)
        xml = result.xml_content

        assert '<a:noFill/>' in xml
        assert '<a:ln>' in xml


class TestMapperStrokeHandling:
    """Test stroke property mapping to DrawingML"""

    def test_stroke_cap_mapping(self):
        """Test all stroke cap types map correctly"""
        test_cases = [
            (StrokeCap.BUTT, 'flat'),
            (StrokeCap.ROUND, 'rnd'),
            (StrokeCap.SQUARE, 'sq'),
        ]

        for cap, expected_val in test_cases:
            stroke = Stroke(width=1.0, paint=SolidPaint(rgb="000000"), cap=cap)
            circle = Circle(center=Point(100, 100), radius=50, stroke=stroke)
            mapper = CircleMapper()

            result = mapper.map(circle)
            assert f'<a:cap val="{expected_val}"/>' in result.xml_content

    def test_stroke_join_mapping(self):
        """Test all stroke join types map correctly"""
        test_cases = [
            (StrokeJoin.MITER, '<a:miter/>'),
            (StrokeJoin.ROUND, '<a:round/>'),
            (StrokeJoin.BEVEL, '<a:bevel/>'),
        ]

        for join, expected_xml in test_cases:
            stroke = Stroke(width=1.0, paint=SolidPaint(rgb="000000"), join=join)
            circle = Circle(center=Point(100, 100), radius=50, stroke=stroke)
            mapper = CircleMapper()

            result = mapper.map(circle)
            assert expected_xml in result.xml_content

    def test_stroke_with_dash_array(self):
        """Test stroke with dash pattern"""
        stroke = Stroke(
            width=1.0,
            paint=SolidPaint(rgb="000000"),
            dash_array=[5, 3, 2, 3],
        )
        circle = Circle(center=Point(100, 100), radius=50, stroke=stroke)
        mapper = CircleMapper()

        result = mapper.map(circle)

        # Should include dash pattern
        assert '<a:prstDash val="dash"/>' in result.xml_content
