"""
Tests for Enhanced SVG Filter Converter

Tests the new filter primitives and enhancements including:
- Morphology effects (dilate/erode)
- Convolution matrix filters
- Lighting effects (diffuse/specular)
- Turbulence noise effects
- Complex filter chain processing
- Rasterization decision logic
"""

import pytest
from lxml import etree as ET
from unittest.mock import Mock, patch
from src.converters.filters import (
    FilterConverter, FilterPrimitiveType, 
    MorphologyPrimitive, ConvolvePrimitive, 
    LightingPrimitive, TurbulencePrimitive
)
from src.converters.base import ConversionContext


class TestEnhancedFilterPrimitives:
    """Test new filter primitive parsing"""

    def setup_method(self):
        """Set up test fixtures"""
        self.converter = FilterConverter()
        self.context = Mock(spec=ConversionContext)
        
        # Mock dependencies
        self.converter.color_parser = Mock()
        self.converter.color_parser.parse = Mock(return_value=Mock())

    def test_parse_morphology_primitive(self):
        """Test parsing of feMorphology primitive"""
        morph_xml = """
        <feMorphology operator="dilate" radius="2" in="SourceGraphic" result="dilated"/>
        """
        morph_element = ET.fromstring(morph_xml)
        
        from src.converters.filters import FilterUnits
        primitive = self.converter._parse_filter_primitive(morph_element, FilterUnits.USER_SPACE_ON_USE)
        
        assert isinstance(primitive, MorphologyPrimitive)
        assert primitive.type == FilterPrimitiveType.MORPH
        assert primitive.operator == "dilate"
        assert primitive.radius_x == 2.0
        assert primitive.radius_y == 2.0
        assert primitive.input == "SourceGraphic"
        assert primitive.result == "dilated"

    def test_parse_morphology_different_radii(self):
        """Test parsing morphology with different x,y radii"""
        morph_xml = """
        <feMorphology operator="erode" radius="3 1.5"/>
        """
        morph_element = ET.fromstring(morph_xml)
        
        from src.converters.filters import FilterUnits
        primitive = self.converter._parse_filter_primitive(morph_element, FilterUnits.USER_SPACE_ON_USE)
        
        assert primitive.operator == "erode"
        assert primitive.radius_x == 3.0
        assert primitive.radius_y == 1.5

    def test_parse_convolve_primitive(self):
        """Test parsing of feConvolveMatrix primitive"""
        convolve_xml = """
        <feConvolveMatrix order="3" kernelMatrix="0 -1 0 -1 5 -1 0 -1 0" 
                         divisor="1" bias="0" edgeMode="duplicate"/>
        """
        convolve_element = ET.fromstring(convolve_xml)
        
        from src.converters.filters import FilterUnits
        primitive = self.converter._parse_filter_primitive(convolve_element, FilterUnits.USER_SPACE_ON_USE)
        
        assert isinstance(primitive, ConvolvePrimitive)
        assert primitive.type == FilterPrimitiveType.CONVOLVE
        assert primitive.order_x == 3
        assert primitive.order_y == 3
        assert primitive.kernel_matrix == [0, -1, 0, -1, 5, -1, 0, -1, 0]
        assert primitive.divisor == 1.0
        assert primitive.bias == 0.0
        assert primitive.edge_mode == "duplicate"
        assert primitive.preserve_alpha is False

    def test_parse_convolve_different_orders(self):
        """Test parsing convolution with different x,y orders"""
        convolve_xml = """
        <feConvolveMatrix order="3 2" kernelMatrix="1 2 1 3 4 3" preserveAlpha="true"/>
        """
        convolve_element = ET.fromstring(convolve_xml)
        
        from src.converters.filters import FilterUnits
        primitive = self.converter._parse_filter_primitive(convolve_element, FilterUnits.USER_SPACE_ON_USE)
        
        assert primitive.order_x == 3
        assert primitive.order_y == 2
        assert primitive.preserve_alpha is True

    def test_parse_lighting_diffuse(self):
        """Test parsing of feDiffuseLighting primitive"""
        lighting_xml = """
        <feDiffuseLighting lighting-color="white" surfaceScale="2" diffuseConstant="1.5"/>
        """
        lighting_element = ET.fromstring(lighting_xml)
        
        from src.converters.filters import FilterUnits
        primitive = self.converter._parse_filter_primitive(lighting_element, FilterUnits.USER_SPACE_ON_USE)
        
        assert isinstance(primitive, LightingPrimitive)
        assert primitive.type == FilterPrimitiveType.LIGHTING
        assert primitive.lighting_type == "diffuse"
        assert primitive.surface_scale == 2.0
        assert primitive.diffuse_constant == 1.5
        self.converter.color_parser.parse.assert_called_with("white")

    def test_parse_lighting_specular(self):
        """Test parsing of feSpecularLighting primitive"""
        lighting_xml = """
        <feSpecularLighting lighting-color="#ff0000" specularConstant="2" specularExponent="3"/>
        """
        lighting_element = ET.fromstring(lighting_xml)
        
        from src.converters.filters import FilterUnits
        primitive = self.converter._parse_filter_primitive(lighting_element, FilterUnits.USER_SPACE_ON_USE)
        
        assert primitive.lighting_type == "specular"
        assert primitive.specular_constant == 2.0
        assert primitive.specular_exponent == 3.0

    def test_parse_turbulence_primitive(self):
        """Test parsing of feTurbulence primitive"""
        turbulence_xml = """
        <feTurbulence baseFrequency="0.1" numOctaves="4" seed="2" type="fractalNoise" stitchTiles="stitch"/>
        """
        turbulence_element = ET.fromstring(turbulence_xml)
        
        from src.converters.filters import FilterUnits
        primitive = self.converter._parse_filter_primitive(turbulence_element, FilterUnits.USER_SPACE_ON_USE)
        
        assert isinstance(primitive, TurbulencePrimitive)
        assert primitive.type == FilterPrimitiveType.TURBULENCE
        assert primitive.base_frequency_x == 0.1
        assert primitive.base_frequency_y == 0.1
        assert primitive.num_octaves == 4
        assert primitive.seed == 2
        assert primitive.stitch_tiles is True
        assert primitive.turbulence_type == "fractalNoise"

    def test_parse_turbulence_different_frequencies(self):
        """Test parsing turbulence with different x,y frequencies"""
        turbulence_xml = """
        <feTurbulence baseFrequency="0.1 0.05" type="turbulence"/>
        """
        turbulence_element = ET.fromstring(turbulence_xml)
        
        from src.converters.filters import FilterUnits
        primitive = self.converter._parse_filter_primitive(turbulence_element, FilterUnits.USER_SPACE_ON_USE)
        
        assert primitive.base_frequency_x == 0.1
        assert primitive.base_frequency_y == 0.05
        assert primitive.turbulence_type == "turbulence"


