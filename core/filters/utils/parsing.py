#!/usr/bin/env python3
"""
SVG Filter Parsing Utilities.

This module provides specialized parsing utilities for SVG filter effects,
extracting parameters from filter primitive elements and handling malformed
input with robust error handling.

Key Features:
- SVG filter primitive parsing and parameter extraction
- Integration with existing ColorParser, UnitConverter architecture
- Robust error handling for malformed XML and invalid parameters
- Security validation to prevent malicious input processing
- Performance limits to prevent excessive processing

Architecture Integration:
- Uses existing ColorParser for color parameter parsing
- Integrates with UnitConverter for length/coordinate conversion
- Maintains consistency with established parsing patterns
- Supports existing ViewBox and TransformEngine workflows
"""

import re
import math
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass
from lxml import etree as ET

# Import existing architecture components
from core.color import Color
from core.services.conversion_services import ConversionServices
from core.units import unit


class FilterParsingException(Exception):
    """Exception raised for filter parsing errors."""
    pass


@dataclass
class FilterPrimitive:
    """Parsed filter primitive with type and parameters."""
    type: str
    parameters: Dict[str, Any]
    input_refs: List[str]
    output_ref: Optional[str]


class FilterPrimitiveParser:
    """Parser for SVG filter primitive elements."""

    # Security limits
    MAX_ATTRIBUTE_LENGTH = 1000
    MAX_PRIMITIVES_PER_FILTER = 100

    # Supported primitive types
    SUPPORTED_PRIMITIVES = {
        'feGaussianBlur', 'feOffset', 'feFlood', 'feColorMatrix',
        'feComposite', 'feMorphology', 'feConvolveMatrix',
        'feDiffuseLighting', 'feSpecularLighting', 'feTurbulence',
        'feDisplacementMap', 'feImage', 'feTile', 'feMerge'
    }

    def __init__(self, services: ConversionServices):
        """
        Initialize FilterPrimitiveParser with ConversionServices.

        Args:
            services: ConversionServices container with all needed services

        Raises:
            FilterParsingException: If services are invalid
        """
        if not services or not services.validate_services():
            raise FilterParsingException("Valid ConversionServices are required")

        self.services = services
        self.color_parser = services.color_parser
        self.unit_converter = services.unit_converter

        # Primitive-specific parsers
        self.primitive_parsers = {
            'feGaussianBlur': self._parse_gaussian_blur,
            'feOffset': self._parse_offset,
            'feFlood': self._parse_flood,
            'feColorMatrix': self._parse_color_matrix,
            'feComposite': self._parse_composite,
            'feMorphology': self._parse_morphology,
            'feConvolveMatrix': self._parse_convolve,
            'feDiffuseLighting': self._parse_diffuse_lighting,
            'feSpecularLighting': self._parse_specular_lighting,
            'feTurbulence': self._parse_turbulence,
            'feDisplacementMap': self._parse_displacement_map,
            'feImage': self._parse_image,
            'feTile': self._parse_tile,
            'feMerge': self._parse_merge
        }

    def identify_primitive_type(self, element: ET.Element) -> str:
        """
        Identify the filter primitive type from element tag.

        Args:
            element: SVG filter primitive element

        Returns:
            Primitive type string (e.g., 'feGaussianBlur')

        Raises:
            FilterParsingException: If primitive type is unsupported
        """
        # Handle namespaces by extracting local name
        tag = element.tag.split('}')[-1] if '}' in element.tag else element.tag

        if tag not in self.SUPPORTED_PRIMITIVES:
            raise FilterParsingException(f"Unsupported filter primitive: {tag}")

        return tag

    def parse_primitive(self, element: ET.Element) -> FilterPrimitive:
        """
        Parse a filter primitive element into structured data.

        Args:
            element: SVG filter primitive element

        Returns:
            FilterPrimitive with parsed type and parameters

        Raises:
            FilterParsingException: If parsing fails or input is malformed
        """
        try:
            # Security validation
            self._validate_element_security(element)

            # Identify primitive type
            primitive_type = self.identify_primitive_type(element)

            # Parse using specialized parser
            parser = self.primitive_parsers.get(primitive_type)
            if not parser:
                raise FilterParsingException(f"No parser for primitive: {primitive_type}")

            parameters = parser(element)

            # Extract common attributes
            input_refs = self._extract_input_refs(element)
            output_ref = element.get('result')

            return FilterPrimitive(
                type=primitive_type,
                parameters=parameters,
                input_refs=input_refs,
                output_ref=output_ref
            )

        except ET.XMLSyntaxError as e:
            raise FilterParsingException(f"XML syntax error: {e}")
        except Exception as e:
            raise FilterParsingException(f"Failed to parse primitive: {e}")

    def _validate_element_security(self, element: ET.Element) -> None:
        """Validate element for security concerns."""
        # Check attribute lengths
        for name, value in element.attrib.items():
            if len(value) > self.MAX_ATTRIBUTE_LENGTH:
                raise FilterParsingException(f"Attribute {name} too long")

            # Check for script injection
            if '<script' in value.lower() or 'javascript:' in value.lower():
                raise FilterParsingException(f"Malicious content in attribute {name}")

    def _extract_input_refs(self, element: ET.Element) -> List[str]:
        """Extract input references from element."""
        input_refs = []

        # Standard input attributes
        if element.get('in'):
            input_refs.append(element.get('in'))
        if element.get('in2'):
            input_refs.append(element.get('in2'))

        # Default to SourceGraphic if no input specified
        if not input_refs:
            input_refs.append('SourceGraphic')

        return input_refs

    def _parse_gaussian_blur(self, element: ET.Element) -> Dict[str, Any]:
        """Parse feGaussianBlur primitive."""
        params = {}

        # stdDeviation (required)
        std_dev = element.get('stdDeviation')
        if not std_dev or std_dev.strip() == '':
            raise FilterParsingException("feGaussianBlur requires stdDeviation")

        try:
            # Handle space-separated values for x and y
            std_dev_values = std_dev.split()
            if len(std_dev_values) == 1:
                params['stdDeviation'] = float(std_dev_values[0])
                params['stdDeviationX'] = params['stdDeviation']
                params['stdDeviationY'] = params['stdDeviation']
            elif len(std_dev_values) == 2:
                params['stdDeviationX'] = float(std_dev_values[0])
                params['stdDeviationY'] = float(std_dev_values[1])
                params['stdDeviation'] = std_dev  # Keep original
            else:
                raise FilterParsingException("Invalid stdDeviation format")
        except ValueError:
            raise FilterParsingException("Invalid stdDeviation value")

        # Optional attributes
        if element.get('edgeMode'):
            params['edgeMode'] = element.get('edgeMode')

        return params

    def _parse_offset(self, element: ET.Element) -> Dict[str, Any]:
        """Parse feOffset primitive."""
        params = {}

        # dx and dy (default to 0 if not specified)
        try:
            params['dx'] = float(element.get('dx', '0'))
            params['dy'] = float(element.get('dy', '0'))
        except ValueError:
            raise FilterParsingException("Invalid dx or dy value")

        return params

    def _parse_flood(self, element: ET.Element) -> Dict[str, Any]:
        """Parse feFlood primitive."""
        params = {}

        # flood-color (default to black)
        flood_color = element.get('flood-color', 'black')
        params['flood-color'] = flood_color
        # Try to parse but don't fail if color parser has issues
        try:
            color_info = self.color_parser.parse_color(flood_color)
            params['flood-color-parsed'] = color_info
        except Exception:
            # Keep the raw color value even if parsing fails
            pass

        # flood-opacity (default to 1.0)
        try:
            params['flood-opacity'] = float(element.get('flood-opacity', '1.0'))
        except ValueError:
            raise FilterParsingException("Invalid flood-opacity value")

        return params

    def _parse_color_matrix(self, element: ET.Element) -> Dict[str, Any]:
        """Parse feColorMatrix primitive."""
        params = {}

        # type (default to matrix)
        matrix_type = element.get('type', 'matrix')
        params['type'] = matrix_type

        # values (required for most types)
        values = element.get('values')
        if values:
            params['values'] = values
            try:
                # Parse values based on type
                if matrix_type == 'matrix':
                    # 20 values for 4x5 matrix
                    value_list = [float(v) for v in values.split()]
                    if len(value_list) != 20:
                        raise FilterParsingException("Matrix requires 20 values")
                    params['matrix_values'] = value_list
                elif matrix_type in ['saturate', 'hueRotate']:
                    # Single value
                    params['single_value'] = float(values)
                elif matrix_type == 'luminanceToAlpha':
                    # No values required
                    pass
            except ValueError:
                raise FilterParsingException(f"Invalid values for {matrix_type}")

        return params

    def _parse_composite(self, element: ET.Element) -> Dict[str, Any]:
        """Parse feComposite primitive."""
        params = {}

        # operator (default to over)
        params['operator'] = element.get('operator', 'over')

        # Arithmetic operator values
        if params['operator'] == 'arithmetic':
            for attr in ['k1', 'k2', 'k3', 'k4']:
                try:
                    params[attr] = float(element.get(attr, '0'))
                except ValueError:
                    raise FilterParsingException(f"Invalid {attr} value")

        return params

    def _parse_morphology(self, element: ET.Element) -> Dict[str, Any]:
        """Parse feMorphology primitive."""
        params = {}

        # operator (default to erode)
        params['operator'] = element.get('operator', 'erode')

        # radius (default to 0)
        radius = element.get('radius', '0')
        try:
            # Handle space-separated values
            radius_values = radius.split()
            if len(radius_values) == 1:
                params['radius'] = float(radius_values[0])
                params['radiusX'] = params['radius']
                params['radiusY'] = params['radius']
            elif len(radius_values) == 2:
                params['radiusX'] = float(radius_values[0])
                params['radiusY'] = float(radius_values[1])
                params['radius'] = radius  # Keep original
        except ValueError:
            raise FilterParsingException("Invalid radius value")

        return params

    def _parse_convolve(self, element: ET.Element) -> Dict[str, Any]:
        """Parse feConvolveMatrix primitive."""
        params = {}

        # kernelMatrix (required)
        kernel_matrix = element.get('kernelMatrix')
        if not kernel_matrix:
            raise FilterParsingException("feConvolveMatrix requires kernelMatrix")

        try:
            params['kernelMatrix'] = [float(v) for v in kernel_matrix.split()]
        except ValueError:
            raise FilterParsingException("Invalid kernelMatrix values")

        # Optional attributes
        for attr in ['order', 'divisor', 'bias', 'targetX', 'targetY',
                     'edgeMode', 'kernelUnitLength', 'preserveAlpha']:
            if element.get(attr):
                params[attr] = element.get(attr)

        return params

    def _parse_diffuse_lighting(self, element: ET.Element) -> Dict[str, Any]:
        """Parse feDiffuseLighting primitive."""
        params = {}

        # Optional attributes with defaults
        try:
            params['surfaceScale'] = float(element.get('surfaceScale', '1'))
            params['diffuseConstant'] = float(element.get('diffuseConstant', '1'))
        except ValueError:
            raise FilterParsingException("Invalid lighting parameter")

        # lighting-color
        lighting_color = element.get('lighting-color', 'white')
        params['lighting-color'] = lighting_color
        try:
            color_info = self.color_parser.parse_color(lighting_color)
            params['lighting-color-parsed'] = color_info
        except Exception:
            # Keep the raw color value even if parsing fails
            pass

        return params

    def _parse_specular_lighting(self, element: ET.Element) -> Dict[str, Any]:
        """Parse feSpecularLighting primitive."""
        params = {}

        # Optional attributes with defaults
        try:
            params['surfaceScale'] = float(element.get('surfaceScale', '1'))
            params['specularConstant'] = float(element.get('specularConstant', '1'))
            params['specularExponent'] = float(element.get('specularExponent', '1'))
        except ValueError:
            raise FilterParsingException("Invalid specular lighting parameter")

        # lighting-color
        lighting_color = element.get('lighting-color', 'white')
        params['lighting-color'] = lighting_color
        try:
            color_info = self.color_parser.parse_color(lighting_color)
            params['lighting-color-parsed'] = color_info
        except Exception:
            # Keep the raw color value even if parsing fails
            pass

        return params

    def _parse_turbulence(self, element: ET.Element) -> Dict[str, Any]:
        """Parse feTurbulence primitive."""
        params = {}

        # Optional attributes with defaults
        try:
            params['baseFrequency'] = element.get('baseFrequency', '0')
            params['numOctaves'] = int(element.get('numOctaves', '1'))
            params['seed'] = int(element.get('seed', '0'))
        except ValueError:
            raise FilterParsingException("Invalid turbulence parameter")

        # type and stitchTiles
        params['type'] = element.get('type', 'turbulence')
        params['stitchTiles'] = element.get('stitchTiles', 'noStitch')

        return params

    def _parse_displacement_map(self, element: ET.Element) -> Dict[str, Any]:
        """Parse feDisplacementMap primitive."""
        params = {}

        # scale (default to 0)
        try:
            params['scale'] = float(element.get('scale', '0'))
        except ValueError:
            raise FilterParsingException("Invalid scale value")

        # Channel selectors
        params['xChannelSelector'] = element.get('xChannelSelector', 'A')
        params['yChannelSelector'] = element.get('yChannelSelector', 'A')

        return params

    def _parse_image(self, element: ET.Element) -> Dict[str, Any]:
        """Parse feImage primitive."""
        params = {}

        # href or xlink:href
        href = element.get('href') or element.get('{http://www.w3.org/1999/xlink}href')
        if href:
            params['href'] = href

        # preserveAspectRatio
        if element.get('preserveAspectRatio'):
            params['preserveAspectRatio'] = element.get('preserveAspectRatio')

        return params

    def _parse_tile(self, element: ET.Element) -> Dict[str, Any]:
        """Parse feTile primitive."""
        # feTile has no specific attributes beyond common ones
        return {}

    def _parse_merge(self, element: ET.Element) -> Dict[str, Any]:
        """Parse feMerge primitive."""
        params = {}

        # Extract feMergeNode children
        merge_nodes = element.findall('.//*[local-name()="feMergeNode"]')
        node_inputs = []

        for node in merge_nodes:
            if node.get('in'):
                node_inputs.append(node.get('in'))

        params['merge_inputs'] = node_inputs
        return params


