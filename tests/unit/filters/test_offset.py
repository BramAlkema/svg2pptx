#!/usr/bin/env python3
"""
Tests for OffsetProcessor - SVG feOffset filter implementation.

Validates offset transformation processing with policy integration,
template-based XML generation, and PowerPoint compatibility.
"""

import pytest
import math
from unittest.mock import Mock, MagicMock
from lxml import etree as ET

from core.filters.offset import (
    OffsetProcessor,
    OffsetParameters,
    OffsetFilterException,
    create_offset_processor
)
from core.filters.base import FilterContext, FilterStrategy


class TestOffsetProcessor:
    """Test OffsetProcessor core functionality."""

    def test_processor_initialization(self):
        """Test OffsetProcessor initialization."""
        processor = OffsetProcessor()

        assert processor.filter_type == 'feOffset'
        assert processor.policy is None

        # Test with policy
        policy = Mock()
        processor_with_policy = OffsetProcessor('feOffset', policy)
        assert processor_with_policy.policy == policy

    def test_can_apply_valid_elements(self):
        """Test can_apply with valid feOffset elements."""
        processor = OffsetProcessor()
        context = Mock()

        # Simple feOffset element
        element = ET.Element('feOffset')
        assert processor.can_apply(element, context) is True

        # Namespaced feOffset element
        ns_element = ET.Element('{http://www.w3.org/2000/svg}feOffset')
        assert processor.can_apply(ns_element, context) is True

        # Element with type attribute
        typed_element = ET.Element('filter')
        typed_element.set('type', 'feOffset')
        assert processor.can_apply(typed_element, context) is True

    def test_can_apply_invalid_elements(self):
        """Test can_apply with invalid elements."""
        processor = OffsetProcessor()
        context = Mock()

        # None element
        assert processor.can_apply(None, context) is False

        # Different element type
        other_element = ET.Element('feBlur')
        assert processor.can_apply(other_element, context) is False

        # Element with empty localname (after namespace removal)
        nonsense_element = ET.Element('random')
        assert processor.can_apply(nonsense_element, context) is False

    def test_parse_offset_parameters_basic(self):
        """Test basic offset parameter parsing."""
        processor = OffsetProcessor()

        # Basic offset with dx and dy
        element = ET.Element('feOffset')
        element.set('dx', '5')
        element.set('dy', '3')

        params = processor._parse_offset_parameters(element)

        assert params.dx == 5.0
        assert params.dy == 3.0
        assert params.input_source == 'SourceGraphic'
        assert params.result_name == 'offset'

    def test_parse_offset_parameters_with_attributes(self):
        """Test offset parameter parsing with additional attributes."""
        processor = OffsetProcessor()

        element = ET.Element('feOffset')
        element.set('dx', '10.5')
        element.set('dy', '-7.2')
        element.set('in', 'blur1')
        element.set('result', 'offset1')

        params = processor._parse_offset_parameters(element)

        assert params.dx == 10.5
        assert params.dy == -7.2
        assert params.input_source == 'blur1'
        assert params.result_name == 'offset1'

    def test_parse_offset_parameters_defaults(self):
        """Test offset parameter parsing with defaults."""
        processor = OffsetProcessor()

        # Element with no offset attributes
        element = ET.Element('feOffset')

        params = processor._parse_offset_parameters(element)

        assert params.dx == 0.0
        assert params.dy == 0.0
        assert params.input_source == 'SourceGraphic'
        assert params.result_name == 'offset'

    def test_parse_offset_parameters_invalid(self):
        """Test offset parameter parsing with invalid values."""
        processor = OffsetProcessor()

        # Invalid numeric values
        element = ET.Element('feOffset')
        element.set('dx', 'invalid')
        element.set('dy', '5')

        with pytest.raises(OffsetFilterException, match="Invalid numeric values"):
            processor._parse_offset_parameters(element)

    def test_has_native_support(self):
        """Test native PowerPoint support detection."""
        processor = OffsetProcessor()

        # Small offset - should have native support
        small_params = OffsetParameters(dx=5, dy=3)
        assert processor._has_native_support(small_params) is True

        # Moderate offset - should have native support
        moderate_params = OffsetParameters(dx=30, dy=40)  # magnitude = 50
        assert processor._has_native_support(moderate_params) is True

        # Large offset - should not have native support
        large_params = OffsetParameters(dx=60, dy=80)  # magnitude = 100
        assert processor._has_native_support(large_params) is False

        # Zero offset - should have native support
        zero_params = OffsetParameters(dx=0, dy=0)
        assert processor._has_native_support(zero_params) is True

    def test_is_moderate_offset(self):
        """Test moderate offset detection for transform approximation."""
        processor = OffsetProcessor()

        # Small offset
        small_params = OffsetParameters(dx=10, dy=15)
        assert processor._is_moderate_offset(small_params) is True

        # Moderate offset
        moderate_params = OffsetParameters(dx=120, dy=160)  # magnitude = 200
        assert processor._is_moderate_offset(moderate_params) is True

        # Large offset
        large_params = OffsetParameters(dx=200, dy=300)  # magnitude > 200
        assert processor._is_moderate_offset(large_params) is False

    def test_calculate_displacement_emu(self):
        """Test EMU displacement calculation."""
        processor = OffsetProcessor()
        context = Mock()

        params = OffsetParameters(dx=10, dy=5)
        dx_emu, dy_emu = processor._calculate_displacement_emu(params, context)

        # Verify EMU values are calculated (exact values depend on unit converter)
        assert isinstance(dx_emu, int)
        assert isinstance(dy_emu, int)
        assert dx_emu > 0  # Positive offset
        assert dy_emu > 0  # Positive offset

    def test_get_rendering_strategy_without_policy(self):
        """Test rendering strategy selection without policy engine."""
        processor = OffsetProcessor()  # No policy
        context = Mock()

        # Small offset - should use native
        small_params = OffsetParameters(dx=5, dy=3)
        strategy = processor._get_rendering_strategy(small_params, context)
        assert strategy == FilterStrategy.NATIVE

        # Large offset within moderate range - should use approximation
        moderate_params = OffsetParameters(dx=80, dy=60)
        strategy = processor._get_rendering_strategy(moderate_params, context)
        assert strategy == FilterStrategy.APPROXIMATION

        # Very large offset - should use EMF rasterization
        large_params = OffsetParameters(dx=300, dy=400)
        strategy = processor._get_rendering_strategy(large_params, context)
        assert strategy == FilterStrategy.EMF_RASTERIZE

    def test_get_rendering_strategy_with_policy(self):
        """Test rendering strategy selection with policy engine."""
        mock_policy = Mock()
        mock_policy.decide_filter_strategy.return_value = FilterStrategy.NATIVE

        processor = OffsetProcessor('feOffset', mock_policy)
        context = Mock()
        context.element = ET.Element('feOffset')

        params = OffsetParameters(dx=10, dy=5)
        strategy = processor._get_rendering_strategy(params, context)

        assert strategy == FilterStrategy.NATIVE
        mock_policy.decide_filter_strategy.assert_called_once()

    def test_get_rendering_strategy_policy_failure(self):
        """Test rendering strategy fallback when policy fails."""
        mock_policy = Mock()
        mock_policy.decide_filter_strategy.side_effect = Exception("Policy error")

        processor = OffsetProcessor('feOffset', mock_policy)
        context = Mock()
        context.element = ET.Element('feOffset')

        # Should fall back to default logic when policy fails
        small_params = OffsetParameters(dx=5, dy=3)
        strategy = processor._get_rendering_strategy(small_params, context)
        assert strategy == FilterStrategy.NATIVE

    def test_generate_native_shadow_drawingml(self):
        """Test native PowerPoint shadow DrawingML generation."""
        processor = OffsetProcessor()
        context = Mock()

        params = OffsetParameters(dx=5, dy=3)
        drawingml = processor._generate_native_shadow_drawingml(params, context)

        assert '<a:outerShdw' in drawingml
        assert 'dist=' in drawingml
        assert 'dir=' in drawingml
        assert '<a:srgbClr val="000000">' in drawingml
        assert '<a:alpha val="50000"/>' in drawingml

    def test_generate_native_shadow_drawingml_zero_offset(self):
        """Test native shadow DrawingML for zero offset."""
        processor = OffsetProcessor()
        context = Mock()

        params = OffsetParameters(dx=0, dy=0)
        drawingml = processor._generate_native_shadow_drawingml(params, context)

        assert '<!-- Zero offset: no shadow effect -->' in drawingml

    def test_generate_transform_drawingml(self):
        """Test transform-based DrawingML generation."""
        processor = OffsetProcessor()
        context = Mock()

        params = OffsetParameters(dx=100, dy=75)
        drawingml = processor._generate_transform_drawingml(params, context)

        assert '<a:xfrm>' in drawingml
        assert '<a:off x=' in drawingml
        assert 'y=' in drawingml
        assert 'Transform-based offset' in drawingml

    def test_generate_raster_fallback_drawingml(self):
        """Test EMF rasterization fallback DrawingML."""
        processor = OffsetProcessor()
        context = Mock()

        params = OffsetParameters(dx=500, dy=400)
        drawingml = processor._generate_raster_fallback_drawingml(params, context)

        assert 'EMF rasterization required' in drawingml
        assert '<a:blip>' in drawingml
        assert 'raster-fallback' in drawingml

    def test_validate_parameters_valid(self):
        """Test parameter validation with valid parameters."""
        processor = OffsetProcessor()
        context = Mock()

        element = ET.Element('feOffset')
        element.set('dx', '10')
        element.set('dy', '5')

        assert processor._validate_parameters(element, context) is True

    def test_validate_parameters_invalid(self):
        """Test parameter validation with invalid parameters."""
        processor = OffsetProcessor()
        context = Mock()

        # Invalid dx value
        element = ET.Element('feOffset')
        element.set('dx', 'invalid')
        element.set('dy', '5')

        assert processor._validate_parameters(element, context) is False

    def test_get_processing_method(self):
        """Test processing method description."""
        processor = OffsetProcessor()

        assert processor._get_processing_method(FilterStrategy.NATIVE) == 'Native PowerPoint shadow'
        assert processor._get_processing_method(FilterStrategy.APPROXIMATION) == 'Transform-based positioning'
        assert processor._get_processing_method(FilterStrategy.EMF_RASTERIZE) == 'EMF rasterization fallback'


