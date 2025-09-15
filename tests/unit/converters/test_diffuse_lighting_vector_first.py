#!/usr/bin/env python3
"""
Unit tests for feDiffuseLighting vector-first conversion (Task 2.2, Subtasks 2.2.1-2.2.8).

This test suite covers the vector-first diffuse lighting implementation using PowerPoint
DrawingML 3D effects like a:sp3d, a:bevel, a:lightRig, and a:innerShdw.

Focus Areas:
- Subtask 2.2.1: Unit tests for diffuse lighting parameter parsing
- Subtask 2.2.2: Tests for a:sp3d + bevel + lightRig combinations
- Subtask 2.2.3: Parser with lighting model extraction
- Subtask 2.2.4: a:sp3d configuration system for 3D shape simulation
- Subtask 2.2.5: a:bevel effects mapping from light direction and intensity
- Subtask 2.2.6: a:lightRig positioning based on light source parameters
- Subtask 2.2.7: Inner shadow effects (a:innerShdw) for depth enhancement
- Subtask 2.2.8: Realistic 3D appearance using vector effects verification
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys
from lxml import etree as ET

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from src.converters.filters.geometric.diffuse_lighting import DiffuseLightingFilter, DiffuseLightingParameters
from src.converters.filters.core.base import FilterContext, FilterResult


class TestDiffuseLightingFilterBasics:
    """Test basic functionality of DiffuseLightingFilter class."""

    def setup_method(self):
        """Setup test fixtures."""
        self.filter = DiffuseLightingFilter()

        # Create mock context with standardized tools
        self.mock_context = Mock(spec=FilterContext)
        self.mock_context.unit_converter = Mock()
        self.mock_context.unit_converter.to_emu.return_value = 25400  # 1px = 25400 EMU
        self.mock_context.color_parser = Mock()
        self.mock_context.color_parser.parse.return_value = "#FFFFFF"
        self.mock_context.transform_parser = Mock()
        self.mock_context.viewport_resolver = Mock()

    def test_filter_initialization(self):
        """Test DiffuseLightingFilter initialization."""
        assert self.filter.filter_type == "diffuse_lighting"
        assert self.filter.strategy == "vector_first"
        assert self.filter.complexity_threshold == 3.0

    def test_can_apply_fediffuselighting_element(self):
        """Test can_apply method with feDiffuseLighting elements."""
        diffuse_element = ET.Element("feDiffuseLighting")
        assert self.filter.can_apply(diffuse_element, self.mock_context) is True

    def test_can_apply_fediffuselighting_namespaced(self):
        """Test can_apply method with namespaced feDiffuseLighting elements."""
        diffuse_element = ET.Element("{http://www.w3.org/2000/svg}feDiffuseLighting")
        assert self.filter.can_apply(diffuse_element, self.mock_context) is True

    def test_can_apply_other_elements(self):
        """Test can_apply method with non-diffuse-lighting elements."""
        blur_element = ET.Element("feGaussianBlur")
        assert self.filter.can_apply(blur_element, self.mock_context) is False

    def test_can_apply_none_element(self):
        """Test can_apply method with None element."""
        assert self.filter.can_apply(None, self.mock_context) is False


class TestDiffuseLightingParameterParsing:
    """Test diffuse lighting parameter parsing (Subtask 2.2.1)."""

    def setup_method(self):
        """Setup test fixtures."""
        self.filter = DiffuseLightingFilter()

    def test_parse_basic_diffuse_lighting_parameters(self):
        """Test parsing basic diffuse lighting parameters."""
        diffuse_element = ET.Element("feDiffuseLighting")
        diffuse_element.set("surfaceScale", "2.0")
        diffuse_element.set("diffuseConstant", "1.5")
        diffuse_element.set("lighting-color", "#FF0000")
        diffuse_element.set("in", "SourceGraphic")
        diffuse_element.set("result", "lit")

        params = self.filter._parse_diffuse_lighting_parameters(diffuse_element)

        assert params.surface_scale == 2.0
        assert params.diffuse_constant == 1.5
        assert params.lighting_color == "#FF0000"
        assert params.input_source == "SourceGraphic"
        assert params.result_name == "lit"

    def test_parse_default_parameters(self):
        """Test parsing with default parameter values."""
        diffuse_element = ET.Element("feDiffuseLighting")
        # No attributes set - should use defaults

        params = self.filter._parse_diffuse_lighting_parameters(diffuse_element)

        assert params.surface_scale == 1.0  # SVG default
        assert params.diffuse_constant == 1.0  # SVG default
        assert params.lighting_color == "#FFFFFF"  # Default white
        assert params.input_source == "SourceGraphic"
        assert params.result_name is None

    def test_parse_with_light_source_reference(self):
        """Test parsing with light source child element."""
        diffuse_element = ET.Element("feDiffuseLighting")

        # Add feDistantLight child
        distant_light = ET.SubElement(diffuse_element, "feDistantLight")
        distant_light.set("azimuth", "45")
        distant_light.set("elevation", "30")

        params = self.filter._parse_diffuse_lighting_parameters(diffuse_element)

        assert params.light_source_type == "distant"
        assert params.light_azimuth == 45.0
        assert params.light_elevation == 30.0

    def test_parse_point_light_source(self):
        """Test parsing with fePointLight source."""
        diffuse_element = ET.Element("feDiffuseLighting")

        # Add fePointLight child
        point_light = ET.SubElement(diffuse_element, "fePointLight")
        point_light.set("x", "100")
        point_light.set("y", "200")
        point_light.set("z", "50")

        params = self.filter._parse_diffuse_lighting_parameters(diffuse_element)

        assert params.light_source_type == "point"
        assert params.light_x == 100.0
        assert params.light_y == 200.0
        assert params.light_z == 50.0

    def test_parse_spot_light_source(self):
        """Test parsing with feSpotLight source."""
        diffuse_element = ET.Element("feDiffuseLighting")

        # Add feSpotLight child
        spot_light = ET.SubElement(diffuse_element, "feSpotLight")
        spot_light.set("x", "50")
        spot_light.set("y", "75")
        spot_light.set("z", "25")
        spot_light.set("pointsAtX", "150")
        spot_light.set("pointsAtY", "250")
        spot_light.set("pointsAtZ", "0")
        spot_light.set("specularExponent", "2.0")
        spot_light.set("limitingConeAngle", "30.0")

        params = self.filter._parse_diffuse_lighting_parameters(diffuse_element)

        assert params.light_source_type == "spot"
        assert params.light_x == 50.0
        assert params.light_points_at_x == 150.0
        assert params.spot_exponent == 2.0
        assert params.cone_angle == 30.0

    def test_parse_invalid_numeric_values(self):
        """Test parsing with invalid numeric values."""
        diffuse_element = ET.Element("feDiffuseLighting")
        diffuse_element.set("surfaceScale", "invalid")
        diffuse_element.set("diffuseConstant", "not-a-number")

        params = self.filter._parse_diffuse_lighting_parameters(diffuse_element)

        # Should default to standard values for invalid inputs
        assert params.surface_scale == 1.0
        assert params.diffuse_constant == 1.0

    def test_parse_extreme_values(self):
        """Test parsing with extreme parameter values."""
        diffuse_element = ET.Element("feDiffuseLighting")
        diffuse_element.set("surfaceScale", "100.0")  # Very high surface scale
        diffuse_element.set("diffuseConstant", "0.01")  # Very low diffuse constant

        params = self.filter._parse_diffuse_lighting_parameters(diffuse_element)

        assert params.surface_scale == 100.0
        assert params.diffuse_constant == 0.01


class TestParameterValidation:
    """Test parameter validation."""

    def setup_method(self):
        """Setup test fixtures."""
        self.filter = DiffuseLightingFilter()
        self.mock_context = Mock(spec=FilterContext)

    def test_validate_valid_diffuse_parameters(self):
        """Test validation of valid diffuse lighting parameters."""
        diffuse_element = ET.Element("feDiffuseLighting")
        diffuse_element.set("surfaceScale", "2.0")
        diffuse_element.set("diffuseConstant", "1.0")
        diffuse_element.set("lighting-color", "#FFFFFF")

        assert self.filter.validate_parameters(diffuse_element, self.mock_context) is True

    def test_validate_negative_surface_scale(self):
        """Test validation with negative surface scale."""
        diffuse_element = ET.Element("feDiffuseLighting")
        diffuse_element.set("surfaceScale", "-1.0")

        # Negative surface scale is technically valid in SVG (flips surface)
        assert self.filter.validate_parameters(diffuse_element, self.mock_context) is True

    def test_validate_zero_diffuse_constant(self):
        """Test validation with zero diffuse constant."""
        diffuse_element = ET.Element("feDiffuseLighting")
        diffuse_element.set("diffuseConstant", "0.0")

        # Zero diffuse constant is valid (no diffuse reflection)
        assert self.filter.validate_parameters(diffuse_element, self.mock_context) is True

    def test_validate_missing_light_source(self):
        """Test validation with no light source child element."""
        diffuse_element = ET.Element("feDiffuseLighting")

        # Should still be valid - will use default lighting
        assert self.filter.validate_parameters(diffuse_element, self.mock_context) is True


class TestComplexityCalculation:
    """Test complexity calculation for strategy decisions."""

    def setup_method(self):
        """Setup test fixtures."""
        self.filter = DiffuseLightingFilter()

    def test_simple_diffuse_lighting_complexity(self):
        """Test complexity for simple diffuse lighting."""
        params = DiffuseLightingParameters(
            surface_scale=1.0,
            diffuse_constant=1.0,
            lighting_color="#FFFFFF",
            light_source_type="distant",
            input_source="SourceGraphic"
        )

        complexity = self.filter._calculate_complexity(params)
        assert 0.5 <= complexity <= 2.0  # Simple case

    def test_high_surface_scale_complexity(self):
        """Test complexity with high surface scale."""
        params = DiffuseLightingParameters(
            surface_scale=50.0,  # Very high surface scale
            diffuse_constant=1.0,
            lighting_color="#FFFFFF",
            light_source_type="distant",
            input_source="SourceGraphic"
        )

        complexity = self.filter._calculate_complexity(params)
        assert complexity > 2.0  # Should increase complexity

    def test_complex_spot_light_complexity(self):
        """Test complexity with complex spot light source."""
        params = DiffuseLightingParameters(
            surface_scale=10.0,
            diffuse_constant=2.0,
            lighting_color="#FF00FF",  # Non-white color
            light_source_type="spot",  # Complex light type
            cone_angle=15.0,  # Narrow cone
            spot_exponent=5.0,  # High exponent
            input_source="blur1"
        )

        complexity = self.filter._calculate_complexity(params)
        assert complexity > 3.0  # Should be high complexity


class TestVectorFirstApplication:
    """Test vector-first diffuse lighting application (Subtasks 2.2.4-2.2.8)."""

    def setup_method(self):
        """Setup test fixtures."""
        self.filter = DiffuseLightingFilter()

        # Mock context with standardized tools
        self.mock_context = Mock(spec=FilterContext)
        self.mock_context.unit_converter = Mock()
        self.mock_context.unit_converter.to_emu.side_effect = lambda val: float(val.replace('px', '')) * 25400
        self.mock_context.color_parser = Mock()
        self.mock_context.color_parser.parse.return_value = "#FFFFFF"
        self.mock_context.transform_parser = Mock()
        self.mock_context.viewport_resolver = Mock()

    def test_apply_basic_diffuse_lighting(self):
        """Test applying basic diffuse lighting with vector-first approach."""
        diffuse_element = ET.Element("feDiffuseLighting")
        diffuse_element.set("surfaceScale", "2.0")
        diffuse_element.set("diffuseConstant", "1.0")
        diffuse_element.set("result", "lit")

        result = self.filter.apply(diffuse_element, self.mock_context)

        assert result.success is True
        assert "3d" in result.drawingml.lower()
        assert result.metadata['strategy'] == 'vector_first'
        assert result.metadata['surface_scale'] == 2.0

    def test_apply_with_distant_light(self):
        """Test applying diffuse lighting with distant light source."""
        diffuse_element = ET.Element("feDiffuseLighting")
        distant_light = ET.SubElement(diffuse_element, "feDistantLight")
        distant_light.set("azimuth", "45")
        distant_light.set("elevation", "30")

        result = self.filter.apply(diffuse_element, self.mock_context)

        assert result.success is True
        assert "lightrig" in result.drawingml.lower()
        assert result.metadata['light_source_type'] == 'distant'
        assert result.metadata['light_azimuth'] == 45.0

    def test_apply_colored_lighting(self):
        """Test applying diffuse lighting with colored light."""
        diffuse_element = ET.Element("feDiffuseLighting")
        diffuse_element.set("lighting-color", "#FF0000")
        diffuse_element.set("surfaceScale", "3.0")

        result = self.filter.apply(diffuse_element, self.mock_context)

        assert result.success is True
        assert result.metadata['lighting_color'] == '#FF0000'
        # Should include color information in DrawingML
        assert "#ff0000" in result.drawingml.lower() or "srgbclr" in result.drawingml.lower()

    def test_sp3d_configuration_system(self):
        """Test a:sp3d configuration system for 3D shape simulation (Subtask 2.2.4)."""
        diffuse_element = ET.Element("feDiffuseLighting")
        diffuse_element.set("surfaceScale", "5.0")

        result = self.filter.apply(diffuse_element, self.mock_context)

        assert result.success is True
        # Should contain 3D shape configuration
        assert "a:sp3d" in result.drawingml
        assert "extrusionH" in result.drawingml or "contourW" in result.drawingml

    def test_bevel_effects_mapping(self):
        """Test a:bevel effects mapping from light direction (Subtask 2.2.5)."""
        diffuse_element = ET.Element("feDiffuseLighting")
        distant_light = ET.SubElement(diffuse_element, "feDistantLight")
        distant_light.set("azimuth", "90")  # Side lighting
        distant_light.set("elevation", "45")

        result = self.filter.apply(diffuse_element, self.mock_context)

        assert result.success is True
        # Should contain bevel effects based on light direction
        assert "a:bevel" in result.drawingml
        assert "bevelT" in result.drawingml or "bevelB" in result.drawingml

    def test_lightrig_positioning(self):
        """Test a:lightRig positioning based on light source parameters (Subtask 2.2.6)."""
        diffuse_element = ET.Element("feDiffuseLighting")
        distant_light = ET.SubElement(diffuse_element, "feDistantLight")
        distant_light.set("azimuth", "180")  # Back lighting
        distant_light.set("elevation", "60")  # High elevation

        result = self.filter.apply(diffuse_element, self.mock_context)

        assert result.success is True
        # Should contain light rig positioning
        assert "a:lightRig" in result.drawingml
        assert "rig=" in result.drawingml
        # Should map azimuth/elevation to PowerPoint light direction

    def test_inner_shadow_depth_enhancement(self):
        """Test inner shadow effects for depth enhancement (Subtask 2.2.7)."""
        diffuse_element = ET.Element("feDiffuseLighting")
        diffuse_element.set("surfaceScale", "4.0")  # High surface scale for depth

        result = self.filter.apply(diffuse_element, self.mock_context)

        assert result.success is True
        # Should contain inner shadow for depth
        assert "a:innerShdw" in result.drawingml
        assert "blurRad" in result.drawingml
        assert "dist" in result.drawingml

    def test_complex_lighting_still_vector_first(self):
        """Test that complex lighting still uses vector-first approach."""
        diffuse_element = ET.Element("feDiffuseLighting")
        diffuse_element.set("surfaceScale", "20.0")  # Very high surface scale
        diffuse_element.set("diffuseConstant", "3.0")  # High diffuse constant

        spot_light = ET.SubElement(diffuse_element, "feSpotLight")
        spot_light.set("limitingConeAngle", "10.0")  # Narrow cone

        result = self.filter.apply(diffuse_element, self.mock_context)

        assert result.success is True
        assert result.metadata['strategy'] == 'vector_first'  # Should still be vector-first
        assert result.metadata['complexity'] > 3.0  # High complexity
        assert "vector-first" in result.drawingml.lower()


class TestDrawingMLGeneration:
    """Test PowerPoint DrawingML generation for 3D lighting effects."""

    def setup_method(self):
        """Setup test fixtures."""
        self.filter = DiffuseLightingFilter()

        # Mock context
        self.mock_context = Mock(spec=FilterContext)
        self.mock_context.unit_converter = Mock()
        self.mock_context.unit_converter.to_emu.side_effect = lambda val: float(val.replace('px', '')) * 25400
        self.mock_context.color_parser = Mock()
        self.mock_context.color_parser.parse.return_value = "#FFFFFF"

    def test_basic_3d_drawingml_structure(self):
        """Test basic 3D DrawingML structure generation."""
        params = DiffuseLightingParameters(
            surface_scale=2.0,
            diffuse_constant=1.0,
            lighting_color="#FFFFFF",
            light_source_type="distant",
            input_source="SourceGraphic"
        )

        drawingml = self.filter._generate_3d_lighting_drawingml(params, self.mock_context)

        # Should contain all 3D effect elements
        assert "a:sp3d" in drawingml
        assert "a:bevel" in drawingml
        assert "a:lightRig" in drawingml
        assert "a:innerShdw" in drawingml
        assert "vector-first" in drawingml.lower()

    def test_distant_light_drawingml(self):
        """Test DrawingML generation for distant light source."""
        params = DiffuseLightingParameters(
            surface_scale=1.0,
            diffuse_constant=1.0,
            lighting_color="#FFFFFF",
            light_source_type="distant",
            light_azimuth=45.0,
            light_elevation=30.0,
            input_source="SourceGraphic"
        )

        drawingml = self.filter._generate_3d_lighting_drawingml(params, self.mock_context)

        # Should map azimuth/elevation to light rig direction
        assert "a:lightRig" in drawingml
        assert "rig=" in drawingml
        # Should include directional information

    def test_point_light_drawingml(self):
        """Test DrawingML generation for point light source."""
        params = DiffuseLightingParameters(
            surface_scale=2.0,
            diffuse_constant=1.5,
            lighting_color="#FFFF00",
            light_source_type="point",
            light_x=100.0,
            light_y=200.0,
            light_z=50.0,
            input_source="SourceGraphic"
        )

        drawingml = self.filter._generate_3d_lighting_drawingml(params, self.mock_context)

        # Should contain 3D positioning information
        assert "a:lightRig" in drawingml
        assert "a:sp3d" in drawingml
        # Point lights should use different configuration than distant

    def test_colored_lighting_drawingml(self):
        """Test DrawingML generation with colored lighting."""
        params = DiffuseLightingParameters(
            surface_scale=1.0,
            diffuse_constant=1.0,
            lighting_color="#FF0000",  # Red lighting
            light_source_type="distant",
            input_source="SourceGraphic"
        )

        drawingml = self.filter._generate_3d_lighting_drawingml(params, self.mock_context)

        # Should include color information in effects
        assert "srgbClr" in drawingml or "rgb" in drawingml.lower()
        # Color parser should be called
        self.mock_context.color_parser.parse.assert_called()

    def test_high_surface_scale_drawingml(self):
        """Test DrawingML generation with high surface scale."""
        params = DiffuseLightingParameters(
            surface_scale=10.0,  # High surface scale
            diffuse_constant=1.0,
            lighting_color="#FFFFFF",
            light_source_type="distant",
            input_source="SourceGraphic"
        )

        drawingml = self.filter._generate_3d_lighting_drawingml(params, self.mock_context)

        # Should increase 3D extrusion based on surface scale
        assert "extrusionH" in drawingml or "contourW" in drawingml
        assert "a:sp3d" in drawingml
        # EMU conversion should be called
        self.mock_context.unit_converter.to_emu.assert_called()


class TestRealistic3DAppearance:
    """Test that diffuse lighting creates realistic 3D appearance (Subtask 2.2.8)."""

    def setup_method(self):
        """Setup test fixtures."""
        self.filter = DiffuseLightingFilter()

        self.mock_context = Mock(spec=FilterContext)
        self.mock_context.unit_converter = Mock()
        self.mock_context.unit_converter.to_emu.return_value = 25400
        self.mock_context.color_parser = Mock()
        self.mock_context.color_parser.parse.return_value = "#FFFFFF"

    def test_realistic_3d_effect_combination(self):
        """Test combination of 3D effects creates realistic appearance."""
        diffuse_element = ET.Element("feDiffuseLighting")
        diffuse_element.set("surfaceScale", "3.0")
        diffuse_element.set("diffuseConstant", "1.2")

        distant_light = ET.SubElement(diffuse_element, "feDistantLight")
        distant_light.set("azimuth", "135")
        distant_light.set("elevation", "45")

        result = self.filter.apply(diffuse_element, self.mock_context)

        assert result.success is True

        # Should combine all effects for realistic 3D appearance
        drawingml = result.drawingml

        # 3D shape configuration
        assert "a:sp3d" in drawingml

        # Bevel for lighting direction
        assert "a:bevel" in drawingml

        # Light rig for illumination
        assert "a:lightRig" in drawingml

        # Inner shadow for depth
        assert "a:innerShdw" in drawingml

        # Should not fall back to rasterization
        assert "raster" not in drawingml.lower()
        assert "bitmap" not in drawingml.lower()

    def test_vector_precision_maintenance(self):
        """Test that diffuse lighting maintains vector precision."""
        diffuse_element = ET.Element("feDiffuseLighting")
        diffuse_element.set("surfaceScale", "2.123456")  # Precise value
        diffuse_element.set("diffuseConstant", "1.789012")

        result = self.filter.apply(diffuse_element, self.mock_context)

        assert result.success is True
        # Should maintain precision in metadata
        assert abs(result.metadata['surface_scale'] - 2.123456) < 1e-6
        assert abs(result.metadata['diffuse_constant'] - 1.789012) < 1e-6
        assert result.metadata['strategy'] == 'vector_first'  # Not rasterized

    def test_powerpoint_compatibility_elements(self):
        """Test PowerPoint compatibility elements are present."""
        diffuse_element = ET.Element("feDiffuseLighting")
        diffuse_element.set("surfaceScale", "2.0")

        result = self.filter.apply(diffuse_element, self.mock_context)

        assert result.success is True
        drawingml = result.drawingml

        # Should use PowerPoint-compatible DrawingML elements
        assert "a:" in drawingml  # DrawingML namespace
        assert "a:sp3d" in drawingml
        assert "a:bevel" in drawingml or "bevel" in drawingml.lower()
        assert "a:lightRig" in drawingml
        assert "a:innerShdw" in drawingml


class TestErrorHandling:
    """Test error handling and edge cases."""

    def setup_method(self):
        """Setup test fixtures."""
        self.filter = DiffuseLightingFilter()
        self.mock_context = Mock(spec=FilterContext)

    def test_apply_invalid_element(self):
        """Test applying filter to invalid element."""
        invalid_element = ET.Element("feGaussianBlur")  # Not feDiffuseLighting

        result = self.filter.apply(invalid_element, self.mock_context)

        # Should still process but may not be optimal
        assert isinstance(result, FilterResult)

    def test_apply_with_exception(self):
        """Test handling of exceptions during apply."""
        diffuse_element = ET.Element("feDiffuseLighting")
        diffuse_element.set("surfaceScale", "2.0")

        # Mock unit converter to raise exception
        self.mock_context.unit_converter = Mock()
        self.mock_context.unit_converter.to_emu.side_effect = Exception("Unit conversion failed")
        self.mock_context.color_parser = Mock()

        result = self.filter.apply(diffuse_element, self.mock_context)

        assert result.success is False
        assert "failed" in result.error_message.lower()
        assert result.metadata['error'] is not None

    def test_missing_light_source_handling(self):
        """Test handling of missing light source elements."""
        diffuse_element = ET.Element("feDiffuseLighting")
        # No light source child element

        result = self.filter.apply(diffuse_element, self.mock_context)

        # Should use default lighting and still succeed
        assert isinstance(result, FilterResult)
        # Should handle gracefully with default distant light


if __name__ == "__main__":
    pytest.main([__file__, "-v"])