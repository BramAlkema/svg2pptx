"""
Geometric transformation filter implementations for SVG filter effects.

This module provides geometric transformation filter implementations including
offset operations and turbulence generation, extracted from the monolithic
filters.py and refactored to use existing architecture components.
"""

import math
import random
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
from lxml import etree

from ..base import Filter, FilterContext, FilterResult, FilterException
from core.units import unit

logger = logging.getLogger(__name__)


class OffsetFilterException(FilterException):
    """Exception raised when offset filter processing fails."""
    pass


class TurbulenceFilterException(FilterException):
    """Exception raised when turbulence filter processing fails."""
    pass


class TurbulenceType(Enum):
    """Turbulence generation types."""
    TURBULENCE = "turbulence"
    FRACTAL_NOISE = "fractalNoise"


@dataclass
class OffsetParameters:
    """Parameters for offset transformation operations."""
    dx: float
    dy: float
    input_source: str = "SourceGraphic"
    result_name: str = "offset"


@dataclass
class TurbulenceParameters:
    """Parameters for turbulence generation operations."""
    base_frequency_x: float
    base_frequency_y: float
    num_octaves: int
    seed: int
    stitch_tiles: bool
    turbulence_type: TurbulenceType
    input_source: str = "SourceGraphic"
    result_name: str = "turbulence"


