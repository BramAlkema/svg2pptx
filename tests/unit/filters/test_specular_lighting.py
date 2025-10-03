#!/usr/bin/env python3
"""
Unit tests for SpecularLightingProcessor.

This test suite focuses on testing the SVG feSpecularLighting filter processor,
including 3D specular lighting effects using PowerPoint sp3d, bevel, lightRig, and outerShdw features.
"""

import pytest
from unittest.mock import Mock, patch
from lxml import etree as ET
import math

from core.filters import (
    SpecularLightingProcessor,
    SpecularLightingParameters,
    SpecularLightingException,
    SpecularLightingValidationError,
    FilterContext,
    FilterResult,
    FilterStrategy,
    create_specular_lighting_processor
)


class TestSpecularLightingParameters:
    """Test SpecularLightingParameters class."""

    def test_default_initialization(self):
        """Test default parameter initialization."""
        params = SpecularLightingParameters()

        assert params.surface_scale == 1.0
        assert params.specular_constant == 1.0
        assert params.specular_exponent == 1.0
        assert params.lighting_color == "white"
        assert params.light_source_type == "distant"
        assert params.light_azimuth == 0.0
        assert params.light_elevation == 0.0
        assert params.input_source == "SourceGraphic"
        assert params.result_name is None

    def test_custom_initialization(self):
        """Test custom parameter initialization."""
        params = SpecularLightingParameters(
            surface_scale=3.0,
            specular_constant=2.0,
            specular_exponent=64.0,
            lighting_color="#FF6600",
            light_source_type="point",
            light_x=100.0,
            light_y=50.0,
            light_z=75.0,
            input_source="blur1",
            result_name="specular_light"
        )

        assert params.surface_scale == 3.0
        assert params.specular_constant == 2.0
        assert params.specular_exponent == 64.0
        assert params.lighting_color == "#FF6600"
        assert params.light_source_type == "point"
        assert params.light_x == 100.0
        assert params.light_y == 50.0
        assert params.light_z == 75.0
        assert params.input_source == "blur1"
        assert params.result_name == "specular_light"

    def test_post_init_validation(self):
        """Test parameter validation in __post_init__."""
        # Test surface scale clamping
        params = SpecularLightingParameters(surface_scale=100.0)
        assert params.surface_scale == 50.0  # Clamped to max

        params = SpecularLightingParameters(surface_scale=-100.0)
        assert params.surface_scale == -50.0  # Clamped to min

        # Test specular constant clamping
        params = SpecularLightingParameters(specular_constant=20.0)
        assert params.specular_constant == 10.0  # Clamped to max

        # Test specular exponent clamping
        params = SpecularLightingParameters(specular_exponent=200.0)
        assert params.specular_exponent == 128.0  # Clamped to max

        # Test angle normalization
        params = SpecularLightingParameters(light_azimuth=450.0)
        assert params.light_azimuth == 90.0  # 450 % 360

        params = SpecularLightingParameters(light_elevation=100.0)
        assert params.light_elevation == 90.0  # Clamped to max

        # Test invalid light source type
        params = SpecularLightingParameters(light_source_type="invalid")
        assert params.light_source_type == "distant"  # Default

    def test_complexity_score_calculation(self):
        """Test complexity score calculation."""
        # Simple case
        simple_params = SpecularLightingParameters(
            surface_scale=1.0,
            specular_constant=1.0,
            specular_exponent=4.0,
            lighting_color="white",
            light_source_type="distant"
        )
        simple_score = simple_params.get_complexity_score()
        assert simple_score < 2.0

        # Complex case
        complex_params = SpecularLightingParameters(
            surface_scale=20.0,
            specular_constant=5.0,
            specular_exponent=128.0,
            lighting_color="#FF6600",
            light_source_type="spot",
            cone_angle=15.0
        )
        complex_score = complex_params.get_complexity_score()
        assert complex_score > simple_score

    def test_is_effective(self):
        """Test is_effective method."""
        # Effective lighting
        effective_params = SpecularLightingParameters(
            surface_scale=2.0,
            specular_constant=1.0,
            specular_exponent=16.0
        )
        assert effective_params.is_effective()

        # Ineffective lighting
        ineffective_params = SpecularLightingParameters(
            surface_scale=0.0,
            specular_constant=0.0,
            specular_exponent=0.0
        )
        assert not ineffective_params.is_effective()

    def test_get_light_direction_vector_distant(self):
        """Test light direction vector calculation for distant light."""
        params = SpecularLightingParameters(
            light_source_type="distant",
            light_azimuth=0.0,
            light_elevation=90.0  # Directly from above
        )

        x, y, z = params.get_light_direction_vector()

        # Should be pointing straight up
        assert abs(x) < 1e-6
        assert abs(y) < 1e-6
        assert abs(z - 1.0) < 1e-6

    def test_get_light_direction_vector_point(self):
        """Test light direction vector calculation for point light."""
        params = SpecularLightingParameters(
            light_source_type="point",
            light_x=100.0,
            light_y=0.0,
            light_z=0.0
        )

        x, y, z = params.get_light_direction_vector()

        # Should be normalized to unit vector
        length = math.sqrt(x**2 + y**2 + z**2)
        assert abs(length - 1.0) < 1e-6
        assert abs(x - 1.0) < 1e-6
        assert abs(y) < 1e-6
        assert abs(z) < 1e-6

    def test_get_light_direction_vector_spot(self):
        """Test light direction vector calculation for spot light."""
        params = SpecularLightingParameters(
            light_source_type="spot",
            light_x=0.0,
            light_y=0.0,
            light_z=100.0,
            light_points_at_x=0.0,
            light_points_at_y=0.0,
            light_points_at_z=0.0
        )

        x, y, z = params.get_light_direction_vector()

        # Should point from light to target (downward)
        assert abs(x) < 1e-6
        assert abs(y) < 1e-6
        assert abs(z + 1.0) < 1e-6  # Pointing down

    def test_get_shininess_material(self):
        """Test shininess to material mapping."""
        # Test various shininess levels
        params = SpecularLightingParameters(specular_exponent=0.5)
        assert params.get_shininess_material() == "flat"

        params = SpecularLightingParameters(specular_exponent=2.0)
        assert params.get_shininess_material() == "matte"

        params = SpecularLightingParameters(specular_exponent=8.0)
        assert params.get_shininess_material() == "plastic"

        params = SpecularLightingParameters(specular_exponent=24.0)
        assert params.get_shininess_material() == "softEdge"

        params = SpecularLightingParameters(specular_exponent=48.0)
        assert params.get_shininess_material() == "metal"

        params = SpecularLightingParameters(specular_exponent=96.0)
        assert params.get_shininess_material() == "warmMatte"

        params = SpecularLightingParameters(specular_exponent=128.0)  # Max value
        assert params.get_shininess_material() == "clear"


