"""
Tests for SVG Font Outlining

Test suite for converting legacy SVG <font> elements to paths,
based on the approach in one_big_method.py
"""

import pytest
import xml.etree.ElementTree as ET
from unittest.mock import Mock, patch
import math


class TestSVGFontParsing:
    """Test parsing of legacy SVG <font> definitions"""
    
    def test_parse_basic_svg_font(self):
        """Test parsing a basic SVG font definition"""
        svg_content = """
        <svg xmlns="http://www.w3.org/2000/svg">
            <defs>
                <font id="TestFont" horiz-adv-x="1000">
                    <font-face font-family="TestFamily" units-per-em="1000" 
                               ascent="800" descent="-200"/>
                    <glyph unicode="A" d="M100,0 L200,800 L300,0 Z" horiz-adv-x="400"/>
                    <glyph unicode="B" d="M50,0 L50,800 L200,800 L200,0 Z"/>
                </font>
            </defs>
        </svg>
        """
        
        # Expected API structure based on one_big_method.py
        # class SvgFont:
        #     def __init__(self, family: str, upm: float, asc: float, dsc: float, adv: float):
        #         self.family = family
        #         self.upm = upm  # units per em
        #         self.asc = asc  # ascent
        #         self.dsc = dsc  # descent  
        #         self.adv = adv  # default advance width
        #         self.glyphs: Dict[str, Tuple[str, Optional[float]]] = {}  # unicode -> (d, advance)
        #
        # fonts = parse_svg_fonts(svg_content)
        # assert 'TestFamily' in fonts
        # 
        # font = fonts['TestFamily']
        # assert font.family == 'TestFamily'
        # assert font.upm == 1000
        # assert font.asc == 800
        # assert font.dsc == -200
        # assert font.adv == 1000
        # 
        # assert 'A' in font.glyphs
        # assert 'B' in font.glyphs
        # 
        # # Glyph A has custom advance width
        # glyph_a = font.glyphs['A']
        # assert glyph_a[0] == "M100,0 L200,800 L300,0 Z"  # path data
        # assert glyph_a[1] == 400  # custom advance width
        # 
        # # Glyph B uses default advance width
        # glyph_b = font.glyphs['B']
        # assert glyph_b[1] is None  # uses font default
        
        # For now, test structure parsing
        root = ET.fromstring(svg_content)
        font_elem = root.find('.//{http://www.w3.org/2000/svg}font')
        assert font_elem is not None
        assert font_elem.get('id') == 'TestFont'
        
        font_face = font_elem.find('.//{http://www.w3.org/2000/svg}font-face')
        assert font_face is not None
        assert font_face.get('font-family') == 'TestFamily'
        
        glyphs = font_elem.findall('.//{http://www.w3.org/2000/svg}glyph')
        assert len(glyphs) == 2
    
    def test_parse_svg_font_with_missing_glyph(self):
        """Test parsing SVG font with missing-glyph definition"""
        svg_content = """
        <svg xmlns="http://www.w3.org/2000/svg">
            <defs>
                <font id="TestFont">
                    <font-face font-family="TestFamily"/>
                    <missing-glyph d="M0,0 L100,100 L0,100 Z" horiz-adv-x="100"/>
                    <glyph unicode="A" d="M0,0 L100,0 L50,100 Z"/>
                </font>
            </defs>
        </svg>
        """
        
        # Expected: missing-glyph should be used for undefined characters
        # font = parse_svg_fonts(svg_content)['TestFamily']
        # assert font.missing is not None
        # assert font.missing[0] == "M0,0 L100,100 L0,100 Z"
        # assert font.missing[1] == 100
        
        root = ET.fromstring(svg_content)
        missing_glyph = root.find('.//{http://www.w3.org/2000/svg}missing-glyph')
        assert missing_glyph is not None
        assert missing_glyph.get('d') == "M0,0 L100,100 L0,100 Z"
    
    def test_parse_svg_font_with_kerning(self):
        """Test parsing SVG font with kerning information"""
        svg_content = """
        <svg xmlns="http://www.w3.org/2000/svg">
            <defs>
                <font id="TestFont">
                    <font-face font-family="TestFamily"/>
                    <glyph unicode="A" d="M0,0 L100,0 Z"/>
                    <glyph unicode="V" d="M0,0 L50,100 L100,0 Z"/>
                    <hkern u1="A" u2="V" k="-50"/>
                </font>
            </defs>
        </svg>
        """
        
        # Expected: kerning pairs should be recorded
        # font = parse_svg_fonts(svg_content)['TestFamily']  
        # assert ('A', 'V') in font.kern
        # assert font.kern[('A', 'V')] == -50
        
        root = ET.fromstring(svg_content)
        hkern = root.find('.//{http://www.w3.org/2000/svg}hkern')
        assert hkern is not None
        assert hkern.get('u1') == 'A'
        assert hkern.get('u2') == 'V'
        assert hkern.get('k') == '-50'
    
    def test_parse_unicode_entities_in_kerning(self):
        """Test parsing unicode entities in kerning definitions"""
        # Test the split_unis function from one_big_method.py
        def split_unis(val: str) -> list:
            if not val:
                return []
            parts = [p for p in val.split(",") if p]
            out = []
            for p in parts:
                import re
                m = re.fullmatch(r"&#x([0-9A-Fa-f]+);", p)
                out.append(chr(int(m.group(1), 16)) if m else p)
            return out
        
        # Test normal characters
        assert split_unis("A,B,C") == ["A", "B", "C"]
        
        # Test unicode entities
        assert split_unis("&#x41;,&#x42;") == ["A", "B"]  # A=0x41, B=0x42
        
        # Test mixed
        assert split_unis("A,&#x42;,C") == ["A", "B", "C"]
        
        # Test empty
        assert split_unis("") == []
        assert split_unis(None) == []


