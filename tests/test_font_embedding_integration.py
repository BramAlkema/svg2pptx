#!/usr/bin/env python3
"""
Comprehensive Test Suite for Font Embedding Integration
Tests the complete three-tier font strategy implementation
"""

import pytest
import xml.etree.ElementTree as ET
import base64
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Import the components we're testing
from src.converters.text import TextConverter
from src.converters.base import ConversionContext, CoordinateSystem
from src.converters.font_embedding import FontEmbeddingAnalyzer, EmbeddedFontFace
from src.pptx_font_embedder import PPTXFontEmbedder, FontResource


class TestFontEmbeddingIntegration:
    """Test complete font embedding integration in TextConverter"""
    
    @pytest.fixture
    def mock_context(self):
        """Create a mock ConversionContext with necessary attributes"""
        context = ConversionContext()
        context.coordinate_system = CoordinateSystem((0, 0, 100, 100))
        context.embedded_fonts = {}
        return context
    
    @pytest.fixture
    def text_converter_with_embedding(self):
        """Create TextConverter with font embedding enabled"""
        return TextConverter(enable_font_embedding=True, enable_text_to_path_fallback=True)
    
    @pytest.fixture
    def text_converter_without_embedding(self):
        """Create TextConverter with font embedding disabled"""
        return TextConverter(enable_font_embedding=False, enable_text_to_path_fallback=False)
    
    def test_text_converter_initialization_with_font_embedding(self):
        """Test that TextConverter initializes with font embedding components"""
        converter = TextConverter(enable_font_embedding=True)
        
        assert converter.enable_font_embedding == True
        assert converter._font_analyzer is not None
        assert converter._font_embedder is not None
        assert hasattr(converter, '_determine_font_strategy')
        assert hasattr(converter, '_parse_font_weight_value')
    
    def test_text_converter_initialization_without_font_embedding(self):
        """Test that TextConverter works in legacy mode without font embedding"""
        converter = TextConverter(enable_font_embedding=False)
        
        assert converter.enable_font_embedding == False
        assert converter._font_analyzer is None
        assert converter._font_embedder is None
    
    def test_parse_font_weight_value(self, text_converter_with_embedding):
        """Test font weight parsing from various formats"""
        converter = text_converter_with_embedding
        
        # Numeric weights
        assert converter._parse_font_weight_value('400') == 400
        assert converter._parse_font_weight_value('700') == 700
        assert converter._parse_font_weight_value('900') == 900
        
        # Named weights
        assert converter._parse_font_weight_value('normal') == 400
        assert converter._parse_font_weight_value('bold') == 700
        assert converter._parse_font_weight_value('lighter') == 200
        assert converter._parse_font_weight_value('bolder') == 800
        
        # Extended named weights
        assert converter._parse_font_weight_value('thin') == 100
        assert converter._parse_font_weight_value('light') == 300
        assert converter._parse_font_weight_value('medium') == 500
        assert converter._parse_font_weight_value('semibold') == 600
        assert converter._parse_font_weight_value('extra-bold') == 800
        assert converter._parse_font_weight_value('black') == 900
        
        # Default for unknown
        assert converter._parse_font_weight_value('unknown') == 400
    
    def test_get_font_variant_name(self, text_converter_with_embedding):
        """Test font variant naming for embedding slots"""
        converter = text_converter_with_embedding
        
        # Regular
        assert converter._get_font_variant_name(400, False) == 'regular'
        assert converter._get_font_variant_name(300, False) == 'regular'
        
        # Bold
        assert converter._get_font_variant_name(700, False) == 'bold'
        assert converter._get_font_variant_name(800, False) == 'bold'
        
        # Italic
        assert converter._get_font_variant_name(400, True) == 'italic'
        assert converter._get_font_variant_name(300, True) == 'italic'
        
        # Bold Italic
        assert converter._get_font_variant_name(700, True) == 'bolditalic'
        assert converter._get_font_variant_name(900, True) == 'bolditalic'
    
    def test_determine_font_strategy_embedded(self, text_converter_with_embedding, mock_context):
        """Test font strategy determination when embedded font exists"""
        converter = text_converter_with_embedding
        
        # Add embedded font to context
        mock_context.embedded_fonts = {
            'CustomFont': {
                'regular': b'fake_font_bytes',
                'bold': b'fake_font_bytes_bold'
            }
        }
        
        # Should return 'embedded' for available variant
        strategy = converter._determine_font_strategy('CustomFont', 400, False, mock_context)
        assert strategy == 'embedded'
        
        # Should return 'embedded' for bold variant
        strategy = converter._determine_font_strategy('CustomFont', 700, False, mock_context)
        assert strategy == 'embedded'
        
        # Should fall back for unavailable italic variant
        strategy = converter._determine_font_strategy('CustomFont', 400, True, mock_context)
        assert strategy == 'convert_to_path'
    
    @patch('src.converters.font_embedding.FontEmbeddingAnalyzer.load_system_font')
    def test_determine_font_strategy_system(self, mock_load_font, text_converter_with_embedding, mock_context):
        """Test font strategy determination for system fonts"""
        converter = text_converter_with_embedding
        
        # Mock system font availability
        mock_load_font.return_value = b'system_font_bytes'
        
        # Should return 'system' when font is available
        strategy = converter._determine_font_strategy('Arial', 400, False, mock_context)
        assert strategy == 'system'
        
        # Verify the system font check was called
        mock_load_font.assert_called_with(
            'Arial', 400, False, ['Arial', 'Helvetica', 'sans-serif']
        )
    
    @patch('src.converters.font_embedding.FontEmbeddingAnalyzer.load_system_font')
    def test_determine_font_strategy_path_fallback(self, mock_load_font, text_converter_with_embedding, mock_context):
        """Test font strategy falls back to path conversion"""
        converter = text_converter_with_embedding
        
        # Mock system font unavailable
        mock_load_font.return_value = None
        
        # Should return 'convert_to_path' when no font available
        strategy = converter._determine_font_strategy('UnknownFont', 400, False, mock_context)
        assert strategy == 'convert_to_path'
    
    def test_register_embedded_font(self, text_converter_with_embedding, mock_context):
        """Test registration of embedded fonts for PPTX"""
        converter = text_converter_with_embedding
        
        # Add embedded font to context
        font_bytes = b'test_font_data'
        mock_context.embedded_fonts = {
            'TestFont': {
                'regular': font_bytes
            }
        }
        
        # Mock the font embedder
        converter._font_embedder = Mock()
        
        # Register the font
        converter._register_embedded_font('TestFont', 400, False, mock_context)
        
        # Verify font was added to embedder
        converter._font_embedder.add_font_embed.assert_called_once_with(
            'TestFont', 'regular', font_bytes
        )
    
    @patch('src.converters.font_embedding.FontEmbeddingAnalyzer.load_system_font')
    def test_register_system_font(self, mock_load_font, text_converter_with_embedding, mock_context):
        """Test registration of system fonts for PPTX"""
        converter = text_converter_with_embedding
        
        # Mock system font loading
        font_bytes = b'system_font_data'
        mock_load_font.return_value = font_bytes
        
        # Mock the font embedder
        converter._font_embedder = Mock()
        
        # Register the system font
        converter._register_system_font('Helvetica', 700, False, mock_context)
        
        # Verify font was loaded and added to embedder
        mock_load_font.assert_called_once()
        converter._font_embedder.add_font_embed.assert_called_once_with(
            'Helvetica', 'bold', font_bytes
        )
    
    def test_convert_with_embedded_font_strategy(self, text_converter_with_embedding, mock_context):
        """Test end-to-end conversion with embedded font strategy"""
        converter = text_converter_with_embedding
        
        # Create SVG text element
        svg_text = '<text x="10" y="20" font-family="EmbeddedFont" font-size="14" font-weight="bold">Hello World</text>'
        element = ET.fromstring(svg_text)
        
        # Add embedded font to context
        mock_context.embedded_fonts = {
            'EmbeddedFont': {
                'bold': b'embedded_font_bytes'
            }
        }
        
        # Mock the font embedder
        converter._font_embedder = Mock()
        
        # Convert the element
        result = converter.convert(element, mock_context)
        
        # Verify result is not empty
        assert result != ""
        
        # Verify font was registered
        converter._font_embedder.add_font_embed.assert_called()
    
    def test_convert_with_path_fallback(self, text_converter_with_embedding, mock_context):
        """Test conversion falls back to path when font unavailable"""
        converter = text_converter_with_embedding
        
        # Create SVG text with unavailable font
        svg_text = '<text x="10" y="20" font-family="UnknownFont" font-size="14">Test</text>'
        element = ET.fromstring(svg_text)
        
        # Mock text-to-path converter
        converter._text_to_path_converter = Mock()
        converter._text_to_path_converter.convert.return_value = '<path d="M 0 0 L 10 10"/>'
        
        # Convert the element
        result = converter.convert(element, mock_context)
        
        # Verify path conversion was called
        converter._text_to_path_converter.convert.assert_called_once_with(element, mock_context)
        assert result == '<path d="M 0 0 L 10 10"/>'
    
    def test_convert_legacy_mode(self, text_converter_without_embedding, mock_context):
        """Test conversion works in legacy mode without font embedding"""
        converter = text_converter_without_embedding
        
        # Create SVG text element
        svg_text = '<text x="10" y="20" font-family="Arial" font-size="14">Legacy Text</text>'
        element = ET.fromstring(svg_text)
        
        # Convert should work without font embedding
        result = converter.convert(element, mock_context)
        
        # Verify result contains DrawingML text
        assert result != ""
        assert 'a:t' in result or 'text' in result.lower()
    
    def test_three_tier_strategy_priority(self, text_converter_with_embedding, mock_context):
        """Test that three-tier strategy follows correct priority order"""
        converter = text_converter_with_embedding
        
        # Priority 1: Embedded font should be chosen first
        mock_context.embedded_fonts = {'Font1': {'regular': b'data'}}
        strategy = converter._determine_font_strategy('Font1', 400, False, mock_context)
        assert strategy == 'embedded'
        
        # Priority 2: System font when no embedded font
        with patch.object(converter._font_analyzer, 'load_system_font', return_value=b'system'):
            strategy = converter._determine_font_strategy('Arial', 400, False, mock_context)
            assert strategy == 'system'
        
        # Priority 3: Path conversion as last resort
        with patch.object(converter._font_analyzer, 'load_system_font', return_value=None):
            strategy = converter._determine_font_strategy('UnknownFont', 400, False, mock_context)
            assert strategy == 'convert_to_path'


