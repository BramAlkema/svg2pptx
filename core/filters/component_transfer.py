#!/usr/bin/env python3
"""
ComponentTransfer Filter Processor for SVG Filter Effects

Implements SVG feComponentTransfer filter with sophisticated vector-first strategy,
mapping transfer functions to PowerPoint native color effects when possible.
"""

from typing import Dict, List, Optional, Tuple, Union, Any
from enum import Enum
from lxml import etree as ET
import re

from .base import FilterProcessor, FilterContext, FilterResult, FilterStrategy
from ..policy.targets import PolicyDecision


class ComponentTransferException(Exception):
    """Exception raised during component transfer processing."""
    pass


class TransferFunctionType(Enum):
    """Types of transfer functions supported by SVG feComponentTransfer."""
    IDENTITY = "identity"
    TABLE = "table"
    DISCRETE = "discrete"
    LINEAR = "linear"
    GAMMA = "gamma"


class ComponentTransferParameters:
    """Parameters for component transfer processing."""

    def __init__(self,
                 red_function: Optional[Dict[str, Any]] = None,
                 green_function: Optional[Dict[str, Any]] = None,
                 blue_function: Optional[Dict[str, Any]] = None,
                 alpha_function: Optional[Dict[str, Any]] = None):
        self.red_function = red_function or {"type": TransferFunctionType.IDENTITY}
        self.green_function = green_function or {"type": TransferFunctionType.IDENTITY}
        self.blue_function = blue_function or {"type": TransferFunctionType.IDENTITY}
        self.alpha_function = alpha_function or {"type": TransferFunctionType.IDENTITY}

    def get_all_functions(self) -> Dict[str, Dict[str, Any]]:
        """Get all transfer functions as a dictionary."""
        return {
            "red": self.red_function,
            "green": self.green_function,
            "blue": self.blue_function,
            "alpha": self.alpha_function
        }

    def has_heterogeneous_functions(self) -> bool:
        """Check if different channels use different function types."""
        functions = self.get_all_functions()
        function_types = set(func["type"] for func in functions.values())
        return len(function_types) > 1

    def get_complexity_score(self) -> float:
        """Calculate complexity score for strategy selection."""
        complexity = 0.5  # Base complexity

        for func in self.get_all_functions().values():
            func_type = func["type"]

            if func_type == TransferFunctionType.IDENTITY:
                complexity += 0.1
            elif func_type == TransferFunctionType.DISCRETE:
                table_values = func.get("table_values", [])
                if len(table_values) == 2:
                    complexity += 0.5  # Binary threshold - simple
                else:
                    complexity += len(table_values) * 0.3
            elif func_type == TransferFunctionType.LINEAR:
                complexity += 0.4
            elif func_type == TransferFunctionType.GAMMA:
                complexity += 0.6
            elif func_type == TransferFunctionType.TABLE:
                table_values = func.get("table_values", [])
                complexity += len(table_values) * 0.2

        # Add complexity for heterogeneous functions
        if self.has_heterogeneous_functions():
            complexity += 1.0

        return complexity


