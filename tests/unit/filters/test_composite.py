#!/usr/bin/env python3
"""
Tests for CompositeProcessor with comprehensive Porter-Duff and blend operations.

Tests all 10 composite operators, arithmetic operations with k1-k4 coefficients,
policy integration, and DrawingML generation for PowerPoint filter effects.
"""

import pytest
from unittest.mock import Mock, patch
from lxml import etree as ET

from core.filters.composite import (
    CompositeProcessor,
    CompositeParameters,
    CompositeOperator,
    CompositeFilterException,
    create_composite_processor
)
from core.filters.base import (
    FilterContext,
    FilterStrategy,
    FilterResult,
    FilterException
)


class TestCompositeParameters:
    """Test CompositeParameters data structure."""

    def test_initialization_with_over_operator(self):
        """Test parameter initialization with over operator."""
        params = CompositeParameters(
            operator=CompositeOperator.OVER,
            input1="SourceGraphic",
            input2="BackgroundImage"
        )

        assert params.operator == CompositeOperator.OVER
        assert params.input1 == "SourceGraphic"
        assert params.input2 == "BackgroundImage"
        assert params.k1 == 0.0
        assert params.k2 == 0.0
        assert params.k3 == 0.0
        assert params.k4 == 0.0

    def test_initialization_with_arithmetic_operator(self):
        """Test parameter initialization with arithmetic operator and k values."""
        params = CompositeParameters(
            operator=CompositeOperator.ARITHMETIC,
            input1="SourceGraphic",
            input2="BackgroundImage",
            k1=0.2,
            k2=0.5,
            k3=0.8,
            k4=0.1
        )

        assert params.operator == CompositeOperator.ARITHMETIC
        assert params.k1 == 0.2
        assert params.k2 == 0.5
        assert params.k3 == 0.8
        assert params.k4 == 0.1

    def test_initialization_with_multiply_operator(self):
        """Test parameter initialization with multiply blend operator."""
        params = CompositeParameters(
            operator=CompositeOperator.MULTIPLY,
            input1="SourceGraphic",
            input2="effect1"
        )

        assert params.operator == CompositeOperator.MULTIPLY
        assert params.input1 == "SourceGraphic"
        assert params.input2 == "effect1"

    def test_porter_duff_operators(self):
        """Test all Porter-Duff operators are available."""
        porter_duff_ops = [
            CompositeOperator.OVER,
            CompositeOperator.IN,
            CompositeOperator.OUT,
            CompositeOperator.ATOP,
            CompositeOperator.XOR
        ]

        for op in porter_duff_ops:
            params = CompositeParameters(
                operator=op,
                input1="SourceGraphic",
                input2="BackgroundImage"
            )
            assert params.operator == op

    def test_blend_operators(self):
        """Test all blend operators are available."""
        blend_ops = [
            CompositeOperator.MULTIPLY,
            CompositeOperator.SCREEN,
            CompositeOperator.DARKEN,
            CompositeOperator.LIGHTEN
        ]

        for op in blend_ops:
            params = CompositeParameters(
                operator=op,
                input1="SourceGraphic",
                input2="BackgroundImage"
            )
            assert params.operator == op