class TestComplexityCalculation:
    """Test filter complexity calculation with new primitives"""

    def setup_method(self):
        """Set up test fixtures"""
        self.converter = FilterConverter()

    def test_complexity_with_morphology(self):
        """Test complexity calculation including morphology"""
        from src.converters.filters import FilterDefinition, FilterUnits
        
        # Create filter with morphology primitive
        morph_primitive = MorphologyPrimitive(
            type=FilterPrimitiveType.MORPH,
            input="SourceGraphic", result="morphed",
            x=0, y=0, width=1, height=1,
            operator="dilate", radius_x=2, radius_y=2
        )
        
        filter_def = FilterDefinition(
            id="test-filter",
            x=0, y=0, width=1, height=1,
            filter_units=FilterUnits.OBJECT_BOUNDING_BOX,
            primitive_units=FilterUnits.USER_SPACE_ON_USE,
            primitives=[morph_primitive]
        )
        
        complexity = self.converter._calculate_filter_complexity(filter_def)
        
        # Base: 1 primitive * 0.5 = 0.5
        # Morphology: 1.8
        # Total: 2.3
        assert complexity == 2.3

    def test_complexity_with_convolution(self):
        """Test complexity calculation with convolution"""
        from src.converters.filters import FilterDefinition, FilterUnits
        
        convolve_primitive = ConvolvePrimitive(
            type=FilterPrimitiveType.CONVOLVE,
            input="SourceGraphic", result="convolved",
            x=0, y=0, width=1, height=1,
            order_x=3, order_y=3, kernel_matrix=[1]*9,
            divisor=1, bias=0, edge_mode="duplicate", preserve_alpha=False
        )
        
        filter_def = FilterDefinition(
            id="test-filter",
            x=0, y=0, width=1, height=1,
            filter_units=FilterUnits.OBJECT_BOUNDING_BOX,
            primitive_units=FilterUnits.USER_SPACE_ON_USE,
            primitives=[convolve_primitive]
        )
        
        complexity = self.converter._calculate_filter_complexity(filter_def)
        
        # Base: 0.5, Convolution: 2.0, Total: 2.5
        assert complexity == 2.5

    def test_complexity_with_turbulence(self):
        """Test complexity calculation with turbulence"""
        from src.converters.filters import FilterDefinition, FilterUnits
        
        turbulence_primitive = TurbulencePrimitive(
            type=FilterPrimitiveType.TURBULENCE,
            input="SourceGraphic", result="noise",
            x=0, y=0, width=1, height=1,
            base_frequency_x=0.1, base_frequency_y=0.1,
            num_octaves=4, seed=0, stitch_tiles=False, turbulence_type="turbulence"
        )
        
        filter_def = FilterDefinition(
            id="test-filter",
            x=0, y=0, width=1, height=1,
            filter_units=FilterUnits.OBJECT_BOUNDING_BOX,
            primitive_units=FilterUnits.USER_SPACE_ON_USE,
            primitives=[turbulence_primitive]
        )
        
        complexity = self.converter._calculate_filter_complexity(filter_def)
        
        # Base: 0.5, Turbulence: 3.0, Total: 3.5
        assert complexity == 3.5


