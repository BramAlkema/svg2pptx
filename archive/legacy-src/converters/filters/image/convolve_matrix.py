"""
feConvolveMatrix filter implementation with hybrid vector + EMF approach.

Supports convolution matrix operations for edge detection, blur, and sharpening
with optimized vector-first approach for simple matrices and EMF fallback
for complex arbitrary matrices.
"""

import math
from lxml import etree as ET
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Dict, Any, Union
from abc import ABC, abstractmethod

from src.converters.filters.core.base import Filter, FilterResult, FilterContext


class EdgeMode(Enum):
    """Edge mode enumeration for convolution matrix processing."""
    DUPLICATE = "duplicate"
    WRAP = "wrap"
    NONE = "none"


@dataclass
class ConvolveMatrixParameters:
    """Parameters for feConvolveMatrix filter operation."""
    matrix: List[float]
    order: str
    divisor: float = 1.0
    bias: float = 0.0
    edge_mode: EdgeMode = EdgeMode.DUPLICATE
    preserve_alpha: bool = False
    target_x: Optional[int] = None
    target_y: Optional[int] = None


class ConvolveMatrixException(Exception):
    """Base exception for convolution matrix operations."""
    pass


class ConvolveMatrixValidationError(ConvolveMatrixException, ValueError):
    """Exception for invalid convolution matrix parameters."""
    pass


class EdgeDetectionPatterns:
    """Known edge detection patterns for vector optimization."""

    # Sobel horizontal edge detection
    SOBEL_HORIZONTAL = [-1.0, 0.0, 1.0, -2.0, 0.0, 2.0, -1.0, 0.0, 1.0]

    # Sobel vertical edge detection
    SOBEL_VERTICAL = [-1.0, -2.0, -1.0, 0.0, 0.0, 0.0, 1.0, 2.0, 1.0]

    # Laplacian edge detection
    LAPLACIAN = [0.0, -1.0, 0.0, -1.0, 4.0, -1.0, 0.0, -1.0, 0.0]

    # Identity matrix (pass-through)
    IDENTITY = [0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0]


class EMFConvolutionProcessor:
    """EMF-based convolution processor for complex matrices."""

    def process_convolution(self, params: ConvolveMatrixParameters, context: FilterContext) -> Dict[str, Any]:
        """
        Process convolution using EMF rasterization.

        Args:
            params: Convolution matrix parameters
            context: Filter context with element and viewport info

        Returns:
            Dictionary with EMF blob data and dimensions
        """
        # This is a placeholder implementation
        # In the full implementation, this would:
        # 1. Render the source element to a bitmap
        # 2. Apply the convolution matrix to the bitmap
        # 3. Generate an EMF blob with the result
        # 4. Return blob data and dimensions for OOXML integration

        return {
            'emf_blob': b'mock_emf_data',
            'width': context.viewport.get('width', 100),
            'height': context.viewport.get('height', 100)
        }


