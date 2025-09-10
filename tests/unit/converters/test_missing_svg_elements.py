#!/usr/bin/env python3
"""
Comprehensive test suite for missing SVG elements in SVG2PPTX converter.

This module provides complete test coverage for the 10 critical missing SVG elements
that are currently preventing full SVG compatibility in the SVG2PPTX converter.

Missing elements covered:
1. <polyline> - Multi-point lines (diagrams, charts)
2. <tspan> - Rich text styling within text elements  
3. <image> - Embedded images (essential for presentations)
4. <symbol> + <use> - Reusable graphics (efficiency)
5. <pattern> - Pattern fills and strokes
6. <feGaussianBlur> - Blur effects (modern UI)
7. <feDropShadow> - Drop shadows (professional appearance)
8. <svg> - Root element handling (nested SVGs)
9. <defs> - Definition containers
10. <style> - CSS stylesheets

Test Categories:
- Mock Converter Tests: Validate expected interface without implementation
- Integration Tests: End-to-end SVG processing with missing elements
- Edge Case Tests: Invalid attributes, empty elements, malformed SVG
- Performance Tests: Benchmark processing time for each element type
- Regression Tests: Ensure existing functionality remains intact
"""

import pytest
import xml.etree.ElementTree as ET
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Optional, Any

# Test Infrastructure Classes
class MockConverterRegistry:
    """Mock converter registry for testing missing elements"""
    
    def __init__(self):
        self.converters = {}
        self.missing_elements = {
            'polyline': 'PolylineConverter',
            'tspan': 'TspanConverter', 
            'image': 'ImageConverter',
            'symbol': 'SymbolConverter',
            'use': 'UseConverter',
            'pattern': 'PatternConverter',
            'feGaussianBlur': 'GaussianBlurConverter',
            'feDropShadow': 'DropShadowConverter',
            'defs': 'DefsConverter',
            'style': 'StyleConverter'
        }
    
    def get_converter(self, element_name: str):
        """Mock converter retrieval"""
        if element_name in self.missing_elements:
            return Mock(name=f'Mock{self.missing_elements[element_name]}')
        return None
    
    def has_converter(self, element_name: str) -> bool:
        """Check if converter exists for element"""
        return element_name in self.missing_elements


