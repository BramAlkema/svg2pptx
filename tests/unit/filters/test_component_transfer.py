#!/usr/bin/env python3
"""
Tests for ComponentTransfer filter processor.

Tests the comprehensive component transfer functionality including
transfer function parsing, pattern detection, and PowerPoint integration.
"""

import pytest
from unittest.mock import Mock, patch
from lxml import etree as ET

from core.filters.component_transfer import (
    ComponentTransferProcessor,
    ComponentTransferParameters,
    ComponentTransferException,
    TransferFunctionType,
    create_component_transfer_processor
)
from core.filters.base import FilterContext, FilterResult, FilterStrategy


class TestComponentTransferParameters:
    """Test ComponentTransferParameters data structure."""

    def test_initialization_defaults(self):
        """Test default parameter initialization."""
        params = ComponentTransferParameters()

        assert params.red_function["type"] == TransferFunctionType.IDENTITY
        assert params.green_function["type"] == TransferFunctionType.IDENTITY
        assert params.blue_function["type"] == TransferFunctionType.IDENTITY
        assert params.alpha_function["type"] == TransferFunctionType.IDENTITY

    def test_initialization_with_functions(self):
        """Test initialization with specific transfer functions."""
        red_func = {"type": TransferFunctionType.LINEAR, "slope": 1.5, "intercept": 0.1}
        green_func = {"type": TransferFunctionType.GAMMA, "amplitude": 1.0, "exponent": 2.2, "offset": 0.0}

        params = ComponentTransferParameters(
            red_function=red_func,
            green_function=green_func
        )

        assert params.red_function == red_func
        assert params.green_function == green_func
        assert params.blue_function["type"] == TransferFunctionType.IDENTITY
        assert params.alpha_function["type"] == TransferFunctionType.IDENTITY

    def test_get_all_functions(self):
        """Test getting all functions as dictionary."""
        linear_func = {"type": TransferFunctionType.LINEAR, "slope": 2.0, "intercept": 0.5}
        params = ComponentTransferParameters(red_function=linear_func)

        all_functions = params.get_all_functions()

        assert "red" in all_functions
        assert "green" in all_functions
        assert "blue" in all_functions
        assert "alpha" in all_functions
        assert all_functions["red"] == linear_func

    def test_has_heterogeneous_functions_false(self):
        """Test heterogeneous function detection when all are same type."""
        params = ComponentTransferParameters()  # All identity functions

        assert params.has_heterogeneous_functions() is False

    def test_has_heterogeneous_functions_true(self):
        """Test heterogeneous function detection when types differ."""
        linear_func = {"type": TransferFunctionType.LINEAR, "slope": 1.0, "intercept": 0.0}
        gamma_func = {"type": TransferFunctionType.GAMMA, "amplitude": 1.0, "exponent": 2.2, "offset": 0.0}

        params = ComponentTransferParameters(
            red_function=linear_func,
            green_function=gamma_func
        )

        assert params.has_heterogeneous_functions() is True

    def test_complexity_score_identity(self):
        """Test complexity calculation for identity functions."""
        params = ComponentTransferParameters()  # All identity

        complexity = params.get_complexity_score()

        # Base (0.5) + 4 identity functions (4 * 0.1) = 0.9
        assert abs(complexity - 0.9) < 0.01

    def test_complexity_score_discrete_binary(self):
        """Test complexity calculation for binary discrete functions."""
        discrete_func = {"type": TransferFunctionType.DISCRETE, "table_values": [0.0, 1.0]}
        params = ComponentTransferParameters(
            red_function=discrete_func,
            green_function=discrete_func,
            blue_function=discrete_func,
            alpha_function=discrete_func  # Set all 4 channels to be homogeneous
        )

        complexity = params.get_complexity_score()

        # Base (0.5) + 4 binary discrete (4 * 0.5) + no heterogeneous penalty = 2.5
        assert abs(complexity - 2.5) < 0.01

    def test_complexity_score_heterogeneous(self):
        """Test complexity calculation with heterogeneous functions."""
        linear_func = {"type": TransferFunctionType.LINEAR, "slope": 1.0, "intercept": 0.0}
        gamma_func = {"type": TransferFunctionType.GAMMA, "amplitude": 1.0, "exponent": 2.2, "offset": 0.0}

        params = ComponentTransferParameters(
            red_function=linear_func,
            green_function=gamma_func
        )

        complexity = params.get_complexity_score()

        # Base (0.5) + linear (0.4) + gamma (0.6) + 2 identity (0.2) + heterogeneous (1.0) = 2.7
        assert abs(complexity - 2.7) < 0.01

    def test_complexity_score_table_function_heterogeneous(self):
        """Test complexity calculation for table functions with heterogeneous channels."""
        table_func = {"type": TransferFunctionType.TABLE, "table_values": [0.0, 0.5, 1.0]}
        params = ComponentTransferParameters(red_function=table_func)

        complexity = params.get_complexity_score()

        # Base (0.5) + 1 table (3 values * 0.2 = 0.6) + 3 identity (3 * 0.1 = 0.3) + heterogeneous (1.0) = 2.4
        assert abs(complexity - 2.4) < 0.01

    def test_complexity_score_table_function_homogeneous(self):
        """Test complexity calculation for table functions without heterogeneous penalty."""
        table_func = {"type": TransferFunctionType.TABLE, "table_values": [0.0, 0.5, 1.0]}
        params = ComponentTransferParameters(
            red_function=table_func,
            green_function=table_func,
            blue_function=table_func,
            alpha_function=table_func
        )

        complexity = params.get_complexity_score()

        # Base (0.5) + 4 table functions (4 * 3 * 0.2 = 2.4) + no heterogeneous penalty = 2.9
        assert abs(complexity - 2.9) < 0.01


