#!/usr/bin/env python3
"""
Tests for BlendProcessor - SVG feBlend filter implementation.

Validates blend mode operations with PowerPoint native support,
approximation strategies, and policy integration following the
established filter testing patterns.
"""

import pytest
from unittest.mock import Mock, MagicMock
from lxml import etree as ET

from core.filters.blend import (
    BlendProcessor,
    BlendParameters,
    BlendMode,
    BlendFilterException,
    create_blend_processor
)
from core.filters.base import (
    FilterContext,
    FilterStrategy,
    create_filter_context
)


class TestBlendProcessor:
    """Test core BlendProcessor functionality."""

    @pytest.fixture
    def processor(self):
        """Create BlendProcessor for testing."""
        return BlendProcessor('feBlend')

    @pytest.fixture
    def mock_policy(self):
        """Create mock policy for testing."""
        policy = Mock()
        policy.decide_filter_strategy.return_value = FilterStrategy.NATIVE
        return policy

    @pytest.fixture
    def processor_with_policy(self, mock_policy):
        """Create BlendProcessor with policy for testing."""
        return BlendProcessor('feBlend', mock_policy)

    @pytest.fixture
    def basic_context(self):
        """Create basic FilterContext for testing."""
        element = ET.Element('feBlend')
        return create_filter_context(
            element=element,
            viewport={'width': 100, 'height': 100}
        )

    def test_initialization_default(self):
        """Test BlendProcessor initialization with defaults."""
        processor = BlendProcessor()
        assert processor.filter_type == 'feBlend'
        assert processor.policy is None

    def test_initialization_with_parameters(self, mock_policy):
        """Test BlendProcessor initialization with parameters."""
        processor = BlendProcessor('customBlend', mock_policy)
        assert processor.filter_type == 'customBlend'
        assert processor.policy == mock_policy

    def test_can_apply_feblend_element(self, processor):
        """Test can_apply identifies feBlend elements."""
        element = ET.Element('feBlend')
        context = Mock()

        assert processor.can_apply(element, context) is True

    def test_can_apply_namespaced_feblend(self, processor):
        """Test can_apply handles namespaced feBlend elements."""
        element = ET.Element('{http://www.w3.org/2000/svg}feBlend')
        context = Mock()

        assert processor.can_apply(element, context) is True

    def test_can_apply_type_attribute(self, processor):
        """Test can_apply recognizes type attribute."""
        element = ET.Element('filter')
        element.set('type', 'feBlend')
        context = Mock()

        assert processor.can_apply(element, context) is True

    def test_can_apply_wrong_element(self, processor):
        """Test can_apply rejects non-blend elements."""
        element = ET.Element('feGaussianBlur')
        context = Mock()

        assert processor.can_apply(element, context) is False

    def test_can_apply_none_element(self, processor):
        """Test can_apply handles None element gracefully."""
        assert processor.can_apply(None, Mock()) is False


class TestBlendParameters:
    """Test BlendParameters parsing and validation."""

    @pytest.fixture
    def processor(self):
        """Create BlendProcessor for testing."""
        return BlendProcessor('feBlend')

    def test_parse_basic_blend_parameters(self, processor):
        """Test parsing basic blend parameters."""
        element = ET.Element('feBlend')
        element.set('mode', 'multiply')
        element.set('in', 'SourceGraphic')
        element.set('in2', 'BackgroundImage')

        params = processor._parse_blend_parameters(element)

        assert params.mode == BlendMode.MULTIPLY
        assert params.input1 == 'SourceGraphic'
        assert params.input2 == 'BackgroundImage'
        assert params.result_name == 'blend'  # default

    def test_parse_blend_with_result(self, processor):
        """Test parsing blend with custom result name."""
        element = ET.Element('feBlend')
        element.set('mode', 'screen')
        element.set('result', 'customBlend')

        params = processor._parse_blend_parameters(element)

        assert params.mode == BlendMode.SCREEN
        assert params.result_name == 'customBlend'

    def test_parse_blend_defaults(self, processor):
        """Test parsing with default values."""
        element = ET.Element('feBlend')

        params = processor._parse_blend_parameters(element)

        assert params.mode == BlendMode.NORMAL
        assert params.input1 == 'SourceGraphic'
        assert params.input2 == 'SourceGraphic'
        assert params.result_name == 'blend'

    def test_parse_invalid_blend_mode(self, processor):
        """Test parsing invalid blend mode raises exception."""
        element = ET.Element('feBlend')
        element.set('mode', 'invalid-mode')

        with pytest.raises(BlendFilterException) as exc_info:
            processor._parse_blend_parameters(element)

        assert "Invalid blend mode: 'invalid-mode'" in str(exc_info.value)

    def test_validate_valid_parameters(self, processor):
        """Test validation passes for valid parameters."""
        element = ET.Element('feBlend')
        element.set('mode', 'overlay')
        element.set('in', 'SourceGraphic')
        element.set('in2', 'BackgroundImage')

        context = Mock()
        assert processor._validate_parameters(element, context) is True

    def test_validate_missing_inputs(self, processor):
        """Test validation fails for missing inputs."""
        element = ET.Element('feBlend')
        element.set('mode', 'multiply')
        element.set('in', '')  # Empty input
        element.set('in2', 'BackgroundImage')

        context = Mock()
        assert processor._validate_parameters(element, context) is False


