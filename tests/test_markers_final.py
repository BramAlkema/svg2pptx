#!/usr/bin/env python3
"""
Final tests to achieve maximum coverage on markers converter.
"""

import pytest
from unittest.mock import Mock, patch
from lxml import etree as ET

from src.converters.markers import MarkerConverter
from src.converters.base import ConversionContext


class TestMarkersFinalizeCoverage:
    """Tests targeting specific uncovered lines."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.converter = MarkerConverter()
        self.context = ConversionContext()
    
    def test_marker_viewbox_with_non_numeric_values(self):
        """Test marker viewBox parsing with non-numeric values."""
        marker_xml = '''<marker id="bad_numeric_viewbox" viewBox="a b c d">
            <circle r="5"/>
        </marker>'''
        marker_elem = ET.fromstring(marker_xml)
        
        self.converter._extract_marker_definition(marker_elem)
        
        # Should handle ValueError gracefully
        marker_def = self.converter.markers['bad_numeric_viewbox']
        assert marker_def.viewbox is None  # Lines 174-175
    
    def test_symbol_viewbox_with_non_numeric_values(self):
        """Test symbol viewBox parsing with non-numeric values."""
        symbol_xml = '''<symbol id="bad_numeric_symbol" viewBox="x y z w">
            <rect width="10" height="10"/>
        </symbol>'''
        symbol_elem = ET.fromstring(symbol_xml)
        
        self.converter._extract_symbol_definition(symbol_elem)
        
        # Should handle ValueError gracefully  
        symbol_def = self.converter.symbols['bad_numeric_symbol']
        assert symbol_def.viewbox is None  # Lines 209-210
    
    def test_process_marker_and_symbol_definitions_directly(self):
        """Test direct processing of marker and symbol definitions."""
        marker_xml = '''<marker id="direct_marker">
            <polygon points="0,0 10,5 0,10"/>
        </marker>'''
        marker_elem = ET.fromstring(marker_xml)
        
        result = self.converter._process_marker_definition(marker_elem, self.context)
        assert result == ""  # Line 241-242
        assert 'direct_marker' in self.converter.markers
        
        symbol_xml = '''<symbol id="direct_symbol">
            <circle r="8"/>  
        </symbol>'''
        symbol_elem = ET.fromstring(symbol_xml)
        
        result = self.converter._process_symbol_definition(symbol_elem, self.context)
        assert result == ""  # Line 246-247
        assert 'direct_symbol' in self.converter.symbols
    
    def test_use_element_with_missing_symbol_reference(self):
        """Test use element with symbol ID that doesn't exist."""
        use_xml = '''<use href="#nonexistent_symbol"/>'''
        use_elem = ET.fromstring(use_xml)
        
        result = self.converter._process_use_element(use_elem, self.context)
        assert result == ""  # Line 253
    
    def test_apply_markers_to_path_with_single_point(self):
        """Test marker application to path with insufficient points."""
        path_elem = ET.Element('path')
        path_elem.set('marker-start', 'url(#arrow)')
        path_elem.set('marker-end', 'url(#arrow)')
        
        # Only one point - insufficient for start/end markers
        path_commands = [('M', 10, 20)]
        
        result = self.converter.apply_markers_to_path(path_elem, path_commands, self.context)
        assert result == ""  # Line 318 (insufficient points)
    
    def test_generate_custom_marker_drawingml(self):
        """Test custom marker DrawingML generation."""
        from src.converters.markers import MarkerDefinition, MarkerUnits
        from src.transforms import Matrix
        from src.colors import ColorInfo, ColorFormat
        
        marker_def = MarkerDefinition(
            id='custom_marker',
            ref_x=1, ref_y=2,
            marker_width=8, marker_height=6,
            orient='auto',
            marker_units=MarkerUnits.STROKE_WIDTH,
            viewbox=None,
            overflow='visible',
            content_xml='<polygon points="0,0 8,3 0,6"/>'
        )
        
        transform_matrix = Matrix.identity()
        color = ColorInfo(200, 100, 50, 0.9, ColorFormat.RGB, 'rgb(200,100,50)')
        
        self.context.get_next_shape_id = Mock(return_value=5001)
        
        result = self.converter._generate_custom_marker_drawingml(
            marker_def, transform_matrix, color, self.context
        )
        
        # Should generate group with marker content
        assert '<p:grpSp>' in result
        assert 'id="5001"' in result
        assert 'name="marker_custom_marker"' in result
        assert marker_def.content_xml in result  # Line 422, 597-603
    
    def test_unsupported_convert_element_types(self):
        """Test convert method with various unsupported elements."""
        # Test with different unsupported element types
        unsupported_elements = ['rect', 'circle', 'line', 'path', 'text', 'g']
        
        for element_name in unsupported_elements:
            elem = ET.Element(element_name)
            result = self.converter.convert(elem, self.context)
            assert result == ""  # Default return for unsupported elements
    
    def test_ellipse_marker_detection(self):
        """Test ellipse detection in markers.""" 
        from src.converters.markers import MarkerDefinition, MarkerUnits
        
        marker_def = MarkerDefinition(
            id='ellipse_marker',
            ref_x=5, ref_y=3,
            marker_width=10, marker_height=6,
            orient='auto',
            marker_units=MarkerUnits.STROKE_WIDTH,
            viewbox=None,
            overflow='hidden',
            content_xml='<ellipse cx="5" cy="3" rx="4" ry="2"/>'
        )
        
        result = self.converter._detect_standard_arrow(marker_def)
        assert result == 'circle'  # Ellipse should be detected as circle variant
    
    def test_arrow_detection_edge_cases(self):
        """Test edge cases in arrow detection logic."""
        # Test empty content
        result = self.converter._is_arrow_polygon("")
        assert not result
        
        # Test content without points attribute
        result = self.converter._is_arrow_polygon('<polygon fill="red"/>')
        assert not result
        
        # Test diamond detection edge cases
        result = self.converter._is_diamond_polygon("")
        assert not result
        
        result = self.converter._is_diamond_polygon('<polygon fill="blue"/>')
        assert not result
    
    def test_marker_detection_with_complex_content(self):
        """Test marker detection with complex nested content."""
        from src.converters.markers import MarkerDefinition, MarkerUnits
        
        # Test marker with nested groups and transforms
        marker_def = MarkerDefinition(
            id='complex_marker',
            ref_x=0, ref_y=0,
            marker_width=12, marker_height=8,
            orient='auto',
            marker_units=MarkerUnits.STROKE_WIDTH,
            viewbox=None,
            overflow='hidden',
            content_xml='''<g transform="scale(0.8)">
                <path d="M 0 0 L 10 5 L 5 5 L 10 8 L 0 10 Z"/>
                <circle cx="8" cy="5" r="1"/>
            </g>'''
        )
        
        result = self.converter._detect_standard_arrow(marker_def)
        # Should detect circle due to circle element in content
        assert result == 'circle'  # Circle detected from nested content


if __name__ == '__main__':
    pytest.main([__file__, '-v'])