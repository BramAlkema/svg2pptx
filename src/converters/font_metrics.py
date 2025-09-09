"""
Font Metrics Analyzer for SVG Text-to-Path Conversion

This module provides font detection, validation, and glyph extraction capabilities
for converting SVG text elements to vector paths when fonts are unavailable in PowerPoint.

Key Features:
- Font detection and availability checking
- Font fallback hierarchy (system fonts → web safe fonts → generic)
- Glyph outline extraction using fonttools
- Font metrics calculation (ascent, descent, line height)
- Performance optimization with font caching
"""

import os
import sys
import platform
from typing import Dict, List, Optional, Tuple, Any, NamedTuple
from pathlib import Path
from functools import lru_cache
import logging

try:
    from fontTools.ttLib import TTFont
    from fontTools.pens.recordingPen import RecordingPen
    from fontTools.pens.transformPen import TransformPen
    from fontTools.misc.transform import Transform
    import uharfbuzz as hb
except ImportError as e:
    raise ImportError(f"Font processing dependencies missing: {e}. Install with: pip install fonttools uharfbuzz") from e


logger = logging.getLogger(__name__)


class FontMetrics(NamedTuple):
    """Font metrics information"""
    family_name: str
    style: str
    weight: int
    units_per_em: int
    ascender: int
    descender: int
    line_gap: int
    x_height: int
    cap_height: int
    bbox: Tuple[int, int, int, int]  # (xMin, yMin, xMax, yMax)


class GlyphOutline(NamedTuple):
    """Glyph outline information"""
    unicode_char: str
    glyph_name: str
    advance_width: int
    bbox: Tuple[int, int, int, int]  # (xMin, yMin, xMax, yMax)
    path_data: List[Tuple[str, Tuple]]  # [(operation, coordinates), ...]


