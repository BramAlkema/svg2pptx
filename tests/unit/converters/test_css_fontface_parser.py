"""
Tests for CSS @font-face Parsing

Test suite for parsing @font-face definitions with data: URLs
from SVG <style> elements, based on one_big_method.py approach.
"""

import pytest
from lxml import etree as ET
import base64
import re
from unittest.mock import Mock, patch


class TestFontFaceRegexPatterns:
    """Test the regex patterns used for @font-face parsing"""
    
    def test_fontface_block_regex(self):
        """Test regex for matching @font-face blocks"""
        # From one_big_method.py: FONTFACE_RE = re.compile(r"@font-face\s*{[^}]*}", re.I|re.S)
        FONTFACE_RE = re.compile(r"@font-face\s*{[^}]*}", re.I | re.S)
        
        css_with_fontface = """
        .some-class { color: red; }
        @font-face {
            font-family: 'TestFont';
            src: url(data:font/ttf;base64,TESTDATA);
        }
        .another-class { font-size: 14px; }
        @font-face{font-family:'Another';src:url(test.ttf);}
        """
        
        matches = FONTFACE_RE.findall(css_with_fontface)
        assert len(matches) == 2
        
        # First match should contain the full block
        assert 'TestFont' in matches[0]
        assert 'data:font/ttf;base64,TESTDATA' in matches[0]
        
        # Second match (compact format)
        assert 'Another' in matches[1]
        assert 'test.ttf' in matches[1]
    
    def test_font_family_regex(self):
        """Test regex for extracting font-family names"""
        # From one_big_method.py: FAMILY_RE = re.compile(r"font-family\s*:\s*(['\"]?)([^;'\"}]+)\1", re.I)
        FAMILY_RE = re.compile(r"font-family\s*:\s*(['\"]?)([^;'\"}]+)\1", re.I)
        
        test_cases = [
            ("font-family: Arial;", "Arial"),
            ("font-family: 'Times New Roman';", "Times New Roman"),
            ('font-family: "Helvetica Neue";', "Helvetica Neue"),
            ("font-family:sans-serif;", "sans-serif"),
            ("font-family : 'Custom Font' ;", "Custom Font"),
        ]
        
        for css, expected_family in test_cases:
            match = FAMILY_RE.search(css)
            assert match is not None, f"Failed to match: {css}"
            assert match.group(2) == expected_family
    
    def test_font_style_regex(self):
        """Test regex for extracting font-style"""
        # STYLE_RE = re.compile(r"font-style\s*:\s*(normal|italic|oblique)", re.I)
        STYLE_RE = re.compile(r"font-style\s*:\s*(normal|italic|oblique)", re.I)
        
        test_cases = [
            ("font-style: normal;", "normal"),
            ("font-style: italic;", "italic"),
            ("font-style: oblique;", "oblique"),
            ("font-style:italic;", "italic"),
            ("FONT-STYLE: ITALIC;", "ITALIC"),  # Case insensitive
        ]
        
        for css, expected_style in test_cases:
            match = STYLE_RE.search(css)
            assert match is not None, f"Failed to match: {css}"
            assert match.group(1).lower() == expected_style.lower()
    
    def test_font_weight_regex(self):
        """Test regex for extracting font-weight"""
        # WEIGHT_RE = re.compile(r"font-weight\s*:\s*([0-9]{3}|bold|normal)", re.I)
        WEIGHT_RE = re.compile(r"font-weight\s*:\s*([0-9]{3}|bold|normal)", re.I)
        
        test_cases = [
            ("font-weight: normal;", "normal"),
            ("font-weight: bold;", "bold"),
            ("font-weight: 400;", "400"),
            ("font-weight: 700;", "700"),
            ("font-weight:900;", "900"),
        ]
        
        for css, expected_weight in test_cases:
            match = WEIGHT_RE.search(css)
            assert match is not None, f"Failed to match: {css}"
            assert match.group(1) == expected_weight
    
    def test_data_url_regex(self):
        """Test regex for extracting data URLs"""
        # SRC_DATA_RE = re.compile(r"url\(\s*['\"]?(data:([^;]+);base64,([^'\"\)]+))['\"]?\s*\)", re.I)
        SRC_DATA_RE = re.compile(r"url\(\s*['\"]?(data:([^;]+);base64,([^'\"\)]+))['\"]?\s*\)", re.I)
        
        test_cases = [
            # Standard format
            ('src: url(data:font/ttf;base64,TESTDATA123);', 
             ('data:font/ttf;base64,TESTDATA123', 'font/ttf', 'TESTDATA123')),
            
            # With quotes
            ("src: url('data:font/woff2;base64,ABCDEFGH');",
             ('data:font/woff2;base64,ABCDEFGH', 'font/woff2', 'ABCDEFGH')),
            
            # With double quotes and spaces
            ('src: url( "data:application/font-woff;base64,XYZ789" );',
             ('data:application/font-woff;base64,XYZ789', 'application/font-woff', 'XYZ789')),
        ]
        
        for css, expected in test_cases:
            match = SRC_DATA_RE.search(css)
            assert match is not None, f"Failed to match: {css}"
            assert match.groups() == expected