class TestOffsetProcessorIntegration:
    """Test OffsetProcessor integration with FilterContext."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock FilterContext for testing."""
        context = Mock(spec=FilterContext)
        context.element = ET.Element('feOffset')
        context.viewport = {'width': 100, 'height': 100}
        context.services = Mock()
        return context

    def test_apply_successful_native_processing(self, mock_context):
        """Test successful offset processing with native strategy."""
        processor = OffsetProcessor()

        element = ET.Element('feOffset')
        element.set('dx', '5')
        element.set('dy', '3')

        result = processor.apply(element, mock_context)

        assert result.is_success() is True
        assert result.get_strategy() == FilterStrategy.NATIVE
        assert '<a:outerShdw' in result.get_drawingml()

        metadata = result.get_metadata()
        # Metadata is wrapped by _create_success_result
        inner_metadata = metadata.get('metadata', metadata)
        assert inner_metadata['filter_type'] == 'feOffset'
        assert inner_metadata['dx'] == 5.0
        assert inner_metadata['dy'] == 3.0
        assert inner_metadata['strategy'] == 'native'
        assert inner_metadata['native_support'] is True

    def test_apply_successful_approximation_processing(self, mock_context):
        """Test successful offset processing with approximation strategy."""
        processor = OffsetProcessor()

        element = ET.Element('feOffset')
        element.set('dx', '80')  # Large enough to trigger approximation
        element.set('dy', '60')

        result = processor.apply(element, mock_context)

        assert result.is_success() is True
        assert result.get_strategy() == FilterStrategy.APPROXIMATION
        assert '<a:xfrm>' in result.get_drawingml()

        metadata = result.get_metadata()
        inner_metadata = metadata.get('metadata', metadata)
        assert inner_metadata['strategy'] == 'approximation'
        assert inner_metadata['native_support'] is False

    def test_apply_rasterization_fallback(self, mock_context):
        """Test offset processing with EMF rasterization fallback."""
        processor = OffsetProcessor()

        element = ET.Element('feOffset')
        element.set('dx', '500')  # Very large offset
        element.set('dy', '400')

        result = processor.apply(element, mock_context)

        assert result.is_success() is True
        assert result.get_strategy() == FilterStrategy.EMF_RASTERIZE
        assert 'EMF rasterization required' in result.get_drawingml()

    def test_apply_invalid_parameters(self, mock_context):
        """Test offset processing with invalid parameters."""
        processor = OffsetProcessor()

        element = ET.Element('feOffset')
        element.set('dx', 'invalid')

        result = processor.apply(element, mock_context)

        assert result.is_success() is False
        assert 'Invalid feOffset parameters' in result.get_error_message()

    def test_apply_with_policy_integration(self, mock_context):
        """Test offset processing with policy engine integration."""
        mock_policy = Mock()
        mock_policy.decide_filter_strategy.return_value = FilterStrategy.NATIVE

        processor = OffsetProcessor('feOffset', mock_policy)

        element = ET.Element('feOffset')
        element.set('dx', '10')
        element.set('dy', '8')

        result = processor.apply(element, mock_context)

        assert result.is_success() is True
        assert result.get_strategy() == FilterStrategy.NATIVE
        mock_policy.decide_filter_strategy.assert_called_once()

    def test_apply_metadata_completeness(self, mock_context):
        """Test that apply generates complete metadata."""
        processor = OffsetProcessor()

        element = ET.Element('feOffset')
        element.set('dx', '15')
        element.set('dy', '20')
        element.set('in', 'blur1')
        element.set('result', 'offset1')

        result = processor.apply(element, mock_context)

        metadata = result.get_metadata()
        inner_metadata = metadata.get('metadata', metadata)
        required_fields = [
            'filter_type', 'dx', 'dy', 'input_source', 'result_name',
            'strategy', 'displacement_emu', 'native_support', 'processing_method'
        ]

        for field in required_fields:
            assert field in inner_metadata, f"Missing metadata field: {field}"

        assert inner_metadata['input_source'] == 'blur1'
        assert inner_metadata['result_name'] == 'offset1'


