"""
Tests for Enhanced SVG Pattern Converter

Tests the enhanced pattern conversion functionality including:
- Pattern content analysis and classification
- Simple texture pattern conversion
- Geometric pattern mapping to PowerPoint presets
- Gradient-based pattern conversion
- Complex pattern handling and fallbacks
- Pattern dimension parsing and scaling
"""

import pytest
from lxml import etree as ET
from unittest.mock import Mock, patch
from src.converters.gradients import GradientConverter
from src.converters.base import ConversionContext


class TestPatternContentAnalysis:
    """Test pattern content analysis functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.converter = GradientConverter()
        self.context = Mock(spec=ConversionContext)

    def test_analyze_simple_pattern(self):
        """Test analysis of simple pattern content"""
        pattern_xml = """
        <pattern id="simple-pattern" width="10" height="10">
            <rect x="0" y="0" width="5" height="5" fill="red"/>
        </pattern>
        """
        pattern_element = ET.fromstring(pattern_xml)
        
        analysis = self.converter._analyze_pattern_content(pattern_element, self.context)
        
        assert analysis['element_count'] == 1
        assert analysis['is_simple_texture'] is True
        assert analysis['is_geometric'] is False
        assert analysis['has_gradients'] is False
        assert analysis['color_count'] == 1
        assert analysis['dominant_shapes'] == [('rect', 1)]
        assert analysis['complexity_score'] < 5.0

    def test_analyze_geometric_pattern(self):
        """Test analysis of geometric pattern with multiple shapes"""
        pattern_xml = """
        <pattern id="geometric-pattern" width="20" height="20">
            <rect x="0" y="0" width="10" height="10" fill="blue"/>
            <circle cx="15" cy="15" r="3" fill="red"/>
            <rect x="10" y="10" width="5" height="5" fill="green"/>
        </pattern>
        """
        pattern_element = ET.fromstring(pattern_xml)
        
        analysis = self.converter._analyze_pattern_content(pattern_element, self.context)
        
        assert analysis['element_count'] == 3
        assert analysis['is_simple_texture'] is False
        assert analysis['is_geometric'] is True
        assert analysis['color_count'] == 3
        assert analysis['dominant_shapes'][0] == ('rect', 2)  # Most common shape
        assert 'circle' in [shape for shape, count in analysis['dominant_shapes']]

    def test_analyze_gradient_pattern(self):
        """Test analysis of pattern containing gradients"""
        pattern_xml = """
        <pattern id="gradient-pattern" width="30" height="30">
            <defs>
                <linearGradient id="grad1">
                    <stop offset="0%" stop-color="white"/>
                    <stop offset="100%" stop-color="black"/>
                </linearGradient>
            </defs>
            <rect x="0" y="0" width="30" height="30" fill="url(#grad1)"/>
        </pattern>
        """
        pattern_element = ET.fromstring(pattern_xml)
        
        analysis = self.converter._analyze_pattern_content(pattern_element, self.context)
        
        assert analysis['has_gradients'] is True
        assert analysis['complexity_score'] > 10  # Gradients add complexity

    def test_analyze_complex_pattern(self):
        """Test analysis of complex pattern with many elements"""
        pattern_xml = """
        <pattern id="complex-pattern" width="50" height="50">
            <rect x="0" y="0" width="50" height="50" fill="white"/>
            <circle cx="10" cy="10" r="5" fill="red"/>
            <circle cx="30" cy="10" r="5" fill="blue"/>
            <circle cx="10" cy="30" r="5" fill="green"/>
            <circle cx="30" cy="30" r="5" fill="yellow"/>
            <path d="M20,20 L30,25 L20,30 Z" fill="purple"/>
            <polygon points="40,40 45,35 50,40 45,45" fill="orange"/>
        </pattern>
        """
        pattern_element = ET.fromstring(pattern_xml)
        
        analysis = self.converter._analyze_pattern_content(pattern_element, self.context)
        
        assert analysis['element_count'] == 7
        assert analysis['is_simple_texture'] is False
        assert analysis['is_geometric'] is False  # Too complex
        assert analysis['color_count'] == 6
        assert analysis['complexity_score'] > 15  # High complexity


class TestPatternDimensionParsing:
    """Test pattern dimension parsing"""

    def setup_method(self):
        """Set up test fixtures"""
        self.converter = GradientConverter()
        self.context = Mock(spec=ConversionContext)

    def test_parse_numeric_dimensions(self):
        """Test parsing numeric pattern dimensions"""
        assert self.converter._parse_pattern_dimension("10", self.context) == 10.0
        assert self.converter._parse_pattern_dimension("15.5", self.context) == 15.5
        assert self.converter._parse_pattern_dimension("0", self.context) == 0.0

    def test_parse_unit_dimensions(self):
        """Test parsing dimensions with units"""
        assert self.converter._parse_pattern_dimension("20px", self.context) == 20.0
        assert self.converter._parse_pattern_dimension("12pt", self.context) == 12.0
        assert self.converter._parse_pattern_dimension("50%", self.context) == 50.0

    def test_parse_invalid_dimensions(self):
        """Test handling of invalid dimension values"""
        assert self.converter._parse_pattern_dimension("", self.context) == 0.0
        assert self.converter._parse_pattern_dimension("invalid", self.context) == 0.0
        assert self.converter._parse_pattern_dimension(None, self.context) == 0.0


class TestSimplePatternConversion:
    """Test conversion of simple patterns"""

    def setup_method(self):
        """Set up test fixtures"""
        self.converter = GradientConverter()
        
        # Mock color extraction
        self.converter._extract_pattern_color = Mock(return_value="FF0000")

    def test_convert_simple_pattern_with_color(self):
        """Test conversion of simple pattern with extracted color"""
        pattern_element = Mock()
        analysis = {
            'is_simple_texture': True,
            'element_count': 1,
            'color_count': 1
        }
        
        result = self.converter._convert_simple_pattern(pattern_element, analysis, None)
        
        assert '<a:solidFill>' in result
        assert 'val="FF0000"' in result
        self.converter._extract_pattern_color.assert_called_once()

    def test_convert_simple_pattern_fallback(self):
        """Test simple pattern conversion fallback when no color found"""
        pattern_element = Mock()
        analysis = {'is_simple_texture': True}
        
        # Mock no color found
        self.converter._extract_pattern_color = Mock(return_value=None)
        
        result = self.converter._convert_simple_pattern(pattern_element, analysis, None)
        
        assert '<a:solidFill>' in result
        assert 'val="808080"' in result  # Default gray


class TestGeometricPatternConversion:
    """Test conversion of geometric patterns"""

    def setup_method(self):
        """Set up test fixtures"""
        self.converter = GradientConverter()
        
        # Mock color extraction
        self.converter._extract_pattern_color = Mock(return_value="0000FF")

    def test_convert_rectangular_pattern(self):
        """Test conversion of pattern with rectangular dominant shape"""
        pattern_element = Mock()
        analysis = {
            'dominant_shapes': [('rect', 3), ('circle', 1)],
            'color_count': 2
        }
        
        result = self.converter._convert_geometric_pattern(pattern_element, analysis, None)
        
        assert '<a:pattFill prst="shingle">' in result
        assert '<a:fgClr><a:srgbClr val="0000FF"/></a:fgClr>' in result
        assert '<a:bgClr><a:srgbClr val="FFFFFF"/></a:bgClr>' in result

    def test_convert_circular_pattern(self):
        """Test conversion of pattern with circular dominant shape"""
        pattern_element = Mock()
        analysis = {
            'dominant_shapes': [('circle', 5), ('rect', 2)],
            'color_count': 3
        }
        
        result = self.converter._convert_geometric_pattern(pattern_element, analysis, None)
        
        assert '<a:pattFill prst="dotGrid">' in result
        assert 'val="0000FF"' in result

    def test_convert_default_geometric_pattern(self):
        """Test conversion of geometric pattern without specific shape mapping"""
        pattern_element = Mock()
        analysis = {
            'dominant_shapes': [('path', 2), ('polygon', 1)],
            'color_count': 2
        }
        
        result = self.converter._convert_geometric_pattern(pattern_element, analysis, None)
        
        assert '<a:pattFill prst="diagBrick">' in result

    def test_convert_geometric_pattern_no_color(self):
        """Test geometric pattern conversion when no color extracted"""
        pattern_element = Mock()
        analysis = {
            'dominant_shapes': [('rect', 2)],
            'color_count': 1
        }
        
        # Mock no color found
        self.converter._extract_pattern_color = Mock(return_value=None)
        
        result = self.converter._convert_geometric_pattern(pattern_element, analysis, None)
        
        assert 'val="808080"' in result  # Default color


class TestGradientPatternConversion:
    """Test conversion of patterns containing gradients"""

    def setup_method(self):
        """Set up test fixtures"""
        self.converter = GradientConverter()
        self.context = Mock()

    def test_convert_gradient_pattern_with_gradient(self):
        """Test conversion of pattern containing gradient elements"""
        # Create mock pattern element with gradient
        pattern_element = Mock()
        gradient_element = Mock()
        pattern_element.xpath.return_value = [gradient_element]
        
        # Mock gradient conversion
        self.converter.convert = Mock(return_value="<mock_gradient_xml/>")
        
        analysis = {'has_gradients': True}
        
        result = self.converter._convert_gradient_pattern(pattern_element, analysis, self.context)
        
        assert result == "<mock_gradient_xml/>"
        self.converter.convert.assert_called_once_with(gradient_element, self.context)

    def test_convert_gradient_pattern_fallback(self):
        """Test gradient pattern conversion fallback when no gradients found"""
        pattern_element = Mock()
        pattern_element.xpath.return_value = []  # No gradients found
        
        analysis = {'has_gradients': True}  # Analysis says there are gradients
        
        # Mock color extraction
        self.converter._extract_pattern_color = Mock(return_value="00FF00")
        
        result = self.converter._convert_gradient_pattern(pattern_element, analysis, self.context)
        
        assert '<a:solidFill>' in result
        assert 'val="00FF00"' in result


class TestComplexPatternConversion:
    """Test conversion of complex patterns"""

    def setup_method(self):
        """Set up test fixtures"""
        self.converter = GradientConverter()
        
        # Mock color extraction
        self.converter._extract_pattern_color = Mock(return_value="FF00FF")

    def test_convert_low_complexity_pattern(self):
        """Test conversion of low complexity pattern"""
        pattern_element = Mock()
        analysis = {
            'complexity_score': 8.0,
            'color_count': 2
        }
        
        result = self.converter._convert_complex_pattern(pattern_element, analysis, None)
        
        assert '<a:pattFill prst="cross">' in result
        assert 'val="FF00FF"' in result

    def test_convert_medium_complexity_pattern(self):
        """Test conversion of medium complexity pattern"""
        pattern_element = Mock()
        analysis = {
            'complexity_score': 12.0,
            'color_count': 3
        }
        
        result = self.converter._convert_complex_pattern(pattern_element, analysis, None)
        
        assert '<a:pattFill prst="zigZag">' in result

    def test_convert_high_complexity_pattern(self):
        """Test conversion of high complexity pattern"""
        pattern_element = Mock()
        analysis = {
            'complexity_score': 20.0,
            'color_count': 5
        }
        
        result = self.converter._convert_complex_pattern(pattern_element, analysis, None)
        
        assert '<a:pattFill prst="weave">' in result

    def test_convert_complex_pattern_no_color(self):
        """Test complex pattern conversion when no color found"""
        pattern_element = Mock()
        analysis = {'complexity_score': 15.0}
        
        # Mock no color found
        self.converter._extract_pattern_color = Mock(return_value=None)
        
        result = self.converter._convert_complex_pattern(pattern_element, analysis, None)
        
        assert 'val="808080"' in result  # Default gray


class TestPatternColorExtraction:
    """Test color extraction from pattern elements"""

    def setup_method(self):
        """Set up test fixtures"""
        self.converter = GradientConverter()
        
        # Mock color parser
        self.converter.parse_color = Mock()

    def test_extract_color_from_fill_attribute(self):
        """Test extracting color from fill attribute"""
        pattern_xml = """
        <pattern id="test-pattern">
            <rect x="0" y="0" width="10" height="10" fill="#FF0000"/>
            <circle cx="5" cy="5" r="2" fill="none"/>
        </pattern>
        """
        pattern_element = ET.fromstring(pattern_xml)
        
        self.converter.parse_color.return_value = "FF0000"
        
        result = self.converter._extract_pattern_color(pattern_element)
        
        assert result == "FF0000"
        self.converter.parse_color.assert_called_with("#FF0000")

    def test_extract_color_from_style_attribute(self):
        """Test extracting color from style attribute"""
        pattern_xml = """
        <pattern id="test-pattern">
            <rect x="0" y="0" width="10" height="10" style="fill: blue; stroke: red"/>
        </pattern>
        """
        pattern_element = ET.fromstring(pattern_xml)
        
        self.converter.parse_color.return_value = "0000FF"
        
        result = self.converter._extract_pattern_color(pattern_element)
        
        assert result == "0000FF"
        self.converter.parse_color.assert_called_with("blue")

    def test_extract_color_skip_none_values(self):
        """Test that 'none' fill values are skipped"""
        pattern_xml = """
        <pattern id="test-pattern">
            <rect x="0" y="0" width="10" height="10" fill="none"/>
            <circle cx="5" cy="5" r="2" fill="green"/>
        </pattern>
        """
        pattern_element = ET.fromstring(pattern_xml)
        
        self.converter.parse_color.return_value = "00FF00"
        
        result = self.converter._extract_pattern_color(pattern_element)
        
        # Should find green, not none
        assert result == "00FF00"
        self.converter.parse_color.assert_called_with("green")

    def test_extract_color_skip_url_references(self):
        """Test that URL references are skipped"""
        pattern_xml = """
        <pattern id="test-pattern">
            <rect x="0" y="0" width="10" height="10" fill="url(#grad1)"/>
            <circle cx="5" cy="5" r="2" fill="purple"/>
        </pattern>
        """
        pattern_element = ET.fromstring(pattern_xml)
        
        self.converter.parse_color.return_value = "800080"
        
        result = self.converter._extract_pattern_color(pattern_element)
        
        # Should find purple, not url reference
        assert result == "800080"
        self.converter.parse_color.assert_called_with("purple")

    def test_extract_color_no_colors_found(self):
        """Test handling when no colors are found"""
        pattern_xml = """
        <pattern id="test-pattern">
            <rect x="0" y="0" width="10" height="10" fill="none"/>
            <path d="M0,0 L10,10" stroke="url(#grad1)"/>
        </pattern>
        """
        pattern_element = ET.fromstring(pattern_xml)
        
        result = self.converter._extract_pattern_color(pattern_element)
        
        assert result is None


class TestPatternConversionIntegration:
    """Integration tests for complete pattern conversion workflow"""

    def setup_method(self):
        """Set up test fixtures"""
        self.converter = GradientConverter()
        self.context = Mock(spec=ConversionContext)

    def test_complete_pattern_conversion_simple(self):
        """Test complete conversion of simple pattern"""
        pattern_xml = """
        <pattern id="simple-dots" width="10" height="10">
            <circle cx="5" cy="5" r="2" fill="red"/>
        </pattern>
        """
        pattern_element = ET.fromstring(pattern_xml)
        
        # Mock dependencies
        self.converter._parse_pattern_dimension = Mock(return_value=10.0)
        self.converter.parse_color = Mock(return_value="FF0000")
        
        result = self.converter._convert_pattern(pattern_element, self.context)
        
        # Should identify as simple texture and convert to solid fill
        assert '<a:solidFill>' in result
        assert 'val="FF0000"' in result

    def test_complete_pattern_conversion_geometric(self):
        """Test complete conversion of geometric pattern"""
        pattern_xml = """
        <pattern id="checkerboard" width="20" height="20">
            <rect x="0" y="0" width="10" height="10" fill="black"/>
            <rect x="10" y="10" width="10" height="10" fill="black"/>
            <rect x="0" y="10" width="10" height="10" fill="white"/>
            <rect x="10" y="0" width="10" height="10" fill="white"/>
        </pattern>
        """
        pattern_element = ET.fromstring(pattern_xml)
        
        # Mock dependencies
        self.converter._parse_pattern_dimension = Mock(return_value=20.0)
        self.converter.parse_color = Mock(return_value="000000")
        
        result = self.converter._convert_pattern(pattern_element, self.context)
        
        # Should identify as geometric and convert to pattern fill
        assert '<a:pattFill' in result
        assert 'prst="shingle"' in result

    def test_complete_pattern_conversion_invalid_dimensions(self):
        """Test handling of pattern with invalid dimensions"""
        pattern_xml = """
        <pattern id="invalid-pattern" width="0" height="invalid">
            <rect x="0" y="0" width="10" height="10" fill="blue"/>
        </pattern>
        """
        pattern_element = ET.fromstring(pattern_xml)
        
        # Mock dimension parsing to return invalid values
        self.converter._parse_pattern_dimension = Mock(side_effect=[0.0, 0.0])  # Invalid dimensions
        self.converter.parse_color = Mock(return_value="0000FF")
        
        result = self.converter._convert_pattern(pattern_element, self.context)
        
        # Should fallback to solid color
        assert '<a:solidFill>' in result
        assert 'val="0000FF"' in result

    def test_complete_pattern_conversion_no_color(self):
        """Test pattern conversion when no color can be extracted"""
        pattern_xml = """
        <pattern id="no-color-pattern" width="10" height="10">
            <rect x="0" y="0" width="10" height="10" fill="none"/>
        </pattern>
        """
        pattern_element = ET.fromstring(pattern_xml)
        
        # Mock valid dimensions but no color
        self.converter._parse_pattern_dimension = Mock(return_value=10.0)
        self.converter.parse_color = Mock(return_value=None)
        
        result = self.converter._convert_pattern(pattern_element, self.context)
        
        # Should return empty string when no fallback is possible
        assert result == ""