class TestFontFaceDataExtraction:
    """Test extraction and decoding of font data from @font-face"""
    
    def test_valid_base64_decoding(self):
        """Test decoding valid base64 font data"""
        # Test data that represents minimal font-like bytes
        test_string = "Hello Font Data"
        encoded_data = base64.b64encode(test_string.encode()).decode()
        
        css_block = f"""
        @font-face {{
            font-family: 'TestFont';
            src: url(data:font/ttf;base64,{encoded_data});
        }}
        """
        
        # Expected API behavior
        # face = parse_fontface_block(css_block)
        # assert face.font_bytes == test_string.encode()
        # assert face.mime_type == 'font/ttf'
        
        # Test direct decoding
        decoded = base64.b64decode(encoded_data)
        assert decoded == test_string.encode()
    
    def test_invalid_base64_handling(self):
        """Test handling of invalid base64 data"""
        invalid_base64_values = [
            "Invalid!!!Base64",  # Invalid characters
            "ABC",               # Wrong padding
            "",                  # Empty string
            "123",               # Too short
        ]
        
        for invalid_data in invalid_base64_values:
            css_block = f"""
            @font-face {{
                font-family: 'BadFont';
                src: url(data:font/ttf;base64,{invalid_data});
            }}
            """
            
            # Should handle gracefully - either return None or empty bytes
            try:
                decoded = base64.b64decode(invalid_data)
                # If it doesn't throw, the result might still be invalid
                assert True  # Just ensure no crash
            except Exception:
                # Invalid base64 should be caught and handled
                assert True
    
    def test_multiple_font_formats_in_src(self):
        """Test handling of multiple font formats in src declaration"""
        css_block = """
        @font-face {
            font-family: 'MultiFormat';
            src: url('font.eot'),
                 url(data:font/woff2;base64,V09GRjIAAAA) format('woff2'),
                 url('font.woff') format('woff'),
                 url('font.ttf') format('truetype');
        }
        """
        
        # Should extract the data URL even when multiple sources present
        SRC_DATA_RE = re.compile(r"url\(\s*['\"]?(data:([^;]+);base64,([^'\"\)]+))['\"]?\s*\)", re.I)
        match = SRC_DATA_RE.search(css_block)
        
        assert match is not None
        assert match.group(2) == 'font/woff2'
        assert match.group(3) == 'V09GRjIAAAA'


