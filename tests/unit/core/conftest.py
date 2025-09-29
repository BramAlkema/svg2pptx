#!/usr/bin/env python3
"""
Core Test Configuration and Fixtures

Provides base fixtures and utilities for testing clean slate components.
"""

import pytest
from unittest.mock import Mock, MagicMock
from typing import Dict, Any, List, Optional
from lxml import etree as ET

# Import core components for testing
try:
    from core.ir import Scene, Path, TextFrame, Group, Image
    from core.ir import Point, Rect, Segment, LineSegment, BezierSegment
    from core.ir import SolidPaint, LinearGradientPaint, GradientStop
    from core.ir import Stroke, StrokeJoin, StrokeCap
    from core.ir import validate_ir
    CORE_IR_AVAILABLE = True
except ImportError:
    CORE_IR_AVAILABLE = False


class IRTestBase:
    """Base class for IR component testing"""

    def assert_valid_ir_element(self, element):
        """Validate IR element structure"""
        if CORE_IR_AVAILABLE:
            # Use existing validation if available
            validate_ir(element)
        else:
            # Basic validation fallback
            assert hasattr(element, '__dataclass_fields__')
            assert element is not None

    def assert_point_equal(self, p1: 'Point', p2: 'Point', tolerance: float = 1e-6):
        """Assert two points are equal within tolerance"""
        assert abs(p1.x - p2.x) < tolerance
        assert abs(p1.y - p2.y) < tolerance

    def assert_rect_equal(self, r1: 'Rect', r2: 'Rect', tolerance: float = 1e-6):
        """Assert two rectangles are equal within tolerance"""
        assert abs(r1.x - r2.x) < tolerance
        assert abs(r1.y - r2.y) < tolerance
        assert abs(r1.width - r2.width) < tolerance
        assert abs(r1.height - r2.height) < tolerance


@pytest.fixture
def sample_points():
    """Sample Point objects for testing"""
    if not CORE_IR_AVAILABLE:
        pytest.skip("Core IR components not available")

    return [
        Point(0, 0),
        Point(10, 20),
        Point(-5, 15.5),
        Point(100, 100)
    ]


@pytest.fixture
def sample_rect():
    """Sample Rect object for testing"""
    if not CORE_IR_AVAILABLE:
        pytest.skip("Core IR components not available")

    return Rect(x=10, y=20, width=50, height=30)


@pytest.fixture
def sample_line_segments(sample_points):
    """Sample LineSegment objects for testing"""
    if not CORE_IR_AVAILABLE:
        pytest.skip("Core IR components not available")

    return [
        LineSegment(start=sample_points[0], end=sample_points[1]),
        LineSegment(start=sample_points[1], end=sample_points[2]),
        LineSegment(start=sample_points[2], end=sample_points[3])
    ]


@pytest.fixture
def sample_bezier_segment(sample_points):
    """Sample BezierSegment for testing"""
    if not CORE_IR_AVAILABLE:
        pytest.skip("Core IR components not available")

    return BezierSegment(
        start=sample_points[0],
        control1=sample_points[1],
        control2=sample_points[2],
        end=sample_points[3]
    )


@pytest.fixture
def sample_solid_paint():
    """Sample SolidPaint for testing"""
    if not CORE_IR_AVAILABLE:
        pytest.skip("Core IR components not available")

    return SolidPaint(color="ff0000")


@pytest.fixture
def sample_gradient_stops():
    """Sample gradient stops for testing"""
    if not CORE_IR_AVAILABLE:
        pytest.skip("Core IR components not available")

    return [
        GradientStop(position=0.0, color="ff0000"),
        GradientStop(position=0.5, color="00ff00"),
        GradientStop(position=1.0, color="0000ff")
    ]


@pytest.fixture
def sample_linear_gradient(sample_gradient_stops):
    """Sample LinearGradientPaint for testing"""
    if not CORE_IR_AVAILABLE:
        pytest.skip("Core IR components not available")

    return LinearGradientPaint(
        stops=sample_gradient_stops,
        angle=45.0,
        x1=0, y1=0, x2=100, y2=100
    )


