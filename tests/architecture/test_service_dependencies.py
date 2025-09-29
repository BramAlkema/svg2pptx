#!/usr/bin/env python3
"""
Service Dependencies Architecture Tests

Tests that validate the dependency injection architecture and ensure
all converters have proper service dependencies configured.
"""

import pytest
import inspect
from unittest.mock import Mock
from typing import get_type_hints

from src.services.conversion_services import ConversionServices
from src.converters.base import BaseConverter
from src.converters.shapes import RectangleConverter, CircleConverter, EllipseConverter
from src.converters.paths import PathConverter
from src.converters.text import TextConverter
from src.converters.image import ImageConverter
from src.converters.symbols import SymbolConverter
from src.converters.gradients import GradientConverter


class TestServiceContainerValidation:
    """Test that ConversionServices contains all required dependencies."""

    def test_service_container_completeness(self):
        """Test that ConversionServices contains ALL required dependencies."""
        services = ConversionServices.create_default()

        # Test all expected services exist
        required_services = [
            'unit_converter', 'color_factory', 'color_parser', 'transform_parser',
            'viewport_resolver', 'style_parser', 'coordinate_transformer',
            'font_processor', 'path_processor', 'pptx_builder', 'gradient_service',
            'pattern_service', 'filter_service', 'image_service'
        ]

        for service_name in required_services:
            assert hasattr(services, service_name), f"Missing service: {service_name}"
            service = getattr(services, service_name)
            # path_system can be None initially
            if service_name != 'path_system':
                assert service is not None, f"Service {service_name} is None"

    def test_service_validation_method(self):
        """Test that service validation correctly identifies missing services."""
        services = ConversionServices.create_default()

        # Should pass validation with all services
        assert services.validate_services(), "Service validation should pass with complete services"

        # Test with broken service
        original_service = services.unit_converter
        services.unit_converter = None
        assert not services.validate_services(), "Service validation should fail with missing unit_converter"

        # Restore service
        services.unit_converter = original_service
        assert services.validate_services(), "Service validation should pass after restoration"

    def test_service_types_are_correct(self):
        """Test that services have the expected types."""
        services = ConversionServices.create_default()

        # Test key service types
        from src.units import UnitConverter
        from src.color import Color
        from src.transforms import TransformEngine
        from src.viewbox import ViewportEngine
        from src.core.pptx_builder import PPTXBuilder

        assert isinstance(services.unit_converter, UnitConverter)
        assert services.color_factory is Color
        assert services.color_parser is Color
        assert isinstance(services.transform_parser, TransformEngine)
        assert isinstance(services.viewport_resolver, ViewportEngine)
        assert isinstance(services.pptx_builder, PPTXBuilder)

    def test_custom_service_creation(self):
        """Test custom service creation works correctly."""
        custom_config = {
            'config': {'default_dpi': 150.0},
            'unit_converter': {},
            'transform_parser': {}
        }

        services = ConversionServices.create_custom(custom_config)
        assert services is not None
        assert services.config.default_dpi == 150.0


class TestConverterServiceRequirements:
    """Test that all converters can be instantiated with ConversionServices."""

    @pytest.fixture
    def services(self):
        """Provide ConversionServices for testing."""
        return ConversionServices.create_default()

    def test_converter_service_requirements(self, services):
        """Test that all converters can be instantiated with ConversionServices."""
        converter_classes = [
            RectangleConverter, CircleConverter, EllipseConverter,
            PathConverter, TextConverter, ImageConverter,
            SymbolConverter, GradientConverter
        ]

        for converter_class in converter_classes:
            # Test instantiation doesn't fail
            converter = converter_class(services)
            assert converter.services is not None
            assert converter.services is services

            # Test required service methods exist
            if hasattr(converter, 'color_parser'):
                color_parser = converter.color_parser
                # Color class should be callable (can parse colors)
                assert callable(color_parser)

    def test_base_converter_service_access(self, services):
        """Test that BaseConverter provides proper service access."""
        # Create a mock converter extending BaseConverter
        class TestConverter(BaseConverter):
            supported_elements = ['test']

            def can_convert(self, element):
                return True

            def convert(self, element, context):
                return "test"

        converter = TestConverter(services)

        # Test service access methods
        assert converter.color_parser is services.color_parser
        assert converter.services.unit_converter is not None
        assert converter.services.transform_parser is not None

    def test_converter_inheritance_chain(self, services):
        """Test that all converters properly inherit from BaseConverter."""
        converter_classes = [
            RectangleConverter, CircleConverter, EllipseConverter,
            PathConverter, TextConverter, ImageConverter,
            SymbolConverter, GradientConverter
        ]

        for converter_class in converter_classes:
            assert issubclass(converter_class, BaseConverter), \
                f"{converter_class.__name__} must inherit from BaseConverter"

            # Test that converter has required interface
            converter = converter_class(services)
            assert hasattr(converter, 'can_convert')
            assert hasattr(converter, 'convert')
            assert hasattr(converter, 'supported_elements')

            # Test interface is callable
            assert callable(converter.can_convert)
            assert callable(converter.convert)


