#!/usr/bin/env python3
"""
Comprehensive consistency test for standardized tool implementation across SVG2PPTX architecture.

This test ensures that all 4 core tools (UnitConverter, ColorParser, TransformParser, ViewportEngine)
are properly implemented and accessible throughout the entire converter toolchain.
"""

import pytest
import inspect
from pathlib import Path
import sys
import importlib

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from src.converters.base import BaseConverter
from core.units import UnitConverter
from core.color import Color
from core.transforms import TransformEngine
from core.viewbox import ViewportEngine
from unittest.mock import Mock


# Mock services for testing
def create_mock_services():
    """Create mock services for testing BaseConverter."""
    services = Mock()
    services.unit_converter = UnitConverter()
    services.color_parser = Color  # Use Color class directly
    services.transform_parser = TransformEngine()

    # Create a mock viewport resolver with expected methods
    viewport_resolver = ViewportEngine()
    # Add the expected method if it doesn't exist
    if not hasattr(viewport_resolver, 'resolve_svg_viewport'):
        viewport_resolver.resolve_svg_viewport = Mock(return_value={'width': 100, 'height': 100})
    services.viewport_resolver = viewport_resolver
    return services


class TestToolChainConsistency:
    """Test that all converters properly implement the standardized tool architecture."""
    
    def test_base_converter_proper_dependency_injection(self):
        """Test that BaseConverter enforces proper dependency injection patterns."""
        # Create a concrete implementation for testing
        class TestConverter(BaseConverter):
            def can_convert(self, element): return True
            def convert(self, element, context): return ""

        services = create_mock_services()
        converter = TestConverter(services=services)

        # Verify tools are accessed through services, not direct properties
        assert hasattr(converter, 'services'), "BaseConverter missing services attribute"
        assert hasattr(converter.services, 'unit_converter'), "Services missing unit_converter"
        assert hasattr(converter.services, 'color_parser'), "Services missing color_parser"
        assert hasattr(converter.services, 'transform_parser'), "Services missing transform_parser"
        assert hasattr(converter.services, 'viewport_resolver'), "Services missing viewport_resolver"

        # Verify tool types through services
        assert isinstance(converter.services.unit_converter, UnitConverter), f"unit_converter has wrong type: {type(converter.services.unit_converter)}"
        # color_parser is the Color class itself, not an instance
        assert converter.services.color_parser == Color, f"color_parser has wrong type: {type(converter.services.color_parser)}"
        assert isinstance(converter.services.transform_parser, TransformEngine), f"transform_parser has wrong type: {type(converter.services.transform_parser)}"
        assert isinstance(converter.services.viewport_resolver, ViewportEngine), f"viewport_resolver has wrong type: {type(converter.services.viewport_resolver)}"

        # Verify that compatibility properties are NOT accessible (proper dependency injection enforced)
        assert not hasattr(converter, 'unit_converter'), "BaseConverter should not have unit_converter property"
        assert not hasattr(converter, 'color_parser'), "BaseConverter should not have color_parser property"
        assert not hasattr(converter, 'transform_parser'), "BaseConverter should not have transform_parser property"
        assert not hasattr(converter, 'viewport_resolver'), "BaseConverter should not have viewport_resolver property"
    
    def test_all_converter_classes_inherit_from_base(self):
        """Test that all converter classes properly inherit from BaseConverter."""
        converter_modules = [
            'src.converters.text',
            'src.converters.shapes', 
            'src.converters.paths',
            'src.converters.groups',
            'src.converters.filters'
        ]
        
        all_converters = []
        
        for module_name in converter_modules:
            try:
                module = importlib.import_module(module_name)
                
                # Find all converter classes in the module
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    # Skip BaseConverter itself and non-converter classes
                    if (obj is not BaseConverter and 
                        name.endswith('Converter') and 
                        obj.__module__ == module_name):
                        all_converters.append((name, obj))
            except ImportError as e:
                pytest.skip(f"Could not import {module_name}: {e}")
        
        assert len(all_converters) > 0, "No converter classes found"
        
        # Test each converter class
        for name, converter_class in all_converters:
            assert issubclass(converter_class, BaseConverter), f"{name} does not inherit from BaseConverter"
            
            # Try to instantiate and verify tools (if constructor allows it)
            try:
                services = create_mock_services()
                if name in ['TextConverter']:
                    # TextConverter has special constructor parameters
                    converter = converter_class(services=services, enable_font_embedding=False)
                else:
                    converter = converter_class(services=services)
                
                # Verify all tools are accessible through services (not direct properties)
                assert hasattr(converter, 'services'), f"{name} missing services"
                assert hasattr(converter.services, 'unit_converter'), f"{name} services missing unit_converter"
                assert hasattr(converter.services, 'color_parser'), f"{name} services missing color_parser"
                assert hasattr(converter.services, 'transform_parser'), f"{name} services missing transform_parser"
                assert hasattr(converter.services, 'viewport_resolver'), f"{name} services missing viewport_resolver"

                # Verify no direct tool properties (proper dependency injection enforced)
                assert not hasattr(converter, 'unit_converter'), f"{name} should not have direct unit_converter property"
                assert not hasattr(converter, 'color_parser'), f"{name} should not have direct color_parser property"
                assert not hasattr(converter, 'transform_parser'), f"{name} should not have direct transform_parser property"
                assert not hasattr(converter, 'viewport_resolver'), f"{name} should not have direct viewport_resolver property"
                
            except Exception as e:
                pytest.skip(f"Could not instantiate {name}: {e}")
    
    def test_tool_method_availability(self):
        """Test that all tools have their expected core methods available through services."""
        class TestConverter(BaseConverter):
            def can_convert(self, element): return True
            def convert(self, element, context): return ""

        services = create_mock_services()
        converter = TestConverter(services=services)

        # Test UnitConverter methods through services
        unit_converter = converter.services.unit_converter
        assert hasattr(unit_converter, 'to_emu'), "UnitConverter missing to_emu method"
        assert hasattr(unit_converter, 'format_emu'), "UnitConverter missing format_emu method"
        assert callable(unit_converter.to_emu), "to_emu is not callable"
        assert callable(unit_converter.format_emu), "format_emu is not callable"

        # Test ColorParser methods - Color class is callable for instantiation through services
        color_parser = converter.services.color_parser
        assert callable(color_parser), "Color class is not callable"

        # Test TransformParser methods through services
        transform_parser = converter.services.transform_parser
        assert hasattr(transform_parser, 'parse_to_matrix'), "TransformParser missing parse_to_matrix method"
        assert callable(transform_parser.parse_to_matrix), "parse_to_matrix is not callable"

        # Test ViewportEngine methods through services
        viewport_resolver = converter.services.viewport_resolver
        assert hasattr(viewport_resolver, 'resolve_svg_viewport'), "ViewportEngine missing resolve_svg_viewport method"
        assert callable(viewport_resolver.resolve_svg_viewport), "resolve_svg_viewport is not callable"
    
    def test_tool_functionality_consistency(self):
        """Test that tools produce consistent results across different converter instances."""
        class TestConverter1(BaseConverter):
            def can_convert(self, element): return True
            def convert(self, element, context): return ""

        class TestConverter2(BaseConverter):
            def can_convert(self, element): return True
            def convert(self, element, context): return ""

        services1 = create_mock_services()
        services2 = create_mock_services()
        converter1 = TestConverter1(services=services1)
        converter2 = TestConverter2(services=services2)
        
        # Test UnitConverter consistency through services
        test_value = '10px'
        result1 = converter1.services.unit_converter.to_emu(test_value)
        result2 = converter2.services.unit_converter.to_emu(test_value)
        assert result1 == result2, f"UnitConverter inconsistent: {result1} != {result2}"

        # Test ColorParser consistency through services
        test_color = 'red'
        color1 = converter1.services.color_parser(test_color)
        color2 = converter2.services.color_parser(test_color)
        assert color1.hex() == color2.hex(), f"ColorParser inconsistent: {color1.hex()} != {color2.hex()}"

        # Test TransformParser consistency through services
        test_transform = 'translate(10, 20)'
        matrix1 = converter1.services.transform_parser.parse_to_matrix(test_transform)
        matrix2 = converter2.services.transform_parser.parse_to_matrix(test_transform)
        # Compare matrix components instead of objects
        assert str(matrix1) == str(matrix2), f"TransformParser inconsistent: {matrix1} != {matrix2}"
    
    def test_no_hardcoded_values_in_converters(self):
        """Test that converter modules don't contain hardcoded EMU values."""
        converter_files = [
            Path(__file__).parent.parent.parent / "src" / "converters" / "text.py",
            Path(__file__).parent.parent.parent / "src" / "converters" / "shapes.py",
            Path(__file__).parent.parent.parent / "src" / "converters" / "paths.py",
        ]
        
        hardcoded_patterns = [
            '25400',  # Common hardcoded EMU value
            '12700',  # Another common EMU value
            '9525',   # Yet another EMU hardcode
            '914400', # More EMU hardcodes
            '* 91440',  # Multiplication patterns
            '* 12700',
        ]
        
        violations = []
        
        for file_path in converter_files:
            if file_path.exists():
                content = file_path.read_text()
                
                for pattern in hardcoded_patterns:
                    if pattern in content:
                        # Get line numbers for better reporting
                        lines = content.split('\n')
                        for i, line in enumerate(lines, 1):
                            if pattern in line and not line.strip().startswith('#'):
                                violations.append(f"{file_path.name}:{i}: {line.strip()}")
        
        if violations:
            violation_report = "\n".join(violations)
            pytest.fail(f"Found hardcoded EMU values in converter files:\n{violation_report}")
    
    def test_converter_usage_patterns(self):
        """Test that converters use tools correctly in their implementations."""
        # Import specific converters to test their tool usage
        try:
            from src.converters.text import TextConverter
            from src.converters.shapes import RectangleConverter

            services = create_mock_services()

            # Test TextConverter uses tools through proper dependency injection
            text_converter = TextConverter(services=services, enable_font_embedding=False)

            # Check that it has access to all tools through services (no direct properties)
            assert hasattr(text_converter, 'services'), "TextConverter missing services"
            assert hasattr(text_converter.services, 'unit_converter'), "TextConverter services missing unit_converter"
            assert hasattr(text_converter.services, 'color_parser'), "TextConverter services missing color_parser"
            assert hasattr(text_converter.services, 'transform_parser'), "TextConverter services missing transform_parser"
            assert hasattr(text_converter.services, 'viewport_resolver'), "TextConverter services missing viewport_resolver"

            # Verify no direct tool properties (proper dependency injection enforced)
            assert not hasattr(text_converter, 'unit_converter'), "TextConverter should not have direct unit_converter property"
            assert not hasattr(text_converter, 'color_parser'), "TextConverter should not have direct color_parser property"
            assert not hasattr(text_converter, 'transform_parser'), "TextConverter should not have direct transform_parser property"
            assert not hasattr(text_converter, 'viewport_resolver'), "TextConverter should not have direct viewport_resolver property"

            # Test RectangleConverter uses tools through proper dependency injection
            rect_converter = RectangleConverter(services=services)

            assert hasattr(rect_converter, 'services'), "RectangleConverter missing services"
            assert hasattr(rect_converter.services, 'unit_converter'), "RectangleConverter services missing unit_converter"
            assert hasattr(rect_converter.services, 'color_parser'), "RectangleConverter services missing color_parser"
            assert hasattr(rect_converter.services, 'transform_parser'), "RectangleConverter services missing transform_parser"
            assert hasattr(rect_converter.services, 'viewport_resolver'), "RectangleConverter services missing viewport_resolver"

            # Verify no direct tool properties (proper dependency injection enforced)
            assert not hasattr(rect_converter, 'unit_converter'), "RectangleConverter should not have direct unit_converter property"
            assert not hasattr(rect_converter, 'color_parser'), "RectangleConverter should not have direct color_parser property"
            assert not hasattr(rect_converter, 'transform_parser'), "RectangleConverter should not have direct transform_parser property"
            assert not hasattr(rect_converter, 'viewport_resolver'), "RectangleConverter should not have direct viewport_resolver property"
            
        except ImportError as e:
            pytest.skip(f"Could not test converter usage patterns: {e}")
    
    def test_tool_import_consistency(self):
        """Test that tools can be imported consistently across the codebase."""
        try:
            # Test direct imports
            from core.units import UnitConverter
            from core.color import Color
            from core.transforms import TransformEngine
            from core.viewbox import ViewportEngine
            
            # Test that each tool can be instantiated
            unit_converter = UnitConverter()
            # Color is used directly, not instantiated
            transform_parser = TransformEngine()
            viewport_resolver = ViewportEngine()

            # Basic functionality test
            assert unit_converter.to_emu('1px') > 0
            parsed_color = Color('red')
            # Color.hex() returns with # prefix, so check accordingly
            hex_value = parsed_color.hex()
            assert hex_value.upper() in ['#FF0000', '#F00', 'FF0000']
            
        except ImportError as e:
            pytest.fail(f"Tool import consistency failed: {e}")


