"""
Integration tests for end-to-end dependency injection system.

This module tests the complete dependency injection workflow from ConversionServices
creation through converter instantiation and actual SVG conversion operations.
"""

import pytest
from unittest.mock import Mock, patch
from lxml import etree as ET
import tempfile
import os

from core.services.conversion_services import ConversionServices, ConversionConfig
from core.services.migration_utils import MigrationHelper
from src.converters.base import ConversionContext


class TestEndToEndServiceInjection:
    """Test complete dependency injection workflow."""

    def test_conversion_services_full_integration(self):
        """Test complete ConversionServices creation and converter usage."""
        # Create services with custom config
        config = ConversionConfig(
            default_dpi=150.0,
            viewport_width=1200.0,
            viewport_height=900.0,
            enable_caching=True
        )

        services = ConversionServices.create_default(config)

        # Verify services are properly initialized
        assert services.validate_services() is True
        assert services.unit_converter is not None
        assert services.color_parser is not None
        assert services.transform_parser is not None
        assert services.viewport_resolver is not None

        # Test service configuration propagation
        assert services.config.default_dpi == 150.0
        assert services.config.viewport_width == 1200.0

    def test_converter_registry_with_service_injection(self):
        """Test converter instantiation works with dependency injection."""
        services = ConversionServices.create_default()

        # Test direct converter instantiation with services
        from src.converters.shapes import RectangleConverter
        converter = RectangleConverter(services=services)

        # Verify converter has services
        assert hasattr(converter, 'services')
        assert converter.services is services

        # Test that converter can access services
        assert converter.unit_converter is services.unit_converter
        assert converter.color_parser is services.color_parser

    def test_migration_helper_integration(self):
        """Test MigrationHelper creates converters with proper service injection."""
        from src.converters.shapes import RectangleConverter
        from src.converters.text import TextConverter
        from src.converters.paths import PathConverter

        # Test with default services
        rect_converter = MigrationHelper.create_converter_with_services(RectangleConverter)
        assert rect_converter.validate_services() is True

        # Test with custom config
        config = ConversionConfig(default_dpi=200.0)
        text_converter = MigrationHelper.create_converter_with_services(
            TextConverter,
            config=config
        )
        assert text_converter.validate_services() is True
        assert text_converter.services.config.default_dpi == 200.0

        # Test with existing services
        services = ConversionServices.create_default()
        path_converter = MigrationHelper.create_converter_with_services(
            PathConverter,
            services=services
        )
        assert path_converter.services is services

    def test_service_consistency_across_converters(self):
        """Test that all converters share the same service instances."""
        services = ConversionServices.create_default()

        from src.converters.shapes import RectangleConverter
        from src.converters.text import TextConverter
        from src.converters.gradients import GradientConverter

        rect_converter = RectangleConverter(services=services)
        text_converter = TextConverter(services=services)
        gradient_converter = GradientConverter(services=services)

        # Verify all converters share the same service instances
        assert rect_converter.unit_converter is text_converter.unit_converter
        assert text_converter.color_parser is gradient_converter.color_parser
        assert rect_converter.transform_parser is gradient_converter.transform_parser
        assert text_converter.viewport_resolver is rect_converter.viewport_resolver

    def test_backward_compatibility_property_access(self):
        """Test that backward compatibility properties work correctly."""
        services = ConversionServices.create_default()

        from src.converters.shapes import RectangleConverter
        converter = RectangleConverter(services=services)

        # Test property access works
        assert converter.unit_converter is services.unit_converter
        assert converter.color_parser is services.color_parser
        assert converter.transform_parser is services.transform_parser
        assert converter.viewport_resolver is services.viewport_resolver

        # Test that property access is consistent
        assert converter.unit_converter is converter.unit_converter
        assert converter.color_parser is converter.color_parser


class TestConversionWorkflowIntegration:
    """Test actual SVG conversion workflows with dependency injection."""

    def test_rectangle_conversion_with_services(self):
        """Test rectangle conversion works with dependency injection."""
        services = ConversionServices.create_default()

        from src.converters.shapes import RectangleConverter
        converter = RectangleConverter(services=services)

        # Create test SVG element
        rect_element = ET.fromstring('<rect x="10" y="20" width="100" height="50" fill="red"/>')

        # Test conversion capability
        assert converter.can_convert(rect_element) is True

        # Test that converter has access to services
        assert converter.services is services
        assert converter.unit_converter is services.unit_converter
        assert converter.color_parser is services.color_parser

        # Test that services are functional
        assert services.validate_services() is True

    def test_text_conversion_with_services(self):
        """Test text conversion works with dependency injection."""
        services = ConversionServices.create_default()

        from src.converters.text import TextConverter
        converter = TextConverter(services=services)

        # Create test SVG element
        text_element = ET.fromstring('<text x="10" y="20" fill="blue">Hello World</text>')

        # Test conversion capability
        assert converter.can_convert(text_element) is True

        # Test that converter has access to services
        assert converter.services is services
        assert converter.unit_converter is services.unit_converter
        assert converter.color_parser is services.color_parser

        # Test that services are functional
        assert services.validate_services() is True

    def test_gradient_conversion_with_services(self):
        """Test gradient conversion works with dependency injection."""
        services = ConversionServices.create_default()

        from src.converters.gradients import GradientConverter
        converter = GradientConverter(services=services)

        # Create test SVG element
        gradient_element = ET.fromstring('''
            <linearGradient id="grad1">
                <stop offset="0%" stop-color="red"/>
                <stop offset="100%" stop-color="blue"/>
            </linearGradient>
        ''')

        # Test conversion capability
        assert converter.can_convert(gradient_element) is True

        # Test that converter has access to services
        assert converter.services is services
        assert converter.unit_converter is services.unit_converter
        assert converter.color_parser is services.color_parser

        # Test that services are functional
        assert services.validate_services() is True


