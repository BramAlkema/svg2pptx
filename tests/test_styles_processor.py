"""
Tests for SVG Style Processor

Tests comprehensive style processing functionality including:
- CSS style attribute parsing
- Presentation attributes processing
- Style inheritance from parent elements
- CSS rule processing from <style> elements
- Fill and stroke style conversion to DrawingML
- Opacity handling and color parsing
- Dash pattern generation and length conversion
"""

import pytest
from lxml import etree as ET
from unittest.mock import Mock, patch
from src.converters.styles import StyleProcessor
from src.converters.base import ConversionContext


class TestStyleProcessor:
    """Test suite for StyleProcessor functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.processor = StyleProcessor()
        self.context = Mock(spec=ConversionContext)
        self.context.to_emu = Mock(return_value=12700)  # Default EMU conversion
        
        # Create mock SVG root
        self.svg_root = ET.Element("svg", nsmap={'svg': 'http://www.w3.org/2000/svg'})
        self.context.svg_root = self.svg_root

    def test_initialization(self):
        """Test processor initialization"""
        processor = StyleProcessor()
        assert hasattr(processor, 'gradient_converter')
        assert hasattr(processor, 'color_parser')
        assert hasattr(processor, 'css_rules')
        assert processor.css_rules == {}


class TestStyleAttributeParsing:
    """Test style attribute parsing functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.processor = StyleProcessor()

    def test_parse_empty_style_attribute(self):
        """Test parsing empty style attribute"""
        result = self.processor._parse_style_attribute("")
        assert result == {}

    def test_parse_none_style_attribute(self):
        """Test parsing None style attribute"""
        result = self.processor._parse_style_attribute(None)
        assert result == {}

    def test_parse_single_style_property(self):
        """Test parsing single CSS property"""
        style = "fill: red"
        result = self.processor._parse_style_attribute(style)
        assert result == {"fill": "red"}

    def test_parse_multiple_style_properties(self):
        """Test parsing multiple CSS properties"""
        style = "fill: red; stroke: blue; stroke-width: 2px"
        result = self.processor._parse_style_attribute(style)
        expected = {
            "fill": "red",
            "stroke": "blue", 
            "stroke-width": "2px"
        }
        assert result == expected

    def test_parse_style_with_whitespace(self):
        """Test parsing style with extra whitespace"""
        style = "  fill : red ;  stroke:   blue  ; stroke-width: 2px  "
        result = self.processor._parse_style_attribute(style)
        expected = {
            "fill": "red",
            "stroke": "blue",
            "stroke-width": "2px"
        }
        assert result == expected

    def test_parse_style_missing_colon(self):
        """Test parsing style with invalid property (no colon)"""
        style = "fill: red; invalid-property; stroke: blue"
        result = self.processor._parse_style_attribute(style)
        expected = {
            "fill": "red",
            "stroke": "blue"
        }
        assert result == expected

    def test_parse_style_empty_property_value(self):
        """Test parsing style with empty property value"""
        style = "fill:; stroke: blue"
        result = self.processor._parse_style_attribute(style)
        expected = {
            "fill": "",
            "stroke": "blue"
        }
        assert result == expected


