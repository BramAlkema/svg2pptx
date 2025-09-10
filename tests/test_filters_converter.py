#!/usr/bin/env python3
"""
Comprehensive tests for SVG filter effects converter.

This test suite provides strategic coverage of the filters module following
the proven Phase 1 methodology:
- Data classes and enums testing
- Filter primitive parsing and processing  
- Filter chain processing and complexity analysis
- PowerPoint effect generation and rasterization decisions
- Integration scenarios and edge cases
"""

import pytest
import math
from unittest.mock import Mock, patch, MagicMock
from lxml import etree as ET
from typing import List, Optional

from src.converters.filters import (
    FilterConverter, FilterDefinition, FilterPrimitive,
    GaussianBlurPrimitive, DropShadowPrimitive, OffsetPrimitive,
    FloodPrimitive, ColorMatrixPrimitive, CompositePrimitive, FilterEffect,
    FilterPrimitiveType, FilterUnits, ColorMatrixType
)
from src.converters.base import ConversionContext
from src.colors import ColorInfo


class TestFilterEnums:
    """Test filter-related enums."""
    
    def test_filter_primitive_type_values(self):
        """Test FilterPrimitiveType enum values."""
        assert FilterPrimitiveType.GAUSSIAN_BLUR.value == "feGaussianBlur"
        assert FilterPrimitiveType.DROP_SHADOW.value == "feDropShadow"
        assert FilterPrimitiveType.OFFSET.value == "feOffset"
        assert FilterPrimitiveType.FLOOD.value == "feFlood"
        assert FilterPrimitiveType.COLOR_MATRIX.value == "feColorMatrix"
        assert FilterPrimitiveType.COMPOSITE.value == "feComposite"
        assert FilterPrimitiveType.MORPH.value == "feMorphology"
        assert FilterPrimitiveType.CONVOLVE.value == "feConvolveMatrix"
        assert FilterPrimitiveType.LIGHTING.value == "feDiffuseLighting"
        assert FilterPrimitiveType.TURBULENCE.value == "feTurbulence"
    
    def test_filter_units_values(self):
        """Test FilterUnits enum values."""
        assert FilterUnits.OBJECT_BOUNDING_BOX.value == "objectBoundingBox"
        assert FilterUnits.USER_SPACE_ON_USE.value == "userSpaceOnUse"
    
    def test_color_matrix_type_values(self):
        """Test ColorMatrixType enum values."""
        assert ColorMatrixType.MATRIX.value == "matrix"
        assert ColorMatrixType.SATURATE.value == "saturate"
        assert ColorMatrixType.HUE_ROTATE.value == "hueRotate"
        assert ColorMatrixType.LUMINANCE_TO_ALPHA.value == "luminanceToAlpha"