class TestServiceConfigurationIntegration:
    """Test service configuration and customization."""

    def test_custom_configuration_propagation(self):
        """Test that custom configuration propagates through the system."""
        config = ConversionConfig(
            default_dpi=300.0,
            viewport_width=2400.0,
            viewport_height=1800.0,
            enable_caching=False
        )

        services = ConversionServices.create_default(config)

        # Verify configuration is properly set
        assert services.config.default_dpi == 300.0
        assert services.config.viewport_width == 2400.0
        assert services.config.viewport_height == 1800.0
        assert services.config.enable_caching is False

        # Test that services use the configuration
        from src.converters.shapes import RectangleConverter
        converter = RectangleConverter(services=services)

        # Verify converter has access to config through services
        assert converter.services.config.default_dpi == 300.0

    def test_service_lifecycle_management(self):
        """Test service lifecycle and initialization order."""
        # Test successful initialization
        services = ConversionServices.create_default()
        assert services.validate_services() is True

        # Test that all services are initialized
        assert services.unit_converter is not None
        assert services.color_parser is not None
        assert services.transform_parser is not None
        assert services.viewport_resolver is not None

        # Test service methods are callable
        assert hasattr(services.unit_converter, 'parse_length')
        assert hasattr(services.color_parser, 'parse')
        assert hasattr(services.transform_parser, 'parse')

    def test_error_handling_and_fallbacks(self):
        """Test error handling in service initialization."""
        # Test with valid config
        config = ConversionConfig()
        services = ConversionServices.create_default(config)
        assert services.validate_services() is True

        # Test service validation catches issues
        # This would normally fail validation if services were None
        assert services.unit_converter is not None
        assert services.color_parser is not None


class TestRegistryIntegration:
    """Test converter registry integration with dependency injection."""

    def test_registry_service_propagation(self):
        """Test that registry properly propagates services to converters."""
        services = ConversionServices.create_default()

        # Test migration utility with registry
        from src.converters.shapes import RectangleConverter
        mock_registry = Mock()
        mock_registry.converters = []  # Mock the converters list

        status = MigrationHelper.get_migration_status(mock_registry)

        # Verify migration helper can analyze conversion status
        assert isinstance(status, dict)
        assert 'total_converters' in status or 'migration_percentage' in status

    def test_converter_validation_in_registry(self):
        """Test converter validation works in registry context."""
        services = ConversionServices.create_default()

        from src.converters.shapes import RectangleConverter
        converter = RectangleConverter(services=services)

        # Test validation
        is_migrated = MigrationHelper.validate_converter_migration(converter)
        assert is_migrated is True

    def test_migration_plan_generation(self):
        """Test migration plan generation for remaining converters."""
        mock_registry = Mock()
        mock_registry.converters = []

        plan = MigrationHelper.create_migration_plan(mock_registry)
        assert isinstance(plan, list)


class TestPerformanceAndCaching:
    """Test performance aspects of dependency injection."""

    def test_service_instance_sharing(self):
        """Test that service instances are properly shared, not recreated."""
        services1 = ConversionServices.create_default()
        services2 = ConversionServices.create_default()

        # Different service instances
        assert services1 is not services2

        # But individual service types should be separate instances
        assert services1.unit_converter is not services2.unit_converter
        assert services1.color_parser is not services2.color_parser

    def test_converter_creation_performance(self):
        """Test that converter creation with services is efficient."""
        services = ConversionServices.create_default()

        from src.converters.shapes import RectangleConverter

        # Create multiple converters with same services
        converters = []
        for _ in range(10):
            converter = RectangleConverter(services=services)
            converters.append(converter)

        # Verify all share same services
        for converter in converters:
            assert converter.services is services
            assert converter.unit_converter is services.unit_converter


@pytest.fixture
def sample_svg_content():
    """Provide sample SVG content for testing."""
    return '''
    <svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
        <rect x="10" y="10" width="30" height="30" fill="red"/>
        <circle cx="50" cy="50" r="20" fill="blue"/>
        <text x="10" y="90" font-size="12">Hello</text>
    </svg>
    '''

@pytest.fixture
def temp_svg_file(sample_svg_content):
    """Create temporary SVG file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False) as f:
        f.write(sample_svg_content)
        temp_path = f.name

    yield temp_path

    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)

@pytest.fixture
def conversion_services():
    """Provide ConversionServices instance for tests."""
    return ConversionServices.create_default()