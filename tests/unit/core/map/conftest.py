#!/usr/bin/env python3
"""
Mapper Test Fixtures

Provides specialized fixtures for testing IR mapper components.
"""

import pytest
from typing import Dict, Any, List
from unittest.mock import Mock, MagicMock
from lxml import etree as ET

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
    from core.map import PathMapper, TextMapper, GroupMapper, ImageMapper
    from core.map.base import Mapper, MapperResult, OutputFormat, MappingError
    from core.policy import Policy, PolicyDecision, PathDecision, TextDecision
    from core.ir import Path, TextFrame, Group, Image, Point, SolidPaint
    CORE_MAP_AVAILABLE = True
except ImportError:
    CORE_MAP_AVAILABLE = False


class MapperTestBase(IRTestBase):
    """Base class for mapper testing with specialized assertions"""

    def assert_mapper_result_valid(self, result: 'MapperResult'):
        """Assert that a MapperResult is valid"""
        if not CORE_MAP_AVAILABLE:
            pytest.skip("Core mapper components not available")

        assert result is not None
        assert hasattr(result, 'element')
        assert hasattr(result, 'output_format')
        assert hasattr(result, 'xml_content')
        assert hasattr(result, 'policy_decision')

        # Validate XML content
        assert isinstance(result.xml_content, str)
        assert len(result.xml_content) > 0

        # Basic XML validation
        try:
            ET.fromstring(result.xml_content.encode('utf-8'))
        except ET.XMLSyntaxError as e:
            pytest.fail(f"Invalid XML in mapper result: {e}")

    def assert_drawingml_structure(self, xml_content: str):
        """Assert that XML has proper DrawingML structure"""
        assert '<p:sp>' in xml_content or '<p:pic>' in xml_content, "Missing shape or picture element"

        if '<p:sp>' in xml_content:
            assert '<p:spPr>' in xml_content, "Missing shape properties"
            assert '<a:xfrm>' in xml_content, "Missing transform"

        if '<p:pic>' in xml_content:
            assert '<p:blipFill>' in xml_content, "Missing picture fill"

    def assert_performance_acceptable(self, result: 'MapperResult', max_time_ms: float = 100.0):
        """Assert that mapper performance is acceptable"""
        if hasattr(result, 'processing_time_ms'):
            assert result.processing_time_ms <= max_time_ms, \
                f"Mapper took {result.processing_time_ms}ms, expected <= {max_time_ms}ms"


@pytest.fixture
def mapper_test_base():
    """Provide mapper test base class instance"""
    return MapperTestBase()


@pytest.fixture
def mock_policy_engine():
    """Mock policy engine for mapper testing"""
    policy = Mock(spec=Policy)

    # Create mock decisions for different element types
    path_decision = Mock(spec=PathDecision)
    path_decision.use_native = True
    path_decision.estimated_quality = 0.95
    path_decision.estimated_performance = 0.9
    path_decision.reasoning = "Simple path, use native DrawingML"
    path_decision.to_dict.return_value = {
        'use_native': True,
        'quality': 0.95,
        'performance': 0.9,
        'reasoning': 'Simple path, use native DrawingML'
    }

    text_decision = Mock(spec=TextDecision)
    text_decision.use_native = True
    text_decision.estimated_quality = 0.98
    text_decision.estimated_performance = 0.95
    text_decision.reasoning = "Simple text, use native text frame"

    # Configure policy methods
    policy.decide_path.return_value = path_decision
    policy.decide_text.return_value = text_decision
    policy.decide_group.return_value = path_decision  # Reuse for simplicity
    policy.decide_image.return_value = path_decision

    return policy