class TestFilterDataClasses:
    """Test filter data classes."""
    
    def test_filter_definition_creation(self):
        """Test FilterDefinition creation."""
        filter_def = FilterDefinition(
            id="filter1",
            x=-0.1, y=-0.1, width=1.2, height=1.2,
            filter_units=FilterUnits.OBJECT_BOUNDING_BOX,
            primitive_units=FilterUnits.USER_SPACE_ON_USE,
            primitives=[]
        )
        
        assert filter_def.id == "filter1"
        assert filter_def.x == -0.1
        assert filter_def.y == -0.1
        assert filter_def.width == 1.2
        assert filter_def.height == 1.2
        assert filter_def.filter_units == FilterUnits.OBJECT_BOUNDING_BOX
        assert filter_def.primitive_units == FilterUnits.USER_SPACE_ON_USE
        assert filter_def.primitives == []
    
    def test_filter_definition_get_bounding_box(self):
        """Test FilterDefinition bounding box calculation."""
        filter_def = FilterDefinition(
            id="test", x=10.0, y=20.0, width=100.0, height=80.0,
            filter_units=FilterUnits.USER_SPACE_ON_USE,
            primitive_units=FilterUnits.USER_SPACE_ON_USE,
            primitives=[]
        )
        
        bbox = filter_def.get_bounding_box()
        assert bbox == (10.0, 20.0, 100.0, 80.0)
    
    def test_filter_primitive_base(self):
        """Test base FilterPrimitive functionality."""
        primitive = FilterPrimitive(
            type=FilterPrimitiveType.GAUSSIAN_BLUR,
            input="SourceGraphic",
            result="blur1",
            x=0.0, y=0.0, width=1.0, height=1.0
        )
        
        assert primitive.type == FilterPrimitiveType.GAUSSIAN_BLUR
        assert primitive.input == "SourceGraphic"
        assert primitive.result == "blur1"
        region = primitive.get_region()
        assert region == (0.0, 0.0, 1.0, 1.0)
    
    def test_gaussian_blur_primitive(self):
        """Test GaussianBlurPrimitive specific functionality."""
        blur = GaussianBlurPrimitive(
            type=FilterPrimitiveType.GAUSSIAN_BLUR,
            input="SourceGraphic", result="blur1",
            x=0.0, y=0.0, width=1.0, height=1.0,
            std_deviation_x=2.0, std_deviation_y=3.0,
            edge_mode="wrap"
        )
        
        assert blur.std_deviation_x == 2.0
        assert blur.std_deviation_y == 3.0
        assert blur.edge_mode == "wrap"
    
    def test_drop_shadow_primitive(self):
        """Test DropShadowPrimitive functionality."""
        color = ColorInfo(red=128, green=128, blue=128, alpha=0.8)
        shadow = DropShadowPrimitive(
            type=FilterPrimitiveType.DROP_SHADOW,
            input="SourceGraphic", result="shadow1",
            x=0.0, y=0.0, width=1.0, height=1.0,
            dx=2.0, dy=2.0, std_deviation=1.5,
            flood_color=color, flood_opacity=0.8
        )
        
        assert shadow.dx == 2.0
        assert shadow.dy == 2.0
        assert shadow.std_deviation == 1.5
        assert shadow.flood_color == color
        assert shadow.flood_opacity == 0.8
    
    def test_color_matrix_primitive(self):
        """Test ColorMatrixPrimitive functionality."""
        matrix_values = [1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0]
        color_matrix = ColorMatrixPrimitive(
            type=FilterPrimitiveType.COLOR_MATRIX,
            input="SourceGraphic", result="colorized",
            x=0.0, y=0.0, width=1.0, height=1.0,
            matrix_type=ColorMatrixType.MATRIX,
            values=matrix_values
        )
        
        assert color_matrix.matrix_type == ColorMatrixType.MATRIX
        assert color_matrix.values == matrix_values
    
    def test_composite_primitive(self):
        """Test CompositePrimitive functionality."""
        composite = CompositePrimitive(
            type=FilterPrimitiveType.COMPOSITE,
            input="blur1", result="composite1",
            x=0.0, y=0.0, width=1.0, height=1.0,
            input2="shadow1", operator="over",
            k1=1.0, k2=2.0, k3=3.0, k4=4.0
        )
        
        assert composite.input2 == "shadow1"
        assert composite.operator == "over"
        assert composite.k1 == 1.0
        assert composite.k2 == 2.0
        assert composite.k3 == 3.0
        assert composite.k4 == 4.0
    
    def test_filter_effect(self):
        """Test FilterEffect data class."""
        effect = FilterEffect(
            effect_type="blur",
            parameters={"radius": 5.0},
            requires_rasterization=False,
            complexity_score=1.5
        )
        
        assert effect.effect_type == "blur"
        assert effect.parameters["radius"] == 5.0
        assert effect.requires_rasterization is False
        assert effect.complexity_score == 1.5


