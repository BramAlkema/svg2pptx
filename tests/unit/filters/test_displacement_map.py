#!/usr/bin/env python3
"""
Tests for DisplacementMap filter processor.

Tests the comprehensive displacement map functionality including
channel mapping, scale calculations, and PowerPoint integration.
"""

import pytest
from unittest.mock import Mock, patch
from lxml import etree as ET

from core.filters.displacement_map import (
    DisplacementMapProcessor,
    DisplacementMapParameters,
    DisplacementMapException,
    DisplacementMapValidationError,
    create_displacement_map_processor
)
from core.filters.base import FilterContext, FilterResult, FilterStrategy


class TestDisplacementMapParameters:
    """Test DisplacementMapParameters data structure."""

    def test_initialization_defaults(self):
        """Test default parameter initialization."""
        params = DisplacementMapParameters()

        assert params.input_source == "SourceGraphic"
        assert params.displacement_source == "SourceGraphic"
        assert params.scale == 0.0
        assert params.x_channel_selector == "A"
        assert params.y_channel_selector == "A"
        assert params.result_name is None

    def test_initialization_with_all_parameters(self):
        """Test initialization with all parameters set."""
        params = DisplacementMapParameters(
            input_source="BackgroundImage",
            displacement_source="SourceAlpha",
            scale=20.0,
            x_channel_selector="R",
            y_channel_selector="G",
            result_name="displaced"
        )

        assert params.input_source == "BackgroundImage"
        assert params.displacement_source == "SourceAlpha"
        assert params.scale == 20.0
        assert params.x_channel_selector == "R"
        assert params.y_channel_selector == "G"
        assert params.result_name == "displaced"

    def test_invalid_channel_selector_defaults_to_alpha(self):
        """Test that invalid channel selectors default to 'A'."""
        params = DisplacementMapParameters(
            x_channel_selector="X",  # Invalid
            y_channel_selector="Y"   # Invalid
        )

        assert params.x_channel_selector == "A"
        assert params.y_channel_selector == "A"

    def test_valid_channel_selectors(self):
        """Test all valid channel selectors are accepted."""
        for channel in ["R", "G", "B", "A"]:
            params = DisplacementMapParameters(
                x_channel_selector=channel,
                y_channel_selector=channel
            )
            assert params.x_channel_selector == channel
            assert params.y_channel_selector == channel

    def test_complexity_score_minimal(self):
        """Test complexity calculation for minimal displacement."""
        params = DisplacementMapParameters(scale=0.0)

        complexity = params.get_complexity_score()

        # Base complexity only
        assert abs(complexity - 0.5) < 0.01

    def test_complexity_score_with_scale(self):
        """Test complexity calculation with scale factor."""
        params = DisplacementMapParameters(scale=10.0)

        complexity = params.get_complexity_score()

        # Base (0.5) + scale factor (10/20 = 0.5) = 1.0
        assert abs(complexity - 1.0) < 0.01

    def test_complexity_score_with_mixed_channels(self):
        """Test complexity calculation with different X/Y channels."""
        params = DisplacementMapParameters(
            x_channel_selector="R",
            y_channel_selector="G"
        )

        complexity = params.get_complexity_score()

        # Base (0.5) + mixed channels (0.5) + high-precision (0.3) = 1.3
        assert abs(complexity - 1.3) < 0.01

    def test_complexity_score_maximum(self):
        """Test complexity calculation with maximum parameters."""
        params = DisplacementMapParameters(
            scale=100.0,  # Should cap at 3x
            x_channel_selector="G",
            y_channel_selector="B"
        )

        complexity = params.get_complexity_score()

        # Base (0.5) + scale (capped at 3.0) + mixed (0.5) + precision (0.3) = 4.3
        assert abs(complexity - 4.3) < 0.01

    def test_requires_subdivision_false(self):
        """Test subdivision requirement for small scales."""
        params = DisplacementMapParameters(scale=3.0)

        assert params.requires_subdivision() is False

    def test_requires_subdivision_true(self):
        """Test subdivision requirement for large scales."""
        params = DisplacementMapParameters(scale=10.0)

        assert params.requires_subdivision() is True

    def test_get_channel_index(self):
        """Test channel index mapping."""
        params = DisplacementMapParameters()

        assert params.get_channel_index('R') == 0
        assert params.get_channel_index('G') == 1
        assert params.get_channel_index('B') == 2
        assert params.get_channel_index('A') == 3
        assert params.get_channel_index('X') == 3  # Invalid defaults to alpha