class TestFontEmbeddingAnalyzer:
    """Test FontEmbeddingAnalyzer functionality"""
    
    def test_parse_fontface_with_data_url(self):
        """Test parsing @font-face with base64 data URL"""
        css_content = """
        @font-face {
            font-family: 'TestFont';
            font-style: normal;
            font-weight: 400;
            src: url(data:font/woff2;base64,SGVsbG8gV29ybGQ=);
        }
        """
        
        analyzer = FontEmbeddingAnalyzer()
        # Test actual parsing implementation
        faces = FontEmbeddingAnalyzer.parse_fontface_css(css_content)
        assert len(faces) == 1
        assert faces[0].family == 'TestFont'
        assert faces[0].weight == 400
        assert faces[0].style == 'normal'
        assert faces[0].font_bytes == b'Hello World'
        
        # Verify the analyzer exists and has expected methods
        assert hasattr(analyzer, 'parse_fontface_css')
        assert hasattr(analyzer, 'load_system_font')
        assert hasattr(analyzer, 'analyze_svg_fonts')
    
    def test_get_font_slot(self):
        """Test font slot determination for variants"""
        analyzer = FontEmbeddingAnalyzer()
        
        # Test slot naming
        assert analyzer.get_font_slot(400, False) == 'regular'
        assert analyzer.get_font_slot(700, False) == 'bold'
        assert analyzer.get_font_slot(400, True) == 'italic'
        assert analyzer.get_font_slot(700, True) == 'bolditalic'


