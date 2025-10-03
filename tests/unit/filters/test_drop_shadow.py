#!/usr/bin/env python3
"""
Tests for DropShadowProcessor with comprehensive drop shadow operations.

Tests all shadow parameters, composite effects, policy integration, and DrawingML
generation for PowerPoint shadow effects.
"""

import pytest
from unittest.mock import Mock, patch
from lxml import etree as ET
import math

from core.filters.drop_shadow import (
    DropShadowProcessor,
    DropShadowParameters,
    DropShadowException,
    DropShadowValidationError,
    create_drop_shadow_processor
)
from core.filters.base import (
    FilterContext,
    FilterStrategy,
    FilterResult,
    FilterException
)


class TestDropShadowParameters:
    """Test DropShadowParameters data structure."""

    def test_initialization_defaults(self):
        """Test parameter initialization with defaults."""
        params = DropShadowParameters()

        assert params.dx == 2.0
        assert params.dy == 2.0
        assert params.std_deviation == 2.0
        assert params.flood_color == "black"
        assert params.flood_opacity == 1.0
        assert params.input_source == "SourceGraphic"

    def test_initialization_custom_values(self):
        """Test parameter initialization with custom values."""
        params = DropShadowParameters(
            dx=5.0,
            dy=3.0,
            std_deviation=4.0,
            flood_color="#808080",
            flood_opacity=0.8,
            input_source="SourceAlpha",
            result_name="shadow1"
        )

        assert params.dx == 5.0
        assert params.dy == 3.0
        assert params.std_deviation == 4.0
        assert params.flood_color == "#808080"
        assert params.flood_opacity == 0.8
        assert params.input_source == "SourceAlpha"
        assert params.result_name == "shadow1"

    def test_post_init_negative_blur(self):
        """Test that negative blur is corrected."""
        params = DropShadowParameters(std_deviation=-1.0)

        assert params.std_deviation == 0.0

    def test_post_init_opacity_clamping(self):
        """Test that opacity is clamped to valid range."""
        params_low = DropShadowParameters(flood_opacity=-0.5)
        params_high = DropShadowParameters(flood_opacity=1.5)

        assert params_low.flood_opacity == 0.0
        assert params_high.flood_opacity == 1.0

    def test_post_init_empty_color(self):
        """Test that empty color defaults to black."""
        params = DropShadowParameters(flood_color="")

        assert params.flood_color == "black"

    def test_complexity_score_simple(self):
        """Test complexity score for simple shadow."""
        params = DropShadowParameters(
            dx=2.0,
            dy=2.0,
            std_deviation=2.0,
            flood_color="black",
            flood_opacity=1.0
        )

        complexity = params.get_complexity_score()
        assert 0.0 <= complexity <= 1.0

    def test_complexity_score_large_offset(self):
        """Test complexity score for large offset."""
        params = DropShadowParameters(
            dx=30.0,
            dy=40.0,  # Distance = 50px
            std_deviation=2.0,
            flood_color="black",
            flood_opacity=1.0
        )

        complexity = params.get_complexity_score()
        assert complexity > 2.0  # Large offset adds complexity

    def test_complexity_score_large_blur(self):
        """Test complexity score for large blur."""
        params = DropShadowParameters(
            dx=2.0,
            dy=2.0,
            std_deviation=30.0,  # Large blur
            flood_color="black",
            flood_opacity=1.0
        )

        complexity = params.get_complexity_score()
        assert complexity > 2.0  # Large blur adds complexity

    def test_complexity_score_colored_shadow(self):
        """Test complexity score for colored shadow."""
        params = DropShadowParameters(
            dx=2.0,
            dy=2.0,
            std_deviation=2.0,
            flood_color="red",  # Non-black color
            flood_opacity=1.0
        )

        complexity = params.get_complexity_score()
        # Should be higher than black shadow
        black_params = DropShadowParameters(dx=2.0, dy=2.0, std_deviation=2.0)
        assert complexity > black_params.get_complexity_score()

    def test_complexity_score_partial_opacity(self):
        """Test complexity score for partial opacity."""
        params = DropShadowParameters(
            dx=2.0,
            dy=2.0,
            std_deviation=2.0,
            flood_color="black",
            flood_opacity=0.5  # Partial opacity
        )

        complexity = params.get_complexity_score()
        # Should be higher than full opacity
        full_params = DropShadowParameters(dx=2.0, dy=2.0, std_deviation=2.0)
        assert complexity > full_params.get_complexity_score()

    def test_is_effective_true(self):
        """Test is_effective for visible shadow."""
        params = DropShadowParameters(dx=2.0, dy=2.0, std_deviation=2.0)

        assert params.is_effective() is True

    def test_is_effective_false_no_offset_no_blur(self):
        """Test is_effective for shadow with no offset and no blur."""
        params = DropShadowParameters(dx=0.0, dy=0.0, std_deviation=0.0)

        assert params.is_effective() is False

    def test_is_effective_false_transparent(self):
        """Test is_effective for completely transparent shadow."""
        params = DropShadowParameters(
            dx=5.0, dy=5.0, std_deviation=3.0,
            flood_opacity=0.0  # Transparent
        )

        assert params.is_effective() is False

    def test_is_effective_true_blur_only(self):
        """Test is_effective for shadow with blur but no offset."""
        params = DropShadowParameters(dx=0.0, dy=0.0, std_deviation=3.0)

        assert params.is_effective() is True

    def test_is_effective_true_offset_only(self):
        """Test is_effective for shadow with offset but no blur."""
        params = DropShadowParameters(dx=3.0, dy=2.0, std_deviation=0.0)

        assert params.is_effective() is True

    def test_get_shadow_distance(self):
        """Test shadow distance calculation."""
        params = DropShadowParameters(dx=3.0, dy=4.0)  # 3-4-5 triangle

        assert params.get_shadow_distance() == 5.0

    def test_get_shadow_angle(self):
        """Test shadow angle calculation."""
        # Test 45-degree angle (dx=dy)
        params = DropShadowParameters(dx=1.0, dy=1.0)
        angle = params.get_shadow_angle()

        # 45 degrees should be around 810000 in PowerPoint units (45 * 60000 * 0.3)
        expected_angle = int((45.0 * 60000) % 21600000)
        assert angle == expected_angle

    def test_get_shadow_angle_zero_offset(self):
        """Test shadow angle for zero offset."""
        params = DropShadowParameters(dx=0.0, dy=0.0)

        assert params.get_shadow_angle() == 0

    def test_to_offset_parameters(self):
        """Test conversion to OffsetParameters."""
        params = DropShadowParameters(
            dx=5.0,
            dy=3.0,
            input_source="SourceAlpha"
        )

        offset_params = params.to_offset_parameters()

        assert offset_params.dx == 5.0
        assert offset_params.dy == 3.0
        assert offset_params.input_source == "SourceAlpha"
        assert offset_params.result_name == "offset_shadow"

    def test_to_blur_parameters(self):
        """Test conversion to BlurParameters."""
        params = DropShadowParameters(
            std_deviation=4.0,
            result_name="shadow1"
        )

        blur_params = params.to_blur_parameters()

        assert blur_params.std_deviation_x == 4.0
        assert blur_params.std_deviation_y == 4.0
        assert blur_params.edge_mode == "duplicate"
        assert blur_params.input_source == "offset_shadow"
        assert blur_params.result_name == "shadow1"


