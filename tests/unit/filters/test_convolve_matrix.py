#!/usr/bin/env python3
"""
Tests for ConvolveMatrix filter processor.

Tests the comprehensive convolution matrix functionality including
parameter parsing, pattern detection, and PowerPoint integration.
"""

import pytest
from unittest.mock import Mock, patch
from lxml import etree as ET
import math

from core.filters.convolve_matrix import (
    ConvolveMatrixProcessor,
    ConvolveMatrixParameters,
    ConvolveMatrixException,
    ConvolveMatrixValidationError,
    EdgeMode,
    create_convolve_matrix_processor
)
from core.filters.base import FilterContext, FilterResult, FilterStrategy


class TestConvolveMatrixParameters:
    """Test ConvolveMatrixParameters data structure."""

    def test_initialization_valid_3x3(self):
        """Test valid 3x3 matrix initialization."""
        kernel = [1.0, 0.0, -1.0, 2.0, 0.0, -2.0, 1.0, 0.0, -1.0]
        params = ConvolveMatrixParameters(
            kernel_matrix=kernel,
            order=3,
            divisor=1.0,
            bias=0.0
        )

        assert params.kernel_matrix == kernel
        assert params.order == 3
        assert params.divisor == 1.0
        assert params.bias == 0.0
        assert params.edge_mode == EdgeMode.DUPLICATE
        assert params.preserve_alpha is False

    def test_initialization_with_all_parameters(self):
        """Test initialization with all parameters set."""
        kernel = [0.0, -1.0, 0.0, -1.0, 4.0, -1.0, 0.0, -1.0, 0.0]
        params = ConvolveMatrixParameters(
            kernel_matrix=kernel,
            order=3,
            divisor=2.0,
            bias=0.5,
            target_x=1,
            target_y=1,
            edge_mode=EdgeMode.WRAP,
            preserve_alpha=True
        )

        assert params.kernel_matrix == kernel
        assert params.order == 3
        assert params.divisor == 2.0
        assert params.bias == 0.5
        assert params.target_x == 1
        assert params.target_y == 1
        assert params.edge_mode == EdgeMode.WRAP
        assert params.preserve_alpha is True

    def test_validation_wrong_matrix_size(self):
        """Test validation with incorrect matrix size."""
        kernel = [1.0, 0.0, -1.0, 2.0]  # Only 4 elements for 3x3

        with pytest.raises(ConvolveMatrixValidationError) as exc_info:
            ConvolveMatrixParameters(kernel_matrix=kernel, order=3)

        assert "Kernel matrix size 4 does not match order 3" in str(exc_info.value)

    def test_validation_zero_order(self):
        """Test validation with zero order."""
        kernel = [1.0]

        with pytest.raises(ConvolveMatrixValidationError) as exc_info:
            ConvolveMatrixParameters(kernel_matrix=kernel, order=0)

        assert "Order must be positive" in str(exc_info.value)

    def test_validation_negative_order(self):
        """Test validation with negative order."""
        kernel = [1.0]

        with pytest.raises(ConvolveMatrixValidationError) as exc_info:
            ConvolveMatrixParameters(kernel_matrix=kernel, order=-1)

        assert "Order must be positive" in str(exc_info.value)

    def test_validation_zero_divisor(self):
        """Test validation with zero divisor."""
        kernel = [1.0, 0.0, 0.0, 0.0]

        with pytest.raises(ConvolveMatrixValidationError) as exc_info:
            ConvolveMatrixParameters(kernel_matrix=kernel, order=2, divisor=0.0)

        assert "Divisor cannot be zero" in str(exc_info.value)

    def test_validation_target_coordinates_out_of_range(self):
        """Test validation with target coordinates out of range."""
        kernel = [1.0, 0.0, 0.0, 0.0]

        with pytest.raises(ConvolveMatrixValidationError) as exc_info:
            ConvolveMatrixParameters(kernel_matrix=kernel, order=2, target_x=3)

        assert "Target X 3 out of range" in str(exc_info.value)

        with pytest.raises(ConvolveMatrixValidationError) as exc_info:
            ConvolveMatrixParameters(kernel_matrix=kernel, order=2, target_y=-1)

        assert "Target Y -1 out of range" in str(exc_info.value)

    def test_complexity_score_identity(self):
        """Test complexity calculation for identity matrix."""
        kernel = [0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0]
        params = ConvolveMatrixParameters(kernel_matrix=kernel, order=3)

        complexity = params.get_complexity_score()

        # Low complexity: sparse matrix with small variation
        assert complexity < 0.3

    def test_complexity_score_sobel(self):
        """Test complexity calculation for Sobel matrix."""
        kernel = [-1.0, 0.0, 1.0, -2.0, 0.0, 2.0, -1.0, 0.0, 1.0]
        params = ConvolveMatrixParameters(kernel_matrix=kernel, order=3)

        complexity = params.get_complexity_score()

        # Medium complexity: more variation but still simple pattern
        assert 0.1 < complexity < 0.5

    def test_complexity_score_high_variation(self):
        """Test complexity calculation for high variation matrix."""
        kernel = [10.0, -5.0, 8.0, -12.0, 15.0, -3.0, 7.0, -9.0, 11.0]
        params = ConvolveMatrixParameters(kernel_matrix=kernel, order=3)

        complexity = params.get_complexity_score()

        # High complexity: large value variation
        assert complexity > 0.4

    def test_is_identity_matrix_true(self):
        """Test identity matrix detection for valid identity."""
        kernel = [0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0]
        params = ConvolveMatrixParameters(kernel_matrix=kernel, order=3)

        assert params.is_identity_matrix() is True

    def test_is_identity_matrix_false(self):
        """Test identity matrix detection for non-identity."""
        kernel = [-1.0, 0.0, 1.0, -2.0, 0.0, 2.0, -1.0, 0.0, 1.0]
        params = ConvolveMatrixParameters(kernel_matrix=kernel, order=3)

        assert params.is_identity_matrix() is False

    def test_is_sobel_horizontal_true(self):
        """Test Sobel horizontal detection for valid pattern."""
        kernel = [-1.0, 0.0, 1.0, -2.0, 0.0, 2.0, -1.0, 0.0, 1.0]
        params = ConvolveMatrixParameters(kernel_matrix=kernel, order=3)

        assert params.is_sobel_horizontal() is True

    def test_is_sobel_horizontal_false(self):
        """Test Sobel horizontal detection for invalid pattern."""
        kernel = [0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0]
        params = ConvolveMatrixParameters(kernel_matrix=kernel, order=3)

        assert params.is_sobel_horizontal() is False

    def test_is_sobel_horizontal_wrong_size(self):
        """Test Sobel horizontal detection rejects wrong size."""
        kernel = [1.0, 0.0, 0.0, 0.0]
        params = ConvolveMatrixParameters(kernel_matrix=kernel, order=2)

        assert params.is_sobel_horizontal() is False

    def test_is_sobel_vertical_true(self):
        """Test Sobel vertical detection for valid pattern."""
        kernel = [-1.0, -2.0, -1.0, 0.0, 0.0, 0.0, 1.0, 2.0, 1.0]
        params = ConvolveMatrixParameters(kernel_matrix=kernel, order=3)

        assert params.is_sobel_vertical() is True

    def test_is_sobel_vertical_false(self):
        """Test Sobel vertical detection for invalid pattern."""
        kernel = [-1.0, 0.0, 1.0, -2.0, 0.0, 2.0, -1.0, 0.0, 1.0]
        params = ConvolveMatrixParameters(kernel_matrix=kernel, order=3)

        assert params.is_sobel_vertical() is False

    def test_is_laplacian_true(self):
        """Test Laplacian detection for valid pattern."""
        kernel = [0.0, -1.0, 0.0, -1.0, 4.0, -1.0, 0.0, -1.0, 0.0]
        params = ConvolveMatrixParameters(kernel_matrix=kernel, order=3)

        assert params.is_laplacian() is True

    def test_is_laplacian_false(self):
        """Test Laplacian detection for invalid pattern."""
        kernel = [-1.0, 0.0, 1.0, -2.0, 0.0, 2.0, -1.0, 0.0, 1.0]
        params = ConvolveMatrixParameters(kernel_matrix=kernel, order=3)

        assert params.is_laplacian() is False

    def test_matrices_equal_tolerance(self):
        """Test matrix equality with tolerance."""
        kernel1 = [1.0, 0.0, -1.0]
        kernel2 = [1.0000001, 0.0000001, -1.0000001]
        # Create with order that matches matrix size - sqrt(3) is not integer, so use 1x1
        kernel1_valid = [1.0]
        kernel2_valid = [1.0000001]
        params = ConvolveMatrixParameters(kernel_matrix=kernel1_valid, order=1)

        assert params._matrices_equal(kernel1, kernel2, 1e-6) is True
        assert params._matrices_equal(kernel1, kernel2, 1e-8) is False

    def test_matrices_equal_different_lengths(self):
        """Test matrix equality with different lengths."""
        kernel1 = [1.0, 0.0]
        kernel2 = [1.0, 0.0, -1.0]
        # Use valid matrix for parameter creation
        kernel_valid = [1.0]
        params = ConvolveMatrixParameters(kernel_matrix=kernel_valid, order=1)

        assert params._matrices_equal(kernel1, kernel2, 1e-6) is False


