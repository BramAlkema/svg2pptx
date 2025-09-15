"""
Unit tests for feConvolveMatrix filter implementation.

Tests convolution matrix parsing, validation, hybrid vector + EMF approach,
and integration with PowerPoint DrawingML generation.
"""

import pytest
import xml.etree.ElementTree as ET
from unittest.mock import Mock, patch
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

from src.converters.filters.core.base import Filter, FilterResult, FilterContext
from src.converters.filters.image.convolve_matrix import (
    ConvolveMatrixFilter,
    ConvolveMatrixParameters,
    EdgeMode,
    ConvolveMatrixException,
    ConvolveMatrixValidationError,
)


# No custom markers needed for basic unit tests


@dataclass
class ConvolutionTestCase:
    """Test case data for convolution matrix tests."""
    name: str
    matrix: List[float]
    order: str
    expected_vector: bool = False
    expected_emf: bool = False
    divisor: float = 1.0
    bias: float = 0.0
    edge_mode: str = "duplicate"
    preserve_alpha: bool = False


class TestConvolveMatrixParameters:
    """Test ConvolveMatrixParameters data class and validation."""

    def test_parameters_initialization_default_values(self):
        """Test parameters initialize with correct default values."""
        params = ConvolveMatrixParameters(
            matrix=[1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0],
            order="3"
        )

        assert params.matrix == [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
        assert params.order == "3"
        assert params.divisor == 1.0
        assert params.bias == 0.0
        assert params.edge_mode == EdgeMode.DUPLICATE
        assert params.preserve_alpha is False
        assert params.target_x is None
        assert params.target_y is None

    def test_parameters_initialization_all_values(self):
        """Test parameters initialize with all custom values."""
        matrix = [-1.0, -1.0, -1.0, -1.0, 8.0, -1.0, -1.0, -1.0, -1.0]
        params = ConvolveMatrixParameters(
            matrix=matrix,
            order="3",
            divisor=1.0,
            bias=0.5,
            edge_mode=EdgeMode.WRAP,
            preserve_alpha=True,
            target_x=1,
            target_y=1
        )

        assert params.matrix == matrix
        assert params.divisor == 1.0
        assert params.bias == 0.5
        assert params.edge_mode == EdgeMode.WRAP
        assert params.preserve_alpha is True
        assert params.target_x == 1
        assert params.target_y == 1

    def test_edge_mode_enum_values(self):
        """Test EdgeMode enum has correct values."""
        assert EdgeMode.DUPLICATE.value == "duplicate"
        assert EdgeMode.WRAP.value == "wrap"
        assert EdgeMode.NONE.value == "none"


class TestConvolveMatrixFilter:
    """Test ConvolveMatrixFilter main functionality."""

    @pytest.fixture
    def mock_context(self):
        """Create mock FilterContext for testing."""
        context = Mock()
        context.unit_converter = Mock()
        context.unit_converter = Mock()
        context.unit_converter.to_emu.return_value = 63500
        context.viewport = {'width': 100, 'height': 100}
        context.element = Mock()
        return context

    @pytest.fixture
    def filter_instance(self):
        """Create ConvolveMatrixFilter instance."""
        return ConvolveMatrixFilter()

    def test_filter_initialization(self, filter_instance):
        """Test filter initializes correctly."""
        assert isinstance(filter_instance, Filter)
        assert filter_instance.filter_type == "feConvolveMatrix"

    def test_can_apply_valid_element(self, filter_instance, mock_context):
        """Test can_apply returns True for valid feConvolveMatrix element."""
        element = ET.fromstring('<feConvolveMatrix kernelMatrix="1 0 0 0 1 0 0 0 1" order="3"/>')

        result = filter_instance.can_apply(element, mock_context)

        assert result is True

    def test_can_apply_invalid_element(self, filter_instance, mock_context):
        """Test can_apply returns False for non-feConvolveMatrix element."""
        element = ET.fromstring('<feGaussianBlur stdDeviation="2"/>')

        result = filter_instance.can_apply(element, mock_context)

        assert result is False

    def test_can_apply_missing_kernel_matrix(self, filter_instance, mock_context):
        """Test can_apply returns False when kernelMatrix is missing."""
        element = ET.fromstring('<feConvolveMatrix order="3"/>')

        result = filter_instance.can_apply(element, mock_context)

        assert result is False


class TestConvolveMatrixParsing:
    """Test parsing of feConvolveMatrix attributes and validation."""

    @pytest.fixture
    def filter_instance(self):
        return ConvolveMatrixFilter()

    @pytest.fixture
    def mock_context(self):
        context = Mock()
        context.unit_converter = Mock()
        context.unit_converter.to_emu.return_value = 63500
        return context

    def test_parse_identity_matrix_3x3(self, filter_instance, mock_context):
        """Test parsing 3x3 identity matrix."""
        element = ET.fromstring(
            '<feConvolveMatrix kernelMatrix="1 0 0 0 1 0 0 0 1" order="3"/>'
        )

        params = filter_instance._parse_parameters(element)

        assert params.matrix == [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
        assert params.order == "3"
        assert params.divisor == 1.0
        assert params.bias == 0.0
        assert params.edge_mode == EdgeMode.DUPLICATE

    def test_parse_edge_detection_sobel_matrix(self, filter_instance, mock_context):
        """Test parsing Sobel edge detection matrix."""
        element = ET.fromstring(
            '<feConvolveMatrix kernelMatrix="-1 0 1 -2 0 2 -1 0 1" order="3"/>'
        )

        params = filter_instance._parse_parameters(element)

        expected_matrix = [-1.0, 0.0, 1.0, -2.0, 0.0, 2.0, -1.0, 0.0, 1.0]
        assert params.matrix == expected_matrix
        assert params.order == "3"

    def test_parse_laplacian_edge_detection_matrix(self, filter_instance, mock_context):
        """Test parsing Laplacian edge detection matrix."""
        element = ET.fromstring(
            '<feConvolveMatrix kernelMatrix="0 -1 0 -1 4 -1 0 -1 0" order="3"/>'
        )

        params = filter_instance._parse_parameters(element)

        expected_matrix = [0.0, -1.0, 0.0, -1.0, 4.0, -1.0, 0.0, -1.0, 0.0]
        assert params.matrix == expected_matrix

    def test_parse_blur_matrix_5x5(self, filter_instance, mock_context):
        """Test parsing 5x5 blur matrix."""
        kernel = "1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1"
        element = ET.fromstring(
            f'<feConvolveMatrix kernelMatrix="{kernel}" order="5" divisor="25"/>'
        )

        params = filter_instance._parse_parameters(element)

        assert len(params.matrix) == 25
        assert all(val == 1.0 for val in params.matrix)
        assert params.order == "5"
        assert params.divisor == 25.0

    def test_parse_with_all_attributes(self, filter_instance, mock_context):
        """Test parsing element with all possible attributes."""
        element = ET.fromstring('''
            <feConvolveMatrix
                kernelMatrix="-1 -1 -1 -1 8 -1 -1 -1 -1"
                order="3"
                divisor="1"
                bias="0.5"
                targetX="1"
                targetY="1"
                edgeMode="wrap"
                preserveAlpha="true"/>
        ''')

        params = filter_instance._parse_parameters(element)

        expected_matrix = [-1.0, -1.0, -1.0, -1.0, 8.0, -1.0, -1.0, -1.0, -1.0]
        assert params.matrix == expected_matrix
        assert params.divisor == 1.0
        assert params.bias == 0.5
        assert params.target_x == 1
        assert params.target_y == 1
        assert params.edge_mode == EdgeMode.WRAP
        assert params.preserve_alpha is True

    def test_parse_invalid_matrix_size(self, filter_instance, mock_context):
        """Test parsing fails with matrix size mismatch."""
        element = ET.fromstring(
            '<feConvolveMatrix kernelMatrix="1 0 0 0 1" order="3"/>'
        )

        with pytest.raises(ConvolveMatrixValidationError, match="Matrix size mismatch"):
            filter_instance._parse_parameters(element)

    def test_parse_invalid_order_value(self, filter_instance, mock_context):
        """Test parsing fails with invalid order value."""
        element = ET.fromstring(
            '<feConvolveMatrix kernelMatrix="1 0 0 0 1 0 0 0 1" order="invalid"/>'
        )

        with pytest.raises(ConvolveMatrixValidationError, match="Invalid order"):
            filter_instance._parse_parameters(element)

    def test_parse_missing_kernel_matrix(self, filter_instance, mock_context):
        """Test parsing fails when kernelMatrix is missing."""
        element = ET.fromstring('<feConvolveMatrix order="3"/>')

        with pytest.raises(ConvolveMatrixValidationError, match="kernelMatrix is required"):
            filter_instance._parse_parameters(element)


class TestVectorConvolutionDecision:
    """Test logic for deciding between vector and EMF approaches."""

    @pytest.fixture
    def filter_instance(self):
        return ConvolveMatrixFilter()

    def test_identity_matrix_uses_vector(self, filter_instance):
        """Test identity matrix can use vector approach (pass-through)."""
        params = ConvolveMatrixParameters(
            matrix=[0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0],
            order="3"
        )

        result = filter_instance._can_use_vector_approach(params)

        assert result is True

    def test_sobel_horizontal_uses_vector(self, filter_instance):
        """Test Sobel horizontal edge detection can use vector approach."""
        params = ConvolveMatrixParameters(
            matrix=[-1.0, 0.0, 1.0, -2.0, 0.0, 2.0, -1.0, 0.0, 1.0],
            order="3"
        )

        result = filter_instance._can_use_vector_approach(params)

        assert result is True

    def test_sobel_vertical_uses_vector(self, filter_instance):
        """Test Sobel vertical edge detection can use vector approach."""
        params = ConvolveMatrixParameters(
            matrix=[-1.0, -2.0, -1.0, 0.0, 0.0, 0.0, 1.0, 2.0, 1.0],
            order="3"
        )

        result = filter_instance._can_use_vector_approach(params)

        assert result is True

    def test_laplacian_uses_vector(self, filter_instance):
        """Test Laplacian edge detection can use vector approach."""
        params = ConvolveMatrixParameters(
            matrix=[0.0, -1.0, 0.0, -1.0, 4.0, -1.0, 0.0, -1.0, 0.0],
            order="3"
        )

        result = filter_instance._can_use_vector_approach(params)

        assert result is True

    def test_complex_arbitrary_matrix_uses_emf(self, filter_instance):
        """Test complex arbitrary matrix requires EMF approach."""
        params = ConvolveMatrixParameters(
            matrix=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9],
            order="3"
        )

        result = filter_instance._can_use_vector_approach(params)

        assert result is False

    def test_large_matrix_5x5_uses_emf(self, filter_instance):
        """Test 5x5 matrix typically requires EMF approach."""
        matrix = [1.0] * 25  # 5x5 uniform matrix
        params = ConvolveMatrixParameters(matrix=matrix, order="5")

        result = filter_instance._can_use_vector_approach(params)

        assert result is False

    def test_gaussian_blur_approximation_uses_emf(self, filter_instance):
        """Test Gaussian blur approximation uses EMF approach."""
        params = ConvolveMatrixParameters(
            matrix=[1.0, 2.0, 1.0, 2.0, 4.0, 2.0, 1.0, 2.0, 1.0],
            order="3",
            divisor=16.0
        )

        result = filter_instance._can_use_vector_approach(params)

        assert result is False


class TestVectorConversionImplementation:
    """Test vector-first approach for simple edge detection matrices."""

    @pytest.fixture
    def filter_instance(self):
        return ConvolveMatrixFilter()

    @pytest.fixture
    def mock_context(self):
        context = Mock()
        context.unit_converter = Mock()
        context.unit_converter.to_emu.return_value = 63500
        context.viewport = {'width': 100, 'height': 100}
        return context

    def test_sobel_horizontal_vector_conversion(self, filter_instance, mock_context):
        """Test Sobel horizontal creates vector dashed stroke outline."""
        params = ConvolveMatrixParameters(
            matrix=[-1.0, 0.0, 1.0, -2.0, 0.0, 2.0, -1.0, 0.0, 1.0],
            order="3"
        )

        result = filter_instance._apply_vector_convolution(params, mock_context)

        assert '<a:ln' in result
        assert 'val="dash"' in result
        assert 'algn="ctr"' in result  # Center alignment for edge detection

    def test_sobel_vertical_vector_conversion(self, filter_instance, mock_context):
        """Test Sobel vertical creates vector dashed stroke outline."""
        params = ConvolveMatrixParameters(
            matrix=[-1.0, -2.0, -1.0, 0.0, 0.0, 0.0, 1.0, 2.0, 1.0],
            order="3"
        )

        result = filter_instance._apply_vector_convolution(params, mock_context)

        assert '<a:ln' in result
        assert 'val="dash"' in result
        assert 'algn="ctr"' in result

    def test_laplacian_vector_conversion(self, filter_instance, mock_context):
        """Test Laplacian creates vector outline with double dash pattern."""
        params = ConvolveMatrixParameters(
            matrix=[0.0, -1.0, 0.0, -1.0, 4.0, -1.0, 0.0, -1.0, 0.0],
            order="3"
        )

        result = filter_instance._apply_vector_convolution(params, mock_context)

        assert '<a:ln' in result
        assert 'val="dashDot"' in result  # More complex pattern for Laplacian
        assert 'algn="ctr"' in result

    def test_identity_vector_conversion_passthrough(self, filter_instance, mock_context):
        """Test identity matrix creates pass-through (no effect)."""
        params = ConvolveMatrixParameters(
            matrix=[0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0],
            order="3"
        )

        result = filter_instance._apply_vector_convolution(params, mock_context)

        # Identity should produce minimal or no DrawingML
        assert result == "" or "<!-- Identity pass-through -->" in result


class TestEMFConvolutionFallback:
    """Test EMF-based convolution for complex matrices."""

    @pytest.fixture
    def filter_instance(self):
        return ConvolveMatrixFilter()

    @pytest.fixture
    def mock_context(self):
        context = Mock()
        context.unit_converter = Mock()
        context.unit_converter.to_emu.return_value = 63500
        context.viewport = {'width': 100, 'height': 100}
        context.element = Mock()
        return context

    def test_complex_matrix_emf_processing(self, filter_instance, mock_context):
        """Test complex matrix uses EMF processing."""
        # Setup mock for the instance's EMF processor
        mock_emf_processor = Mock()
        mock_emf_processor.process_convolution.return_value = {
            'emf_blob': b'mock_emf_data',
            'width': 100,
            'height': 100
        }
        filter_instance._emf_processor = mock_emf_processor

        params = ConvolveMatrixParameters(
            matrix=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9],
            order="3"
        )

        result = filter_instance._apply_emf_convolution(params, mock_context)

        # Verify EMF processor was called
        mock_emf_processor.process_convolution.assert_called_once_with(
            params, mock_context
        )

        # Verify result contains EMF reference
        assert 'r:embed=' in result or 'blip' in result

    def test_5x5_blur_matrix_emf_processing(self, filter_instance, mock_context):
        """Test 5x5 blur matrix uses EMF processing."""
        # Setup mock for the instance's EMF processor
        mock_emf_processor = Mock()
        mock_emf_processor.process_convolution.return_value = {
            'emf_blob': b'mock_emf_data',
            'width': 100,
            'height': 100
        }
        filter_instance._emf_processor = mock_emf_processor

        matrix = [1.0] * 25  # 5x5 uniform blur
        params = ConvolveMatrixParameters(matrix=matrix, order="5", divisor=25.0)

        result = filter_instance._apply_emf_convolution(params, mock_context)

        # Verify EMF processor was called with correct parameters
        mock_emf_processor.process_convolution.assert_called_once_with(params, mock_context)
        called_params = mock_emf_processor.process_convolution.call_args[0][0]
        assert len(called_params.matrix) == 25
        assert called_params.divisor == 25.0

    def test_emf_processor_edge_mode_handling(self, filter_instance, mock_context):
        """Test EMF processor handles different edge modes."""
        params = ConvolveMatrixParameters(
            matrix=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9],
            order="3",
            edge_mode=EdgeMode.WRAP
        )

        # Setup mock for the instance's EMF processor
        mock_emf_processor = Mock()
        mock_emf_processor.process_convolution.return_value = {
            'emf_blob': b'mock_data',
            'width': 100,
            'height': 100
        }
        filter_instance._emf_processor = mock_emf_processor

        filter_instance._apply_emf_convolution(params, mock_context)

        # Verify edge mode was passed correctly
        called_params = mock_emf_processor.process_convolution.call_args[0][0]
        assert called_params.edge_mode == EdgeMode.WRAP


