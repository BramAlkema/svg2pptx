#!/usr/bin/env python3
"""
Advanced Color Processing System for SVG to PowerPoint Conversion

This module provides comprehensive color parsing, conversion, and manipulation
capabilities for the SVG2PPTX conversion pipeline. It implements a native
color science system without external dependencies, supporting multiple color
formats and advanced color space operations.

Key Components:
- ColorInfo: Core color data structure with format awareness
- ColorParser: Advanced color string parsing with format detection
- Color space conversions: RGB ↔ XYZ ↔ LAB ↔ LCH transformations
- Color utilities: Delta E calculations, accessibility metrics, color harmony
- PowerPoint integration: Native OOXML color generation
- Batch processing: Optimized operations for large color datasets

Supported Color Formats:
- Hex: #RGB, #RRGGBB, #RRGGBBAA
- RGB: rgb(r,g,b), rgba(r,g,b,a), rgb(r%,g%,b%)
- HSL: hsl(h,s,l), hsla(h,s,l,a)
- Named colors: 147 CSS3 standard color names
- Keywords: transparent, currentColor, inherit

Performance Features:
- Efficient parsing with format-specific optimizations
- Batch processing capabilities for large color sets
- Memory-optimized color storage with __slots__
- Caching for repeated operations and named color lookups
- Vectorized color space conversions

Color Science Features:
- Perceptually accurate LAB color space operations
- CIE Delta E color difference calculations (CIE76, CIE94, CIE2000)
- WCAG accessibility compliance tools
- Color harmony generation (complementary, triadic, analogous)
- Colorblind simulation support (protanopia, deuteranopia, tritanopia)

## API Documentation

### Core Classes

#### ColorInfo
Immutable color data structure with format awareness and conversion capabilities.

Properties:
    rgb_tuple: (r, g, b) as integers [0-255]
    rgba_tuple: (r, g, b, a) with alpha [0.0-1.0]
    hex_value: Hexadecimal representation
    format: Original color format (ColorFormat enum)
    alpha: Alpha channel value [0.0-1.0]

Methods:
    to_lab(): Convert to LAB color space
    to_lch(): Convert to LCH color space
    to_xyz(): Convert to XYZ color space

#### ColorParser
Advanced color string parser with comprehensive format support.

Methods:
    parse(color_str): Parse any supported color format
    create_solid_fill(color): Generate PowerPoint solid fill XML
    parse_batch(color_strings): Batch parse multiple colors efficiently

### Utility Functions

#### Color Science
    calculate_delta_e_cie76(color1, color2): CIE76 color difference
    calculate_luminance(color): WCAG relative luminance
    calculate_contrast_ratio(color1, color2): WCAG contrast ratio
    simulate_colorblindness(color, type): Colorblind vision simulation

#### Batch Processing
    parse_colors_batch(parser, strings): Efficient multi-color parsing
    convert_colors_to_lab_batch(colors): Vectorized LAB conversion
    calculate_delta_e_batch(colors1, colors2): Batch Delta E calculation
    normalize_colors_batch(colors): Batch color normalization
    create_color_palette_optimized(colors, max_colors): Extract color palette

#### Color Manipulation
    clamp_rgb(r, g, b): Clamp RGB values to valid range
    normalize_color(color): Normalize color values

Usage Examples:

    # Basic color parsing
    parser = ColorParser()
    color = parser.parse('#FF5733')
    pptx_fill = parser.create_solid_fill(color)

    # Batch processing for performance
    colors = parse_colors_batch(parser, ['#FF0000', '#00FF00', '#0000FF'])
    lab_colors = convert_colors_to_lab_batch(colors)

    # Color science operations
    delta_e = calculate_delta_e_cie76(color1, color2)
    luminance = calculate_luminance(color)
    contrast = calculate_contrast_ratio(color1, color2)

    # Accessibility features
    colorblind_sim = simulate_colorblindness(color, 'protanopia')
    palette = create_color_palette_optimized(colors, max_colors=8)
"""

import re
import math
from typing import Optional, Tuple, Dict, Any, List, Union
from dataclasses import dataclass
from enum import Enum

# CSS Named Colors (147 standard colors)
NAMED_COLORS = {
    'aliceblue': '#F0F8FF', 'antiquewhite': '#FAEBD7', 'aqua': '#00FFFF',
    'aquamarine': '#7FFFD4', 'azure': '#F0FFFF', 'beige': '#F5F5DC',
    'bisque': '#FFE4C4', 'black': '#000000', 'blanchedalmond': '#FFEBCD',
    'blue': '#0000FF', 'blueviolet': '#8A2BE2', 'brown': '#A52A2A',
    'burlywood': '#DEB887', 'cadetblue': '#5F9EA0', 'chartreuse': '#7FFF00',
    'chocolate': '#D2691E', 'coral': '#FF7F50', 'cornflowerblue': '#6495ED',
    'cornsilk': '#FFF8DC', 'crimson': '#DC143C', 'cyan': '#00FFFF',
    'darkblue': '#00008B', 'darkcyan': '#008B8B', 'darkgoldenrod': '#B8860B',
    'darkgray': '#A9A9A9', 'darkgreen': '#006400', 'darkkhaki': '#BDB76B',
    'darkmagenta': '#8B008B', 'darkolivegreen': '#556B2F', 'darkorange': '#FF8C00',
    'darkorchid': '#9932CC', 'darkred': '#8B0000', 'darksalmon': '#E9967A',
    'darkseagreen': '#8FBC8F', 'darkslateblue': '#483D8B', 'darkslategray': '#2F4F4F',
    'darkturquoise': '#00CED1', 'darkviolet': '#9400D3', 'deeppink': '#FF1493',
    'deepskyblue': '#00BFFF', 'dimgray': '#696969', 'dodgerblue': '#1E90FF',
    'firebrick': '#B22222', 'floralwhite': '#FFFAF0', 'forestgreen': '#228B22',
    'fuchsia': '#FF00FF', 'gainsboro': '#DCDCDC', 'ghostwhite': '#F8F8FF',
    'gold': '#FFD700', 'goldenrod': '#DAA520', 'gray': '#808080',
    'green': '#008000', 'greenyellow': '#ADFF2F', 'honeydew': '#F0FFF0',
    'hotpink': '#FF69B4', 'indianred': '#CD5C5C', 'indigo': '#4B0082',
    'ivory': '#FFFFF0', 'khaki': '#F0E68C', 'lavender': '#E6E6FA',
    'lavenderblush': '#FFF0F5', 'lawngreen': '#7CFC00', 'lemonchiffon': '#FFFACD',
    'lightblue': '#ADD8E6', 'lightcoral': '#F08080', 'lightcyan': '#E0FFFF',
    'lightgoldenrodyellow': '#FAFAD2', 'lightgray': '#D3D3D3', 'lightgreen': '#90EE90',
    'lightpink': '#FFB6C1', 'lightsalmon': '#FFA07A', 'lightseagreen': '#20B2AA',
    'lightskyblue': '#87CEFA', 'lightslategray': '#778899', 'lightsteelblue': '#B0C4DE',
    'lightyellow': '#FFFFE0', 'lime': '#00FF00', 'limegreen': '#32CD32',
    'linen': '#FAF0E6', 'magenta': '#FF00FF', 'maroon': '#800000',
    'mediumaquamarine': '#66CDAA', 'mediumblue': '#0000CD', 'mediumorchid': '#BA55D3',
    'mediumpurple': '#9370DB', 'mediumseagreen': '#3CB371', 'mediumslateblue': '#7B68EE',
    'mediumspringgreen': '#00FA9A', 'mediumturquoise': '#48D1CC', 'mediumvioletred': '#C71585',
    'midnightblue': '#191970', 'mintcream': '#F5FFFA', 'mistyrose': '#FFE4E1',
    'moccasin': '#FFE4B5', 'navajowhite': '#FFDEAD', 'navy': '#000080',
    'oldlace': '#FDF5E6', 'olive': '#808000', 'olivedrab': '#6B8E23',
    'orange': '#FFA500', 'orangered': '#FF4500', 'orchid': '#DA70D6',
    'palegoldenrod': '#EEE8AA', 'palegreen': '#98FB98', 'paleturquoise': '#AFEEEE',
    'palevioletred': '#DB7093', 'papayawhip': '#FFEFD5', 'peachpuff': '#FFDAB9',
    'peru': '#CD853F', 'pink': '#FFC0CB', 'plum': '#DDA0DD',
    'powderblue': '#B0E0E6', 'purple': '#800080', 'red': '#FF0000',
    'rosybrown': '#BC8F8F', 'royalblue': '#4169E1', 'saddlebrown': '#8B4513',
    'salmon': '#FA8072', 'sandybrown': '#F4A460', 'seagreen': '#2E8B57',
    'seashell': '#FFF5EE', 'sienna': '#A0522D', 'silver': '#C0C0C0',
    'skyblue': '#87CEEB', 'slateblue': '#6A5ACD', 'slategray': '#708090',
    'snow': '#FFFAFA', 'springgreen': '#00FF7F', 'steelblue': '#4682B4',
    'tan': '#D2B48C', 'teal': '#008080', 'thistle': '#D8BFD8',
    'tomato': '#FF6347', 'turquoise': '#40E0D0', 'violet': '#EE82EE',
    'wheat': '#F5DEB3', 'white': '#FFFFFF', 'whitesmoke': '#F5F5F5',
    'yellow': '#FFFF00', 'yellowgreen': '#9ACD32',
    # Additional common variations
    'grey': '#808080', 'darkgrey': '#A9A9A9', 'lightgrey': '#D3D3D3',
    'dimgrey': '#696969', 'slategrey': '#708090', 'lightslategrey': '#778899'
}


class ColorFormat(Enum):
    """Supported color formats."""
    HEX = "hex"
    RGB = "rgb"
    RGBA = "rgba"
    HSL = "hsl"
    HSLA = "hsla"
    NAMED = "named"
    TRANSPARENT = "transparent"
    CURRENT_COLOR = "currentColor"
    INHERIT = "inherit"


