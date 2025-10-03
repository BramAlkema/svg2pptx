#!/usr/bin/env python3
"""
Tests for ColorMatrixProcessor - SVG feColorMatrix filter implementation.

Validates color matrix operations with PowerPoint native support,
approximation strategies, and policy integration following the
established filter testing patterns.
"""

import pytest
from unittest.mock import Mock, MagicMock
from lxml import etree as ET

from core.filters.color_matrix import (
    ColorMatrixProcessor,
    ColorMatrixParameters,
    ColorMatrixType,
    ColorMatrixFilterException,
    create_color_matrix_processor
)
from core.filters.base import (
    FilterContext,
    FilterStrategy,
    create_filter_context
)


class TestColorMatrixProcessor:
    """Test core ColorMatrixProcessor functionality."""

    @pytest.fixture
    def processor(self):
        """Create ColorMatrixProcessor for testing."""
        return ColorMatrixProcessor('feColorMatrix')

    @pytest.fixture
    def mock_policy(self):
        """Create mock policy for testing."""
        policy = Mock()
        policy.decide_filter_strategy.return_value = FilterStrategy.NATIVE
        return policy

    @pytest.fixture
    def processor_with_policy(self, mock_policy):
        """Create ColorMatrixProcessor with policy for testing."""
        return ColorMatrixProcessor('feColorMatrix', mock_policy)

    @pytest.fixture
    def basic_context(self):
        """Create basic FilterContext for testing."""
        element = ET.Element('feColorMatrix')
        return create_filter_context(
            element=element,
            viewport={'width': 100, 'height': 100}
        )

    def test_initialization_default(self):
        """Test ColorMatrixProcessor initialization with defaults."""
        processor = ColorMatrixProcessor()
        assert processor.filter_type == 'feColorMatrix'
        assert processor.policy is None

    def test_initialization_with_parameters(self, mock_policy):
        """Test ColorMatrixProcessor initialization with parameters."""
        processor = ColorMatrixProcessor('customColorMatrix', mock_policy)
        assert processor.filter_type == 'customColorMatrix'
        assert processor.policy == mock_policy

    def test_can_apply_fecolormatrix_element(self, processor):
        """Test can_apply identifies feColorMatrix elements."""
        element = ET.Element('feColorMatrix')
        context = Mock()

        assert processor.can_apply(element, context) is True

    def test_can_apply_namespaced_fecolormatrix(self, processor):
        """Test can_apply handles namespaced feColorMatrix elements."""
        element = ET.Element('{http://www.w3.org/2000/svg}feColorMatrix')
        context = Mock()

        assert processor.can_apply(element, context) is True

    def test_can_apply_type_attribute(self, processor):
        """Test can_apply recognizes type attribute."""
        element = ET.Element('filter')
        element.set('type', 'feColorMatrix')
        context = Mock()

        assert processor.can_apply(element, context) is True

    def test_can_apply_wrong_element(self, processor):
        """Test can_apply rejects non-colormatrix elements."""
        element = ET.Element('feGaussianBlur')
        context = Mock()

        assert processor.can_apply(element, context) is False

    def test_can_apply_none_element(self, processor):
        """Test can_apply handles None element gracefully."""
        assert processor.can_apply(None, Mock()) is False


