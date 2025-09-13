"""
Mock objects and contexts for testing.

Provides mock converters, contexts, and other test doubles.
"""
from lxml import etree as ET
from typing import Dict, Any

import pytest


@pytest.fixture
def mock_conversion_context():
    """Mock conversion context for testing converters.
    
    Returns:
        Configured ConversionContext instance for testing.
    """
    from src.context import ConversionContext
    
    context = ConversionContext()
    context.shape_id_counter = 1000
    context.coordinate_system = None
    context.gradients = {}
    context.patterns = {}
    context.clips = {}
    context.fonts = {}
    
    return context


@pytest.fixture
def mock_svg_element() -> ET.Element:
    """Create a mock SVG element for testing.
    
    Returns:
        lxml Element representing a simple SVG rectangle.
    """
    root = ET.fromstring('''
    <rect x="10" y="10" width="50" height="30" 
          fill="red" stroke="blue" stroke-width="2"
          transform="translate(5,5)"/>
    ''')
    return root


@pytest.fixture
def mock_converter_output() -> str:
    """Mock DrawingML output from a converter.
    
    Returns:
        String containing sample DrawingML XML.
    """
    return '''<p:sp>
    <p:nvSpPr>
        <p:cNvPr id="1001" name="Rectangle"/>
        <p:cNvSpPr/>
        <p:nvPr/>
    </p:nvSpPr>
    <p:spPr>
        <a:xfrm>
            <a:off x="914400" y="914400"/>
            <a:ext cx="4572000" cy="2743200"/>
        </a:xfrm>
        <a:prstGeom prst="rect"/>
        <a:solidFill>
            <a:srgbClr val="FF0000"/>
        </a:solidFill>
    </p:spPr>
</p:sp>'''


@pytest.fixture
def mock_presentation():
    """Create a mock PowerPoint presentation object.
    
    Returns:
        Mock presentation object for testing.
    """
    from unittest.mock import Mock, MagicMock
    
    presentation = Mock()
    presentation.slides = MagicMock()
    presentation.slide_width = 9144000  # 10 inches in EMU
    presentation.slide_height = 6858000  # 7.5 inches in EMU
    
    # Add mock slide
    slide = Mock()
    slide.shapes = MagicMock()
    presentation.slides.add_slide = MagicMock(return_value=slide)
    
    return presentation


@pytest.fixture
def mock_svg_document():
    """Create a mock SVG document tree.
    
    Returns:
        lxml ElementTree representing a complete SVG document.
    """
    svg_content = '''<?xml version="1.0" encoding="UTF-8"?>
    <svg width="100" height="100" viewBox="0 0 100 100" 
         xmlns="http://www.w3.org/2000/svg">
        <g id="layer1">
            <rect x="10" y="10" width="30" height="20" fill="red"/>
            <circle cx="50" cy="50" r="20" fill="blue"/>
        </g>
    </svg>'''
    
    return ET.fromstring(svg_content)


@pytest.fixture
def mock_style_parser():
    """Create a mock style parser.
    
    Returns:
        Mock style parser for testing style processing.
    """
    from unittest.mock import Mock
    
    parser = Mock()
    parser.parse = Mock(return_value={
        'fill': 'red',
        'stroke': 'blue',
        'stroke-width': '2',
        'opacity': '0.8'
    })
    
    return parser


@pytest.fixture
def mock_coordinate_system():
    """Create a mock coordinate system.
    
    Returns:
        Mock coordinate system for testing transformations.
    """
    from unittest.mock import Mock
    
    coord_system = Mock()
    coord_system.transform_point = Mock(side_effect=lambda x, y: (x * 914400, y * 914400))
    coord_system.transform_length = Mock(side_effect=lambda l: l * 914400)
    coord_system.viewport_width = 100
    coord_system.viewport_height = 100
    
    return coord_system


@pytest.fixture
def mock_batch_job_data() -> Dict[str, Any]:
    """Create mock batch job data for testing.
    
    Returns:
        Dictionary containing sample batch job data.
    """
    return {
        "job_id": "test-job-123",
        "status": "pending",
        "input_files": ["file1.svg", "file2.svg"],
        "output_format": "pptx",
        "created_at": "2025-01-01T00:00:00Z",
        "metadata": {
            "user_id": "test-user",
            "project": "test-project"
        }
    }