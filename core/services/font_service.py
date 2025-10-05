"""
FontService - Enhanced font loading and metrics service

This module provides comprehensive font management using fonttools:
- Font file discovery and loading across platforms
- Font validation and health checking
- Character→glyph mapping
- Basic font metrics extraction

This is the foundation for the advanced font processing system.
"""

import os
import platform
from dataclasses import dataclass
from typing import Dict, List, Optional

from fontTools.ttLib import TTFont
from fontTools.ttLib.ttFont import TTLibError


class FontServiceError(Exception):
    """Exception raised when font service operations fail."""
    pass


@dataclass
class FontMetrics:
    """Font metric ratios."""
    ascent: float   # Ratio of font size (0.0-1.0)
    descent: float  # Ratio of font size (0.0-1.0)


class FontService:
    """
    Enhanced font loading and management service using fonttools.

    Provides cross-platform font discovery, loading, and basic validation
    as the foundation for precise font metrics and embedding capabilities.
    """

    # Font metrics table: family -> FontMetrics
    FONT_METRICS: dict[str, FontMetrics] = {
        "Arial": FontMetrics(0.82, 0.18),
        "Helvetica": FontMetrics(0.82, 0.18),
        "Times New Roman": FontMetrics(0.83, 0.17),
        "Courier New": FontMetrics(0.80, 0.20),
        "Verdana": FontMetrics(0.82, 0.18),
        "Georgia": FontMetrics(0.83, 0.17),
        "Tahoma": FontMetrics(0.82, 0.18),
        "Comic Sans MS": FontMetrics(0.81, 0.19),
        "Impact": FontMetrics(0.85, 0.15),
        "Trebuchet MS": FontMetrics(0.82, 0.18),
        # Default fallback
        "default": FontMetrics(0.80, 0.20),
    }

    # Character width table (as fraction of em)
    CHAR_WIDTHS = {
        'A': 0.72, 'B': 0.67, 'C': 0.72, 'D': 0.72, 'E': 0.67, 'F': 0.61, 'G': 0.78, 'H': 0.72, 'I': 0.28, 'J': 0.50,
        'K': 0.67, 'L': 0.56, 'M': 0.83, 'N': 0.72, 'O': 0.78, 'P': 0.67, 'Q': 0.78, 'R': 0.72, 'S': 0.67, 'T': 0.61,
        'U': 0.72, 'V': 0.67, 'W': 0.94, 'X': 0.67, 'Y': 0.67, 'Z': 0.61,
        'a': 0.56, 'b': 0.56, 'c': 0.50, 'd': 0.56, 'e': 0.56, 'f': 0.28, 'g': 0.56, 'h': 0.56, 'i': 0.22, 'j': 0.22,
        'k': 0.50, 'l': 0.22, 'm': 0.83, 'n': 0.56, 'o': 0.56, 'p': 0.56, 'q': 0.56, 'r': 0.33, 's': 0.50, 't': 0.28,
        'u': 0.56, 'v': 0.50, 'w': 0.72, 'x': 0.50, 'y': 0.50, 'z': 0.50,
        '0': 0.56, '1': 0.56, '2': 0.56, '3': 0.56, '4': 0.56, '5': 0.56, '6': 0.56, '7': 0.56, '8': 0.56, '9': 0.56,
        ' ': 0.28, '.': 0.28, ',': 0.28, ':': 0.28, ';': 0.28, '!': 0.33, '?': 0.56, '-': 0.33, '_': 0.56,
        '(': 0.33, ')': 0.33, '[': 0.28, ']': 0.28, '{': 0.33, '}': 0.33, '/': 0.28, '\\': 0.28, '|': 0.26,
        '@': 1.0, '#': 0.56, '$': 0.56, '%': 0.89, '^': 0.47, '&': 0.67, '*': 0.39, '+': 0.58, '=': 0.58,
        '<': 0.58, '>': 0.58, '"': 0.35, "'": 0.19, '`': 0.33, '~': 0.58,
    }

    def __init__(self, font_directories: list[str] | None = None):
        """
        Initialize FontService with system font directories.

        Args:
            font_directories: Optional list of directories to search for fonts.
                             If None, uses platform-specific defaults.
        """
        self._font_cache: dict[str, TTFont] = {}
        self._font_directories = font_directories or self._get_system_font_directories()
        self._font_file_cache: dict[str, str | None] = {}

    def _get_system_font_directories(self) -> list[str]:
        """
        Get platform-specific system font directories.

        Returns:
            List of directory paths where fonts are typically installed
        """
        system = platform.system().lower()
        directories = []

        if system == "darwin":  # macOS
            directories.extend([
                "/System/Library/Fonts",
                "/Library/Fonts",
                os.path.expanduser("~/Library/Fonts"),
            ])
        elif system == "windows":
            directories.extend([
                "C:/Windows/Fonts",
                os.path.expanduser("~/AppData/Local/Microsoft/Windows/Fonts"),
            ])
        elif system == "linux":
            directories.extend([
                "/usr/share/fonts",
                "/usr/local/share/fonts",
                os.path.expanduser("~/.fonts"),
                os.path.expanduser("~/.local/share/fonts"),
            ])

        # Filter to existing directories
        return [d for d in directories if os.path.exists(d)]

    def find_font_file(self, font_family: str, font_weight: str = "normal",
                       font_style: str = "normal") -> str | None:
        """
        Locate font file in system directories.

        Args:
            font_family: Font family name (e.g., "Arial", "Times New Roman")
            font_weight: Font weight ("normal", "bold", etc.)
            font_style: Font style ("normal", "italic", etc.)

        Returns:
            Path to font file if found, None otherwise
        """
        cache_key = f"{font_family}:{font_weight}:{font_style}"

        if cache_key in self._font_file_cache:
            return self._font_file_cache[cache_key]

        font_path = None

        # Search in all font directories
        for directory in self._font_directories:
            if not os.path.exists(directory):
                continue

            try:
                for root, dirs, files in os.walk(directory):
                    for file in files:
                        if file.lower().endswith(('.ttf', '.otf', '.woff', '.woff2')):
                            file_path = os.path.join(root, file)
                            if self._matches_font_criteria(file_path, font_family, font_weight, font_style):
                                font_path = file_path
                                break
                    if font_path:
                        break
            except (OSError, PermissionError):
                # Skip directories we can't access
                continue

        self._font_file_cache[cache_key] = font_path
        return font_path

    def _matches_font_criteria(self, file_path: str, font_family: str,
                              font_weight: str, font_style: str) -> bool:
        """
        Check if font file matches the specified criteria.

        This is a basic implementation that matches by filename.
        More sophisticated matching would require loading the font
        and checking its metadata.

        Args:
            file_path: Path to font file
            font_family: Target font family
            font_weight: Target font weight
            font_style: Target font style

        Returns:
            True if font matches criteria
        """
        # Handle edge cases
        if not file_path or not font_family:
            return False

        filename = os.path.basename(file_path).lower()
        family_lower = font_family.lower().replace(" ", "")

        # Basic filename matching
        if family_lower in filename:
            # Check for weight and style indicators
            weight_matches = (
                font_weight == "normal" or
                (font_weight == "bold" and ("bold" in filename or "heavy" in filename)) or
                (font_weight == "light" and "light" in filename)
            )

            style_matches = (
                font_style == "normal" or
                (font_style == "italic" and ("italic" in filename or "oblique" in filename))
            )

            return weight_matches and style_matches

        return False

    def load_font(self, font_family: str, font_weight: str = "normal",
                  font_style: str = "normal") -> TTFont | None:
        """
        Load font file using fonttools.

        Args:
            font_family: Font family name
            font_weight: Font weight
            font_style: Font style

        Returns:
            TTFont object if successful, None if font not found or invalid
        """
        cache_key = f"{font_family}:{font_weight}:{font_style}"

        if cache_key in self._font_cache:
            return self._font_cache[cache_key]

        font_path = self.find_font_file(font_family, font_weight, font_style)
        if not font_path:
            return None

        try:
            font = TTFont(font_path)
            self._font_cache[cache_key] = font
            return font
        except (TTLibError, OSError, IOError):
            # Font file is corrupted or invalid
            return None

    def load_font_from_path(self, font_path: str) -> TTFont | None:
        """
        Load font directly from file path.

        Args:
            font_path: Direct path to font file

        Returns:
            TTFont object if successful, None if invalid
        """
        if font_path in self._font_cache:
            return self._font_cache[font_path]

        try:
            font = TTFont(font_path)
            self._font_cache[font_path] = font
            return font
        except (TTLibError, OSError, IOError):
            return None

    def validate_font(self, font: TTFont) -> list[FontServiceError]:
        """
        Validate font file and return any issues found.

        Args:
            font: TTFont object to validate

        Returns:
            List of validation errors (empty if font is valid)
        """
        errors = []

        try:
            # Check for required tables
            required_tables = ['cmap', 'head', 'hhea', 'hmtx', 'maxp', 'name', 'post']
            missing_tables = [table for table in required_tables if table not in font]

            if missing_tables:
                errors.append(FontServiceError(
                    message=f"Missing required font tables: {', '.join(missing_tables)}",
                    error_type="FontValidationError",
                ))

            # Check if font has glyph data
            if 'glyf' not in font and 'CFF ' not in font and 'CFF2' not in font:
                errors.append(FontServiceError(
                    message="Font contains no glyph outline data",
                    error_type="FontValidationError",
                ))

            # Basic table integrity checks
            if 'head' in font:
                head_table = font['head']
                if head_table.unitsPerEm <= 0:
                    errors.append(FontServiceError(
                        message="Invalid unitsPerEm value in head table",
                        error_type="FontValidationError",
                    ))

        except Exception as e:
            errors.append(FontServiceError(
                message=f"Font validation failed: {str(e)}",
                error_type="FontValidationError",
            ))

        return errors

    def get_available_fonts(self) -> list[dict[str, str]]:
        """
        Get list of available fonts in system directories.

        Returns:
            List of dictionaries with font information
        """
        fonts = []

        for directory in self._font_directories:
            if not os.path.exists(directory):
                continue

            try:
                for root, dirs, files in os.walk(directory):
                    for file in files:
                        if file.lower().endswith(('.ttf', '.otf')):
                            file_path = os.path.join(root, file)
                            font_info = {
                                'path': file_path,
                                'filename': file,
                                'directory': root,
                            }
                            fonts.append(font_info)
            except (OSError, PermissionError):
                continue

        return fonts

    def clear_cache(self):
        """Clear font and file caches."""
        self._font_cache.clear()
        self._font_file_cache.clear()

    def get_cache_stats(self) -> dict[str, int]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache size information
        """
        return {
            'loaded_fonts': len(self._font_cache),
            'font_file_paths': len(self._font_file_cache),
            'font_directories': len(self._font_directories),
        }

    def get_metrics(self, font_family: str) -> FontMetrics:
        """Get font metrics for family."""
        return self.FONT_METRICS.get(font_family, self.FONT_METRICS["default"])

    def measure_text_width(self, text: str, font_family: str, font_size_pt: float) -> float:
        """Measure text width in points."""
        total_width = 0.0

        for char in text:
            char_width = self.CHAR_WIDTHS.get(char, 0.56)  # Default to 'o' width
            total_width += char_width

        # Convert em units to points
        return total_width * font_size_pt

    def map_svg_font_to_ppt(self, svg_font_family: str) -> str:
        """Map SVG font-family to PowerPoint typeface."""
        if not svg_font_family:
            return "Arial"

        font_map = {
            "Arial": "Arial",
            "Helvetica": "Arial",
            "Times": "Times New Roman",
            "Times New Roman": "Times New Roman",
            "Courier": "Courier New",
            "Courier New": "Courier New",
            "Verdana": "Verdana",
            "Georgia": "Georgia",
            "Tahoma": "Tahoma",
            "Comic Sans MS": "Comic Sans MS",
            "Impact": "Impact",
            "Trebuchet MS": "Trebuchet MS",
            "sans-serif": "Arial",
            "serif": "Times New Roman",
            "monospace": "Courier New",
        }

        cleaned = svg_font_family.strip().strip('\'"').split(',')[0].strip()
        return font_map.get(cleaned, cleaned)