class TestConvolveMatrixIntegration:
    """Test full filter application and integration."""

    @pytest.fixture
    def filter_instance(self):
        return ConvolveMatrixFilter()

    @pytest.fixture
    def mock_context(self):
        context = Mock()
        context.unit_converter = Mock()
        context.unit_converter.to_emu.return_value = 63500
        context.viewport = {'width': 100, 'height': 100}
        context.element = Mock()
        return context

    def test_apply_sobel_edge_detection_success(self, filter_instance, mock_context):
        """Test applying Sobel edge detection returns successful vector result."""
        element = ET.fromstring(
            '<feConvolveMatrix kernelMatrix="-1 0 1 -2 0 2 -1 0 1" order="3"/>'
        )

        result = filter_instance.apply(element, mock_context)

        assert result.is_success()
        assert result.get_metadata()['filter_type'] == 'feConvolveMatrix'
        assert result.get_metadata()['approach'] == 'vector'
        assert '<a:ln' in result.get_drawingml()

    def test_apply_complex_matrix_emf_fallback(self, filter_instance, mock_context):
        """Test applying complex matrix falls back to EMF approach."""
        # Setup mock for the instance's EMF processor
        mock_emf_processor = Mock()
        mock_emf_processor.process_convolution.return_value = {
            'emf_blob': b'mock_emf_data',
            'width': 100,
            'height': 100
        }
        filter_instance._emf_processor = mock_emf_processor

        element = ET.fromstring(
            '<feConvolveMatrix kernelMatrix="0.1 0.2 0.3 0.4 0.5 0.6 0.7 0.8 0.9" order="3"/>'
        )

        result = filter_instance.apply(element, mock_context)

        assert result.is_success()
        assert result.get_metadata()['filter_type'] == 'feConvolveMatrix'
        assert result.get_metadata()['approach'] == 'emf'

    def test_apply_invalid_matrix_validation_error(self, filter_instance, mock_context):
        """Test applying invalid matrix returns validation error."""
        element = ET.fromstring(
            '<feConvolveMatrix kernelMatrix="1 0 0 0 1" order="3"/>'  # Wrong size
        )

        result = filter_instance.apply(element, mock_context)

        assert not result.is_success()
        assert "Matrix size mismatch" in result.get_error_message()
        assert result.get_metadata()['filter_type'] == 'feConvolveMatrix'

    def test_validate_parameters_valid_element(self, filter_instance, mock_context):
        """Test parameter validation passes for valid element."""
        element = ET.fromstring(
            '<feConvolveMatrix kernelMatrix="1 0 0 0 1 0 0 0 1" order="3"/>'
        )

        result = filter_instance.validate_parameters(element, mock_context)

        assert result is True

    def test_validate_parameters_invalid_element(self, filter_instance, mock_context):
        """Test parameter validation fails for invalid element."""
        element = ET.fromstring(
            '<feConvolveMatrix kernelMatrix="1 0 0" order="3"/>'  # Wrong size
        )

        result = filter_instance.validate_parameters(element, mock_context)

        assert result is False


