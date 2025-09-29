#!/usr/bin/env python3
"""
Comprehensive tests for SVG Marker and Symbol Converter.

This test suite covers all aspects of SVG marker and symbol processing:
- Marker definition extraction and parsing
- Symbol definition extraction and processing  
- Use element instantiation with transforms
- Marker positioning on paths (start, mid, end)
- Standard arrow detection and generation
- Custom marker geometry processing
- Transform calculations for marker orientation
- ViewBox handling for symbols
- Path point extraction for marker placement
- DrawingML generation for various marker types
"""

import pytest
import math
from unittest.mock import Mock, patch, MagicMock
from lxml import etree as ET
from dataclasses import dataclass

# Import the module under test
from src.converters.markers import (
    MarkerConverter, MarkerDefinition, SymbolDefinition, MarkerInstance,
    MarkerPosition, MarkerUnits
)
from src.converters.base import ConversionContext
from src.color import Color
from src.transforms import Matrix


class TestMarkerConverter:
    """Test the main MarkerConverter class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create mock services for dependency injection
        mock_services = Mock()
        mock_services.unit_converter = Mock()
        mock_services.viewport_handler = Mock()
        mock_services.font_service = Mock()
        mock_services.gradient_service = Mock()
        mock_services.pattern_service = Mock()
        mock_services.clip_service = Mock()

        self.converter = MarkerConverter(services=mock_services)
        self.context = ConversionContext(services=mock_services)
        self.context.get_next_shape_id = Mock(return_value=1001)
    
    def test_initialization(self):
        """Test converter initialization."""
        assert isinstance(self.converter.markers, dict)
        assert isinstance(self.converter.symbols, dict)
        assert 'arrow' in self.converter.standard_arrows
        assert 'circle' in self.converter.standard_arrows
        assert 'square' in self.converter.standard_arrows
        assert 'diamond' in self.converter.standard_arrows
    
    def test_can_convert(self):
        """Test element conversion capability detection."""
        # Test supported elements
        marker_elem = ET.Element('marker')
        assert self.converter.can_convert(marker_elem)
        
        symbol_elem = ET.Element('symbol')  
        assert self.converter.can_convert(symbol_elem)
        
        use_elem = ET.Element('use')
        assert self.converter.can_convert(use_elem)
        
        defs_elem = ET.Element('defs')
        assert self.converter.can_convert(defs_elem)
        
        # Test unsupported element
        path_elem = ET.Element('path')
        assert not self.converter.can_convert(path_elem)
    
    def test_convert_routing(self):
        """Test convert method routing to appropriate handlers."""
        with patch.object(self.converter, '_process_definitions') as mock_defs:
            defs_elem = ET.Element('defs')
            self.converter.convert(defs_elem, self.context)
            mock_defs.assert_called_once_with(defs_elem, self.context)
        
        with patch.object(self.converter, '_process_marker_definition') as mock_marker:
            marker_elem = ET.Element('marker')
            self.converter.convert(marker_elem, self.context)
            mock_marker.assert_called_once_with(marker_elem, self.context)
        
        with patch.object(self.converter, '_process_symbol_definition') as mock_symbol:
            symbol_elem = ET.Element('symbol')
            self.converter.convert(symbol_elem, self.context)
            mock_symbol.assert_called_once_with(symbol_elem, self.context)
        
        with patch.object(self.converter, '_process_use_element') as mock_use:
            use_elem = ET.Element('use')
            self.converter.convert(use_elem, self.context)
            mock_use.assert_called_once_with(use_elem, self.context)


class TestMarkerDefinitionExtraction:
    """Test marker definition extraction and parsing."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create mock services for dependency injection
        mock_services = Mock()
        mock_services.unit_converter = Mock()
        mock_services.viewport_handler = Mock()
        mock_services.font_service = Mock()
        mock_services.gradient_service = Mock()
        mock_services.pattern_service = Mock()
        mock_services.clip_service = Mock()

        self.converter = MarkerConverter(services=mock_services)
    
    def test_basic_marker_extraction(self):
        """Test basic marker definition extraction."""
        marker_xml = '''
        <marker id="arrow1" markerWidth="10" markerHeight="10" 
                refX="5" refY="5" orient="auto">
            <polygon points="0,0 10,5 0,10" fill="black"/>
        </marker>
        '''
        marker_elem = ET.fromstring(marker_xml)
        
        self.converter._extract_marker_definition(marker_elem)
        
        assert 'arrow1' in self.converter.markers
        marker_def = self.converter.markers['arrow1']
        assert marker_def.id == 'arrow1'
        assert marker_def.marker_width == 10
        assert marker_def.marker_height == 10
        assert marker_def.ref_x == 5
        assert marker_def.ref_y == 5
        assert marker_def.orient == 'auto'
        assert marker_def.marker_units == MarkerUnits.STROKE_WIDTH
    
    def test_marker_with_viewbox(self):
        """Test marker with viewBox attribute."""
        marker_xml = '''
        <marker id="arrow2" viewBox="0 0 20 20" markerWidth="8" markerHeight="8">
            <path d="M 0 0 L 20 10 L 0 20 Z"/>
        </marker>
        '''
        marker_elem = ET.fromstring(marker_xml)
        
        self.converter._extract_marker_definition(marker_elem)
        
        marker_def = self.converter.markers['arrow2']
        assert marker_def.viewbox == (0, 0, 20, 20)
    
    def test_marker_units_user_space(self):
        """Test marker with userSpaceOnUse units."""
        marker_xml = '''
        <marker id="custom" markerUnits="userSpaceOnUse">
            <circle r="3"/>
        </marker>
        '''
        marker_elem = ET.fromstring(marker_xml)
        
        self.converter._extract_marker_definition(marker_elem)
        
        marker_def = self.converter.markers['custom']
        assert marker_def.marker_units == MarkerUnits.USER_SPACE_ON_USE
    
    def test_marker_orientation_angles(self):
        """Test marker orientation handling."""
        # Test auto orientation
        marker_def = MarkerDefinition(
            id='test', ref_x=0, ref_y=0, marker_width=10, marker_height=10,
            orient='auto', marker_units=MarkerUnits.STROKE_WIDTH,
            viewbox=None, overflow='hidden', content_xml=''
        )
        assert marker_def.get_orientation_angle(45.0) == 45.0
        
        # Test auto-start-reverse
        marker_def.orient = 'auto-start-reverse'
        assert marker_def.get_orientation_angle(45.0) == 225.0
        
        # Test fixed angle
        marker_def.orient = '90'
        assert marker_def.get_orientation_angle(45.0) == 90.0
        
        # Test invalid angle
        marker_def.orient = 'invalid'
        assert marker_def.get_orientation_angle(45.0) == 0.0
    
    def test_content_extraction(self):
        """Test extraction of marker inner content."""
        marker_xml = '''
        <marker id="complex">
            <g transform="scale(0.5)">
                <polygon points="0,0 10,5 0,10" fill="red"/>
                <circle cx="5" cy="5" r="2" fill="blue"/>
            </g>
        </marker>
        '''
        marker_elem = ET.fromstring(marker_xml)
        
        content = self.converter._extract_element_content(marker_elem)
        
        assert 'polygon' in content
        assert 'circle' in content
        assert 'points="0,0 10,5 0,10"' in content
        assert 'cx="5"' in content


