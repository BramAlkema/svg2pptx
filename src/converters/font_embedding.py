"""
Font Embedding System for SVG to PPTX Conversion

This module implements a three-tier font strategy:
1. @font-face embedded fonts (data: URLs) - highest priority
2. System fonts - fallback when embedded fonts not available
3. SVG font outlining - legacy support only

The goal is to embed actual font bytes in PPTX to preserve editable text,
only converting to paths when absolutely necessary.

TODO: Issue 8 - Fix Font Embedding
===================================
PRIORITY: MEDIUM
STATUS: Needs integration

Problems:
- Font embedding system exists but is not integrated with main conversion pipeline
- Fonts are not being embedded into PPTX files properly
- Font fallback chain is not working correctly
- Custom @font-face fonts from SVG are not being processed

Required Changes:
1. Integrate FontEmbeddingEngine with ConversionServices
2. Wire up font processing in text conversion pipeline
3. Ensure font bytes are embedded into PPTX ZIP structure
4. Fix font fallback chain (embedded -> system -> outline)
5. Handle font licensing and subsetting properly
6. Add proper error handling for missing fonts

Files to modify:
- src/converters/font_embedding.py (this file - fix integration)
- src/services/conversion_services.py (add font_embedding_service)
- src/converters/text.py (integrate font processing)
- src/core/pptx_builder.py (add font embedding support)
- src/services/font_service.py (update service)

Test:
- SVG with @font-face embedded fonts
- SVG with custom font families
- Verify fonts are embedded in PPTX
- Test font fallback behavior
- Verify text remains editable in PowerPoint
"""

import re
import base64
import os
import platform
from pathlib import Path
from typing import Dict, List, Optional, Set, NamedTuple, Union
from dataclasses import dataclass
from functools import lru_cache
from lxml import etree as ET


class EmbeddedFontFace(NamedTuple):
    """Represents a parsed @font-face with embedded font data"""
    family: str
    style: str  # 'normal' or 'italic'
    weight: int
    mime_type: str
    font_bytes: bytes


@dataclass
class FontEmbedResult:
    """Result of font embedding analysis"""
    processed_svg: str  # SVG with legacy fonts converted to paths
    embeds: Dict[str, Dict[str, bytes]]  # {family: {slot: font_bytes}}
    
    