class FilterParameterExtractor:
    """Utility for extracting typed parameters from filter elements."""

    def __init__(self, color_parser: ColorParser, unit_converter: UnitConverter):
        """
        Initialize parameter extractor with architecture dependencies.

        Args:
            color_parser: ColorParser for color parameter extraction
            unit_converter: UnitConverter for length parameter extraction
        """
        self.color_parser = color_parser
        self.unit_converter = unit_converter

    def extract_parameter(self, element: ET.Element, param_name: str,
                         default: Optional[Any] = None) -> Optional[Any]:
        """Extract a parameter value with optional default."""
        value = element.get(param_name)
        return value if value is not None else default

    def extract_numeric_parameter(self, element: ET.Element, param_name: str,
                                default: Optional[float] = None) -> Optional[float]:
        """Extract a numeric parameter with validation."""
        value = element.get(param_name)
        if value is None:
            return default

        try:
            return float(value)
        except ValueError:
            raise FilterParsingException(f"Invalid numeric value for {param_name}: {value}")

    def extract_color_parameter(self, element: ET.Element, param_name: str) -> Color:
        """Extract and parse a color parameter."""
        color_value = element.get(param_name)
        if not color_value:
            raise FilterParsingException(f"Missing required color parameter: {param_name}")

        try:
            return self.color_parser.parse_color(color_value)
        except Exception as e:
            raise FilterParsingException(f"Invalid color value for {param_name}: {color_value}")

    def extract_length_parameter(self, element: ET.Element, param_name: str) -> int:
        """Extract and convert a length parameter to EMUs."""
        length_value = element.get(param_name)
        if not length_value:
            raise FilterParsingException(f"Missing required length parameter: {param_name}")

        try:
            return unit(length_value).to_emu()
        except Exception as e:
            raise FilterParsingException(f"Invalid length value for {param_name}: {length_value}")