class TestCompositeProcessor:
    """Test CompositeProcessor filter processing."""

    @pytest.fixture
    def mock_policy(self):
        """Create mock policy for testing."""
        policy = Mock()
        return policy

    @pytest.fixture
    def composite_processor(self, mock_policy):
        """Create CompositeProcessor for testing."""
        return CompositeProcessor(policy=mock_policy)

    @pytest.fixture
    def mock_context(self):
        """Create mock filter context."""
        context = Mock(spec=FilterContext)
        context.element = ET.Element('feComposite')
        context.viewport = {'width': 100, 'height': 100}
        context.unit_converter = Mock()
        context.transform_parser = Mock()
        context.color_parser = Mock()
        return context

    def test_initialization(self, mock_policy):
        """Test CompositeProcessor initialization."""
        processor = CompositeProcessor(policy=mock_policy)

        assert processor.filter_type == 'feComposite'
        assert processor.policy == mock_policy
        assert hasattr(processor, 'logger')

    def test_parse_over_operator_from_element(self, composite_processor, mock_context):
        """Test parsing over operator from SVG element."""
        element = ET.Element('feComposite')
        element.set('operator', 'over')
        element.set('in', 'SourceGraphic')
        element.set('in2', 'BackgroundImage')

        params = composite_processor._parse_composite_parameters(element)

        assert params.operator == CompositeOperator.OVER
        assert params.input1 == 'SourceGraphic'
        assert params.input2 == 'BackgroundImage'

    def test_parse_arithmetic_operator_from_element(self, composite_processor, mock_context):
        """Test parsing arithmetic operator with k values from SVG element."""
        element = ET.Element('feComposite')
        element.set('operator', 'arithmetic')
        element.set('in', 'SourceGraphic')
        element.set('in2', 'BackgroundImage')
        element.set('k1', '0.2')
        element.set('k2', '0.5')
        element.set('k3', '0.8')
        element.set('k4', '0.1')
        params = composite_processor._parse_composite_parameters(element)

        assert params.operator == CompositeOperator.ARITHMETIC
        assert params.k1 == 0.2
        assert params.k2 == 0.5
        assert params.k3 == 0.8
        assert params.k4 == 0.1

    def test_parse_multiply_operator_from_element(self, composite_processor, mock_context):
        """Test parsing multiply blend operator from SVG element."""
        element = ET.Element('feComposite')
        element.set('operator', 'multiply')
        element.set('in', 'SourceGraphic')
        element.set('in2', 'effect1')
        params = composite_processor._parse_composite_parameters(element)

        assert params.operator == CompositeOperator.MULTIPLY
        assert params.input1 == 'SourceGraphic'
        assert params.input2 == 'effect1'

    def test_parse_defaults_to_over(self, composite_processor, mock_context):
        """Test parsing defaults to over operator when not specified."""
        element = ET.Element('feComposite')
        element.set('in', 'SourceGraphic')
        element.set('in2', 'BackgroundImage')
        params = composite_processor._parse_composite_parameters(element)

        assert params.operator == CompositeOperator.OVER

    def test_parse_invalid_operator_raises_exception(self, composite_processor, mock_context):
        """Test parsing invalid operator raises exception."""
        element = ET.Element('feComposite')
        element.set('operator', 'invalid-operator')
        element.set('in', 'SourceGraphic')
        element.set('in2', 'BackgroundImage')

        with pytest.raises(CompositeFilterException) as exc_info:
            composite_processor._parse_composite_parameters(element)

        assert "Invalid composite operator: 'invalid-operator'" in str(exc_info.value)

    def test_has_native_support_for_multiply(self, composite_processor):
        """Test native support detection for multiply operator."""
        params = CompositeParameters(
            operator=CompositeOperator.MULTIPLY,
            input1="SourceGraphic",
            input2="BackgroundImage"
        )

        assert composite_processor._has_native_support(params) is True

    def test_has_native_support_for_screen(self, composite_processor):
        """Test native support detection for screen operator."""
        params = CompositeParameters(
            operator=CompositeOperator.SCREEN,
            input1="SourceGraphic",
            input2="BackgroundImage"
        )

        assert composite_processor._has_native_support(params) is True

    def test_has_native_support_for_darken(self, composite_processor):
        """Test native support detection for darken operator."""
        params = CompositeParameters(
            operator=CompositeOperator.DARKEN,
            input1="SourceGraphic",
            input2="BackgroundImage"
        )

        assert composite_processor._has_native_support(params) is True

    def test_has_native_support_for_lighten(self, composite_processor):
        """Test native support detection for lighten operator."""
        params = CompositeParameters(
            operator=CompositeOperator.LIGHTEN,
            input1="SourceGraphic",
            input2="BackgroundImage"
        )

        assert composite_processor._has_native_support(params) is True

    def test_has_native_support_for_over(self, composite_processor):
        """Test native support detection for over operator."""
        params = CompositeParameters(
            operator=CompositeOperator.OVER,
            input1="SourceGraphic",
            input2="BackgroundImage"
        )

        assert composite_processor._has_native_support(params) is True

    def test_no_native_support_for_porter_duff(self, composite_processor):
        """Test no native support for complex Porter-Duff operators."""
        porter_duff_ops = [
            CompositeOperator.IN,
            CompositeOperator.OUT,
            CompositeOperator.ATOP,
            CompositeOperator.XOR
        ]

        for op in porter_duff_ops:
            params = CompositeParameters(
                operator=op,
                input1="SourceGraphic",
                input2="BackgroundImage"
            )
            assert composite_processor._has_native_support(params) is False

    def test_no_native_support_for_arithmetic(self, composite_processor):
        """Test no native support for arithmetic operator."""
        params = CompositeParameters(
            operator=CompositeOperator.ARITHMETIC,
            input1="SourceGraphic",
            input2="BackgroundImage",
            k1=0.2, k2=0.5, k3=0.8, k4=0.1
        )

        assert composite_processor._has_native_support(params) is False

    def test_generate_native_multiply_drawingml(self, composite_processor, mock_context):
        """Test generating native DrawingML for multiply operator."""
        params = CompositeParameters(
            operator=CompositeOperator.MULTIPLY,
            input1="SourceGraphic",
            input2="BackgroundImage"
        )

        drawingml = composite_processor._generate_native_composite_drawingml(params, mock_context)

        assert 'a:blend' in drawingml
        assert 'blendMode="mult"' in drawingml
        assert 'Native composite: SourceGraphic multiply BackgroundImage' in drawingml

    def test_generate_native_screen_drawingml(self, composite_processor, mock_context):
        """Test generating native DrawingML for screen operator."""
        params = CompositeParameters(
            operator=CompositeOperator.SCREEN,
            input1="SourceGraphic",
            input2="BackgroundImage"
        )

        drawingml = composite_processor._generate_native_composite_drawingml(params, mock_context)

        assert 'a:blend' in drawingml
        assert 'blendMode="screen"' in drawingml
        assert 'Native composite: SourceGraphic screen BackgroundImage' in drawingml

    def test_generate_native_darken_drawingml(self, composite_processor, mock_context):
        """Test generating native DrawingML for darken operator."""
        params = CompositeParameters(
            operator=CompositeOperator.DARKEN,
            input1="SourceGraphic",
            input2="BackgroundImage"
        )

        drawingml = composite_processor._generate_native_composite_drawingml(params, mock_context)

        assert 'a:blend' in drawingml
        assert 'blendMode="darken"' in drawingml
        assert 'Native composite: SourceGraphic darken BackgroundImage' in drawingml

    def test_generate_native_lighten_drawingml(self, composite_processor, mock_context):
        """Test generating native DrawingML for lighten operator."""
        params = CompositeParameters(
            operator=CompositeOperator.LIGHTEN,
            input1="SourceGraphic",
            input2="BackgroundImage"
        )

        drawingml = composite_processor._generate_native_composite_drawingml(params, mock_context)

        assert 'a:blend' in drawingml
        assert 'blendMode="lighten"' in drawingml
        assert 'Native composite: SourceGraphic lighten BackgroundImage' in drawingml

    def test_generate_approximation_over_drawingml(self, composite_processor, mock_context):
        """Test generating approximation DrawingML for over operator."""
        params = CompositeParameters(
            operator=CompositeOperator.OVER,
            input1="SourceGraphic",
            input2="BackgroundImage"
        )

        drawingml = composite_processor._generate_approximation_composite_drawingml(params, mock_context)

        assert 'a:blend' in drawingml
        assert 'blendMode="over"' in drawingml
        assert 'Approximated Porter-Duff operation: over' in drawingml

    def test_generate_approximation_in_drawingml(self, composite_processor, mock_context):
        """Test generating approximation DrawingML for in operator."""
        params = CompositeParameters(
            operator=CompositeOperator.IN,
            input1="SourceGraphic",
            input2="BackgroundImage"
        )

        drawingml = composite_processor._generate_approximation_composite_drawingml(params, mock_context)

        assert 'a:blend' in drawingml
        assert 'blendMode="mult"' in drawingml
        assert 'Approximated Porter-Duff operation: in' in drawingml

    def test_generate_approximation_out_drawingml(self, composite_processor, mock_context):
        """Test generating approximation DrawingML for out operator."""
        params = CompositeParameters(
            operator=CompositeOperator.OUT,
            input1="SourceGraphic",
            input2="BackgroundImage"
        )

        drawingml = composite_processor._generate_approximation_composite_drawingml(params, mock_context)

        assert 'a:blend' in drawingml
        assert 'blendMode="exclusion"' in drawingml
        assert 'Approximated Porter-Duff operation: out' in drawingml

    def test_generate_approximation_atop_drawingml(self, composite_processor, mock_context):
        """Test generating approximation DrawingML for atop operator."""
        params = CompositeParameters(
            operator=CompositeOperator.ATOP,
            input1="SourceGraphic",
            input2="BackgroundImage"
        )

        drawingml = composite_processor._generate_approximation_composite_drawingml(params, mock_context)

        assert 'a:blend' in drawingml
        assert 'blendMode="overlay"' in drawingml
        assert 'Approximated Porter-Duff operation: atop' in drawingml

    def test_generate_approximation_xor_drawingml(self, composite_processor, mock_context):
        """Test generating approximation DrawingML for xor operator."""
        params = CompositeParameters(
            operator=CompositeOperator.XOR,
            input1="SourceGraphic",
            input2="BackgroundImage"
        )

        drawingml = composite_processor._generate_approximation_composite_drawingml(params, mock_context)

        assert 'a:blend' in drawingml
        assert 'blendMode="exclusion"' in drawingml
        assert 'Approximated Porter-Duff operation: xor' in drawingml

    def test_generate_approximation_arithmetic_drawingml(self, composite_processor, mock_context):
        """Test generating approximation DrawingML for arithmetic operator."""
        params = CompositeParameters(
            operator=CompositeOperator.ARITHMETIC,
            input1="SourceGraphic",
            input2="BackgroundImage",
            k1=0.2, k2=0.5, k3=0.8, k4=0.1
        )

        drawingml = composite_processor._generate_approximation_composite_drawingml(params, mock_context)

        assert 'a:blend' in drawingml
        assert 'blendMode="lighten"' in drawingml
        assert 'Arithmetic: addition-based' in drawingml

    def test_can_apply_returns_true(self, composite_processor, mock_context):
        """Test can_apply returns True for composite elements."""
        element = ET.Element('feComposite')
        mock_context.element = element

        assert composite_processor.can_apply(element, mock_context) is True

    def test_can_apply_returns_false_for_non_composite(self, composite_processor, mock_context):
        """Test can_apply returns False for non-composite elements."""
        element = ET.Element('feGaussianBlur')
        mock_context.element = element

        assert composite_processor.can_apply(element, mock_context) is False