class TestColorMatrixParameters:
    """Test ColorMatrixParameters parsing and validation."""

    @pytest.fixture
    def processor(self):
        """Create ColorMatrixProcessor for testing."""
        return ColorMatrixProcessor('feColorMatrix')

    def test_parse_saturate_parameters(self, processor):
        """Test parsing saturate parameters."""
        element = ET.Element('feColorMatrix')
        element.set('type', 'saturate')
        element.set('values', '0.5')

        params = processor._parse_color_matrix_parameters(element)

        assert params.matrix_type == ColorMatrixType.SATURATE
        assert params.values == [0.5]
        assert params.input_source == 'SourceGraphic'
        assert params.result_name == 'colorMatrix'

    def test_parse_hue_rotate_parameters(self, processor):
        """Test parsing hue rotate parameters."""
        element = ET.Element('feColorMatrix')
        element.set('type', 'hueRotate')
        element.set('values', '90')
        element.set('result', 'hueRotated')

        params = processor._parse_color_matrix_parameters(element)

        assert params.matrix_type == ColorMatrixType.HUE_ROTATE
        assert params.values == [90.0]
        assert params.result_name == 'hueRotated'

    def test_parse_matrix_parameters(self, processor):
        """Test parsing full matrix parameters."""
        element = ET.Element('feColorMatrix')
        element.set('type', 'matrix')
        element.set('values', '1 0 0 0 0.2 0 1 0 0 0 0 0 1 0 0 0 0 0 1 0')

        params = processor._parse_color_matrix_parameters(element)

        assert params.matrix_type == ColorMatrixType.MATRIX
        assert len(params.values) == 20
        assert params.values[4] == 0.2  # Red offset

    def test_parse_luminance_alpha_parameters(self, processor):
        """Test parsing luminanceToAlpha parameters."""
        element = ET.Element('feColorMatrix')
        element.set('type', 'luminanceToAlpha')

        params = processor._parse_color_matrix_parameters(element)

        assert params.matrix_type == ColorMatrixType.LUMINANCE_TO_ALPHA
        assert params.values == []

    def test_parse_matrix_with_comma_separation(self, processor):
        """Test parsing matrix with comma-separated values."""
        element = ET.Element('feColorMatrix')
        element.set('type', 'matrix')
        element.set('values', '1,0,0,0,0,0,1,0,0,0,0,0,1,0,0,0,0,0,1,0')

        params = processor._parse_color_matrix_parameters(element)

        assert len(params.values) == 20
        assert params.values[0] == 1.0

    def test_parse_default_values(self, processor):
        """Test parsing with default values."""
        element = ET.Element('feColorMatrix')

        params = processor._parse_color_matrix_parameters(element)

        assert params.matrix_type == ColorMatrixType.MATRIX
        assert len(params.values) == 20
        # Should be identity matrix
        assert params.values[0] == 1.0  # R->R
        assert params.values[6] == 1.0  # G->G
        assert params.values[12] == 1.0  # B->B

    def test_parse_invalid_matrix_type(self, processor):
        """Test parsing invalid matrix type raises exception."""
        element = ET.Element('feColorMatrix')
        element.set('type', 'invalid-type')

        with pytest.raises(ColorMatrixFilterException) as exc_info:
            processor._parse_color_matrix_parameters(element)

        assert "Invalid matrix type: 'invalid-type'" in str(exc_info.value)

    def test_parse_invalid_matrix_values_count(self, processor):
        """Test parsing invalid matrix values count raises exception."""
        element = ET.Element('feColorMatrix')
        element.set('type', 'matrix')
        element.set('values', '1 0 0')  # Too few values

        with pytest.raises(ColorMatrixFilterException) as exc_info:
            processor._parse_color_matrix_parameters(element)

        assert "Matrix requires 20 values" in str(exc_info.value)

    def test_parse_invalid_saturate_value(self, processor):
        """Test parsing invalid saturate value raises exception."""
        element = ET.Element('feColorMatrix')
        element.set('type', 'saturate')
        element.set('values', 'invalid')

        with pytest.raises(ColorMatrixFilterException) as exc_info:
            processor._parse_color_matrix_parameters(element)

        assert "Invalid saturate value" in str(exc_info.value)

    def test_validate_valid_parameters(self, processor):
        """Test validation passes for valid parameters."""
        element = ET.Element('feColorMatrix')
        element.set('type', 'saturate')
        element.set('values', '0.5')

        context = Mock()
        assert processor._validate_parameters(element, context) is True

    def test_validate_invalid_saturate_negative(self, processor):
        """Test validation fails for negative saturate value."""
        element = ET.Element('feColorMatrix')
        element.set('type', 'saturate')
        element.set('values', '-0.5')

        context = Mock()
        assert processor._validate_parameters(element, context) is False


