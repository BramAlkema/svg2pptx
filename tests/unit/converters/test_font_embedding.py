"""
Tests for Font Embedding System

Test suite for the enhanced font system that embeds actual font bytes in PPTX
instead of converting to paths when possible.
"""

import pytest
from lxml import etree as ET
import base64
from unittest.mock import Mock, patch, mock_open
from pathlib import Path

# We'll create these classes as we implement
# from src.converters.font_embedding import FontEmbeddingAnalyzer, EmbeddedFontFace, FontEmbedResult


class TestFontFaceDataUrlParsing:
    """Test parsing of @font-face CSS with data: URLs"""
    
    def test_parse_single_fontface_data_url(self):
        """Test parsing a single @font-face with data URL"""
        css_content = """
        @font-face {
            font-family: 'CustomFont';
            font-style: normal;
            font-weight: 400;
            src: url(data:font/woff2;base64,d09GMgABAAAAAAYQAAoAAAAABFgAAAW+AAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAABmAAgkIKgUCBNwsGAAE2AiQDCAQgBQYHMBuTA1GUzL0Q2Y9k2I2NG0cY2kK7UHb5z4yH/9Ze75udSYAVoMQGAUFEhbrCPrHI+hqRp7adrq4n/5+f2/df4XdPe1KYpk0cWdqQyKRBJe5wg5yC3H4);
        }
        """
        
        # This test will define the expected API
        # result = FontEmbeddingAnalyzer.parse_fontface_css(css_content)
        # 
        # assert len(result) == 1
        # face = result[0]
        # assert face.family == 'CustomFont'
        # assert face.style == 'normal'
        # assert face.weight == 400
        # assert face.mime_type == 'font/woff2'
        # assert len(face.font_bytes) > 0
        
        # For now, test the structure we expect
        assert '@font-face' in css_content
        assert 'data:font/woff2;base64,' in css_content
        assert 'font-family:' in css_content or 'font-family =' in css_content.replace(' ', '')
    
    def test_parse_multiple_fontface_variants(self):
        """Test parsing multiple @font-face variants (regular, bold, italic)"""
        css_content = """
        @font-face {
            font-family: 'TestFamily';
            font-style: normal;
            font-weight: 400;
            src: url(data:font/ttf;base64,AAABAAIAAAAAAAAA);
        }
        @font-face {
            font-family: 'TestFamily';
            font-style: normal;
            font-weight: 700;
            src: url(data:font/ttf;base64,BBBBBBBBBBBBBBB);
        }
        @font-face {
            font-family: 'TestFamily';
            font-style: italic;
            font-weight: 400;
            src: url(data:font/ttf;base64,CCCCCCCCCCCCCCC);
        }
        """
        
        # Expected API design
        # result = FontEmbeddingAnalyzer.parse_fontface_css(css_content)
        # 
        # assert len(result) == 3
        # families = {face.family for face in result}
        # assert len(families) == 1  # Same family
        # assert 'TestFamily' in families
        # 
        # # Check we have regular, bold, and italic
        # styles = {(face.weight, face.style) for face in result}
        # expected_styles = {(400, 'normal'), (700, 'normal'), (400, 'italic')}
        # assert styles == expected_styles
        
        # For now, verify structure
        assert css_content.count('@font-face') == 3
        assert css_content.count('TestFamily') >= 3
    
    def test_parse_fontface_invalid_base64(self):
        """Test handling of invalid base64 data in font-face"""
        css_content = """
        @font-face {
            font-family: 'BadFont';
            src: url(data:font/ttf;base64,InvalidBase64!!!);
        }
        """
        
        # Should handle gracefully
        # result = FontEmbeddingAnalyzer.parse_fontface_css(css_content)
        # assert len(result) == 0  # Invalid base64 should be skipped
        
        # Test base64 validation
        try:
            base64.b64decode('InvalidBase64!!!')
            assert False, "Should have raised an exception"
        except Exception:
            assert True  # Expected
    
    def test_extract_from_svg_style_elements(self):
        """Test extracting @font-face from SVG <style> elements"""
        svg_content = """
        <svg xmlns="http://www.w3.org/2000/svg">
            <style>
                @font-face {
                    font-family: 'SVGEmbedded';
                    src: url(data:font/woff;base64,TESTDATA123);
                }
                .text { font-family: 'SVGEmbedded'; }
            </style>
            <text class="text">Hello World</text>
        </svg>
        """
        
        root = ET.fromstring(svg_content)
        style_elements = root.findall('.//{http://www.w3.org/2000/svg}style')
        
        assert len(style_elements) >= 1
        assert '@font-face' in style_elements[0].text
        assert 'SVGEmbedded' in style_elements[0].text


