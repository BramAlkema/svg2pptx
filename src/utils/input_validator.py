#!/usr/bin/env python3
"""
Input Validation Framework

Robust input validation and sanitization for SVG2PPTX conversion system.
Replaces unsafe parsing patterns with comprehensive validation that handles
edge cases, prevents overflow, and provides security against injection attacks.

This framework addresses issues like:
- Blind string replacement (.replace('px', '')) causing crashes
- Numeric overflow vulnerabilities
- XSS and injection attacks through SVG attributes
- Invalid unit handling across different SVG specifications
"""

import re
import html
import urllib.parse
from typing import Optional, Dict, List, Union, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Base exception for input validation errors."""
    pass


class NumericOverflowError(ValidationError):
    """Exception raised when numeric values exceed safe bounds."""
    pass


class UnitConversionError(ValidationError):
    """Exception raised when unit conversion fails."""
    pass


class AttributeSanitizationError(ValidationError):
    """Exception raised when attribute sanitization fails."""
    pass


class LengthUnit(Enum):
    """Supported SVG length units with conversion factors."""
    # Absolute units (converted to pixels at 96 DPI)
    PX = ("px", 1.0)                    # pixels
    PT = ("pt", 96.0 / 72.0)           # points (1/72 inch)
    PC = ("pc", 96.0 / 6.0)            # picas (1/6 inch)
    IN = ("in", 96.0)                   # inches
    CM = ("cm", 96.0 / 2.54)           # centimeters
    MM = ("mm", 96.0 / 25.4)           # millimeters

    # Relative units (require context for conversion)
    EM = ("em", None)                   # relative to font size
    EX = ("ex", None)                   # relative to x-height
    REM = ("rem", None)                 # relative to root font size

    # Percentage (relative to parent/viewport)
    PERCENT = ("%", None)               # percentage of parent dimension

    # Viewport units
    VW = ("vw", None)                   # viewport width
    VH = ("vh", None)                   # viewport height
    VMIN = ("vmin", None)               # minimum viewport dimension
    VMAX = ("vmax", None)               # maximum viewport dimension

    def __init__(self, unit_str: str, px_factor: Optional[float]):
        self.unit_str = unit_str
        self.px_factor = px_factor
        self.is_absolute = px_factor is not None


@dataclass
class ValidationContext:
    """Context for validation operations including defaults and constraints."""
    default_dpi: float = 96.0
    default_font_size: float = 16.0
    viewport_width: float = 800.0
    viewport_height: float = 600.0
    max_numeric_value: float = 1e20
    min_numeric_value: float = -1e20
    max_string_length: int = 10000
    allow_relative_units: bool = True
    strict_mode: bool = False


class InputValidator:
    """
    Comprehensive input validation framework for SVG processing.

    Provides secure, robust parsing of SVG attributes, numeric values,
    and length units with proper error handling and bounds checking.
    """

    # Regex patterns for various input types
    NUMERIC_PATTERN = re.compile(r'^[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?$')
    LENGTH_PATTERN = re.compile(r'^[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?(px|pt|pc|in|cm|mm|em|ex|rem|%|vw|vh|vmin|vmax)?$', re.IGNORECASE)
    COLOR_HEX_PATTERN = re.compile(r'^#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6}|[0-9A-Fa-f]{8})$')
    COLOR_RGB_PATTERN = re.compile(r'^rgb\s*\(\s*(\d+(?:\.\d+)?%?)\s*,\s*(\d+(?:\.\d+)?%?)\s*,\s*(\d+(?:\.\d+)?%?)\s*\)$', re.IGNORECASE)
    COLOR_RGBA_PATTERN = re.compile(r'^rgba\s*\(\s*(\d+(?:\.\d+)?%?)\s*,\s*(\d+(?:\.\d+)?%?)\s*,\s*(\d+(?:\.\d+)?%?)\s*,\s*(\d+(?:\.\d+)?)\s*\)$', re.IGNORECASE)

    # Dangerous patterns for sanitization
    SCRIPT_PATTERN = re.compile(r'<script[^>]*>.*?</script>', re.IGNORECASE | re.DOTALL)
    ON_EVENT_PATTERN = re.compile(r'\bon\w+\s*=', re.IGNORECASE)
    JAVASCRIPT_PATTERN = re.compile(r'javascript:', re.IGNORECASE)
    DATA_URL_PATTERN = re.compile(r'data:[^;,]*(?:;[^;,]*)*,', re.IGNORECASE)

    def __init__(self, context: Optional[ValidationContext] = None):
        """
        Initialize InputValidator with validation context.

        Args:
            context: Validation context with defaults and constraints
        """
        self.context = context or ValidationContext()
        self._unit_lookup = {unit.unit_str: unit for unit in LengthUnit}

    def parse_length_safe(self, length_str: str, default_unit: str = 'px') -> Optional[float]:
        """
        Parse length values with comprehensive unit support and overflow protection.

        Replaces unsafe patterns like .replace('px', '') with robust parsing
        that handles all SVG units and prevents crashes on invalid input.

        Args:
            length_str: Length string to parse (e.g., "100px", "5em", "50%")
            default_unit: Default unit if none specified

        Returns:
            Parsed length in pixels, or None if parsing fails

        Raises:
            NumericOverflowError: If numeric value exceeds safe bounds
            UnitConversionError: If unit conversion fails
        """
        if not length_str or not isinstance(length_str, str):
            return None

        # Trim whitespace and convert to lowercase for unit matching
        length_str = length_str.strip()
        if not length_str:
            return None

        # Check string length to prevent DoS
        if len(length_str) > self.context.max_string_length:
            raise ValidationError(f"Input string too long: {len(length_str)} > {self.context.max_string_length}")

        try:
            # Use regex to extract numeric and unit parts
            match = self.LENGTH_PATTERN.match(length_str)
            if not match:
                logger.debug(f"Length string doesn't match pattern: {length_str}")
                return None

            # Extract unit part (group 1 from regex)
            unit_part = match.group(1) or default_unit

            # Extract numeric part by removing the unit
            if unit_part and length_str.endswith(unit_part):
                numeric_part = length_str[:-len(unit_part)].strip()
            else:
                numeric_part = length_str.strip()

            # Parse numeric value with bounds checking
            try:
                numeric_value = float(numeric_part)
            except (ValueError, OverflowError):
                logger.debug(f"Failed to parse numeric part: {numeric_part}")
                return None

            # Check numeric bounds
            if not (self.context.min_numeric_value <= numeric_value <= self.context.max_numeric_value):
                raise NumericOverflowError(f"Numeric value out of bounds: {numeric_value}")

            # Convert to pixels based on unit
            return self._convert_to_pixels(numeric_value, unit_part.lower())

        except (ValueError, TypeError, OverflowError) as e:
            logger.debug(f"Length parsing failed for '{length_str}': {e}")
            return None

    def _convert_to_pixels(self, value: float, unit: str) -> float:
        """
        Convert a numeric value with unit to pixels.

        Args:
            value: Numeric value
            unit: Unit string (px, pt, em, etc.)

        Returns:
            Value converted to pixels

        Raises:
            UnitConversionError: If unit is not supported or conversion fails
        """
        unit = unit.lower()

        # Look up unit in our enum
        if unit not in self._unit_lookup:
            # Try common variations and abbreviations
            unit_variants = {
                'pixels': 'px',
                'points': 'pt',
                'inches': 'in',
                'centimeters': 'cm',
                'millimeters': 'mm',
                'percent': '%',
                'percentage': '%'
            }
            unit = unit_variants.get(unit, unit)

            if unit not in self._unit_lookup:
                raise UnitConversionError(f"Unsupported unit: {unit}")

        unit_enum = self._unit_lookup[unit]

        # Handle absolute units with direct conversion factors
        if unit_enum.is_absolute:
            return value * unit_enum.px_factor

        # Handle relative and contextual units
        if unit == '%':
            # For percentage, we need context (parent size, viewport, etc.)
            # Return as-is for now, calling code should provide context
            return value
        elif unit == 'em':
            return value * self.context.default_font_size
        elif unit == 'ex':
            # x-height is typically ~0.5em
            return value * self.context.default_font_size * 0.5
        elif unit == 'rem':
            return value * self.context.default_font_size  # Assume root = default
        elif unit == 'vw':
            return value * self.context.viewport_width / 100.0
        elif unit == 'vh':
            return value * self.context.viewport_height / 100.0
        elif unit == 'vmin':
            return value * min(self.context.viewport_width, self.context.viewport_height) / 100.0
        elif unit == 'vmax':
            return value * max(self.context.viewport_width, self.context.viewport_height) / 100.0
        else:
            raise UnitConversionError(f"Cannot convert unit {unit} without additional context")

    def parse_numeric_safe(self, value_str: str, min_val: float = -1e10, max_val: float = 1e10) -> Optional[float]:
        """
        Parse numeric values with bounds checking and overflow protection.

        Args:
            value_str: String containing numeric value
            min_val: Minimum allowed value
            max_val: Maximum allowed value

        Returns:
            Parsed numeric value, or None if parsing fails

        Raises:
            NumericOverflowError: If value exceeds bounds
        """
        if not value_str or not isinstance(value_str, str):
            return None

        value_str = value_str.strip()
        if not value_str:
            return None

        # Check string length
        if len(value_str) > self.context.max_string_length:
            raise ValidationError(f"Numeric string too long: {len(value_str)}")

        try:
            # Use regex to validate numeric format
            if not self.NUMERIC_PATTERN.match(value_str):
                logger.debug(f"Invalid numeric format: {value_str}")
                return None

            # Parse the value
            try:
                numeric_value = float(value_str)
            except (ValueError, OverflowError):
                logger.debug(f"Failed to parse numeric value: {value_str}")
                return None

            # Check for infinity and NaN
            if not (numeric_value == numeric_value and abs(numeric_value) != float('inf')):
                logger.debug(f"Invalid numeric value (NaN or infinity): {numeric_value}")
                return None

            # Check bounds
            if not (min_val <= numeric_value <= max_val):
                raise NumericOverflowError(f"Numeric value {numeric_value} outside bounds [{min_val}, {max_val}]")

            return numeric_value

        except (ValueError, TypeError) as e:
            logger.debug(f"Numeric parsing failed for '{value_str}': {e}")
            return None

    def validate_svg_attributes(self, attrs: Dict[str, str]) -> Dict[str, str]:
        """
        Sanitize SVG attributes against injection attacks and invalid content.

        Args:
            attrs: Dictionary of attribute name -> value

        Returns:
            Sanitized attributes dictionary

        Raises:
            AttributeSanitizationError: If sanitization fails
        """
        if not attrs:
            return {}

        sanitized = {}

        for attr_name, attr_value in attrs.items():
            try:
                # Sanitize attribute name
                clean_name = self._sanitize_attribute_name(attr_name)
                if not clean_name:
                    logger.debug(f"Skipping invalid attribute name: {attr_name}")
                    continue

                # Sanitize attribute value
                clean_value = self._sanitize_attribute_value(attr_name, attr_value)
                if clean_value is not None:
                    sanitized[clean_name] = clean_value
                else:
                    logger.debug(f"Skipping invalid attribute value for {attr_name}: {attr_value}")

            except Exception as e:
                logger.warning(f"Error sanitizing attribute {attr_name}={attr_value}: {e}")
                if self.context.strict_mode:
                    raise AttributeSanitizationError(f"Failed to sanitize attribute {attr_name}: {e}")
                continue

        return sanitized

    def _sanitize_attribute_name(self, name: str) -> Optional[str]:
        """Sanitize SVG attribute name."""
        if not name or not isinstance(name, str):
            return None

        name = name.strip().lower()

        # Check length
        if len(name) > 100:  # Reasonable limit for attribute names
            return None

        # Allow namespaced attributes (like xlink:href)
        # Check for valid XML/SVG attribute name pattern
        # Must start with letter or underscore, contain only alphanumeric, hyphens, periods, underscores, colons
        if not re.match(r'^[a-z_][a-z0-9\-\._:]*$', name):
            return None

        # Block dangerous attribute names
        dangerous_attrs = {'onload', 'onerror', 'onclick', 'onmouseover', 'onfocus', 'onblur'}
        if name in dangerous_attrs or (name.startswith('on') and ':' not in name):
            logger.warning(f"Blocked dangerous attribute: {name}")
            return None

        return name

    def _sanitize_attribute_value(self, attr_name: str, value: str) -> Optional[str]:
        """Sanitize SVG attribute value based on attribute type."""
        if not isinstance(value, str):
            return None

        # Check length
        if len(value) > self.context.max_string_length:
            logger.warning(f"Attribute value too long for {attr_name}: {len(value)}")
            return None

        # HTML entity decode first to catch encoded attacks
        try:
            decoded_value = html.unescape(value)
        except:
            decoded_value = value

        # URL decode to catch encoded attacks
        try:
            url_decoded = urllib.parse.unquote(decoded_value)
        except:
            url_decoded = decoded_value

        # Check for script injection in any form
        for check_value in [value, decoded_value, url_decoded]:
            if self.SCRIPT_PATTERN.search(check_value):
                logger.warning(f"Blocked script injection in {attr_name}: {value}")
                return None

            if self.ON_EVENT_PATTERN.search(check_value):
                logger.warning(f"Blocked event handler in {attr_name}: {value}")
                return None

            if self.JAVASCRIPT_PATTERN.search(check_value):
                logger.warning(f"Blocked javascript: URL in {attr_name}: {value}")
                return None

        # Handle specific attribute types
        if attr_name in ['width', 'height', 'x', 'y', 'cx', 'cy', 'r', 'rx', 'ry']:
            # Length/coordinate attributes
            parsed = self.parse_length_safe(value)
            return str(parsed) if parsed is not None else None

        elif attr_name in ['fill', 'stroke', 'color']:
            # Color attributes
            return self._sanitize_color_value(value)

        elif attr_name in ['href', 'xlink:href']:
            # URL attributes - be very careful
            return self._sanitize_url_value(value)

        elif attr_name == 'style':
            # CSS style attribute
            return self._sanitize_style_value(value)

        else:
            # Generic text attribute - basic sanitization
            # Remove control characters except whitespace
            sanitized = re.sub(r'[\x00-\x08\x0B-\x1F\x7F-\x9F]', '', value)

            # Limit to reasonable character set (printable ASCII + common Unicode)
            # This is conservative but safe
            sanitized = re.sub(r'[^\x20-\x7E\u00A0-\u00FF\u0100-\u017F\u0180-\u024F]', '', sanitized)

            return sanitized.strip() if sanitized.strip() else None

    def _sanitize_color_value(self, color: str) -> Optional[str]:
        """Sanitize color values (hex, rgb, rgba, named colors)."""
        color = color.strip().lower()

        # Check hex colors - be strict about format
        hex_match = self.COLOR_HEX_PATTERN.match(color)
        if hex_match:
            hex_part = hex_match.group(1)
            # Validate hex digits
            try:
                int(hex_part, 16)
                return color
            except ValueError:
                logger.debug(f"Invalid hex color: {color}")
                return None

        # Check rgb() colors - validate numeric ranges
        rgb_match = self.COLOR_RGB_PATTERN.match(color)
        if rgb_match:
            try:
                r_str, g_str, b_str = rgb_match.groups()
                # Parse and validate RGB values
                for val_str in [r_str, g_str, b_str]:
                    if val_str.endswith('%'):
                        val = float(val_str[:-1])
                        if not (0 <= val <= 100):
                            return None
                    else:
                        val = float(val_str)
                        if not (0 <= val <= 255):
                            return None
                return color
            except ValueError:
                logger.debug(f"Invalid RGB color: {color}")
                return None

        # Check rgba() colors
        rgba_match = self.COLOR_RGBA_PATTERN.match(color)
        if rgba_match:
            try:
                r_str, g_str, b_str, a_str = rgba_match.groups()
                # Validate RGB values (same as above)
                for val_str in [r_str, g_str, b_str]:
                    if val_str.endswith('%'):
                        val = float(val_str[:-1])
                        if not (0 <= val <= 100):
                            return None
                    else:
                        val = float(val_str)
                        if not (0 <= val <= 255):
                            return None
                # Validate alpha
                alpha = float(a_str)
                if not (0 <= alpha <= 1):
                    return None
                return color
            except ValueError:
                logger.debug(f"Invalid RGBA color: {color}")
                return None

        # Named colors (basic set)
        named_colors = {
            'red', 'green', 'blue', 'black', 'white', 'yellow', 'cyan', 'magenta',
            'gray', 'grey', 'orange', 'purple', 'brown', 'pink', 'transparent', 'none'
        }

        if color in named_colors:
            return color

        logger.debug(f"Invalid color value: {color}")
        return None

    def _sanitize_url_value(self, url: str) -> Optional[str]:
        """Sanitize URL values with strict security checks."""
        if not url:
            return None

        url = url.strip()

        # Block javascript: URLs
        if self.JAVASCRIPT_PATTERN.search(url):
            logger.warning(f"Blocked javascript: URL: {url}")
            return None

        # Be very careful with data: URLs - they can contain scripts
        if self.DATA_URL_PATTERN.search(url):
            # Only allow safe data URLs (images)
            if url.startswith('data:image/'):
                return url  # Could add more validation here
            else:
                logger.warning(f"Blocked potentially unsafe data: URL: {url}")
                return None

        # Allow relative URLs and http/https URLs
        if url.startswith(('#', '/', './', '../')) or url.startswith(('http://', 'https://')):
            # Basic URL validation
            try:
                parsed = urllib.parse.urlparse(url)
                if parsed.scheme in ('', 'http', 'https'):
                    return url
            except:
                pass

        logger.debug(f"Invalid or unsafe URL: {url}")
        return None

    def _sanitize_style_value(self, style: str) -> Optional[str]:
        """Sanitize CSS style attribute values."""
        if not style:
            return None

        # Remove dangerous CSS content
        # This is a basic implementation - could be more sophisticated
        dangerous_patterns = [
            r'expression\s*\(',
            r'javascript:',
            r'@import',
            r'behavior\s*:',
            r'-moz-binding\s*:',
        ]

        clean_style = style
        for pattern in dangerous_patterns:
            clean_style = re.sub(pattern, '', clean_style, flags=re.IGNORECASE)

        # Basic CSS syntax validation
        # Should contain property: value; pairs
        if ':' not in clean_style:
            return None

        return clean_style.strip() if clean_style.strip() else None

    def validate_viewbox(self, viewbox_str: str) -> Optional[Tuple[float, float, float, float]]:
        """
        Validate and parse SVG viewBox attribute.

        Args:
            viewbox_str: viewBox string (e.g., "0 0 100 100")

        Returns:
            Tuple of (min_x, min_y, width, height) or None if invalid
        """
        if not viewbox_str or not isinstance(viewbox_str, str):
            return None

        try:
            # Split by whitespace or commas
            parts = re.split(r'[\s,]+', viewbox_str.strip())

            if len(parts) != 4:
                logger.debug(f"viewBox must have exactly 4 values: {viewbox_str}")
                return None

            # Parse each value
            values = []
            for part in parts:
                value = self.parse_numeric_safe(part, min_val=-1e6, max_val=1e6)
                if value is None:
                    logger.debug(f"Invalid viewBox value: {part}")
                    return None
                values.append(value)

            min_x, min_y, width, height = values

            # Width and height must be positive
            if width <= 0 or height <= 0:
                logger.debug(f"viewBox width and height must be positive: {width}, {height}")
                return None

            return (min_x, min_y, width, height)

        except Exception as e:
            logger.debug(f"viewBox parsing failed for '{viewbox_str}': {e}")
            return None

    def validate_transform_list(self, transform_str: str) -> bool:
        """
        Validate SVG transform attribute syntax.

        Args:
            transform_str: Transform string (e.g., "translate(10,20) rotate(45)")

        Returns:
            True if transform syntax is valid, False otherwise
        """
        if not transform_str or not isinstance(transform_str, str):
            return False

        try:
            # Basic transform function pattern
            transform_pattern = re.compile(
                r'(matrix|translate|scale|rotate|skewX|skewY)\s*\(\s*([^)]*)\s*\)',
                re.IGNORECASE
            )

            # Find all transform functions
            transforms = transform_pattern.findall(transform_str)

            if not transforms:
                return False

            # Validate each transform function
            for func_name, params_str in transforms:
                params = re.split(r'[\s,]+', params_str.strip())
                params = [p for p in params if p]  # Remove empty strings

                # Validate parameter count and values
                if func_name.lower() in ['translate', 'scale']:
                    if len(params) not in [1, 2]:
                        return False
                elif func_name.lower() in ['rotate', 'skewx', 'skewy']:
                    if len(params) not in [1, 3]:  # rotate can have 1 or 3 params
                        return False
                elif func_name.lower() == 'matrix':
                    if len(params) != 6:
                        return False
                else:
                    return False  # Unknown function

                # Validate each parameter is numeric
                for param in params:
                    if self.parse_numeric_safe(param, min_val=-1e6, max_val=1e6) is None:
                        return False

            return True

        except Exception as e:
            logger.debug(f"Transform validation failed for '{transform_str}': {e}")
            return False


# Default global instance for convenience
default_input_validator = InputValidator()