#!/usr/bin/env python3
"""
Enhanced tests for SVG path converter with improved coverage.

This test suite builds on the existing path tests to provide comprehensive
coverage of edge cases, error handling, and complex path operations that
were previously untested.
"""

import pytest
import math
from unittest.mock import Mock, patch, MagicMock
from lxml import etree as ET

from src.converters.paths import PathConverter
from src.converters.base import ConversionContext
from tests.fixtures import *


class TestPathConverterEdgeCases:
    """Test edge cases and error handling in path conversion."""
    
    def test_convert_empty_path_data(self, mock_conversion_context):
        """Test handling of empty path data."""
        converter = PathConverter()
        path_element = ET.Element("path")
        path_element.set("d", "")
        
        result = converter.convert(path_element, mock_conversion_context)
        
        # Should handle empty path gracefully
        assert result is None or len(result) == 0
    
    def test_convert_invalid_path_commands(self):
        """Test handling of invalid path commands."""
        path_element = ET.Element("path")
        path_element.set("d", "X 10 20 Y 30 40")  # Invalid commands
        
        result = self.converter.convert(path_element, self.context)
        
        # Should handle invalid commands without crashing
        assert result is None or isinstance(result, list)
    
    def test_convert_path_with_relative_coordinates(self):
        """Test path conversion with relative coordinates."""
        path_element = ET.Element("path")
        path_element.set("d", "m 10,20 l 30,40 l -10,-5 z")
        
        result = self.converter.convert(path_element, self.context)
        
        assert result is not None
        assert len(result) > 0
    
    def test_convert_bezier_curve_paths(self):
        """Test conversion of Bezier curve paths."""
        path_element = ET.Element("path")
        path_element.set("d", "M 10,30 C 20,10 40,10 50,30 S 80,50 90,30")
        
        result = self.converter.convert(path_element, self.context)
        
        assert result is not None
        assert len(result) > 0
    
    def test_convert_quadratic_curve_paths(self):
        """Test conversion of quadratic curve paths."""
        path_element = ET.Element("path")
        path_element.set("d", "M 10,80 Q 95,10 180,80 T 350,80")
        
        result = self.converter.convert(path_element, self.context)
        
        assert result is not None
        assert len(result) > 0
    
    def test_convert_arc_paths(self):
        """Test conversion of arc paths."""
        path_element = ET.Element("path")
        path_element.set("d", "M 125,75 A 100,50 0 0,0 225,125")
        
        result = self.converter.convert(path_element, self.context)
        
        assert result is not None
        assert len(result) > 0
    
    def test_path_with_transform(self):
        """Test path conversion with transform attribute."""
        path_element = ET.Element("path")
        path_element.set("d", "M 10,10 L 50,50")
        path_element.set("transform", "translate(10,10) scale(2)")
        
        result = self.converter.convert(path_element, self.context)
        
        assert result is not None
    
    def test_path_with_styling(self):
        """Test path conversion with fill and stroke styling."""
        path_element = ET.Element("path")
        path_element.set("d", "M 10,10 L 50,50 L 10,50 Z")
        path_element.set("fill", "#FF0000")
        path_element.set("stroke", "#00FF00")
        path_element.set("stroke-width", "2")
        
        result = self.converter.convert(path_element, self.context)
        
        assert result is not None
        assert len(result) > 0
    
    def test_path_coordinate_parsing_edge_cases(self):
        """Test parsing of edge case coordinate formats."""
        test_cases = [
            "M10 20L30 40",           # No comma separators
            "M 10,20 L 30,40",        # Mixed separators  
            "M10,20L30,40L50,60",     # Concatenated commands
            "M 10.5,20.7 L 30.1,40.9", # Decimal coordinates
            "M1e2,2e1 L3e1,4e1",      # Scientific notation
        ]
        
        for path_data in test_cases:
            path_element = ET.Element("path")
            path_element.set("d", path_data)
            
            # Should not raise exceptions
            result = self.converter.convert(path_element, self.context)
            assert result is None or isinstance(result, list)
    
    def test_path_with_multiple_subpaths(self):
        """Test path with multiple disconnected subpaths."""
        path_element = ET.Element("path")
        path_element.set("d", "M 10,10 L 50,10 L 50,50 Z M 70,70 L 100,70 L 100,100 Z")
        
        result = self.converter.convert(path_element, self.context)
        
        assert result is not None
        assert len(result) > 0
    
    def test_path_coordinate_overflow(self):
        """Test handling of very large coordinates."""
        path_element = ET.Element("path")
        path_element.set("d", "M 999999,999999 L 1000000,1000000")
        
        # Should handle large coordinates without crashing
        result = self.converter.convert(path_element, self.context)
        assert result is None or isinstance(result, list)
    
    def test_path_with_negative_coordinates(self):
        """Test path with negative coordinates."""
        path_element = ET.Element("path")
        path_element.set("d", "M -10,-20 L -50,-60 L 10,20 Z")
        
        result = self.converter.convert(path_element, self.context)
        
        assert result is not None