class TestPrimitiveToEffectConversion:
    """Test conversion of new primitives to filter effects"""

    def setup_method(self):
        """Set up test fixtures"""
        self.converter = FilterConverter()

    def test_convert_morphology_to_effect(self):
        """Test conversion of morphology primitive to effect"""
        primitive = MorphologyPrimitive(
            type=FilterPrimitiveType.MORPH,
            input="SourceGraphic", result="morphed",
            x=0, y=0, width=1, height=1,
            operator="dilate", radius_x=3, radius_y=2
        )
        
        effect = self.converter._convert_primitive_to_effect(primitive, force_raster=False)
        
        assert effect is not None
        assert effect.effect_type == "morphology"
        assert effect.requires_rasterization is True
        assert effect.complexity_score == 1.8
        assert effect.parameters["operator"] == "dilate"
        assert effect.parameters["radius_x"] == 3
        assert effect.parameters["radius_y"] == 2

    def test_convert_convolve_to_effect(self):
        """Test conversion of convolution primitive to effect"""
        kernel = [0, -1, 0, -1, 5, -1, 0, -1, 0]
        primitive = ConvolvePrimitive(
            type=FilterPrimitiveType.CONVOLVE,
            input="SourceGraphic", result="convolved",
            x=0, y=0, width=1, height=1,
            order_x=3, order_y=3, kernel_matrix=kernel,
            divisor=1, bias=0, edge_mode="duplicate", preserve_alpha=False
        )
        
        effect = self.converter._convert_primitive_to_effect(primitive, force_raster=False)
        
        assert effect.effect_type == "convolve"
        assert effect.requires_rasterization is True
        assert effect.complexity_score == 2.5
        assert effect.parameters["kernel_matrix"] == kernel
        assert effect.parameters["order_x"] == 3
        assert effect.parameters["divisor"] == 1

    def test_convert_lighting_to_effect(self):
        """Test conversion of lighting primitive to effect"""
        mock_color = Mock()
        primitive = LightingPrimitive(
            type=FilterPrimitiveType.LIGHTING,
            input="SourceGraphic", result="lit",
            x=0, y=0, width=1, height=1,
            lighting_type="diffuse", lighting_color=mock_color,
            surface_scale=1.5, diffuse_constant=2.0,
            specular_constant=1.0, specular_exponent=1.0
        )
        
        effect = self.converter._convert_primitive_to_effect(primitive, force_raster=False)
        
        assert effect.effect_type == "lighting"
        assert effect.requires_rasterization is True
        assert effect.complexity_score == 2.2
        assert effect.parameters["lighting_type"] == "diffuse"
        assert effect.parameters["surface_scale"] == 1.5
        assert effect.parameters["diffuse_constant"] == 2.0

    def test_convert_turbulence_to_effect(self):
        """Test conversion of turbulence primitive to effect"""
        primitive = TurbulencePrimitive(
            type=FilterPrimitiveType.TURBULENCE,
            input="SourceGraphic", result="noise",
            x=0, y=0, width=1, height=1,
            base_frequency_x=0.1, base_frequency_y=0.05,
            num_octaves=3, seed=42, stitch_tiles=True, turbulence_type="fractalNoise"
        )
        
        effect = self.converter._convert_primitive_to_effect(primitive, force_raster=False)
        
        assert effect.effect_type == "turbulence"
        assert effect.requires_rasterization is True
        assert effect.complexity_score == 3.0
        assert effect.parameters["base_frequency_x"] == 0.1
        assert effect.parameters["base_frequency_y"] == 0.05
        assert effect.parameters["num_octaves"] == 3
        assert effect.parameters["seed"] == 42
        assert effect.parameters["turbulence_type"] == "fractalNoise"

    def test_force_rasterization(self):
        """Test that force_raster parameter works"""
        primitive = MorphologyPrimitive(
            type=FilterPrimitiveType.MORPH,
            input="SourceGraphic", result="morphed",
            x=0, y=0, width=1, height=1,
            operator="dilate", radius_x=1, radius_y=1
        )
        
        # Even though morphology normally requires rasterization,
        # the force_raster flag should still be respected in the logic
        effect = self.converter._convert_primitive_to_effect(primitive, force_raster=True)
        
        assert effect.requires_rasterization is True