@pytest.fixture
def mock_path_system():
    """Mock existing PathSystem for integration testing"""
    path_system = Mock()

    # Mock successful path processing
    mock_result = Mock()
    mock_result.success = True
    mock_result.path_xml = '<a:custGeom><a:pathLst><a:path w="21600" h="21600"><a:moveTo><a:pt x="0" y="0"/></a:moveTo><a:lnTo><a:pt x="21600" y="21600"/></a:lnTo></a:path></a:pathLst></a:custGeom>'

    path_system.process_path.return_value = mock_result

    return path_system


@pytest.fixture
def sample_mapper_inputs():
    """Sample IR elements for mapper testing"""
    if not CORE_MAP_AVAILABLE:
        pytest.skip("Core mapper components not available")

    from core.ir import LineSegment, Run, TextAnchor

    return {
        'simple_path': Path(
            segments=[
                LineSegment(start=Point(0, 0), end=Point(10, 10)),
                LineSegment(start=Point(10, 10), end=Point(20, 0)),
                LineSegment(start=Point(20, 0), end=Point(0, 0))
            ],
            fill=SolidPaint(color="ff0000"),
            stroke=None,
            is_closed=True,
            data="M 0 0 L 10 10 L 20 0 Z"
        ),
        'simple_text': TextFrame(
            runs=[
                Run(content="Hello World", font_family="Arial", font_size_pt=12, color="000000")
            ],
            x=10, y=20,
            width=100, height=20,
            anchor=TextAnchor.TOP_LEFT
        ),
        'simple_group': Group(
            children=[],  # Children would be provided separately
            transform="translate(10, 20)",
            opacity=0.8
        ),
        'simple_image': Image(
            href="test.png",
            x=0, y=0,
            width=100, height=100,
            preserve_aspect_ratio=True
        )
    }


@pytest.fixture
def complex_mapper_inputs():
    """Complex IR elements for advanced mapper testing"""
    if not CORE_MAP_AVAILABLE:
        pytest.skip("Core mapper components not available")

    from core.ir import (
        BezierSegment, LinearGradientPaint, GradientStop,
        Stroke, StrokeJoin, StrokeCap, Run
    )

    # Complex path with curves and gradient fill
    complex_path = Path(
        segments=[
            LineSegment(start=Point(0, 0), end=Point(25, 0)),
            BezierSegment(
                start=Point(25, 0),
                control1=Point(35, 10),
                control2=Point(45, 10),
                end=Point(55, 0)
            ),
            LineSegment(start=Point(55, 0), end=Point(55, 30)),
            LineSegment(start=Point(55, 30), end=Point(0, 30)),
            LineSegment(start=Point(0, 30), end=Point(0, 0))
        ],
        fill=LinearGradientPaint(
            stops=[
                GradientStop(position=0.0, color="ff0000"),
                GradientStop(position=1.0, color="0000ff")
            ],
            angle=45.0,
            x1=0, y1=0, x2=100, y2=100
        ),
        stroke=Stroke(
            paint=SolidPaint(color="000000"),
            width=2.0,
            cap=StrokeCap.ROUND,
            join=StrokeJoin.ROUND,
            dash_array=[5, 3]
        ),
        is_closed=True,
        data="M 0 0 L 25 0 C 35 10, 45 10, 55 0 L 55 30 L 0 30 Z"
    )

    # Multi-style text
    complex_text = TextFrame(
        runs=[
            Run(content="Bold ", font_family="Arial", font_size_pt=14, color="000000", bold=True),
            Run(content="Italic ", font_family="Arial", font_size_pt=12, color="ff0000", italic=True),
            Run(content="Normal", font_family="Times", font_size_pt=10, color="0000ff")
        ],
        x=50, y=60,
        width=200, height=40
    )

    return {
        'complex_path': complex_path,
        'complex_text': complex_text
    }


