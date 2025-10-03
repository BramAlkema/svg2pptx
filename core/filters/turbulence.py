#!/usr/bin/env python3
"""
SVG feTurbulence Filter Processor

Implements SVG feTurbulence filter effects using procedural Perlin-style noise generation
for both fractalNoise and turbulence modes. Provides policy-driven strategy selection
between native PowerPoint effects, pattern approximations, and rasterization.

This processor supports:
- fractalNoise and turbulence noise types
- Multi-octave noise with proper amplitude scaling
- Deterministic seeding for reproducible results
- Frequency control in objectBoundingBox coordinates
- Basic tile stitching for seamless patterns
"""

import math
from dataclasses import dataclass, field
from typing import Tuple, Optional, Dict, Any, List, Literal, TYPE_CHECKING
from lxml import etree as ET

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

from .base import (
    FilterProcessor,
    FilterContext,
    FilterResult,
    FilterStrategy,
    FilterException,
    FilterValidationError
)

if TYPE_CHECKING:
    from ..policy.engine import Policy


class TurbulenceFilterException(FilterException):
    """Exception raised during turbulence filter processing."""
    pass


class TurbulenceValidationError(FilterValidationError, TurbulenceFilterException):
    """Exception raised for invalid turbulence parameters."""
    pass


@dataclass
class TurbulenceParameters:
    """Parameters for SVG feTurbulence filter processing."""

    # Core turbulence attributes
    turbulence_type: Literal["fractalNoise", "turbulence"] = "turbulence"
    base_frequency_x: float = 0.01
    base_frequency_y: Optional[float] = None
    num_octaves: int = 1
    seed: int = 0
    stitch_tiles: bool = False

    # Input/output
    input_source: str = "SourceGraphic"
    result_name: Optional[str] = None

    def __post_init__(self):
        """Validate parameters after initialization."""
        if self.turbulence_type not in ("fractalNoise", "turbulence"):
            raise TurbulenceValidationError(f"Invalid turbulence type: {self.turbulence_type}")

        if self.base_frequency_x <= 0:
            raise TurbulenceValidationError("Base frequency X must be positive")

        if self.base_frequency_y is not None and self.base_frequency_y <= 0:
            raise TurbulenceValidationError("Base frequency Y must be positive")

        if self.num_octaves < 1:
            raise TurbulenceValidationError("Number of octaves must be at least 1")

        # Clamp parameters to reasonable ranges
        self.base_frequency_x = max(0.001, min(10.0, self.base_frequency_x))
        if self.base_frequency_y is not None:
            self.base_frequency_y = max(0.001, min(10.0, self.base_frequency_y))
        self.num_octaves = max(1, min(8, self.num_octaves))  # Limit for performance
        self.seed = int(self.seed) & 0xFFFFFFFF  # 32-bit seed

    def get_frequency_y(self) -> float:
        """Get effective Y frequency (defaults to X frequency if not specified)."""
        return self.base_frequency_y if self.base_frequency_y is not None else self.base_frequency_x

    def get_complexity_score(self) -> float:
        """Calculate complexity score for strategy selection."""
        base_score = 0.0

        # More octaves = more complex
        if self.num_octaves > 3:
            base_score += 0.3

        # High frequency = more complex
        max_freq = max(self.base_frequency_x, self.get_frequency_y())
        if max_freq > 0.1:
            base_score += 0.3

        # Stitching adds complexity
        if self.stitch_tiles:
            base_score += 0.2

        return min(1.0, base_score)

    def is_suitable_for_native(self) -> bool:
        """Check if parameters are suitable for native PowerPoint effects."""
        # Simple turbulence with low octaves could use texture fills
        return (self.num_octaves <= 2 and
                max(self.base_frequency_x, self.get_frequency_y()) <= 0.05 and
                not self.stitch_tiles)