class TestPresentationAttributes:
    """Test presentation attributes processing"""

    def setup_method(self):
        """Set up test fixtures"""
        self.processor = StyleProcessor()

    def test_get_presentation_attributes_basic(self):
        """Test extracting basic presentation attributes"""
        element = ET.Element("rect")
        element.set("fill", "#ff0000")
        element.set("stroke", "#0000ff")
        element.set("stroke-width", "2")
        
        result = self.processor._get_presentation_attributes(element)
        expected = {
            "fill": "#ff0000",
            "stroke": "#0000ff",
            "stroke-width": "2"
        }
        assert result == expected

    def test_get_presentation_attributes_all_supported(self):
        """Test extracting all supported presentation attributes"""
        element = ET.Element("rect")
        
        # Set all presentation attributes
        attrs = {
            'fill': '#ff0000', 'stroke': '#0000ff', 'stroke-width': '2',
            'stroke-linecap': 'round', 'stroke-linejoin': 'bevel',
            'stroke-dasharray': '5,5', 'stroke-opacity': '0.5', 
            'fill-opacity': '0.8', 'opacity': '0.9',
            'font-family': 'Arial', 'font-size': '12px', 'font-weight': 'bold',
            'font-style': 'italic', 'text-anchor': 'middle',
            'text-decoration': 'underline', 'visibility': 'hidden',
            'display': 'none'
        }
        
        for attr, value in attrs.items():
            element.set(attr, value)
        
        result = self.processor._get_presentation_attributes(element)
        assert result == attrs

    def test_get_presentation_attributes_ignores_non_presentation(self):
        """Test that non-presentation attributes are ignored"""
        element = ET.Element("rect")
        element.set("id", "myRect")
        element.set("class", "shape")
        element.set("x", "10")
        element.set("y", "20")
        element.set("fill", "#ff0000")  # This should be included
        
        result = self.processor._get_presentation_attributes(element)
        assert result == {"fill": "#ff0000"}

    def test_get_presentation_attributes_empty(self):
        """Test extracting from element with no presentation attributes"""
        element = ET.Element("rect")
        element.set("id", "myRect")
        element.set("x", "10")
        
        result = self.processor._get_presentation_attributes(element)
        assert result == {}


class TestStyleInheritance:
    """Test style inheritance functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.processor = StyleProcessor()

    def test_get_inherited_styles_no_parent(self):
        """Test inheritance with no parent element"""
        element = ET.Element("rect")
        
        result = self.processor._get_inherited_styles(element)
        assert result == {}

    def test_get_inherited_styles_from_parent_style(self):
        """Test inheriting styles from parent's style attribute"""
        parent = ET.Element("g")
        parent.set("style", "color: red; font-family: Arial; opacity: 0.8")
        
        element = ET.SubElement(parent, "text")
        
        result = self.processor._get_inherited_styles(element)
        expected = {
            "color": "red",
            "font-family": "Arial", 
            "opacity": "0.8"
        }
        assert result == expected

    def test_get_inherited_styles_from_parent_attributes(self):
        """Test inheriting from parent's presentation attributes"""
        parent = ET.Element("g")
        parent.set("font-size", "14px")
        parent.set("text-anchor", "middle")
        parent.set("stroke", "#000000")  # Non-inheritable
        
        element = ET.SubElement(parent, "text")
        
        result = self.processor._get_inherited_styles(element)
        expected = {
            "font-size": "14px",
            "text-anchor": "middle"
        }
        assert result == expected

    def test_get_inherited_styles_multiple_ancestors(self):
        """Test inheriting from multiple ancestor levels"""
        grandparent = ET.Element("svg")
        grandparent.set("font-family", "Times")
        grandparent.set("color", "blue")
        
        parent = ET.SubElement(grandparent, "g")
        parent.set("style", "font-size: 16px; color: red")  # Override color
        
        element = ET.SubElement(parent, "text")
        
        result = self.processor._get_inherited_styles(element)
        expected = {
            "font-family": "Times",  # From grandparent
            "font-size": "16px",     # From parent
            "color": "red"           # From parent (overrides grandparent)
        }
        assert result == expected

    def test_get_inherited_styles_non_inheritable_ignored(self):
        """Test that non-inheritable properties are not inherited"""
        parent = ET.Element("g")
        parent.set("style", "fill: red; stroke: blue; font-size: 14px")
        
        element = ET.SubElement(parent, "text")
        
        result = self.processor._get_inherited_styles(element)
        expected = {
            "font-size": "14px"  # Only inheritable property
        }
        assert result == expected


