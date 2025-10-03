#!/usr/bin/env python3
"""
Tests for GaussianBlurProcessor with comprehensive blur operations.

Tests all blur modes, edge cases, policy integration, and DrawingML generation
for PowerPoint filter effects.
"""

import pytest
from unittest.mock import Mock, patch
from lxml import etree as ET

from core.filters.blur import (
    GaussianBlurProcessor,
    BlurParameters,
    BlurFilterException,
    BlurValidationError,
    create_gaussian_blur_processor
)
from core.filters.base import (
    FilterContext,
    FilterStrategy,
    FilterResult,
    FilterException
)


class TestBlurParameters:
    """Test BlurParameters data structure."""

    def test_initialization_isotropic(self):
        """Test parameter initialization with isotropic blur."""
        params = BlurParameters(
            std_deviation_x=2.5,
            std_deviation_y=2.5,
            edge_mode="duplicate"
        )

        assert params.std_deviation_x == 2.5
        assert params.std_deviation_y == 2.5
        assert params.edge_mode == "duplicate"
        assert params.input_source == "SourceGraphic"
        assert params.is_isotropic() is True

    def test_initialization_anisotropic(self):
        """Test parameter initialization with anisotropic blur."""
        params = BlurParameters(
            std_deviation_x=3.0,
            std_deviation_y=1.5,
            edge_mode="wrap"
        )

        assert params.std_deviation_x == 3.0
        assert params.std_deviation_y == 1.5
        assert params.edge_mode == "wrap"
        assert params.is_isotropic() is False

    def test_post_init_negative_values(self):
        """Test that negative standard deviations are corrected."""
        params = BlurParameters(
            std_deviation_x=-1.0,
            std_deviation_y=-2.0
        )

        assert params.std_deviation_x == 0.0
        assert params.std_deviation_y == 0.0

    def test_post_init_invalid_edge_mode(self):
        """Test that invalid edge modes are corrected."""
        params = BlurParameters(
            std_deviation_x=2.0,
            std_deviation_y=2.0,
            edge_mode="invalid"
        )

        assert params.edge_mode == "duplicate"

    def test_complexity_score_simple(self):
        """Test complexity score for simple blur."""
        params = BlurParameters(
            std_deviation_x=2.0,
            std_deviation_y=2.0,
            edge_mode="duplicate"
        )

        complexity = params.get_complexity_score()
        assert 0.0 <= complexity <= 1.0

    def test_complexity_score_anisotropic(self):
        """Test complexity score for anisotropic blur."""
        params = BlurParameters(
            std_deviation_x=5.0,
            std_deviation_y=2.0,
            edge_mode="wrap"
        )

        complexity = params.get_complexity_score()
        assert complexity > 1.0  # Anisotropic adds complexity

    def test_complexity_score_large_blur(self):
        """Test complexity score for large blur."""
        params = BlurParameters(
            std_deviation_x=50.0,
            std_deviation_y=50.0
        )

        complexity = params.get_complexity_score()
        assert complexity >= 3.0  # Large blur is complex

    def test_is_effective_true(self):
        """Test is_effective for visible blur."""
        params = BlurParameters(
            std_deviation_x=2.0,
            std_deviation_y=1.5
        )

        assert params.is_effective() is True

    def test_is_effective_false(self):
        """Test is_effective for tiny blur."""
        params = BlurParameters(
            std_deviation_x=0.05,
            std_deviation_y=0.03
        )

        assert params.is_effective() is False

    def test_get_average_std_deviation(self):
        """Test average standard deviation calculation."""
        params = BlurParameters(
            std_deviation_x=4.0,
            std_deviation_y=2.0
        )

        assert params.get_average_std_deviation() == 3.0