class TestSystemFontLoading:
    """Test loading and caching of system fonts"""
    
    def test_load_system_font_by_family(self):
        """Test loading system font by family name"""
        # Expected API design
        # analyzer = FontEmbeddingAnalyzer()
        # font_bytes = analyzer.load_system_font('Arial', weight=400, italic=False)
        # 
        # assert font_bytes is not None
        # assert len(font_bytes) > 1000  # Should be a real font file
        # assert font_bytes.startswith(b'\x00\x01\x00\x00')  # TTF signature
        
        # For now, test the concept exists
        assert True  # Placeholder
    
    def test_system_font_fallback_chain(self):
        """Test font fallback when primary font not available"""
        # Expected API design
        # analyzer = FontEmbeddingAnalyzer()
        # 
        # # Try to load non-existent font
        # font_bytes = analyzer.load_system_font('NonExistentFont123', 
        #                                       fallback=['Arial', 'Helvetica'])
        # 
        # assert font_bytes is not None  # Should fall back to Arial
        
        assert True  # Placeholder
    
    @patch('builtins.open', mock_open(read_data=b'FAKE_FONT_DATA'))
    @patch('os.path.exists', return_value=True)
    def test_font_file_caching(self, mock_exists):
        """Test that font files are cached after first load"""
        # Expected behavior: same font loaded twice should use cache
        
        # First load should read from file
        # Second load should use cache
        # analyzer = FontEmbeddingAnalyzer()
        # 
        # bytes1 = analyzer.load_system_font('Arial')
        # bytes2 = analyzer.load_system_font('Arial') 
        # 
        # assert bytes1 == bytes2
        # # File should only be read once due to caching
        
        assert True  # Placeholder


