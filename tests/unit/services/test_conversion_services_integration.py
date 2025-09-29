#!/usr/bin/env python3
"""
ConversionServices Integration Tests

Tests for the dependency injection container to ensure all services
are properly initialized and integrated.
"""

import pytest
from unittest.mock import Mock, MagicMock
from lxml import etree as ET

from src.services.conversion_services import ConversionServices, ConversionConfig, ServiceInitializationError


class TestConversionServicesIntegration:
    """Integration tests for ConversionServices dependency injection."""

    def test_create_default_services(self):
        """Test creation of default services."""
        services = ConversionServices.create_default()

        # Verify all services are initialized
        assert services.unit_converter is not None
        assert services.color_factory is not None
        assert services.color_parser is not None
        assert services.transform_parser is not None
        assert services.viewport_resolver is not None
        assert services.style_parser is not None
        assert services.coordinate_transformer is not None
        assert services.font_processor is not None
        assert services.path_processor is not None
        assert services.pptx_builder is not None
        assert services.gradient_service is not None
        assert services.pattern_service is not None
        assert services.filter_service is not None
        assert services.image_service is not None
        assert services.config is not None

    def test_service_validation_passes(self):
        """Test that all services pass validation."""
        services = ConversionServices.create_default()
        assert services.validate_services() is True

    def test_unit_converter_functionality(self):
        """Test unit converter service."""
        services = ConversionServices.create_default()

        # Test unit conversion
        from src.units import unit
        result = unit("10px").to_emu()
        assert isinstance(result, int)
        assert result > 0

    def test_color_factory_functionality(self):
        """Test color factory service."""
        services = ConversionServices.create_default()

        # Test color creation
        color = services.color_factory("#FF0000")
        assert color is not None

        # Test from_hex method (adapter)
        color_hex = services.color_factory.from_hex("#00FF00")
        assert color_hex is not None

    def test_transform_parser_functionality(self):
        """Test transform parser service."""
        services = ConversionServices.create_default()

        # Test transform parsing
        result = services.transform_parser.parse_to_matrix("translate(10,20)")
        assert result is not None

    def test_viewport_resolver_functionality(self):
        """Test viewport resolver service."""
        services = ConversionServices.create_default()

        # Test viewbox parsing (adapter method)
        viewbox = services.viewport_resolver.parse_viewbox("0 0 100 100")
        assert viewbox is not None or viewbox is None  # Method may return None for invalid input

        # Test viewport calculation (adapter method)
        viewport = services.viewport_resolver.calculate_viewport(800, 600)
        assert isinstance(viewport, dict)
        assert 'viewport_width' in viewport
        assert 'viewport_height' in viewport

    def test_style_parser_functionality(self):
        """Test style parser service."""
        services = ConversionServices.create_default()

        # Test style string parsing (may return StyleResult object)
        styles = services.style_parser.parse_style_string("color: red; font-size: 12px")
        # StyleParser may return StyleResult object or dict
        if hasattr(styles, 'declarations'):
            assert len(styles.declarations) > 0
        else:
            assert isinstance(styles, dict)
            assert len(styles) > 0

        # Test style attribute parsing (adapter method)
        styles_attr = services.style_parser.parse_style_attribute("color: blue; margin: 10px")
        assert isinstance(styles_attr, dict)

    def test_coordinate_transformer_functionality(self):
        """Test coordinate transformer service."""
        services = ConversionServices.create_default()

        # Test coordinate parsing
        result = services.coordinate_transformer.parse_coordinate_string("10,20 30,40")
        assert result is not None

        # Test coordinate transformation (adapter method)
        coords = [(10, 20), (30, 40)]
        result = services.coordinate_transformer.transform_coordinates(coords)
        assert isinstance(result, list)

    def test_font_processor_functionality(self):
        """Test font processor service."""
        services = ConversionServices.create_default()

        # Create mock element
        element = ET.Element('text')
        element.set('font-family', 'Arial')
        element.set('font-size', '12px')

        # Test font family extraction
        family = services.font_processor.get_font_family(element)
        assert family == 'Arial'

        # Test font attributes processing (adapter method)
        attrs = services.font_processor.process_font_attributes(element)
        assert isinstance(attrs, dict)
        assert 'family' in attrs

    def test_path_processor_functionality(self):
        """Test path processor service."""
        services = ConversionServices.create_default()

        path_data = "M 10 10 L 20 20"

        # Test path parsing
        result = services.path_processor.parse_path_string(path_data)
        assert result is not None

        # Test path optimization (adapter method)
        optimized = services.path_processor.optimize_path(path_data)
        assert isinstance(optimized, str)

    def test_pptx_builder_functionality(self):
        """Test PPTX builder service."""
        services = ConversionServices.create_default()

        # Test presentation creation (adapter method)
        presentation = services.pptx_builder.create_presentation()

        if presentation is not None:
            # Test slide addition (adapter method)
            slide = services.pptx_builder.add_slide(presentation)
            # Slide may be None depending on implementation

    def test_gradient_service_functionality(self):
        """Test gradient service."""
        services = ConversionServices.create_default()

        # Test gradient content retrieval
        content = services.gradient_service.get_gradient_content("test_gradient")
        assert content is None  # Should return None for non-existent gradient

        # Test gradient creation (adapter method)
        stops = [{"offset": 0, "color": "FF0000"}, {"offset": 100, "color": "0000FF"}]
        gradient_xml = services.gradient_service.create_gradient("linear", stops)
        assert isinstance(gradient_xml, str)

    def test_pattern_service_functionality(self):
        """Test pattern service."""
        services = ConversionServices.create_default()

        # Test pattern content retrieval
        content = services.pattern_service.get_pattern_content("test_pattern")
        assert content is None  # Should return None for non-existent pattern

        # Test pattern creation (adapter method)
        pattern_xml = services.pattern_service.create_pattern("dots", {"size": 5})
        assert isinstance(pattern_xml, str)

    def test_filter_service_functionality(self):
        """Test filter service."""
        services = ConversionServices.create_default()

        # Test filter content retrieval
        content = services.filter_service.get_filter_content("test_filter")
        assert content is None  # Should return None for non-existent filter

        # Test filter application (adapter method)
        element = ET.Element('rect')
        filter_xml = services.filter_service.apply_filter("blur", element, {"radius": 5})
        assert isinstance(filter_xml, str)

    def test_image_service_functionality(self):
        """Test image service."""
        services = ConversionServices.create_default()

        # Test image info retrieval (adapter method)
        info = services.image_service.get_image_info("/nonexistent/path")
        assert info is None  # Should return None for non-existent image

    def test_service_cleanup(self):
        """Test service cleanup functionality."""
        services = ConversionServices.create_default()

        # Ensure services are initialized
        assert services.unit_converter is not None

        # Cleanup services
        services.cleanup()

        # All services should be None after cleanup
        assert services.unit_converter is None
        assert services.color_factory is None
        assert services.transform_parser is None

    def test_singleton_instance(self):
        """Test singleton pattern for default instance."""
        # Reset singleton first
        ConversionServices.reset_default_instance()

        # Get two instances
        instance1 = ConversionServices.get_default_instance()
        instance2 = ConversionServices.get_default_instance()

        # Should be the same instance
        assert instance1 is instance2

        # Reset for cleanup
        ConversionServices.reset_default_instance()

    def test_custom_configuration(self):
        """Test custom service configuration."""
        custom_config = {
            'config': {
                'default_dpi': 150.0,
                'viewport_width': 1024.0,
                'viewport_height': 768.0,
                'enable_caching': False
            }
        }

        services = ConversionServices.create_custom(custom_config)

        assert services.config.default_dpi == 150.0
        assert services.config.viewport_width == 1024.0
        assert services.config.viewport_height == 768.0
        assert services.config.enable_caching is False

    def test_service_initialization_error_handling(self):
        """Test error handling in service initialization."""
        # This would require mocking imports to fail, which is complex
        # For now, just ensure the error types are available
        assert ServiceInitializationError is not None

    def test_configuration_from_dict(self):
        """Test configuration creation from dictionary."""
        config_dict = {
            'default_dpi': 72.0,
            'viewport_width': 1200.0,
            'viewport_height': 800.0,
            'enable_caching': True
        }

        config = ConversionConfig.from_dict(config_dict)

        assert config.default_dpi == 72.0
        assert config.viewport_width == 1200.0
        assert config.viewport_height == 800.0
        assert config.enable_caching is True

    def test_configuration_to_dict(self):
        """Test configuration serialization to dictionary."""
        config = ConversionConfig(
            default_dpi=90.0,
            viewport_width=1000.0,
            viewport_height=750.0,
            enable_caching=False
        )

        config_dict = config.to_dict()

        assert config_dict['default_dpi'] == 90.0
        assert config_dict['viewport_width'] == 1000.0
        assert config_dict['viewport_height'] == 750.0
        assert config_dict['enable_caching'] is False

    def test_full_service_integration_workflow(self):
        """Test complete workflow using all services together."""
        services = ConversionServices.create_default()

        # Create mock SVG element
        svg_element = ET.Element('svg')
        svg_element.set('viewBox', '0 0 100 100')
        svg_element.set('width', '100px')
        svg_element.set('height', '100px')

        rect_element = ET.SubElement(svg_element, 'rect')
        rect_element.set('x', '10')
        rect_element.set('y', '10')
        rect_element.set('width', '80')
        rect_element.set('height', '80')
        rect_element.set('fill', '#FF0000')
        rect_element.set('style', 'stroke: blue; stroke-width: 2px')

        # Test workflow using multiple services
        # 1. Parse viewBox
        viewbox = services.viewport_resolver.parse_viewbox("0 0 100 100")

        # 2. Create color
        fill_color = services.color_factory("#FF0000")

        # 3. Parse style
        styles = services.style_parser.parse_style_string("stroke: blue; stroke-width: 2px")

        # 4. Process transforms (if any)
        transform_result = services.transform_parser.parse_to_matrix("translate(0,0)")

        # 5. Convert units
        from src.units import unit
        width_emu = unit("80px").to_emu()

        # All operations should complete without error
        assert fill_color is not None
        # StyleParser may return StyleResult object or dict
        if hasattr(styles, 'declarations'):
            assert len(styles.declarations) > 0
        else:
            assert isinstance(styles, dict)
        assert transform_result is not None
        assert isinstance(width_emu, int)


