#!/usr/bin/env python3
"""
Integration tests for end-to-end ConversionServices dependency injection.

This test suite verifies that the dependency injection refactor is complete
and working properly across the entire conversion pipeline. It tests:

1. Service injection through the full conversion flow
2. Proper service sharing between converter instances
3. Configuration propagation to all services
4. Error handling for service initialization failures
5. Memory efficiency through service reuse
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
from lxml import etree as ET

from src.services.conversion_services import ConversionServices, ConversionConfig, ServiceInitializationError
from src.converters.base import BaseConverter, ConversionContext, ConverterRegistry
from src.converters.shapes import RectangleConverter
from src.converters.text import TextConverter
from src.converters.paths import PathConverter


class TestDependencyInjectionIntegration:
    """Test suite for end-to-end dependency injection functionality."""

    @pytest.fixture
    def sample_svg_content(self):
        """Sample SVG content for integration testing."""
        return '''
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
            <rect x="10" y="20" width="30" height="40" fill="red"/>
            <text x="50" y="60">Hello</text>
            <path d="M70,70 L80,80 L90,70 Z" fill="blue"/>
        </svg>
        '''

    @pytest.fixture
    def custom_config(self):
        """Custom configuration for testing."""
        return ConversionConfig(
            default_dpi=120.0,
            viewport_width=1000.0,
            viewport_height=800.0,
            enable_caching=False
        )

    def test_end_to_end_service_injection_flow(self, sample_svg_content):
        """Test complete conversion flow with service injection."""
        # Create services container
        services = ConversionServices.create_default()

        # Parse SVG
        svg_root = ET.fromstring(sample_svg_content.encode('utf-8'))

        # Create conversion context with services
        context = ConversionContext(services=services, svg_root=svg_root)

        # Set up coordinate system (required for conversions)
        from src.converters.base import CoordinateSystem
        context.coordinate_system = CoordinateSystem((0, 0, 800, 600))

        # Create converter registry with service injection
        registry = ConverterRegistry()

        # Register converters with services
        registry.register(RectangleConverter(services=services))
        registry.register(TextConverter(services=services))
        registry.register(PathConverter(services=services))

        # Test that all converters received the same service instances
        # Create test elements to get converters
        rect_element = ET.fromstring('<rect x="0" y="0" width="100" height="50"/>')
        text_element = ET.fromstring('<text x="10" y="20">Test</text>')
        path_element = ET.fromstring('<path d="M 0 0 L 100 100"/>')

        rect_converter = registry.get_converter(rect_element)
        text_converter = registry.get_converter(text_element)
        path_converter = registry.get_converter(path_element)

        # Verify all converters share the same service instances
        assert rect_converter.services is text_converter.services
        assert text_converter.services is path_converter.services
        assert path_converter.services is services

        # Verify each service is properly injected
        assert rect_converter.services.unit_converter is not None
        assert rect_converter.services.color_factory is not None
        assert rect_converter.services.transform_parser is not None
        assert rect_converter.services.viewport_resolver is not None

        # Test actual conversion using injected services
        rect_element = svg_root.find('.//{http://www.w3.org/2000/svg}rect')
        text_element = svg_root.find('.//{http://www.w3.org/2000/svg}text')
        path_element = svg_root.find('.//{http://www.w3.org/2000/svg}path')

        # These should work without any manual service instantiation
        rect_result = rect_converter.convert(rect_element, context)
        text_result = text_converter.convert(text_element, context)
        path_result = path_converter.convert(path_element, context)

        # Verify all conversions succeeded
        assert rect_result is not None
        assert text_result is not None
        assert path_result is not None

    def test_service_configuration_propagation(self, custom_config):
        """Test that configuration is properly propagated to all services."""
        # Create services with custom configuration
        services = ConversionServices.create_default(config=custom_config)

        # Verify configuration is accessible through services
        assert services.config.default_dpi == 120.0
        assert services.config.viewport_width == 1000.0
        assert services.config.viewport_height == 800.0
        assert services.config.enable_caching is False

        # Create converter with services
        converter = RectangleConverter(services=services)

        # Verify converter can access configuration through services
        assert converter.services.config.default_dpi == 120.0
        assert converter.unit_converter is not None  # Backward compatibility

        # Test that configuration affects service behavior
        # (This would test actual service configuration usage)
        unit_converter = services.unit_converter
        assert unit_converter is not None

    def test_service_sharing_across_converter_instances(self):
        """Test that multiple converter instances share the same service instances."""
        services = ConversionServices.create_default()

        # Create multiple converter instances
        converter1 = RectangleConverter(services=services)
        converter2 = RectangleConverter(services=services)
        converter3 = TextConverter(services=services)

        # Verify all share the same service instances (not just equal objects)
        assert converter1.services is converter2.services is converter3.services
        assert converter1.services.unit_converter is converter2.services.unit_converter
        assert converter2.services.color_factory is converter3.services.color_factory
        assert converter1.services.transform_parser is converter3.services.transform_parser

    def test_service_initialization_error_handling(self):
        """Test proper error handling when service initialization fails."""
        # Mock a service that fails to initialize
        with patch('src.services.conversion_services.UnitConverter') as mock_unit_converter:
            mock_unit_converter.side_effect = Exception("Service init failed")

            # Should raise ServiceInitializationError
            with pytest.raises(ServiceInitializationError) as exc_info:
                ConversionServices.create_default()

            assert "Service init failed" in str(exc_info.value)

    def test_memory_efficiency_through_service_reuse(self):
        """Test that service reuse is memory efficient."""
        services = ConversionServices.create_default()

        # Create many converter instances
        converters = []
        for i in range(100):
            if i % 3 == 0:
                converters.append(RectangleConverter(services=services))
            elif i % 3 == 1:
                converters.append(TextConverter(services=services))
            else:
                converters.append(PathConverter(services=services))

        # Verify all 100 converters share the same 4 service instances
        base_services = services
        for converter in converters:
            assert converter.services is base_services
            assert converter.services.unit_converter is base_services.unit_converter
            assert converter.services.color_factory is base_services.color_factory
            assert converter.services.transform_parser is base_services.transform_parser
            assert converter.services.viewport_resolver is base_services.viewport_resolver

    def test_conversion_context_service_integration(self, sample_svg_content):
        """Test ConversionContext integration with services."""
        services = ConversionServices.create_default()
        svg_root = ET.fromstring(sample_svg_content.encode('utf-8'))

        # Create context with services
        context = ConversionContext(services=services, svg_root=svg_root)

        # Set up coordinate system (required for conversions)
        from src.converters.base import CoordinateSystem
        context.coordinate_system = CoordinateSystem((0, 0, 800, 600))

        # Verify context has access to services
        assert context.services is services
        assert context.services.unit_converter is not None
        assert context.services.color_factory is not None

        # Test that context can be used for conversion
        rect_element = svg_root.find('.//{http://www.w3.org/2000/svg}rect')
        converter = RectangleConverter(services=services)

        # This should work without any manual service setup
        result = converter.convert(rect_element, context)
        assert result is not None

    def test_backward_compatibility_property_access(self):
        """Test that backward compatibility properties work correctly."""
        services = ConversionServices.create_default()
        converter = RectangleConverter(services=services)

        # Test backward compatibility properties
        assert converter.unit_converter is services.unit_converter
        assert converter.color_parser.color_factory is services.color_factory  # Test compatibility wrapper
        assert converter.transform_parser is services.transform_parser
        assert converter.viewport_resolver is services.viewport_resolver

        # These should be the same instances
        assert converter.unit_converter is converter.services.unit_converter
        assert converter.color_parser.color_factory is converter.services.color_factory

    def test_config_file_loading_integration(self):
        """Test configuration loading from file integration."""
        config_data = {
            "default_dpi": 150.0,
            "viewport_width": 1200.0,
            "viewport_height": 900.0,
            "enable_caching": True,
            "extra_field": "should_be_ignored"  # Should be filtered out
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            import json
            json.dump(config_data, f)
            config_file = Path(f.name)

        try:
            # Load config from file
            config = ConversionConfig.from_file(config_file)
            services = ConversionServices.create_default(config=config)

            # Verify configuration is applied
            assert services.config.default_dpi == 150.0
            assert services.config.viewport_width == 1200.0
            assert services.config.viewport_height == 900.0
            assert services.config.enable_caching is True

            # Verify invalid field was ignored
            assert not hasattr(services.config, 'extra_field')

        finally:
            config_file.unlink()  # Cleanup

    def test_converter_registry_service_injection(self):
        """Test ConverterRegistry properly handles service injection."""
        services = ConversionServices.create_default()
        registry = ConverterRegistry()

        # Register converters with services
        rect_converter = RectangleConverter(services=services)
        text_converter = TextConverter(services=services)

        registry.register(rect_converter)
        registry.register(text_converter)

        # Verify converters are properly registered and have services
        rect_element = ET.fromstring('<rect x="0" y="0" width="100" height="50"/>')
        text_element = ET.fromstring('<text x="10" y="20">Test</text>')

        retrieved_rect = registry.get_converter(rect_element)
        retrieved_text = registry.get_converter(text_element)

        assert retrieved_rect is rect_converter
        assert retrieved_text is text_converter
        assert retrieved_rect.services is services
        assert retrieved_text.services is services

    def test_service_validation_and_lifecycle(self):
        """Test service validation and lifecycle management."""
        services = ConversionServices.create_default()

        # Test service validation
        assert services.validate_services() is True

        # Test that all required services are present
        required_services = ['unit_converter', 'color_factory', 'transform_parser', 'viewport_resolver']
        for service_name in required_services:
            assert hasattr(services, service_name)
            assert getattr(services, service_name) is not None

    def test_error_propagation_through_conversion_pipeline(self, sample_svg_content):
        """Test that errors are properly propagated through the conversion pipeline."""
        # Create services with a mocked service that will fail
        services = ConversionServices.create_default()

        svg_root = ET.fromstring(sample_svg_content.encode('utf-8'))
        context = ConversionContext(services=services, svg_root=svg_root)

        # Set up coordinate system and mock it to fail
        from src.converters.base import CoordinateSystem
        context.coordinate_system = CoordinateSystem((0, 0, 800, 600))

        # Mock the coordinate system method that's actually called
        context.coordinate_system.svg_to_emu = Mock(side_effect=ValueError("Coordinate conversion failed"))

        rect_element = svg_root.find('.//{http://www.w3.org/2000/svg}rect')
        converter = RectangleConverter(services=services)

        # The error should propagate properly through the conversion pipeline
        with pytest.raises(ValueError, match="Coordinate conversion failed"):
            converter.convert(rect_element, context)

    def test_concurrent_service_usage(self, sample_svg_content):
        """Test that services can be safely used concurrently."""
        import threading
        import time

        services = ConversionServices.create_default()
        svg_root = ET.fromstring(sample_svg_content.encode('utf-8'))

        results = []
        errors = []

        def conversion_worker():
            try:
                context = ConversionContext(services=services, svg_root=svg_root)

                # Set up coordinate system (required for conversions)
                from src.converters.base import CoordinateSystem
                context.coordinate_system = CoordinateSystem((0, 0, 800, 600))

                converter = RectangleConverter(services=services)
                rect_element = svg_root.find('.//{http://www.w3.org/2000/svg}rect')

                result = converter.convert(rect_element, context)
                results.append(result)
            except Exception as e:
                errors.append(e)

        # Start multiple threads using the same services
        threads = []
        for i in range(10):
            thread = threading.Thread(target=conversion_worker)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify all conversions succeeded
        assert len(errors) == 0, f"Concurrent conversion errors: {errors}"
        assert len(results) == 10
        assert all(result is not None for result in results)


class TestServiceInjectionPerformance:
    """Performance tests for service injection system."""

    def test_service_creation_performance(self):
        """Test that service creation is reasonably fast."""
        import time

        start_time = time.perf_counter()

        # Create many service containers
        for i in range(100):
            services = ConversionServices.create_default()

        elapsed = time.perf_counter() - start_time

        # Should be able to create 100 service containers in under 1 second
        assert elapsed < 1.0, f"Service creation took {elapsed:.2f}s for 100 instances"

    def test_converter_instantiation_performance(self):
        """Test that converter instantiation with services is fast."""
        import time

        services = ConversionServices.create_default()

        start_time = time.perf_counter()

        # Create many converters with service injection
        converters = []
        for i in range(1000):
            converters.append(RectangleConverter(services=services))

        elapsed = time.perf_counter() - start_time

        # Should be able to create 1000 converters in under 0.5 seconds
        assert elapsed < 0.5, f"Converter creation took {elapsed:.2f}s for 1000 instances"

        # Verify all share the same services (memory efficient)
        base_services = services
        for converter in converters:
            assert converter.services is base_services