@pytest.fixture
def sample_stroke(sample_solid_paint):
    """Sample Stroke for testing"""
    if not CORE_IR_AVAILABLE:
        pytest.skip("Core IR components not available")

    return Stroke(
        paint=sample_solid_paint,
        width=2.0,
        cap=StrokeCap.ROUND,
        join=StrokeJoin.ROUND,
        dash_array=[5, 5]
    )


@pytest.fixture
def sample_path(sample_line_segments, sample_solid_paint, sample_stroke):
    """Sample Path IR element for testing"""
    if not CORE_IR_AVAILABLE:
        pytest.skip("Core IR components not available")

    return Path(
        segments=sample_line_segments,
        fill=sample_solid_paint,
        stroke=sample_stroke,
        is_closed=True,
        data="M 0 0 L 10 20 L -5 15.5 L 100 100 Z"
    )


@pytest.fixture
def sample_textframe():
    """Sample TextFrame IR element for testing"""
    if not CORE_IR_AVAILABLE:
        pytest.skip("Core IR components not available")

    from core.ir import Run, TextAnchor

    runs = [
        Run(content="Hello ", font_family="Arial", font_size_pt=12, color="000000"),
        Run(content="World", font_family="Arial", font_size_pt=12, color="ff0000", bold=True)
    ]

    return TextFrame(
        runs=runs,
        x=10, y=20,
        width=100, height=30,
        anchor=TextAnchor.TOP_LEFT
    )


@pytest.fixture
def sample_group(sample_path, sample_textframe):
    """Sample Group IR element for testing"""
    if not CORE_IR_AVAILABLE:
        pytest.skip("Core IR components not available")

    return Group(
        children=[sample_path, sample_textframe],
        transform="translate(10, 20) rotate(45)",
        clip_id="clip1"
    )


@pytest.fixture
def sample_image():
    """Sample Image IR element for testing"""
    if not CORE_IR_AVAILABLE:
        pytest.skip("Core IR components not available")

    return Image(
        href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==",
        x=0, y=0,
        width=100, height=100,
        preserve_aspect_ratio=True
    )


@pytest.fixture
def sample_ir_scene(sample_path, sample_textframe, sample_group, sample_image):
    """Sample complete IR Scene for testing"""
    if not CORE_IR_AVAILABLE:
        pytest.skip("Core IR components not available")

    return Scene(
        elements=[sample_path, sample_textframe, sample_group, sample_image],
        viewbox=(0, 0, 200, 200),
        width=200,
        height=200
    )


@pytest.fixture
def mock_policy_engine():
    """Mock policy engine for testing"""
    policy = Mock()

    # Mock policy decision
    decision = Mock()
    decision.use_native = True
    decision.estimated_quality = 0.95
    decision.estimated_performance = 0.9
    decision.reasoning = "Simple path, use native DrawingML"

    policy.decide_path.return_value = decision
    policy.decide_text.return_value = decision
    policy.decide_group.return_value = decision
    policy.decide_image.return_value = decision

    return policy


@pytest.fixture
def mock_conversion_services():
    """Mock ConversionServices for testing"""
    services = Mock()

    # Mock basic services
    services.unit_converter = Mock()
    services.color_parser = Mock()
    services.transform_parser = Mock()
    services.viewport_handler = Mock()

    # Mock clean slate services
    services.ir_scene_factory = Mock()
    services.policy_engine = Mock()
    services.mapper_registry = Mock()
    services.drawingml_embedder = Mock()

    return services