@pytest.fixture
def edge_case_mapper_inputs():
    """Edge case IR elements for robustness testing"""
    if not CORE_MAP_AVAILABLE:
        pytest.skip("Core mapper components not available")

    return {
        'empty_path': Path(
            segments=[],
            fill=None,
            stroke=None,
            is_closed=False,
            data=""
        ),
        'zero_dimension_image': Image(
            href="test.png",
            x=0, y=0,
            width=0, height=0
        ),
        'empty_text': TextFrame(
            runs=[],
            x=0, y=0,
            width=0, height=0
        ),
        'huge_coordinates': Path(
            segments=[
                LineSegment(start=Point(-1e6, -1e6), end=Point(1e6, 1e6))
            ],
            data="M -1000000 -1000000 L 1000000 1000000"
        )
    }


@pytest.fixture
def performance_test_elements():
    """Large number of elements for performance testing"""
    if not CORE_MAP_AVAILABLE:
        pytest.skip("Core mapper components not available")

    elements = []

    # Create 100 simple paths
    for i in range(100):
        x = (i % 10) * 20
        y = (i // 10) * 20

        path = Path(
            segments=[
                LineSegment(start=Point(x, y), end=Point(x+10, y+10))
            ],
            fill=SolidPaint(color=f"{i % 256:02x}0000"),
            data=f"M {x} {y} L {x+10} {y+10}"
        )
        elements.append(path)

    return elements


@pytest.fixture
def mapper_factories(mock_policy_engine, mock_path_system):
    """Factory functions for creating mappers"""
    if not CORE_MAP_AVAILABLE:
        pytest.skip("Core mapper components not available")

    def create_path_mapper(with_path_system=True):
        path_system = mock_path_system if with_path_system else None
        return PathMapper(mock_policy_engine, path_system)

    def create_text_mapper():
        return TextMapper(mock_policy_engine)

    def create_group_mapper():
        return GroupMapper(mock_policy_engine)

    def create_image_mapper():
        return ImageMapper(mock_policy_engine)

    return {
        'path': create_path_mapper,
        'text': create_text_mapper,
        'group': create_group_mapper,
        'image': create_image_mapper
    }


@pytest.fixture
def svg_to_ir_test_data():
    """Sample SVG elements for testing SVG to IR conversion"""
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
    group.set('transform', 'translate(10, 20) rotate(45)')
    elements['group'] = group

    # Image element
    image = ET.Element('image')
    image.set('x', '0')
    image.set('y', '0')
    image.set('width', '100')
    image.set('height', '100')
    image.set('href', 'test.png')
    elements['image'] = image

    return elements


# Utility functions for mapper testing
def validate_mapper_xml_output(xml_content: str, expected_elements: List[str]) -> bool:
    """Validate that mapper XML output contains expected elements"""
    for element in expected_elements:
        if element not in xml_content:
            return False
    return True


def measure_mapper_performance(mapper: 'Mapper', element, iterations: int = 10) -> Dict[str, float]:
    """Measure mapper performance across multiple iterations"""
    import time

    times = []
    for _ in range(iterations):
        start_time = time.perf_counter()
        result = mapper.map(element)
        end_time = time.perf_counter()
        times.append((end_time - start_time) * 1000)

    return {
        'avg_time_ms': sum(times) / len(times),
        'min_time_ms': min(times),
        'max_time_ms': max(times),
        'std_dev_ms': (sum((t - sum(times)/len(times))**2 for t in times) / len(times))**0.5
    }


def create_mock_mapper_result(element, output_format: 'OutputFormat' = None) -> Mock:
    """Create mock MapperResult for testing"""
    if not CORE_MAP_AVAILABLE:
        return Mock()

    result = Mock(spec=MapperResult)
    result.element = element
    result.output_format = output_format or OutputFormat.NATIVE_DML
    result.xml_content = '<p:sp><p:nvSpPr><p:cNvPr id="1" name="Test"/></p:nvSpPr><p:spPr></p:spPr></p:sp>'
    result.policy_decision = Mock()
    result.metadata = {}
    result.estimated_quality = 0.95
    result.estimated_performance = 0.9
    result.output_size_bytes = len(result.xml_content)
    result.processing_time_ms = 5.0

    return result