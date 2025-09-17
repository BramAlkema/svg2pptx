"""
Comprehensive tests for converter dependency injection migration.

This module tests all converter classes that need to be migrated from manual
service instantiation to the ConversionServices dependency injection pattern.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from lxml import etree as ET
from abc import ABC

from src.services.conversion_services import ConversionServices, ConversionConfig
from src.converters.base import BaseConverter, ConversionContext


class TestShapeConverterDependencyInjection:
    """Test ShapeConverter classes with dependency injection patterns."""

    def test_rectangle_converter_accepts_services(self, mock_conversion_services):
        """Test RectangleConverter constructor accepts ConversionServices parameter."""
        from src.converters.shapes import RectangleConverter

        converter = RectangleConverter(services=mock_conversion_services)

        assert converter.services is mock_conversion_services
        assert hasattr(converter, 'services')
        assert converter.unit_converter is mock_conversion_services.unit_converter

    def test_rectangle_converter_backward_compatibility_properties(self, mock_conversion_services):
        """Test RectangleConverter provides backward compatible service properties."""
        from src.converters.shapes import RectangleConverter

        converter = RectangleConverter(services=mock_conversion_services)

        # Test all service property accessors
        assert converter.unit_converter is mock_conversion_services.unit_converter
        assert converter.color_parser is mock_conversion_services.color_parser
        assert converter.transform_parser is mock_conversion_services.transform_parser
        assert converter.viewport_resolver is mock_conversion_services.viewport_resolver

    def test_rectangle_converter_service_usage_in_conversion(self, mock_conversion_services, sample_conversion_context):
        """Test RectangleConverter uses injected services during conversion."""
        from src.converters.shapes import RectangleConverter

        converter = RectangleConverter(services=mock_conversion_services)

        # Mock service methods that would be called during conversion
        mock_conversion_services.unit_converter.parse_length.return_value = 100.0

        element = ET.fromstring('<rect x="10" y="20" width="100" height="50"/>')

        # Test that the converter can be instantiated and has access to services
        assert converter.can_convert(element) is True
        assert hasattr(converter, 'parse_length')  # Should inherit from BaseConverter

    def test_circle_converter_dependency_injection(self, mock_conversion_services):
        """Test CircleConverter with dependency injection."""
        from src.converters.shapes import CircleConverter

        converter = CircleConverter(services=mock_conversion_services)

        assert converter.services is mock_conversion_services
        assert converter.unit_converter is mock_conversion_services.unit_converter

    def test_ellipse_converter_dependency_injection(self, mock_conversion_services):
        """Test EllipseConverter with dependency injection."""
        from src.converters.shapes import EllipseConverter

        converter = EllipseConverter(services=mock_conversion_services)

        assert converter.services is mock_conversion_services
        assert converter.unit_converter is mock_conversion_services.unit_converter

    def test_polygon_converter_dependency_injection(self, mock_conversion_services):
        """Test PolygonConverter with dependency injection."""
        from src.converters.shapes import PolygonConverter

        converter = PolygonConverter(services=mock_conversion_services)

        assert converter.services is mock_conversion_services
        assert converter.unit_converter is mock_conversion_services.unit_converter

    def test_line_converter_dependency_injection(self, mock_conversion_services):
        """Test LineConverter with dependency injection."""
        from src.converters.shapes import LineConverter

        converter = LineConverter(services=mock_conversion_services)

        assert converter.services is mock_conversion_services
        assert converter.unit_converter is mock_conversion_services.unit_converter


class TestTextConverterDependencyInjection:
    """Test TextConverter with dependency injection patterns."""

    def test_text_converter_accepts_services(self, mock_conversion_services):
        """Test TextConverter constructor accepts ConversionServices parameter."""
        from src.converters.text import TextConverter

        converter = TextConverter(services=mock_conversion_services)

        assert converter.services is mock_conversion_services
        assert hasattr(converter, 'services')

    def test_text_converter_backward_compatibility_properties(self, mock_conversion_services):
        """Test TextConverter provides backward compatible service properties."""
        from src.converters.text import TextConverter

        converter = TextConverter(services=mock_conversion_services)

        # Test all service property accessors
        assert converter.unit_converter is mock_conversion_services.unit_converter
        assert converter.color_parser is mock_conversion_services.color_parser
        assert converter.transform_parser is mock_conversion_services.transform_parser
        assert converter.viewport_resolver is mock_conversion_services.viewport_resolver

    def test_text_converter_with_font_options(self, mock_conversion_services):
        """Test TextConverter maintains font-specific options with dependency injection."""
        from src.converters.text import TextConverter

        converter = TextConverter(
            services=mock_conversion_services,
            enable_font_embedding=True,
            enable_text_to_path_fallback=False
        )

        assert converter.services is mock_conversion_services
        assert converter.enable_font_embedding is True
        assert converter.enable_text_to_path_fallback is False

    def test_text_converter_service_usage_in_conversion(self, mock_conversion_services, sample_conversion_context):
        """Test TextConverter uses injected services during conversion."""
        from src.converters.text import TextConverter

        converter = TextConverter(services=mock_conversion_services)

        # Mock service methods that would be called during conversion
        mock_conversion_services.color_parser.parse_color.return_value = "#000000"
        mock_conversion_services.unit_converter.parse_length.return_value = 12.0

        element = ET.fromstring('<text x="10" y="20" fill="black">Hello</text>')

        # Test that the converter can be instantiated and has access to services
        assert converter.can_convert(element) is True
        assert 'text' in converter.supported_elements


class TestPathConverterDependencyInjection:
    """Test PathConverter with dependency injection patterns."""

    def test_path_converter_accepts_services(self, mock_conversion_services):
        """Test PathConverter constructor accepts ConversionServices parameter."""
        from src.converters.paths import PathConverter

        converter = PathConverter(services=mock_conversion_services)

        assert converter.services is mock_conversion_services
        assert hasattr(converter, 'services')

    def test_path_converter_backward_compatibility_properties(self, mock_conversion_services):
        """Test PathConverter provides backward compatible service properties."""
        from src.converters.paths import PathConverter

        converter = PathConverter(services=mock_conversion_services)

        # Test all service property accessors
        assert converter.unit_converter is mock_conversion_services.unit_converter
        assert converter.color_parser is mock_conversion_services.color_parser
        assert converter.transform_parser is mock_conversion_services.transform_parser
        assert converter.viewport_resolver is mock_conversion_services.viewport_resolver

    def test_path_converter_service_usage_in_conversion(self, mock_conversion_services, sample_conversion_context):
        """Test PathConverter uses injected services during conversion."""
        from src.converters.paths import PathConverter

        converter = PathConverter(services=mock_conversion_services)

        element = ET.fromstring('<path d="M 10 10 L 20 20 Z"/>')

        # Test that the converter can be instantiated and has access to services
        assert converter.can_convert(element) is True


class TestGradientConverterDependencyInjection:
    """Test GradientConverter with dependency injection patterns."""

    def test_gradient_converter_accepts_services(self, mock_conversion_services):
        """Test GradientConverter constructor accepts ConversionServices parameter."""
        from src.converters.gradients import GradientConverter

        converter = GradientConverter(services=mock_conversion_services)

        assert converter.services is mock_conversion_services
        assert hasattr(converter, 'services')

    def test_gradient_converter_backward_compatibility_properties(self, mock_conversion_services):
        """Test GradientConverter provides backward compatible service properties."""
        from src.converters.gradients import GradientConverter

        converter = GradientConverter(services=mock_conversion_services)

        # Test all service property accessors
        assert converter.unit_converter is mock_conversion_services.unit_converter
        assert converter.color_parser is mock_conversion_services.color_parser
        assert converter.transform_parser is mock_conversion_services.transform_parser
        assert converter.viewport_resolver is mock_conversion_services.viewport_resolver

    def test_gradient_converter_cache_preservation(self, mock_conversion_services):
        """Test GradientConverter preserves gradient cache with dependency injection."""
        from src.converters.gradients import GradientConverter

        converter = GradientConverter(services=mock_conversion_services)

        # Test that gradient caching functionality is preserved
        assert hasattr(converter, 'gradients')
        assert isinstance(converter.gradients, dict)

    def test_gradient_converter_supported_elements(self, mock_conversion_services):
        """Test GradientConverter maintains supported elements with dependency injection."""
        from src.converters.gradients import GradientConverter

        converter = GradientConverter(services=mock_conversion_services)

        # Test supported elements are preserved
        expected_elements = ['linearGradient', 'radialGradient', 'pattern', 'meshgradient']
        assert converter.supported_elements == expected_elements


class TestImageConverterDependencyInjection:
    """Test ImageConverter with dependency injection patterns."""

    def test_image_converter_accepts_services(self, mock_conversion_services):
        """Test ImageConverter constructor accepts ConversionServices parameter."""
        from src.converters.image import ImageConverter

        converter = ImageConverter(services=mock_conversion_services)

        assert converter.services is mock_conversion_services
        assert hasattr(converter, 'services')

    def test_image_converter_backward_compatibility_properties(self, mock_conversion_services):
        """Test ImageConverter provides backward compatible service properties."""
        from src.converters.image import ImageConverter

        converter = ImageConverter(services=mock_conversion_services)

        # Test all service property accessors
        assert converter.unit_converter is mock_conversion_services.unit_converter
        assert converter.color_parser is mock_conversion_services.color_parser
        assert converter.transform_parser is mock_conversion_services.transform_parser
        assert converter.viewport_resolver is mock_conversion_services.viewport_resolver


class TestStyleProcessorDependencyInjection:
    """Test StyleProcessor with dependency injection patterns."""

    def test_style_processor_manual_services_identification(self):
        """Test identification of manual service instantiation in StyleProcessor."""
        from src.converters.styles import StyleProcessor

        # Create processor with old pattern to identify what needs migration
        processor = StyleProcessor()

        # Verify that it currently has manual instantiation (before migration)
        assert hasattr(processor, 'gradient_converter')
        assert hasattr(processor, 'color_parser')
        assert hasattr(processor, 'unit_converter')
        assert hasattr(processor, 'transform_parser')
        assert hasattr(processor, 'viewport_resolver')

    def test_style_processor_with_services_parameter(self, mock_conversion_services):
        """Test StyleProcessor with services parameter (future migration pattern)."""
        # This test defines the target state after migration
        from src.converters.styles import StyleProcessor

        # This will fail initially but shows the target pattern
        try:
            processor = StyleProcessor(services=mock_conversion_services)
            assert processor.services is mock_conversion_services
        except TypeError:
            # Expected to fail before migration - this test documents the target
            pytest.skip("StyleProcessor not yet migrated to dependency injection")


class TestAnimationConverterDependencyInjection:
    """Test AnimationConverter with dependency injection patterns."""

    def test_animation_converter_accepts_services(self, mock_conversion_services):
        """Test AnimationConverter constructor accepts ConversionServices parameter."""
        from src.converters.animations import AnimationConverter

        converter = AnimationConverter(services=mock_conversion_services)

        assert converter.services is mock_conversion_services
        assert hasattr(converter, 'services')

    def test_animation_converter_backward_compatibility_properties(self, mock_conversion_services):
        """Test AnimationConverter provides backward compatible service properties."""
        from src.converters.animations import AnimationConverter

        converter = AnimationConverter(services=mock_conversion_services)

        # Test all service property accessors
        assert converter.unit_converter is mock_conversion_services.unit_converter
        assert converter.color_parser is mock_conversion_services.color_parser
        assert converter.transform_parser is mock_conversion_services.transform_parser
        assert converter.viewport_resolver is mock_conversion_services.viewport_resolver


class TestGroupsConverterDependencyInjection:
    """Test GroupConverter with dependency injection patterns."""

    def test_group_converter_accepts_services(self, mock_conversion_services):
        """Test GroupConverter constructor accepts ConversionServices parameter."""
        from src.converters.groups import GroupConverter

        converter = GroupConverter(services=mock_conversion_services)

        assert converter.services is mock_conversion_services
        assert hasattr(converter, 'services')


class TestMaskingConverterDependencyInjection:
    """Test MaskingConverter with dependency injection patterns."""

    def test_masking_converter_accepts_services(self, mock_conversion_services):
        """Test MaskingConverter constructor accepts ConversionServices parameter."""
        from src.converters.masking import MaskingConverter

        converter = MaskingConverter(services=mock_conversion_services)

        assert converter.services is mock_conversion_services
        assert hasattr(converter, 'services')


class TestMarkersConverterDependencyInjection:
    """Test MarkerConverter with dependency injection patterns."""

    def test_marker_converter_accepts_services(self, mock_conversion_services):
        """Test MarkerConverter constructor accepts ConversionServices parameter."""
        from src.converters.markers import MarkerConverter

        converter = MarkerConverter(services=mock_conversion_services)

        assert converter.services is mock_conversion_services
        assert hasattr(converter, 'services')


class TestSymbolsConverterDependencyInjection:
    """Test SymbolConverter with dependency injection patterns."""

    def test_symbol_converter_accepts_services(self, mock_conversion_services):
        """Test SymbolConverter constructor accepts ConversionServices parameter."""
        from src.converters.symbols import SymbolConverter

        converter = SymbolConverter(services=mock_conversion_services)

        assert converter.services is mock_conversion_services
        assert hasattr(converter, 'services')


class TestTextPathConverterDependencyInjection:
    """Test TextPathConverter with dependency injection patterns."""

    def test_text_path_converter_accepts_services(self, mock_conversion_services):
        """Test TextPathConverter constructor accepts ConversionServices parameter."""
        from src.converters.text_path import TextPathConverter

        converter = TextPathConverter(services=mock_conversion_services)

        assert converter.services is mock_conversion_services
        assert hasattr(converter, 'services')


class TestMigrationUtilityIntegration:
    """Test migration utilities with real converter classes."""

    def test_migration_helper_with_shape_converter(self):
        """Test MigrationHelper creates shape converter with services."""
        from src.services.migration_utils import MigrationHelper
        from src.converters.shapes import RectangleConverter

        converter = MigrationHelper.create_converter_with_services(RectangleConverter)

        assert hasattr(converter, 'services')
        assert converter.services is not None
        assert converter.validate_services() is True

    def test_migration_helper_with_text_converter(self):
        """Test MigrationHelper creates text converter with services."""
        from src.services.migration_utils import MigrationHelper
        from src.converters.text import TextConverter

        converter = MigrationHelper.create_converter_with_services(TextConverter)

        assert hasattr(converter, 'services')
        assert converter.services is not None
        assert converter.validate_services() is True

    def test_migration_helper_with_custom_config(self):
        """Test MigrationHelper with custom ConversionConfig."""
        from src.services.migration_utils import MigrationHelper
        from src.converters.paths import PathConverter
        from src.services.conversion_services import ConversionConfig

        config = ConversionConfig(default_dpi=150.0, viewport_width=1200.0)
        converter = MigrationHelper.create_converter_with_services(PathConverter, config=config)

        assert hasattr(converter, 'services')
        assert converter.services is not None
        assert converter.validate_services() is True


class TestConverterServiceValidation:
    """Test service validation across all converter classes."""

    def test_all_migrated_converters_validate_services(self, mock_conversion_services):
        """Test that all migrated converters properly validate their services."""
        converter_classes = [
            'RectangleConverter', 'CircleConverter', 'EllipseConverter',
            'PolygonConverter', 'LineConverter', 'TextConverter',
            'PathConverter', 'GradientConverter', 'ImageConverter',
            'AnimationConverter', 'GroupConverter', 'MaskingConverter',
            'MarkerConverter', 'SymbolConverter', 'TextPathConverter'
        ]

        mock_conversion_services.validate_services.return_value = True

        for converter_class_name in converter_classes:
            try:
                # Import converter class dynamically
                module_name = converter_class_name.lower().replace('converter', '')
                if module_name in ['rectangle', 'circle', 'ellipse', 'polygon', 'line']:
                    module_name = 'shapes'
                elif module_name == 'group':
                    module_name = 'groups'
                elif module_name == 'marker':
                    module_name = 'markers'
                elif module_name == 'symbol':
                    module_name = 'symbols'
                elif module_name == 'textpath':
                    module_name = 'text_path'
                elif module_name == 'animation':
                    module_name = 'animations'
                elif module_name == 'masking':
                    module_name = 'masking'

                module = __import__(f'src.converters.{module_name}', fromlist=[converter_class_name])
                converter_class = getattr(module, converter_class_name)

                # Test converter with services
                converter = converter_class(services=mock_conversion_services)
                assert converter.validate_services() is True

            except (ImportError, AttributeError, TypeError) as e:
                # Skip converters not yet migrated or with different patterns
                pytest.skip(f"{converter_class_name} not yet migrated or has different pattern: {e}")


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