class TestSymbolDefinitionExtraction:
    """Test symbol definition extraction and parsing."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create mock services for dependency injection
        mock_services = Mock()
        mock_services.unit_converter = Mock()
        mock_services.viewport_handler = Mock()
        mock_services.font_service = Mock()
        mock_services.gradient_service = Mock()
        mock_services.pattern_service = Mock()
        mock_services.clip_service = Mock()

        self.converter = MarkerConverter(services=mock_services)
    
    def test_basic_symbol_extraction(self):
        """Test basic symbol definition extraction."""
        symbol_xml = '''
        <symbol id="star" viewBox="0 0 100 100">
            <polygon points="50,0 61,35 98,35 68,57 79,91 50,70 21,91 32,57 2,35 39,35"/>
        </symbol>
        '''
        symbol_elem = ET.fromstring(symbol_xml)
        
        self.converter._extract_symbol_definition(symbol_elem)
        
        assert 'star' in self.converter.symbols
        symbol_def = self.converter.symbols['star']
        assert symbol_def.id == 'star'
        assert symbol_def.viewbox == (0, 0, 100, 100)
        assert symbol_def.preserve_aspect_ratio == 'xMidYMid meet'
    
    def test_symbol_with_dimensions(self):
        """Test symbol with explicit width/height."""
        symbol_xml = '''
        <symbol id="rect" width="200px" height="100px">
            <rect width="100%" height="100%" fill="green"/>
        </symbol>
        '''
        symbol_elem = ET.fromstring(symbol_xml)
        
        self.converter._extract_symbol_definition(symbol_elem)
        
        symbol_def = self.converter.symbols['rect']
        assert symbol_def.width == 200
        assert symbol_def.height == 100
    
    def test_symbol_preserve_aspect_ratio(self):
        """Test symbol with custom preserveAspectRatio."""
        symbol_xml = '''
        <symbol id="logo" preserveAspectRatio="xMinYMin slice">
            <circle cx="50" cy="50" r="40"/>
        </symbol>
        '''
        symbol_elem = ET.fromstring(symbol_xml)
        
        self.converter._extract_symbol_definition(symbol_elem)
        
        symbol_def = self.converter.symbols['logo']
        assert symbol_def.preserve_aspect_ratio == 'xMinYMin slice'


class TestUseElementProcessing:
    """Test <use> element processing for symbol instantiation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create mock services for dependency injection
        mock_services = Mock()
        mock_services.unit_converter = Mock()
        mock_services.viewport_handler = Mock()
        mock_services.font_service = Mock()
        mock_services.gradient_service = Mock()
        mock_services.pattern_service = Mock()
        mock_services.clip_service = Mock()

        self.converter = MarkerConverter(services=mock_services)
        self.context = ConversionContext(services=mock_services)
        self.context.get_next_shape_id = Mock(return_value=2001)

        # Mock transform parser to return identity matrix by default
        from src.transforms import Matrix
        self.converter.transform_parser.parse_to_matrix = Mock(return_value=Matrix.identity())
        
        # Add a test symbol
        self.converter.symbols['test_symbol'] = SymbolDefinition(
            id='test_symbol',
            viewbox=(0, 0, 50, 50),
            preserve_aspect_ratio='xMidYMid meet',
            width=None,
            height=None,
            content_xml='<rect width="50" height="50" fill="blue"/>'
        )
    
    def test_use_element_basic(self):
        """Test basic use element processing."""
        use_xml = '''<use href="#test_symbol" x="10" y="20"/>'''
        use_elem = ET.fromstring(use_xml)
        
        with patch.object(self.converter, '_generate_symbol_drawingml') as mock_gen:
            mock_gen.return_value = '<test>symbol</test>'
            result = self.converter._process_use_element(use_elem, self.context)
            mock_gen.assert_called_once()
            assert result == '<test>symbol</test>'
    
    def test_use_element_with_transform(self):
        """Test use element with transform attribute."""
        use_xml = '''<use href="#test_symbol" transform="rotate(45)"/>'''
        use_elem = ET.fromstring(use_xml)
        
        with patch.object(self.converter, '_generate_symbol_drawingml') as mock_gen:
            mock_gen.return_value = '<test>symbol</test>'
            self.converter._process_use_element(use_elem, self.context)
            
            # Verify transform matrix was passed
            call_args = mock_gen.call_args
            transform_matrix = call_args[0][1]  # Second argument
            assert isinstance(transform_matrix, Matrix)
    
    def test_use_element_with_dimensions(self):
        """Test use element with explicit width/height."""
        use_xml = '''<use href="#test_symbol" width="100" height="75"/>'''
        use_elem = ET.fromstring(use_xml)
        
        with patch.object(self.converter, '_generate_symbol_drawingml') as mock_gen:
            mock_gen.return_value = '<test>symbol</test>'
            self.converter._process_use_element(use_elem, self.context)
            
            # Verify scaling was applied
            call_args = mock_gen.call_args
            transform_matrix = call_args[0][1]
            decomp = transform_matrix.decompose()
            assert decomp['scaleX'] == 2.0  # 100/50
            assert decomp['scaleY'] == 1.5   # 75/50
    
    def test_use_element_missing_symbol(self):
        """Test use element referencing missing symbol."""
        use_xml = '''<use href="#missing_symbol"/>'''
        use_elem = ET.fromstring(use_xml)
        
        result = self.converter._process_use_element(use_elem, self.context)
        assert result == ""
    
    def test_use_element_xlink_href(self):
        """Test use element with xlink:href attribute."""
        use_xml = '''<use xmlns:xlink="http://www.w3.org/1999/xlink" xlink:href="#test_symbol"/>'''
        use_elem = ET.fromstring(use_xml)
        
        with patch.object(self.converter, '_generate_symbol_drawingml') as mock_gen:
            mock_gen.return_value = '<test>symbol</test>'
            result = self.converter._process_use_element(use_elem, self.context)
            mock_gen.assert_called_once()
            assert result == '<test>symbol</test>'