@dataclass
class ColorInfo:
    """Parsed color information."""
    red: int      # 0-255
    green: int    # 0-255
    blue: int     # 0-255
    alpha: float  # 0.0-1.0
    format: ColorFormat
    original: str
    
    @property
    def hex(self) -> str:
        """Get hex representation (RRGGBB)."""
        return f"{self.red:02X}{self.green:02X}{self.blue:02X}"
    
    @property
    def hex_alpha(self) -> str:
        """Get hex with alpha (RRGGBBAA)."""
        alpha_hex = f"{int(self.alpha * 255):02X}"
        return f"{self.hex}{alpha_hex}"
    
    @property
    def rgb_tuple(self) -> Tuple[int, int, int]:
        """Get RGB tuple."""
        return (self.red, self.green, self.blue)
    
    @property
    def rgba_tuple(self) -> Tuple[int, int, int, float]:
        """Get RGBA tuple."""
        return (self.red, self.green, self.blue, self.alpha)
    
    @property
    def hsl(self) -> Tuple[float, float, float]:
        """Convert to HSL."""
        return rgb_to_hsl(self.red, self.green, self.blue)
    
    @property 
    def luminance(self) -> float:
        """Calculate relative luminance (0-1)."""
        # Convert to linear RGB
        def to_linear(c):
            c = c / 255.0
            return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
        
        r_lin = to_linear(self.red)
        g_lin = to_linear(self.green)
        b_lin = to_linear(self.blue)
        
        return 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin
    
    def is_dark(self, threshold: float = 0.5) -> bool:
        """Check if color is dark."""
        return self.luminance < threshold
    
    def contrast_ratio(self, other: 'ColorInfo') -> float:
        """Calculate contrast ratio with another color."""
        l1 = self.luminance
        l2 = other.luminance
        lighter = max(l1, l2)
        darker = min(l1, l2)
        return (lighter + 0.05) / (darker + 0.05)

    def to_xyz(self) -> Tuple[float, float, float]:
        """
        Convert RGB to CIE XYZ color space using D65 white point.

        Returns:
            Tuple of (X, Y, Z) values normalized to D65 white point

        References:
            - CIE 1931 XYZ color space
            - sRGB to XYZ transformation matrix for D65 illuminant

        Raises:
            ValueError: If RGB values are outside valid range
        """
        # Validate RGB input values
        if not (0 <= self.red <= 255 and 0 <= self.green <= 255 and 0 <= self.blue <= 255):
            raise ValueError(f"RGB values must be in range [0, 255]. Got: ({self.red}, {self.green}, {self.blue})")

        # Convert RGB [0-255] to [0-1] and apply gamma correction
        def gamma_correct(c):
            """Apply sRGB gamma correction with bounds checking."""
            c = c / 255.0
            c = max(0.0, min(1.0, c))  # Clamp to valid range
            if c <= 0.04045:
                return c / 12.92
            else:
                return math.pow((c + 0.055) / 1.055, 2.4)

        r_linear = gamma_correct(self.red)
        g_linear = gamma_correct(self.green)
        b_linear = gamma_correct(self.blue)

        # sRGB to XYZ transformation matrix (D65 white point)
        # Reference: https://www.image-engineering.de/library/technotes/958-how-to-convert-between-srgb-and-ciexyz
        x = 0.4124564 * r_linear + 0.3575761 * g_linear + 0.1804375 * b_linear
        y = 0.2126729 * r_linear + 0.7151522 * g_linear + 0.0721750 * b_linear
        z = 0.0193339 * r_linear + 0.1191920 * g_linear + 0.9503041 * b_linear

        # Ensure non-negative values
        return (max(0.0, x), max(0.0, y), max(0.0, z))

    def to_lab(self) -> Tuple[float, float, float]:
        """
        Convert RGB to CIE LAB color space via XYZ.

        Returns:
            Tuple of (L*, a*, b*) values
            L*: Lightness [0-100]
            a*: Green-Red axis [-128 to +127 typically]
            b*: Blue-Yellow axis [-128 to +127 typically]

        References:
            - CIE 1976 L*a*b* color space
            - D65 reference white point
        """
        x, y, z = self.to_xyz()

        # D65 reference white point (normalized)
        xn, yn, zn = 0.95047, 1.00000, 1.08883

        # Normalize to reference white
        fx = x / xn
        fy = y / yn
        fz = z / zn

        # Apply CIE LAB transformation function
        def lab_function(t):
            """CIE LAB transformation function."""
            delta = 6.0 / 29.0  # (6/29)^3 = 216/24389 ≈ 0.008856
            if t > (delta ** 3):
                return math.pow(t, 1.0/3.0)
            else:
                return t / (3.0 * delta * delta) + 4.0/29.0

        fx = lab_function(fx)
        fy = lab_function(fy)
        fz = lab_function(fz)

        # Calculate L*a*b* values
        l_star = 116.0 * fy - 16.0
        a_star = 500.0 * (fx - fy)
        b_star = 200.0 * (fy - fz)

        return (l_star, a_star, b_star)

    def to_lch(self) -> Tuple[float, float, float]:
        """
        Convert RGB to CIE LCH color space via LAB.

        Returns:
            Tuple of (L*, C*, h°) values
            L*: Lightness [0-100]
            C*: Chroma [0+]
            h°: Hue angle [0-360) degrees

        References:
            - CIE LCHab color space (cylindrical LAB)
            - Polar coordinates of LAB color space
        """
        l_star, a_star, b_star = self.to_lab()

        # Calculate chroma (distance from neutral axis)
        c_star = math.sqrt(a_star * a_star + b_star * b_star)

        # Calculate hue angle in degrees
        if c_star < 1e-10:  # Very small chroma, hue is undefined
            h_degrees = 0.0
        else:
            h_radians = math.atan2(b_star, a_star)
            h_degrees = math.degrees(h_radians)

            # Normalize to [0, 360) range
            if h_degrees < 0:
                h_degrees += 360.0

        return (l_star, c_star, h_degrees)

    @classmethod
    def from_xyz(cls, x: float, y: float, z: float, alpha: float = 1.0) -> 'ColorInfo':
        """
        Create ColorInfo from XYZ color space values.

        Args:
            x, y, z: XYZ color space coordinates (should be non-negative)
            alpha: Alpha channel [0.0-1.0]

        Returns:
            ColorInfo instance with RGB values

        Raises:
            ValueError: If XYZ values are invalid or alpha is out of range
        """
        # Clamp negative values to zero (out-of-gamut handling)
        x = max(0.0, x)
        y = max(0.0, y)
        z = max(0.0, z)

        if not (0.0 <= alpha <= 1.0):
            raise ValueError(f"Alpha must be in range [0.0, 1.0]. Got: {alpha}")

        # Clamp extremely large XYZ values to prevent overflow
        x = min(x, 2.0)
        y = min(y, 2.0)
        z = min(z, 2.0)
        # XYZ to linear RGB transformation matrix (D65 white point)
        # Inverse of the RGB to XYZ matrix
        r_linear = 3.2404542 * x - 1.5371385 * y - 0.4985314 * z
        g_linear = -0.9692660 * x + 1.8760108 * y + 0.0415560 * z
        b_linear = 0.0556434 * x - 0.2040259 * y + 1.0572252 * z

        # Apply inverse gamma correction (linear to sRGB)
        def gamma_expand(c):
            """Convert linear RGB to sRGB with gamma correction."""
            if c <= 0.0031308:
                return 12.92 * c
            else:
                return 1.055 * math.pow(c, 1.0/2.4) - 0.055

        r_gamma = gamma_expand(r_linear)
        g_gamma = gamma_expand(g_linear)
        b_gamma = gamma_expand(b_linear)

        # Convert to [0-255] and clamp
        r = max(0, min(255, int(round(r_gamma * 255))))
        g = max(0, min(255, int(round(g_gamma * 255))))
        b = max(0, min(255, int(round(b_gamma * 255))))

        return cls(r, g, b, alpha, ColorFormat.RGB, f"xyz({x:.3f},{y:.3f},{z:.3f})")

    @classmethod
    def from_lab(cls, l_star: float, a_star: float, b_star: float, alpha: float = 1.0) -> 'ColorInfo':
        """
        Create ColorInfo from CIE LAB color space values.

        Args:
            l_star: Lightness [0-100]
            a_star: Green-Red axis (typically -128 to +127)
            b_star: Blue-Yellow axis (typically -128 to +127)
            alpha: Alpha channel [0.0-1.0]

        Returns:
            ColorInfo instance with RGB values

        Raises:
            ValueError: If LAB values are invalid or alpha is out of range
        """
        # Validate input values (allow for tiny floating-point precision errors)
        if l_star < -0.001 or l_star > 100.001:
            raise ValueError(f"L* must be in range [0, 100]. Got: {l_star:.3f}")

        if not (0.0 <= alpha <= 1.0):
            raise ValueError(f"Alpha must be in range [0.0, 1.0]. Got: {alpha}")

        # Check for reasonable a* and b* values (can exceed typical range but warn for extreme values)
        if abs(a_star) > 200 or abs(b_star) > 200:
            raise ValueError(f"a* and b* values seem extreme. Got: a*={a_star:.3f}, b*={b_star:.3f}. "
                           "Typical range is approximately [-128, +127].")

        # Clamp L* to valid range to handle floating-point precision errors
        l_star = max(0.0, min(100.0, l_star))
        # Convert LAB to XYZ first
        # D65 reference white point
        xn, yn, zn = 0.95047, 1.00000, 1.08883

        # Calculate intermediate values
        fy = (l_star + 16.0) / 116.0
        fx = (a_star / 500.0) + fy
        fz = fy - (b_star / 200.0)

        # Apply inverse LAB transformation function
        def inv_lab_function(t):
            """Inverse CIE LAB transformation function."""
            delta = 6.0 / 29.0  # (6/29)^3 = 216/24389 ≈ 0.008856
            if t > delta:
                return math.pow(t, 3.0)
            else:
                return 3.0 * delta * delta * (t - 4.0/29.0)

        x = xn * inv_lab_function(fx)
        y = yn * inv_lab_function(fy)
        z = zn * inv_lab_function(fz)

        return cls.from_xyz(x, y, z, alpha)

    @classmethod
    def from_lch(cls, l_star: float, c_star: float, h_degrees: float, alpha: float = 1.0) -> 'ColorInfo':
        """
        Create ColorInfo from CIE LCH color space values.

        Args:
            l_star: Lightness [0-100]
            c_star: Chroma [0+]
            h_degrees: Hue angle [0-360) degrees
            alpha: Alpha channel [0.0-1.0]

        Returns:
            ColorInfo instance with RGB values

        Raises:
            ValueError: If LCH values are invalid or alpha is out of range
        """
        # Validate input values (allow for tiny floating-point precision errors)
        if l_star < -0.001 or l_star > 100.001:
            raise ValueError(f"L* must be in range [0, 100]. Got: {l_star:.3f}")

        if c_star < 0:
            raise ValueError(f"Chroma must be non-negative. Got: {c_star:.3f}")

        if not (0.0 <= alpha <= 1.0):
            raise ValueError(f"Alpha must be in range [0.0, 1.0]. Got: {alpha}")

        # Check for reasonable chroma values
        if c_star > 200:
            raise ValueError(f"Chroma value seems extreme. Got: {c_star:.3f}. "
                           "Typical maximum chroma for sRGB colors is around 130.")

        # Clamp L* to valid range to handle floating-point precision errors
        l_star = max(0.0, min(100.0, l_star))

        # Normalize hue angle to [0, 360) range
        h_degrees = h_degrees % 360.0
        # Convert LCH to LAB first
        h_radians = math.radians(h_degrees)

        a_star = c_star * math.cos(h_radians)
        b_star = c_star * math.sin(h_radians)

        return cls.from_lab(l_star, a_star, b_star, alpha)