class TestComplexFilterChains:
    """Test processing of complex filter chains with new primitives"""

    def setup_method(self):
        """Set up test fixtures"""
        self.converter = FilterConverter()
        self.context = Mock(spec=ConversionContext)

    def test_morphology_blur_chain(self):
        """Test chain with morphology and blur"""
        from src.converters.filters import FilterDefinition, FilterUnits, GaussianBlurPrimitive
        
        morph_primitive = MorphologyPrimitive(
            type=FilterPrimitiveType.MORPH,
            input="SourceGraphic", result="dilated",
            x=0, y=0, width=1, height=1,
            operator="dilate", radius_x=2, radius_y=2
        )
        
        blur_primitive = GaussianBlurPrimitive(
            type=FilterPrimitiveType.GAUSSIAN_BLUR,
            input="dilated", result="blurred",
            x=0, y=0, width=1, height=1,
            std_deviation_x=1, std_deviation_y=1
        )
        
        filter_def = FilterDefinition(
            id="complex-filter",
            x=0, y=0, width=1, height=1,
            filter_units=FilterUnits.OBJECT_BOUNDING_BOX,
            primitive_units=FilterUnits.USER_SPACE_ON_USE,
            primitives=[morph_primitive, blur_primitive]
        )
        
        # Mock element for processing
        element = Mock()
        
        effects = self.converter._process_filter_chain(filter_def, element, self.context)
        
        # Should generate multiple effects
        assert len(effects) >= 1
        
        # At least one should require rasterization due to morphology
        assert any(effect.requires_rasterization for effect in effects)

    def test_turbulence_composite_chain(self):
        """Test chain with turbulence and composite"""
        from src.converters.filters import FilterDefinition, FilterUnits, CompositePrimitive
        
        turbulence_primitive = TurbulencePrimitive(
            type=FilterPrimitiveType.TURBULENCE,
            input="SourceGraphic", result="noise",
            x=0, y=0, width=1, height=1,
            base_frequency_x=0.1, base_frequency_y=0.1,
            num_octaves=4, seed=0, stitch_tiles=False, turbulence_type="turbulence"
        )
        
        composite_primitive = CompositePrimitive(
            type=FilterPrimitiveType.COMPOSITE,
            input="SourceGraphic", input2="noise", result="final",
            x=0, y=0, width=1, height=1,
            operator="multiply", k1=0, k2=0, k3=0, k4=0
        )
        
        filter_def = FilterDefinition(
            id="texture-filter",
            x=0, y=0, width=1, height=1,
            filter_units=FilterUnits.OBJECT_BOUNDING_BOX,
            primitive_units=FilterUnits.USER_SPACE_ON_USE,
            primitives=[turbulence_primitive, composite_primitive]
        )
        
        element = Mock()
        effects = self.converter._process_filter_chain(filter_def, element, self.context)
        
        # Complex chain should require rasterization
        assert any(effect.requires_rasterization for effect in effects)
        
        # Should have high complexity
        complexity = self.converter._calculate_filter_complexity(filter_def)
        assert complexity > 3.0  # Very complex


