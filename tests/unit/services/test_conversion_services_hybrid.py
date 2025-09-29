#!/usr/bin/env python3
"""
Unit tests for ConversionServices hybrid extensions

Tests the clean slate service integration and hybrid factory methods.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from lxml import etree as ET

from core.services.conversion_services import ConversionServices, ServiceInitializationError
from src.config.hybrid_config import HybridConversionConfig


class TestConversionServicesHybridExtensions:
    """Test hybrid extensions to ConversionServices"""

    def test_conversion_services_has_clean_slate_fields(self):
        """Test that ConversionServices has clean slate service fields"""
        services = ConversionServices.create_default()

        # Clean slate fields should exist and be None by default
        assert hasattr(services, 'ir_scene_factory')
        assert hasattr(services, 'policy_engine')
        assert hasattr(services, 'mapper_registry')
        assert hasattr(services, 'drawingml_embedder')

        assert services.ir_scene_factory is None
        assert services.policy_engine is None
        assert services.mapper_registry is None
        assert services.drawingml_embedder is None

    @patch('core.io.DrawingMLEmbedder')
    @patch('core.map.MapperRegistry')
    @patch('core.policy.PolicyEngine')
    @patch('core.ir.SceneFactory')
    def test_create_with_clean_slate_success(self, mock_scene_factory, mock_policy_engine,
                                           mock_mapper_registry, mock_embedder):
        """Test successful creation with clean slate components"""
        # Mock the clean slate components
        mock_scene_factory.return_value = Mock()
        mock_policy_engine.return_value = Mock()
        mock_mapper_registry.return_value = Mock()
        mock_embedder.return_value = Mock()

        # Create services with clean slate
        services = ConversionServices.create_with_clean_slate()

        # Verify base services were created
        assert services.unit_converter is not None
        assert services.color_parser is not None
        assert services.transform_parser is not None

        # Verify clean slate services were initialized
        assert services.ir_scene_factory is not None
        assert services.policy_engine is not None
        assert services.mapper_registry is not None
        assert services.drawingml_embedder is not None

        # Verify clean slate components were called with correct parameters
        mock_scene_factory.assert_called_once()
        mock_policy_engine.assert_called_once()
        mock_mapper_registry.assert_called_once()
        mock_embedder.assert_called_once()

    def test_create_with_clean_slate_import_error(self):
        """Test graceful handling of clean slate import errors"""
        # Should not raise an exception, just return services without clean slate components
        services = ConversionServices.create_with_clean_slate()

        # Base services should still be available
        assert services.unit_converter is not None
        assert services.color_parser is not None

        # Clean slate services should be None due to import error
        assert services.ir_scene_factory is None
        assert services.policy_engine is None
        assert services.mapper_registry is None
        assert services.drawingml_embedder is None

    @patch('core.ir.SceneFactory')
    def test_create_with_clean_slate_initialization_error(self, mock_scene_factory):
        """Test handling of clean slate initialization errors"""
        # Make SceneFactory raise an exception
        mock_scene_factory.side_effect = Exception("Scene factory initialization failed")

        with pytest.raises(ServiceInitializationError, match="Failed to initialize clean slate services"):
            ConversionServices.create_with_clean_slate()

    def test_create_with_clean_slate_with_config(self):
        """Test create_with_clean_slate with custom configuration"""
        from core.services.conversion_services import ConversionConfig

        config = ConversionConfig(
            default_dpi=120.0,
            viewport_width=1024.0,
            viewport_height=768.0
        )

        # Should not raise an exception
        services = ConversionServices.create_with_clean_slate(config)

        assert services.config == config
        assert services.unit_converter is not None

    def test_create_with_clean_slate_with_svg_root(self):
        """Test create_with_clean_slate with SVG root element"""
        svg_root = ET.Element('svg')
        svg_root.set('width', '100')
        svg_root.set('height', '200')

        # Should not raise an exception
        services = ConversionServices.create_with_clean_slate(svg_root=svg_root)

        assert services.style_service is not None

    @patch('core.io.DrawingMLEmbedder')
    @patch('core.map.MapperRegistry')
    @patch('core.policy.PolicyEngine')
    @patch('core.ir.SceneFactory')
    def test_clean_slate_service_parameters(self, mock_scene_factory, mock_policy_engine,
                                          mock_mapper_registry, mock_embedder):
        """Test that clean slate services are initialized with correct parameters"""
        # Mock the components
        mock_scene_factory.return_value = Mock()
        mock_policy_engine.return_value = Mock()
        mock_mapper_registry.return_value = Mock()
        mock_embedder.return_value = Mock()

        services = ConversionServices.create_with_clean_slate()

        # Verify SceneFactory was called with existing services
        scene_factory_call = mock_scene_factory.call_args
        assert 'unit_converter' in scene_factory_call.kwargs
        assert 'color_parser' in scene_factory_call.kwargs
        assert 'transform_engine' in scene_factory_call.kwargs

        # Verify PolicyEngine was called with thresholds
        policy_engine_call = mock_policy_engine.call_args
        assert 'path_complexity_threshold' in policy_engine_call.kwargs
        assert 'text_complexity_threshold' in policy_engine_call.kwargs
        assert 'group_nesting_threshold' in policy_engine_call.kwargs
        assert 'image_size_threshold' in policy_engine_call.kwargs

        # Verify MapperRegistry was called with existing services
        mapper_registry_call = mock_mapper_registry.call_args
        assert 'path_system' in mapper_registry_call.kwargs
        assert 'style_service' in mapper_registry_call.kwargs
        assert 'gradient_service' in mapper_registry_call.kwargs

        # Verify DrawingMLEmbedder was called with slide dimensions
        embedder_call = mock_embedder.call_args
        assert 'slide_width_emu' in embedder_call.kwargs
        assert 'slide_height_emu' in embedder_call.kwargs
        assert embedder_call.kwargs['slide_width_emu'] == 9144000  # 10 inches
        assert embedder_call.kwargs['slide_height_emu'] == 6858000  # 7.5 inches

    def test_service_cleanup_includes_clean_slate_services(self):
        """Test that cleanup method handles clean slate services"""
        services = ConversionServices.create_default()

        # Manually set clean slate services for testing
        services.ir_scene_factory = Mock()
        services.policy_engine = Mock()
        services.mapper_registry = Mock()
        services.drawingml_embedder = Mock()

        # Cleanup should not raise an exception
        services.cleanup()

        # All services should be None after cleanup
        assert services.ir_scene_factory is None
        assert services.policy_engine is None
        assert services.mapper_registry is None
        assert services.drawingml_embedder is None

    def test_validate_services_with_clean_slate_components(self):
        """Test service validation includes clean slate components"""
        services = ConversionServices.create_default()

        # Base validation should pass
        assert services.validate_services() is True

        # Add mock clean slate services
        services.ir_scene_factory = Mock()
        services.policy_engine = Mock()
        services.mapper_registry = Mock()
        services.drawingml_embedder = Mock()

        # Validation should still pass
        assert services.validate_services() is True


class TestConversionServicesIntegration:
    """Integration tests for ConversionServices with hybrid configuration"""

    def test_services_support_hybrid_workflow(self):
        """Test that services can support a hybrid workflow"""
        services = ConversionServices.create_default()

        # Should be able to create hybrid configuration
        hybrid_config = HybridConversionConfig.create_existing_only()

        # Services should work with hybrid configuration
        assert services.unit_converter is not None
        assert services.color_parser is not None
        assert services.transform_parser is not None

        # Clean slate services should be None initially
        assert services.ir_scene_factory is None
        assert services.policy_engine is None

    def test_services_creation_performance(self):
        """Test that service creation performance is acceptable"""
        import time

        start_time = time.perf_counter()
        services = ConversionServices.create_default()
        end_time = time.perf_counter()

        creation_time = (end_time - start_time) * 1000  # Convert to milliseconds

        # Service creation should be fast (under 100ms)
        assert creation_time < 100.0
        assert services.unit_converter is not None

    def test_services_memory_usage(self):
        """Test that services don't consume excessive memory"""
        import sys

        # Get initial memory usage
        initial_size = sys.getsizeof(ConversionServices.create_default())

        # Create multiple service instances
        services_list = [ConversionServices.create_default() for _ in range(10)]

        # Memory per service should be reasonable (under 10KB)
        avg_size = sum(sys.getsizeof(s) for s in services_list) / len(services_list)
        assert avg_size < 10000  # 10KB

    def test_singleton_pattern_preserved(self):
        """Test that singleton pattern is preserved with extensions"""
        instance1 = ConversionServices.get_default_instance()
        instance2 = ConversionServices.get_default_instance()

        assert instance1 is instance2

        # Reset and test again
        ConversionServices.reset_default_instance()
        instance3 = ConversionServices.get_default_instance()

        assert instance3 is not instance1

    def test_custom_services_creation_with_clean_slate_fields(self):
        """Test custom services creation preserves clean slate fields"""
        custom_config = {
            'unit_converter': {},
            'color_factory': {},
            'config': {'default_dpi': 120.0}
        }

        services = ConversionServices.create_custom(custom_config)

        # Should have clean slate fields even in custom creation
        assert hasattr(services, 'ir_scene_factory')
        assert hasattr(services, 'policy_engine')
        assert hasattr(services, 'mapper_registry')
        assert hasattr(services, 'drawingml_embedder')

        # Fields should be None by default
        assert services.ir_scene_factory is None
        assert services.policy_engine is None
        assert services.mapper_registry is None
        assert services.drawingml_embedder is None


