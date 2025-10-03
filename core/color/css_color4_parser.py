"""
CSS Color 4 Parser and Normalizer for SVG2PPTX

Supports CSS Color 4 features:
- color(display-p3 ...), color(rec2020 ...), color(prophoto-rgb ...)
- @color-profile rules
- Integration with existing color system

Uses existing color system for hex, rgb(), hsl(), named colors.
"""

import re
from typing import Dict, List, Optional, Tuple, NamedTuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


class CSSColor(NamedTuple):
    """Parsed CSS color with space, coordinates, and alpha"""
    space: str                     # e.g. 'srgb', 'display-p3', 'oklab'
    coords: Tuple[float, ...]      # numeric coords in source space
    alpha: float                   # transparency (0..1)


@dataclass
class ColorProfileRule:
    """Represents a CSS @color-profile rule"""
    name: str
    src: Optional[str] = None
    rendering_intent: str = "relative-colorimetric"
    components: Optional[List[str]] = None


def parse_css_color4_function(expr: str) -> Optional[CSSColor]:
    """
    Parse CSS Color 4 functions only (color(), lab(), lch(), oklab(), oklch())

    For standard colors (hex, rgb(), hsl(), named), use existing color system.
    """
    expr = expr.strip().lower()

    # color(space ... / alpha)
    if expr.startswith("color("):
        return _parse_color_function(expr)

    # lab(), lch(), oklab(), oklch()
    for fn in ["lab", "lch", "oklab", "oklch"]:
        if expr.startswith(fn + "("):
            return _parse_lab_lch(expr, fn)

    return None


def _parse_color_function(expr: str) -> Optional[CSSColor]:
    """Parse color(space ...) function"""
    m = re.match(r"color\(([a-zA-Z0-9\-_]+)\s+([^)]+)\)", expr)
    if not m:
        return None

    space, coords_str = m.groups()
    parts = coords_str.split("/")
    vals = [float(x) for x in parts[0].split()]
    alpha = float(parts[1]) if len(parts) > 1 else 1.0

    # Normalize space name
    space_aliases = {
        'display-p3': 'display_p3',
        'a98-rgb': 'adobe_rgb',
        'prophoto-rgb': 'prophoto_rgb',
        'rec-2020': 'rec2020'
    }
    normalized_space = space_aliases.get(space.lower(), space.lower())

    return CSSColor(normalized_space, tuple(vals), alpha)


def _parse_lab_lch(expr: str, fn: str) -> Optional[CSSColor]:
    """Parse lab(), lch(), oklab(), oklch() functions"""
    inside = expr[expr.find("(")+1:expr.rfind(")")]
    parts = inside.split("/")
    coords = [float(x.strip("%"))/100.0 if "%" in x else float(x) for x in parts[0].split()]
    alpha = float(parts[1]) if len(parts) > 1 else 1.0
    return CSSColor(fn, tuple(coords), alpha)