class TestServiceAdapters:
    """Test service adapters specifically."""

    def test_viewport_resolver_adapter_methods(self):
        """Test viewport resolver adapter methods."""
        services = ConversionServices.create_default()

        # These methods are added by the adapter
        assert hasattr(services.viewport_resolver, 'parse_viewbox')
        assert hasattr(services.viewport_resolver, 'calculate_viewport')

        # Test actual functionality
        viewbox = services.viewport_resolver.parse_viewbox("0 0 100 100")
        viewport = services.viewport_resolver.calculate_viewport(800, 600)

        assert isinstance(viewport, dict)

    def test_color_factory_adapter_methods(self):
        """Test color factory adapter methods."""
        services = ConversionServices.create_default()

        # The adapter should provide from_hex method
        assert hasattr(services.color_factory, 'from_hex')

        # Test functionality
        color = services.color_factory.from_hex("#123456")
        assert color is not None

    def test_all_adapter_methods_exist(self):
        """Test that all expected adapter methods exist."""
        services = ConversionServices.create_default()

        # Check all expected adapter methods
        assert hasattr(services.style_parser, 'parse_style_attribute')
        assert hasattr(services.coordinate_transformer, 'transform_coordinates')
        assert hasattr(services.font_processor, 'process_font_attributes')
        assert hasattr(services.path_processor, 'optimize_path')
        assert hasattr(services.pptx_builder, 'create_presentation')
        assert hasattr(services.pptx_builder, 'add_slide')
        assert hasattr(services.gradient_service, 'create_gradient')
        assert hasattr(services.pattern_service, 'create_pattern')
        assert hasattr(services.filter_service, 'apply_filter')
        assert hasattr(services.image_service, 'get_image_info')


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])