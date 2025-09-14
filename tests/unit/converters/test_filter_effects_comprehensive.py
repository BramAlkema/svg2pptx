#!/usr/bin/env python3
"""
Comprehensive Test Suite for SVG Filter Effects Pipeline

Tests SVG filter parsing, OOXML effect mapping, and effect chaining based on
the comprehensive filter effects mapping table. Covers all strategies:
- S1: Native DML effects
- S2: DML hacks and workarounds
- S3: Rasterization fallbacks

Test Categories:
1. Basic Filter Primitives (feGaussianBlur, feDropShadow, etc.)
2. Effect Chaining and Composite Operations
3. OOXML Effect Mapping Accuracy
4. Parameter Conversion Mathematics
5. Fallback Strategy Selection
6. Filter Bounds and Positioning
7. Performance and Optimization
"""

import pytest
import math
import xml.etree.ElementTree as ET
from pathlib import Path
import sys
from unittest.mock import Mock, patch

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from src.converters.filters import FilterConverter, FilterPrimitiveType, FilterPrimitive
from src.converters.base import ConversionContext
from src.colors import ColorParser
from src.units import UnitConverter
from src.transforms import TransformParser
from src.viewbox import ViewportResolver


@pytest.fixture
def filter_converter():
    """Create FilterConverter instance for testing."""
    return FilterConverter()


@pytest.fixture
def mock_context():
    """Create mock conversion context."""
    context = Mock(spec=ConversionContext)
    context.color_parser = ColorParser()
    context.unit_converter = Mock(spec=UnitConverter)
    context.transform_parser = Mock(spec=TransformParser)
    context.viewport_resolver = Mock(spec=ViewportResolver)
    context.dpi = 96
    return context


@pytest.mark.unit
class TestBasicFilterPrimitives:
    """Test basic SVG filter primitive parsing and conversion."""

    def test_fe_gaussian_blur_parsing(self, filter_converter, mock_context):
        """Test feGaussianBlur primitive parsing with stdDeviation parameter."""
        svg_content = '''
        <filter>
            <feGaussianBlur in="SourceGraphic" stdDeviation="3"/>
        </filter>
        '''
        filter_elem = ET.fromstring(svg_content)
        blur_elem = filter_elem.find('.//feGaussianBlur')

        result = filter_converter._parse_gaussian_blur(blur_elem, mock_context)

        assert result is not None
        assert result.primitive_type == FilterPrimitiveType.GAUSSIAN_BLUR
        assert result.std_deviation == 3.0
        assert result.input_source == "SourceGraphic"

    def test_fe_drop_shadow_parsing(self, filter_converter, mock_context):
        """Test feDropShadow primitive parsing with dx, dy, blur parameters."""
        svg_content = '''
        <filter>
            <feDropShadow dx="3" dy="3" stdDeviation="2" flood-color="black" flood-opacity="0.3"/>
        </filter>
        '''
        filter_elem = ET.fromstring(svg_content)
        shadow_elem = filter_elem.find('.//feDropShadow')

        result = filter_converter._parse_drop_shadow(shadow_elem, mock_context)

        assert result is not None
        assert result.primitive_type == FilterPrimitiveType.DROP_SHADOW
        assert result.dx == 3.0
        assert result.dy == 3.0
        assert result.std_deviation == 2.0
        assert result.flood_color.original == "black"
        assert result.flood_opacity == 0.3

    def test_fe_color_matrix_parsing(self, filter_converter, mock_context):
        """Test feColorMatrix primitive parsing with matrix values."""
        svg_content = '''
        <filter>
            <feColorMatrix type="matrix" values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 1 0"/>
        </filter>
        '''
        filter_elem = ET.fromstring(svg_content)
        matrix_elem = filter_elem.find('.//feColorMatrix')

        result = filter_converter._parse_color_matrix(matrix_elem, mock_context)

        assert result is not None
        assert result.primitive_type == FilterPrimitiveType.COLOR_MATRIX
        assert result.matrix_type == "matrix"
        assert len(result.values) == 20
        assert result.values[0] == 1.0  # Identity matrix first element

    def test_fe_offset_parsing(self, filter_converter, mock_context):
        """Test feOffset primitive parsing with dx, dy parameters."""
        svg_content = '''
        <filter>
            <feOffset in="SourceGraphic" dx="5" dy="-3"/>
        </filter>
        '''
        filter_elem = ET.fromstring(svg_content)
        offset_elem = filter_elem.find('.//feOffset')

        result = filter_converter._parse_offset(offset_elem, mock_context)

        assert result is not None
        assert result.primitive_type == FilterPrimitiveType.OFFSET
        assert result.dx == 5.0
        assert result.dy == -3.0
        assert result.input_source == "SourceGraphic"


