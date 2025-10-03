#!/usr/bin/env python3
"""
Tests for FloodProcessor - SVG feFlood filter implementation.

Validates flood fill processing with Color system integration,
policy-driven strategy selection, and PowerPoint compatibility.
"""

import pytest
from unittest.mock import Mock, MagicMock
from lxml import etree as ET

from core.filters.flood import (
    FloodProcessor,
    FloodParameters,
    FloodFilterException,
    create_flood_processor
)
from core.filters.base import FilterContext, FilterStrategy


class TestFloodProcessor:
    """Test FloodProcessor core functionality."""

    def test_processor_initialization(self):
        """Test FloodProcessor initialization."""
        processor = FloodProcessor()

        assert processor.filter_type == 'feFlood'
        assert processor.policy is None

        # Test with policy
        policy = Mock()
        processor_with_policy = FloodProcessor('feFlood', policy)
        assert processor_with_policy.policy == policy

    def test_can_apply_valid_elements(self):
        """Test can_apply with valid feFlood elements."""
        processor = FloodProcessor()
        context = Mock()

        # Simple feFlood element
        element = ET.Element('feFlood')
        assert processor.can_apply(element, context) is True

        # Namespaced feFlood element
        ns_element = ET.Element('{http://www.w3.org/2000/svg}feFlood')
        assert processor.can_apply(ns_element, context) is True

        # Element with type attribute
        typed_element = ET.Element('filter')
        typed_element.set('type', 'feFlood')
        assert processor.can_apply(typed_element, context) is True

    def test_can_apply_invalid_elements(self):
        """Test can_apply with invalid elements."""
        processor = FloodProcessor()
        context = Mock()

        # None element
        assert processor.can_apply(None, context) is False

        # Different element type
        other_element = ET.Element('feBlur')
        assert processor.can_apply(other_element, context) is False

        # Unrelated element
        random_element = ET.Element('rect')
        assert processor.can_apply(random_element, context) is False

    def test_parse_flood_parameters_basic(self):
        """Test basic flood parameter parsing."""
        processor = FloodProcessor()
        context = Mock()

        # Basic flood with color and opacity
        element = ET.Element('feFlood')
        element.set('flood-color', '#FF0000')
        element.set('flood-opacity', '0.8')

        params = processor._parse_flood_parameters(element, context)

        assert params.flood_color == '#FF0000'
        assert params.flood_opacity == 0.8
        assert params.input_source == 'SourceGraphic'
        assert params.result_name == 'flood'

    def test_parse_flood_parameters_with_attributes(self):
        """Test flood parameter parsing with additional attributes."""
        processor = FloodProcessor()
        context = Mock()

        element = ET.Element('feFlood')
        element.set('flood-color', 'blue')
        element.set('flood-opacity', '0.5')
        element.set('in', 'blur1')
        element.set('result', 'flood1')

        params = processor._parse_flood_parameters(element, context)

        assert params.flood_color == 'blue'
        assert params.flood_opacity == 0.5
        assert params.input_source == 'blur1'
        assert params.result_name == 'flood1'

    def test_parse_flood_parameters_defaults(self):
        """Test flood parameter parsing with defaults."""
        processor = FloodProcessor()
        context = Mock()

        # Element with no flood attributes
        element = ET.Element('feFlood')

        params = processor._parse_flood_parameters(element, context)

        assert params.flood_color == 'black'
        assert params.flood_opacity == 1.0
        assert params.input_source == 'SourceGraphic'
        assert params.result_name == 'flood'

    def test_parse_flood_parameters_opacity_clamping(self):
        """Test flood opacity clamping to valid range."""
        processor = FloodProcessor()
        context = Mock()

        # Test opacity > 1.0
        element1 = ET.Element('feFlood')
        element1.set('flood-opacity', '1.5')

        params1 = processor._parse_flood_parameters(element1, context)
        assert params1.flood_opacity == 1.0

        # Test opacity < 0.0
        element2 = ET.Element('feFlood')
        element2.set('flood-opacity', '-0.2')

        params2 = processor._parse_flood_parameters(element2, context)
        assert params2.flood_opacity == 0.0

    def test_parse_flood_parameters_invalid_opacity(self):
        """Test flood parameter parsing with invalid opacity."""
        processor = FloodProcessor()
        context = Mock()

        # Invalid opacity value
        element = ET.Element('feFlood')
        element.set('flood-opacity', 'invalid')

        with pytest.raises(FloodFilterException, match="Invalid flood-opacity value"):
            processor._parse_flood_parameters(element, context)

    def test_is_simple_color(self):
        """Test simple color detection."""
        processor = FloodProcessor()

        # Named colors
        assert processor._is_simple_color('black') is True
        assert processor._is_simple_color('red') is True
        assert processor._is_simple_color('WHITE') is True

        # Hex colors
        assert processor._is_simple_color('#FF0000') is True
        assert processor._is_simple_color('#F00') is True

        # RGB colors
        assert processor._is_simple_color('rgb(255, 0, 0)') is True

        # Complex expressions
        assert processor._is_simple_color('currentColor') is False
        assert processor._is_simple_color('inherit') is False

    def test_get_color_complexity(self):
        """Test color complexity assessment."""
        processor = FloodProcessor()

        assert processor._get_color_complexity('#FF0000') == 'simple'
        assert processor._get_color_complexity('red') == 'simple'
        assert processor._get_color_complexity('rgb(255, 0, 0)') == 'moderate'  # RGB is moderate complexity
        assert processor._get_color_complexity('hsl(0, 100%, 50%)') == 'moderate'
        assert processor._get_color_complexity('currentColor') == 'complex'

    def test_get_color_format(self):
        """Test color format detection."""
        processor = FloodProcessor()

        assert processor._get_color_format('#FF0000') == 'hex'
        assert processor._get_color_format('red') == 'named'
        assert processor._get_color_format('rgb(255, 0, 0)') == 'rgb'
        assert processor._get_color_format('hsl(0, 100%, 50%)') == 'hsl'
        assert processor._get_color_format('currentColor') == 'other'

    def test_parse_color_fallback(self):
        """Test fallback color parsing."""
        processor = FloodProcessor()

        # Named colors
        assert processor._parse_color_fallback('black') == '000000'
        assert processor._parse_color_fallback('white') == 'FFFFFF'
        assert processor._parse_color_fallback('red') == 'FF0000'

        # Hex colors
        assert processor._parse_color_fallback('#FF0000') == 'FF0000'
        assert processor._parse_color_fallback('#F00') == 'FF0000'

        # Unknown colors
        assert processor._parse_color_fallback('unknown') == '000000'

    def test_get_rendering_strategy_without_policy(self):
        """Test rendering strategy selection without policy engine."""
        processor = FloodProcessor()  # No policy
        context = Mock()

        # Simple color - should use native
        simple_params = FloodParameters(flood_color='red', flood_opacity=1.0)
        strategy = processor._get_rendering_strategy(simple_params, context)
        assert strategy == FilterStrategy.NATIVE

        # Complex color - should use approximation
        complex_params = FloodParameters(flood_color='currentColor', flood_opacity=0.5)
        strategy = processor._get_rendering_strategy(complex_params, context)
        assert strategy == FilterStrategy.APPROXIMATION

    def test_get_rendering_strategy_with_policy(self):
        """Test rendering strategy selection with policy engine."""
        mock_policy = Mock()
        mock_policy.decide_filter_strategy.return_value = FilterStrategy.NATIVE

        processor = FloodProcessor('feFlood', mock_policy)
        context = Mock()
        context.element = ET.Element('feFlood')

        params = FloodParameters(flood_color='blue', flood_opacity=0.8)
        strategy = processor._get_rendering_strategy(params, context)

        assert strategy == FilterStrategy.NATIVE
        mock_policy.decide_filter_strategy.assert_called_once()

    def test_get_rendering_strategy_policy_failure(self):
        """Test rendering strategy fallback when policy fails."""
        mock_policy = Mock()
        mock_policy.decide_filter_strategy.side_effect = Exception("Policy error")

        processor = FloodProcessor('feFlood', mock_policy)
        context = Mock()
        context.element = ET.Element('feFlood')

        # Should fall back to default logic when policy fails
        simple_params = FloodParameters(flood_color='green', flood_opacity=1.0)
        strategy = processor._get_rendering_strategy(simple_params, context)
        assert strategy == FilterStrategy.NATIVE

    def test_generate_native_flood_drawingml(self):
        """Test native PowerPoint flood fill DrawingML generation."""
        processor = FloodProcessor()
        context = Mock()

        # Test with fully opaque color
        params = FloodParameters(flood_color='#FF0000', flood_opacity=1.0)
        drawingml = processor._generate_native_flood_drawingml(params, context)

        assert '<a:solidFill>' in drawingml
        assert '<a:srgbClr val="FF0000"/>' in drawingml
        assert '<a:alpha' not in drawingml  # No alpha for fully opaque

    def test_generate_native_flood_drawingml_with_alpha(self):
        """Test native flood DrawingML with transparency."""
        processor = FloodProcessor()
        context = Mock()

        # Test with semi-transparent color
        params = FloodParameters(flood_color='blue', flood_opacity=0.5)
        drawingml = processor._generate_native_flood_drawingml(params, context)

        assert '<a:solidFill>' in drawingml
        assert '<a:srgbClr val=' in drawingml
        assert '<a:alpha val="50000"/>' in drawingml

    def test_generate_native_flood_drawingml_color_parsing_failure(self):
        """Test native flood DrawingML with color parsing failure."""
        processor = FloodProcessor()
        context = Mock()

        # Test with invalid color that causes parsing failure
        params = FloodParameters(flood_color='invalid-color', flood_opacity=0.8)
        drawingml = processor._generate_native_flood_drawingml(params, context)

        # Should fall back to black
        assert '<a:solidFill>' in drawingml
        assert '<a:srgbClr val="000000">' in drawingml
        assert '<a:alpha val="80000"/>' in drawingml

    def test_generate_approximation_flood_drawingml(self):
        """Test approximation flood DrawingML generation."""
        processor = FloodProcessor()
        context = Mock()

        params = FloodParameters(flood_color='currentColor', flood_opacity=0.7)
        drawingml = processor._generate_approximation_flood_drawingml(params, context)

        assert 'Approximated flood color' in drawingml
        assert '<a:solidFill>' in drawingml
        assert '<a:alpha val="70000"/>' in drawingml

    def test_generate_raster_fallback_drawingml(self):
        """Test EMF rasterization fallback DrawingML."""
        processor = FloodProcessor()
        context = Mock()

        params = FloodParameters(flood_color='complex-expression', flood_opacity=0.9)
        drawingml = processor._generate_raster_fallback_drawingml(params, context)

        assert 'EMF rasterization required' in drawingml
        assert '<a:blip>' in drawingml
        assert 'raster-fallback' in drawingml

    def test_validate_parameters_valid(self):
        """Test parameter validation with valid parameters."""
        processor = FloodProcessor()
        context = Mock()

        element = ET.Element('feFlood')
        element.set('flood-color', 'red')
        element.set('flood-opacity', '0.8')

        assert processor._validate_parameters(element, context) is True

    def test_validate_parameters_invalid_opacity(self):
        """Test parameter validation with invalid opacity."""
        processor = FloodProcessor()
        context = Mock()

        # Opacity out of range
        element = ET.Element('feFlood')
        element.set('flood-opacity', '1.5')  # Will be clamped, so should be valid

        # The validation happens after clamping, so this should be valid
        assert processor._validate_parameters(element, context) is True

    def test_validate_parameters_parsing_failure(self):
        """Test parameter validation with parsing failure."""
        processor = FloodProcessor()
        context = Mock()

        # Invalid opacity that causes parsing exception
        element = ET.Element('feFlood')
        element.set('flood-opacity', 'invalid')

        assert processor._validate_parameters(element, context) is False

    def test_get_processing_method(self):
        """Test processing method description."""
        processor = FloodProcessor()

        assert processor._get_processing_method(FilterStrategy.NATIVE) == 'Native PowerPoint solid fill'
        assert processor._get_processing_method(FilterStrategy.APPROXIMATION) == 'Approximated color parsing'
        assert processor._get_processing_method(FilterStrategy.EMF_RASTERIZE) == 'EMF rasterization fallback'


