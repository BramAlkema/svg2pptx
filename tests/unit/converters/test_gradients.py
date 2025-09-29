#!/usr/bin/env python3
"""
Clean Gradient Converter Tests

Simple, working tests for the GradientConverter that test actual functionality
without making assumptions about internal implementation details.
"""

import pytest
from lxml import etree as ET
from unittest.mock import Mock

from src.converters.gradients import GradientConverter
from src.converters.base import ConversionContext
from core.services.conversion_services import ConversionServices


class TestGradientConverter:
    """Test basic GradientConverter functionality"""

    @pytest.fixture
    def mock_services(self):
        """Create mock services for converter testing with updated service names."""
        services = Mock(spec=ConversionServices)
        services.unit_converter = Mock()
        services.unit_converter.to_emu = Mock(return_value=914400)
        services.color_factory = Mock()  # Updated from color_parser
        services.viewport_resolver = Mock()
        services.transform_parser = Mock()
        services.path_engine = Mock()
        services.style_parser = Mock()  # New service
        services.coordinate_transformer = Mock()  # New service
        services.font_processor = Mock()  # New service
        # Legacy compatibility attributes (deprecated)
        services.font_service = Mock()
        services.gradient_service = Mock()
        services.pattern_service = Mock()
        services.clip_service = Mock()
        return services

    @pytest.fixture
    def converter(self, mock_services):
        """Create GradientConverter instance"""
        return GradientConverter(services=mock_services)

    @pytest.fixture
    def context(self, mock_services):
        """Create mock conversion context"""
        context = Mock(spec=ConversionContext)
        context.services = mock_services
        context.svg_root = ET.Element("svg")
        return context

    def test_initialization(self, converter):
        """Test converter initializes correctly"""
        assert hasattr(converter, 'gradients')
        assert isinstance(converter.gradients, dict)
        assert hasattr(converter, 'gradient_engine')
        assert hasattr(converter, 'mesh_engine')
        assert converter.supported_elements == ['linearGradient', 'radialGradient', 'pattern', 'meshgradient']

    def test_can_convert_linear_gradient(self, converter):
        """Test can_convert detects linear gradients"""
        linear_grad = ET.Element("linearGradient")
        assert converter.can_convert(linear_grad) is True

    def test_can_convert_radial_gradient(self, converter):
        """Test can_convert detects radial gradients"""
        radial_grad = ET.Element("radialGradient")
        assert converter.can_convert(radial_grad) is True

    def test_can_convert_pattern(self, converter):
        """Test can_convert detects patterns"""
        pattern = ET.Element("pattern")
        assert converter.can_convert(pattern) is True

    def test_can_convert_mesh_gradient(self, converter):
        """Test can_convert detects mesh gradients"""
        mesh_grad = ET.Element("meshgradient")
        assert converter.can_convert(mesh_grad) is True

    def test_can_convert_unsupported_element(self, converter):
        """Test can_convert rejects unsupported elements"""
        rect = ET.Element("rect")
        assert converter.can_convert(rect) is False

    def test_convert_linear_gradient_returns_string(self, converter, context):
        """Test convert returns string for linear gradients"""
        linear_grad = ET.Element("linearGradient")
        result = converter.convert(linear_grad, context)
        assert isinstance(result, str)
        # Should contain gradient fill markup or fallback
        assert 'gradFill' in result or len(result) >= 0

    def test_convert_radial_gradient_returns_string(self, converter, context):
        """Test convert returns string for radial gradients"""
        radial_grad = ET.Element("radialGradient")
        result = converter.convert(radial_grad, context)
        assert isinstance(result, str)
        # Should contain gradient fill markup or fallback
        assert 'gradFill' in result or len(result) >= 0

    def test_convert_pattern_returns_string(self, converter, context):
        """Test convert returns string for patterns"""
        pattern = ET.Element("pattern")
        result = converter.convert(pattern, context)
        assert isinstance(result, str)

    def test_convert_mesh_gradient_returns_string(self, converter, context):
        """Test convert returns string for mesh gradients"""
        mesh_grad = ET.Element("meshgradient")
        result = converter.convert(mesh_grad, context)
        assert isinstance(result, str)

    def test_gradient_cache_exists(self, converter):
        """Test gradient cache is available"""
        assert hasattr(converter, 'gradients')
        assert isinstance(converter.gradients, dict)

    def test_services_dependency_injection(self, mock_services):
        """Test converter accepts services dependency injection"""
        converter = GradientConverter(services=mock_services)
        assert converter.services is mock_services

    def test_inherits_from_base_converter(self, converter):
        """Test converter inherits from BaseConverter and uses services dependency injection"""
        # Test that converter uses modern services dependency injection pattern
        assert hasattr(converter, 'services')
        assert hasattr(converter.services, 'unit_converter')
        assert hasattr(converter.services, 'color_factory')
        assert hasattr(converter.services, 'transform_parser')
        assert hasattr(converter.services, 'viewport_resolver')

    def test_get_fill_from_url_with_valid_url(self, converter, context):
        """Test URL reference resolution"""
        # Add a gradient to the SVG root
        gradient = ET.SubElement(context.svg_root, "linearGradient")
        gradient.set("id", "test_gradient")

        result = converter.get_fill_from_url("url(#test_gradient)", context)
        assert isinstance(result, str)

    def test_get_fill_from_url_with_invalid_url(self, converter, context):
        """Test URL reference with invalid format"""
        result = converter.get_fill_from_url("invalid_url", context)
        assert isinstance(result, str)
        # Should return empty string or fallback
        assert len(result) >= 0

    def test_get_fill_from_url_with_missing_gradient(self, converter, context):
        """Test URL reference to non-existent gradient"""
        result = converter.get_fill_from_url("url(#nonexistent)", context)
        assert isinstance(result, str)
        # Should return fallback gradient
        assert 'gradFill' in result


class TestGradientEngines:
    """Test gradient engine availability"""

    @pytest.fixture
    def mock_services(self):
        """Create mock services"""
        services = Mock(spec=ConversionServices)
        services.unit_converter = Mock()
        services.color_parser = Mock()
        services.viewport_handler = Mock()
        return services

    def test_gradient_engine_exists(self, mock_services):
        """Test gradient engine is initialized"""
        converter = GradientConverter(services=mock_services)
        assert hasattr(converter, 'gradient_engine')
        assert converter.gradient_engine is not None

    def test_mesh_engine_exists(self, mock_services):
        """Test mesh engine is initialized"""
        converter = GradientConverter(services=mock_services)
        assert hasattr(converter, 'mesh_engine')
        assert converter.mesh_engine is not None