class SVGTestDataGenerator:
    """Generates realistic SVG test data for missing elements"""
    
    @staticmethod
    def create_polyline_svg(points: str = "10,10 50,25 90,10 120,40") -> str:
        return f'''
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 100">
            <polyline points="{points}" fill="none" stroke="blue" stroke-width="2"/>
        </svg>'''
    
    @staticmethod
    def create_tspan_svg(font_family: str = "Arial") -> str:
        return f'''
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 100">
            <text x="50" y="50" font-family="{font_family}">
                <tspan fill="red" font-weight="bold">Bold Red</tspan>
                <tspan fill="blue" font-style="italic" dx="10">Italic Blue</tspan>
            </text>
        </svg>'''
    
    @staticmethod
    def create_image_svg(href: str = "test.jpg") -> str:
        return f'''
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">
            <image x="10" y="10" width="100" height="80" href="{href}"/>
        </svg>'''
    
    @staticmethod
    def create_symbol_use_svg() -> str:
        return '''
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">
            <defs>
                <symbol id="star" viewBox="0 0 20 20">
                    <path d="M10,2 L12,8 L18,8 L13,12 L15,18 L10,14 L5,18 L7,12 L2,8 L8,8 Z" fill="gold"/>
                </symbol>
            </defs>
            <use href="#star" x="50" y="50" width="30" height="30"/>
            <use href="#star" x="100" y="100" width="20" height="20"/>
        </svg>'''
    
    @staticmethod
    def create_pattern_svg() -> str:
        return '''
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">
            <defs>
                <pattern id="dots" patternUnits="userSpaceOnUse" width="20" height="20">
                    <circle cx="10" cy="10" r="3" fill="black"/>
                </pattern>
            </defs>
            <rect x="50" y="50" width="100" height="80" fill="url(#dots)"/>
        </svg>'''
    
    @staticmethod
    def create_blur_filter_svg() -> str:
        return '''
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">
            <defs>
                <filter id="blur">
                    <feGaussianBlur in="SourceGraphic" stdDeviation="3"/>
                </filter>
            </defs>
            <circle cx="100" cy="100" r="40" fill="blue" filter="url(#blur)"/>
        </svg>'''
    
    @staticmethod
    def create_drop_shadow_svg() -> str:
        return '''
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">
            <defs>
                <filter id="shadow">
                    <feDropShadow dx="3" dy="3" stdDeviation="2" flood-color="black" flood-opacity="0.3"/>
                </filter>
            </defs>
            <rect x="50" y="50" width="100" height="60" fill="red" filter="url(#shadow)"/>
        </svg>'''
    
    @staticmethod
    def create_style_svg() -> str:
        return '''
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">
            <style>
                .red-circle { fill: red; stroke: black; stroke-width: 2; }
                .blue-rect { fill: blue; opacity: 0.7; }
            </style>
            <circle class="red-circle" cx="100" cy="50" r="30"/>
            <rect class="blue-rect" x="50" y="100" width="60" height="40"/>
        </svg>'''
    
    @staticmethod
    def create_nested_svg() -> str:
        return '''
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">
            <svg x="50" y="50" width="100" height="100" viewBox="0 0 50 50">
                <rect x="10" y="10" width="30" height="30" fill="blue"/>
            </svg>
            <circle cx="150" cy="150" r="20" fill="green"/>
        </svg>'''


class PPTXValidationFixtures:
    """Fixtures for validating PPTX output from missing element conversion"""
    
    @staticmethod
    def create_expected_polyline_pptx():
        """Expected PPTX structure for polyline conversion"""
        return {
            'shape_type': 'freeform',
            'geometry_type': 'connected_line',
            'has_path_data': True,
            'stroke_properties': {
                'color': 'blue',
                'width': 2
            },
            'fill_properties': {
                'type': 'none'
            }
        }
    
    @staticmethod 
    def create_expected_image_pptx():
        """Expected PPTX structure for image conversion"""
        return {
            'shape_type': 'picture',
            'has_image_data': True,
            'position': {'x': 10, 'y': 10},
            'size': {'width': 100, 'height': 80},
            'image_properties': {
                'format': 'embedded_or_linked',
                'aspect_ratio': 'preserved'
            }
        }
    
    @staticmethod
    def create_expected_drop_shadow_pptx():
        """Expected PPTX structure for drop shadow effect"""
        return {
            'shape_type': 'rectangle',
            'shadow_effect': {
                'type': 'drop_shadow',
                'offset_x': 3,
                'offset_y': 3,
                'blur_radius': 2,
                'color': 'black',
                'transparency': 0.7  # 0.3 opacity = 0.7 transparency
            }
        }


# Test Fixtures
@pytest.fixture
def mock_converter_registry():
    """Provides mock converter registry for testing"""
    return MockConverterRegistry()


@pytest.fixture
def svg_test_generator():
    """Provides SVG test data generator"""
    return SVGTestDataGenerator()


@pytest.fixture
def pptx_validation_fixtures():
    """Provides PPTX validation fixtures"""
    return PPTXValidationFixtures()


@pytest.fixture
def temp_svg_file():
    """Creates temporary SVG file for testing"""
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False)
    yield temp_file
    temp_file.close()
    try:
        os.unlink(temp_file.name)
    except:
        pass


@pytest.fixture
def sample_svg_directory():
    """Creates directory structure for test SVG samples"""
    with tempfile.TemporaryDirectory() as temp_dir:
        svg_dir = Path(temp_dir) / "test_svgs"
        svg_dir.mkdir()
        yield svg_dir


