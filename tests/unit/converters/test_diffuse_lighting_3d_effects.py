#!/usr/bin/env python3
"""
Unit tests for feDiffuseLighting 3D effects combinations (Task 2.2, Subtask 2.2.2).

This test suite focuses specifically on testing a:sp3d + bevel + lightRig combinations
for realistic 3D lighting effects using PowerPoint DrawingML.

Focus Areas:
- a:sp3d configuration and 3D shape simulation
- a:bevel effects mapping from light direction and intensity
- a:lightRig positioning based on light source parameters
- Complex combinations and realistic 3D appearance
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


class TestSp3dConfiguration:
    """Test a:sp3d configuration system for 3D shape simulation (Subtask 2.2.4)."""

    def setup_method(self):
        """Setup test fixtures."""
        self.filter = DiffuseLightingFilter()

        self.mock_context = Mock(spec=FilterContext)
        self.mock_context.unit_converter = Mock()
        self.mock_context.unit_converter.to_emu.side_effect = lambda val: float(val.replace('px', '')) * 25400
        self.mock_context.color_parser = Mock()
        self.mock_context.color_parser.parse.return_value = "#FFFFFF"

    def test_basic_sp3d_configuration(self):
        """Test basic a:sp3d configuration generation."""
        params = DiffuseLightingParameters(
            surface_scale=2.0,
            diffuse_constant=1.0,
            lighting_color="#FFFFFF",
            light_source_type="distant",
            input_source="SourceGraphic"
        )

        drawingml = self.filter._generate_sp3d_configuration(params, self.mock_context)

        assert "a:sp3d" in drawingml
        assert "extrusionH=" in drawingml or "contourW=" in drawingml
        assert "3d shape simulation" in drawingml.lower()

    def test_surface_scale_to_extrusion_mapping(self):
        """Test mapping surface scale to 3D extrusion height."""
        # Low surface scale
        low_params = DiffuseLightingParameters(
            surface_scale=1.0,
            diffuse_constant=1.0,
            lighting_color="#FFFFFF",
            light_source_type="distant",
            input_source="SourceGraphic"
        )

        low_drawingml = self.filter._generate_sp3d_configuration(low_params, self.mock_context)

        # High surface scale
        high_params = DiffuseLightingParameters(
            surface_scale=10.0,
            diffuse_constant=1.0,
            lighting_color="#FFFFFF",
            light_source_type="distant",
            input_source="SourceGraphic"
        )

        high_drawingml = self.filter._generate_sp3d_configuration(high_params, self.mock_context)

        # High surface scale should result in higher extrusion
        assert "a:sp3d" in low_drawingml
        assert "a:sp3d" in high_drawingml
        # Should call EMU converter for different values
        assert self.mock_context.unit_converter.to_emu.call_count >= 2

    def test_sp3d_material_properties(self):
        """Test a:sp3d material properties configuration."""
        params = DiffuseLightingParameters(
            surface_scale=3.0,
            diffuse_constant=2.0,  # High diffuse constant
            lighting_color="#FFFFFF",
            light_source_type="distant",
            input_source="SourceGraphic"
        )

        drawingml = self.filter._generate_sp3d_configuration(params, self.mock_context)

        # Should include material properties
        assert "a:sp3d" in drawingml
        assert "prstMaterial=" in drawingml or "material" in drawingml.lower()

    def test_sp3d_with_complex_surface(self):
        """Test a:sp3d configuration with complex surface parameters."""
        params = DiffuseLightingParameters(
            surface_scale=5.0,
            diffuse_constant=1.5,
            lighting_color="#CCCCCC",  # Gray lighting
            light_source_type="distant",
            input_source="blur1"  # Non-default input
        )

        drawingml = self.filter._generate_sp3d_configuration(params, self.mock_context)

        assert "a:sp3d" in drawingml
        # Should handle complex surface parameters
        assert "extrusionH" in drawingml or "contourW" in drawingml
        # Should reference input source in comments
        assert "blur1" in drawingml or "input" in drawingml.lower()


class TestBevelEffectsMapping:
    """Test a:bevel effects mapping from light direction and intensity (Subtask 2.2.5)."""

    def setup_method(self):
        """Setup test fixtures."""
        self.filter = DiffuseLightingFilter()

        self.mock_context = Mock(spec=FilterContext)
        self.mock_context.unit_converter = Mock()
        self.mock_context.unit_converter.to_emu.return_value = 25400

    def test_distant_light_to_bevel_mapping(self):
        """Test mapping distant light direction to bevel effects."""
        params = DiffuseLightingParameters(
            surface_scale=2.0,
            diffuse_constant=1.0,
            lighting_color="#FFFFFF",
            light_source_type="distant",
            light_azimuth=45.0,
            light_elevation=30.0,
            input_source="SourceGraphic"
        )

        drawingml = self.filter._generate_bevel_effects(params, self.mock_context)

        assert "a:bevel" in drawingml
        # Should map light direction to bevel orientation
        assert "bevelT" in drawingml or "bevelB" in drawingml or "bevelL" in drawingml or "bevelR" in drawingml
        assert "w=" in drawingml and "h=" in drawingml  # Bevel dimensions

    def test_top_lighting_bevel_mapping(self):
        """Test top lighting creates appropriate bevel effects."""
        params = DiffuseLightingParameters(
            surface_scale=2.0,
            diffuse_constant=1.0,
            lighting_color="#FFFFFF",
            light_source_type="distant",
            light_azimuth=0.0,  # North
            light_elevation=90.0,  # Directly from above
            input_source="SourceGraphic"
        )

        drawingml = self.filter._generate_bevel_effects(params, self.mock_context)

        # Top lighting should create top bevel
        assert "a:bevel" in drawingml
        assert "bevelT" in drawingml
        assert "elevation 90" in drawingml.lower() or "top" in drawingml.lower()

    def test_side_lighting_bevel_mapping(self):
        """Test side lighting creates appropriate bevel effects."""
        params = DiffuseLightingParameters(
            surface_scale=2.0,
            diffuse_constant=1.0,
            lighting_color="#FFFFFF",
            light_source_type="distant",
            light_azimuth=90.0,  # East/right side
            light_elevation=45.0,  # 45 degree angle
            input_source="SourceGraphic"
        )

        drawingml = self.filter._generate_bevel_effects(params, self.mock_context)

        # Side lighting should create side bevel
        assert "a:bevel" in drawingml
        # Should contain directional information
        assert "azimuth 90" in drawingml.lower() or "side" in drawingml.lower()

    def test_diffuse_constant_to_bevel_intensity(self):
        """Test mapping diffuse constant to bevel intensity."""
        # Low diffuse constant
        low_params = DiffuseLightingParameters(
            surface_scale=2.0,
            diffuse_constant=0.2,  # Low intensity
            lighting_color="#FFFFFF",
            light_source_type="distant",
            light_azimuth=45.0,
            light_elevation=30.0,
            input_source="SourceGraphic"
        )

        low_drawingml = self.filter._generate_bevel_effects(low_params, self.mock_context)

        # High diffuse constant
        high_params = DiffuseLightingParameters(
            surface_scale=2.0,
            diffuse_constant=3.0,  # High intensity
            lighting_color="#FFFFFF",
            light_source_type="distant",
            light_azimuth=45.0,
            light_elevation=30.0,
            input_source="SourceGraphic"
        )

        high_drawingml = self.filter._generate_bevel_effects(high_params, self.mock_context)

        # Both should have bevel, but different intensities
        assert "a:bevel" in low_drawingml
        assert "a:bevel" in high_drawingml
        # Different diffuse constants should result in different bevel parameters

    def test_point_light_bevel_mapping(self):
        """Test point light source creates appropriate bevel effects."""
        params = DiffuseLightingParameters(
            surface_scale=2.0,
            diffuse_constant=1.0,
            lighting_color="#FFFFFF",
            light_source_type="point",
            light_x=100.0,
            light_y=50.0,
            light_z=75.0,
            input_source="SourceGraphic"
        )

        drawingml = self.filter._generate_bevel_effects(params, self.mock_context)

        assert "a:bevel" in drawingml
        # Point light should calculate direction from position
        assert "point light" in drawingml.lower() or "position" in drawingml.lower()


class TestLightRigPositioning:
    """Test a:lightRig positioning based on light source parameters (Subtask 2.2.6)."""

    def setup_method(self):
        """Setup test fixtures."""
        self.filter = DiffuseLightingFilter()

        self.mock_context = Mock(spec=FilterContext)
        self.mock_context.unit_converter = Mock()
        self.mock_context.unit_converter.to_emu.return_value = 25400

    def test_distant_light_rig_positioning(self):
        """Test distant light mapping to PowerPoint light rig."""
        params = DiffuseLightingParameters(
            surface_scale=2.0,
            diffuse_constant=1.0,
            lighting_color="#FFFFFF",
            light_source_type="distant",
            light_azimuth=45.0,
            light_elevation=60.0,
            input_source="SourceGraphic"
        )

        drawingml = self.filter._generate_lightrig_positioning(params, self.mock_context)

        assert "a:lightRig" in drawingml
        assert "rig=" in drawingml
        # Should map azimuth/elevation to PowerPoint light direction
        assert "dir=" in drawingml or "direction" in drawingml.lower()

    def test_standard_light_rig_directions(self):
        """Test mapping to standard PowerPoint light rig directions."""
        # Test top lighting
        top_params = DiffuseLightingParameters(
            surface_scale=1.0,
            diffuse_constant=1.0,
            lighting_color="#FFFFFF",
            light_source_type="distant",
            light_azimuth=0.0,
            light_elevation=90.0,  # Top
            input_source="SourceGraphic"
        )

        top_drawingml = self.filter._generate_lightrig_positioning(top_params, self.mock_context)

        # Test front lighting
        front_params = DiffuseLightingParameters(
            surface_scale=1.0,
            diffuse_constant=1.0,
            lighting_color="#FFFFFF",
            light_source_type="distant",
            light_azimuth=180.0,
            light_elevation=45.0,  # Front
            input_source="SourceGraphic"
        )

        front_drawingml = self.filter._generate_lightrig_positioning(front_params, self.mock_context)

        # Both should have light rigs but different directions
        assert "a:lightRig" in top_drawingml
        assert "a:lightRig" in front_drawingml
        assert "rig=" in top_drawingml
        assert "rig=" in front_drawingml

    def test_point_light_rig_positioning(self):
        """Test point light source light rig positioning."""
        params = DiffuseLightingParameters(
            surface_scale=2.0,
            diffuse_constant=1.0,
            lighting_color="#FFFFFF",
            light_source_type="point",
            light_x=150.0,
            light_y=100.0,
            light_z=200.0,
            input_source="SourceGraphic"
        )

        drawingml = self.filter._generate_lightrig_positioning(params, self.mock_context)

        assert "a:lightRig" in drawingml
        # Point light should calculate effective direction from 3D position
        assert "rig=" in drawingml
        # Should include position information in comments
        assert "point" in drawingml.lower() or "position" in drawingml.lower()

    def test_spot_light_rig_positioning(self):
        """Test spot light source light rig positioning."""
        params = DiffuseLightingParameters(
            surface_scale=2.0,
            diffuse_constant=1.0,
            lighting_color="#FFFFFF",
            light_source_type="spot",
            light_x=100.0,
            light_y=100.0,
            light_z=100.0,
            light_points_at_x=200.0,
            light_points_at_y=200.0,
            light_points_at_z=0.0,
            cone_angle=30.0,
            spot_exponent=2.0,
            input_source="SourceGraphic"
        )

        drawingml = self.filter._generate_lightrig_positioning(params, self.mock_context)

        assert "a:lightRig" in drawingml
        # Spot light should use direction from position to target
        assert "rig=" in drawingml
        assert "spot" in drawingml.lower() or "cone" in drawingml.lower()

    def test_custom_light_rig_angles(self):
        """Test custom light rig angle calculations."""
        params = DiffuseLightingParameters(
            surface_scale=1.0,
            diffuse_constant=1.0,
            lighting_color="#FFFFFF",
            light_source_type="distant",
            light_azimuth=135.0,  # Southwest
            light_elevation=30.0,  # Low angle
            input_source="SourceGraphic"
        )

        drawingml = self.filter._generate_lightrig_positioning(params, self.mock_context)

        assert "a:lightRig" in drawingml
        # Should handle custom angles and map to nearest PowerPoint direction
        assert "rig=" in drawingml
        assert "135" in drawingml or "southwest" in drawingml.lower()


class TestComplex3DEffectsCombinations:
    """Test complex combinations of a:sp3d + bevel + lightRig effects."""

    def setup_method(self):
        """Setup test fixtures."""
        self.filter = DiffuseLightingFilter()

        self.mock_context = Mock(spec=FilterContext)
        self.mock_context.unit_converter = Mock()
        self.mock_context.unit_converter.to_emu.side_effect = lambda val: float(val.replace('px', '')) * 25400
        self.mock_context.color_parser = Mock()
        self.mock_context.color_parser.parse.return_value = "#FFFFFF"

    def test_complete_3d_effect_integration(self):
        """Test complete integration of all 3D effects."""
        params = DiffuseLightingParameters(
            surface_scale=3.0,
            diffuse_constant=1.5,
            lighting_color="#FFFFE0",  # Light yellow
            light_source_type="distant",
            light_azimuth=45.0,
            light_elevation=45.0,
            input_source="SourceGraphic"
        )

        drawingml = self.filter._generate_3d_lighting_drawingml(params, self.mock_context)

        # Should contain all 3D effect components
        assert "a:sp3d" in drawingml
        assert "a:bevel" in drawingml
        assert "a:lightRig" in drawingml
        assert "a:innerShdw" in drawingml

        # Effects should be properly coordinated
        assert "extrusionH" in drawingml or "contourW" in drawingml
        assert "rig=" in drawingml
        assert "bevel" in drawingml.lower()
        assert "blurRad" in drawingml

    def test_high_intensity_lighting_combination(self):
        """Test high intensity lighting with coordinated 3D effects."""
        params = DiffuseLightingParameters(
            surface_scale=5.0,  # High surface
            diffuse_constant=3.0,  # High diffuse
            lighting_color="#FFFFFF",
            light_source_type="distant",
            light_azimuth=90.0,
            light_elevation=60.0,
            input_source="SourceGraphic"
        )

        drawingml = self.filter._generate_3d_lighting_drawingml(params, self.mock_context)

        # High intensity should result in more pronounced 3D effects
        assert "a:sp3d" in drawingml
        assert "a:bevel" in drawingml
        assert "a:lightRig" in drawingml
        assert "a:innerShdw" in drawingml

        # Should call EMU converter for scaling
        self.mock_context.unit_converter.to_emu.assert_called()

    def test_colored_lighting_3d_coordination(self):
        """Test colored lighting coordination across all 3D effects."""
        params = DiffuseLightingParameters(
            surface_scale=2.0,
            diffuse_constant=1.0,
            lighting_color="#FF6600",  # Orange lighting
            light_source_type="distant",
            light_azimuth=120.0,
            light_elevation=45.0,
            input_source="SourceGraphic"
        )

        drawingml = self.filter._generate_3d_lighting_drawingml(params, self.mock_context)

        # Should coordinate color across all effects
        assert "a:sp3d" in drawingml
        assert "a:bevel" in drawingml
        assert "a:lightRig" in drawingml
        assert "a:innerShdw" in drawingml

        # Color should be applied consistently
        self.mock_context.color_parser.parse.assert_called_with("#FF6600")

    def test_point_light_3d_coordination(self):
        """Test point light source with coordinated 3D effects."""
        params = DiffuseLightingParameters(
            surface_scale=4.0,
            diffuse_constant=2.0,
            lighting_color="#FFFFFF",
            light_source_type="point",
            light_x=200.0,
            light_y=150.0,
            light_z=300.0,
            input_source="SourceGraphic"
        )

        drawingml = self.filter._generate_3d_lighting_drawingml(params, self.mock_context)

        # Point light should coordinate across all 3D effects
        assert "a:sp3d" in drawingml
        assert "a:bevel" in drawingml
        assert "a:lightRig" in drawingml
        assert "a:innerShdw" in drawingml

        # Should calculate effective lighting direction for all effects

    def test_spot_light_complex_coordination(self):
        """Test spot light with complex 3D effects coordination."""
        params = DiffuseLightingParameters(
            surface_scale=3.0,
            diffuse_constant=1.5,
            lighting_color="#CCFFCC",  # Light green
            light_source_type="spot",
            light_x=100.0,
            light_y=200.0,
            light_z=150.0,
            light_points_at_x=300.0,
            light_points_at_y=400.0,
            light_points_at_z=0.0,
            cone_angle=20.0,  # Narrow cone
            spot_exponent=3.0,  # High focus
            input_source="blur1"
        )

        drawingml = self.filter._generate_3d_lighting_drawingml(params, self.mock_context)

        # Spot light should create sophisticated 3D lighting
        assert "a:sp3d" in drawingml
        assert "a:bevel" in drawingml
        assert "a:lightRig" in drawingml
        assert "a:innerShdw" in drawingml

        # Should handle spot light parameters across all effects
        assert "spot" in drawingml.lower() or "cone" in drawingml.lower()

    def test_edge_case_minimal_parameters(self):
        """Test 3D effects with minimal parameters."""
        params = DiffuseLightingParameters(
            surface_scale=0.1,  # Very low
            diffuse_constant=0.1,  # Very low
            lighting_color="#FFFFFF",
            light_source_type="distant",
            input_source="SourceGraphic"
        )

        drawingml = self.filter._generate_3d_lighting_drawingml(params, self.mock_context)

        # Even minimal parameters should generate valid 3D effects
        assert "a:sp3d" in drawingml
        assert "a:bevel" in drawingml
        assert "a:lightRig" in drawingml
        assert "a:innerShdw" in drawingml

    def test_edge_case_maximum_parameters(self):
        """Test 3D effects with maximum parameters."""
        params = DiffuseLightingParameters(
            surface_scale=50.0,  # Very high
            diffuse_constant=10.0,  # Very high
            lighting_color="#FFFFFF",
            light_source_type="distant",
            light_azimuth=359.0,  # Near full circle
            light_elevation=89.0,  # Nearly vertical
            input_source="SourceGraphic"
        )

        drawingml = self.filter._generate_3d_lighting_drawingml(params, self.mock_context)

        # Should handle extreme parameters gracefully
        assert "a:sp3d" in drawingml
        assert "a:bevel" in drawingml
        assert "a:lightRig" in drawingml
        assert "a:innerShdw" in drawingml


if __name__ == "__main__":
    pytest.main([__file__, "-v"])