"""
Unified Color Converter Service

Takes any CSS color expression and converts to normalized sRGB RGBA tuples.
Integrates CSS Color 4 parser with existing ICC profiles and known profiles system.

Supports all formats:
- Legacy: #hex, rgb(), hsl(), named colors
- CSS Color 4: color(display-p3 ...), lab(), lch(), oklab(), oklch()
- @color-profile rules for custom ICC profiles
"""

from typing import Tuple, Optional
import logging

from .css_color4_parser import (
    parse_css_color4_function,
    CSSColor4Converter,
    CSSColor4Parser
)

logger = logging.getLogger(__name__)


class UnifiedColorConverter:
    """
    Unified color converter that handles all CSS color formats

    Fallback chain:
    1. CSS Color 4 functions → CSS Color 4 parser + ICC/known profiles
    2. Legacy colors → existing color system
    3. Ultimate fallback → treat as sRGB
    """

    def __init__(self, icc_converter=None, known_profiles=None, legacy_color_parser=None):
        """
        Initialize with color conversion backends

        Args:
            icc_converter: ICCConverter instance for profile-based conversion
            known_profiles: KnownProfiles instance for built-in color spaces
            legacy_color_parser: Existing color parser for hex/rgb/hsl/named colors
        """
        self.css4_converter = CSSColor4Converter(
            icc_converter=icc_converter,
            known_profiles=known_profiles
        )
        self.css4_parser = CSSColor4Parser()
        self.legacy_color_parser = legacy_color_parser

    def resolve_color(self, color_expr: str) -> Tuple[float, float, float, float]:
        """
        Main entry point - convert any CSS color expression to sRGB RGBA

        Args:
            color_expr: CSS color expression (any format)

        Returns:
            (r, g, b, a) tuple in 0-1 sRGB space

        Examples:
            resolve_color("#ff0000") → (1.0, 0.0, 0.0, 1.0)
            resolve_color("color(display-p3 0.9 0.2 0.1)") → (0.84, 0.18, 0.09, 1.0)
            resolve_color("lab(50 40 30 / 0.5)") → (converted sRGB, 0.5)
        """
        color_expr = color_expr.strip()

        # Try CSS Color 4 functions first
        css4_color = parse_css_color4_function(color_expr)
        if css4_color:
            return self.css4_converter.convert_css_color(css4_color)

        # Fall back to legacy color parser
        if self.legacy_color_parser:
            try:
                return self._convert_legacy_color(color_expr)
            except Exception as e:
                logger.debug(f"Legacy color parsing failed for '{color_expr}': {e}")

        # Ultimate fallback - basic parsing
        return self._parse_basic_color(color_expr)

    def _convert_legacy_color(self, color_expr: str) -> Tuple[float, float, float, float]:
        """Convert using existing legacy color parser"""
        # This would integrate with your existing color parsing system
        # For now, delegate to basic parsing
        return self._parse_basic_color(color_expr)

    def _parse_basic_color(self, color_expr: str) -> Tuple[float, float, float, float]:
        """
        Basic color parsing for common formats

        Handles hex, rgb(), rgba(), hsl(), hsla(), and named colors
        """
        expr = color_expr.lower().strip()

        # Hex colors
        if expr.startswith('#'):
            return self._parse_hex(expr)

        # rgb() / rgba()
        if expr.startswith('rgb'):
            return self._parse_rgb(expr)

        # hsl() / hsla()
        if expr.startswith('hsl'):
            return self._parse_hsl(expr)

        # Named colors
        if expr in NAMED_COLORS:
            rgb = NAMED_COLORS[expr]
            alpha = 0.0 if expr == 'transparent' else 1.0
            return (*rgb, alpha)

        # Unknown - return black
        logger.warning(f"Unknown color format: {color_expr}")
        return (0.0, 0.0, 0.0, 1.0)

    def _parse_hex(self, expr: str) -> Tuple[float, float, float, float]:
        """Parse hex color #rgb, #rgba, #rrggbb, #rrggbbaa"""
        import re

        hex_match = re.match(r'^#([0-9a-f]+)$', expr)
        if not hex_match:
            return (0.0, 0.0, 0.0, 1.0)

        hex_val = hex_match.group(1)

        # Expand short forms
        if len(hex_val) == 3:  # #rgb
            hex_val = ''.join(c*2 for c in hex_val)
        elif len(hex_val) == 4:  # #rgba
            hex_val = ''.join(c*2 for c in hex_val)

        if len(hex_val) == 6:  # #rrggbb
            r = int(hex_val[0:2], 16) / 255.0
            g = int(hex_val[2:4], 16) / 255.0
            b = int(hex_val[4:6], 16) / 255.0
            return (r, g, b, 1.0)
        elif len(hex_val) == 8:  # #rrggbbaa
            r = int(hex_val[0:2], 16) / 255.0
            g = int(hex_val[2:4], 16) / 255.0
            b = int(hex_val[4:6], 16) / 255.0
            a = int(hex_val[6:8], 16) / 255.0
            return (r, g, b, a)

        return (0.0, 0.0, 0.0, 1.0)

    def _parse_rgb(self, expr: str) -> Tuple[float, float, float, float]:
        """Parse rgb() / rgba() functions"""
        import re

        # Extract numbers and percentages
        nums = re.findall(r'[\d\.]+%?', expr)
        if len(nums) < 3:
            return (0.0, 0.0, 0.0, 1.0)

        # Parse RGB components
        rgb = []
        for i in range(3):
            val_str = nums[i]
            if val_str.endswith('%'):
                val = float(val_str[:-1]) / 100.0
            else:
                val = float(val_str) / 255.0
            rgb.append(max(0.0, min(1.0, val)))

        # Parse alpha if present
        alpha = 1.0
        if len(nums) >= 4:
            alpha_str = nums[3]
            if alpha_str.endswith('%'):
                alpha = float(alpha_str[:-1]) / 100.0
            else:
                alpha = float(alpha_str)
            alpha = max(0.0, min(1.0, alpha))

        return (*rgb, alpha)

    def _parse_hsl(self, expr: str) -> Tuple[float, float, float, float]:
        """Parse hsl() / hsla() functions"""
        import re

        # Extract numbers
        nums = re.findall(r'[\d\.]+%?', expr)
        if len(nums) < 3:
            return (0.0, 0.0, 0.0, 1.0)

        # Parse HSL components
        h = float(nums[0]) % 360.0  # Hue in degrees
        s = float(nums[1][:-1]) / 100.0 if nums[1].endswith('%') else float(nums[1]) / 100.0
        l = float(nums[2][:-1]) / 100.0 if nums[2].endswith('%') else float(nums[2]) / 100.0

        # Parse alpha if present
        alpha = 1.0
        if len(nums) >= 4:
            alpha_str = nums[3]
            if alpha_str.endswith('%'):
                alpha = float(alpha_str[:-1]) / 100.0
            else:
                alpha = float(alpha_str)
            alpha = max(0.0, min(1.0, alpha))

        # Convert HSL to RGB
        rgb = self._hsl_to_rgb(h, s, l)
        return (*rgb, alpha)

    def _hsl_to_rgb(self, h: float, s: float, l: float) -> Tuple[float, float, float]:
        """Convert HSL to RGB"""
        h = h / 360.0  # Normalize hue to 0-1

        if s == 0:
            # Achromatic (gray)
            return (l, l, l)

        def hue_to_rgb(p: float, q: float, t: float) -> float:
            if t < 0:
                t += 1
            if t > 1:
                t -= 1
            if t < 1/6:
                return p + (q - p) * 6 * t
            if t < 1/2:
                return q
            if t < 2/3:
                return p + (q - p) * (2/3 - t) * 6
            return p

        q = l * (1 + s) if l < 0.5 else l + s - l * s
        p = 2 * l - q

        r = hue_to_rgb(p, q, h + 1/3)
        g = hue_to_rgb(p, q, h)
        b = hue_to_rgb(p, q, h - 1/3)

        return (r, g, b)

    def parse_color_profiles(self, css_text: str) -> list:
        """Parse @color-profile rules from CSS text"""
        return self.css4_parser.parse_color_profile_rule(css_text)

    def detect_color_functions(self, text: str) -> list:
        """Detect CSS Color 4 functions in text"""
        return self.css4_parser.detect_color_functions(text)