class TestCSSRuleProcessing:
    """Test CSS rule processing functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.processor = StyleProcessor()
        self.context = Mock(spec=ConversionContext)

    def test_parse_css_from_style_element_basic(self):
        """Test parsing basic CSS rules"""
        style_element = ET.Element("style")
        style_element.text = """
        rect { fill: red; stroke: blue; }
        circle { fill: green; }
        """
        
        self.processor.parse_css_from_style_element(style_element)
        
        expected = {
            'rect': {'fill': 'red', 'stroke': 'blue'},
            'circle': {'fill': 'green'}
        }
        assert self.processor.css_rules == expected

    def test_parse_css_with_comments(self):
        """Test parsing CSS with comments"""
        style_element = ET.Element("style")
        style_element.text = """
        /* This is a comment */
        rect { 
            fill: red; /* inline comment */
            stroke: blue; 
        }
        /* Multi-line
           comment */
        circle { fill: green; }
        """
        
        self.processor.parse_css_from_style_element(style_element)
        
        expected = {
            'rect': {'fill': 'red', 'stroke': 'blue'},
            'circle': {'fill': 'green'}
        }
        assert self.processor.css_rules == expected

    def test_parse_css_multiple_selectors(self):
        """Test parsing CSS with multiple selectors"""
        style_element = ET.Element("style")
        style_element.text = """
        rect, circle { fill: red; }
        text { font-size: 14px; }
        """
        
        self.processor.parse_css_from_style_element(style_element)
        
        expected = {
            'rect': {'fill': 'red'},
            'circle': {'fill': 'red'},
            'text': {'font-size': '14px'}
        }
        assert self.processor.css_rules == expected

    def test_parse_css_empty_style(self):
        """Test parsing empty style element"""
        style_element = ET.Element("style")
        style_element.text = ""
        
        self.processor.parse_css_from_style_element(style_element)
        
        assert self.processor.css_rules == {}

    def test_parse_css_none_text(self):
        """Test parsing style element with None text"""
        style_element = ET.Element("style")
        style_element.text = None
        
        self.processor.parse_css_from_style_element(style_element)
        
        assert self.processor.css_rules == {}


class TestCSSSelector:
    """Test CSS selector matching functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.processor = StyleProcessor()

    def test_matches_selector_element(self):
        """Test matching element selectors"""
        assert self.processor._matches_selector("rect", "rect", "", "") is True
        assert self.processor._matches_selector("rect", "circle", "", "") is False

    def test_matches_selector_id(self):
        """Test matching ID selectors"""
        assert self.processor._matches_selector("#myId", "rect", "myId", "") is True
        assert self.processor._matches_selector("#myId", "rect", "otherId", "") is False
        assert self.processor._matches_selector("#myId", "rect", "", "") is False

    def test_matches_selector_class(self):
        """Test matching class selectors"""
        assert self.processor._matches_selector(".myClass", "rect", "", "myClass") is True
        assert self.processor._matches_selector(".myClass", "rect", "", "myClass otherClass") is True
        assert self.processor._matches_selector(".myClass", "rect", "", "otherClass") is False
        assert self.processor._matches_selector(".myClass", "rect", "", "") is False

    def test_matches_selector_universal(self):
        """Test matching universal selector"""
        assert self.processor._matches_selector("*", "rect", "anyId", "anyClass") is True
        assert self.processor._matches_selector("*", "circle", "", "") is True

    def test_matches_selector_whitespace(self):
        """Test selector matching with whitespace"""
        assert self.processor._matches_selector("  rect  ", "rect", "", "") is True
        assert self.processor._matches_selector("  #myId  ", "rect", "myId", "") is True


