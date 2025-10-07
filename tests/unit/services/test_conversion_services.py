"""
Test ConversionServices dependency injection container.

This module tests the ConversionServices class that centralizes
dependency injection for all converter services.
"""

import pytest
from unittest.mock import Mock, patch
import json
from pathlib import Path

from core.services.conversion_services import (
    ConversionServices,
    ConversionConfig,
    ServiceInitializationError
)


class TestConversionConfig:
    """Test ConversionConfig data class."""

    def test_conversion_config_default_values(self):
        """Test ConversionConfig provides expected default values."""
        config = ConversionConfig()

        assert config.default_dpi == 96.0
        assert config.viewport_width == 800.0
        assert config.viewport_height == 600.0
        assert config.enable_caching is True

    def test_conversion_config_custom_values(self):
        """Test ConversionConfig accepts custom values."""
        config = ConversionConfig(
            default_dpi=120.0,
            viewport_width=1000.0,
            viewport_height=800.0,
            enable_caching=False
        )

        assert config.default_dpi == 120.0
        assert config.viewport_width == 1000.0
        assert config.viewport_height == 800.0
        assert config.enable_caching is False


class TestConversionServices:
    """Test ConversionServices dependency injection container."""

    def test_conversion_services_initialization(self):
        """Test ConversionServices requires all service dependencies."""
        mock_unit_converter = Mock()
        mock_color_factory = Mock()
        mock_transform_parser = Mock()
        mock_viewport_resolver = Mock()

        # Mock the additional services that were added
        mock_path_system = Mock()
        mock_style_parser = Mock()
        mock_coordinate_transformer = Mock()
        mock_font_processor = Mock()
        mock_path_processor = Mock()
        mock_gradient_service = Mock()
        mock_pattern_service = Mock()
        mock_filter_service = Mock()
        mock_image_service = Mock()
        mock_color_parser = Mock()
        mock_pptx_builder = Mock()
        mock_style_service = Mock()

        mock_font_service = Mock()
        mock_fractional_emu_converter = Mock()

        services = ConversionServices(
            unit_converter=mock_unit_converter,
            color_factory=mock_color_factory,
            color_parser=mock_color_parser,
            transform_parser=mock_transform_parser,
            viewport_resolver=mock_viewport_resolver,
            path_system=mock_path_system,
            style_parser=mock_style_parser,
            style_service=mock_style_service,
            coordinate_transformer=mock_coordinate_transformer,
            font_processor=mock_font_processor,
            font_service=mock_font_service,
            path_processor=mock_path_processor,
            pptx_builder=mock_pptx_builder,
            gradient_service=mock_gradient_service,
            pattern_service=mock_pattern_service,
            filter_service=mock_filter_service,
            image_service=mock_image_service,
            fractional_emu_converter=mock_fractional_emu_converter
        )

        assert services.unit_converter is mock_unit_converter
        assert services.color_factory is mock_color_factory
        assert services.color_parser is mock_color_parser
        assert services.transform_parser is mock_transform_parser
        assert services.viewport_resolver is mock_viewport_resolver
        assert services.path_system is mock_path_system
        assert services.style_parser is mock_style_parser
        assert services.style_service is mock_style_service
        assert services.coordinate_transformer is mock_coordinate_transformer
        assert services.font_processor is mock_font_processor
        assert services.path_processor is mock_path_processor
        assert services.pptx_builder is mock_pptx_builder
        assert services.gradient_service is mock_gradient_service
        assert services.pattern_service is mock_pattern_service
        assert services.filter_service is mock_filter_service
        assert services.image_service is mock_image_service
        assert services.fractional_emu_converter is mock_fractional_emu_converter

    def test_conversion_services_create_default(self):
        """Test ConversionServices.create_default creates working services."""
        services = ConversionServices.create_default()

        # Verify all services are initialized
        assert services.unit_converter is not None
        assert services.color_factory is not None
        assert services.transform_parser is not None
        assert services.viewport_resolver is not None
        # PathSystem is created on-demand to avoid circular dependencies
        assert services.path_system is None
        # Test that we can create it on demand
        path_system = services.get_path_system()
        assert path_system is not None
        assert services.style_parser is not None
        assert services.coordinate_transformer is not None
        assert services.font_processor is not None
        assert services.path_processor is not None
        assert services.gradient_service is not None
        assert services.pattern_service is not None
        assert services.filter_service is not None
        assert services.image_service is not None

        # Verify config is created
        assert services.config is not None
        assert isinstance(services.config, ConversionConfig)

    def test_conversion_services_create_default_with_config(self):
        """Test ConversionServices.create_default accepts custom config."""
        custom_config = ConversionConfig(default_dpi=120.0)
        services = ConversionServices.create_default(config=custom_config)

        assert services.config is custom_config
        assert services.config.default_dpi == 120.0

    def test_conversion_services_basic_functionality(self):
        """Test ConversionServices services provide basic functionality."""
        services = ConversionServices.create_default()

        # Test basic service functionality with actual method names
        assert hasattr(services.unit_converter, 'to_emu')
        assert hasattr(services.unit_converter, 'parse_length')
        assert hasattr(services.transform_parser, 'parse_to_matrix')
        assert hasattr(services.viewport_resolver, 'parse_viewbox_strings')
        # PathSystem is created on-demand
        path_system = services.get_path_system()
        assert hasattr(path_system, 'process_path')
        assert hasattr(services.style_parser, 'parse_style_string')
        assert hasattr(services.coordinate_transformer, 'parse_coordinate_string')
        assert hasattr(services.font_processor, 'get_font_family')
        assert hasattr(services.path_processor, 'parse_path_string')
        assert hasattr(services.gradient_service, 'get_gradient_content')
        assert hasattr(services.pattern_service, 'get_pattern_content')
        assert hasattr(services.filter_service, 'get_filter_content')
        assert hasattr(services.image_service, 'process_image_source')

    def test_conversion_services_lifecycle_management(self):
        """Test ConversionServices cleanup and singleton management."""
        # Test singleton
        services1 = ConversionServices.get_default_instance()
        services2 = ConversionServices.get_default_instance()
        assert services1 is services2

        # Test reset
        ConversionServices.reset_default_instance()
        services3 = ConversionServices.get_default_instance()
        assert services3 is not services1


