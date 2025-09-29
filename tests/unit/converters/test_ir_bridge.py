#!/usr/bin/env python3
"""
Unit tests for IR Converter Bridge

Tests the bridge between existing converter system and clean slate IR architecture.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from lxml import etree as ET

from src.converters.ir_bridge import IRConverterBridge, create_ir_bridge
from src.converters.base import ConversionContext
from src.services.conversion_services import ConversionServices
from src.config.hybrid_config import HybridConversionConfig, ConversionMode


class TestIRConverterBridge:
    """Test IR Converter Bridge functionality"""

    @pytest.fixture
    def mock_services(self):
        """Create mock services for testing"""
        services = Mock(spec=ConversionServices)
        services.unit_converter = Mock()
        services.color_parser = Mock()
        services.transform_parser = Mock()
        services.viewport_resolver = Mock()
        services.path_system = Mock()
        services.style_service = Mock()
        services.gradient_service = Mock()
        services.pattern_service = Mock()
        services.filter_service = Mock()
        services.image_service = Mock()

        # Clean slate services (initially None)
        services.ir_scene_factory = None
        services.policy_engine = None
        services.mapper_registry = None
        services.drawingml_embedder = None

        return services

    @pytest.fixture
    def mock_clean_slate_services(self, mock_services):
        """Create mock services with clean slate components"""
        services = mock_services

        # Add clean slate services
        services.ir_scene_factory = Mock()
        services.policy_engine = Mock()
        services.mapper_registry = Mock()
        services.drawingml_embedder = Mock()

        return services

    @pytest.fixture
    def existing_only_config(self):
        """Configuration for existing system only"""
        return HybridConversionConfig.create_existing_only()

    @pytest.fixture
    def hybrid_config(self):
        """Configuration for hybrid mode"""
        return HybridConversionConfig.create_hybrid_paths_only()

    @pytest.fixture
    def clean_slate_config(self):
        """Configuration for clean slate only"""
        return HybridConversionConfig.create_clean_slate_only()

    @pytest.fixture
    def sample_path_element(self):
        """Create sample SVG path element"""
        element = ET.Element('path')
        element.set('d', 'M 10 10 L 20 20 Z')
        element.set('fill', '#ff0000')
        element.set('stroke', '#000000')
        return element

    @pytest.fixture
    def sample_text_element(self):
        """Create sample SVG text element"""
        element = ET.Element('text')
        element.set('x', '10')
        element.set('y', '20')
        element.set('font-family', 'Arial')
        element.set('font-size', '12')
        element.text = 'Sample Text'
        return element

    def test_initialization_existing_only(self, mock_services, existing_only_config):
        """Test initialization with existing system only"""
        bridge = IRConverterBridge(mock_services, existing_only_config)

        assert bridge.services == mock_services
        assert bridge.hybrid_config == existing_only_config
        assert bridge.supported_elements == ['*']
        assert bridge._stats['total_elements'] == 0

    def test_initialization_clean_slate_missing_services(self, mock_services, hybrid_config):
        """Test initialization fails when clean slate services are missing"""
        with pytest.raises(ValueError, match="Missing required clean slate services"):
            IRConverterBridge(mock_services, hybrid_config)

    def test_initialization_clean_slate_services_available(self, mock_clean_slate_services, hybrid_config):
        """Test initialization succeeds with clean slate services"""
        bridge = IRConverterBridge(mock_clean_slate_services, hybrid_config)

        assert bridge.services == mock_clean_slate_services
        assert bridge.hybrid_config == hybrid_config

    def test_can_convert_existing_only(self, mock_services, existing_only_config, sample_path_element):
        """Test can_convert with existing system only"""
        bridge = IRConverterBridge(mock_services, existing_only_config)

        assert bridge.can_convert(sample_path_element) is True

    def test_can_convert_hybrid_mode(self, mock_clean_slate_services, hybrid_config, sample_path_element):
        """Test can_convert in hybrid mode"""
        bridge = IRConverterBridge(mock_clean_slate_services, hybrid_config)

        # Path elements should use clean slate in hybrid_paths_only config
        assert bridge.can_convert(sample_path_element) is True

    def test_can_convert_clean_slate_mode(self, mock_clean_slate_services, clean_slate_config, sample_text_element):
        """Test can_convert in clean slate mode"""
        bridge = IRConverterBridge(mock_clean_slate_services, clean_slate_config)

        # All elements should use clean slate
        assert bridge.can_convert(sample_text_element) is True

    def test_should_use_clean_slate_existing_only(self, mock_services, existing_only_config, sample_path_element):
        """Test should_use_clean_slate with existing only config"""
        bridge = IRConverterBridge(mock_services, existing_only_config)

        assert bridge._should_use_clean_slate(sample_path_element, 'path') is False

    def test_should_use_clean_slate_hybrid_paths(self, mock_clean_slate_services, hybrid_config, sample_path_element, sample_text_element):
        """Test should_use_clean_slate in hybrid mode"""
        bridge = IRConverterBridge(mock_clean_slate_services, hybrid_config)

        # Path should use clean slate
        assert bridge._should_use_clean_slate(sample_path_element, 'path') is True

        # Text should use existing system
        assert bridge._should_use_clean_slate(sample_text_element, 'text') is False

    @patch('src.converters.ir_bridge.Path')
    def test_create_ir_path(self, mock_path_class, mock_clean_slate_services, sample_path_element):
        """Test creation of IR Path element"""
        bridge = IRConverterBridge(mock_clean_slate_services, HybridConversionConfig())

        # Mock the Path class
        mock_path_instance = Mock()
        mock_path_class.return_value = mock_path_instance

        with patch('src.converters.ir_bridge.Path', mock_path_class):
            result = bridge._create_ir_path(sample_path_element, None)

        assert result == mock_path_instance
        mock_path_class.assert_called_once()

    @patch('src.converters.ir_bridge.TextFrame')
    def test_create_ir_textframe(self, mock_textframe_class, mock_clean_slate_services, sample_text_element):
        """Test creation of IR TextFrame element"""
        bridge = IRConverterBridge(mock_clean_slate_services, HybridConversionConfig())

        # Mock the TextFrame class
        mock_textframe_instance = Mock()
        mock_textframe_class.return_value = mock_textframe_instance

        result = bridge._create_ir_textframe(sample_text_element, None)

        assert result == mock_textframe_instance
        mock_textframe_class.assert_called_once()

    def test_shape_to_path_conversion_rect(self, mock_clean_slate_services):
        """Test rectangle to path conversion"""
        bridge = IRConverterBridge(mock_clean_slate_services, HybridConversionConfig())

        rect_element = ET.Element('rect')
        rect_element.set('x', '10')
        rect_element.set('y', '20')
        rect_element.set('width', '30')
        rect_element.set('height', '40')

        path_data = bridge._rect_to_path_data(rect_element)
        expected = "M 10.0 20.0 L 40.0 20.0 L 40.0 60.0 L 10.0 60.0 Z"

        assert path_data == expected

    def test_shape_to_path_conversion_circle(self, mock_clean_slate_services):
        """Test circle to path conversion"""
        bridge = IRConverterBridge(mock_clean_slate_services, HybridConversionConfig())

        circle_element = ET.Element('circle')
        circle_element.set('cx', '50')
        circle_element.set('cy', '60')
        circle_element.set('r', '25')

        path_data = bridge._circle_to_path_data(circle_element)

        # Should contain two arc commands
        assert 'M 25.0 60.0' in path_data
        assert 'A 25.0 25.0' in path_data
        assert path_data.endswith(' Z')

    def test_shape_to_path_conversion_line(self, mock_clean_slate_services):
        """Test line to path conversion"""
        bridge = IRConverterBridge(mock_clean_slate_services, HybridConversionConfig())

        line_element = ET.Element('line')
        line_element.set('x1', '10')
        line_element.set('y1', '20')
        line_element.set('x2', '30')
        line_element.set('y2', '40')

        path_data = bridge._line_to_path_data(line_element)
        expected = "M 10.0 20.0 L 30.0 40.0"

        assert path_data == expected

    def test_extract_fill_info(self, mock_clean_slate_services, sample_path_element):
        """Test fill information extraction"""
        bridge = IRConverterBridge(mock_clean_slate_services, HybridConversionConfig())

        fill_info = bridge._extract_fill_info(sample_path_element)

        assert fill_info == {'color': '#ff0000'}

    def test_extract_fill_info_none(self, mock_clean_slate_services):
        """Test fill information extraction with no fill"""
        bridge = IRConverterBridge(mock_clean_slate_services, HybridConversionConfig())

        element = ET.Element('path')
        element.set('fill', 'none')

        fill_info = bridge._extract_fill_info(element)

        assert fill_info is None

    def test_extract_stroke_info(self, mock_clean_slate_services, sample_path_element):
        """Test stroke information extraction"""
        bridge = IRConverterBridge(mock_clean_slate_services, HybridConversionConfig())

        stroke_info = bridge._extract_stroke_info(sample_path_element)

        assert stroke_info == {'color': '#000000', 'width': 1.0}

    def test_extract_text_content(self, mock_clean_slate_services, sample_text_element):
        """Test text content extraction"""
        bridge = IRConverterBridge(mock_clean_slate_services, HybridConversionConfig())

        content = bridge._extract_text_content(sample_text_element)

        assert content == 'Sample Text'

    def test_extract_text_content_with_tspan(self, mock_clean_slate_services):
        """Test text content extraction with tspan children"""
        bridge = IRConverterBridge(mock_clean_slate_services, HybridConversionConfig())

        text_element = ET.Element('text')
        text_element.text = 'Hello '

        tspan = ET.SubElement(text_element, 'tspan')
        tspan.text = 'World'

        content = bridge._extract_text_content(text_element)

        assert content == 'Hello World'

    def test_get_statistics(self, mock_clean_slate_services, hybrid_config):
        """Test statistics retrieval"""
        bridge = IRConverterBridge(mock_clean_slate_services, hybrid_config)

        # Simulate some conversions
        bridge._stats['total_elements'] = 10
        bridge._stats['clean_slate_elements'] = 6
        bridge._stats['existing_system_elements'] = 4
        bridge._stats['conversion_failures'] = 0

        stats = bridge.get_statistics()

        assert stats['total_elements'] == 10
        assert stats['clean_slate_ratio'] == 0.6
        assert stats['existing_system_ratio'] == 0.4
        assert stats['failure_rate'] == 0.0
        assert 'hybrid_config' in stats

    def test_reset_statistics(self, mock_clean_slate_services, hybrid_config):
        """Test statistics reset"""
        bridge = IRConverterBridge(mock_clean_slate_services, hybrid_config)

        # Set some values
        bridge._stats['total_elements'] = 5
        bridge._stats['clean_slate_elements'] = 3

        # Reset
        bridge.reset_statistics()

        assert bridge._stats['total_elements'] == 0
        assert bridge._stats['clean_slate_elements'] == 0
        assert bridge._stats['existing_system_elements'] == 0
        assert bridge._stats['conversion_failures'] == 0

    def test_factory_function(self, mock_clean_slate_services, hybrid_config):
        """Test factory function for creating bridge"""
        bridge = create_ir_bridge(mock_clean_slate_services, hybrid_config)

        assert isinstance(bridge, IRConverterBridge)
        assert bridge.services == mock_clean_slate_services
        assert bridge.hybrid_config == hybrid_config

    def test_factory_function_default_config(self, mock_services):
        """Test factory function with default configuration"""
        bridge = create_ir_bridge(mock_services)

        assert isinstance(bridge, IRConverterBridge)
        assert bridge.services == mock_services
        assert bridge.hybrid_config.conversion_mode == ConversionMode.EXISTING_ONLY


class TestIRBridgeIntegration:
    """Integration tests for IR Bridge with real components"""

    @pytest.fixture
    def real_services(self):
        """Create real ConversionServices for integration testing"""
        return ConversionServices.create_default()

    def test_bridge_with_real_services_existing_mode(self, real_services):
        """Test bridge with real services in existing mode"""
        config = HybridConversionConfig.create_existing_only()
        bridge = IRConverterBridge(real_services, config)

        # Should work without clean slate services
        path_element = ET.Element('path')
        path_element.set('d', 'M 0 0 L 10 10')

        assert bridge.can_convert(path_element) is True
        assert bridge._should_use_clean_slate(path_element, 'path') is False

    def test_bridge_validates_missing_clean_slate_services(self, real_services):
        """Test bridge validation with missing clean slate services"""
        config = HybridConversionConfig.create_hybrid_paths_only()

        # Should fail because real_services doesn't have clean slate components
        with pytest.raises(ValueError, match="Missing required clean slate services"):
            IRConverterBridge(real_services, config)

    def test_bridge_graceful_fallback_on_clean_slate_import_error(self, real_services):
        """Test bridge handles clean slate import errors gracefully"""
        config = HybridConversionConfig.create_existing_only()
        bridge = IRConverterBridge(real_services, config)

        # Even with missing clean slate modules, should work in existing mode
        assert bridge._has_clean_slate_support() is False
        assert bridge._requires_clean_slate() is False


class TestHybridConfigurationValidation:
    """Test hybrid configuration validation"""

    def test_existing_only_config_properties(self):
        """Test existing only configuration properties"""
        config = HybridConversionConfig.create_existing_only()

        assert config.conversion_mode == ConversionMode.EXISTING_ONLY
        assert config.clean_slate_elements == []
        assert config.feature_flags.use_clean_slate_paths is False
        assert config.feature_flags.use_existing_path_system is True

    def test_clean_slate_only_config_properties(self):
        """Test clean slate only configuration properties"""
        config = HybridConversionConfig.create_clean_slate_only()

        assert config.conversion_mode == ConversionMode.CLEAN_SLATE_ONLY
        assert 'path' in config.clean_slate_elements
        assert 'text' in config.clean_slate_elements
        assert config.feature_flags.use_clean_slate_paths is True

    def test_hybrid_paths_only_config_properties(self):
        """Test hybrid paths only configuration properties"""
        config = HybridConversionConfig.create_hybrid_paths_only()

        assert config.conversion_mode == ConversionMode.HYBRID
        assert config.clean_slate_elements == ['path']
        assert config.feature_flags.use_clean_slate_paths is True
        assert config.feature_flags.use_clean_slate_text is False

    def test_should_use_clean_slate_for_element(self):
        """Test element-specific clean slate decisions"""
        config = HybridConversionConfig.create_hybrid_paths_only()

        assert config.should_use_clean_slate_for_element('path') is True
        assert config.should_use_clean_slate_for_element('text') is False
        assert config.should_use_clean_slate_for_element('rect') is False

    def test_config_serialization(self):
        """Test configuration serialization and deserialization"""
        config = HybridConversionConfig.create_full_hybrid()
        config_dict = config.to_dict()

        # Should contain all major sections
        assert 'conversion_mode' in config_dict
        assert 'policy_thresholds' in config_dict
        assert 'feature_flags' in config_dict
        assert 'performance_config' in config_dict

        # Test deserialization
        restored_config = HybridConversionConfig.from_dict(config_dict)
        assert restored_config.conversion_mode == config.conversion_mode
        assert restored_config.clean_slate_elements == config.clean_slate_elements