class TestSpecularLightingProcessor:
    """Test SpecularLightingProcessor class."""

    def setup_method(self):
        """Setup test fixtures."""
        self.processor = SpecularLightingProcessor()

        # Setup mock context
        self.mock_context = Mock(spec=FilterContext)
        self.mock_context.unit_converter = Mock()
        self.mock_context.unit_converter.to_emu.side_effect = lambda val: float(val.replace('px', '')) * 25400
        self.mock_context.color_parser = Mock()
        self.mock_context.color_parser.parse.return_value = "#FFFFFF"

    def test_initialization(self):
        """Test processor initialization."""
        processor = SpecularLightingProcessor()
        assert processor.filter_type == 'feSpecularLighting'
        assert processor.max_surface_scale == 20.0
        assert processor.max_extrusion_emu == 1270000

    def test_factory_function(self):
        """Test factory function."""
        processor = create_specular_lighting_processor()
        assert isinstance(processor, SpecularLightingProcessor)
        assert processor.filter_type == 'feSpecularLighting'

    def test_can_apply_valid_element(self):
        """Test can_apply with valid feSpecularLighting element."""
        element = ET.fromstring("""
            <feSpecularLighting surfaceScale="2.0" specularConstant="1.0" specularExponent="32.0">
                <feDistantLight azimuth="45" elevation="60"/>
            </feSpecularLighting>
        """)

        assert self.processor.can_apply(element, self.mock_context)

    def test_can_apply_invalid_element(self):
        """Test can_apply with invalid element."""
        # Wrong element type
        element = ET.fromstring('<feGaussianBlur stdDeviation="2"/>')
        assert not self.processor.can_apply(element, self.mock_context)

        # None element
        assert not self.processor.can_apply(None, self.mock_context)

    def test_parse_distant_light_parameters(self):
        """Test parsing distant light parameters."""
        element = ET.fromstring("""
            <feSpecularLighting surfaceScale="3.0" specularConstant="2.0" specularExponent="64.0" lighting-color="#FF6600">
                <feDistantLight azimuth="45" elevation="60"/>
            </feSpecularLighting>
        """)

        params = self.processor._parse_specular_lighting_parameters(element)

        assert params.surface_scale == 3.0
        assert params.specular_constant == 2.0
        assert params.specular_exponent == 64.0
        assert params.lighting_color == "#FF6600"
        assert params.light_source_type == "distant"
        assert params.light_azimuth == 45.0
        assert params.light_elevation == 60.0

    def test_parse_point_light_parameters(self):
        """Test parsing point light parameters."""
        element = ET.fromstring("""
            <feSpecularLighting surfaceScale="2.0" specularConstant="1.5" specularExponent="32.0">
                <fePointLight x="100" y="50" z="75"/>
            </feSpecularLighting>
        """)

        params = self.processor._parse_specular_lighting_parameters(element)

        assert params.light_source_type == "point"
        assert params.light_x == 100.0
        assert params.light_y == 50.0
        assert params.light_z == 75.0

    def test_parse_spot_light_parameters(self):
        """Test parsing spot light parameters."""
        element = ET.fromstring("""
            <feSpecularLighting surfaceScale="1.5" specularConstant="1.0" specularExponent="16.0">
                <feSpotLight x="100" y="100" z="100" pointsAtX="200" pointsAtY="200" pointsAtZ="0"
                           limitingConeAngle="30" specularExponent="2"/>
            </feSpecularLighting>
        """)

        params = self.processor._parse_specular_lighting_parameters(element)

        assert params.light_source_type == "spot"
        assert params.light_x == 100.0
        assert params.light_y == 100.0
        assert params.light_z == 100.0
        assert params.light_points_at_x == 200.0
        assert params.light_points_at_y == 200.0
        assert params.light_points_at_z == 0.0
        assert params.cone_angle == 30.0
        assert params.spot_exponent == 2.0

    def test_can_use_native_3d(self):
        """Test native 3D capability checking."""
        # Simple case that can use native
        simple_params = SpecularLightingParameters(
            surface_scale=2.0,
            specular_constant=1.0,
            specular_exponent=32.0
        )
        assert self.processor._can_use_native_3d(simple_params)

        # Complex case that cannot use native
        complex_params = SpecularLightingParameters(
            surface_scale=30.0,  # Too high
            specular_constant=8.0,  # Too intense
            specular_exponent=200.0  # Too high (will be clamped)
        )
        assert not self.processor._can_use_native_3d(complex_params)

        # Ineffective case
        ineffective_params = SpecularLightingParameters(
            surface_scale=0.0,
            specular_constant=0.0,
            specular_exponent=0.0
        )
        assert self.processor._can_use_native_3d(ineffective_params)  # No-op case

    def test_apply_native_strategy_success(self):
        """Test successful native strategy application."""
        element = ET.fromstring("""
            <feSpecularLighting surfaceScale="2.0" specularConstant="1.0" specularExponent="32.0">
                <feDistantLight azimuth="45" elevation="60"/>
            </feSpecularLighting>
        """)

        result = self.processor.apply(element, self.mock_context)

        assert result.success
        assert result.strategy == FilterStrategy.NATIVE
        assert "a:sp3d" in result.drawingml
        assert "a:bevel" in result.drawingml
        assert "a:lightRig" in result.drawingml
        assert "a:outerShdw" in result.drawingml

    def test_apply_ineffective_lighting(self):
        """Test applying ineffective lighting parameters."""
        element = ET.fromstring("""
            <feSpecularLighting surfaceScale="0.0" specularConstant="0.0" specularExponent="0.0">
                <feDistantLight azimuth="0" elevation="0"/>
            </feSpecularLighting>
        """)

        result = self.processor.apply(element, self.mock_context)

        assert result.success
        assert result.strategy == FilterStrategy.NATIVE
        assert "No visible specular lighting effect" in result.drawingml

    def test_generate_sp3d_configuration(self):
        """Test a:sp3d configuration generation."""
        params = SpecularLightingParameters(
            surface_scale=2.0,
            specular_constant=1.5,
            specular_exponent=64.0
        )

        drawingml = self.processor._generate_sp3d_configuration(params, self.mock_context)

        assert "a:sp3d" in drawingml
        assert "extrusionH=" in drawingml
        assert "contourW=" in drawingml
        assert "prstMaterial=" in drawingml
        assert "metal" in drawingml  # Expected material for exponent=64

    def test_generate_bevel_effects(self):
        """Test a:bevel effects generation."""
        params = SpecularLightingParameters(
            surface_scale=2.0,
            specular_constant=1.0,
            specular_exponent=32.0,
            light_source_type="distant",
            light_azimuth=45.0,
            light_elevation=30.0
        )

        drawingml = self.processor._generate_bevel_effects(params, self.mock_context)

        assert "a:bevel" in drawingml
        assert "bevelT" in drawingml or "bevelB" in drawingml
        assert "w=" in drawingml
        assert "h=" in drawingml

    def test_generate_lightrig_positioning(self):
        """Test a:lightRig positioning generation."""
        params = SpecularLightingParameters(
            surface_scale=2.0,
            specular_constant=1.0,
            specular_exponent=32.0,
            light_source_type="distant",
            light_azimuth=45.0,
            light_elevation=60.0
        )

        drawingml = self.processor._generate_lightrig_positioning(params, self.mock_context)

        assert "a:lightRig" in drawingml
        assert "rig=" in drawingml
        assert "dir=" in drawingml
        assert "azimuth 45.0, elevation 60.0" in drawingml

    def test_generate_specular_highlights(self):
        """Test specular highlight generation."""
        params = SpecularLightingParameters(
            surface_scale=2.0,
            specular_constant=1.0,
            specular_exponent=64.0,
            light_source_type="distant",
            light_azimuth=45.0,
            light_elevation=60.0
        )

        drawingml = self.processor._generate_specular_highlights(params, self.mock_context)

        assert "a:outerShdw" in drawingml
        assert "blurRad=" in drawingml
        assert "dist=" in drawingml
        assert "dir=" in drawingml
        assert "a:alpha" in drawingml

    def test_color_conversion(self):
        """Test color conversion to hex format."""
        # Named colors
        assert self.processor._convert_color_to_hex("white") == "FFFFFF"
        assert self.processor._convert_color_to_hex("black") == "000000"
        assert self.processor._convert_color_to_hex("red") == "FF0000"

        # Hex colors
        assert self.processor._convert_color_to_hex("#FF6600") == "FF6600"
        assert self.processor._convert_color_to_hex("#F60") == "FF6600"  # 3-digit to 6-digit

        # Unknown colors default to white
        assert self.processor._convert_color_to_hex("unknown") == "FFFFFF"

    def test_apply_approximation_strategy(self):
        """Test approximation strategy for complex lighting."""
        # Mock to force approximation strategy
        with patch.object(self.processor, '_get_strategy', return_value=FilterStrategy.APPROXIMATION):
            element = ET.fromstring("""
                <feSpecularLighting surfaceScale="25.0" specularConstant="8.0" specularExponent="128.0">
                    <feDistantLight azimuth="45" elevation="60"/>
                </feSpecularLighting>
            """)

            result = self.processor.apply(element, self.mock_context)

            assert result.success
            assert result.strategy == FilterStrategy.APPROXIMATION
            assert "a:sp3d" in result.drawingml
            assert "approximation" in result.drawingml

    def test_apply_emf_strategy(self):
        """Test EMF rasterization strategy."""
        # Mock to force EMF strategy
        with patch.object(self.processor, '_get_strategy', return_value=FilterStrategy.EMF_RASTERIZE):
            element = ET.fromstring("""
                <feSpecularLighting surfaceScale="2.0" specularConstant="1.0" specularExponent="32.0">
                    <feDistantLight azimuth="45" elevation="60"/>
                </feSpecularLighting>
            """)

            result = self.processor.apply(element, self.mock_context)

            assert result.success
            assert result.strategy == FilterStrategy.EMF_RASTERIZE
            assert "EMF rasterization" in result.drawingml

    def test_apply_with_exception(self):
        """Test apply method with exception handling."""
        # Invalid element that will cause parsing exception
        invalid_element = ET.fromstring('<feSpecularLighting specularConstant="invalid"/>')

        result = self.processor.apply(invalid_element, self.mock_context)

        assert not result.success
        assert result.strategy == FilterStrategy.EMF_RASTERIZE
        assert "processing failed" in result.error_message

    def test_point_light_3d_effects(self):
        """Test point light source with 3D effects."""
        element = ET.fromstring("""
            <feSpecularLighting surfaceScale="3.0" specularConstant="2.0" specularExponent="64.0">
                <fePointLight x="200" y="150" z="300"/>
            </feSpecularLighting>
        """)

        result = self.processor.apply(element, self.mock_context)

        assert result.success
        assert "point position" in result.drawingml

    def test_spot_light_3d_effects(self):
        """Test spot light source with 3D effects."""
        element = ET.fromstring("""
            <feSpecularLighting surfaceScale="2.0" specularConstant="1.5" specularExponent="32.0">
                <feSpotLight x="100" y="200" z="150" pointsAtX="300" pointsAtY="400" pointsAtZ="0"
                           limitingConeAngle="20" specularExponent="3"/>
            </feSpecularLighting>
        """)

        result = self.processor.apply(element, self.mock_context)

        assert result.success
        assert "spot cone angle" in result.drawingml

    def test_colored_lighting_effects(self):
        """Test colored lighting coordination."""
        element = ET.fromstring("""
            <feSpecularLighting surfaceScale="2.0" specularConstant="1.0" specularExponent="32.0" lighting-color="#FF6600">
                <feDistantLight azimuth="120" elevation="45"/>
            </feSpecularLighting>
        """)

        result = self.processor.apply(element, self.mock_context)

        assert result.success
        assert result.metadata['lighting_color'] == "#FF6600"

    def test_edge_case_minimal_parameters(self):
        """Test edge case with minimal parameters."""
        element = ET.fromstring("""
            <feSpecularLighting surfaceScale="0.1" specularConstant="0.1" specularExponent="0.5">
                <feDistantLight/>
            </feSpecularLighting>
        """)

        result = self.processor.apply(element, self.mock_context)

        assert result.success

    def test_edge_case_maximum_parameters(self):
        """Test edge case with maximum parameters."""
        element = ET.fromstring("""
            <feSpecularLighting surfaceScale="50.0" specularConstant="10.0" specularExponent="128.0">
                <feDistantLight azimuth="359" elevation="89"/>
            </feSpecularLighting>
        """)

        result = self.processor.apply(element, self.mock_context)

        assert result.success

    def test_shininess_material_mapping(self):
        """Test various shininess levels map to correct materials."""
        # Test each material category
        test_cases = [
            (0.5, "flat"),
            (2.0, "matte"),
            (8.0, "plastic"),
            (24.0, "softEdge"),
            (48.0, "metal"),
            (96.0, "warmMatte"),
            (128.0, "clear")
        ]

        for exponent, expected_material in test_cases:
            element = ET.fromstring(f"""
                <feSpecularLighting surfaceScale="2.0" specularConstant="1.0" specularExponent="{exponent}">
                    <feDistantLight azimuth="45" elevation="60"/>
                </feSpecularLighting>
            """)

            result = self.processor.apply(element, self.mock_context)
            assert result.success
            assert result.metadata['material'] == expected_material


