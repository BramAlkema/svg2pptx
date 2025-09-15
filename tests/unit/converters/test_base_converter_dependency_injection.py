"""
Tests for BaseConverter dependency injection refactoring.

This module tests the refactored BaseConverter that uses ConversionServices
dependency injection instead of manual service instantiation.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from abc import ABC
from lxml import etree as ET

from src.services.conversion_services import ConversionServices, ConversionConfig
from src.converters.base import BaseConverter, ConversionContext


class TestBaseConverterDependencyInjection:
    """Test BaseConverter with dependency injection patterns."""

    def test_base_converter_accepts_conversion_services(self, mock_conversion_services):
        """Test BaseConverter constructor accepts ConversionServices parameter."""
        # Create a concrete implementation for testing
        class TestConverter(BaseConverter):
            def can_convert(self, element):
                return True

            def convert(self, element, context):
                return "<test/>"

        converter = TestConverter(services=mock_conversion_services)

        assert converter.services is mock_conversion_services
        assert hasattr(converter, 'services')

    def test_base_converter_backward_compatibility_unit_converter(self, mock_conversion_services):
        """Test BaseConverter provides backward compatible unit_converter property."""
        class TestConverter(BaseConverter):
            def can_convert(self, element):
                return True

            def convert(self, element, context):
                return "<test/>"

        converter = TestConverter(services=mock_conversion_services)

        # Test property accessor
        unit_converter = converter.unit_converter
        assert unit_converter is mock_conversion_services.unit_converter

    def test_base_converter_backward_compatibility_color_parser(self, mock_conversion_services):
        """Test BaseConverter provides backward compatible color_parser property."""
        class TestConverter(BaseConverter):
            def can_convert(self, element):
                return True

            def convert(self, element, context):
                return "<test/>"

        converter = TestConverter(services=mock_conversion_services)

        # Test property accessor
        color_parser = converter.color_parser
        assert color_parser is mock_conversion_services.color_parser

    def test_base_converter_backward_compatibility_transform_parser(self, mock_conversion_services):
        """Test BaseConverter provides backward compatible transform_parser property."""
        class TestConverter(BaseConverter):
            def can_convert(self, element):
                return True

            def convert(self, element, context):
                return "<test/>"

        converter = TestConverter(services=mock_conversion_services)

        # Test property accessor
        transform_parser = converter.transform_parser
        assert transform_parser is mock_conversion_services.transform_parser

    def test_base_converter_backward_compatibility_viewport_resolver(self, mock_conversion_services):
        """Test BaseConverter provides backward compatible viewport_resolver property."""
        class TestConverter(BaseConverter):
            def can_convert(self, element):
                return True

            def convert(self, element, context):
                return "<test/>"

        converter = TestConverter(services=mock_conversion_services)

        # Test property accessor
        viewport_resolver = converter.viewport_resolver
        assert viewport_resolver is mock_conversion_services.viewport_resolver

    def test_base_converter_services_required(self):
        """Test BaseConverter requires services parameter."""
        class TestConverter(BaseConverter):
            def can_convert(self, element):
                return True

            def convert(self, element, context):
                return "<test/>"

        # Should raise TypeError when services not provided
        with pytest.raises(TypeError):
            TestConverter()

    def test_base_converter_legacy_constructor_support(self, mock_conversion_services):
        """Test BaseConverter supports legacy constructor pattern during migration."""
        class TestConverter(BaseConverter):
            def can_convert(self, element):
                return True

            def convert(self, element, context):
                return "<test/>"

        # Test new pattern (preferred)
        converter_new = TestConverter(services=mock_conversion_services)
        assert converter_new.services is mock_conversion_services

        # Test legacy pattern (with migration utility)
        converter_legacy = TestConverter.create_with_default_services()
        assert hasattr(converter_legacy, 'services')
        assert converter_legacy.services is not None

    def test_base_converter_service_validation(self, mock_conversion_services):
        """Test BaseConverter validates service availability."""
        class TestConverter(BaseConverter):
            def can_convert(self, element):
                return True

            def convert(self, element, context):
                return "<test/>"

        converter = TestConverter(services=mock_conversion_services)

        # Mock validate_services method
        mock_conversion_services.validate_services.return_value = True

        assert converter.validate_services() is True
        mock_conversion_services.validate_services.assert_called_once()

    def test_base_converter_type_hints(self, mock_conversion_services):
        """Test BaseConverter has proper type hints for services."""
        class TestConverter(BaseConverter):
            def can_convert(self, element):
                return True

            def convert(self, element, context):
                return "<test/>"

        converter = TestConverter(services=mock_conversion_services)

        # Check type annotations exist
        annotations = TestConverter.__init__.__annotations__
        assert 'services' in annotations
        assert annotations['services'] == ConversionServices


class TestConverterRegistryDependencyInjection:
    """Test ConverterRegistry with service injection support."""

    def test_converter_registry_injects_services(self, mock_conversion_services):
        """Test ConverterRegistry injects services during converter instantiation."""
        from src.converters.base import ConverterRegistry

        class TestConverter(BaseConverter):
            supported_elements = ['test']

            def can_convert(self, element):
                return element.tag == 'test'

            def convert(self, element, context):
                return "<test/>"

        registry = ConverterRegistry(services=mock_conversion_services)
        registry.register_class(TestConverter)

        # Test service injection during converter creation
        element = ET.fromstring('<test/>')
        converter = registry.get_converter(element)

        assert converter is not None
        assert hasattr(converter, 'services')
        assert converter.services is mock_conversion_services

    def test_converter_registry_backward_compatibility(self):
        """Test ConverterRegistry maintains backward compatibility."""
        from src.converters.base import ConverterRegistry

        # Test legacy registry creation (should use default services)
        registry = ConverterRegistry.create_with_default_services()

        assert hasattr(registry, 'services')
        assert registry.services is not None

    def test_converter_registry_service_propagation(self, mock_conversion_services):
        """Test ConverterRegistry propagates services to all converters."""
        from src.converters.base import ConverterRegistry

        class TestConverter1(BaseConverter):
            supported_elements = ['test1']

            def can_convert(self, element):
                return element.tag == 'test1'

            def convert(self, element, context):
                return "<test1/>"

        class TestConverter2(BaseConverter):
            supported_elements = ['test2']

            def can_convert(self, element):
                return element.tag == 'test2'

            def convert(self, element, context):
                return "<test2/>"

        registry = ConverterRegistry(services=mock_conversion_services)
        registry.register_class(TestConverter1)
        registry.register_class(TestConverter2)

        # Both converters should receive the same services
        element1 = ET.fromstring('<test1/>')
        element2 = ET.fromstring('<test2/>')
        converter1 = registry.get_converter(element1)
        converter2 = registry.get_converter(element2)

        assert converter1.services is mock_conversion_services
        assert converter2.services is mock_conversion_services
        assert converter1.services is converter2.services


class TestMigrationUtilities:
    """Test migration utilities for gradual converter transition."""

    def test_create_with_default_services_utility(self):
        """Test create_with_default_services migration utility."""
        class TestConverter(BaseConverter):
            def can_convert(self, element):
                return True

            def convert(self, element, context):
                return "<test/>"

        # Test migration utility
        converter = TestConverter.create_with_default_services()

        assert hasattr(converter, 'services')
        assert converter.services is not None
        assert hasattr(converter.services, 'unit_converter')
        assert hasattr(converter.services, 'color_parser')
        assert hasattr(converter.services, 'transform_parser')
        assert hasattr(converter.services, 'viewport_resolver')

    def test_migration_config_override(self):
        """Test migration utility with custom configuration."""
        class TestConverter(BaseConverter):
            def can_convert(self, element):
                return True

            def convert(self, element, context):
                return "<test/>"

        config = ConversionConfig(default_dpi=150.0, viewport_width=1200.0)
        converter = TestConverter.create_with_default_services(config)

        assert converter.services is not None
        # Services should be created with custom config (verified through integration)

    def test_migration_warning_deprecated_pattern(self, mock_conversion_services):
        """Test migration utility warns about deprecated usage patterns."""
        class TestConverter(BaseConverter):
            def can_convert(self, element):
                return True

            def convert(self, element, context):
                return "<test/>"

        # Test that using the deprecated migration utility shows warning
        from src.services.migration_utils import MigrationHelper

        with pytest.warns(UserWarning, match="Manual service instantiation is deprecated"):
            converter = MigrationHelper.create_legacy_converter(TestConverter)

    def test_converter_compatibility_mode(self, mock_conversion_services):
        """Test converter compatibility mode during migration."""
        class TestConverter(BaseConverter):
            def can_convert(self, element):
                return True

            def convert(self, element, context):
                # Use both old and new patterns
                dpi = self.unit_converter.default_dpi
                color = self.color_parser.parse_color("#ff0000")
                return f"<test dpi='{dpi}' color='{color}'/>"

        converter = TestConverter(services=mock_conversion_services)

        # Mock the services
        mock_conversion_services.unit_converter.default_dpi = 96.0
        mock_conversion_services.color_parser.parse_color.return_value = "red"

        element = ET.fromstring('<test/>')
        context = Mock()

        result = converter.convert(element, context)

        assert "dpi='96.0'" in result
        assert "color='red'" in result
        mock_conversion_services.color_parser.parse_color.assert_called_once_with("#ff0000")


class TestBaseConverterIntegration:
    """Test BaseConverter integration with existing converter classes."""

    def test_shape_converter_compatibility(self, mock_conversion_services):
        """Test BaseConverter changes don't break ShapeConverter."""
        # Import actual converter to test compatibility
        try:
            from src.converters.shapes import ShapeConverter

            # Should be able to create with services
            converter = ShapeConverter(services=mock_conversion_services)
            assert hasattr(converter, 'services')
            assert converter.unit_converter is mock_conversion_services.unit_converter

        except ImportError:
            # If ShapeConverter doesn't exist, test with mock
            class MockShapeConverter(BaseConverter):
                def can_convert(self, element):
                    return element.tag in ['rect', 'circle', 'ellipse']

                def convert(self, element, context):
                    width = self.unit_converter.to_emu("10px")
                    return f"<shape width='{width}'/>"

            converter = MockShapeConverter(services=mock_conversion_services)
            mock_conversion_services.unit_converter.to_emu.return_value = 914400

            element = ET.fromstring('<rect/>')
            context = Mock()
            result = converter.convert(element, context)

            assert "width='914400'" in result

    def test_text_converter_compatibility(self, mock_conversion_services):
        """Test BaseConverter changes don't break TextConverter."""
        class MockTextConverter(BaseConverter):
            def can_convert(self, element):
                return element.tag == 'text'

            def convert(self, element, context):
                color = self.color_parser.parse_color("#000000")
                return f"<text color='{color}'/>"

        converter = MockTextConverter(services=mock_conversion_services)
        mock_conversion_services.color_parser.parse_color.return_value = "black"

        element = ET.fromstring('<text/>')
        context = Mock()
        result = converter.convert(element, context)

        assert "color='black'" in result
        mock_conversion_services.color_parser.parse_color.assert_called_once_with("#000000")

    def test_path_converter_compatibility(self, mock_conversion_services):
        """Test BaseConverter changes don't break PathConverter."""
        class MockPathConverter(BaseConverter):
            def can_convert(self, element):
                return element.tag == 'path'

            def convert(self, element, context):
                transform = self.transform_parser.parse_transform("translate(10,20)")
                return f"<path transform='{transform}'/>"

        converter = MockPathConverter(services=mock_conversion_services)
        mock_conversion_services.transform_parser.parse_transform.return_value = {'tx': 10, 'ty': 20}

        element = ET.fromstring('<path/>')
        context = Mock()
        result = converter.convert(element, context)

        assert "transform=" in result
        mock_conversion_services.transform_parser.parse_transform.assert_called_once_with("translate(10,20)")


@pytest.fixture
def mock_conversion_services():
    """Create mock ConversionServices for testing."""
    services = Mock(spec=ConversionServices)
    services.unit_converter = Mock()
    services.color_parser = Mock()
    services.transform_parser = Mock()
    services.viewport_resolver = Mock()
    services.validate_services = Mock(return_value=True)
    return services


@pytest.fixture
def sample_conversion_context():
    """Provide sample ConversionContext for testing."""
    context = Mock(spec=ConversionContext)
    context.coordinate_system = Mock()
    context.styles = {}
    context.filters = {}
    return context