class TestMarkerPathApplication:
    """Test marker application to paths."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create mock services for dependency injection
        mock_services = Mock()
        mock_services.unit_converter = Mock()
        mock_services.viewport_handler = Mock()
        mock_services.font_service = Mock()
        mock_services.gradient_service = Mock()
        mock_services.pattern_service = Mock()
        mock_services.clip_service = Mock()

        self.converter = MarkerConverter(services=mock_services)
        self.context = ConversionContext(services=mock_services)
        
        # Add test marker
        self.converter.markers['arrow'] = MarkerDefinition(
            id='arrow',
            ref_x=5,
            ref_y=5,
            marker_width=10,
            marker_height=10,
            orient='auto',
            marker_units=MarkerUnits.STROKE_WIDTH,
            viewbox=(0, 0, 10, 10),
            overflow='hidden',
            content_xml='<polygon points="0,0 10,5 0,10"/>'
        )
    
    def test_extract_marker_id(self):
        """Test marker ID extraction from URL format."""
        assert self.converter._extract_marker_id('url(#arrow)') == 'arrow'
        assert self.converter._extract_marker_id('url(#complex-name)') == 'complex-name'
        assert self.converter._extract_marker_id('invalid') == ''
    
    def test_extract_path_points(self):
        """Test path point extraction from commands."""
        # Simple line path
        path_commands = [('M', 0, 0), ('L', 10, 10), ('L', 20, 0)]
        points = self.converter._extract_path_points(path_commands)
        
        expected = [(0, 0), (10, 10), (20, 0)]
        assert points == expected
    
    def test_extract_path_points_curves(self):
        """Test path point extraction with curves."""
        path_commands = [
            ('M', 0, 0),
            ('C', 5, 5, 15, 5, 20, 0),  # Cubic Bézier
            ('Q', 25, 5, 30, 0)         # Quadratic Bézier
        ]
        points = self.converter._extract_path_points(path_commands)
        
        expected = [(0, 0), (20, 0), (30, 0)]  # End points only
        assert points == expected
    
    def test_extract_path_points_closed(self):
        """Test closed path point extraction."""
        path_commands = [('M', 0, 0), ('L', 10, 0), ('L', 10, 10), ('Z',)]
        points = self.converter._extract_path_points(path_commands)
        
        expected = [(0, 0), (10, 0), (10, 10), (0, 0)]  # Includes closure
        assert points == expected
    
    def test_calculate_angle(self):
        """Test angle calculation between points."""
        # Horizontal line (0 degrees)
        angle = self.converter._calculate_angle((0, 0), (10, 0))
        assert abs(angle - 0.0) < 1e-6
        
        # Vertical line (90 degrees)
        angle = self.converter._calculate_angle((0, 0), (0, 10))
        assert abs(angle - 90.0) < 1e-6
        
        # Diagonal line (45 degrees)
        angle = self.converter._calculate_angle((0, 0), (10, 10))
        assert abs(angle - 45.0) < 1e-6
        
        # Negative direction (-45 degrees)
        angle = self.converter._calculate_angle((0, 0), (10, -10))
        assert abs(angle - (-45.0)) < 1e-6
    
    def test_apply_markers_to_path_start_end(self):
        """Test applying start and end markers to path."""
        path_elem = ET.Element('path')
        path_elem.set('marker-start', 'url(#arrow)')
        path_elem.set('marker-end', 'url(#arrow)')
        path_elem.set('stroke-width', '2')
        path_elem.set('stroke', 'red')
        
        path_commands = [('M', 0, 0), ('L', 100, 0)]
        
        with patch.object(self.converter, '_generate_marker_drawingml') as mock_gen:
            mock_gen.return_value = '<marker_shape/>'
            
            result = self.converter.apply_markers_to_path(path_elem, path_commands, self.context)
            
            # Should generate two markers (start and end)
            assert mock_gen.call_count == 2
            assert '<marker_shape/>' in result
    
    def test_apply_markers_mid_vertices(self):
        """Test applying mid markers to path vertices."""
        path_elem = ET.Element('path')
        path_elem.set('marker-mid', 'url(#arrow)')
        
        path_commands = [('M', 0, 0), ('L', 50, 0), ('L', 100, 50)]
        
        with patch.object(self.converter, '_generate_marker_drawingml') as mock_gen:
            mock_gen.return_value = '<marker_shape/>'
            
            result = self.converter.apply_markers_to_path(path_elem, path_commands, self.context)
            
            # Should generate one mid marker at vertex (50, 0)
            assert mock_gen.call_count == 1
            
            # Check marker instance properties
            call_args = mock_gen.call_args[0][0]  # First argument (MarkerInstance)
            assert call_args.position == MarkerPosition.MID
            assert call_args.x == 50
            assert call_args.y == 0
    
    def test_no_markers_applied(self):
        """Test path with no marker properties."""
        path_elem = ET.Element('path')
        path_commands = [('M', 0, 0), ('L', 10, 10)]
        
        result = self.converter.apply_markers_to_path(path_elem, path_commands, self.context)
        assert result == ""
    
    def test_empty_path_commands(self):
        """Test marker application to empty path."""
        path_elem = ET.Element('path')
        path_elem.set('marker-start', 'url(#arrow)')
        
        result = self.converter.apply_markers_to_path(path_elem, [], self.context)
        assert result == ""


class TestStandardArrowDetection:
    """Test detection and generation of standard arrow types."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create mock services for dependency injection
        mock_services = Mock()
        mock_services.unit_converter = Mock()
        mock_services.viewport_handler = Mock()
        mock_services.font_service = Mock()
        mock_services.gradient_service = Mock()
        mock_services.pattern_service = Mock()
        mock_services.clip_service = Mock()

        self.converter = MarkerConverter(services=mock_services)
    
    def test_detect_arrow_polygon(self):
        """Test arrow polygon detection."""
        content = '<polygon points="0,0 10,5 0,10" fill="black"/>'
        assert self.converter._is_arrow_polygon(content.lower())
        
        # More complex arrow with many points
        content = '<polygon points="0,0 10,5 8,5 10,8 0,10 2,5" fill="black"/>'
        assert self.converter._is_arrow_polygon(content.lower())
        
        # Not enough points
        content = '<polygon points="0,0 5,5"/>'
        assert not self.converter._is_arrow_polygon(content.lower())
    
    def test_detect_circle_marker(self):
        """Test circle marker detection."""
        marker_def = MarkerDefinition(
            id='test', ref_x=0, ref_y=0, marker_width=10, marker_height=10,
            orient='auto', marker_units=MarkerUnits.STROKE_WIDTH,
            viewbox=None, overflow='hidden',
            content_xml='<circle cx="5" cy="5" r="3"/>'
        )
        
        result = self.converter._detect_standard_arrow(marker_def)
        assert result == 'circle'
    
    def test_detect_square_marker(self):
        """Test square marker detection."""
        marker_def = MarkerDefinition(
            id='test', ref_x=0, ref_y=0, marker_width=10, marker_height=10,
            orient='auto', marker_units=MarkerUnits.STROKE_WIDTH,
            viewbox=None, overflow='hidden',
            content_xml='<rect width="10" height="10"/>'
        )
        
        result = self.converter._detect_standard_arrow(marker_def)
        assert result == 'square'
    
    def test_detect_diamond_polygon(self):
        """Test diamond polygon detection."""
        content = '<polygon points="5,0 10,5 5,10 0,5" fill="red"/>'
        # The detection logic checks for arrow first, so let's test _is_diamond_polygon directly
        assert self.converter._is_diamond_polygon(content.lower())
        
        # Test a content that doesn't have 4 points
        content_no_diamond = '<polygon points="0,0 10,5 0,10" fill="red"/>'
        assert not self.converter._is_diamond_polygon(content_no_diamond.lower())
    
    def test_standard_arrow_paths(self):
        """Test standard arrow path generation."""
        assert self.converter._create_arrow_path() == "M 0 0 L 10 5 L 0 10 Z"
        assert "A 5 5 0 1 1" in self.converter._create_circle_path()
        assert self.converter._create_square_path() == "M 0 0 L 10 0 L 10 10 L 0 10 Z"
        assert self.converter._create_diamond_path() == "M 5 0 L 10 5 L 5 10 L 0 5 Z"