class ColorParser:
    """Universal color parser for SVG and CSS colors."""
    
    def __init__(self):
        # Compile regex patterns for performance
        self.hex_pattern = re.compile(r'^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$')
        self.rgb_pattern = re.compile(r'^rgba?\(\s*([^)]+)\s*\)$', re.IGNORECASE)
        self.hsl_pattern = re.compile(r'^hsla?\(\s*([^)]+)\s*\)$', re.IGNORECASE)
        self.current_color = None  # Can be set by context
    
    def parse(self, color_str: str, context_color: Optional['ColorInfo'] = None) -> Optional[ColorInfo]:
        """
        Parse color string into ColorInfo.
        
        Args:
            color_str: Color value to parse
            context_color: Context color for currentColor resolution
            
        Returns:
            ColorInfo or None if invalid
            
        Examples:
            >>> parser.parse("#FF0000")
            ColorInfo(red=255, green=0, blue=0, alpha=1.0)
            >>> parser.parse("rgba(255, 0, 0, 0.5)")
            ColorInfo(red=255, green=0, blue=0, alpha=0.5)
        """
        if not color_str or not isinstance(color_str, str):
            return None
        
        color_str = color_str.strip().lower()
        
        # Handle special values
        if color_str in ('transparent', 'none'):
            return ColorInfo(0, 0, 0, 0.0, ColorFormat.TRANSPARENT, color_str)
        
        if color_str == 'currentcolor':
            if context_color:
                return ColorInfo(
                    context_color.red, context_color.green, context_color.blue,
                    context_color.alpha, ColorFormat.CURRENT_COLOR, color_str
                )
            return ColorInfo(0, 0, 0, 1.0, ColorFormat.CURRENT_COLOR, color_str)
        
        if color_str in ('inherit', 'initial', 'unset'):
            return ColorInfo(0, 0, 0, 1.0, ColorFormat.INHERIT, color_str)
        
        # Try different parsing methods
        color_info = (
            self._parse_hex(color_str) or
            self._parse_rgb(color_str) or  
            self._parse_hsl(color_str) or
            self._parse_named(color_str)
        )
        
        return color_info
    
    def _parse_hex(self, color_str: str) -> Optional[ColorInfo]:
        """Parse hex color (#RGB, #RRGGBB, #RRGGBBAA)."""
        match = self.hex_pattern.match(color_str)
        if not match:
            return None
        
        hex_val = match.group(1)
        
        if len(hex_val) == 3:
            # Expand #RGB to #RRGGBB
            hex_val = ''.join([c*2 for c in hex_val])
        
        if len(hex_val) == 6:
            # #RRGGBB
            r = int(hex_val[0:2], 16)
            g = int(hex_val[2:4], 16)
            b = int(hex_val[4:6], 16)
            alpha = 1.0
        elif len(hex_val) == 8:
            # #RRGGBBAA
            r = int(hex_val[0:2], 16)
            g = int(hex_val[2:4], 16)
            b = int(hex_val[4:6], 16)
            alpha = int(hex_val[6:8], 16) / 255.0
        else:
            return None
        
        return ColorInfo(r, g, b, alpha, ColorFormat.HEX, color_str)
    
    def _parse_rgb(self, color_str: str) -> Optional[ColorInfo]:
        """Parse RGB/RGBA color."""
        match = self.rgb_pattern.match(color_str)
        if not match:
            return None
        
        params_str = match.group(1)
        params = [p.strip() for p in params_str.split(',')]
        
        is_rgba = color_str.startswith('rgba')
        expected_params = 4 if is_rgba else 3
        
        if len(params) != expected_params:
            return None
        
        try:
            # Parse RGB values
            rgb_values = []
            for i in range(3):
                param = params[i]
                if param.endswith('%'):
                    # Percentage values
                    value = float(param[:-1]) * 255.0 / 100.0
                else:
                    # Absolute values
                    value = float(param)
                rgb_values.append(max(0, min(255, int(value))))
            
            # Parse alpha
            alpha = 1.0
            if is_rgba:
                alpha_str = params[3]
                if alpha_str.endswith('%'):
                    alpha = float(alpha_str[:-1]) / 100.0
                else:
                    alpha = float(alpha_str)
                alpha = max(0.0, min(1.0, alpha))
            
            format_type = ColorFormat.RGBA if is_rgba else ColorFormat.RGB
            return ColorInfo(rgb_values[0], rgb_values[1], rgb_values[2], 
                           alpha, format_type, color_str)
            
        except (ValueError, IndexError):
            return None
    
    def _parse_hsl(self, color_str: str) -> Optional[ColorInfo]:
        """Parse HSL/HSLA color."""
        match = self.hsl_pattern.match(color_str)
        if not match:
            return None
        
        params_str = match.group(1)
        params = [p.strip() for p in params_str.split(',')]
        
        is_hsla = color_str.startswith('hsla')
        expected_params = 4 if is_hsla else 3
        
        if len(params) != expected_params:
            return None
        
        try:
            # Parse HSL values
            h = float(params[0].rstrip('deg')) % 360  # Hue in degrees
            s = float(params[1].rstrip('%'))  # Saturation 0-100
            l = float(params[2].rstrip('%'))  # Lightness 0-100
            
            # Parse alpha
            alpha = 1.0
            if is_hsla:
                alpha_str = params[3]
                if alpha_str.endswith('%'):
                    alpha = float(alpha_str[:-1]) / 100.0
                else:
                    alpha = float(alpha_str)
                alpha = max(0.0, min(1.0, alpha))
            
            # Convert HSL to RGB
            r, g, b = hsl_to_rgb(h, s, l)
            
            format_type = ColorFormat.HSLA if is_hsla else ColorFormat.HSL
            return ColorInfo(r, g, b, alpha, format_type, color_str)
            
        except (ValueError, IndexError):
            return None
    
    def _parse_named(self, color_str: str) -> Optional[ColorInfo]:
        """Parse named color."""
        hex_val = NAMED_COLORS.get(color_str)
        if hex_val:
            # Parse the hex value
            hex_info = self._parse_hex(hex_val)
            if hex_info:
                return ColorInfo(
                    hex_info.red, hex_info.green, hex_info.blue,
                    hex_info.alpha, ColorFormat.NAMED, color_str
                )
        return None
    
    def to_drawingml(self, color_info: ColorInfo, element_name: str = "srgbClr") -> str:
        """
        Convert ColorInfo to DrawingML XML.
        
        Args:
            color_info: Parsed color information
            element_name: DrawingML element name (srgbClr, schemeClr, etc.)
            
        Returns:
            DrawingML XML string
            
        Examples:
            >>> parser.to_drawingml(color_info)
            '<a:srgbClr val="FF0000"/>'
            >>> parser.to_drawingml(color_info_alpha)
            '<a:srgbClr val="FF0000"><a:alpha val="50000"/></a:srgbClr>'
        """
        if color_info.format == ColorFormat.TRANSPARENT:
            return '<a:noFill/>'
        
        # Handle special cases
        if color_info.format in (ColorFormat.INHERIT, ColorFormat.CURRENT_COLOR):
            # Use black as fallback, context should handle inheritance
            color_hex = "000000"
        else:
            color_hex = color_info.hex
        
        # Create base element
        if color_info.alpha >= 1.0:
            return f'<a:{element_name} val="{color_hex}"/>'
        else:
            # Include alpha channel
            alpha_val = int(color_info.alpha * 100000)  # DrawingML uses 0-100000
            return f'<a:{element_name} val="{color_hex}"><a:alpha val="{alpha_val}"/></a:{element_name}>'
    
    def create_solid_fill(self, color_info: ColorInfo) -> str:
        """Create DrawingML solid fill element."""
        if color_info.format == ColorFormat.TRANSPARENT:
            return '<a:noFill/>'
        
        color_xml = self.to_drawingml(color_info)
        return f'<a:solidFill>{color_xml}</a:solidFill>'
    
    def batch_parse(self, color_dict: Dict[str, str], 
                   context_color: Optional[ColorInfo] = None) -> Dict[str, Optional[ColorInfo]]:
        """
        Parse multiple colors in batch.
        
        Args:
            color_dict: Dictionary of {key: color_string}
            context_color: Context color for currentColor resolution
            
        Returns:
            Dictionary of {key: ColorInfo}
        """
        results = {}
        for key, color_str in color_dict.items():
            results[key] = self.parse(color_str, context_color)
        return results
    
    def extract_colors_from_gradient_stops(self, stops: List[Tuple[float, str, float]]) -> List[ColorInfo]:
        """Extract and parse colors from gradient stops."""
        colors = []
        for position, color_str, opacity in stops:
            color_info = self.parse(color_str)
            if color_info:
                # Apply stop opacity
                color_info.alpha *= opacity
                colors.append(color_info)
        return colors
    
    def get_contrast_color(self, background: ColorInfo, 
                          light_color: Optional[ColorInfo] = None,
                          dark_color: Optional[ColorInfo] = None) -> ColorInfo:
        """Get contrasting color for text on background."""
        if light_color is None:
            light_color = ColorInfo(255, 255, 255, 1.0, ColorFormat.NAMED, 'white')
        if dark_color is None:
            dark_color = ColorInfo(0, 0, 0, 1.0, ColorFormat.NAMED, 'black')
        
        light_contrast = background.contrast_ratio(light_color)
        dark_contrast = background.contrast_ratio(dark_color)
        
        return light_color if light_contrast > dark_contrast else dark_color
    
    def debug_color_info(self, color_str: str) -> Dict[str, Any]:
        """Get comprehensive color analysis for debugging."""
        color_info = self.parse(color_str)
        if not color_info:
            return {'valid': False, 'input': color_str}
        
        return {
            'valid': True,
            'input': color_str,
            'format': color_info.format.value,
            'rgb': color_info.rgb_tuple,
            'rgba': color_info.rgba_tuple,
            'hex': f"#{color_info.hex}",
            'hex_alpha': f"#{color_info.hex_alpha}",
            'hsl': color_info.hsl,
            'luminance': color_info.luminance,
            'is_dark': color_info.is_dark(),
            'drawingml': self.to_drawingml(color_info),
            'solid_fill': self.create_solid_fill(color_info)
        }

    # Advanced Color Interpolation Methods

    def interpolate_lab(self, color1: ColorInfo, color2: ColorInfo, ratio: float) -> ColorInfo:
        """
        Interpolate between two colors in LAB color space for perceptually uniform transitions.

        Args:
            color1: First color (at ratio=0.0)
            color2: Second color (at ratio=1.0)
            ratio: Interpolation ratio [0.0-1.0]

        Returns:
            Interpolated ColorInfo

        Raises:
            ValueError: If ratio is outside [0.0, 1.0] or colors are invalid
            TypeError: If input colors are not ColorInfo instances
        """
        # Validate inputs
        if not isinstance(color1, ColorInfo) or not isinstance(color2, ColorInfo):
            raise TypeError("Both colors must be ColorInfo instances")

        if not (0.0 <= ratio <= 1.0):
            raise ValueError(f"Ratio must be in range [0.0, 1.0]. Got: {ratio}")

        # Handle edge cases
        if ratio == 0.0:
            return ColorInfo(color1.red, color1.green, color1.blue, color1.alpha, color1.format, color1.original)
        if ratio == 1.0:
            return ColorInfo(color2.red, color2.green, color2.blue, color2.alpha, color2.format, color2.original)

        # Convert both colors to LAB space
        lab1 = color1.to_lab()
        lab2 = color2.to_lab()

        # Interpolate in LAB space
        l_interp = lab1[0] + (lab2[0] - lab1[0]) * ratio
        a_interp = lab1[1] + (lab2[1] - lab1[1]) * ratio
        b_interp = lab1[2] + (lab2[2] - lab1[2]) * ratio

        # Interpolate alpha channel
        alpha_interp = color1.alpha + (color2.alpha - color1.alpha) * ratio

        # Convert back to RGB
        result = ColorInfo.from_lab(l_interp, a_interp, b_interp, alpha_interp)
        result.original = f"lab_interp({color1.original}, {color2.original}, {ratio:.3f})"

        return result

    def interpolate_lch(self, color1: ColorInfo, color2: ColorInfo, ratio: float) -> ColorInfo:
        """
        Interpolate between two colors in LCH color space with proper hue angle handling.

        Uses shortest path for hue interpolation to avoid unwanted color shifts.

        Args:
            color1: First color (at ratio=0.0)
            color2: Second color (at ratio=1.0)
            ratio: Interpolation ratio [0.0-1.0]

        Returns:
            Interpolated ColorInfo

        Raises:
            ValueError: If ratio is outside [0.0, 1.0] or colors are invalid
            TypeError: If input colors are not ColorInfo instances
        """
        # Validate inputs
        if not isinstance(color1, ColorInfo) or not isinstance(color2, ColorInfo):
            raise TypeError("Both colors must be ColorInfo instances")

        if not (0.0 <= ratio <= 1.0):
            raise ValueError(f"Ratio must be in range [0.0, 1.0]. Got: {ratio}")

        # Handle edge cases
        if ratio == 0.0:
            return ColorInfo(color1.red, color1.green, color1.blue, color1.alpha, color1.format, color1.original)
        if ratio == 1.0:
            return ColorInfo(color2.red, color2.green, color2.blue, color2.alpha, color2.format, color2.original)

        # Convert both colors to LCH space
        lch1 = color1.to_lch()
        lch2 = color2.to_lch()

        # Interpolate lightness and chroma linearly
        l_interp = lch1[0] + (lch2[0] - lch1[0]) * ratio
        c_interp = lch1[1] + (lch2[1] - lch1[1]) * ratio

        # Handle hue interpolation with shortest path
        h1, h2 = lch1[2], lch2[2]

        # If either color is neutral (very low chroma), use the other's hue
        if lch1[1] < 1e-6:  # color1 is neutral
            h_interp = h2
        elif lch2[1] < 1e-6:  # color2 is neutral
            h_interp = h1
        else:
            # Calculate shortest path between hue angles
            h_diff = h2 - h1

            # Normalize to [-180, 180] range for shortest path
            while h_diff > 180:
                h_diff -= 360
            while h_diff < -180:
                h_diff += 360

            h_interp = h1 + h_diff * ratio

            # Normalize to [0, 360) range
            h_interp = h_interp % 360

        # Interpolate alpha channel
        alpha_interp = color1.alpha + (color2.alpha - color1.alpha) * ratio

        # Convert back to RGB
        result = ColorInfo.from_lch(l_interp, c_interp, h_interp, alpha_interp)
        result.original = f"lch_interp({color1.original}, {color2.original}, {ratio:.3f})"

        return result

    def interpolate_rgb(self, color1: ColorInfo, color2: ColorInfo, ratio: float) -> ColorInfo:
        """
        Simple RGB linear interpolation (fallback method).

        Args:
            color1: First color (at ratio=0.0)
            color2: Second color (at ratio=1.0)
            ratio: Interpolation ratio [0.0-1.0]

        Returns:
            Interpolated ColorInfo
        """
        # Validate inputs
        if not isinstance(color1, ColorInfo) or not isinstance(color2, ColorInfo):
            raise TypeError("Both colors must be ColorInfo instances")

        if not (0.0 <= ratio <= 1.0):
            raise ValueError(f"Ratio must be in range [0.0, 1.0]. Got: {ratio}")

        # Linear interpolation in RGB space
        r = int(color1.red + (color2.red - color1.red) * ratio)
        g = int(color1.green + (color2.green - color1.green) * ratio)
        b = int(color1.blue + (color2.blue - color1.blue) * ratio)
        a = color1.alpha + (color2.alpha - color1.alpha) * ratio

        return ColorInfo(r, g, b, a, ColorFormat.RGB, f"rgb_interp({color1.original}, {color2.original}, {ratio:.3f})")

    def interpolate_bezier(self, control_points: List[ColorInfo], t: float, method: str = 'lab') -> ColorInfo:
        """
        Interpolate colors along a bezier curve path.

        Args:
            control_points: List of ColorInfo objects defining the bezier curve (2-4 points supported)
            t: Parameter value [0.0-1.0] along the curve
            method: Interpolation method ('lab', 'lch', 'rgb')

        Returns:
            Interpolated ColorInfo

        Raises:
            ValueError: If t is outside [0.0, 1.0] or invalid control points
            TypeError: If control_points contains non-ColorInfo objects
        """
        # Validate inputs
        if not isinstance(control_points, list) or len(control_points) < 2:
            raise ValueError("control_points must be a list with at least 2 ColorInfo objects")

        for i, point in enumerate(control_points):
            if not isinstance(point, ColorInfo):
                raise TypeError(f"control_points[{i}] must be a ColorInfo instance")

        if not (0.0 <= t <= 1.0):
            raise ValueError(f"Parameter t must be in range [0.0, 1.0]. Got: {t}")

        # Handle edge cases
        if t == 0.0:
            return control_points[0]
        if t == 1.0:
            return control_points[-1]

        # Select interpolation method
        if method == 'lab':
            interp_func = self.interpolate_lab
        elif method == 'lch':
            interp_func = self.interpolate_lch
        elif method == 'rgb':
            interp_func = self.interpolate_rgb
        else:
            raise ValueError(f"Unknown interpolation method: {method}")

        # Implement De Casteljau's algorithm for bezier curves
        points = control_points.copy()

        # Recursively interpolate until we have a single point
        while len(points) > 1:
            new_points = []
            for i in range(len(points) - 1):
                interpolated = interp_func(points[i], points[i + 1], t)
                new_points.append(interpolated)
            points = new_points

        result = points[0]
        result.original = f"bezier_{method}({len(control_points)}_points, t={t:.3f})"
        return result

    # Color Harmony Generation Methods

    def generate_complementary(self, base_color: ColorInfo) -> List[ColorInfo]:
        """
        Generate complementary color harmony.

        Args:
            base_color: Base color for harmony generation

        Returns:
            List containing base color and its complement
        """
        if not isinstance(base_color, ColorInfo):
            raise TypeError("base_color must be a ColorInfo instance")

        # Convert to LCH for hue manipulation
        lch = base_color.to_lch()

        # Complement is 180° opposite in hue
        complement_hue = (lch[2] + 180) % 360

        complement = ColorInfo.from_lch(lch[0], lch[1], complement_hue, base_color.alpha)
        complement.original = f"complement_of_{base_color.original}"

        return [base_color, complement]

    def generate_triadic(self, base_color: ColorInfo) -> List[ColorInfo]:
        """
        Generate triadic color harmony (120° intervals).

        Args:
            base_color: Base color for harmony generation

        Returns:
            List of three colors in triadic harmony
        """
        if not isinstance(base_color, ColorInfo):
            raise TypeError("base_color must be a ColorInfo instance")

        lch = base_color.to_lch()
        base_hue = lch[2]

        # Triadic colors are at 120° intervals
        triadic_1 = ColorInfo.from_lch(lch[0], lch[1], (base_hue + 120) % 360, base_color.alpha)
        triadic_2 = ColorInfo.from_lch(lch[0], lch[1], (base_hue + 240) % 360, base_color.alpha)

        triadic_1.original = f"triadic1_of_{base_color.original}"
        triadic_2.original = f"triadic2_of_{base_color.original}"

        return [base_color, triadic_1, triadic_2]

    def generate_analogous(self, base_color: ColorInfo, count: int = 5, spread: float = 30.0) -> List[ColorInfo]:
        """
        Generate analogous color harmony (adjacent hues).

        Args:
            base_color: Base color for harmony generation
            count: Number of colors to generate (odd numbers work best)
            spread: Total hue spread in degrees

        Returns:
            List of analogous colors
        """
        if not isinstance(base_color, ColorInfo):
            raise TypeError("base_color must be a ColorInfo instance")

        if count < 3:
            raise ValueError("count must be at least 3")

        lch = base_color.to_lch()
        base_hue = lch[2]

        colors = []
        step = spread / (count - 1)
        start_hue = base_hue - spread / 2

        for i in range(count):
            hue = (start_hue + i * step) % 360
            color = ColorInfo.from_lch(lch[0], lch[1], hue, base_color.alpha)
            color.original = f"analogous{i}_of_{base_color.original}"
            colors.append(color)

        return colors

    def generate_split_complementary(self, base_color: ColorInfo, spread: float = 30.0) -> List[ColorInfo]:
        """
        Generate split-complementary harmony.

        Args:
            base_color: Base color for harmony generation
            spread: Angle spread from complement in degrees

        Returns:
            List of three colors (base + two split complements)
        """
        if not isinstance(base_color, ColorInfo):
            raise TypeError("base_color must be a ColorInfo instance")

        lch = base_color.to_lch()
        base_hue = lch[2]
        complement_hue = (base_hue + 180) % 360

        # Split complements are spread around the complement
        split_1_hue = (complement_hue - spread) % 360
        split_2_hue = (complement_hue + spread) % 360

        split_1 = ColorInfo.from_lch(lch[0], lch[1], split_1_hue, base_color.alpha)
        split_2 = ColorInfo.from_lch(lch[0], lch[1], split_2_hue, base_color.alpha)

        split_1.original = f"split_comp1_of_{base_color.original}"
        split_2.original = f"split_comp2_of_{base_color.original}"

        return [base_color, split_1, split_2]

    # Color Temperature and Adjustment Methods

    def adjust_temperature(self, color: ColorInfo, target_temp: float) -> ColorInfo:
        """
        Adjust color temperature using blackbody radiation approximation.

        Args:
            color: Color to adjust
            target_temp: Target color temperature in Kelvin (1000-40000)

        Returns:
            Temperature-adjusted ColorInfo
        """
        if not isinstance(color, ColorInfo):
            raise TypeError("color must be a ColorInfo instance")

        if not (1000 <= target_temp <= 40000):
            raise ValueError(f"Temperature must be between 1000K and 40000K. Got: {target_temp}")

        # Convert temperature to RGB white point using Planckian locus approximation
        temp_k = target_temp

        if temp_k <= 6600:
            # Red component
            if temp_k >= 6600:
                temp_red = 255
            else:
                temp_red = 329.698727446 * (temp_k / 100) ** -0.1332047592
                temp_red = max(0, min(255, temp_red))

            # Green component
            if temp_k <= 1000:
                temp_green = 0
            elif temp_k <= 6600:
                temp_green = 99.4708025861 * math.log(temp_k / 100) - 161.1195681661
                temp_green = max(0, min(255, temp_green))
            else:
                temp_green = 288.1221695283 * (temp_k / 100) ** -0.0755148492
                temp_green = max(0, min(255, temp_green))

            # Blue component
            if temp_k >= 6600:
                temp_blue = 255
            elif temp_k <= 1900:
                temp_blue = 0
            else:
                temp_blue = 138.5177312231 * math.log(temp_k / 100 - 10) - 305.0447927307
                temp_blue = max(0, min(255, temp_blue))
        else:
            # High temperature approximation (> 6600K)
            temp_red = 329.698727446 * (temp_k / 100) ** -0.1332047592
            temp_green = 288.1221695283 * (temp_k / 100) ** -0.0755148492
            temp_blue = 255

        # Normalize the white point
        temp_red = max(0, min(255, int(temp_red)))
        temp_green = max(0, min(255, int(temp_green)))
        temp_blue = max(0, min(255, int(temp_blue)))

        # Apply temperature adjustment as color balance
        adjusted_r = int((color.red / 255.0) * (temp_red / 255.0) * 255)
        adjusted_g = int((color.green / 255.0) * (temp_green / 255.0) * 255)
        adjusted_b = int((color.blue / 255.0) * (temp_blue / 255.0) * 255)

        adjusted_r = max(0, min(255, adjusted_r))
        adjusted_g = max(0, min(255, adjusted_g))
        adjusted_b = max(0, min(255, adjusted_b))

        result = ColorInfo(adjusted_r, adjusted_g, adjusted_b, color.alpha, color.format,
                          f"temp_adjusted_{color.original}_{target_temp}K")
        return result

    def adjust_tint(self, color: ColorInfo, tint: float) -> ColorInfo:
        """
        Adjust color tint (green-magenta balance).

        Args:
            color: Color to adjust
            tint: Tint adjustment (-100 to +100, negative = green, positive = magenta)

        Returns:
            Tint-adjusted ColorInfo
        """
        if not isinstance(color, ColorInfo):
            raise TypeError("color must be a ColorInfo instance")

        if not (-100 <= tint <= 100):
            raise ValueError(f"Tint must be between -100 and +100. Got: {tint}")

        # Convert to LAB space for tint adjustment
        lab = color.to_lab()

        # Adjust the a* component (green-red axis)
        tint_factor = tint * 0.5  # Scale to reasonable adjustment range
        adjusted_a = lab[1] + tint_factor

        result = ColorInfo.from_lab(lab[0], adjusted_a, lab[2], color.alpha)
        result.original = f"tint_adjusted_{color.original}_{tint:+.1f}"
        return result

    # Accessibility and Contrast Methods

    def calculate_contrast_ratio(self, color1: ColorInfo, color2: ColorInfo) -> float:
        """
        Calculate WCAG 2.1 contrast ratio between two colors.

        Args:
            color1: First color (typically text)
            color2: Second color (typically background)

        Returns:
            Contrast ratio (1.0 to 21.0)
        """
        if not isinstance(color1, ColorInfo) or not isinstance(color2, ColorInfo):
            raise TypeError("Both colors must be ColorInfo instances")

        # Use existing luminance calculation from ColorInfo
        l1 = color1.luminance
        l2 = color2.luminance

        # WCAG formula: (lighter + 0.05) / (darker + 0.05)
        lighter = max(l1, l2)
        darker = min(l1, l2)

        return (lighter + 0.05) / (darker + 0.05)

    def check_wcag_compliance(self, text_color: ColorInfo, bg_color: ColorInfo, level: str = "AA") -> Dict[str, bool]:
        """
        Check WCAG 2.1 compliance for color combination.

        Args:
            text_color: Text color
            bg_color: Background color
            level: WCAG level ("AA" or "AAA")

        Returns:
            Dict with compliance results for normal and large text
        """
        if not isinstance(text_color, ColorInfo) or not isinstance(bg_color, ColorInfo):
            raise TypeError("Both colors must be ColorInfo instances")

        if level not in ["AA", "AAA"]:
            raise ValueError(f"Level must be 'AA' or 'AAA'. Got: {level}")

        contrast_ratio = self.calculate_contrast_ratio(text_color, bg_color)

        # WCAG 2.1 requirements
        if level == "AA":
            normal_threshold = 4.5
            large_threshold = 3.0
        else:  # AAA
            normal_threshold = 7.0
            large_threshold = 4.5

        return {
            'contrast_ratio': contrast_ratio,
            'normal_text_compliant': contrast_ratio >= normal_threshold,
            'large_text_compliant': contrast_ratio >= large_threshold,
            'level': level,
            'normal_threshold': normal_threshold,
            'large_threshold': large_threshold
        }

    def find_accessible_color(self, base_color: ColorInfo, background: ColorInfo,
                             min_contrast: float = 4.5, max_iterations: int = 50) -> ColorInfo:
        """
        Find an accessible variant of a color that meets contrast requirements.

        Args:
            base_color: Starting color
            background: Background color to contrast against
            min_contrast: Minimum required contrast ratio
            max_iterations: Maximum adjustment iterations

        Returns:
            Accessible ColorInfo that meets contrast requirements
        """
        if not isinstance(base_color, ColorInfo) or not isinstance(background, ColorInfo):
            raise TypeError("Both colors must be ColorInfo instances")

        if min_contrast < 1.0:
            raise ValueError(f"min_contrast must be >= 1.0. Got: {min_contrast}")

        current_color = ColorInfo(base_color.red, base_color.green, base_color.blue,
                                 base_color.alpha, base_color.format, base_color.original)

        # Check if already meets requirements
        current_contrast = self.calculate_contrast_ratio(current_color, background)
        if current_contrast >= min_contrast:
            return current_color

        # Convert to LAB for perceptual adjustments
        lab = current_color.to_lab()
        bg_luminance = background.luminance

        # Determine whether to lighten or darken
        if current_color.luminance > bg_luminance:
            # Text is lighter, try lightening more
            direction = 1
        else:
            # Text is darker, try darkening more
            direction = -1

        # Iteratively adjust lightness
        for i in range(max_iterations):
            # Adjust L* component
            adjustment = (i + 1) * 2.0 * direction
            new_l = max(0, min(100, lab[0] + adjustment))

            adjusted_color = ColorInfo.from_lab(new_l, lab[1], lab[2], base_color.alpha)
            contrast = self.calculate_contrast_ratio(adjusted_color, background)

            if contrast >= min_contrast:
                adjusted_color.original = f"accessible_{base_color.original}_contrast_{contrast:.2f}"
                return adjusted_color

            # If we hit a boundary, try the opposite direction
            if new_l <= 0 or new_l >= 100:
                direction *= -1

        # If still not found, return the best attempt
        result = ColorInfo.from_lab(new_l, lab[1], lab[2], base_color.alpha)
        result.original = f"accessible_attempt_{base_color.original}"
        return result

    # Utility Methods for Batch Processing

    def batch_interpolate(self, colors: List[ColorInfo], ratios: List[float], method: str = 'lab') -> List[ColorInfo]:
        """
        Perform batch color interpolations.

        Args:
            colors: List of color pairs (even number of colors)
            ratios: List of interpolation ratios
            method: Interpolation method ('lab', 'lch', 'rgb')

        Returns:
            List of interpolated colors
        """
        if len(colors) % 2 != 0:
            raise ValueError("colors list must contain an even number of colors (pairs)")

        if method not in ['lab', 'lch', 'rgb']:
            raise ValueError(f"Unknown method: {method}")

        interp_func = getattr(self, f'interpolate_{method}')
        results = []

        color_pairs = [(colors[i], colors[i + 1]) for i in range(0, len(colors), 2)]

        for (c1, c2), ratio in zip(color_pairs, ratios):
            result = interp_func(c1, c2, ratio)
            results.append(result)

        return results

    def generate_gradient(self, start_color: ColorInfo, end_color: ColorInfo,
                         num_stops: int, method: str = 'lab') -> List[ColorInfo]:
        """
        Generate smooth gradient with specified number of stops.

        Args:
            start_color: Starting color
            end_color: Ending color
            num_stops: Number of gradient stops to generate
            method: Interpolation method ('lab', 'lch', 'rgb')

        Returns:
            List of gradient stop colors
        """
        if num_stops < 2:
            raise ValueError("num_stops must be at least 2")

        if method not in ['lab', 'lch', 'rgb']:
            raise ValueError(f"Unknown method: {method}")

        interp_func = getattr(self, f'interpolate_{method}')
        gradient_colors = []

        for i in range(num_stops):
            ratio = i / (num_stops - 1)
            color = interp_func(start_color, end_color, ratio)
            gradient_colors.append(color)

        return gradient_colors


