"""
Blur filter implementations for SVG filter effects.

This module provides blur filter implementations including Gaussian blur
and motion blur effects, extracted from the monolithic filters.py and
refactored to follow the modular filter architecture.
"""

import re
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
import logging
from lxml import etree

from ..core.base import Filter, FilterContext, FilterResult, FilterException

logger = logging.getLogger(__name__)


class BlurFilterException(FilterException):
    """Exception raised when blur filter processing fails."""
    pass


@dataclass
class BlurParameters:
    """Parameters for blur filter operations."""
    std_deviation_x: float
    std_deviation_y: float
    edge_mode: str = "duplicate"  # duplicate, wrap, none
    input_source: str = "SourceGraphic"
    result_name: str = "blur"


class GaussianBlurFilter(Filter):
    """
    Gaussian blur filter implementation.

    This filter implements SVG feGaussianBlur elements, providing native
    PowerPoint blur effects when possible and appropriate fallbacks for
    complex scenarios.

    Supports:
    - Isotropic and anisotropic blur (different X/Y standard deviations)
    - All SVG edge modes (duplicate, wrap, none)
    - Native OOXML blur effect generation
    - Proper unit conversion and bounds calculation

    Example:
        >>> blur_filter = GaussianBlurFilter()
        >>> element = etree.fromstring('<feGaussianBlur stdDeviation="2.5"/>')
        >>> result = blur_filter.apply(element, context)
        >>> print(result.drawingml)  # '<a:blur rad="63500"/>'
    """

    def __init__(self):
        """Initialize the Gaussian blur filter."""
        super().__init__("gaussian_blur")

    def can_apply(self, element: etree.Element, context: FilterContext) -> bool:
        """
        Check if this filter can be applied to the given element.

        Args:
            element: SVG element to check
            context: Filter processing context

        Returns:
            True if this filter can process the element
        """
        if element is None:
            return False

        # Check for feGaussianBlur elements
        tag = element.tag
        return (
            tag.endswith('feGaussianBlur') or
            'gaussianblur' in tag.lower() or
            element.get('type') == 'feGaussianBlur'
        )

    def apply(self, element: etree.Element, context: FilterContext) -> FilterResult:
        """
        Apply Gaussian blur filter to the SVG element.

        Args:
            element: SVG feGaussianBlur element
            context: Filter processing context with unit converter, etc.

        Returns:
            FilterResult containing the blur effect DrawingML
        """
        try:
            # Parse blur parameters
            params = self._parse_blur_parameters(element)

            # Generate DrawingML based on blur complexity
            if self._is_simple_blur(params):
                drawingml = self._generate_native_blur_dml(params, context)
            else:
                drawingml = self._generate_complex_blur_dml(params, context)

            # Create metadata
            metadata = {
                'filter_type': self.filter_type,
                'std_deviation_x': params.std_deviation_x,
                'std_deviation_y': params.std_deviation_y,
                'edge_mode': params.edge_mode,
                'is_isotropic': params.std_deviation_x == params.std_deviation_y,
                'native_support': self._is_simple_blur(params)
            }

            return FilterResult(
                success=True,
                drawingml=drawingml,
                metadata=metadata
            )

        except Exception as e:
            self.logger.error(f"Gaussian blur filter failed: {e}")
            return FilterResult(
                success=False,
                error_message=f"Gaussian blur processing failed: {str(e)}",
                metadata={'filter_type': self.filter_type, 'error': str(e)}
            )

    def validate_parameters(self, element: etree.Element, context: FilterContext) -> bool:
        """
        Validate that the element has valid parameters for Gaussian blur.

        Args:
            element: SVG element to validate
            context: Filter processing context

        Returns:
            True if element parameters are valid
        """
        try:
            params = self._parse_blur_parameters(element)

            # Validate standard deviation values
            if params.std_deviation_x < 0 or params.std_deviation_y < 0:
                return False

            # Validate edge mode
            valid_edge_modes = ['duplicate', 'wrap', 'none']
            if params.edge_mode not in valid_edge_modes:
                return False

            return True

        except Exception:
            return False

    def _parse_blur_parameters(self, element: etree.Element) -> BlurParameters:
        """
        Parse blur parameters from SVG feGaussianBlur element.

        Args:
            element: SVG feGaussianBlur element

        Returns:
            BlurParameters with parsed values

        Raises:
            BlurFilterException: If parameters are invalid
        """
        # Parse stdDeviation attribute
        std_deviation = element.get('stdDeviation', '0')
        std_x, std_y = self._parse_std_deviation(std_deviation)

        # Parse edge mode
        edge_mode = element.get('edgeMode', 'duplicate').lower()
        if edge_mode not in ['duplicate', 'wrap', 'none']:
            edge_mode = 'duplicate'

        # Parse input and result
        input_source = element.get('in', 'SourceGraphic')
        result_name = element.get('result', 'blur')

        return BlurParameters(
            std_deviation_x=std_x,
            std_deviation_y=std_y,
            edge_mode=edge_mode,
            input_source=input_source,
            result_name=result_name
        )

    def _parse_std_deviation(self, std_deviation: str) -> Tuple[float, float]:
        """
        Parse stdDeviation attribute value.

        SVG allows either one value (isotropic) or two values (anisotropic).

        Args:
            std_deviation: String value from stdDeviation attribute

        Returns:
            Tuple of (std_x, std_y) values

        Raises:
            BlurFilterException: If value is invalid
        """
        if not std_deviation or not std_deviation.strip():
            return (0.0, 0.0)

        std_deviation = std_deviation.strip()

        try:
            # Check if it contains two values (anisotropic)
            if ' ' in std_deviation:
                parts = std_deviation.split()
                if len(parts) != 2:
                    raise ValueError(f"Invalid stdDeviation format: {std_deviation}")

                std_x = float(parts[0])
                std_y = float(parts[1])
            else:
                # Single value (isotropic)
                std_x = std_y = float(std_deviation)

            # Validate non-negative values
            if std_x < 0 or std_y < 0:
                raise ValueError(f"Standard deviation must be non-negative: {std_deviation}")

            return (std_x, std_y)

        except ValueError as e:
            raise BlurFilterException(f"Invalid stdDeviation value '{std_deviation}': {e}")

    def _is_simple_blur(self, params: BlurParameters) -> bool:
        """
        Determine if blur can use native PowerPoint effects.

        Args:
            params: Blur parameters

        Returns:
            True if can use native blur effect
        """
        # PowerPoint blur works best with isotropic blur
        if params.std_deviation_x != params.std_deviation_y:
            return False

        # PowerPoint blur works with moderate values
        max_std = max(params.std_deviation_x, params.std_deviation_y)
        if max_std > 25.0:  # Very large blur might need fallback
            return False

        # Edge modes other than duplicate might need special handling
        if params.edge_mode != 'duplicate':
            return False

        return True

    def _generate_native_blur_dml(self, params: BlurParameters, context: FilterContext) -> str:
        """
        Generate native PowerPoint blur effect DrawingML.

        Args:
            params: Blur parameters
            context: Filter processing context

        Returns:
            DrawingML XML string for native blur effect
        """
        # Use average of X and Y for isotropic-like effect
        std_dev = (params.std_deviation_x + params.std_deviation_y) / 2

        # Convert to EMUs (PowerPoint's internal units)
        # PowerPoint blur radius is roughly std_deviation * pixels_to_emu
        radius_emu = context.unit_converter.to_emu(f"{std_dev}px")

        # Clamp to reasonable range for PowerPoint
        radius_emu = max(0, min(radius_emu, 2540000))  # Max ~100px blur

        return f'<a:blur rad="{int(radius_emu)}"/>'

    def _generate_complex_blur_dml(self, params: BlurParameters, context: FilterContext) -> str:
        """
        Generate complex blur effect using DML approximations.

        For anisotropic blur or edge modes that don't map directly to
        PowerPoint blur, we use approximations or multiple effects.

        Args:
            params: Blur parameters
            context: Filter processing context

        Returns:
            DrawingML XML string for approximated blur effect
        """
        effects = []

        if params.std_deviation_x != params.std_deviation_y:
            # Anisotropic blur approximation
            # Use the larger value for main blur
            main_std = max(params.std_deviation_x, params.std_deviation_y)
            main_radius = context.unit_converter.to_emu(f"{main_std}px")
            main_radius = max(0, min(int(main_radius), 2540000))

            effects.append(f'<a:blur rad="{main_radius}"/>')

            # Add comment about anisotropic approximation
            effects.append(
                f'<!-- Anisotropic blur approximation: {params.std_deviation_x}x{params.std_deviation_y} -->'
            )
        else:
            # Isotropic blur with special edge mode
            radius_emu = context.unit_converter.to_emu(f"{params.std_deviation_x}px")
            radius_emu = max(0, min(int(radius_emu), 2540000))

            effects.append(f'<a:blur rad="{radius_emu}"/>')

            if params.edge_mode != 'duplicate':
                effects.append(f'<!-- Edge mode: {params.edge_mode} (approximated) -->')

        return ''.join(effects)

    def _convert_to_ooxml_radius(self, std_deviation: float, unit_converter) -> int:
        """
        Convert standard deviation to OOXML blur radius.

        Args:
            std_deviation: Blur standard deviation in SVG units
            unit_converter: Unit conversion utility

        Returns:
            Blur radius in EMUs
        """
        radius_emu = unit_converter.to_emu(f"{std_deviation}px")
        return max(0, min(int(radius_emu), 2540000))


