#!/usr/bin/env python3
"""
Unit tests for feMorphology stroke-to-outline boolean operations (Task 2.1, Subtask 2.1.2).

This test suite covers the vector-first approach for converting feMorphology
dilate/erode operations to PowerPoint using stroke expansion and boolean operations:
- Stroke expansion using PowerPoint a:ln elements with thick strokes
- Boolean union operations to convert expanded strokes to filled outlines
- Conversion to a:custGeom with calculated path vertices
- Radius scaling and proportional expansion handling
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys
from lxml import etree as ET
import math

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from src.converters.filters.geometric.morphology import MorphologyFilter, MorphologyParameters
from src.converters.filters.core.base import FilterContext
from src.converters.base import ConversionContext
from src.colors import ColorInfo, ColorFormat


class TestStrokeExpansionSystem:
    """Test stroke expansion system using PowerPoint a:ln elements (Subtask 2.1.4)."""

    def setup_method(self):
        """Setup test fixtures for stroke expansion tests."""
        self.filter = MorphologyFilter()

        # Mock standardized tools from filter architecture
        self.mock_context = Mock(spec=FilterContext)
        self.mock_context.unit_converter = Mock()
        self.mock_context.unit_converter.to_emu.return_value = 25400  # 1px = 25400 EMU

        self.mock_context.color_parser = Mock()
        self.mock_context.color_parser.parse.return_value = ColorInfo(0, 0, 0, 1.0, ColorFormat.RGBA, "rgba(0,0,0,1)")

    def test_dilate_stroke_thickness_calculation(self):
        """Test calculation of stroke thickness for dilate operations."""
        params = MorphologyParameters(
            operator="dilate",
            radius_x=3.0,
            radius_y=3.0,
            input_source="SourceGraphic",
            result_name="dilated"
        )

        # Generate DrawingML for dilate operation
        drawingml = self.filter._generate_dilate_drawingml(params, self.mock_context)

        # For dilate, stroke thickness should be 2 * radius (expanding outward)
        # Verify that DrawingML contains stroke expansion elements
        assert "a:effectLst" in drawingml
        assert "a:outerShdw" in drawingml  # PowerPoint stroke expansion technique

        # Verify EMU conversion is used for PowerPoint compatibility
        self.mock_context.unit_converter.to_emu.assert_called()

    def test_asymmetric_dilate_stroke_calculation(self):
        """Test stroke calculation for asymmetric dilate operations."""
        morph_primitive = MorphologyPrimitive(
            type=FilterPrimitiveType.MORPH,
            input="SourceGraphic", result="asymmetric_dilate",
            x=0, y=0, width=1, height=1,
            operator="dilate", radius_x=4.0, radius_y=2.0
        )

        effect = self.converter._convert_primitive_to_effect(morph_primitive, False)

        # Should handle different x and y radius values
        assert effect.parameters["radius_x"] == 4.0
        assert effect.parameters["radius_y"] == 2.0

        # For PowerPoint implementation, this requires special handling
        assert "asymmetric" in effect.parameters.get("morphology_type", "")

    def test_erode_stroke_reduction_calculation(self):
        """Test stroke calculation for erode operations."""
        morph_primitive = MorphologyPrimitive(
            type=FilterPrimitiveType.MORPH,
            input="SourceGraphic", result="eroded",
            x=0, y=0, width=1, height=1,
            operator="erode", radius_x=2.0, radius_y=2.0
        )

        effect = self.converter._convert_primitive_to_effect(morph_primitive, False)

        # Erode reduces the shape, requiring different PowerPoint approach
        assert effect.parameters["operator"] == "erode"
        assert effect.parameters["radius_x"] == 2.0
        assert effect.parameters["radius_y"] == 2.0

    def test_zero_radius_stroke_handling(self):
        """Test stroke handling for zero radius (no-op case)."""
        morph_primitive = MorphologyPrimitive(
            type=FilterPrimitiveType.MORPH,
            input="SourceGraphic", result="no_change",
            x=0, y=0, width=1, height=1,
            operator="dilate", radius_x=0.0, radius_y=0.0
        )

        effect = self.converter._convert_primitive_to_effect(morph_primitive, False)

        # Zero radius should result in minimal or no stroke modification
        assert effect.parameters["radius_x"] == 0.0
        assert effect.parameters["radius_y"] == 0.0
        assert effect.complexity_score < 0.1  # Very low complexity


class TestBooleanUnionOperations:
    """Test boolean union operations for converting expanded strokes to outlines (Subtask 2.1.5)."""

    def setup_method(self):
        """Setup test fixtures for boolean operations tests."""
        self.converter = FilterConverter()

        # Mock the standardized tools
        self.converter.unit_converter = Mock()
        self.converter.unit_converter.to_emu.return_value = 25400

        self.converter.transform_parser = Mock()
        self.converter.viewport_resolver = Mock()

    def test_stroke_to_outline_conversion_interface(self):
        """Test interface for converting expanded strokes to filled outlines."""
        morph_primitive = MorphologyPrimitive(
            type=FilterPrimitiveType.MORPH,
            input="SourceGraphic", result="stroke_converted",
            x=0, y=0, width=1, height=1,
            operator="dilate", radius_x=2.5, radius_y=2.5
        )

        effect = self.converter._convert_primitive_to_effect(morph_primitive, False)

        # Should indicate that stroke-to-outline conversion is needed
        assert "boolean_union" in effect.parameters.get("conversion_type", "") or \
               "stroke_to_outline" in effect.parameters.get("conversion_type", "")

    def test_dilate_union_operation_parameters(self):
        """Test parameters for dilate union operations."""
        morph_primitive = MorphologyPrimitive(
            type=FilterPrimitiveType.MORPH,
            input="SourceGraphic", result="union_dilate",
            x=0, y=0, width=1, height=1,
            operator="dilate", radius_x=3.0, radius_y=4.0
        )

        effect = self.converter._convert_primitive_to_effect(morph_primitive, False)

        # Union operation for dilate should expand the shape
        assert effect.parameters["operator"] == "dilate"
        assert "union_type" in effect.parameters or "boolean_op" in effect.parameters

    def test_erode_difference_operation_parameters(self):
        """Test parameters for erode difference operations."""
        morph_primitive = MorphologyPrimitive(
            type=FilterPrimitiveType.MORPH,
            input="blur1", result="difference_erode",
            x=0, y=0, width=1, height=1,
            operator="erode", radius_x=1.5, radius_y=1.5
        )

        effect = self.converter._convert_primitive_to_effect(morph_primitive, False)

        # Erode operation should use difference/subtraction approach
        assert effect.parameters["operator"] == "erode"
        assert effect.parameters["radius_x"] == 1.5

    def test_complex_boolean_operation_handling(self):
        """Test handling of complex boolean operations for large radius values."""
        morph_primitive = MorphologyPrimitive(
            type=FilterPrimitiveType.MORPH,
            input="SourceGraphic", result="complex_boolean",
            x=0, y=0, width=1, height=1,
            operator="dilate", radius_x=10.0, radius_y=8.0
        )

        effect = self.converter._convert_primitive_to_effect(morph_primitive, False)

        # Large radius values should still use vector approach
        assert not effect.requires_rasterization
        assert effect.complexity_score < 2.5  # Should remain below rasterization threshold


class TestCustomGeometryConversion:
    """Test conversion to a:custGeom with calculated path vertices (Subtask 2.1.6)."""

    def setup_method(self):
        """Setup test fixtures for custom geometry tests."""
        self.converter = FilterConverter()

        # Mock the standardized tools
        self.converter.unit_converter = Mock()
        self.converter.unit_converter.to_emu.return_value = 25400

    def test_custgeom_conversion_parameters(self):
        """Test parameters for a:custGeom conversion."""
        morph_primitive = MorphologyPrimitive(
            type=FilterPrimitiveType.MORPH,
            input="SourceGraphic", result="custom_geom",
            x=0, y=0, width=1, height=1,
            operator="dilate", radius_x=2.0, radius_y=2.0
        )

        effect = self.converter._convert_primitive_to_effect(morph_primitive, False)

        # Should have parameters needed for custom geometry generation
        required_for_custgeom = ["operator", "radius_x", "radius_y"]
        for param in required_for_custgeom:
            assert param in effect.parameters

    def test_path_vertex_calculation_interface(self):
        """Test interface for calculating path vertices from morphology parameters."""
        morph_primitive = MorphologyPrimitive(
            type=FilterPrimitiveType.MORPH,
            input="SourceGraphic", result="vertex_calc",
            x=0, y=0, width=1, height=1,
            operator="dilate", radius_x=3.5, radius_y=2.5
        )

        effect = self.converter._convert_primitive_to_effect(morph_primitive, False)

        # Should indicate that vertex calculation is needed
        assert "path_calculation" in effect.parameters.get("processing_type", "") or \
               "vertex_generation" in effect.parameters.get("processing_type", "")

    def test_asymmetric_custgeom_handling(self):
        """Test custom geometry handling for asymmetric radius values."""
        morph_primitive = MorphologyPrimitive(
            type=FilterPrimitiveType.MORPH,
            input="SourceGraphic", result="asymmetric_custgeom",
            x=0, y=0, width=1, height=1,
            operator="erode", radius_x=4.0, radius_y=1.0
        )

        effect = self.converter._convert_primitive_to_effect(morph_primitive, False)

        # Asymmetric values should be preserved for custom geometry generation
        assert effect.parameters["radius_x"] == 4.0
        assert effect.parameters["radius_y"] == 1.0


class TestRadiusScalingAndProportions:
    """Test radius scaling and proportional expansion handling (Subtask 2.1.7)."""

    def setup_method(self):
        """Setup test fixtures for radius scaling tests."""
        self.converter = FilterConverter()

        # Mock the standardized tools
        self.converter.unit_converter = Mock()
        self.converter.unit_converter.to_emu.side_effect = lambda val: val * 25400

        self.converter.viewport_resolver = Mock()

    def test_radius_emu_conversion(self):
        """Test proper EMU conversion for radius values."""
        morph_primitive = MorphologyPrimitive(
            type=FilterPrimitiveType.MORPH,
            input="SourceGraphic", result="emu_converted",
            x=0, y=0, width=1, height=1,
            operator="dilate", radius_x=2.0, radius_y=3.0
        )

        effect = self.converter._convert_primitive_to_effect(morph_primitive, False)

        # Unit converter should be used for radius values
        assert self.converter.unit_converter.to_emu.called

        # Radius values should be available for EMU conversion
        assert effect.parameters["radius_x"] == 2.0
        assert effect.parameters["radius_y"] == 3.0

    def test_proportional_scaling_maintenance(self):
        """Test that proportional relationships are maintained during scaling."""
        morph_primitive = MorphologyPrimitive(
            type=FilterPrimitiveType.MORPH,
            input="SourceGraphic", result="proportional",
            x=0, y=0, width=1, height=1,
            operator="dilate", radius_x=6.0, radius_y=3.0  # 2:1 ratio
        )

        effect = self.converter._convert_primitive_to_effect(morph_primitive, False)

        # The 2:1 ratio should be preserved in the effect parameters
        x_radius = effect.parameters["radius_x"]
        y_radius = effect.parameters["radius_y"]

        assert x_radius / y_radius == 2.0  # Ratio should be maintained

    def test_scaling_with_viewport_context(self):
        """Test radius scaling with viewport context considerations."""
        # Mock viewport context
        self.converter.viewport_resolver.get_current_viewport.return_value = {
            "viewBox": "0 0 100 100",
            "width": "200",
            "height": "200"
        }

        morph_primitive = MorphologyPrimitive(
            type=FilterPrimitiveType.MORPH,
            input="SourceGraphic", result="viewport_scaled",
            x=0, y=0, width=1, height=1,
            operator="dilate", radius_x=1.0, radius_y=1.0
        )

        effect = self.converter._convert_primitive_to_effect(morph_primitive, False)

        # Should have consistent radius values regardless of viewport scaling
        assert effect.parameters["radius_x"] == 1.0
        assert effect.parameters["radius_y"] == 1.0

    def test_minimum_radius_threshold_handling(self):
        """Test handling of very small radius values."""
        morph_primitive = MorphologyPrimitive(
            type=FilterPrimitiveType.MORPH,
            input="SourceGraphic", result="tiny_radius",
            x=0, y=0, width=1, height=1,
            operator="dilate", radius_x=0.01, radius_y=0.01
        )

        effect = self.converter._convert_primitive_to_effect(morph_primitive, False)

        # Very small radius should still be handled correctly
        assert effect.parameters["radius_x"] == 0.01
        assert effect.parameters["radius_y"] == 0.01
        assert effect.complexity_score < 0.5  # Should be low complexity

    def test_maximum_radius_threshold_handling(self):
        """Test handling of very large radius values."""
        morph_primitive = MorphologyPrimitive(
            type=FilterPrimitiveType.MORPH,
            input="SourceGraphic", result="large_radius",
            x=0, y=0, width=1, height=1,
            operator="dilate", radius_x=50.0, radius_y=40.0
        )

        effect = self.converter._convert_primitive_to_effect(morph_primitive, False)

        # Large radius should increase complexity but still be vector-first
        assert not effect.requires_rasterization
        assert effect.complexity_score > 1.0  # Higher complexity
        assert effect.complexity_score < 2.5  # But still below rasterization threshold


class TestVectorPrecisionVerification:
    """Test verification that morphology effects maintain vector precision (Subtask 2.1.8)."""

    def setup_method(self):
        """Setup test fixtures for vector precision tests."""
        self.converter = FilterConverter()

        # Mock the standardized tools
        self.converter.unit_converter = Mock()
        self.converter.unit_converter.to_emu.return_value = 25400

    def test_vector_precision_maintenance(self):
        """Test that morphology effects maintain vector precision in PowerPoint."""
        morph_primitive = MorphologyPrimitive(
            type=FilterPrimitiveType.MORPH,
            input="SourceGraphic", result="precision_test",
            x=0, y=0, width=1, height=1,
            operator="dilate", radius_x=2.75, radius_y=3.25
        )

        effect = self.converter._convert_primitive_to_effect(morph_primitive, False)

        # Should not require rasterization - maintaining vector precision
        assert not effect.requires_rasterization

        # Fractional radius values should be preserved
        assert effect.parameters["radius_x"] == 2.75
        assert effect.parameters["radius_y"] == 3.25

    def test_powerpoint_compatibility_assurance(self):
        """Test assurance of PowerPoint compatibility for vector morphology."""
        morph_primitive = MorphologyPrimitive(
            type=FilterPrimitiveType.MORPH,
            input="SourceGraphic", result="ppt_compat",
            x=0, y=0, width=1, height=1,
            operator="erode", radius_x=1.5, radius_y=1.5
        )

        effect = self.converter._convert_primitive_to_effect(morph_primitive, False)

        # Should be suitable for PowerPoint vector rendering
        assert effect.effect_type == "morphology"
        assert not effect.requires_rasterization

        # Should use EMU units for PowerPoint compatibility
        self.converter.unit_converter.to_emu.assert_called()

    def test_morphology_chain_precision(self):
        """Test precision maintenance in morphology filter chains."""
        morph1 = MorphologyPrimitive(
            type=FilterPrimitiveType.MORPH,
            input="SourceGraphic", result="step1",
            x=0, y=0, width=1, height=1,
            operator="dilate", radius_x=2.0, radius_y=2.0
        )

        morph2 = MorphologyPrimitive(
            type=FilterPrimitiveType.MORPH,
            input="step1", result="final",
            x=0, y=0, width=1, height=1,
            operator="erode", radius_x=1.0, radius_y=1.0
        )

        effect1 = self.converter._convert_primitive_to_effect(morph1, False)
        effect2 = self.converter._convert_primitive_to_effect(morph2, False)

        # Both operations should maintain vector precision
        assert not effect1.requires_rasterization
        assert not effect2.requires_rasterization

        # Chain should be preserved
        assert morph2.input == "step1"
        assert morph1.result == "step1"

    def test_edge_case_precision_handling(self):
        """Test precision handling for edge cases."""
        # Test with very precise fractional values
        morph_primitive = MorphologyPrimitive(
            type=FilterPrimitiveType.MORPH,
            input="SourceGraphic", result="precise",
            x=0, y=0, width=1, height=1,
            operator="dilate", radius_x=1.123456, radius_y=2.987654
        )

        effect = self.converter._convert_primitive_to_effect(morph_primitive, False)

        # Should maintain precision without rasterization
        assert not effect.requires_rasterization
        assert abs(effect.parameters["radius_x"] - 1.123456) < 1e-6
        assert abs(effect.parameters["radius_y"] - 2.987654) < 1e-6


if __name__ == "__main__":
    pytest.main([__file__, "-v"])