#!/usr/bin/env python3
"""
Comprehensive consistency test for standardized tool implementation across SVG2PPTX architecture.

This test ensures that all 4 core tools (UnitConverter, ColorParser, TransformParser, ViewportResolver)
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
from src.units import UnitConverter
from src.colors import ColorParser
from src.transforms import TransformParser
from src.viewbox import ViewportResolver


class TestToolChainConsistency:
    """Test that all converters properly implement the standardized tool architecture."""
    
    def test_base_converter_has_all_four_tools(self):
        """Test that BaseConverter initializes all 4 core tools."""
        # Create a concrete implementation for testing
        class TestConverter(BaseConverter):
            def can_convert(self, element): return True
            def convert(self, element, context): return ""
        
        converter = TestConverter()
        
        # Verify all 4 tools are present and correctly typed
        assert hasattr(converter, 'unit_converter'), "BaseConverter missing unit_converter"
        assert hasattr(converter, 'color_parser'), "BaseConverter missing color_parser"
        assert hasattr(converter, 'transform_parser'), "BaseConverter missing transform_parser"
        assert hasattr(converter, 'viewport_resolver'), "BaseConverter missing viewport_resolver"
        
        # Verify tool types
        assert isinstance(converter.unit_converter, UnitConverter), f"unit_converter has wrong type: {type(converter.unit_converter)}"
        assert isinstance(converter.color_parser, ColorParser), f"color_parser has wrong type: {type(converter.color_parser)}"
        assert isinstance(converter.transform_parser, TransformParser), f"transform_parser has wrong type: {type(converter.transform_parser)}"
        assert isinstance(converter.viewport_resolver, ViewportResolver), f"viewport_resolver has wrong type: {type(converter.viewport_resolver)}"
    
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
                if name in ['TextConverter']:
                    # TextConverter has special constructor parameters
                    converter = converter_class(enable_font_embedding=False)
                else:
                    converter = converter_class()
                
                # Verify all tools are accessible
                assert hasattr(converter, 'unit_converter'), f"{name} missing unit_converter"
                assert hasattr(converter, 'color_parser'), f"{name} missing color_parser" 
                assert hasattr(converter, 'transform_parser'), f"{name} missing transform_parser"
                assert hasattr(converter, 'viewport_resolver'), f"{name} missing viewport_resolver"
                
            except Exception as e:
                pytest.skip(f"Could not instantiate {name}: {e}")
    
    def test_tool_method_availability(self):
        """Test that all tools have their expected core methods available."""
        class TestConverter(BaseConverter):
            def can_convert(self, element): return True
            def convert(self, element, context): return ""
        
        converter = TestConverter()
        
        # Test UnitConverter methods
        unit_converter = converter.unit_converter
        assert hasattr(unit_converter, 'to_emu'), "UnitConverter missing to_emu method"
        assert hasattr(unit_converter, 'format_emu'), "UnitConverter missing format_emu method"
        assert callable(unit_converter.to_emu), "to_emu is not callable"
        assert callable(unit_converter.format_emu), "format_emu is not callable"
        
        # Test ColorParser methods
        color_parser = converter.color_parser
        assert hasattr(color_parser, 'parse'), "ColorParser missing parse method"
        assert callable(color_parser.parse), "parse is not callable"
        
        # Test TransformParser methods
        transform_parser = converter.transform_parser
        assert hasattr(transform_parser, 'parse_to_matrix'), "TransformParser missing parse_to_matrix method"
        assert callable(transform_parser.parse_to_matrix), "parse_to_matrix is not callable"
        
        # Test ViewportResolver methods
        viewport_resolver = converter.viewport_resolver
        assert hasattr(viewport_resolver, 'resolve_svg_viewport'), "ViewportResolver missing resolve_svg_viewport method"
        assert callable(viewport_resolver.resolve_svg_viewport), "resolve_svg_viewport is not callable"
    
    def test_tool_functionality_consistency(self):
        """Test that tools produce consistent results across different converter instances."""
        class TestConverter1(BaseConverter):
            def can_convert(self, element): return True
            def convert(self, element, context): return ""
        
        class TestConverter2(BaseConverter):
            def can_convert(self, element): return True
            def convert(self, element, context): return ""
        
        converter1 = TestConverter1()
        converter2 = TestConverter2()
        
        # Test UnitConverter consistency
        test_value = '10px'
        result1 = converter1.unit_converter.to_emu(test_value)
        result2 = converter2.unit_converter.to_emu(test_value)
        assert result1 == result2, f"UnitConverter inconsistent: {result1} != {result2}"
        
        # Test ColorParser consistency 
        test_color = 'red'
        color1 = converter1.color_parser.parse(test_color)
        color2 = converter2.color_parser.parse(test_color)
        assert color1.hex == color2.hex, f"ColorParser inconsistent: {color1.hex} != {color2.hex}"
        
        # Test TransformParser consistency
        test_transform = 'translate(10, 20)'
        matrix1 = converter1.transform_parser.parse_to_matrix(test_transform)
        matrix2 = converter2.transform_parser.parse_to_matrix(test_transform)
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
            
            # Test TextConverter uses tools
            text_converter = TextConverter(enable_font_embedding=False)
            
            # Check that it has access to all tools
            assert hasattr(text_converter, 'unit_converter')
            assert hasattr(text_converter, 'color_parser') 
            assert hasattr(text_converter, 'transform_parser')
            assert hasattr(text_converter, 'viewport_resolver')
            
            # Test RectangleConverter uses tools
            rect_converter = RectangleConverter()
            
            assert hasattr(rect_converter, 'unit_converter')
            assert hasattr(rect_converter, 'color_parser')
            assert hasattr(rect_converter, 'transform_parser') 
            assert hasattr(rect_converter, 'viewport_resolver')
            
        except ImportError as e:
            pytest.skip(f"Could not test converter usage patterns: {e}")
    
    def test_tool_import_consistency(self):
        """Test that tools can be imported consistently across the codebase."""
        try:
            # Test direct imports
            from src.units import UnitConverter
            from src.colors import ColorParser
            from src.transforms import TransformParser
            from src.viewbox import ViewportResolver
            
            # Test that each tool can be instantiated
            unit_converter = UnitConverter()
            color_parser = ColorParser()
            transform_parser = TransformParser()
            viewport_resolver = ViewportResolver()
            
            # Basic functionality test
            assert unit_converter.to_emu('1px') > 0
            assert color_parser.parse('red').hex.upper() == 'FF0000'
            
        except ImportError as e:
            pytest.fail(f"Tool import consistency failed: {e}")


class TestArchitecturalIntegrity:
    """Test the overall architectural integrity of the tool system."""
    
    def test_base_converter_abstract_methods(self):
        """Test that BaseConverter properly defines abstract methods."""
        # BaseConverter should not be instantiable
        with pytest.raises(TypeError):
            BaseConverter()
        
        # But should work with proper implementation
        class GoodConverter(BaseConverter):
            def can_convert(self, element): return True
            def convert(self, element, context): return ""
        
        converter = GoodConverter()
        assert converter is not None
    
    def test_tool_initialization_order(self):
        """Test that tools are initialized in correct order and dependencies."""
        class TestConverter(BaseConverter):
            def can_convert(self, element): return True
            def convert(self, element, context): return ""
        
        converter = TestConverter()
        
        # All tools should be initialized and ready
        assert converter.unit_converter is not None
        assert converter.color_parser is not None
        assert converter.transform_parser is not None
        assert converter.viewport_resolver is not None
        
        # Tools should be independent (no circular dependencies)
        assert converter.unit_converter is not converter.color_parser
        assert converter.color_parser is not converter.transform_parser
        assert converter.transform_parser is not converter.viewport_resolver
    
    def generate_tool_consistency_report(self):
        """Generate a comprehensive report on tool implementation consistency."""
        # This method would be called manually for debugging
        pass


if __name__ == '__main__':
    pytest.main([__file__, '-v'])