class TestColorMatrixSupport:
    """Test color matrix support classification."""

    @pytest.fixture
    def processor(self):
        """Create ColorMatrixProcessor for testing."""
        return ColorMatrixProcessor('feColorMatrix')

    def test_native_support_saturate(self, processor):
        """Test native support for saturate operation."""
        params = ColorMatrixParameters(
            matrix_type=ColorMatrixType.SATURATE,
            values=[0.5]
        )
        assert processor._has_native_support(params) is True

    def test_native_support_hue_rotate(self, processor):
        """Test native support for hue rotate operation."""
        params = ColorMatrixParameters(
            matrix_type=ColorMatrixType.HUE_ROTATE,
            values=[90.0]
        )
        assert processor._has_native_support(params) is True

    def test_native_support_simple_matrix(self, processor):
        """Test native support for simple matrix."""
        # Identity matrix with small brightness adjustment
        params = ColorMatrixParameters(
            matrix_type=ColorMatrixType.MATRIX,
            values=[1,0,0,0,0.1, 0,1,0,0,0.1, 0,0,1,0,0.1, 0,0,0,1,0]
        )
        assert processor._has_native_support(params) is True

    def test_no_native_support_complex_matrix(self, processor):
        """Test no native support for complex matrix."""
        # Complex matrix with many changes
        params = ColorMatrixParameters(
            matrix_type=ColorMatrixType.MATRIX,
            values=[0.5,0.3,0.2,0,0.1, 0.2,0.8,0.1,0,0, 0.1,0.2,0.9,0,0, 0,0,0,1,0]
        )
        assert processor._has_native_support(params) is False

    def test_no_native_support_luminance_alpha(self, processor):
        """Test no native support for luminanceToAlpha."""
        params = ColorMatrixParameters(
            matrix_type=ColorMatrixType.LUMINANCE_TO_ALPHA,
            values=[]
        )
        assert processor._has_native_support(params) is False

    def test_approximation_support_luminance_alpha(self, processor):
        """Test approximation support for luminanceToAlpha."""
        params = ColorMatrixParameters(
            matrix_type=ColorMatrixType.LUMINANCE_TO_ALPHA,
            values=[]
        )
        assert processor._has_approximation_support(params) is True

    def test_approximation_support_complex_matrix(self, processor):
        """Test approximation support for complex matrix."""
        params = ColorMatrixParameters(
            matrix_type=ColorMatrixType.MATRIX,
            values=[0.5,0.3,0.2,0,0.1, 0.2,0.8,0.1,0,0, 0.1,0.2,0.9,0,0, 0,0,0,1,0]
        )
        assert processor._has_approximation_support(params) is True

    def test_matrix_complexity_assessment(self, processor):
        """Test matrix complexity classification."""
        # Simple operations
        simple_saturate = ColorMatrixParameters(
            matrix_type=ColorMatrixType.SATURATE,
            values=[0.5]
        )
        assert processor._get_matrix_complexity(simple_saturate) == 'simple'

        simple_hue = ColorMatrixParameters(
            matrix_type=ColorMatrixType.HUE_ROTATE,
            values=[90.0]
        )
        assert processor._get_matrix_complexity(simple_hue) == 'simple'

        # Moderate operation
        luminance = ColorMatrixParameters(
            matrix_type=ColorMatrixType.LUMINANCE_TO_ALPHA,
            values=[]
        )
        assert processor._get_matrix_complexity(luminance) == 'moderate'

        # Simple matrix
        simple_matrix = ColorMatrixParameters(
            matrix_type=ColorMatrixType.MATRIX,
            values=[1,0,0,0,0.1, 0,1,0,0,0, 0,0,1,0,0, 0,0,0,1,0]
        )
        assert processor._get_matrix_complexity(simple_matrix) == 'simple'

        # Complex matrix
        complex_matrix = ColorMatrixParameters(
            matrix_type=ColorMatrixType.MATRIX,
            values=[0.5,0.3,0.2,0,0.1, 0.2,0.8,0.1,0,0, 0.1,0.2,0.9,0,0, 0,0,0,1,0]
        )
        assert processor._get_matrix_complexity(complex_matrix) == 'complex'

    def test_is_simple_matrix(self, processor):
        """Test simple matrix detection."""
        # Identity matrix
        identity = [1,0,0,0,0, 0,1,0,0,0, 0,0,1,0,0, 0,0,0,1,0]
        assert processor._is_simple_matrix(identity) is True

        # Matrix with few changes
        simple = [1,0,0,0,0.1, 0,1,0,0,0, 0,0,1,0,0, 0,0,0,1,0]
        assert processor._is_simple_matrix(simple) is True

        # Matrix with many changes
        complex_matrix = [0.5,0.3,0.2,0,0.1, 0.2,0.8,0.1,0,0, 0.1,0.2,0.9,0,0, 0,0,0,1,0]
        assert processor._is_simple_matrix(complex_matrix) is False