class TestDropShadowProcessor:
    """Test DropShadowProcessor filter processing."""

    @pytest.fixture
    def mock_policy(self):
        """Create mock policy for testing."""
        policy = Mock()
        return policy

    @pytest.fixture
    def shadow_processor(self, mock_policy):
        """Create DropShadowProcessor for testing."""
        return DropShadowProcessor(policy=mock_policy)

    @pytest.fixture
    def mock_context(self):
        """Create mock filter context."""
        context = Mock(spec=FilterContext)
        context.element = ET.Element('feDropShadow')
        context.viewport = {'width': 100, 'height': 100}
        context.unit_converter = Mock()
        context.transform_parser = Mock()
        context.color_parser = Mock()
        return context

    def test_initialization(self, mock_policy):
        """Test DropShadowProcessor initialization."""
        processor = DropShadowProcessor(policy=mock_policy)

        assert processor.filter_type == 'feDropShadow'
        assert processor.policy == mock_policy
        assert processor.max_native_distance == 50.0
        assert processor.max_native_blur == 25.0

    def test_can_apply_valid_element(self, shadow_processor, mock_context):
        """Test can_apply with valid feDropShadow element."""
        element = ET.Element('feDropShadow')
        element.set('dx', '3.0')
        element.set('dy', '2.0')
        element.set('stdDeviation', '2.5')

        assert shadow_processor.can_apply(element, mock_context) is True

    def test_can_apply_invalid_element(self, shadow_processor, mock_context):
        """Test can_apply with invalid element."""
        element = ET.Element('feGaussianBlur')
        mock_context.element = element

        assert shadow_processor.can_apply(element, mock_context) is False

    def test_can_apply_none_element(self, shadow_processor, mock_context):
        """Test can_apply with None element."""
        assert shadow_processor.can_apply(None, mock_context) is False

    def test_parse_drop_shadow_parameters_defaults(self, shadow_processor):
        """Test parsing drop shadow parameters with defaults."""
        element = ET.Element('feDropShadow')

        params = shadow_processor._parse_drop_shadow_parameters(element)

        assert params.dx == 2.0
        assert params.dy == 2.0
        assert params.std_deviation == 2.0
        assert params.flood_color == "black"
        assert params.flood_opacity == 1.0
        assert params.input_source == "SourceGraphic"

    def test_parse_drop_shadow_parameters_custom(self, shadow_processor):
        """Test parsing drop shadow parameters with custom values."""
        element = ET.Element('feDropShadow')
        element.set('dx', '5.0')
        element.set('dy', '3.0')
        element.set('stdDeviation', '4.0')
        element.set('flood-color', 'red')
        element.set('flood-opacity', '0.8')
        element.set('in', 'SourceAlpha')
        element.set('result', 'shadow1')

        params = shadow_processor._parse_drop_shadow_parameters(element)

        assert params.dx == 5.0
        assert params.dy == 3.0
        assert params.std_deviation == 4.0
        assert params.flood_color == "red"
        assert params.flood_opacity == 0.8
        assert params.input_source == "SourceAlpha"
        assert params.result_name == "shadow1"

    def test_parse_invalid_numeric_values(self, shadow_processor):
        """Test parsing with invalid numeric values raises exception."""
        element = ET.Element('feDropShadow')
        element.set('dx', 'invalid')

        with pytest.raises((DropShadowException, ValueError)):
            shadow_processor._parse_drop_shadow_parameters(element)

    def test_can_use_native_shadow_simple(self, shadow_processor):
        """Test native shadow support for simple shadow."""
        params = DropShadowParameters(
            dx=5.0,
            dy=3.0,
            std_deviation=2.0,
            flood_color="black",
            flood_opacity=1.0
        )

        assert shadow_processor._can_use_native_shadow(params) is True

    def test_can_use_native_shadow_large_distance_false(self, shadow_processor):
        """Test native shadow unsupported for large distance."""
        params = DropShadowParameters(
            dx=100.0,  # Very large offset
            dy=100.0,
            std_deviation=2.0
        )

        assert shadow_processor._can_use_native_shadow(params) is False

    def test_can_use_native_shadow_large_blur_false(self, shadow_processor):
        """Test native shadow unsupported for large blur."""
        params = DropShadowParameters(
            dx=5.0,
            dy=3.0,
            std_deviation=50.0  # Very large blur
        )

        assert shadow_processor._can_use_native_shadow(params) is False

    def test_can_use_native_shadow_transparent_false(self, shadow_processor):
        """Test native shadow unsupported for very transparent shadow."""
        params = DropShadowParameters(
            dx=5.0,
            dy=3.0,
            std_deviation=2.0,
            flood_opacity=0.05  # Very transparent
        )

        assert shadow_processor._can_use_native_shadow(params) is False

    def test_can_use_native_shadow_no_effect_true(self, shadow_processor):
        """Test native shadow supported for no-effect shadow."""
        params = DropShadowParameters(
            dx=0.0,
            dy=0.0,
            std_deviation=0.0
        )

        assert shadow_processor._can_use_native_shadow(params) is True

    @patch('core.filters.drop_shadow.unit')
    def test_generate_native_shadow_drawingml(self, mock_unit, shadow_processor, mock_context):
        """Test generating native shadow DrawingML."""
        mock_unit.return_value.to_emu.side_effect = [127000, 127000]  # Distance and blur

        params = DropShadowParameters(
            dx=3.0,
            dy=4.0,  # Distance = 5px
            std_deviation=5.0,
            flood_color="black",
            flood_opacity=0.8
        )

        drawingml = shadow_processor._generate_native_shadow_drawingml(params, mock_context)

        assert '<a:outerShdw' in drawingml
        assert 'blurRad="127000"' in drawingml
        assert 'dist="127000"' in drawingml
        assert 'val="000000"' in drawingml  # Black color
        assert 'val="80000"' in drawingml  # 80% opacity

    @patch('core.filters.drop_shadow.unit')
    def test_generate_native_shadow_drawingml_colored(self, mock_unit, shadow_processor, mock_context):
        """Test generating native shadow DrawingML with colored shadow."""
        mock_unit.return_value.to_emu.side_effect = [63500, 63500]

        params = DropShadowParameters(
            dx=2.0,
            dy=2.0,
            std_deviation=2.5,
            flood_color="red",
            flood_opacity=1.0
        )

        drawingml = shadow_processor._generate_native_shadow_drawingml(params, mock_context)

        assert '<a:outerShdw' in drawingml
        assert 'val="FF0000"' in drawingml  # Red color
        assert 'val="100000"' in drawingml  # Full opacity

    @patch('core.filters.drop_shadow.unit')
    def test_generate_composite_shadow_drawingml(self, mock_unit, shadow_processor, mock_context):
        """Test generating composite shadow DrawingML for large parameters."""
        mock_unit.return_value.to_emu.return_value = 635000  # Reduced values

        params = DropShadowParameters(
            dx=100.0,  # Large offset that exceeds native limits
            dy=100.0,
            std_deviation=50.0,  # Large blur that exceeds native limits
            flood_color="gray",
            flood_opacity=0.7
        )

        drawingml = shadow_processor._generate_composite_shadow_drawingml(params, mock_context)

        assert '<a:outerShdw' in drawingml
        assert 'val="808080"' in drawingml  # Gray color
        assert 'Drop shadow approximation' in drawingml  # Approximation comment

    def test_convert_color_to_hex_named_colors(self, shadow_processor):
        """Test color conversion for named colors."""
        assert shadow_processor._convert_color_to_hex("black") == "000000"
        assert shadow_processor._convert_color_to_hex("white") == "FFFFFF"
        assert shadow_processor._convert_color_to_hex("red") == "FF0000"
        assert shadow_processor._convert_color_to_hex("green") == "008000"
        assert shadow_processor._convert_color_to_hex("blue") == "0000FF"
        assert shadow_processor._convert_color_to_hex("gray") == "808080"
        assert shadow_processor._convert_color_to_hex("grey") == "808080"

    def test_convert_color_to_hex_hex_format(self, shadow_processor):
        """Test color conversion for hex format."""
        assert shadow_processor._convert_color_to_hex("#FF0000") == "FF0000"
        assert shadow_processor._convert_color_to_hex("#123456") == "123456"
        assert shadow_processor._convert_color_to_hex("#abc") == "AABBCC"  # 3-digit expansion

    def test_convert_color_to_hex_unknown(self, shadow_processor):
        """Test color conversion for unknown colors defaults to black."""
        assert shadow_processor._convert_color_to_hex("unknown-color") == "000000"
        assert shadow_processor._convert_color_to_hex("") == "000000"

    def test_apply_native_strategy_simple_shadow(self, shadow_processor, mock_context, mock_policy):
        """Test apply with native strategy for simple shadow."""
        element = ET.Element('feDropShadow')
        element.set('dx', '3.0')
        element.set('dy', '4.0')
        element.set('stdDeviation', '2.0')
        mock_context.element = element

        mock_policy.decide_drop_shadow_strategy.return_value = Mock(strategy=FilterStrategy.NATIVE)

        with patch.object(shadow_processor, '_generate_native_shadow_drawingml') as mock_generate:
            mock_generate.return_value = '<a:outerShdw>...</a:outerShdw>'

            result = shadow_processor.apply(element, mock_context)

            assert isinstance(result, FilterResult)
            assert result.success is True
            assert result.strategy == FilterStrategy.NATIVE
            assert result.metadata['filter_type'] == 'feDropShadow'
            assert result.metadata['approach'] == 'native'
            assert result.metadata['dx'] == 3.0
            assert result.metadata['dy'] == 4.0

    def test_apply_approximation_strategy(self, shadow_processor, mock_context, mock_policy):
        """Test apply with approximation strategy."""
        element = ET.Element('feDropShadow')
        element.set('dx', '100.0')  # Large offset
        element.set('dy', '100.0')
        element.set('stdDeviation', '10.0')
        mock_context.element = element

        mock_policy.decide_drop_shadow_strategy.return_value = Mock(strategy=FilterStrategy.APPROXIMATION)

        with patch.object(shadow_processor, '_generate_composite_shadow_drawingml') as mock_generate:
            mock_generate.return_value = '<a:outerShdw>...approximation...</a:outerShdw>'

            result = shadow_processor.apply(element, mock_context)

            assert isinstance(result, FilterResult)
            assert result.success is True
            assert result.strategy == FilterStrategy.APPROXIMATION
            assert result.metadata['approach'] == 'composite'

    def test_apply_emf_strategy(self, shadow_processor, mock_context, mock_policy):
        """Test apply with EMF rasterization strategy."""
        element = ET.Element('feDropShadow')
        element.set('dx', '200.0')  # Very large parameters
        element.set('dy', '200.0')
        element.set('stdDeviation', '100.0')
        mock_context.element = element

        mock_policy.decide_drop_shadow_strategy.return_value = Mock(strategy=FilterStrategy.EMF_RASTERIZE)

        result = shadow_processor.apply(element, mock_context)

        assert isinstance(result, FilterResult)
        assert result.success is True
        assert result.strategy == FilterStrategy.EMF_RASTERIZE
        assert 'EMF rasterization for complex drop shadow' in result.drawingml
        assert result.metadata['approach'] == 'emf'

    def test_apply_no_effect_shadow(self, shadow_processor, mock_context, mock_policy):
        """Test apply with no-effect shadow."""
        element = ET.Element('feDropShadow')
        element.set('dx', '0.0')
        element.set('dy', '0.0')
        element.set('stdDeviation', '0.0')
        mock_context.element = element

        mock_policy.decide_drop_shadow_strategy.return_value = Mock(strategy=FilterStrategy.NATIVE)

        result = shadow_processor.apply(element, mock_context)

        assert isinstance(result, FilterResult)
        assert result.success is True
        assert result.strategy == FilterStrategy.NATIVE
        assert 'No visible drop shadow effect' in result.drawingml

    def test_apply_parsing_error_handling(self, shadow_processor, mock_context, mock_policy):
        """Test apply handles parsing errors gracefully."""
        element = ET.Element('feDropShadow')
        element.set('dx', 'invalid')  # Invalid value
        mock_context.element = element

        mock_policy.decide_drop_shadow_strategy.return_value = Mock(strategy=FilterStrategy.NATIVE)

        result = shadow_processor.apply(element, mock_context)

        assert isinstance(result, FilterResult)
        assert result.success is False
        assert result.error_message is not None
        assert "Drop shadow processing failed" in result.error_message

    def test_apply_strategy_without_policy(self, mock_context):
        """Test apply with strategy selection without policy."""
        processor = DropShadowProcessor()  # No policy
        element = ET.Element('feDropShadow')
        element.set('dx', '3.0')
        element.set('dy', '4.0')
        element.set('stdDeviation', '2.0')
        mock_context.element = element

        with patch.object(processor, '_generate_native_shadow_drawingml') as mock_generate:
            mock_generate.return_value = '<a:outerShdw>...</a:outerShdw>'

            result = processor.apply(element, mock_context)

            assert result.success is True
            assert result.strategy == FilterStrategy.NATIVE

    def test_validate_parameters_valid(self, shadow_processor, mock_context):
        """Test parameter validation with valid element."""
        element = ET.Element('feDropShadow')
        element.set('dx', '3.0')
        element.set('dy', '2.0')
        element.set('stdDeviation', '2.5')

        assert shadow_processor._validate_parameters(element, mock_context) is True

    def test_validate_parameters_invalid_element(self, shadow_processor, mock_context):
        """Test parameter validation with invalid element."""
        element = ET.Element('feDropShadow')
        element.set('dx', 'invalid')

        assert shadow_processor._validate_parameters(element, mock_context) is False

    def test_validate_parameters_none_element(self, shadow_processor, mock_context):
        """Test parameter validation with None element."""
        assert shadow_processor._validate_parameters(None, mock_context) is False

    def test_validate_parameters_none_context(self, shadow_processor):
        """Test parameter validation with None context."""
        element = ET.Element('feDropShadow')
        element.set('dx', '3.0')

        assert shadow_processor._validate_parameters(element, None) is False