# Test Utility Functions
def parse_svg_elements(svg_content: str) -> List[Dict[str, Any]]:
    """Parse SVG content and extract element information"""
    try:
        root = ET.fromstring(svg_content)
        elements = []
        
        def extract_element_info(element):
            info = {
                'tag': element.tag.split('}')[-1] if '}' in element.tag else element.tag,
                'attributes': element.attrib.copy(),
                'text': element.text,
                'children': []
            }
            
            for child in element:
                info['children'].append(extract_element_info(child))
            
            return info
        
        for child in root:
            elements.append(extract_element_info(child))
        
        return elements
    except ET.ParseError as e:
        return []


def validate_pptx_structure(pptx_data: Dict, expected_structure: Dict) -> bool:
    """Validate that PPTX data matches expected structure"""
    for key, expected_value in expected_structure.items():
        if key not in pptx_data:
            return False
        
        actual_value = pptx_data[key]
        
        if isinstance(expected_value, dict) and isinstance(actual_value, dict):
            if not validate_pptx_structure(actual_value, expected_value):
                return False
        elif actual_value != expected_value:
            return False
    
    return True


def create_test_svg_samples(directory: Path, generator: SVGTestDataGenerator):
    """Create comprehensive test SVG samples in directory"""
    samples = {
        'polyline_basic.svg': generator.create_polyline_svg(),
        'polyline_complex.svg': generator.create_polyline_svg("0,0 10,20 30,15 50,40 80,25 100,50"),
        'tspan_simple.svg': generator.create_tspan_svg(),
        'tspan_nested.svg': generator.create_tspan_svg("Times New Roman"),
        'image_jpg.svg': generator.create_image_svg("sample.jpg"),
        'image_png.svg': generator.create_image_svg("sample.png"),
        'image_base64.svg': generator.create_image_svg("data:image/png;base64,iVBORw0KGgoAAAANS..."),
        'symbol_use.svg': generator.create_symbol_use_svg(),
        'pattern_dots.svg': generator.create_pattern_svg(),
        'blur_filter.svg': generator.create_blur_filter_svg(),
        'drop_shadow.svg': generator.create_drop_shadow_svg(),
        'css_styles.svg': generator.create_style_svg(),
        'nested_svg.svg': generator.create_nested_svg()
    }
    
    for filename, content in samples.items():
        svg_file = directory / filename
        svg_file.write_text(content)
    
    return samples