class TestComponentTransferProcessor:
    """Test ComponentTransferProcessor functionality."""

    @pytest.fixture
    def processor(self):
        """Create a ComponentTransferProcessor instance for testing."""
        return ComponentTransferProcessor()

    @pytest.fixture
    def mock_context(self):
        """Create mock FilterContext for testing."""
        context = Mock(spec=FilterContext)
        context.unit_converter = Mock()
        context.color_parser = Mock()
        context.transform_parser = Mock()
        context.viewport = {"width": 100, "height": 100}
        return context

    def test_processor_initialization(self, processor):
        """Test processor initialization."""
        assert processor.filter_type == 'feComponentTransfer'
        assert processor.policy is None

    def test_processor_initialization_with_policy(self):
        """Test processor initialization with policy."""
        policy = Mock()
        processor = ComponentTransferProcessor(policy=policy)

        assert processor.policy == policy

    def test_can_apply_valid_element(self, processor, mock_context):
        """Test can_apply with valid feComponentTransfer element."""
        element = ET.Element('feComponentTransfer')

        assert processor.can_apply(element, mock_context) is True

    def test_can_apply_invalid_element(self, processor, mock_context):
        """Test can_apply with invalid element."""
        element = ET.Element('feGaussianBlur')

        assert processor.can_apply(element, mock_context) is False

    def test_can_apply_none_element(self, processor, mock_context):
        """Test can_apply with None element."""
        assert processor.can_apply(None, mock_context) is False

    def test_parse_transfer_function_identity(self, processor):
        """Test parsing identity transfer function."""
        element = ET.Element('feFuncR')
        element.set('type', 'identity')

        func = processor._parse_transfer_function(element)

        assert func["type"] == TransferFunctionType.IDENTITY

    def test_parse_transfer_function_linear(self, processor):
        """Test parsing linear transfer function."""
        element = ET.Element('feFuncR')
        element.set('type', 'linear')
        element.set('slope', '1.5')
        element.set('intercept', '0.2')

        func = processor._parse_transfer_function(element)

        assert func["type"] == TransferFunctionType.LINEAR
        assert func["slope"] == 1.5
        assert func["intercept"] == 0.2

    def test_parse_transfer_function_gamma(self, processor):
        """Test parsing gamma transfer function."""
        element = ET.Element('feFuncG')
        element.set('type', 'gamma')
        element.set('amplitude', '1.2')
        element.set('exponent', '2.2')
        element.set('offset', '0.1')

        func = processor._parse_transfer_function(element)

        assert func["type"] == TransferFunctionType.GAMMA
        assert func["amplitude"] == 1.2
        assert func["exponent"] == 2.2
        assert func["offset"] == 0.1

    def test_parse_transfer_function_discrete(self, processor):
        """Test parsing discrete transfer function."""
        element = ET.Element('feFuncB')
        element.set('type', 'discrete')
        element.set('tableValues', '0.0 1.0')

        func = processor._parse_transfer_function(element)

        assert func["type"] == TransferFunctionType.DISCRETE
        assert func["table_values"] == [0.0, 1.0]

    def test_parse_transfer_function_table(self, processor):
        """Test parsing table transfer function."""
        element = ET.Element('feFuncA')
        element.set('type', 'table')
        element.set('tableValues', '0.0,0.5,1.0')

        func = processor._parse_transfer_function(element)

        assert func["type"] == TransferFunctionType.TABLE
        assert func["table_values"] == [0.0, 0.5, 1.0]

    def test_parse_number_list_spaces(self, processor):
        """Test parsing space-separated number list."""
        result = processor._parse_number_list("0.0 0.5 1.0")

        assert result == [0.0, 0.5, 1.0]

    def test_parse_number_list_commas(self, processor):
        """Test parsing comma-separated number list."""
        result = processor._parse_number_list("0.0,0.5,1.0")

        assert result == [0.0, 0.5, 1.0]

    def test_parse_number_list_mixed(self, processor):
        """Test parsing mixed separator number list."""
        result = processor._parse_number_list("0.0, 0.5 1.0")

        assert result == [0.0, 0.5, 1.0]

    def test_parse_number_list_empty(self, processor):
        """Test parsing empty number list."""
        result = processor._parse_number_list("")

        assert result == []

    def test_parse_component_transfer_parameters_full(self, processor):
        """Test parsing complete component transfer parameters."""
        element = ET.Element('feComponentTransfer')

        # Add function elements
        red_func = ET.SubElement(element, 'feFuncR')
        red_func.set('type', 'linear')
        red_func.set('slope', '1.5')

        green_func = ET.SubElement(element, 'feFuncG')
        green_func.set('type', 'gamma')
        green_func.set('exponent', '2.2')

        blue_func = ET.SubElement(element, 'feFuncB')
        blue_func.set('type', 'discrete')
        blue_func.set('tableValues', '0.0 1.0')

        alpha_func = ET.SubElement(element, 'feFuncA')
        alpha_func.set('type', 'table')
        alpha_func.set('tableValues', '0.0,0.5,1.0')

        params = processor._parse_component_transfer_parameters(element)

        assert params.red_function["type"] == TransferFunctionType.LINEAR
        assert params.red_function["slope"] == 1.5
        assert params.green_function["type"] == TransferFunctionType.GAMMA
        assert params.green_function["exponent"] == 2.2
        assert params.blue_function["type"] == TransferFunctionType.DISCRETE
        assert params.blue_function["table_values"] == [0.0, 1.0]
        assert params.alpha_function["type"] == TransferFunctionType.TABLE
        assert params.alpha_function["table_values"] == [0.0, 0.5, 1.0]

    def test_is_binary_threshold_true(self, processor):
        """Test binary threshold detection for valid binary pattern."""
        discrete_func = {"type": TransferFunctionType.DISCRETE, "table_values": [0.0, 1.0]}
        params = ComponentTransferParameters(
            red_function=discrete_func,
            green_function=discrete_func,
            blue_function=discrete_func
        )

        assert processor._is_binary_threshold(params) is True

    def test_is_binary_threshold_false_wrong_type(self, processor):
        """Test binary threshold detection with wrong function type."""
        linear_func = {"type": TransferFunctionType.LINEAR, "slope": 1.0, "intercept": 0.0}
        params = ComponentTransferParameters(red_function=linear_func)

        assert processor._is_binary_threshold(params) is False

    def test_is_binary_threshold_false_wrong_values(self, processor):
        """Test binary threshold detection with wrong table values."""
        discrete_func = {"type": TransferFunctionType.DISCRETE, "table_values": [0.2, 0.8]}
        params = ComponentTransferParameters(
            red_function=discrete_func,
            green_function=discrete_func,
            blue_function=discrete_func
        )

        assert processor._is_binary_threshold(params) is False

    def test_is_duotone_pattern_true(self, processor):
        """Test duotone pattern detection for valid duotone."""
        discrete_func = {"type": TransferFunctionType.DISCRETE, "table_values": [0.3, 0.7]}
        params = ComponentTransferParameters(
            red_function=discrete_func,
            green_function=discrete_func,
            blue_function=discrete_func
        )

        assert processor._is_duotone_pattern(params) is True

    def test_is_duotone_pattern_false_binary(self, processor):
        """Test duotone pattern detection rejects binary values."""
        discrete_func = {"type": TransferFunctionType.DISCRETE, "table_values": [0.0, 1.0]}
        params = ComponentTransferParameters(
            red_function=discrete_func,
            green_function=discrete_func,
            blue_function=discrete_func
        )

        assert processor._is_duotone_pattern(params) is False

    def test_is_grayscale_conversion_true(self, processor):
        """Test grayscale conversion detection for standard weights."""
        red_func = {"type": TransferFunctionType.LINEAR, "slope": 0.299, "intercept": 0.0}
        green_func = {"type": TransferFunctionType.LINEAR, "slope": 0.587, "intercept": 0.0}
        blue_func = {"type": TransferFunctionType.LINEAR, "slope": 0.114, "intercept": 0.0}

        params = ComponentTransferParameters(
            red_function=red_func,
            green_function=green_func,
            blue_function=blue_func
        )

        assert processor._is_grayscale_conversion(params) is True

    def test_is_grayscale_conversion_false_wrong_weights(self, processor):
        """Test grayscale conversion detection with wrong weights."""
        red_func = {"type": TransferFunctionType.LINEAR, "slope": 0.5, "intercept": 0.0}
        green_func = {"type": TransferFunctionType.LINEAR, "slope": 0.5, "intercept": 0.0}
        blue_func = {"type": TransferFunctionType.LINEAR, "slope": 0.5, "intercept": 0.0}

        params = ComponentTransferParameters(
            red_function=red_func,
            green_function=green_func,
            blue_function=blue_func
        )

        assert processor._is_grayscale_conversion(params) is False

    def test_is_gamma_correction_true(self, processor):
        """Test gamma correction detection for valid gamma."""
        gamma_func = {"type": TransferFunctionType.GAMMA, "amplitude": 1.0, "exponent": 2.2, "offset": 0.0}
        params = ComponentTransferParameters(
            red_function=gamma_func,
            green_function=gamma_func,
            blue_function=gamma_func
        )

        assert processor._is_gamma_correction(params) is True

    def test_is_gamma_correction_false_wrong_type(self, processor):
        """Test gamma correction detection with wrong function type."""
        linear_func = {"type": TransferFunctionType.LINEAR, "slope": 1.0, "intercept": 0.0}
        params = ComponentTransferParameters(red_function=linear_func)

        assert processor._is_gamma_correction(params) is False

    def test_is_gamma_correction_false_invalid_exponent(self, processor):
        """Test gamma correction detection with invalid exponent."""
        gamma_func = {"type": TransferFunctionType.GAMMA, "amplitude": 1.0, "exponent": 5.0, "offset": 0.0}
        params = ComponentTransferParameters(
            red_function=gamma_func,
            green_function=gamma_func,
            blue_function=gamma_func
        )

        assert processor._is_gamma_correction(params) is False

    def test_can_use_native_effects_binary_threshold(self, processor):
        """Test native effects detection for binary threshold."""
        discrete_func = {"type": TransferFunctionType.DISCRETE, "table_values": [0.0, 1.0]}
        params = ComponentTransferParameters(
            red_function=discrete_func,
            green_function=discrete_func,
            blue_function=discrete_func
        )

        assert processor._can_use_native_effects(params) is True

    def test_can_use_native_effects_duotone(self, processor):
        """Test native effects detection for duotone."""
        discrete_func = {"type": TransferFunctionType.DISCRETE, "table_values": [0.3, 0.7]}
        params = ComponentTransferParameters(
            red_function=discrete_func,
            green_function=discrete_func,
            blue_function=discrete_func
        )

        assert processor._can_use_native_effects(params) is True

    def test_can_use_native_effects_grayscale(self, processor):
        """Test native effects detection for grayscale."""
        red_func = {"type": TransferFunctionType.LINEAR, "slope": 0.299, "intercept": 0.0}
        green_func = {"type": TransferFunctionType.LINEAR, "slope": 0.587, "intercept": 0.0}
        blue_func = {"type": TransferFunctionType.LINEAR, "slope": 0.114, "intercept": 0.0}

        params = ComponentTransferParameters(
            red_function=red_func,
            green_function=green_func,
            blue_function=blue_func
        )

        assert processor._can_use_native_effects(params) is True

    def test_can_use_native_effects_gamma(self, processor):
        """Test native effects detection for gamma correction."""
        gamma_func = {"type": TransferFunctionType.GAMMA, "amplitude": 1.0, "exponent": 2.2, "offset": 0.0}
        params = ComponentTransferParameters(
            red_function=gamma_func,
            green_function=gamma_func,
            blue_function=gamma_func
        )

        assert processor._can_use_native_effects(params) is True

    def test_can_use_native_effects_false(self, processor):
        """Test native effects detection returns false for complex functions."""
        table_func = {"type": TransferFunctionType.TABLE, "table_values": [0.0, 0.3, 0.6, 1.0]}
        params = ComponentTransferParameters(red_function=table_func)

        assert processor._can_use_native_effects(params) is False

    def test_generate_binary_threshold_drawingml(self, processor, mock_context):
        """Test binary threshold DrawingML generation."""
        discrete_func = {"type": TransferFunctionType.DISCRETE, "table_values": [0.0, 1.0]}
        params = ComponentTransferParameters(
            red_function=discrete_func,
            green_function=discrete_func,
            blue_function=discrete_func
        )

        drawingml = processor._generate_binary_threshold_drawingml(params, mock_context)

        assert '<a:biLevel thresh="50000"/>' in drawingml
        assert '<a:effectLst>' in drawingml
        assert '</a:effectLst>' in drawingml

    def test_generate_duotone_drawingml(self, processor, mock_context):
        """Test duotone DrawingML generation."""
        red_func = {"type": TransferFunctionType.DISCRETE, "table_values": [0.2, 0.8]}
        green_func = {"type": TransferFunctionType.DISCRETE, "table_values": [0.1, 0.9]}
        blue_func = {"type": TransferFunctionType.DISCRETE, "table_values": [0.0, 1.0]}

        params = ComponentTransferParameters(
            red_function=red_func,
            green_function=green_func,
            blue_function=blue_func
        )

        drawingml = processor._generate_duotone_drawingml(params, mock_context)

        assert '<a:duotone>' in drawingml
        assert '<a:srgbClr val=' in drawingml
        assert '</a:duotone>' in drawingml

    def test_generate_grayscale_drawingml(self, processor, mock_context):
        """Test grayscale DrawingML generation."""
        red_func = {"type": TransferFunctionType.LINEAR, "slope": 0.299, "intercept": 0.0}
        params = ComponentTransferParameters(red_function=red_func)

        drawingml = processor._generate_grayscale_drawingml(params, mock_context)

        assert '<a:grayscl/>' in drawingml
        assert '<a:effectLst>' in drawingml

    def test_generate_gamma_drawingml_normal(self, processor, mock_context):
        """Test gamma DrawingML generation for normal gamma."""
        gamma_func = {"type": TransferFunctionType.GAMMA, "amplitude": 1.0, "exponent": 2.2, "offset": 0.0}
        params = ComponentTransferParameters(red_function=gamma_func)

        drawingml = processor._generate_gamma_drawingml(params, mock_context)

        assert '<a:gamma inv="false"/>' in drawingml

    def test_generate_gamma_drawingml_inverted(self, processor, mock_context):
        """Test gamma DrawingML generation for inverted gamma."""
        gamma_func = {"type": TransferFunctionType.GAMMA, "amplitude": 1.0, "exponent": 0.7, "offset": 0.0}
        params = ComponentTransferParameters(red_function=gamma_func)

        drawingml = processor._generate_gamma_drawingml(params, mock_context)

        assert '<a:gamma inv="true"/>' in drawingml

    def test_apply_native_strategy_binary_threshold(self, processor, mock_context):
        """Test applying native strategy for binary threshold."""
        element = ET.Element('feComponentTransfer')

        # Add discrete functions
        for channel in ['feFuncR', 'feFuncG', 'feFuncB']:
            func_elem = ET.SubElement(element, channel)
            func_elem.set('type', 'discrete')
            func_elem.set('tableValues', '0.0 1.0')

        result = processor.apply(element, mock_context)

        assert result.success is True
        assert result.strategy == FilterStrategy.NATIVE
        assert '<a:biLevel' in result.drawingml

    def test_apply_native_strategy_grayscale(self, processor, mock_context):
        """Test applying native strategy for grayscale conversion."""
        element = ET.Element('feComponentTransfer')

        # Add linear functions with luminance weights
        weights = [('feFuncR', '0.299'), ('feFuncG', '0.587'), ('feFuncB', '0.114')]
        for channel, weight in weights:
            func_elem = ET.SubElement(element, channel)
            func_elem.set('type', 'linear')
            func_elem.set('slope', weight)
            func_elem.set('intercept', '0.0')

        result = processor.apply(element, mock_context)

        assert result.success is True
        assert result.strategy == FilterStrategy.NATIVE
        assert '<a:grayscl/>' in result.drawingml

    def test_apply_approximation_strategy(self, processor, mock_context):
        """Test applying approximation strategy."""
        element = ET.Element('feComponentTransfer')

        # Add table function that doesn't match native patterns
        func_elem = ET.SubElement(element, 'feFuncR')
        func_elem.set('type', 'table')
        func_elem.set('tableValues', '0.0,0.3,0.6,1.0')

        result = processor.apply(element, mock_context)

        assert result.success is True
        assert result.strategy == FilterStrategy.APPROXIMATION
        assert '<a:lum' in result.drawingml

    def test_apply_emf_strategy_complex(self, processor, mock_context):
        """Test applying EMF strategy for complex functions."""
        # Mock policy to force EMF strategy
        policy = Mock()
        policy.decide_component_transfer_strategy.return_value = Mock(strategy=FilterStrategy.EMF_RASTERIZE)
        processor.policy = policy

        element = ET.Element('feComponentTransfer')

        result = processor.apply(element, mock_context)

        assert result.success is True
        assert result.strategy == FilterStrategy.EMF_RASTERIZE

    def test_apply_error_handling(self, processor, mock_context):
        """Test error handling during apply."""
        # Force error by providing invalid element
        element = None

        result = processor.apply(element, mock_context)

        assert result.success is False
        assert result.strategy == FilterStrategy.EMF_RASTERIZE
        assert "Component transfer processing failed" in result.error_message

    def test_validate_parameters_valid(self, processor, mock_context):
        """Test parameter validation with valid element."""
        element = ET.Element('feComponentTransfer')

        assert processor._validate_parameters(element, mock_context) is True

    def test_validate_parameters_invalid_element(self, processor, mock_context):
        """Test parameter validation with invalid element."""
        assert processor._validate_parameters(None, mock_context) is False

    def test_validate_parameters_invalid_context(self, processor):
        """Test parameter validation with invalid context."""
        element = ET.Element('feComponentTransfer')

        assert processor._validate_parameters(element, None) is False