class TestSpecularLightingIntegration:
    """Integration tests for specular lighting processor."""

    def setup_method(self):
        """Setup test fixtures."""
        self.processor = SpecularLightingProcessor()

        # Setup realistic context
        self.mock_context = Mock(spec=FilterContext)
        self.mock_context.unit_converter = Mock()
        self.mock_context.unit_converter.to_emu.side_effect = lambda val: float(val.replace('px', '')) * 25400
        self.mock_context.color_parser = Mock()
        self.mock_context.color_parser.parse.side_effect = lambda color: color

    def test_complete_3d_specular_integration(self):
        """Test complete integration of all 3D specular effects."""
        element = ET.fromstring("""
            <feSpecularLighting surfaceScale="3.0" specularConstant="1.5" specularExponent="64.0" lighting-color="#FFFFE0">
                <feDistantLight azimuth="45" elevation="45"/>
            </feSpecularLighting>
        """)

        result = self.processor.apply(element, self.mock_context)

        assert result.success
        assert result.strategy == FilterStrategy.NATIVE

        # Verify all 3D components are present
        assert "a:sp3d" in result.drawingml
        assert "a:bevel" in result.drawingml
        assert "a:lightRig" in result.drawingml
        assert "a:outerShdw" in result.drawingml

        # Verify proper coordination
        assert "extrusionH" in result.drawingml
        assert "rig=" in result.drawingml
        assert "blurRad" in result.drawingml

    def test_high_shininess_specular_combination(self):
        """Test high shininess with coordinated 3D effects."""
        element = ET.fromstring("""
            <feSpecularLighting surfaceScale="2.0" specularConstant="2.0" specularExponent="128.0">
                <feDistantLight azimuth="90" elevation="60"/>
            </feSpecularLighting>
        """)

        result = self.processor.apply(element, self.mock_context)

        assert result.success
        assert result.strategy == FilterStrategy.NATIVE
        assert result.metadata['material'] == "clear"  # Highest shininess

    def test_metadata_completeness(self):
        """Test that all metadata is properly populated."""
        element = ET.fromstring("""
            <feSpecularLighting surfaceScale="2.0" specularConstant="1.0" specularExponent="32.0" lighting-color="#FF6600" result="specular_result">
                <feDistantLight azimuth="45" elevation="60"/>
            </feSpecularLighting>
        """)

        result = self.processor.apply(element, self.mock_context)

        assert result.success
        assert result.metadata['filter_type'] == 'feSpecularLighting'
        assert result.metadata['approach'] == 'native_3d_specular'
        assert result.metadata['surface_scale'] == 2.0
        assert result.metadata['specular_constant'] == 1.0
        assert result.metadata['specular_exponent'] == 32.0
        assert result.metadata['lighting_color'] == "#FF6600"
        assert result.metadata['light_source_type'] == "distant"
        assert result.metadata['material'] == "softEdge"
        assert 'complexity' in result.metadata


if __name__ == "__main__":
    pytest.main([__file__, "-v"])