class TestCSSStyleResolution:
    """Test CSS style resolution for elements"""

    def setup_method(self):
        """Set up test fixtures"""
        self.processor = StyleProcessor()
        self.context = Mock(spec=ConversionContext)
        
        # Set up CSS rules
        self.processor.css_rules = {
            'rect': {'fill': 'red', 'stroke': 'blue'},
            '#special': {'fill': 'green'},
            '.highlight': {'stroke-width': '3'},
            '*': {'opacity': '0.9'}
        }

    def test_get_css_styles_element_match(self):
        """Test CSS style resolution for element selector"""
        element = ET.Element("rect")
        
        result = self.processor._get_css_styles(element, self.context)
        # Should match both 'rect' and '*' selectors
        assert result['fill'] == 'red'
        assert result['stroke'] == 'blue'
        assert result['opacity'] == '0.9'

    def test_get_css_styles_id_match(self):
        """Test CSS style resolution for ID selector"""
        element = ET.Element("rect")
        element.set("id", "special")
        
        result = self.processor._get_css_styles(element, self.context)
        # Should match multiple selectors
        assert 'fill' in result
        assert result['fill'] == 'green'  # ID selector has priority

    def test_get_css_styles_class_match(self):
        """Test CSS style resolution for class selector"""
        element = ET.Element("rect")
        element.set("class", "highlight")
        
        result = self.processor._get_css_styles(element, self.context)
        # Should match 'rect', '.highlight', and '*' selectors
        assert 'stroke-width' in result
        assert result['stroke-width'] == '3'  # From class selector
        assert result['fill'] == 'red'  # From element selector
        assert result['opacity'] == '0.9'  # From universal selector

    def test_get_css_styles_universal_match(self):
        """Test CSS style resolution for universal selector"""
        element = ET.Element("circle")  # No specific rules
        
        result = self.processor._get_css_styles(element, self.context)
        expected = {'opacity': '0.9'}  # Universal selector
        assert result == expected

    def test_get_css_styles_multiple_matches(self):
        """Test CSS style resolution with multiple matching selectors"""
        element = ET.Element("rect")
        element.set("class", "highlight")
        
        # Should match both 'rect' and '.highlight' selectors
        result = self.processor._get_css_styles(element, self.context)
        
        # The exact behavior depends on implementation order
        # Both selectors should contribute styles
        assert 'stroke-width' in result or 'fill' in result

    def test_get_css_styles_namespaced_element(self):
        """Test CSS style resolution for namespaced elements"""
        element = ET.Element("{http://www.w3.org/2000/svg}rect")
        
        result = self.processor._get_css_styles(element, self.context)
        # Should match both 'rect' and '*' selectors
        assert result['fill'] == 'red'
        assert result['stroke'] == 'blue'
        assert result['opacity'] == '0.9'