@pytest.mark.unit
class TestOOXMLEffectMapping:
    """Test SVG to OOXML effect mapping based on the mapping table strategies."""

    def test_gaussian_blur_to_dml_blur_mapping(self, filter_converter, mock_context):
        """Test feGaussianBlur → a:effectLst/a:blur mapping with EMU conversion."""
        svg_content = '''
        <filter>
            <feGaussianBlur stdDeviation="4"/>
        </filter>
        '''
        filter_elem = ET.fromstring(svg_content)

        result = filter_converter.convert_to_ooxml(filter_elem, mock_context)

        assert 'a:effectLst' in result or 'a:blur' in result
        # Test parameter conversion: rad_emu ≈ stdDev_px * px_to_emu
        # where px_to_emu = 914400/96
        expected_emu = 4 * (914400 / 96)
        assert str(int(expected_emu)) in result

    def test_drop_shadow_to_dml_outer_shadow_mapping(self, filter_converter, mock_context):
        """Test feDropShadow → a:outerShdw mapping with distance and direction calculation."""
        svg_content = '''
        <filter>
            <feDropShadow dx="6" dy="8" stdDeviation="2" flood-color="#FF0000" flood-opacity="0.5"/>
        </filter>
        '''
        filter_elem = ET.fromstring(svg_content)

        result = filter_converter.convert_to_ooxml(filter_elem, mock_context)

        assert 'a:outerShdw' in result

        # Test parameter conversion: dx,dy → dist,dir
        # dist = √(dx²+dy²) in EMU; dir = atan2(dy,dx) in degrees
        dx, dy = 6.0, 8.0
        expected_dist = math.sqrt(dx**2 + dy**2) * (914400 / 96)
        expected_dir = math.degrees(math.atan2(dy, dx))

        assert str(int(expected_dist)) in result
        # Direction should be converted to 60000ths of a degree for OOXML
        expected_dir_ooxml = int(expected_dir * 60000)
        assert str(expected_dir_ooxml) in result or str(int(expected_dir)) in result

    def test_color_matrix_hue_rotate_to_dml_hue_mod(self, filter_converter, mock_context):
        """Test feColorMatrix hueRotate → a:hueMod mapping."""
        svg_content = '''
        <filter>
            <feColorMatrix type="hueRotate" values="45"/>
        </filter>
        '''
        filter_elem = ET.fromstring(svg_content)

        result = filter_converter.convert_to_ooxml(filter_elem, mock_context)

        # Test parameter conversion: hueMod = (deg/360)*100000
        degrees = 45.0
        expected_hue_mod = int((degrees / 360) * 100000)

        if 'hueMod' in result:
            assert str(expected_hue_mod) in result

    def test_color_matrix_saturate_to_dml_sat_mod(self, filter_converter, mock_context):
        """Test feColorMatrix saturate → a:satMod mapping."""
        svg_content = '''
        <filter>
            <feColorMatrix type="saturate" values="0.7"/>
        </filter>
        '''
        filter_elem = ET.fromstring(svg_content)

        result = filter_converter.convert_to_ooxml(filter_elem, mock_context)

        # Test parameter conversion: satMod = s*100000
        saturation = 0.7
        expected_sat_mod = int(saturation * 100000)

        if 'satMod' in result:
            assert str(expected_sat_mod) in result

    def test_morphology_dilate_fallback_strategy(self, filter_converter, mock_context):
        """Test feMorphology dilate → stroke outline boolean union fallback."""
        svg_content = '''
        <filter>
            <feMorphology operator="dilate" radius="2"/>
        </filter>
        '''
        filter_elem = ET.fromstring(svg_content)

        result = filter_converter.convert_to_ooxml(filter_elem, mock_context)

        # Should use fallback strategy S2: duplicate shape with stroke
        # stroke width = 2*radius in EMU
        radius = 2.0
        expected_stroke_width = 2 * radius * (914400 / 96)

        # Result should indicate stroke-based approach or fallback to rasterization
        assert 'stroke' in result.lower() or 'raster' in result.lower() or 'fallback' in result.lower()