class FontMetricsAnalyzer:
    """
    Analyzes fonts and extracts metrics and glyph outlines for text-to-path conversion.
    
    Provides comprehensive font detection, validation, and glyph extraction capabilities
    with intelligent fallback systems and performance optimization.
    """
    
    # Web-safe font fallback hierarchy
    FALLBACK_FONTS = {
        'serif': ['Times New Roman', 'Times', 'Georgia', 'serif'],
        'sans-serif': ['Arial', 'Helvetica', 'Verdana', 'Tahoma', 'sans-serif'],
        'monospace': ['Courier New', 'Courier', 'Monaco', 'Consolas', 'monospace'],
        'fantasy': ['Impact', 'Comic Sans MS', 'fantasy'],
        'cursive': ['Brush Script MT', 'cursive']
    }
    
    # Generic font family mappings
    GENERIC_FAMILIES = {
        'serif': 'Times New Roman',
        'sans-serif': 'Arial',
        'monospace': 'Courier New',
        'fantasy': 'Impact',
        'cursive': 'Brush Script MT'
    }
    
    def __init__(self, font_cache_size: int = 128):
        """
        Initialize FontMetricsAnalyzer with optional cache configuration.
        
        Args:
            font_cache_size: Maximum number of fonts to cache in memory
        """
        self.font_cache_size = font_cache_size
        self._font_cache: Dict[str, TTFont] = {}
        self._metrics_cache: Dict[str, FontMetrics] = {}
        self._system_fonts: Optional[Dict[str, str]] = None
        
        # Configure LRU cache for glyph outlines
        self._get_glyph_outline_cached = lru_cache(maxsize=1024)(self._get_glyph_outline_impl)
    
    def detect_font_availability(self, font_family: str) -> bool:
        """
        Check if a font family is available on the system.
        
        Args:
            font_family: Font family name to check
            
        Returns:
            True if font is available, False otherwise
        """
        if not font_family:
            return False
            
        # Clean font family name
        clean_name = self._clean_font_name(font_family)
        
        # Check system fonts
        system_fonts = self._get_system_fonts()
        return clean_name.lower() in [name.lower() for name in system_fonts.keys()]
    
    def get_font_fallback_chain(self, font_families: List[str]) -> List[str]:
        """
        Create a font fallback chain with system font availability checking.
        
        Args:
            font_families: List of preferred font families
            
        Returns:
            Ordered list of available fonts with fallbacks
        """
        fallback_chain = []
        
        # Add requested fonts if available
        for font_family in font_families:
            clean_name = self._clean_font_name(font_family)
            if self.detect_font_availability(clean_name):
                fallback_chain.append(clean_name)
        
        # Add generic family fallbacks
        for font_family in font_families:
            generic = self._detect_generic_family(font_family)
            if generic and generic in self.FALLBACK_FONTS:
                for fallback in self.FALLBACK_FONTS[generic]:
                    if fallback not in fallback_chain and self.detect_font_availability(fallback):
                        fallback_chain.append(fallback)
        
        # Ensure we have at least Arial or Times New Roman as ultimate fallback
        ultimate_fallbacks = ['Arial', 'Times New Roman', 'Helvetica', 'Times']
        for fallback in ultimate_fallbacks:
            if fallback not in fallback_chain and self.detect_font_availability(fallback):
                fallback_chain.append(fallback)
                break
        
        return fallback_chain or ['Arial']  # Always return at least one font
    
    def get_font_metrics(self, font_family: str, font_style: str = 'normal', font_weight: int = 400) -> Optional[FontMetrics]:
        """
        Extract comprehensive font metrics for layout calculations.
        
        Args:
            font_family: Font family name
            font_style: Font style ('normal', 'italic', 'oblique')
            font_weight: Font weight (100-900)
            
        Returns:
            FontMetrics object or None if font cannot be loaded
        """
        cache_key = f"{font_family}:{font_style}:{font_weight}"
        
        # Check cache first
        if cache_key in self._metrics_cache:
            return self._metrics_cache[cache_key]
        
        try:
            font = self._load_font(font_family, font_style, font_weight)
            if not font:
                return None
            
            # Extract font metrics
            head_table = font['head']
            hhea_table = font['hhea']
            os2_table = font.get('OS/2')
            
            # Get font name
            name_table = font['name']
            family_name = str(name_table.getDebugName(1) or font_family)
            
            # Calculate metrics
            units_per_em = head_table.unitsPerEm
            ascender = hhea_table.ascent
            descender = hhea_table.descent
            line_gap = hhea_table.lineGap
            
            # Get additional metrics from OS/2 table if available
            x_height = os2_table.sxHeight if os2_table else int(units_per_em * 0.5)
            cap_height = os2_table.sCapHeight if os2_table else int(units_per_em * 0.7)
            
            # Font bounding box
            bbox = (head_table.xMin, head_table.yMin, head_table.xMax, head_table.yMax)
            
            metrics = FontMetrics(
                family_name=family_name,
                style=font_style,
                weight=font_weight,
                units_per_em=units_per_em,
                ascender=ascender,
                descender=descender,
                line_gap=line_gap,
                x_height=x_height,
                cap_height=cap_height,
                bbox=bbox
            )
            
            # Cache the result
            self._metrics_cache[cache_key] = metrics
            return metrics
            
        except Exception as e:
            logger.warning(f"Failed to extract metrics for font {font_family}: {e}")
            return None
    
    def get_glyph_outline(self, font_family: str, character: str, font_size: float = 100.0, 
                         font_style: str = 'normal', font_weight: int = 400) -> Optional[GlyphOutline]:
        """
        Extract glyph outline for a specific character.
        
        Args:
            font_family: Font family name
            character: Unicode character to extract
            font_size: Font size for scaling (default: 100.0)
            font_style: Font style ('normal', 'italic', 'oblique')
            font_weight: Font weight (100-900)
            
        Returns:
            GlyphOutline object or None if glyph cannot be extracted
        """
        return self._get_glyph_outline_cached(font_family, character, font_size, font_style, font_weight)
    
    def _get_glyph_outline_impl(self, font_family: str, character: str, font_size: float,
                               font_style: str, font_weight: int) -> Optional[GlyphOutline]:
        """Internal implementation for glyph outline extraction (cached)."""
        try:
            font = self._load_font(font_family, font_style, font_weight)
            if not font:
                return None
            
            # Get the glyph for this character
            cmap = font.getBestCmap()
            unicode_value = ord(character)
            
            if unicode_value not in cmap:
                logger.warning(f"Character '{character}' not found in font {font_family}")
                return None
            
            glyph_name = cmap[unicode_value]
            glyph_set = font.getGlyphSet()
            
            if glyph_name not in glyph_set:
                logger.warning(f"Glyph '{glyph_name}' not found in font {font_family}")
                return None
            
            glyph = glyph_set[glyph_name]
            
            # Get glyph metrics
            advance_width = glyph.width
            
            # Extract glyph outline using RecordingPen
            pen = RecordingPen()
            
            # Apply scaling transformation based on font size
            units_per_em = font['head'].unitsPerEm
            scale = font_size / units_per_em
            transform = Transform(scale, 0, 0, -scale, 0, 0)  # Flip Y-axis for PowerPoint
            transform_pen = TransformPen(pen, transform)
            
            # Draw the glyph
            glyph.draw(transform_pen)
            
            # Get path data
            path_data = pen.value
            
            # Calculate scaled bounding box
            bounds = glyph.getBounds(glyph_set) if hasattr(glyph, 'getBounds') else (0, 0, advance_width, units_per_em)
            if bounds:
                bbox = (
                    int(bounds[0] * scale),
                    int(bounds[1] * -scale),  # Flip Y
                    int(bounds[2] * scale),
                    int(bounds[3] * -scale)   # Flip Y
                )
            else:
                bbox = (0, 0, int(advance_width * scale), int(font_size))
            
            return GlyphOutline(
                unicode_char=character,
                glyph_name=glyph_name,
                advance_width=int(advance_width * scale),
                bbox=bbox,
                path_data=path_data
            )
            
        except Exception as e:
            logger.warning(f"Failed to extract glyph outline for '{character}' in {font_family}: {e}")
            return None
    
    def _load_font(self, font_family: str, font_style: str = 'normal', font_weight: int = 400) -> Optional[TTFont]:
        """Load font from system with caching."""
        cache_key = f"{font_family}:{font_style}:{font_weight}"
        
        # Check cache first
        if cache_key in self._font_cache:
            return self._font_cache[cache_key]
        
        # Find font file
        font_path = self._find_font_file(font_family, font_style, font_weight)
        if not font_path:
            logger.warning(f"Font file not found for {font_family}")
            return None
        
        try:
            font = TTFont(font_path)
            
            # Cache management - remove oldest if cache is full
            if len(self._font_cache) >= self.font_cache_size:
                oldest_key = next(iter(self._font_cache))
                del self._font_cache[oldest_key]
            
            self._font_cache[cache_key] = font
            return font
            
        except Exception as e:
            logger.error(f"Failed to load font {font_path}: {e}")
            return None
    
    def _find_font_file(self, font_family: str, font_style: str = 'normal', font_weight: int = 400) -> Optional[str]:
        """Find the actual font file path on the system."""
        system_fonts = self._get_system_fonts()
        clean_name = self._clean_font_name(font_family)
        
        # Try exact match first
        if clean_name in system_fonts:
            return system_fonts[clean_name]
        
        # Try case-insensitive match
        for name, path in system_fonts.items():
            if name.lower() == clean_name.lower():
                return path
        
        # Try partial match
        for name, path in system_fonts.items():
            if clean_name.lower() in name.lower() or name.lower() in clean_name.lower():
                return path
        
        return None
    
    @lru_cache(maxsize=1)
    def _get_system_fonts(self) -> Dict[str, str]:
        """Get dictionary of available system fonts with their file paths."""
        if self._system_fonts is not None:
            return self._system_fonts
        
        fonts = {}
        font_dirs = self._get_font_directories()
        
        for font_dir in font_dirs:
            if not os.path.exists(font_dir):
                continue
                
            for root, _, files in os.walk(font_dir):
                for file in files:
                    if file.lower().endswith(('.ttf', '.otf', '.ttc')):
                        font_path = os.path.join(root, file)
                        try:
                            font = TTFont(font_path)
                            name_table = font['name']
                            family_name = str(name_table.getDebugName(1))
                            if family_name:
                                fonts[family_name] = font_path
                            font.close()
                        except Exception:
                            continue  # Skip invalid fonts
        
        self._system_fonts = fonts
        return fonts
    
    def _get_font_directories(self) -> List[str]:
        """Get list of system font directories based on platform."""
        system = platform.system()
        
        if system == "Windows":
            return [
                os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts'),
                os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'Microsoft', 'Windows', 'Fonts')
            ]
        elif system == "Darwin":  # macOS
            return [
                '/System/Library/Fonts',
                '/Library/Fonts',
                os.path.join(os.path.expanduser('~'), 'Library', 'Fonts')
            ]
        else:  # Linux and other Unix-like systems
            return [
                '/usr/share/fonts',
                '/usr/local/share/fonts',
                os.path.join(os.path.expanduser('~'), '.fonts'),
                os.path.join(os.path.expanduser('~'), '.local', 'share', 'fonts')
            ]
    
    def _clean_font_name(self, font_name: str) -> str:
        """Clean and normalize font family name."""
        if not font_name:
            return ""
        
        # Remove quotes and extra spaces
        cleaned = font_name.strip().strip('"\'')
        
        # Handle comma-separated font lists (take first one)
        cleaned = cleaned.split(',')[0].strip()
        
        return cleaned
    
    def _detect_generic_family(self, font_family: str) -> Optional[str]:
        """Detect if font family is a generic CSS font family."""
        clean_name = self._clean_font_name(font_family).lower()
        return clean_name if clean_name in self.GENERIC_FAMILIES else None
    
    def clear_cache(self) -> None:
        """Clear all cached fonts and metrics."""
        self._font_cache.clear()
        self._metrics_cache.clear()
        self._get_glyph_outline_cached.cache_clear()
        self._system_fonts = None
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring and debugging."""
        return {
            'font_cache_size': len(self._font_cache),
            'font_cache_max': self.font_cache_size,
            'metrics_cache_size': len(self._metrics_cache),
            'glyph_cache_info': self._get_glyph_outline_cached.cache_info()._asdict(),
            'system_fonts_count': len(self._get_system_fonts())
        }