class TestDisplacementMapProcessor:
    """Test DisplacementMapProcessor functionality."""

    @pytest.fixture
    def processor(self):
        """Create a DisplacementMapProcessor instance for testing."""
        return DisplacementMapProcessor()

    @pytest.fixture
    def mock_context(self):
        """Create mock FilterContext for testing."""
        context = Mock(spec=FilterContext)
        context.services = Mock()
        context.viewport = {"width": 100, "height": 100}
        return context

    def test_processor_initialization(self, processor):
        """Test processor initialization."""
        assert processor.filter_type == 'feDisplacementMap'
        assert processor.policy is None
        assert processor.complexity_threshold == 3.0

    def test_processor_initialization_with_policy(self):
        """Test processor initialization with policy."""
        policy = Mock()
        processor = DisplacementMapProcessor(policy=policy)

        assert processor.policy == policy

    def test_can_apply_valid_element(self, processor, mock_context):
        """Test can_apply with valid feDisplacementMap element."""
        element = ET.Element('feDisplacementMap')

        assert processor.can_apply(element, mock_context) is True

    def test_can_apply_invalid_element(self, processor, mock_context):
        """Test can_apply with invalid element."""
        element = ET.Element('feGaussianBlur')

        assert processor.can_apply(element, mock_context) is False

    def test_can_apply_none_element(self, processor, mock_context):
        """Test can_apply with None element."""
        assert processor.can_apply(None, mock_context) is False

    def test_parse_displacement_map_parameters_minimal(self, processor):
        """Test parsing minimal displacement map parameters."""
        element = ET.Element('feDisplacementMap')

        params = processor._parse_displacement_map_parameters(element)

        assert params.input_source == "SourceGraphic"
        assert params.displacement_source == "SourceGraphic"
        assert params.scale == 0.0
        assert params.x_channel_selector == "A"
        assert params.y_channel_selector == "A"

    def test_parse_displacement_map_parameters_full(self, processor):
        """Test parsing complete displacement map parameters."""
        element = ET.Element('feDisplacementMap')
        element.set('in', 'BackgroundImage')
        element.set('in2', 'SourceAlpha')
        element.set('scale', '25.5')
        element.set('xChannelSelector', 'R')
        element.set('yChannelSelector', 'B')
        element.set('result', 'displacedOutput')

        params = processor._parse_displacement_map_parameters(element)

        assert params.input_source == "BackgroundImage"
        assert params.displacement_source == "SourceAlpha"
        assert params.scale == 25.5
        assert params.x_channel_selector == "R"
        assert params.y_channel_selector == "B"
        assert params.result_name == "displacedOutput"

    def test_parse_displacement_map_parameters_invalid_scale(self, processor):
        """Test parsing with invalid scale value."""
        element = ET.Element('feDisplacementMap')
        element.set('scale', 'invalid')

        with pytest.raises(DisplacementMapValidationError) as exc_info:
            processor._parse_displacement_map_parameters(element)

        assert "Invalid scale value" in str(exc_info.value)

    def test_parse_displacement_map_parameters_lowercase_channels(self, processor):
        """Test parsing with lowercase channel selectors."""
        element = ET.Element('feDisplacementMap')
        element.set('xChannelSelector', 'r')
        element.set('yChannelSelector', 'g')

        params = processor._parse_displacement_map_parameters(element)

        assert params.x_channel_selector == "R"
        assert params.y_channel_selector == "G"

    def test_can_use_vector_approach_small_scale(self, processor):
        """Test vector approach detection for small scales."""
        params = DisplacementMapParameters(scale=5.0)

        assert processor._can_use_vector_approach(params) is True

    def test_can_use_vector_approach_same_channels(self, processor):
        """Test vector approach detection for same X/Y channels."""
        params = DisplacementMapParameters(
            scale=15.0,
            x_channel_selector="R",
            y_channel_selector="R"
        )

        assert processor._can_use_vector_approach(params) is True

    def test_can_use_vector_approach_false(self, processor):
        """Test vector approach rejection for complex displacement."""
        params = DisplacementMapParameters(
            scale=50.0,
            x_channel_selector="R",
            y_channel_selector="G"
        )

        assert processor._can_use_vector_approach(params) is False

    def test_generate_transform_displacement_drawingml(self, processor, mock_context):
        """Test transform-based displacement DrawingML generation."""
        params = DisplacementMapParameters(scale=3.0)

        drawingml = processor._generate_transform_displacement_drawingml(params, mock_context)

        assert '<a:xfrm>' in drawingml
        assert '<a:off' in drawingml
        assert '<a:ext' in drawingml

    def test_generate_custom_geometry_drawingml(self, processor, mock_context):
        """Test custom geometry displacement DrawingML generation."""
        params = DisplacementMapParameters(scale=8.0)

        drawingml = processor._generate_custom_geometry_drawingml(params, mock_context)

        assert '<a:custGeom>' in drawingml
        assert '<a:pathLst>' in drawingml
        assert '<a:moveTo>' in drawingml
        assert '<a:lnTo>' in drawingml
        assert '<a:close/>' in drawingml

    def test_extract_channel_value(self, processor):
        """Test channel value extraction from RGBA pixel."""
        rgba_pixel = (255, 128, 64, 192)  # R=255, G=128, B=64, A=192

        # Test each channel extraction
        assert abs(processor._extract_channel_value(rgba_pixel, 'R') - 0.5) < 0.01
        assert abs(processor._extract_channel_value(rgba_pixel, 'G') - 0.0) < 0.01
        assert abs(processor._extract_channel_value(rgba_pixel, 'B') - (-0.25)) < 0.01
        assert abs(processor._extract_channel_value(rgba_pixel, 'A') - 0.25) < 0.01

    def test_calculate_adaptive_subdivisions(self, processor):
        """Test adaptive subdivision calculation."""
        # Small scale and short segment
        params1 = DisplacementMapParameters(scale=5.0)
        subdivs1 = processor._calculate_adaptive_subdivisions(params1, 10.0)
        assert 2 <= subdivs1 <= 5

        # Large scale and long segment
        params2 = DisplacementMapParameters(scale=50.0)
        subdivs2 = processor._calculate_adaptive_subdivisions(params2, 100.0)
        assert 10 <= subdivs2 <= 20

        # Very large values should cap at 20
        params3 = DisplacementMapParameters(scale=1000.0)
        subdivs3 = processor._calculate_adaptive_subdivisions(params3, 1000.0)
        assert subdivs3 == 20

    def test_clamp_displaced_point(self, processor):
        """Test displaced point clamping to bounds."""
        original_point = (50.0, 50.0)
        displacement = (30.0, -30.0)
        bounds = {
            'min_x': 0.0,
            'max_x': 100.0,
            'min_y': 0.0,
            'max_y': 100.0
        }

        clamped = processor._clamp_displaced_point(original_point, displacement, bounds)

        # 50 + 30 = 80 (within bounds)
        # 50 - 30 = 20 (within bounds)
        assert clamped == (80.0, 20.0)

    def test_clamp_displaced_point_exceeds_bounds(self, processor):
        """Test displaced point clamping when exceeding bounds."""
        original_point = (50.0, 50.0)
        displacement = (100.0, -100.0)
        bounds = {
            'min_x': 0.0,
            'max_x': 100.0,
            'min_y': 0.0,
            'max_y': 100.0
        }

        clamped = processor._clamp_displaced_point(original_point, displacement, bounds)

        # 50 + 100 = 150 -> clamped to 100
        # 50 - 100 = -50 -> clamped to 0
        assert clamped == (100.0, 0.0)

    def test_clamp_displaced_point_inverted_bounds(self, processor):
        """Test displaced point clamping with inverted bounds."""
        original_point = (50.0, 50.0)
        displacement = (10.0, 10.0)
        bounds = {
            'min_x': 100.0,  # Inverted
            'max_x': 0.0,
            'min_y': 100.0,  # Inverted
            'max_y': 0.0
        }

        clamped = processor._clamp_displaced_point(original_point, displacement, bounds)

        # Should handle inverted bounds gracefully
        assert clamped == (60.0, 60.0)

    def test_apply_native_strategy_minimal(self, processor, mock_context):
        """Test applying native strategy for minimal displacement."""
        element = ET.Element('feDisplacementMap')
        element.set('scale', '0.5')

        result = processor.apply(element, mock_context)

        assert result.success is True
        assert result.strategy == FilterStrategy.NATIVE
        assert "Minimal displacement" in result.drawingml

    def test_apply_native_strategy_transform(self, processor, mock_context):
        """Test applying native strategy with transform displacement."""
        element = ET.Element('feDisplacementMap')
        element.set('scale', '3.0')

        result = processor.apply(element, mock_context)

        assert result.success is True
        assert result.strategy == FilterStrategy.NATIVE
        assert '<a:xfrm>' in result.drawingml

    def test_apply_native_strategy_custom_geometry(self, processor, mock_context):
        """Test applying native strategy with custom geometry."""
        element = ET.Element('feDisplacementMap')
        element.set('scale', '8.0')

        result = processor.apply(element, mock_context)

        assert result.success is True
        assert result.strategy == FilterStrategy.NATIVE
        assert '<a:custGeom>' in result.drawingml

    def test_apply_approximation_strategy(self, processor, mock_context):
        """Test applying approximation strategy."""
        # Mock to force approximation
        with patch.object(processor, '_can_use_vector_approach', return_value=False):
            element = ET.Element('feDisplacementMap')
            element.set('scale', '15.0')
            element.set('xChannelSelector', 'R')
            element.set('yChannelSelector', 'G')

            result = processor.apply(element, mock_context)

        assert result.success is True
        assert result.strategy == FilterStrategy.APPROXIMATION
        assert '<a:xfrm>' in result.drawingml
        assert '<a:chOff' in result.drawingml

    def test_apply_emf_strategy_complex(self, processor, mock_context):
        """Test applying EMF strategy for complex displacement."""
        # Mock policy to force EMF strategy
        policy = Mock()
        policy.decide_displacement_map_strategy.return_value = Mock(strategy=FilterStrategy.EMF_RASTERIZE)
        processor.policy = policy

        element = ET.Element('feDisplacementMap')
        element.set('scale', '50.0')

        result = processor.apply(element, mock_context)

        assert result.success is True
        assert result.strategy == FilterStrategy.EMF_RASTERIZE
        assert "EMF rasterization" in result.drawingml

    def test_apply_error_handling(self, processor, mock_context):
        """Test error handling during apply."""
        # Force error by providing invalid element
        element = None

        result = processor.apply(element, mock_context)

        assert result.success is False
        assert result.strategy == FilterStrategy.EMF_RASTERIZE
        assert "Displacement map processing failed" in result.error_message

    def test_validate_parameters_valid(self, processor, mock_context):
        """Test parameter validation with valid element."""
        element = ET.Element('feDisplacementMap')

        assert processor._validate_parameters(element, mock_context) is True

    def test_validate_parameters_invalid_element(self, processor, mock_context):
        """Test parameter validation with invalid element."""
        assert processor._validate_parameters(None, mock_context) is False

    def test_validate_parameters_invalid_context(self, processor):
        """Test parameter validation with invalid context."""
        element = ET.Element('feDisplacementMap')

        assert processor._validate_parameters(element, None) is False