class TestGaussianBlurProcessor:
    """Test GaussianBlurProcessor filter processing."""

    @pytest.fixture
    def mock_policy(self):
        """Create mock policy for testing."""
        policy = Mock()
        return policy

    @pytest.fixture
    def blur_processor(self, mock_policy):
        """Create GaussianBlurProcessor for testing."""
        return GaussianBlurProcessor(policy=mock_policy)

    @pytest.fixture
    def mock_context(self):
        """Create mock filter context."""
        context = Mock(spec=FilterContext)
        context.element = ET.Element('feGaussianBlur')
        context.viewport = {'width': 100, 'height': 100}
        context.unit_converter = Mock()
        context.transform_parser = Mock()
        context.color_parser = Mock()
        return context

    def test_initialization(self, mock_policy):
        """Test GaussianBlurProcessor initialization."""
        processor = GaussianBlurProcessor(policy=mock_policy)

        assert processor.filter_type == 'feGaussianBlur'
        assert processor.policy == mock_policy
        assert processor.max_native_blur == 25.0
        assert processor.max_blur_radius_emu == 2540000

    def test_can_apply_valid_element(self, blur_processor, mock_context):
        """Test can_apply with valid feGaussianBlur element."""
        element = ET.Element('feGaussianBlur')
        element.set('stdDeviation', '2.0')

        assert blur_processor.can_apply(element, mock_context) is True

    def test_can_apply_invalid_element(self, blur_processor, mock_context):
        """Test can_apply with invalid element."""
        element = ET.Element('feOffset')
        mock_context.element = element

        assert blur_processor.can_apply(element, mock_context) is False

    def test_can_apply_none_element(self, blur_processor, mock_context):
        """Test can_apply with None element."""
        assert blur_processor.can_apply(None, mock_context) is False

    def test_parse_isotropic_std_deviation(self, blur_processor):
        """Test parsing isotropic standard deviation."""
        element = ET.Element('feGaussianBlur')
        element.set('stdDeviation', '2.5')

        params = blur_processor._parse_blur_parameters(element)

        assert params.std_deviation_x == 2.5
        assert params.std_deviation_y == 2.5
        assert params.is_isotropic() is True

    def test_parse_anisotropic_std_deviation(self, blur_processor):
        """Test parsing anisotropic standard deviation."""
        element = ET.Element('feGaussianBlur')
        element.set('stdDeviation', '3.0 1.5')

        params = blur_processor._parse_blur_parameters(element)

        assert params.std_deviation_x == 3.0
        assert params.std_deviation_y == 1.5
        assert params.is_isotropic() is False

    def test_parse_edge_mode_duplicate(self, blur_processor):
        """Test parsing edge mode duplicate."""
        element = ET.Element('feGaussianBlur')
        element.set('stdDeviation', '2.0')
        element.set('edgeMode', 'duplicate')

        params = blur_processor._parse_blur_parameters(element)

        assert params.edge_mode == 'duplicate'

    def test_parse_edge_mode_wrap(self, blur_processor):
        """Test parsing edge mode wrap."""
        element = ET.Element('feGaussianBlur')
        element.set('stdDeviation', '2.0')
        element.set('edgeMode', 'wrap')

        params = blur_processor._parse_blur_parameters(element)

        assert params.edge_mode == 'wrap'

    def test_parse_edge_mode_none(self, blur_processor):
        """Test parsing edge mode none."""
        element = ET.Element('feGaussianBlur')
        element.set('stdDeviation', '2.0')
        element.set('edgeMode', 'none')

        params = blur_processor._parse_blur_parameters(element)

        assert params.edge_mode == 'none'

    def test_parse_invalid_std_deviation_format(self, blur_processor):
        """Test parsing invalid standard deviation format raises exception."""
        element = ET.Element('feGaussianBlur')
        element.set('stdDeviation', '2.0 1.5 3.0')  # Too many values

        with pytest.raises(BlurValidationError) as exc_info:
            blur_processor._parse_blur_parameters(element)

        assert "Invalid stdDeviation format" in str(exc_info.value)

    def test_parse_negative_std_deviation(self, blur_processor):
        """Test parsing negative standard deviation raises exception."""
        element = ET.Element('feGaussianBlur')
        element.set('stdDeviation', '-1.0')

        with pytest.raises(BlurValidationError) as exc_info:
            blur_processor._parse_blur_parameters(element)

        assert "must be non-negative" in str(exc_info.value)

    def test_parse_non_numeric_std_deviation(self, blur_processor):
        """Test parsing non-numeric standard deviation raises exception."""
        element = ET.Element('feGaussianBlur')
        element.set('stdDeviation', 'invalid')

        with pytest.raises(BlurValidationError):
            blur_processor._parse_blur_parameters(element)

    def test_can_use_native_blur_simple_isotropic(self, blur_processor):
        """Test native blur support for simple isotropic blur."""
        params = BlurParameters(
            std_deviation_x=5.0,
            std_deviation_y=5.0,
            edge_mode="duplicate"
        )

        assert blur_processor._can_use_native_blur(params) is True

    def test_can_use_native_blur_anisotropic_false(self, blur_processor):
        """Test native blur unsupported for anisotropic blur."""
        params = BlurParameters(
            std_deviation_x=5.0,
            std_deviation_y=2.0,
            edge_mode="duplicate"
        )

        assert blur_processor._can_use_native_blur(params) is False

    def test_can_use_native_blur_large_false(self, blur_processor):
        """Test native blur unsupported for large blur."""
        params = BlurParameters(
            std_deviation_x=50.0,
            std_deviation_y=50.0,
            edge_mode="duplicate"
        )

        assert blur_processor._can_use_native_blur(params) is False

    def test_can_use_native_blur_edge_mode_false(self, blur_processor):
        """Test native blur unsupported for non-duplicate edge mode."""
        params = BlurParameters(
            std_deviation_x=5.0,
            std_deviation_y=5.0,
            edge_mode="wrap"
        )

        assert blur_processor._can_use_native_blur(params) is False

    def test_can_use_native_blur_no_effect_true(self, blur_processor):
        """Test native blur supported for no-effect blur."""
        params = BlurParameters(
            std_deviation_x=0.0,
            std_deviation_y=0.0
        )

        assert blur_processor._can_use_native_blur(params) is True

    @patch('core.filters.blur.unit')
    def test_generate_native_blur_drawingml(self, mock_unit, blur_processor, mock_context):
        """Test generating native blur DrawingML."""
        mock_unit.return_value.to_emu.return_value = 127000  # 5px = 127000 EMU

        params = BlurParameters(
            std_deviation_x=5.0,
            std_deviation_y=5.0
        )

        drawingml = blur_processor._generate_native_blur_drawingml(params, mock_context)

        assert '<a:blur rad="127000"/>' in drawingml
        mock_unit.assert_called_with("5.0px")

    @patch('core.filters.blur.unit')
    def test_generate_native_blur_drawingml_clamped(self, mock_unit, blur_processor, mock_context):
        """Test generating native blur DrawingML with clamping."""
        mock_unit.return_value.to_emu.return_value = 5000000  # Very large value

        params = BlurParameters(
            std_deviation_x=200.0,
            std_deviation_y=200.0
        )

        drawingml = blur_processor._generate_native_blur_drawingml(params, mock_context)

        # Should be clamped to max_blur_radius_emu
        assert '<a:blur rad="2540000"/>' in drawingml

    @patch('core.filters.blur.unit')
    def test_generate_approximation_blur_drawingml_anisotropic(self, mock_unit, blur_processor, mock_context):
        """Test generating approximation blur DrawingML for anisotropic blur."""
        mock_unit.return_value.to_emu.return_value = 190500  # 7.5px EMU

        params = BlurParameters(
            std_deviation_x=7.5,
            std_deviation_y=2.5
        )

        drawingml = blur_processor._generate_approximation_blur_drawingml(params, mock_context)

        assert '<a:blur rad="190500"/>' in drawingml
        assert 'Anisotropic blur approximation: 7.5x2.5' in drawingml

    @patch('core.filters.blur.unit')
    def test_generate_approximation_blur_drawingml_edge_mode(self, mock_unit, blur_processor, mock_context):
        """Test generating approximation blur DrawingML for special edge mode."""
        mock_unit.return_value.to_emu.return_value = 127000

        params = BlurParameters(
            std_deviation_x=5.0,
            std_deviation_y=5.0,
            edge_mode="wrap"
        )

        drawingml = blur_processor._generate_approximation_blur_drawingml(params, mock_context)

        assert '<a:blur rad="127000"/>' in drawingml
        assert 'Edge mode: wrap (approximated)' in drawingml

    def test_apply_native_strategy_simple_blur(self, blur_processor, mock_context, mock_policy):
        """Test apply with native strategy for simple blur."""
        element = ET.Element('feGaussianBlur')
        element.set('stdDeviation', '5.0')
        mock_context.element = element

        mock_policy.decide_blur_strategy.return_value = Mock(strategy=FilterStrategy.NATIVE)

        with patch.object(blur_processor, '_generate_native_blur_drawingml') as mock_generate:
            mock_generate.return_value = '<a:blur rad="127000"/>'

            result = blur_processor.apply(element, mock_context)

            assert isinstance(result, FilterResult)
            assert result.success is True
            assert result.strategy == FilterStrategy.NATIVE
            assert '<a:blur rad="127000"/>' in result.drawingml
            assert result.metadata['filter_type'] == 'feGaussianBlur'
            assert result.metadata['approach'] == 'native'

    def test_apply_approximation_strategy(self, blur_processor, mock_context, mock_policy):
        """Test apply with approximation strategy."""
        element = ET.Element('feGaussianBlur')
        element.set('stdDeviation', '10.0 5.0')  # Anisotropic
        mock_context.element = element

        mock_policy.decide_blur_strategy.return_value = Mock(strategy=FilterStrategy.APPROXIMATION)

        with patch.object(blur_processor, '_generate_approximation_blur_drawingml') as mock_generate:
            mock_generate.return_value = '<a:blur rad="254000"/><!-- Anisotropic approximation -->'

            result = blur_processor.apply(element, mock_context)

            assert isinstance(result, FilterResult)
            assert result.success is True
            assert result.strategy == FilterStrategy.APPROXIMATION
            assert result.metadata['approach'] == 'approximation'

    def test_apply_emf_strategy(self, blur_processor, mock_context, mock_policy):
        """Test apply with EMF rasterization strategy."""
        element = ET.Element('feGaussianBlur')
        element.set('stdDeviation', '100.0')  # Very large blur
        mock_context.element = element

        mock_policy.decide_blur_strategy.return_value = Mock(strategy=FilterStrategy.EMF_RASTERIZE)

        result = blur_processor.apply(element, mock_context)

        assert isinstance(result, FilterResult)
        assert result.success is True
        assert result.strategy == FilterStrategy.EMF_RASTERIZE
        assert 'EMF rasterization for complex Gaussian blur' in result.drawingml
        assert result.metadata['approach'] == 'emf'

    def test_apply_no_effect_blur(self, blur_processor, mock_context, mock_policy):
        """Test apply with no-effect blur."""
        element = ET.Element('feGaussianBlur')
        element.set('stdDeviation', '0.0')
        mock_context.element = element

        mock_policy.decide_blur_strategy.return_value = Mock(strategy=FilterStrategy.NATIVE)

        result = blur_processor.apply(element, mock_context)

        assert isinstance(result, FilterResult)
        assert result.success is True
        assert result.strategy == FilterStrategy.NATIVE
        assert 'No visible blur effect' in result.drawingml

    def test_apply_parsing_error_handling(self, blur_processor, mock_context, mock_policy):
        """Test apply handles parsing errors gracefully."""
        element = ET.Element('feGaussianBlur')
        element.set('stdDeviation', 'invalid')  # Invalid value
        mock_context.element = element

        mock_policy.decide_blur_strategy.return_value = Mock(strategy=FilterStrategy.NATIVE)

        result = blur_processor.apply(element, mock_context)

        assert isinstance(result, FilterResult)
        assert result.success is False
        assert result.error_message is not None
        assert "Gaussian blur processing failed" in result.error_message

    def test_apply_strategy_without_policy(self, mock_context):
        """Test apply with strategy selection without policy."""
        processor = GaussianBlurProcessor()  # No policy
        element = ET.Element('feGaussianBlur')
        element.set('stdDeviation', '5.0')
        mock_context.element = element

        with patch.object(processor, '_generate_native_blur_drawingml') as mock_generate:
            mock_generate.return_value = '<a:blur rad="127000"/>'

            result = processor.apply(element, mock_context)

            assert result.success is True
            assert result.strategy == FilterStrategy.NATIVE

    def test_validate_parameters_valid(self, blur_processor, mock_context):
        """Test parameter validation with valid element."""
        element = ET.Element('feGaussianBlur')
        element.set('stdDeviation', '2.5')

        assert blur_processor._validate_parameters(element, mock_context) is True

    def test_validate_parameters_invalid_element(self, blur_processor, mock_context):
        """Test parameter validation with invalid element."""
        element = ET.Element('feGaussianBlur')
        element.set('stdDeviation', 'invalid')

        assert blur_processor._validate_parameters(element, mock_context) is False

    def test_validate_parameters_none_element(self, blur_processor, mock_context):
        """Test parameter validation with None element."""
        assert blur_processor._validate_parameters(None, mock_context) is False

    def test_validate_parameters_none_context(self, blur_processor):
        """Test parameter validation with None context."""
        element = ET.Element('feGaussianBlur')
        element.set('stdDeviation', '2.5')

        assert blur_processor._validate_parameters(element, None) is False