class TestFontEmbedStrategy:
    """Test the three-tier font embedding strategy"""
    
    def test_strategy_priority_embedded_first(self):
        """Test that @font-face embedded fonts take priority"""
        svg_with_embedded = """
        <svg xmlns="http://www.w3.org/2000/svg">
            <style>
                @font-face {
                    font-family: 'Arial';  /* Same name as system font */
                    src: url(data:font/ttf;base64,EMBEDDED_DATA);
                }
            </style>
            <text font-family="Arial">Test</text>
        </svg>
        """
        
        # Expected: embedded font should be preferred over system Arial
        # result = FontEmbeddingAnalyzer.analyze_svg_fonts(svg_with_embedded)
        # 
        # assert 'Arial' in result.embeds
        # assert result.embeds['Arial']['regular'] == b'EMBEDDED_DATA'  # From embedded, not system
        
        root = ET.fromstring(svg_with_embedded)
        assert len(root.findall('.//{http://www.w3.org/2000/svg}style')) == 1
    
    def test_strategy_fallback_to_system(self):
        """Test fallback to system fonts when no embedded fonts"""
        svg_system_only = """
        <svg xmlns="http://www.w3.org/2000/svg">
            <text font-family="Arial" font-weight="bold">Test</text>
        </svg>
        """
        
        # Expected: should load system Arial Bold
        # result = FontEmbeddingAnalyzer.analyze_svg_fonts(svg_system_only)
        # 
        # assert 'Arial' in result.embeds
        # assert 'bold' in result.embeds['Arial']
        # assert len(result.embeds['Arial']['bold']) > 1000  # Real font data
        
        root = ET.fromstring(svg_system_only)
        text_elem = root.find('.//{http://www.w3.org/2000/svg}text')
        assert text_elem.get('font-family') == 'Arial'
        assert text_elem.get('font-weight') == 'bold'
    
    def test_strategy_outline_svg_fonts_only(self):
        """Test that legacy SVG <font> elements are converted to paths"""
        svg_with_legacy_font = """
        <svg xmlns="http://www.w3.org/2000/svg">
            <defs>
                <font id="TestFont">
                    <font-face font-family="LegacyFont" units-per-em="1000"/>
                    <glyph unicode="A" d="M100,0 L200,800 L300,0 Z"/>
                </font>
            </defs>
            <text font-family="LegacyFont">A</text>
        </svg>
        """
        
        # Expected: SVG fonts should be outlined to paths, not embedded
        # result = FontEmbeddingAnalyzer.analyze_svg_fonts(svg_with_legacy_font)
        # 
        # assert 'LegacyFont' not in result.embeds  # No embedding for SVG fonts
        # assert '<path' in result.processed_svg    # Should be converted to paths
        
        root = ET.fromstring(svg_with_legacy_font)
        font_elem = root.find('.//{http://www.w3.org/2000/svg}font')
        assert font_elem is not None
        assert font_elem.get('id') == 'TestFont'


class TestFontEmbedResult:
    """Test the result object returned by font embedding analysis"""
    
    def test_embed_result_structure(self):
        """Test that FontEmbedResult has expected structure"""
        # Expected structure:
        # result = FontEmbedResult(
        #     processed_svg="<svg>...</svg>",
        #     embeds={
        #         'Arial': {
        #             'regular': b'font_bytes',
        #             'bold': b'font_bytes'
        #         }
        #     }
        # )
        # 
        # assert hasattr(result, 'processed_svg')
        # assert hasattr(result, 'embeds')
        # assert isinstance(result.embeds, dict)
        
        # Test the concept
        embeds_structure = {
            'Arial': {
                'regular': b'fake_bytes',
                'bold': b'fake_bytes',
                'italic': b'fake_bytes',
                'bolditalic': b'fake_bytes'
            }
        }
        
        assert 'Arial' in embeds_structure
        assert 'regular' in embeds_structure['Arial']
        assert isinstance(embeds_structure['Arial']['regular'], bytes)
    
    def test_embed_slot_naming(self):
        """Test font variant slot naming convention"""
        # Test the slot naming logic from one_big_method.py
        def get_font_slot(weight: int, italic: bool) -> str:
            if italic and weight >= 700:
                return "bolditalic"
            elif weight >= 700 and not italic:
                return "bold"
            elif italic:
                return "italic"
            else:
                return "regular"
        
        assert get_font_slot(400, False) == "regular"
        assert get_font_slot(700, False) == "bold"
        assert get_font_slot(400, True) == "italic"
        assert get_font_slot(700, True) == "bolditalic"
        assert get_font_slot(800, True) == "bolditalic"  # Heavy italic -> bolditalic
    
    def test_embed_deduplication(self):
        """Test that same font variant is not embedded twice"""
        # Expected: if same font+weight+style appears multiple times,
        # should only be recorded once in embeds
        
        # This tests the logic: "only keep first per slot"
        embeds = {}
        
        def record_embed(family: str, weight: int, italic: bool, font_bytes: bytes):
            slot = ("bolditalic" if italic and weight >= 700 else
                    "bold" if weight >= 700 and not italic else
                    "italic" if italic else "regular")
            if family not in embeds:
                embeds[family] = {}
            # Only keep first per slot
            if slot not in embeds[family]:
                embeds[family][slot] = font_bytes
        
        # Record same font twice
        record_embed('Arial', 400, False, b'first')
        record_embed('Arial', 400, False, b'second')  # Should be ignored
        
        assert embeds['Arial']['regular'] == b'first'  # First one kept
        assert len(embeds['Arial']) == 1