class TestDisplacementMapIntegration:
    """Test DisplacementMapProcessor integration patterns."""

    def test_processor_with_policy_integration(self):
        """Test processor integration with policy."""
        policy = Mock()
        policy.decide_displacement_map_strategy.return_value = Mock(strategy=FilterStrategy.NATIVE)

        processor = DisplacementMapProcessor(policy=policy)
        context = Mock(spec=FilterContext)

        element = ET.Element('feDisplacementMap')
        element.set('scale', '5.0')

        # Mock validation to pass
        with patch.object(processor, '_validate_parameters', return_value=True):
            result = processor.apply(element, context)

        # Policy should have been consulted
        policy.decide_displacement_map_strategy.assert_called_once()
        assert result.strategy == FilterStrategy.NATIVE

    def test_processor_factory_function(self):
        """Test processor factory function."""
        policy = Mock()
        processor = create_displacement_map_processor(policy=policy)

        assert isinstance(processor, DisplacementMapProcessor)
        assert processor.policy == policy

    def test_processor_factory_function_no_policy(self):
        """Test processor factory function without policy."""
        processor = create_displacement_map_processor()

        assert isinstance(processor, DisplacementMapProcessor)
        assert processor.policy is None

    def test_comprehensive_displacement_processing(self):
        """Test comprehensive displacement map processing workflow."""
        processor = DisplacementMapProcessor()
        context = Mock(spec=FilterContext)
        context.services = Mock()

        # Create complex displacement map
        element = ET.Element('feDisplacementMap')
        element.set('in', 'SourceGraphic')
        element.set('in2', 'BackgroundImage')
        element.set('scale', '12.0')
        element.set('xChannelSelector', 'R')
        element.set('yChannelSelector', 'R')  # Same channel for simplicity

        result = processor.apply(element, context)

        # Should succeed with appropriate strategy
        assert result.success is True
        assert result.strategy in [FilterStrategy.NATIVE, FilterStrategy.APPROXIMATION, FilterStrategy.EMF_RASTERIZE]
        assert 'scale' in result.metadata
        assert 'complexity' in result.metadata

    def test_displacement_error_recovery(self):
        """Test displacement map error recovery patterns."""
        processor = DisplacementMapProcessor()
        context = Mock(spec=FilterContext)

        # Create element with invalid scale
        element = ET.Element('feDisplacementMap')
        element.set('scale', 'not-a-number')

        # Should handle error gracefully
        result = processor.apply(element, context)

        assert result.success is False
        assert "Displacement map processing failed" in result.error_message

    def test_metadata_completeness(self):
        """Test that result metadata contains all expected fields."""
        processor = DisplacementMapProcessor()
        context = Mock(spec=FilterContext)
        context.services = Mock()

        element = ET.Element('feDisplacementMap')
        element.set('scale', '5.0')

        result = processor.apply(element, context)

        assert result.success is True
        assert 'filter_type' in result.metadata
        assert 'approach' in result.metadata
        assert 'scale' in result.metadata
        assert 'complexity' in result.metadata
        assert result.metadata['filter_type'] == 'feDisplacementMap'

    def test_channel_selector_case_insensitivity(self):
        """Test that channel selectors are case-insensitive."""
        processor = DisplacementMapProcessor()

        for lower, upper in [('r', 'R'), ('g', 'G'), ('b', 'B'), ('a', 'A')]:
            element = ET.Element('feDisplacementMap')
            element.set('xChannelSelector', lower)
            element.set('yChannelSelector', upper)

            params = processor._parse_displacement_map_parameters(element)
            assert params.x_channel_selector == upper
            assert params.y_channel_selector == upper

    def test_scale_strategy_selection(self):
        """Test that scale influences strategy selection correctly."""
        processor = DisplacementMapProcessor()
        context = Mock(spec=FilterContext)
        context.services = Mock()

        # Test different scale values
        scales_and_strategies = [
            (0.5, FilterStrategy.NATIVE),   # Minimal
            (5.0, FilterStrategy.NATIVE),   # Small
            (10.0, FilterStrategy.NATIVE),  # Medium (same channels)
        ]

        for scale, expected_strategy in scales_and_strategies:
            element = ET.Element('feDisplacementMap')
            element.set('scale', str(scale))
            element.set('xChannelSelector', 'A')
            element.set('yChannelSelector', 'A')  # Same channels

            result = processor.apply(element, context)
            assert result.success is True
            assert result.strategy == expected_strategy


if __name__ == '__main__':
    pytest.main([__file__])