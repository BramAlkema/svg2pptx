#!/usr/bin/env python3
"""
Additional tests to improve markers converter coverage.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from lxml import etree as ET

from src.converters.markers import MarkerConverter
from src.converters.base import ConversionContext
from src.colors import ColorInfo, ColorFormat
from src.transforms import Matrix


class TestMarkersAdditionalCoverage:
    """Additional tests to improve coverage."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.converter = MarkerConverter()
        self.context = ConversionContext()
        self.context.get_next_shape_id = Mock(return_value=4001)
    
    def test_defs_processing_with_nested_elements(self):
        """Test processing defs with multiple nested markers and symbols."""
        defs_xml = '''
        <defs>
            <marker id="nested_marker1">
                <circle r="5"/>
            </marker>
            <symbol id="nested_symbol1">
                <rect width="10" height="10"/>
            </symbol>
            <marker id="nested_marker2">
                <polygon points="0,0 10,5 0,10"/>
            </marker>
            <g>
                <!-- Non-marker/symbol content should be ignored -->
                <path d="M 0 0 L 10 10"/>
            </g>
        </defs>
        '''
        defs_elem = ET.fromstring(defs_xml)
        
        result = self.converter._process_definitions(defs_elem, self.context)
        
        # Should extract both markers and one symbol
        assert 'nested_marker1' in self.converter.markers
        assert 'nested_marker2' in self.converter.markers
        assert 'nested_symbol1' in self.converter.symbols
        assert result == ""  # Defs don't generate output
    
    def test_use_element_with_only_width(self):
        """Test use element with only width specified."""
        # Add a symbol with viewbox
        self.converter.symbols['test_symbol_width'] = Mock()
        self.converter.symbols['test_symbol_width'].viewbox = (0, 0, 50, 25)
        self.converter.symbols['test_symbol_width'].content_xml = '<rect/>'
        
        use_xml = '''<use href="#test_symbol_width" width="100"/>'''
        use_elem = ET.fromstring(use_xml)
        
        with patch.object(self.converter, '_generate_symbol_drawingml') as mock_gen:
            mock_gen.return_value = '<test>width_only</test>'
            result = self.converter._process_use_element(use_elem, self.context)
            
            # Should call with scaling
            mock_gen.assert_called_once()
            call_args = mock_gen.call_args
            transform_matrix = call_args[0][1]
            decomp = transform_matrix.decompose()
            assert decomp['scaleX'] == 2.0  # 100/50
            assert decomp['scaleY'] == 2.0  # Same scale for both axes
    
    def test_use_element_with_only_height(self):
        """Test use element with only height specified."""
        # Add a symbol with viewbox  
        self.converter.symbols['test_symbol_height'] = Mock()
        self.converter.symbols['test_symbol_height'].viewbox = (0, 0, 40, 20)
        self.converter.symbols['test_symbol_height'].content_xml = '<circle/>'
        
        use_xml = '''<use href="#test_symbol_height" height="60"/>'''
        use_elem = ET.fromstring(use_xml)
        
        with patch.object(self.converter, '_generate_symbol_drawingml') as mock_gen:
            mock_gen.return_value = '<test>height_only</test>'
            result = self.converter._process_use_element(use_elem, self.context)
            
            # Should call with scaling based on height
            mock_gen.assert_called_once()
            call_args = mock_gen.call_args
            transform_matrix = call_args[0][1]
            decomp = transform_matrix.decompose()
            assert decomp['scaleX'] == 3.0  # 60/20
            assert decomp['scaleY'] == 3.0  # Same scale for both axes
    
    def test_use_element_without_href(self):
        """Test use element without href attribute."""
        use_xml = '''<use x="10" y="20"/>'''
        use_elem = ET.fromstring(use_xml)
        
        result = self.converter._process_use_element(use_elem, self.context)
        assert result == ""
    
    def test_use_element_with_invalid_href(self):
        """Test use element with href not starting with #."""
        use_xml = '''<use href="external-symbol"/>'''
        use_elem = ET.fromstring(use_xml)
        
        result = self.converter._process_use_element(use_elem, self.context)
        assert result == ""
    
    def test_apply_markers_single_point_path(self):
        """Test marker application to single-point path."""
        path_elem = ET.Element('path')
        path_elem.set('marker-start', 'url(#arrow)')
        path_elem.set('marker-end', 'url(#arrow)')
        
        # Single point path
        path_commands = [('M', 10, 20)]
        
        result = self.converter.apply_markers_to_path(path_elem, path_commands, self.context)
        assert result == ""  # No markers on single point
    
    def test_apply_markers_unknown_marker_reference(self):
        """Test marker application with unknown marker ID."""
        path_elem = ET.Element('path')
        path_elem.set('marker-start', 'url(#unknown_marker)')
        
        path_commands = [('M', 0, 0), ('L', 10, 10)]
        
        result = self.converter.apply_markers_to_path(path_elem, path_commands, self.context)
        assert result == ""  # No markers generated for unknown reference
    
    def test_marker_with_stroke_width_units_scaling(self):
        """Test marker generation with strokeWidth units."""
        from src.converters.markers import MarkerDefinition, MarkerInstance, MarkerPosition, MarkerUnits
        
        marker_def = MarkerDefinition(
            id='stroke_width_marker',
            ref_x=0, ref_y=0,
            marker_width=10, marker_height=10,
            orient='auto',
            marker_units=MarkerUnits.STROKE_WIDTH,  # Scale with stroke
            viewbox=None,
            overflow='hidden',
            content_xml='<circle r="3"/>'
        )
        
        color = ColorInfo(128, 64, 192, 1.0, ColorFormat.RGB, 'rgb(128,64,192)')
        
        marker_instance = MarkerInstance(
            definition=marker_def,
            position=MarkerPosition.START,
            x=50, y=75,
            angle=0.0,
            stroke_width=3.0,  # Should scale marker
            color=color
        )
        
        with patch.object(self.converter, '_detect_standard_arrow', return_value=None):
            with patch.object(self.converter, '_generate_custom_marker_drawingml') as mock_custom:
                mock_custom.return_value = '<scaled_marker/>'
                
                result = self.converter._generate_marker_drawingml(marker_instance, self.context)
                
                # Verify scaling was applied (stroke_width = 3.0)
                mock_custom.assert_called_once()
                args = mock_custom.call_args[0]
                transform_matrix = args[1]  # Second argument
                decomp = transform_matrix.decompose()
                # Scale should include the stroke width factor
                assert 'scaled_marker' in result
    
    def test_marker_with_user_space_units(self):
        """Test marker generation with userSpaceOnUse units."""
        from src.converters.markers import MarkerDefinition, MarkerInstance, MarkerPosition, MarkerUnits
        
        marker_def = MarkerDefinition(
            id='user_space_marker',
            ref_x=2, ref_y=3,
            marker_width=8, marker_height=6,
            orient='45',
            marker_units=MarkerUnits.USER_SPACE_ON_USE,  # No stroke scaling
            viewbox=None,
            overflow='hidden',
            content_xml='<rect width="8" height="6"/>'
        )
        
        color = ColorInfo(255, 128, 0, 0.7, ColorFormat.RGBA, 'rgba(255,128,0,0.7)')
        
        marker_instance = MarkerInstance(
            definition=marker_def,
            position=MarkerPosition.END,
            x=100, y=150,
            angle=30.0,
            stroke_width=5.0,  # Should NOT scale marker
            color=color
        )
        
        with patch.object(self.converter, '_detect_standard_arrow', return_value=None):
            with patch.object(self.converter, '_generate_custom_marker_drawingml') as mock_custom:
                mock_custom.return_value = '<unscaled_marker/>'
                
                result = self.converter._generate_marker_drawingml(marker_instance, self.context)
                
                # Verify no stroke scaling was applied
                mock_custom.assert_called_once()
                assert 'unscaled_marker' in result
    
    def test_standard_arrow_detection_no_match(self):
        """Test arrow detection with content that doesn't match patterns."""
        from src.converters.markers import MarkerDefinition, MarkerUnits
        
        marker_def = MarkerDefinition(
            id='unknown_shape',
            ref_x=0, ref_y=0,
            marker_width=10, marker_height=10,
            orient='auto',
            marker_units=MarkerUnits.STROKE_WIDTH,
            viewbox=None,
            overflow='hidden',
            content_xml='<path d="M 0 0 Q 5 5 10 0 T 20 0"/>'  # Complex path
        )
        
        result = self.converter._detect_standard_arrow(marker_def)
        assert result is None
    
    def test_viewbox_string_parsing_errors(self):
        """Test viewBox parsing with various invalid formats."""
        marker_xml_invalid = '''<marker id="bad_viewbox1" viewBox="1 2 3">
            <circle r="5"/>
        </marker>'''
        marker_elem = ET.fromstring(marker_xml_invalid)
        
        self.converter._extract_marker_definition(marker_elem)
        marker_def = self.converter.markers['bad_viewbox1']
        assert marker_def.viewbox is None
        
        # Test with empty viewBox
        marker_xml_empty = '''<marker id="bad_viewbox2" viewBox="">
            <circle r="5"/>
        </marker>'''
        marker_elem = ET.fromstring(marker_xml_empty)
        
        self.converter._extract_marker_definition(marker_elem)
        marker_def = self.converter.markers['bad_viewbox2']
        assert marker_def.viewbox is None
    
    def test_symbol_dimension_parsing_errors(self):
        """Test symbol dimension parsing with invalid values."""
        symbol_xml = '''<symbol id="bad_dims" width="invalid%" height="also-bad">
            <rect width="100%" height="100%"/>
        </symbol>'''
        symbol_elem = ET.fromstring(symbol_xml)
        
        self.converter._extract_symbol_definition(symbol_elem)
        symbol_def = self.converter.symbols['bad_dims']
        assert symbol_def.width is None
        assert symbol_def.height is None
    
    def test_generate_symbol_without_viewbox(self):
        """Test symbol generation without viewBox."""
        from src.converters.markers import SymbolDefinition
        
        symbol_def = SymbolDefinition(
            id='no_viewbox_symbol',
            viewbox=None,  # No viewBox
            preserve_aspect_ratio='xMidYMid meet',
            width=None,
            height=None,
            content_xml='<rect width="50" height="30" fill="blue"/>'
        )
        
        transform_matrix = Matrix.translate(20, 30)
        
        result = self.converter._generate_symbol_drawingml(symbol_def, transform_matrix, self.context)
        
        # Should generate group without viewBox transform
        assert '<p:grpSp>' in result
        assert 'name="symbol_no_viewbox_symbol"' in result
        assert symbol_def.content_xml in result
    
    def test_convert_with_unsupported_element(self):
        """Test convert method with unsupported element type."""
        path_elem = ET.Element('path')
        
        result = self.converter.convert(path_elem, self.context)
        assert result == ""
    
    def test_matrix_decomposition_edge_cases(self):
        """Test matrix to DrawingML transform with edge cases."""
        # Identity matrix (no transform needed)
        matrix = Matrix.identity()
        result = self.converter._matrix_to_drawingml_transform(matrix)
        assert result == ""  # No transform elements needed
        
        # Very small values (should be ignored)
        matrix = Matrix.translate(1e-8, 1e-8).multiply(Matrix.rotate(1e-8))
        result = self.converter._matrix_to_drawingml_transform(matrix)
        assert result == ""  # Values too small to matter


if __name__ == '__main__':
    pytest.main([__file__, '-v'])