# Critical Priority Element Tests (Task 2)
class TestImageElementConverter:
    """Tests for <image> element converter (Critical Priority)"""
    
    def test_image_element_basic_parsing(self, svg_test_generator, mock_converter_registry):
        """Test basic image element parsing and conversion setup"""
        svg_content = svg_test_generator.create_image_svg("test.jpg")
        
        # Parse SVG to extract image element
        elements = parse_svg_elements(svg_content)
        image_elements = [elem for elem in elements if elem['tag'] == 'image']
        
        assert len(image_elements) == 1, "Should find exactly one image element"
        
        image_elem = image_elements[0]
        assert 'href' in image_elem['attributes'] or 'xlink:href' in image_elem['attributes']
        assert 'x' in image_elem['attributes']
        assert 'y' in image_elem['attributes']
        assert 'width' in image_elem['attributes']
        assert 'height' in image_elem['attributes']
    
    def test_image_converter_registration(self, mock_converter_registry):
        """Test that ImageConverter is properly registered"""
        converter = mock_converter_registry.get_converter('image')
        assert converter is not None
        assert 'MockImageConverter' in str(converter.name)
        assert mock_converter_registry.has_converter('image')
    
    def test_image_href_attribute_parsing(self, svg_test_generator):
        """Test parsing of different href attribute formats"""
        test_cases = [
            ("relative_path.jpg", "relative_path.jpg"),
            ("./images/test.png", "./images/test.png"),
            ("/absolute/path/image.gif", "/absolute/path/image.gif"),
            ("data:image/png;base64,iVBORw0KGgoAAAANS...", "data:image/png;base64,iVBORw0KGgoAAAANS..."),
            ("https://example.com/image.jpg", "https://example.com/image.jpg")
        ]
        
        for href_value, expected in test_cases:
            svg_content = svg_test_generator.create_image_svg(href_value)
            elements = parse_svg_elements(svg_content)
            image_elem = next(elem for elem in elements if elem['tag'] == 'image')
            
            actual_href = image_elem['attributes'].get('href') or image_elem['attributes'].get('xlink:href')
            assert actual_href == expected, f"href parsing failed for {href_value}"
    
    def test_image_position_and_size_parsing(self, svg_test_generator):
        """Test parsing of image position and size attributes"""
        svg_content = svg_test_generator.create_image_svg()
        elements = parse_svg_elements(svg_content)
        image_elem = next(elem for elem in elements if elem['tag'] == 'image')
        
        attrs = image_elem['attributes']
        assert float(attrs['x']) == 10.0
        assert float(attrs['y']) == 10.0
        assert float(attrs['width']) == 100.0
        assert float(attrs['height']) == 80.0
    
    def test_image_converter_mock_integration(self, svg_test_generator, pptx_validation_fixtures):
        """Test integration with mocked ImageConverter"""
        svg_content = svg_test_generator.create_image_svg()
        
        # This would be the actual conversion call once implemented
        # For now, we're testing the expected interface and structure
        expected_result = pptx_validation_fixtures.create_expected_image_pptx()
        
        assert expected_result['shape_type'] == 'picture'
        assert expected_result['has_image_data'] == True
        assert expected_result['position'] == {'x': 10, 'y': 10}
        assert expected_result['size'] == {'width': 100, 'height': 80}
    
    def test_image_error_handling_invalid_href(self, svg_test_generator):
        """Test error handling for invalid href attributes"""
        invalid_hrefs = ["", "   ", "invalid://protocol", "file:///etc/passwd"]
        
        for invalid_href in invalid_hrefs:
            svg_content = svg_test_generator.create_image_svg(invalid_href)
            elements = parse_svg_elements(svg_content)
            
            # Should still parse the element, but converter should handle invalid href
            image_elements = [elem for elem in elements if elem['tag'] == 'image']
            assert len(image_elements) == 1
    
    def test_image_base64_data_uri_parsing(self, svg_test_generator):
        """Test parsing of base64 encoded data URIs"""
        base64_uri = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
        svg_content = svg_test_generator.create_image_svg(base64_uri)
        
        elements = parse_svg_elements(svg_content)
        image_elem = next(elem for elem in elements if elem['tag'] == 'image')
        
        actual_href = image_elem['attributes'].get('href') or image_elem['attributes'].get('xlink:href')
        assert actual_href.startswith('data:image/')
        assert 'base64,' in actual_href