class TestBlendModeSupport:
    """Test blend mode support classification."""

    @pytest.fixture
    def processor(self):
        """Create BlendProcessor for testing."""
        return BlendProcessor('feBlend')

    def test_native_support_modes(self, processor):
        """Test native PowerPoint blend mode support."""
        native_modes = [
            BlendMode.NORMAL,
            BlendMode.MULTIPLY,
            BlendMode.SCREEN,
            BlendMode.OVERLAY,
            BlendMode.DARKEN,
            BlendMode.LIGHTEN
        ]

        for mode in native_modes:
            params = BlendParameters(mode=mode, input1='A', input2='B')
            assert processor._has_native_support(params) is True

    def test_approximation_support_modes(self, processor):
        """Test approximation blend mode support."""
        approximation_modes = [
            BlendMode.COLOR_DODGE,
            BlendMode.COLOR_BURN,
            BlendMode.HARD_LIGHT,
            BlendMode.SOFT_LIGHT,
            BlendMode.DIFFERENCE,
            BlendMode.EXCLUSION
        ]

        for mode in approximation_modes:
            params = BlendParameters(mode=mode, input1='A', input2='B')
            assert processor._has_native_support(params) is False
            assert processor._has_approximation_support(params) is True

    def test_blend_complexity_assessment(self, processor):
        """Test blend mode complexity classification."""
        # Simple modes
        simple_modes = [BlendMode.NORMAL, BlendMode.MULTIPLY, BlendMode.SCREEN]
        for mode in simple_modes:
            assert processor._get_blend_complexity(mode) == 'simple'

        # Moderate modes
        moderate_modes = [BlendMode.OVERLAY, BlendMode.DARKEN, BlendMode.LIGHTEN]
        for mode in moderate_modes:
            assert processor._get_blend_complexity(mode) == 'moderate'

        # Complex modes
        complex_modes = [BlendMode.COLOR_DODGE, BlendMode.HARD_LIGHT]
        for mode in complex_modes:
            assert processor._get_blend_complexity(mode) == 'complex'

    def test_powerpoint_mode_mapping(self, processor):
        """Test PowerPoint blend mode mapping."""
        # Native mappings
        assert processor._get_powerpoint_mode(BlendMode.NORMAL) == 'over'
        assert processor._get_powerpoint_mode(BlendMode.MULTIPLY) == 'mult'
        assert processor._get_powerpoint_mode(BlendMode.SCREEN) == 'screen'
        assert processor._get_powerpoint_mode(BlendMode.OVERLAY) == 'overlay'
        assert processor._get_powerpoint_mode(BlendMode.DARKEN) == 'darken'
        assert processor._get_powerpoint_mode(BlendMode.LIGHTEN) == 'lighten'

        # Approximation mappings
        assert processor._get_powerpoint_mode(BlendMode.COLOR_DODGE) == 'lighten'
        assert processor._get_powerpoint_mode(BlendMode.COLOR_BURN) == 'darken'
        assert processor._get_powerpoint_mode(BlendMode.HARD_LIGHT) == 'overlay'
        assert processor._get_powerpoint_mode(BlendMode.SOFT_LIGHT) == 'overlay'
        assert processor._get_powerpoint_mode(BlendMode.DIFFERENCE) == 'exclusion'
        assert processor._get_powerpoint_mode(BlendMode.EXCLUSION) == 'exclusion'