class TestRasterizationDecisions:
    """Test rasterization decision logic"""

    def setup_method(self):
        """Set up test fixtures"""
        self.converter = FilterConverter()

    def test_simple_effects_no_rasterization(self):
        """Test that simple effects don't require rasterization"""
        from src.converters.filters import FilterDefinition, FilterUnits, GaussianBlurPrimitive
        
        blur_primitive = GaussianBlurPrimitive(
            type=FilterPrimitiveType.GAUSSIAN_BLUR,
            input="SourceGraphic", result="blurred",
            x=0, y=0, width=1, height=1,
            std_deviation_x=2, std_deviation_y=2
        )
        
        filter_def = FilterDefinition(
            id="simple-filter",
            x=0, y=0, width=1, height=1,
            filter_units=FilterUnits.OBJECT_BOUNDING_BOX,
            primitive_units=FilterUnits.USER_SPACE_ON_USE,
            primitives=[blur_primitive]
        )
        
        complexity = self.converter._calculate_filter_complexity(filter_def)
        assert complexity < self.converter.rasterization_threshold

    def test_complex_effects_require_rasterization(self):
        """Test that complex effects require rasterization"""
        from src.converters.filters import FilterDefinition, FilterUnits
        
        turbulence_primitive = TurbulencePrimitive(
            type=FilterPrimitiveType.TURBULENCE,
            input="SourceGraphic", result="noise",
            x=0, y=0, width=1, height=1,
            base_frequency_x=0.1, base_frequency_y=0.1,
            num_octaves=4, seed=0, stitch_tiles=False, turbulence_type="turbulence"
        )
        
        convolve_primitive = ConvolvePrimitive(
            type=FilterPrimitiveType.CONVOLVE,
            input="noise", result="convolved",
            x=0, y=0, width=1, height=1,
            order_x=5, order_y=5, kernel_matrix=[1]*25,
            divisor=1, bias=0, edge_mode="duplicate", preserve_alpha=False
        )
        
        filter_def = FilterDefinition(
            id="complex-filter",
            x=0, y=0, width=1, height=1,
            filter_units=FilterUnits.OBJECT_BOUNDING_BOX,
            primitive_units=FilterUnits.USER_SPACE_ON_USE,
            primitives=[turbulence_primitive, convolve_primitive]
        )
        
        complexity = self.converter._calculate_filter_complexity(filter_def)
        assert complexity > self.converter.rasterization_threshold