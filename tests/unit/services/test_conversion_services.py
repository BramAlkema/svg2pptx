"""
Tests for ConversionServices dependency injection container.

This module tests the ConversionServices container that centralizes dependency
injection for UnitConverter, ColorParser, TransformParser, and ViewportResolver.
"""

import pytest
from unittest.mock import Mock, patch
from dataclasses import dataclass
from typing import Optional, Dict, Any
import tempfile
import json
import os

from src.services.conversion_services import ConversionServices, ConversionConfig
from src.services.conversion_services import ServiceInitializationError


class TestConversionConfig:
    """Test ConversionConfig dataclass for service configuration."""

    def test_conversion_config_default_values(self):
        """Test ConversionConfig creates with expected default values."""
        config = ConversionConfig()

        assert config.default_dpi == 96.0
        assert config.viewport_width == 800.0
        assert config.viewport_height == 600.0
        assert config.enable_caching is True

    def test_conversion_config_custom_values(self):
        """Test ConversionConfig accepts custom values."""
        config = ConversionConfig(
            default_dpi=150.0,
            viewport_width=1920.0,
            viewport_height=1080.0,
            enable_caching=False
        )

        assert config.default_dpi == 150.0
        assert config.viewport_width == 1920.0
        assert config.viewport_height == 1080.0
        assert config.enable_caching is False

    def test_conversion_config_from_dict(self):
        """Test ConversionConfig creation from dictionary."""
        config_dict = {
            'default_dpi': 120.0,
            'viewport_width': 1024.0,
            'viewport_height': 768.0,
            'enable_caching': True
        }

        config = ConversionConfig.from_dict(config_dict)

        assert config.default_dpi == 120.0
        assert config.viewport_width == 1024.0
        assert config.viewport_height == 768.0
        assert config.enable_caching is True

    def test_conversion_config_from_dict_partial(self):
        """Test ConversionConfig from dict with partial values uses defaults."""
        config_dict = {'default_dpi': 144.0}

        config = ConversionConfig.from_dict(config_dict)

        assert config.default_dpi == 144.0
        assert config.viewport_width == 800.0  # Default
        assert config.viewport_height == 600.0  # Default
        assert config.enable_caching is True  # Default

    def test_conversion_config_from_file(self):
        """Test ConversionConfig loading from JSON file."""
        config_data = {
            'default_dpi': 200.0,
            'viewport_width': 1280.0,
            'viewport_height': 720.0,
            'enable_caching': False
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_file = f.name

        try:
            config = ConversionConfig.from_file(temp_file)

            assert config.default_dpi == 200.0
            assert config.viewport_width == 1280.0
            assert config.viewport_height == 720.0
            assert config.enable_caching is False
        finally:
            os.unlink(temp_file)

    def test_conversion_config_from_file_not_found(self):
        """Test ConversionConfig from non-existent file returns defaults."""
        config = ConversionConfig.from_file('/non/existent/file.json')

        # Should use defaults when file not found
        assert config.default_dpi == 96.0
        assert config.viewport_width == 800.0
        assert config.viewport_height == 600.0
        assert config.enable_caching is True

    def test_conversion_config_to_dict(self):
        """Test ConversionConfig serialization to dictionary."""
        config = ConversionConfig(
            default_dpi=125.0,
            viewport_width=1366.0,
            viewport_height=768.0,
            enable_caching=True
        )

        config_dict = config.to_dict()

        expected = {
            'default_dpi': 125.0,
            'viewport_width': 1366.0,
            'viewport_height': 768.0,
            'enable_caching': True
        }
        assert config_dict == expected


class TestConversionServices:
    """Test ConversionServices dependency injection container."""

    def test_conversion_services_initialization(self):
        """Test ConversionServices requires all service dependencies."""
        mock_unit_converter = Mock()
        mock_color_parser = Mock()
        mock_transform_parser = Mock()
        mock_viewport_resolver = Mock()

        services = ConversionServices(
            unit_converter=mock_unit_converter,
            color_parser=mock_color_parser,
            transform_parser=mock_transform_parser,
            viewport_resolver=mock_viewport_resolver
        )

        assert services.unit_converter is mock_unit_converter
        assert services.color_parser is mock_color_parser
        assert services.transform_parser is mock_transform_parser
        assert services.viewport_resolver is mock_viewport_resolver

    @patch('src.services.conversion_services.UnitConverter')
    @patch('src.services.conversion_services.ColorParser')
    @patch('src.services.conversion_services.TransformParser')
    @patch('src.services.conversion_services.ViewportResolver')
    def test_conversion_services_create_default(self, mock_viewport, mock_transform,
                                               mock_color, mock_unit):
        """Test ConversionServices.create_default() factory method."""
        # Setup mocks
        mock_unit_instance = Mock()
        mock_color_instance = Mock()
        mock_transform_instance = Mock()
        mock_viewport_instance = Mock()

        mock_unit.return_value = mock_unit_instance
        mock_color.return_value = mock_color_instance
        mock_transform.return_value = mock_transform_instance
        mock_viewport.return_value = mock_viewport_instance

        services = ConversionServices.create_default()

        assert services.unit_converter is mock_unit_instance
        assert services.color_parser is mock_color_instance
        assert services.transform_parser is mock_transform_instance
        assert services.viewport_resolver is mock_viewport_instance

    @patch('src.services.conversion_services.UnitConverter')
    @patch('src.services.conversion_services.ColorParser')
    @patch('src.services.conversion_services.TransformParser')
    @patch('src.services.conversion_services.ViewportResolver')
    def test_conversion_services_create_default_with_config(self, mock_viewport,
                                                           mock_transform, mock_color, mock_unit):
        """Test ConversionServices.create_default() with custom config."""
        config = ConversionConfig(default_dpi=150.0, enable_caching=False)

        services = ConversionServices.create_default(config)

        # Verify services were created with config
        mock_unit.assert_called_once_with(default_dpi=150.0)
        # ViewportResolver takes the unit_converter instance
        mock_viewport.assert_called_once()

    @patch('src.services.conversion_services.UnitConverter')
    def test_conversion_services_create_default_initialization_error(self, mock_unit):
        """Test ConversionServices handles service initialization failures."""
        mock_unit.side_effect = Exception("UnitConverter initialization failed")

        with pytest.raises(ServiceInitializationError) as exc_info:
            ConversionServices.create_default()

        assert "Failed to initialize UnitConverter" in str(exc_info.value)

    @patch('src.services.conversion_services.UnitConverter')
    @patch('src.services.conversion_services.ColorParser')
    @patch('src.services.conversion_services.TransformParser')
    @patch('src.services.conversion_services.ViewportResolver')
    def test_conversion_services_create_custom(self, mock_viewport, mock_transform,
                                              mock_color, mock_unit):
        """Test ConversionServices.create_custom() factory method."""
        custom_config = {
            'unit_converter': {'default_dpi': 200.0},
            'color_parser': {'color_space': 'sRGB'},
            'transform_parser': {'precision': 6},
            'viewport_resolver': {}
        }

        services = ConversionServices.create_custom(custom_config)

        mock_unit.assert_called_once_with(default_dpi=200.0)
        mock_color.assert_called_once_with(color_space='sRGB')
        mock_transform.assert_called_once_with(precision=6)
        # ViewportResolver takes unit_converter instance, not direct parameters
        mock_viewport.assert_called_once()

    def test_conversion_services_lifecycle_management(self):
        """Test service lifecycle with proper initialization order."""
        services = ConversionServices.create_default()

        # Test services are properly initialized and accessible
        assert hasattr(services, 'unit_converter')
        assert hasattr(services, 'color_parser')
        assert hasattr(services, 'transform_parser')
        assert hasattr(services, 'viewport_resolver')

        # Test services can be cleaned up
        services.cleanup()

        # After cleanup, services should be None
        assert services.unit_converter is None
        assert services.color_parser is None
        assert services.transform_parser is None
        assert services.viewport_resolver is None

    def test_conversion_services_singleton_behavior(self):
        """Test ConversionServices singleton pattern for default instances."""
        services1 = ConversionServices.get_default_instance()
        services2 = ConversionServices.get_default_instance()

        assert services1 is services2

    def test_conversion_services_reset_singleton(self):
        """Test ConversionServices singleton can be reset."""
        services1 = ConversionServices.get_default_instance()

        ConversionServices.reset_default_instance()

        services2 = ConversionServices.get_default_instance()

        assert services1 is not services2


class TestServiceInitializationError:
    """Test ServiceInitializationError exception."""

    def test_service_initialization_error_creation(self):
        """Test ServiceInitializationError can be created with message."""
        error = ServiceInitializationError("Test error message")

        assert str(error) == "Test error message"
        assert isinstance(error, Exception)

    def test_service_initialization_error_with_cause(self):
        """Test ServiceInitializationError with underlying cause."""
        cause = ValueError("Original error")
        error = ServiceInitializationError("Service failed", cause)

        assert str(error) == "Service failed"
        assert error.__cause__ is cause


class TestServiceMockingFixtures:
    """Test pytest fixtures for service mocking and test isolation."""

    def test_mock_services_fixture_structure(self, mock_conversion_services):
        """Test mock_conversion_services fixture provides proper structure."""
        assert hasattr(mock_conversion_services, 'unit_converter')
        assert hasattr(mock_conversion_services, 'color_parser')
        assert hasattr(mock_conversion_services, 'transform_parser')
        assert hasattr(mock_conversion_services, 'viewport_resolver')

    def test_mock_unit_converter_fixture(self, mock_unit_converter):
        """Test mock_unit_converter fixture provides expected interface."""
        # Test common methods are mocked
        result = mock_unit_converter.to_emu("10px")
        assert result is not None

        mock_unit_converter.to_emu.assert_called_once_with("10px")

    def test_mock_color_parser_fixture(self, mock_color_parser):
        """Test mock_color_parser fixture provides expected interface."""
        result = mock_color_parser.parse_color("#ff0000")
        assert result is not None

        mock_color_parser.parse_color.assert_called_once_with("#ff0000")

    def test_isolated_services_fixture(self, isolated_conversion_services):
        """Test isolated_conversion_services creates fresh instances."""
        services1 = isolated_conversion_services()
        services2 = isolated_conversion_services()

        # Each call should return a new isolated instance
        assert services1 is not services2


@pytest.fixture
def mock_conversion_services():
    """Create mock ConversionServices for testing."""
    services = Mock(spec=ConversionServices)
    services.unit_converter = Mock()
    services.color_parser = Mock()
    services.transform_parser = Mock()
    services.viewport_resolver = Mock()
    return services


@pytest.fixture
def mock_unit_converter():
    """Create mock UnitConverter for testing."""
    mock = Mock()
    mock.to_emu.return_value = 914400  # 1 inch in EMU
    mock.to_px.return_value = 96.0
    return mock


@pytest.fixture
def mock_color_parser():
    """Create mock ColorParser for testing."""
    mock = Mock()
    mock.parse_color.return_value = {
        'red': 255, 'green': 0, 'blue': 0, 'alpha': 1.0
    }
    return mock


@pytest.fixture
def mock_transform_parser():
    """Create mock TransformParser for testing."""
    mock = Mock()
    mock.parse_transform.return_value = {'matrix': [1, 0, 0, 1, 0, 0]}
    return mock


@pytest.fixture
def mock_viewport_resolver():
    """Create mock ViewportResolver for testing."""
    mock = Mock()
    mock.resolve_viewport.return_value = {'width': 800, 'height': 600}
    return mock


@pytest.fixture
def isolated_conversion_services():
    """Create isolated ConversionServices instance for testing."""
    def _create_isolated():
        return ConversionServices.create_default()
    return _create_isolated


@pytest.fixture
def sample_conversion_config():
    """Provide sample ConversionConfig for testing."""
    return ConversionConfig(
        default_dpi=150.0,
        viewport_width=1024.0,
        viewport_height=768.0,
        enable_caching=True
    )