class TestConvolveMatrixProcessor:
    """Test ConvolveMatrixProcessor functionality."""

    @pytest.fixture
    def processor(self):
        """Create a ConvolveMatrixProcessor instance for testing."""
        return ConvolveMatrixProcessor()

    @pytest.fixture
    def mock_context(self):
        """Create mock FilterContext for testing."""
        context = Mock(spec=FilterContext)
        context.services = Mock()
        context.viewport = {"width": 100, "height": 100}
        return context

    def test_processor_initialization(self, processor):
        """Test processor initialization."""
        assert processor.filter_type == 'feConvolveMatrix'
        assert processor.policy is None

    def test_processor_initialization_with_policy(self):
        """Test processor initialization with policy."""
        policy = Mock()
        processor = ConvolveMatrixProcessor(policy=policy)

        assert processor.policy == policy

    def test_can_apply_valid_element(self, processor, mock_context):
        """Test can_apply with valid feConvolveMatrix element."""
        element = ET.Element('feConvolveMatrix')
        element.set('kernelMatrix', '0 0 0 0 1 0 0 0 0')
        element.set('order', '3')

        assert processor.can_apply(element, mock_context) is True

    def test_can_apply_invalid_element(self, processor, mock_context):
        """Test can_apply with invalid element."""
        element = ET.Element('feGaussianBlur')

        assert processor.can_apply(element, mock_context) is False

    def test_can_apply_none_element(self, processor, mock_context):
        """Test can_apply with None element."""
        assert processor.can_apply(None, mock_context) is False

    def test_parse_number_list_spaces(self, processor):
        """Test parsing space-separated number list."""
        result = processor._parse_number_list("1.0 0.0 -1.0 2.0")

        assert result == [1.0, 0.0, -1.0, 2.0]

    def test_parse_number_list_commas(self, processor):
        """Test parsing comma-separated number list."""
        result = processor._parse_number_list("1.0,0.0,-1.0,2.0")

        assert result == [1.0, 0.0, -1.0, 2.0]

    def test_parse_number_list_mixed(self, processor):
        """Test parsing mixed separator number list."""
        result = processor._parse_number_list("1.0, 0.0 -1.0,2.0")

        assert result == [1.0, 0.0, -1.0, 2.0]

    def test_parse_number_list_empty(self, processor):
        """Test parsing empty number list."""
        result = processor._parse_number_list("")

        assert result == []

    def test_parse_convolve_matrix_parameters_minimal(self, processor):
        """Test parsing minimal convolution matrix parameters."""
        element = ET.Element('feConvolveMatrix')
        element.set('kernelMatrix', '0 0 0 0 1 0 0 0 0')

        params = processor._parse_convolve_matrix_parameters(element)

        assert len(params.kernel_matrix) == 9
        assert params.kernel_matrix[4] == 1.0  # Center element
        assert params.order == 3  # Inferred from matrix size
        assert params.divisor == 1.0
        assert params.bias == 0.0

    def test_parse_convolve_matrix_parameters_explicit_order(self, processor):
        """Test parsing with explicit order attribute."""
        element = ET.Element('feConvolveMatrix')
        element.set('kernelMatrix', '1 0 0 0')
        element.set('order', '2')

        params = processor._parse_convolve_matrix_parameters(element)

        assert len(params.kernel_matrix) == 4
        assert params.order == 2

    def test_parse_convolve_matrix_parameters_order_format_3x3(self, processor):
        """Test parsing with "3x3" order format."""
        element = ET.Element('feConvolveMatrix')
        element.set('kernelMatrix', '0 0 0 0 1 0 0 0 0')
        element.set('order', '3x3')

        params = processor._parse_convolve_matrix_parameters(element)

        assert params.order == 3

    def test_parse_convolve_matrix_parameters_full(self, processor):
        """Test parsing complete convolution matrix parameters."""
        element = ET.Element('feConvolveMatrix')
        element.set('kernelMatrix', '0 -1 0 -1 4 -1 0 -1 0')
        element.set('order', '3')
        element.set('divisor', '2.0')
        element.set('bias', '0.5')
        element.set('targetX', '1')
        element.set('targetY', '1')
        element.set('edgeMode', 'wrap')
        element.set('preserveAlpha', 'true')

        params = processor._parse_convolve_matrix_parameters(element)

        assert params.order == 3
        assert params.divisor == 2.0
        assert params.bias == 0.5
        assert params.target_x == 1
        assert params.target_y == 1
        assert params.edge_mode == EdgeMode.WRAP
        assert params.preserve_alpha is True

    def test_parse_convolve_matrix_parameters_missing_kernel(self, processor):
        """Test parsing with missing kernelMatrix attribute."""
        element = ET.Element('feConvolveMatrix')

        with pytest.raises(ConvolveMatrixValidationError) as exc_info:
            processor._parse_convolve_matrix_parameters(element)

        assert "kernelMatrix attribute is required" in str(exc_info.value)

    def test_parse_convolve_matrix_parameters_empty_kernel(self, processor):
        """Test parsing with empty kernelMatrix."""
        element = ET.Element('feConvolveMatrix')
        element.set('kernelMatrix', '')

        with pytest.raises(ConvolveMatrixValidationError) as exc_info:
            processor._parse_convolve_matrix_parameters(element)

        assert "kernelMatrix cannot be empty" in str(exc_info.value)

    def test_parse_convolve_matrix_parameters_non_square_order(self, processor):
        """Test parsing with non-square order format."""
        element = ET.Element('feConvolveMatrix')
        element.set('kernelMatrix', '1 0 0 0')
        element.set('order', '2x3')  # Non-square

        with pytest.raises(ConvolveMatrixValidationError) as exc_info:
            processor._parse_convolve_matrix_parameters(element)

        assert "Non-square matrices not supported" in str(exc_info.value)

    def test_parse_convolve_matrix_parameters_infer_non_square(self, processor):
        """Test parsing with matrix that can't infer square order."""
        element = ET.Element('feConvolveMatrix')
        element.set('kernelMatrix', '1 0 0')  # 3 elements, not perfect square

        with pytest.raises(ConvolveMatrixValidationError) as exc_info:
            processor._parse_convolve_matrix_parameters(element)

        assert "not a perfect square" in str(exc_info.value)

    def test_parse_convolve_matrix_parameters_invalid_divisor(self, processor):
        """Test parsing with invalid divisor."""
        element = ET.Element('feConvolveMatrix')
        element.set('kernelMatrix', '1 0 0 0')
        element.set('order', '2')
        element.set('divisor', 'invalid')

        with pytest.raises(ConvolveMatrixValidationError) as exc_info:
            processor._parse_convolve_matrix_parameters(element)

        assert "Invalid divisor value" in str(exc_info.value)

    def test_parse_convolve_matrix_parameters_invalid_bias(self, processor):
        """Test parsing with invalid bias."""
        element = ET.Element('feConvolveMatrix')
        element.set('kernelMatrix', '1 0 0 0')
        element.set('order', '2')
        element.set('bias', 'invalid')

        with pytest.raises(ConvolveMatrixValidationError) as exc_info:
            processor._parse_convolve_matrix_parameters(element)

        assert "Invalid bias value" in str(exc_info.value)

    def test_parse_convolve_matrix_parameters_invalid_target(self, processor):
        """Test parsing with invalid target coordinates."""
        element = ET.Element('feConvolveMatrix')
        element.set('kernelMatrix', '1 0 0 0')
        element.set('order', '2')
        element.set('targetX', 'invalid')

        with pytest.raises(ConvolveMatrixValidationError) as exc_info:
            processor._parse_convolve_matrix_parameters(element)

        assert "Invalid targetX value" in str(exc_info.value)

    def test_can_use_vector_approach_identity(self, processor):
        """Test vector approach detection for identity matrix."""
        kernel = [0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0]
        params = ConvolveMatrixParameters(kernel_matrix=kernel, order=3)

        assert processor._can_use_vector_approach(params) is True

    def test_can_use_vector_approach_sobel(self, processor):
        """Test vector approach detection for Sobel matrix."""
        kernel = [-1.0, 0.0, 1.0, -2.0, 0.0, 2.0, -1.0, 0.0, 1.0]
        params = ConvolveMatrixParameters(kernel_matrix=kernel, order=3)

        assert processor._can_use_vector_approach(params) is True

    def test_can_use_vector_approach_laplacian(self, processor):
        """Test vector approach detection for Laplacian matrix."""
        kernel = [0.0, -1.0, 0.0, -1.0, 4.0, -1.0, 0.0, -1.0, 0.0]
        params = ConvolveMatrixParameters(kernel_matrix=kernel, order=3)

        assert processor._can_use_vector_approach(params) is True

    def test_can_use_vector_approach_false_large_matrix(self, processor):
        """Test vector approach rejects large matrices."""
        kernel = [1.0] * 25  # 5x5 matrix
        params = ConvolveMatrixParameters(kernel_matrix=kernel, order=5)

        assert processor._can_use_vector_approach(params) is False

    def test_can_use_vector_approach_false_complex_matrix(self, processor):
        """Test vector approach rejects complex matrices."""
        kernel = [10.0, -5.0, 8.0, -12.0, 15.0, -3.0, 7.0, -9.0, 11.0]
        params = ConvolveMatrixParameters(kernel_matrix=kernel, order=3)

        assert processor._can_use_vector_approach(params) is False

    def test_can_use_approximation_medium_complexity(self, processor):
        """Test approximation detection for medium complexity."""
        kernel = [1.0, -1.0, 1.0, -1.0, 5.0, -1.0, 1.0, -1.0, 1.0]
        params = ConvolveMatrixParameters(kernel_matrix=kernel, order=3)

        # This should have medium complexity
        assert processor._can_use_approximation(params) is True

    def test_can_use_approximation_false_large_matrix(self, processor):
        """Test approximation rejects very large matrices."""
        kernel = [1.0] * 100  # 10x10 matrix
        params = ConvolveMatrixParameters(kernel_matrix=kernel, order=10)

        assert processor._can_use_approximation(params) is False

    def test_generate_sobel_horizontal_drawingml(self, processor, mock_context):
        """Test Sobel horizontal DrawingML generation."""
        kernel = [-1.0, 0.0, 1.0, -2.0, 0.0, 2.0, -1.0, 0.0, 1.0]
        params = ConvolveMatrixParameters(kernel_matrix=kernel, order=3)

        drawingml = processor._generate_sobel_horizontal_drawingml(params, mock_context)

        assert '<a:ln' in drawingml
        assert 'val="dash"' in drawingml
        assert '<a:effectLst>' in drawingml

    def test_generate_sobel_vertical_drawingml(self, processor, mock_context):
        """Test Sobel vertical DrawingML generation."""
        kernel = [-1.0, -2.0, -1.0, 0.0, 0.0, 0.0, 1.0, 2.0, 1.0]
        params = ConvolveMatrixParameters(kernel_matrix=kernel, order=3)

        drawingml = processor._generate_sobel_vertical_drawingml(params, mock_context)

        assert '<a:ln' in drawingml
        assert 'val="dash"' in drawingml
        assert '<a:reflection' in drawingml

    def test_generate_laplacian_drawingml(self, processor, mock_context):
        """Test Laplacian DrawingML generation."""
        kernel = [0.0, -1.0, 0.0, -1.0, 4.0, -1.0, 0.0, -1.0, 0.0]
        params = ConvolveMatrixParameters(kernel_matrix=kernel, order=3)

        drawingml = processor._generate_laplacian_drawingml(params, mock_context)

        assert '<a:ln' in drawingml
        assert 'val="dashDot"' in drawingml

    def test_generate_generic_edge_drawingml(self, processor, mock_context):
        """Test generic edge DrawingML generation."""
        kernel = [1.0, -1.0, 0.0, -1.0, 2.0, -1.0, 0.0, -1.0, 1.0]
        params = ConvolveMatrixParameters(kernel_matrix=kernel, order=3)

        drawingml = processor._generate_generic_edge_drawingml(params, mock_context)

        assert '<a:ln' in drawingml
        assert 'val="dot"' in drawingml

    def test_apply_native_strategy_identity(self, processor, mock_context):
        """Test applying native strategy for identity matrix."""
        element = ET.Element('feConvolveMatrix')
        element.set('kernelMatrix', '0 0 0 0 1 0 0 0 0')
        element.set('order', '3')

        result = processor.apply(element, mock_context)

        assert result.success is True
        assert result.strategy == FilterStrategy.NATIVE
        assert "Identity matrix" in result.drawingml

    def test_apply_native_strategy_sobel_horizontal(self, processor, mock_context):
        """Test applying native strategy for Sobel horizontal."""
        element = ET.Element('feConvolveMatrix')
        element.set('kernelMatrix', '-1 0 1 -2 0 2 -1 0 1')
        element.set('order', '3')

        result = processor.apply(element, mock_context)

        assert result.success is True
        assert result.strategy == FilterStrategy.NATIVE
        assert '<a:ln' in result.drawingml

    def test_apply_approximation_strategy(self, processor, mock_context):
        """Test applying approximation strategy."""
        element = ET.Element('feConvolveMatrix')
        element.set('kernelMatrix', '1 -1 1 -1 5 -1 1 -1 1')
        element.set('order', '3')

        # Mock the decision methods to force approximation
        with patch.object(processor, '_can_use_vector_approach', return_value=False):
            with patch.object(processor, '_can_use_approximation', return_value=True):
                result = processor.apply(element, mock_context)

        assert result.success is True
        assert result.strategy == FilterStrategy.APPROXIMATION
        assert '<a:outerShdw' in result.drawingml

    def test_apply_emf_strategy_complex(self, processor, mock_context):
        """Test applying EMF strategy for complex matrix."""
        # Mock policy to force EMF strategy
        policy = Mock()
        policy.decide_convolve_matrix_strategy.return_value = Mock(strategy=FilterStrategy.EMF_RASTERIZE)
        processor.policy = policy

        element = ET.Element('feConvolveMatrix')
        element.set('kernelMatrix', '10 -5 8 -12 15 -3 7 -9 11')
        element.set('order', '3')

        result = processor.apply(element, mock_context)

        assert result.success is True
        assert result.strategy == FilterStrategy.EMF_RASTERIZE
        assert result.metadata['approach'] == 'emf'

    def test_apply_error_handling(self, processor, mock_context):
        """Test error handling during apply."""
        # Force error by providing invalid element
        element = None

        result = processor.apply(element, mock_context)

        assert result.success is False
        assert result.strategy == FilterStrategy.EMF_RASTERIZE
        assert "Convolve matrix processing failed" in result.error_message

    def test_validate_parameters_valid(self, processor, mock_context):
        """Test parameter validation with valid element."""
        element = ET.Element('feConvolveMatrix')
        element.set('kernelMatrix', '0 0 0 0 1 0 0 0 0')

        assert processor._validate_parameters(element, mock_context) is True

    def test_validate_parameters_invalid_element(self, processor, mock_context):
        """Test parameter validation with invalid element."""
        assert processor._validate_parameters(None, mock_context) is False

    def test_validate_parameters_invalid_context(self, processor):
        """Test parameter validation with invalid context."""
        element = ET.Element('feConvolveMatrix')
        element.set('kernelMatrix', '0 0 0 0 1 0 0 0 0')

        assert processor._validate_parameters(element, None) is False