class TestFilterConverter:
    """Test FilterConverter main functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.converter = FilterConverter()
        self.context = Mock()
        self.context.get_next_shape_id.return_value = 2000
        
        # Mock dependencies
        self.converter.color_parser = Mock()
        self.converter.color_parser.parse.return_value = ColorInfo(255, 0, 0, 1.0)
        self.converter.unit_converter = Mock()
        self.converter.unit_converter.convert_to_emu.return_value = 914400
        self.converter.transform_parser = Mock()
        self.converter.viewport_resolver = Mock()
    
    def test_initialization(self):
        """Test converter initialization."""
        assert self.converter.__class__.supported_elements == ['filter', 'defs']
        assert isinstance(self.converter.filters, dict)
        assert len(self.converter.filters) == 0
        assert 'blur' in self.converter.powerpoint_effects
        assert 'shadow' in self.converter.powerpoint_effects
        assert self.converter.rasterization_threshold == 3.0
    
    def test_can_convert_filter_element(self):
        """Test can_convert with filter element."""
        filter_element = ET.Element("filter")
        result = self.converter.can_convert(filter_element, self.context)
        assert result is True
    
    def test_can_convert_defs_element(self):
        """Test can_convert with defs element."""
        defs_element = ET.Element("defs")
        result = self.converter.can_convert(defs_element, self.context)
        assert result is True
    
    def test_can_convert_element_with_filter(self):
        """Test can_convert with element that has filter applied."""
        rect_element = ET.Element("rect")
        rect_element.set("filter", "url(#blur1)")
        result = self.converter.can_convert(rect_element, self.context)
        assert result is True
    
    def test_can_convert_unsupported_element(self):
        """Test can_convert with unsupported element."""
        line_element = ET.Element("line")
        result = self.converter.can_convert(line_element, self.context)
        assert result is False
    
    def test_convert_filter_element(self):
        """Test converting filter element."""
        filter_element = ET.Element("filter")
        filter_element.set("id", "testFilter")
        
        with patch.object(self.converter, '_process_filter_definition') as mock_process:
            mock_process.return_value = ""
            result = self.converter.convert(filter_element, self.context)
            mock_process.assert_called_once_with(filter_element, self.context)
            assert result == ""
    
    def test_convert_defs_element(self):
        """Test converting defs element."""
        defs_element = ET.Element("defs")
        
        with patch.object(self.converter, '_process_filter_definitions') as mock_process:
            mock_process.return_value = ""
            result = self.converter.convert(defs_element, self.context)
            mock_process.assert_called_once_with(defs_element, self.context)
            assert result == ""


class TestFilterDefinitionParsing:
    """Test filter definition parsing."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.converter = FilterConverter()
        self.converter.color_parser = Mock()
        self.converter.color_parser.parse.return_value = ColorInfo(0, 0, 0, 1.0)
    
    def test_extract_filter_definition_basic(self):
        """Test basic filter definition extraction."""
        filter_element = ET.Element("filter")
        filter_element.set("id", "simpleFilter")
        filter_element.set("x", "0")
        filter_element.set("y", "0")
        filter_element.set("width", "100%")
        filter_element.set("height", "100%")
        
        # Add a simple blur primitive
        blur = ET.SubElement(filter_element, "feGaussianBlur")
        blur.set("stdDeviation", "3")
        
        self.converter._extract_filter_definition(filter_element)
        
        assert "simpleFilter" in self.converter.filters
        filter_def = self.converter.filters["simpleFilter"]
        assert filter_def.id == "simpleFilter"
        assert filter_def.x == 0.0
        assert filter_def.y == 0.0
        assert filter_def.width == 1.0  # 100%
        assert filter_def.height == 1.0
        assert len(filter_def.primitives) == 1
        assert isinstance(filter_def.primitives[0], GaussianBlurPrimitive)
    
    def test_extract_filter_definition_percentage_coordinates(self):
        """Test filter definition with percentage coordinates."""
        filter_element = ET.Element("filter")
        filter_element.set("id", "percentFilter")
        filter_element.set("x", "-10%")
        filter_element.set("y", "-10%")
        filter_element.set("width", "120%")
        filter_element.set("height", "120%")
        
        self.converter._extract_filter_definition(filter_element)
        
        filter_def = self.converter.filters["percentFilter"]
        assert filter_def.x == -0.1
        assert filter_def.y == -0.1
        assert filter_def.width == 1.2
        assert filter_def.height == 1.2
    
    def test_extract_filter_definition_no_id(self):
        """Test filter definition without id."""
        filter_element = ET.Element("filter")
        # No id attribute
        
        self.converter._extract_filter_definition(filter_element)
        assert len(self.converter.filters) == 0
    
    def test_extract_filter_definition_units(self):
        """Test filter definition with different units."""
        filter_element = ET.Element("filter")
        filter_element.set("id", "unitsFilter")
        filter_element.set("filterUnits", "userSpaceOnUse")
        filter_element.set("primitiveUnits", "objectBoundingBox")
        
        self.converter._extract_filter_definition(filter_element)
        
        filter_def = self.converter.filters["unitsFilter"]
        assert filter_def.filter_units == FilterUnits.USER_SPACE_ON_USE
        assert filter_def.primitive_units == FilterUnits.OBJECT_BOUNDING_BOX
    
    def test_parse_filter_coordinate(self):
        """Test filter coordinate parsing."""
        # Percentage
        result = self.converter._parse_filter_coordinate("50%")
        assert result == 0.5
        
        # Negative percentage
        result = self.converter._parse_filter_coordinate("-10%")
        assert result == -0.1
        
        # Absolute value
        result = self.converter._parse_filter_coordinate("25")
        assert result == 25.0