@pytest.mark.unit
class TestEffectChaining:
    """Test complex filter effect chaining and composite operations."""

    def test_blur_plus_drop_shadow_chain(self, filter_converter, mock_context):
        """Test chaining feGaussianBlur + feDropShadow effects."""
        svg_content = '''
        <filter>
            <feGaussianBlur in="SourceGraphic" stdDeviation="2" result="blur"/>
            <feDropShadow in="blur" dx="3" dy="3" stdDeviation="1" flood-color="black"/>
        </filter>
        '''
        filter_elem = ET.fromstring(svg_content)

        result = filter_converter.convert_to_ooxml(filter_elem, mock_context)

        # Should contain both blur and shadow effects
        assert 'blur' in result.lower()
        assert ('shadow' in result.lower() or 'outerShdw' in result)

        # Verify chaining: blur result should feed into shadow input
        chain_result = filter_converter._build_effect_chain(filter_elem, mock_context)
        assert len(chain_result) >= 2
        assert chain_result[1].input_source == "blur"

    def test_offset_plus_composite_chain(self, filter_converter, mock_context):
        """Test feOffset + feComposite effect chaining."""
        svg_content = '''
        <filter>
            <feOffset in="SourceGraphic" dx="2" dy="2" result="offset"/>
            <feComposite in="SourceGraphic" in2="offset" operator="over"/>
        </filter>
        '''
        filter_elem = ET.fromstring(svg_content)

        chain_result = filter_converter._build_effect_chain(filter_elem, mock_context)

        assert len(chain_result) == 2
        assert chain_result[0].primitive_type == FilterPrimitiveType.OFFSET
        assert chain_result[1].primitive_type == FilterPrimitiveType.COMPOSITE
        assert chain_result[1].input_source == "SourceGraphic"
        assert chain_result[1].input_source2 == "offset"

    def test_complex_lighting_effect_chain(self, filter_converter, mock_context):
        """Test complex lighting effect with multiple primitives."""
        svg_content = '''
        <filter>
            <feGaussianBlur in="SourceAlpha" stdDeviation="3" result="blur"/>
            <feSpecularLighting in="blur" lighting-color="white" surfaceScale="1"
                              specularConstant="1" specularExponent="20" result="light">
                <feDistantLight azimuth="45" elevation="60"/>
            </feSpecularLighting>
            <feComposite in="light" in2="SourceGraphic" operator="multiply"/>
        </filter>
        '''
        filter_elem = ET.fromstring(svg_content)

        chain_result = filter_converter._build_effect_chain(filter_elem, mock_context)

        assert len(chain_result) >= 3
        # Should detect lighting effect and use appropriate fallback
        has_lighting = any(p.primitive_type == FilterPrimitiveType.LIGHTING for p in chain_result)
        assert has_lighting


