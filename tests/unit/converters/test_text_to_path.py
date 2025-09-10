"""
Tests for TextToPathConverter

Comprehensive test suite for text-to-path fallback system and integration testing.
"""

import pytest
import xml.etree.ElementTree as ET
from unittest.mock import Mock, patch, MagicMock

from src.converters.text_to_path import TextToPathConverter
from src.converters.base import ConversionContext, CoordinateSystem
from src.converters.font_metrics import FontMetrics, GlyphOutline
from src.units import UnitConverter
from src.colors import ColorParser


class TestTextToPathConverter:
    """Test suite for TextToPathConverter functionality."""
    
    @pytest.fixture
    def converter(self):
        """Create TextToPathConverter instance for testing."""
        return TextToPathConverter()
    
    @pytest.fixture
    def custom_converter(self):
        """Create TextToPathConverter with custom configuration."""
        config = {
            'font_detection_enabled': True,
            'fallback_threshold': 0.9,
            'path_optimization_level': 2,
            'max_cache_size': 64
        }
        return TextToPathConverter(config=config)
    
    @pytest.fixture
    def mock_context(self):
        """Create mock conversion context."""
        context = Mock(spec=ConversionContext)
        context.coordinate_system = Mock(spec=CoordinateSystem)
        # Use UnitConverter to calculate proper EMU values
        unit_converter = UnitConverter()
        pt1_emu = unit_converter.to_emu('1pt')
        pt2_emu = unit_converter.to_emu('2pt')
        context.coordinate_system.svg_to_emu.return_value = (pt1_emu, pt2_emu)
        context.get_next_shape_id.return_value = 100
        return context
    
    def test_initialization_default(self, converter):
        """Test proper initialization with default configuration."""
        assert converter.config['font_detection_enabled'] is True
        assert converter.config['fallback_threshold'] == 0.8
        assert converter.config['path_optimization_level'] == 1
        assert converter.font_analyzer is not None
        assert converter.path_generator is not None
        assert converter.conversion_stats['total_conversions'] == 0
    
    def test_initialization_custom_config(self, custom_converter):
        """Test initialization with custom configuration."""
        assert custom_converter.config['fallback_threshold'] == 0.9
        assert custom_converter.config['path_optimization_level'] == 2
        assert custom_converter.config['max_cache_size'] == 64
    
    def test_can_convert_supported_elements(self, converter):
        """Test can_convert method for supported elements."""
        text_elem = ET.fromstring('<text>Hello</text>')
        tspan_elem = ET.fromstring('<tspan>World</tspan>')
        rect_elem = ET.fromstring('<rect width="100" height="50"/>')
        
        assert converter.can_convert(text_elem) is True
        assert converter.can_convert(tspan_elem) is True
        assert converter.can_convert(rect_elem) is False
    
    @patch('src.converters.text_to_path.TextToPathConverter._get_font_families')
    def test_should_convert_to_path_no_detection(self, mock_get_families, converter):
        """Test path conversion decision when detection is disabled."""
        converter.config['font_detection_enabled'] = False
        element = ET.fromstring('<text>Test</text>')
        context = Mock()
        
        result = converter.should_convert_to_path(element, context)
        assert result is True
        mock_get_families.assert_not_called()
    
    @patch('src.converters.text_to_path.TextToPathConverter._get_font_families')
    def test_should_convert_to_path_no_fonts(self, mock_get_families, converter):
        """Test path conversion decision when no fonts specified."""
        mock_get_families.return_value = []
        element = ET.fromstring('<text>Test</text>')
        context = Mock()
        
        result = converter.should_convert_to_path(element, context)
        assert result is True
    
    def test_should_convert_to_path_available_font(self, converter):
        """Test path conversion decision when font is available."""
        with patch.object(converter, '_get_font_families', return_value=['Arial']), \
             patch.object(converter.font_analyzer, 'detect_font_availability', return_value=True):
            
            element = ET.fromstring('<text>Test</text>')
            context = Mock()
            
            result = converter.should_convert_to_path(element, context)
            assert result is False  # Should use regular text
    
    def test_should_convert_to_path_good_fallback(self, converter):
        """Test path conversion decision with good fallback font."""
        with patch.object(converter, '_get_font_families', return_value=['UnknownFont']), \
             patch.object(converter.font_analyzer, 'detect_font_availability', return_value=False), \
             patch.object(converter.font_analyzer, 'get_font_fallback_chain', return_value=['Arial']):
            
            element = ET.fromstring('<text>Test</text>')
            context = Mock()
            
            result = converter.should_convert_to_path(element, context)
            assert result is False  # Good fallback available
    
    def test_should_convert_to_path_poor_fallback(self, converter):
        """Test path conversion decision with poor fallback font."""
        with patch.object(converter, '_get_font_families', return_value=['UnknownFont']), \
             patch.object(converter.font_analyzer, 'detect_font_availability', return_value=False), \
             patch.object(converter.font_analyzer, 'get_font_fallback_chain', return_value=['SomeObscureFont']):
            
            element = ET.fromstring('<text>Test</text>')
            context = Mock()
            
            result = converter.should_convert_to_path(element, context)
            assert result is True  # Convert to path for better fidelity
    
    def test_extract_text_content_simple(self, converter):
        """Test text content extraction from simple text element."""
        element = ET.fromstring('<text>Hello World</text>')
        content = converter._extract_text_content(element)
        assert content == 'Hello World'
    
    def test_extract_text_content_with_tspan(self, converter):
        """Test text content extraction with tspan elements."""
        element = ET.fromstring('<text>Hello <tspan>World</tspan></text>')
        content = converter._extract_text_content(element)
        assert 'Hello' in content
        assert 'World' in content
    
    def test_extract_text_content_empty(self, converter):
        """Test text content extraction from empty element."""
        element = ET.fromstring('<text></text>')
        content = converter._extract_text_content(element)
        assert content == ''
    
    def test_get_font_families_attribute(self, converter):
        """Test font family extraction from font-family attribute."""
        element = ET.fromstring('<text font-family="Arial, Helvetica">Test</text>')
        families = converter._get_font_families(element)
        assert 'Arial' in families
        assert 'Helvetica' in families
    
    def test_get_font_families_style(self, converter):
        """Test font family extraction from style attribute."""
        element = ET.fromstring('<text style="font-family: Times New Roman, serif">Test</text>')
        families = converter._get_font_families(element)
        assert 'Times New Roman' in families
        assert 'serif' in families
    
    def test_get_font_families_default(self, converter):
        """Test font family extraction with no fonts specified."""
        element = ET.fromstring('<text>Test</text>')
        families = converter._get_font_families(element)
        assert families == ['Arial']  # Default font
    
    def test_parse_font_family_list(self, converter):
        """Test parsing of comma-separated font family list."""
        families = converter._parse_font_family_list('Arial, "Times New Roman", \'Courier New\'')
        assert families == ['Arial', 'Times New Roman', 'Courier New']
    
    def test_get_font_size_attribute(self, converter):
        """Test font size extraction from attribute."""
        element = ET.fromstring('<text font-size="14px">Test</text>')
        context = Mock()
        size = converter._get_font_size(element, context)
        assert size > 0  # Should parse to some positive value
    
    def test_get_font_size_style(self, converter):
        """Test font size extraction from style attribute."""
        element = ET.fromstring('<text style="font-size: 16pt">Test</text>')
        context = Mock()
        size = converter._get_font_size(element, context)
        assert size == 16.0
    
    def test_get_font_size_default(self, converter):
        """Test font size extraction with no size specified."""
        element = ET.fromstring('<text>Test</text>')
        context = Mock()
        size = converter._get_font_size(element, context)
        assert size == 12.0  # Default size
    
    def test_parse_font_size_pixels(self, converter):
        """Test font size parsing with pixel units."""
        size = converter._parse_font_size('16px')
        assert size == 12.0  # 16px * 72/96 = 12pt
    
    def test_parse_font_size_points(self, converter):
        """Test font size parsing with point units."""
        size = converter._parse_font_size('14pt')
        assert size == 14.0
    
    def test_parse_font_size_ems(self, converter):
        """Test font size parsing with em units."""
        size = converter._parse_font_size('1.5em')
        assert size == 18.0  # 1.5 * 12 = 18
    
    def test_get_font_weight_numeric(self, converter):
        """Test font weight extraction as numeric value."""
        element = ET.fromstring('<text font-weight="bold">Test</text>')
        weight = converter._get_font_weight_numeric(element)
        assert weight == 700
        
        element = ET.fromstring('<text font-weight="400">Test</text>')
        weight = converter._get_font_weight_numeric(element)
        assert weight == 400
    
    def test_get_font_style(self, converter):
        """Test font style extraction."""
        element = ET.fromstring('<text font-style="italic">Test</text>')
        style = converter._get_font_style(element)
        assert style == 'italic'
        
        element = ET.fromstring('<text>Test</text>')
        style = converter._get_font_style(element)
        assert style == 'normal'
    
    def test_get_fill_color_xml(self, converter):
        """Test fill color extraction as DrawingML XML."""
        element = ET.fromstring('<text fill="red">Test</text>')
        # Use ColorParser to get expected hex value
        color_parser = ColorParser()
        expected_hex = color_parser.parse('red').hex.upper()
        with patch.object(converter, 'parse_color', return_value=expected_hex):
            color_xml = converter._get_fill_color_xml(element)
            assert '<a:solidFill>' in color_xml
            assert expected_hex in color_xml
    
    def test_get_text_decorations(self, converter):
        """Test text decoration extraction."""
        element = ET.fromstring('<text text-decoration="underline">Test</text>')
        decorations = converter._get_text_decorations(element)
        assert 'underline' in decorations
    
    def test_extract_text_properties(self, converter, mock_context):
        """Test comprehensive text property extraction."""
        element = ET.fromstring('''
            <text x="100" y="200" font-family="Arial" font-size="14" 
                  font-weight="bold" fill="blue" text-anchor="middle">
                Test Text
            </text>
        ''')
        
        # Use ColorParser to get expected hex value for blue
        color_parser = ColorParser()
        expected_blue_hex = color_parser.parse('blue').hex.upper()
        with patch.object(converter, 'parse_color', return_value=expected_blue_hex):
            props = converter._extract_text_properties(element, mock_context)
            
            assert props['x'] == 100
            assert props['y'] == 200
            assert 'Arial' in props['font_families']
            assert props['font_size'] > 0
            assert props['font_weight'] == 700  # bold
            assert props['text_anchor'] == 'middle'
            assert '<a:solidFill>' in props['fill_color']
    
    def test_convert_empty_text(self, converter, mock_context):
        """Test conversion of element with empty text."""
        element = ET.fromstring('<text></text>')
        result = converter.convert(element, mock_context)
        assert result == ""
        assert converter.conversion_stats['total_conversions'] == 1
    
    def test_convert_to_path_success(self, converter, mock_context):
        """Test successful conversion to path."""
        element = ET.fromstring('<text x="100" y="200">A</text>')
        
        # Mock the should_convert_to_path to return True
        with patch.object(converter, 'should_convert_to_path', return_value=True), \
             patch.object(converter, '_convert_to_path', return_value='<path_result/>') as mock_convert:
            
            result = converter.convert(element, mock_context)
            assert result == '<path_result/>'
            mock_convert.assert_called_once()
            assert converter.conversion_stats['total_conversions'] == 1
    
    def test_convert_to_regular_text_success(self, converter, mock_context):
        """Test successful conversion to regular text."""
        element = ET.fromstring('<text x="100" y="200">A</text>')
        
        # Mock the should_convert_to_path to return False
        with patch.object(converter, 'should_convert_to_path', return_value=False), \
             patch.object(converter, '_convert_to_regular_text', return_value='<text_result/>') as mock_convert:
            
            result = converter.convert(element, mock_context)
            assert result == '<text_result/>'
            mock_convert.assert_called_once()
            assert converter.conversion_stats['total_conversions'] == 1
    
    def test_convert_exception_handling(self, converter, mock_context):
        """Test exception handling during conversion."""
        element = ET.fromstring('<text>Test</text>')
        
        # Mock extract_text_content to raise an exception
        with patch.object(converter, '_extract_text_content', side_effect=Exception('Test error')):
            result = converter.convert(element, mock_context)
            assert result == ""
            assert converter.conversion_stats['failed_conversions'] == 1
    
    def test_convert_to_path_implementation(self, converter, mock_context):
        """Test internal path conversion implementation."""
        element = ET.fromstring('<text>A</text>')
        text_content = 'A'
        text_props = {
            'font_families': ['Arial'],
            'font_size': 12,
            'font_weight': 400,
            'font_style': 'normal',
            'x': 0,
            'y': 0
        }
        
        # Mock dependencies
        with patch.object(converter.font_analyzer, 'get_font_fallback_chain', return_value=['Arial']), \
             patch.object(converter, '_split_text_lines', return_value=['A']), \
             patch.object(converter.path_generator, 'generate_text_path', return_value='<mock_path/>'), \
             patch.object(converter, '_create_text_path_shape', return_value='<final_shape/>'):
            
            result = converter._convert_to_path(element, text_content, text_props, mock_context)
            assert result == '<final_shape/>'
            assert converter.conversion_stats['successful_conversions'] == 1
            assert converter.conversion_stats['fallback_conversions'] == 1
    
    def test_convert_to_path_no_fonts(self, converter, mock_context):
        """Test path conversion when no fonts are available."""
        element = ET.fromstring('<text>A</text>')
        text_content = 'A'
        text_props = {'font_families': ['UnknownFont']}
        
        with patch.object(converter.font_analyzer, 'get_font_fallback_chain', return_value=[]):
            result = converter._convert_to_path(element, text_content, text_props, mock_context)
            assert result == ""
            assert converter.conversion_stats['failed_conversions'] == 1
    
    def test_convert_to_regular_text_implementation(self, converter, mock_context):
        """Test regular text conversion implementation."""
        element = ET.fromstring('<text>Hello</text>')
        text_content = 'Hello'
        text_props = {
            'x': 100, 'y': 200, 'font_size': 12, 'text_anchor': 'start',
            'font_weight': 400, 'font_style': 'normal',
            'font_families': ['Arial'],
            'fill_color': '<a:solidFill><a:srgbClr val="000000"/></a:solidFill>'
        }
        
        result = converter._convert_to_regular_text(element, text_content, text_props, mock_context)
        
        assert '<a:sp>' in result
        assert '<a:txBody>' in result
        assert 'Hello' in result
        assert converter.conversion_stats['successful_conversions'] == 1
    
    def test_split_text_lines(self, converter):
        """Test text line splitting functionality."""
        element = ET.fromstring('<text>Line 1\nLine 2\n\nLine 3</text>')
        lines = converter._split_text_lines('Line 1\nLine 2\n\nLine 3', element)
        
        assert len(lines) == 3  # Empty lines should be filtered out
        assert 'Line 1' in lines
        assert 'Line 2' in lines
        assert 'Line 3' in lines
    
    def test_create_text_path_shape_single_line(self, converter, mock_context):
        """Test text path shape creation for single line."""
        line_paths = ['<mock_path id="{shape_id}" fill="{fill_color}"/>']
        text_props = {
            'fill_color': '<a:solidFill><a:srgbClr val="FF0000"/></a:solidFill>'
        }
        
        result = converter._create_text_path_shape(line_paths, text_props, mock_context)
        
        assert 'id="100"' in result  # Shape ID should be replaced
        assert 'FF0000' in result    # Fill color should be replaced
    
    def test_create_text_path_shape_multiple_lines(self, converter, mock_context):
        """Test text path shape creation for multiple lines."""
        line_paths = [
            '<mock_path id="{shape_id}" fill="{fill_color}"/>',
            '<mock_path id="{shape_id}" fill="{fill_color}"/>'
        ]
        text_props = {
            'x': 100, 'y': 200,
            'fill_color': '<a:solidFill><a:srgbClr val="0000FF"/></a:solidFill>'
        }
        
        result = converter._create_text_path_shape(line_paths, text_props, mock_context)
        
        assert '<a:grpSp>' in result
        assert result.count('<mock_path') == 2
        assert '0000FF' in result
    
    def test_extract_color_hex(self, converter):
        """Test hex color extraction from DrawingML XML."""
        fill_xml = '<a:solidFill><a:srgbClr val="FF0000"/></a:solidFill>'
        color = converter._extract_color_hex(fill_xml)
        assert color == 'FF0000'
        
        # Test with invalid XML
        color = converter._extract_color_hex('invalid xml')
        assert color == '000000'  # Default color
    
    def test_get_alignment_code(self, converter):
        """Test text alignment code conversion."""
        assert converter._get_alignment_code('start') == 'l'
        assert converter._get_alignment_code('middle') == 'ctr'
        assert converter._get_alignment_code('end') == 'r'
        assert converter._get_alignment_code('unknown') == 'l'  # Default
    
    def test_escape_xml(self, converter):
        """Test XML character escaping."""
        text = 'Hello & "World" < > \''
        escaped = converter._escape_xml(text)
        
        assert '&amp;' in escaped
        assert '&quot;' in escaped
        assert '&lt;' in escaped
        assert '&gt;' in escaped
        assert '&apos;' in escaped
    
    def test_get_conversion_stats(self, converter):
        """Test conversion statistics retrieval."""
        # Simulate some conversions
        converter.conversion_stats['total_conversions'] = 10
        converter.conversion_stats['successful_conversions'] = 8
        converter.conversion_stats['fallback_conversions'] = 3
        converter.conversion_stats['failed_conversions'] = 2
        
        stats = converter.get_conversion_stats()
        
        assert stats['total_conversions'] == 10
        assert stats['successful_conversions'] == 8
        assert stats['fallback_conversions'] == 3
        assert stats['failed_conversions'] == 2
        assert stats['success_rate'] == 0.8
        assert stats['fallback_rate'] == 0.3
    
    def test_get_conversion_stats_zero_conversions(self, converter):
        """Test conversion statistics with zero conversions."""
        stats = converter.get_conversion_stats()
        
        assert stats['success_rate'] == 0.0
        assert stats['fallback_rate'] == 0.0
    
    def test_reset_stats(self, converter):
        """Test statistics reset functionality."""
        # Set some stats
        converter.conversion_stats['total_conversions'] = 5
        converter.conversion_stats['successful_conversions'] = 4
        
        converter.reset_stats()
        
        assert converter.conversion_stats['total_conversions'] == 0
        assert converter.conversion_stats['successful_conversions'] == 0
        assert converter.conversion_stats['fallback_conversions'] == 0
        assert converter.conversion_stats['failed_conversions'] == 0
    
    def test_clear_caches(self, converter):
        """Test cache clearing functionality."""
        with patch.object(converter.font_analyzer, 'clear_cache') as mock_clear:
            converter.clear_caches()
            mock_clear.assert_called_once()
            # Stats should also be reset
            assert converter.conversion_stats['total_conversions'] == 0