class TestPPTXFontEmbedder:
    """Test PPTXFontEmbedder functionality"""
    
    def test_add_font_embed(self):
        """Test adding fonts for embedding"""
        embedder = PPTXFontEmbedder()
        
        # Add a font
        font_bytes = b'test_font_data'
        resource_id = embedder.add_font_embed('TestFont', 'regular', font_bytes)
        
        # Verify font was added
        assert 'TestFont' in embedder.embedded_fonts
        assert 'regular' in embedder.embedded_fonts['TestFont']
        assert embedder.embedded_fonts['TestFont']['regular'].font_bytes == font_bytes
        assert resource_id.startswith('font')
    
    def test_get_font_reference(self):
        """Test getting font references for embedded fonts"""
        embedder = PPTXFontEmbedder()
        
        # Add a font
        font_bytes = b'test_font_data'
        embedder.add_font_embed('TestFont', 'bold', font_bytes)
        
        # Get reference
        ref = embedder.get_font_reference('TestFont', 700, False)
        assert ref is not None
        
        # Non-existent font should return None
        ref = embedder.get_font_reference('UnknownFont', 400, False)
        assert ref is None
    
    def test_create_font_embedding_manifest(self):
        """Test manifest generation for debugging"""
        embedder = PPTXFontEmbedder()
        
        # Add some fonts
        embedder.add_font_embed('Font1', 'regular', b'data1')
        embedder.add_font_embed('Font1', 'bold', b'data2')
        embedder.add_font_embed('Font2', 'italic', b'data3')
        
        # Generate manifest
        manifest = embedder.create_font_embedding_manifest()
        
        assert manifest['total_families'] == 2
        assert manifest['total_variants'] == 3
        assert 'Font1' in manifest['families']
        assert 'Font2' in manifest['families']
        assert len(manifest['families']['Font1']['variants']) == 2