class TestConvolveMatrixIntegration:
    """Test ConvolveMatrixProcessor integration patterns."""

    def test_processor_with_policy_integration(self):
        """Test processor integration with policy."""
        policy = Mock()
        policy.decide_convolve_matrix_strategy.return_value = Mock(strategy=FilterStrategy.NATIVE)

        processor = ConvolveMatrixProcessor(policy=policy)
        context = Mock(spec=FilterContext)

        element = ET.Element('feConvolveMatrix')
        element.set('kernelMatrix', '0 0 0 0 1 0 0 0 0')
        element.set('order', '3')

        # Mock validation to pass
        with patch.object(processor, '_validate_parameters', return_value=True):
            result = processor.apply(element, context)

        # Policy should have been consulted
        policy.decide_convolve_matrix_strategy.assert_called_once()
        assert result.strategy == FilterStrategy.NATIVE

    def test_processor_factory_function(self):
        """Test processor factory function."""
        policy = Mock()
        processor = create_convolve_matrix_processor(policy=policy)

        assert isinstance(processor, ConvolveMatrixProcessor)
        assert processor.policy == policy

    def test_processor_factory_function_no_policy(self):
        """Test processor factory function without policy."""
        processor = create_convolve_matrix_processor()

        assert isinstance(processor, ConvolveMatrixProcessor)
        assert processor.policy is None

    def test_comprehensive_convolve_matrix_processing(self):
        """Test comprehensive convolution matrix processing workflow."""
        processor = ConvolveMatrixProcessor()
        context = Mock(spec=FilterContext)
        context.services = Mock()

        # Create complex convolution matrix
        element = ET.Element('feConvolveMatrix')
        element.set('kernelMatrix', '1 2 1 0 0 0 -1 -2 -1')  # Edge detection variant
        element.set('order', '3')
        element.set('divisor', '1.0')
        element.set('bias', '0.0')

        result = processor.apply(element, context)

        # Should succeed with appropriate strategy
        assert result.success is True
        assert result.strategy in [FilterStrategy.NATIVE, FilterStrategy.APPROXIMATION, FilterStrategy.EMF_RASTERIZE]
        assert 'matrix_size' in result.metadata
        assert 'complexity' in result.metadata

    def test_convolve_matrix_error_recovery(self):
        """Test convolution matrix error recovery patterns."""
        processor = ConvolveMatrixProcessor()
        context = Mock(spec=FilterContext)

        # Create element with invalid matrix parameters
        element = ET.Element('feConvolveMatrix')
        element.set('kernelMatrix', '1 0 0')  # Wrong size for inferred order
        element.set('divisor', '0')  # Invalid divisor

        # Should handle error gracefully
        result = processor.apply(element, context)

        assert result.success is False
        assert "Convolve matrix processing failed" in result.error_message

    def test_edge_mode_parameter_handling(self):
        """Test edge mode parameter parsing and handling."""
        processor = ConvolveMatrixProcessor()

        # Test all edge modes
        for edge_mode_str, expected_enum in [
            ('duplicate', EdgeMode.DUPLICATE),
            ('wrap', EdgeMode.WRAP),
            ('none', EdgeMode.NONE),
            ('invalid', EdgeMode.DUPLICATE)  # Should default
        ]:
            element = ET.Element('feConvolveMatrix')
            element.set('kernelMatrix', '0 0 0 0 1 0 0 0 0')
            element.set('order', '3')
            element.set('edgeMode', edge_mode_str)

            params = processor._parse_convolve_matrix_parameters(element)
            assert params.edge_mode == expected_enum

    def test_preserve_alpha_parameter_handling(self):
        """Test preserve alpha parameter parsing."""
        processor = ConvolveMatrixProcessor()

        # Test various boolean representations
        for alpha_str, expected_bool in [
            ('true', True),
            ('True', True),
            ('1', True),
            ('yes', True),
            ('false', False),
            ('False', False),
            ('0', False),
            ('no', False),
            ('invalid', False)  # Should default to False
        ]:
            element = ET.Element('feConvolveMatrix')
            element.set('kernelMatrix', '0 0 0 0 1 0 0 0 0')
            element.set('order', '3')
            element.set('preserveAlpha', alpha_str)

            params = processor._parse_convolve_matrix_parameters(element)
            assert params.preserve_alpha == expected_bool

    def test_metadata_completeness(self):
        """Test that result metadata contains all expected fields."""
        processor = ConvolveMatrixProcessor()
        context = Mock(spec=FilterContext)
        context.services = Mock()

        element = ET.Element('feConvolveMatrix')
        element.set('kernelMatrix', '0 -1 0 -1 4 -1 0 -1 0')  # Laplacian
        element.set('order', '3')

        result = processor.apply(element, context)

        assert result.success is True
        assert 'filter_type' in result.metadata
        assert 'approach' in result.metadata
        assert 'matrix_size' in result.metadata
        assert 'complexity' in result.metadata
        assert result.metadata['filter_type'] == 'feConvolveMatrix'
        assert result.metadata['matrix_size'] == '3x3'


if __name__ == '__main__':
    pytest.main([__file__])