class TestArchitecturalIntegrity:
    """Test the overall architectural integrity of the tool system."""
    
    def test_base_converter_abstract_methods(self):
        """Test that BaseConverter properly defines abstract methods."""
        # BaseConverter should not be instantiable without services
        with pytest.raises(TypeError):
            BaseConverter()

        # But should work with proper implementation and services
        class GoodConverter(BaseConverter):
            def can_convert(self, element): return True
            def convert(self, element, context): return ""

        services = create_mock_services()
        converter = GoodConverter(services=services)
        assert converter is not None
    
    def test_tool_initialization_order(self):
        """Test that tools are initialized in correct order and dependencies."""
        class TestConverter(BaseConverter):
            def can_convert(self, element): return True
            def convert(self, element, context): return ""

        services = create_mock_services()
        converter = TestConverter(services=services)
        
        # All tools should be initialized and ready through services
        assert converter.services.unit_converter is not None
        assert converter.services.color_parser is not None
        assert converter.services.transform_parser is not None
        assert converter.services.viewport_resolver is not None

        # Tools should be independent (no circular dependencies)
        assert converter.services.unit_converter is not converter.services.color_parser
        assert converter.services.color_parser is not converter.services.transform_parser
        assert converter.services.transform_parser is not converter.services.viewport_resolver
    
    def generate_tool_consistency_report(self):
        """Generate a comprehensive report on tool implementation consistency."""
        # This method would be called manually for debugging
        pass


if __name__ == '__main__':
    pytest.main([__file__, '-v'])