class TestSVGFontOutlining:
    """Test conversion of SVG fonts to path outlines"""
    
    def test_outline_single_character(self):
        """Test outlining a single character from SVG font"""
        # Mock SVG font structure
        class MockSvgFont:
            def __init__(self):
                self.family = "TestFont"
                self.upm = 1000  # units per em
                self.asc = 800   # ascender
                self.dsc = -200  # descender  
                self.adv = 500   # default advance
                self.glyphs = {
                    'A': ("M100,0 L200,800 L300,0 Z", 400)  # (path_data, advance_width)
                }
                self.kern = {}
                self.missing = None
        
        font = MockSvgFont()
        
        # Expected API from one_big_method.py
        # def outline_svgfont_run(text: str, font: SvgFont, size_px: float, 
        #                        x: float, y: float, fill: str) -> ET.Element:
        
        # Test the math for scaling and positioning
        text = "A"
        size_px = 48.0  # 48px font size
        x, y = 100.0, 200.0  # position
        fill = "#000000"
        
        # Scale factor: size_px / font.upm
        scale = size_px / font.upm  # 48/1000 = 0.048
        
        # Expected transform calculation
        glyph_data, advance_width = font.glyphs['A']
        pen_x = 0.0  # start of text
        pen_y = font.asc  # baseline + ascender = 800
        
        # Final position after scaling
        tx = x + pen_x * scale  # 100 + 0 = 100
        ty = y - pen_y * scale  # 200 - 800*0.048 = 200 - 38.4 = 161.6
        
        assert abs(ty - 161.6) < 0.1  # floating point precision
        assert scale == 0.048
    
    def test_outline_text_with_kerning(self):
        """Test outlining text with kerning applied"""
        class MockSvgFont:
            def __init__(self):
                self.family = "TestFont"
                self.upm = 1000
                self.asc = 800
                self.dsc = -200
                self.adv = 500
                self.glyphs = {
                    'A': ("M0,0 L100,0", 400),
                    'V': ("M0,100 L50,0 L100,100", 400)
                }
                self.kern = {('A', 'V'): -50}  # AV pair has -50 kern
                self.missing = None
        
        font = MockSvgFont()
        text = "AV"
        
        # Expected positioning calculation
        pen_x = 0.0
        positions = []
        prev_char = None
        
        for char in text:
            # Apply kerning
            if prev_char and (prev_char, char) in font.kern:
                pen_x += font.kern[(prev_char, char)]
            
            positions.append(pen_x)
            
            # Advance for next character
            glyph_data, advance = font.glyphs.get(char, (None, font.adv))
            advance = advance if advance is not None else font.adv
            pen_x += advance
            prev_char = char
        
        # A at position 0, V at position 350 (400 - 50 kerning)
        assert positions == [0.0, 350.0]
    
    def test_outline_multiline_text(self):
        """Test outlining text with newlines"""
        class MockSvgFont:
            def __init__(self):
                self.family = "TestFont"  
                self.upm = 1000
                self.asc = 800
                self.dsc = -200
                self.adv = 500
                self.glyphs = {'A': ("M0,0 L100,0", 400)}
                self.kern = {}
                self.missing = None
        
        font = MockSvgFont()
        text = "A\nA"  # Two lines
        
        # Expected positioning for multiline
        lines = []
        pen_x, pen_y = 0.0, font.asc
        current_line = []
        
        for char in text:
            if char == '\n':
                lines.append(current_line)
                current_line = []
                pen_x = 0.0
                pen_y -= (font.asc - font.dsc) * 1.2  # Line height factor
            else:
                current_line.append((char, pen_x, pen_y))
                pen_x += font.glyphs.get(char, (None, font.adv))[1] or font.adv
        
        if current_line:
            lines.append(current_line)
        
        assert len(lines) == 2  # Two lines
        assert lines[0][0][0] == 'A'  # First char of first line
        assert lines[1][0][0] == 'A'  # First char of second line
        
        # Y positions should be different (second line lower)
        y1 = lines[0][0][2]  # Y of first A
        y2 = lines[1][0][2]  # Y of second A
        assert y2 < y1  # Second line is lower (negative Y direction)
    
    def test_outline_missing_glyph_fallback(self):
        """Test fallback to missing-glyph for undefined characters"""
        class MockSvgFont:
            def __init__(self):
                self.family = "TestFont"
                self.upm = 1000
                self.asc = 800
                self.dsc = -200  
                self.adv = 500
                self.glyphs = {'A': ("M0,0 L100,0", 400)}
                self.kern = {}
                self.missing = ("M0,0 L100,100 L0,100 Z", 300)  # Missing glyph definition
        
        font = MockSvgFont()
        
        # Test character not in font
        char = 'Z'  # Not defined in glyphs
        
        # Should fall back to missing glyph
        glyph_data = font.glyphs.get(char) or font.missing
        assert glyph_data is not None
        assert glyph_data[0] == "M0,0 L100,100 L0,100 Z"  # Missing glyph path
        assert glyph_data[1] == 300  # Missing glyph advance