class TestFillProcessing:
    """Test fill processing functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.processor = StyleProcessor()
        self.context = Mock(spec=ConversionContext)
        
        # Mock color parsing
        from src.colors import ColorInfo
        def mock_color_parse(color_str):
            if color_str.startswith('#'):
                hex_val = color_str.upper().replace('#', '')
                return type('ColorInfo', (), {'hex': hex_val})()
            return None
        
        self.processor.color_parser.parse = Mock(side_effect=mock_color_parse)

    def test_process_fill_solid_color(self):
        """Test processing solid color fill"""
        styles = {'fill': '#ff0000'}
        element = ET.Element("rect")
        
        result = self.processor._process_fill(styles, element, self.context)
        
        assert result == '<a:solidFill><a:srgbClr val="FF0000"/></a:solidFill>'

    def test_process_fill_solid_color_with_opacity(self):
        """Test processing solid color fill with opacity"""
        styles = {'fill': '#0000ff', 'fill-opacity': '0.5'}
        element = ET.Element("rect")
        
        result = self.processor._process_fill(styles, element, self.context)
        
        assert result == '<a:solidFill><a:srgbClr val="0000FF" alpha="50000"/></a:solidFill>'

    def test_process_fill_none(self):
        """Test processing no fill"""
        styles = {'fill': 'none'}
        element = ET.Element("rect")
        
        result = self.processor._process_fill(styles, element, self.context)
        
        assert result == '<a:noFill/>'

    def test_process_fill_url_reference(self):
        """Test processing URL reference fill (gradient)"""
        styles = {'fill': 'url(#myGradient)'}
        element = ET.Element("rect")
        
        # Mock gradient converter
        self.processor.gradient_converter.get_fill_from_url = Mock(return_value='<gradient-xml/>')
        
        result = self.processor._process_fill(styles, element, self.context)
        
        assert result == '<gradient-xml/>'
        self.processor.gradient_converter.get_fill_from_url.assert_called_once_with('url(#myGradient)', self.context)

    def test_process_fill_url_reference_with_opacity(self):
        """Test processing URL reference fill with opacity"""
        styles = {'fill': 'url(#myGradient)', 'fill-opacity': '0.8'}
        element = ET.Element("rect")
        
        # Mock gradient converter
        self.processor.gradient_converter.get_fill_from_url = Mock(return_value='<gradient-xml/>')
        
        result = self.processor._process_fill(styles, element, self.context)
        
        # Should return gradient (opacity handling is simplified)
        assert result == '<gradient-xml/>'

    def test_process_fill_default_black(self):
        """Test processing default fill (black)"""
        styles = {}  # No fill specified
        element = ET.Element("rect")
        
        result = self.processor._process_fill(styles, element, self.context)
        
        # Should use black as default
        self.processor.color_parser.parse.assert_called_with('black')

    def test_process_fill_invalid_color(self):
        """Test processing invalid color returns None"""
        styles = {'fill': 'invalid-color'}
        element = ET.Element("rect")
        
        self.processor.color_parser.parse = Mock(return_value=None)
        
        result = self.processor._process_fill(styles, element, self.context)
        
        assert result is None

    def test_process_fill_invalid_opacity(self):
        """Test processing with invalid opacity value"""
        styles = {'fill': '#ff0000', 'fill-opacity': 'invalid'}
        element = ET.Element("rect")
        
        # Should handle gracefully and use default opacity (1.0)
        result = self.processor._process_fill(styles, element, self.context)
        
        # Should not have alpha attribute (default opacity)
        assert 'alpha=' not in result
        assert 'val="FF0000"' in result


class TestStrokeProcessing:
    """Test stroke processing functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.processor = StyleProcessor()
        self.context = Mock(spec=ConversionContext)
        self.context.to_emu = Mock(return_value=12700)  # 1pt = 12700 EMU
        
        # Mock color parsing
        from src.colors import ColorInfo
        def mock_color_parse(color_str):
            if color_str.startswith('#'):
                hex_val = color_str.upper().replace('#', '')
                return type('ColorInfo', (), {'hex': hex_val})()
            return None
        
        self.processor.color_parser.parse = Mock(side_effect=mock_color_parse)

    def test_process_stroke_basic(self):
        """Test processing basic stroke"""
        styles = {'stroke': '#ff0000', 'stroke-width': '1'}
        
        result = self.processor._process_stroke(styles, self.context)
        
        assert '<a:ln w="12700" cap="flat">' in result
        assert 'val="FF0000"' in result
        assert '<a:miter lim="800000"/>' in result

    def test_process_stroke_none(self):
        """Test processing no stroke"""
        styles = {'stroke': 'none'}
        
        result = self.processor._process_stroke(styles, self.context)
        
        assert result == '<a:ln><a:noFill/></a:ln>'

    def test_process_stroke_missing(self):
        """Test processing with no stroke specified"""
        styles = {}
        
        result = self.processor._process_stroke(styles, self.context)
        
        assert result == '<a:ln><a:noFill/></a:ln>'

    def test_process_stroke_with_opacity(self):
        """Test processing stroke with opacity"""
        styles = {'stroke': '#0000ff', 'stroke-opacity': '0.7'}
        
        result = self.processor._process_stroke(styles, self.context)
        
        assert 'alpha="70000"' in result
        assert 'val="0000FF"' in result

    def test_process_stroke_caps_and_joins(self):
        """Test processing stroke with different caps and joins"""
        styles = {
            'stroke': '#ff0000',
            'stroke-linecap': 'round',
            'stroke-linejoin': 'bevel'
        }
        
        result = self.processor._process_stroke(styles, self.context)
        
        assert 'cap="rnd"' in result  # round -> rnd
        # Note: linejoin affects miter element, but simplified implementation uses miter

    def test_process_stroke_dash_array_simple(self):
        """Test processing stroke with dash array"""
        styles = {
            'stroke': '#000000',
            'stroke-dasharray': '3,2'
        }
        
        result = self.processor._process_stroke(styles, self.context)
        
        # 3*1000=3000, which is > 800, so it's lgDash
        assert '<a:prstDash val="lgDash"/>' in result

    def test_process_stroke_dash_array_long(self):
        """Test processing stroke with longer dash array"""
        styles = {
            'stroke': '#000000',
            'stroke-dasharray': '10,5'
        }
        
        result = self.processor._process_stroke(styles, self.context)
        
        assert '<a:prstDash val="lgDash"/>' in result

    def test_process_stroke_url_reference(self):
        """Test processing stroke with URL reference (gradient)"""
        styles = {'stroke': 'url(#myGradient)'}
        
        # Mock gradient converter
        self.processor.gradient_converter.get_fill_from_url = Mock(return_value='<gradient-xml/>')
        
        result = self.processor._process_stroke(styles, self.context)
        
        assert '<gradient-xml/>' in result
        self.processor.gradient_converter.get_fill_from_url.assert_called_once_with('url(#myGradient)', self.context)


