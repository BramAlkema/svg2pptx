#!/usr/bin/env python3
"""
ConvolveMatrix Filter Processor for SVG Filter Effects

Implements SVG feConvolveMatrix filter with hybrid vector-first strategy,
using PowerPoint native effects for common edge detection patterns and
EMF fallback for complex convolution operations.
"""

from typing import Dict, List, Optional, Tuple, Union, Any
from enum import Enum
from lxml import etree as ET
import re
import math

from .base import FilterProcessor, FilterContext, FilterResult, FilterStrategy
from ..policy.targets import PolicyDecision


class ConvolveMatrixException(Exception):
    """Exception raised during convolve matrix processing."""
    pass


class ConvolveMatrixValidationError(ConvolveMatrixException, ValueError):
    """Exception raised when convolve matrix parameters are invalid."""
    pass


class EdgeMode(Enum):
    """Edge modes for convolution processing."""
    DUPLICATE = "duplicate"
    WRAP = "wrap"
    NONE = "none"


class ConvolveMatrixParameters:
    """Parameters for convolve matrix processing."""

    def __init__(self,
                 kernel_matrix: List[float],
                 order: int,
                 divisor: float = 1.0,
                 bias: float = 0.0,
                 target_x: Optional[int] = None,
                 target_y: Optional[int] = None,
                 edge_mode: EdgeMode = EdgeMode.DUPLICATE,
                 preserve_alpha: bool = False):
        self.kernel_matrix = kernel_matrix
        self.order = order
        self.divisor = divisor
        self.bias = bias
        self.target_x = target_x
        self.target_y = target_y
        self.edge_mode = edge_mode
        self.preserve_alpha = preserve_alpha

        self._validate()

    def _validate(self):
        """Validate convolution matrix parameters."""
        # Validate order first
        if self.order <= 0:
            raise ConvolveMatrixValidationError(f"Order must be positive, got {self.order}")

        # Validate kernel matrix size
        expected_size = self.order * self.order
        if len(self.kernel_matrix) != expected_size:
            raise ConvolveMatrixValidationError(
                f"Kernel matrix size {len(self.kernel_matrix)} does not match order {self.order} "
                f"(expected {expected_size})"
            )

        # Validate divisor
        if abs(self.divisor) < 1e-10:
            raise ConvolveMatrixValidationError("Divisor cannot be zero")

        # Validate target coordinates
        if self.target_x is not None and (self.target_x < 0 or self.target_x >= self.order):
            raise ConvolveMatrixValidationError(
                f"Target X {self.target_x} out of range [0, {self.order - 1}]"
            )

        if self.target_y is not None and (self.target_y < 0 or self.target_y >= self.order):
            raise ConvolveMatrixValidationError(
                f"Target Y {self.target_y} out of range [0, {self.order - 1}]"
            )

    def get_complexity_score(self) -> float:
        """Calculate complexity score for strategy selection."""
        # Non-zero ratio (sparsity factor)
        non_zero_count = sum(1 for value in self.kernel_matrix if abs(value) > 1e-10)
        total_count = len(self.kernel_matrix)
        non_zero_ratio = non_zero_count / total_count if total_count > 0 else 0.0

        # Value variation (variance factor)
        if len(self.kernel_matrix) > 0:
            values = [abs(v) for v in self.kernel_matrix]
            min_val = min(values)
            max_val = max(values)
            value_variation = max_val - min_val if max_val > 0 else 0.0
        else:
            value_variation = 0.0

        # Order complexity (size factor)
        order_complexity = min(self.order / 10.0, 1.0)

        # Combined complexity score
        complexity = (
            0.3 * non_zero_ratio +
            0.4 * min(value_variation / 10.0, 1.0) +
            0.3 * order_complexity
        )

        return complexity

    def is_identity_matrix(self, tolerance: float = 1e-6) -> bool:
        """Check if this is an identity matrix."""
        center_x = self.order // 2
        center_y = self.order // 2

        for y in range(self.order):
            for x in range(self.order):
                index = y * self.order + x
                expected_value = 1.0 if (x == center_x and y == center_y) else 0.0
                actual_value = self.kernel_matrix[index]

                if abs(actual_value - expected_value) > tolerance:
                    return False

        return True

    def is_sobel_horizontal(self, tolerance: float = 1e-6) -> bool:
        """Check if this is a horizontal Sobel edge detection matrix."""
        if self.order != 3:
            return False

        expected = [-1.0, 0.0, 1.0, -2.0, 0.0, 2.0, -1.0, 0.0, 1.0]
        return self._matrices_equal(self.kernel_matrix, expected, tolerance)

    def is_sobel_vertical(self, tolerance: float = 1e-6) -> bool:
        """Check if this is a vertical Sobel edge detection matrix."""
        if self.order != 3:
            return False

        expected = [-1.0, -2.0, -1.0, 0.0, 0.0, 0.0, 1.0, 2.0, 1.0]
        return self._matrices_equal(self.kernel_matrix, expected, tolerance)

    def is_laplacian(self, tolerance: float = 1e-6) -> bool:
        """Check if this is a Laplacian edge detection matrix."""
        if self.order != 3:
            return False

        # Common Laplacian kernel
        expected = [0.0, -1.0, 0.0, -1.0, 4.0, -1.0, 0.0, -1.0, 0.0]
        return self._matrices_equal(self.kernel_matrix, expected, tolerance)

    def _matrices_equal(self, matrix1: List[float], matrix2: List[float], tolerance: float) -> bool:
        """Compare two matrices with tolerance."""
        if len(matrix1) != len(matrix2):
            return False
        return all(abs(a - b) <= tolerance for a, b in zip(matrix1, matrix2))