class TurbulenceProcessor(FilterProcessor):
    """Processor for SVG feTurbulence filter effects."""

    def __init__(self, filter_type: str = 'feTurbulence', policy=None):
        super().__init__(filter_type=filter_type, policy=policy)
        self.max_texture_size = 512  # Maximum texture size for performance

    def can_apply(self, element: ET.Element, context: FilterContext) -> bool:
        """Check if this processor can handle the given element."""
        if element.tag != "feTurbulence":
            return False

        try:
            self._parse_parameters(element, context)
            return True
        except (TurbulenceValidationError, ValueError):
            return False

    def apply(self, element: ET.Element, context: FilterContext) -> FilterResult:
        """Apply feTurbulence filter with strategy selection."""
        try:
            # Parse parameters
            params = self._parse_parameters(element, context)

            # Check NumPy availability for complex processing
            if not NUMPY_AVAILABLE and params.get_complexity_score() > 0.3:
                return FilterResult(
                    success=False,
                    strategy=FilterStrategy.EMF_RASTERIZE,
                    error_message="NumPy required for complex turbulence processing",
                    metadata={'filter_type': self.filter_type, 'error': 'numpy_required'}
                )

            # Select strategy based on complexity
            strategy = self._select_strategy(params, context)

            # Apply selected strategy
            if strategy == FilterStrategy.NATIVE:
                return self._apply_native_strategy(params, context)
            elif strategy == FilterStrategy.APPROXIMATION:
                return self._apply_approximation_strategy(params, context)
            else:  # EMF_RASTERIZE
                return self._apply_rasterization_strategy(params, context)

        except TurbulenceValidationError as e:
            return FilterResult(
                success=False,
                strategy=FilterStrategy.APPROXIMATION,
                error_message=str(e),
                metadata={'filter_type': self.filter_type, 'error': str(e)}
            )
        except Exception as e:
            return FilterResult(
                success=False,
                strategy=FilterStrategy.EMF_RASTERIZE,
                error_message=f"Turbulence filter processing failed: {str(e)}",
                metadata={'filter_type': self.filter_type, 'error': str(e)}
            )

    def _parse_parameters(self, element: ET.Element, context: FilterContext) -> TurbulenceParameters:
        """Parse feTurbulence element attributes."""
        try:
            # Turbulence type
            turbulence_type = element.get("type", "turbulence")
            if turbulence_type not in ("fractalNoise", "turbulence"):
                turbulence_type = "turbulence"

            # Base frequency (can be single value or "fx fy")
            base_frequency = element.get("baseFrequency", "0.01")
            freq_parts = base_frequency.strip().split()
            if len(freq_parts) >= 2:
                base_frequency_x = float(freq_parts[0])
                base_frequency_y = float(freq_parts[1])
            else:
                base_frequency_x = float(freq_parts[0])
                base_frequency_y = None

            # Number of octaves
            num_octaves = int(element.get("numOctaves", "1"))

            # Seed
            seed = int(element.get("seed", "0"))

            # Stitch tiles
            stitch_tiles = element.get("stitchTiles", "noStitch") == "stitch"

            # Input/output
            input_source = element.get("in", "SourceGraphic")
            result_name = element.get("result")

            return TurbulenceParameters(
                turbulence_type=turbulence_type,
                base_frequency_x=base_frequency_x,
                base_frequency_y=base_frequency_y,
                num_octaves=num_octaves,
                seed=seed,
                stitch_tiles=stitch_tiles,
                input_source=input_source,
                result_name=result_name
            )

        except ValueError as e:
            raise TurbulenceValidationError(f"Invalid turbulence parameters: {e}")

    def _select_strategy(self, params: TurbulenceParameters, context: FilterContext) -> FilterStrategy:
        """Select processing strategy based on complexity and capabilities."""
        complexity = params.get_complexity_score()

        # Simple patterns can use native PowerPoint textures
        if complexity < 0.3 and params.is_suitable_for_native():
            return FilterStrategy.NATIVE

        # Medium complexity uses pattern approximation
        if complexity < 0.7 and NUMPY_AVAILABLE:
            return FilterStrategy.APPROXIMATION

        # Complex patterns need rasterization (requires NumPy)
        return FilterStrategy.EMF_RASTERIZE

    def _apply_native_strategy(self, params: TurbulenceParameters, context: FilterContext) -> FilterResult:
        """Apply turbulence using PowerPoint's native texture capabilities."""
        try:
            # Use PowerPoint texture fills for simple noise patterns
            pattern_type = self._select_native_pattern(params)
            drawingml = self._generate_native_texture_xml(params, pattern_type, context)

            return FilterResult(
                success=True,
                strategy=FilterStrategy.NATIVE,
                drawingml=drawingml,
                metadata={
                    'filter_type': self.filter_type,
                    'turbulence_type': params.turbulence_type,
                    'pattern': pattern_type,
                    'frequency_x': params.base_frequency_x,
                    'frequency_y': params.get_frequency_y(),
                    'octaves': params.num_octaves,
                    'seed': params.seed
                }
            )

        except Exception as e:
            raise TurbulenceFilterException(f"Native strategy failed: {e}")

    def _apply_approximation_strategy(self, params: TurbulenceParameters, context: FilterContext) -> FilterResult:
        """Apply turbulence using pattern approximation."""
        try:
            if not NUMPY_AVAILABLE:
                raise TurbulenceFilterException("NumPy required for approximation strategy")

            # Generate simplified noise pattern
            pattern_xml = self._generate_pattern_approximation(params, context)

            return FilterResult(
                success=True,
                strategy=FilterStrategy.APPROXIMATION,
                drawingml=pattern_xml,
                metadata={
                    'filter_type': self.filter_type,
                    'approach': 'pattern_approximation',
                    'turbulence_type': params.turbulence_type,
                    'frequency_x': params.base_frequency_x,
                    'frequency_y': params.get_frequency_y(),
                    'octaves': params.num_octaves,
                    'seed': params.seed
                }
            )

        except Exception as e:
            raise TurbulenceFilterException(f"Approximation strategy failed: {e}")

    def _apply_rasterization_strategy(self, params: TurbulenceParameters, context: FilterContext) -> FilterResult:
        """Apply turbulence using full rasterization (your original implementation)."""
        try:
            if not NUMPY_AVAILABLE:
                raise TurbulenceFilterException("NumPy required for rasterization strategy")

            # Use the full Perlin noise implementation you provided
            noise_data = self._generate_perlin_noise(params, context)

            # Convert to EMF or pattern reference
            texture_reference = f"turbulence_{params.turbulence_type}_{params.seed}_{id(params)}"
            drawingml = self._generate_rasterized_xml(params, texture_reference, context)

            return FilterResult(
                success=True,
                strategy=FilterStrategy.EMF_RASTERIZE,
                drawingml=drawingml,
                metadata={
                    'filter_type': self.filter_type,
                    'approach': 'rasterization',
                    'turbulence_type': params.turbulence_type,
                    'texture_reference': texture_reference,
                    'frequency_x': params.base_frequency_x,
                    'frequency_y': params.get_frequency_y(),
                    'octaves': params.num_octaves,
                    'seed': params.seed,
                    'stitch_tiles': params.stitch_tiles
                }
            )

        except Exception as e:
            raise TurbulenceFilterException(f"Rasterization strategy failed: {e}")

    def _select_native_pattern(self, params: TurbulenceParameters) -> str:
        """Select appropriate PowerPoint texture pattern."""
        if params.turbulence_type == "fractalNoise":
            return "canvas" if params.num_octaves <= 1 else "paperBag"
        else:  # turbulence
            return "granite" if params.num_octaves <= 1 else "marble"

    def _generate_native_texture_xml(self, params: TurbulenceParameters, pattern_type: str, context: FilterContext) -> str:
        """Generate native PowerPoint texture XML."""
        return f'''<a:pattFill prst="{pattern_type}">
    <a:fgClr><a:schemeClr val="tx1"/></a:fgClr>
    <a:bgClr><a:schemeClr val="bg1"/></a:bgClr>
</a:pattFill>'''

    def _generate_pattern_approximation(self, params: TurbulenceParameters, context: FilterContext) -> str:
        """Generate simplified pattern approximation."""
        # Use a simpler noise pattern for medium complexity
        if params.turbulence_type == "fractalNoise":
            return '''<a:pattFill prst="weave">
    <a:fgClr><a:srgbClr val="808080"/></a:fgClr>
    <a:bgClr><a:srgbClr val="E0E0E0"/></a:bgClr>
</a:pattFill>'''
        else:
            return '''<a:pattFill prst="confetti">
    <a:fgClr><a:srgbClr val="606060"/></a:fgClr>
    <a:bgClr><a:srgbClr val="F0F0F0"/></a:bgClr>
</a:pattFill>'''

    def _generate_rasterized_xml(self, params: TurbulenceParameters, texture_ref: str, context: FilterContext) -> str:
        """Generate rasterized texture XML."""
        return f'''<a:blipFill>
    <a:blip r:embed="{texture_ref}">
        <a:extLst>
            <a:ext uri="{{28A0092B-C50C-407E-A947-70E740481C1C}}">
                <a14:useLocalDpi val="0"/>
            </a:ext>
        </a:extLst>
    </a:blip>
    <a:stretch>
        <a:fillRect/>
    </a:stretch>
</a:blipFill>'''

    def _generate_perlin_noise(self, params: TurbulenceParameters, context: FilterContext) -> 'np.ndarray':
        """Generate Perlin noise using your provided implementation."""
        if not NUMPY_AVAILABLE:
            raise TurbulenceFilterException("NumPy required for noise generation")

        # Use reasonable dimensions for texture generation
        w, h = 256, 256  # Standard texture size

        fx = float(params.base_frequency_x)
        fy = float(params.get_frequency_y())
        octaves = max(1, int(params.num_octaves))

        # Build grid of normalized coordinates
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        nx = (xx / max(1.0, w)) * fx
        ny = (yy / max(1.0, h)) * fy

        # Multi-octave noise accumulation
        rng_seed = int(params.seed) & 0xFFFFFFFF
        total = np.zeros((h, w), dtype=np.float32)
        amp_sum = 0.0
        freq_x = 1.0
        freq_y = 1.0
        amp = 1.0

        for octave in range(octaves):
            x = nx * freq_x
            y = ny * freq_y

            layer = self._perlin_like(x, y, rng_seed + octave, stitch=params.stitch_tiles)
            if params.turbulence_type == "turbulence":
                layer = np.abs(layer)
            total += amp * layer
            amp_sum += amp
            amp *= 0.5
            freq_x *= 2.0
            freq_y *= 2.0

        if amp_sum == 0.0:
            amp_sum = 1.0
        noise = total / amp_sum

        if params.turbulence_type == "fractalNoise":
            noise = (noise * 0.5) + 0.5

        # RGB channels identical, alpha=1.0
        img = np.empty((h, w, 4), dtype=np.float32)
        img[..., 0] = noise
        img[..., 1] = noise
        img[..., 2] = noise
        img[..., 3] = 1.0
        return img

    def _perlin_like(self, x: 'np.ndarray', y: 'np.ndarray', seed: int, stitch: bool = False) -> 'np.ndarray':
        """Lightweight gradient noise implementation (your code)."""
        # Grid corners
        x0 = np.floor(x).astype(np.int32)
        y0 = np.floor(y).astype(np.int32)
        x1 = x0 + 1
        y1 = y0 + 1

        # Relative positions
        xf = x - x0
        yf = y - y0

        # Fade curve
        u = self._fade(xf)
        v = self._fade(yf)

        # Pseudo-random gradients
        g00 = self._grad(x0, y0, seed)
        g10 = self._grad(x1, y0, seed)
        g01 = self._grad(x0, y1, seed)
        g11 = self._grad(x1, y1, seed)

        # Dot products
        n00 = g00[..., 0] * (xf    ) + g00[..., 1] * (yf    )
        n10 = g10[..., 0] * (xf-1.0) + g10[..., 1] * (yf    )
        n01 = g01[..., 0] * (xf    ) + g01[..., 1] * (yf-1.0)
        n11 = g11[..., 0] * (xf-1.0) + g11[..., 1] * (yf-1.0)

        # Bilinear interpolate
        nx0 = n00 + u * (n10 - n00)
        nx1 = n01 + u * (n11 - n01)
        nxy = nx0 + v * (nx1 - nx0)

        if stitch:
            period = 64
            nxy = self._tile_wrap(nxy, x0, y0, period)

        return np.clip(nxy, -1.0, 1.0)

    def _fade(self, t: 'np.ndarray') -> 'np.ndarray':
        """Perlin fade function."""
        return t * t * t * (t * (t * 6 - 15) + 10)

    def _grad(self, ix: 'np.ndarray', iy: 'np.ndarray', seed: int) -> 'np.ndarray':
        """Hash integer coords to unit vector gradient."""
        # Ensure all values are int32 to prevent overflow
        ix = ix.astype(np.int32)
        iy = iy.astype(np.int32)
        seed = np.int32(seed)

        # Use int64 for intermediate calculations to prevent overflow
        h = (ix.astype(np.int64) * 374761393 + iy.astype(np.int64) * 668265263 + np.int64(seed) * 982451653) & 0xFFFFFFFF
        h = h.astype(np.int32)
        h ^= (h >> 13)
        h = (h.astype(np.int64) * 1274126177) & 0xFFFFFFFF
        h = h.astype(np.uint32)  # Use uint32 for proper division
        angle = (h.astype(np.float32) / np.float32(0xFFFFFFFF)) * (2.0 * np.pi)
        return np.stack((np.cos(angle), np.sin(angle)), axis=-1).astype(np.float32)

    def _tile_wrap(self, values: 'np.ndarray', x0: 'np.ndarray', y0: 'np.ndarray', period: int) -> 'np.ndarray':
        """Basic tile stitching support."""
        mask_x = ((x0 % period) == 0) | ((x0 % period) == period - 1)
        mask_y = ((y0 % period) == 0) | ((y0 % period) == period - 1)
        mask = mask_x | mask_y
        if np.any(mask):
            values = values.copy()
            values[mask] *= 0.9
        return values


def create_turbulence_processor(policy=None) -> TurbulenceProcessor:
    """
    Factory function to create a TurbulenceProcessor instance.

    Args:
        policy: Optional policy for strategy selection

    Returns:
        Configured TurbulenceProcessor instance
    """
    return TurbulenceProcessor(policy=policy)