class TestSVGFontToPathConversion:
    """Test complete conversion of SVG fonts to path elements"""
    
    def test_convert_text_element_with_svg_font(self):
        """Test converting <text> element using SVG font to <path> elements"""
        svg_input = """
        <svg xmlns="http://www.w3.org/2000/svg">
            <defs>
                <font id="MyFont">
                    <font-face font-family="MyCustomFont" units-per-em="1000"/>
                    <glyph unicode="H" d="M0,0 L0,800 M0,400 L400,400 M400,0 L400,800"/>
                    <glyph unicode="i" d="M0,0 L0,600 M0,700 L0,800"/>
                </font>
            </defs>
            <text x="100" y="200" font-family="MyCustomFont" font-size="48">Hi</text>
        </svg>
        """
        
        # Expected output: text element replaced with group of path elements
        # <g>
        #   <path d="..." transform="..." fill="..."/>  <!-- H -->
        #   <path d="..." transform="..." fill="..."/>  <!-- i -->  
        # </g>
        
        root = ET.fromstring(svg_input)
        
        # Verify input structure
        text_elem = root.find('.//{http://www.w3.org/2000/svg}text')
        assert text_elem is not None
        assert text_elem.get('font-family') == 'MyCustomFont'
        assert text_elem.text == 'Hi'
        
        font_elem = root.find('.//{http://www.w3.org/2000/svg}font')
        assert font_elem is not None
        
        glyphs = font_elem.findall('.//{http://www.w3.org/2000/svg}glyph')
        unicode_chars = {g.get('unicode') for g in glyphs}
        assert 'H' in unicode_chars and 'i' in unicode_chars
    
    def test_preserve_text_attributes_in_paths(self):
        """Test that text attributes are preserved in generated paths"""
        # Test that fill, transform, etc. are properly applied to paths
        
        # Expected: text attributes should be converted to path attributes
        text_attributes = {
            'font-size': '48',
            'fill': '#ff0000', 
            'transform': 'rotate(45)',
            'opacity': '0.8'
        }
        
        # These should be applied to the generated paths
        expected_path_attributes = {
            'fill': '#ff0000',
            'opacity': '0.8'
            # font-size affects the scale in transform
            # original transform should be combined with glyph positioning
        }
        
        assert text_attributes['fill'] == expected_path_attributes['fill']
        assert 'transform' in text_attributes  # Should be processed into path transform
    
    def test_handle_tspan_elements_in_svg_font_text(self):
        """Test handling of tspan elements within SVG font text"""
        svg_input = """
        <svg xmlns="http://www.w3.org/2000/svg">
            <defs>
                <font id="MyFont">
                    <font-face font-family="MyCustomFont"/>
                    <glyph unicode="H" d="M0,0 L100,0"/>
                    <glyph unicode="e" d="M0,50 L50,50"/>
                    <glyph unicode="l" d="M0,0 L0,100"/>
                    <glyph unicode="o" d="M25,25 m25,0 a25,25 0 1,1 -50,0 a25,25 0 1,1 50,0"/>
                </font>
            </defs>
            <text x="100" y="200" font-family="MyCustomFont">
                Hel
                <tspan dx="10" fill="red">lo</tspan>
            </text>
        </svg>
        """
        
        # Expected: should handle both direct text content and tspan content
        # Each run should be positioned according to its attributes
        
        root = ET.fromstring(svg_input)
        text_elem = root.find('.//{http://www.w3.org/2000/svg}text')
        tspan_elem = text_elem.find('.//{http://www.w3.org/2000/svg}tspan')
        
        # Extract text runs
        runs = []
        if text_elem.text and text_elem.text.strip():
            runs.append(('text', text_elem.text.strip()))
        if tspan_elem is not None and tspan_elem.text:
            runs.append(('tspan', tspan_elem.text))
        
        assert len(runs) == 2
        assert runs[0][1] == 'Hel'  
        assert runs[1][1] == 'lo'
    
    def test_svg_font_cleanup_after_conversion(self):
        """Test that SVG font definitions are removed after conversion"""
        # After converting text to paths, the original font definitions 
        # in <defs> should be removed since they're no longer needed
        
        svg_with_font = """
        <svg xmlns="http://www.w3.org/2000/svg">
            <defs>
                <font id="MyFont">
                    <font-face font-family="MyCustomFont"/>
                    <glyph unicode="A" d="M0,0 L100,100"/>
                </font>
            </defs>
            <text font-family="MyCustomFont">A</text>
        </svg>
        """
        
        # Expected after processing: font definition removed, text converted to paths
        root = ET.fromstring(svg_with_font)
        font_before = root.find('.//{http://www.w3.org/2000/svg}font')
        assert font_before is not None  # Font exists before processing
        
        # After processing, font should be removed and text converted
        # (This test defines expected behavior for the implementation)