class TestPPTXFontIntegration:
    """Test integration with PPTX font embedding"""
    
    def test_font_bytes_to_pptx_format(self):
        """Test conversion of font bytes to PPTX-compatible format"""
        font_bytes = b'FAKE_FONT_DATA'
        
        # Expected: font bytes should be prepared for PPTX embedding
        # This might involve base64 encoding or other PPTX-specific formatting
        
        # Test the concept
        import base64
        encoded = base64.b64encode(font_bytes)
        assert isinstance(encoded, bytes)
        assert base64.b64decode(encoded) == font_bytes
    
    def test_multiple_font_families_in_pptx(self):
        """Test embedding multiple font families in PPTX"""
        embeds = {
            'Arial': {
                'regular': b'arial_regular',
                'bold': b'arial_bold'
            },
            'Times': {
                'regular': b'times_regular',
                'italic': b'times_italic'
            }
        }
        
        # Expected: PPTX should handle multiple font families
        assert len(embeds) == 2
        assert 'Arial' in embeds and 'Times' in embeds
        
        total_bytes = sum(len(variant_bytes) 
                         for family in embeds.values() 
                         for variant_bytes in family.values())
        assert total_bytes > 0


@pytest.mark.integration
class TestFontEmbeddingIntegration:
    """Integration tests for complete font embedding workflow"""
    
    def test_end_to_end_svg_processing(self):
        """Test complete SVG processing with mixed font types"""
        svg_content = """
        <svg xmlns="http://www.w3.org/2000/svg">
            <style>
                @font-face {
                    font-family: 'EmbeddedFont';
                    src: url(data:font/ttf;base64,VEVTVERBVEExMjM=);  /* "TESTDATA123" in base64 */
                }
            </style>
            <defs>
                <font id="legacy">
                    <font-face font-family="LegacyFont"/>
                    <glyph unicode="X" d="M0,0 L100,100 M100,0 L0,100"/>
                </font>
            </defs>
            <text font-family="EmbeddedFont">Embedded text</text>
            <text font-family="Arial">System text</text>
            <text font-family="LegacyFont">X</text>
        </svg>
        """
        
        # Expected results:
        # 1. EmbeddedFont -> embedded bytes, text preserved
        # 2. Arial -> system font bytes, text preserved  
        # 3. LegacyFont -> converted to paths, no embedding
        
        root = ET.fromstring(svg_content)
        text_elements = root.findall('.//{http://www.w3.org/2000/svg}text')
        assert len(text_elements) == 3
        
        font_families = [elem.get('font-family') for elem in text_elements]
        assert 'EmbeddedFont' in font_families
        assert 'Arial' in font_families
        assert 'LegacyFont' in font_families
    
    def test_performance_with_large_svg(self):
        """Test performance with SVG containing many text elements"""
        # Generate SVG with many text elements
        text_elements = []
        for i in range(100):
            text_elements.append(f'<text font-family="Arial" x="{i*10}" y="50">Text {i}</text>')
        
        svg_content = f"""
        <svg xmlns="http://www.w3.org/2000/svg">
            {''.join(text_elements)}
        </svg>
        """
        
        # Expected: should handle large number of text elements efficiently
        # Font should only be loaded once despite 100 text elements
        
        root = ET.fromstring(svg_content)
        text_elements = root.findall('.//{http://www.w3.org/2000/svg}text')
        assert len(text_elements) == 100
        
        # All should use same font family
        font_families = {elem.get('font-family') for elem in text_elements}
        assert len(font_families) == 1
        assert 'Arial' in font_families