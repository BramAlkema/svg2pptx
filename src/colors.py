#!/usr/bin/env python3
"""
Universal Color Parser for SVG2PPTX

This module provides centralized, robust color parsing with comprehensive
support for all CSS color formats, gradients, and patterns. Handles
accurate color conversion and provides PowerPoint-compatible output.

Key Features:
- Complete CSS color support (hex, rgb, hsl, named colors)
- Alpha channel and transparency handling
- Color space conversions (RGB, HSL, HSV)
- DrawingML color XML generation
- Named color database (147 standard colors)
- Gradient and pattern color extraction
- Color palette optimization
- Context-aware color inheritance

Color Format Support:
- Hex: #RGB, #RRGGBB, #RRGGBBAA
- RGB: rgb(r,g,b), rgba(r,g,b,a), rgb(r%,g%,b%)
- HSL: hsl(h,s,l), hsla(h,s,l,a)  
- Named: red, blue, transparent, currentColor
- System: inherit, initial, unset
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
        # Validate input values
        if x < 0 or y < 0 or z < 0:
            raise ValueError(f"XYZ values must be non-negative. Got: ({x:.6f}, {y:.6f}, {z:.6f})")

        if not (0.0 <= alpha <= 1.0):
            raise ValueError(f"Alpha must be in range [0.0, 1.0]. Got: {alpha}")

        # Check for unreasonably large XYZ values (likely input errors)
        if x > 2.0 or y > 2.0 or z > 2.0:
            raise ValueError(f"XYZ values seem unusually large. Got: ({x:.6f}, {y:.6f}, {z:.6f}). "
                           "Expected range roughly [0.0, 1.0] for typical colors.")
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