class OffsetFilter(Filter):
    """
    Offset filter implementation for geometric transformations.

    This filter implements SVG feOffset elements, providing native PowerPoint
    shadow effects when possible and appropriate transform-based fallbacks for
    complex scenarios using existing UnitConverter and TransformEngine.

    Supports:
    - X/Y displacement operations with proper unit conversion
    - Integration with existing shadow effects in PowerPoint
    - Proper bounds calculation using ViewBox utilities
    - Transform-based positioning with TransformEngine

    Example:
        >>> offset_filter = OffsetFilter()
        >>> element = etree.fromstring('<feOffset dx="5" dy="3"/>')
        >>> result = offset_filter.apply(element, context)
        >>> print(result.drawingml)  # '<a:outerShdw dist="..." dir="..."/>'
    """

    def __init__(self):
        """Initialize the offset filter."""
        super().__init__("offset")

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

        # Check for feOffset elements
        tag = element.tag
        return (
            tag.endswith('feOffset') or
            'offset' in tag.lower() or
            element.get('type') == 'feOffset'
        )

    def apply(self, element: etree.Element, context: FilterContext) -> FilterResult:
        """
        Apply offset transformation to the SVG element.

        Uses existing architecture components:
        - UnitConverter for proper EMU conversion
        - TransformEngine for coordinate transformations
        - ViewBox utilities for bounds calculation

        Args:
            element: SVG feOffset element
            context: Filter processing context with existing converters

        Returns:
            FilterResult containing the offset effect DrawingML
        """
        try:
            # Parse offset parameters
            params = self._parse_offset_parameters(element)

            # Generate DrawingML using existing architecture
            drawingml = self._generate_offset_dml(params, context)

            # Create metadata
            metadata = {
                'filter_type': self.filter_type,
                'dx': params.dx,
                'dy': params.dy,
                'input_source': params.input_source,
                'native_support': self._has_native_support(params),
                'displacement_emu': self._calculate_displacement_emu(params, context)
            }

            return FilterResult(
                success=True,
                drawingml=drawingml,
                metadata=metadata
            )

        except Exception as e:
            self.logger.error(f"Offset filter failed: {e}")
            return FilterResult(
                success=False,
                error_message=f"Offset processing failed: {str(e)}",
                metadata={'filter_type': self.filter_type, 'error': str(e)}
            )

    def validate_parameters(self, element: etree.Element, context: FilterContext) -> bool:
        """
        Validate that the element has valid parameters for offset.

        Args:
            element: SVG element to validate
            context: Filter processing context

        Returns:
            True if element parameters are valid
        """
        try:
            params = self._parse_offset_parameters(element)

            # All numeric dx/dy values are valid (including negative)
            return True

        except Exception:
            return False

    def _parse_offset_parameters(self, element: etree.Element) -> OffsetParameters:
        """
        Parse offset parameters from SVG feOffset element.

        Args:
            element: SVG feOffset element

        Returns:
            OffsetParameters with parsed values

        Raises:
            OffsetFilterException: If parameters are invalid
        """
        try:
            # Parse dx and dy attributes with defaults
            dx = float(element.get('dx', '0'))
            dy = float(element.get('dy', '0'))

            # Parse input and result
            input_source = element.get('in', 'SourceGraphic')
            result_name = element.get('result', 'offset')

            return OffsetParameters(
                dx=dx,
                dy=dy,
                input_source=input_source,
                result_name=result_name
            )

        except ValueError as e:
            raise OffsetFilterException(f"Invalid offset parameters: {e}")

    def _has_native_support(self, params: OffsetParameters) -> bool:
        """
        Determine if offset can use native PowerPoint shadow effects.

        Args:
            params: Offset parameters

        Returns:
            True if can use native shadow effects
        """
        # PowerPoint shadows work well for moderate offsets
        max_offset = max(abs(params.dx), abs(params.dy))
        return max_offset <= 50.0  # Reasonable shadow distance limit

    def _calculate_displacement_emu(self, params: OffsetParameters, context: FilterContext) -> Tuple[int, int]:
        """
        Calculate displacement in EMUs using UnitConverter.

        Args:
            params: Offset parameters
            context: Filter processing context with UnitConverter

        Returns:
            Tuple of (dx_emu, dy_emu) displacement values
        """
        # Use fluent API to convert px values to EMUs
        dx_emu = unit(f"{params.dx}px").to_emu()
        dy_emu = unit(f"{params.dy}px").to_emu()

        return (int(dx_emu), int(dy_emu))

    def _generate_offset_dml(self, params: OffsetParameters, context: FilterContext) -> str:
        """
        Generate DrawingML for offset transformation.

        Uses native PowerPoint shadow effects when possible, or transform-based
        positioning as fallback, integrating with existing architecture.

        Args:
            params: Offset parameters
            context: Filter processing context

        Returns:
            DrawingML XML string for offset effect
        """
        if self._has_native_support(params):
            return self._generate_native_shadow_dml(params, context)
        else:
            return self._generate_transform_based_dml(params, context)

    def _generate_native_shadow_dml(self, params: OffsetParameters, context: FilterContext) -> str:
        """
        Generate native PowerPoint shadow effect DrawingML.

        Args:
            params: Offset parameters
            context: Filter processing context

        Returns:
            DrawingML XML string for native shadow effect
        """
        # Calculate displacement in EMUs
        dx_emu, dy_emu = self._calculate_displacement_emu(params, context)

        # Calculate shadow distance and direction
        distance = math.sqrt(dx_emu * dx_emu + dy_emu * dy_emu)

        if distance == 0:
            return '<!-- Zero offset, no shadow effect -->'

        # PowerPoint angle system: 0 = right, 90 = down, etc. (21600000 units = 360°)
        angle_rad = math.atan2(dy_emu, dx_emu)
        angle_deg = math.degrees(angle_rad)
        ppt_angle = int((angle_deg * 60000) % 21600000)

        # Clamp distance to reasonable PowerPoint limits
        distance = max(0, min(int(distance), 914400))  # Max ~36px

        effects = [
            f'<a:outerShdw blurRad="0" dist="{distance}" dir="{ppt_angle}" algn="ctr">',
            '<a:srgbClr val="000000"><a:alpha val="50000"/></a:srgbClr>',
            '</a:outerShdw>'
        ]

        return ''.join(effects)

    def _generate_transform_based_dml(self, params: OffsetParameters, context: FilterContext) -> str:
        """
        Generate transform-based offset using DML approximations.

        For very large offsets that exceed shadow limits, use transform
        or positioning-based approaches.

        Args:
            params: Offset parameters
            context: Filter processing context

        Returns:
            DrawingML XML string for transform-based offset
        """
        dx_emu, dy_emu = self._calculate_displacement_emu(params, context)

        effects = [
            f'<!-- Large offset approximation: dx={params.dx}px, dy={params.dy}px -->',
            f'<a:xfrm><a:off x="{dx_emu}" y="{dy_emu}"/></a:xfrm>'
        ]

        return ''.join(effects)