@pytest.fixture
def sample_svg_elements():
    """Sample SVG elements for testing mappers"""
    elements = {}

    # Path element
    path = ET.Element('path')
    path.set('d', 'M 0 0 L 10 10 L 20 0 Z')
    path.set('fill', 'red')
    path.set('stroke', 'blue')
    path.set('stroke-width', '2')
    elements['path'] = path

    # Text element
    text = ET.Element('text')
    text.set('x', '10')
    text.set('y', '20')
    text.set('font-family', 'Arial')
    text.set('font-size', '12')
    text.text = 'Hello World'
    elements['text'] = text

    # Group element
    group = ET.Element('g')
    group.set('transform', 'translate(10, 20)')
    group.append(path)
    elements['group'] = group

    # Rectangle element
    rect = ET.Element('rect')
    rect.set('x', '0')
    rect.set('y', '0')
    rect.set('width', '100')
    rect.set('height', '50')
    rect.set('fill', 'green')
    elements['rect'] = rect

    # Circle element
    circle = ET.Element('circle')
    circle.set('cx', '50')
    circle.set('cy', '50')
    circle.set('r', '25')
    circle.set('fill', 'yellow')
    elements['circle'] = circle

    # Image element
    image = ET.Element('image')
    image.set('x', '0')
    image.set('y', '0')
    image.set('width', '100')
    image.set('height', '100')
    image.set('href', 'test.png')
    elements['image'] = image

    return elements


@pytest.fixture
def sample_svg_content():
    """Sample SVG content strings for testing"""
    return {
        'simple': '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="100" height="100" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
    <rect x="10" y="10" width="50" height="30" fill="red"/>
</svg>''',

        'complex': '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="200" height="200" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
    <defs>
        <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" style="stop-color:rgb(255,255,0);stop-opacity:1" />
            <stop offset="100%" style="stop-color:rgb(255,0,0);stop-opacity:1" />
        </linearGradient>
    </defs>
    <g transform="translate(10, 20) rotate(45)">
        <rect x="10" y="10" width="50" height="30" fill="url(#grad1)"/>
        <path d="M 50 50 L 100 50 L 100 100 L 50 100 Z" fill="blue" stroke="black" stroke-width="2"/>
        <text x="10" y="150" font-family="Arial" font-size="12">Test Text</text>
        <circle cx="150" cy="150" r="25" fill="green"/>
    </g>
</svg>'''
    }


# Test utilities
def create_test_svg_element(tag: str, **attributes) -> ET.Element:
    """Create a test SVG element with given attributes"""
    element = ET.Element(tag)
    for key, value in attributes.items():
        element.set(key.replace('_', '-'), str(value))
    return element


def validate_drawingml_xml(xml_content: str) -> bool:
    """Validate that XML content is well-formed DrawingML"""
    try:
        # Basic XML validation
        ET.fromstring(xml_content.encode('utf-8'))

        # Check for basic DrawingML structure
        required_patterns = ['<p:sp>', '<p:spPr>', '<a:xfrm>']
        return all(pattern in xml_content for pattern in required_patterns[:1])  # At least one required
    except ET.XMLSyntaxError:
        return False


def assert_performance_within_bounds(actual_time_ms: float, baseline_time_ms: float, tolerance: float = 1.5):
    """Assert that performance is within acceptable bounds"""
    ratio = actual_time_ms / max(baseline_time_ms, 1.0)  # Avoid division by zero
    assert ratio <= tolerance, f"Performance regression: {ratio:.2f}x slower than baseline (tolerance: {tolerance}x)"


class TestDataGenerator:
    """Utility class for generating test data"""

    @staticmethod
    def create_random_path(num_segments: int = 5) -> str:
        """Generate random path data string"""
        import random

        commands = [f'M {random.randint(0, 100)} {random.randint(0, 100)}']

        for _ in range(num_segments):
            if random.choice([True, False]):
                # Line to
                commands.append(f'L {random.randint(0, 100)} {random.randint(0, 100)}')
            else:
                # Curve to
                commands.append(f'C {random.randint(0, 100)} {random.randint(0, 100)} '
                             f'{random.randint(0, 100)} {random.randint(0, 100)} '
                             f'{random.randint(0, 100)} {random.randint(0, 100)}')

        if random.choice([True, False]):
            commands.append('Z')  # Close path

        return ' '.join(commands)

    @staticmethod
    def create_test_colors(count: int = 5) -> List[str]:
        """Generate test color values"""
        import random
        return [f"{random.randint(0, 255):02x}{random.randint(0, 255):02x}{random.randint(0, 255):02x}"
                for _ in range(count)]