class TestFilterPrimitiveParsing:
    """Test filter primitive parsing."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.converter = FilterConverter()
        self.converter.color_parser = Mock()
        self.converter.color_parser.parse.return_value = ColorInfo(128, 128, 128, 0.5)
    
    def test_parse_gaussian_blur_primitive(self):
        """Test parsing feGaussianBlur primitive."""
        blur_element = ET.Element("feGaussianBlur")
        blur_element.set("stdDeviation", "3 5")
        blur_element.set("in", "SourceGraphic")
        blur_element.set("result", "blurred")
        blur_element.set("edgeMode", "wrap")
        
        result = self.converter._parse_filter_primitive(blur_element, FilterUnits.USER_SPACE_ON_USE)
        
        assert isinstance(result, GaussianBlurPrimitive)
        assert result.type == FilterPrimitiveType.GAUSSIAN_BLUR
        assert result.std_deviation_x == 3.0
        assert result.std_deviation_y == 5.0
        assert result.input == "SourceGraphic"
        assert result.result == "blurred"
        assert result.edge_mode == "wrap"
    
    def test_parse_gaussian_blur_single_deviation(self):
        """Test parsing feGaussianBlur with single deviation value."""
        blur_element = ET.Element("feGaussianBlur")
        blur_element.set("stdDeviation", "4")
        
        result = self.converter._parse_filter_primitive(blur_element, FilterUnits.USER_SPACE_ON_USE)
        
        assert result.std_deviation_x == 4.0
        assert result.std_deviation_y == 4.0  # Should use same value
    
    def test_parse_drop_shadow_primitive(self):
        """Test parsing feDropShadow primitive."""
        shadow_element = ET.Element("feDropShadow")
        shadow_element.set("dx", "3")
        shadow_element.set("dy", "4")
        shadow_element.set("stdDeviation", "2")
        shadow_element.set("flood-color", "red")
        shadow_element.set("flood-opacity", "0.8")
        
        result = self.converter._parse_filter_primitive(shadow_element, FilterUnits.USER_SPACE_ON_USE)
        
        assert isinstance(result, DropShadowPrimitive)
        assert result.type == FilterPrimitiveType.DROP_SHADOW
        assert result.dx == 3.0
        assert result.dy == 4.0
        assert result.std_deviation == 2.0
        assert result.flood_opacity == 0.8
        # Color should be parsed by mock
        self.converter.color_parser.parse.assert_called_with("red")
    
    def test_parse_offset_primitive(self):
        """Test parsing feOffset primitive."""
        offset_element = ET.Element("feOffset")
        offset_element.set("dx", "5")
        offset_element.set("dy", "-3")
        offset_element.set("in", "blur1")
        
        result = self.converter._parse_filter_primitive(offset_element, FilterUnits.USER_SPACE_ON_USE)
        
        assert isinstance(result, OffsetPrimitive)
        assert result.type == FilterPrimitiveType.OFFSET
        assert result.dx == 5.0
        assert result.dy == -3.0
        assert result.input == "blur1"
    
    def test_parse_flood_primitive(self):
        """Test parsing feFlood primitive."""
        flood_element = ET.Element("feFlood")
        flood_element.set("flood-color", "blue")
        flood_element.set("flood-opacity", "0.6")
        flood_element.set("result", "flood1")
        
        result = self.converter._parse_filter_primitive(flood_element, FilterUnits.USER_SPACE_ON_USE)
        
        assert isinstance(result, FloodPrimitive)
        assert result.type == FilterPrimitiveType.FLOOD
        assert result.flood_opacity == 0.6
        assert result.result == "flood1"
        self.converter.color_parser.parse.assert_called_with("blue")
    
    def test_parse_color_matrix_primitive(self):
        """Test parsing feColorMatrix primitive."""
        matrix_element = ET.Element("feColorMatrix")
        matrix_element.set("type", "saturate")
        matrix_element.set("values", "0.5")
        matrix_element.set("in", "SourceGraphic")
        
        result = self.converter._parse_filter_primitive(matrix_element, FilterUnits.USER_SPACE_ON_USE)
        
        assert isinstance(result, ColorMatrixPrimitive)
        assert result.type == FilterPrimitiveType.COLOR_MATRIX
        assert result.matrix_type == ColorMatrixType.SATURATE
        assert result.values == [0.5]
        assert result.input == "SourceGraphic"
    
    def test_parse_color_matrix_full_matrix(self):
        """Test parsing feColorMatrix with full matrix."""
        matrix_element = ET.Element("feColorMatrix")
        matrix_element.set("type", "matrix")
        matrix_element.set("values", "1 0 0 0 0.2 0 1 0 0 0 0 0 1 0 0 0 0 0 1 0")
        
        result = self.converter._parse_filter_primitive(matrix_element, FilterUnits.USER_SPACE_ON_USE)
        
        assert result.matrix_type == ColorMatrixType.MATRIX
        assert len(result.values) == 20
        assert result.values[4] == 0.2  # Red channel offset
    
    def test_parse_composite_primitive(self):
        """Test parsing feComposite primitive."""
        composite_element = ET.Element("feComposite")
        composite_element.set("in", "blur1")
        composite_element.set("in2", "offset1")
        composite_element.set("operator", "arithmetic")
        composite_element.set("k1", "0.5")
        composite_element.set("k2", "1.0")
        composite_element.set("k3", "0.5")
        composite_element.set("k4", "0.1")
        
        result = self.converter._parse_filter_primitive(composite_element, FilterUnits.USER_SPACE_ON_USE)
        
        assert isinstance(result, CompositePrimitive)
        assert result.type == FilterPrimitiveType.COMPOSITE
        assert result.input == "blur1"
        assert result.input2 == "offset1"
        assert result.operator == "arithmetic"
        assert result.k1 == 0.5
        assert result.k2 == 1.0
        assert result.k3 == 0.5
        assert result.k4 == 0.1
    
    def test_parse_unknown_primitive(self):
        """Test parsing unknown primitive type."""
        unknown_element = ET.Element("feUnknown")
        
        result = self.converter._parse_filter_primitive(unknown_element, FilterUnits.USER_SPACE_ON_USE)
        assert result is None


class TestFilterApplication:
    """Test filter application to elements."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.converter = FilterConverter()
        self.context = Mock()
        
        # Setup mock methods
        self.converter._process_filter_chain = Mock(return_value=[])
        self.converter._convert_filter_effects_to_drawingml = Mock(return_value="<filter_output/>")
        
        # Create test filter
        blur_primitive = GaussianBlurPrimitive(
            type=FilterPrimitiveType.GAUSSIAN_BLUR,
            input="SourceGraphic", result="blur1",
            x=0, y=0, width=1, height=1,
            std_deviation_x=3.0, std_deviation_y=3.0
        )
        
        filter_def = FilterDefinition(
            id="testFilter",
            x=-0.1, y=-0.1, width=1.2, height=1.2,
            filter_units=FilterUnits.OBJECT_BOUNDING_BOX,
            primitive_units=FilterUnits.USER_SPACE_ON_USE,
            primitives=[blur_primitive]
        )
        
        self.converter.filters["testFilter"] = filter_def
    
    def test_apply_filter_to_element_basic(self):
        """Test basic filter application."""
        element = ET.Element("rect")
        element.set("filter", "url(#testFilter)")
        
        result = self.converter.apply_filter_to_element(element, self.context)
        
        assert result == "<filter_output/>"
        self.converter._process_filter_chain.assert_called_once()
        self.converter._convert_filter_effects_to_drawingml.assert_called_once()
    
    def test_apply_filter_invalid_reference(self):
        """Test filter application with invalid reference."""
        element = ET.Element("circle")
        element.set("filter", "url(#nonexistent)")
        
        result = self.converter.apply_filter_to_element(element, self.context)
        assert result == ""
    
    def test_apply_filter_malformed_reference(self):
        """Test filter application with malformed reference."""
        element = ET.Element("path")
        element.set("filter", "invalid-reference")
        
        result = self.converter.apply_filter_to_element(element, self.context)
        assert result == ""
    
    def test_apply_filter_no_reference(self):
        """Test filter application with no filter attribute."""
        element = ET.Element("ellipse")
        
        result = self.converter.apply_filter_to_element(element, self.context)
        assert result == ""