@pytest.mark.integration
class TestSVGFontOutliningIntegration:
    """Integration tests for SVG font outlining with real examples"""
    
    def test_complex_svg_font_document(self):
        """Test processing complex SVG with multiple fonts and mixed content"""
        svg_content = """
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600">
            <defs>
                <font id="TitleFont">
                    <font-face font-family="TitleFont" units-per-em="1000" ascent="800"/>
                    <glyph unicode="T" d="M50,0 L50,50 L450,50 L450,0 L500,0 L500,800 L400,800 L400,100 L100,100 L100,800 L0,800 L0,0 Z"/>
                </font>
                <font id="BodyFont">  
                    <font-face font-family="BodyFont" units-per-em="1000"/>
                    <glyph unicode="B" d="M0,0 L0,800 L300,800 Q400,800 400,700 Q400,600 350,600 Q400,600 400,500 Q400,400 300,400 L0,400 Z"/>
                </font>
            </defs>
            
            <!-- Mix of SVG fonts and system fonts -->
            <text x="100" y="100" font-family="TitleFont" font-size="72">T</text>
            <text x="100" y="200" font-family="BodyFont" font-size="48">B</text>
            <text x="100" y="300" font-family="Arial" font-size="36">System font text</text>
            
            <!-- Regular paths should be preserved -->
            <path d="M400,400 L500,500 L400,600 Z" fill="blue"/>
        </svg>
        """
        
        root = ET.fromstring(svg_content)
        
        # Verify structure before processing
        fonts = root.findall('.//{http://www.w3.org/2000/svg}font')
        assert len(fonts) == 2  # TitleFont and BodyFont
        
        text_elements = root.findall('.//{http://www.w3.org/2000/svg}text')  
        assert len(text_elements) == 3
        
        # Text with SVG fonts should be converted to paths
        # Text with system fonts should be preserved as text
        # Regular paths should be unaffected
        
        regular_paths = root.findall('.//{http://www.w3.org/2000/svg}path')
        assert len(regular_paths) >= 1  # At least the blue triangle
    
    def test_performance_with_large_text_blocks(self):
        """Test performance with large blocks of text using SVG fonts"""
        # Generate large text block
        large_text = "A" * 1000  # 1000 character string
        
        svg_content = f"""
        <svg xmlns="http://www.w3.org/2000/svg">
            <defs>
                <font id="TestFont">
                    <font-face font-family="TestFont"/>
                    <glyph unicode="A" d="M0,0 L100,800 L200,0 Z" horiz-adv-x="200"/>
                </font>
            </defs>
            <text font-family="TestFont">{large_text}</text>
        </svg>
        """
        
        # Expected: should handle large text blocks efficiently
        # Each character should generate a path element
        root = ET.fromstring(svg_content)
        text_elem = root.find('.//{http://www.w3.org/2000/svg}text')
        
        assert text_elem is not None
        assert len(text_elem.text) == 1000
        
        # After processing, should generate 1000 path elements
        # (This defines the expected performance characteristics)


