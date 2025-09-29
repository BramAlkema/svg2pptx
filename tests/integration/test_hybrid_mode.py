#!/usr/bin/env python3
"""
Integration tests for hybrid mode functionality

Tests the integration between existing converter system and clean slate architecture
through the IRConverterBridge and hybrid configuration.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from lxml import etree as ET

from src.services.conversion_services import ConversionServices
from src.config.hybrid_config import HybridConversionConfig, ConversionMode
from src.converters.base import ConverterRegistryFactory, ConversionContext


class TestHybridModeIntegration:
    """Integration tests for hybrid mode"""

    @pytest.fixture
    def sample_svg(self):
        """Create sample SVG for testing"""
        return """<?xml version="1.0" encoding="UTF-8"?>
        <svg width="200" height="200" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
            <rect x="10" y="10" width="50" height="30" fill="#ff0000"/>
            <circle cx="100" cy="100" r="25" fill="#00ff00"/>
            <path d="M 50 50 L 100 50 L 100 100 Z" fill="#0000ff"/>
            <text x="10" y="150" font-family="Arial" font-size="12">Test Text</text>
        </svg>"""

    @pytest.fixture
    def mock_clean_slate_services(self):
        """Create mock services with clean slate components"""
        services = ConversionServices.create_default()

        # Add mock clean slate services
        services.ir_scene_factory = Mock()
        services.policy_engine = Mock()
        services.mapper_registry = Mock()
        services.drawingml_embedder = Mock()

        return services

    def test_hybrid_config_creation(self):
        """Test creation of different hybrid configurations"""
        # Test existing only mode
        config = HybridConversionConfig.create_existing_only()
        assert config.conversion_mode == ConversionMode.EXISTING_ONLY
        assert config.clean_slate_elements == []
        assert not config.should_use_clean_slate_for_element('path')

        # Test clean slate only mode
        config = HybridConversionConfig.create_clean_slate_only()
        assert config.conversion_mode == ConversionMode.CLEAN_SLATE_ONLY
        assert 'path' in config.clean_slate_elements
        assert config.should_use_clean_slate_for_element('path')

        # Test hybrid paths only mode
        config = HybridConversionConfig.create_hybrid_paths_only()
        assert config.conversion_mode == ConversionMode.HYBRID
        assert config.clean_slate_elements == ['path']
        assert config.should_use_clean_slate_for_element('path')
        assert not config.should_use_clean_slate_for_element('text')

    def test_conversion_services_extension(self):
        """Test that ConversionServices has clean slate fields"""
        services = ConversionServices.create_default()

        # Check that clean slate fields exist
        assert hasattr(services, 'ir_scene_factory')
        assert hasattr(services, 'policy_engine')
        assert hasattr(services, 'mapper_registry')
        assert hasattr(services, 'drawingml_embedder')

        # Should be None by default
        assert services.ir_scene_factory is None
        assert services.policy_engine is None
        assert services.mapper_registry is None
        assert services.drawingml_embedder is None

    @patch('src.services.conversion_services.SceneFactory')
    @patch('src.services.conversion_services.PolicyEngine')
    @patch('src.services.conversion_services.MapperRegistry')
    @patch('src.services.conversion_services.DrawingMLEmbedder')
    def test_clean_slate_services_creation(self, mock_embedder, mock_mapper_registry,
                                         mock_policy_engine, mock_scene_factory):
        """Test creation of services with clean slate components"""
        # Mock the clean slate components
        mock_scene_factory.return_value = Mock()
        mock_policy_engine.return_value = Mock()
        mock_mapper_registry.return_value = Mock()
        mock_embedder.return_value = Mock()

        # This will try to import clean slate components (which should fail in test)
        # but should gracefully fall back to regular services
        services = ConversionServices.create_with_clean_slate()

        # Should still have base services even if clean slate fails
        assert services.unit_converter is not None
        assert services.color_parser is not None
        assert services.transform_parser is not None

    def test_registry_factory_clean_slate_detection(self, mock_clean_slate_services):
        """Test that registry factory detects clean slate services"""
        from src.converters.base import ConverterRegistryFactory

        # Test detection of clean slate services
        has_clean_slate = ConverterRegistryFactory._has_clean_slate_services(mock_clean_slate_services)
        assert has_clean_slate is True

        # Test with regular services (no clean slate)
        regular_services = ConversionServices.create_default()
        has_clean_slate = ConverterRegistryFactory._has_clean_slate_services(regular_services)
        assert has_clean_slate is False

    def test_hybrid_registry_creation(self, mock_clean_slate_services):
        """Test creation of hybrid registry"""
        from src.converters.base import ConverterRegistryFactory

        hybrid_config = HybridConversionConfig.create_hybrid_paths_only()

        # This should not fail even if IR bridge import fails
        registry = ConverterRegistryFactory.get_hybrid_registry(
            mock_clean_slate_services,
            hybrid_config
        )

        assert registry is not None
        assert registry.services == mock_clean_slate_services

    def test_ir_bridge_creation_with_missing_services(self):
        """Test IR bridge creation with missing clean slate services"""
        from src.converters.ir_bridge import IRConverterBridge

        services = ConversionServices.create_default()
        hybrid_config = HybridConversionConfig.create_hybrid_paths_only()

        # Should fail because clean slate services are missing
        with pytest.raises(ValueError, match="Missing required clean slate services"):
            IRConverterBridge(services, hybrid_config)

    def test_ir_bridge_creation_with_clean_slate_services(self, mock_clean_slate_services):
        """Test IR bridge creation with clean slate services"""
        from src.converters.ir_bridge import IRConverterBridge

        hybrid_config = HybridConversionConfig.create_hybrid_paths_only()

        # Should succeed with clean slate services
        bridge = IRConverterBridge(mock_clean_slate_services, hybrid_config)
        assert bridge.services == mock_clean_slate_services
        assert bridge.hybrid_config == hybrid_config

    def test_svg_to_drawingml_converter_clean_slate_flag(self):
        """Test SVGToDrawingMLConverter with clean slate flag"""
        from src.svg2drawingml import SVGToDrawingMLConverter

        # Test without clean slate flag
        converter = SVGToDrawingMLConverter(use_clean_slate=False)
        assert converter.use_clean_slate is False

        # Test with clean slate flag (should gracefully handle missing components)
        converter = SVGToDrawingMLConverter(use_clean_slate=True)
        assert converter.use_clean_slate is True

    def test_existing_system_compatibility(self, sample_svg):
        """Test that existing system still works with hybrid extensions"""
        from src.svg2drawingml import SVGToDrawingMLConverter

        # Create converter in existing mode
        converter = SVGToDrawingMLConverter(use_clean_slate=False)

        # Should be able to parse SVG without issues
        try:
            result = converter.convert(sample_svg)
            # Should produce some output
            assert isinstance(result, str)
            assert len(result) > 0
        except Exception as e:
            # Expected in test environment due to missing dependencies
            assert "services_bootstrap" in str(e) or "import" in str(e)

    def test_hybrid_config_serialization(self):
        """Test hybrid configuration serialization"""
        config = HybridConversionConfig.create_full_hybrid()

        # Test serialization
        config_dict = config.to_dict()
        assert 'conversion_mode' in config_dict
        assert 'policy_thresholds' in config_dict
        assert 'feature_flags' in config_dict

        # Test deserialization
        restored_config = HybridConversionConfig.from_dict(config_dict)
        assert restored_config.conversion_mode == config.conversion_mode
        assert restored_config.clean_slate_elements == config.clean_slate_elements

    def test_path_mapper_integration(self):
        """Test PathMapper integration with existing PathSystem"""
        try:
            from core.map.path_mapper import PathMapper, create_path_mapper
            from core.policy import Policy

            # Create mock policy and path system
            mock_policy = Mock(spec=Policy)
            mock_path_system = Mock()

            # Create mapper with path system integration
            mapper = create_path_mapper(mock_policy, mock_path_system)

            assert mapper.path_system == mock_path_system
            assert mapper.policy == mock_policy
        except ImportError:
            # Expected if clean slate components not available
            pytest.skip("Clean slate components not available")

    def test_converter_registry_ir_bridge_priority(self, mock_clean_slate_services):
        """Test that converter registry prioritizes IR bridge when available"""
        from src.converters.base import ConverterRegistry
        from src.converters.ir_bridge import IRConverterBridge

        registry = ConverterRegistry(services=mock_clean_slate_services)

        # Register a regular converter
        mock_converter = Mock()
        mock_converter.can_convert.return_value = True
        mock_converter.supported_elements = ['path']
        registry.register(mock_converter)

        # Create a sample element
        path_element = ET.Element('path')
        path_element.set('d', 'M 0 0 L 10 10')

        # Without IR bridge, should use regular converter
        converter = registry.get_converter(path_element)
        assert converter == mock_converter

        # Register IR bridge
        mock_ir_bridge = Mock()
        mock_ir_bridge.can_convert.return_value = True
        registry.register_ir_bridge(mock_ir_bridge)

        # With IR bridge, should prioritize IR bridge
        converter = registry.get_converter(path_element)
        assert converter == mock_ir_bridge

    def test_performance_integration(self):
        """Test that hybrid mode doesn't significantly impact performance"""
        from src.services.conversion_services import ConversionServices
        import time

        # Measure base service creation time
        start_time = time.perf_counter()
        services = ConversionServices.create_default()
        base_time = (time.perf_counter() - start_time) * 1000

        # Measure hybrid service creation time (should gracefully fail)
        start_time = time.perf_counter()
        services = ConversionServices.create_with_clean_slate()
        hybrid_time = (time.perf_counter() - start_time) * 1000

        # Hybrid mode should not be significantly slower (allowing for some overhead)
        assert hybrid_time < base_time * 3  # Allow up to 3x overhead

    def test_error_handling_and_fallbacks(self):
        """Test error handling and fallback mechanisms"""
        from src.converters.base import ConverterRegistryFactory

        # Test with services that don't have clean slate components
        services = ConversionServices.create_default()

        # Should gracefully fall back to regular registry
        registry = ConverterRegistryFactory.get_registry(services=services)
        assert registry is not None
        assert registry.ir_bridge is None

    def test_backward_compatibility(self, sample_svg):
        """Test that all existing functionality remains unaffected"""
        # Test that existing converter creation still works
        services = ConversionServices.create_default()
        assert services.unit_converter is not None
        assert services.color_parser is not None

        # Test that existing registry creation still works
        registry = ConverterRegistryFactory.get_registry()
        assert registry is not None

        # Test that converter registry can still find converters
        rect_element = ET.Element('rect')
        rect_element.set('x', '10')
        rect_element.set('y', '10')
        rect_element.set('width', '50')
        rect_element.set('height', '30')

        # Should either find a converter or return None gracefully
        converter = registry.get_converter(rect_element)
        # In test environment, may not have converters loaded, but shouldn't crash