class TestFilterComplexityAnalysis:
    """Test filter complexity analysis and rasterization decisions."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.converter = FilterConverter()
    
    def test_calculate_filter_complexity_simple(self):
        """Test complexity calculation for simple filters."""
        blur_primitive = GaussianBlurPrimitive(
            type=FilterPrimitiveType.GAUSSIAN_BLUR,
            input="SourceGraphic", result="blur1",
            x=0, y=0, width=1, height=1,
            std_deviation_x=2.0, std_deviation_y=2.0
        )
        
        filter_def = FilterDefinition(
            id="simple", x=0, y=0, width=1, height=1,
            filter_units=FilterUnits.OBJECT_BOUNDING_BOX,
            primitive_units=FilterUnits.USER_SPACE_ON_USE,
            primitives=[blur_primitive]
        )
        
        complexity = self.converter._calculate_filter_complexity(filter_def)
        
        # Single blur should have low complexity
        assert 0.5 <= complexity <= 1.5
    
    def test_calculate_filter_complexity_complex(self):
        """Test complexity calculation for complex filters."""
        # Create multiple primitives
        primitives = []
        
        # Blur (moderate complexity)
        blur = GaussianBlurPrimitive(
            type=FilterPrimitiveType.GAUSSIAN_BLUR,
            input="SourceGraphic", result="blur1",
            x=0, y=0, width=1, height=1,
            std_deviation_x=5.0, std_deviation_y=5.0
        )
        primitives.append(blur)
        
        # Color matrix (high complexity)
        color_matrix = ColorMatrixPrimitive(
            type=FilterPrimitiveType.COLOR_MATRIX,
            input="blur1", result="matrix1",
            x=0, y=0, width=1, height=1,
            matrix_type=ColorMatrixType.MATRIX,
            values=[1, 0, 0, 0, 0] * 4
        )
        primitives.append(color_matrix)
        
        # Composite (high complexity)
        composite = CompositePrimitive(
            type=FilterPrimitiveType.COMPOSITE,
            input="matrix1", result="final",
            x=0, y=0, width=1, height=1,
            input2="SourceGraphic", operator="multiply"
        )
        primitives.append(composite)
        
        filter_def = FilterDefinition(
            id="complex", x=0, y=0, width=1, height=1,
            filter_units=FilterUnits.OBJECT_BOUNDING_BOX,
            primitive_units=FilterUnits.USER_SPACE_ON_USE,
            primitives=primitives
        )
        
        complexity = self.converter._calculate_filter_complexity(filter_def)
        
        # Multiple complex primitives should have high complexity
        assert complexity >= 3.0
    
    def test_convert_primitive_to_effect_blur(self):
        """Test converting blur primitive to effect."""
        blur_primitive = GaussianBlurPrimitive(
            type=FilterPrimitiveType.GAUSSIAN_BLUR,
            input="SourceGraphic", result="blur1",
            x=0, y=0, width=1, height=1,
            std_deviation_x=3.0, std_deviation_y=4.0
        )
        
        effect = self.converter._convert_primitive_to_effect(blur_primitive, False)
        
        assert effect is not None
        assert effect.effect_type == "blur"
        assert effect.parameters["radius"] == 4.0  # max(3.0, 4.0)
        assert effect.requires_rasterization is False
        assert effect.complexity_score == 0.8
    
    def test_convert_primitive_to_effect_color_matrix(self):
        """Test converting color matrix primitive to effect."""
        matrix_primitive = ColorMatrixPrimitive(
            type=FilterPrimitiveType.COLOR_MATRIX,
            input="SourceGraphic", result="colorized",
            x=0, y=0, width=1, height=1,
            matrix_type=ColorMatrixType.SATURATE,
            values=[0.5]
        )
        
        effect = self.converter._convert_primitive_to_effect(matrix_primitive, False)
        
        assert effect is not None
        assert effect.effect_type == "color_matrix"
        assert effect.parameters["type"] == "saturate"
        assert effect.requires_rasterization is True  # Color matrix always requires rasterization
        assert effect.complexity_score == 2.0
    
    def test_convert_primitive_to_effect_unknown(self):
        """Test converting unknown primitive type."""
        # Create a mock primitive that doesn't match known types
        unknown_primitive = FilterPrimitive(
            type=FilterPrimitiveType.TURBULENCE,
            input="SourceGraphic", result="turbulence1",
            x=0, y=0, width=1, height=1
        )
        
        effect = self.converter._convert_primitive_to_effect(unknown_primitive, False)
        assert effect is None


class TestFilterIntegrationScenarios:
    """Test complex filter integration scenarios."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.converter = FilterConverter()
        self.context = Mock()
        self.converter.color_parser = Mock()
        self.converter.color_parser.parse.return_value = ColorInfo(0, 0, 0, 1.0)
    
    def test_complete_filter_workflow(self):
        """Test complete filter processing workflow."""
        # Step 1: Create filter definition with multiple primitives
        filter_element = ET.Element("filter")
        filter_element.set("id", "complexFilter")
        
        # Add blur primitive
        blur = ET.SubElement(filter_element, "feGaussianBlur")
        blur.set("stdDeviation", "3")
        blur.set("in", "SourceGraphic")
        blur.set("result", "blur")
        
        # Add offset primitive
        offset = ET.SubElement(filter_element, "feOffset")
        offset.set("dx", "2")
        offset.set("dy", "2")
        offset.set("in", "blur")
        offset.set("result", "offset")
        
        # Process filter definition
        self.converter._extract_filter_definition(filter_element)
        
        assert "complexFilter" in self.converter.filters
        filter_def = self.converter.filters["complexFilter"]
        assert len(filter_def.primitives) == 2
        
        # Step 2: Apply filter to element
        target_element = ET.Element("rect")
        target_element.set("filter", "url(#complexFilter)")
        
        with patch.object(self.converter, '_process_filter_chain') as mock_chain:
            mock_chain.return_value = []  # Mock empty effects for simplicity
            with patch.object(self.converter, '_convert_filter_effects_to_drawingml') as mock_convert:
                mock_convert.return_value = "<complex_filter_output/>"
                
                result = self.converter.apply_filter_to_element(target_element, self.context)
                
                assert result == "<complex_filter_output/>"
                mock_chain.assert_called_once()
                mock_convert.assert_called_once()
    
    def test_filter_in_defs_processing(self):
        """Test processing filters within defs element."""
        defs_element = ET.Element("defs")
        
        # Add filter to defs
        filter1 = ET.SubElement(defs_element, "filter")
        filter1.set("id", "defsFilter1")
        blur1 = ET.SubElement(filter1, "feGaussianBlur")
        blur1.set("stdDeviation", "2")
        
        # Add another filter
        filter2 = ET.SubElement(defs_element, "filter")
        filter2.set("id", "defsFilter2")
        shadow = ET.SubElement(filter2, "feDropShadow")
        shadow.set("dx", "1")
        shadow.set("dy", "1")
        
        # Process defs
        result = self.converter._process_filter_definitions(defs_element, self.context)
        
        assert result == ""  # Definitions don't produce output
        assert "defsFilter1" in self.converter.filters
        assert "defsFilter2" in self.converter.filters
        assert len(self.converter.filters["defsFilter1"].primitives) == 1
        assert len(self.converter.filters["defsFilter2"].primitives) == 1
    
    def test_multiple_filters_same_element(self):
        """Test edge case with element referencing multiple filters."""
        # Create filter definitions
        simple_blur = GaussianBlurPrimitive(
            type=FilterPrimitiveType.GAUSSIAN_BLUR,
            input="SourceGraphic", result="blur1",
            x=0, y=0, width=1, height=1,
            std_deviation_x=2.0, std_deviation_y=2.0
        )
        
        filter_def = FilterDefinition(
            id="multiFilter", x=0, y=0, width=1, height=1,
            filter_units=FilterUnits.OBJECT_BOUNDING_BOX,
            primitive_units=FilterUnits.USER_SPACE_ON_USE,
            primitives=[simple_blur]
        )
        self.converter.filters["multiFilter"] = filter_def
        
        # Apply to element multiple times (simulating multiple references)
        element = ET.Element("circle")
        element.set("filter", "url(#multiFilter)")
        
        with patch.object(self.converter, '_process_filter_chain', return_value=[]):
            with patch.object(self.converter, '_convert_filter_effects_to_drawingml', return_value="output"):
                result1 = self.converter.apply_filter_to_element(element, self.context)
                result2 = self.converter.apply_filter_to_element(element, self.context)
                
                assert result1 == "output"
                assert result2 == "output"  # Should work consistently
    
    def test_filter_with_no_primitives(self):
        """Test filter definition with no primitives."""
        filter_element = ET.Element("filter")
        filter_element.set("id", "emptyFilter")
        # No child primitives
        
        self.converter._extract_filter_definition(filter_element)
        
        assert "emptyFilter" in self.converter.filters
        filter_def = self.converter.filters["emptyFilter"]
        assert len(filter_def.primitives) == 0
        
        # Apply empty filter
        element = ET.Element("rect")
        element.set("filter", "url(#emptyFilter)")
        
        with patch.object(self.converter, '_process_filter_chain', return_value=[]):
            with patch.object(self.converter, '_convert_filter_effects_to_drawingml', return_value="empty"):
                result = self.converter.apply_filter_to_element(element, self.context)
                assert result == "empty"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])