#!/usr/bin/env python3
"""
SVG feTile Filter Processor

Implements SVG feTile filter effects using PowerPoint's native tiling capabilities
with a:blipFill/a:tile DrawingML elements for seamless pattern generation.

This processor uses a policy-driven approach to select the best implementation
strategy for different tile requirements:
- NATIVE: PowerPoint's a:tile with pattern generation
- APPROXIMATION: Basic pattern fills
- EMF_RASTERIZE: Complex custom patterns
"""

import math
from dataclasses import dataclass, field
from typing import Tuple, Optional, Dict, Any, List
from lxml import etree as ET

from .base import (
    FilterProcessor,
    FilterContext,
    FilterResult,
    FilterStrategy,
    FilterException,
    FilterValidationError
)


class TileFilterException(FilterException):
    """Exception raised during tile filter processing."""
    pass


class TileValidationError(FilterValidationError, TileFilterException):
    """Exception raised for invalid tile parameters."""
    pass


@dataclass
class TileParameters:
    """Parameters for SVG feTile filter processing."""

    # Core tile attributes
    tile_x: float = 0.0
    tile_y: float = 0.0
    tile_width: float = 100.0
    tile_height: float = 100.0

    # Source region
    source_x: float = 0.0
    source_y: float = 0.0
    source_width: float = 100.0
    source_height: float = 100.0

    # Pattern properties
    pattern_type: str = "auto"
    seamless: bool = True
    scaling_x: float = 1.0
    scaling_y: float = 1.0

    # Input/output
    input_source: str = "SourceGraphic"
    result_name: Optional[str] = None

    def __post_init__(self):
        """Validate parameters after initialization."""
        if self.tile_width <= 0:
            raise TileValidationError("Tile width must be positive")
        if self.tile_height <= 0:
            raise TileValidationError("Tile height must be positive")
        if self.source_width <= 0:
            raise TileValidationError("Source width must be positive")
        if self.source_height <= 0:
            raise TileValidationError("Source height must be positive")

        # Clamp scaling factors to reasonable range
        self.scaling_x = max(0.1, min(10.0, self.scaling_x))
        self.scaling_y = max(0.1, min(10.0, self.scaling_y))

    def get_complexity_score(self) -> float:
        """Calculate complexity score for strategy selection."""
        base_score = 0.0

        # Size complexity
        total_area = self.tile_width * self.tile_height
        if total_area > 10000:  # Large tiles are more complex
            base_score += 0.3

        # Pattern complexity
        if self.pattern_type not in ["auto", "grid", "dots"]:
            base_score += 0.2

        # Scaling complexity
        if abs(self.scaling_x - 1.0) > 0.1 or abs(self.scaling_y - 1.0) > 0.1:
            base_score += 0.2

        # Seamless requirement
        if self.seamless:
            base_score += 0.1

        return min(1.0, base_score)

    def get_aspect_ratio(self) -> float:
        """Get tile aspect ratio."""
        return self.tile_width / self.tile_height if self.tile_height > 0 else 1.0

    def get_scaling_ratio(self) -> float:
        """Get the overall scaling ratio."""
        return (self.scaling_x + self.scaling_y) / 2.0

    def get_pattern_density(self) -> float:
        """Calculate pattern density for optimization."""
        area = self.tile_width * self.tile_height

        if self.pattern_type in ["dots", "grid"]:
            return min(1.0, 1000.0 / area)
        elif "hatch" in self.pattern_type:
            return min(1.0, 2000.0 / area)
        else:
            return min(1.0, 1500.0 / area)