class CSSColor4Parser:
    """Parser for CSS Color 4 profile rules and advanced color functions"""

    def __init__(self):
        self.color_profiles: Dict[str, ColorProfileRule] = {}
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile regex patterns for parsing"""
        # Pattern for color() function
        self.color_function_pattern = re.compile(
            r'color\s*\(\s*'
            r'([a-zA-Z0-9\-_]+)\s+'  # color space
            r'([^)]+)'  # components and optional alpha
            r'\s*\)',
            re.IGNORECASE
        )

        # Pattern for @color-profile rule
        self.color_profile_pattern = re.compile(
            r'@color-profile\s+'
            r'(--[a-zA-Z0-9\-_]+)\s*'  # profile name
            r'\{([^}]+)\}',  # rule body
            re.IGNORECASE | re.DOTALL
        )

    def parse_color_profile_rule(self, css_text: str) -> List[ColorProfileRule]:
        """
        Parse @color-profile rules from CSS text

        Example:
            @color-profile --my-display-p3 {
                src: url("display-p3.icc");
                rendering-intent: perceptual;
            }
        """
        profiles = []

        for match in self.color_profile_pattern.finditer(css_text):
            name = match.group(1)  # Include the -- prefix
            body = match.group(2).strip()

            profile = ColorProfileRule(name=name)

            # Parse properties in the rule body
            properties = self._parse_rule_body(body)

            if 'src' in properties:
                profile.src = self._extract_url(properties['src'])

            if 'rendering-intent' in properties:
                profile.rendering_intent = properties['rendering-intent'].strip('\'"')

            if 'components' in properties:
                profile.components = [
                    comp.strip() for comp in properties['components'].split(',')
                ]

            profiles.append(profile)
            self.color_profiles[name] = profile

            logger.debug(f"Parsed color profile: {name} -> {profile}")

        return profiles

    def _parse_rule_body(self, body: str) -> Dict[str, str]:
        """Parse CSS rule body into property-value pairs"""
        properties = {}

        # Split by semicolons and parse each declaration
        declarations = body.split(';')

        for decl in declarations:
            decl = decl.strip()
            if ':' in decl:
                prop, value = decl.split(':', 1)
                properties[prop.strip()] = value.strip()

        return properties

    def _extract_url(self, url_value: str) -> str:
        """Extract URL from CSS url() function"""
        url_match = re.search(r'url\s*\(\s*["\']?([^"\']+)["\']?\s*\)', url_value)
        if url_match:
            return url_match.group(1)
        return url_value.strip('\'"')

    def detect_color_functions(self, text: str) -> List[Tuple[str, CSSColor]]:
        """
        Detect all color() functions in text and parse them

        Returns list of (original_text, parsed_function) tuples
        """
        results = []

        for match in self.color_function_pattern.finditer(text):
            original = match.group(0)
            parsed = parse_css_color4_function(original)
            if parsed:
                results.append((original, parsed))

        return results

    def get_color_profile(self, name: str) -> Optional[ColorProfileRule]:
        """Get a registered color profile by name"""
        return self.color_profiles.get(name)


class CSSColor4Converter:
    """Converts CSS Color 4 functions to sRGB using existing color system"""

    def __init__(self, icc_converter=None, known_profiles=None):
        """
        Initialize with color conversion backends

        Args:
            icc_converter: ICCConverter instance for profile-based conversion
            known_profiles: KnownProfiles instance for built-in color spaces
        """
        self.parser = CSSColor4Parser()
        self.icc_converter = icc_converter
        self.known_profiles = known_profiles

    def convert_css_color(self, css_color: CSSColor) -> Tuple[float, float, float, float]:
        """
        Convert a parsed CSS color to sRGB

        Returns (r, g, b, a) in 0-1 range
        """
        if not css_color:
            return (0.0, 0.0, 0.0, 1.0)

        # Already sRGB - no conversion needed
        if css_color.space == 'srgb':
            return (*css_color.coords, css_color.alpha)

        # Handle special color spaces (lab, lch, oklab, oklch)
        if css_color.space in ['lab', 'lch', 'oklab', 'oklch']:
            return self._convert_perceptual_color_space(css_color)

        # Handle XYZ color spaces
        if css_color.space.startswith('xyz'):
            return self._convert_xyz_color_space(css_color)

        # Handle RGB color spaces via existing color system
        return self._convert_rgb_color_space(css_color)

    def _convert_rgb_color_space(self, css_color: CSSColor) -> Tuple[float, float, float, float]:
        """Convert RGB-based color spaces using existing system"""
        r, g, b = css_color.coords[:3]

        # Try known profiles first
        if self.known_profiles:
            try:
                import numpy as np
                rgb_array = np.array([[r, g, b]])
                converted = self.known_profiles.convert_to_srgb(rgb_array, css_color.space)
                if converted is not None:
                    r_conv, g_conv, b_conv = converted[0]
                    return (r_conv, g_conv, b_conv, css_color.alpha)
            except Exception as e:
                logger.debug(f"Known profiles conversion failed: {e}")

        # Fallback to ICC converter
        if self.icc_converter:
            try:
                result = self.icc_converter.convert_to_srgb(
                    (r, g, b),
                    css_color.space
                )
                if result.success:
                    return (*result.color, css_color.alpha)
            except Exception as e:
                logger.debug(f"ICC conversion failed: {e}")

        # Ultimate fallback - return as-is (assume sRGB)
        logger.warning(f"No conversion available for {css_color.space}, treating as sRGB")
        return (r, g, b, css_color.alpha)

    def _convert_perceptual_color_space(self, css_color: CSSColor) -> Tuple[float, float, float, float]:
        """Convert LAB, LCH, OKLAB, OKLCH color spaces"""
        # For now, use safe LAB conversion if available
        if css_color.space == 'lab':
            try:
                from core.color.safe_lab import convert_lab_to_srgb_safe
                lab_tuple = css_color.coords[:3]
                rgb = convert_lab_to_srgb_safe(lab_tuple)
                return (*rgb, css_color.alpha)
            except Exception as e:
                logger.debug(f"LAB conversion failed: {e}")

        logger.warning(f"Perceptual color space {css_color.space} not yet implemented")
        return (0.5, 0.5, 0.5, css_color.alpha)

    def _convert_xyz_color_space(self, css_color: CSSColor) -> Tuple[float, float, float, float]:
        """Convert XYZ color spaces"""
        logger.warning(f"XYZ color space {css_color.space} not yet implemented")
        return (0.5, 0.5, 0.5, css_color.alpha)

    def resolve_color(self, expr: str) -> Tuple[float, float, float, float]:
        """Main entry point - parse and convert CSS Color 4 functions to sRGB"""
        parsed = parse_css_color4_function(expr)
        if not parsed:
            raise ValueError(f"Not a CSS Color 4 function: {expr}")
        return self.convert_css_color(parsed)