class MotionBlurFilter(Filter):
    """
    Motion blur filter implementation.

    Motion blur is typically implemented using convolution matrices or
    transform-based effects. This filter provides approximations using
    PowerPoint's available effect primitives.

    Note: True motion blur requires complex convolution operations that
    are not directly supported in PowerPoint, so this implementation
    provides visual approximations.
    """

    def __init__(self):
        """Initialize the motion blur filter."""
        super().__init__("motion_blur")

    def can_apply(self, element: etree.Element, context: FilterContext) -> bool:
        """
        Check if this filter can be applied to the given element.

        Motion blur is typically implemented through:
        - Custom feConvolveMatrix with motion kernel
        - Transform animations with blur
        - Special motion-blur attributes

        Args:
            element: SVG element to check
            context: Filter processing context

        Returns:
            True if this filter can process the element
        """
        if element is None:
            return False

        tag = element.tag

        # Check for motion blur indicators
        if ('motion' in tag.lower() and 'blur' in tag.lower()):
            return True

        # Check for feConvolveMatrix with motion-like kernels
        if tag.endswith('feConvolveMatrix'):
            # Look for motion blur patterns in kernel matrix
            kernel = element.get('kernelMatrix', '')
            if self._is_motion_kernel(kernel):
                return True

        # Check for custom motion blur attributes
        if (element.get('data-motion-blur') or
            element.get('motion-angle') or
            element.get('motion-distance')):
            return True

        return False

    def apply(self, element: etree.Element, context: FilterContext) -> FilterResult:
        """
        Apply motion blur effect to the SVG element.

        Args:
            element: SVG element with motion blur parameters
            context: Filter processing context

        Returns:
            FilterResult containing the motion blur approximation
        """
        try:
            # Parse motion parameters
            angle, distance = self._parse_motion_parameters(element)

            # Generate approximation DrawingML
            drawingml = self._generate_motion_blur_approximation(angle, distance, context)

            metadata = {
                'filter_type': self.filter_type,
                'motion_angle': angle,
                'motion_distance': distance,
                'approximation': True  # This is an approximation
            }

            return FilterResult(
                success=True,
                drawingml=drawingml,
                metadata=metadata
            )

        except Exception as e:
            self.logger.error(f"Motion blur filter failed: {e}")
            return FilterResult(
                success=False,
                error_message=f"Motion blur processing failed: {str(e)}",
                metadata={'filter_type': self.filter_type, 'error': str(e)}
            )

    def validate_parameters(self, element: etree.Element, context: FilterContext) -> bool:
        """
        Validate motion blur parameters.

        Args:
            element: SVG element to validate
            context: Filter processing context

        Returns:
            True if element parameters are valid
        """
        try:
            angle, distance = self._parse_motion_parameters(element)

            # Validate angle (0-360 degrees)
            if not (0 <= angle <= 360):
                return False

            # Validate distance (non-negative)
            if distance < 0:
                return False

            return True

        except Exception:
            return False

    def _parse_motion_parameters(self, element: etree.Element) -> Tuple[float, float]:
        """
        Parse motion blur parameters from element.

        Args:
            element: SVG element

        Returns:
            Tuple of (angle_degrees, distance_pixels)
        """
        # Try custom attributes first
        angle = float(element.get('data-motion-angle', element.get('motion-angle', '0')))
        distance = float(element.get('data-motion-distance', element.get('motion-distance', '5')))

        # If not found, try to extract from convolution matrix
        if angle == 0 and distance == 5:
            kernel_matrix = element.get('kernelMatrix', '')
            if kernel_matrix:
                angle, distance = self._extract_motion_from_kernel(kernel_matrix)

        return (angle, distance)

    def _is_motion_kernel(self, kernel: str) -> bool:
        """
        Check if convolution kernel represents motion blur.

        Args:
            kernel: Kernel matrix string

        Returns:
            True if kernel looks like motion blur
        """
        if not kernel:
            return False

        # Simple heuristic: motion blur kernels often have
        # patterns like line segments or directional weights
        values = kernel.split()
        if len(values) < 9:  # At least 3x3
            return False

        # Look for linear patterns that might indicate motion
        non_zero_count = sum(1 for v in values if float(v) != 0)
        return non_zero_count > 2 and non_zero_count < len(values) * 0.5

    def _extract_motion_from_kernel(self, kernel: str) -> Tuple[float, float]:
        """
        Extract motion parameters from convolution kernel.

        Args:
            kernel: Kernel matrix string

        Returns:
            Tuple of (angle_degrees, distance_pixels)
        """
        # This is a simplified extraction - in practice this would
        # require more sophisticated kernel analysis
        values = [float(v) for v in kernel.split()]

        # Default values for unrecognized kernels
        angle = 0.0
        distance = len([v for v in values if v != 0])  # Rough approximation

        return (angle, distance)

    def _generate_motion_blur_approximation(self, angle: float, distance: float,
                                          context: FilterContext) -> str:
        """
        Generate motion blur approximation using available PowerPoint effects.

        Since PowerPoint doesn't have native motion blur, we approximate
        using a combination of blur and shadow effects.

        Args:
            angle: Motion angle in degrees
            distance: Motion distance in pixels
            context: Filter processing context

        Returns:
            DrawingML XML string approximating motion blur
        """
        effects = []

        # Base blur effect
        blur_radius = context.unit_converter.to_emu(f"{distance * 0.3}px")  # Approximation
        blur_radius = max(0, min(int(blur_radius), 1270000))  # Reasonable limit

        effects.append(f'<a:blur rad="{blur_radius}"/>')

        # Add directional shadow to simulate motion trail
        # Convert angle to PowerPoint's angle system (21600000 units = 360°)
        ppt_angle = int((angle * 60000) % 21600000)

        # Distance in EMUs
        shadow_distance = context.unit_converter.to_emu(f"{distance * 0.5}px")
        shadow_distance = max(0, min(int(shadow_distance), 914400))  # Max ~36px

        effects.append(
            f'<a:outerShdw blurRad="{blur_radius // 2}" '
            f'dist="{shadow_distance}" dir="{ppt_angle}" algn="ctr">'
            '<a:srgbClr val="808080"><a:alpha val="30000"/></a:srgbClr>'
            '</a:outerShdw>'
        )

        # Add comment explaining the approximation
        effects.append(
            f'<!-- Motion blur approximation: {angle}° angle, {distance}px distance -->'
        )

        return ''.join(effects)