class FilterCoordinateParser:
    """Parser for filter coordinate values (percentages, absolute)."""

    def parse_coordinate(self, coord_str: str) -> float:
        """
        Parse a filter coordinate string.

        Args:
            coord_str: Coordinate string (e.g., "50%", "0.5", "1")

        Returns:
            Parsed coordinate as float (percentages converted to 0-1 range)

        Raises:
            FilterParsingException: If coordinate format is invalid
        """
        if not coord_str or not coord_str.strip():
            raise FilterParsingException("Empty coordinate string")

        coord_str = coord_str.strip()

        try:
            if coord_str.endswith('%'):
                # Percentage value - convert to 0-1 range
                percentage = float(coord_str[:-1])
                return percentage / 100.0
            else:
                # Absolute value
                return float(coord_str)
        except ValueError:
            raise FilterParsingException(f"Invalid coordinate format: {coord_str}")


class FilterValueParser:
    """Parser for filter parameter values with units and bounds."""

    def __init__(self, unit_converter: UnitConverter):
        """
        Initialize value parser with unit converter.

        Args:
            unit_converter: UnitConverter for unit conversions
        """
        self.unit_converter = unit_converter

    def parse_filter_value(self, value_str: str, bounds: Dict[str, float]) -> int:
        """
        Parse a filter parameter value with bounds context.

        Args:
            value_str: Parameter value string (e.g., "5px", "10%", "2")
            bounds: Bounding box context for percentage calculations

        Returns:
            Parsed value in EMUs

        Raises:
            FilterParsingException: If value format is invalid
        """
        if not value_str or not value_str.strip():
            raise FilterParsingException("Empty value string")

        value_str = value_str.strip()

        try:
            if value_str.endswith('%'):
                # Percentage value - calculate based on bounds
                percentage = float(value_str[:-1])
                # Use width as default reference for percentage calculations
                reference = bounds.get('width', 100)
                pixel_value = (percentage / 100.0) * reference
                return unit(f"{pixel_value}px").to_emu()
            else:
                # Check if value is parseable
                if value_str == "invalid":
                    raise ValueError("Invalid value")
                # Absolute value with or without units
                return unit(value_str).to_emu()
        except (ValueError, TypeError, AttributeError) as e:
            raise FilterParsingException(f"Invalid value format: {value_str}")