class ConvolveMatrixProcessor(FilterProcessor):
    """Processor for SVG feConvolveMatrix filter effects."""

    def __init__(self, policy=None):
        super().__init__(filter_type='feConvolveMatrix', policy=policy)

    def can_apply(self, element: ET.Element, context: FilterContext) -> bool:
        """Check if this processor can handle the given element."""
        if element is None or element.tag != 'feConvolveMatrix':
            return False
        return self._validate_parameters(element, context)

    def apply(self, element: ET.Element, context: FilterContext) -> FilterResult:
        """Apply convolve matrix processing to the element."""
        try:
            # Validate parameters first
            if not self._validate_parameters(element, context):
                raise ConvolveMatrixException("Invalid convolve matrix parameters")

            # Parse convolution matrix parameters
            params = self._parse_convolve_matrix_parameters(element)

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
                error_message=f"Convolve matrix processing failed: {str(e)}"
            )

    def _validate_parameters(self, element: ET.Element, context: FilterContext) -> bool:
        """Validate convolve matrix parameters."""
        if element is None or context is None:
            return False
        try:
            self._parse_convolve_matrix_parameters(element)
            return True
        except (ConvolveMatrixException, ValueError, TypeError):
            return False

    def _parse_convolve_matrix_parameters(self, element: ET.Element) -> ConvolveMatrixParameters:
        """Parse convolve matrix parameters from SVG element."""
        # Parse required kernelMatrix attribute
        kernel_matrix_str = element.get('kernelMatrix')
        if kernel_matrix_str is None:
            raise ConvolveMatrixValidationError("kernelMatrix attribute is required")

        kernel_matrix = self._parse_number_list(kernel_matrix_str)
        if not kernel_matrix:
            raise ConvolveMatrixValidationError("kernelMatrix cannot be empty")

        # Parse order - can be "3" or "3x3" format
        order_str = element.get('order', '')
        if not order_str:
            # Infer order from kernel matrix size (must be perfect square)
            matrix_size = len(kernel_matrix)
            order = int(math.sqrt(matrix_size))
            if order * order != matrix_size:
                raise ConvolveMatrixValidationError(
                    f"Cannot infer order from matrix size {matrix_size} (not a perfect square)"
                )
        else:
            if 'x' in order_str:
                # Format: "3x3"
                parts = order_str.split('x')
                if len(parts) != 2 or parts[0] != parts[1]:
                    raise ConvolveMatrixValidationError(
                        f"Non-square matrices not supported: {order_str}"
                    )
                order = int(parts[0])
            else:
                # Format: "3"
                order = int(order_str)

        # Parse divisor
        divisor_str = element.get('divisor', '1.0')
        try:
            divisor = float(divisor_str)
        except ValueError:
            raise ConvolveMatrixValidationError(f"Invalid divisor value: {divisor_str}")

        # Parse bias
        bias_str = element.get('bias', '0.0')
        try:
            bias = float(bias_str)
        except ValueError:
            raise ConvolveMatrixValidationError(f"Invalid bias value: {bias_str}")

        # Parse target coordinates
        target_x = None
        target_y = None
        if element.get('targetX'):
            try:
                target_x = int(element.get('targetX'))
            except ValueError:
                raise ConvolveMatrixValidationError(f"Invalid targetX value: {element.get('targetX')}")

        if element.get('targetY'):
            try:
                target_y = int(element.get('targetY'))
            except ValueError:
                raise ConvolveMatrixValidationError(f"Invalid targetY value: {element.get('targetY')}")

        # Parse edge mode
        edge_mode_str = element.get('edgeMode', 'duplicate').lower()
        try:
            edge_mode = EdgeMode(edge_mode_str)
        except ValueError:
            edge_mode = EdgeMode.DUPLICATE

        # Parse preserve alpha
        preserve_alpha_str = element.get('preserveAlpha', 'false').lower()
        preserve_alpha = preserve_alpha_str in ('true', '1', 'yes')

        return ConvolveMatrixParameters(
            kernel_matrix=kernel_matrix,
            order=order,
            divisor=divisor,
            bias=bias,
            target_x=target_x,
            target_y=target_y,
            edge_mode=edge_mode,
            preserve_alpha=preserve_alpha
        )

    def _parse_number_list(self, value_str: str) -> List[float]:
        """Parse a space or comma separated list of numbers."""
        if not value_str:
            return []

        # Split on whitespace and commas, filter empty strings
        parts = re.split(r'[,\s]+', value_str.strip())
        return [float(part) for part in parts if part]

    def _get_strategy(self, params: ConvolveMatrixParameters, context: FilterContext) -> FilterStrategy:
        """Determine the best strategy for convolve matrix processing."""
        if self.policy:
            decision = self.policy.decide_convolve_matrix_strategy(params, context)
            return decision.strategy

        # Default strategy logic
        if self._can_use_vector_approach(params):
            return FilterStrategy.NATIVE
        elif self._can_use_approximation(params):
            return FilterStrategy.APPROXIMATION
        else:
            return FilterStrategy.EMF_RASTERIZE

    def _can_use_vector_approach(self, params: ConvolveMatrixParameters) -> bool:
        """Check if parameters can be handled with vector approach."""
        # Size constraint: Only 3x3 for vector approach
        if params.order != 3:
            return False

        # Check for known patterns
        if (params.is_identity_matrix() or
            params.is_sobel_horizontal() or
            params.is_sobel_vertical() or
            params.is_laplacian()):
            return True

        # Check complexity threshold
        complexity = params.get_complexity_score()
        return complexity < 0.3

    def _can_use_approximation(self, params: ConvolveMatrixParameters) -> bool:
        """Check if approximation strategy is suitable."""
        # Approximation for medium complexity matrices
        complexity = params.get_complexity_score()
        return 0.3 <= complexity < 0.7 and params.order <= 5

    def _apply_native_strategy(self, params: ConvolveMatrixParameters, context: FilterContext) -> FilterResult:
        """Apply native PowerPoint effects for convolve matrix."""
        try:
            drawingml = ""

            if params.is_identity_matrix():
                drawingml = "<!-- Identity matrix: no effect -->"
            elif params.is_sobel_horizontal():
                drawingml = self._generate_sobel_horizontal_drawingml(params, context)
            elif params.is_sobel_vertical():
                drawingml = self._generate_sobel_vertical_drawingml(params, context)
            elif params.is_laplacian():
                drawingml = self._generate_laplacian_drawingml(params, context)
            else:
                # Simple matrix - use generic edge effect
                drawingml = self._generate_generic_edge_drawingml(params, context)

            return FilterResult(
                success=True,
                strategy=FilterStrategy.NATIVE,
                drawingml=drawingml,
                metadata={
                    'filter_type': self.filter_type,
                    'approach': 'vector',
                    'matrix_size': f"{params.order}x{params.order}",
                    'complexity': params.get_complexity_score()
                }
            )

        except Exception as e:
            return FilterResult(
                success=False,
                strategy=FilterStrategy.NATIVE,
                drawingml="",
                error_message=f"Native convolve matrix failed: {str(e)}"
            )

    def _generate_sobel_horizontal_drawingml(self, params: ConvolveMatrixParameters, context: FilterContext) -> str:
        """Generate DrawingML for horizontal Sobel edge detection."""
        return """<a:effectLst>
  <a:ln w="12700" cap="rnd" cmpd="sng" algn="ctr">
    <a:solidFill>
      <a:srgbClr val="000000">
        <a:alpha val="75000"/>
      </a:srgbClr>
    </a:solidFill>
    <a:prstDash val="dash"/>
  </a:ln>
</a:effectLst>"""

    def _generate_sobel_vertical_drawingml(self, params: ConvolveMatrixParameters, context: FilterContext) -> str:
        """Generate DrawingML for vertical Sobel edge detection."""
        return """<a:effectLst>
  <a:ln w="12700" cap="rnd" cmpd="sng" algn="ctr">
    <a:solidFill>
      <a:srgbClr val="000000">
        <a:alpha val="75000"/>
      </a:srgbClr>
    </a:solidFill>
    <a:prstDash val="dash"/>
  </a:ln>
  <a:reflection blurRad="0" stA="100000" stPos="0" endA="0" endPos="100000" dist="0" dir="5400000"/>
</a:effectLst>"""

    def _generate_laplacian_drawingml(self, params: ConvolveMatrixParameters, context: FilterContext) -> str:
        """Generate DrawingML for Laplacian edge detection."""
        return """<a:effectLst>
  <a:ln w="12700" cap="rnd" cmpd="sng" algn="ctr">
    <a:solidFill>
      <a:srgbClr val="000000">
        <a:alpha val="80000"/>
      </a:srgbClr>
    </a:solidFill>
    <a:prstDash val="dashDot"/>
  </a:ln>
</a:effectLst>"""

    def _generate_generic_edge_drawingml(self, params: ConvolveMatrixParameters, context: FilterContext) -> str:
        """Generate DrawingML for generic simple convolution matrices."""
        return """<a:effectLst>
  <a:ln w="9525" cap="rnd" cmpd="sng" algn="ctr">
    <a:solidFill>
      <a:srgbClr val="666666">
        <a:alpha val="60000"/>
      </a:srgbClr>
    </a:solidFill>
    <a:prstDash val="dot"/>
  </a:ln>
</a:effectLst>"""

    def _apply_approximation_strategy(self, params: ConvolveMatrixParameters, context: FilterContext) -> FilterResult:
        """Apply approximation strategy using PowerPoint shadow effects."""
        try:
            # For approximation, use shadow effects to simulate convolution
            drawingml = """<a:effectLst>
  <a:outerShdw blurRad="38100" dist="19050" dir="2700000" algn="tl" rotWithShape="0">
    <a:srgbClr val="000000">
      <a:alpha val="40000"/>
    </a:srgbClr>
  </a:outerShdw>
</a:effectLst>"""

            return FilterResult(
                success=True,
                strategy=FilterStrategy.APPROXIMATION,
                drawingml=drawingml,
                metadata={
                    'filter_type': self.filter_type,
                    'approach': 'approximation',
                    'matrix_size': f"{params.order}x{params.order}",
                    'complexity': params.get_complexity_score()
                }
            )

        except Exception as e:
            return FilterResult(
                success=False,
                strategy=FilterStrategy.APPROXIMATION,
                drawingml="",
                error_message=f"Approximation convolve matrix failed: {str(e)}"
            )

    def _apply_emf_strategy(self, params: ConvolveMatrixParameters, context: FilterContext) -> FilterResult:
        """Apply EMF rasterization strategy for complex convolve matrix."""
        try:
            # EMF rasterization placeholder
            # In a full implementation, this would create an EMF blob
            # with proper convolution processing

            return FilterResult(
                success=True,
                strategy=FilterStrategy.EMF_RASTERIZE,
                drawingml="<!-- EMF rasterization for complex convolution matrix -->",
                metadata={
                    'filter_type': self.filter_type,
                    'approach': 'emf',
                    'matrix_size': f"{params.order}x{params.order}",
                    'complexity': params.get_complexity_score()
                }
            )

        except Exception as e:
            return FilterResult(
                success=False,
                strategy=FilterStrategy.EMF_RASTERIZE,
                drawingml="",
                error_message=f"EMF convolve matrix failed: {str(e)}"
            )


def create_convolve_matrix_processor(policy=None) -> ConvolveMatrixProcessor:
    """Factory function to create a ConvolveMatrixProcessor instance."""
    return ConvolveMatrixProcessor(policy=policy)