class TestColorMatrixPolicyIntegration:
    """Test policy integration for strategy selection."""

    @pytest.fixture
    def mock_policy(self):
        """Create mock policy for testing."""
        return Mock()

    @pytest.fixture
    def processor_with_policy(self, mock_policy):
        """Create ColorMatrixProcessor with policy."""
        return ColorMatrixProcessor('feColorMatrix', mock_policy)

    def test_policy_decision_native_strategy(self, processor_with_policy, mock_policy):
        """Test policy decision returns native strategy."""
        mock_policy.decide_filter_strategy.return_value = FilterStrategy.NATIVE

        params = ColorMatrixParameters(
            matrix_type=ColorMatrixType.SATURATE,
            values=[0.5]
        )
        context = Mock()
        context.element = ET.Element('feColorMatrix')

        strategy = processor_with_policy._get_rendering_strategy(params, context)

        assert strategy == FilterStrategy.NATIVE
        mock_policy.decide_filter_strategy.assert_called_once()

    def test_policy_decision_approximation_strategy(self, processor_with_policy, mock_policy):
        """Test policy decision returns approximation strategy."""
        mock_policy.decide_filter_strategy.return_value = FilterStrategy.APPROXIMATION

        params = ColorMatrixParameters(
            matrix_type=ColorMatrixType.LUMINANCE_TO_ALPHA,
            values=[]
        )
        context = Mock()
        context.element = ET.Element('feColorMatrix')

        strategy = processor_with_policy._get_rendering_strategy(params, context)

        assert strategy == FilterStrategy.APPROXIMATION

    def test_policy_decision_context_creation(self, processor_with_policy, mock_policy):
        """Test policy receives correct decision context."""
        mock_policy.decide_filter_strategy.return_value = FilterStrategy.NATIVE

        params = ColorMatrixParameters(
            matrix_type=ColorMatrixType.HUE_ROTATE,
            values=[90.0]
        )
        context = Mock()
        context.element = ET.Element('feColorMatrix')

        processor_with_policy._get_rendering_strategy(params, context)

        call_args = mock_policy.decide_filter_strategy.call_args
        assert call_args[1]['filter_type'] == 'feColorMatrix'
        assert call_args[1]['context']['matrix_type'] == 'hueRotate'
        assert call_args[1]['context']['values_count'] == 1
        assert call_args[1]['context']['native_support'] is True
        assert call_args[1]['context']['complexity'] == 'simple'

    def test_fallback_strategy_native_support(self):
        """Test fallback strategy for native support."""
        processor = ColorMatrixProcessor('feColorMatrix')  # No policy

        params = ColorMatrixParameters(
            matrix_type=ColorMatrixType.SATURATE,
            values=[0.5]
        )
        context = Mock()

        strategy = processor._get_rendering_strategy(params, context)

        assert strategy == FilterStrategy.NATIVE

    def test_fallback_strategy_approximation_support(self):
        """Test fallback strategy for approximation support."""
        processor = ColorMatrixProcessor('feColorMatrix')  # No policy

        params = ColorMatrixParameters(
            matrix_type=ColorMatrixType.LUMINANCE_TO_ALPHA,
            values=[]
        )
        context = Mock()

        strategy = processor._get_rendering_strategy(params, context)

        assert strategy == FilterStrategy.APPROXIMATION

    def test_policy_error_fallback(self, processor_with_policy, mock_policy):
        """Test fallback when policy decision fails."""
        mock_policy.decide_filter_strategy.side_effect = Exception("Policy error")

        params = ColorMatrixParameters(
            matrix_type=ColorMatrixType.SATURATE,
            values=[0.5]
        )
        context = Mock()
        context.element = ET.Element('feColorMatrix')

        strategy = processor_with_policy._get_rendering_strategy(params, context)

        # Should fall back to native support
        assert strategy == FilterStrategy.NATIVE