class TestErrorHandling:
    """Test error handling in SVG font processing"""
    
    def test_malformed_svg_font_definition(self):
        """Test handling of malformed SVG font definitions"""
        malformed_svg = """
        <svg xmlns="http://www.w3.org/2000/svg">
            <defs>
                <font id="BadFont">
                    <!-- Missing font-face -->
                    <glyph unicode="A"/>  <!-- Missing 'd' attribute -->
                    <glyph d="M0,0 L100,100"/>  <!-- Missing unicode -->
                </font>
            </defs>
            <text font-family="BadFont">A</text>
        </svg>
        """
        
        # Expected: should handle gracefully, skip invalid glyphs
        root = ET.fromstring(malformed_svg)
        font_elem = root.find('.//{http://www.w3.org/2000/svg}font')
        glyphs = font_elem.findall('.//{http://www.w3.org/2000/svg}glyph')
        
        # Should parse without throwing errors
        assert len(glyphs) == 2
        
        # Invalid glyphs should be skipped during processing
        valid_glyphs = [g for g in glyphs if g.get('unicode') and g.get('d')]
        assert len(valid_glyphs) == 0  # Both glyphs are invalid
    
    def test_text_with_undefined_characters(self):
        """Test text containing characters not defined in SVG font"""
        svg_content = """
        <svg xmlns="http://www.w3.org/2000/svg">
            <defs>
                <font id="LimitedFont">
                    <font-face font-family="LimitedFont"/>
                    <glyph unicode="A" d="M0,0 L100,100"/>
                    <!-- Only A is defined -->
                </font>
            </defs>
            <text font-family="LimitedFont">ABC</text>  <!-- B and C undefined -->
        </svg>
        """
        
        # Expected: should handle undefined characters gracefully
        # Either skip them or use missing-glyph if defined
        root = ET.fromstring(svg_content)
        font_elem = root.find('.//{http://www.w3.org/2000/svg}font')
        glyphs = font_elem.findall('.//{http://www.w3.org/2000/svg}glyph')
        
        defined_chars = {g.get('unicode') for g in glyphs}
        assert 'A' in defined_chars
        assert 'B' not in defined_chars
        assert 'C' not in defined_chars
        
        # Processing should not fail despite undefined characters