class FontEmbeddingAnalyzer:
    """Main class for analyzing and processing fonts in SVG for PPTX embedding"""
    
    # CSS @font-face regex patterns
    FONTFACE_PATTERN = re.compile(
        r'@font-face\s*\{([^}]+)\}',
        re.MULTILINE | re.DOTALL
    )
    
    FONT_FAMILY_PATTERN = re.compile(
        r'font-family\s*:\s*[\'"]?([^\'";]+)[\'"]?',
        re.IGNORECASE
    )
    
    FONT_STYLE_PATTERN = re.compile(
        r'font-style\s*:\s*([^;]+)',
        re.IGNORECASE
    )
    
    FONT_WEIGHT_PATTERN = re.compile(
        r'font-weight\s*:\s*([^;]+)',
        re.IGNORECASE
    )
    
    DATA_URL_PATTERN = re.compile(
        r'url\(data:([^;]+);base64,([^)]+)\)',
        re.IGNORECASE
    )
    
    def __init__(self):
        self._font_cache: Dict[str, bytes] = {}
        self._system_fonts: Optional[Set[str]] = None
    
    @classmethod
    def parse_fontface_css(cls, css_content: str) -> List[EmbeddedFontFace]:
        """Parse @font-face declarations from CSS content"""
        faces = []
        
        for match in cls.FONTFACE_PATTERN.finditer(css_content):
            face_css = match.group(1)
            
            # Extract font properties
            family_match = cls.FONT_FAMILY_PATTERN.search(face_css)
            if not family_match:
                continue
                
            family = family_match.group(1).strip().strip('\'"')
            
            # Extract style (default to normal)
            style_match = cls.FONT_STYLE_PATTERN.search(face_css)
            style = 'normal'
            if style_match:
                style = style_match.group(1).strip()
            
            # Extract weight (default to 400)
            weight = 400
            weight_match = cls.FONT_WEIGHT_PATTERN.search(face_css)
            if weight_match:
                weight_str = weight_match.group(1).strip()
                try:
                    weight = int(weight_str)
                except ValueError:
                    # Handle keyword weights
                    weight_map = {
                        'normal': 400,
                        'bold': 700,
                        'lighter': 300,
                        'bolder': 700
                    }
                    weight = weight_map.get(weight_str.lower(), 400)
            
            # Extract data URL
            data_match = cls.DATA_URL_PATTERN.search(face_css)
            if not data_match:
                continue
                
            mime_type = data_match.group(1)
            base64_data = data_match.group(2)
            
            try:
                font_bytes = base64.b64decode(base64_data)
                faces.append(EmbeddedFontFace(
                    family=family,
                    style=style,
                    weight=weight,
                    mime_type=mime_type,
                    font_bytes=font_bytes
                ))
            except Exception:
                # Skip invalid base64
                continue
        
        return faces
    
    def extract_fontfaces_from_svg(self, svg_content: str) -> List[EmbeddedFontFace]:
        """Extract @font-face declarations from SVG <style> elements"""
        faces = []
        
        try:
            root = ET.fromstring(svg_content)
            style_elements = root.findall('.//{http://www.w3.org/2000/svg}style')
            
            for style_elem in style_elements:
                if style_elem.text:
                    faces.extend(self.parse_fontface_css(style_elem.text))
        except ET.ParseError:
            pass
        
        return faces
    
    def load_system_font(self, family: str, weight: int = 400, italic: bool = False, fallback: Optional[List[str]] = None) -> Optional[bytes]:
        """Load system font by family name with enhanced fallback chain"""
        cache_key = f"{family}:{weight}:{italic}"

        if cache_key in self._font_cache:
            return self._font_cache[cache_key]

        # Try primary font first
        font_bytes = self._load_font_file(family, weight, italic)

        # Try fallback chain if provided
        if not font_bytes and fallback:
            for fallback_family in fallback:
                font_bytes = self._load_font_file(fallback_family, weight, italic)
                if font_bytes:
                    break

        # Cache result (even if None)
        self._font_cache[cache_key] = font_bytes
        return font_bytes

    def is_font_available(self, family: str, weight: int = 400, italic: bool = False) -> bool:
        """Check if a font is available without loading the font bytes"""
        cache_key = f"{family}:{weight}:{italic}:available"

        # Check if we already know availability
        if hasattr(self, '_availability_cache'):
            if cache_key in self._availability_cache:
                return self._availability_cache[cache_key]
        else:
            self._availability_cache = {}

        # Check if font file exists
        font_paths = self._get_system_font_paths()
        patterns = self._generate_font_patterns(family, weight, italic)

        available = False
        for font_path in font_paths:
            for pattern in patterns:
                file_path = font_path / pattern
                if file_path.exists():
                    available = True
                    break
            if available:
                break

        # Cache availability result
        self._availability_cache[cache_key] = available
        return available
    
    def _load_font_file(self, family: str, weight: int, italic: bool) -> Optional[bytes]:
        """Load font file from system font directories"""
        font_paths = self._get_system_font_paths()
        
        # Common font file patterns
        patterns = self._generate_font_patterns(family, weight, italic)
        
        for font_path in font_paths:
            for pattern in patterns:
                file_path = font_path / pattern
                if file_path.exists():
                    try:
                        with open(file_path, 'rb') as f:
                            return f.read()
                    except (IOError, OSError):
                        continue
        
        return None
    
    def _get_system_font_paths(self) -> List[Path]:
        """Get system font directories by platform"""
        paths = []
        system = platform.system()
        
        if system == "Darwin":  # macOS
            paths.extend([
                Path("/System/Library/Fonts"),
                Path("/Library/Fonts"),
                Path.home() / "Library/Fonts"
            ])
        elif system == "Windows":
            paths.extend([
                Path("C:/Windows/Fonts"),
                Path.home() / "AppData/Local/Microsoft/Windows/Fonts"
            ])
        else:  # Linux and others
            paths.extend([
                Path("/usr/share/fonts"),
                Path("/usr/local/share/fonts"),
                Path.home() / ".fonts",
                Path.home() / ".local/share/fonts"
            ])
        
        # Filter to existing directories
        return [p for p in paths if p.exists()]
    
    def _generate_font_patterns(self, family: str, weight: int, italic: bool) -> List[str]:
        """Generate possible font file patterns for a family/weight/style with enhanced matching"""
        patterns = []

        # Normalize family name variations
        family_clean = family.lower().replace(' ', '').replace('-', '')
        family_dash = family.lower().replace(' ', '-')
        family_space = family.lower()
        family_original = family

        # Enhanced weight/style suffix mapping
        weight_suffixes = []
        if weight >= 900:
            weight_suffixes.extend(["black", "heavy", "ultra", "extra"])
        elif weight >= 800:
            weight_suffixes.extend(["extrabold", "extra-bold", "ultra"])
        elif weight >= 700:
            weight_suffixes.extend(["bold", "b"])
        elif weight >= 600:
            weight_suffixes.extend(["semibold", "semi-bold", "demi", "medium"])
        elif weight >= 500:
            weight_suffixes.extend(["medium", "normal"])
        elif weight >= 400:
            weight_suffixes.extend(["regular", "normal", ""])
        elif weight >= 300:
            weight_suffixes.extend(["light", "thin"])
        elif weight >= 200:
            weight_suffixes.extend(["extralight", "extra-light", "ultralight"])
        else:
            weight_suffixes.extend(["thin", "hairline"])

        style_suffixes = ["italic", "oblique", "i"] if italic else ["", "regular"]

        # Generate all combinations
        base_families = [family_original, family_clean, family_dash, family_space]
        extensions = [".ttf", ".otf", ".TTF", ".OTF", ".ttc", ".TTC"]

        # Priority order: exact match first, then variations
        for base_family in base_families:
            # First try most specific patterns
            for weight_suffix in weight_suffixes[:2]:  # Only first 2 weight variants
                for style_suffix in style_suffixes[:1]:  # Only first style variant
                    for ext in extensions:
                        if weight_suffix and style_suffix:
                            patterns.extend([
                                f"{base_family}{weight_suffix}{style_suffix}{ext}",
                                f"{base_family}-{weight_suffix}{style_suffix}{ext}",
                                f"{base_family}_{weight_suffix}{style_suffix}{ext}",
                                f"{base_family}{weight_suffix}-{style_suffix}{ext}",
                                f"{base_family}-{weight_suffix}-{style_suffix}{ext}",
                            ])
                        elif weight_suffix:
                            patterns.extend([
                                f"{base_family}{weight_suffix}{ext}",
                                f"{base_family}-{weight_suffix}{ext}",
                                f"{base_family}_{weight_suffix}{ext}",
                            ])
                        elif style_suffix:
                            patterns.extend([
                                f"{base_family}{style_suffix}{ext}",
                                f"{base_family}-{style_suffix}{ext}",
                                f"{base_family}_{style_suffix}{ext}",
                            ])
                        else:
                            patterns.append(f"{base_family}{ext}")

        # Remove duplicates while preserving order
        seen = set()
        unique_patterns = []
        for pattern in patterns:
            if pattern not in seen:
                seen.add(pattern)
                unique_patterns.append(pattern)

        return unique_patterns
    
    @staticmethod
    def get_font_slot(weight: int, italic: bool) -> str:
        """Get PPTX font slot name from weight and italic flags"""
        if italic and weight >= 700:
            return "bolditalic"
        elif weight >= 700 and not italic:
            return "bold"
        elif italic:
            return "italic"
        else:
            return "regular"
    
    def analyze_svg_fonts(self, svg_content: str) -> FontEmbedResult:
        """Analyze SVG and prepare font embedding strategy"""
        embeds = {}
        processed_svg = svg_content
        
        try:
            root = ET.fromstring(svg_content)
            
            # Step 1: Extract embedded fonts from @font-face
            embedded_faces = self.extract_fontfaces_from_svg(svg_content)
            for face in embedded_faces:
                slot = self.get_font_slot(face.weight, face.style == 'italic')
                if face.family not in embeds:
                    embeds[face.family] = {}
                if slot not in embeds[face.family]:  # Only keep first per slot
                    embeds[face.family][slot] = face.font_bytes
            
            # Step 2: Find text elements needing system fonts
            text_elements = root.findall('.//{http://www.w3.org/2000/svg}text')
            tspan_elements = root.findall('.//{http://www.w3.org/2000/svg}tspan')
            
            for elem in text_elements + tspan_elements:
                family = elem.get('font-family', 'Arial')
                weight_str = elem.get('font-weight', '400')
                style = elem.get('font-style', 'normal')
                
                # Parse weight
                try:
                    weight = int(weight_str)
                except ValueError:
                    weight = 700 if weight_str.lower() == 'bold' else 400
                
                italic = style.lower() == 'italic'
                slot = self.get_font_slot(weight, italic)
                
                # Skip if already have embedded font for this family/slot
                if family in embeds and slot in embeds[family]:
                    continue
                
                # Try to load system font
                font_bytes = self.load_system_font(family, weight, italic, ['Arial', 'Helvetica', 'sans-serif'])
                if font_bytes:
                    if family not in embeds:
                        embeds[family] = {}
                    if slot not in embeds[family]:
                        embeds[family][slot] = font_bytes
            
            # Step 3: Handle legacy SVG fonts (convert to paths)
            svg_fonts = root.findall('.//{http://www.w3.org/2000/svg}font')
            if svg_fonts:
                processed_svg = self._outline_svg_fonts(svg_content)
            
        except ET.ParseError:
            pass
        
        return FontEmbedResult(
            processed_svg=processed_svg,
            embeds=embeds
        )
    
    def _outline_svg_fonts(self, svg_content: str) -> str:
        """Convert legacy SVG <font> elements to paths"""
        # This is a placeholder implementation
        # In practice, this would parse SVG fonts and convert text to paths
        # For now, just return the original SVG
        return svg_content