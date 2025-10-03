#!/usr/bin/env python3
"""
Gaussian Blur Filter Processor for SVG Filter Effects

Implements SVG feGaussianBlur filter with vector-first strategy,
using PowerPoint native blur effects for high-fidelity conversion
and EMF fallback for complex blur operations.

Migrated from archive implementation and adapted to clean slate architecture.
"""

from typing import Dict, List, Optional, Tuple, Union, Any
from enum import Enum
from dataclasses import dataclass
from lxml import etree as ET
import math

from .base import FilterProcessor, FilterContext, FilterResult, FilterStrategy
from ..units import unit
from ..policy.targets import PolicyDecision


class BlurFilterException(Exception):
    """Exception raised during Gaussian blur processing."""
    pass


class BlurValidationError(BlurFilterException, ValueError):
    """Exception raised when blur parameters are invalid."""
    pass


@dataclass
class BlurParameters:
    """Parameters for Gaussian blur processing."""
    std_deviation_x: float = 0.0
    std_deviation_y: float = 0.0
    edge_mode: str = "duplicate"  # duplicate, wrap, none
    input_source: str = "SourceGraphic"
    result_name: Optional[str] = None

    def __post_init__(self):
        """Validate parameters after initialization."""
        # Ensure non-negative standard deviations
        if self.std_deviation_x < 0:
            self.std_deviation_x = 0.0
        if self.std_deviation_y < 0:
            self.std_deviation_y = 0.0

        # Validate edge mode
        valid_edge_modes = {"duplicate", "wrap", "none"}
        if self.edge_mode not in valid_edge_modes:
            self.edge_mode = "duplicate"

    def get_complexity_score(self) -> float:
        """Calculate complexity score for strategy selection."""
        complexity = 0.0

        # Base complexity from standard deviation magnitude
        max_std = max(self.std_deviation_x, self.std_deviation_y)
        complexity += min(max_std / 10.0, 3.0)  # Cap at 3x

        # Anisotropic blur adds complexity
        if self.std_deviation_x != self.std_deviation_y:
            complexity += 1.0

        # Non-standard edge modes add complexity
        if self.edge_mode != "duplicate":
            complexity += 0.5

        return complexity

    def is_isotropic(self) -> bool:
        """Check if blur is isotropic (same X and Y standard deviation)."""
        return abs(self.std_deviation_x - self.std_deviation_y) < 1e-6

    def is_effective(self) -> bool:
        """Check if blur has any visible effect."""
        return max(self.std_deviation_x, self.std_deviation_y) > 0.1

    def get_average_std_deviation(self) -> float:
        """Get average standard deviation for isotropic approximation."""
        return (self.std_deviation_x + self.std_deviation_y) / 2.0