@pytest.mark.unit
class TestParameterConversion:
    """Test mathematical parameter conversions between SVG and OOXML."""

    def test_pixel_to_emu_conversion(self, filter_converter):
        """Test pixel to EMU conversion accuracy."""
        # Standard conversion: 1 px = 914400/96 EMU at 96 DPI
        px_values = [1, 2.5, 10, 0.5]
        expected_emu = [v * (914400 / 96) for v in px_values]

        for px, expected in zip(px_values, expected_emu):
            result = filter_converter._px_to_emu(px, dpi=96)
            assert abs(result - expected) < 1  # Allow 1 EMU tolerance

    def test_distance_and_direction_calculation(self, filter_converter):
        """Test dx, dy → distance, direction conversion."""
        test_cases = [
            (3, 4, 5, 53.13),    # 3-4-5 triangle
            (0, 5, 5, 90),       # Vertical
            (5, 0, 5, 0),        # Horizontal
            (-3, -4, 5, -126.87) # Negative quadrant
        ]

        for dx, dy, expected_dist, expected_dir in test_cases:
            dist, dir_deg = filter_converter._calculate_distance_direction(dx, dy)
            assert abs(dist - expected_dist) < 0.1
            assert abs(dir_deg - expected_dir) < 0.1

    def test_color_matrix_parameter_mapping(self, filter_converter):
        """Test color matrix parameter conversions."""
        # Test hue rotation conversion
        hue_degrees = 45
        expected_hue_mod = (hue_degrees / 360) * 100000
        result = filter_converter._convert_hue_rotate_to_hue_mod(hue_degrees)
        assert abs(result - expected_hue_mod) < 1

        # Test saturation conversion
        saturation = 0.7
        expected_sat_mod = saturation * 100000
        result = filter_converter._convert_saturation_to_sat_mod(saturation)
        assert abs(result - expected_sat_mod) < 1

    def test_bevel_depth_conversion(self, filter_converter):
        """Test lighting surfaceScale → bevel depth conversion."""
        surface_scales = [0.5, 1.0, 2.0, 5.0]

        for scale in surface_scales:
            bevel_depth = filter_converter._convert_surface_scale_to_bevel(scale)
            # Bevel depth should be proportional to surface scale
            assert bevel_depth > 0
            assert bevel_depth == scale * filter_converter._default_bevel_multiplier


@pytest.mark.unit
class TestFilterBounds:
    """Test filter bounds calculation and positioning."""

    def test_gaussian_blur_bounds_expansion(self, filter_converter):
        """Test bounds expansion for Gaussian blur effects."""
        std_dev = 3.0
        bounds_expansion = filter_converter._calculate_blur_bounds_expansion(std_dev)

        # Blur typically expands bounds by ~3x standard deviation
        expected_expansion = std_dev * 3
        assert abs(bounds_expansion - expected_expansion) < 1

    def test_drop_shadow_bounds_calculation(self, filter_converter):
        """Test bounds calculation for drop shadow effects."""
        dx, dy, blur = 5, 3, 2
        bounds = filter_converter._calculate_shadow_bounds(dx, dy, blur)

        # Bounds should include offset plus blur expansion
        assert bounds['min_x'] <= -blur * 3
        assert bounds['max_x'] >= dx + blur * 3
        assert bounds['min_y'] <= -blur * 3
        assert bounds['max_y'] >= dy + blur * 3

    def test_morphology_bounds_calculation(self, filter_converter):
        """Test bounds calculation for morphology effects."""
        radius = 2
        bounds_dilate = filter_converter._calculate_morphology_bounds(radius, "dilate")
        bounds_erode = filter_converter._calculate_morphology_bounds(radius, "erode")

        # Dilate expands bounds, erode contracts them
        assert bounds_dilate['expansion'] == radius
        assert bounds_erode['expansion'] == -radius


