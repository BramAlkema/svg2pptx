"""
Tests for SVG Symbol and Use Element Converter

Tests comprehensive symbol and use element functionality including:
- Symbol definition extraction and storage
- Use element instantiation with proper transforms
- Nested symbol and use element support
- ViewBox handling for symbol scaling
- Transform application and coordinate system handling
- Recursion prevention and error handling
"""

import pytest
from lxml import etree as ET
from unittest.mock import Mock, patch, MagicMock
from src.converters.symbols import SymbolConverter, SymbolDefinition, UseInstance
from src.converters.base import ConversionContext
from src.transforms import TransformMatrix


class TestSymbolConverter:
    """Test suite for SymbolConverter functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.converter = SymbolConverter()
        self.context = Mock(spec=ConversionContext)
        
        # Create mock SVG root
        self.svg_root = ET.Element("svg", nsmap={'svg': 'http://www.w3.org/2000/svg'})
        self.defs = ET.SubElement(self.svg_root, "defs")
        self.context.svg_root = self.svg_root
        self.context.get_next_shape_id = Mock(return_value=1)
        
        # Mock converter registry
        self.context.converter_registry = Mock()
        mock_converter = Mock()
        mock_converter.convert = Mock(return_value="<mock_converted_content/>")
        self.context.converter_registry.get_converter_for_element = Mock(return_value=mock_converter)

    def test_initialization(self):
        """Test converter initialization"""
        converter = SymbolConverter()
        assert hasattr(converter, 'symbols')
        assert converter.symbols == {}
        assert converter.supported_elements == ['symbol', 'use', 'defs']
        assert hasattr(converter, 'use_processing_stack')
        assert hasattr(converter, 'symbol_content_cache')

    def test_can_convert_symbol(self):
        """Test detection of symbol elements"""
        element = ET.Element("symbol")
        assert self.converter.can_convert(element, self.context) is True

    def test_can_convert_use(self):
        """Test detection of use elements"""
        element = ET.Element("use")
        assert self.converter.can_convert(element, self.context) is True

    def test_can_convert_defs(self):
        """Test detection of defs elements"""
        element = ET.Element("defs")
        assert self.converter.can_convert(element, self.context) is True

    def test_can_convert_unsupported(self):
        """Test rejection of unsupported elements"""
        element = ET.Element("rect")
        assert self.converter.can_convert(element, self.context) is False


class TestSymbolDefinitionExtraction:
    """Test symbol definition parsing and extraction"""

    def setup_method(self):
        """Set up test fixtures"""
        self.converter = SymbolConverter()

    def test_extract_basic_symbol(self):
        """Test extraction of basic symbol definition"""
        symbol_xml = """
        <symbol id="test-symbol">
            <rect x="0" y="0" width="10" height="10"/>
        </symbol>
        """
        symbol_element = ET.fromstring(symbol_xml)
        
        self.converter._extract_symbol_definition(symbol_element)
        
        assert "test-symbol" in self.converter.symbols
        symbol_def = self.converter.symbols["test-symbol"]
        assert symbol_def.id == "test-symbol"
        assert symbol_def.viewBox is None
        assert symbol_def.width is None
        assert symbol_def.height is None

    def test_extract_symbol_with_viewbox(self):
        """Test extraction of symbol with viewBox"""
        symbol_xml = """
        <symbol id="vb-symbol" viewBox="0 0 100 100">
            <circle cx="50" cy="50" r="25"/>
        </symbol>
        """
        symbol_element = ET.fromstring(symbol_xml)
        
        self.converter._extract_symbol_definition(symbol_element)
        
        symbol_def = self.converter.symbols["vb-symbol"]
        assert symbol_def.viewBox == (0.0, 0.0, 100.0, 100.0)

    def test_extract_symbol_with_dimensions(self):
        """Test extraction of symbol with width and height"""
        symbol_xml = """
        <symbol id="sized-symbol" width="50" height="30">
            <rect x="0" y="0" width="50" height="30"/>
        </symbol>
        """
        symbol_element = ET.fromstring(symbol_xml)
        
        self.converter._extract_symbol_definition(symbol_element)
        
        symbol_def = self.converter.symbols["sized-symbol"]
        assert symbol_def.width == 50.0
        assert symbol_def.height == 30.0

    def test_extract_symbol_invalid_viewbox(self):
        """Test handling of invalid viewBox values"""
        symbol_xml = """
        <symbol id="invalid-vb" viewBox="invalid values">
            <rect x="0" y="0" width="10" height="10"/>
        </symbol>
        """
        symbol_element = ET.fromstring(symbol_xml)
        
        self.converter._extract_symbol_definition(symbol_element)
        
        symbol_def = self.converter.symbols["invalid-vb"]
        assert symbol_def.viewBox is None

    def test_extract_symbol_no_id(self):
        """Test handling of symbol without ID"""
        symbol_xml = """
        <symbol>
            <rect x="0" y="0" width="10" height="10"/>
        </symbol>
        """
        symbol_element = ET.fromstring(symbol_xml)
        
        self.converter._extract_symbol_definition(symbol_element)
        
        # Should not be stored without ID
        assert len(self.converter.symbols) == 0


class TestUseElementParsing:
    """Test use element parsing and instantiation"""

    def setup_method(self):
        """Set up test fixtures"""
        self.converter = SymbolConverter()

    def test_parse_basic_use_element(self):
        """Test parsing of basic use element"""
        use_xml = '<use href="#test-symbol"/>'
        use_element = ET.fromstring(use_xml)
        
        use_instance = self.converter._parse_use_element(use_element)
        
        assert use_instance.href == "test-symbol"
        assert use_instance.x == 0.0
        assert use_instance.y == 0.0
        assert use_instance.width is None
        assert use_instance.height is None
        assert use_instance.transform is None

    def test_parse_use_with_xlink_href(self):
        """Test parsing use element with xlink:href"""
        use_xml = '<use xmlns:xlink="http://www.w3.org/1999/xlink" xlink:href="#test-symbol"/>'
        use_element = ET.fromstring(use_xml)
        
        use_instance = self.converter._parse_use_element(use_element)
        
        assert use_instance.href == "test-symbol"

    def test_parse_use_with_position(self):
        """Test parsing use element with x,y position"""
        use_xml = '<use href="#test-symbol" x="10" y="20"/>'
        use_element = ET.fromstring(use_xml)
        
        use_instance = self.converter._parse_use_element(use_element)
        
        assert use_instance.x == 10.0
        assert use_instance.y == 20.0

    def test_parse_use_with_dimensions(self):
        """Test parsing use element with width and height"""
        use_xml = '<use href="#test-symbol" width="50" height="30"/>'
        use_element = ET.fromstring(use_xml)
        
        use_instance = self.converter._parse_use_element(use_element)
        
        assert use_instance.width == 50.0
        assert use_instance.height == 30.0

    def test_parse_use_with_transform(self):
        """Test parsing use element with transform"""
        use_xml = '<use href="#test-symbol" transform="translate(10,20) scale(2)"/>'
        use_element = ET.fromstring(use_xml)
        
        # Mock transform parser
        mock_transform = Mock(spec=TransformMatrix)
        with patch.object(self.converter, 'transform_parser') as mock_parser:
            mock_parser.parse_to_matrix.return_value = mock_transform
            
            use_instance = self.converter._parse_use_element(use_element)
            
            assert use_instance.transform == mock_transform
            mock_parser.parse_to_matrix.assert_called_once_with("translate(10,20) scale(2)")


class TestSymbolInstantiation:
    """Test symbol instantiation logic"""

    def setup_method(self):
        """Set up test fixtures"""
        self.converter = SymbolConverter()
        self.context = Mock(spec=ConversionContext)
        self.context.get_next_shape_id = Mock(return_value=1)
        
        # Create mock SVG with symbol
        self.svg_root = ET.Element("svg")
        self.context.svg_root = self.svg_root
        
        symbol_xml = """
        <symbol id="test-symbol" viewBox="0 0 100 100">
            <rect x="10" y="10" width="80" height="80" fill="blue"/>
        </symbol>
        """
        symbol_element = ET.fromstring(symbol_xml)
        self.svg_root.append(symbol_element)

    def test_find_referenced_element(self):
        """Test finding referenced element by ID"""
        element = self.converter._find_referenced_element("test-symbol", self.context)
        
        assert element is not None
        assert element.get('id') == 'test-symbol'

    def test_find_nonexistent_element(self):
        """Test handling of nonexistent referenced element"""
        element = self.converter._find_referenced_element("nonexistent", self.context)
        
        assert element is None

    def test_symbol_scaling_calculation(self):
        """Test symbol scaling calculation"""
        # Create symbol with viewBox
        symbol_def = SymbolDefinition(
            id="test-symbol",
            element=Mock(),
            viewBox=(0, 0, 100, 100)
        )
        
        # Use with different dimensions
        use_instance = UseInstance(
            href="test-symbol",
            width=200.0,
            height=150.0
        )
        
        scale_x, scale_y = self.converter._calculate_symbol_scaling(symbol_def, use_instance)
        
        assert scale_x == 2.0  # 200/100
        assert scale_y == 1.5  # 150/100

    def test_symbol_scaling_no_use_dimensions(self):
        """Test symbol scaling when use element has no dimensions"""
        symbol_def = SymbolDefinition(
            id="test-symbol",
            element=Mock(),
            viewBox=(0, 0, 100, 100)
        )
        
        use_instance = UseInstance(href="test-symbol")
        
        scale_x, scale_y = self.converter._calculate_symbol_scaling(symbol_def, use_instance)
        
        assert scale_x == 1.0
        assert scale_y == 1.0

    def test_symbol_scaling_with_explicit_dimensions(self):
        """Test symbol scaling with explicit symbol dimensions"""
        symbol_def = SymbolDefinition(
            id="test-symbol",
            element=Mock(),
            width=50.0,
            height=40.0
        )
        
        use_instance = UseInstance(
            href="test-symbol",
            width=100.0,
            height=80.0
        )
        
        scale_x, scale_y = self.converter._calculate_symbol_scaling(symbol_def, use_instance)
        
        assert scale_x == 2.0  # 100/50
        assert scale_y == 2.0  # 80/40


class TestRecursionPrevention:
    """Test recursion prevention in use elements"""

    def setup_method(self):
        """Set up test fixtures"""
        self.converter = SymbolConverter()
        self.context = Mock(spec=ConversionContext)
        self.context.svg_root = ET.Element("svg")
        self.context.get_next_shape_id = Mock(return_value=1)

    def test_circular_reference_detection(self):
        """Test detection of circular references"""
        # Simulate processing stack
        self.converter.use_processing_stack = ["symbol1"]
        
        use_xml = '<use href="#symbol1"/>'
        use_element = ET.fromstring(use_xml)
        
        result = self.converter._process_use_element(use_element, self.context)
        
        assert "Circular reference detected: symbol1" in result

    def test_deep_nesting_prevention(self):
        """Test prevention of deep nesting"""
        # Create nested symbol structure
        use_xml = '<use href="#nested-symbol"/>'
        use_element = ET.fromstring(use_xml)
        
        # Mock the referenced element
        with patch.object(self.converter, '_find_referenced_element') as mock_find:
            mock_find.return_value = None
            
            result = self.converter._process_use_element(use_element, self.context)
            
            assert "Referenced element not found: nested-symbol" in result


class TestTransformApplication:
    """Test transform application for use elements"""

    def setup_method(self):
        """Set up test fixtures"""
        self.converter = SymbolConverter()

    def test_apply_use_transforms_basic(self):
        """Test basic transform application"""
        element = ET.Element("rect", {'x': '0', 'y': '0', 'width': '10', 'height': '10'})
        use_instance = UseInstance(href="test", x=10, y=20)
        
        result = self.converter._apply_use_transforms(element, use_instance)
        
        assert result.get('transform') == 'translate(10,20)'

    def test_apply_use_transforms_with_existing(self):
        """Test transform application with existing transform"""
        element = ET.Element("rect", {
            'x': '0', 'y': '0', 'width': '10', 'height': '10',
            'transform': 'rotate(45)'
        })
        use_instance = UseInstance(href="test", x=10, y=20)
        
        result = self.converter._apply_use_transforms(element, use_instance)
        
        assert result.get('transform') == 'translate(10,20) rotate(45)'

    def test_apply_use_transforms_matrix(self):
        """Test transform application with matrix transform"""
        element = ET.Element("rect", {'x': '0', 'y': '0', 'width': '10', 'height': '10'})
        
        # Create mock transform matrix
        mock_matrix = Mock(spec=TransformMatrix)
        mock_matrix.is_identity.return_value = False
        mock_matrix.a, mock_matrix.b, mock_matrix.c = 1, 0, 0
        mock_matrix.d, mock_matrix.e, mock_matrix.f = 1, 5, 10
        
        use_instance = UseInstance(href="test", x=10, y=20, transform=mock_matrix)
        
        result = self.converter._apply_use_transforms(element, use_instance)
        
        expected_transform = 'translate(10,20) matrix(1,0,0,1,5,10)'
        assert result.get('transform') == expected_transform


class TestUtilityFunctions:
    """Test utility functions"""

    def setup_method(self):
        """Set up test fixtures"""
        self.converter = SymbolConverter()

    def test_parse_dimension_valid(self):
        """Test parsing valid dimension strings"""
        assert self.converter._parse_dimension("10") == 10.0
        assert self.converter._parse_dimension("15.5px") == 15.5
        assert self.converter._parse_dimension("20pt") == 20.0
        assert self.converter._parse_dimension("100%") == 100.0

    def test_parse_dimension_invalid(self):
        """Test parsing invalid dimension strings"""
        assert self.converter._parse_dimension("") is None
        assert self.converter._parse_dimension(None) is None
        assert self.converter._parse_dimension("invalid") is None

    def test_symbol_management_functions(self):
        """Test symbol management utility functions"""
        # Create test symbol
        symbol_def = SymbolDefinition(id="test", element=Mock())
        self.converter.symbols["test"] = symbol_def
        
        # Test getter
        assert self.converter.get_symbol_definition("test") == symbol_def
        assert self.converter.get_symbol_definition("nonexistent") is None
        
        # Test has_symbol
        assert self.converter.has_symbol("test") is True
        assert self.converter.has_symbol("nonexistent") is False
        
        # Test cache clearing
        self.converter.symbol_content_cache["test"] = "cached_content"
        self.converter.clear_cache()
        assert len(self.converter.symbol_content_cache) == 0


class TestIntegration:
    """Integration tests for symbol converter"""

    def setup_method(self):
        """Set up test fixtures"""
        self.converter = SymbolConverter()
        self.context = Mock(spec=ConversionContext)
        
        # Create complete SVG with symbols and use elements
        svg_content = """
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">
            <defs>
                <symbol id="star" viewBox="0 0 20 20">
                    <path d="M10,2 L12,8 L18,8 L13,12 L15,18 L10,14 L5,18 L7,12 L2,8 L8,8 Z" fill="gold"/>
                </symbol>
            </defs>
            <use href="#star" x="50" y="50" width="30" height="30"/>
            <use href="#star" x="100" y="100" transform="scale(0.5)"/>
        </svg>
        """
        self.svg_root = ET.fromstring(svg_content)
        self.context.svg_root = self.svg_root
        self.context.get_next_shape_id = Mock(return_value=1)

    def test_complete_symbol_workflow(self):
        """Test complete workflow from definition to instantiation"""
        # Process defs section
        defs = self.svg_root.find('.//defs')
        self.converter.convert(defs, self.context)
        
        # Verify symbol was extracted
        assert self.converter.has_symbol("star")
        symbol_def = self.converter.get_symbol_definition("star")
        assert symbol_def.viewBox == (0.0, 0.0, 20.0, 20.0)
        
        # Process use elements
        use_elements = self.svg_root.findall('.//use')
        assert len(use_elements) == 2
        
        # Mock converter registry for symbol content conversion
        mock_converter = Mock()
        mock_converter.convert = Mock(return_value="<converted_path/>")
        self.context.converter_registry = Mock()
        self.context.converter_registry.get_converter_for_element = Mock(return_value=mock_converter)
        
        # Test first use element
        with patch.object(self.converter, 'transform_converter') as mock_transform:
            mock_transform.get_drawingml_transform.return_value = "<transform_xml/>"
            
            result1 = self.converter.convert(use_elements[0], self.context)
            
            # Should generate group with proper structure
            assert "<a:grpSp>" in result1
            assert "symbol_star_1" in result1
            assert "<converted_path/>" in result1