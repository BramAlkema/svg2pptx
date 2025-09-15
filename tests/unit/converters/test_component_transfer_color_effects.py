#!/usr/bin/env python3
"""
Unit tests for feComponentTransfer PowerPoint color effects integration (Task 2.4, Subtasks 2.4.2-2.4.8).

This test suite focuses on the PowerPoint color effects integration for component transfer,
particularly testing the a:duotone + a:biLevel + a:grayscl effect combinations and
color effect mapping strategies.

Focus Areas:
- Subtask 2.4.2: Tests for a:duotone + a:biLevel + a:grayscl effect mapping
- Subtask 2.4.4: Build threshold detection for a:biLevel conversion (binary effects)
- Subtask 2.4.5: Implement duotone mapping (a:duotone) for two-color transfers
- Subtask 2.4.6: Add grayscale conversion (a:grayscl) for luminance-only transfers
- Subtask 2.4.7: Handle gamma correction mapping to PowerPoint color effects
- Subtask 2.4.8: Verify component transfer effects maintain vector quality where possible
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys
from lxml import etree as ET

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from src.converters.filters.geometric.component_transfer import ComponentTransferFilter, ComponentTransferParameters
from src.converters.filters.core.base import FilterContext


class TestBinaryThresholdDetection:
    """Test threshold detection for a:biLevel conversion (Subtask 2.4.4)."""

    def setup_method(self):
        """Setup test fixtures."""
        self.filter = ComponentTransferFilter()

        self.mock_context = Mock(spec=FilterContext)
        self.mock_context.unit_converter = Mock()
        self.mock_context.unit_converter.to_emu.return_value = 25400
        self.mock_context.color_parser = Mock()
        self.mock_context.color_parser.parse.return_value = "#FFFFFF"

    def test_binary_threshold_function_detection(self):
        """Test detection of binary threshold functions."""
        # Test various binary patterns
        binary_patterns = [
            [0.0, 1.0],        # Standard binary
            [0, 1],            # Integer binary
            [1.0, 0.0]         # Inverted binary
        ]

        for pattern in binary_patterns:
            function = {'type': 'discrete', 'table_values': pattern}
            is_binary = self.filter._is_binary_threshold(function)
            assert is_binary, f"Pattern {pattern} should be detected as binary"

    def test_non_binary_function_detection(self):
        """Test detection that non-binary functions are not flagged as binary."""
        # Test various non-binary patterns
        non_binary_patterns = [
            [0.2, 0.8],           # Duotone
            [0.0, 0.5, 1.0],      # Three-level gradient
            [0.1, 0.3, 0.7, 0.9], # Multi-level
            [0.33, 0.66]          # Non-extreme values
        ]

        for pattern in non_binary_patterns:
            function = {'type': 'discrete', 'table_values': pattern}
            is_binary = self.filter._is_binary_threshold(function)
            assert not is_binary, f"Pattern {pattern} should not be detected as binary"

    def test_bilevel_effect_generation(self):
        """Test a:biLevel effect generation for binary transfers."""
        params = ComponentTransferParameters(
            input_source="SourceGraphic",
            red_function={'type': 'discrete', 'table_values': [0.0, 1.0]},
            green_function={'type': 'discrete', 'table_values': [0.0, 1.0]},
            blue_function={'type': 'discrete', 'table_values': [0.0, 1.0]},
            alpha_function={'type': 'identity'}
        )

        bilevel_effect = self.filter._generate_bilevel_effect(params, self.mock_context)

        # Should generate proper a:biLevel DrawingML
        assert "a:biLevel" in bilevel_effect
        assert "thresh=" in bilevel_effect

        # Should include threshold calculation
        assert "50000" in bilevel_effect or "thresh" in bilevel_effect

    def test_threshold_value_calculation(self):
        """Test threshold value calculation for binary effects."""
        # Test different binary patterns and their thresholds
        test_cases = [
            ([0.0, 1.0], 50000),   # 50% threshold
            ([0.2, 0.8], 50000),   # Still 50% for symmetric
            ([0.0, 0.6], 30000),   # 30% threshold
            ([0.4, 1.0], 70000),   # 70% threshold
        ]

        for table_values, expected_threshold in test_cases:
            function = {'type': 'discrete', 'table_values': table_values}
            threshold = self.filter._calculate_threshold(function)

            # Allow some tolerance in threshold calculation
            assert abs(threshold - expected_threshold) <= 5000, \
                f"Threshold for {table_values} should be approximately {expected_threshold}"

    def test_bilevel_with_inverted_colors(self):
        """Test a:biLevel with inverted color mapping."""
        params = ComponentTransferParameters(
            input_source="SourceGraphic",
            red_function={'type': 'discrete', 'table_values': [1.0, 0.0]},  # Inverted
            green_function={'type': 'discrete', 'table_values': [1.0, 0.0]},
            blue_function={'type': 'discrete', 'table_values': [1.0, 0.0]},
            alpha_function={'type': 'identity'}
        )

        bilevel_effect = self.filter._generate_bilevel_effect(params, self.mock_context)

        # Should handle inverted mapping
        assert "a:biLevel" in bilevel_effect
        assert "invert" in bilevel_effect.lower() or "reverse" in bilevel_effect.lower()


class TestDuotoneMapping:
    """Test duotone mapping (a:duotone) for two-color transfers (Subtask 2.4.5)."""

    def setup_method(self):
        """Setup test fixtures."""
        self.filter = ComponentTransferFilter()

        self.mock_context = Mock(spec=FilterContext)
        self.mock_context.unit_converter = Mock()
        self.mock_context.unit_converter.to_emu.return_value = 25400
        self.mock_context.color_parser = Mock()

    def test_duotone_function_detection(self):
        """Test detection of duotone transfer functions."""
        # Test duotone patterns (two distinct non-binary values)
        duotone_patterns = [
            [0.2, 0.8],       # Classic duotone
            [0.1, 0.9],       # High contrast duotone
            [0.3, 0.7],       # Medium contrast duotone
            [0.15, 0.85]      # Asymmetric duotone
        ]

        for pattern in duotone_patterns:
            function = {'type': 'discrete', 'table_values': pattern}
            is_duotone = self.filter._is_duotone(function)
            assert is_duotone, f"Pattern {pattern} should be detected as duotone"

    def test_duotone_effect_generation(self):
        """Test a:duotone effect generation for two-color transfers."""
        # Mock color parser to return different colors
        self.mock_context.color_parser.parse.side_effect = ["#FF0000", "#0000FF"]

        params = ComponentTransferParameters(
            input_source="SourceGraphic",
            red_function={'type': 'discrete', 'table_values': [0.2, 0.8]},
            green_function={'type': 'discrete', 'table_values': [0.1, 0.9]},
            blue_function={'type': 'discrete', 'table_values': [0.3, 0.7]},
            alpha_function={'type': 'identity'}
        )

        duotone_effect = self.filter._generate_duotone_effect(params, self.mock_context)

        # Should generate proper a:duotone DrawingML
        assert "a:duotone" in duotone_effect
        assert "srgbClr" in duotone_effect

        # Should call color parser for duotone colors
        assert self.mock_context.color_parser.parse.call_count >= 2

    def test_duotone_color_calculation(self):
        """Test duotone color calculation from table values."""
        params = ComponentTransferParameters(
            input_source="SourceGraphic",
            red_function={'type': 'discrete', 'table_values': [0.2, 0.8]},
            green_function={'type': 'discrete', 'table_values': [0.1, 0.9]},
            blue_function={'type': 'discrete', 'table_values': [0.3, 0.7]},
            alpha_function={'type': 'identity'}
        )

        colors = self.filter._calculate_duotone_colors(params)

        # Should return two colors calculated from RGB values
        assert len(colors) == 2
        assert all(color.startswith('#') for color in colors)

    def test_duotone_with_single_channel(self):
        """Test duotone detection with single channel modification."""
        # Set up mock to return valid color strings
        self.mock_context.color_parser.parse.side_effect = ["#330000", "#CCFFFF"]

        params = ComponentTransferParameters(
            input_source="SourceGraphic",
            red_function={'type': 'discrete', 'table_values': [0.2, 0.8]},  # Duotone in red
            green_function={'type': 'identity'},  # Identity in green/blue
            blue_function={'type': 'identity'},
            alpha_function={'type': 'identity'}
        )

        duotone_effect = self.filter._generate_duotone_effect(params, self.mock_context)

        # Should still generate duotone effect for single-channel modification
        assert "a:duotone" in duotone_effect

    def test_duotone_with_different_channel_patterns(self):
        """Test duotone with different patterns in different channels."""
        # Set up mock to return valid color strings
        self.mock_context.color_parser.parse.side_effect = ["#194C66", "#E5B299"]

        params = ComponentTransferParameters(
            input_source="SourceGraphic",
            red_function={'type': 'discrete', 'table_values': [0.1, 0.9]},    # High contrast
            green_function={'type': 'discrete', 'table_values': [0.3, 0.7]},  # Medium contrast
            blue_function={'type': 'discrete', 'table_values': [0.4, 0.6]},   # Low contrast
            alpha_function={'type': 'identity'}
        )

        duotone_effect = self.filter._generate_duotone_effect(params, self.mock_context)

        # Should adapt to different channel contrasts
        assert "a:duotone" in duotone_effect


class TestGrayscaleConversion:
    """Test grayscale conversion (a:grayscl) for luminance-only transfers (Subtask 2.4.6)."""

    def setup_method(self):
        """Setup test fixtures."""
        self.filter = ComponentTransferFilter()

        self.mock_context = Mock(spec=FilterContext)
        self.mock_context.unit_converter = Mock()
        self.mock_context.unit_converter.to_emu.return_value = 25400
        self.mock_context.color_parser = Mock()
        self.mock_context.color_parser.parse.return_value = "#FFFFFF"

    def test_grayscale_function_detection(self):
        """Test detection of grayscale conversion functions."""
        # Standard luminance weights: R=0.299, G=0.587, B=0.114
        grayscale_function_r = {'type': 'linear', 'slope': 0.299, 'intercept': 0.0}
        grayscale_function_g = {'type': 'linear', 'slope': 0.587, 'intercept': 0.0}
        grayscale_function_b = {'type': 'linear', 'slope': 0.114, 'intercept': 0.0}

        assert self.filter._is_grayscale_component(grayscale_function_r, 'red')
        assert self.filter._is_grayscale_component(grayscale_function_g, 'green')
        assert self.filter._is_grayscale_component(grayscale_function_b, 'blue')

    def test_grayscale_effect_generation(self):
        """Test a:grayscl effect generation for luminance conversion."""
        params = ComponentTransferParameters(
            input_source="SourceGraphic",
            red_function={'type': 'linear', 'slope': 0.299, 'intercept': 0.0},
            green_function={'type': 'linear', 'slope': 0.587, 'intercept': 0.0},
            blue_function={'type': 'linear', 'slope': 0.114, 'intercept': 0.0},
            alpha_function={'type': 'identity'}
        )

        grayscale_effect = self.filter._generate_grayscale_effect(params, self.mock_context)

        # Should generate proper a:grayscl DrawingML
        assert "a:grayscl" in grayscale_effect
        assert "luminance" in grayscale_effect.lower()

    def test_custom_grayscale_weights(self):
        """Test grayscale with custom luminance weights."""
        # Custom weights that still produce grayscale
        params = ComponentTransferParameters(
            input_source="SourceGraphic",
            red_function={'type': 'linear', 'slope': 0.33, 'intercept': 0.0},   # Equal weights
            green_function={'type': 'linear', 'slope': 0.33, 'intercept': 0.0},
            blue_function={'type': 'linear', 'slope': 0.34, 'intercept': 0.0},
            alpha_function={'type': 'identity'}
        )

        grayscale_effect = self.filter._generate_grayscale_effect(params, self.mock_context)

        # Should handle custom weights
        assert "a:grayscl" in grayscale_effect
        assert "custom" in grayscale_effect.lower() or "weights" in grayscale_effect.lower()

    def test_single_channel_grayscale_detection(self):
        """Test detection of single-channel grayscale conversion."""
        # Only red channel active (common for red-channel grayscale)
        params = ComponentTransferParameters(
            input_source="SourceGraphic",
            red_function={'type': 'linear', 'slope': 1.0, 'intercept': 0.0},
            green_function={'type': 'linear', 'slope': 0.0, 'intercept': 0.0},
            blue_function={'type': 'linear', 'slope': 0.0, 'intercept': 0.0},
            alpha_function={'type': 'identity'}
        )

        is_grayscale = self.filter._is_grayscale_conversion(params)
        # This pattern should be detected as single-channel grayscale
        assert is_grayscale, "Single channel (red=1.0, green=0.0, blue=0.0) should be detected as grayscale"

    def test_inverted_grayscale_detection(self):
        """Test detection of inverted grayscale conversion."""
        params = ComponentTransferParameters(
            input_source="SourceGraphic",
            red_function={'type': 'linear', 'slope': -0.299, 'intercept': 1.0},   # Inverted
            green_function={'type': 'linear', 'slope': -0.587, 'intercept': 1.0},
            blue_function={'type': 'linear', 'slope': -0.114, 'intercept': 1.0},
            alpha_function={'type': 'identity'}
        )

        grayscale_effect = self.filter._generate_grayscale_effect(params, self.mock_context)

        # Should handle inverted grayscale
        assert "a:grayscl" in grayscale_effect
        assert "invert" in grayscale_effect.lower() or "negative" in grayscale_effect.lower()


class TestGammaCorrectionMapping:
    """Test gamma correction mapping to PowerPoint color effects (Subtask 2.4.7)."""

    def setup_method(self):
        """Setup test fixtures."""
        self.filter = ComponentTransferFilter()

        self.mock_context = Mock(spec=FilterContext)
        self.mock_context.unit_converter = Mock()
        self.mock_context.unit_converter.to_emu.return_value = 25400
        self.mock_context.color_parser = Mock()
        self.mock_context.color_parser.parse.return_value = "#FFFFFF"

    def test_gamma_function_detection(self):
        """Test detection of gamma correction functions."""
        gamma_functions = [
            {'type': 'gamma', 'amplitude': 1.0, 'exponent': 2.2, 'offset': 0.0},  # Standard sRGB
            {'type': 'gamma', 'amplitude': 1.0, 'exponent': 1.8, 'offset': 0.0},  # Mac gamma
            {'type': 'gamma', 'amplitude': 1.2, 'exponent': 2.0, 'offset': 0.1},  # Custom gamma
        ]

        for gamma_func in gamma_functions:
            is_gamma = self.filter._is_gamma_correction(gamma_func)
            assert is_gamma, f"Function {gamma_func} should be detected as gamma correction"

    def test_gamma_effect_generation(self):
        """Test gamma correction effect generation."""
        params = ComponentTransferParameters(
            input_source="SourceGraphic",
            red_function={'type': 'gamma', 'amplitude': 1.0, 'exponent': 2.2, 'offset': 0.0},
            green_function={'type': 'gamma', 'amplitude': 1.0, 'exponent': 2.2, 'offset': 0.0},
            blue_function={'type': 'gamma', 'amplitude': 1.0, 'exponent': 2.2, 'offset': 0.0},
            alpha_function={'type': 'identity'}
        )

        gamma_effect = self.filter._generate_gamma_effect(params, self.mock_context)

        # Should generate gamma correction DrawingML
        assert "gamma" in gamma_effect.lower()
        assert "correction" in gamma_effect.lower()

        # Should include gamma value
        assert "2.2" in gamma_effect or "22" in gamma_effect  # Could be scaled

    def test_different_gamma_values(self):
        """Test handling of different gamma values."""
        gamma_values = [1.0, 1.4, 1.8, 2.2, 2.4, 3.0]

        for gamma_value in gamma_values:
            params = ComponentTransferParameters(
                input_source="SourceGraphic",
                red_function={'type': 'gamma', 'amplitude': 1.0, 'exponent': gamma_value, 'offset': 0.0}
            )

            gamma_effect = self.filter._generate_gamma_effect(params, self.mock_context)

            # Should adapt to different gamma values
            assert "gamma" in gamma_effect.lower()
            # Should include reference to the gamma value
            assert str(gamma_value) in gamma_effect or str(int(gamma_value * 10)) in gamma_effect

    def test_gamma_with_amplitude_and_offset(self):
        """Test gamma correction with amplitude and offset parameters."""
        params = ComponentTransferParameters(
            input_source="SourceGraphic",
            red_function={'type': 'gamma', 'amplitude': 1.5, 'exponent': 2.0, 'offset': 0.1},
            green_function={'type': 'gamma', 'amplitude': 1.5, 'exponent': 2.0, 'offset': 0.1},
            blue_function={'type': 'gamma', 'amplitude': 1.5, 'exponent': 2.0, 'offset': 0.1},
            alpha_function={'type': 'identity'}
        )

        gamma_effect = self.filter._generate_gamma_effect(params, self.mock_context)

        # Should handle amplitude and offset
        assert "gamma" in gamma_effect.lower()
        assert "amplitude" in gamma_effect.lower() or "offset" in gamma_effect.lower()

    def test_per_channel_gamma_correction(self):
        """Test per-channel gamma correction with different values."""
        params = ComponentTransferParameters(
            input_source="SourceGraphic",
            red_function={'type': 'gamma', 'amplitude': 1.0, 'exponent': 2.2, 'offset': 0.0},   # sRGB
            green_function={'type': 'gamma', 'amplitude': 1.0, 'exponent': 1.8, 'offset': 0.0}, # Mac
            blue_function={'type': 'gamma', 'amplitude': 1.0, 'exponent': 2.4, 'offset': 0.0},  # Custom
            alpha_function={'type': 'identity'}
        )

        gamma_effect = self.filter._generate_gamma_effect(params, self.mock_context)

        # Should handle per-channel gamma correction
        assert "gamma" in gamma_effect.lower()
        # Note: Per-channel handling indicated by different gamma values, not explicit text
        assert "2.2" in gamma_effect or "1.8" in gamma_effect or "2.4" in gamma_effect


class TestColorEffectCombinations:
    """Test combinations of PowerPoint color effects (Subtask 2.4.2)."""

    def setup_method(self):
        """Setup test fixtures."""
        self.filter = ComponentTransferFilter()

        self.mock_context = Mock(spec=FilterContext)
        self.mock_context.unit_converter = Mock()
        self.mock_context.unit_converter.to_emu.return_value = 25400
        self.mock_context.color_parser = Mock()
        self.mock_context.color_parser.parse.return_value = "#FFFFFF"

    def test_bilevel_duotone_combination(self):
        """Test combination of a:biLevel and a:duotone effects."""
        params = ComponentTransferParameters(
            input_source="SourceGraphic",
            red_function={'type': 'discrete', 'table_values': [0.0, 1.0]},   # Binary
            green_function={'type': 'discrete', 'table_values': [0.2, 0.8]}, # Duotone
            blue_function={'type': 'identity'},
            alpha_function={'type': 'identity'}
        )

        drawingml = self.filter._generate_component_transfer_drawingml(params, self.mock_context)

        # Should indicate combined effects
        assert "combined" in drawingml.lower() or "mixed" in drawingml.lower()

    def test_grayscale_gamma_combination(self):
        """Test combination of a:grayscl and gamma correction effects."""
        params = ComponentTransferParameters(
            input_source="SourceGraphic",
            red_function={'type': 'linear', 'slope': 0.299, 'intercept': 0.0},    # Grayscale
            green_function={'type': 'linear', 'slope': 0.587, 'intercept': 0.0},  # Grayscale
            blue_function={'type': 'gamma', 'amplitude': 1.0, 'exponent': 2.2, 'offset': 0.0}, # Gamma
            alpha_function={'type': 'identity'}
        )

        drawingml = self.filter._generate_component_transfer_drawingml(params, self.mock_context)

        # Should handle grayscale + gamma combination
        assert "grayscale" in drawingml.lower() or "a:grayscl" in drawingml
        assert "gamma" in drawingml.lower()

    def test_all_effects_combination(self):
        """Test combination of all effect types in single transfer."""
        params = ComponentTransferParameters(
            input_source="SourceGraphic",
            red_function={'type': 'discrete', 'table_values': [0.0, 1.0]},        # Binary
            green_function={'type': 'discrete', 'table_values': [0.2, 0.8]},      # Duotone
            blue_function={'type': 'gamma', 'amplitude': 1.0, 'exponent': 2.2, 'offset': 0.0}, # Gamma
            alpha_function={'type': 'linear', 'slope': 0.8, 'intercept': 0.1}     # Alpha modification
        )

        drawingml = self.filter._generate_component_transfer_drawingml(params, self.mock_context)

        # Should indicate complex multi-effect processing
        assert "complex" in drawingml.lower() or "multi" in drawingml.lower()

    def test_effect_priority_selection(self):
        """Test effect priority when multiple effects could apply."""
        # Scenario where RGB could be interpreted as grayscale OR duotone
        params = ComponentTransferParameters(
            input_source="SourceGraphic",
            red_function={'type': 'linear', 'slope': 0.33, 'intercept': 0.0},
            green_function={'type': 'linear', 'slope': 0.33, 'intercept': 0.0},
            blue_function={'type': 'linear', 'slope': 0.34, 'intercept': 0.0},
            alpha_function={'type': 'identity'}
        )

        effect_type = self.filter._determine_primary_effect_type(params)

        # Should select the most appropriate effect (likely grayscale for equal weights)
        assert effect_type in ['grayscale', 'duotone', 'custom']


class TestVectorQualityIntegration:
    """Test vector quality maintenance in color effects (Subtask 2.4.8)."""

    def setup_method(self):
        """Setup test fixtures."""
        self.filter = ComponentTransferFilter()

        self.mock_context = Mock(spec=FilterContext)
        self.mock_context.unit_converter = Mock()
        self.mock_context.unit_converter.to_emu.return_value = 25400
        self.mock_context.color_parser = Mock()
        self.mock_context.color_parser.parse.return_value = "#FFFFFF"

    def test_native_powerpoint_effect_usage(self):
        """Test usage of native PowerPoint effects for best quality."""
        # Test each native effect type
        test_cases = [
            ('binary', "a:biLevel"),
            ('duotone', "a:duotone"),
            ('grayscale', "a:grayscl")
        ]

        for effect_type, expected_element in test_cases:
            if effect_type == 'binary':
                params = ComponentTransferParameters(
                    input_source="SourceGraphic",
                    red_function={'type': 'discrete', 'table_values': [0.0, 1.0]}
                )
            elif effect_type == 'duotone':
                params = ComponentTransferParameters(
                    input_source="SourceGraphic",
                    red_function={'type': 'discrete', 'table_values': [0.2, 0.8]}
                )
            else:  # grayscale
                params = ComponentTransferParameters(
                    input_source="SourceGraphic",
                    red_function={'type': 'linear', 'slope': 0.299, 'intercept': 0.0},
                    green_function={'type': 'linear', 'slope': 0.587, 'intercept': 0.0},
                    blue_function={'type': 'linear', 'slope': 0.114, 'intercept': 0.0}
                )

            drawingml = self.filter._generate_component_transfer_drawingml(params, self.mock_context)

            # Should use native PowerPoint effect
            assert expected_element in drawingml

    def test_vector_quality_comments(self):
        """Test that DrawingML includes vector quality maintenance comments."""
        params = ComponentTransferParameters(
            input_source="SourceGraphic",
            red_function={'type': 'discrete', 'table_values': [0.0, 1.0]}
        )

        drawingml = self.filter._generate_component_transfer_drawingml(params, self.mock_context)

        # Should include quality maintenance comments
        assert "vector" in drawingml.lower()
        assert "quality" in drawingml.lower() or "native" in drawingml.lower()

    def test_fallback_quality_handling(self):
        """Test quality handling when falling back to complex effects."""
        # Complex transfer that might require fallback
        params = ComponentTransferParameters(
            input_source="SourceGraphic",
            red_function={'type': 'table', 'table_values': [0.0, 0.25, 0.5, 0.75, 1.0]},
            green_function={'type': 'table', 'table_values': [0.1, 0.3, 0.6, 0.8, 0.9]},
            blue_function={'type': 'table', 'table_values': [0.2, 0.4, 0.7, 0.85, 0.95]}
        )

        drawingml = self.filter._generate_component_transfer_drawingml(params, self.mock_context)

        # Should indicate quality handling approach
        assert "quality" in drawingml.lower() or "fallback" in drawingml.lower()

    def test_powerpoint_compatibility_verification(self):
        """Test PowerPoint compatibility verification for generated effects."""
        params = ComponentTransferParameters(
            input_source="SourceGraphic",
            red_function={'type': 'discrete', 'table_values': [0.2, 0.8]}
        )

        drawingml = self.filter._generate_component_transfer_drawingml(params, self.mock_context)

        # Should indicate PowerPoint compatibility
        assert "powerpoint" in drawingml.lower() or "compatible" in drawingml.lower()

        # Should use proper DrawingML namespace
        assert drawingml.count("<a:") >= 1  # At least one DrawingML element


if __name__ == "__main__":
    pytest.main([__file__, "-v"])