class TestFloodProcessorIntegration:
    """Test FloodProcessor integration with FilterContext."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock FilterContext for testing."""
        context = Mock(spec=FilterContext)
        context.element = ET.Element('feFlood')
        context.viewport = {'width': 100, 'height': 100}
        context.services = Mock()
        return context

    def test_apply_successful_native_processing(self, mock_context):
        """Test successful flood processing with native strategy."""
        processor = FloodProcessor()

        element = ET.Element('feFlood')
        element.set('flood-color', '#FF0000')
        element.set('flood-opacity', '0.8')

        result = processor.apply(element, mock_context)

        assert result.is_success() is True
        assert result.get_strategy() == FilterStrategy.NATIVE
        assert '<a:solidFill>' in result.get_drawingml()
        assert 'FF0000' in result.get_drawingml()

        metadata = result.get_metadata()
        inner_metadata = metadata.get('metadata', metadata)
        assert inner_metadata['filter_type'] == 'feFlood'
        assert inner_metadata['flood_color'] == '#FF0000'
        assert inner_metadata['flood_opacity'] == 0.8
        assert inner_metadata['strategy'] == 'native'
        assert inner_metadata['color_format'] == 'hex'
        assert inner_metadata['has_transparency'] is True

    def test_apply_successful_approximation_processing(self, mock_context):
        """Test successful flood processing with approximation strategy."""
        processor = FloodProcessor()

        element = ET.Element('feFlood')
        element.set('flood-color', 'currentColor')  # Complex color
        element.set('flood-opacity', '1.0')

        result = processor.apply(element, mock_context)

        assert result.is_success() is True
        assert result.get_strategy() == FilterStrategy.APPROXIMATION
        assert 'Approximated flood color' in result.get_drawingml()

        metadata = result.get_metadata()
        inner_metadata = metadata.get('metadata', metadata)
        assert inner_metadata['strategy'] == 'approximation'
        assert inner_metadata['color_format'] == 'other'
        assert inner_metadata['has_transparency'] is False

    def test_apply_invalid_parameters(self, mock_context):
        """Test flood processing with invalid parameters."""
        processor = FloodProcessor()

        element = ET.Element('feFlood')
        element.set('flood-opacity', 'invalid')

        result = processor.apply(element, mock_context)

        assert result.is_success() is False
        assert 'Invalid feFlood parameters' in result.get_error_message()

    def test_apply_with_policy_integration(self, mock_context):
        """Test flood processing with policy engine integration."""
        mock_policy = Mock()
        mock_policy.decide_filter_strategy.return_value = FilterStrategy.NATIVE

        processor = FloodProcessor('feFlood', mock_policy)

        element = ET.Element('feFlood')
        element.set('flood-color', 'blue')
        element.set('flood-opacity', '0.5')

        result = processor.apply(element, mock_context)

        assert result.is_success() is True
        assert result.get_strategy() == FilterStrategy.NATIVE
        mock_policy.decide_filter_strategy.assert_called_once()

    def test_apply_metadata_completeness(self, mock_context):
        """Test that apply generates complete metadata."""
        processor = FloodProcessor()

        element = ET.Element('feFlood')
        element.set('flood-color', 'rgb(128, 64, 192)')
        element.set('flood-opacity', '0.6')
        element.set('in', 'blur1')
        element.set('result', 'flood1')

        result = processor.apply(element, mock_context)

        metadata = result.get_metadata()
        inner_metadata = metadata.get('metadata', metadata)
        required_fields = [
            'filter_type', 'flood_color', 'flood_opacity', 'input_source', 'result_name',
            'strategy', 'color_format', 'has_transparency', 'processing_method'
        ]

        for field in required_fields:
            assert field in inner_metadata, f"Missing metadata field: {field}"

        assert inner_metadata['input_source'] == 'blur1'
        assert inner_metadata['result_name'] == 'flood1'
        assert inner_metadata['color_format'] == 'rgb'
        assert inner_metadata['has_transparency'] is True

    def test_apply_defaults_processing(self, mock_context):
        """Test flood processing with all default values."""
        processor = FloodProcessor()

        element = ET.Element('feFlood')  # No attributes

        result = processor.apply(element, mock_context)

        assert result.is_success() is True

        metadata = result.get_metadata()
        inner_metadata = metadata.get('metadata', metadata)
        assert inner_metadata['flood_color'] == 'black'
        assert inner_metadata['flood_opacity'] == 1.0
        assert inner_metadata['input_source'] == 'SourceGraphic'
        assert inner_metadata['result_name'] == 'flood'
        assert inner_metadata['has_transparency'] is False