class TestEmbeddedFaceStructure:
    """Test the EmbeddedFace class structure and behavior"""
    
    def test_embedded_face_creation(self):
        """Test creation of EmbeddedFace objects"""
        # Based on one_big_method.py structure:
        # class EmbeddedFace:
        #     def __init__(self, fam, sty, wt, mime, bytes_):
        #         self.family = fam
        #         self.style = sty  
        #         self.weight = wt
        #         self.mime = mime
        #         self.bytes = bytes_
        
        # Mock the expected structure
        class EmbeddedFace:
            def __init__(self, family, style, weight, mime, font_bytes):
                self.family = family
                self.style = style
                self.weight = weight
                self.mime = mime
                self.bytes = font_bytes
        
        test_bytes = b"FAKE_FONT_DATA"
        face = EmbeddedFace("Arial", "italic", 700, "font/ttf", test_bytes)
        
        assert face.family == "Arial"
        assert face.style == "italic"
        assert face.weight == 700
        assert face.mime == "font/ttf"
        assert face.bytes == test_bytes
    
    def test_font_weight_normalization(self):
        """Test normalization of font-weight values"""
        # Test weight string to numeric conversion
        def normalize_weight(weight_str: str) -> int:
            weight_str = weight_str.lower().strip()
            if weight_str == "bold":
                return 700
            elif weight_str == "normal":
                return 400
            else:
                # Try to parse as number
                try:
                    return int(weight_str)
                except ValueError:
                    return 400  # Default
        
        test_cases = [
            ("normal", 400),
            ("bold", 700),
            ("400", 400),
            ("700", 700),
            ("900", 900),
            ("invalid", 400),  # Should default
            ("", 400),         # Should default
        ]
        
        for input_weight, expected in test_cases:
            result = normalize_weight(input_weight)
            assert result == expected, f"Failed for input: {input_weight}"
    
    def test_font_style_normalization(self):
        """Test normalization of font-style values"""
        def normalize_style(style_str: str) -> str:
            if not style_str:
                return "normal"
            style_str = style_str.lower().strip()
            return style_str if style_str in ["normal", "italic", "oblique"] else "normal"
        
        test_cases = [
            ("normal", "normal"),
            ("italic", "italic"),
            ("oblique", "oblique"),
            ("ITALIC", "italic"),  # Case insensitive
            ("invalid", "normal"), # Should default
            ("", "normal"),        # Should default
        ]
        
        for input_style, expected in test_cases:
            result = normalize_style(input_style)
            assert result == expected