@pytest.mark.unit
class TestFallbackStrategies:
    """Test fallback strategy selection and implementation."""

    def test_unsupported_filter_fallback_to_raster(self, filter_converter, mock_context):
        """Test fallback to rasterization for unsupported filters."""
        svg_content = '''
        <filter>
            <feTurbulence type="noise" baseFrequency="0.1"/>
            <feDisplacementMap in="SourceGraphic" in2="noise" scale="10"/>
        </filter>
        '''
        filter_elem = ET.fromstring(svg_content)

        result = filter_converter.convert_to_ooxml(filter_elem, mock_context)

        # Should detect unsupported combination and fallback to rasterization
        assert ('raster' in result.lower() or 'bake' in result.lower() or
                'pic' in result.lower() or 'blipFill' in result.lower())

    def test_complex_chain_fallback_selection(self, filter_converter, mock_context):
        """Test fallback strategy selection for complex filter chains."""
        svg_content = '''
        <filter>
            <feGaussianBlur stdDeviation="2"/>
            <feColorMatrix type="matrix" values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 1 0"/>
            <feConvolveMatrix order="3" kernelMatrix="0 -1 0 -1 5 -1 0 -1 0"/>
        </filter>
        '''
        filter_elem = ET.fromstring(svg_content)

        strategy = filter_converter._select_fallback_strategy(filter_elem, mock_context)

        # Should select appropriate strategy based on complexity
        assert strategy in ['native', 'hack', 'raster']

        # ConvolveMatrix should typically force rasterization
        has_convolve = any(child.tag.endswith('feConvolveMatrix') for child in filter_elem)
        if has_convolve:
            assert strategy == 'raster'

    def test_performance_based_fallback_threshold(self, filter_converter, mock_context):
        """Test performance-based fallback to rasterization."""
        # Create filter with many primitives (should trigger performance fallback)
        primitives = [
            '<feGaussianBlur stdDeviation="1"/>',
            '<feOffset dx="1" dy="1"/>',
            '<feGaussianBlur stdDeviation="2"/>',
            '<feOffset dx="2" dy="2"/>',
            '<feGaussianBlur stdDeviation="3"/>',
            '<feOffset dx="3" dy="3"/>'
        ]

        svg_content = f'<filter>{"".join(primitives)}</filter>'
        filter_elem = ET.fromstring(svg_content)

        strategy = filter_converter._select_fallback_strategy(filter_elem, mock_context)

        # Many primitives should trigger performance-based rasterization
        primitive_count = len(list(filter_elem))
        if primitive_count > filter_converter._performance_threshold:
            assert strategy == 'raster'


@pytest.mark.unit
class TestFilterIntegration:
    """Test integration with shape and text rendering systems."""

    def test_filter_application_to_shape_element(self, filter_converter, mock_context):
        """Test applying filters to SVG shape elements."""
        svg_content = '''
        <g>
            <defs>
                <filter id="shadow">
                    <feDropShadow dx="2" dy="2" stdDeviation="1"/>
                </filter>
            </defs>
            <rect x="10" y="10" width="50" height="30" fill="blue" filter="url(#shadow)"/>
        </g>
        '''
        root = ET.fromstring(svg_content)
        rect = root.find('.//rect')
        filter_ref = rect.get('filter')

        assert filter_ref == "url(#shadow)"

        # Test filter ID extraction
        filter_id = filter_converter._extract_filter_id(filter_ref)
        assert filter_id == "shadow"

        # Test filter lookup and application
        filter_elem = root.find(f'.//filter[@id="{filter_id}"]')
        assert filter_elem is not None

        result = filter_converter.apply_filter_to_element(rect, filter_elem, mock_context)
        assert result is not None

    def test_multiple_filter_references(self, filter_converter, mock_context):
        """Test handling multiple filter references in document."""
        svg_content = '''
        <g>
            <defs>
                <filter id="blur"><feGaussianBlur stdDeviation="2"/></filter>
                <filter id="shadow"><feDropShadow dx="3" dy="3"/></filter>
            </defs>
            <rect filter="url(#blur)"/>
            <circle filter="url(#shadow)"/>
        </g>
        '''
        root = ET.fromstring(svg_content)

        # Test filter registry/cache
        filter_cache = filter_converter._build_filter_cache(root)

        assert 'blur' in filter_cache
        assert 'shadow' in filter_cache
        assert len(filter_cache) == 2

    def test_nested_group_filter_inheritance(self, filter_converter, mock_context):
        """Test filter inheritance in nested group structures."""
        svg_content = '''
        <g filter="url(#groupBlur)">
            <defs>
                <filter id="groupBlur"><feGaussianBlur stdDeviation="1"/></filter>
            </defs>
            <g>
                <rect fill="red"/>
                <circle fill="green"/>
            </g>
        </g>
        '''
        root = ET.fromstring(svg_content)

        # Test filter inheritance resolution
        inheritance_map = filter_converter._resolve_filter_inheritance(root, mock_context)

        # All child elements should inherit the group filter
        rect = root.find('.//rect')
        circle = root.find('.//circle')

        assert filter_converter._get_effective_filter(rect, inheritance_map) == "url(#groupBlur)"
        assert filter_converter._get_effective_filter(circle, inheritance_map) == "url(#groupBlur)"


