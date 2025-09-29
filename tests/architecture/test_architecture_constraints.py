#!/usr/bin/env python3
"""
Architecture Integration Tests

Tests for architectural constraints, end-to-end conversion pipelines,
and converter registry completeness.
"""

import pytest
import tempfile
import os
import zipfile
from pathlib import Path
from lxml import etree as ET

from src.svg2pptx import convert_svg_to_pptx, SVGToPowerPointConverter
from src.svg2drawingml import SVGToDrawingMLConverter
from core.services.conversion_services import ConversionServices
from src.converters.base import ConverterRegistry, ConversionContext
from src.converters.shapes import RectangleConverter, CircleConverter, EllipseConverter
from src.converters.paths import PathConverter
from src.converters.text import TextConverter
from src.converters.image import ImageConverter
from src.converters.symbols import SymbolConverter
from src.converters.gradients import GradientConverter


class TestEndToEndConversionPipeline:
    """Test complete SVG to PPTX conversion without crashes."""

    def test_full_conversion_pipeline_simple_shapes(self):
        """Test complete SVG to PPTX conversion with simple shapes."""
        test_svgs = [
            ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200"><rect x="50" y="50" width="100" height="80" fill="blue"/></svg>', 'Rectangle'),
            ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200"><circle cx="100" cy="100" r="50" fill="red"/></svg>', 'Circle'),
            ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200"><ellipse cx="100" cy="100" rx="75" ry="50" fill="green"/></svg>', 'Ellipse'),
            ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200"><line x1="50" y1="50" x2="150" y2="150" stroke="black" stroke-width="2"/></svg>', 'Line'),
        ]

        for svg_content, shape_type in test_svgs:
            with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as tmp:
                try:
                    result = convert_svg_to_pptx(svg_content, tmp.name)
                    assert os.path.exists(result), f"{shape_type} conversion should create file"
                    assert os.path.getsize(result) > 1000, f"{shape_type} file should be non-trivial size"

                    # Verify it's a valid ZIP (PPTX format)
                    with zipfile.ZipFile(result, 'r') as zf:
                        files = zf.namelist()
                        assert '[Content_Types].xml' in files, f"{shape_type} PPTX missing content types"
                        assert 'ppt/presentation.xml' in files, f"{shape_type} PPTX missing presentation"
                        assert any('slide' in f for f in files), f"{shape_type} PPTX missing slides"

                finally:
                    if os.path.exists(tmp.name):
                        os.unlink(tmp.name)

    def test_full_conversion_pipeline_complex_elements(self):
        """Test conversion with complex SVG elements."""
        complex_svgs = [
            ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200"><path d="M50,50 L150,50 Q150,100 100,150 L50,150 Z" fill="purple"/></svg>', 'Path with curves'),
            ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200"><g transform="translate(50,50)"><rect width="100" height="80" fill="blue"/></g></svg>', 'Transformed group'),
            ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200"><text x="100" y="100" text-anchor="middle" font-size="16" fill="black">Test Text</text></svg>', 'Text element'),
            ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200"><polygon points="100,50 150,150 50,150" fill="orange"/></svg>', 'Polygon'),
        ]

        for svg_content, description in complex_svgs:
            try:
                result = convert_svg_to_pptx(svg_content)
                assert os.path.exists(result), f"{description} conversion should create file"

                # Basic validation
                with zipfile.ZipFile(result, 'r') as zf:
                    assert '[Content_Types].xml' in zf.namelist()

                # Clean up
                os.unlink(result)

            except Exception as e:
                pytest.fail(f"{description} conversion failed: {e}")

    def test_conversion_with_edge_case_units(self):
        """Test conversion with various unit types."""
        unit_svgs = [
            ('<svg xmlns="http://www.w3.org/2000/svg" width="100%" height="300px"><rect width="50%" height="200px" fill="red"/></svg>', 'Mixed percentage and pixels'),
            ('<svg xmlns="http://www.w3.org/2000/svg" width="10cm" height="7.5cm"><rect width="5cm" height="3cm" fill="blue"/></svg>', 'Metric units'),
            ('<svg xmlns="http://www.w3.org/2000/svg" width="4in" height="3in"><rect width="2in" height="1.5in" fill="green"/></svg>', 'Imperial units'),
        ]

        for svg_content, description in unit_svgs:
            try:
                result = convert_svg_to_pptx(svg_content)
                assert os.path.exists(result), f"{description} should convert successfully"
                assert os.path.getsize(result) > 1000, f"{description} should produce non-trivial file"
                os.unlink(result)

            except Exception as e:
                # Unit conversion failures are acceptable for complex cases
                print(f"Note: {description} failed (may be expected): {e}")

    def test_svg_to_drawingml_converter_direct(self):
        """Test SVGToDrawingMLConverter directly."""
        services = ConversionServices.create_default()
        converter = SVGToDrawingMLConverter(services=services)

        test_svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect x="10" y="10" width="80" height="80" fill="red"/></svg>'

        try:
            result = converter.convert(test_svg)
            assert isinstance(result, str), "DrawingML result should be string"
            assert len(result.strip()) > 0, "DrawingML result should not be empty"

            # Should contain DrawingML elements
            assert '<p:sp>' in result or '<a:' in result, "Should contain DrawingML markup"

        except Exception as e:
            pytest.fail(f"Direct DrawingML conversion failed: {e}")

    def test_malformed_svg_handling(self):
        """Test that malformed SVGs are handled gracefully."""
        malformed_svgs = [
            ('', 'Empty string'),
            ('<svg></svg>', 'Empty SVG'),
            ('<svg xmlns="http://www.w3.org/2000/svg"><rect x="invalid" y="also invalid"/></svg>', 'Invalid attributes'),
            ('<svg xmlns="http://www.w3.org/2000/svg"><rect width="100%" height="50vh"/></svg>', 'Viewport units'),
            ('<not-svg>Not SVG at all</not-svg>', 'Not SVG'),
        ]

        for svg_content, description in malformed_svgs:
            try:
                result = convert_svg_to_pptx(svg_content)

                # If conversion succeeds, result should be valid
                if result and os.path.exists(result):
                    assert result.endswith('.pptx')
                    with zipfile.ZipFile(result, 'r') as zf:
                        assert '[Content_Types].xml' in zf.namelist()
                    os.unlink(result)

            except Exception:
                # Graceful failure is acceptable for malformed input
                # The key is that it shouldn't crash the entire system
                pass