class TestBackwardCompatibility:
    """Test that hybrid extensions don't break existing functionality"""

    def test_existing_service_creation_unchanged(self):
        """Test that existing service creation behavior is unchanged"""
        services = ConversionServices.create_default()

        # All existing services should still be available
        required_services = [
            'unit_converter', 'color_factory', 'color_parser', 'transform_parser',
            'viewport_resolver', 'style_parser', 'style_service', 'coordinate_transformer',
            'font_processor', 'path_processor', 'pptx_builder', 'gradient_service',
            'pattern_service', 'filter_service', 'image_service'
        ]

        for service_name in required_services:
            assert hasattr(services, service_name)
            # path_system can be None initially, others should not be
            if service_name != 'path_system':
                assert getattr(services, service_name) is not None

    def test_existing_service_validation_unchanged(self):
        """Test that existing service validation behavior is unchanged"""
        services = ConversionServices.create_default()

        # Validation should pass as before
        assert services.validate_services() is True

    def test_existing_cleanup_behavior_unchanged(self):
        """Test that existing cleanup behavior is unchanged"""
        services = ConversionServices.create_default()

        # Store references to check cleanup
        unit_converter = services.unit_converter
        color_parser = services.color_parser

        assert unit_converter is not None
        assert color_parser is not None

        # Cleanup should work as before
        services.cleanup()

        assert services.unit_converter is None
        assert services.color_parser is None

    def test_existing_path_system_creation_unchanged(self):
        """Test that existing path system creation is unchanged"""
        services = ConversionServices.create_default()

        # get_path_system should work as before
        path_system = services.get_path_system(800, 600)
        assert path_system is not None

        # Should be cached
        path_system2 = services.get_path_system(800, 600)
        assert path_system2 is path_system