class TestColorMatrixDrawingMLGeneration:
    """Test DrawingML generation for different strategies."""

    @pytest.fixture
    def processor(self):
        """Create ColorMatrixProcessor for testing."""
        return ColorMatrixProcessor('feColorMatrix')

    def test_saturate_drawingml_grayscale(self, processor):
        """Test saturation DrawingML generation for grayscale."""
        drawingml = processor._generate_saturation_drawingml(0.0)
        assert '<a:grayscl/>' in drawingml

    def test_saturate_drawingml_normal(self, processor):
        """Test saturation DrawingML generation for normal."""
        drawingml = processor._generate_saturation_drawingml(1.0)
        assert 'No saturation effect needed' in drawingml

    def test_saturate_drawingml_oversaturate(self, processor):
        """Test saturation DrawingML generation for oversaturation."""
        drawingml = processor._generate_saturation_drawingml(1.5)
        assert '<a:tint val=' in drawingml

    def test_hue_rotate_drawingml(self, processor):
        """Test hue rotation DrawingML generation."""
        drawingml = processor._generate_hue_rotate_drawingml(90.0)
        assert '<a:hue val=' in drawingml
        assert 'val="5400000"' in drawingml  # 90 degrees in PowerPoint units

    def test_luminance_alpha_drawingml(self, processor):
        """Test luminance-to-alpha DrawingML generation."""
        drawingml = processor._generate_luminance_alpha_drawingml()
        assert '<a:alpha val="50000"/>' in drawingml
        assert 'Luminance to alpha approximation' in drawingml

    def test_simple_matrix_drawingml_brightness(self, processor):
        """Test simple matrix DrawingML for brightness adjustment."""
        # Matrix with brightness offset
        values = [1,0,0,0,0.1, 0,1,0,0,0.1, 0,0,1,0,0.1, 0,0,0,1,0]
        drawingml = processor._generate_simple_matrix_drawingml(values)
        assert '<a:lumMod val=' in drawingml

    def test_simple_matrix_drawingml_color_adjust(self, processor):
        """Test simple matrix DrawingML for color channel adjustment."""
        # Matrix with color channel adjustments
        values = [1.2,0,0,0,0, 0,1.1,0,0,0, 0,0,0.9,0,0, 0,0,0,1,0]
        drawingml = processor._generate_simple_matrix_drawingml(values)
        assert '<a:tint val=' in drawingml

    def test_complex_matrix_drawingml(self, processor):
        """Test complex matrix DrawingML generation."""
        values = [0.5,0.3,0.2,0,0.1, 0.2,0.8,0.1,0,0, 0.1,0.2,0.9,0,0, 0,0,0,1,0]
        drawingml = processor._generate_complex_matrix_drawingml(values)
        assert 'Complex color matrix approximation' in drawingml
        assert '<a:tint val="10000"/>' in drawingml

    def test_raster_fallback_drawingml(self, processor):
        """Test EMF raster fallback DrawingML generation."""
        params = ColorMatrixParameters(
            matrix_type=ColorMatrixType.MATRIX,
            values=[0.5,0.3,0.2,0,0.1, 0.2,0.8,0.1,0,0, 0.1,0.2,0.9,0,0, 0,0,0,1,0]
        )
        context = Mock()

        drawingml = processor._generate_raster_fallback_drawingml(params, context)

        assert 'EMF rasterization required' in drawingml
        assert '<a:blip>' in drawingml
        assert 'r:colorMatrix type="matrix"' in drawingml

    def test_strategy_based_generation_native(self, processor):
        """Test strategy-based generation for native strategy."""
        params = ColorMatrixParameters(
            matrix_type=ColorMatrixType.SATURATE,
            values=[0.5]
        )
        context = Mock()

        drawingml = processor._generate_color_matrix_drawingml(params, context, FilterStrategy.NATIVE)

        assert '<a:grayscl/>' in drawingml

    def test_strategy_based_generation_approximation(self, processor):
        """Test strategy-based generation for approximation strategy."""
        params = ColorMatrixParameters(
            matrix_type=ColorMatrixType.LUMINANCE_TO_ALPHA,
            values=[]
        )
        context = Mock()

        drawingml = processor._generate_color_matrix_drawingml(params, context, FilterStrategy.APPROXIMATION)

        assert 'Luminance to alpha approximation' in drawingml

    def test_strategy_based_generation_raster(self, processor):
        """Test strategy-based generation for raster strategy."""
        params = ColorMatrixParameters(
            matrix_type=ColorMatrixType.MATRIX,
            values=[0.5,0.3,0.2,0,0.1, 0.2,0.8,0.1,0,0, 0.1,0.2,0.9,0,0, 0,0,0,1,0]
        )
        context = Mock()

        drawingml = processor._generate_color_matrix_drawingml(params, context, FilterStrategy.EMF_RASTERIZE)

        assert 'EMF rasterization required' in drawingml