class TestCreateFloodProcessor:
    """Test create_flood_processor factory function."""

    def test_create_flood_processor_without_policy(self):
        """Test factory function without policy."""
        processor = create_flood_processor()

        assert isinstance(processor, FloodProcessor)
        assert processor.filter_type == 'feFlood'
        assert processor.policy is None

    def test_create_flood_processor_with_policy(self):
        """Test factory function with policy."""
        policy = Mock()
        processor = create_flood_processor(policy)

        assert isinstance(processor, FloodProcessor)
        assert processor.policy == policy


class TestFloodParametersClass:
    """Test FloodParameters dataclass."""

    def test_flood_parameters_defaults(self):
        """Test FloodParameters with default values."""
        params = FloodParameters()

        assert params.flood_color == "black"
        assert params.flood_opacity == 1.0
        assert params.input_source == "SourceGraphic"
        assert params.result_name == "flood"

    def test_flood_parameters_custom_values(self):
        """Test FloodParameters with custom values."""
        params = FloodParameters(
            flood_color="#FF0000",
            flood_opacity=0.5,
            input_source="blur1",
            result_name="flood1"
        )

        assert params.flood_color == "#FF0000"
        assert params.flood_opacity == 0.5
        assert params.input_source == "blur1"
        assert params.result_name == "flood1"


if __name__ == '__main__':
    pytest.main([__file__])