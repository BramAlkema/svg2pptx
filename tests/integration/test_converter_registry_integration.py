"""
Integration tests for converter registry pipeline integration.

Tests the integration between the main SVGToDrawingMLConverter and the 
ConverterRegistry system to ensure E2E tests properly exercise converter modules.
"""

import pytest
import tempfile
import os
from pathlib import Path
import logging
from unittest.mock import Mock, patch
from lxml import etree as ET

from src.svg2pptx import convert_svg_to_pptx
from src.svg2drawingml import SVGToDrawingMLConverter
from src.converters.base import ConverterRegistry, BaseConverter, ConversionContext, ConverterRegistryFactory

logger = logging.getLogger(__name__)


class MockConverter(BaseConverter):
    """Mock converter for testing registry integration."""
    
    def __init__(self, element_types: list, conversion_result: str = "<mock>converted</mock>"):
        super().__init__()
        self.supported_elements = element_types
        self.conversion_result = conversion_result
        self.convert_called = False
        self.last_element = None
        self.last_context = None
    
    def can_convert(self, element: ET.Element) -> bool:
        """Check if this converter can handle the element."""
        tag = element.tag.split('}')[-1] if '}' in element.tag else element.tag
        return tag in self.supported_elements
    
    def convert(self, element: ET.Element, context: ConversionContext) -> str:
        """Convert element to DrawingML."""
        self.convert_called = True
        self.last_element = element
        self.last_context = context
        return self.conversion_result


class TestConverterRegistryIntegration:
    """Test converter registry integration with main pipeline."""
    
    @pytest.fixture
    def sample_svg(self):
        """Simple SVG for testing."""
        return '''<?xml version="1.0"?>
<svg width="100" height="100" xmlns="http://www.w3.org/2000/svg">
    <rect x="10" y="10" width="50" height="50" fill="red"/>
    <circle cx="75" cy="25" r="15" fill="blue"/>
</svg>'''
    
    @pytest.fixture
    def registry_with_mocks(self):
        """Registry with mock converters for testing."""
        registry = ConverterRegistry()
        
        # Add mock converters for different element types
        rect_converter = MockConverter(['rect'], '<rect>mock-rect</rect>')
        circle_converter = MockConverter(['circle'], '<circle>mock-circle</circle>')
        
        registry.register(rect_converter)
        registry.register(circle_converter)
        
        return registry, rect_converter, circle_converter
    
    def test_registry_integration_basic(self, sample_svg, registry_with_mocks):
        """Test basic registry integration with main converter."""
        registry, rect_converter, circle_converter = registry_with_mocks
        
        # Create converter with registry integration
        main_converter = SVGToDrawingMLConverter()
        
        # Mock the registry factory to test integration
        with patch.object(ConverterRegistryFactory, 'get_registry', return_value=registry):
            # Convert SVG - this should route through registry
            result = main_converter.convert(sample_svg)
            
            # Verify both mock converters were called
            assert rect_converter.convert_called, "Rectangle converter should have been called"
            assert circle_converter.convert_called, "Circle converter should have been called"
            
            # Verify correct element types were passed
            assert rect_converter.last_element.tag.endswith('rect')
            assert circle_converter.last_element.tag.endswith('circle')
    
    def test_registry_integration_e2e(self, sample_svg):
        """Test E2E integration with real converter modules."""
        # This test verifies that when we integrate the registry,
        # E2E tests will actually exercise converter modules
        
        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as temp_file:
            try:
                # Convert using the main API
                result_path = convert_svg_to_pptx(sample_svg, temp_file.name)
                assert os.path.exists(result_path)
                
                # Verify PPTX was created
                file_size = os.path.getsize(result_path)
                assert file_size > 20000, f"PPTX file too small: {file_size} bytes"
                
                logger.info(f"E2E conversion successful: {file_size} bytes")
                
            finally:
                if os.path.exists(temp_file.name):
                    os.unlink(temp_file.name)
    
    def test_registry_fallback_behavior(self, registry_with_mocks):
        """Test registry fallback when no converter is found."""
        registry, rect_converter, circle_converter = registry_with_mocks
        
        # Create element that no converter can handle
        unsupported_svg = '''<?xml version="1.0"?>
<svg width="100" height="100" xmlns="http://www.w3.org/2000/svg">
    <polygon points="50,10 90,90 10,90" fill="green"/>
</svg>'''
        
        main_converter = SVGToDrawingMLConverter()
        
        with patch.object(ConverterRegistryFactory, 'get_registry', return_value=registry):
            # Should handle unsupported elements gracefully
            result = main_converter.convert(unsupported_svg)
            
            # Neither mock converter should have been called
            assert not rect_converter.convert_called
            assert not circle_converter.convert_called
            
            # Should still produce some output (fallback behavior)
            assert isinstance(result, str)
    
    def test_registry_error_handling(self, sample_svg, registry_with_mocks):
        """Test error handling in registry integration."""
        registry, rect_converter, circle_converter = registry_with_mocks
        
        # Make one converter raise an exception
        def failing_convert(element, context):
            raise ValueError("Mock conversion error")
        
        rect_converter.convert = failing_convert
        
        main_converter = SVGToDrawingMLConverter()
        
        with patch.object(ConverterRegistryFactory, 'get_registry', return_value=registry):
            # Should handle converter errors gracefully
            result = main_converter.convert(sample_svg)
            
            # Should still process other elements
            assert circle_converter.convert_called, "Non-failing converter should still be called"
            
            # Should produce output despite error
            assert isinstance(result, str)
    
    def test_converter_context_passing(self, sample_svg, registry_with_mocks):
        """Test that conversion context is properly passed to converters."""
        registry, rect_converter, circle_converter = registry_with_mocks
        
        main_converter = SVGToDrawingMLConverter()
        
        with patch.object(ConverterRegistryFactory, 'get_registry', return_value=registry):
            result = main_converter.convert(sample_svg)
            
            # Verify context was passed to converters
            assert rect_converter.last_context is not None
            assert circle_converter.last_context is not None
            
            # Verify context has required attributes
            context = rect_converter.last_context
            assert hasattr(context, 'coordinate_system')
            assert hasattr(context, 'gradients')
    
    def test_registry_performance_impact(self, sample_svg):
        """Test performance impact of registry integration."""
        import time
        
        # Time the conversion
        start_time = time.time()
        
        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as temp_file:
            try:
                convert_svg_to_pptx(sample_svg, temp_file.name)
                conversion_time = time.time() - start_time
                
                # Should complete reasonably quickly (under 5 seconds)
                assert conversion_time < 5.0, f"Conversion took too long: {conversion_time:.2f}s"
                
                logger.info(f"Conversion completed in {conversion_time:.3f}s")
                
            finally:
                if os.path.exists(temp_file.name):
                    os.unlink(temp_file.name)