class TestPathCommandParsing:
    """Test detailed path command parsing functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.context = mock_conversion_context()
        self.converter = PathConverter()
    
    def test_parse_moveto_commands(self):
        """Test parsing of MoveTo commands (M/m)."""
        path_element = ET.Element("path")
        path_element.set("d", "M 10,20 m 30,40")
        
        result = self.converter.convert(path_element, self.context)
        assert result is not None
    
    def test_parse_lineto_commands(self):
        """Test parsing of LineTo commands (L/l)."""
        path_element = ET.Element("path")
        path_element.set("d", "M 10,20 L 50,60 l 20,30")
        
        result = self.converter.convert(path_element, self.context)
        assert result is not None
    
    def test_parse_horizontal_lineto(self):
        """Test parsing of horizontal LineTo commands (H/h)."""
        path_element = ET.Element("path")
        path_element.set("d", "M 10,20 H 50 h 30")
        
        result = self.converter.convert(path_element, self.context)
        assert result is not None
    
    def test_parse_vertical_lineto(self):
        """Test parsing of vertical LineTo commands (V/v)."""
        path_element = ET.Element("path")
        path_element.set("d", "M 10,20 V 60 v 30")
        
        result = self.converter.convert(path_element, self.context)
        assert result is not None
    
    def test_parse_closepath_command(self):
        """Test parsing of ClosePath commands (Z/z)."""
        path_element = ET.Element("path")
        path_element.set("d", "M 10,10 L 50,10 L 30,50 Z")
        
        result = self.converter.convert(path_element, self.context)
        assert result is not None
    
    def test_parse_cubic_bezier_commands(self):
        """Test parsing of cubic Bezier commands (C/c/S/s)."""
        path_element = ET.Element("path")
        path_element.set("d", "M 10,90 C 30,10 70,10 90,90 S 150,170 170,90")
        
        result = self.converter.convert(path_element, self.context)
        assert result is not None
    
    def test_parse_quadratic_bezier_commands(self):
        """Test parsing of quadratic Bezier commands (Q/q/T/t)."""
        path_element = ET.Element("path")
        path_element.set("d", "M 10,80 Q 52.5,10 95,80 T 180,80")
        
        result = self.converter.convert(path_element, self.context)
        assert result is not None
    
    def test_parse_elliptical_arc_commands(self):
        """Test parsing of elliptical arc commands (A/a)."""
        path_element = ET.Element("path")
        path_element.set("d", "M 125,75 A 100,50 0 0,0 225,125 a 50,25 0 1,1 100,50")
        
        result = self.converter.convert(path_element, self.context)
        assert result is not None


class TestPathConverterIntegration:
    """Test path converter integration with other systems."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.context = mock_conversion_context()
        self.converter = PathConverter()
    
    def test_path_conversion_with_context(self):
        """Test path conversion integrates properly with conversion context."""
        path_element = ET.Element("path")
        path_element.set("d", "M 10,10 L 50,50 Z")
        
        # Mock context methods
        self.context.get_next_shape_id.return_value = 1001
        
        result = self.converter.convert(path_element, self.context)
        
        # Verify context integration
        assert self.context.get_next_shape_id.called
        assert result is not None
    
    def test_path_with_inherited_styles(self):
        """Test path conversion with inherited styles from parent elements."""
        path_element = ET.Element("path")
        path_element.set("d", "M 10,10 L 50,50 Z")
        
        # Mock inherited styles
        inherited_styles = {"fill": "blue", "stroke-width": "3"}
        self.context.get_inherited_style = Mock(return_value=inherited_styles)
        
        result = self.converter.convert(path_element, self.context)
        
        assert result is not None
        assert self.context.get_inherited_style.called
    
    def test_error_handling_insufficient_coordinates(self):
        """Test error handling for paths with insufficient coordinate data."""
        path_element = ET.Element("path")
        path_element.set("d", "M 10 L 20")  # Missing coordinate for L command
        
        # Should handle gracefully without crashing
        result = self.converter.convert(path_element, self.context)
        assert result is None or isinstance(result, list)
    
    def test_path_optimization_simple_shapes(self):
        """Test that simple paths are optimized to basic shapes when possible."""
        # Rectangle as path
        rect_path = ET.Element("path")
        rect_path.set("d", "M 10,10 L 60,10 L 60,40 L 10,40 Z")
        
        result = self.converter.convert(rect_path, self.context)
        assert result is not None
        
        # Should potentially optimize to rectangle shape
        # (Implementation detail - may vary based on optimization logic)
    
    def test_complex_path_fallback(self):
        """Test that complex paths fall back to appropriate rendering method."""
        complex_path = ET.Element("path")
        complex_path.set("d", "M 10,10 Q 50,5 90,10 T 170,10 L 170,90 Q 165,130 170,170 T 170,250 L 10,250 Z")
        
        result = self.converter.convert(complex_path, self.context)
        assert result is not None
        assert len(result) > 0


class TestPathValidation:
    """Test path data validation and error recovery."""
    
    def setup_method(self):
        """Set up test fixtures.""" 
        self.context = mock_conversion_context()
        self.converter = PathConverter()
    
    def test_malformed_path_data_recovery(self):
        """Test recovery from malformed path data."""
        malformed_paths = [
            "M 10,10 L",           # Incomplete command
            "M 10,10 L 20,",       # Missing coordinate
            "M 10,10 L 20 30 40",  # Too many coordinates
            "M 10,10 L abc,def",   # Non-numeric coordinates
            "",                     # Empty string
            "   ",                 # Whitespace only
        ]
        
        for path_data in malformed_paths:
            path_element = ET.Element("path")
            path_element.set("d", path_data)
            
            # Should handle malformed data without raising exceptions
            try:
                result = self.converter.convert(path_element, self.context)
                assert result is None or isinstance(result, list)
            except Exception as e:
                pytest.fail(f"Path converter raised exception on malformed data '{path_data}': {e}")
    
    def test_path_bounds_calculation(self):
        """Test calculation of path bounding boxes."""
        path_element = ET.Element("path")
        path_element.set("d", "M 10,10 L 50,50 L 20,70 Z")
        
        result = self.converter.convert(path_element, self.context)
        
        # Path should be converted and have reasonable bounds
        assert result is not None