class TestCreateOffsetProcessor:
    """Test create_offset_processor factory function."""

    def test_create_offset_processor_without_policy(self):
        """Test factory function without policy."""
        processor = create_offset_processor()

        assert isinstance(processor, OffsetProcessor)
        assert processor.filter_type == 'feOffset'
        assert processor.policy is None

    def test_create_offset_processor_with_policy(self):
        """Test factory function with policy."""
        policy = Mock()
        processor = create_offset_processor(policy)

        assert isinstance(processor, OffsetProcessor)
        assert processor.policy == policy


class TestOffsetParametersClass:
    """Test OffsetParameters dataclass."""

    def test_offset_parameters_defaults(self):
        """Test OffsetParameters with default values."""
        params = OffsetParameters(dx=5, dy=3)

        assert params.dx == 5
        assert params.dy == 3
        assert params.input_source == "SourceGraphic"
        assert params.result_name == "offset"

    def test_offset_parameters_custom_values(self):
        """Test OffsetParameters with custom values."""
        params = OffsetParameters(
            dx=10.5,
            dy=-7.2,
            input_source="blur1",
            result_name="offset1"
        )

        assert params.dx == 10.5
        assert params.dy == -7.2
        assert params.input_source == "blur1"
        assert params.result_name == "offset1"


if __name__ == '__main__':
    pytest.main([__file__])