class TestBlurProcessorIntegration:
    """Test GaussianBlurProcessor integration with policy and context."""

    @pytest.fixture
    def mock_policy(self):
        """Create mock policy with strategy decisions."""
        policy = Mock()
        return policy

    @pytest.fixture
    def blur_processor(self, mock_policy):
        """Create GaussianBlurProcessor with mock policy."""
        return GaussianBlurProcessor(policy=mock_policy)

    @pytest.fixture
    def mock_context(self):
        """Create realistic filter context."""
        context = Mock(spec=FilterContext)
        context.viewport = {'width': 100, 'height': 100}
        context.unit_converter = Mock()
        context.transform_parser = Mock()
        context.color_parser = Mock()
        return context

    def test_policy_integration_calls_decide_blur_strategy(self, blur_processor, mock_context, mock_policy):
        """Test policy integration calls decide_blur_strategy."""
        element = ET.Element('feGaussianBlur')
        element.set('stdDeviation', '5.0')
        mock_context.element = element

        mock_policy.decide_blur_strategy.return_value = Mock(strategy=FilterStrategy.NATIVE)

        with patch.object(blur_processor, '_generate_native_blur_drawingml') as mock_generate:
            mock_generate.return_value = '<a:blur rad="127000"/>'

            blur_processor.apply(element, mock_context)

            # Verify policy was called
            mock_policy.decide_blur_strategy.assert_called_once()
            call_args = mock_policy.decide_blur_strategy.call_args[0]
            assert isinstance(call_args[0], BlurParameters)
            assert call_args[1] == mock_context

    def test_comprehensive_blur_processing(self, blur_processor, mock_context, mock_policy):
        """Test comprehensive blur processing with metadata."""
        element = ET.Element('feGaussianBlur')
        element.set('stdDeviation', '3.0 2.0')
        element.set('edgeMode', 'wrap')
        element.set('in', 'SourceGraphic')
        element.set('result', 'blur1')
        mock_context.element = element

        mock_policy.decide_blur_strategy.return_value = Mock(strategy=FilterStrategy.APPROXIMATION)

        with patch.object(blur_processor, '_generate_approximation_blur_drawingml') as mock_generate:
            mock_generate.return_value = '<a:blur rad="190500"/><!-- Anisotropic -->'

            result = blur_processor.apply(element, mock_context)

            assert result.success is True
            assert result.metadata['std_deviation_x'] == 3.0
            assert result.metadata['std_deviation_y'] == 2.0
            assert result.metadata['edge_mode'] == 'wrap'
            assert result.metadata['is_isotropic'] is False

    def test_blur_error_recovery(self, blur_processor, mock_context, mock_policy):
        """Test blur processor error recovery."""
        element = ET.Element('feGaussianBlur')
        element.set('stdDeviation', 'completely-invalid-value')
        mock_context.element = element

        mock_policy.decide_blur_strategy.return_value = Mock(strategy=FilterStrategy.NATIVE)

        result = blur_processor.apply(element, mock_context)

        assert result.success is False
        assert result.strategy == FilterStrategy.EMF_RASTERIZE
        assert result.error_message is not None


class TestBlurFilterException:
    """Test BlurFilterException error handling."""

    def test_exception_creation_with_message(self):
        """Test creating exception with message."""
        exception = BlurFilterException("Test error message")

        assert str(exception) == "Test error message"
        assert exception.args[0] == "Test error message"

    def test_validation_error_inheritance(self):
        """Test BlurValidationError inherits correctly."""
        exception = BlurValidationError("Validation error")

        assert isinstance(exception, BlurFilterException)
        assert isinstance(exception, ValueError)
        assert isinstance(exception, BlurValidationError)


class TestCreateGaussianBlurProcessor:
    """Test create_gaussian_blur_processor factory function."""

    def test_create_with_policy(self):
        """Test creating processor with policy."""
        policy = Mock()
        processor = create_gaussian_blur_processor(policy=policy)

        assert isinstance(processor, GaussianBlurProcessor)
        assert processor.policy == policy
        assert processor.filter_type == 'feGaussianBlur'

    def test_create_without_policy(self):
        """Test creating processor without policy."""
        processor = create_gaussian_blur_processor()

        assert isinstance(processor, GaussianBlurProcessor)
        assert processor.policy is None
        assert processor.filter_type == 'feGaussianBlur'


if __name__ == '__main__':
    pytest.main([__file__])