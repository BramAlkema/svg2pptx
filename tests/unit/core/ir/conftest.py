#!/usr/bin/env python3
"""
IR Component Test Fixtures

Provides specialized fixtures for testing Intermediate Representation components.
"""

import pytest
from typing import List, Dict, Any
from unittest.mock import Mock

# Import from parent conftest
import sys
import os

# Add parent directory to path
parent_dir = os.path.join(os.path.dirname(__file__), '..')
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

try:
    from tests.unit.core.conftest import IRTestBase
except ImportError:
    # Fallback: create a simple IRTestBase
    class IRTestBase:
        def assert_valid_ir_element(self, element):
            assert hasattr(element, '__dataclass_fields__') or hasattr(element, '__dict__')

try:
    from core.ir import (
        Scene, Path, TextFrame, Group, Image,
        Point, Rect, Segment, LineSegment, BezierSegment, ArcSegment,
        SolidPaint, LinearGradientPaint, RadialGradientPaint, PatternPaint,
        GradientStop, Stroke, StrokeJoin, StrokeCap,
        Run, TextAnchor, ClipRef, ClipStrategy,
        validate_ir, IRValidationError
    )
    CORE_IR_AVAILABLE = True
except ImportError:
    CORE_IR_AVAILABLE = False


class IRComponentTestBase(IRTestBase):
    """Base class for IR component testing with specialized assertions"""

    def assert_scene_valid(self, scene: 'Scene'):
        """Assert that a Scene is valid"""
        if not CORE_IR_AVAILABLE:
            pytest.skip("Core IR components not available")

        assert scene is not None
        assert hasattr(scene, 'elements')
        assert isinstance(scene.elements, list)
        assert scene.viewbox is not None
        assert len(scene.viewbox) == 4  # x, y, width, height

        # Validate all elements
        for element in scene.elements:
            self.assert_valid_ir_element(element)

    def assert_path_segments_valid(self, segments: List['Segment']):
        """Assert that path segments form a valid path"""
        if not CORE_IR_AVAILABLE:
            pytest.skip("Core IR components not available")

        assert len(segments) > 0

        # First segment should start from a defined point
        first_segment = segments[0]
        assert hasattr(first_segment, 'start')

        # Segments should be connected
        for i in range(1, len(segments)):
            prev_end = segments[i-1].end
            curr_start = segments[i].start
            self.assert_point_equal(prev_end, curr_start)

    def assert_paint_valid(self, paint):
        """Assert that paint is valid"""
        if not CORE_IR_AVAILABLE:
            pytest.skip("Core IR components not available")

        if paint is None:
            return

        if hasattr(paint, 'color'):
            # Solid paint
            assert isinstance(paint.color, str)
            assert len(paint.color) in [6, 8]  # RGB or RGBA hex
        elif hasattr(paint, 'stops'):
            # Gradient paint
            assert len(paint.stops) >= 2
            for stop in paint.stops:
                assert 0.0 <= stop.position <= 1.0
                assert isinstance(stop.color, str)


@pytest.fixture
def ir_test_base():
    """Provide IR test base class instance"""
    return IRComponentTestBase()


@pytest.fixture
def complex_path_segments():
    """Complex path with multiple segment types"""
    if not CORE_IR_AVAILABLE:
        pytest.skip("Core IR components not available")

    return [
        LineSegment(start=Point(0, 0), end=Point(10, 0)),
        BezierSegment(
            start=Point(10, 0),
            control1=Point(15, 5),
            control2=Point(20, 5),
            end=Point(25, 0)
        ),
        ArcSegment(
            start=Point(25, 0),
            end=Point(35, 10),
            rx=10, ry=10,
            rotation=0,
            large_arc=False,
            sweep=True
        ),
        LineSegment(start=Point(35, 10), end=Point(0, 10)),
        LineSegment(start=Point(0, 10), end=Point(0, 0))
    ]


@pytest.fixture
def radial_gradient_paint():
    """Radial gradient paint for testing"""
    if not CORE_IR_AVAILABLE:
        pytest.skip("Core IR components not available")

    stops = [
        GradientStop(position=0.0, color="ffffff"),
        GradientStop(position=0.5, color="888888"),
        GradientStop(position=1.0, color="000000")
    ]

    return RadialGradientPaint(
        stops=stops,
        cx=50, cy=50, r=25,
        fx=50, fy=50
    )


@pytest.fixture
def pattern_paint():
    """Pattern paint for testing"""
    if not CORE_IR_AVAILABLE:
        pytest.skip("Core IR components not available")

    return PatternPaint(
        pattern_id="pattern1",
        width=10, height=10,
        pattern_units="userSpaceOnUse",
        content_units="userSpaceOnUse"
    )


@pytest.fixture
def complex_stroke():
    """Complex stroke with all properties"""
    if not CORE_IR_AVAILABLE:
        pytest.skip("Core IR components not available")

    return Stroke(
        paint=SolidPaint(color="ff0000"),
        width=2.5,
        cap=StrokeCap.ROUND,
        join=StrokeJoin.MITER,
        miter_limit=4.0,
        dash_array=[5, 3, 2, 3],
        dash_offset=1.5,
        opacity=0.8
    )