class TestBlendPolicyIntegration:
    """Test policy integration for strategy selection."""

    @pytest.fixture
    def mock_policy(self):
        """Create mock policy for testing."""
        return Mock()

    @pytest.fixture
    def processor_with_policy(self, mock_policy):
        """Create BlendProcessor with policy."""
        return BlendProcessor('feBlend', mock_policy)

    def test_policy_decision_native_strategy(self, processor_with_policy, mock_policy):
        """Test policy decision returns native strategy."""
        mock_policy.decide_filter_strategy.return_value = FilterStrategy.NATIVE

        params = BlendParameters(mode=BlendMode.MULTIPLY, input1='A', input2='B')
        context = Mock()
        context.element = ET.Element('feBlend')

        strategy = processor_with_policy._get_rendering_strategy(params, context)

        assert strategy == FilterStrategy.NATIVE
        mock_policy.decide_filter_strategy.assert_called_once()

    def test_policy_decision_approximation_strategy(self, processor_with_policy, mock_policy):
        """Test policy decision returns approximation strategy."""
        mock_policy.decide_filter_strategy.return_value = FilterStrategy.APPROXIMATION

        params = BlendParameters(mode=BlendMode.COLOR_DODGE, input1='A', input2='B')
        context = Mock()
        context.element = ET.Element('feBlend')

        strategy = processor_with_policy._get_rendering_strategy(params, context)

        assert strategy == FilterStrategy.APPROXIMATION

    def test_policy_decision_context_creation(self, processor_with_policy, mock_policy):
        """Test policy receives correct decision context."""
        mock_policy.decide_filter_strategy.return_value = FilterStrategy.NATIVE

        params = BlendParameters(mode=BlendMode.OVERLAY, input1='A', input2='B')
        context = Mock()
        context.element = ET.Element('feBlend')

        processor_with_policy._get_rendering_strategy(params, context)

        call_args = mock_policy.decide_filter_strategy.call_args
        assert call_args[1]['filter_type'] == 'feBlend'
        assert call_args[1]['context']['blend_mode'] == 'overlay'
        assert call_args[1]['context']['native_support'] is True
        assert call_args[1]['context']['complexity'] == 'moderate'

    def test_fallback_strategy_native_support(self):
        """Test fallback strategy for native support."""
        processor = BlendProcessor('feBlend')  # No policy

        params = BlendParameters(mode=BlendMode.MULTIPLY, input1='A', input2='B')
        context = Mock()

        strategy = processor._get_rendering_strategy(params, context)

        assert strategy == FilterStrategy.NATIVE

    def test_fallback_strategy_approximation_support(self):
        """Test fallback strategy for approximation support."""
        processor = BlendProcessor('feBlend')  # No policy

        params = BlendParameters(mode=BlendMode.COLOR_DODGE, input1='A', input2='B')
        context = Mock()

        strategy = processor._get_rendering_strategy(params, context)

        assert strategy == FilterStrategy.APPROXIMATION

    def test_policy_error_fallback(self, processor_with_policy, mock_policy):
        """Test fallback when policy decision fails."""
        mock_policy.decide_filter_strategy.side_effect = Exception("Policy error")

        params = BlendParameters(mode=BlendMode.SCREEN, input1='A', input2='B')
        context = Mock()
        context.element = ET.Element('feBlend')

        strategy = processor_with_policy._get_rendering_strategy(params, context)

        # Should fall back to native support
        assert strategy == FilterStrategy.NATIVE


