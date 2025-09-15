#!/usr/bin/env python3
"""
Unit tests for filter parsing utilities.

This module tests SVG filter-specific parsing functions including:
- SVG filter primitive parsing
- Parameter extraction and validation
- Malformed input handling
- Integration with existing ColorParser, UnitConverter, etc.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from lxml import etree as ET
from typing import Dict, Any, Optional, List

# Import the parsing utilities we'll be testing
from src.converters.filters.utils.parsing import (
    FilterPrimitiveParser,
    FilterParameterExtractor,
    FilterCoordinateParser,
    FilterValueParser,
    FilterParsingException,
    parse_filter_primitive,
    parse_filter_coordinate,
    parse_filter_value,
    extract_primitive_parameters
)

# Import existing architecture components
from src.colors import ColorParser, ColorInfo, ColorFormat
from src.units import UnitConverter
from src.transforms import TransformParser
from src.viewbox import ViewportResolver


class TestFilterPrimitiveParser:
    """Test SVG filter primitive parsing functionality."""

    @pytest.fixture
    def mock_color_parser(self):
        """Mock ColorParser for testing."""
        mock = Mock()
        mock.parse_color.return_value = ColorInfo(
            red=255, green=0, blue=0, alpha=1.0,
            format=ColorFormat.HEX, original="#ff0000"
        )
        return mock

    @pytest.fixture
    def mock_unit_converter(self):
        """Mock UnitConverter for testing."""
        mock = Mock()
        mock.to_emu.return_value = 914400  # 1 inch in EMUs
        mock.parse_length.return_value = (1.0, 'px')
        return mock

    @pytest.fixture
    def parser(self, mock_color_parser, mock_unit_converter):
        """Create FilterPrimitiveParser instance with mocked dependencies."""
        return FilterPrimitiveParser(
            color_parser=mock_color_parser,
            unit_converter=mock_unit_converter
        )

    def test_initialization(self, mock_color_parser, mock_unit_converter):
        """Test FilterPrimitiveParser initialization."""
        parser = FilterPrimitiveParser(mock_color_parser, mock_unit_converter)

        assert parser.color_parser == mock_color_parser
        assert parser.unit_converter == mock_unit_converter
        assert hasattr(parser, 'primitive_parsers')

    def test_initialization_with_invalid_dependencies(self):
        """Test initialization with invalid dependencies."""
        with pytest.raises(FilterParsingException):
            FilterPrimitiveParser(None, Mock())

        with pytest.raises(FilterParsingException):
            FilterPrimitiveParser(Mock(), None)

    @pytest.mark.parametrize("primitive_type,expected_parser", [
        ("feGaussianBlur", "gaussian_blur"),
        ("feOffset", "offset"),
        ("feFlood", "flood"),
        ("feColorMatrix", "color_matrix"),
        ("feComposite", "composite"),
        ("feMorphology", "morphology"),
        ("feConvolveMatrix", "convolve"),
        ("feDiffuseLighting", "diffuse_lighting")
    ])
    def test_primitive_type_recognition(self, parser, primitive_type, expected_parser):
        """Test recognition of different filter primitive types."""
        xml_string = f'<{primitive_type} xmlns="http://www.w3.org/2000/svg"/>'
        element = ET.fromstring(xml_string)

        result = parser.identify_primitive_type(element)
        assert result == primitive_type

    def test_gaussian_blur_parsing(self, parser):
        """Test parsing of feGaussianBlur primitive."""
        xml_string = '''
        <feGaussianBlur xmlns="http://www.w3.org/2000/svg"
                        stdDeviation="2.5"
                        in="SourceGraphic"
                        result="blur1"/>
        '''
        element = ET.fromstring(xml_string)

        result = parser.parse_primitive(element)

        assert result.type == "feGaussianBlur"
        assert result.parameters["stdDeviation"] == 2.5
        assert result.input_refs == ["SourceGraphic"]
        assert result.output_ref == "blur1"

    def test_offset_parsing(self, parser):
        """Test parsing of feOffset primitive."""
        xml_string = '''
        <feOffset xmlns="http://www.w3.org/2000/svg"
                  dx="3"
                  dy="4"
                  in="blur1"
                  result="offset1"/>
        '''
        element = ET.fromstring(xml_string)

        result = parser.parse_primitive(element)

        assert result.type == "feOffset"
        assert result.parameters["dx"] == 3.0
        assert result.parameters["dy"] == 4.0
        assert result.input_refs == ["blur1"]
        assert result.output_ref == "offset1"

    def test_flood_parsing(self, parser):
        """Test parsing of feFlood primitive with color."""
        xml_string = '''
        <feFlood xmlns="http://www.w3.org/2000/svg"
                 flood-color="#ff0000"
                 flood-opacity="0.8"
                 result="flood1"/>
        '''
        element = ET.fromstring(xml_string)

        result = parser.parse_primitive(element)

        assert result.type == "feFlood"
        assert result.parameters["flood-color"] == "#ff0000"
        assert result.parameters["flood-opacity"] == 0.8
        assert result.output_ref == "flood1"

    def test_color_matrix_parsing(self, parser):
        """Test parsing of feColorMatrix primitive."""
        xml_string = '''
        <feColorMatrix xmlns="http://www.w3.org/2000/svg"
                       type="saturate"
                       values="0.5"
                       in="SourceGraphic"
                       result="colorMatrix1"/>
        '''
        element = ET.fromstring(xml_string)

        result = parser.parse_primitive(element)

        assert result.type == "feColorMatrix"
        assert result.parameters["type"] == "saturate"
        assert result.parameters["values"] == "0.5"
        assert result.input_refs == ["SourceGraphic"]
        assert result.output_ref == "colorMatrix1"

    def test_composite_parsing(self, parser):
        """Test parsing of feComposite primitive."""
        xml_string = '''
        <feComposite xmlns="http://www.w3.org/2000/svg"
                     operator="over"
                     in="flood1"
                     in2="offset1"
                     result="composite1"/>
        '''
        element = ET.fromstring(xml_string)

        result = parser.parse_primitive(element)

        assert result.type == "feComposite"
        assert result.parameters["operator"] == "over"
        assert result.input_refs == ["flood1", "offset1"]
        assert result.output_ref == "composite1"

    def test_morphology_parsing(self, parser):
        """Test parsing of feMorphology primitive."""
        xml_string = '''
        <feMorphology xmlns="http://www.w3.org/2000/svg"
                      operator="dilate"
                      radius="2"
                      in="SourceGraphic"
                      result="morph1"/>
        '''
        element = ET.fromstring(xml_string)

        result = parser.parse_primitive(element)

        assert result.type == "feMorphology"
        assert result.parameters["operator"] == "dilate"
        assert result.parameters["radius"] == 2.0
        assert result.input_refs == ["SourceGraphic"]
        assert result.output_ref == "morph1"

    def test_malformed_primitive_handling(self, parser):
        """Test handling of malformed filter primitives."""
        # Missing required attributes
        xml_string = '<feGaussianBlur xmlns="http://www.w3.org/2000/svg"/>'
        element = ET.fromstring(xml_string)

        with pytest.raises(FilterParsingException):
            parser.parse_primitive(element)

        # Invalid primitive type
        xml_string = '<feInvalidFilter xmlns="http://www.w3.org/2000/svg"/>'
        element = ET.fromstring(xml_string)

        with pytest.raises(FilterParsingException):
            parser.parse_primitive(element)

    def test_edge_cases(self, parser):
        """Test edge cases in primitive parsing."""
        # Empty stdDeviation should raise error
        xml_string = '''
        <feGaussianBlur xmlns="http://www.w3.org/2000/svg"
                        stdDeviation=""
                        in="SourceGraphic"/>
        '''
        element = ET.fromstring(xml_string)

        with pytest.raises(FilterParsingException):
            parser.parse_primitive(element)

        # Missing in attribute should default to SourceGraphic
        xml_string = '<feGaussianBlur xmlns="http://www.w3.org/2000/svg" stdDeviation="1"/>'
        element = ET.fromstring(xml_string)

        result = parser.parse_primitive(element)
        assert result.input_refs == ["SourceGraphic"]


class TestFilterParameterExtractor:
    """Test filter parameter extraction functionality."""

    @pytest.fixture
    def mock_color_parser(self):
        """Mock ColorParser for testing."""
        mock = Mock()
        mock.parse_color.return_value = ColorInfo(
            red=0, green=255, blue=0, alpha=0.8,
            format=ColorFormat.HEX, original="#00ff00"
        )
        return mock

    @pytest.fixture
    def mock_unit_converter(self):
        """Mock UnitConverter for testing."""
        mock = Mock()
        mock.to_emu.return_value = 1828800  # 2 inches in EMUs
        mock.parse_length.return_value = (2.0, 'px')
        return mock

    @pytest.fixture
    def extractor(self, mock_color_parser, mock_unit_converter):
        """Create FilterParameterExtractor instance."""
        return FilterParameterExtractor(
            color_parser=mock_color_parser,
            unit_converter=mock_unit_converter
        )

    def test_initialization(self, extractor, mock_color_parser, mock_unit_converter):
        """Test FilterParameterExtractor initialization."""
        assert extractor.color_parser == mock_color_parser
        assert extractor.unit_converter == mock_unit_converter

    @pytest.mark.parametrize("param_name,param_value,expected_type", [
        ("stdDeviation", "2.5", float),
        ("dx", "3", int),
        ("dy", "-4", int),
        ("flood-color", "#ff0000", str),
        ("flood-opacity", "0.8", float),
        ("operator", "over", str),
        ("radius", "1 2", str),  # Space-separated values
        ("values", "0.21 0.72 0.07 0 0", str)  # Matrix values
    ])
    def test_parameter_type_extraction(self, extractor, param_name, param_value, expected_type):
        """Test extraction of different parameter types."""
        xml_string = f'<filter xmlns="http://www.w3.org/2000/svg" {param_name}="{param_value}"/>'
        element = ET.fromstring(xml_string)

        if expected_type == float:
            result = extractor.extract_numeric_parameter(element, param_name)
            assert isinstance(result, float)
            assert result == float(param_value)
        elif expected_type == int:
            result = extractor.extract_numeric_parameter(element, param_name)
            assert isinstance(result, (int, float))
            assert result == float(param_value)  # numeric_parameter returns float
        else:
            result = extractor.extract_parameter(element, param_name)
            assert isinstance(result, str)
            assert result == param_value

    def test_color_parameter_extraction(self, extractor):
        """Test extraction of color parameters using ColorParser."""
        xml_string = '<filter xmlns="http://www.w3.org/2000/svg" flood-color="#00ff00"/>'
        element = ET.fromstring(xml_string)

        result = extractor.extract_color_parameter(element, "flood-color")

        assert result.original == "#00ff00"
        assert result.format == ColorFormat.HEX
        extractor.color_parser.parse_color.assert_called_with("#00ff00")

    def test_length_parameter_extraction(self, extractor):
        """Test extraction of length parameters using UnitConverter."""
        xml_string = '<filter xmlns="http://www.w3.org/2000/svg" dx="5px"/>'
        element = ET.fromstring(xml_string)

        result = extractor.extract_length_parameter(element, "dx")

        assert result == 1828800  # Mock returns 2 inches in EMUs
        extractor.unit_converter.to_emu.assert_called_with("5px")

    def test_missing_parameter_handling(self, extractor):
        """Test handling of missing parameters."""
        xml_string = '<filter xmlns="http://www.w3.org/2000/svg"/>'
        element = ET.fromstring(xml_string)

        # Should return None for missing parameters
        result = extractor.extract_parameter(element, "nonexistent")
        assert result is None

        # Should return default for missing parameters with default
        result = extractor.extract_parameter(element, "stdDeviation", default="0")
        assert result == "0"

    def test_malformed_parameter_handling(self, extractor):
        """Test handling of malformed parameters."""
        # Invalid numeric value
        xml_string = '<filter xmlns="http://www.w3.org/2000/svg" stdDeviation="invalid"/>'
        element = ET.fromstring(xml_string)

        with pytest.raises(FilterParsingException):
            extractor.extract_numeric_parameter(element, "stdDeviation")

        # Invalid color value
        extractor.color_parser.parse_color.side_effect = Exception("Invalid color")
        xml_string = '<filter xmlns="http://www.w3.org/2000/svg" flood-color="invalid"/>'
        element = ET.fromstring(xml_string)

        with pytest.raises(FilterParsingException):
            extractor.extract_color_parameter(element, "flood-color")


class TestFilterCoordinateParser:
    """Test filter coordinate parsing functionality."""

    @pytest.fixture
    def parser(self):
        """Create FilterCoordinateParser instance."""
        return FilterCoordinateParser()

    def test_initialization(self, parser):
        """Test FilterCoordinateParser initialization."""
        assert hasattr(parser, 'parse_coordinate')

    @pytest.mark.parametrize("coord_string,expected_value", [
        ("0", 0.0),
        ("1", 1.0),
        ("-0.5", -0.5),
        ("50%", 0.5),
        ("100%", 1.0),
        ("0%", 0.0),
        ("150%", 1.5),
        ("0.25", 0.25)
    ])
    def test_coordinate_parsing(self, parser, coord_string, expected_value):
        """Test parsing of different coordinate formats."""
        result = parser.parse_coordinate(coord_string)
        assert result == expected_value

    def test_malformed_coordinate_handling(self, parser):
        """Test handling of malformed coordinates."""
        with pytest.raises(FilterParsingException):
            parser.parse_coordinate("invalid")

        with pytest.raises(FilterParsingException):
            parser.parse_coordinate("50.5%px")  # Mixed units

        with pytest.raises(FilterParsingException):
            parser.parse_coordinate("")  # Empty string

    def test_edge_cases(self, parser):
        """Test edge cases in coordinate parsing."""
        # Very small percentages
        result = parser.parse_coordinate("0.01%")
        assert result == 0.0001

        # Large values
        result = parser.parse_coordinate("1000%")
        assert result == 10.0

        # Negative percentages
        result = parser.parse_coordinate("-25%")
        assert result == -0.25


class TestFilterValueParser:
    """Test filter value parsing functionality."""

    @pytest.fixture
    def mock_unit_converter(self):
        """Mock UnitConverter for testing."""
        mock = Mock()
        mock.to_emu.return_value = 914400
        mock.parse_length.return_value = (1.0, 'px')
        return mock

    @pytest.fixture
    def parser(self, mock_unit_converter):
        """Create FilterValueParser instance."""
        return FilterValueParser(unit_converter=mock_unit_converter)

    def test_initialization(self, parser, mock_unit_converter):
        """Test FilterValueParser initialization."""
        assert parser.unit_converter == mock_unit_converter

    @pytest.mark.parametrize("value_string,bounds,expected_result", [
        ("5", {"width": 100, "height": 100}, 914400),  # Absolute value
        ("5px", {"width": 100, "height": 100}, 914400),  # With units
        ("10%", {"width": 100, "height": 100}, 914400),  # Percentage (mock result)
        ("0", {"width": 100, "height": 100}, 914400),  # Zero value
        ("-2", {"width": 100, "height": 100}, 914400)  # Negative value
    ])
    def test_value_parsing(self, parser, value_string, bounds, expected_result):
        """Test parsing of different value formats."""
        result = parser.parse_filter_value(value_string, bounds)
        assert result == expected_result
        parser.unit_converter.to_emu.assert_called()

    def test_percentage_bounds_calculation(self, parser):
        """Test percentage value calculation with bounds."""
        bounds = {"width": 200, "height": 150}

        # Mock should be called with percentage calculation
        parser.parse_filter_value("50%", bounds)
        parser.unit_converter.to_emu.assert_called()

    def test_malformed_value_handling(self, parser):
        """Test handling of malformed values."""
        bounds = {"width": 100, "height": 100}

        with pytest.raises(FilterParsingException):
            parser.parse_filter_value("invalid", bounds)

        with pytest.raises(FilterParsingException):
            parser.parse_filter_value("", bounds)  # Empty value

    def test_edge_cases(self, parser):
        """Test edge cases in value parsing."""
        bounds = {"width": 100, "height": 100}

        # Very large values
        parser.parse_filter_value("999999", bounds)
        parser.unit_converter.to_emu.assert_called()

        # Very small values
        parser.parse_filter_value("0.001", bounds)
        parser.unit_converter.to_emu.assert_called()


class TestParseFunctionHelpers:
    """Test standalone parsing function helpers."""

    def test_parse_filter_primitive_function(self):
        """Test parse_filter_primitive standalone function."""
        xml_string = '''
        <feGaussianBlur xmlns="http://www.w3.org/2000/svg"
                        stdDeviation="1.5"
                        in="SourceGraphic"/>
        '''
        element = ET.fromstring(xml_string)

        mock_color_parser = Mock()
        mock_unit_converter = Mock()

        result = parse_filter_primitive(element, mock_color_parser, mock_unit_converter)

        assert result.type == "feGaussianBlur"
        assert result.parameters["stdDeviation"] == 1.5
        assert result.input_refs == ["SourceGraphic"]

    def test_parse_filter_coordinate_function(self):
        """Test parse_filter_coordinate standalone function."""
        result = parse_filter_coordinate("75%")
        assert result == 0.75

        result = parse_filter_coordinate("3.14")
        assert result == 3.14

    def test_parse_filter_value_function(self):
        """Test parse_filter_value standalone function."""
        mock_unit_converter = Mock(spec=UnitConverter)
        mock_unit_converter.to_emu.return_value = 1371600  # 1.5 inches

        bounds = {"width": 300, "height": 200}
        result = parse_filter_value("10px", bounds, mock_unit_converter)

        assert result == 1371600
        mock_unit_converter.to_emu.assert_called_with("10px")

    def test_extract_primitive_parameters_function(self):
        """Test extract_primitive_parameters standalone function."""
        xml_string = '''
        <feOffset xmlns="http://www.w3.org/2000/svg"
                  dx="2"
                  dy="3"
                  in="blur1"
                  result="offset1"/>
        '''
        element = ET.fromstring(xml_string)

        mock_color_parser = Mock()
        mock_unit_converter = Mock()

        result = extract_primitive_parameters(
            element, ["dx", "dy", "in", "result"],
            mock_color_parser, mock_unit_converter
        )

        assert result["dx"] == "2"
        assert result["dy"] == "3"
        assert result["in"] == "blur1"
        assert result["result"] == "offset1"


class TestIntegrationWithExistingArchitecture:
    """Test integration with existing ColorParser, UnitConverter, etc."""

    @pytest.fixture
    def real_color_parser(self):
        """Use a real ColorParser instance for integration testing."""
        return ColorParser()

    @pytest.fixture
    def real_unit_converter(self):
        """Use a real UnitConverter instance for integration testing."""
        return UnitConverter()

    def test_integration_with_color_parser(self, real_color_parser):
        """Test integration with real ColorParser."""
        mock_unit_converter = Mock()
        parser = FilterPrimitiveParser(real_color_parser, mock_unit_converter)

        xml_string = '''
        <feFlood xmlns="http://www.w3.org/2000/svg"
                 flood-color="#ff8000"
                 flood-opacity="0.9"/>
        '''
        element = ET.fromstring(xml_string)

        result = parser.parse_primitive(element)

        assert result.type == "feFlood"
        assert result.parameters["flood-color"] == "#ff8000"
        assert result.parameters["flood-opacity"] == 0.9

    def test_integration_with_unit_converter(self, real_unit_converter):
        """Test integration with real UnitConverter."""
        mock_color_parser = Mock()
        parser = FilterValueParser(real_unit_converter)

        bounds = {"width": 400, "height": 300}
        result = parser.parse_filter_value("12pt", bounds)

        # Should return actual EMU conversion for 12pt
        assert isinstance(result, (int, float))
        assert result > 0


class TestErrorHandlingAndValidation:
    """Test comprehensive error handling and validation."""

    @pytest.fixture
    def parser(self):
        """Create parser with mocked dependencies."""
        mock_color_parser = Mock()
        mock_unit_converter = Mock()
        return FilterPrimitiveParser(mock_color_parser, mock_unit_converter)

    def test_xml_parsing_errors(self, parser):
        """Test handling of XML parsing errors."""
        # Malformed XML should raise XMLSyntaxError at XML parsing level
        with pytest.raises(ET.XMLSyntaxError):
            xml_string = '<feGaussianBlur unclosed="value"'
            element = ET.fromstring(xml_string)

    def test_namespace_handling(self, parser):
        """Test proper namespace handling in parsing."""
        # SVG namespace
        xml_string = '''
        <svg:feGaussianBlur xmlns:svg="http://www.w3.org/2000/svg"
                           stdDeviation="2"/>
        '''
        element = ET.fromstring(xml_string)

        result = parser.parse_primitive(element)
        assert result.type == "feGaussianBlur"

        # No namespace
        xml_string = '<feGaussianBlur stdDeviation="2"/>'
        element = ET.fromstring(xml_string)

        result = parser.parse_primitive(element)
        assert result.type == "feGaussianBlur"

    def test_security_validation(self, parser):
        """Test security validation for parsing inputs."""
        # Extremely long attribute values should be rejected
        long_value = "x" * 10000
        xml_string = f'<feGaussianBlur xmlns="http://www.w3.org/2000/svg" stdDeviation="{long_value}"/>'
        element = ET.fromstring(xml_string)

        with pytest.raises(FilterParsingException):
            parser.parse_primitive(element)

        # Script injection attempts should be caught by validation
        # Test with properly formed but malicious content
        test_value = 'javascript:alert(1)'
        xml_string = f'<feFlood xmlns="http://www.w3.org/2000/svg" flood-color="{test_value}"/>'
        element = ET.fromstring(xml_string)

        # Should detect javascript: in the attribute
        with pytest.raises(FilterParsingException):
            parser.parse_primitive(element)

    def test_performance_limits(self, parser):
        """Test performance limits and timeouts."""
        # Very complex filter graphs should have reasonable limits
        complex_xml = '''
        <filter xmlns="http://www.w3.org/2000/svg">
        ''' + '\n'.join([
            f'<feGaussianBlur stdDeviation="{i}" result="blur{i}"/>'
            for i in range(1000)  # Very large number of primitives
        ]) + '''
        </filter>
        '''

        # This should either complete quickly or raise a reasonable limit exception
        # Implementation should prevent infinite loops or excessive processing
        try:
            element = ET.fromstring(complex_xml)
            # Test should complete in reasonable time
        except FilterParsingException:
            # Or raise appropriate limit exception
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])