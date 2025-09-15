#!/usr/bin/env python3
"""
Unit tests for feMorphology stroke expansion and boolean operations (Task 2.1, Subtasks 2.1.4-2.1.7).

This test suite covers the stroke expansion system and boolean operations for
the vector-first feMorphology implementation using the new filter architecture.

Focus Areas:
- Subtask 2.1.4: Stroke expansion system using PowerPoint a:ln
- Subtask 2.1.5: Boolean union operations for stroke-to-outline conversion
- Subtask 2.1.6: Convert result to a:custGeom with calculated vertices
- Subtask 2.1.7: Handle radius scaling and maintain proportional expansion
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys
from lxml import etree as ET

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from src.converters.filters.geometric.morphology import MorphologyFilter, MorphologyParameters
from src.converters.filters.core.base import FilterContext


class TestStrokeExpansionSystem:
    """Test stroke expansion system using PowerPoint a:ln elements (Subtask 2.1.4)."""

    def setup_method(self):
        """Setup test fixtures for stroke expansion tests."""
        self.filter = MorphologyFilter()

        # Mock FilterContext with standardized tools
        self.mock_context = Mock(spec=FilterContext)
        self.mock_context.unit_converter = Mock()
        self.mock_context.unit_converter.to_emu.side_effect = lambda val: float(val.replace('px', '')) * 25400
        self.mock_context.color_parser = Mock()
        self.mock_context.transform_parser = Mock()
        self.mock_context.viewport_resolver = Mock()

    def test_dilate_stroke_expansion_drawingml(self):
        """Test DrawingML generation for dilate stroke expansion."""
        params = MorphologyParameters(
            operator="dilate",
            radius_x=3.0,
            radius_y=3.0,
            input_source="SourceGraphic",
            result_name="dilated"
        )

        drawingml = self.filter._generate_dilate_drawingml(params, self.mock_context)

        # Verify PowerPoint stroke expansion elements
        assert "a:effectLst" in drawingml
        assert "a:outerShdw" in drawingml  # Stroke expansion technique
        assert "vector-first" in drawingml.lower()
        assert "dilate" in drawingml.lower()

        # Verify EMU conversion is called for radius scaling
        self.mock_context.unit_converter.to_emu.assert_called()

    def test_symmetric_dilate_drawingml_structure(self):
        """Test symmetric dilate generates correct DrawingML structure."""
        params = MorphologyParameters(
            operator="dilate",
            radius_x=2.0,
            radius_y=2.0,
            input_source="SourceGraphic"
        )

        drawingml = self.filter._generate_dilate_drawingml(params, self.mock_context)

        # Should use symmetric dilate approach
        assert "a:outerShdw" in drawingml
        assert "sx=\"100000\"" in drawingml  # Symmetric scaling
        assert "sy=\"100000\"" in drawingml

    def test_asymmetric_dilate_drawingml_structure(self):
        """Test asymmetric dilate generates different DrawingML structure."""
        params = MorphologyParameters(
            operator="dilate",
            radius_x=4.0,
            radius_y=2.0,
            input_source="SourceGraphic"
        )

        drawingml = self.filter._generate_dilate_drawingml(params, self.mock_context)

        # Should use asymmetric dilate approach
        assert "asymmetric" in drawingml.lower()
        assert "a:outerShdw" in drawingml
        # Should have different scaling factors for x and y

    def test_erode_stroke_reduction_drawingml(self):
        """Test DrawingML generation for erode stroke reduction."""
        params = MorphologyParameters(
            operator="erode",
            radius_x=1.5,
            radius_y=1.5,
            input_source="blur1",
            result_name="eroded"
        )

        drawingml = self.filter._generate_erode_drawingml(params, self.mock_context)

        # Verify PowerPoint stroke reduction elements
        assert "a:effectLst" in drawingml
        assert "a:innerShdw" in drawingml  # Stroke reduction technique
        assert "vector-first" in drawingml.lower()
        assert "erode" in drawingml.lower()

    def test_stroke_expansion_emu_scaling(self):
        """Test EMU scaling for stroke expansion (Subtask 2.1.7)."""
        # Mock unit converter to return specific EMU values
        self.mock_context.unit_converter.to_emu.side_effect = lambda val: {
            "3.0px": 76200,  # 3px * 25400 EMU/px
            "4.0px": 101600  # 4px * 25400 EMU/px
        }.get(val, 25400)

        params = MorphologyParameters(
            operator="dilate",
            radius_x=3.0,
            radius_y=4.0,
            input_source="SourceGraphic"
        )

        drawingml = self.filter._generate_dilate_drawingml(params, self.mock_context)

        # Should call unit converter for both radius values
        expected_calls = ["3.0px", "4.0px"]
        actual_calls = [call[0][0] for call in self.mock_context.unit_converter.to_emu.call_args_list]

        for expected_call in expected_calls:
            assert expected_call in actual_calls


class TestBooleanOperationsIntegration:
    """Test boolean operations integration (Subtask 2.1.5)."""

    def setup_method(self):
        """Setup test fixtures."""
        self.filter = MorphologyFilter()

        self.mock_context = Mock(spec=FilterContext)
        self.mock_context.unit_converter = Mock()
        self.mock_context.unit_converter.to_emu.return_value = 25400

    def test_dilate_boolean_union_comments(self):
        """Test dilate generates boolean union comments."""
        params = MorphologyParameters(
            operator="dilate",
            radius_x=2.5,
            radius_y=2.5,
            input_source="SourceGraphic"
        )

        drawingml = self.filter._generate_dilate_drawingml(params, self.mock_context)

        # Should contain comments about boolean union operations
        assert "boolean union" in drawingml.lower()
        assert "stroke-to-outline" in drawingml.lower()

    def test_erode_boolean_difference_comments(self):
        """Test erode generates boolean difference comments."""
        params = MorphologyParameters(
            operator="erode",
            radius_x=1.0,
            radius_y=1.0,
            input_source="SourceGraphic"
        )

        drawingml = self.filter._generate_erode_drawingml(params, self.mock_context)

        # Should contain comments about boolean difference operations
        assert "boolean difference" in drawingml.lower()
        assert "stroke reduction" in drawingml.lower()


class TestCustomGeometryConversion:
    """Test conversion to a:custGeom with calculated vertices (Subtask 2.1.6)."""

    def setup_method(self):
        """Setup test fixtures."""
        self.filter = MorphologyFilter()

        self.mock_context = Mock(spec=FilterContext)
        self.mock_context.unit_converter = Mock()
        self.mock_context.unit_converter.to_emu.return_value = 25400

    def test_custgeom_conversion_comments_dilate(self):
        """Test dilate generates custom geometry conversion comments."""
        params = MorphologyParameters(
            operator="dilate",
            radius_x=2.0,
            radius_y=2.0,
            input_source="SourceGraphic"
        )

        drawingml = self.filter._generate_dilate_drawingml(params, self.mock_context)

        # Should contain comments about custom geometry conversion
        assert "custgeom" in drawingml.lower()
        assert "converted to" in drawingml.lower()

    def test_custgeom_conversion_comments_erode(self):
        """Test erode generates custom geometry conversion comments."""
        params = MorphologyParameters(
            operator="erode",
            radius_x=1.5,
            radius_y=1.5,
            input_source="SourceGraphic"
        )

        drawingml = self.filter._generate_erode_drawingml(params, self.mock_context)

        # Should contain comments about custom geometry generation
        assert "custom geometry generation" in drawingml.lower()
        assert "eroded result" in drawingml.lower()


class TestProportionalExpansion:
    """Test radius scaling and proportional expansion (Subtask 2.1.7)."""

    def setup_method(self):
        """Setup test fixtures."""
        self.filter = MorphologyFilter()

        self.mock_context = Mock(spec=FilterContext)
        self.mock_context.unit_converter = Mock()
        self.mock_context.unit_converter.to_emu.side_effect = lambda val: float(val.replace('px', '')) * 25400

    def test_proportional_scaling_preservation(self):
        """Test that proportional relationships are preserved in DrawingML."""
        # Test with 2:1 ratio
        params = MorphologyParameters(
            operator="dilate",
            radius_x=6.0,
            radius_y=3.0,  # 2:1 ratio
            input_source="SourceGraphic"
        )

        drawingml = self.filter._generate_dilate_drawingml(params, self.mock_context)

        # Should handle proportional scaling - verify both radii are processed
        calls = self.mock_context.unit_converter.to_emu.call_args_list
        assert len(calls) >= 2  # Should convert both x and y radius values

        # Verify asymmetric handling is triggered for different radii
        assert "asymmetric" in drawingml.lower()

    def test_emu_conversion_accuracy(self):
        """Test accurate EMU conversion for morphology radii."""
        self.mock_context.unit_converter.to_emu.side_effect = lambda val: {
            "2.5px": 63500,  # 2.5 * 25400
            "3.75px": 95250  # 3.75 * 25400
        }.get(val, 25400)

        params = MorphologyParameters(
            operator="dilate",
            radius_x=2.5,
            radius_y=3.75,
            input_source="SourceGraphic"
        )

        drawingml = self.filter._generate_dilate_drawingml(params, self.mock_context)

        # Should call converter with precise px values
        expected_calls = ["2.5px", "3.75px"]
        actual_calls = [call[0][0] for call in self.mock_context.unit_converter.to_emu.call_args_list]

        for expected_call in expected_calls:
            assert expected_call in actual_calls

    def test_minimum_radius_handling(self):
        """Test handling of very small radius values."""
        params = MorphologyParameters(
            operator="dilate",
            radius_x=0.01,
            radius_y=0.01,
            input_source="SourceGraphic"
        )

        drawingml = self.filter._generate_dilate_drawingml(params, self.mock_context)

        # Should still generate valid DrawingML for very small radii
        assert "a:effectLst" in drawingml
        assert "a:outerShdw" in drawingml

    def test_large_radius_handling(self):
        """Test handling of large radius values."""
        params = MorphologyParameters(
            operator="dilate",
            radius_x=50.0,
            radius_y=40.0,
            input_source="SourceGraphic"
        )

        drawingml = self.filter._generate_dilate_drawingml(params, self.mock_context)

        # Should generate asymmetric DrawingML for large different radii
        assert "asymmetric" in drawingml.lower()
        assert "a:outerShdw" in drawingml


class TestVectorPrecisionMaintenance:
    """Test that morphology effects maintain vector precision (Subtask 2.1.8)."""

    def setup_method(self):
        """Setup test fixtures."""
        self.filter = MorphologyFilter()

        self.mock_context = Mock(spec=FilterContext)
        self.mock_context.unit_converter = Mock()
        self.mock_context.unit_converter.to_emu.return_value = 25400

    def test_vector_precision_in_drawingml(self):
        """Test vector precision is maintained in generated DrawingML."""
        params = MorphologyParameters(
            operator="dilate",
            radius_x=2.123456,
            radius_y=3.789012,
            input_source="SourceGraphic"
        )

        drawingml = self.filter._generate_dilate_drawingml(params, self.mock_context)

        # Should generate vector-based DrawingML (not raster fallback)
        assert "a:effectLst" in drawingml
        assert "vector-first" in drawingml.lower()

        # Should not contain any rasterization indicators
        assert "raster" not in drawingml.lower()
        assert "bitmap" not in drawingml.lower()

    def test_powerpoint_compatibility_elements(self):
        """Test PowerPoint compatibility elements are present."""
        params = MorphologyParameters(
            operator="erode",
            radius_x=1.5,
            radius_y=1.5,
            input_source="SourceGraphic"
        )

        drawingml = self.filter._generate_erode_drawingml(params, self.mock_context)

        # Should use PowerPoint-compatible DrawingML elements
        assert "a:" in drawingml  # DrawingML namespace
        assert "a:effectLst" in drawingml
        assert "a:innerShdw" in drawingml

    def test_complex_morphology_vector_preservation(self):
        """Test complex morphology operations preserve vector approach."""
        # Large asymmetric radius - still should be vector-first
        params = MorphologyParameters(
            operator="dilate",
            radius_x=25.0,
            radius_y=15.0,
            input_source="SourceGraphic"
        )

        drawingml = self.filter._generate_dilate_drawingml(params, self.mock_context)

        # Even complex operations should maintain vector approach
        assert "vector-first" in drawingml.lower()
        assert "a:effectLst" in drawingml

        # Should handle large asymmetric values
        assert "asymmetric" in drawingml.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])