@pytest.mark.integration
class TestTextToPathConverterIntegration:
    """Integration tests for TextToPathConverter with real dependencies."""
    
    @pytest.fixture
    def converter(self):
        return TextToPathConverter()
    
    @pytest.fixture
    def context(self):
        coord_system = CoordinateSystem(width=1920, height=1080, viewbox=(0, 0, 1920, 1080))
        return ConversionContext(coordinate_system=coord_system)
    
    def test_end_to_end_conversion_path(self, converter, context):
        """Test end-to-end conversion to path (mocked)."""
        element = ET.fromstring('<text x="100" y="200" font-family="UnknownFont">Hello</text>')
        
        # Force path conversion by making font unavailable
        with patch.object(converter.font_analyzer, 'detect_font_availability', return_value=False), \
             patch.object(converter.font_analyzer, 'get_font_fallback_chain', return_value=[]), \
             patch.object(converter.path_generator, 'generate_text_path', return_value='<mock_path/>'):
            
            result = converter.convert(element, context)
            # Should attempt path conversion even if it fails
            assert converter.conversion_stats['total_conversions'] == 1
    
    def test_end_to_end_conversion_text(self, converter, context):
        """Test end-to-end conversion to regular text."""
        element = ET.fromstring('<text x="100" y="200" font-family="Arial">Hello</text>')
        
        # Make Arial available
        with patch.object(converter.font_analyzer, 'detect_font_availability', return_value=True):
            result = converter.convert(element, context)
            
            assert '<a:sp>' in result  # Should generate text shape
            assert '<a:txBody>' in result
            assert 'Hello' in result
            assert converter.conversion_stats['successful_conversions'] == 1


class TestTextToPathConverterConfiguration:
    """Test configuration handling for TextToPathConverter."""
    
    def test_config_merging(self):
        """Test that custom config merges with defaults."""
        custom_config = {
            'path_optimization_level': 2,
            'custom_setting': 'test_value'
        }
        
        converter = TextToPathConverter(config=custom_config)
        
        # Should merge with defaults
        assert converter.config['font_detection_enabled'] is True  # Default
        assert converter.config['path_optimization_level'] == 2    # Custom
        assert converter.config['custom_setting'] == 'test_value' # Custom
    
    def test_config_none(self):
        """Test initialization with None config."""
        converter = TextToPathConverter(config=None)
        
        # Should use all defaults
        assert converter.config == TextToPathConverter.DEFAULT_CONFIG
    
    def test_config_empty(self):
        """Test initialization with empty config."""
        converter = TextToPathConverter(config={})
        
        # Should use all defaults
        assert converter.config == TextToPathConverter.DEFAULT_CONFIG