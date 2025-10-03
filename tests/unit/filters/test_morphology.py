#!/usr/bin/env python3
"""
Tests for MorphologyProcessor with comprehensive erosion and dilation operations.

Tests all morphology operators, radius handling, policy integration, and DrawingML
generation for PowerPoint morphology effects.
"""

import pytest
from unittest.mock import Mock, patch
from lxml import etree as ET

from core.filters.morphology import (
    MorphologyProcessor,
    MorphologyParameters,
    MorphologyOperator,
    MorphologyFilterException,
    create_morphology_processor
)
from core.filters.base import (
    FilterContext,
    FilterStrategy,
    FilterResult,
    FilterException
)


class TestMorphologyParameters:
    """Test MorphologyParameters data structure."""

    def test_initialization_with_dilate_operator(self):
        """Test parameter initialization with dilate operator."""
        params = MorphologyParameters(
            operator=MorphologyOperator.DILATE,
            radius_x=5.0,
            radius_y=3.0,
            input_source="SourceGraphic",
            result_name="dilated"
        )

        assert params.operator == MorphologyOperator.DILATE
        assert params.radius_x == 5.0
        assert params.radius_y == 3.0
        assert params.input_source == "SourceGraphic"
        assert params.result_name == "dilated"

    def test_initialization_with_erode_operator(self):
        """Test parameter initialization with erode operator."""
        params = MorphologyParameters(
            operator=MorphologyOperator.ERODE,
            radius_x=2.5,
            radius_y=2.5
        )

        assert params.operator == MorphologyOperator.ERODE
        assert params.radius_x == 2.5
        assert params.radius_y == 2.5
        assert params.input_source == "SourceGraphic"  # default
        assert params.result_name == "morphology"  # default

    def test_initialization_with_symmetric_radius(self):
        """Test parameter initialization with symmetric radius."""
        params = MorphologyParameters(
            operator=MorphologyOperator.DILATE,
            radius_x=7.0,
            radius_y=7.0
        )

        assert params.radius_x == params.radius_y
        assert abs(params.radius_x - params.radius_y) < 0.1

    def test_initialization_with_asymmetric_radius(self):
        """Test parameter initialization with asymmetric radius."""
        params = MorphologyParameters(
            operator=MorphologyOperator.ERODE,
            radius_x=8.0,
            radius_y=3.0
        )

        assert params.radius_x != params.radius_y
        assert abs(params.radius_x - params.radius_y) > 0.1