class TestColorMatrixFilterIntegration:
    """Test comprehensive ColorMatrixProcessor integration."""

    @pytest.fixture
    def processor(self):
        """Create ColorMatrixProcessor for testing."""
        return ColorMatrixProcessor('feColorMatrix')

    @pytest.fixture
    def mock_context(self):
        """Create mock FilterContext."""
        context = Mock()
        context.element = ET.Element('feColorMatrix')
        context.viewport = {'width': 100, 'height': 100}
        return context

    def test_apply_successful_saturate_operation(self, processor, mock_context):
        """Test successful application with saturate operation."""
        element = ET.Element('feColorMatrix')
        element.set('type', 'saturate')
        element.set('values', '0.5')

        result = processor.apply(element, mock_context)

        assert result.success is True
        assert result.strategy == FilterStrategy.NATIVE
        assert '<a:grayscl/>' in result.drawingml
        assert result.metadata['matrix_type'] == 'saturate'
        assert result.metadata['native_support'] is True

    def test_apply_successful_hue_rotate_operation(self, processor, mock_context):
        """Test successful application with hue rotate operation."""
        element = ET.Element('feColorMatrix')
        element.set('type', 'hueRotate')
        element.set('values', '90')

        result = processor.apply(element, mock_context)

        assert result.success is True
        assert result.strategy == FilterStrategy.NATIVE
        assert '<a:hue val=' in result.drawingml
        assert result.metadata['matrix_type'] == 'hueRotate'

    def test_apply_successful_matrix_operation(self, processor, mock_context):
        """Test successful application with matrix operation."""
        element = ET.Element('feColorMatrix')
        element.set('type', 'matrix')
        element.set('values', '1 0 0 0 0.1 0 1 0 0 0 0 0 1 0 0 0 0 0 1 0')

        result = processor.apply(element, mock_context)

        assert result.success is True
        assert result.strategy == FilterStrategy.NATIVE
        assert result.metadata['matrix_type'] == 'matrix'
        assert result.metadata['values_count'] == 20

    def test_apply_luminance_alpha_approximation(self, processor, mock_context):
        """Test application with luminanceToAlpha requiring approximation."""
        element = ET.Element('feColorMatrix')
        element.set('type', 'luminanceToAlpha')

        result = processor.apply(element, mock_context)

        assert result.success is True
        assert result.strategy == FilterStrategy.APPROXIMATION
        assert 'Luminance to alpha approximation' in result.drawingml
        assert result.metadata['matrix_type'] == 'luminanceToAlpha'

    def test_apply_invalid_parameters(self, processor, mock_context):
        """Test application with invalid parameters."""
        element = ET.Element('feColorMatrix')
        element.set('type', 'invalid-type')

        result = processor.apply(element, mock_context)

        assert result.success is False
        assert 'Invalid feColorMatrix parameters' in result.error_message

    def test_apply_comprehensive_metadata(self, processor, mock_context):
        """Test comprehensive metadata generation."""
        element = ET.Element('feColorMatrix')
        element.set('type', 'saturate')
        element.set('values', '0.8')
        element.set('in', 'SourceGraphic')
        element.set('result', 'saturateResult')

        result = processor.apply(element, mock_context)

        metadata = result.metadata
        assert metadata['filter_type'] == 'feColorMatrix'
        assert metadata['matrix_type'] == 'saturate'
        assert metadata['values_count'] == 1
        assert metadata['input_source'] == 'SourceGraphic'
        assert metadata['result_name'] == 'saturateResult'
        assert metadata['strategy_value'] == 'native'
        assert metadata['matrix_complexity'] == 'simple'

    def test_apply_with_policy_integration(self, mock_context):
        """Test application with policy integration."""
        mock_policy = Mock()
        mock_policy.decide_filter_strategy.return_value = FilterStrategy.APPROXIMATION

        processor = ColorMatrixProcessor('feColorMatrix', mock_policy)

        element = ET.Element('feColorMatrix')
        element.set('type', 'saturate')  # Normally native, but policy overrides
        element.set('values', '0.5')

        result = processor.apply(element, mock_context)

        assert result.success is True
        assert result.strategy == FilterStrategy.APPROXIMATION
        mock_policy.decide_filter_strategy.assert_called_once()