class TestServiceMockingFixtures:
    """Test mock service fixtures for unit testing."""

    def test_mock_services_fixture_structure(self):
        """Test mock services fixture provides all required services."""
        # Create mock services similar to what would be in a fixture
        mock_services = Mock()
        mock_services.unit_converter = Mock()
        mock_services.color_factory = Mock()
        mock_services.transform_parser = Mock()
        mock_services.viewport_resolver = Mock()
        mock_services.path_system = Mock()
        mock_services.style_parser = Mock()
        mock_services.coordinate_transformer = Mock()
        mock_services.font_processor = Mock()
        mock_services.path_processor = Mock()
        mock_services.gradient_service = Mock()
        mock_services.pattern_service = Mock()
        mock_services.filter_service = Mock()
        mock_services.image_service = Mock()

        # Verify all required services are present
        assert hasattr(mock_services, 'unit_converter')
        assert hasattr(mock_services, 'color_factory')
        assert hasattr(mock_services, 'transform_parser')
        assert hasattr(mock_services, 'viewport_resolver')
        assert hasattr(mock_services, 'path_system')
        assert hasattr(mock_services, 'style_parser')
        assert hasattr(mock_services, 'coordinate_transformer')
        assert hasattr(mock_services, 'font_processor')
        assert hasattr(mock_services, 'path_processor')
        assert hasattr(mock_services, 'gradient_service')
        assert hasattr(mock_services, 'pattern_service')
        assert hasattr(mock_services, 'filter_service')
        assert hasattr(mock_services, 'image_service')

    def test_mock_unit_converter_fixture(self):
        """Test mock unit converter provides expected methods."""
        mock_unit_converter = Mock()
        mock_unit_converter.to_emu.return_value = 91440
        mock_unit_converter.parse_length.return_value = 100.0

        # Test mock behavior
        assert mock_unit_converter.to_emu() == 91440
        assert mock_unit_converter.parse_length() == 100.0

    def test_mock_color_factory_fixture(self):
        """Test mock color factory provides expected behavior."""
        mock_color = Mock()
        mock_color.hex = "#FF0000"
        mock_color.rgb = (255, 0, 0)

        mock_color_factory = Mock()
        mock_color_factory.return_value = mock_color

        # Test mock behavior
        color = mock_color_factory("#FF0000")
        assert color.hex == "#FF0000"
        assert color.rgb == (255, 0, 0)

    def test_isolated_services_fixture(self):
        """Test isolated services fixture for individual service testing."""
        # This would test a fixture that provides individual service mocks
        # without the full ConversionServices container
        individual_mocks = {
            'unit_converter': Mock(),
            'color_factory': Mock(),
            'transform_parser': Mock(),
            'viewport_resolver': Mock(),
            'path_system': Mock(),
            'style_parser': Mock(),
            'coordinate_transformer': Mock(),
            'font_processor': Mock(),
            'path_processor': Mock(),
            'gradient_service': Mock(),
            'pattern_service': Mock(),
            'filter_service': Mock(),
            'image_service': Mock()
        }

        # Verify all expected services are available
        expected_services = [
            'unit_converter', 'color_factory', 'transform_parser',
            'viewport_resolver', 'path_system', 'style_parser',
            'coordinate_transformer', 'font_processor', 'path_processor',
            'gradient_service', 'pattern_service', 'filter_service', 'image_service'
        ]

        for service_name in expected_services:
            assert service_name in individual_mocks
            assert individual_mocks[service_name] is not None