class TestComponentTransferIntegration:
    """Test ComponentTransferProcessor integration patterns."""

    def test_processor_with_policy_integration(self):
        """Test processor integration with policy."""
        policy = Mock()
        policy.decide_component_transfer_strategy.return_value = Mock(strategy=FilterStrategy.NATIVE)

        processor = ComponentTransferProcessor(policy=policy)
        context = Mock(spec=FilterContext)

        element = ET.Element('feComponentTransfer')

        # Add discrete functions to all RGB channels to create binary threshold pattern
        for channel in ['feFuncR', 'feFuncG', 'feFuncB']:
            func_elem = ET.SubElement(element, channel)
            func_elem.set('type', 'discrete')
            func_elem.set('tableValues', '0.0 1.0')

        # Mock validation to pass
        with patch.object(processor, '_validate_parameters', return_value=True):
            result = processor.apply(element, context)

        # Policy should have been consulted
        policy.decide_component_transfer_strategy.assert_called_once()
        assert result.strategy == FilterStrategy.NATIVE

    def test_processor_factory_function(self):
        """Test processor factory function."""
        policy = Mock()
        processor = create_component_transfer_processor(policy=policy)

        assert isinstance(processor, ComponentTransferProcessor)
        assert processor.policy == policy

    def test_processor_factory_function_no_policy(self):
        """Test processor factory function without policy."""
        processor = create_component_transfer_processor()

        assert isinstance(processor, ComponentTransferProcessor)
        assert processor.policy is None

    def test_comprehensive_component_transfer_processing(self):
        """Test comprehensive component transfer processing workflow."""
        processor = ComponentTransferProcessor()
        context = Mock(spec=FilterContext)
        context.unit_converter = Mock()
        context.color_parser = Mock()
        context.transform_parser = Mock()

        # Create complex component transfer with mixed functions
        element = ET.Element('feComponentTransfer')

        # Binary threshold on red
        red_func = ET.SubElement(element, 'feFuncR')
        red_func.set('type', 'discrete')
        red_func.set('tableValues', '0.0 1.0')

        # Linear on green
        green_func = ET.SubElement(element, 'feFuncG')
        green_func.set('type', 'linear')
        green_func.set('slope', '1.5')
        green_func.set('intercept', '0.1')

        # Gamma on blue
        blue_func = ET.SubElement(element, 'feFuncB')
        blue_func.set('type', 'gamma')
        blue_func.set('amplitude', '1.0')
        blue_func.set('exponent', '2.2')
        blue_func.set('offset', '0.0')

        result = processor.apply(element, context)

        # Should succeed with approximation strategy due to mixed functions
        assert result.success is True
        assert result.strategy in [FilterStrategy.APPROXIMATION, FilterStrategy.EMF_RASTERIZE]

    def test_component_transfer_error_recovery(self):
        """Test component transfer error recovery patterns."""
        processor = ComponentTransferProcessor()
        context = Mock(spec=FilterContext)

        # Create element with invalid function parameters
        element = ET.Element('feComponentTransfer')
        func_elem = ET.SubElement(element, 'feFuncR')
        func_elem.set('type', 'linear')
        func_elem.set('slope', 'invalid')  # Invalid number

        # Should handle error gracefully
        result = processor.apply(element, context)

        assert result.success is False
        assert "Component transfer processing failed" in result.error_message


if __name__ == '__main__':
    pytest.main([__file__])