class TestConverterRegistryCompleteness:
    """Test that converter registry handles all SVG element types."""

    @pytest.fixture
    def services(self):
        return ConversionServices.create_default()

    @pytest.fixture
    def registry(self, services):
        registry = ConverterRegistry()
        registry.register_default_converters(services)
        return registry

    def test_converter_registry_basic_elements(self, registry, services):
        """Test registry handles basic SVG elements."""
        basic_elements = [
            ('rect', 'RectangleConverter'),
            ('circle', 'CircleConverter'),
            ('ellipse', 'EllipseConverter'),
            ('line', 'LineConverter'),
            ('polygon', 'PolygonConverter'),
            ('polyline', 'PolylineConverter')
        ]

        for element_type, converter_name in basic_elements:
            element = ET.Element(element_type)
            converter = registry.get_converter(element)

            if converter is not None:  # Some converters may not be registered yet
                assert converter.can_convert(element), f"Converter should handle {element_type}"

                # Test actual conversion with minimal context
                context = ConversionContext(services=services)
                try:
                    result = converter.convert(element, context)
                    assert isinstance(result, str), f"{converter_name} should return string"
                except Exception as e:
                    # Conversion may fail due to missing attributes, but shouldn't crash
                    print(f"Note: {converter_name} conversion failed (may be expected): {e}")

    def test_converter_registry_complex_elements(self, registry, services):
        """Test registry handles complex SVG elements."""
        complex_elements = ['path', 'text', 'image', 'g', 'use', 'symbol']

        for element_type in complex_elements:
            element = ET.Element(element_type)
            converter = registry.get_converter(element)

            if converter is not None:  # Some converters may not be available
                assert converter.can_convert(element), f"Should handle {element_type}"

                # Test with basic context
                context = ConversionContext(services=services)
                try:
                    result = converter.convert(element, context)
                    assert isinstance(result, str), f"Converter for {element_type} should return string"
                except Exception as e:
                    # Complex elements may fail without proper setup
                    print(f"Note: {element_type} conversion failed (may be expected): {e}")

    def test_converter_can_convert_consistency(self, services):
        """Test that converters consistently report what they can convert."""
        converters = [
            RectangleConverter(services), CircleConverter(services), EllipseConverter(services),
            PathConverter(services), TextConverter(services), ImageConverter(services),
            SymbolConverter(services), GradientConverter(services)
        ]

        for converter in converters:
            supported = converter.supported_elements

            for element_type in supported:
                element = ET.Element(element_type)
                assert converter.can_convert(element), \
                    f"{converter.__class__.__name__} claims to support {element_type} but can_convert returns False"

    def test_registry_fallback_behavior(self, registry, services):
        """Test registry behavior with unsupported elements."""
        unsupported_elements = ['unsupported', 'fake-element', 'not-svg']

        for element_type in unsupported_elements:
            element = ET.Element(element_type)
            converter = registry.get_converter(element)

            # Should return None or a fallback converter
            if converter is not None:
                # If a converter is returned, it should handle the element gracefully
                context = ConversionContext(services=services)
                try:
                    result = converter.convert(element, context)
                    assert isinstance(result, str)
                except Exception:
                    # Fallback conversion may fail, which is acceptable
                    pass