class TestCompositeProcessorIntegration:
    """Test CompositeProcessor integration with policy and context."""

    @pytest.fixture
    def mock_policy(self):
        """Create mock policy with strategy decisions."""
        policy = Mock()
        return policy

    @pytest.fixture
    def composite_processor(self, mock_policy):
        """Create CompositeProcessor with mock policy."""
        return CompositeProcessor(policy=mock_policy)

    @pytest.fixture
    def mock_context(self):
        """Create realistic filter context."""
        context = Mock(spec=FilterContext)
        context.viewport = {'width': 100, 'height': 100}
        context.unit_converter = Mock()
        context.transform_parser = Mock()
        context.color_parser = Mock()
        return context

    def test_apply_with_native_strategy(self, composite_processor, mock_context, mock_policy):
        """Test apply with NATIVE strategy."""
        # Setup
        element = ET.Element('feComposite')
        element.set('operator', 'multiply')
        element.set('in', 'SourceGraphic')
        element.set('in2', 'BackgroundImage')
        mock_context.element = element

        mock_policy.decide_filter_strategy.return_value = FilterStrategy.NATIVE

        # Execute
        result = composite_processor.apply(element, mock_context)

        # Verify
        assert isinstance(result, FilterResult)
        assert result.success is True
        assert result.strategy == FilterStrategy.NATIVE
        assert 'a:blend' in result.drawingml
        assert 'blendMode="mult"' in result.drawingml
        assert result.metadata['operator'] == 'multiply'
        assert result.metadata['input1'] == 'SourceGraphic'
        assert result.metadata['input2'] == 'BackgroundImage'

    def test_apply_with_approximation_strategy(self, composite_processor, mock_context, mock_policy):
        """Test apply with APPROXIMATION strategy."""
        # Setup
        element = ET.Element('feComposite')
        element.set('operator', 'over')
        element.set('in', 'SourceGraphic')
        element.set('in2', 'BackgroundImage')
        mock_context.element = element

        mock_policy.decide_filter_strategy.return_value = FilterStrategy.APPROXIMATION

        # Execute
        result = composite_processor.apply(element, mock_context)

        # Verify
        assert isinstance(result, FilterResult)
        assert result.success is True
        assert result.strategy == FilterStrategy.APPROXIMATION
        assert 'a:blend' in result.drawingml
        assert 'blendMode="over"' in result.drawingml
        assert result.metadata['operator'] =='over'

    def test_apply_with_emf_rasterize_strategy(self, composite_processor, mock_context, mock_policy):
        """Test apply with EMF_RASTERIZE strategy."""
        # Setup
        element = ET.Element('feComposite')
        element.set('operator', 'arithmetic')
        element.set('in', 'SourceGraphic')
        element.set('in2', 'BackgroundImage')
        element.set('k1', '0.5')
        mock_context.element = element

        mock_policy.decide_filter_strategy.return_value = FilterStrategy.EMF_RASTERIZE

        # Execute
        result = composite_processor.apply(element, mock_context)

        # Verify
        assert isinstance(result, FilterResult)
        assert result.success is True
        assert result.strategy == FilterStrategy.EMF_RASTERIZE
        assert 'EMF rasterization required' in result.drawingml
        assert 'a:blip' in result.drawingml
        assert result.metadata['operator'] =='arithmetic'

    def test_apply_parsing_error_handling(self, composite_processor, mock_context, mock_policy):
        """Test apply handles parsing errors gracefully."""
        # Setup invalid element
        element = ET.Element('feComposite')
        element.set('k1', 'invalid-number')  # This will cause parsing error
        mock_context.element = element

        mock_policy.decide_filter_strategy.return_value = FilterStrategy.NATIVE

        # Execute
        result = composite_processor.apply(element, mock_context)

        # Verify error handling
        assert isinstance(result, FilterResult)
        assert result.success is False
        assert result.error_message is not None

    def test_policy_integration_calls_decide_filter_strategy(self, composite_processor, mock_context, mock_policy):
        """Test policy integration calls decide_filter_strategy."""
        # Setup
        element = ET.Element('feComposite')
        element.set('operator', 'screen')
        mock_context.element = element

        mock_policy.decide_filter_strategy.return_value = FilterStrategy.NATIVE

        # Execute
        composite_processor.apply(element, mock_context)

        # Verify policy was called with correct parameters
        mock_policy.decide_filter_strategy.assert_called_once()
        call_args = mock_policy.decide_filter_strategy.call_args[1]
        assert call_args['filter_type'] == 'feComposite'
        assert call_args['element'] == element
        # context argument is the decision context dict, not FilterContext
        assert 'context' in call_args


