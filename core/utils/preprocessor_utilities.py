#!/usr/bin/env python3
"""
PreprocessorUtilities service for SVG2PPTX.

This module provides centralized utility functions for preprocessing plugins,
eliminating duplicate formatting, parsing, and processing implementations across
preprocessing modules.

Consolidates:
- Number/coordinate formatting logic from multiple plugins
- Points/coordinate parsing from geometry plugins
- Style processing and validation utilities
- Transform parsing and matrix operations
- Common preprocessing patterns and validations
"""

import math
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

from .input_validator import InputValidator

# Integration with existing utility services
try:
    from .coordinate_transformer import CoordinateTransformer, coordinate_transformer
    from .style_parser import StyleParser, style_parser
    UTILITY_SERVICES_AVAILABLE = True
except ImportError:
    UTILITY_SERVICES_AVAILABLE = False
    style_parser = None
    coordinate_transformer = None


@dataclass
class ProcessingResult:
    """Result of preprocessing operation with success status and metadata."""
    success: bool
    value: Any
    original_value: Any = None
    errors: list[str] = None
    modifications: list[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.modifications is None:
            self.modifications = []


class PreprocessorUtilities:
    """
    Centralized utility service for preprocessing plugins.

    Consolidates duplicate formatting, parsing, and processing logic
    from multiple preprocessing plugin implementations.
    """

    def __init__(self):
        """Initialize PreprocessorUtilities with optimization settings."""
        self._validator = InputValidator()

        # Number formatting patterns
        self.number_pattern = re.compile(r'[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?')
        self.scientific_threshold = 1e6  # Use scientific notation for large numbers

        # Transform parsing patterns
        self.transform_patterns = {
            'matrix': re.compile(r'matrix\s*\(\s*([-\d.]+(?:\s*,\s*[-\d.]+){5})\s*\)'),
            'translate': re.compile(r'translate\s*\(\s*([-\d.]+)(?:\s*,\s*([-\d.]+))?\s*\)'),
            'scale': re.compile(r'scale\s*\(\s*([-\d.]+)(?:\s*,\s*([-\d.]+))?\s*\)'),
            'rotate': re.compile(r'rotate\s*\(\s*([-\d.]+)(?:\s+([-\d.]+)\s+([-\d.]+))?\s*\)'),
            'skewX': re.compile(r'skewX\s*\(\s*([-\d.]+)\s*\)'),
            'skewY': re.compile(r'skewY\s*\(\s*([-\d.]+)\s*\)'),
        }

    def format_number(self, num: float | int, precision: int = 3) -> str:
        """
        Format number with specified precision, removing unnecessary decimals.

        Consolidates number formatting from:
        - src/preprocessing/plugins.py:73 (_clean_numeric_value)
        - src/preprocessing/geometry_plugins.py:182 (_format_number)
        - src/preprocessing/geometry_plugins.py:368 (_format_number) [duplicate]
        - src/preprocessing/advanced_geometry_plugins.py:254 (_format_number)
        - src/preprocessing/advanced_geometry_plugins.py:394 (_format_number) [duplicate]

        Args:
            num: Number to format
            precision: Decimal precision

        Returns:
            Formatted number string
        """
        if not isinstance(num, (int, float)):
            try:
                num = float(num)
            except (ValueError, TypeError):
                return str(num)

        # Handle special cases
        if math.isnan(num):
            return "0"
        if math.isinf(num):
            return "0"

        # Handle very small numbers (round to zero)
        if abs(num) < 10**-precision:
            return "0"

        # Handle integers
        if num == int(num):
            return str(int(num))

        # Handle large numbers with scientific notation
        if abs(num) >= self.scientific_threshold:
            return f"{num:.{precision}e}"

        # Standard decimal formatting
        formatted = f"{num:.{precision}f}".rstrip('0').rstrip('.')
        return formatted if formatted else "0"

    def format_number_pair(self, x: float | int, y: float | int,
                          precision: int = 3, separator: str = ",") -> str:
        """
        Format coordinate pair with consistent precision.

        Args:
            x, y: Coordinate values
            precision: Decimal precision
            separator: Separator between x and y

        Returns:
            Formatted coordinate pair string
        """
        x_str = self.format_number(x, precision)
        y_str = self.format_number(y, precision)
        return f"{x_str}{separator}{y_str}"

    def clean_numeric_value(self, value: str, precision: int = 3) -> str:
        """
        Clean numeric value string with precision control and unit removal.

        Consolidates from: src/preprocessing/plugins.py:73 (_clean_numeric_value)
        Specifically handles removal of 'px' units and numeric formatting.

        Args:
            value: Numeric value string (may include units like 'px')
            precision: Decimal precision

        Returns:
            Cleaned numeric value string without units
        """
        if not value or not value.strip():
            return value

        # Use secure parsing instead of unsafe string replacement
        numeric_value = self._validator.parse_length_safe(value, default_unit='px')
        if numeric_value is not None:
            return self.format_number(numeric_value, precision)

        return value

    def parse_points_string(self, points_str: str) -> ProcessingResult:
        """
        Parse SVG points attribute string into coordinate tuples.

        Consolidates points parsing from:
        - src/preprocessing/geometry_plugins.py:76 (_parse_points)
        - src/preprocessing/advanced_geometry_plugins.py:228 (_parse_points)
        - src/preprocessing/advanced_geometry_plugins.py:320 (_parse_points) [duplicate]

        Args:
            points_str: SVG points attribute string

        Returns:
            ProcessingResult with List[Tuple[float, float]] as value
        """
        if not points_str or not points_str.strip():
            return ProcessingResult(success=True, value=[], original_value=points_str)

        try:
            # Use CoordinateTransformer if available
            if UTILITY_SERVICES_AVAILABLE and coordinate_transformer:
                result = coordinate_transformer.parse_coordinate_string(points_str)
                return ProcessingResult(
                    success=True,
                    value=result.coordinates,
                    original_value=points_str,
                    errors=result.parsing_errors,
                )

        except Exception as e:
            # Fall back to manual parsing
            pass

        # Manual parsing fallback
        try:
            # Extract all numbers from the string
            numbers = self.number_pattern.findall(points_str.strip())
            float_numbers = [float(num) for num in numbers]

            # Group into coordinate pairs
            coordinates = []
            for i in range(0, len(float_numbers), 2):
                if i + 1 < len(float_numbers):
                    coordinates.append((float_numbers[i], float_numbers[i + 1]))

            return ProcessingResult(
                success=True,
                value=coordinates,
                original_value=points_str,
            )

        except Exception as e:
            return ProcessingResult(
                success=False,
                value=[],
                original_value=points_str,
                errors=[f"Points parsing failed: {str(e)}"],
            )

    def format_points_string(self, coordinates: list[tuple[float, float]],
                           precision: int = 3) -> str:
        """
        Format coordinate list back to SVG points string.

        Args:
            coordinates: List of (x, y) coordinate tuples
            precision: Decimal precision

        Returns:
            Formatted points string
        """
        if not coordinates:
            return ""

        point_strings = []
        for x, y in coordinates:
            point_strings.append(self.format_number_pair(x, y, precision))

        return " ".join(point_strings)

    def parse_style_attribute(self, style_str: str) -> ProcessingResult:
        """
        Parse CSS style attribute string into property dictionary.

        Consolidates style parsing from:
        - src/preprocessing/advanced_plugins.py:502 (style parsing)
        - src/preprocessing/geometry_plugins.py:458 (_parse_style)

        Args:
            style_str: CSS style attribute string

        Returns:
            ProcessingResult with Dict[str, str] as value
        """
        if not style_str or not style_str.strip():
            return ProcessingResult(success=True, value={}, original_value=style_str)

        try:
            # Use StyleParser if available
            if UTILITY_SERVICES_AVAILABLE and style_parser:
                style_result = style_parser.parse_style_string(style_str)
                properties = {}
                for decl in style_result.declarations:
                    properties[decl.property] = decl.value

                return ProcessingResult(
                    success=True,
                    value=properties,
                    original_value=style_str,
                    errors=style_result.errors,
                )

        except Exception as e:
            # Fall back to manual parsing
            pass

        # Manual parsing fallback
        try:
            properties = {}
            if style_str.strip():
                # Split on semicolons and parse each declaration
                declarations = style_str.split(';')
                for decl in declarations:
                    if ':' in decl:
                        prop, value = decl.split(':', 1)
                        properties[prop.strip()] = value.strip()

            return ProcessingResult(
                success=True,
                value=properties,
                original_value=style_str,
            )

        except Exception as e:
            return ProcessingResult(
                success=False,
                value={},
                original_value=style_str,
                errors=[f"Style parsing failed: {str(e)}"],
            )

    def format_style_attribute(self, properties: dict[str, str]) -> str:
        """
        Format property dictionary back to CSS style string.

        Args:
            properties: Dictionary of CSS properties

        Returns:
            Formatted CSS style string
        """
        if not properties:
            return ""

        declarations = []
        for prop, value in properties.items():
            if value and value.strip():
                declarations.append(f"{prop}:{value}")

        return ";".join(declarations)

    def parse_transform_attribute(self, transform_str: str) -> ProcessingResult:
        """
        Parse SVG transform attribute string into transform list.

        Consolidates transform parsing from:
        - src/preprocessing/advanced_plugins.py:230 (_parse_transforms)

        Args:
            transform_str: SVG transform attribute string

        Returns:
            ProcessingResult with List[Dict] as value
        """
        if not transform_str or not transform_str.strip():
            return ProcessingResult(success=True, value=[], original_value=transform_str)

        transforms = []
        errors = []

        try:
            # Parse each transform function
            for func_name, pattern in self.transform_patterns.items():
                matches = pattern.finditer(transform_str)
                for match in matches:
                    try:
                        transform_dict = self._parse_transform_match(func_name, match)
                        if transform_dict:
                            transforms.append(transform_dict)
                    except Exception as e:
                        errors.append(f"Failed to parse {func_name}: {str(e)}")

            return ProcessingResult(
                success=True,
                value=transforms,
                original_value=transform_str,
                errors=errors,
            )

        except Exception as e:
            return ProcessingResult(
                success=False,
                value=[],
                original_value=transform_str,
                errors=[f"Transform parsing failed: {str(e)}"],
            )

    def _parse_transform_match(self, func_name: str, match) -> dict | None:
        """Parse individual transform function match into dictionary."""
        if func_name == 'matrix':
            values = [float(x.strip()) for x in match.group(1).split(',')]
            if len(values) == 6:
                return {
                    'type': 'matrix',
                    'a': values[0], 'b': values[1], 'c': values[2],
                    'd': values[3], 'e': values[4], 'f': values[5],
                }

        elif func_name == 'translate':
            tx = float(match.group(1))
            ty = float(match.group(2)) if match.group(2) else 0.0
            return {'type': 'translate', 'tx': tx, 'ty': ty}

        elif func_name == 'scale':
            sx = float(match.group(1))
            sy = float(match.group(2)) if match.group(2) else sx
            return {'type': 'scale', 'sx': sx, 'sy': sy}

        elif func_name == 'rotate':
            angle = float(match.group(1))
            cx = float(match.group(2)) if match.group(2) else 0.0
            cy = float(match.group(3)) if match.group(3) else 0.0
            return {'type': 'rotate', 'angle': angle, 'cx': cx, 'cy': cy}

        elif func_name == 'skewX':
            angle = float(match.group(1))
            return {'type': 'skewX', 'angle': angle}

        elif func_name == 'skewY':
            angle = float(match.group(1))
            return {'type': 'skewY', 'angle': angle}

        return None

    def format_transform_attribute(self, transforms: list[dict], precision: int = 3) -> str:
        """
        Format transform list back to SVG transform string.

        Args:
            transforms: List of transform dictionaries
            precision: Decimal precision

        Returns:
            Formatted transform string
        """
        if not transforms:
            return ""

        transform_strings = []
        for transform in transforms:
            transform_type = transform.get('type')

            if transform_type == 'matrix':
                values = [
                    transform.get('a', 1), transform.get('b', 0), transform.get('c', 0),
                    transform.get('d', 1), transform.get('e', 0), transform.get('f', 0),
                ]
                formatted_values = [self.format_number(v, precision) for v in values]
                transform_strings.append(f"matrix({','.join(formatted_values)})")

            elif transform_type == 'translate':
                tx = self.format_number(transform.get('tx', 0), precision)
                ty = transform.get('ty', 0)
                if ty == 0:
                    transform_strings.append(f"translate({tx})")
                else:
                    ty_str = self.format_number(ty, precision)
                    transform_strings.append(f"translate({tx},{ty_str})")

            elif transform_type == 'scale':
                sx = self.format_number(transform.get('sx', 1), precision)
                sy = transform.get('sy')
                if sy is None or sy == transform.get('sx', 1):
                    transform_strings.append(f"scale({sx})")
                else:
                    sy_str = self.format_number(sy, precision)
                    transform_strings.append(f"scale({sx},{sy_str})")

            elif transform_type == 'rotate':
                angle = self.format_number(transform.get('angle', 0), precision)
                cx = transform.get('cx', 0)
                cy = transform.get('cy', 0)
                if cx == 0 and cy == 0:
                    transform_strings.append(f"rotate({angle})")
                else:
                    cx_str = self.format_number(cx, precision)
                    cy_str = self.format_number(cy, precision)
                    transform_strings.append(f"rotate({angle} {cx_str} {cy_str})")

            elif transform_type == 'skewX':
                angle = self.format_number(transform.get('angle', 0), precision)
                transform_strings.append(f"skewX({angle})")

            elif transform_type == 'skewY':
                angle = self.format_number(transform.get('angle', 0), precision)
                transform_strings.append(f"skewY({angle})")

        return " ".join(transform_strings)

    def parse_dimension_value(self, dimension_str: str) -> ProcessingResult:
        """
        Parse dimension string (like "100px", "50%") into numeric value.

        Consolidates dimension parsing from multiple plugins.

        Args:
            dimension_str: Dimension string with optional units

        Returns:
            ProcessingResult with float as value
        """
        if not dimension_str or not dimension_str.strip():
            return ProcessingResult(success=False, value=0.0, original_value=dimension_str)

        try:
            # Remove common units and parse number
            cleaned = dimension_str.strip().lower()

            # Handle percentage
            if cleaned.endswith('%'):
                num = float(cleaned[:-1])
                return ProcessingResult(
                    success=True,
                    value=num,
                    original_value=dimension_str,
                    modifications=[f"Parsed percentage: {num}%"],
                )

            # Handle other units
            for unit in ['px', 'pt', 'em', 'rem', 'in', 'cm', 'mm']:
                if cleaned.endswith(unit):
                    num = float(cleaned[:-len(unit)])
                    return ProcessingResult(
                        success=True,
                        value=num,
                        original_value=dimension_str,
                        modifications=[f"Parsed {unit} value: {num}"],
                    )

            # No unit, parse as number
            num = float(cleaned)
            return ProcessingResult(
                success=True,
                value=num,
                original_value=dimension_str,
            )

        except Exception as e:
            return ProcessingResult(
                success=False,
                value=0.0,
                original_value=dimension_str,
                errors=[f"Dimension parsing failed: {str(e)}"],
            )

    def optimize_numeric_precision(self, text: str, precision: int = 3) -> str:
        """
        Optimize numeric precision in any text containing numbers.

        Consolidates numeric optimization across preprocessing plugins.

        Args:
            text: Text containing numbers
            precision: Target decimal precision

        Returns:
            Text with optimized numeric precision
        """
        if not text:
            return text

        def format_match(match):
            try:
                num = float(match.group())
                return self.format_number(num, precision)
            except (ValueError, TypeError):
                return match.group()

        return self.number_pattern.sub(format_match, text)

    def validate_element_attribute(self, element, attr_name: str,
                                 expected_type: type = str) -> ProcessingResult:
        """
        Validate and clean element attribute with type checking.

        Args:
            element: XML element
            attr_name: Attribute name
            expected_type: Expected type (str, float, int)

        Returns:
            ProcessingResult with validated attribute value
        """
        attr_value = element.get(attr_name)

        if attr_value is None:
            return ProcessingResult(
                success=False,
                value=None,
                original_value=None,
                errors=[f"Attribute '{attr_name}' not found"],
            )

        try:
            if expected_type == float:
                value = float(attr_value)
            elif expected_type == int:
                value = int(float(attr_value))  # Handle decimal strings
            else:
                value = str(attr_value).strip()

            return ProcessingResult(
                success=True,
                value=value,
                original_value=attr_value,
            )

        except Exception as e:
            return ProcessingResult(
                success=False,
                value=None,
                original_value=attr_value,
                errors=[f"Type conversion failed: {str(e)}"],
            )


# Global preprocessor utilities instance for convenience
preprocessor_utilities = PreprocessorUtilities()


# Convenience functions for common operations
def format_number(num: float | int, precision: int = 3) -> str:
    """Convenience function for number formatting."""
    return preprocessor_utilities.format_number(num, precision)


def parse_points(points_str: str) -> list[tuple[float, float]]:
    """Convenience function for points parsing."""
    result = preprocessor_utilities.parse_points_string(points_str)
    return result.value if result.success else []


def parse_style(style_str: str) -> dict[str, str]:
    """Convenience function for style parsing."""
    result = preprocessor_utilities.parse_style_attribute(style_str)
    return result.value if result.success else {}


def clean_numeric_value(value: str, precision: int = 3) -> str:
    """Convenience function for numeric value cleaning."""
    return preprocessor_utilities.clean_numeric_value(value, precision)