class TestConvolveMatrixPerformance:
    """Test performance considerations and optimizations."""

    @pytest.fixture
    def filter_instance(self):
        return ConvolveMatrixFilter()

    def test_vector_approach_preferred_for_simple_matrices(self, filter_instance):
        """Test vector approach is preferred for performance on simple matrices."""
        sobel_params = ConvolveMatrixParameters(
            matrix=[-1.0, 0.0, 1.0, -2.0, 0.0, 2.0, -1.0, 0.0, 1.0],
            order="3"
        )

        assert filter_instance._can_use_vector_approach(sobel_params) is True

    def test_emf_fallback_for_complex_matrices(self, filter_instance):
        """Test EMF fallback is used for complex matrices to maintain quality."""
        complex_params = ConvolveMatrixParameters(
            matrix=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9],
            order="3"
        )

        assert filter_instance._can_use_vector_approach(complex_params) is False

    def test_matrix_complexity_scoring(self, filter_instance):
        """Test matrix complexity scoring for decision making."""
        # Simple identity-like matrix (low complexity)
        simple_params = ConvolveMatrixParameters(
            matrix=[0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0],
            order="3"
        )
        simple_score = filter_instance._calculate_matrix_complexity(simple_params)

        # Complex arbitrary matrix (high complexity)
        complex_params = ConvolveMatrixParameters(
            matrix=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9],
            order="3"
        )
        complex_score = filter_instance._calculate_matrix_complexity(complex_params)

        assert simple_score < complex_score


class TestConvolveMatrixEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def filter_instance(self):
        return ConvolveMatrixFilter()

    @pytest.fixture
    def mock_context(self):
        context = Mock()
        context.unit_converter = Mock()
        context.unit_converter.to_emu.return_value = 63500
        return context

    def test_zero_matrix_handling(self, filter_instance, mock_context):
        """Test handling of all-zero matrix."""
        element = ET.fromstring(
            '<feConvolveMatrix kernelMatrix="0 0 0 0 0 0 0 0 0" order="3"/>'
        )

        result = filter_instance.apply(element, mock_context)

        # Zero matrix should be handled gracefully
        assert result.is_success()

    def test_single_element_matrix(self, filter_instance, mock_context):
        """Test handling of 1x1 matrix."""
        element = ET.fromstring(
            '<feConvolveMatrix kernelMatrix="2.5" order="1"/>'
        )

        result = filter_instance.apply(element, mock_context)

        assert result.is_success()

    def test_very_large_matrix_values(self, filter_instance, mock_context):
        """Test handling of very large matrix values."""
        element = ET.fromstring(
            '<feConvolveMatrix kernelMatrix="1000 -1000 1000 -1000 1000 -1000 1000 -1000 1000" order="3"/>'
        )

        result = filter_instance.apply(element, mock_context)

        # Should fall back to EMF for extreme values
        assert result.is_success()
        assert result.get_metadata()['approach'] == 'emf'

    def test_division_by_zero_protection(self, filter_instance, mock_context):
        """Test protection against division by zero."""
        element = ET.fromstring(
            '<feConvolveMatrix kernelMatrix="1 0 0 0 1 0 0 0 1" order="3" divisor="0"/>'
        )

        result = filter_instance.apply(element, mock_context)

        # Should handle division by zero gracefully
        assert not result.is_success()
        assert "divisor cannot be zero" in result.get_error_message()

    def test_negative_divisor_handling(self, filter_instance, mock_context):
        """Test handling of negative divisor values."""
        element = ET.fromstring(
            '<feConvolveMatrix kernelMatrix="1 0 0 0 1 0 0 0 1" order="3" divisor="-2"/>'
        )

        result = filter_instance.apply(element, mock_context)

        # Negative divisor should be allowed (creates inversion effect)
        assert result.is_success()