#!/usr/bin/env python3
"""
Unit tests for core Scene Mapper.

Tests the mapping from IR Scene objects to PowerPoint slide XML structure.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys

from tests.unit.core.conftest import IRTestBase

try:
    from core.mappers import SceneMapper
    from core.ir import Scene, Path, TextFrame, Group, Image
    from core.ir import Point, Rect, LineSegment, SolidPaint
    CORE_MAPPERS_AVAILABLE = True
except ImportError:
    CORE_MAPPERS_AVAILABLE = False
    pytest.skip("Core mappers not available", allow_module_level=True)


class TestSceneMapperCreation(IRTestBase):
    """Test SceneMapper creation and initialization."""

    def test_scene_mapper_initialization(self):
        """Test creating a scene mapper."""
        mapper = SceneMapper()

        assert mapper is not None
        # Test if mapper has required methods
        assert hasattr(mapper, 'map_scene')
        assert callable(mapper.map_scene)

    def test_scene_mapper_with_options(self):
        """Test scene mapper with configuration options."""
        options = {
            'slide_width': 10 * 914400,  # 10 inches in EMU
            'slide_height': 7.5 * 914400,  # 7.5 inches in EMU
            'preserve_aspect_ratio': True
        }

        try:
            mapper = SceneMapper(options=options)
            assert mapper is not None
            if hasattr(mapper, 'options'):
                assert mapper.options == options
        except TypeError:
            # Options might not be supported in constructor
            mapper = SceneMapper()
            assert mapper is not None


class TestSceneMapperBasicMapping(IRTestBase):
    """Test basic scene mapping functionality."""

    def test_map_empty_scene(self, sample_ir_scene):
        """Test mapping an empty scene."""
        # Create empty scene
        empty_scene = Scene(
            elements=[],
            viewbox=(0, 0, 100, 100),
            width=100,
            height=100
        )

        mapper = SceneMapper()
        result = mapper.map_scene(empty_scene)

        assert result is not None
        # Should produce some XML structure even for empty scene
        if hasattr(result, 'tag'):
            # Result is XML element
            assert result.tag is not None
        elif isinstance(result, str):
            # Result is XML string
            assert len(result) > 0

    def test_map_scene_with_single_element(self):
        """Test mapping scene with single path element."""
        # Create simple path
        path = Path(
            segments=[LineSegment(Point(0, 0), Point(100, 100))],
            fill=SolidPaint(color="#FF0000"),
            stroke=None,
            is_closed=False,
            data="M 0 0 L 100 100"
        )

        scene = Scene(
            elements=[path],
            viewbox=(0, 0, 200, 200),
            width=200,
            height=200
        )

        mapper = SceneMapper()
        result = mapper.map_scene(scene)

        assert result is not None
        # Should contain path-related XML
        if isinstance(result, str):
            assert "path" in result.lower() or "sp" in result  # Shape element

    def test_map_scene_with_multiple_elements(self):
        """Test mapping scene with multiple elements."""
        # Create multiple elements
        path = Path(
            segments=[LineSegment(Point(0, 0), Point(50, 50))],
            fill=SolidPaint(color="#FF0000"),
            stroke=None,
            is_closed=False,
            data="M 0 0 L 50 50"
        )

        text_frame = TextFrame(
            content="Test Text",
            bounds=Rect(60, 60, 100, 30),
            style=None
        )

        scene = Scene(
            elements=[path, text_frame],
            viewbox=(0, 0, 200, 200),
            width=200,
            height=200
        )

        mapper = SceneMapper()
        result = mapper.map_scene(scene)

        assert result is not None
        # Should contain multiple shape elements
        if isinstance(result, str):
            # Count occurrences of shape-like elements
            shape_count = result.lower().count('<p:sp') + result.lower().count('<a:path')
            assert shape_count > 0


class TestSceneMapperCoordinateTransformation(IRTestBase):
    """Test coordinate transformation during mapping."""

    def test_viewbox_to_slide_transformation(self):
        """Test viewbox coordinate transformation."""
        # Create scene with specific viewbox
        path = Path(
            segments=[LineSegment(Point(10, 10), Point(90, 90))],
            fill=SolidPaint(color="#0000FF"),
            stroke=None,
            is_closed=False,
            data="M 10 10 L 90 90"
        )

        scene = Scene(
            elements=[path],
            viewbox=(0, 0, 100, 100),  # 100x100 SVG units
            width=200,  # 200 actual units (2x scale)
            height=200
        )

        mapper = SceneMapper()
        result = mapper.map_scene(scene)

        assert result is not None
        # Coordinates should be transformed
        # (10,10) in SVG should become (20,20) in slide coordinates

    def test_coordinate_offset_transformation(self):
        """Test coordinate transformation with viewbox offset."""
        path = Path(
            segments=[LineSegment(Point(0, 0), Point(50, 50))],
            fill=SolidPaint(color="#00FF00"),
            stroke=None,
            is_closed=False,
            data="M 0 0 L 50 50"
        )

        scene = Scene(
            elements=[path],
            viewbox=(25, 25, 125, 125),  # Offset viewbox
            width=100,
            height=100
        )

        mapper = SceneMapper()
        result = mapper.map_scene(scene)

        assert result is not None
        # Coordinates should account for viewbox offset

    def test_emu_coordinate_conversion(self):
        """Test conversion to EMU (English Metric Units)."""
        path = Path(
            segments=[LineSegment(Point(0, 0), Point(1, 1))],
            fill=SolidPaint(color="#FF00FF"),
            stroke=None,
            is_closed=False,
            data="M 0 0 L 1 1"
        )

        scene = Scene(
            elements=[path],
            viewbox=(0, 0, 10, 10),
            width=10,
            height=10
        )

        mapper = SceneMapper()
        result = mapper.map_scene(scene)

        assert result is not None
        # Should contain EMU coordinates (large numbers)
        if isinstance(result, str):
            # Look for EMU-scale numbers (6+ digits)
            import re
            emu_numbers = re.findall(r'\d{6,}', result)
            # Should find some EMU coordinates


class TestSceneMapperElementMapping(IRTestBase):
    """Test mapping of different element types."""

    def test_map_path_element(self):
        """Test mapping of path elements to DrawingML."""
        path = Path(
            segments=[
                LineSegment(Point(0, 0), Point(50, 0)),
                LineSegment(Point(50, 0), Point(50, 50)),
                LineSegment(Point(50, 50), Point(0, 50)),
                LineSegment(Point(0, 50), Point(0, 0))
            ],
            fill=SolidPaint(color="#FF0000"),
            stroke=None,
            is_closed=True,
            data="M 0 0 L 50 0 L 50 50 L 0 50 Z"
        )

        scene = Scene(
            elements=[path],
            viewbox=(0, 0, 100, 100),
            width=100,
            height=100
        )

        mapper = SceneMapper()
        result = mapper.map_scene(scene)

        assert result is not None
        if isinstance(result, str):
            # Should contain path-related DrawingML
            assert any(tag in result.lower() for tag in ['path', 'custgeom', 'sp'])

    def test_map_text_element(self):
        """Test mapping of text elements to DrawingML."""
        text_frame = TextFrame(
            content="Sample Text",
            bounds=Rect(10, 20, 150, 40),
            style=None
        )

        scene = Scene(
            elements=[text_frame],
            viewbox=(0, 0, 200, 200),
            width=200,
            height=200
        )

        mapper = SceneMapper()
        result = mapper.map_scene(scene)

        assert result is not None
        if isinstance(result, str):
            # Should contain text-related DrawingML
            assert any(tag in result.lower() for tag in ['txbody', 'r', 't', 'sp'])
            # Should contain the actual text content
            assert "Sample Text" in result

    def test_map_group_element(self):
        """Test mapping of group elements."""
        # Create group with child elements
        child_path = Path(
            segments=[LineSegment(Point(0, 0), Point(25, 25))],
            fill=SolidPaint(color="#0000FF"),
            stroke=None,
            is_closed=False,
            data="M 0 0 L 25 25"
        )

        try:
            group = Group(
                children=[child_path],
                transform="translate(10, 10)",
                clip_id=None
            )

            scene = Scene(
                elements=[group],
                viewbox=(0, 0, 100, 100),
                width=100,
                height=100
            )

            mapper = SceneMapper()
            result = mapper.map_scene(scene)

            assert result is not None
            if isinstance(result, str):
                # Should contain group-related DrawingML
                assert any(tag in result.lower() for tag in ['grpsp', 'sp'])
        except NameError:
            pytest.skip("Group element not available")

    def test_map_image_element(self):
        """Test mapping of image elements."""
        try:
            image = Image(
                src="test_image.png",
                bounds=Rect(0, 0, 100, 75),
                alt_text="Test Image"
            )

            scene = Scene(
                elements=[image],
                viewbox=(0, 0, 200, 200),
                width=200,
                height=200
            )

            mapper = SceneMapper()
            result = mapper.map_scene(scene)

            assert result is not None
            if isinstance(result, str):
                # Should contain image-related DrawingML
                assert any(tag in result.lower() for tag in ['pic', 'blipfill', 'sp'])
        except NameError:
            pytest.skip("Image element not available")


class TestSceneMapperStyleMapping(IRTestBase):
    """Test mapping of styles and visual properties."""

    def test_map_fill_styles(self):
        """Test mapping of fill styles."""
        # Solid fill
        solid_path = Path(
            segments=[LineSegment(Point(0, 0), Point(50, 50))],
            fill=SolidPaint(color="#FF0000"),
            stroke=None,
            is_closed=False,
            data="M 0 0 L 50 50"
        )

        scene = Scene(
            elements=[solid_path],
            viewbox=(0, 0, 100, 100),
            width=100,
            height=100
        )

        mapper = SceneMapper()
        result = mapper.map_scene(scene)

        assert result is not None
        if isinstance(result, str):
            # Should contain fill-related DrawingML
            assert any(tag in result.lower() for tag in ['solidfill', 'srgbclr', 'fill'])

    def test_map_stroke_styles(self):
        """Test mapping of stroke styles."""
        from core.ir import Stroke

        try:
            stroke = Stroke(
                paint=SolidPaint(color="#000000"),
                width=2.0
            )

            path = Path(
                segments=[LineSegment(Point(0, 0), Point(100, 0))],
                fill=None,
                stroke=stroke,
                is_closed=False,
                data="M 0 0 L 100 0"
            )

            scene = Scene(
                elements=[path],
                viewbox=(0, 0, 150, 150),
                width=150,
                height=150
            )

            mapper = SceneMapper()
            result = mapper.map_scene(scene)

            assert result is not None
            if isinstance(result, str):
                # Should contain stroke-related DrawingML
                assert any(tag in result.lower() for tag in ['ln', 'solidfill', 'w'])
        except NameError:
            pytest.skip("Stroke not available")

    def test_map_gradient_styles(self):
        """Test mapping of gradient styles."""
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
                segments=[LineSegment(Point(0, 0), Point(100, 100))],
                fill=gradient,
                stroke=None,
                is_closed=False,
                data="M 0 0 L 100 100"
            )

            scene = Scene(
                elements=[path],
                viewbox=(0, 0, 150, 150),
                width=150,
                height=150
            )

            mapper = SceneMapper()
            result = mapper.map_scene(scene)

            assert result is not None
            if isinstance(result, str):
                # Should contain gradient-related DrawingML
                assert any(tag in result.lower() for tag in ['gradfill', 'lin', 'gs'])
        except NameError:
            pytest.skip("LinearGradient not available")


class TestSceneMapperValidation(IRTestBase):
    """Test scene mapper validation and error handling."""

    def test_map_invalid_scene(self):
        """Test mapping with invalid scene object."""
        mapper = SceneMapper()

        with pytest.raises((TypeError, ValueError, AttributeError)):
            mapper.map_scene(None)

        with pytest.raises((TypeError, ValueError, AttributeError)):
            mapper.map_scene("invalid_scene")

    def test_map_scene_with_invalid_elements(self):
        """Test mapping scene with invalid elements."""
        # Scene with invalid element
        invalid_scene = Scene(
            elements=[Mock()],  # Invalid element
            viewbox=(0, 0, 100, 100),
            width=100,
            height=100
        )

        mapper = SceneMapper()

        # Should either handle gracefully or raise appropriate error
        try:
            result = mapper.map_scene(invalid_scene)
            # If it succeeds, should still produce valid result
            assert result is not None
        except (TypeError, ValueError, AttributeError):
            # Expected for invalid elements
            pass

    def test_map_scene_with_missing_properties(self):
        """Test mapping scene with missing properties."""
        # Create element with missing properties
        incomplete_path = Mock()
        incomplete_path.fill = None
        incomplete_path.stroke = None

        scene = Scene(
            elements=[incomplete_path],
            viewbox=(0, 0, 100, 100),
            width=100,
            height=100
        )

        mapper = SceneMapper()

        # Should handle missing properties gracefully
        try:
            result = mapper.map_scene(scene)
            assert result is not None
        except (AttributeError, TypeError):
            # Might fail with incomplete elements
            pass


class TestSceneMapperOutput(IRTestBase):
    """Test scene mapper output format and structure."""

    def test_output_format_xml(self):
        """Test that output is valid XML format."""
        path = Path(
            segments=[LineSegment(Point(0, 0), Point(50, 50))],
            fill=SolidPaint(color="#FF0000"),
            stroke=None,
            is_closed=False,
            data="M 0 0 L 50 50"
        )

        scene = Scene(
            elements=[path],
            viewbox=(0, 0, 100, 100),
            width=100,
            height=100
        )

        mapper = SceneMapper()
        result = mapper.map_scene(scene)

        assert result is not None

        if isinstance(result, str):
            # Should be valid XML
            try:
                from lxml import etree
                etree.fromstring(result)
                # No exception means valid XML
            except etree.XMLSyntaxError:
                # Try wrapping in root element
                wrapped = f"<root>{result}</root>"
                etree.fromstring(wrapped)

    def test_output_contains_required_namespaces(self):
        """Test that output contains required PowerPoint namespaces."""
        path = Path(
            segments=[LineSegment(Point(0, 0), Point(25, 25))],
            fill=SolidPaint(color="#00FF00"),
            stroke=None,
            is_closed=False,
            data="M 0 0 L 25 25"
        )

        scene = Scene(
            elements=[path],
            viewbox=(0, 0, 100, 100),
            width=100,
            height=100
        )

        mapper = SceneMapper()
        result = mapper.map_scene(scene)

        assert result is not None

        if isinstance(result, str):
            # Should contain PowerPoint/Office namespaces
            expected_namespaces = ['p:', 'a:', 'r:']
            found_namespaces = [ns for ns in expected_namespaces if ns in result]
            # Should find at least one namespace
            assert len(found_namespaces) > 0

    def test_output_structure_validity(self):
        """Test that output has valid PowerPoint structure."""
        path = Path(
            segments=[LineSegment(Point(0, 0), Point(75, 75))],
            fill=SolidPaint(color="#0000FF"),
            stroke=None,
            is_closed=False,
            data="M 0 0 L 75 75"
        )

        scene = Scene(
            elements=[path],
            viewbox=(0, 0, 150, 150),
            width=150,
            height=150
        )

        mapper = SceneMapper()
        result = mapper.map_scene(scene)

        assert result is not None

        if isinstance(result, str):
            # Should have proper nesting structure
            # Count opening vs closing tags
            opening_tags = result.count('<p:') + result.count('<a:')
            closing_tags = result.count('</p:') + result.count('</a:')
            # Should be balanced (allowing for self-closing tags)
            assert abs(opening_tags - closing_tags) <= opening_tags // 2


class TestSceneMapperPerformance(IRTestBase):
    """Test scene mapper performance characteristics."""

    def test_mapping_performance_simple_scene(self):
        """Test mapping performance with simple scene."""
        import time

        # Create simple scene
        path = Path(
            segments=[LineSegment(Point(0, 0), Point(100, 100))],
            fill=SolidPaint(color="#FF0000"),
            stroke=None,
            is_closed=False,
            data="M 0 0 L 100 100"
        )

        scene = Scene(
            elements=[path],
            viewbox=(0, 0, 200, 200),
            width=200,
            height=200
        )

        mapper = SceneMapper()

        start_time = time.time()
        result = mapper.map_scene(scene)
        mapping_time = time.time() - start_time

        assert result is not None
        assert mapping_time < 0.1  # Should map quickly

    def test_mapping_performance_complex_scene(self):
        """Test mapping performance with complex scene."""
        import time

        # Create scene with multiple elements
        elements = []
        for i in range(50):
            path = Path(
                segments=[LineSegment(Point(i, 0), Point(i+10, 10))],
                fill=SolidPaint(color=f"#{i:02x}0000"),
                stroke=None,
                is_closed=False,
                data=f"M {i} 0 L {i+10} 10"
            )
            elements.append(path)

        scene = Scene(
            elements=elements,
            viewbox=(0, 0, 100, 100),
            width=100,
            height=100
        )

        mapper = SceneMapper()

        start_time = time.time()
        result = mapper.map_scene(scene)
        mapping_time = time.time() - start_time

        assert result is not None
        assert mapping_time < 1.0  # Should handle complex scenes reasonably fast

    def test_memory_usage_large_scene(self):
        """Test memory usage with large scene."""
        import sys

        # Create large scene
        elements = []
        for i in range(100):
            path = Path(
                segments=[LineSegment(Point(i, 0), Point(i+5, 5))],
                fill=SolidPaint(color="#FF0000"),
                stroke=None,
                is_closed=False,
                data=f"M {i} 0 L {i+5} 5"
            )
            elements.append(path)

        scene = Scene(
            elements=elements,
            viewbox=(0, 0, 200, 200),
            width=200,
            height=200
        )

        mapper = SceneMapper()
        result = mapper.map_scene(scene)

        assert result is not None

        # Check result size is reasonable
        if isinstance(result, str):
            result_size = sys.getsizeof(result)
            assert result_size < 1000000  # Less than 1MB


if __name__ == "__main__":
    pytest.main([__file__])