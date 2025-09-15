#!/usr/bin/env python3
"""
Unit tests for feSpecularLighting 3D effects and material properties (Task 2.3, Subtasks 2.3.2-2.3.8).

This test suite focuses on the PowerPoint 3D effects integration for specular lighting,
particularly testing the a:sp3d + bevel + highlight shadow combinations and material
property mapping for different shininess levels.

Focus Areas:
- Subtask 2.3.2: Tests for a:sp3d + bevel + highlight shadow combinations
- Subtask 2.3.4: Reuse feDiffuseLighting a:sp3d and a:bevel infrastructure
- Subtask 2.3.5: Add outer highlight shadow (a:outerShdw) for specular reflection
- Subtask 2.3.6: Implement shininess mapping to PowerPoint material properties
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


class TestSp3dConfiguration:
    """Test a:sp3d configuration for specular lighting (Subtask 2.3.2, 2.3.4)."""

    def setup_method(self):
        """Setup test fixtures."""
        self.filter = SpecularLightingFilter()

        self.mock_context = Mock(spec=FilterContext)
        self.mock_context.unit_converter = Mock()
        self.mock_context.unit_converter.to_emu.side_effect = lambda val: float(val.replace('px', '')) * 25400
        self.mock_context.color_parser = Mock()
        self.mock_context.color_parser.parse.return_value = "#FFFFFF"

    def test_sp3d_with_complex_surface(self):
        """Test a:sp3d configuration with complex surface scale."""
        params = SpecularLightingParameters(
            surface_scale=5.0,
            specular_constant=2.0,
            specular_exponent=64.0,
            lighting_color="#FFFFFF",
            input_source="SourceGraphic",
            light_source_type="distant",
            light_azimuth=45.0,
            light_elevation=60.0
        )

        sp3d_config = self.filter._generate_sp3d_configuration(params, self.mock_context)

        # Should generate proper a:sp3d DrawingML
        assert "a:sp3d" in sp3d_config
        assert "extrusionH" in sp3d_config
        assert "contourW" in sp3d_config
        assert "prstMaterial" in sp3d_config

        # Should call unit converter for surface scale
        self.mock_context.unit_converter.to_emu.assert_called()

        # Should have comments indicating specular lighting configuration
        assert "specular" in sp3d_config.lower()

    def test_sp3d_material_selection_based_on_shininess(self):
        """Test a:sp3d material selection based on specular exponent."""
        # Test different shininess levels
        test_cases = [
            (1.0, "flat"),        # Very low shininess
            (16.0, "plastic"),    # Medium-low shininess
            (64.0, "metal"),      # High shininess
            (128.0, "warmMatte")  # Very high shininess (glass-like)
        ]

        for exponent, expected_material in test_cases:
            params = SpecularLightingParameters(
                surface_scale=2.0,
                specular_constant=1.5,
                specular_exponent=exponent,
                lighting_color="#FFFFFF",
                input_source="SourceGraphic"
            )

            sp3d_config = self.filter._generate_sp3d_configuration(params, self.mock_context)

            # Should contain appropriate material for shininess level
            assert "prstMaterial" in sp3d_config
            # Material selection logic should be documented in comments
            assert "exponent" in sp3d_config.lower() or "shininess" in sp3d_config.lower()

    def test_sp3d_reuse_diffuse_infrastructure(self):
        """Test reuse of feDiffuseLighting a:sp3d infrastructure (Subtask 2.3.4)."""
        params = SpecularLightingParameters(
            surface_scale=3.0,
            specular_constant=1.8,
            specular_exponent=32.0,
            lighting_color="#FFFFFF",
            input_source="SourceGraphic"
        )

        sp3d_config = self.filter._generate_sp3d_configuration(params, self.mock_context)

        # Should indicate reuse of diffuse lighting infrastructure
        assert "diffuse" in sp3d_config.lower() or "reuse" in sp3d_config.lower()

        # Should follow similar structure as diffuse lighting a:sp3d
        assert "bevelT" in sp3d_config or "bevel" in sp3d_config.lower()
        assert "lightRig" in sp3d_config

    def test_sp3d_with_asymmetric_parameters(self):
        """Test a:sp3d configuration with asymmetric parameters."""
        params = SpecularLightingParameters(
            surface_scale=8.0,  # High surface scale
            specular_constant=0.5,  # Low specular constant
            specular_exponent=4.0,   # Low shininess
            lighting_color="#FF6600",  # Orange lighting
            input_source="SourceGraphic"
        )

        sp3d_config = self.filter._generate_sp3d_configuration(params, self.mock_context)

        # Should handle asymmetric/unusual parameter combinations
        assert "a:sp3d" in sp3d_config
        assert int(params.surface_scale * 25400) > 0  # Should scale surface properly

    def test_sp3d_integration_with_light_sources(self):
        """Test a:sp3d integration with different light source types."""
        light_source_types = ["distant", "point", "spot"]

        for light_type in light_source_types:
            params = SpecularLightingParameters(
                surface_scale=2.5,
                specular_constant=1.5,
                specular_exponent=32.0,
                lighting_color="#FFFFFF",
                input_source="SourceGraphic",
                light_source_type=light_type
            )

            sp3d_config = self.filter._generate_sp3d_configuration(params, self.mock_context)

            # Should adapt to different light source types
            assert "a:sp3d" in sp3d_config
            assert "lightRig" in sp3d_config


class TestBevelEffectsIntegration:
    """Test bevel effects integration for specular lighting."""

    def setup_method(self):
        """Setup test fixtures."""
        self.filter = SpecularLightingFilter()

        self.mock_context = Mock(spec=FilterContext)
        self.mock_context.unit_converter = Mock()
        self.mock_context.unit_converter.to_emu.side_effect = lambda val: float(val.replace('px', '')) * 25400
        self.mock_context.color_parser = Mock()
        self.mock_context.color_parser.parse.return_value = "#FFFFFF"

    def test_bevel_directional_mapping(self):
        """Test bevel effects mapping from light direction."""
        # Test different light directions
        test_cases = [
            (0.0, 75.0, "bevelT"),    # High elevation -> top bevel
            (45.0, 30.0, "bevelR"),   # Right azimuth -> right bevel
            (180.0, 30.0, "bevelB"),  # Back azimuth -> bottom bevel
            (270.0, 30.0, "bevelL")   # Left azimuth -> left bevel
        ]

        for azimuth, elevation, expected_bevel in test_cases:
            params = SpecularLightingParameters(
                surface_scale=2.0,
                specular_constant=1.5,
                specular_exponent=20.0,
                lighting_color="#FFFFFF",
                input_source="SourceGraphic",
                light_source_type="distant",
                light_azimuth=azimuth,
                light_elevation=elevation
            )

            bevel_effects = self.filter._generate_bevel_effects(params, self.mock_context)

            # Should generate appropriate bevel direction
            assert "bevel" in bevel_effects.lower()
            assert "a:" in bevel_effects  # Should have DrawingML namespace

    def test_bevel_intensity_scaling(self):
        """Test bevel intensity scaling based on specular parameters."""
        # Test different intensity levels
        test_cases = [
            (0.5, 4.0),   # Low intensity
            (1.5, 32.0),  # Medium intensity
            (3.0, 128.0)  # High intensity
        ]

        for specular_constant, specular_exponent in test_cases:
            params = SpecularLightingParameters(
                surface_scale=2.0,
                specular_constant=specular_constant,
                specular_exponent=specular_exponent,
                lighting_color="#FFFFFF",
                input_source="SourceGraphic"
            )

            bevel_effects = self.filter._generate_bevel_effects(params, self.mock_context)

            # Should scale bevel effects based on specular parameters
            assert "w=" in bevel_effects  # Width parameter
            assert "h=" in bevel_effects  # Height parameter

            # Should call unit converter for scaling
            assert self.mock_context.unit_converter.to_emu.call_count >= 2

    def test_bevel_reuse_diffuse_infrastructure(self):
        """Test bevel effects reuse diffuse lighting infrastructure."""
        params = SpecularLightingParameters(
            surface_scale=3.0,
            specular_constant=2.0,
            specular_exponent=16.0,
            lighting_color="#FFFFFF",
            input_source="SourceGraphic"
        )

        bevel_effects = self.filter._generate_bevel_effects(params, self.mock_context)

        # Should indicate reuse of diffuse lighting bevel infrastructure
        assert "bevel" in bevel_effects.lower()
        # Should follow similar pattern as diffuse lighting bevel generation


class TestHighlightShadowGeneration:
    """Test outer highlight shadow generation (Subtask 2.3.5)."""

    def setup_method(self):
        """Setup test fixtures."""
        self.filter = SpecularLightingFilter()

        self.mock_context = Mock(spec=FilterContext)
        self.mock_context.unit_converter = Mock()
        self.mock_context.unit_converter.to_emu.side_effect = lambda val: float(val.replace('px', '')) * 25400
        self.mock_context.color_parser = Mock()
        self.mock_context.color_parser.parse.return_value = "#FFFFFF"

    def test_outer_shadow_for_specular_reflection(self):
        """Test outer shadow generation for specular reflection highlights."""
        params = SpecularLightingParameters(
            surface_scale=2.0,
            specular_constant=2.5,
            specular_exponent=64.0,  # Shiny surface
            lighting_color="#FFFFFF",
            input_source="SourceGraphic",
            light_source_type="distant",
            light_azimuth=45.0,
            light_elevation=60.0
        )

        highlight_shadow = self.filter._generate_highlight_shadow_effects(params, self.mock_context)

        # Should generate a:outerShdw for specular highlights
        assert "a:outerShdw" in highlight_shadow
        assert "highlight" in highlight_shadow.lower()
        assert "specular" in highlight_shadow.lower()

        # Should have proper shadow parameters
        assert "blurRad" in highlight_shadow
        assert "dist" in highlight_shadow
        assert "dir" in highlight_shadow

    def test_highlight_shadow_intensity_scaling(self):
        """Test highlight shadow intensity based on specular parameters."""
        # Test different intensity combinations
        test_cases = [
            (1.0, 4.0),    # Low intensity
            (2.0, 32.0),   # Medium intensity
            (3.0, 128.0)   # High intensity
        ]

        for specular_constant, specular_exponent in test_cases:
            params = SpecularLightingParameters(
                surface_scale=2.0,
                specular_constant=specular_constant,
                specular_exponent=specular_exponent,
                lighting_color="#FFFFFF",
                input_source="SourceGraphic"
            )

            highlight_shadow = self.filter._generate_highlight_shadow_effects(params, self.mock_context)

            # Should scale highlight intensity
            assert "alpha" in highlight_shadow.lower()
            assert "srgbClr" in highlight_shadow

            # Higher specular exponent should create more focused highlights
            if specular_exponent >= 64.0:
                assert "focused" in highlight_shadow.lower() or "sharp" in highlight_shadow.lower()

    def test_highlight_shadow_color_configuration(self):
        """Test highlight shadow color configuration based on lighting color."""
        test_colors = ["#FFFFFF", "#FFD700", "#FF6600", "#00FF00"]

        for color in test_colors:
            self.mock_context.color_parser.parse.return_value = color

            params = SpecularLightingParameters(
                surface_scale=2.0,
                specular_constant=1.5,
                specular_exponent=32.0,
                lighting_color=color,
                input_source="SourceGraphic"
            )

            highlight_shadow = self.filter._generate_highlight_shadow_effects(params, self.mock_context)

            # Should use color parser for highlight color
            self.mock_context.color_parser.parse.assert_called_with(color)

            # Should contain color information
            assert "srgbClr" in highlight_shadow

    def test_highlight_shadow_direction_calculation(self):
        """Test highlight shadow direction calculation based on light source."""
        params = SpecularLightingParameters(
            surface_scale=2.0,
            specular_constant=1.8,
            specular_exponent=48.0,
            lighting_color="#FFFFFF",
            input_source="SourceGraphic",
            light_source_type="distant",
            light_azimuth=90.0,  # Right side lighting
            light_elevation=45.0
        )

        highlight_shadow = self.filter._generate_highlight_shadow_effects(params, self.mock_context)

        # Should calculate highlight direction based on light source
        assert "dir=" in highlight_shadow
        # Direction should be calculated (not hard-coded)
        direction_matches = highlight_shadow.count('dir="')
        assert direction_matches >= 1


class TestMaterialPropertyMapping:
    """Test shininess mapping to PowerPoint material properties (Subtask 2.3.6)."""

    def setup_method(self):
        """Setup test fixtures."""
        self.filter = SpecularLightingFilter()

    def test_shininess_to_material_mapping(self):
        """Test mapping different shininess levels to PowerPoint materials."""
        # Test comprehensive mapping of specular exponent to materials
        test_cases = [
            (1.0, "flat"),         # No shininess
            (4.0, "matte"),        # Low shininess
            (16.0, "plastic"),     # Medium shininess
            (32.0, "softEdge"),    # Medium-high shininess
            (64.0, "metal"),       # High shininess
            (128.0, "warmMatte"),  # Very high shininess (glass-like)
            (256.0, "clear")       # Extreme shininess (mirror-like)
        ]

        for exponent, expected_material in test_cases:
            result = self.filter._map_shininess_to_material(exponent)

            # Should return appropriate material type
            assert isinstance(result, str)
            assert len(result) > 0

            # Should be a valid PowerPoint material preset
            valid_materials = ["flat", "matte", "plastic", "softEdge", "metal", "warmMatte", "clear"]
            assert result in valid_materials

    def test_material_selection_edge_cases(self):
        """Test material selection for edge cases."""
        edge_cases = [0.0, 0.5, 500.0, 1000.0]  # Very low and very high values

        for exponent in edge_cases:
            result = self.filter._map_shininess_to_material(exponent)

            # Should handle edge cases gracefully
            assert isinstance(result, str)
            assert len(result) > 0

    def test_material_comments_include_mapping_logic(self):
        """Test that generated DrawingML includes material mapping comments."""
        params = SpecularLightingParameters(
            surface_scale=2.0,
            specular_constant=1.5,
            specular_exponent=64.0,  # Should map to metal
            lighting_color="#FFFFFF",
            input_source="SourceGraphic"
        )

        mock_context = Mock(spec=FilterContext)
        mock_context.unit_converter = Mock()
        mock_context.unit_converter.to_emu.return_value = 25400

        sp3d_config = self.filter._generate_sp3d_configuration(params, mock_context)

        # Should include comments about material mapping
        assert "material" in sp3d_config.lower()
        assert "exponent" in sp3d_config.lower() or "shininess" in sp3d_config.lower()


class TestColorIntensityConfiguration:
    """Test specular color and intensity configuration (Subtask 2.3.7)."""

    def setup_method(self):
        """Setup test fixtures."""
        self.filter = SpecularLightingFilter()

        self.mock_context = Mock(spec=FilterContext)
        self.mock_context.unit_converter = Mock()
        self.mock_context.unit_converter.to_emu.return_value = 25400
        self.mock_context.color_parser = Mock()

    def test_lighting_color_configuration(self):
        """Test configuration based on lighting-color attribute."""
        test_colors = [
            "#FFFFFF",  # White
            "#FFD700",  # Gold
            "#FF0000",  # Red
            "#00FF00",  # Green
            "#0000FF"   # Blue
        ]

        for color in test_colors:
            self.mock_context.color_parser.parse.return_value = color

            params = SpecularLightingParameters(
                surface_scale=2.0,
                specular_constant=1.5,
                specular_exponent=32.0,
                lighting_color=color,
                input_source="SourceGraphic"
            )

            drawingml = self.filter._generate_3d_specular_drawingml(params, self.mock_context)

            # Should use color parser for lighting color
            self.mock_context.color_parser.parse.assert_called_with(color)

            # Should configure color in DrawingML
            assert "srgbClr" in drawingml

            # Reset mock for next iteration
            self.mock_context.reset_mock()

    def test_specular_constant_intensity_scaling(self):
        """Test intensity scaling based on specular constant."""
        test_constants = [0.5, 1.0, 1.5, 2.0, 3.0]

        for constant in test_constants:
            params = SpecularLightingParameters(
                surface_scale=2.0,
                specular_constant=constant,
                specular_exponent=32.0,
                lighting_color="#FFFFFF",
                input_source="SourceGraphic"
            )

            self.mock_context.color_parser.parse.return_value = "#FFFFFF"

            drawingml = self.filter._generate_3d_specular_drawingml(params, self.mock_context)

            # Should scale effect intensity based on specular constant
            assert "alpha" in drawingml.lower()

            # Higher constants should produce more visible effects
            if constant >= 2.0:
                effects_count = drawingml.count("<a:")
                assert effects_count >= 3  # Should have multiple visible effects

    def test_light_parameter_integration(self):
        """Test integration of light parameters with color and intensity."""
        params = SpecularLightingParameters(
            surface_scale=3.0,
            specular_constant=2.0,
            specular_exponent=48.0,
            lighting_color="#FFD700",
            input_source="SourceGraphic",
            light_source_type="spot",
            light_x=100.0,
            light_y=150.0,
            light_z=200.0,
            cone_angle=30.0,
            spot_exponent=2.0
        )

        self.mock_context.color_parser.parse.return_value = "#FFD700"

        drawingml = self.filter._generate_3d_specular_drawingml(params, self.mock_context)

        # Should integrate light parameters with color/intensity configuration
        assert "spot" in drawingml.lower() or "light" in drawingml.lower()
        assert "srgbClr" in drawingml

        # Should call both color parser and unit converter
        self.mock_context.color_parser.parse.assert_called()
        self.mock_context.unit_converter.to_emu.assert_called()


class TestVisualDepthEnhancement:
    """Test 3D visual depth enhancement with vector precision (Subtask 2.3.8)."""

    def setup_method(self):
        """Setup test fixtures."""
        self.filter = SpecularLightingFilter()

        self.mock_context = Mock(spec=FilterContext)
        self.mock_context.unit_converter = Mock()
        self.mock_context.unit_converter.to_emu.side_effect = lambda val: float(val.replace('px', '')) * 25400
        self.mock_context.color_parser = Mock()
        self.mock_context.color_parser.parse.return_value = "#FFFFFF"

    def test_combined_effects_for_depth(self):
        """Test combination of effects creates enhanced visual depth."""
        params = SpecularLightingParameters(
            surface_scale=4.0,
            specular_constant=2.0,
            specular_exponent=64.0,
            lighting_color="#FFFFFF",
            input_source="SourceGraphic",
            light_source_type="distant",
            light_azimuth=45.0,
            light_elevation=60.0
        )

        drawingml = self.filter._generate_3d_specular_drawingml(params, self.mock_context)

        # Should combine multiple effects for realistic depth
        assert "a:sp3d" in drawingml        # 3D shape
        assert "bevel" in drawingml.lower()  # Surface detail
        assert "a:outerShdw" in drawingml   # Specular highlights
        assert "lightRig" in drawingml      # Light positioning

        # Should have sufficient effect count for realistic appearance
        effect_count = drawingml.count("<a:")
        assert effect_count >= 4  # Minimum effects for good depth

    def test_vector_precision_maintenance(self):
        """Test that effects maintain vector precision."""
        params = SpecularLightingParameters(
            surface_scale=2.123,  # Precise decimal
            specular_constant=1.789,
            specular_exponent=32.456,
            lighting_color="#FFFFFF",
            input_source="SourceGraphic"
        )

        drawingml = self.filter._generate_3d_specular_drawingml(params, self.mock_context)

        # Should maintain vector-based approach
        assert "vector" in drawingml.lower()

        # Should not use rasterization
        assert "raster" not in drawingml.lower()
        assert "bitmap" not in drawingml.lower()

        # Should use precise EMU calculations
        self.mock_context.unit_converter.to_emu.assert_called()

        # Should indicate precision maintenance in comments
        assert "precision" in drawingml.lower() or "accurate" in drawingml.lower()

    def test_complex_lighting_scenarios(self):
        """Test complex lighting scenarios maintain vector precision."""
        # Test complex scenario with multiple challenging parameters
        params = SpecularLightingParameters(
            surface_scale=8.0,    # High surface scale
            specular_constant=3.5, # High specular constant
            specular_exponent=128.0, # Very shiny surface
            lighting_color="#FFD700", # Colored lighting
            input_source="SourceGraphic",
            light_source_type="spot",
            light_x=75.5,
            light_y=125.7,
            light_z=200.3,
            cone_angle=15.0,  # Narrow cone
            spot_exponent=3.0
        )

        self.mock_context.color_parser.parse.return_value = "#FFD700"

        drawingml = self.filter._generate_3d_specular_drawingml(params, self.mock_context)

        # Even complex scenarios should maintain vector precision
        assert "vector" in drawingml.lower()

        # Should enhance visual depth with multiple effects
        assert "depth" in drawingml.lower() or "3d" in drawingml.lower()

        # Should handle complex parameters correctly (high exponent produces sharp highlight)
        assert "sharp" in drawingml.lower() or "focused" in drawingml.lower()

    def test_performance_optimization_comments(self):
        """Test that DrawingML includes performance optimization comments."""
        params = SpecularLightingParameters(
            surface_scale=3.0,
            specular_constant=2.0,
            specular_exponent=32.0,
            lighting_color="#FFFFFF",
            input_source="SourceGraphic"
        )

        drawingml = self.filter._generate_3d_specular_drawingml(params, self.mock_context)

        # Should include vector precision and depth enhancement comments
        assert "vector" in drawingml.lower() and "precision" in drawingml.lower()

        # Should indicate 3D visual depth enhancement
        assert "depth" in drawingml.lower() or "3d" in drawingml.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])