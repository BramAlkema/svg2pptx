#!/usr/bin/env python3
"""
Unit tests for feComponentTransfer vector-first conversion (Task 2.4, Subtasks 2.4.1-2.4.8).

This test suite covers the vector-first feComponentTransfer implementation using PowerPoint
color effects like a:duotone, a:biLevel, and a:grayscl for component transfer functions.

Focus Areas:
- Subtask 2.4.1: Unit tests for component transfer function parsing
- Subtask 2.4.2: Tests for a:duotone + a:biLevel + a:grayscl effect mapping
- Subtask 2.4.3: feComponentTransfer parser with transfer function analysis
- Subtask 2.4.4: Threshold detection for a:biLevel conversion (binary effects)
- Subtask 2.4.5: Duotone mapping (a:duotone) for two-color transfers
- Subtask 2.4.6: Grayscale conversion (a:grayscl) for luminance-only transfers
- Subtask 2.4.7: Gamma correction mapping to PowerPoint color effects
- Subtask 2.4.8: Verify component transfer effects maintain vector quality
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


class TestComponentTransferFilterBasics:
    """Test basic ComponentTransferFilter functionality."""

    def setup_method(self):
        """Setup test fixtures."""
        self.filter = ComponentTransferFilter()

        # Mock FilterContext with standardized tools
        self.mock_context = Mock(spec=FilterContext)
        self.mock_context.unit_converter = Mock()
        self.mock_context.unit_converter.to_emu.return_value = 25400
        self.mock_context.color_parser = Mock()
        self.mock_context.color_parser.parse.return_value = "#FFFFFF"
        self.mock_context.transform_parser = Mock()
        self.mock_context.viewport_resolver = Mock()

    def test_filter_initialization(self):
        """Test ComponentTransferFilter initialization."""
        assert self.filter.filter_type == "component_transfer"
        assert self.filter.strategy == "vector_first"
        assert hasattr(self.filter, 'complexity_threshold')

    def test_can_apply_fecomponenttransfer_element(self):
        """Test can_apply returns True for feComponentTransfer elements."""
        element = ET.Element("feComponentTransfer")
        result = self.filter.can_apply(element, self.mock_context)
        assert result is True

    def test_can_apply_with_namespace(self):
        """Test can_apply handles namespaced elements correctly."""
        element = ET.Element("{http://www.w3.org/2000/svg}feComponentTransfer")
        result = self.filter.can_apply(element, self.mock_context)
        assert result is True

    def test_can_apply_non_fecomponenttransfer_element(self):
        """Test can_apply returns False for non-feComponentTransfer elements."""
        element = ET.Element("feGaussianBlur")
        result = self.filter.can_apply(element, self.mock_context)
        assert result is False

    def test_can_apply_none_element(self):
        """Test can_apply handles None element gracefully."""
        result = self.filter.can_apply(None, self.mock_context)
        assert result is False


class TestComponentTransferParameterParsing:
    """Test component transfer function parsing (Subtask 2.4.1)."""

    def setup_method(self):
        """Setup test fixtures."""
        self.filter = ComponentTransferFilter()

        self.mock_context = Mock(spec=FilterContext)
        self.mock_context.unit_converter = Mock()
        self.mock_context.unit_converter.to_emu.return_value = 25400
        self.mock_context.color_parser = Mock()
        self.mock_context.color_parser.parse.return_value = "#FFFFFF"

    def test_basic_component_transfer_parsing(self):
        """Test parsing basic feComponentTransfer parameters."""
        element = ET.Element("feComponentTransfer")
        element.set("in", "blur1")
        element.set("result", "transfer")

        params = self.filter._parse_component_transfer_parameters(element)

        assert params.input_source == "blur1"
        assert params.result_name == "transfer"

    def test_default_parameter_values(self):
        """Test default parameter values for feComponentTransfer."""
        element = ET.Element("feComponentTransfer")

        params = self.filter._parse_component_transfer_parameters(element)

        assert params.input_source == "SourceGraphic"  # SVG default
        assert params.result_name is None

    def test_discrete_transfer_function_parsing(self):
        """Test parsing discrete transfer function for red channel."""
        element = ET.Element("feComponentTransfer")
        red_func = ET.SubElement(element, "feFuncR")
        red_func.set("type", "discrete")
        red_func.set("tableValues", "0.2 0.8")

        params = self.filter._parse_component_transfer_parameters(element)

        assert params.red_function is not None
        assert params.red_function['type'] == 'discrete'
        assert params.red_function['table_values'] == [0.2, 0.8]

    def test_linear_transfer_function_parsing(self):
        """Test parsing linear transfer function for green channel."""
        element = ET.Element("feComponentTransfer")
        green_func = ET.SubElement(element, "feFuncG")
        green_func.set("type", "linear")
        green_func.set("slope", "1.5")
        green_func.set("intercept", "0.1")

        params = self.filter._parse_component_transfer_parameters(element)

        assert params.green_function is not None
        assert params.green_function['type'] == 'linear'
        assert params.green_function['slope'] == 1.5
        assert params.green_function['intercept'] == 0.1

    def test_gamma_transfer_function_parsing(self):
        """Test parsing gamma transfer function for blue channel."""
        element = ET.Element("feComponentTransfer")
        blue_func = ET.SubElement(element, "feFuncB")
        blue_func.set("type", "gamma")
        blue_func.set("amplitude", "2.0")
        blue_func.set("exponent", "0.5")
        blue_func.set("offset", "0.05")

        params = self.filter._parse_component_transfer_parameters(element)

        assert params.blue_function is not None
        assert params.blue_function['type'] == 'gamma'
        assert params.blue_function['amplitude'] == 2.0
        assert params.blue_function['exponent'] == 0.5
        assert params.blue_function['offset'] == 0.05

    def test_table_transfer_function_parsing(self):
        """Test parsing table transfer function for alpha channel."""
        element = ET.Element("feComponentTransfer")
        alpha_func = ET.SubElement(element, "feFuncA")
        alpha_func.set("type", "table")
        alpha_func.set("tableValues", "0.0 0.5 1.0")

        params = self.filter._parse_component_transfer_parameters(element)

        assert params.alpha_function is not None
        assert params.alpha_function['type'] == 'table'
        assert params.alpha_function['table_values'] == [0.0, 0.5, 1.0]

    def test_identity_transfer_function_parsing(self):
        """Test parsing identity transfer function."""
        element = ET.Element("feComponentTransfer")
        red_func = ET.SubElement(element, "feFuncR")
        red_func.set("type", "identity")

        params = self.filter._parse_component_transfer_parameters(element)

        assert params.red_function is not None
        assert params.red_function['type'] == 'identity'

    def test_multiple_channel_functions(self):
        """Test parsing multiple channel functions in single element."""
        element = ET.Element("feComponentTransfer")

        # Red channel - discrete
        red_func = ET.SubElement(element, "feFuncR")
        red_func.set("type", "discrete")
        red_func.set("tableValues", "0 1")

        # Green channel - linear
        green_func = ET.SubElement(element, "feFuncG")
        green_func.set("type", "linear")
        green_func.set("slope", "0.5")

        # Blue channel - gamma
        blue_func = ET.SubElement(element, "feFuncB")
        blue_func.set("type", "gamma")
        blue_func.set("exponent", "2.0")

        # Alpha channel - identity
        alpha_func = ET.SubElement(element, "feFuncA")
        alpha_func.set("type", "identity")

        params = self.filter._parse_component_transfer_parameters(element)

        assert params.red_function['type'] == 'discrete'
        assert params.green_function['type'] == 'linear'
        assert params.blue_function['type'] == 'gamma'
        assert params.alpha_function['type'] == 'identity'

    def test_invalid_transfer_function_type(self):
        """Test handling of invalid transfer function types."""
        element = ET.Element("feComponentTransfer")
        red_func = ET.SubElement(element, "feFuncR")
        red_func.set("type", "invalid_type")

        params = self.filter._parse_component_transfer_parameters(element)

        # Should default to identity for invalid types
        assert params.red_function['type'] == 'identity'

    def test_missing_required_parameters(self):
        """Test handling of missing required parameters."""
        element = ET.Element("feComponentTransfer")
        red_func = ET.SubElement(element, "feFuncR")
        red_func.set("type", "linear")
        # Missing slope and intercept

        params = self.filter._parse_component_transfer_parameters(element)

        # Should provide default values
        assert params.red_function['slope'] == 1.0  # Default
        assert params.red_function['intercept'] == 0.0  # Default


class TestTransferFunctionAnalysis:
    """Test transfer function analysis for PowerPoint mapping (Subtask 2.4.3)."""

    def setup_method(self):
        """Setup test fixtures."""
        self.filter = ComponentTransferFilter()

    def test_binary_threshold_detection(self):
        """Test detection of binary threshold functions for a:biLevel mapping."""
        # Test discrete function with binary values
        binary_function = {
            'type': 'discrete',
            'table_values': [0.0, 1.0]
        }

        transfer_type = self.filter._analyze_transfer_function(binary_function)
        assert transfer_type == 'binary'

    def test_duotone_detection(self):
        """Test detection of duotone functions for a:duotone mapping."""
        # Test discrete function with two distinct non-binary values
        duotone_function = {
            'type': 'discrete',
            'table_values': [0.2, 0.8]
        }

        transfer_type = self.filter._analyze_transfer_function(duotone_function)
        assert transfer_type == 'duotone'

    def test_grayscale_detection(self):
        """Test detection of grayscale functions for a:grayscl mapping."""
        # Test linear function that produces grayscale
        grayscale_function = {
            'type': 'linear',
            'slope': 0.3,  # Typical luminance weight
            'intercept': 0.0
        }

        transfer_type = self.filter._analyze_transfer_function(grayscale_function)
        assert transfer_type == 'grayscale'

    def test_gamma_correction_detection(self):
        """Test detection of gamma correction for color adjustment mapping."""
        # Test gamma function
        gamma_function = {
            'type': 'gamma',
            'amplitude': 1.0,
            'exponent': 2.2,  # Typical gamma value
            'offset': 0.0
        }

        transfer_type = self.filter._analyze_transfer_function(gamma_function)
        assert transfer_type == 'gamma'

    def test_identity_function_analysis(self):
        """Test analysis of identity functions."""
        identity_function = {'type': 'identity'}

        transfer_type = self.filter._analyze_transfer_function(identity_function)
        assert transfer_type == 'identity'

    def test_complex_table_function_analysis(self):
        """Test analysis of complex table functions."""
        # Test table function with smooth gradient
        complex_function = {
            'type': 'table',
            'table_values': [0.0, 0.25, 0.5, 0.75, 1.0]
        }

        transfer_type = self.filter._analyze_transfer_function(complex_function)
        assert transfer_type == 'gradient'


class TestPowerPointEffectMapping:
    """Test PowerPoint color effect mapping (Subtask 2.4.2)."""

    def setup_method(self):
        """Setup test fixtures."""
        self.filter = ComponentTransferFilter()

        self.mock_context = Mock(spec=FilterContext)
        self.mock_context.unit_converter = Mock()
        self.mock_context.unit_converter.to_emu.return_value = 25400
        self.mock_context.color_parser = Mock()
        self.mock_context.color_parser.parse.return_value = "#FFFFFF"

    def test_bilevel_effect_mapping(self):
        """Test a:biLevel effect mapping for binary transfers (Subtask 2.4.4)."""
        params = ComponentTransferParameters(
            input_source="SourceGraphic",
            red_function={'type': 'discrete', 'table_values': [0.0, 1.0]},
            green_function={'type': 'discrete', 'table_values': [0.0, 1.0]},
            blue_function={'type': 'discrete', 'table_values': [0.0, 1.0]},
            alpha_function={'type': 'identity'}
        )

        drawingml = self.filter._generate_component_transfer_drawingml(params, self.mock_context)

        # Should contain a:biLevel for binary threshold effects
        assert "a:biLevel" in drawingml
        assert "thresh=" in drawingml
        assert "binary" in drawingml.lower()

    def test_duotone_effect_mapping(self):
        """Test a:duotone effect mapping for two-color transfers (Subtask 2.4.5)."""
        params = ComponentTransferParameters(
            input_source="SourceGraphic",
            red_function={'type': 'discrete', 'table_values': [0.2, 0.8]},
            green_function={'type': 'discrete', 'table_values': [0.1, 0.9]},
            blue_function={'type': 'discrete', 'table_values': [0.3, 0.7]},
            alpha_function={'type': 'identity'}
        )

        drawingml = self.filter._generate_component_transfer_drawingml(params, self.mock_context)

        # Should contain a:duotone for two-color effects
        assert "a:duotone" in drawingml
        assert "srgbClr" in drawingml
        assert "duotone" in drawingml.lower()

    def test_grayscale_effect_mapping(self):
        """Test a:grayscl effect mapping for luminance conversion (Subtask 2.4.6)."""
        params = ComponentTransferParameters(
            input_source="SourceGraphic",
            red_function={'type': 'linear', 'slope': 0.299, 'intercept': 0.0},
            green_function={'type': 'linear', 'slope': 0.587, 'intercept': 0.0},
            blue_function={'type': 'linear', 'slope': 0.114, 'intercept': 0.0},
            alpha_function={'type': 'identity'}
        )

        drawingml = self.filter._generate_component_transfer_drawingml(params, self.mock_context)

        # Should contain a:grayscl for luminance-only conversion
        assert "a:grayscl" in drawingml
        assert "grayscale" in drawingml.lower()

    def test_gamma_correction_mapping(self):
        """Test gamma correction mapping to PowerPoint color effects (Subtask 2.4.7)."""
        params = ComponentTransferParameters(
            input_source="SourceGraphic",
            red_function={'type': 'gamma', 'amplitude': 1.0, 'exponent': 2.2, 'offset': 0.0},
            green_function={'type': 'gamma', 'amplitude': 1.0, 'exponent': 2.2, 'offset': 0.0},
            blue_function={'type': 'gamma', 'amplitude': 1.0, 'exponent': 2.2, 'offset': 0.0},
            alpha_function={'type': 'identity'}
        )

        drawingml = self.filter._generate_component_transfer_drawingml(params, self.mock_context)

        # Should contain gamma correction effects
        assert "gamma" in drawingml.lower()
        assert "correction" in drawingml.lower()

    def test_combined_effect_mapping(self):
        """Test combined effect mapping with multiple transfer types."""
        params = ComponentTransferParameters(
            input_source="SourceGraphic",
            red_function={'type': 'discrete', 'table_values': [0.0, 1.0]},  # Binary
            green_function={'type': 'linear', 'slope': 0.5, 'intercept': 0.0},  # Grayscale
            blue_function={'type': 'gamma', 'amplitude': 1.0, 'exponent': 1.8, 'offset': 0.0},  # Gamma
            alpha_function={'type': 'identity'}  # Identity
        )

        drawingml = self.filter._generate_component_transfer_drawingml(params, self.mock_context)

        # Should indicate combined/complex processing
        assert "combined" in drawingml.lower() or "complex" in drawingml.lower()


class TestVectorFirstApplication:
    """Test vector-first component transfer application."""

    def setup_method(self):
        """Setup test fixtures."""
        self.filter = ComponentTransferFilter()

        self.mock_context = Mock(spec=FilterContext)
        self.mock_context.unit_converter = Mock()
        self.mock_context.unit_converter.to_emu.return_value = 25400
        self.mock_context.color_parser = Mock()
        self.mock_context.color_parser.parse.return_value = "#FFFFFF"

    def test_apply_simple_component_transfer(self):
        """Test applying simple feComponentTransfer element."""
        element = ET.Element("feComponentTransfer")
        red_func = ET.SubElement(element, "feFuncR")
        red_func.set("type", "discrete")
        red_func.set("tableValues", "0 1")

        result = self.filter.apply(element, self.mock_context)

        assert result.success is True
        assert result.drawingml is not None
        assert "component" in result.drawingml.lower()
        assert "vector-first" in result.drawingml.lower()

        # Should contain PowerPoint color effects
        assert "a:" in result.drawingml

        # Metadata should be present
        assert result.metadata['filter_type'] == 'component_transfer'
        assert result.metadata['strategy'] == 'vector_first'

    def test_apply_binary_threshold_transfer(self):
        """Test applying binary threshold transfer."""
        element = ET.Element("feComponentTransfer")

        # All channels binary
        for channel in ['feFuncR', 'feFuncG', 'feFuncB']:
            func = ET.SubElement(element, channel)
            func.set("type", "discrete")
            func.set("tableValues", "0 1")

        result = self.filter.apply(element, self.mock_context)

        assert result.success is True
        assert "binary" in result.drawingml.lower() or "bilevel" in result.drawingml.lower()

    def test_apply_complex_transfer_still_vector(self):
        """Test complex component transfer still uses vector-first approach."""
        element = ET.Element("feComponentTransfer")

        # Complex multi-channel setup
        red_func = ET.SubElement(element, "feFuncR")
        red_func.set("type", "gamma")
        red_func.set("exponent", "2.2")

        green_func = ET.SubElement(element, "feFuncG")
        green_func.set("type", "table")
        green_func.set("tableValues", "0.0 0.25 0.5 0.75 1.0")

        result = self.filter.apply(element, self.mock_context)

        # Even complex transfers should use vector-first approach
        assert result.success is True
        assert result.metadata['strategy'] == 'vector_first'

    @patch('src.converters.filters.geometric.component_transfer.logger')
    def test_apply_with_exception(self, mock_logger):
        """Test handling of exceptions during apply."""
        # Mock the unit converter to raise an exception during processing
        self.mock_context.unit_converter.to_emu.side_effect = ValueError("Unit conversion failed")

        element = ET.Element("feComponentTransfer")
        red_func = ET.SubElement(element, "feFuncR")
        red_func.set("type", "discrete")
        red_func.set("tableValues", "0.0 1.0")  # Binary to trigger specific processing

        # Mock the _generate_component_transfer_drawingml to use unit converter
        with patch.object(self.filter, '_generate_component_transfer_drawingml') as mock_generate:
            mock_generate.side_effect = ValueError("DrawingML generation failed")

            result = self.filter.apply(element, self.mock_context)

            assert result.success is False
            assert "failed" in result.error_message.lower()
            assert result.metadata['filter_type'] == 'component_transfer'
            mock_logger.error.assert_called()


class TestVectorQualityMaintenance:
    """Test vector quality maintenance (Subtask 2.4.8)."""

    def setup_method(self):
        """Setup test fixtures."""
        self.filter = ComponentTransferFilter()

        self.mock_context = Mock(spec=FilterContext)
        self.mock_context.unit_converter = Mock()
        self.mock_context.unit_converter.to_emu.return_value = 25400
        self.mock_context.color_parser = Mock()
        self.mock_context.color_parser.parse.return_value = "#FFFFFF"

    def test_vector_quality_preservation(self):
        """Test that component transfer effects maintain vector quality."""
        params = ComponentTransferParameters(
            input_source="SourceGraphic",
            red_function={'type': 'discrete', 'table_values': [0.0, 1.0]},
            green_function={'type': 'discrete', 'table_values': [0.0, 1.0]},
            blue_function={'type': 'discrete', 'table_values': [0.0, 1.0]}
        )

        drawingml = self.filter._generate_component_transfer_drawingml(params, self.mock_context)

        # Should generate vector-based DrawingML (not raster fallback)
        assert "a:" in drawingml  # DrawingML namespace
        assert "vector" in drawingml.lower()

        # Should not contain any rasterization indicators
        assert "raster" not in drawingml.lower()
        assert "bitmap" not in drawingml.lower()

    def test_powerpoint_native_effects_usage(self):
        """Test usage of PowerPoint native color effects for best quality."""
        params = ComponentTransferParameters(
            input_source="SourceGraphic",
            red_function={'type': 'linear', 'slope': 0.299, 'intercept': 0.0},
            green_function={'type': 'linear', 'slope': 0.587, 'intercept': 0.0},
            blue_function={'type': 'linear', 'slope': 0.114, 'intercept': 0.0}
        )

        drawingml = self.filter._generate_component_transfer_drawingml(params, self.mock_context)

        # Should use PowerPoint native color effects
        powerpoint_effects = ["a:biLevel", "a:duotone", "a:grayscl"]
        has_native_effect = any(effect in drawingml for effect in powerpoint_effects)
        assert has_native_effect

    def test_quality_optimization_comments(self):
        """Test that DrawingML includes quality optimization comments."""
        params = ComponentTransferParameters(
            input_source="SourceGraphic",
            red_function={'type': 'discrete', 'table_values': [0.2, 0.8]}
        )

        drawingml = self.filter._generate_component_transfer_drawingml(params, self.mock_context)

        # Should include quality maintenance comments
        assert "vector" in drawingml.lower()
        assert "quality" in drawingml.lower() or "native" in drawingml.lower()


class TestErrorHandling:
    """Test error handling for component transfer operations."""

    def setup_method(self):
        """Setup test fixtures."""
        self.filter = ComponentTransferFilter()

        self.mock_context = Mock(spec=FilterContext)
        self.mock_context.unit_converter = Mock()
        self.mock_context.color_parser = Mock()

    @patch('src.converters.filters.geometric.component_transfer.logger')
    def test_parameter_parsing_error_handling(self, mock_logger):
        """Test error handling during parameter parsing."""
        # Create a malformed element that might cause parsing errors
        element = Mock()
        element.get.side_effect = Exception("XML parsing error")

        result = self.filter.apply(element, self.mock_context)

        assert result.success is False
        assert "failed" in result.error_message.lower()
        mock_logger.error.assert_called()

    def test_invalid_table_values_handling(self):
        """Test handling of invalid table values."""
        element = ET.Element("feComponentTransfer")
        red_func = ET.SubElement(element, "feFuncR")
        red_func.set("type", "discrete")
        red_func.set("tableValues", "invalid not_a_number")

        params = self.filter._parse_component_transfer_parameters(element)

        # Should handle invalid values gracefully
        assert params.red_function is not None
        # Invalid values should be filtered out or defaulted
        assert len(params.red_function.get('table_values', [])) == 0 or \
               all(isinstance(v, (int, float)) for v in params.red_function.get('table_values', []))

    def test_missing_function_elements_handling(self):
        """Test handling when no function elements are present."""
        element = ET.Element("feComponentTransfer")
        # No feFuncR, feFuncG, feFuncB, or feFuncA children

        params = self.filter._parse_component_transfer_parameters(element)

        # Should provide default identity functions
        assert params.red_function is None or params.red_function.get('type') == 'identity'
        assert params.green_function is None or params.green_function.get('type') == 'identity'
        assert params.blue_function is None or params.blue_function.get('type') == 'identity'
        assert params.alpha_function is None or params.alpha_function.get('type') == 'identity'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])