class TestColorMatrixProcessorFactory:
    """Test ColorMatrixProcessor factory function."""

    def test_create_color_matrix_processor_default(self):
        """Test creating ColorMatrixProcessor with defaults."""
        processor = create_color_matrix_processor()

        assert isinstance(processor, ColorMatrixProcessor)
        assert processor.filter_type == 'feColorMatrix'
        assert processor.policy is None

    def test_create_color_matrix_processor_with_policy(self):
        """Test creating ColorMatrixProcessor with policy."""
        mock_policy = Mock()
        processor = create_color_matrix_processor(mock_policy)

        assert isinstance(processor, ColorMatrixProcessor)
        assert processor.filter_type == 'feColorMatrix'
        assert processor.policy == mock_policy


class TestColorMatrixProcessorErrorHandling:
    """Test ColorMatrixProcessor error handling."""

    @pytest.fixture
    def processor(self):
        """Create ColorMatrixProcessor for testing."""
        return ColorMatrixProcessor('feColorMatrix')

    def test_malformed_element_handling(self, processor):
        """Test handling of malformed elements."""
        element = ET.Element('feColorMatrix')
        element.set('type', 'matrix')
        element.set('values', 'invalid values')
        context = Mock()

        result = processor.apply(element, context)

        assert result.success is False
        assert 'Invalid feColorMatrix parameters' in result.error_message

    def test_unexpected_error_handling(self, processor):
        """Test handling of unexpected errors."""
        element = ET.Element('feColorMatrix')
        element.set('type', 'saturate')  # Valid to pass validation
        element.set('values', '0.5')
        context = Mock()

        # Force unexpected error after validation passes
        processor._generate_color_matrix_drawingml = Mock(side_effect=Exception("Unexpected error"))

        result = processor.apply(element, context)

        assert result.success is False
        assert 'Color matrix processing failed' in result.error_message

    def test_processing_method_description(self, processor):
        """Test processing method descriptions."""
        assert processor._get_processing_method(FilterStrategy.NATIVE) == 'Native PowerPoint color effects'
        assert processor._get_processing_method(FilterStrategy.APPROXIMATION) == 'Approximated color matrix mapping'
        assert processor._get_processing_method(FilterStrategy.EMF_RASTERIZE) == 'EMF rasterization fallback'

    def test_parse_matrix_values_flexibility(self, processor):
        """Test flexible matrix value parsing."""
        # Space-separated
        values1 = processor._parse_matrix_values('1.0 0.5 0.2')
        assert values1 == [1.0, 0.5, 0.2]

        # Comma-separated
        values2 = processor._parse_matrix_values('1.0,0.5,0.2')
        assert values2 == [1.0, 0.5, 0.2]

        # Mixed separators
        values3 = processor._parse_matrix_values('1.0, 0.5 0.2')
        assert values3 == [1.0, 0.5, 0.2]

        # Empty string
        values4 = processor._parse_matrix_values('')
        assert values4 == []


class TestColorMatrixParametersClass:
    """Test ColorMatrixParameters dataclass."""

    def test_color_matrix_parameters_defaults(self):
        """Test ColorMatrixParameters with defaults."""
        params = ColorMatrixParameters(
            matrix_type=ColorMatrixType.SATURATE,
            values=[0.5]
        )

        assert params.matrix_type == ColorMatrixType.SATURATE
        assert params.values == [0.5]
        assert params.input_source == "SourceGraphic"
        assert params.result_name == "colorMatrix"

    def test_color_matrix_parameters_custom_values(self):
        """Test ColorMatrixParameters with custom values."""
        params = ColorMatrixParameters(
            matrix_type=ColorMatrixType.HUE_ROTATE,
            values=[90.0],
            input_source="filteredImage",
            result_name="hueRotated"
        )

        assert params.matrix_type == ColorMatrixType.HUE_ROTATE
        assert params.values == [90.0]
        assert params.input_source == "filteredImage"
        assert params.result_name == "hueRotated"


if __name__ == '__main__':
    pytest.main([__file__])