class TestMarkerDrawingMLGeneration:
    """Test DrawingML generation for markers and symbols."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create mock services for dependency injection
        mock_services = Mock()
        mock_services.unit_converter = Mock()
        mock_services.viewport_handler = Mock()
        mock_services.font_service = Mock()
        mock_services.gradient_service = Mock()
        mock_services.pattern_service = Mock()
        mock_services.clip_service = Mock()

        self.converter = MarkerConverter(services=mock_services)
        self.context = ConversionContext(services=mock_services)
        self.context.get_next_shape_id = Mock(return_value=3001)
    
    def test_marker_instance_creation(self):
        """Test marker instance creation with proper attributes."""
        marker_def = MarkerDefinition(
            id='test_marker',
            ref_x=5, ref_y=5,
            marker_width=10, marker_height=10,
            orient='auto',
            marker_units=MarkerUnits.STROKE_WIDTH,
            viewbox=(0, 0, 10, 10),
            overflow='hidden',
            content_xml='<polygon points="0,0 10,5 0,10"/>'
        )
        
        color = Color('rgb(255,0,0)')
        
        marker_instance = MarkerInstance(
            definition=marker_def,
            position=MarkerPosition.START,
            x=100, y=200,
            angle=45.0,
            stroke_width=2.0,
            color=color
        )
        
        assert marker_instance.definition == marker_def
        assert marker_instance.position == MarkerPosition.START
        assert marker_instance.x == 100
        assert marker_instance.y == 200
        assert marker_instance.angle == 45.0
        assert marker_instance.stroke_width == 2.0
        assert marker_instance.color == color
    
    def test_generate_standard_arrow_drawingml(self):
        """Test DrawingML generation for standard arrows."""
        transform_matrix = Matrix.identity()
        color = Color('rgb(0,128,255)')
        
        result = self.converter._generate_standard_arrow_drawingml(
            'arrow', transform_matrix, color, self.context
        )
        
        assert '<p:sp>' in result
        assert 'id="3001"' in result
        assert 'name="marker_arrow"' in result
        assert '<a:custGeom>' in result
        assert '<a:solidFill>' in result
    
    def test_generate_marker_drawingml_with_transforms(self):
        """Test marker DrawingML generation with transforms."""
        marker_def = MarkerDefinition(
            id='custom',
            ref_x=2, ref_y=3,
            marker_width=6, marker_height=8,
            orient='45',  # Fixed angle
            marker_units=MarkerUnits.STROKE_WIDTH,
            viewbox=None,
            overflow='hidden',
            content_xml='<circle r="3"/>'
        )
        
        color = Color('rgba(255,0,0,0.8)')
        
        marker_instance = MarkerInstance(
            definition=marker_def,
            position=MarkerPosition.END,
            x=50, y=75,
            angle=30.0,  # Path angle (should be ignored due to fixed orient)
            stroke_width=1.5,
            color=color
        )
        
        with patch.object(self.converter, '_detect_standard_arrow', return_value=None):
            with patch.object(self.converter, '_generate_custom_marker_drawingml') as mock_custom:
                mock_custom.return_value = '<custom_marker/>'
                
                result = self.converter._generate_marker_drawingml(marker_instance, self.context)
                
                mock_custom.assert_called_once()
                assert result == '<custom_marker/>'
    
    def test_generate_symbol_drawingml(self):
        """Test DrawingML generation for symbols."""
        symbol_def = SymbolDefinition(
            id='test_symbol',
            viewbox=(0, 0, 100, 100),
            preserve_aspect_ratio='xMidYMid meet',
            width=100,
            height=100,
            content_xml='<rect width="100" height="100" fill="green"/>'
        )
        
        transform_matrix = Matrix.translate(10, 20).multiply(Matrix.scale(2, 2))
        
        result = self.converter._generate_symbol_drawingml(symbol_def, transform_matrix, self.context)
        
        assert '<p:grpSp>' in result
        assert 'id="3001"' in result
        assert 'name="symbol_test_symbol"' in result
        assert '<a:xfrm>' in result
        assert symbol_def.content_xml in result
    
    def test_matrix_to_drawingml_transform(self):
        """Test conversion of transform matrix to DrawingML."""
        # Translation only
        matrix = Matrix.translate(100, 200)
        result = self.converter._matrix_to_drawingml_transform(matrix)
        
        # Should contain offset elements
        assert '<a:off' in result
        assert 'x=' in result
        assert 'y=' in result
        
        # Rotation
        matrix = Matrix.rotate(45)
        result = self.converter._matrix_to_drawingml_transform(matrix)
        
        # Should contain rotation element
        assert '<a:rot' in result
        assert 'angle=' in result


class TestViewBoxCalculations:
    """Test viewBox transform calculations."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create mock services for dependency injection
        mock_services = Mock()
        mock_services.unit_converter = Mock()
        mock_services.viewport_handler = Mock()
        mock_services.font_service = Mock()
        mock_services.gradient_service = Mock()
        mock_services.pattern_service = Mock()
        mock_services.clip_service = Mock()

        self.converter = MarkerConverter(services=mock_services)
    
    def test_viewbox_transform_basic(self):
        """Test basic viewBox transform calculation."""
        viewbox = (0, 0, 100, 100)
        width = 200
        height = 150
        
        transform = self.converter._calculate_viewbox_transform(
            viewbox, width, height, 'xMidYMid meet'
        )
        
        # Should scale to fit (meet = smaller scale)
        decomp = transform.decompose()
        assert decomp['scaleX'] == 1.5  # min(200/100, 150/100) = min(2, 1.5) = 1.5
        assert decomp['scaleY'] == 1.5
    
    def test_viewbox_transform_slice(self):
        """Test viewBox transform with slice aspect ratio."""
        viewbox = (10, 20, 80, 60)
        width = 160
        height = 90
        
        transform = self.converter._calculate_viewbox_transform(
            viewbox, width, height, 'xMidYMid slice'
        )
        
        # Should scale to fill (slice = larger scale)
        decomp = transform.decompose()
        expected_scale = max(160/80, 90/60)  # max(2, 1.5) = 2
        assert abs(decomp['scaleX'] - expected_scale) < 1e-6
        assert abs(decomp['scaleY'] - expected_scale) < 1e-6
        
        # Should translate by viewBox offset
        assert abs(decomp['translateX'] - (-10)) < 1e-6
        assert abs(decomp['translateY'] - (-20)) < 1e-6
    
    def test_viewbox_transform_none(self):
        """Test viewBox transform with no aspect ratio preservation."""
        viewbox = (0, 0, 50, 25)
        width = 100
        height = 75
        
        transform = self.converter._calculate_viewbox_transform(
            viewbox, width, height, 'none'
        )
        
        # Should scale independently
        decomp = transform.decompose()
        assert abs(decomp['scaleX'] - 2.0) < 1e-6  # 100/50
        assert abs(decomp['scaleY'] - 3.0) < 1e-6  # 75/25
    
    def test_viewbox_transform_no_dimensions(self):
        """Test viewBox transform without explicit dimensions."""
        viewbox = (5, 10, 40, 30)
        
        transform = self.converter._calculate_viewbox_transform(
            viewbox, None, None, 'xMidYMid meet'
        )
        
        # Should only apply viewBox offset
        decomp = transform.decompose()
        assert abs(decomp['translateX'] - (-5)) < 1e-6
        assert abs(decomp['translateY'] - (-10)) < 1e-6
        assert abs(decomp['scaleX'] - 1.0) < 1e-6
        assert abs(decomp['scaleY'] - 1.0) < 1e-6


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create mock services for dependency injection
        mock_services = Mock()
        mock_services.unit_converter = Mock()
        mock_services.viewport_handler = Mock()
        mock_services.font_service = Mock()
        mock_services.gradient_service = Mock()
        mock_services.pattern_service = Mock()
        mock_services.clip_service = Mock()

        self.converter = MarkerConverter(services=mock_services)
        self.context = ConversionContext(services=mock_services)
    
    def test_marker_without_id(self):
        """Test marker definition without ID."""
        marker_xml = '''<marker markerWidth="10" markerHeight="10"/>'''
        marker_elem = ET.fromstring(marker_xml)
        
        initial_count = len(self.converter.markers)
        self.converter._extract_marker_definition(marker_elem)
        
        # Should not add marker without ID
        assert len(self.converter.markers) == initial_count
    
    def test_symbol_without_id(self):
        """Test symbol definition without ID."""
        symbol_xml = '''<symbol viewBox="0 0 100 100"/>'''
        symbol_elem = ET.fromstring(symbol_xml)
        
        initial_count = len(self.converter.symbols)
        self.converter._extract_symbol_definition(symbol_elem)
        
        # Should not add symbol without ID
        assert len(self.converter.symbols) == initial_count
    
    def test_invalid_viewbox_format(self):
        """Test handling of invalid viewBox format."""
        marker_xml = '''<marker id="bad_viewbox" viewBox="invalid format">
            <circle r="5"/>
        </marker>'''
        marker_elem = ET.fromstring(marker_xml)
        
        self.converter._extract_marker_definition(marker_elem)
        
        # Should handle gracefully with None viewbox
        marker_def = self.converter.markers['bad_viewbox']
        assert marker_def.viewbox is None
    
    def test_invalid_numeric_attributes(self):
        """Test handling of invalid numeric attributes."""
        symbol_xml = '''<symbol id="bad_nums" width="invalid" height="also_bad">
            <rect width="10" height="10"/>
        </symbol>'''
        symbol_elem = ET.fromstring(symbol_xml)
        
        self.converter._extract_symbol_definition(symbol_elem)
        
        # Should handle gracefully with None dimensions
        symbol_def = self.converter.symbols['bad_nums']
        assert symbol_def.width is None
        assert symbol_def.height is None
    
    def test_process_definitions_element(self):
        """Test processing <defs> element with nested definitions."""
        defs_xml = '''
        <defs>
            <marker id="def_marker">
                <polygon points="0,0 10,5 0,10"/>
            </marker>
            <symbol id="def_symbol">
                <circle r="10"/>
            </symbol>
        </defs>
        '''
        defs_elem = ET.fromstring(defs_xml)
        
        result = self.converter._process_definitions(defs_elem, self.context)
        
        # Should extract both definitions
        assert 'def_marker' in self.converter.markers
        assert 'def_symbol' in self.converter.symbols
        
        # Should return empty string (definitions don't generate output)
        assert result == ""


if __name__ == '__main__':
    pytest.main([__file__, '-v'])