class TestDropShadowProcessorIntegration:
    """Test DropShadowProcessor integration with policy and context."""

    @pytest.fixture
    def mock_policy(self):
        """Create mock policy with strategy decisions."""
        policy = Mock()
        return policy

    @pytest.fixture
    def shadow_processor(self, mock_policy):
        """Create DropShadowProcessor with mock policy."""
        return DropShadowProcessor(policy=mock_policy)

    @pytest.fixture
    def mock_context(self):
        """Create realistic filter context."""
        context = Mock(spec=FilterContext)
        context.viewport = {'width': 100, 'height': 100}
        context.unit_converter = Mock()
        context.transform_parser = Mock()
        context.color_parser = Mock()
        return context

    def test_policy_integration_calls_decide_drop_shadow_strategy(self, shadow_processor, mock_context, mock_policy):
        """Test policy integration calls decide_drop_shadow_strategy."""
        element = ET.Element('feDropShadow')
        element.set('dx', '5.0')
        element.set('dy', '3.0')
        mock_context.element = element

        mock_policy.decide_drop_shadow_strategy.return_value = Mock(strategy=FilterStrategy.NATIVE)

        with patch.object(shadow_processor, '_generate_native_shadow_drawingml') as mock_generate:
            mock_generate.return_value = '<a:outerShdw>...</a:outerShdw>'

            shadow_processor.apply(element, mock_context)

            # Verify policy was called
            mock_policy.decide_drop_shadow_strategy.assert_called_once()
            call_args = mock_policy.decide_drop_shadow_strategy.call_args[0]
            assert isinstance(call_args[0], DropShadowParameters)
            assert call_args[1] == mock_context

    def test_comprehensive_drop_shadow_processing(self, shadow_processor, mock_context, mock_policy):
        """Test comprehensive drop shadow processing with metadata."""
        element = ET.Element('feDropShadow')
        element.set('dx', '5.0')
        element.set('dy', '3.0')
        element.set('stdDeviation', '4.0')
        element.set('flood-color', 'red')
        element.set('flood-opacity', '0.8')
        element.set('in', 'SourceAlpha')
        element.set('result', 'shadow1')
        mock_context.element = element

        mock_policy.decide_drop_shadow_strategy.return_value = Mock(strategy=FilterStrategy.NATIVE)

        with patch.object(shadow_processor, '_generate_native_shadow_drawingml') as mock_generate:
            mock_generate.return_value = '<a:outerShdw>...</a:outerShdw>'

            result = shadow_processor.apply(element, mock_context)

            assert result.success is True
            assert result.metadata['dx'] == 5.0
            assert result.metadata['dy'] == 3.0
            assert result.metadata['std_deviation'] == 4.0
            assert result.metadata['flood_color'] == 'red'
            assert result.metadata['flood_opacity'] == 0.8
            assert result.metadata['shadow_distance'] == math.sqrt(25 + 9)  # sqrt(5²+3²)
            assert 'shadow_angle' in result.metadata

    def test_drop_shadow_error_recovery(self, shadow_processor, mock_context, mock_policy):
        """Test drop shadow processor error recovery."""
        element = ET.Element('feDropShadow')
        element.set('dx', 'completely-invalid-value')
        mock_context.element = element

        mock_policy.decide_drop_shadow_strategy.return_value = Mock(strategy=FilterStrategy.NATIVE)

        result = shadow_processor.apply(element, mock_context)

        assert result.success is False
        assert result.strategy == FilterStrategy.EMF_RASTERIZE
        assert result.error_message is not None


class TestDropShadowFilterException:
    """Test DropShadowFilterException error handling."""

    def test_exception_creation_with_message(self):
        """Test creating exception with message."""
        exception = DropShadowException("Test error message")

        assert str(exception) == "Test error message"
        assert exception.args[0] == "Test error message"

    def test_validation_error_inheritance(self):
        """Test DropShadowValidationError inherits correctly."""
        exception = DropShadowValidationError("Validation error")

        assert isinstance(exception, DropShadowException)
        assert isinstance(exception, ValueError)
        assert isinstance(exception, DropShadowValidationError)


class TestCreateDropShadowProcessor:
    """Test create_drop_shadow_processor factory function."""

    def test_create_with_policy(self):
        """Test creating processor with policy."""
        policy = Mock()
        processor = create_drop_shadow_processor(policy=policy)

        assert isinstance(processor, DropShadowProcessor)
        assert processor.policy == policy
        assert processor.filter_type == 'feDropShadow'

    def test_create_without_policy(self):
        """Test creating processor without policy."""
        processor = create_drop_shadow_processor()

        assert isinstance(processor, DropShadowProcessor)
        assert processor.policy is None
        assert processor.filter_type == 'feDropShadow'


if __name__ == '__main__':
    pytest.main([__file__])