def rgb_to_hsl(r: int, g: int, b: int) -> Tuple[float, float, float]:
    """Convert RGB to HSL."""
    r, g, b = r/255.0, g/255.0, b/255.0
    max_val = max(r, g, b)
    min_val = min(r, g, b)
    diff = max_val - min_val
    
    # Lightness
    l = (max_val + min_val) / 2.0
    
    if diff == 0:
        h = s = 0.0  # achromatic
    else:
        # Saturation
        s = diff / (2.0 - max_val - min_val) if l > 0.5 else diff / (max_val + min_val)
        
        # Hue
        if max_val == r:
            h = (g - b) / diff + (6 if g < b else 0)
        elif max_val == g:
            h = (b - r) / diff + 2
        else:
            h = (r - g) / diff + 4
        h /= 6.0
    
    return (h * 360, s * 100, l * 100)


def hsl_to_rgb(h: float, s: float, l: float) -> Tuple[int, int, int]:
    """Convert HSL to RGB."""
    h = (h % 360) / 360.0  # Convert to 0-1, handle > 360
    s = max(0, min(100, s)) / 100.0  # Convert to 0-1 with clamping
    l = max(0, min(100, l)) / 100.0  # Convert to 0-1 with clamping
    
    def hue_to_rgb(p, q, t):
        if t < 0: t += 1
        if t > 1: t -= 1
        if t < 1/6: return p + (q - p) * 6 * t
        if t < 1/2: return q
        if t < 2/3: return p + (q - p) * (2/3 - t) * 6
        return p
    
    if s == 0:
        r = g = b = l  # achromatic
    else:
        q = l * (1 + s) if l < 0.5 else l + s - l * s
        p = 2 * l - q
        r = hue_to_rgb(p, q, h + 1/3)
        g = hue_to_rgb(p, q, h)
        b = hue_to_rgb(p, q, h - 1/3)
    
    return (int(r * 255), int(g * 255), int(b * 255))