class TestBlendDrawingMLGeneration:
    """Test DrawingML generation for different strategies."""

    @pytest.fixture
    def processor(self):
        """Create BlendProcessor for testing."""
        return BlendProcessor('feBlend')

    def test_native_blend_drawingml(self, processor):
        """Test native blend DrawingML generation."""
        params = BlendParameters(
            mode=BlendMode.MULTIPLY,
            input1='SourceGraphic',
            input2='BackgroundImage'
        )
        context = Mock()

        drawingml = processor._generate_native_blend_drawingml(params, context)

        assert '<a:blend blendMode="mult">' in drawingml
        assert 'Native blend: SourceGraphic multiply BackgroundImage' in drawingml
        assert '</a:blend>' in drawingml

    def test_approximation_blend_drawingml(self, processor):
        """Test approximation blend DrawingML generation."""
        params = BlendParameters(
            mode=BlendMode.COLOR_DODGE,
            input1='SourceGraphic',
            input2='BackgroundImage'
        )
        context = Mock()

        drawingml = processor._generate_approximation_blend_drawingml(params, context)

        assert '<a:blend blendMode="lighten">' in drawingml
        assert 'Approximated blend mode: color-dodge → lighten' in drawingml
        assert 'Inputs: SourceGraphic, BackgroundImage' in drawingml
        assert '</a:blend>' in drawingml

    def test_raster_fallback_drawingml(self, processor):
        """Test EMF raster fallback DrawingML generation."""
        params = BlendParameters(
            mode=BlendMode.DIFFERENCE,
            input1='SourceGraphic',
            input2='BackgroundImage'
        )
        context = Mock()

        drawingml = processor._generate_raster_fallback_drawingml(params, context)

        assert 'EMF rasterization required: complex blend mode difference' in drawingml
        assert '<a:blip>' in drawingml
        assert 'r:blend mode="difference"' in drawingml
        assert 'in1="SourceGraphic"' in drawingml
        assert 'in2="BackgroundImage"' in drawingml

    def test_strategy_based_generation_native(self, processor):
        """Test strategy-based generation for native strategy."""
        params = BlendParameters(mode=BlendMode.SCREEN, input1='A', input2='B')
        context = Mock()

        drawingml = processor._generate_blend_drawingml(params, context, FilterStrategy.NATIVE)

        assert '<a:blend blendMode="screen">' in drawingml

    def test_strategy_based_generation_approximation(self, processor):
        """Test strategy-based generation for approximation strategy."""
        params = BlendParameters(mode=BlendMode.HARD_LIGHT, input1='A', input2='B')
        context = Mock()

        drawingml = processor._generate_blend_drawingml(params, context, FilterStrategy.APPROXIMATION)

        assert 'Approximated blend mode: hard-light → overlay' in drawingml

    def test_strategy_based_generation_raster(self, processor):
        """Test strategy-based generation for raster strategy."""
        params = BlendParameters(mode=BlendMode.EXCLUSION, input1='A', input2='B')
        context = Mock()

        drawingml = processor._generate_blend_drawingml(params, context, FilterStrategy.EMF_RASTERIZE)

        assert 'EMF rasterization required' in drawingml