class ConvolveMatrixFilter(Filter):
    """
    feConvolveMatrix filter with hybrid vector + EMF approach.

    Implements convolution matrix operations using:
    - Vector-first approach for simple edge detection matrices (Sobel, Laplacian)
    - EMF fallback for complex arbitrary convolution matrices
    - Performance optimization based on matrix complexity analysis
    """

    def __init__(self):
        """Initialize the convolution matrix filter."""
        super().__init__("feConvolveMatrix")
        self._edge_patterns = EdgeDetectionPatterns()
        self._emf_processor = EMFConvolutionProcessor()

    def can_apply(self, element: ET.Element, context: FilterContext) -> bool:
        """
        Check if this filter can process the given element.

        Args:
            element: SVG filter element
            context: Filter processing context

        Returns:
            True if element is feConvolveMatrix with required attributes
        """
        if element.tag != "feConvolveMatrix":
            return False

        # Check for required kernelMatrix attribute
        kernel_matrix = element.get("kernelMatrix")
        if not kernel_matrix:
            return False

        return True

    def validate_parameters(self, element: ET.Element, context: FilterContext) -> bool:
        """
        Validate convolution matrix parameters.

        Args:
            element: SVG filter element
            context: Filter processing context

        Returns:
            True if parameters are valid
        """
        try:
            self._parse_parameters(element)
            return True
        except ConvolveMatrixValidationError:
            return False

    def apply(self, element: ET.Element, context: FilterContext) -> FilterResult:
        """
        Apply convolution matrix filter using hybrid approach.

        Args:
            element: SVG feConvolveMatrix element
            context: Filter processing context

        Returns:
            FilterResult with DrawingML or EMF content
        """
        try:
            # Parse and validate parameters
            params = self._parse_parameters(element)

            # Decide between vector and EMF approaches
            if self._can_use_vector_approach(params):
                drawingml = self._apply_vector_convolution(params, context)
                approach = "vector"
            else:
                drawingml = self._apply_emf_convolution(params, context)
                approach = "emf"

            return FilterResult(
                success=True,
                drawingml=drawingml,
                metadata={
                    'filter_type': self.filter_type,
                    'approach': approach,
                    'matrix_size': f"{params.order}x{params.order}",
                    'complexity': self._calculate_matrix_complexity(params)
                }
            )

        except ConvolveMatrixValidationError as e:
            return FilterResult(
                success=False,
                error_message=str(e),
                metadata={'filter_type': self.filter_type, 'error': str(e)}
            )
        except Exception as e:
            return FilterResult(
                success=False,
                error_message=f"Convolution matrix processing failed: {str(e)}",
                metadata={'filter_type': self.filter_type, 'error': str(e)}
            )

    def _parse_parameters(self, element: ET.Element) -> ConvolveMatrixParameters:
        """
        Parse feConvolveMatrix element attributes into parameters.

        Args:
            element: SVG feConvolveMatrix element

        Returns:
            ConvolveMatrixParameters with parsed values

        Raises:
            ConvolveMatrixValidationError: If parameters are invalid
        """
        # Parse required kernelMatrix attribute
        kernel_matrix_str = element.get("kernelMatrix")
        if not kernel_matrix_str:
            raise ConvolveMatrixValidationError("kernelMatrix is required")

        try:
            matrix = [float(val) for val in kernel_matrix_str.split()]
        except ValueError as e:
            raise ConvolveMatrixValidationError(f"Invalid kernelMatrix values: {e}")

        # Parse order attribute
        order_str = element.get("order", "3")
        try:
            if "x" in order_str:
                # Handle "3x3" format
                order_parts = order_str.split("x")
                if len(order_parts) != 2 or order_parts[0] != order_parts[1]:
                    raise ConvolveMatrixValidationError("Only square matrices are supported")
                order = int(order_parts[0])
            else:
                # Handle single number format
                order = int(order_str)
        except ValueError:
            raise ConvolveMatrixValidationError(f"Invalid order value: {order_str}")

        # Validate matrix size matches order
        expected_size = order * order
        if len(matrix) != expected_size:
            raise ConvolveMatrixValidationError(
                f"Matrix size mismatch: expected {expected_size} values for order {order}, got {len(matrix)}"
            )

        # Parse optional attributes
        divisor = float(element.get("divisor", "1.0"))
        if divisor == 0.0:
            raise ConvolveMatrixValidationError("divisor cannot be zero")

        bias = float(element.get("bias", "0.0"))

        # Parse edge mode
        edge_mode_str = element.get("edgeMode", "duplicate")
        try:
            edge_mode = EdgeMode(edge_mode_str)
        except ValueError:
            raise ConvolveMatrixValidationError(f"Invalid edgeMode: {edge_mode_str}")

        # Parse preserve alpha
        preserve_alpha = element.get("preserveAlpha", "false").lower() == "true"

        # Parse target coordinates
        target_x = None
        target_y = None
        if element.get("targetX"):
            target_x = int(element.get("targetX"))
        if element.get("targetY"):
            target_y = int(element.get("targetY"))

        return ConvolveMatrixParameters(
            matrix=matrix,
            order=order_str,
            divisor=divisor,
            bias=bias,
            edge_mode=edge_mode,
            preserve_alpha=preserve_alpha,
            target_x=target_x,
            target_y=target_y
        )

    def _can_use_vector_approach(self, params: ConvolveMatrixParameters) -> bool:
        """
        Determine if matrix can use vector-first approach.

        Args:
            params: Convolution matrix parameters

        Returns:
            True if vector approach is suitable
        """
        # Only support 3x3 matrices for vector approach
        if params.order != "3":
            return False

        # Check for known edge detection patterns
        matrix = params.matrix

        # Check for identity matrix
        if self._matrices_equal(matrix, self._edge_patterns.IDENTITY):
            return True

        # Check for Sobel horizontal
        if self._matrices_equal(matrix, self._edge_patterns.SOBEL_HORIZONTAL):
            return True

        # Check for Sobel vertical
        if self._matrices_equal(matrix, self._edge_patterns.SOBEL_VERTICAL):
            return True

        # Check for Laplacian
        if self._matrices_equal(matrix, self._edge_patterns.LAPLACIAN):
            return True

        # Check matrix complexity
        complexity = self._calculate_matrix_complexity(params)
        return complexity < 0.3  # Lower threshold for vector suitability

    def _matrices_equal(self, matrix1: List[float], matrix2: List[float], tolerance: float = 1e-6) -> bool:
        """
        Compare two matrices for equality within tolerance.

        Args:
            matrix1: First matrix
            matrix2: Second matrix
            tolerance: Floating point comparison tolerance

        Returns:
            True if matrices are equal within tolerance
        """
        if len(matrix1) != len(matrix2):
            return False

        return all(abs(a - b) <= tolerance for a, b in zip(matrix1, matrix2))

    def _calculate_matrix_complexity(self, params: ConvolveMatrixParameters) -> float:
        """
        Calculate complexity score for matrix to guide approach selection.

        Args:
            params: Convolution matrix parameters

        Returns:
            Complexity score (0.0 = simple, 1.0 = complex)
        """
        matrix = params.matrix

        # Factor 1: Number of non-zero elements
        non_zero_count = sum(1 for val in matrix if abs(val) > 1e-6)
        non_zero_ratio = non_zero_count / len(matrix)

        # Factor 2: Value range and variation
        if non_zero_count > 0:
            non_zero_values = [val for val in matrix if abs(val) > 1e-6]
            value_range = max(non_zero_values) - min(non_zero_values)
            mean_value = sum(non_zero_values) / len(non_zero_values)
            value_variation = sum(abs(val - mean_value) for val in non_zero_values) / len(non_zero_values)
        else:
            value_range = 0.0
            value_variation = 0.0

        # Factor 3: Matrix order (larger matrices are more complex)
        order = int(params.order) if isinstance(params.order, str) and params.order.isdigit() else 3
        order_complexity = min(order / 5.0, 1.0)  # Normalize to max 5x5

        # Combine factors (weighted)
        complexity = (
            0.3 * non_zero_ratio +
            0.4 * min(value_variation / 10.0, 1.0) +
            0.3 * order_complexity
        )

        return min(complexity, 1.0)

    def _apply_vector_convolution(self, params: ConvolveMatrixParameters, context: FilterContext) -> str:
        """
        Apply convolution using vector-first approach for simple matrices.

        Args:
            params: Convolution matrix parameters
            context: Filter processing context

        Returns:
            DrawingML string for vector-based convolution
        """
        matrix = params.matrix

        # Handle identity matrix (pass-through)
        if self._matrices_equal(matrix, self._edge_patterns.IDENTITY):
            return "<!-- Identity pass-through -->"

        # Handle Sobel horizontal edge detection
        if self._matrices_equal(matrix, self._edge_patterns.SOBEL_HORIZONTAL):
            return self._generate_sobel_horizontal_dml(context)

        # Handle Sobel vertical edge detection
        if self._matrices_equal(matrix, self._edge_patterns.SOBEL_VERTICAL):
            return self._generate_sobel_vertical_dml(context)

        # Handle Laplacian edge detection
        if self._matrices_equal(matrix, self._edge_patterns.LAPLACIAN):
            return self._generate_laplacian_dml(context)

        # For other simple matrices, generate basic vector outline
        return self._generate_generic_vector_outline(params, context)

    def _generate_sobel_horizontal_dml(self, context: FilterContext) -> str:
        """Generate DrawingML for Sobel horizontal edge detection."""
        return '''<a:ln w="12700" cap="rnd" cmpd="sng" algn="ctr">
    <a:solidFill>
        <a:schemeClr val="tx1">
            <a:alpha val="75000"/>
        </a:schemeClr>
    </a:solidFill>
    <a:prstDash val="dash"/>
    <a:round/>
</a:ln>'''

    def _generate_sobel_vertical_dml(self, context: FilterContext) -> str:
        """Generate DrawingML for Sobel vertical edge detection."""
        return '''<a:ln w="12700" cap="rnd" cmpd="sng" algn="ctr">
    <a:solidFill>
        <a:schemeClr val="tx1">
            <a:alpha val="75000"/>
        </a:schemeClr>
    </a:solidFill>
    <a:prstDash val="dash"/>
    <a:round/>
</a:ln>'''

    def _generate_laplacian_dml(self, context: FilterContext) -> str:
        """Generate DrawingML for Laplacian edge detection."""
        return '''<a:ln w="12700" cap="rnd" cmpd="sng" algn="ctr">
    <a:solidFill>
        <a:schemeClr val="tx1">
            <a:alpha val="75000"/>
        </a:schemeClr>
    </a:solidFill>
    <a:prstDash val="dashDot"/>
    <a:round/>
</a:ln>'''

    def _generate_generic_vector_outline(self, params: ConvolveMatrixParameters, context: FilterContext) -> str:
        """Generate DrawingML for generic simple matrix."""
        return '''<a:ln w="12700" cap="rnd" cmpd="sng" algn="ctr">
    <a:solidFill>
        <a:schemeClr val="tx1">
            <a:alpha val="50000"/>
        </a:schemeClr>
    </a:solidFill>
    <a:prstDash val="dot"/>
    <a:round/>
</a:ln>'''

    def _apply_emf_convolution(self, params: ConvolveMatrixParameters, context: FilterContext) -> str:
        """
        Apply convolution using EMF fallback for complex matrices.

        Args:
            params: Convolution matrix parameters
            context: Filter processing context

        Returns:
            DrawingML string with EMF blob reference
        """
        # Process convolution using EMF processor
        emf_result = self._emf_processor.process_convolution(params, context)

        # Generate DrawingML with EMF blob reference
        # This is a placeholder - in full implementation would:
        # 1. Add EMF blob to presentation media
        # 2. Generate proper r:embed reference
        # 3. Create blip element with correct dimensions

        width = emf_result['width']
        height = emf_result['height']

        return f'''<a:blip r:embed="rId_emf_convolve_matrix">
    <a:extLst>
        <a:ext uri="{{28A0092B-C50C-407E-A947-70E740481C1C}}">
            <a14:useLocalDpi val="0"/>
        </a:ext>
    </a:extLst>
</a:blip>
<a:srcRect/>
<a:stretch>
    <a:fillRect/>
</a:stretch>
<!-- EMF convolution result: {width}x{height} -->'''