class TestCompositeFilterException:
    """Test CompositeFilterException error handling."""

    def test_exception_creation_with_message(self):
        """Test creating exception with message."""
        exception = CompositeFilterException("Test error message")

        assert str(exception) == "Test error message"
        assert exception.args[0] == "Test error message"

    def test_exception_creation_with_message_and_cause(self):
        """Test creating exception with message and cause."""
        cause = ValueError("Original error")
        try:
            raise CompositeFilterException("Composite error") from cause
        except CompositeFilterException as exception:
            assert str(exception) == "Composite error"
            assert exception.__cause__ == cause

    def test_exception_inheritance(self):
        """Test exception inherits from FilterException."""
        exception = CompositeFilterException("Test")

        assert isinstance(exception, FilterException)
        assert isinstance(exception, CompositeFilterException)


class TestCreateCompositeProcessor:
    """Test create_composite_processor factory function."""

    def test_create_with_policy(self):
        """Test creating processor with policy."""
        policy = Mock()
        processor = create_composite_processor(policy=policy)

        assert isinstance(processor, CompositeProcessor)
        assert processor.policy == policy
        assert processor.filter_type == 'feComposite'

    def test_create_without_policy(self):
        """Test creating processor without policy."""
        processor = create_composite_processor()

        assert isinstance(processor, CompositeProcessor)
        assert processor.policy is None
        assert processor.filter_type == 'feComposite'


if __name__ == '__main__':
    pytest.main([__file__])