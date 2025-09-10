#!/usr/bin/env python3
"""
Enhanced unit tests for PolygonConverter improvements.

Tests the enhanced PolygonConverter functionality including:
- Advanced points parsing (various formats, edge cases)
- Custom geometry path generation accuracy
- Polygon vs polyline distinction 
- Bounding box optimization
- Complex polygon shapes support
- Performance with large point sets
- Universal utilities integration
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import xml.etree.ElementTree as ET
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from src.converters.shapes import PolygonConverter
from src.converters.base import ConversionContext


class TestPolygonConverterEnhancements:
    """Test enhanced PolygonConverter functionality."""
    
    @pytest.fixture
    def converter(self):
        """Create PolygonConverter instance for testing."""
        return PolygonConverter()
    
    @pytest.fixture
    def mock_context(self):
        """Create mock ConversionContext."""
        context = Mock(spec=ConversionContext)
        
        # Mock coordinate system
        coord_system = Mock()
        coord_system.svg_to_emu.return_value = (0, 0)
        coord_system.svg_length_to_emu.return_value = 914400  # 100px in EMUs
        context.coordinate_system = coord_system
        
        context.get_next_shape_id.return_value = 2001
        
        return context

    def test_points_parsing_advanced_formats(self, converter):
        """Test parsing various advanced point formats."""
        test_cases = [
            # (input_string, expected_points, description)
            ("10,20 30,40 50,60", [(10.0, 20.0), (30.0, 40.0), (50.0, 60.0)], "Basic comma-space format"),
            ("10 20 30 40 50 60", [(10.0, 20.0), (30.0, 40.0), (50.0, 60.0)], "Space-only format"),
            ("10,20,30,40,50,60", [(10.0, 20.0), (30.0, 40.0), (50.0, 60.0)], "Comma-only format"),
            ("10,20\n30,40\t50,60", [(10.0, 20.0), (30.0, 40.0), (50.0, 60.0)], "Mixed whitespace"),
            ("  10,20   30,40   50,60  ", [(10.0, 20.0), (30.0, 40.0), (50.0, 60.0)], "Leading/trailing spaces"),
            ("10.5,20.7 30.1,40.9", [(10.5, 20.7), (30.1, 40.9)], "Decimal coordinates"),
            ("-10,-20 30,40", [(-10.0, -20.0), (30.0, 40.0)], "Negative coordinates"),
            ("0,0", [(0.0, 0.0)], "Single point"),
        ]
        
        for points_str, expected, description in test_cases:
            result = converter._parse_points(points_str)
            assert result == expected, f"Failed for {description}: got {result}, expected {expected}"

    def test_points_parsing_edge_cases(self, converter):
        """Test points parsing with edge cases and error conditions.""" 
        test_cases = [
            # (input_string, expected_behavior, description)
            ("", [], "Empty string"),
            ("   ", [], "Whitespace only"),
            ("10,20 invalid 30,40", [(10.0, 20.0)], "Invalid coordinate stops parsing"),
            ("10,20,30", [(10.0, 20.0)], "Odd number of coordinates"),
            ("10,,20", [(10.0, 20.0)], "Empty coordinate - parses valid parts"),
            ("10,NaN 30,40", [(30.0, 40.0)], "NaN coordinate - filtered out"),  
            ("10,inf 30,40", [(30.0, 40.0)], "Infinity coordinate - filtered out"),
            ("1e6,1e6", [(1000000.0, 1000000.0)], "Scientific notation"),
        ]
        
        for points_str, expected, description in test_cases:
            result = converter._parse_points(points_str)
            if expected:
                assert result == expected, f"Failed for {description}: got {result}, expected {expected}"
            else:
                assert len(result) == 0, f"Failed for {description}: expected empty, got {result}"

    def test_bounding_box_calculation_accuracy(self, converter, mock_context):
        """Test accurate bounding box calculation for various polygon shapes."""
        test_cases = [
            # (points, expected_min_x, expected_min_y, expected_width, expected_height)
            ("0,0 100,0 50,100", 0, 0, 100, 100),  # Triangle
            ("10,20 90,20 90,80 10,80", 10, 20, 80, 60),  # Rectangle offset
            ("-50,-25 50,25", -50, -25, 100, 50),  # Negative coordinates
            ("100,200 300,100 200,400", 100, 100, 200, 300),  # Complex shape
        ]
        
        for points_str, exp_min_x, exp_min_y, exp_width, exp_height in test_cases:
            element = ET.fromstring(f'<polygon points="{points_str}"/>')
            
            # Mock coordinate conversions based on expected values
            mock_context.coordinate_system.svg_to_emu.return_value = (exp_min_x * 9144, exp_min_y * 9144)
            mock_context.coordinate_system.svg_length_to_emu.side_effect = [exp_width * 9144, exp_height * 9144]
            
            converter.generate_fill = Mock(return_value='<fill-mock/>')
            converter.generate_stroke = Mock(return_value='<stroke-mock/>')
            
            result = converter.convert(element, mock_context)
            
            # Verify bounding box calculation
            mock_context.coordinate_system.svg_to_emu.assert_called_with(exp_min_x, exp_min_y)

    def test_polygon_vs_polyline_distinction(self, converter, mock_context):
        """Test proper distinction between polygon and polyline behavior."""
        points_str = "0,0 50,50 100,0"
        
        # Test polygon (should be closed)
        polygon_element = ET.fromstring(f'<polygon points="{points_str}"/>')
        converter.generate_fill = Mock(return_value='<fill-mock/>')
        converter.generate_stroke = Mock(return_value='<stroke-mock/>')
        
        polygon_result = converter.convert(polygon_element, mock_context)
        
        # Verify polygon properties
        assert 'name="Polygon' in polygon_result
        assert '<a:close/>' in polygon_result  # Should be closed
        
        # Test polyline (should NOT be closed)
        polyline_element = ET.fromstring(f'<polyline points="{points_str}"/>')
        converter.generate_fill = Mock(return_value='<fill-mock/>')
        converter.generate_stroke = Mock(return_value='<stroke-mock/>')
        mock_context.get_next_shape_id.return_value = 2002
        
        polyline_result = converter.convert(polyline_element, mock_context)
        
        # Verify polyline properties
        assert 'name="Polyline' in polyline_result
        assert '<a:close/>' not in polyline_result  # Should NOT be closed

    def test_custom_geometry_path_generation_accuracy(self, converter, mock_context):
        """Test accuracy of custom geometry path generation."""
        # Test with known coordinates that should map to specific path points
        points_str = "0,0 100,0 100,100 0,100"  # Square
        element = ET.fromstring(f'<polygon points="{points_str}"/>')
        
        converter.generate_fill = Mock(return_value='<fill-mock/>')
        converter.generate_stroke = Mock(return_value='<stroke-mock/>')
        
        result = converter.convert(element, mock_context)
        
        # Check path structure
        assert '<a:path w="21600" h="21600">' in result
        assert '<a:moveTo>' in result
        assert '<a:lnTo>' in result
        
        # For a square starting at (0,0), the first point should be at path coordinate (0,0)
        assert '<a:pt x="0" y="0"/>' in result
        # Last point should be at path coordinate (21600, 21600) for bottom-right
        assert '<a:pt x="21600" y="21600"/>' in result

    def test_complex_polygon_shapes(self, converter, mock_context):
        """Test support for complex polygon shapes."""
        test_cases = [
            # (description, points, special_checks)
            ("Star shape", "50,0 61,35 96,35 68,57 79,91 50,70 21,91 32,57 4,35 39,35", None),
            ("Self-intersecting", "0,0 100,100 100,0 0,100", None),
            ("Concave polygon", "0,0 100,0 100,50 50,50 50,100 0,100", None),
            ("Many points", " ".join([f"{i*10},{i*5}" for i in range(20)]), "performance"),
        ]
        
        for description, points_str, special_check in test_cases:
            element = ET.fromstring(f'<polygon points="{points_str}"/>')
            
            converter.generate_fill = Mock(return_value='<fill-mock/>')
            converter.generate_stroke = Mock(return_value='<stroke-mock/>')
            mock_context.get_next_shape_id.return_value = 2003
            
            # Should not raise exceptions for complex shapes
            result = converter.convert(element, mock_context)
            
            # Basic structure should be present
            assert '<p:sp>' in result
            assert '<a:custGeom>' in result
            assert '<a:pathLst>' in result
            
            if special_check == "performance":
                # For many points, verify all are processed
                move_to_count = result.count('<a:moveTo>')
                line_to_count = result.count('<a:lnTo>')
                assert move_to_count == 1  # Should have one moveTo
                assert line_to_count == 19  # Should have 19 lineTo commands (20 points - 1 moveTo)

    def test_performance_with_large_point_sets(self, converter, mock_context):
        """Test performance with large point sets."""
        # Generate 1000 points
        large_points = []
        for i in range(1000):
            x = i % 100
            y = i // 100
            large_points.append(f"{x},{y}")
        
        points_str = " ".join(large_points)
        element = ET.fromstring(f'<polygon points="{points_str}"/>')
        
        converter.generate_fill = Mock(return_value='<fill-mock/>')
        converter.generate_stroke = Mock(return_value='<stroke-mock/>')
        
        # Should complete without performance issues
        import time
        start_time = time.time()
        result = converter.convert(element, mock_context)
        end_time = time.time()
        
        # Should complete in reasonable time (less than 1 second)
        assert (end_time - start_time) < 1.0
        assert '<p:sp>' in result

    def test_universal_utilities_integration(self, converter):
        """Test integration with universal utilities."""
        # Verify universal utilities are accessible
        assert hasattr(converter, 'unit_converter')
        assert hasattr(converter, 'color_parser') 
        assert hasattr(converter, 'transform_parser')
        assert hasattr(converter, 'viewport_resolver')
        
        # Verify inherited methods
        assert hasattr(converter, 'parse_length')
        assert hasattr(converter, 'get_attribute_with_style')
        assert hasattr(converter, 'generate_fill')
        assert hasattr(converter, 'generate_stroke')

    def test_style_processing_consistency(self, converter, mock_context):
        """Test consistent style processing for polygon vs polyline."""
        points_str = "0,0 50,50 100,0"
        
        # Test polygon with fill and stroke
        polygon_element = ET.fromstring(f'''
            <polygon points="{points_str}" 
                     fill="red" stroke="blue" stroke-width="2"/>
        ''')
        
        converter.generate_fill = Mock(return_value='<red-fill/>')
        converter.generate_stroke = Mock(return_value='<blue-stroke/>')
        
        result = converter.convert(polygon_element, mock_context)
        
        # Verify both fill and stroke are processed for polygon
        converter.generate_fill.assert_called_once_with('red', '1', mock_context)
        converter.generate_stroke.assert_called_once_with('blue', '2', '1', mock_context)
        assert '<red-fill/>' in result
        assert '<blue-stroke/>' in result

    def test_viewport_resolver_integration(self, converter, mock_context):
        """Test integration with ViewportResolver for coordinate mapping."""
        element = ET.fromstring('<polygon points="0,0 100,0 50,100"/>')
        
        # Mock ViewportResolver integration through context
        viewport_mapping = Mock()
        viewport_mapping.svg_to_emu.return_value = (914400, 914400)
        mock_context.viewport_mapping = viewport_mapping
        
        converter.generate_fill = Mock(return_value='<fill-mock/>')
        converter.generate_stroke = Mock(return_value='<stroke-mock/>')
        
        result = converter.convert(element, mock_context)
        
        # Should complete without errors even with viewport mapping
        assert '<p:sp>' in result
        assert 'Polygon' in result

    def test_error_handling_robustness(self, converter, mock_context):
        """Test robust error handling."""
        error_cases = [
            ('<polygon/>', "Missing points attribute"),
            ('<polygon points=""/>', "Empty points"),
            ('<polygon points="invalid"/>', "Invalid points format"),
            ('<polygon points="10"/>', "Insufficient coordinates"),
        ]
        
        for element_xml, description in error_cases:
            element = ET.fromstring(element_xml)
            
            # Should not raise exceptions, should handle gracefully
            result = converter.convert(element, mock_context)
            
            # Should return some form of valid or comment response
            assert isinstance(result, str)

    def test_backward_compatibility(self, converter, mock_context):
        """Test that enhancements maintain backward compatibility."""
        # Test with same basic polygon from original test suite
        element = ET.fromstring('<polygon points="0,0 100,0 50,100"/>')
        
        converter.generate_fill = Mock(return_value='<fill-mock/>')
        converter.generate_stroke = Mock(return_value='<stroke-mock/>')
        
        result = converter.convert(element, mock_context)
        
        # Should maintain same basic structure as original
        assert '<p:sp>' in result
        assert 'name="Polygon' in result
        assert '<a:custGeom>' in result
        assert '<a:pathLst>' in result
        assert '<a:moveTo>' in result
        assert '<a:lnTo>' in result
        assert '<a:close/>' in result


class TestPolygonConverterPathGeneration:
    """Test polygon/polyline path generation accuracy."""
    
    def test_path_coordinate_scaling(self):
        """Test path coordinate scaling to 21600x21600 coordinate system."""
        converter = PolygonConverter()
        
        # Test with simple rectangle: (0,0), (100,0), (100,100), (0,100)
        points = [(0, 0), (100, 0), (100, 100), (0, 100)]
        min_x, min_y = 0, 0
        width, height = 100, 100
        
        path_xml = converter._generate_path(points, min_x, min_y, width, height, True)
        
        # Verify coordinate scaling
        assert '<a:pt x="0" y="0"/>' in path_xml          # (0,0) -> (0,0)
        assert '<a:pt x="21600" y="0"/>' in path_xml      # (100,0) -> (21600,0) 
        assert '<a:pt x="21600" y="21600"/>' in path_xml  # (100,100) -> (21600,21600)
        assert '<a:pt x="0" y="21600"/>' in path_xml      # (0,100) -> (0,21600)
        assert '<a:close/>' in path_xml                   # Should be closed

    def test_path_coordinate_scaling_offset(self):
        """Test path coordinate scaling with offset bounding box."""
        converter = PolygonConverter()
        
        # Test with offset rectangle: (50,25), (150,25), (150,125), (50,125)
        points = [(50, 25), (150, 25), (150, 125), (50, 125)]
        min_x, min_y = 50, 25
        width, height = 100, 100
        
        path_xml = converter._generate_path(points, min_x, min_y, width, height, True)
        
        # Points should be scaled relative to bounding box origin
        assert '<a:pt x="0" y="0"/>' in path_xml          # (50,25) -> (0,0)
        assert '<a:pt x="21600" y="0"/>' in path_xml      # (150,25) -> (21600,0)
        assert '<a:pt x="21600" y="21600"/>' in path_xml  # (150,125) -> (21600,21600)
        assert '<a:pt x="0" y="21600"/>' in path_xml      # (50,125) -> (0,21600)

    def test_polyline_vs_polygon_path_closure(self):
        """Test polyline vs polygon path closure."""
        converter = PolygonConverter()
        
        points = [(0, 0), (100, 0), (50, 100)]
        min_x, min_y = 0, 0
        width, height = 100, 100
        
        # Test polygon (should be closed)
        polygon_path = converter._generate_path(points, min_x, min_y, width, height, True)
        assert '<a:close/>' in polygon_path
        
        # Test polyline (should NOT be closed)
        polyline_path = converter._generate_path(points, min_x, min_y, width, height, False)
        assert '<a:close/>' not in polyline_path

    def test_path_generation_edge_cases(self):
        """Test path generation with edge cases."""
        converter = PolygonConverter()
        
        # Test with empty points
        empty_path = converter._generate_path([], 0, 0, 100, 100, True)
        assert empty_path == ''
        
        # Test with zero dimensions
        points = [(50, 50)]
        zero_width_path = converter._generate_path(points, 50, 50, 0, 0, True)
        # Should handle division by zero gracefully
        assert '<a:path' in zero_width_path