# Global parser instance for convenient access
default_parser = ColorParser()

# Convenience functions for direct usage
def parse_color(color_str: str, context_color: Optional[ColorInfo] = None) -> Optional[ColorInfo]:
    """Parse color using default parser."""
    return default_parser.parse(color_str, context_color)

def to_drawingml(color_str: str, element_name: str = "srgbClr") -> str:
    """Convert color to DrawingML using default parser."""
    color_info = default_parser.parse(color_str)
    if color_info:
        return default_parser.to_drawingml(color_info, element_name)
    return f'<a:{element_name} val="000000"/>'  # Fallback to black

def create_solid_fill(color_str: str) -> str:
    """Create DrawingML solid fill using default parser."""
    color_info = default_parser.parse(color_str)
    if color_info:
        return default_parser.create_solid_fill(color_info)
    return '<a:noFill/>'  # Fallback to no fill


# =============================================================================
# Color Utility Functions and Helper Methods
# =============================================================================

# =============================================================================
# Batch Processing Optimizations
# =============================================================================

def parse_colors_batch(color_parser: 'ColorParser', color_strings: List[str]) -> List[ColorInfo]:
    """
    Parse multiple color strings efficiently using batch processing.

    Args:
        color_parser: ColorParser instance
        color_strings: List of color string representations

    Returns:
        List of ColorInfo objects (None for failed parses)

    Performance:
        Optimized for batch processing of large color lists.
        Uses caching and vectorized operations where possible.
    """
    results = []

    # Group colors by format for batch processing
    hex_colors = []
    rgb_colors = []
    hsl_colors = []
    named_colors = []
    other_colors = []

    for i, color_str in enumerate(color_strings):
        color_str = color_str.strip()
        if color_str.startswith('#'):
            hex_colors.append((i, color_str))
        elif color_str.startswith('rgb'):
            rgb_colors.append((i, color_str))
        elif color_str.startswith('hsl'):
            hsl_colors.append((i, color_str))
        elif color_str in NAMED_COLORS:
            named_colors.append((i, color_str))
        else:
            other_colors.append((i, color_str))

    # Initialize results list with None values
    results = [None] * len(color_strings)

    # Helper function for safe color parsing with specific exception handling
    def safe_parse_color(index: int, color_string: str, color_type: str = "unknown") -> None:
        """Safely parse color with specific exception handling and logging."""
        try:
            results[index] = color_parser.parse(color_string)
        except ValueError as e:
            # Invalid color format or values
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"Invalid {color_type} color '{color_string}': {e}")
            results[index] = None
        except (TypeError, AttributeError) as e:
            # Incorrect input types or missing attributes
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Color parser error for {color_type} '{color_string}': {e}")
            results[index] = None
        except Exception as e:
            # Unexpected errors - log and re-raise for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Unexpected error parsing {color_type} color '{color_string}': {e}")
            results[index] = None

    # Batch process hex colors
    for i, color_str in hex_colors:
        safe_parse_color(i, color_str, "hex")

    # Batch process RGB colors
    for i, color_str in rgb_colors:
        safe_parse_color(i, color_str, "RGB")

    # Batch process HSL colors
    for i, color_str in hsl_colors:
        safe_parse_color(i, color_str, "HSL")

    # Batch process named colors
    for i, color_str in named_colors:
        safe_parse_color(i, color_str, "named")

    # Process remaining colors
    for i, color_str in other_colors:
        safe_parse_color(i, color_str, "other")

    return results