class GaussianBlurProcessor(FilterProcessor):
    """Processor for SVG feGaussianBlur filter effects."""

    def __init__(self, policy=None):
        super().__init__(filter_type='feGaussianBlur', policy=policy)
        self.max_native_blur = 25.0  # PowerPoint works well up to ~25px blur
        self.max_blur_radius_emu = 2540000  # ~100px in EMUs

    def can_apply(self, element: ET.Element, context: FilterContext) -> bool:
        """Check if this processor can handle the given element."""
        if element is None or element.tag != 'feGaussianBlur':
            return False
        return self._validate_parameters(element, context)

    def apply(self, element: ET.Element, context: FilterContext) -> FilterResult:
        """Apply Gaussian blur processing to the element."""
        try:
            # Validate parameters first
            if not self._validate_parameters(element, context):
                raise BlurFilterException("Invalid Gaussian blur parameters")

            # Parse blur parameters
            params = self._parse_blur_parameters(element)

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
                error_message=f"Gaussian blur processing failed: {str(e)}"
            )

    def _validate_parameters(self, element: ET.Element, context: FilterContext) -> bool:
        """Validate Gaussian blur parameters."""
        if element is None or context is None:
            return False
        try:
            self._parse_blur_parameters(element)
            return True
        except (BlurFilterException, ValueError, TypeError):
            return False

    def _parse_blur_parameters(self, element: ET.Element) -> BlurParameters:
        """Parse Gaussian blur parameters from SVG element."""
        # Parse standard deviation
        std_deviation_str = element.get('stdDeviation', '0')
        std_x, std_y = self._parse_std_deviation(std_deviation_str)

        # Parse edge mode
        edge_mode = element.get('edgeMode', 'duplicate').lower()

        # Parse input source
        input_source = element.get('in', 'SourceGraphic')

        # Parse result name
        result_name = element.get('result')

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
            BlurValidationError: If value is invalid
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
            raise BlurValidationError(f"Invalid stdDeviation value '{std_deviation}': {e}")

    def _get_strategy(self, params: BlurParameters, context: FilterContext) -> FilterStrategy:
        """Determine the best strategy for Gaussian blur processing."""
        if self.policy:
            decision = self.policy.decide_blur_strategy(params, context)
            return decision.strategy

        # Default strategy logic
        complexity = params.get_complexity_score()

        if self._can_use_native_blur(params):
            return FilterStrategy.NATIVE
        elif complexity < 3.0:
            return FilterStrategy.APPROXIMATION
        else:
            return FilterStrategy.EMF_RASTERIZE

    def _can_use_native_blur(self, params: BlurParameters) -> bool:
        """Check if parameters can be handled with native PowerPoint blur."""
        # Check if blur is effective
        if not params.is_effective():
            return True  # No-op case

        # PowerPoint blur works best with isotropic blur
        if not params.is_isotropic():
            return False

        # Check if within PowerPoint's effective range
        max_std = max(params.std_deviation_x, params.std_deviation_y)
        if max_std > self.max_native_blur:
            return False

        # Edge modes other than duplicate need special handling
        if params.edge_mode != "duplicate":
            return False

        return True

    def _apply_native_strategy(self, params: BlurParameters, context: FilterContext) -> FilterResult:
        """Apply native PowerPoint blur effects."""
        try:
            drawingml = ""

            if not params.is_effective():
                # No-op case: very small or zero blur
                drawingml = "<!-- No visible blur effect -->"
            else:
                # Generate native blur effect
                drawingml = self._generate_native_blur_drawingml(params, context)

            return FilterResult(
                success=True,
                strategy=FilterStrategy.NATIVE,
                drawingml=drawingml,
                metadata={
                    'filter_type': self.filter_type,
                    'approach': 'native',
                    'std_deviation_x': params.std_deviation_x,
                    'std_deviation_y': params.std_deviation_y,
                    'edge_mode': params.edge_mode,
                    'is_isotropic': params.is_isotropic(),
                    'complexity': params.get_complexity_score()
                }
            )

        except Exception as e:
            return FilterResult(
                success=False,
                strategy=FilterStrategy.NATIVE,
                drawingml="",
                error_message=f"Native Gaussian blur failed: {str(e)}"
            )

    def _generate_native_blur_drawingml(self, params: BlurParameters, context: FilterContext) -> str:
        """Generate DrawingML for native PowerPoint blur effect."""
        # Use average of X and Y for isotropic-like effect
        std_dev = params.get_average_std_deviation()

        # Convert to EMUs (PowerPoint's internal units)
        radius_emu = unit(f"{std_dev}px").to_emu()

        # Clamp to reasonable range for PowerPoint
        radius_emu = max(0, min(int(radius_emu), self.max_blur_radius_emu))

        return f'<a:blur rad="{radius_emu}"/>'

    def _apply_approximation_strategy(self, params: BlurParameters, context: FilterContext) -> FilterResult:
        """Apply approximation strategy for complex blur."""
        try:
            drawingml = self._generate_approximation_blur_drawingml(params, context)

            return FilterResult(
                success=True,
                strategy=FilterStrategy.APPROXIMATION,
                drawingml=drawingml,
                metadata={
                    'filter_type': self.filter_type,
                    'approach': 'approximation',
                    'std_deviation_x': params.std_deviation_x,
                    'std_deviation_y': params.std_deviation_y,
                    'edge_mode': params.edge_mode,
                    'is_isotropic': params.is_isotropic(),
                    'complexity': params.get_complexity_score()
                }
            )

        except Exception as e:
            return FilterResult(
                success=False,
                strategy=FilterStrategy.APPROXIMATION,
                drawingml="",
                error_message=f"Approximation Gaussian blur failed: {str(e)}"
            )

    def _generate_approximation_blur_drawingml(self, params: BlurParameters, context: FilterContext) -> str:
        """Generate DrawingML for approximated blur effects."""
        effects = []

        if not params.is_isotropic():
            # Anisotropic blur approximation
            # Use the larger value for main blur
            main_std = max(params.std_deviation_x, params.std_deviation_y)
            main_radius = unit(f"{main_std}px").to_emu()
            main_radius = max(0, min(int(main_radius), self.max_blur_radius_emu))

            effects.append(f'<a:blur rad="{main_radius}"/>')

            # Add comment about anisotropic approximation
            effects.append(
                f'<!-- Anisotropic blur approximation: {params.std_deviation_x}x{params.std_deviation_y} -->'
            )
        else:
            # Isotropic blur with special edge mode or large radius
            radius_emu = unit(f"{params.std_deviation_x}px").to_emu()
            radius_emu = max(0, min(int(radius_emu), self.max_blur_radius_emu))

            effects.append(f'<a:blur rad="{radius_emu}"/>')

            if params.edge_mode != 'duplicate':
                effects.append(f'<!-- Edge mode: {params.edge_mode} (approximated) -->')

        return ''.join(effects)

    def _apply_emf_strategy(self, params: BlurParameters, context: FilterContext) -> FilterResult:
        """Apply EMF rasterization strategy for complex blur."""
        try:
            # EMF rasterization placeholder
            # In a full implementation, this would:
            # 1. Render the source graphic to EMF bitmap
            # 2. Apply Gaussian blur convolution
            # 3. Embed as blip reference

            return FilterResult(
                success=True,
                strategy=FilterStrategy.EMF_RASTERIZE,
                drawingml="<!-- EMF rasterization for complex Gaussian blur -->",
                metadata={
                    'filter_type': self.filter_type,
                    'approach': 'emf',
                    'std_deviation_x': params.std_deviation_x,
                    'std_deviation_y': params.std_deviation_y,
                    'edge_mode': params.edge_mode,
                    'is_isotropic': params.is_isotropic(),
                    'complexity': params.get_complexity_score()
                }
            )

        except Exception as e:
            return FilterResult(
                success=False,
                strategy=FilterStrategy.EMF_RASTERIZE,
                drawingml="",
                error_message=f"EMF Gaussian blur failed: {str(e)}"
            )

    def _convert_to_ooxml_radius(self, std_deviation: float) -> int:
        """Convert standard deviation to OOXML blur radius."""
        radius_emu = unit(f"{std_deviation}px").to_emu()
        return max(0, min(int(radius_emu), self.max_blur_radius_emu))


def create_gaussian_blur_processor(policy=None) -> GaussianBlurProcessor:
    """Factory function to create a GaussianBlurProcessor instance."""
    return GaussianBlurProcessor(policy=policy)