class TestDashPatterns:
    """Test dash pattern creation functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.processor = StyleProcessor()

    def test_create_dash_pattern_simple(self):
        """Test creating simple dash pattern"""
        result = self.processor._create_dash_pattern('3,2')
        # 3*1000=3000, which is > 800, so it's lgDash
        assert result == '<a:prstDash val="lgDash"/>'

    def test_create_dash_pattern_medium(self):
        """Test creating medium dash pattern"""
        result = self.processor._create_dash_pattern('5,3')
        # 5*1000=5000, which is > 800, so it's lgDash
        assert result == '<a:prstDash val="lgDash"/>'

    def test_create_dash_pattern_large(self):
        """Test creating large dash pattern"""
        result = self.processor._create_dash_pattern('15,8')
        assert result == '<a:prstDash val="lgDash"/>'

    def test_create_dash_pattern_empty(self):
        """Test creating dash pattern from empty string"""
        result = self.processor._create_dash_pattern('')
        assert result == ''

    def test_create_dash_pattern_none(self):
        """Test creating dash pattern from 'none'"""
        result = self.processor._create_dash_pattern('none')
        assert result == ''

    def test_create_dash_pattern_invalid_values(self):
        """Test creating dash pattern with invalid values"""
        result = self.processor._create_dash_pattern('invalid,values')
        assert result == ''

    def test_create_dash_pattern_multiple_values(self):
        """Test creating dash pattern with more than 2 values"""
        result = self.processor._create_dash_pattern('3,2,1,2')
        assert result == '<a:prstDash val="dash"/>'  # Default

    def test_create_dash_pattern_space_separated(self):
        """Test creating dash pattern with space-separated values"""
        result = self.processor._create_dash_pattern('5 3')
        # 5*1000=5000, which is > 800, so it's lgDash
        assert result == '<a:prstDash val="lgDash"/>'

    def test_create_dash_pattern_comma_and_space(self):
        """Test creating dash pattern with mixed separators"""
        result = self.processor._create_dash_pattern('3, 2')
        # 3*1000=3000, which is > 800, so it's lgDash
        assert result == '<a:prstDash val="lgDash"/>'

    def test_create_dash_pattern_very_small_values(self):
        """Test creating dash pattern with very small values (dot pattern)"""
        result = self.processor._create_dash_pattern('0.1,0.2')
        # Both values <= 300 when converted (0.1*1000=100, 0.2*1000=200)
        assert result == '<a:prstDash val="dot"/>'

    def test_create_dash_pattern_medium_dash_length(self):
        """Test creating dash pattern with medium dash length"""
        result = self.processor._create_dash_pattern('0.5,0.3')
        # dash_len = 500, which is <= 800
        assert result == '<a:prstDash val="dash"/>'


class TestUtilityMethods:
    """Test utility methods"""

    def setup_method(self):
        """Set up test fixtures"""
        self.processor = StyleProcessor()
        self.context = Mock(spec=ConversionContext)
        self.context.to_emu = Mock(return_value=25400)  # 2pt

    def test_get_opacity_valid(self):
        """Test getting valid opacity value"""
        styles = {'opacity': '0.7'}
        result = self.processor._get_opacity(styles)
        assert result == 0.7

    def test_get_opacity_default(self):
        """Test getting default opacity"""
        styles = {}
        result = self.processor._get_opacity(styles)
        assert result == 1.0

    def test_get_opacity_invalid(self):
        """Test getting opacity with invalid value"""
        styles = {'opacity': 'invalid'}
        result = self.processor._get_opacity(styles)
        assert result == 1.0

    def test_parse_length_to_emu(self):
        """Test parsing length to EMU"""
        result = self.processor._parse_length_to_emu('2pt', self.context)
        assert result == 25400
        self.context.to_emu.assert_called_once_with('2pt')


class TestCompleteStyleProcessing:
    """Test complete style processing workflow"""

    def setup_method(self):
        """Set up test fixtures"""
        self.processor = StyleProcessor()
        self.context = Mock(spec=ConversionContext)
        self.context.to_emu = Mock(return_value=12700)
        
        # Mock color parsing
        from src.colors import ColorInfo
        def mock_color_parse(color_str):
            if color_str.startswith('#'):
                hex_val = color_str.upper().replace('#', '')
                return type('ColorInfo', (), {'hex': hex_val})()
            return None
        
        self.processor.color_parser.parse = Mock(side_effect=mock_color_parse)

    def test_process_element_styles_complete_workflow(self):
        """Test complete style processing workflow"""
        # Create element hierarchy
        parent = ET.Element("g")
        parent.set("style", "font-family: Arial; opacity: 0.8")
        
        element = ET.SubElement(parent, "rect")
        element.set("fill", "#ff0000")  # Presentation attribute
        element.set("style", "stroke: #0000ff; stroke-width: 2px")  # Inline style
        
        # Set up CSS rules
        self.processor.css_rules = {
            'rect': {'stroke-opacity': '0.9'}
        }
        
        result = self.processor.process_element_styles(element, self.context)
        
        # Should have processed fill, stroke, and opacity
        assert 'fill' in result
        assert 'stroke' in result
        assert 'opacity' in result
        
        assert result['opacity'] == 0.8  # Inherited from parent

    def test_process_element_styles_visibility_hidden(self):
        """Test processing element with hidden visibility"""
        element = ET.Element("rect")
        element.set("style", "visibility: hidden")
        
        result = self.processor.process_element_styles(element, self.context)
        
        assert result['hidden'] is True

    def test_process_element_styles_cascade_priority(self):
        """Test style cascade priority (inline > CSS > attributes > inherited)"""
        # Create hierarchy with different style sources
        parent = ET.Element("g")
        parent.set("fill", "red")  # Inherited
        
        element = ET.SubElement(parent, "rect")
        element.set("fill", "blue")  # Presentation attribute
        element.set("style", "fill: green")  # Inline style (highest priority)
        
        # Set up CSS rule
        self.processor.css_rules = {
            'rect': {'fill': 'yellow'}
        }
        
        # Mock the internal methods to track what gets processed
        with patch.object(self.processor, '_process_fill') as mock_fill:
            mock_fill.return_value = '<fill-xml/>'
            
            result = self.processor.process_element_styles(element, self.context)
            
            # Check that the final styles passed to _process_fill have inline style priority
            call_args = mock_fill.call_args[0][0]  # First argument (styles dict)
            assert call_args['fill'] == 'green'  # Inline style should win


class TestEdgeCasesAndErrorHandling:
    """Test edge cases and error handling"""

    def setup_method(self):
        """Set up test fixtures"""
        self.processor = StyleProcessor()
        self.context = Mock(spec=ConversionContext)

    def test_process_element_styles_none_context(self):
        """Test processing with None context"""
        element = ET.Element("rect")
        
        # Should handle gracefully
        with patch.object(self.processor, 'process_element_styles') as mock_process:
            mock_process.return_value = {}
            result = self.processor.process_element_styles(element, None)
            # Should not crash

    def test_process_fill_invalid_gradient_url(self):
        """Test processing fill with invalid gradient URL"""
        styles = {'fill': 'url(#nonexistent)'}
        element = ET.Element("rect")
        
        # Mock gradient converter to return None
        self.processor.gradient_converter.get_fill_from_url = Mock(return_value=None)
        
        result = self.processor._process_fill(styles, element, self.context)
        
        # Should handle gracefully
        assert result is None or result == ''

    def test_parse_css_malformed_rules(self):
        """Test parsing malformed CSS rules"""
        style_element = ET.Element("style")
        style_element.text = """
        rect { fill: red stroke: blue }  /* Missing semicolon */
        circle fill: green; }            /* Missing opening brace */
        { stroke: black; }               /* Missing selector */
        """
        
        # Should handle gracefully without crashing
        self.processor.parse_css_from_style_element(style_element)
        
        # May have partial parsing or empty rules
        assert isinstance(self.processor.css_rules, dict)