class TestBlendFilterIntegration:
    """Test comprehensive BlendProcessor integration."""

    @pytest.fixture
    def processor(self):
        """Create BlendProcessor for testing."""
        return BlendProcessor('feBlend')

    @pytest.fixture
    def mock_context(self):
        """Create mock FilterContext."""
        context = Mock()
        context.element = ET.Element('feBlend')
        context.viewport = {'width': 100, 'height': 100}
        return context

    def test_apply_successful_native_blend(self, processor, mock_context):
        """Test successful application with native blend mode."""
        element = ET.Element('feBlend')
        element.set('mode', 'multiply')
        element.set('in', 'SourceGraphic')
        element.set('in2', 'BackgroundImage')

        result = processor.apply(element, mock_context)

        assert result.success is True
        assert result.strategy == FilterStrategy.NATIVE
        assert '<a:blend blendMode="mult">' in result.drawingml
        assert result.metadata['mode'] == 'multiply'
        assert result.metadata['native_support'] is True

    def test_apply_successful_approximation_blend(self, processor, mock_context):
        """Test successful application with approximation blend mode."""
        element = ET.Element('feBlend')
        element.set('mode', 'color-dodge')
        element.set('in', 'SourceGraphic')
        element.set('in2', 'BackgroundImage')

        result = processor.apply(element, mock_context)

        assert result.success is True
        assert result.strategy == FilterStrategy.APPROXIMATION
        assert 'Approximated blend mode' in result.drawingml
        assert result.metadata['mode'] == 'color-dodge'
        assert result.metadata['native_support'] is False

    def test_apply_invalid_parameters(self, processor, mock_context):
        """Test application with invalid parameters."""
        element = ET.Element('feBlend')
        element.set('mode', 'invalid-mode')

        result = processor.apply(element, mock_context)

        assert result.success is False
        # The validation fails first, before we get to the parsing error
        assert 'Invalid feBlend parameters' in result.error_message

    def test_apply_comprehensive_metadata(self, processor, mock_context):
        """Test comprehensive metadata generation."""
        element = ET.Element('feBlend')
        element.set('mode', 'overlay')
        element.set('in', 'SourceGraphic')
        element.set('in2', 'BackgroundImage')
        element.set('result', 'blendResult')

        result = processor.apply(element, mock_context)

        metadata = result.metadata
        assert metadata['filter_type'] == 'feBlend'
        assert metadata['mode'] == 'overlay'
        assert metadata['input1'] == 'SourceGraphic'
        assert metadata['input2'] == 'BackgroundImage'
        assert metadata['result_name'] == 'blendResult'
        assert metadata['strategy_value'] == 'native'
        assert metadata['powerpoint_mode'] == 'overlay'
        assert metadata['blend_complexity'] == 'moderate'

    def test_apply_with_policy_integration(self, mock_context):
        """Test application with policy integration."""
        mock_policy = Mock()
        mock_policy.decide_filter_strategy.return_value = FilterStrategy.APPROXIMATION

        processor = BlendProcessor('feBlend', mock_policy)

        element = ET.Element('feBlend')
        element.set('mode', 'multiply')  # Normally native, but policy overrides

        result = processor.apply(element, mock_context)

        assert result.success is True
        assert result.strategy == FilterStrategy.APPROXIMATION
        mock_policy.decide_filter_strategy.assert_called_once()


class TestBlendProcessorFactory:
    """Test BlendProcessor factory function."""

    def test_create_blend_processor_default(self):
        """Test creating BlendProcessor with defaults."""
        processor = create_blend_processor()

        assert isinstance(processor, BlendProcessor)
        assert processor.filter_type == 'feBlend'
        assert processor.policy is None

    def test_create_blend_processor_with_policy(self):
        """Test creating BlendProcessor with policy."""
        mock_policy = Mock()
        processor = create_blend_processor(mock_policy)

        assert isinstance(processor, BlendProcessor)
        assert processor.filter_type == 'feBlend'
        assert processor.policy == mock_policy


class TestBlendProcessorErrorHandling:
    """Test BlendProcessor error handling."""

    @pytest.fixture
    def processor(self):
        """Create BlendProcessor for testing."""
        return BlendProcessor('feBlend')

    def test_malformed_element_handling(self, processor):
        """Test handling of malformed elements."""
        element = ET.Element('feBlend')
        # Create intentionally malformed setup
        context = Mock()

        # Override validation to force error path
        processor._validate_parameters = Mock(return_value=False)

        result = processor.apply(element, context)

        assert result.success is False
        assert 'Invalid feBlend parameters' in result.error_message

    def test_unexpected_error_handling(self, processor):
        """Test handling of unexpected errors."""
        element = ET.Element('feBlend')
        element.set('mode', 'multiply')  # Valid to pass validation
        context = Mock()

        # Force unexpected error after validation passes
        processor._generate_blend_drawingml = Mock(side_effect=Exception("Unexpected error"))

        result = processor.apply(element, context)

        assert result.success is False
        assert 'Blend processing failed' in result.error_message

    def test_processing_method_description(self, processor):
        """Test processing method descriptions."""
        assert processor._get_processing_method(FilterStrategy.NATIVE) == 'Native PowerPoint blend modes'
        assert processor._get_processing_method(FilterStrategy.APPROXIMATION) == 'Approximated blend mode mapping'
        assert processor._get_processing_method(FilterStrategy.EMF_RASTERIZE) == 'EMF rasterization fallback'


if __name__ == '__main__':
    pytest.main([__file__])