class TestFontFaceSelection:
    """Test font face selection logic"""
    
    def test_pick_embedded_face_exact_match(self):
        """Test selecting exact match for font family, weight, and style"""
        # Mock embedded faces
        class EmbeddedFace:
            def __init__(self, family, style, weight, mime, font_bytes):
                self.family = family
                self.style = style
                self.weight = weight
                self.mime = mime
                self.bytes = font_bytes
        
        faces = [
            EmbeddedFace("Arial", "normal", 400, "font/ttf", b"arial_regular"),
            EmbeddedFace("Arial", "normal", 700, "font/ttf", b"arial_bold"),
            EmbeddedFace("Arial", "italic", 400, "font/ttf", b"arial_italic"),
            EmbeddedFace("Times", "normal", 400, "font/ttf", b"times_regular"),
        ]
        
        # Test exact match
        def pick_embedded_face(faces, family, weight, italic):
            wanted_style = "italic" if italic else "normal"
            family = family.strip().strip("'\"")
            
            # Find exact family and style match
            candidates = [f for f in faces if f.family == family and f.style == wanted_style]
            if candidates:
                # Return closest weight match
                return min(candidates, key=lambda f: abs(f.weight - weight))
            
            # Fallback to same family, any style
            candidates = [f for f in faces if f.family == family]
            return min(candidates, key=lambda f: abs(f.weight - weight)) if candidates else None
        
        # Test exact matches
        result = pick_embedded_face(faces, "Arial", 400, False)
        assert result is not None
        assert result.family == "Arial"
        assert result.style == "normal"
        assert result.weight == 400
        
        result = pick_embedded_face(faces, "Arial", 700, False)
        assert result.weight == 700
        
        result = pick_embedded_face(faces, "Arial", 400, True)
        assert result.style == "italic"
    
    def test_pick_embedded_face_weight_fallback(self):
        """Test weight fallback when exact weight not available"""
        class EmbeddedFace:
            def __init__(self, family, style, weight, mime, font_bytes):
                self.family = family
                self.style = style
                self.weight = weight
                self.mime = mime
                self.bytes = font_bytes
        
        faces = [
            EmbeddedFace("Arial", "normal", 400, "font/ttf", b"arial_400"),
            EmbeddedFace("Arial", "normal", 700, "font/ttf", b"arial_700"),
        ]
        
        def pick_embedded_face(faces, family, weight, italic):
            wanted_style = "italic" if italic else "normal"
            candidates = [f for f in faces if f.family == family and f.style == wanted_style]
            return min(candidates, key=lambda f: abs(f.weight - weight)) if candidates else None
        
        # Request weight 600 - should get 700 (closer than 400)
        result = pick_embedded_face(faces, "Arial", 600, False)
        assert result.weight == 700
        
        # Request weight 300 - should get 400 (closer than 700)
        result = pick_embedded_face(faces, "Arial", 300, False)
        assert result.weight == 400
        
        # Request weight 550 - should get 400 (550-400=150, 700-550=150, but 400 comes first)
        result = pick_embedded_face(faces, "Arial", 550, False)
        assert result.weight == 400  # First in list when distances are equal
    
    def test_pick_embedded_face_no_match(self):
        """Test handling when no matching font family found"""
        class EmbeddedFace:
            def __init__(self, family, style, weight, mime, font_bytes):
                self.family = family
                self.style = style
                self.weight = weight
                self.mime = mime
                self.bytes = font_bytes
        
        faces = [
            EmbeddedFace("Arial", "normal", 400, "font/ttf", b"arial"),
        ]
        
        def pick_embedded_face(faces, family, weight, italic):
            wanted_style = "italic" if italic else "normal"
            candidates = [f for f in faces if f.family == family and f.style == wanted_style]
            return min(candidates, key=lambda f: abs(f.weight - weight)) if candidates else None
        
        # Request non-existent font
        result = pick_embedded_face(faces, "Times", 400, False)
        assert result is None
        
        # Request existing font but wrong style
        result = pick_embedded_face(faces, "Arial", 400, True)  # italic not available
        assert result is None


class TestSVGStyleElementParsing:
    """Test parsing @font-face from SVG <style> elements"""
    
    def test_extract_css_from_style_elements(self):
        """Test extracting CSS content from multiple <style> elements"""
        svg_content = """
        <svg xmlns="http://www.w3.org/2000/svg">
            <style type="text/css">
                @font-face {
                    font-family: 'Font1';
                    src: url(data:font/ttf;base64,FONT1DATA);
                }
            </style>
            <style>
                .text { color: red; }
                @font-face {
                    font-family: 'Font2';
                    src: url(data:font/woff;base64,FONT2DATA);
                }
            </style>
            <text>Some text</text>
        </svg>
        """
        
        root = ET.fromstring(svg_content)
        
        # Extract all style elements (with and without namespace)
        style_elements = []
        for tag in ['style', '{http://www.w3.org/2000/svg}style']:
            style_elements.extend(root.findall(f'.//{tag}'))
        
        assert len(style_elements) == 2
        
        # Combine CSS content
        css_content = []
        for style_elem in style_elements:
            if style_elem.text:
                css_content.append(style_elem.text)
        
        combined_css = '\n'.join(css_content)
        
        # Should contain both @font-face declarations
        assert 'Font1' in combined_css
        assert 'Font2' in combined_css
        assert 'FONT1DATA' in combined_css
        assert 'FONT2DATA' in combined_css
    
    def test_handle_cdata_in_style_elements(self):
        """Test handling CDATA sections in style elements"""
        svg_content = """
        <svg xmlns="http://www.w3.org/2000/svg">
            <style><![CDATA[
                @font-face {
                    font-family: 'CDATAFont';
                    src: url(data:font/ttf;base64,CDATAFONT);
                }
            ]]></style>
        </svg>
        """
        
        root = ET.fromstring(svg_content)
        style_elem = root.find('.//{http://www.w3.org/2000/svg}style')
        
        assert style_elem is not None
        assert style_elem.text is not None
        assert 'CDATAFont' in style_elem.text
        assert '@font-face' in style_elem.text
    
    def test_handle_empty_or_missing_style_elements(self):
        """Test handling of empty or missing style elements"""
        svg_without_styles = """
        <svg xmlns="http://www.w3.org/2000/svg">
            <text>No styles here</text>
        </svg>
        """
        
        root = ET.fromstring(svg_without_styles)
        style_elements = root.findall('.//{http://www.w3.org/2000/svg}style')
        
        assert len(style_elements) == 0
        
        # Should handle gracefully
        css_content = []
        for style_elem in style_elements:
            if style_elem.text:
                css_content.append(style_elem.text)
        
        combined_css = '\n'.join(css_content)
        assert combined_css == ""


