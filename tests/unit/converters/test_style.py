"""
Test suite for StyleConverter.
Tests CSS parsing, selector matching, and style application.
"""

import pytest
from unittest.mock import Mock
from lxml import etree as ET

from src.converters.style import StyleConverter
from src.converters.base import ConversionContext


class TestStyleConverter:
    """Test suite for StyleConverter functionality."""
    
    @pytest.fixture
    def converter(self):
        """Create a StyleConverter instance."""
        return StyleConverter()
    
    @pytest.fixture
    def mock_context(self):
        """Create a mock ConversionContext."""
        context = Mock(spec=ConversionContext)
        context.css_styles = {}
        return context
    
    def test_can_convert_style_element(self, converter):
        """Test that converter can handle style elements."""
        element = ET.fromstring('<style>rect { fill: blue; }</style>')
        assert converter.can_convert(element) is True
        
        non_style = ET.fromstring('<rect/>')
        assert converter.can_convert(non_style) is False
    
    def test_basic_css_parsing(self, converter, mock_context):
        """Test basic CSS rule parsing."""
        css_content = """
        rect {
            fill: blue;
            stroke: red;
            stroke-width: 2px;
        }
        """
        element = ET.fromstring(f'<style>{css_content}</style>')
        
        result = converter.convert(element, mock_context)
        
        assert '<!-- Processed 1 CSS rules -->' in result
        assert 'rect' in mock_context.css_styles
        assert mock_context.css_styles['rect']['fill'] == 'blue'
        assert mock_context.css_styles['rect']['stroke'] == 'red'
        assert mock_context.css_styles['rect']['stroke-width'] == '2px'
    
    def test_multiple_selectors(self, converter, mock_context):
        """Test CSS with multiple selectors."""
        css_content = """
        rect, circle {
            fill: green;
        }
        ellipse {
            stroke: purple;
        }
        """
        element = ET.fromstring(f'<style>{css_content}</style>')
        
        converter.convert(element, mock_context)
        
        assert 'rect' in mock_context.css_styles
        assert 'circle' in mock_context.css_styles
        assert 'ellipse' in mock_context.css_styles
        assert mock_context.css_styles['rect']['fill'] == 'green'
        assert mock_context.css_styles['circle']['fill'] == 'green'
        assert mock_context.css_styles['ellipse']['stroke'] == 'purple'
    
    def test_class_selectors(self, converter, mock_context):
        """Test CSS class selectors."""
        css_content = """
        .highlight {
            fill: yellow;
            stroke: orange;
        }
        .border {
            stroke-width: 3px;
        }
        """
        element = ET.fromstring(f'<style>{css_content}</style>')
        
        converter.convert(element, mock_context)
        
        assert '.highlight' in mock_context.css_styles
        assert '.border' in mock_context.css_styles
        assert mock_context.css_styles['.highlight']['fill'] == 'yellow'
        assert mock_context.css_styles['.border']['stroke-width'] == '3px'
    
    def test_id_selectors(self, converter, mock_context):
        """Test CSS ID selectors."""
        css_content = """
        #header {
            font-size: 24px;
            font-weight: bold;
        }
        #footer {
            opacity: 0.5;
        }
        """
        element = ET.fromstring(f'<style>{css_content}</style>')
        
        converter.convert(element, mock_context)
        
        assert '#header' in mock_context.css_styles
        assert '#footer' in mock_context.css_styles
        assert mock_context.css_styles['#header']['font-size'] == '24px'
        assert mock_context.css_styles['#footer']['opacity'] == '0.5'
    
    def test_css_comments_removal(self, converter, mock_context):
        """Test that CSS comments are properly removed."""
        css_content = """
        /* This is a comment */
        rect {
            fill: blue; /* Another comment */
        }
        /* Multi-line
           comment */
        circle {
            stroke: red;
        }
        """
        element = ET.fromstring(f'<style>{css_content}</style>')
        
        converter.convert(element, mock_context)
        
        assert 'rect' in mock_context.css_styles
        assert 'circle' in mock_context.css_styles
        assert mock_context.css_styles['rect']['fill'] == 'blue'
        assert mock_context.css_styles['circle']['stroke'] == 'red'
    
    def test_empty_style_element(self, converter, mock_context):
        """Test handling of empty style elements."""
        element = ET.fromstring('<style></style>')
        
        result = converter.convert(element, mock_context)
        
        assert '<!-- Empty style element -->' in result
    
    def test_get_element_styles_type_selector(self, converter, mock_context):
        """Test getting styles for element with type selector."""
        mock_context.css_styles = {
            'rect': {'fill': 'blue', 'stroke': 'red'},
            'circle': {'fill': 'green'}
        }
        
        rect_element = ET.fromstring('<rect/>')
        styles = converter.get_element_styles(rect_element, mock_context)
        
        assert styles['fill'] == 'blue'
        assert styles['stroke'] == 'red'
    
    def test_get_element_styles_class_selector(self, converter, mock_context):
        """Test getting styles for element with class selector."""
        mock_context.css_styles = {
            '.highlight': {'fill': 'yellow'},
            '.border': {'stroke-width': '2px'}
        }
        
        element = ET.fromstring('<rect class="highlight border"/>')
        styles = converter.get_element_styles(element, mock_context)
        
        assert styles['fill'] == 'yellow'
        assert styles['stroke-width'] == '2px'
    
    def test_get_element_styles_id_selector(self, converter, mock_context):
        """Test getting styles for element with ID selector."""
        mock_context.css_styles = {
            '#myRect': {'fill': 'purple', 'opacity': '0.8'}
        }
        
        element = ET.fromstring('<rect id="myRect"/>')
        styles = converter.get_element_styles(element, mock_context)
        
        assert styles['fill'] == 'purple'
        assert styles['opacity'] == '0.8'
    
    def test_css_specificity_override(self, converter, mock_context):
        """Test CSS specificity - ID > class > type."""
        mock_context.css_styles = {
            'rect': {'fill': 'blue'},
            '.highlight': {'fill': 'yellow'},
            '#special': {'fill': 'red'}
        }
        
        element = ET.fromstring('<rect class="highlight" id="special"/>')
        styles = converter.get_element_styles(element, mock_context)
        
        # ID selector should win
        assert styles['fill'] == 'red'
    
    def test_apply_css_styles_to_element(self, converter, mock_context):
        """Test applying CSS styles to an element."""
        mock_context.css_styles = {
            'rect': {'fill': 'blue', 'stroke': 'red', 'stroke-width': '2px'}
        }
        
        element = ET.fromstring('<rect/>')
        converter.apply_css_styles(element, mock_context)
        
        assert element.get('fill') == 'blue'
        assert element.get('stroke') == 'red'
        assert element.get('stroke-width') == '2px'
    
    def test_attribute_precedence_over_css(self, converter, mock_context):
        """Test that element attributes take precedence over CSS."""
        mock_context.css_styles = {
            'rect': {'fill': 'blue', 'stroke': 'red'}
        }
        
        element = ET.fromstring('<rect fill="green"/>')
        converter.apply_css_styles(element, mock_context)
        
        # Attribute should not be overridden
        assert element.get('fill') == 'green'
        # CSS property should be applied
        assert element.get('stroke') == 'red'
    
    def test_merge_css_with_attributes(self, converter, mock_context):
        """Test merging CSS styles with element attributes."""
        mock_context.css_styles = {
            'rect': {'fill': 'blue', 'stroke': 'red', 'opacity': '0.8'}
        }
        
        element = ET.fromstring('<rect fill="green" stroke-width="3px"/>')
        merged = converter.merge_css_with_attributes(element, mock_context)
        
        # Attributes should override CSS
        assert merged['fill'] == 'green'
        assert merged['stroke-width'] == '3px'
        # CSS should provide missing properties
        assert merged['stroke'] == 'red'
        assert merged['opacity'] == '0.8'
    
    def test_get_computed_style_value(self, converter, mock_context):
        """Test getting computed style values."""
        mock_context.css_styles = {
            'rect': {'fill': 'blue', 'stroke': 'red'}
        }
        
        element = ET.fromstring('<rect fill="green"/>')
        
        # Attribute should win
        fill_value = converter.get_computed_style_value(element, 'fill', mock_context)
        assert fill_value == 'green'
        
        # CSS should be used when no attribute
        stroke_value = converter.get_computed_style_value(element, 'stroke', mock_context)
        assert stroke_value == 'red'
        
        # Default should be used when neither exists
        width_value = converter.get_computed_style_value(element, 'stroke-width', mock_context, '1px')
        assert width_value == '1px'
    
    def test_attribute_selector_matching(self, converter):
        """Test attribute selector matching."""
        element = ET.fromstring('<rect data-type="shape" fill="blue"/>')
        
        # Test presence selector
        assert converter._matches_attribute_selector('[data-type]', element) is True
        assert converter._matches_attribute_selector('[nonexistent]', element) is False
        
        # Test value selector
        assert converter._matches_attribute_selector('[data-type="shape"]', element) is True
        assert converter._matches_attribute_selector('[data-type="other"]', element) is False
        assert converter._matches_attribute_selector('[fill="blue"]', element) is True
    
    def test_complex_css_parsing(self, converter, mock_context):
        """Test parsing more complex CSS."""
        css_content = """
        /* Header styles */
        .header rect {
            fill: #3366cc;
            stroke: none;
        }
        
        text.title {
            font-family: Arial, sans-serif;
            font-size: 18px;
            font-weight: bold;
        }
        
        [data-interactive="true"] {
            cursor: pointer;
            opacity: 0.9;
        }
        """
        element = ET.fromstring(f'<style>{css_content}</style>')
        
        converter.convert(element, mock_context)
        
        # Note: Simple parser may not handle complex selectors perfectly
        # but should handle basic cases
        assert len(mock_context.css_styles) > 0
    
    def test_malformed_css_handling(self, converter, mock_context):
        """Test handling of malformed CSS."""
        css_content = """
        rect {
            fill: blue
            stroke red;  /* missing colon */
            stroke-width: ;  /* missing value */
        }
        """
        element = ET.fromstring(f'<style>{css_content}</style>')
        
        # Should not crash, may or may not parse correctly
        result = converter.convert(element, mock_context)
        assert 'Processed' in result
    
    def test_css_property_parsing_edge_cases(self, converter):
        """Test edge cases in CSS property parsing."""
        # Test various property formats
        properties_text = "fill:blue;stroke:red;stroke-width:2px;opacity:0.5;"
        properties = converter._parse_properties(properties_text)
        
        assert properties['fill'] == 'blue'
        assert properties['stroke'] == 'red'
        assert properties['stroke-width'] == '2px'
        assert properties['opacity'] == '0.5'
        
        # Test with extra spaces
        properties_text = " fill : blue ; stroke : red ; "
        properties = converter._parse_properties(properties_text)
        
        assert properties['fill'] == 'blue'
        assert properties['stroke'] == 'red'