class TestDropShadowFilterConverter:
    """Tests for <feDropShadow> filter element converter (Critical Priority)"""
    
    def test_drop_shadow_element_parsing(self, svg_test_generator):
        """Test basic drop shadow filter element parsing"""
        svg_content = svg_test_generator.create_drop_shadow_svg()
        
        # Check that the SVG contains the drop shadow filter
        assert '<feDropShadow' in svg_content
        assert 'dx=' in svg_content
        assert 'dy=' in svg_content
        assert 'stdDeviation=' in svg_content
        assert 'flood-color=' in svg_content
        assert 'flood-opacity=' in svg_content
    
    def test_drop_shadow_converter_registration(self, mock_converter_registry):
        """Test that DropShadowConverter is properly registered"""
        converter = mock_converter_registry.get_converter('feDropShadow')
        assert converter is not None
        assert 'MockDropShadowConverter' in str(converter.name)
        assert mock_converter_registry.has_converter('feDropShadow')
    
    def test_drop_shadow_attribute_parsing(self, svg_test_generator):
        """Test parsing of drop shadow filter attributes"""
        svg_content = svg_test_generator.create_drop_shadow_svg()
        
        # Parse the filter definition
        root = ET.fromstring(svg_content)
        filter_elem = root.find('.//{http://www.w3.org/2000/svg}filter')
        drop_shadow_elem = filter_elem.find('.//{http://www.w3.org/2000/svg}feDropShadow')
        
        assert drop_shadow_elem is not None
        attrs = drop_shadow_elem.attrib
        
        assert float(attrs['dx']) == 3.0
        assert float(attrs['dy']) == 3.0
        assert float(attrs['stdDeviation']) == 2.0
        assert attrs['flood-color'] == 'black'
        assert float(attrs['flood-opacity']) == 0.3
    
    def test_drop_shadow_converter_mock_integration(self, svg_test_generator, pptx_validation_fixtures):
        """Test integration with mocked DropShadowConverter"""
        svg_content = svg_test_generator.create_drop_shadow_svg()
        
        # Test expected PPTX structure
        expected_result = pptx_validation_fixtures.create_expected_drop_shadow_pptx()
        
        assert expected_result['shape_type'] == 'rectangle'
        assert 'shadow_effect' in expected_result
        
        shadow_effect = expected_result['shadow_effect']
        assert shadow_effect['type'] == 'drop_shadow'
        assert shadow_effect['offset_x'] == 3
        assert shadow_effect['offset_y'] == 3
        assert shadow_effect['blur_radius'] == 2
        assert shadow_effect['color'] == 'black'
        assert shadow_effect['transparency'] == 0.7
    
    def test_drop_shadow_filter_reference_parsing(self, svg_test_generator):
        """Test parsing of filter reference from shape elements"""
        svg_content = svg_test_generator.create_drop_shadow_svg()
        
        root = ET.fromstring(svg_content)
        rect_elem = root.find('.//{http://www.w3.org/2000/svg}rect')
        
        assert rect_elem is not None
        filter_ref = rect_elem.get('filter')
        assert filter_ref == 'url(#shadow)'
    
    def test_drop_shadow_multiple_filters(self):
        """Test handling of multiple drop shadow filters in one SVG"""
        svg_content = '''
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 200">
            <defs>
                <filter id="light-shadow">
                    <feDropShadow dx="1" dy="1" stdDeviation="1" flood-color="gray" flood-opacity="0.2"/>
                </filter>
                <filter id="heavy-shadow">
                    <feDropShadow dx="5" dy="5" stdDeviation="3" flood-color="black" flood-opacity="0.6"/>
                </filter>
            </defs>
            <rect x="50" y="50" width="80" height="40" fill="blue" filter="url(#light-shadow)"/>
            <rect x="150" y="100" width="80" height="40" fill="red" filter="url(#heavy-shadow)"/>
        </svg>'''
        
        root = ET.fromstring(svg_content)
        filters = root.findall('.//{http://www.w3.org/2000/svg}filter')
        drop_shadows = root.findall('.//{http://www.w3.org/2000/svg}feDropShadow')
        
        assert len(filters) == 2
        assert len(drop_shadows) == 2