@pytest.mark.unit
class TestFilterChainProcessing:
    """Test filter effect chaining system."""

    @pytest.fixture
    def chain_processor(self):
        """Create FilterChainProcessor instance."""
        from src.converters.filters import FilterChainProcessor
        return FilterChainProcessor()

    @pytest.fixture
    def mock_filter_definition(self):
        """Create mock filter definition with chained primitives."""
        from src.converters.filters import (
            FilterDefinition, FilterUnits, OffsetPrimitive,
            GaussianBlurPrimitive, CompositePrimitive, FilterPrimitiveType
        )

        # Create chain: offset -> blur -> composite (drop shadow pattern)
        offset_primitive = OffsetPrimitive(
            type=FilterPrimitiveType.OFFSET,
            input='SourceGraphic',
            result='offset',
            x=0, y=0, width=100, height=100,
            dx=3, dy=3
        )

        blur_primitive = GaussianBlurPrimitive(
            type=FilterPrimitiveType.GAUSSIAN_BLUR,
            input='offset',
            result='blur',
            x=0, y=0, width=100, height=100,
            std_deviation_x=2, std_deviation_y=2
        )

        composite_primitive = CompositePrimitive(
            type=FilterPrimitiveType.COMPOSITE,
            input='blur',
            input2='SourceGraphic',
            result='composite',
            x=0, y=0, width=100, height=100,
            operator='over'
        )

        return FilterDefinition(
            id='chain-test',
            x=0, y=0, width=100, height=100,
            filter_units=FilterUnits.USER_SPACE_ON_USE,
            primitive_units=FilterUnits.USER_SPACE_ON_USE,
            primitives=[offset_primitive, blur_primitive, composite_primitive]
        )

    def test_dependency_graph_building(self, mock_filter_definition):
        """Test filter dependency graph construction."""
        dependencies = mock_filter_definition.build_dependency_graph()

        assert 'offset' in dependencies
        assert 'blur' in dependencies
        assert 'composite' in dependencies

        # Check dependency relationships
        assert dependencies['offset'] == []  # offset depends on SourceGraphic (not in graph)
        assert 'offset' in dependencies['blur']  # blur depends on offset
        assert 'blur' in dependencies['composite']  # composite depends on blur
        assert 'SourceGraphic' in dependencies['composite']  # composite also depends on SourceGraphic

    def test_execution_order_resolution(self, mock_filter_definition):
        """Test filter execution order resolution."""
        execution_order = mock_filter_definition.get_execution_order()

        assert len(execution_order) == 3

        # Should execute in dependency order: offset -> blur -> composite
        primitive_types = [p.type for p in execution_order]
        assert FilterPrimitiveType.OFFSET in primitive_types
        assert FilterPrimitiveType.GAUSSIAN_BLUR in primitive_types
        assert FilterPrimitiveType.COMPOSITE in primitive_types

    def test_chain_processing(self, chain_processor, mock_filter_definition):
        """Test filter chain processing."""
        processed_nodes = chain_processor.process_filter_chain(mock_filter_definition)

        assert len(processed_nodes) == 3
        assert all(node.processed for node in processed_nodes)

        # Check intermediate results tracking
        assert 'SourceGraphic' in chain_processor.intermediate_results
        assert 'offset' in chain_processor.intermediate_results
        assert 'blur' in chain_processor.intermediate_results
        assert 'composite' in chain_processor.intermediate_results

    def test_drop_shadow_pattern_detection(self, chain_processor, mock_filter_definition):
        """Test detection of drop shadow filter pattern."""
        chain_processor.process_filter_chain(mock_filter_definition)
        patterns = chain_processor.detect_pattern_chains()

        assert len(patterns) >= 1
        shadow_pattern = next((p for p in patterns if p['pattern_type'] == 'drop_shadow'), None)
        assert shadow_pattern is not None
        assert shadow_pattern['can_optimize'] == True
        assert shadow_pattern['ooxml_equivalent'] == 'outerShdw'
        assert len(shadow_pattern['nodes']) == 3