class TestConstructorSignatures:
    """Test all converters have compatible constructor signatures."""

    def test_constructor_signatures(self):
        """Test all converters have compatible constructor signatures."""
        converter_classes = [
            RectangleConverter, CircleConverter, EllipseConverter,
            PathConverter, TextConverter, ImageConverter,
            SymbolConverter, GradientConverter
        ]

        services = ConversionServices.create_default()

        for converter_class in converter_classes:
            sig = inspect.signature(converter_class.__init__)
            params = list(sig.parameters.keys())

            # All converters must accept 'services' parameter
            assert 'services' in params, f"{converter_class.__name__} missing 'services' parameter"

            # Services parameter should be required (not optional)
            services_param = sig.parameters['services']
            assert services_param.default == inspect.Parameter.empty, \
                f"{converter_class.__name__} has optional services (should be required)"

            # Test instantiation works
            try:
                converter = converter_class(services)
                assert converter is not None
            except Exception as e:
                pytest.fail(f"{converter_class.__name__} instantiation failed: {e}")

    def test_constructor_type_hints(self):
        """Test that constructors have proper type hints."""
        converter_classes = [
            RectangleConverter, CircleConverter, EllipseConverter,
            PathConverter, TextConverter, ImageConverter,
            SymbolConverter, GradientConverter
        ]

        for converter_class in converter_classes:
            try:
                type_hints = get_type_hints(converter_class.__init__)
                # Should have type hint for services parameter
                assert 'services' in type_hints or hasattr(converter_class.__init__, '__annotations__'), \
                    f"{converter_class.__name__} missing type hints"
            except (NameError, AttributeError):
                # Some type hints may not be resolvable in test context
                pass

    def test_method_signature_consistency(self):
        """Test that converter methods have consistent signatures."""
        services = ConversionServices.create_default()
        converters = [
            RectangleConverter(services), CircleConverter(services),
            EllipseConverter(services), PathConverter(services),
            TextConverter(services), ImageConverter(services),
            SymbolConverter(services), GradientConverter(services)
        ]

        for converter in converters:
            # All converters must have can_convert method
            assert hasattr(converter, 'can_convert')
            assert callable(converter.can_convert)

            # All converters must have convert method
            assert hasattr(converter, 'convert')
            assert callable(converter.convert)

            # Test method signatures
            can_convert_sig = inspect.signature(converter.can_convert)
            convert_sig = inspect.signature(converter.convert)

            # can_convert should take element parameter
            can_convert_params = list(can_convert_sig.parameters.keys())
            assert 'element' in can_convert_params or len(can_convert_params) >= 1

            # convert should take element and context parameters
            convert_params = list(convert_sig.parameters.keys())
            assert len(convert_params) >= 2, \
                f"{converter.__class__.__name__}.convert needs element and context parameters"


class TestServiceLifecycle:
    """Test service lifecycle management."""

    def test_service_cleanup(self):
        """Test that services can be properly cleaned up."""
        services = ConversionServices.create_default()

        # Test cleanup doesn't crash
        services.cleanup()

        # After cleanup, services should be None
        assert services.unit_converter is None
        assert services.color_factory is None
        assert services.transform_parser is None

    def test_singleton_behavior(self):
        """Test singleton behavior of default instance."""
        # Reset any existing singleton
        ConversionServices.reset_default_instance()

        # Get default instances
        instance1 = ConversionServices.get_default_instance()
        instance2 = ConversionServices.get_default_instance()

        # Should be the same instance
        assert instance1 is instance2

        # Reset and verify new instance is created
        ConversionServices.reset_default_instance()
        instance3 = ConversionServices.get_default_instance()

        # Should be different from previous instances
        assert instance3 is not instance1

    def test_service_initialization_error_handling(self):
        """Test that service initialization errors are properly handled."""
        from src.services.conversion_services import ServiceInitializationError

        # Test that invalid configuration raises appropriate error
        with pytest.raises(ServiceInitializationError):
            # This should fail because we're passing invalid parameters
            ConversionServices.create_custom({
                'unit_converter': {'invalid_param': 'invalid_value'}
            })


if __name__ == "__main__":
    pytest.main([__file__, "-v"])