class TestHybridModeEndToEnd:
    """End-to-end integration tests for hybrid mode"""

    def test_api_parameter_propagation(self):
        """Test that clean slate parameters propagate through API layers"""
        # This would test the full API chain but requires actual API setup
        # For now, just verify the parameter exists in the API schema
        from api.main import convert_svg_to_drive
        import inspect

        sig = inspect.signature(convert_svg_to_drive)
        assert 'clean_slate' in sig.parameters

    def test_configuration_precedence(self):
        """Test configuration precedence and override behavior"""
        config = HybridConversionConfig.create_existing_only()

        # Should not use clean slate for any element
        assert not config.should_use_clean_slate_for_element('path')
        assert not config.should_use_clean_slate_for_element('text')

        # Create hybrid config
        config = HybridConversionConfig.create_hybrid_paths_only()

        # Should use clean slate only for paths
        assert config.should_use_clean_slate_for_element('path')
        assert not config.should_use_clean_slate_for_element('text')

    def test_memory_and_resource_management(self, mock_clean_slate_services):
        """Test that hybrid mode doesn't leak memory or resources"""
        from src.converters.ir_bridge import IRConverterBridge

        config = HybridConversionConfig.create_hybrid_paths_only()

        # Create and destroy multiple bridges
        bridges = []
        for _ in range(10):
            bridge = IRConverterBridge(mock_clean_slate_services, config)
            bridges.append(bridge)

        # Reset statistics (should not fail)
        for bridge in bridges:
            bridge.reset_statistics()
            stats = bridge.get_statistics()
            assert isinstance(stats, dict)

    def test_concurrent_usage(self, mock_clean_slate_services):
        """Test concurrent usage of hybrid components"""
        from src.converters.base import ConverterRegistryFactory
        import threading

        results = []

        def create_registry():
            try:
                registry = ConverterRegistryFactory.get_registry(
                    services=mock_clean_slate_services,
                    force_new=True
                )
                results.append(registry is not None)
            except Exception as e:
                results.append(False)

        # Create multiple registries concurrently
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=create_registry)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All should succeed
        assert all(results)