@pytest.mark.unit
class TestOOXMLEffectMapper:
    """Test OOXML effect mapping with fallback strategies."""

    @pytest.fixture
    def ooxml_mapper(self):
        """Create OOXML effect mapper instance."""
        from src.converters.filters import OOXMLEffectMapper
        from src.units import UnitConverter
        from src.colors import ColorParser

        unit_converter = UnitConverter(100, 100)
        color_parser = ColorParser()
        return OOXMLEffectMapper(unit_converter, color_parser)

    @pytest.fixture
    def blur_effect(self):
        """Create sample blur filter effect."""
        from src.converters.filters import FilterEffect
        return FilterEffect(
            effect_type='blur',
            parameters={'radius': 5.0},
            requires_rasterization=False,
            complexity_score=1.0
        )

    @pytest.fixture
    def shadow_effect(self):
        """Create sample shadow filter effect."""
        from src.converters.filters import FilterEffect
        from src.colors import ColorInfo
        return FilterEffect(
            effect_type='shadow',
            parameters={
                'dx': 3, 'dy': 3, 'blur': 2,
                'color': ColorInfo(0, 0, 0, 0.5, 'rgb', 'black'),
                'opacity': 0.5
            },
            requires_rasterization=False,
            complexity_score=1.5
        )

    @pytest.fixture
    def complex_effect(self):
        """Create complex effect requiring rasterization."""
        from src.converters.filters import FilterEffect
        return FilterEffect(
            effect_type='turbulence',
            parameters={'base_frequency': 0.1, 'octaves': 3},
            requires_rasterization=True,
            complexity_score=3.0
        )

    def test_native_blur_mapping(self, ooxml_mapper, blur_effect):
        """Test native blur effect mapping to DML."""
        dml_xml, strategy = ooxml_mapper.map_filter_effect(blur_effect)

        assert strategy.value == 'native'
        assert '<a:blur rad=' in dml_xml
        assert 'rad="127000"' in dml_xml  # 5px converted to EMU

    def test_native_shadow_mapping(self, ooxml_mapper, shadow_effect):
        """Test native shadow effect mapping to DML."""
        dml_xml, strategy = ooxml_mapper.map_filter_effect(shadow_effect)

        assert strategy.value == 'native'
        assert '<a:outerShdw' in dml_xml
        assert 'dist=' in dml_xml
        assert 'dir=' in dml_xml
        assert 'blurRad=' in dml_xml
        assert '<a:srgbClr val="000000">' in dml_xml
        assert '<a:alpha val="50000"/>' in dml_xml

    def test_strategy_determination(self, ooxml_mapper):
        """Test strategy determination for different effect types."""
        from src.converters.filters import FilterEffect, OOXMLEffectStrategy

        # Native DML strategy
        blur_effect = FilterEffect('blur', {}, False, 1.0)
        strategy = ooxml_mapper._determine_strategy(blur_effect)
        assert strategy == OOXMLEffectStrategy.NATIVE_DML

        # DML hack strategy
        color_effect = FilterEffect('color_matrix', {}, False, 2.0)
        strategy = ooxml_mapper._determine_strategy(color_effect)
        assert strategy == OOXMLEffectStrategy.DML_HACK

        # Rasterization strategy (high complexity)
        complex_effect = FilterEffect('blur', {}, False, 3.0)
        strategy = ooxml_mapper._determine_strategy(complex_effect)
        assert strategy == OOXMLEffectStrategy.RASTERIZE

        # Rasterization strategy (explicitly required)
        raster_effect = FilterEffect('blur', {}, True, 1.0)
        strategy = ooxml_mapper._determine_strategy(raster_effect)
        assert strategy == OOXMLEffectStrategy.RASTERIZE

    def test_color_matrix_hack_mapping(self, ooxml_mapper):
        """Test color matrix approximation using DML hacks."""
        from src.converters.filters import FilterEffect

        # Saturation adjustment
        sat_effect = FilterEffect(
            'color_matrix',
            {'matrix_type': 'saturate', 'values': [0.5]},
            False, 1.5
        )
        dml_xml, strategy = ooxml_mapper.map_filter_effect(sat_effect)
        assert strategy.value == 'hack'
        assert '<a:satMod val="50000"/>' in dml_xml

        # Hue rotation
        hue_effect = FilterEffect(
            'color_matrix',
            {'matrix_type': 'hueRotate', 'values': [90]},
            False, 1.5
        )
        dml_xml, strategy = ooxml_mapper.map_filter_effect(hue_effect)
        assert '<a:hue val="5400000"/>' in dml_xml  # 90 degrees * 60000

    def test_lighting_hack_mapping(self, ooxml_mapper):
        """Test lighting effect approximation using 3D effects."""
        from src.converters.filters import FilterEffect

        # Diffuse lighting
        diffuse_effect = FilterEffect(
            'lighting',
            {'lighting_type': 'diffuse'},
            False, 2.0
        )
        dml_xml, strategy = ooxml_mapper.map_filter_effect(diffuse_effect)
        assert strategy.value == 'hack'
        assert '<a:sp3d>' in dml_xml
        assert '<a:bevelT' in dml_xml
        assert '<a:innerShdw' in dml_xml

        # Specular lighting
        specular_effect = FilterEffect(
            'lighting',
            {'lighting_type': 'specular'},
            False, 2.0
        )
        dml_xml, strategy = ooxml_mapper.map_filter_effect(specular_effect)
        assert '<a:outerShdw' in dml_xml
        assert 'val="FFFFFF"' in dml_xml  # White highlight

    def test_rasterization_fallback(self, ooxml_mapper, complex_effect):
        """Test rasterization fallback for complex effects."""
        dml_xml, strategy = ooxml_mapper.map_filter_effect(complex_effect)

        assert strategy.value == 'raster'
        assert 'requires rasterization' in dml_xml
        assert 'complexity: 3.0' in dml_xml

    def test_effect_list_generation(self, ooxml_mapper, blur_effect, shadow_effect, complex_effect):
        """Test generation of complete effect list with statistics."""
        effects = [blur_effect, shadow_effect, complex_effect]
        effect_list = ooxml_mapper.generate_effect_list(effects)

        # Should contain statistics comment
        assert 'Filter mapping:' in effect_list
        assert '2 native' in effect_list  # blur and shadow
        assert '0 hacks' in effect_list
        assert '1 raster' in effect_list  # complex effect

        # Should contain effect list wrapper
        assert '<a:effectLst>' in effect_list
        assert '</a:effectLst>' in effect_list

        # Should contain actual effects
        assert '<a:blur' in effect_list
        assert '<a:outerShdw' in effect_list

    def test_empty_effect_list(self, ooxml_mapper):
        """Test handling of empty effect list."""
        effect_list = ooxml_mapper.generate_effect_list([])
        assert effect_list == ""

    def test_glow_effect_mapping(self, ooxml_mapper):
        """Test glow effect mapping to native DML."""
        from src.converters.filters import FilterEffect
        from src.colors import ColorInfo

        glow_effect = FilterEffect(
            'glow',
            {
                'blur': 8,
                'color': ColorInfo(255, 255, 255, 0.8, 'rgb', 'white'),
                'opacity': 0.8
            },
            False, 1.2
        )

        dml_xml, strategy = ooxml_mapper.map_filter_effect(glow_effect)
        assert strategy.value == 'native'
        assert '<a:glow rad=' in dml_xml
        assert 'val="FFFFFF"' in dml_xml
        assert '<a:alpha val="80000"/>' in dml_xml


if __name__ == '__main__':
    pytest.main([__file__, '-v'])