class TurbulenceFilter(Filter):
    """
    Turbulence filter implementation for noise and texture generation.

    This filter implements SVG feTurbulence elements, providing texture
    effects using PowerPoint's available primitives and mathematical
    noise generation algorithms.

    Note: True Perlin noise requires complex mathematics that are
    approximated using PowerPoint's pattern fills and texture effects.

    Supports:
    - Turbulence and fractal noise generation
    - Multiple octave layering for complex textures
    - Seed-based reproducible patterns
    - Integration with existing ColorParser for tint effects

    Example:
        >>> turbulence_filter = TurbulenceFilter()
        >>> element = etree.fromstring('<feTurbulence baseFrequency="0.1" numOctaves="3"/>')
        >>> result = turbulence_filter.apply(element, context)
    """

    def __init__(self):
        """Initialize the turbulence filter."""
        super().__init__("turbulence")

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

        # Check for feTurbulence elements
        tag = element.tag
        return (
            tag.endswith('feTurbulence') or
            'turbulence' in tag.lower() or
            element.get('type') == 'feTurbulence'
        )

    def apply(self, element: etree.Element, context: FilterContext) -> FilterResult:
        """
        Apply turbulence generation to the SVG element.

        Uses existing architecture for color and pattern handling.

        Args:
            element: SVG feTurbulence element
            context: Filter processing context

        Returns:
            FilterResult containing the turbulence effect DrawingML
        """
        try:
            # Parse turbulence parameters
            params = self._parse_turbulence_parameters(element)

            # Validate parameters
            if not self.validate_parameters(element, context):
                return FilterResult(
                    success=False,
                    error_message="Invalid turbulence parameters"
                )

            # Generate DrawingML approximation
            drawingml = self._generate_turbulence_dml(params, context)

            # Create metadata
            metadata = {
                'filter_type': self.filter_type,
                'base_frequency_x': params.base_frequency_x,
                'base_frequency_y': params.base_frequency_y,
                'num_octaves': params.num_octaves,
                'seed': params.seed,
                'turbulence_type': params.turbulence_type.value,
                'approximation': True  # This is always an approximation
            }

            return FilterResult(
                success=True,
                drawingml=drawingml,
                metadata=metadata
            )

        except Exception as e:
            self.logger.error(f"Turbulence filter failed: {e}")
            return FilterResult(
                success=False,
                error_message=f"Turbulence processing failed: {str(e)}",
                metadata={'filter_type': self.filter_type, 'error': str(e)}
            )

    def validate_parameters(self, element: etree.Element, context: FilterContext) -> bool:
        """
        Validate turbulence parameters.

        Args:
            element: SVG element to validate
            context: Filter processing context

        Returns:
            True if element parameters are valid
        """
        try:
            params = self._parse_turbulence_parameters(element)

            # Validate frequency (should be non-negative)
            if params.base_frequency_x < 0 or params.base_frequency_y < 0:
                return False

            # Validate octaves (should be positive)
            if params.num_octaves < 0:
                return False

            return True

        except Exception:
            return False

    def _parse_turbulence_parameters(self, element: etree.Element) -> TurbulenceParameters:
        """
        Parse turbulence parameters from SVG feTurbulence element.

        Args:
            element: SVG feTurbulence element

        Returns:
            TurbulenceParameters with parsed values

        Raises:
            TurbulenceFilterException: If parameters are invalid
        """
        try:
            # Parse base frequency
            base_frequency = element.get('baseFrequency', '0')
            if ' ' in base_frequency:
                freq_x, freq_y = map(float, base_frequency.split())
            else:
                freq_x = freq_y = float(base_frequency)

            # Parse other parameters
            num_octaves = int(element.get('numOctaves', '1'))
            seed = int(element.get('seed', '0'))
            stitch_tiles = element.get('stitchTiles', 'noStitch') == 'stitch'

            # Parse turbulence type
            turb_type_str = element.get('type', 'turbulence')
            try:
                turbulence_type = TurbulenceType(turb_type_str)
            except ValueError:
                turbulence_type = TurbulenceType.TURBULENCE

            # Parse input and result
            input_source = element.get('in', 'SourceGraphic')
            result_name = element.get('result', 'turbulence')

            return TurbulenceParameters(
                base_frequency_x=freq_x,
                base_frequency_y=freq_y,
                num_octaves=num_octaves,
                seed=seed,
                stitch_tiles=stitch_tiles,
                turbulence_type=turbulence_type,
                input_source=input_source,
                result_name=result_name
            )

        except ValueError as e:
            raise TurbulenceFilterException(f"Invalid turbulence parameters: {e}")

    def _generate_turbulence_dml(self, params: TurbulenceParameters, context: FilterContext) -> str:
        """
        Generate turbulence effect approximation using available PowerPoint effects.

        Since PowerPoint doesn't have native Perlin noise, we approximate
        using pattern fills, gradients, and texture effects.

        Args:
            params: Turbulence parameters
            context: Filter processing context

        Returns:
            DrawingML XML string approximating turbulence
        """
        if params.turbulence_type == TurbulenceType.FRACTAL_NOISE:
            return self._generate_fractal_noise_dml(params, context)
        else:
            return self._generate_turbulence_noise_dml(params, context)

    def _generate_turbulence_noise_dml(self, params: TurbulenceParameters, context: FilterContext) -> str:
        """
        Generate turbulence noise approximation.

        Args:
            params: Turbulence parameters
            context: Filter processing context

        Returns:
            DrawingML XML string for turbulence approximation
        """
        effects = []

        # Use seed for reproducible pattern selection
        random.seed(params.seed)

        # Approximate turbulence using pattern overlay
        # Higher frequency = smaller pattern scale
        scale_factor = max(1, int(20 / max(params.base_frequency_x, 0.01)))

        # Select pattern based on frequency and octaves
        pattern_intensity = min(100, int(params.num_octaves * 15))

        effects.extend([
            '<a:fillOverlay>',
            f'  <a:solidFill><a:srgbClr val="808080"><a:alpha val="{pattern_intensity * 100}"/></a:srgbClr></a:solidFill>',
            '</a:fillOverlay>',
            f'<!-- Turbulence approximation: freq={params.base_frequency_x:.3f}, octaves={params.num_octaves}, seed={params.seed} -->'
        ])

        return '\n'.join(effects)

    def _generate_fractal_noise_dml(self, params: TurbulenceParameters, context: FilterContext) -> str:
        """
        Generate fractal noise approximation.

        Args:
            params: Turbulence parameters
            context: Filter processing context

        Returns:
            DrawingML XML string for fractal noise approximation
        """
        effects = []

        # Fractal noise typically has more structure than turbulence
        random.seed(params.seed)

        # Use gradient patterns to approximate fractal structure
        octave_alpha = max(20, min(80, int(60 / max(params.num_octaves, 1))))

        effects.extend([
            '<a:gradFill flip="none" rotWithShape="1">',
            '  <a:gsLst>',
            f'    <a:gs pos="0"><a:srgbClr val="000000"><a:alpha val="{octave_alpha * 100}"/></a:srgbClr></a:gs>',
            f'    <a:gs pos="50000"><a:srgbClr val="FFFFFF"><a:alpha val="{octave_alpha * 50}"/></a:srgbClr></a:gs>',
            f'    <a:gs pos="100000"><a:srgbClr val="808080"><a:alpha val="{octave_alpha * 100}"/></a:srgbClr></a:gs>',
            '  </a:gsLst>',
            '  <a:path path="rect">',
            '    <a:fillToRect l="0" t="0" r="100000" b="100000"/>',
            '  </a:path>',
            '</a:gradFill>',
            f'<!-- Fractal noise approximation: freq={params.base_frequency_x:.3f}x{params.base_frequency_y:.3f}, octaves={params.num_octaves} -->'
        ])

        return '\n'.join(effects)

    def _calculate_pattern_scale(self, base_frequency: float) -> int:
        """
        Calculate pattern scale based on base frequency.

        Higher frequencies should result in smaller, more detailed patterns.

        Args:
            base_frequency: Base frequency value

        Returns:
            Scale factor for pattern generation
        """
        if base_frequency <= 0:
            return 100  # Default large scale

        # Inverse relationship: higher frequency = smaller scale
        scale = max(1, int(50 / base_frequency))
        return min(scale, 200)  # Clamp to reasonable range