# Basic named colors - extend as needed
NAMED_COLORS = {
    'transparent': (0, 0, 0),
    'black': (0, 0, 0),
    'white': (1, 1, 1),
    'red': (1, 0, 0),
    'green': (0, 1, 0),
    'blue': (0, 0, 1),
    'yellow': (1, 1, 0),
    'cyan': (0, 1, 1),
    'magenta': (1, 0, 1),
    'gray': (0.5, 0.5, 0.5),
    'grey': (0.5, 0.5, 0.5),
    'orange': (1, 0.65, 0),
    'purple': (0.5, 0, 0.5),
    'brown': (0.65, 0.16, 0.16),
    'pink': (1, 0.75, 0.8),
    'lime': (0, 1, 0),
    'navy': (0, 0, 0.5),
    'maroon': (0.5, 0, 0),
    'olive': (0.5, 0.5, 0),
    'teal': (0, 0.5, 0.5),
    'silver': (0.75, 0.75, 0.75),
}


def create_unified_converter(icc_converter=None, known_profiles=None, legacy_parser=None):
    """
    Factory function to create a unified color converter

    Args:
        icc_converter: ICCConverter instance (optional)
        known_profiles: KnownProfiles instance (optional)
        legacy_parser: Existing color parser (optional)

    Returns:
        UnifiedColorConverter instance
    """
    return UnifiedColorConverter(
        icc_converter=icc_converter,
        known_profiles=known_profiles,
        legacy_color_parser=legacy_parser
    )


# Convenience function for direct usage
def resolve_color(color_expr: str, icc_converter=None, known_profiles=None) -> Tuple[float, float, float, float]:
    """
    Convenience function to convert any CSS color to sRGB RGBA

    Args:
        color_expr: CSS color expression
        icc_converter: Optional ICCConverter instance
        known_profiles: Optional KnownProfiles instance

    Returns:
        (r, g, b, a) tuple in 0-1 sRGB space

    Examples:
        resolve_color("#ff0000") → (1.0, 0.0, 0.0, 1.0)
        resolve_color("color(display-p3 0.9 0.2 0.1)") → (converted sRGB, 1.0)
    """
    converter = create_unified_converter(icc_converter, known_profiles)
    return converter.resolve_color(color_expr)