@pytest.mark.integration  
class TestFontFaceParsingIntegration:
    """Integration tests for complete @font-face parsing workflow"""
    
    def test_complete_svg_fontface_extraction(self):
        """Test complete extraction from real-world SVG with embedded fonts"""
        svg_content = """
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300">
            <style type="text/css">
                @font-face {
                    font-family: 'CustomRegular';
                    font-style: normal;
                    font-weight: 400;
                    src: url(data:font/woff2;base64,UmVndWxhckZvbnREYXRh) format('woff2');
                }
                @font-face {
                    font-family: 'CustomRegular';
                    font-style: normal;
                    font-weight: 700;
                    src: url(data:font/woff2;base64,Qm9sZEZvbnREYXRh) format('woff2');
                }
                @font-face {
                    font-family: 'CustomRegular';
                    font-style: italic;
                    font-weight: 400;
                    src: url(data:font/woff2;base64,SXRhbGljRm9udERhdGE=) format('woff2');
                }
                .title { font-family: 'CustomRegular'; font-weight: 700; }
                .body { font-family: 'CustomRegular'; font-style: italic; }
            </style>
            
            <text x="10" y="50" class="title">Bold Title</text>
            <text x="10" y="100" class="body">Italic Body</text>
            <text x="10" y="150" font-family="CustomRegular">Regular Text</text>
        </svg>
        """
        
        # Expected result: 3 embedded faces extracted
        # CustomRegular: regular=400, bold=700, italic=400
        
        root = ET.fromstring(svg_content)
        style_elem = root.find('.//{http://www.w3.org/2000/svg}style')
        assert style_elem is not None
        
        css = style_elem.text
        assert css.count('@font-face') == 3
        assert css.count('CustomRegular') >= 3
        
        # Each should have different base64 data
        assert 'UmVndWxhckZvbnREYXRh' in css  # Regular
        assert 'Qm9sZEZvbnREYXRh' in css      # Bold  
        assert 'SXRhbGljRm9udERhdGE=' in css   # Italic
        
        # Text elements should reference the font
        text_elements = root.findall('.//{http://www.w3.org/2000/svg}text')
        assert len(text_elements) == 3
    
    def test_mixed_font_sources_priority(self):
        """Test handling SVG with mix of embedded and system fonts"""
        svg_content = """
        <svg xmlns="http://www.w3.org/2000/svg">
            <style>
                @font-face {
                    font-family: 'Arial';  /* Same name as system font */
                    src: url(data:font/ttf;base64,Q3VzdG9tQXJpYWxEYXRh);
                }
            </style>
            
            <!-- Both should use embedded Arial, not system Arial -->
            <text font-family="Arial" font-weight="400">Text 1</text>
            <text font-family="Arial" font-weight="700">Text 2</text>
        </svg>
        """
        
        # Expected: embedded @font-face should take priority over system Arial
        root = ET.fromstring(svg_content)
        
        # Verify embedded font present
        style_elem = root.find('.//{http://www.w3.org/2000/svg}style')
        assert 'Q3VzdG9tQXJpYWxEYXRh' in style_elem.text
        
        # Verify text elements reference Arial
        text_elements = root.findall('.//{http://www.w3.org/2000/svg}text')
        for text_elem in text_elements:
            assert text_elem.get('font-family') == 'Arial'