class TileProcessor(FilterProcessor):
    """Processor for SVG feTile filter effects."""

    def __init__(self, policy=None):
        super().__init__(filter_type='feTile', policy=policy)
        self.max_tile_size = 512  # Maximum tile size for performance
        self.pattern_cache = {}

    def can_apply(self, element: ET.Element, context: FilterContext) -> bool:
        """Check if this processor can handle the given element."""
        if element.tag != "feTile":
            return False

        # Check for basic required attributes
        try:
            self._parse_parameters(element, context)
            return True
        except (TileValidationError, ValueError):
            return False

    def apply(self, element: ET.Element, context: FilterContext) -> FilterResult:
        """Apply feTile filter with strategy selection."""
        try:
            # Parse parameters
            params = self._parse_parameters(element, context)

            # Select strategy based on complexity
            strategy = self._select_strategy(params, context)

            # Apply selected strategy
            if strategy == FilterStrategy.NATIVE:
                return self._apply_native_strategy(params, context)
            elif strategy == FilterStrategy.APPROXIMATION:
                return self._apply_approximation_strategy(params, context)
            else:  # EMF_RASTERIZE
                return self._apply_emf_strategy(params, context)

        except TileValidationError as e:
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
                error_message=f"Tile filter processing failed: {str(e)}",
                metadata={'filter_type': self.filter_type, 'error': str(e)}
            )

    def _parse_parameters(self, element: ET.Element, context: FilterContext) -> TileParameters:
        """Parse feTile element attributes."""
        try:
            # Core tile region
            tile_x = float(element.get("x", "0"))
            tile_y = float(element.get("y", "0"))
            tile_width = float(element.get("width", "100"))
            tile_height = float(element.get("height", "100"))

            # Source region (defaults to tile region)
            source_x = float(element.get("sourceX", str(tile_x)))
            source_y = float(element.get("sourceY", str(tile_y)))
            source_width = float(element.get("sourceWidth", str(tile_width)))
            source_height = float(element.get("sourceHeight", str(tile_height)))

            # Pattern properties
            pattern_type = element.get("pattern", "auto")
            seamless = element.get("seamless", "true").lower() == "true"
            scaling_x = float(element.get("scaleX", "1.0"))
            scaling_y = float(element.get("scaleY", "1.0"))

            # Input/output
            input_source = element.get("in", "SourceGraphic")
            result_name = element.get("result")

            return TileParameters(
                tile_x=tile_x,
                tile_y=tile_y,
                tile_width=tile_width,
                tile_height=tile_height,
                source_x=source_x,
                source_y=source_y,
                source_width=source_width,
                source_height=source_height,
                pattern_type=pattern_type,
                seamless=seamless,
                scaling_x=scaling_x,
                scaling_y=scaling_y,
                input_source=input_source,
                result_name=result_name
            )

        except ValueError as e:
            raise TileValidationError(f"Invalid tile parameters: {e}")

    def _select_strategy(self, params: TileParameters, context: FilterContext) -> FilterStrategy:
        """Select processing strategy based on complexity and capabilities."""
        complexity = params.get_complexity_score()

        # Simple patterns can use native PowerPoint tiling
        if complexity < 0.3 and params.pattern_type in ["auto", "grid", "dots"]:
            return FilterStrategy.NATIVE

        # Medium complexity uses approximation
        if complexity < 0.7:
            return FilterStrategy.APPROXIMATION

        # Complex patterns need EMF rasterization
        return FilterStrategy.EMF_RASTERIZE

    def _apply_native_strategy(self, params: TileParameters, context: FilterContext) -> FilterResult:
        """Apply tile using PowerPoint's native a:tile capabilities."""
        try:
            # Generate pattern type
            pattern_name = self._select_pattern_type(params)

            # Create native PowerPoint tile XML
            drawingml = self._generate_native_tile_xml(params, pattern_name, context)

            return FilterResult(
                success=True,
                strategy=FilterStrategy.NATIVE,
                drawingml=drawingml,
                metadata={
                    'filter_type': self.filter_type,
                    'pattern': pattern_name,
                    'scaling_x': params.scaling_x,
                    'scaling_y': params.scaling_y,
                    'seamless': params.seamless,
                    'tile_size': f"{params.tile_width}x{params.tile_height}"
                }
            )

        except Exception as e:
            raise TileFilterException(f"Native tile strategy failed: {e}")

    def _apply_approximation_strategy(self, params: TileParameters, context: FilterContext) -> FilterResult:
        """Apply tile using pattern approximation."""
        try:
            # Use basic pattern fills as approximation
            pattern_type = self._select_pattern_type(params)
            drawingml = self._generate_pattern_fill_xml(params, pattern_type, context)

            return FilterResult(
                success=True,
                strategy=FilterStrategy.APPROXIMATION,
                drawingml=drawingml,
                metadata={
                    'filter_type': self.filter_type,
                    'approach': 'pattern_approximation',
                    'pattern': pattern_type,
                    'scaling_x': params.scaling_x,
                    'scaling_y': params.scaling_y,
                    'seamless': params.seamless
                }
            )

        except Exception as e:
            raise TileFilterException(f"Approximation strategy failed: {e}")

    def _apply_emf_strategy(self, params: TileParameters, context: FilterContext) -> FilterResult:
        """Apply tile using EMF rasterization for complex patterns."""
        try:
            # Generate EMF-based pattern
            pattern_name = self._select_pattern_type(params)
            emf_reference = f"emf_tile_{pattern_name}_{id(params)}"

            # Create EMF tile XML
            drawingml = self._generate_emf_tile_xml(params, emf_reference, context)

            return FilterResult(
                success=True,
                strategy=FilterStrategy.EMF_RASTERIZE,
                drawingml=drawingml,
                metadata={
                    'filter_type': self.filter_type,
                    'approach': 'emf_rasterization',
                    'pattern': pattern_name,
                    'emf_reference': emf_reference,
                    'scaling_x': params.scaling_x,
                    'scaling_y': params.scaling_y,
                    'seamless': params.seamless
                }
            )

        except Exception as e:
            raise TileFilterException(f"EMF strategy failed: {e}")

    def _select_pattern_type(self, params: TileParameters) -> str:
        """Select appropriate pattern type based on parameters."""
        if params.pattern_type != "auto":
            return params.pattern_type

        # Auto-select based on tile characteristics
        aspect_ratio = params.get_aspect_ratio()

        if abs(aspect_ratio - 1.0) < 0.1:
            return "dots"
        elif aspect_ratio > 2.0:
            return "hatch_horizontal"
        elif aspect_ratio < 0.5:
            return "hatch_vertical"
        else:
            return "grid"

    def _generate_native_tile_xml(self, params: TileParameters, pattern_name: str, context: FilterContext) -> str:
        """Generate native PowerPoint tile DrawingML."""
        # Convert to PowerPoint units
        sx = int(params.scaling_x * 100000)  # Percentage * 1000
        sy = int(params.scaling_y * 100000)

        # Calculate offsets in EMU
        tx = int(params.tile_x * 12700)
        ty = int(params.tile_y * 12700)

        # Generate pattern-specific fill
        if pattern_name == "dots":
            pattern_fill = self._generate_dot_pattern_fill()
        elif pattern_name.startswith("hatch"):
            pattern_fill = self._generate_hatch_pattern_fill(pattern_name)
        else:  # grid
            pattern_fill = self._generate_grid_pattern_fill()

        return f'''<a:blipFill>
    {pattern_fill}
    <a:tile tx="{tx}" ty="{ty}" sx="{sx}" sy="{sy}" algn="tl" flip="none"/>
</a:blipFill>'''

    def _generate_pattern_fill_xml(self, params: TileParameters, pattern_type: str, context: FilterContext) -> str:
        """Generate pattern fill approximation."""
        # Use PowerPoint's built-in patterns
        if pattern_type == "dots":
            return '''<a:pattFill prst="dotGrid">
    <a:fgClr><a:schemeClr val="tx1"/></a:fgClr>
    <a:bgClr><a:schemeClr val="bg1"/></a:bgClr>
</a:pattFill>'''
        elif pattern_type in ["hatch_horizontal", "hatch_vertical"]:
            direction = "horz" if pattern_type == "hatch_horizontal" else "vert"
            return f'''<a:pattFill prst="{direction}">
    <a:fgClr><a:schemeClr val="tx1"/></a:fgClr>
    <a:bgClr><a:schemeClr val="bg1"/></a:bgClr>
</a:pattFill>'''
        else:  # grid
            return '''<a:pattFill prst="grid">
    <a:fgClr><a:schemeClr val="tx1"/></a:fgClr>
    <a:bgClr><a:schemeClr val="bg1"/></a:bgClr>
</a:pattFill>'''

    def _generate_emf_tile_xml(self, params: TileParameters, emf_reference: str, context: FilterContext) -> str:
        """Generate EMF-based tile DrawingML."""
        # Convert scaling to PowerPoint units
        sx = int(params.scaling_x * 100000)
        sy = int(params.scaling_y * 100000)

        # Convert offsets to EMU
        tx = int(params.tile_x * 12700)
        ty = int(params.tile_y * 12700)

        return f'''<a:blipFill>
    <a:blip r:embed="{emf_reference}">
        <a:extLst>
            <a:ext uri="{{28A0092B-C50C-407E-A947-70E740481C1C}}">
                <a14:useLocalDpi val="0"/>
            </a:ext>
        </a:extLst>
    </a:blip>
    <a:tile tx="{tx}" ty="{ty}" sx="{sx}" sy="{sy}" algn="tl" flip="none"/>
</a:blipFill>'''

    def _generate_dot_pattern_fill(self) -> str:
        """Generate dot pattern blip fill."""
        return '''<a:blip r:embed="dotPattern">
    <a:lum bright="0" contrast="0"/>
</a:blip>'''

    def _generate_hatch_pattern_fill(self, hatch_type: str) -> str:
        """Generate hatch pattern blip fill."""
        pattern_ref = "hatchHorizontal" if hatch_type == "hatch_horizontal" else "hatchVertical"
        return f'''<a:blip r:embed="{pattern_ref}">
    <a:lum bright="0" contrast="0"/>
</a:blip>'''

    def _generate_grid_pattern_fill(self) -> str:
        """Generate grid pattern blip fill."""
        return '''<a:blip r:embed="gridPattern">
    <a:lum bright="0" contrast="0"/>
</a:blip>'''

    def _optimize_tile_size(self, width: float, height: float) -> Tuple[float, float]:
        """Optimize tile size for performance."""
        # Round to multiples of 8 for efficiency
        optimized_width = math.ceil(width / 8) * 8
        optimized_height = math.ceil(height / 8) * 8

        # Cap at maximum size
        optimized_width = min(optimized_width, self.max_tile_size)
        optimized_height = min(optimized_height, self.max_tile_size)

        return optimized_width, optimized_height

    def _get_available_patterns(self) -> List[str]:
        """Get list of available tile patterns."""
        return [
            "auto",
            "grid",
            "dots",
            "hatch_horizontal",
            "hatch_vertical",
            "hatch_diagonal",
            "crosshatch",
            "brick"
        ]


def create_tile_processor(policy=None) -> TileProcessor:
    """
    Factory function to create a TileProcessor instance.

    Args:
        policy: Optional policy for strategy selection

    Returns:
        Configured TileProcessor instance
    """
    return TileProcessor(policy=policy)