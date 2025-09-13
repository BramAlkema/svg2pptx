#!/usr/bin/env python3
"""
Enhanced path converter tests to improve coverage.

Focuses on testing untested code paths and edge cases to boost
coverage from 39% to higher levels.
"""

import pytest
from lxml import etree as ET
from src.converters.paths import PathConverter
from tests.fixtures import *


class TestPathConverterCoverage:
    """Tests to improve path converter coverage."""
    
    def test_empty_path_data_handling(self, mock_conversion_context):
        """Test handling of empty path data."""
        converter = PathConverter()
        path_element = ET.Element("path")
        path_element.set("d", "")
        
        result = converter.convert(path_element, mock_conversion_context)
        assert result is None or len(result) == 0
    
    def test_invalid_path_commands(self, mock_conversion_context):
        """Test handling of invalid path commands."""
        converter = PathConverter()
        path_element = ET.Element("path")
        path_element.set("d", "X 10 20 Y 30 40")  # Invalid commands
        
        # Should not crash on invalid commands
        result = converter.convert(path_element, mock_conversion_context)
        assert result is None or isinstance(result, (list, str))
    
    def test_relative_coordinate_paths(self, mock_conversion_context):
        """Test path conversion with relative coordinates."""
        converter = PathConverter()
        path_element = ET.Element("path")
        path_element.set("d", "m 10,20 l 30,40 l -10,-5 z")
        
        result = converter.convert(path_element, mock_conversion_context)
        assert result is not None
    
    def test_bezier_curve_paths(self, mock_conversion_context):
        """Test conversion of Bezier curve paths."""
        converter = PathConverter()
        path_element = ET.Element("path")
        path_element.set("d", "M 10,30 C 20,10 40,10 50,30 S 80,50 90,30")
        
        result = converter.convert(path_element, mock_conversion_context)
        assert result is not None
    
    def test_quadratic_curve_paths(self, mock_conversion_context):
        """Test conversion of quadratic curve paths."""
        converter = PathConverter()
        path_element = ET.Element("path")
        path_element.set("d", "M 10,80 Q 95,10 180,80 T 350,80")
        
        result = converter.convert(path_element, mock_conversion_context)
        assert result is not None
    
    def test_arc_paths(self, mock_conversion_context):
        """Test conversion of arc paths."""
        converter = PathConverter()
        path_element = ET.Element("path")
        path_element.set("d", "M 125,75 A 100,50 0 0,0 225,125")
        
        result = converter.convert(path_element, mock_conversion_context)
        assert result is not None
    
    def test_path_with_transforms(self, mock_conversion_context):
        """Test path conversion with transform attribute."""
        converter = PathConverter()
        path_element = ET.Element("path")
        path_element.set("d", "M 10,10 L 50,50")
        path_element.set("transform", "translate(10,10) scale(2)")
        
        result = converter.convert(path_element, mock_conversion_context)
        assert result is not None
    
    def test_styled_paths(self, mock_conversion_context):
        """Test path conversion with styling."""
        converter = PathConverter()
        path_element = ET.Element("path")
        path_element.set("d", "M 10,10 L 50,50 L 10,50 Z")
        path_element.set("fill", "#FF0000")
        path_element.set("stroke", "#00FF00")
        path_element.set("stroke-width", "2")
        
        result = converter.convert(path_element, mock_conversion_context)
        assert result is not None
    
    def test_coordinate_edge_cases(self, mock_conversion_context):
        """Test parsing of edge case coordinate formats."""
        converter = PathConverter()
        test_cases = [
            "M10 20L30 40",           # No comma separators
            "M 10,20 L 30,40",        # Mixed separators  
            "M10,20L30,40L50,60",     # Concatenated commands
            "M 10.5,20.7 L 30.1,40.9", # Decimal coordinates
        ]
        
        for path_data in test_cases:
            path_element = ET.Element("path")
            path_element.set("d", path_data)
            
            # Should not raise exceptions
            result = converter.convert(path_element, mock_conversion_context)
            assert result is None or isinstance(result, (list, str))
    
    def test_multiple_subpaths(self, mock_conversion_context):
        """Test path with multiple disconnected subpaths."""
        converter = PathConverter()
        path_element = ET.Element("path")
        path_element.set("d", "M 10,10 L 50,10 L 50,50 Z M 70,70 L 100,70 L 100,100 Z")
        
        result = converter.convert(path_element, mock_conversion_context)
        assert result is not None
    
    def test_negative_coordinates(self, mock_conversion_context):
        """Test path with negative coordinates."""
        converter = PathConverter()
        path_element = ET.Element("path")
        path_element.set("d", "M -10,-20 L -50,-60 L 10,20 Z")
        
        result = converter.convert(path_element, mock_conversion_context)
        assert result is not None
    
    def test_horizontal_vertical_line_commands(self, mock_conversion_context):
        """Test H/V line commands."""
        converter = PathConverter()
        path_element = ET.Element("path")
        path_element.set("d", "M 10,20 H 50 V 60 h 30 v -20")
        
        result = converter.convert(path_element, mock_conversion_context)
        assert result is not None
    
    def test_smooth_curve_commands(self, mock_conversion_context):
        """Test smooth curve commands (S/T)."""
        converter = PathConverter()
        path_element = ET.Element("path")
        path_element.set("d", "M 10,90 C 30,10 70,10 90,90 S 150,170 170,90")
        
        result = converter.convert(path_element, mock_conversion_context)
        assert result is not None
    
    def test_malformed_data_recovery(self, mock_conversion_context):
        """Test recovery from malformed path data."""
        converter = PathConverter()
        malformed_paths = [
            "M 10,10 L",           # Incomplete command
            "M 10,10 L 20,",       # Missing coordinate
            "M 10,10 L abc,def",   # Non-numeric coordinates
            "",                     # Empty string
            "   ",                 # Whitespace only
        ]
        
        for path_data in malformed_paths:
            path_element = ET.Element("path")
            path_element.set("d", path_data)
            
            # Should handle malformed data without raising exceptions
            try:
                result = converter.convert(path_element, mock_conversion_context)
                assert result is None or isinstance(result, (list, str))
            except Exception as e:
                pytest.fail(f"Path converter raised exception on malformed data '{path_data}': {e}")