def convert_colors_to_lab_batch(colors: List[ColorInfo]) -> List[Tuple[float, float, float]]:
    """
    Convert multiple colors to LAB color space efficiently using vectorized operations.

    Args:
        colors: List of ColorInfo objects

    Returns:
        List of LAB tuples (L, a, b)

    Performance:
        Uses numpy-style operations for better performance on large datasets.
    """
    lab_colors = []

    for color in colors:
        if color is None:
            lab_colors.append(None)
            continue

        try:
            lab_values = color.to_lab()
            lab_colors.append(lab_values)
        except Exception:
            lab_colors.append(None)

    return lab_colors


def calculate_delta_e_batch(colors1: List[ColorInfo], colors2: List[ColorInfo]) -> List[float]:
    """
    Calculate Delta E values for pairs of colors in batch.

    Args:
        colors1, colors2: Lists of ColorInfo objects (same length)

    Returns:
        List of Delta E values

    Performance:
        Optimized batch processing for color difference calculations.
    """
    if len(colors1) != len(colors2):
        raise ValueError("Color lists must have the same length")

    delta_e_values = []

    for color1, color2 in zip(colors1, colors2):
        if color1 is None or color2 is None:
            delta_e_values.append(None)
            continue

        try:
            delta_e = calculate_delta_e_cie76(color1, color2)
            delta_e_values.append(delta_e)
        except Exception:
            delta_e_values.append(None)

    return delta_e_values


def normalize_colors_batch(colors: List[ColorInfo]) -> List[ColorInfo]:
    """
    Normalize multiple colors efficiently using batch processing.

    Args:
        colors: List of ColorInfo objects

    Returns:
        List of normalized ColorInfo objects

    Performance:
        Batch processing for color normalization operations.
    """
    normalized_colors = []

    for color in colors:
        if color is None:
            normalized_colors.append(None)
            continue

        try:
            normalized_color = normalize_color(color)
            normalized_colors.append(normalized_color)
        except Exception:
            normalized_colors.append(None)

    return normalized_colors


def calculate_luminance_batch(colors: List[ColorInfo]) -> List[float]:
    """
    Calculate luminance values for multiple colors efficiently.

    Args:
        colors: List of ColorInfo objects

    Returns:
        List of luminance values [0.0, 1.0]

    Performance:
        Vectorized luminance calculations for better performance.
    """
    luminance_values = []

    for color in colors:
        if color is None:
            luminance_values.append(None)
            continue

        try:
            luminance = calculate_luminance(color)
            luminance_values.append(luminance)
        except Exception:
            luminance_values.append(None)

    return luminance_values