@pytest.fixture
def multilingual_text_runs():
    """Text runs with different languages and styles"""
    if not CORE_IR_AVAILABLE:
        pytest.skip("Core IR components not available")

    return [
        Run(
            content="Hello ",
            font_family="Arial",
            font_size_pt=12,
            color="000000",
            bold=False,
            italic=False
        ),
        Run(
            content="World",
            font_family="Arial",
            font_size_pt=12,
            color="ff0000",
            bold=True,
            italic=False
        ),
        Run(
            content=" 世界",
            font_family="SimHei",
            font_size_pt=12,
            color="0000ff",
            bold=False,
            italic=True
        ),
        Run(
            content=" مرحبا",
            font_family="Arial Unicode MS",
            font_size_pt=12,
            color="00ff00",
            bold=False,
            italic=False,
            direction="rtl"
        )
    ]


@pytest.fixture
def nested_group_structure():
    """Nested group structure for testing"""
    if not CORE_IR_AVAILABLE:
        pytest.skip("Core IR components not available")

    # Inner group
    inner_path = Path(
        segments=[LineSegment(start=Point(0, 0), end=Point(10, 10))],
        fill=SolidPaint(color="ff0000"),
        data="M 0 0 L 10 10"
    )

    inner_group = Group(
        children=[inner_path],
        transform="translate(5, 5)",
        opacity=0.8
    )

    # Outer group
    outer_path = Path(
        segments=[LineSegment(start=Point(20, 20), end=Point(30, 30))],
        fill=SolidPaint(color="00ff00"),
        data="M 20 20 L 30 30"
    )

    outer_group = Group(
        children=[inner_group, outer_path],
        transform="rotate(45)",
        clip_id="clip1"
    )

    return outer_group


@pytest.fixture
def clip_references():
    """Clipping references for testing"""
    if not CORE_IR_AVAILABLE:
        pytest.skip("Core IR components not available")

    return [
        ClipRef(
            clip_id="rect_clip",
            strategy=ClipStrategy.MASK,
            path_data="M 0 0 L 100 0 L 100 100 L 0 100 Z"
        ),
        ClipRef(
            clip_id="circle_clip",
            strategy=ClipStrategy.REGION,
            path_data="M 50 50 m -25 0 a 25 25 0 1 0 50 0 a 25 25 0 1 0 -50 0"
        )
    ]


@pytest.fixture
def performance_test_scene():
    """Large scene for performance testing"""
    if not CORE_IR_AVAILABLE:
        pytest.skip("Core IR components not available")

    elements = []

    # Create many simple paths
    for i in range(100):
        x = (i % 10) * 20
        y = (i // 10) * 20

        path = Path(
            segments=[
                LineSegment(start=Point(x, y), end=Point(x+10, y)),
                LineSegment(start=Point(x+10, y), end=Point(x+10, y+10)),
                LineSegment(start=Point(x+10, y+10), end=Point(x, y+10)),
                LineSegment(start=Point(x, y+10), end=Point(x, y))
            ],
            fill=SolidPaint(color=f"{i:02x}0000"),
            stroke=Stroke(paint=SolidPaint(color="000000"), width=1),
            is_closed=True,
            data=f"M {x} {y} L {x+10} {y} L {x+10} {y+10} L {x} {y+10} Z"
        )
        elements.append(path)

    return Scene(
        elements=elements,
        viewbox=(0, 0, 200, 200),
        width=200,
        height=200
    )


@pytest.fixture
def edge_case_elements():
    """Edge case elements for robustness testing"""
    if not CORE_IR_AVAILABLE:
        pytest.skip("Core IR components not available")

    return {
        'empty_path': Path(
            segments=[],
            data="",
            fill=None,
            stroke=None
        ),
        'zero_dimensions': Image(
            href="test.png",
            x=0, y=0,
            width=0, height=0
        ),
        'empty_text': TextFrame(
            runs=[],
            x=0, y=0,
            width=0, height=0,
            anchor=TextAnchor.TOP_LEFT
        ),
        'empty_group': Group(
            children=[],
            transform=None
        ),
        'extreme_coordinates': Path(
            segments=[
                LineSegment(
                    start=Point(-1e6, -1e6),
                    end=Point(1e6, 1e6)
                )
            ],
            data="M -1000000 -1000000 L 1000000 1000000"
        )
    }


# Validation utilities
def validate_ir_structure(element):
    """Validate IR element structure comprehensively"""
    if not CORE_IR_AVAILABLE:
        pytest.skip("Core IR components not available")

    try:
        validate_ir(element)
        return True
    except IRValidationError as e:
        pytest.fail(f"IR validation failed: {e}")
    except Exception as e:
        pytest.fail(f"Unexpected validation error: {e}")


def create_minimal_valid_scene():
    """Create minimal valid scene for testing"""
    if not CORE_IR_AVAILABLE:
        pytest.skip("Core IR components not available")

    path = Path(
        segments=[LineSegment(start=Point(0, 0), end=Point(10, 10))],
        fill=SolidPaint(color="000000"),
        data="M 0 0 L 10 10"
    )

    return Scene(
        elements=[path],
        viewbox=(0, 0, 100, 100),
        width=100,
        height=100
    )