class TestEndToEndFontEmbedding:
    """Test complete SVG to PPTX conversion with font embedding"""
    
    def test_svg_with_embedded_font_to_pptx(self):
        """Test converting SVG with @font-face to PPTX with embedded fonts"""
        # This would be a full integration test
        svg_content = """
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 100">
            <defs>
                <style>
                @font-face {
                    font-family: 'CustomFont';
                    src: url(data:font/woff2;base64,SGVsbG8=);
                }
                </style>
            </defs>
            <text x="10" y="50" font-family="CustomFont" font-size="20">
                Custom Font Text
            </text>
        </svg>
        """
        
        # Create converter
        converter = TextConverter(enable_font_embedding=True)
        context = ConversionContext()
        context.coordinate_system = CoordinateSystem((0, 0, 200, 100))
        
        # This would test the full pipeline
        # For now, verify the converter can handle the input
        root = ET.fromstring(svg_content)
        text_elem = root.find('.//{http://www.w3.org/2000/svg}text')
        
        if text_elem is not None:
            assert converter.can_convert(text_elem)
    
    def test_font_strategy_performance(self):
        """Test font strategy performance characteristics (informational)"""
        import time
        
        # Create converters
        converter_with = TextConverter(enable_font_embedding=True)
        converter_without = TextConverter(enable_font_embedding=False)
        
        # Create test element
        svg_text = '<text x="10" y="20" font-family="Arial">Performance Test</text>'
        element = ET.fromstring(svg_text)
        
        context = ConversionContext()
        context.coordinate_system = CoordinateSystem((0, 0, 100, 100))
        
        # Measure with font embedding (single iteration to avoid repeated font loading)
        start = time.time()
        result_with = converter_with.convert(element, context)
        time_with = time.time() - start
        
        # Measure without font embedding
        start = time.time()
        result_without = converter_without.convert(element, context)
        time_without = time.time() - start
        
        # Both should produce valid results
        assert result_with != ""
        assert result_without != ""
        
        # Log performance for information (font loading is inherently expensive)
        ratio = time_with / time_without if time_without > 0 else float('inf')
        print(f"Performance ratio (with/without font embedding): {ratio:.2f}x")
        print(f"Time with embedding: {time_with:.4f}s")
        print(f"Time without embedding: {time_without:.4f}s")
        
        # Just ensure both complete in reasonable time (under 1 second each)
        assert time_with < 1.0, f"Font embedding took too long: {time_with:.3f}s"
        assert time_without < 1.0, f"Regular conversion took too long: {time_without:.3f}s"


if __name__ == '__main__':
    # Run tests with pytest
    pytest.main([__file__, '-v', '--tb=short'])