class ComponentTransferProcessor(FilterProcessor):
    """Processor for SVG feComponentTransfer filter effects."""

    def __init__(self, policy=None):
        super().__init__(filter_type='feComponentTransfer', policy=policy)

    def can_apply(self, element: ET.Element, context: FilterContext) -> bool:
        """Check if this processor can handle the given element."""
        if element is None or element.tag != 'feComponentTransfer':
            return False
        return self._validate_parameters(element, context)

    def apply(self, element: ET.Element, context: FilterContext) -> FilterResult:
        """Apply component transfer processing to the element."""
        try:
            # Validate parameters first
            if not self._validate_parameters(element, context):
                raise ComponentTransferException("Invalid component transfer parameters")

            # Parse transfer function parameters
            params = self._parse_component_transfer_parameters(element)

            # Get strategy from policy
            strategy = self._get_strategy(params, context)

            # Apply based on strategy
            if strategy == FilterStrategy.NATIVE:
                return self._apply_native_strategy(params, context)
            elif strategy == FilterStrategy.APPROXIMATION:
                return self._apply_approximation_strategy(params, context)
            else:  # EMF_RASTERIZE
                return self._apply_emf_strategy(params, context)

        except Exception as e:
            return FilterResult(
                success=False,
                strategy=FilterStrategy.EMF_RASTERIZE,
                drawingml="",
                error_message=f"Component transfer processing failed: {str(e)}"
            )

    def _validate_parameters(self, element: ET.Element, context: FilterContext) -> bool:
        """Validate component transfer parameters."""
        if element is None or context is None:
            return False
        try:
            self._parse_component_transfer_parameters(element)
            return True
        except (ComponentTransferException, ValueError, TypeError):
            return False

    def _parse_component_transfer_parameters(self, element: ET.Element) -> ComponentTransferParameters:
        """Parse component transfer parameters from SVG element."""
        functions = {}

        # Parse each channel function from child elements
        for child in element:
            channel = None
            if child.tag == 'feFuncR':
                channel = 'red'
            elif child.tag == 'feFuncG':
                channel = 'green'
            elif child.tag == 'feFuncB':
                channel = 'blue'
            elif child.tag == 'feFuncA':
                channel = 'alpha'

            if channel:
                functions[f"{channel}_function"] = self._parse_transfer_function(child)

        return ComponentTransferParameters(**functions)

    def _parse_transfer_function(self, element: ET.Element) -> Dict[str, Any]:
        """Parse a single transfer function from feFuncX element."""
        func_type_str = element.get('type', 'identity').lower()

        try:
            func_type = TransferFunctionType(func_type_str)
        except ValueError:
            func_type = TransferFunctionType.IDENTITY

        function = {"type": func_type}

        if func_type == TransferFunctionType.TABLE:
            table_values = self._parse_number_list(element.get('tableValues', ''))
            function["table_values"] = table_values

        elif func_type == TransferFunctionType.DISCRETE:
            table_values = self._parse_number_list(element.get('tableValues', ''))
            function["table_values"] = table_values

        elif func_type == TransferFunctionType.LINEAR:
            function["slope"] = float(element.get('slope', '1'))
            function["intercept"] = float(element.get('intercept', '0'))

        elif func_type == TransferFunctionType.GAMMA:
            function["amplitude"] = float(element.get('amplitude', '1'))
            function["exponent"] = float(element.get('exponent', '1'))
            function["offset"] = float(element.get('offset', '0'))

        return function

    def _parse_number_list(self, value_str: str) -> List[float]:
        """Parse a space or comma separated list of numbers."""
        if not value_str:
            return []

        # Split on whitespace and commas, filter empty strings
        parts = re.split(r'[,\s]+', value_str.strip())
        return [float(part) for part in parts if part]

    def _get_strategy(self, params: ComponentTransferParameters, context: FilterContext) -> FilterStrategy:
        """Determine the best strategy for component transfer processing."""
        if self.policy:
            decision = self.policy.decide_component_transfer_strategy(params, context)
            return decision.strategy

        # Default strategy logic
        complexity = params.get_complexity_score()

        # Check for patterns that map well to PowerPoint native effects
        if self._can_use_native_effects(params):
            return FilterStrategy.NATIVE
        elif complexity < 4.0:
            return FilterStrategy.APPROXIMATION
        else:
            return FilterStrategy.EMF_RASTERIZE

    def _can_use_native_effects(self, params: ComponentTransferParameters) -> bool:
        """Check if parameters can be mapped to PowerPoint native effects."""
        # Binary threshold pattern
        if self._is_binary_threshold(params):
            return True

        # Duotone pattern
        if self._is_duotone_pattern(params):
            return True

        # Grayscale conversion pattern
        if self._is_grayscale_conversion(params):
            return True

        # Gamma correction pattern
        if self._is_gamma_correction(params):
            return True

        return False

    def _is_binary_threshold(self, params: ComponentTransferParameters) -> bool:
        """Check if this represents a binary threshold operation."""
        functions = params.get_all_functions()

        # Check if all RGB channels use discrete functions with 2 values
        for channel in ['red', 'green', 'blue']:
            func = functions[channel]
            if func["type"] != TransferFunctionType.DISCRETE:
                return False

            table_values = func.get("table_values", [])
            if len(table_values) != 2:
                return False

            # Values should be close to 0.0 and 1.0 (in either order)
            values_set = set(table_values)
            if not (values_set.issubset({0.0, 1.0}) or
                   all(abs(v - 0.0) < 0.1 or abs(v - 1.0) < 0.1 for v in table_values)):
                return False

        return True

    def _is_duotone_pattern(self, params: ComponentTransferParameters) -> bool:
        """Check if this represents a duotone effect."""
        functions = params.get_all_functions()

        # Check if all RGB channels use discrete functions with 2 distinct values
        for channel in ['red', 'green', 'blue']:
            func = functions[channel]
            if func["type"] != TransferFunctionType.DISCRETE:
                return False

            table_values = func.get("table_values", [])
            if len(table_values) != 2:
                return False

            # Values should be distinct and not binary (0/1)
            if abs(table_values[0] - table_values[1]) < 0.2:
                return False
            if all(v in [0.0, 1.0] for v in table_values):
                return False

        return True

    def _is_grayscale_conversion(self, params: ComponentTransferParameters) -> bool:
        """Check if this represents a grayscale conversion."""
        functions = params.get_all_functions()

        # Standard luminance weights: R=0.299, G=0.587, B=0.114
        expected_weights = {'red': 0.299, 'green': 0.587, 'blue': 0.114}

        for channel in ['red', 'green', 'blue']:
            func = functions[channel]
            if func["type"] != TransferFunctionType.LINEAR:
                return False

            slope = func.get("slope", 1.0)
            intercept = func.get("intercept", 0.0)

            # Check if matches standard luminance weights
            expected_slope = expected_weights[channel]
            if abs(slope - expected_slope) > 0.05 or abs(intercept) > 0.05:
                return False

        return True

    def _is_gamma_correction(self, params: ComponentTransferParameters) -> bool:
        """Check if this represents gamma correction."""
        functions = params.get_all_functions()

        # Check if all RGB channels use gamma functions with reasonable values
        for channel in ['red', 'green', 'blue']:
            func = functions[channel]
            if func["type"] != TransferFunctionType.GAMMA:
                return False

            amplitude = func.get("amplitude", 1.0)
            exponent = func.get("exponent", 1.0)
            offset = func.get("offset", 0.0)

            # Reasonable gamma values: amplitude=1, exponent 0.5-3.0, offset=0
            if (abs(amplitude - 1.0) > 0.1 or
                exponent < 0.5 or exponent > 3.0 or
                abs(offset) > 0.1):
                return False

        return True

    def _apply_native_strategy(self, params: ComponentTransferParameters, context: FilterContext) -> FilterResult:
        """Apply native PowerPoint effects for component transfer."""
        try:
            drawingml = ""

            if self._is_binary_threshold(params):
                drawingml = self._generate_binary_threshold_drawingml(params, context)
            elif self._is_duotone_pattern(params):
                drawingml = self._generate_duotone_drawingml(params, context)
            elif self._is_grayscale_conversion(params):
                drawingml = self._generate_grayscale_drawingml(params, context)
            elif self._is_gamma_correction(params):
                drawingml = self._generate_gamma_drawingml(params, context)
            else:
                # Fallback to approximation
                return self._apply_approximation_strategy(params, context)

            return FilterResult(
                success=True,
                strategy=FilterStrategy.NATIVE,
                drawingml=drawingml
            )

        except Exception as e:
            return FilterResult(
                success=False,
                strategy=FilterStrategy.NATIVE,
                drawingml="",
                error_message=f"Native component transfer failed: {str(e)}"
            )

    def _generate_binary_threshold_drawingml(self, params: ComponentTransferParameters, context: FilterContext) -> str:
        """Generate DrawingML for binary threshold effect."""
        # Calculate threshold from first channel (they should all be the same)
        functions = params.get_all_functions()
        red_func = functions['red']
        table_values = red_func.get("table_values", [0.0, 1.0])

        # Threshold is at 50% by default, but adjust based on pattern
        threshold = 50000  # 50% in PowerPoint units (0-100000)

        # If pattern is (1.0, 0.0), it's inverted
        if len(table_values) >= 2 and table_values[0] > table_values[1]:
            # Inverted threshold
            threshold = 50000

        return f"""<a:effectLst>
  <a:biLevel thresh="{threshold}"/>
</a:effectLst>"""

    def _generate_duotone_drawingml(self, params: ComponentTransferParameters, context: FilterContext) -> str:
        """Generate DrawingML for duotone effect."""
        functions = params.get_all_functions()

        # Extract colors from RGB channel table values
        red_values = functions['red'].get("table_values", [0.0, 1.0])
        green_values = functions['green'].get("table_values", [0.0, 1.0])
        blue_values = functions['blue'].get("table_values", [0.0, 1.0])

        # Create two colors from the table values
        color1_rgb = (
            int(red_values[0] * 255),
            int(green_values[0] * 255),
            int(blue_values[0] * 255)
        )
        color2_rgb = (
            int(red_values[1] * 255),
            int(green_values[1] * 255),
            int(blue_values[1] * 255)
        )

        color1_hex = f"{color1_rgb[0]:02X}{color1_rgb[1]:02X}{color1_rgb[2]:02X}"
        color2_hex = f"{color2_rgb[0]:02X}{color2_rgb[1]:02X}{color2_rgb[2]:02X}"

        return f"""<a:effectLst>
  <a:duotone>
    <a:srgbClr val="{color1_hex}"/>
    <a:srgbClr val="{color2_hex}"/>
  </a:duotone>
</a:effectLst>"""

    def _generate_grayscale_drawingml(self, params: ComponentTransferParameters, context: FilterContext) -> str:
        """Generate DrawingML for grayscale conversion."""
        return """<a:effectLst>
  <a:grayscl/>
</a:effectLst>"""

    def _generate_gamma_drawingml(self, params: ComponentTransferParameters, context: FilterContext) -> str:
        """Generate DrawingML for gamma correction."""
        functions = params.get_all_functions()
        red_func = functions['red']
        exponent = red_func.get("exponent", 1.0)

        # PowerPoint gamma: inv="false" for normal, inv="true" for inverted
        inverted = "false"
        if exponent < 1.0:
            inverted = "true"

        return f"""<a:effectLst>
  <a:gamma inv="{inverted}"/>
</a:effectLst>"""

    def _apply_approximation_strategy(self, params: ComponentTransferParameters, context: FilterContext) -> FilterResult:
        """Apply approximation strategy using PowerPoint color adjustments."""
        try:
            # For approximation, we use brightness/contrast adjustments
            # This is a simplified approach for complex transfer functions

            drawingml = """<a:effectLst>
  <a:lum bright="10000" contrast="0"/>
</a:effectLst>"""

            return FilterResult(
                success=True,
                strategy=FilterStrategy.APPROXIMATION,
                drawingml=drawingml
            )

        except Exception as e:
            return FilterResult(
                success=False,
                strategy=FilterStrategy.APPROXIMATION,
                drawingml="",
                error_message=f"Approximation component transfer failed: {str(e)}"
            )

    def _apply_emf_strategy(self, params: ComponentTransferParameters, context: FilterContext) -> FilterResult:
        """Apply EMF rasterization strategy for complex component transfer."""
        try:
            # EMF rasterization placeholder
            # In a full implementation, this would create an EMF blob
            # with proper component transfer rendering

            return FilterResult(
                success=True,
                strategy=FilterStrategy.EMF_RASTERIZE,
                drawingml="<!-- EMF rasterization for complex component transfer -->"
            )

        except Exception as e:
            return FilterResult(
                success=False,
                strategy=FilterStrategy.EMF_RASTERIZE,
                drawingml="",
                error_message=f"EMF component transfer failed: {str(e)}"
            )


def create_component_transfer_processor(policy=None) -> ComponentTransferProcessor:
    """Factory function to create a ComponentTransferProcessor instance."""
    return ComponentTransferProcessor(policy=policy)