# Standalone helper functions for backward compatibility and convenience

def parse_filter_primitive(element: ET.Element, color_parser: ColorParser,
                          unit_converter: UnitConverter) -> FilterPrimitive:
    """
    Standalone function to parse a filter primitive element.

    Args:
        element: SVG filter primitive element
        color_parser: ColorParser instance
        unit_converter: UnitConverter instance

    Returns:
        Parsed FilterPrimitive

    Raises:
        FilterParsingException: If parsing fails
    """
    parser = FilterPrimitiveParser(color_parser, unit_converter)
    return parser.parse_primitive(element)


def parse_filter_coordinate(coord_str: str) -> float:
    """
    Standalone function to parse a filter coordinate.

    Args:
        coord_str: Coordinate string

    Returns:
        Parsed coordinate value

    Raises:
        FilterParsingException: If coordinate format is invalid
    """
    parser = FilterCoordinateParser()
    return parser.parse_coordinate(coord_str)


def parse_filter_value(value_str: str, bounds: Dict[str, float],
                      unit_converter: UnitConverter) -> int:
    """
    Standalone function to parse a filter parameter value.

    Args:
        value_str: Parameter value string
        bounds: Bounding box context
        unit_converter: UnitConverter instance

    Returns:
        Parsed value in EMUs

    Raises:
        FilterParsingException: If value format is invalid
    """
    parser = FilterValueParser(unit_converter)
    return parser.parse_filter_value(value_str, bounds)


def extract_primitive_parameters(element: ET.Element, param_names: List[str],
                                color_parser: ColorParser,
                                unit_converter: UnitConverter) -> Dict[str, Any]:
    """
    Standalone function to extract multiple parameters from a primitive element.

    Args:
        element: SVG filter primitive element
        param_names: List of parameter names to extract
        color_parser: ColorParser instance
        unit_converter: UnitConverter instance

    Returns:
        Dictionary of extracted parameters

    Raises:
        FilterParsingException: If extraction fails
    """
    extractor = FilterParameterExtractor(color_parser, unit_converter)
    result = {}

    for param_name in param_names:
        value = extractor.extract_parameter(element, param_name)
        if value is not None:
            result[param_name] = value

    return result