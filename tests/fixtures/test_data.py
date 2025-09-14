"""
Test data fixtures for SVG2PPTX testing.

Provides sample data, test cases, and validation utilities.
"""
from lxml import etree as ET
from typing import Dict, Any, List
import pytest


@pytest.fixture
def sample_element_attributes():
    """Sample element attributes for testing."""
    return {
        'x': '10',
        'y': '20',
        'width': '100',
        'height': '50',
        'fill': 'red',
        'stroke': 'blue',
        'stroke-width': '2',
        'transform': 'translate(5,5)'
    }


@pytest.fixture
def unit_test_svg_elements():
    """Common SVG elements for unit testing."""
    return {
        'rect': ET.fromstring('<rect x="10" y="10" width="50" height="30" fill="red"/>'),
        'circle': ET.fromstring('<circle cx="50" cy="50" r="25" fill="blue"/>'),
        'line': ET.fromstring('<line x1="0" y1="0" x2="100" y2="100" stroke="black"/>'),
        'path': ET.fromstring('<path d="M 10 10 L 90 90" stroke="green" fill="none"/>'),
        'text': ET.fromstring('<text x="50" y="50" fill="black">Hello</text>')
    }


@pytest.fixture
def converter_test_cases():
    """Test cases for different converter scenarios."""
    return {
        'simple_shapes': [
            '<rect x="10" y="10" width="50" height="30" fill="red"/>',
            '<circle cx="50" cy="50" r="25" fill="blue"/>',
            '<ellipse cx="50" cy="50" rx="30" ry="20" fill="green"/>',
            '<line x1="0" y1="0" x2="100" y2="100" stroke="black"/>'
        ],
        'complex_paths': [
            '<path d="M 10 10 L 90 90 Z" fill="red"/>',
            '<path d="M 20 80 C 40 10, 65 10, 95 80 S 150 150, 180 80" stroke="blue" fill="none"/>',
            '<path d="M 20 20 L 80 20 A 30 30 0 0 1 80 80 L 20 80 Z" fill="yellow"/>'
        ],
        'text_elements': [
            '<text x="50" y="50" fill="black">Simple Text</text>',
            '<text x="50" y="50"><tspan x="50" dy="0">Multi</tspan><tspan x="50" dy="20">Line</tspan></text>',
            '<text x="50" y="50" font-family="Arial" font-size="16" font-weight="bold">Styled Text</text>'
        ]
    }


@pytest.fixture
def expected_drawingml_outputs():
    """Expected DrawingML outputs for test validation."""
    return {
        'simple_rect': '''<p:sp>
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
</p:sp>''',
        'simple_circle': '''<p:sp>
    <p:nvSpPr>
        <p:cNvPr id="1002" name="Circle"/>
        <p:cNvSpPr/>
        <p:nvPr/>
    </p:nvSpPr>
    <p:spPr>
        <a:xfrm>
            <a:off x="2286000" y="2286000"/>
            <a:ext cx="2286000" cy="2286000"/>
        </a:xfrm>
        <a:prstGeom prst="ellipse"/>
        <a:solidFill>
            <a:srgbClr val="0000FF"/>
        </a:solidFill>
    </p:spPr>
</p:sp>'''
    }


@pytest.fixture
def converter_performance_data():
    """Performance benchmarking data for converter tests."""
    return {
        'expected_max_time': 0.1,  # 100ms max per element
        'expected_memory_limit': 10 * 1024 * 1024,  # 10MB max
        'batch_sizes': [1, 10, 50, 100],
        'complexity_levels': ['simple', 'medium', 'complex']
    }


@pytest.fixture
def svg_element_factory():
    """Factory for creating SVG elements for testing."""
    def _create_element(tag, **attributes):
        attrib_str = ' '.join(f'{k}="{v}"' for k, v in attributes.items())
        xml_str = f'<{tag} {attrib_str}/>'
        return ET.fromstring(xml_str)

    return _create_element


@pytest.fixture
def validate_drawingml():
    """Utility function to validate DrawingML output."""
    def _validate(xml_content: str):
        """Validate that XML content is proper DrawingML."""
        # Parse XML to ensure it's valid
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as e:
            pytest.fail(f"Invalid XML: {e}")

        # Check for required DrawingML structure
        if root.tag.endswith('sp'):  # Shape element
            # Should have nvSpPr and spPr children
            nvSpPr = root.find('.//{http://schemas.openxmlformats.org/presentationml/2006/main}nvSpPr')
            spPr = root.find('.//{http://schemas.openxmlformats.org/presentationml/2006/main}spPr')

            if nvSpPr is None and spPr is None:
                # Try without namespace (for test simplicity)
                nvSpPr = root.find('.//nvSpPr') or root.find('.//p:nvSpPr')
                spPr = root.find('.//spPr') or root.find('.//p:spPr')

            assert nvSpPr is not None, "Missing nvSpPr element in shape"
            assert spPr is not None, "Missing spPr element in shape"

        return True

    return _validate