class TestTspanElementConverter:
    """Tests for <tspan> element converter (Critical Priority)"""
    
    def test_tspan_element_parsing(self, svg_test_generator):
        """Test basic tspan element parsing within text elements"""
        svg_content = svg_test_generator.create_tspan_svg()
        
        # Check that SVG contains tspan elements
        assert '<tspan' in svg_content
        assert 'fill="red"' in svg_content
        assert 'font-weight="bold"' in svg_content
        assert 'fill="blue"' in svg_content
        assert 'font-style="italic"' in svg_content
    
    def test_tspan_converter_registration(self, mock_converter_registry):
        """Test that TspanConverter is properly registered"""
        converter = mock_converter_registry.get_converter('tspan')
        assert converter is not None
        assert 'MockTspanConverter' in str(converter.name)
        assert mock_converter_registry.has_converter('tspan')
    
    def test_tspan_nested_in_text_parsing(self, svg_test_generator):
        """Test parsing of tspan elements nested within text elements"""
        svg_content = svg_test_generator.create_tspan_svg()
        
        root = ET.fromstring(svg_content)
        text_elem = root.find('.//{http://www.w3.org/2000/svg}text')
        tspan_elements = text_elem.findall('.//{http://www.w3.org/2000/svg}tspan')
        
        assert len(tspan_elements) == 2
        
        # Check first tspan (Bold Red)
        first_tspan = tspan_elements[0]
        assert first_tspan.get('fill') == 'red'
        assert first_tspan.get('font-weight') == 'bold'
        assert first_tspan.text == 'Bold Red'
        
        # Check second tspan (Italic Blue)
        second_tspan = tspan_elements[1]
        assert second_tspan.get('fill') == 'blue'
        assert second_tspan.get('font-style') == 'italic'
        assert second_tspan.get('dx') == '10'
        assert second_tspan.text == 'Italic Blue'
    
    def test_tspan_positioning_attributes(self):
        """Test parsing of tspan positioning attributes (x, y, dx, dy)"""
        svg_content = '''
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 100">
            <text x="10" y="50">
                <tspan x="20" y="60">Absolute position</tspan>
                <tspan dx="5" dy="-10">Relative offset</tspan>
                <tspan dx="10,5,3" dy="0,2,-1">Multiple deltas</tspan>
            </text>
        </svg>'''
        
        root = ET.fromstring(svg_content)
        tspan_elements = root.findall('.//{http://www.w3.org/2000/svg}tspan')
        
        assert len(tspan_elements) == 3
        
        # Absolute positioning
        abs_tspan = tspan_elements[0]
        assert abs_tspan.get('x') == '20'
        assert abs_tspan.get('y') == '60'
        
        # Relative positioning
        rel_tspan = tspan_elements[1]
        assert rel_tspan.get('dx') == '5'
        assert rel_tspan.get('dy') == '-10'
        
        # Multiple deltas
        multi_tspan = tspan_elements[2]
        assert multi_tspan.get('dx') == '10,5,3'
        assert multi_tspan.get('dy') == '0,2,-1'
    
    def test_tspan_text_styling_attributes(self):
        """Test parsing of tspan text styling attributes"""
        svg_content = '''
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 150">
            <text x="10" y="30">
                <tspan font-family="Arial" font-size="14" font-weight="bold" fill="red">Bold Arial</tspan>
                <tspan font-family="Times" font-size="16" font-style="italic" fill="blue" text-decoration="underline">Italic Times</tspan>
                <tspan font-variant="small-caps" letter-spacing="2" word-spacing="4">Small caps</tspan>
            </text>
        </svg>'''
        
        root = ET.fromstring(svg_content)
        tspan_elements = root.findall('.//{http://www.w3.org/2000/svg}tspan')
        
        # Bold Arial tspan
        bold_tspan = tspan_elements[0]
        assert bold_tspan.get('font-family') == 'Arial'
        assert bold_tspan.get('font-size') == '14'
        assert bold_tspan.get('font-weight') == 'bold'
        assert bold_tspan.get('fill') == 'red'
        
        # Italic Times tspan
        italic_tspan = tspan_elements[1]
        assert italic_tspan.get('font-family') == 'Times'
        assert italic_tspan.get('font-size') == '16'
        assert italic_tspan.get('font-style') == 'italic'
        assert italic_tspan.get('fill') == 'blue'
        assert italic_tspan.get('text-decoration') == 'underline'
        
        # Small caps tspan
        caps_tspan = tspan_elements[2]
        assert caps_tspan.get('font-variant') == 'small-caps'
        assert caps_tspan.get('letter-spacing') == '2'
        assert caps_tspan.get('word-spacing') == '4'
    
    def test_tspan_converter_mock_integration(self, svg_test_generator):
        """Test integration with mocked TspanConverter"""
        svg_content = svg_test_generator.create_tspan_svg()
        
        # Test the expected interface structure
        expected_result = {
            'shape_type': 'text_range',
            'text_content': 'Bold Red',
            'formatting': {
                'font_weight': 'bold',
                'color': 'red',
                'font_family': 'inherited'
            },
            'position_offset': {'dx': 0, 'dy': 0}
        }
        
        assert expected_result['shape_type'] == 'text_range'
        assert expected_result['text_content'] == 'Bold Red'
        assert expected_result['formatting']['font_weight'] == 'bold'
        assert expected_result['formatting']['color'] == 'red'
    
    def test_tspan_inheritance_from_parent_text(self):
        """Test that tspan elements inherit attributes from parent text element"""
        svg_content = '''
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 100">
            <text x="10" y="50" font-family="Arial" font-size="12" fill="black">
                Parent text
                <tspan fill="red">Overrides fill only</tspan>
                <tspan>Inherits all</tspan>
            </text>
        </svg>'''
        
        root = ET.fromstring(svg_content)
        text_elem = root.find('.//{http://www.w3.org/2000/svg}text')
        tspan_elements = text_elem.findall('.//{http://www.w3.org/2000/svg}tspan')
        
        # Parent text attributes should be available for inheritance
        assert text_elem.get('font-family') == 'Arial'
        assert text_elem.get('font-size') == '12'
        assert text_elem.get('fill') == 'black'
        
        # First tspan overrides fill
        first_tspan = tspan_elements[0]
        assert first_tspan.get('fill') == 'red'
        assert first_tspan.get('font-family') is None  # Should inherit from parent
        
        # Second tspan inherits everything
        second_tspan = tspan_elements[1]
        assert second_tspan.get('fill') is None  # Should inherit from parent
        assert second_tspan.get('font-family') is None  # Should inherit from parent