class TestMorphologyProcessor:
    """Test MorphologyProcessor filter processing."""

    @pytest.fixture
    def mock_policy(self):
        """Create mock policy for testing."""
        policy = Mock()
        return policy

    @pytest.fixture
    def morphology_processor(self, mock_policy):
        """Create MorphologyProcessor for testing."""
        return MorphologyProcessor(policy=mock_policy)

    @pytest.fixture
    def mock_context(self):
        """Create mock filter context."""
        context = Mock(spec=FilterContext)
        context.element = ET.Element('feMorphology')
        context.viewport = {'width': 100, 'height': 100}
        context.unit_converter = Mock()
        context.transform_parser = Mock()
        context.color_parser = Mock()
        return context

    def test_initialization(self, mock_policy):
        """Test MorphologyProcessor initialization."""
        processor = MorphologyProcessor(policy=mock_policy)

        assert processor.filter_type == 'feMorphology'
        assert processor.policy == mock_policy
        assert hasattr(processor, 'logger')

    def test_parse_dilate_operator_from_element(self, morphology_processor, mock_context):
        """Test parsing dilate operator from SVG element."""
        element = ET.Element('feMorphology')
        element.set('operator', 'dilate')
        element.set('radius', '5 3')
        element.set('in', 'SourceGraphic')

        params = morphology_processor._parse_morphology_parameters(element)

        assert params.operator == MorphologyOperator.DILATE
        assert params.radius_x == 5.0
        assert params.radius_y == 3.0
        assert params.input_source == 'SourceGraphic'

    def test_parse_erode_operator_from_element(self, morphology_processor, mock_context):
        """Test parsing erode operator from SVG element."""
        element = ET.Element('feMorphology')
        element.set('operator', 'erode')
        element.set('radius', '2.5')
        element.set('result', 'eroded')

        params = morphology_processor._parse_morphology_parameters(element)

        assert params.operator == MorphologyOperator.ERODE
        assert params.radius_x == 2.5
        assert params.radius_y == 2.5  # Single value applied to both
        assert params.result_name == 'eroded'

    def test_parse_defaults_to_dilate(self, morphology_processor, mock_context):
        """Test parsing defaults to dilate operator when not specified."""
        element = ET.Element('feMorphology')
        element.set('radius', '1')

        params = morphology_processor._parse_morphology_parameters(element)

        assert params.operator == MorphologyOperator.DILATE
        assert params.input_source == 'SourceGraphic'
        assert params.result_name == 'morphology'

    def test_parse_invalid_operator_raises_exception(self, morphology_processor, mock_context):
        """Test parsing invalid operator raises exception."""
        element = ET.Element('feMorphology')
        element.set('operator', 'invalid-operator')
        element.set('radius', '1')

        with pytest.raises(MorphologyFilterException) as exc_info:
            morphology_processor._parse_morphology_parameters(element)

        assert "Invalid morphology operator: 'invalid-operator'" in str(exc_info.value)

    def test_parse_invalid_radius_raises_exception(self, morphology_processor, mock_context):
        """Test parsing invalid radius raises exception."""
        element = ET.Element('feMorphology')
        element.set('operator', 'dilate')
        element.set('radius', 'invalid-radius')

        with pytest.raises(MorphologyFilterException) as exc_info:
            morphology_processor._parse_morphology_parameters(element)

        assert "Failed to parse morphology parameters" in str(exc_info.value)

    def test_parse_negative_radius_raises_exception(self, morphology_processor, mock_context):
        """Test parsing negative radius raises exception."""
        element = ET.Element('feMorphology')
        element.set('operator', 'dilate')
        element.set('radius', '-5')

        with pytest.raises(MorphologyFilterException) as exc_info:
            morphology_processor._parse_morphology_parameters(element)

        assert "Radius values must be non-negative" in str(exc_info.value)

    def test_has_native_support_for_symmetric_small_radius(self, morphology_processor):
        """Test native support detection for symmetric small radius."""
        params = MorphologyParameters(
            operator=MorphologyOperator.DILATE,
            radius_x=5.0,
            radius_y=5.0
        )

        assert morphology_processor._has_native_support(params) is True

    def test_has_native_support_for_symmetric_moderate_radius(self, morphology_processor):
        """Test native support detection for symmetric moderate radius."""
        params = MorphologyParameters(
            operator=MorphologyOperator.ERODE,
            radius_x=10.0,
            radius_y=10.0
        )

        assert morphology_processor._has_native_support(params) is True

    def test_no_native_support_for_large_radius(self, morphology_processor):
        """Test no native support for large radius values."""
        params = MorphologyParameters(
            operator=MorphologyOperator.DILATE,
            radius_x=15.0,
            radius_y=15.0
        )

        assert morphology_processor._has_native_support(params) is False

    def test_no_native_support_for_asymmetric_radius(self, morphology_processor):
        """Test no native support for asymmetric radius values."""
        params = MorphologyParameters(
            operator=MorphologyOperator.DILATE,
            radius_x=5.0,
            radius_y=8.0  # Different values
        )

        assert morphology_processor._has_native_support(params) is False

    def test_has_approximation_support_for_moderate_radius(self, morphology_processor):
        """Test approximation support for moderate radius values."""
        params = MorphologyParameters(
            operator=MorphologyOperator.ERODE,
            radius_x=15.0,
            radius_y=12.0
        )

        assert morphology_processor._has_approximation_support(params) is True

    def test_no_approximation_support_for_extreme_radius(self, morphology_processor):
        """Test no approximation support for extreme radius values."""
        params = MorphologyParameters(
            operator=MorphologyOperator.DILATE,
            radius_x=25.0,
            radius_y=30.0
        )

        assert morphology_processor._has_approximation_support(params) is False

    def test_complexity_assessment_no_op(self, morphology_processor):
        """Test complexity assessment for no-op case."""
        params = MorphologyParameters(
            operator=MorphologyOperator.DILATE,
            radius_x=0.0,
            radius_y=0.0
        )

        complexity = morphology_processor._get_morphology_complexity(params)
        assert complexity == "no-op"

    def test_complexity_assessment_simple(self, morphology_processor):
        """Test complexity assessment for simple case."""
        params = MorphologyParameters(
            operator=MorphologyOperator.DILATE,
            radius_x=3.0,
            radius_y=3.0
        )

        complexity = morphology_processor._get_morphology_complexity(params)
        assert complexity == "simple"

    def test_complexity_assessment_moderate(self, morphology_processor):
        """Test complexity assessment for moderate case."""
        params = MorphologyParameters(
            operator=MorphologyOperator.ERODE,
            radius_x=8.0,
            radius_y=6.0
        )

        complexity = morphology_processor._get_morphology_complexity(params)
        assert complexity == "moderate"

    def test_complexity_assessment_extreme(self, morphology_processor):
        """Test complexity assessment for extreme case."""
        params = MorphologyParameters(
            operator=MorphologyOperator.DILATE,
            radius_x=25.0,
            radius_y=30.0
        )

        complexity = morphology_processor._get_morphology_complexity(params)
        assert complexity == "extreme"

    def test_generate_native_symmetric_dilate_drawingml(self, morphology_processor, mock_context):
        """Test generating native DrawingML for symmetric dilate."""
        params = MorphologyParameters(
            operator=MorphologyOperator.DILATE,
            radius_x=5.0,
            radius_y=5.0
        )

        drawingml = morphology_processor._generate_native_morphology_drawingml(params, mock_context)

        assert 'a:outerShdw' in drawingml
        assert 'dist="63500"' in drawingml  # 5px * 12700 EMU/px
        assert 'dir="0"' in drawingml
        assert 'sx="100000" sy="100000"' in drawingml
        assert 'Native morphology: dilate radius=5.0' in drawingml

    def test_generate_native_asymmetric_dilate_drawingml(self, morphology_processor, mock_context):
        """Test generating native DrawingML for asymmetric dilate."""
        params = MorphologyParameters(
            operator=MorphologyOperator.DILATE,
            radius_x=6.0,
            radius_y=3.0
        )

        drawingml = morphology_processor._generate_native_morphology_drawingml(params, mock_context)

        assert 'a:outerShdw' in drawingml
        assert 'asymmetric rx=6.0 ry=3.0' in drawingml
        assert 'sx=' in drawingml and 'sy=' in drawingml  # Proportional scaling

    def test_generate_native_symmetric_erode_drawingml(self, morphology_processor, mock_context):
        """Test generating native DrawingML for symmetric erode."""
        params = MorphologyParameters(
            operator=MorphologyOperator.ERODE,
            radius_x=4.0,
            radius_y=4.0
        )

        drawingml = morphology_processor._generate_native_morphology_drawingml(params, mock_context)

        assert 'a:innerShdw' in drawingml
        assert 'dist="50800"' in drawingml  # 4px * 12700 EMU/px
        assert 'dir="180"' in drawingml
        assert 'val="FFFFFF"' in drawingml  # White for erode
        assert 'Native morphology: erode radius=4.0' in drawingml

    def test_generate_native_zero_radius_no_op(self, morphology_processor, mock_context):
        """Test generating native DrawingML for zero radius (no-op)."""
        params = MorphologyParameters(
            operator=MorphologyOperator.DILATE,
            radius_x=0.0,
            radius_y=0.0
        )

        drawingml = morphology_processor._generate_native_morphology_drawingml(params, mock_context)

        assert 'No morphology operation: zero radius' in drawingml
        assert 'a:outerShdw' not in drawingml
        assert 'a:innerShdw' not in drawingml

    def test_generate_approximation_dilate_drawingml(self, morphology_processor, mock_context):
        """Test generating approximation DrawingML for dilate."""
        params = MorphologyParameters(
            operator=MorphologyOperator.DILATE,
            radius_x=15.0,
            radius_y=12.0
        )

        drawingml = morphology_processor._generate_approximation_morphology_drawingml(params, mock_context)

        assert 'a:outerShdw' in drawingml
        assert 'Approximated morphology: dilate simplified' in drawingml
        assert 'blurRad=' in drawingml  # Has blur for approximation
        assert 'alpha val="80000"' in drawingml  # Reduced opacity

    def test_generate_approximation_erode_drawingml(self, morphology_processor, mock_context):
        """Test generating approximation DrawingML for erode."""
        params = MorphologyParameters(
            operator=MorphologyOperator.ERODE,
            radius_x=18.0,
            radius_y=15.0
        )

        drawingml = morphology_processor._generate_approximation_morphology_drawingml(params, mock_context)

        assert 'a:innerShdw' in drawingml
        assert 'Approximated morphology: erode simplified' in drawingml
        assert 'dir="180"' in drawingml
        assert 'val="FFFFFF"' in drawingml

    def test_generate_raster_fallback_drawingml(self, morphology_processor, mock_context):
        """Test generating EMF raster fallback DrawingML."""
        params = MorphologyParameters(
            operator=MorphologyOperator.DILATE,
            radius_x=30.0,
            radius_y=25.0,
            input_source="effect1"
        )

        drawingml = morphology_processor._generate_raster_fallback_drawingml(params, mock_context)

        assert 'EMF rasterization required: complex morphology operation dilate' in drawingml
        assert 'a:blip' in drawingml
        assert 'r:morphology' in drawingml
        assert 'operator="dilate"' in drawingml
        assert 'radiusX="30.0"' in drawingml
        assert 'radiusY="25.0"' in drawingml
        assert 'in="effect1"' in drawingml

    def test_can_apply_returns_true(self, morphology_processor, mock_context):
        """Test can_apply returns True for morphology elements."""
        element = ET.Element('feMorphology')
        mock_context.element = element

        assert morphology_processor.can_apply(element, mock_context) is True

    def test_can_apply_returns_false_for_non_morphology(self, morphology_processor, mock_context):
        """Test can_apply returns False for non-morphology elements."""
        element = ET.Element('feGaussianBlur')
        mock_context.element = element

        assert morphology_processor.can_apply(element, mock_context) is False