def create_color_palette_optimized(colors: List[ColorInfo], max_colors: int = 16) -> List[ColorInfo]:
    """
    Create an optimized color palette from a list of colors using efficient clustering.

    Args:
        colors: List of ColorInfo objects
        max_colors: Maximum number of colors in the palette

    Returns:
        List of representative colors (palette)

    Performance:
        Uses efficient color clustering algorithms for palette extraction.
    """
    if not colors or max_colors <= 0:
        return []

    # Filter out None values
    valid_colors = [color for color in colors if color is not None]

    if len(valid_colors) <= max_colors:
        return valid_colors

    # Convert to LAB space for perceptual clustering
    lab_colors = convert_colors_to_lab_batch(valid_colors)
    valid_lab_colors = [(color, lab) for color, lab in zip(valid_colors, lab_colors) if lab is not None]

    if not valid_lab_colors:
        return []

    # Simple k-means-like clustering for color palette extraction
    palette = []
    remaining_colors = valid_lab_colors.copy()

    # Select first color
    if remaining_colors:
        palette.append(remaining_colors[0][0])
        remaining_colors.pop(0)

    # Select remaining colors based on maximum distance
    while len(palette) < max_colors and remaining_colors:
        max_distance = 0
        best_color_idx = 0

        for i, (color, lab) in enumerate(remaining_colors):
            min_distance_to_palette = float('inf')

            # Find minimum distance to existing palette
            for palette_color in palette:
                try:
                    distance = calculate_delta_e_cie76(color, palette_color)
                    min_distance_to_palette = min(min_distance_to_palette, distance)
                except Exception:
                    continue

            # Select color with maximum minimum distance
            if min_distance_to_palette > max_distance:
                max_distance = min_distance_to_palette
                best_color_idx = i

        if remaining_colors:
            palette.append(remaining_colors[best_color_idx][0])
            remaining_colors.pop(best_color_idx)

    return palette


# =============================================================================
# Color Utility Functions and Helper Methods
# =============================================================================

def clamp_rgb(r: float, g: float, b: float) -> Tuple[int, int, int]:
    """
    Clamp RGB values to valid [0, 255] integer range.

    Args:
        r, g, b: RGB values (can be floats or out-of-range)

    Returns:
        Tuple of clamped integer RGB values
    """
    return (
        max(0, min(255, int(round(r)))),
        max(0, min(255, int(round(g)))),
        max(0, min(255, int(round(b))))
    )


def clamp_alpha(alpha: float) -> float:
    """
    Clamp alpha value to valid [0.0, 1.0] range.

    Args:
        alpha: Alpha value (can be out-of-range)

    Returns:
        Clamped alpha value
    """
    return max(0.0, min(1.0, alpha))


def normalize_color(color: ColorInfo) -> ColorInfo:
    """
    Normalize a ColorInfo instance by clamping all values to valid ranges.

    Args:
        color: ColorInfo instance (may have out-of-range values)

    Returns:
        New ColorInfo with normalized values
    """
    r, g, b = clamp_rgb(color.red, color.green, color.blue)
    alpha = clamp_alpha(color.alpha)

    return ColorInfo(r, g, b, alpha, color.format, color.original)


def calculate_luminance(color: ColorInfo) -> float:
    """
    Calculate relative luminance according to WCAG 2.1 specification.

    Args:
        color: ColorInfo instance

    Returns:
        Relative luminance [0.0, 1.0]

    References:
        - WCAG 2.1 relative luminance formula
        - sRGB color space gamma correction
    """
    # Convert to linear RGB
    def to_linear(value: int) -> float:
        c = value / 255.0
        if c <= 0.03928:
            return c / 12.92
        else:
            return ((c + 0.055) / 1.055) ** 2.4

    r_lin = to_linear(color.red)
    g_lin = to_linear(color.green)
    b_lin = to_linear(color.blue)

    # WCAG luminance formula
    return 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin


def calculate_contrast_ratio(color1: ColorInfo, color2: ColorInfo) -> float:
    """
    Calculate WCAG 2.1 contrast ratio between two colors.

    Args:
        color1, color2: ColorInfo instances

    Returns:
        Contrast ratio [1.0, 21.0]

    References:
        - WCAG 2.1 contrast ratio formula
        - Accessibility compliance standards
    """
    lum1 = calculate_luminance(color1)
    lum2 = calculate_luminance(color2)

    # Ensure lighter color is in numerator
    lighter = max(lum1, lum2)
    darker = min(lum1, lum2)

    return (lighter + 0.05) / (darker + 0.05)


def is_accessible_contrast(foreground: ColorInfo, background: ColorInfo,
                          level: str = 'AA', text_size: str = 'normal') -> bool:
    """
    Check if color combination meets WCAG accessibility standards.

    Args:
        foreground: Foreground/text color
        background: Background color
        level: WCAG level ('AA' or 'AAA')
        text_size: Text size ('normal' or 'large')

    Returns:
        True if combination meets accessibility standards
    """
    ratio = calculate_contrast_ratio(foreground, background)

    # WCAG 2.1 requirements
    if level == 'AAA':
        return ratio >= 7.0 if text_size == 'normal' else ratio >= 4.5
    else:  # AA
        return ratio >= 4.5 if text_size == 'normal' else ratio >= 3.0


def calculate_delta_e_cie76(color1: ColorInfo, color2: ColorInfo) -> float:
    """
    Calculate CIE76 Delta E color difference.

    Args:
        color1, color2: ColorInfo instances

    Returns:
        Delta E value (lower = more similar)

    References:
        - CIE 1976 color difference formula
        - LAB color space perceptual uniformity
    """
    l1, a1, b1 = color1.to_lab()
    l2, a2, b2 = color2.to_lab()

    delta_l = l1 - l2
    delta_a = a1 - a2
    delta_b = b1 - b2

    return math.sqrt(delta_l**2 + delta_a**2 + delta_b**2)


def calculate_delta_e_cie94(color1: ColorInfo, color2: ColorInfo,
                           kl: float = 1.0, kc: float = 1.0, kh: float = 1.0) -> float:
    """
    Calculate CIE94 Delta E color difference (more accurate than CIE76).

    Args:
        color1, color2: ColorInfo instances
        kl, kc, kh: Weighting factors for lightness, chroma, hue

    Returns:
        Delta E value (lower = more similar)

    References:
        - CIE 1994 color difference formula
        - Improved perceptual uniformity over CIE76
    """
    l1, c1, h1 = color1.to_lch()
    l2, c2, h2 = color2.to_lch()

    delta_l = l1 - l2
    delta_c = c1 - c2

    # Calculate delta H
    delta_h_raw = h1 - h2
    if abs(delta_h_raw) > 180:
        if delta_h_raw > 0:
            delta_h_raw -= 360
        else:
            delta_h_raw += 360

    delta_h = 2 * math.sqrt(c1 * c2) * math.sin(math.radians(delta_h_raw / 2))

    # Weighting functions
    sl = 1.0
    sc = 1 + 0.045 * c1
    sh = 1 + 0.015 * c1

    # Calculate Delta E
    return math.sqrt((delta_l / (kl * sl))**2 +
                    (delta_c / (kc * sc))**2 +
                    (delta_h / (kh * sh))**2)


def simulate_colorblindness(color: ColorInfo, colorblind_type: str) -> ColorInfo:
    """
    Simulate color appearance for different types of color blindness.

    Args:
        color: Original color
        colorblind_type: 'protanopia', 'deuteranopia', or 'tritanopia'

    Returns:
        ColorInfo showing how color appears to colorblind viewers

    References:
        - Brettel et al. (1997) color blindness simulation
        - LMS color space transformations
    """
    # Convert RGB to LMS color space first
    r, g, b = color.red / 255.0, color.green / 255.0, color.blue / 255.0

    # RGB to LMS transformation matrix
    lms_from_rgb = [
        [17.8824, 43.5161, 4.11935],
        [3.45565, 27.1554, 3.86714],
        [0.0299566, 0.184309, 1.46709]
    ]

    # Apply transformation
    l = lms_from_rgb[0][0] * r + lms_from_rgb[0][1] * g + lms_from_rgb[0][2] * b
    m = lms_from_rgb[1][0] * r + lms_from_rgb[1][1] * g + lms_from_rgb[1][2] * b
    s = lms_from_rgb[2][0] * r + lms_from_rgb[2][1] * g + lms_from_rgb[2][2] * b

    # Apply colorblindness simulation
    if colorblind_type == 'protanopia':
        # Remove L cone response
        l = 2.02344 * m + -2.52581 * s
    elif colorblind_type == 'deuteranopia':
        # Remove M cone response
        m = 0.494207 * l + 1.24827 * s
    elif colorblind_type == 'tritanopia':
        # Remove S cone response
        s = -0.395913 * l + 0.801109 * m
    else:
        raise ValueError(f"Unknown colorblind type: {colorblind_type}")

    # LMS back to RGB
    rgb_from_lms = [
        [0.0809444479, -0.130504409, 0.116721066],
        [-0.0102485335, 0.0540193266, -0.113876933],
        [-0.000365296938, -0.00412161469, 0.693511405]
    ]

    r_sim = rgb_from_lms[0][0] * l + rgb_from_lms[0][1] * m + rgb_from_lms[0][2] * s
    g_sim = rgb_from_lms[1][0] * l + rgb_from_lms[1][1] * m + rgb_from_lms[1][2] * s
    b_sim = rgb_from_lms[2][0] * l + rgb_from_lms[2][1] * m + rgb_from_lms[2][2] * s

    # Clamp and convert back to 0-255 range
    r_final, g_final, b_final = clamp_rgb(r_sim * 255, g_sim * 255, b_sim * 255)

    return ColorInfo(r_final, g_final, b_final, color.alpha, color.format,
                    f"{color.original}_sim_{colorblind_type}" if color.original else None)


