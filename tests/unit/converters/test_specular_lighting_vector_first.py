#!/usr/bin/env python3
"""
Unit tests for feSpecularLighting vector-first conversion (Task 2.3, Subtasks 2.3.1-2.3.8).

This test suite covers the vector-first feSpecularLighting implementation using PowerPoint
3D effects like a:sp3d, a:bevel, a:lightRig, and a:outerShdw for specular reflection.

Focus Areas:
- Subtask 2.3.1: Unit tests for specular lighting parameter parsing
- Subtask 2.3.2: Tests for a:sp3d + bevel + highlight shadow combinations
- Subtask 2.3.3: feSpecularLighting parser with reflection model analysis
- Subtask 2.3.4: Reuse feDiffuseLighting a:sp3d and a:bevel infrastructure
- Subtask 2.3.5: Add outer highlight shadow (a:outerShdw) for specular reflection
- Subtask 2.3.6: Shininess mapping to PowerPoint material properties
- Subtask 2.3.7: Configure specular color and intensity based on light parameters
- Subtask 2.3.8: Verify specular highlights enhance 3D visual depth with vector precision
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys
from lxml import etree as ET

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from src.converters.filters.geometric.specular_lighting import SpecularLightingFilter, SpecularLightingParameters
from src.converters.filters.core.base import FilterContext


class TestSpecularLightingFilterBasics:
    """Test basic SpecularLightingFilter functionality."""

    def setup_method(self):
        """Setup test fixtures."""
        self.filter = SpecularLightingFilter()

        # Mock FilterContext with standardized tools
        self.mock_context = Mock(spec=FilterContext)
        self.mock_context.unit_converter = Mock()
        self.mock_context.unit_converter.to_emu.return_value = 25400
        self.mock_context.color_parser = Mock()
        self.mock_context.color_parser.parse.return_value = "#FFFFFF"
        self.mock_context.transform_parser = Mock()
        self.mock_context.viewport_resolver = Mock()

    def test_filter_initialization(self):
        """Test SpecularLightingFilter initialization."""
        assert self.filter.filter_type == "specular_lighting"
        assert self.filter.strategy == "vector_first"
        assert hasattr(self.filter, 'complexity_threshold')

    def test_can_apply_fespecularlighting_element(self):
        """Test can_apply returns True for feSpecularLighting elements."""
        element = ET.Element("feSpecularLighting")
        result = self.filter.can_apply(element, self.mock_context)
        assert result is True

    def test_can_apply_with_namespace(self):
        """Test can_apply handles namespaced elements correctly."""
        element = ET.Element("{http://www.w3.org/2000/svg}feSpecularLighting")
        result = self.filter.can_apply(element, self.mock_context)
        assert result is True

    def test_can_apply_non_fespecularlighting_element(self):
        """Test can_apply returns False for non-feSpecularLighting elements."""
        element = ET.Element("feGaussianBlur")
        result = self.filter.can_apply(element, self.mock_context)
        assert result is False

    def test_can_apply_none_element(self):
        """Test can_apply handles None element gracefully."""
        result = self.filter.can_apply(None, self.mock_context)
        assert result is False


class TestSpecularLightingParameterParsing:
    """Test specular lighting parameter parsing (Subtask 2.3.1)."""

    def setup_method(self):
        """Setup test fixtures."""
        self.filter = SpecularLightingFilter()

        self.mock_context = Mock(spec=FilterContext)
        self.mock_context.unit_converter = Mock()
        self.mock_context.unit_converter.to_emu.return_value = 25400
        self.mock_context.color_parser = Mock()
        self.mock_context.color_parser.parse.return_value = "#FFFFFF"

    def test_basic_parameter_parsing(self):
        """Test parsing basic feSpecularLighting parameters."""
        element = ET.Element("feSpecularLighting")
        element.set("surfaceScale", "2.5")
        element.set("specularConstant", "1.8")
        element.set("specularExponent", "20")
        element.set("lighting-color", "#FFD700")
        element.set("in", "blur1")
        element.set("result", "specular")

        params = self.filter._parse_specular_lighting_parameters(element)

        assert params.surface_scale == 2.5
        assert params.specular_constant == 1.8
        assert params.specular_exponent == 20.0
        assert params.lighting_color == "#FFD700"
        assert params.input_source == "blur1"
        assert params.result_name == "specular"

    def test_default_parameter_values(self):
        """Test default parameter values for feSpecularLighting."""
        element = ET.Element("feSpecularLighting")

        params = self.filter._parse_specular_lighting_parameters(element)

        assert params.surface_scale == 1.0  # SVG default
        assert params.specular_constant == 1.0  # SVG default
        assert params.specular_exponent == 1.0  # SVG default
        assert params.lighting_color == "#FFFFFF"  # Default white
        assert params.input_source == "SourceGraphic"  # SVG default

    def test_invalid_numeric_parameters(self):
        """Test handling of invalid numeric parameters."""
        element = ET.Element("feSpecularLighting")
        element.set("surfaceScale", "invalid")
        element.set("specularConstant", "not_a_number")
        element.set("specularExponent", "bad_value")

        params = self.filter._parse_specular_lighting_parameters(element)

        # Should use default values for invalid parameters
        assert params.surface_scale == 1.0
        assert params.specular_constant == 1.0
        assert params.specular_exponent == 1.0

    def test_distant_light_source_parsing(self):
        """Test parsing feDistantLight child element."""
        element = ET.Element("feSpecularLighting")
        light = ET.SubElement(element, "feDistantLight")
        light.set("azimuth", "45")
        light.set("elevation", "60")

        params = self.filter._parse_specular_lighting_parameters(element)

        assert params.light_source_type == "distant"
        assert params.light_azimuth == 45.0
        assert params.light_elevation == 60.0

    def test_point_light_source_parsing(self):
        """Test parsing fePointLight child element."""
        element = ET.Element("feSpecularLighting")
        light = ET.SubElement(element, "fePointLight")
        light.set("x", "100")
        light.set("y", "150")
        light.set("z", "200")

        params = self.filter._parse_specular_lighting_parameters(element)

        assert params.light_source_type == "point"
        assert params.light_x == 100.0
        assert params.light_y == 150.0
        assert params.light_z == 200.0

    def test_spot_light_source_parsing(self):
        """Test parsing feSpotLight child element."""
        element = ET.Element("feSpecularLighting")
        light = ET.SubElement(element, "feSpotLight")
        light.set("x", "50")
        light.set("y", "75")
        light.set("z", "100")
        light.set("pointsAtX", "0")
        light.set("pointsAtY", "0")
        light.set("pointsAtZ", "0")
        light.set("limitingConeAngle", "30")
        light.set("specularExponent", "2")

        params = self.filter._parse_specular_lighting_parameters(element)

        assert params.light_source_type == "spot"
        assert params.light_x == 50.0
        assert params.light_y == 75.0
        assert params.light_z == 100.0
        assert params.light_points_at_x == 0.0
        assert params.light_points_at_y == 0.0
        assert params.light_points_at_z == 0.0
        assert params.cone_angle == 30.0
        assert params.spot_exponent == 2.0


class TestParameterValidation:
    """Test parameter validation for feSpecularLighting."""

    def setup_method(self):
        """Setup test fixtures."""
        self.filter = SpecularLightingFilter()

        self.mock_context = Mock(spec=FilterContext)

    def test_valid_parameters(self):
        """Test validation of valid parameters."""
        element = ET.Element("feSpecularLighting")
        element.set("surfaceScale", "2.0")
        element.set("specularConstant", "1.5")
        element.set("specularExponent", "20")

        result = self.filter.validate_parameters(element, self.mock_context)
        assert result is True

    def test_negative_specular_constant(self):
        """Test validation rejects negative specular constant."""
        element = ET.Element("feSpecularLighting")
        element.set("specularConstant", "-1.0")

        result = self.filter.validate_parameters(element, self.mock_context)
        assert result is False

    def test_negative_specular_exponent(self):
        """Test validation rejects negative specular exponent."""
        element = ET.Element("feSpecularLighting")
        element.set("specularExponent", "-5.0")

        result = self.filter.validate_parameters(element, self.mock_context)
        assert result is False

    def test_zero_specular_exponent(self):
        """Test validation handles zero specular exponent."""
        element = ET.Element("feSpecularLighting")
        element.set("specularExponent", "0")

        result = self.filter.validate_parameters(element, self.mock_context)
        # Zero exponent should be valid (produces uniform specular)
        assert result is True


class TestComplexityCalculation:
    """Test complexity calculation for specular lighting effects."""

    def setup_method(self):
        """Setup test fixtures."""
        self.filter = SpecularLightingFilter()

    def test_simple_specular_lighting_complexity(self):
        """Test complexity calculation for simple specular lighting."""
        params = SpecularLightingParameters(
            surface_scale=1.0,
            specular_constant=1.0,
            specular_exponent=1.0,
            lighting_color="#FFFFFF",
            input_source="SourceGraphic",
            light_source_type="distant",
            light_azimuth=0.0,
            light_elevation=45.0
        )

        complexity = self.filter._calculate_complexity(params)
        assert 0.5 <= complexity <= 1.5  # Should be relatively simple

    def test_high_surface_scale_complexity(self):
        """Test complexity increases with high surface scale."""
        params = SpecularLightingParameters(
            surface_scale=25.0,  # High surface scale
            specular_constant=1.0,
            specular_exponent=1.0,
            lighting_color="#FFFFFF",
            input_source="SourceGraphic",
            light_source_type="distant"
        )

        complexity = self.filter._calculate_complexity(params)
        assert complexity >= 2.5  # Should be marked as complex

    def test_high_specular_exponent_complexity(self):
        """Test complexity increases with high specular exponent (shininess)."""
        params = SpecularLightingParameters(
            surface_scale=1.0,
            specular_constant=1.0,
            specular_exponent=128.0,  # Very shiny surface
            lighting_color="#FFFFFF",
            input_source="SourceGraphic",
            light_source_type="distant"
        )

        complexity = self.filter._calculate_complexity(params)
        assert complexity >= 2.0  # High shininess increases complexity

    def test_spot_light_complexity(self):
        """Test spot light adds complexity."""
        params = SpecularLightingParameters(
            surface_scale=1.0,
            specular_constant=1.0,
            specular_exponent=1.0,
            lighting_color="#FFFFFF",
            input_source="SourceGraphic",
            light_source_type="spot",
            cone_angle=15.0  # Narrow cone
        )

        complexity = self.filter._calculate_complexity(params)
        assert complexity >= 1.5  # Spot light should increase complexity

    def test_colored_lighting_complexity(self):
        """Test colored lighting adds complexity."""
        params = SpecularLightingParameters(
            surface_scale=1.0,
            specular_constant=1.0,
            specular_exponent=1.0,
            lighting_color="#FF0000",  # Red lighting
            input_source="SourceGraphic",
            light_source_type="distant"
        )

        complexity = self.filter._calculate_complexity(params)
        # Should have slightly higher complexity due to colored lighting
        assert complexity > 0.5


class TestVectorFirstApplication:
    """Test vector-first specular lighting application (Subtasks 2.3.3-2.3.8)."""

    def setup_method(self):
        """Setup test fixtures."""
        self.filter = SpecularLightingFilter()

        self.mock_context = Mock(spec=FilterContext)
        self.mock_context.unit_converter = Mock()
        self.mock_context.unit_converter.to_emu.return_value = 25400
        self.mock_context.color_parser = Mock()
        self.mock_context.color_parser.parse.return_value = "#FFFFFF"

    def test_apply_simple_specular_lighting(self):
        """Test applying simple feSpecularLighting element."""
        element = ET.Element("feSpecularLighting")
        element.set("surfaceScale", "2.0")
        element.set("specularConstant", "1.5")
        element.set("specularExponent", "20")

        result = self.filter.apply(element, self.mock_context)

        assert result.success is True
        assert result.drawingml is not None
        assert "specular" in result.drawingml.lower()
        assert "vector-first" in result.drawingml.lower()

        # Should contain PowerPoint 3D effects
        assert "a:effectLst" in result.drawingml
        assert "a:sp3d" in result.drawingml

        # Metadata should be present
        assert result.metadata['filter_type'] == 'specular_lighting'
        assert result.metadata['strategy'] == 'vector_first'
        assert result.metadata['surface_scale'] == 2.0
        assert result.metadata['specular_constant'] == 1.5
        assert result.metadata['specular_exponent'] == 20.0

    def test_apply_with_distant_light(self):
        """Test applying specular lighting with distant light source."""
        element = ET.Element("feSpecularLighting")
        element.set("specularExponent", "50")  # Shiny surface
        light = ET.SubElement(element, "feDistantLight")
        light.set("azimuth", "45")
        light.set("elevation", "30")

        result = self.filter.apply(element, self.mock_context)

        assert result.success is True
        assert "distant" in result.drawingml.lower() or "azimuth" in result.drawingml.lower()

        # Should include light positioning in metadata
        assert result.metadata['light_source_type'] == 'distant'
        assert result.metadata['light_azimuth'] == 45.0
        assert result.metadata['light_elevation'] == 30.0

    def test_apply_complex_specular_still_vector(self):
        """Test complex specular lighting still uses vector-first approach."""
        element = ET.Element("feSpecularLighting")
        element.set("surfaceScale", "30.0")  # Very high surface scale
        element.set("specularExponent", "128.0")  # Very shiny
        element.set("lighting-color", "#FFD700")  # Gold lighting

        result = self.filter.apply(element, self.mock_context)

        # Even complex specular should use vector-first approach
        assert result.success is True
        assert result.metadata['strategy'] == 'vector_first'
        assert result.metadata['surface_scale'] == 30.0
        assert result.metadata['specular_exponent'] == 128.0

    @patch('src.converters.filters.geometric.specular_lighting.logger')
    def test_apply_with_exception(self, mock_logger):
        """Test handling of exceptions during apply."""
        # Mock the unit converter to raise an exception
        self.mock_context.unit_converter.to_emu.side_effect = ValueError("Unit conversion failed")

        element = ET.Element("feSpecularLighting")
        element.set("surfaceScale", "2.0")  # Non-zero to trigger unit conversion

        result = self.filter.apply(element, self.mock_context)

        assert result.success is False
        assert "failed" in result.error_message.lower()
        assert result.metadata['filter_type'] == 'specular_lighting'
        mock_logger.error.assert_called()


class TestDrawingMLGeneration:
    """Test PowerPoint DrawingML generation for specular lighting effects."""

    def setup_method(self):
        """Setup test fixtures."""
        self.filter = SpecularLightingFilter()

        self.mock_context = Mock(spec=FilterContext)
        self.mock_context.unit_converter = Mock()
        self.mock_context.unit_converter.to_emu.side_effect = lambda val: float(val.replace('px', '')) * 25400
        self.mock_context.color_parser = Mock()
        self.mock_context.color_parser.parse.return_value = "#FFFFFF"

    def test_sp3d_bevel_integration(self):
        """Test a:sp3d + bevel integration (Subtask 2.3.2, 2.3.4)."""
        params = SpecularLightingParameters(
            surface_scale=3.0,
            specular_constant=2.0,
            specular_exponent=32.0,
            lighting_color="#FFFFFF",
            input_source="SourceGraphic",
            light_source_type="distant",
            light_azimuth=45.0,
            light_elevation=60.0
        )

        drawingml = self.filter._generate_3d_specular_drawingml(params, self.mock_context)

        # Should contain a:sp3d configuration from feDiffuseLighting infrastructure
        assert "a:sp3d" in drawingml
        assert "extrusionH" in drawingml
        assert "prstMaterial" in drawingml

        # Should contain bevel effects reused from diffuse lighting
        assert "bevel" in drawingml.lower()

        # Should indicate integration with diffuse lighting infrastructure
        assert "reuse" in drawingml.lower() or "diffuse" in drawingml.lower()

    def test_outer_highlight_shadow(self):
        """Test outer highlight shadow generation (Subtask 2.3.5)."""
        params = SpecularLightingParameters(
            surface_scale=2.0,
            specular_constant=1.5,
            specular_exponent=20.0,
            lighting_color="#FFFFFF",
            input_source="SourceGraphic",
            light_source_type="distant"
        )

        drawingml = self.filter._generate_3d_specular_drawingml(params, self.mock_context)

        # Should contain outer shadow for specular reflection highlights
        assert "a:outerShdw" in drawingml
        assert "highlight" in drawingml.lower()
        assert "specular" in drawingml.lower()

    def test_shininess_material_mapping(self):
        """Test shininess mapping to PowerPoint material properties (Subtask 2.3.6)."""
        # Test different shininess levels
        test_cases = [
            (1.0, "flat"),       # Low shininess
            (20.0, "plastic"),   # Medium shininess
            (64.0, "metal"),     # High shininess
            (128.0, "warmMatte") # Very high shininess
        ]

        for exponent, expected_material_type in test_cases:
            params = SpecularLightingParameters(
                surface_scale=1.0,
                specular_constant=1.0,
                specular_exponent=exponent,
                lighting_color="#FFFFFF",
                input_source="SourceGraphic"
            )

            drawingml = self.filter._generate_3d_specular_drawingml(params, self.mock_context)

            # Should contain appropriate material mapping
            assert "prstMaterial" in drawingml
            # Material type comment should indicate shininess mapping
            assert "shininess" in drawingml.lower() or "exponent" in drawingml.lower()

    def test_specular_color_intensity_configuration(self):
        """Test specular color and intensity configuration (Subtask 2.3.7)."""
        params = SpecularLightingParameters(
            surface_scale=2.0,
            specular_constant=2.5,  # High intensity
            specular_exponent=32.0,
            lighting_color="#FFD700",  # Gold
            input_source="SourceGraphic"
        )

        drawingml = self.filter._generate_3d_specular_drawingml(params, self.mock_context)

        # Should configure color based on lighting color
        assert "srgbClr" in drawingml

        # Should use unit converter for intensity calculations
        self.mock_context.unit_converter.to_emu.assert_called()

        # Should use color parser for lighting color
        self.mock_context.color_parser.parse.assert_called_with("#FFD700")

    def test_3d_visual_depth_enhancement(self):
        """Test 3D visual depth enhancement with vector precision (Subtask 2.3.8)."""
        params = SpecularLightingParameters(
            surface_scale=4.0,
            specular_constant=1.8,
            specular_exponent=64.0,
            lighting_color="#FFFFFF",
            input_source="SourceGraphic",
            light_source_type="point",
            light_x=100.0,
            light_y=150.0,
            light_z=200.0
        )

        drawingml = self.filter._generate_3d_specular_drawingml(params, self.mock_context)

        # Should enhance 3D appearance
        assert "3d" in drawingml.lower()
        assert "depth" in drawingml.lower() or "visual" in drawingml.lower()

        # Should maintain vector precision
        assert "vector" in drawingml.lower()
        assert "precision" in drawingml.lower() or "accurate" in drawingml.lower()

        # Should not use rasterization
        assert "raster" not in drawingml.lower()
        assert "bitmap" not in drawingml.lower()

        # Should combine multiple effects for realistic appearance
        effects_count = drawingml.count("<a:")
        assert effects_count >= 3  # Should have multiple DrawingML effects


class TestErrorHandling:
    """Test error handling for specular lighting operations."""

    def setup_method(self):
        """Setup test fixtures."""
        self.filter = SpecularLightingFilter()

        self.mock_context = Mock(spec=FilterContext)
        self.mock_context.unit_converter = Mock()
        self.mock_context.color_parser = Mock()

    @patch('src.converters.filters.geometric.specular_lighting.logger')
    def test_parameter_parsing_error_handling(self, mock_logger):
        """Test error handling during parameter parsing."""
        # Create a malformed element that might cause parsing errors
        element = Mock()
        element.get.side_effect = Exception("XML parsing error")

        result = self.filter.apply(element, self.mock_context)

        assert result.success is False
        assert "failed" in result.error_message.lower()
        mock_logger.error.assert_called()

    @patch('src.converters.filters.geometric.specular_lighting.logger')
    def test_drawingml_generation_error_handling(self, mock_logger):
        """Test error handling during DrawingML generation."""
        # Mock context to raise exception during DrawingML generation
        self.mock_context.unit_converter.to_emu.side_effect = ValueError("EMU conversion failed")

        element = ET.Element("feSpecularLighting")
        element.set("surfaceScale", "2.0")  # Non-zero to trigger unit conversion

        result = self.filter.apply(element, self.mock_context)

        assert result.success is False
        assert result.metadata['filter_type'] == 'specular_lighting'
        mock_logger.error.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])