class TestMorphologyProcessorIntegration:
    """Test MorphologyProcessor integration with policy and context."""

    @pytest.fixture
    def mock_policy(self):
        """Create mock policy with strategy decisions."""
        policy = Mock()
        return policy

    @pytest.fixture
    def morphology_processor(self, mock_policy):
        """Create MorphologyProcessor with mock policy."""
        return MorphologyProcessor(policy=mock_policy)

    @pytest.fixture
    def mock_context(self):
        """Create realistic filter context."""
        context = Mock(spec=FilterContext)
        context.viewport = {'width': 100, 'height': 100}
        context.unit_converter = Mock()
        context.transform_parser = Mock()
        context.color_parser = Mock()
        return context

    def test_apply_with_native_strategy(self, morphology_processor, mock_context, mock_policy):
        """Test apply with NATIVE strategy."""
        # Setup
        element = ET.Element('feMorphology')
        element.set('operator', 'dilate')
        element.set('radius', '5')
        mock_context.element = element

        mock_policy.decide_filter_strategy.return_value = FilterStrategy.NATIVE

        # Execute
        result = morphology_processor.apply(element, mock_context)

        # Verify
        assert isinstance(result, FilterResult)
        assert result.success is True
        assert result.strategy == FilterStrategy.NATIVE
        assert 'a:outerShdw' in result.drawingml
        assert result.metadata['operator'] == 'dilate'
        assert result.metadata['radius_x'] == 5.0
        assert result.metadata['radius_y'] == 5.0

    def test_apply_with_approximation_strategy(self, morphology_processor, mock_context, mock_policy):
        """Test apply with APPROXIMATION strategy."""
        # Setup
        element = ET.Element('feMorphology')
        element.set('operator', 'erode')
        element.set('radius', '15 12')
        mock_context.element = element

        mock_policy.decide_filter_strategy.return_value = FilterStrategy.APPROXIMATION

        # Execute
        result = morphology_processor.apply(element, mock_context)

        # Verify
        assert isinstance(result, FilterResult)
        assert result.success is True
        assert result.strategy == FilterStrategy.APPROXIMATION
        assert 'Approximated morphology' in result.drawingml
        assert result.metadata['operator'] == 'erode'

    def test_apply_with_emf_rasterize_strategy(self, morphology_processor, mock_context, mock_policy):
        """Test apply with EMF_RASTERIZE strategy."""
        # Setup
        element = ET.Element('feMorphology')
        element.set('operator', 'dilate')
        element.set('radius', '30 25')
        mock_context.element = element

        mock_policy.decide_filter_strategy.return_value = FilterStrategy.EMF_RASTERIZE

        # Execute
        result = morphology_processor.apply(element, mock_context)

        # Verify
        assert isinstance(result, FilterResult)
        assert result.success is True
        assert result.strategy == FilterStrategy.EMF_RASTERIZE
        assert 'EMF rasterization required' in result.drawingml
        assert result.metadata['operator'] == 'dilate'

    def test_apply_no_op_case(self, morphology_processor, mock_context, mock_policy):
        """Test apply with zero radius (no-op case)."""
        # Setup
        element = ET.Element('feMorphology')
        element.set('operator', 'dilate')
        element.set('radius', '0')
        mock_context.element = element

        mock_policy.decide_filter_strategy.return_value = FilterStrategy.NATIVE

        # Execute
        result = morphology_processor.apply(element, mock_context)

        # Verify
        assert isinstance(result, FilterResult)
        assert result.success is True
        assert result.strategy == FilterStrategy.NATIVE
        assert 'No morphology operation: zero radius' in result.drawingml
        assert result.metadata['max_radius'] == 0.0

    def test_apply_parsing_error_handling(self, morphology_processor, mock_context, mock_policy):
        """Test apply handles parsing errors gracefully."""
        # Setup invalid element
        element = ET.Element('feMorphology')
        element.set('radius', 'invalid-radius')
        mock_context.element = element

        mock_policy.decide_filter_strategy.return_value = FilterStrategy.NATIVE

        # Execute
        result = morphology_processor.apply(element, mock_context)

        # Verify error handling
        assert isinstance(result, FilterResult)
        assert result.success is False
        assert result.error_message is not None

    def test_policy_integration_calls_decide_filter_strategy(self, morphology_processor, mock_context, mock_policy):
        """Test policy integration calls decide_filter_strategy."""
        # Setup
        element = ET.Element('feMorphology')
        element.set('operator', 'erode')
        element.set('radius', '8')
        mock_context.element = element

        mock_policy.decide_filter_strategy.return_value = FilterStrategy.NATIVE

        # Execute
        morphology_processor.apply(element, mock_context)

        # Verify policy was called with correct parameters
        mock_policy.decide_filter_strategy.assert_called_once()
        call_args = mock_policy.decide_filter_strategy.call_args[1]
        assert call_args['filter_type'] == 'feMorphology'
        assert call_args['element'] == element
        # context argument is the decision context dict, not FilterContext
        assert 'context' in call_args

    def test_fallback_strategy_selection_without_policy(self, mock_context):
        """Test fallback strategy selection when no policy is available."""
        processor = MorphologyProcessor(policy=None)

        # Setup
        element = ET.Element('feMorphology')
        element.set('operator', 'dilate')
        element.set('radius', '5')
        mock_context.element = element

        # Execute
        result = processor.apply(element, mock_context)

        # Verify fallback logic works
        assert isinstance(result, FilterResult)
        assert result.success is True
        assert result.strategy == FilterStrategy.NATIVE  # Should use native for small symmetric radius