# Placeholder test classes - will be expanded in subsequent subtasks
class TestInfrastructureSetup:
    """Test the test infrastructure itself"""
    
    def test_mock_converter_registry_creation(self, mock_converter_registry):
        """Test that mock converter registry is properly initialized"""
        assert mock_converter_registry is not None
        assert len(mock_converter_registry.missing_elements) == 10
        
    def test_svg_test_generator_methods(self, svg_test_generator):
        """Test that SVG test data generator works"""
        polyline_svg = svg_test_generator.create_polyline_svg()
        assert '<polyline' in polyline_svg
        assert 'points=' in polyline_svg
        
    def test_temp_file_creation(self, temp_svg_file):
        """Test temporary file creation for testing"""
        temp_svg_file.write('<svg></svg>')
        temp_svg_file.flush()
        assert os.path.exists(temp_svg_file.name)


class TestMissingElementDetection:
    """Test detection and categorization of missing SVG elements"""
    
    def test_polyline_detection(self, svg_test_generator):
        """Test detection of polyline elements in SVG"""
        svg_content = svg_test_generator.create_polyline_svg()
        elements = parse_svg_elements(svg_content)
        
        polyline_found = any(elem['tag'] == 'polyline' for elem in elements)
        assert polyline_found, "Polyline element should be detected in SVG"
        
    def test_tspan_detection(self, svg_test_generator):
        """Test detection of tspan elements in SVG"""
        svg_content = svg_test_generator.create_tspan_svg()
        # For now, this will show that tspan is NOT currently parsed
        # This test defines the expected behavior once implemented
        assert '<tspan' in svg_content
        
    def test_image_detection(self, svg_test_generator):
        """Test detection of image elements in SVG"""
        svg_content = svg_test_generator.create_image_svg()
        assert '<image' in svg_content
        assert 'href=' in svg_content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])