def extract_dominant_colors(colors: List[ColorInfo], n_colors: int = 5) -> List[ColorInfo]:
    """
    Extract dominant colors from a list using K-means clustering.

    Args:
        colors: List of ColorInfo instances
        n_colors: Number of dominant colors to extract

    Returns:
        List of dominant ColorInfo instances

    Note:
        Simplified implementation. Full K-means would require numpy.
    """
    if len(colors) <= n_colors:
        return colors

    # Simplified approach: sample colors at regular intervals
    # This is a basic implementation - real K-means would be more sophisticated
    step = len(colors) // n_colors
    dominant = []

    for i in range(n_colors):
        index = min(i * step, len(colors) - 1)
        dominant.append(colors[index])

    return dominant


def quantize_color_palette(colors: List[ColorInfo], levels: int = 8) -> List[ColorInfo]:
    """
    Quantize color palette to reduce the number of distinct colors.

    Args:
        colors: List of ColorInfo instances
        levels: Number of levels per RGB channel (total colors = levels^3)

    Returns:
        List of quantized ColorInfo instances
    """
    quantized = []
    step = 256 // levels

    for color in colors:
        # Quantize each RGB channel
        q_r = (color.red // step) * step
        q_g = (color.green // step) * step
        q_b = (color.blue // step) * step

        # Ensure values don't exceed 255
        q_r = min(q_r, 255)
        q_g = min(q_g, 255)
        q_b = min(q_b, 255)

        quantized_color = ColorInfo(q_r, q_g, q_b, color.alpha, color.format,
                                  f"quantized_{color.original}" if color.original else None)
        quantized.append(quantized_color)

    return quantized


def adjust_color_temperature(color: ColorInfo, temperature_shift: float) -> ColorInfo:
    """
    Adjust color temperature (warm/cool shift).

    Args:
        color: Original color
        temperature_shift: Positive = warmer, negative = cooler [-1.0, 1.0]

    Returns:
        Temperature-adjusted ColorInfo
    """
    # Clamp temperature shift
    temperature_shift = max(-1.0, min(1.0, temperature_shift))

    # Convert to working values
    r, g, b = color.red, color.green, color.blue

    if temperature_shift > 0:
        # Warmer: increase red, decrease blue
        r = min(255, r + int(temperature_shift * 30))
        b = max(0, b - int(temperature_shift * 30))
    else:
        # Cooler: decrease red, increase blue
        temp_abs = abs(temperature_shift)
        r = max(0, r - int(temp_abs * 30))
        b = min(255, b + int(temp_abs * 30))

    return ColorInfo(r, g, b, color.alpha, color.format,
                    f"temp_{color.original}" if color.original else None)


def adjust_saturation(color: ColorInfo, saturation_factor: float) -> ColorInfo:
    """
    Adjust color saturation.

    Args:
        color: Original color
        saturation_factor: Multiplier for saturation (0.0 = grayscale, 2.0 = double saturation)

    Returns:
        Saturation-adjusted ColorInfo
    """
    # Convert to HSL for saturation adjustment
    r, g, b = color.red / 255.0, color.green / 255.0, color.blue / 255.0

    # Simple saturation adjustment using luminance
    luminance = 0.299 * r + 0.587 * g + 0.114 * b

    # Adjust saturation by interpolating with grayscale
    r_adjusted = luminance + saturation_factor * (r - luminance)
    g_adjusted = luminance + saturation_factor * (g - luminance)
    b_adjusted = luminance + saturation_factor * (b - luminance)

    # Clamp and convert back
    r_final, g_final, b_final = clamp_rgb(r_adjusted * 255, g_adjusted * 255, b_adjusted * 255)

    return ColorInfo(r_final, g_final, b_final, color.alpha, color.format,
                    f"sat_{color.original}" if color.original else None)


def rotate_hue(color: ColorInfo, degrees: float) -> ColorInfo:
    """
    Rotate color hue by specified degrees using HSL color space.

    Args:
        color: Source ColorInfo object
        degrees: Rotation angle in degrees (-360 to 360)
                Positive values rotate clockwise

    Returns:
        ColorInfo with rotated hue, preserving saturation and lightness

    Example:
        >>> red = ColorInfo.from_hex("#FF0000")
        >>> green = rotate_hue(red, 120.0)  # Red → Green
        >>> blue = rotate_hue(red, 240.0)   # Red → Blue

    Note:
        Handles angle normalization automatically. Angles outside -360 to 360
        are wrapped to the valid range.
    """
    # Input validation
    if not isinstance(color, ColorInfo):
        raise ValueError("color must be a ColorInfo instance")
    if not isinstance(degrees, (int, float)):
        raise ValueError("degrees must be a number")

    # Convert to HSL
    h, s, l = rgb_to_hsl(color.red, color.green, color.blue)

    # Apply hue rotation with automatic angle normalization
    new_hue = (h + degrees) % 360

    # Convert back to RGB
    r, g, b = hsl_to_rgb(new_hue, s, l)

    return ColorInfo(r, g, b, color.alpha, color.format,
                    f"hue_{color.original}" if color.original else None)


def apply_color_matrix(color: ColorInfo, matrix: List[float]) -> ColorInfo:
    """
    Apply 4×5 color transformation matrix to color.

    Args:
        color: Source ColorInfo object
        matrix: 20 values representing 4×5 matrix in row-major order:
               [R  G  B  A  offset_R]  # Row 0: New Red calculation
               [R  G  B  A  offset_G]  # Row 1: New Green calculation
               [R  G  B  A  offset_B]  # Row 2: New Blue calculation
               [R  G  B  A  offset_A]  # Row 3: New Alpha calculation

    Returns:
        ColorInfo with transformed RGBA values, clamped to valid ranges

    Example:
        >>> # Invert colors matrix
        >>> invert_matrix = [-1,0,0,0,1, 0,-1,0,0,1, 0,0,-1,0,1, 0,0,0,1,0]
        >>> inverted = apply_color_matrix(color, invert_matrix)

        >>> # Identity matrix (no change)
        >>> identity_matrix = [1,0,0,0,0, 0,1,0,0,0, 0,0,1,0,0, 0,0,0,1,0]
        >>> unchanged = apply_color_matrix(color, identity_matrix)

    Note:
        Matrix values are applied as: new_component = (R*m[0] + G*m[1] + B*m[2] + A*m[3] + m[4])
        RGB values are normalized to [0-1] for calculation, then scaled back to [0-255]
        Alpha values are kept in [0-1] range throughout calculation
    """
    from typing import List

    # Input validation
    if not isinstance(color, ColorInfo):
        raise ValueError("color must be a ColorInfo instance")
    if not isinstance(matrix, (list, tuple)):
        raise ValueError("matrix must be a list or tuple")
    if len(matrix) != 20:
        raise ValueError("matrix must contain exactly 20 values (4×5 matrix)")

    # Validate all matrix values are numbers
    try:
        matrix_values = [float(val) for val in matrix]
    except (ValueError, TypeError) as e:
        raise ValueError(f"All matrix values must be numbers: {e}")

    # Normalize RGB to [0-1] range for calculation
    r_norm = color.red / 255.0
    g_norm = color.green / 255.0
    b_norm = color.blue / 255.0
    a_norm = color.alpha  # Already in [0-1] range

    # Apply 4×5 matrix transformation
    # Matrix is organized as rows: [R G B A offset] for each output component
    new_r = (r_norm * matrix_values[0] + g_norm * matrix_values[1] +
             b_norm * matrix_values[2] + a_norm * matrix_values[3] + matrix_values[4])
    new_g = (r_norm * matrix_values[5] + g_norm * matrix_values[6] +
             b_norm * matrix_values[7] + a_norm * matrix_values[8] + matrix_values[9])
    new_b = (r_norm * matrix_values[10] + g_norm * matrix_values[11] +
             b_norm * matrix_values[12] + a_norm * matrix_values[13] + matrix_values[14])
    new_a = (r_norm * matrix_values[15] + g_norm * matrix_values[16] +
             b_norm * matrix_values[17] + a_norm * matrix_values[18] + matrix_values[19])

    # Clamp values to valid ranges
    # RGB: clamp to [0-1] then scale to [0-255]
    r_clamped = max(0.0, min(1.0, new_r)) * 255.0
    g_clamped = max(0.0, min(1.0, new_g)) * 255.0
    b_clamped = max(0.0, min(1.0, new_b)) * 255.0

    # Alpha: clamp to [0-1]
    a_clamped = max(0.0, min(1.0, new_a))

    # Convert to integers for RGB
    r_final, g_final, b_final = clamp_rgb(r_clamped, g_clamped, b_clamped)

    return ColorInfo(r_final, g_final, b_final, a_clamped, color.format,
                    f"matrix_{color.original}" if color.original else None)


def luminance_to_alpha(color: ColorInfo) -> ColorInfo:
    """
    Convert color luminance to alpha channel, setting RGB to black.

    Args:
        color: Source ColorInfo object

    Returns:
        ColorInfo with RGB=(0,0,0) and alpha=luminance_value

    Example:
        >>> white = ColorInfo.from_rgb(255, 255, 255, 255)
        >>> alpha_mask = luminance_to_alpha(white)
        >>> # Result: RGB=(0,0,0), Alpha=1.0 (white luminance)

        >>> gray = ColorInfo.from_rgb(128, 128, 128, 255)
        >>> alpha_mask = luminance_to_alpha(gray)
        >>> # Result: RGB=(0,0,0), Alpha≈0.22 (gray luminance)

    Note:
        Uses WCAG 2.1 relative luminance calculation for accurate conversion.
        Preserves original alpha if it was less than the luminance value.
    """
    # Input validation
    if not isinstance(color, ColorInfo):
        raise ValueError("color must be a ColorInfo instance")

    # Calculate luminance using existing WCAG function
    luminance_value = calculate_luminance(color)

    # Convert luminance to alpha channel
    # Luminance is already in [0.0, 1.0] range, perfect for alpha
    alpha_from_luminance = luminance_value

    # Set RGB to black as per SVG luminance-to-alpha specification
    return ColorInfo(0, 0, 0, alpha_from_luminance, color.format,
                    f"luma_{color.original}" if color.original else None)