class TestMorphologyFilterException:
    """Test MorphologyFilterException error handling."""

    def test_exception_creation_with_message(self):
        """Test creating exception with message."""
        exception = MorphologyFilterException("Test error message")

        assert str(exception) == "Test error message"
        assert exception.args[0] == "Test error message"

    def test_exception_creation_with_message_and_cause(self):
        """Test creating exception with message and cause."""
        cause = ValueError("Original error")
        try:
            raise MorphologyFilterException("Morphology error") from cause
        except MorphologyFilterException as exception:
            assert str(exception) == "Morphology error"
            assert exception.__cause__ == cause

    def test_exception_inheritance(self):
        """Test exception inherits from FilterException."""
        exception = MorphologyFilterException("Test")

        assert isinstance(exception, FilterException)
        assert isinstance(exception, MorphologyFilterException)


class TestCreateMorphologyProcessor:
    """Test create_morphology_processor factory function."""

    def test_create_with_policy(self):
        """Test creating processor with policy."""
        policy = Mock()
        processor = create_morphology_processor(policy=policy)

        assert isinstance(processor, MorphologyProcessor)
        assert processor.policy == policy
        assert processor.filter_type == 'feMorphology'

    def test_create_without_policy(self):
        """Test creating processor without policy."""
        processor = create_morphology_processor()

        assert isinstance(processor, MorphologyProcessor)
        assert processor.policy is None
        assert processor.filter_type == 'feMorphology'


if __name__ == '__main__':
    pytest.main([__file__])