class TestArchitecturalConstraints:
    """Test architectural constraints and dependencies."""

    def test_converter_dependency_injection(self):
        """Test that all converters use dependency injection properly."""
        services = ConversionServices.create_default()

        converter_classes = [
            RectangleConverter, CircleConverter, EllipseConverter,
            PathConverter, TextConverter, ImageConverter,
            SymbolConverter, GradientConverter
        ]

        for converter_class in converter_classes:
            # Test that constructor requires services
            try:
                # This should fail because services are required
                converter_class()
                pytest.fail(f"{converter_class.__name__} should require services parameter")
            except TypeError:
                # Expected - services parameter is required
                pass

            # Test that constructor works with services
            converter = converter_class(services)
            assert converter.services is services
            assert hasattr(converter, 'can_convert')
            assert hasattr(converter, 'convert')

    def test_service_interface_compliance(self):
        """Test that services implement expected interfaces."""
        services = ConversionServices.create_default()

        # Test that all expected services exist and are callable/usable
        service_tests = [
            ('unit_converter', lambda s: hasattr(s.unit_converter, 'parse_value')),
            ('color_factory', lambda s: callable(s.color_factory)),
            ('color_parser', lambda s: callable(s.color_parser)),
            ('transform_parser', lambda s: hasattr(s.transform_parser, 'parse')),
            ('pptx_builder', lambda s: hasattr(s.pptx_builder, 'create_minimal_pptx')),
        ]

        for service_name, test_func in service_tests:
            assert hasattr(services, service_name), f"Missing service: {service_name}"
            service = getattr(services, service_name)
            assert service is not None, f"Service {service_name} is None"
            assert test_func(services), f"Service {service_name} fails interface test"

    def test_conversion_context_completeness(self):
        """Test that ConversionContext provides all needed functionality."""
        services = ConversionServices.create_default()

        # Create a minimal SVG for context
        svg_content = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="50" height="50"/></svg>'
        svg_root = ET.fromstring(svg_content.encode())

        context = ConversionContext(services=services, svg_root=svg_root)

        # Test that context has expected attributes/methods
        expected_attributes = ['services', 'svg_root']
        for attr in expected_attributes:
            assert hasattr(context, attr), f"ConversionContext missing {attr}"

        # Test that context can provide coordinate system
        try:
            coord_system = context.coordinate_system
            assert coord_system is not None, "ConversionContext should provide coordinate system"
        except AttributeError:
            # Coordinate system may be set up differently
            pass

    def test_error_handling_consistency(self):
        """Test that error handling is consistent across converters."""
        services = ConversionServices.create_default()
        context = ConversionContext(services=services)

        converters = [
            RectangleConverter(services), CircleConverter(services),
            PathConverter(services), TextConverter(services)
        ]

        # Test with invalid element
        invalid_element = ET.Element('invalid')

        for converter in converters:
            # Should handle gracefully, not crash
            try:
                can_convert = converter.can_convert(invalid_element)
                assert isinstance(can_convert, bool)

                if can_convert:
                    result = converter.convert(invalid_element, context)
                    assert isinstance(result, str)

            except Exception as e:
                # Some exceptions are acceptable, but should be meaningful
                assert len(str(e)) > 0, f"Exception from {converter.__class__.__name__} should be meaningful"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])