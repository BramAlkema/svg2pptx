#!/usr/bin/env python3
"""
Unit tests for feMorphology Vector-First Filter Implementation (Task 2.1).

This test suite verifies the vector-first approach for feMorphology effects,
testing the new MorphologyFilter class that replaces rasterization with
PowerPoint vector elements for better scalability and visual quality.

Task 2.1 Subtasks Tested:
- Subtask 2.1.1: feMorphology parsing (dilate/erode operations)
- Subtask 2.1.2: Stroke-to-outline boolean operations
- Subtask 2.1.3: feMorphology parser with operation and radius extraction
- Subtask 2.1.4: Stroke expansion system using PowerPoint a:ln
- Subtask 2.1.5: Boolean union operations for stroke-to-outline conversion
- Subtask 2.1.6: Convert result to a:custGeom with calculated vertices
- Subtask 2.1.7: Handle radius scaling and proportional expansion
- Subtask 2.1.8: Verify morphology effects maintain vector precision
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys
from lxml import etree as ET

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from src.converters.filters.geometric.morphology import MorphologyFilter, MorphologyParameters
from src.converters.filters.core.base import FilterContext, FilterResult


class TestMorphologyFilterBasics:
    """Test basic functionality of MorphologyFilter class."""

    def setup_method(self):
        """Setup test fixtures."""
        self.filter = MorphologyFilter()

        # Create mock context with standardized tools
        self.mock_context = Mock(spec=FilterContext)
        self.mock_context.unit_converter = Mock()
        self.mock_context.unit_converter.to_emu.return_value = 25400  # 1px = 25400 EMU
        self.mock_context.color_parser = Mock()
        self.mock_context.transform_parser = Mock()
        self.mock_context.viewport_resolver = Mock()

    def test_filter_initialization(self):
        """Test MorphologyFilter initialization."""
        assert self.filter.filter_type == "morphology"
        assert self.filter.strategy == "vector_first"
        assert self.filter.complexity_threshold == 2.5

    def test_can_apply_femorphology_element(self):
        """Test can_apply method with feMorphology elements."""
        morph_element = ET.Element("feMorphology")
        assert self.filter.can_apply(morph_element, self.mock_context) is True

    def test_can_apply_femorphology_namespaced(self):
        """Test can_apply method with namespaced feMorphology elements."""
        morph_element = ET.Element("{http://www.w3.org/2000/svg}feMorphology")
        assert self.filter.can_apply(morph_element, self.mock_context) is True

    def test_can_apply_other_elements(self):
        """Test can_apply method with non-morphology elements."""
        blur_element = ET.Element("feGaussianBlur")
        assert self.filter.can_apply(blur_element, self.mock_context) is False

    def test_can_apply_none_element(self):
        """Test can_apply method with None element."""
        assert self.filter.can_apply(None, self.mock_context) is False


class TestMorphologyParameterParsing:
    """Test morphology parameter parsing (Subtask 2.1.3)."""

    def setup_method(self):
        """Setup test fixtures."""
        self.filter = MorphologyFilter()

    def test_parse_dilate_parameters(self):
        """Test parsing dilate operation parameters."""
        morph_element = ET.Element("feMorphology")
        morph_element.set("operator", "dilate")
        morph_element.set("radius", "2 3")
        morph_element.set("in", "SourceGraphic")
        morph_element.set("result", "dilated")

        params = self.filter._parse_morphology_parameters(morph_element)

        assert params.operator == "dilate"
        assert params.radius_x == 2.0
        assert params.radius_y == 3.0
        assert params.input_source == "SourceGraphic"
        assert params.result_name == "dilated"

    def test_parse_erode_parameters(self):
        """Test parsing erode operation parameters."""
        morph_element = ET.Element("feMorphology")
        morph_element.set("operator", "erode")
        morph_element.set("radius", "1.5")
        morph_element.set("in", "blur1")

        params = self.filter._parse_morphology_parameters(morph_element)

        assert params.operator == "erode"
        assert params.radius_x == 1.5
        assert params.radius_y == 1.5  # Single value applies to both
        assert params.input_source == "blur1"
        assert params.result_name is None

    def test_parse_default_parameters(self):
        """Test parsing with default parameter values."""
        morph_element = ET.Element("feMorphology")
        # No attributes set - should use defaults

        params = self.filter._parse_morphology_parameters(morph_element)

        assert params.operator == "erode"  # Default operator
        assert params.radius_x == 0.0
        assert params.radius_y == 0.0
        assert params.input_source == "SourceGraphic"
        assert params.result_name is None

    def test_parse_invalid_radius_values(self):
        """Test parsing with invalid radius values."""
        morph_element = ET.Element("feMorphology")
        morph_element.set("radius", "invalid")

        params = self.filter._parse_morphology_parameters(morph_element)

        # Should default to 0 for invalid values
        assert params.radius_x == 0.0
        assert params.radius_y == 0.0

    def test_parse_large_radius_values(self):
        """Test parsing with large radius values."""
        morph_element = ET.Element("feMorphology")
        morph_element.set("radius", "10.5 15.75")

        params = self.filter._parse_morphology_parameters(morph_element)

        assert params.radius_x == 10.5
        assert params.radius_y == 15.75


class TestParameterValidation:
    """Test parameter validation."""

    def setup_method(self):
        """Setup test fixtures."""
        self.filter = MorphologyFilter()
        self.mock_context = Mock(spec=FilterContext)

    def test_validate_valid_dilate_parameters(self):
        """Test validation of valid dilate parameters."""
        morph_element = ET.Element("feMorphology")
        morph_element.set("operator", "dilate")
        morph_element.set("radius", "2.5 3.0")

        assert self.filter.validate_parameters(morph_element, self.mock_context) is True

    def test_validate_valid_erode_parameters(self):
        """Test validation of valid erode parameters."""
        morph_element = ET.Element("feMorphology")
        morph_element.set("operator", "erode")
        morph_element.set("radius", "1.0")

        assert self.filter.validate_parameters(morph_element, self.mock_context) is True

    def test_validate_invalid_operator(self):
        """Test validation with invalid operator."""
        morph_element = ET.Element("feMorphology")
        morph_element.set("operator", "unknown")
        morph_element.set("radius", "2.0")

        assert self.filter.validate_parameters(morph_element, self.mock_context) is False

    def test_validate_negative_radius(self):
        """Test validation with negative radius values."""
        morph_element = ET.Element("feMorphology")
        morph_element.set("operator", "dilate")
        morph_element.set("radius", "-1.0")

        assert self.filter.validate_parameters(morph_element, self.mock_context) is False


class TestComplexityCalculation:
    """Test complexity calculation for strategy decisions."""

    def setup_method(self):
        """Setup test fixtures."""
        self.filter = MorphologyFilter()

    def test_zero_radius_complexity(self):
        """Test complexity for zero radius (no-op case)."""
        params = MorphologyParameters(
            operator="dilate",
            radius_x=0.0,
            radius_y=0.0,
            input_source="SourceGraphic"
        )

        complexity = self.filter._calculate_complexity(params)
        assert complexity == 0.0

    def test_small_radius_complexity(self):
        """Test complexity for small radius values."""
        params = MorphologyParameters(
            operator="dilate",
            radius_x=2.0,
            radius_y=2.0,
            input_source="SourceGraphic"
        )

        complexity = self.filter._calculate_complexity(params)
        assert 0.0 < complexity < 1.0

    def test_large_radius_complexity(self):
        """Test complexity for large radius values."""
        params = MorphologyParameters(
            operator="dilate",
            radius_x=15.0,
            radius_y=15.0,
            input_source="SourceGraphic"
        )

        complexity = self.filter._calculate_complexity(params)
        assert complexity > 1.0

    def test_asymmetric_radius_complexity(self):
        """Test complexity for asymmetric radius values."""
        params = MorphologyParameters(
            operator="dilate",
            radius_x=5.0,
            radius_y=2.0,
            input_source="SourceGraphic"
        )

        complexity = self.filter._calculate_complexity(params)

        # Should be higher than symmetric case
        symmetric_params = MorphologyParameters(
            operator="dilate",
            radius_x=3.5,
            radius_y=3.5,
            input_source="SourceGraphic"
        )
        symmetric_complexity = self.filter._calculate_complexity(symmetric_params)

        assert complexity > symmetric_complexity


class TestVectorFirstApplication:
    """Test vector-first morphology application (Subtasks 2.1.4-2.1.8)."""

    def setup_method(self):
        """Setup test fixtures."""
        self.filter = MorphologyFilter()

        # Mock context with standardized tools
        self.mock_context = Mock(spec=FilterContext)
        self.mock_context.unit_converter = Mock()
        self.mock_context.unit_converter.to_emu.side_effect = lambda val: float(val.replace('px', '')) * 25400
        self.mock_context.color_parser = Mock()
        self.mock_context.transform_parser = Mock()
        self.mock_context.viewport_resolver = Mock()

    def test_apply_dilate_operation(self):
        """Test applying dilate operation with vector-first approach."""
        morph_element = ET.Element("feMorphology")
        morph_element.set("operator", "dilate")
        morph_element.set("radius", "2.0")
        morph_element.set("result", "dilated")

        result = self.filter.apply(morph_element, self.mock_context)

        assert result.success is True
        assert "dilate" in result.drawingml.lower()
        assert result.metadata['strategy'] == 'vector_first'
        assert result.metadata['operator'] == 'dilate'
        assert result.metadata['radius_x'] == 2.0

    def test_apply_erode_operation(self):
        """Test applying erode operation with vector-first approach."""
        morph_element = ET.Element("feMorphology")
        morph_element.set("operator", "erode")
        morph_element.set("radius", "1.5 2.0")
        morph_element.set("result", "eroded")

        result = self.filter.apply(morph_element, self.mock_context)

        assert result.success is True
        assert "erode" in result.drawingml.lower()
        assert result.metadata['strategy'] == 'vector_first'
        assert result.metadata['operator'] == 'erode'
        assert result.metadata['radius_x'] == 1.5
        assert result.metadata['radius_y'] == 2.0

    def test_apply_zero_radius_optimization(self):
        """Test zero radius optimization (no-op case)."""
        morph_element = ET.Element("feMorphology")
        morph_element.set("operator", "dilate")
        morph_element.set("radius", "0")

        result = self.filter.apply(morph_element, self.mock_context)

        assert result.success is True
        assert "no-op" in result.drawingml.lower()
        assert result.metadata['strategy'] == 'no_op'
        assert result.metadata['complexity'] == 0.0

    def test_stroke_expansion_emu_conversion(self):
        """Test stroke expansion with EMU conversion (Subtask 2.1.7)."""
        morph_element = ET.Element("feMorphology")
        morph_element.set("operator", "dilate")
        morph_element.set("radius", "3.0")

        result = self.filter.apply(morph_element, self.mock_context)

        # Verify unit converter was called for EMU conversion
        self.mock_context.unit_converter.to_emu.assert_called()
        assert result.success is True

    def test_asymmetric_radius_handling(self):
        """Test handling of asymmetric radius values."""
        morph_element = ET.Element("feMorphology")
        morph_element.set("operator", "dilate")
        morph_element.set("radius", "4.0 2.0")

        result = self.filter.apply(morph_element, self.mock_context)

        assert result.success is True
        assert result.metadata['radius_x'] == 4.0
        assert result.metadata['radius_y'] == 2.0
        assert "asymmetric" in result.drawingml.lower()

    def test_vector_precision_maintenance(self):
        """Test that morphology maintains vector precision (Subtask 2.1.8)."""
        morph_element = ET.Element("feMorphology")
        morph_element.set("operator", "dilate")
        morph_element.set("radius", "2.123456")

        result = self.filter.apply(morph_element, self.mock_context)

        assert result.success is True
        # Should maintain precision in metadata
        assert abs(result.metadata['radius_x'] - 2.123456) < 1e-6
        assert result.metadata['strategy'] == 'vector_first'  # Not rasterized

    def test_complex_morphology_still_vector_first(self):
        """Test that even complex morphology uses vector-first approach."""
        morph_element = ET.Element("feMorphology")
        morph_element.set("operator", "dilate")
        morph_element.set("radius", "20.0 15.0")  # Large, complex radius

        result = self.filter.apply(morph_element, self.mock_context)

        assert result.success is True
        assert result.metadata['strategy'] == 'vector_first'  # Should still be vector-first
        assert result.metadata['complexity'] > 1.0  # High complexity
        assert "vector-first" in result.drawingml.lower()


class TestDrawingMLGeneration:
    """Test PowerPoint DrawingML generation (Subtasks 2.1.4-2.1.6)."""

    def setup_method(self):
        """Setup test fixtures."""
        self.filter = MorphologyFilter()

        # Mock context
        self.mock_context = Mock(spec=FilterContext)
        self.mock_context.unit_converter = Mock()
        self.mock_context.unit_converter.to_emu.side_effect = lambda val: float(val.replace('px', '')) * 25400

    def test_dilate_drawingml_structure(self):
        """Test structure of generated DrawingML for dilate operations."""
        params = MorphologyParameters(
            operator="dilate",
            radius_x=2.0,
            radius_y=2.0,
            input_source="SourceGraphic",
            result_name="dilated"
        )

        drawingml = self.filter._generate_dilate_drawingml(params, self.mock_context)

        # Should contain PowerPoint effect elements
        assert "a:effectLst" in drawingml
        assert "a:outerShdw" in drawingml  # Stroke expansion technique
        assert "dilate" in drawingml.lower()
        assert "vector-first" in drawingml.lower()

    def test_erode_drawingml_structure(self):
        """Test structure of generated DrawingML for erode operations."""
        params = MorphologyParameters(
            operator="erode",
            radius_x=1.5,
            radius_y=1.5,
            input_source="SourceGraphic",
            result_name="eroded"
        )

        drawingml = self.filter._generate_erode_drawingml(params, self.mock_context)

        # Should contain PowerPoint effect elements for erode
        assert "a:effectLst" in drawingml
        assert "a:innerShdw" in drawingml  # Stroke reduction technique
        assert "erode" in drawingml.lower()
        assert "vector-first" in drawingml.lower()

    def test_symmetric_vs_asymmetric_dilate(self):
        """Test different DrawingML for symmetric vs asymmetric dilate."""
        # Symmetric dilate
        symmetric_params = MorphologyParameters(
            operator="dilate",
            radius_x=2.0,
            radius_y=2.0,
            input_source="SourceGraphic"
        )

        symmetric_drawingml = self.filter._generate_dilate_drawingml(symmetric_params, self.mock_context)

        # Asymmetric dilate
        asymmetric_params = MorphologyParameters(
            operator="dilate",
            radius_x=4.0,
            radius_y=2.0,
            input_source="SourceGraphic"
        )

        asymmetric_drawingml = self.filter._generate_dilate_drawingml(asymmetric_params, self.mock_context)

        # Should generate different DrawingML
        assert symmetric_drawingml != asymmetric_drawingml
        assert "asymmetric" in asymmetric_drawingml.lower()


class TestErrorHandling:
    """Test error handling and edge cases."""

    def setup_method(self):
        """Setup test fixtures."""
        self.filter = MorphologyFilter()
        self.mock_context = Mock(spec=FilterContext)

    def test_apply_invalid_element(self):
        """Test applying filter to invalid element."""
        invalid_element = ET.Element("feGaussianBlur")  # Not feMorphology

        result = self.filter.apply(invalid_element, self.mock_context)

        # Should still process but may not be optimal
        assert isinstance(result, FilterResult)

    def test_apply_with_exception(self):
        """Test handling of exceptions during apply."""
        morph_element = ET.Element("feMorphology")
        morph_element.set("operator", "dilate")

        # Mock unit converter to raise exception
        self.mock_context.unit_converter = Mock()
        self.mock_context.unit_converter.to_emu.side_effect = Exception("Unit conversion failed")

        result = self.filter.apply(morph_element, self.mock_context)

        # Filter should gracefully handle unit conversion errors with fallback
        assert result.success is True  # Graceful degradation
        assert "no-op" in result.drawingml.lower()  # Fallback behavior
        assert result.metadata['radius_x'] == 0.0  # Safe fallback values


if __name__ == "__main__":
    pytest.main([__file__, "-v"])