class TestConverterRegistryFactory:
    """Test factory pattern for converter instantiation."""
    
    def test_registry_factory_creation(self):
        """Test factory method for creating populated registry."""
        # This will test the factory pattern once implemented
        pass
    
    def test_converter_discovery(self):
        """Test automatic discovery of converter modules."""
        # This will test auto-discovery once implemented
        pass
    
    def test_registry_singleton_behavior(self):
        """Test registry singleton pattern."""
        # This will test singleton behavior once implemented
        pass


# Integration test to verify converter modules are exercised
class TestConverterModulesExercised:
    """Test that converter modules are actually exercised in E2E tests."""
    
    def test_shapes_converter_exercised(self):
        """Test that shapes converter is called during E2E conversion."""
        from src.converters import shapes
        
        svg_with_shapes = '''<?xml version="1.0"?>
<svg width="200" height="200" xmlns="http://www.w3.org/2000/svg">
    <rect x="10" y="10" width="50" height="50" fill="red"/>
    <circle cx="100" cy="50" r="30" fill="blue"/>
    <ellipse cx="150" cy="100" rx="40" ry="20" fill="green"/>
</svg>'''
        
        with patch.object(shapes, 'RectangleConverter', wraps=shapes.RectangleConverter) as mock_rect:
            with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as temp_file:
                try:
                    convert_svg_to_pptx(svg_with_shapes, temp_file.name)
                    # This test will verify the converter was called once registry is integrated
                    # For now, it serves as a placeholder for future validation
                    logger.info("Shapes converter integration test completed")
                    
                finally:
                    if os.path.exists(temp_file.name):
                        os.unlink(temp_file.name)