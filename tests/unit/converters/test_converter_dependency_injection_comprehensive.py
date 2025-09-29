"""
Clean Comprehensive Dependency Injection Tests

Tests that all converter classes properly implement dependency injection patterns
using the ConversionServices system. Focuses on practical functionality rather
than complex integration scenarios.
"""

import pytest
from unittest.mock import Mock, MagicMock
from lxml import etree as ET

from src.services.conversion_services import ConversionServices
from src.converters.base import ConversionContext


class TestConverterDependencyInjection:
    """Test dependency injection patterns across all converters."""

    @pytest.fixture
    def mock_services(self):
        """Create comprehensive mock services."""
        services = Mock(spec=ConversionServices)
        services.unit_converter = Mock()
        services.unit_converter.to_emu = Mock(return_value=914400)
        services.unit_converter.parse_length = Mock(return_value=100.0)
        services.color_factory = Mock()
        services.transform_parser = Mock()
        services.viewport_resolver = Mock()
        services.font_service = Mock()
        services.gradient_service = Mock()
        services.pattern_service = Mock()
        services.clip_service = Mock()
        return services

    @pytest.fixture
    def context(self, mock_services):
        """Create basic conversion context."""
        context = Mock(spec=ConversionContext)
        context.services = mock_services
        context.svg_root = ET.Element("svg")

        # Mock coordinate_system for converters that need it
        context.coordinate_system = Mock()
        context.coordinate_system.svg_to_emu = Mock(return_value=(914400, 914400))

        return context

    def test_shape_converters_accept_services(self, mock_services):
        """Test that shape converters accept services parameter."""
        from src.converters.shapes import RectangleConverter, CircleConverter, EllipseConverter

        # Test each shape converter accepts services
        rect_converter = RectangleConverter(services=mock_services)
        assert rect_converter.services is mock_services

        circle_converter = CircleConverter(services=mock_services)
        assert circle_converter.services is mock_services

        ellipse_converter = EllipseConverter(services=mock_services)
        assert ellipse_converter.services is mock_services

    def test_text_converter_accepts_services(self, mock_services):
        """Test TextConverter with dependency injection."""
        from src.converters.text import TextConverter

        converter = TextConverter(services=mock_services)
        assert converter.services is mock_services
        assert hasattr(converter, 'unit_converter')

    def test_path_converter_accepts_services(self, mock_services):
        """Test PathConverter with dependency injection."""
        from src.converters.paths import PathConverter

        converter = PathConverter(services=mock_services)
        assert converter.services is mock_services
        assert hasattr(converter, 'unit_converter')

    def test_gradient_converter_accepts_services(self, mock_services):
        """Test GradientConverter with dependency injection."""
        from src.converters.gradients import GradientConverter

        converter = GradientConverter(services=mock_services)
        assert converter.services is mock_services
        assert hasattr(converter, 'gradients')

    def test_animation_converter_accepts_services(self, mock_services):
        """Test AnimationConverter with dependency injection."""
        from src.converters.animations import AnimationConverter

        converter = AnimationConverter(services=mock_services)
        assert converter.services is mock_services

    def test_service_property_access(self, mock_services):
        """Test that converters provide service property access."""
        from src.converters.shapes import RectangleConverter

        converter = RectangleConverter(services=mock_services)

        # Test property access works
        assert converter.unit_converter is mock_services.unit_converter
        # color_factory is accessed via services, not as direct property
        assert converter.transform_parser is mock_services.transform_parser
        assert converter.viewport_resolver is mock_services.viewport_resolver

    def test_converter_can_convert_basic_elements(self, mock_services):
        """Test that converters can identify their supported elements."""
        from src.converters.shapes import RectangleConverter

        converter = RectangleConverter(services=mock_services)

        # Test element recognition
        rect_element = ET.Element("rect")
        assert converter.can_convert(rect_element) is True

        circle_element = ET.Element("circle")
        assert converter.can_convert(circle_element) is False

    def test_converter_has_convert_method(self, mock_services):
        """Test that converters have convert method available."""
        from src.converters.shapes import RectangleConverter

        converter = RectangleConverter(services=mock_services)
        rect_element = ET.Element("rect")

        # Test that convert method exists and is callable
        assert hasattr(converter, 'convert')
        assert callable(converter.convert)

    def test_multiple_converter_service_isolation(self, mock_services):
        """Test that multiple converters don't interfere with services."""
        from src.converters.shapes import RectangleConverter, CircleConverter

        rect_converter = RectangleConverter(services=mock_services)
        circle_converter = CircleConverter(services=mock_services)

        # Both should have same services but be independent instances
        assert rect_converter.services is mock_services
        assert circle_converter.services is mock_services
        assert rect_converter is not circle_converter


class TestConversionServicesIntegration:
    """Test integration with actual ConversionServices."""

    def test_conversion_services_creation(self):
        """Test ConversionServices can be created."""
        services = ConversionServices.create_default()
        assert services is not None
        assert hasattr(services, 'unit_converter')
        assert hasattr(services, 'color_factory')

    def test_converter_with_real_services(self):
        """Test converter works with real ConversionServices."""
        from src.converters.shapes import RectangleConverter

        services = ConversionServices.create_default()
        converter = RectangleConverter(services=services)

        assert converter.services is services
        assert converter.unit_converter is not None

    def test_conversion_context_with_real_services(self):
        """Test ConversionContext with real services."""
        services = ConversionServices.create_default()
        svg_root = ET.Element("svg")

        context = ConversionContext(services=services, svg_root=svg_root)
        assert context.services is services
        assert context.svg_root is svg_root


class TestServiceValidation:
    """Test service validation functionality."""

    @pytest.fixture
    def mock_services(self):
        """Create mock services for validation tests."""
        services = Mock(spec=ConversionServices)
        services.unit_converter = Mock()
        services.color_factory = Mock()
        services.transform_parser = Mock()
        services.viewport_resolver = Mock()
        services.validate_services = Mock(return_value=True)
        return services

    def test_converter_validates_services(self, mock_services):
        """Test converters can validate their services."""
        from src.converters.shapes import RectangleConverter

        converter = RectangleConverter(services=mock_services)
        if hasattr(converter, 'validate_services'):
            assert converter.validate_services() is True

    def test_services_provide_required_methods(self):
        """Test that ConversionServices provides required methods."""
        services = ConversionServices.create_default()

        # Check required service components exist
        assert hasattr(services, 'unit_converter')
        assert hasattr(services, 'color_factory')
        assert hasattr(services, 'transform_parser')
        assert hasattr(services, 'viewport_resolver')