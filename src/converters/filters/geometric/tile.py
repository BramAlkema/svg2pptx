"""
feTile filter implementation with EMF-based pattern system.

Implements SVG feTile filter effects using EMF pattern generation for seamless
tiling in PowerPoint with a:blipFill/a:tile integration.
"""

import math
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Tuple, Optional, Dict, Any, List
from abc import ABC, abstractmethod

from src.converters.filters.core.base import Filter, FilterResult, FilterContext
from src.emf_tiles import get_tile_library, get_pattern_tile, create_colored_pattern
from src.emf_blob import EMFBlob, create_pattern_tile


@dataclass
class TileParameters:
    """Parameters for feTile filter operation."""
    tile_region: Tuple[float, float, float, float]  # (x, y, width, height)
    source_region: Tuple[float, float, float, float]  # (x, y, width, height)
    pattern_type: str = "auto"
    seamless: bool = True
    scaling_x: float = 1.0
    scaling_y: float = 1.0

    def __post_init__(self):
        """Validate parameters after creation."""
        x, y, width, height = self.tile_region
        if width <= 0:
            raise TileValidationError("Tile region width must be positive")
        if height <= 0:
            raise TileValidationError("Tile region height must be positive")


@dataclass
class TileResult:
    """Result of EMF tile creation."""
    emf_blob: bytes
    pattern_name: str
    is_seamless: bool
    scaling_x: float = 1.0
    scaling_y: float = 1.0
    offset_x: float = 0.0
    offset_y: float = 0.0


class TileException(Exception):
    """Base exception for tile operations."""
    pass


class TileValidationError(TileException, ValueError):
    """Exception for invalid tile parameters."""
    pass


class EMFTileProcessor:
    """EMF-based tile processor for complex patterns."""

    def process_tile(self, params: TileParameters, context: FilterContext) -> TileResult:
        """
        Process tile using EMF pattern generation.

        Args:
            params: Tile parameters
            context: Filter context with element and viewport info

        Returns:
            TileResult with EMF blob data and pattern information
        """
        # Determine pattern from parameters
        pattern_name = self._select_pattern(params)

        # Get or create EMF pattern
        emf_blob, actual_pattern_name = self._get_or_create_pattern(pattern_name, params)

        # Calculate scaling and positioning
        scaling_x, scaling_y = self._calculate_scaling(params)

        return TileResult(
            emf_blob=emf_blob,
            pattern_name=actual_pattern_name,  # Use the actual pattern name that was used
            is_seamless=params.seamless,
            scaling_x=scaling_x,
            scaling_y=scaling_y
        )

    def _select_pattern(self, params: TileParameters) -> str:
        """Select appropriate pattern based on parameters."""
        if params.pattern_type != "auto":
            return params.pattern_type

        # Auto-select based on tile characteristics
        tx, ty, tw, th = params.tile_region
        sx, sy, sw, sh = params.source_region

        # Simple heuristics for pattern selection
        aspect_ratio = tw / th
        source_ratio = sw / sh

        if abs(aspect_ratio - 1.0) < 0.1 and abs(source_ratio - 1.0) < 0.1:
            return "dots"
        elif tw > th * 2:
            return "hatch_horizontal"
        elif th > tw * 2:
            return "hatch_vertical"
        else:
            return "grid"

    def _get_or_create_pattern(self, pattern_name: str, params: TileParameters) -> Tuple[bytes, str]:
        """Get existing pattern or create custom one.

        Returns:
            Tuple of (emf_blob_data, actual_pattern_name_used)
        """
        # Try to get from library first
        tile_library = get_tile_library()
        pattern_tile = tile_library.get_tile(pattern_name)

        if pattern_tile:
            return pattern_tile.finalize(), pattern_name

        # Create custom pattern
        return self._create_custom_pattern(pattern_name, params)

    def _create_custom_pattern(self, pattern_name: str, params: TileParameters) -> Tuple[bytes, str]:
        """Create custom EMF pattern for unique requirements.

        Returns:
            Tuple of (emf_blob_data, actual_pattern_name_used)
        """
        try:
            # Use EMF blob creation for custom patterns
            emf_blob = create_pattern_tile(
                pattern_type=pattern_name,
                width=int(params.source_region[2]),
                height=int(params.source_region[3]),
                line_width=1,
                spacing=8
            )
            return emf_blob.finalize(), pattern_name
        except ValueError:
            # Fallback to grid pattern for unsupported types
            emf_blob = create_pattern_tile(
                pattern_type="grid",
                width=int(params.source_region[2]),
                height=int(params.source_region[3]),
                line_width=1,
                spacing=8
            )
            return emf_blob.finalize(), "grid"

    def _calculate_scaling(self, params: TileParameters) -> Tuple[float, float]:
        """Calculate scaling factors for tile."""
        # Use provided scaling factors directly with validation
        # Ensure minimum reasonable scaling values
        scale_x = max(0.1, min(10.0, params.scaling_x))  # Clamp between 0.1 and 10.0
        scale_y = max(0.1, min(10.0, params.scaling_y))  # Clamp between 0.1 and 10.0
        return scale_x, scale_y


class TileFilter(Filter):
    """
    feTile filter with EMF-based pattern system.

    Implements SVG feTile filter effects using EMF pattern generation for
    seamless tiling in PowerPoint with a:blipFill/a:tile integration.
    """

    def __init__(self):
        """Initialize the tile filter."""
        super().__init__("feTile")
        self._emf_processor = EMFTileProcessor()
        self._tile_library = get_tile_library()
        self._pattern_cache = {}

    def can_apply(self, element: ET.Element, context: FilterContext) -> bool:
        """
        Check if this filter can process the given element.

        Args:
            element: SVG filter element
            context: Filter processing context

        Returns:
            True if element is feTile with required attributes
        """
        if element.tag != "feTile":
            return False

        # Check for basic region attributes
        required_attrs = ['x', 'y', 'width', 'height']
        for attr in required_attrs:
            if element.get(attr) is None:
                return False

        return True

    def validate_parameters(self, element: ET.Element, context: FilterContext) -> bool:
        """
        Validate tile parameters.

        Args:
            element: SVG filter element
            context: Filter processing context

        Returns:
            True if parameters are valid
        """
        try:
            self._parse_parameters(element)
            return True
        except TileValidationError:
            return False

    def apply(self, element: ET.Element, context: FilterContext) -> FilterResult:
        """
        Apply tile filter using EMF-based pattern system.

        Args:
            element: SVG feTile element
            context: Filter processing context

        Returns:
            FilterResult with DrawingML content
        """
        try:
            # Parse and validate parameters
            params = self._parse_parameters(element)

            # Create EMF tile pattern
            tile_result = self._create_emf_tile(params, context)

            # Generate DrawingML with a:blipFill/a:tile
            drawingml = self._generate_blip_fill_tile_xml(tile_result, context)

            return FilterResult(
                success=True,
                drawingml=drawingml,
                metadata={
                    'filter_type': self.filter_type,
                    'approach': 'emf',
                    'pattern': tile_result.pattern_name,
                    'scaling_x': tile_result.scaling_x,
                    'scaling_y': tile_result.scaling_y,
                    'seamless': tile_result.is_seamless
                }
            )

        except TileValidationError as e:
            return FilterResult(
                success=False,
                error_message=str(e),
                metadata={'filter_type': self.filter_type, 'error': str(e)}
            )
        except Exception as e:
            return FilterResult(
                success=False,
                error_message=f"Tile filter processing failed: {str(e)}",
                metadata={'filter_type': self.filter_type, 'error': str(e)}
            )

    def _parse_parameters(self, element: ET.Element) -> TileParameters:
        """
        Parse feTile element attributes into parameters.

        Args:
            element: SVG feTile element

        Returns:
            TileParameters with parsed values

        Raises:
            TileValidationError: If parameters are invalid
        """
        try:
            # Parse required tile region
            x = float(element.get("x", "0"))
            y = float(element.get("y", "0"))
            width = float(element.get("width", "0"))
            height = float(element.get("height", "0"))
        except ValueError as e:
            raise TileValidationError(f"Invalid coordinate values: {e}")

        if width <= 0:
            raise TileValidationError("Width must be positive")
        if height <= 0:
            raise TileValidationError("Height must be positive")

        # Parse optional source region
        source_x = float(element.get("sourceX", "0"))
        source_y = float(element.get("sourceY", "0"))
        source_width = float(element.get("sourceWidth", str(width)))
        source_height = float(element.get("sourceHeight", str(height)))

        # Parse pattern type
        pattern_type = element.get("pattern", "auto")

        # Parse scaling
        scaling_x = float(element.get("scaleX", "1.0"))
        scaling_y = float(element.get("scaleY", "1.0"))

        # Parse seamless flag
        seamless = element.get("seamless", "true").lower() == "true"

        return TileParameters(
            tile_region=(x, y, width, height),
            source_region=(source_x, source_y, source_width, source_height),
            pattern_type=pattern_type,
            seamless=seamless,
            scaling_x=scaling_x,
            scaling_y=scaling_y
        )

    def _create_emf_tile(self, params: TileParameters, context: FilterContext) -> TileResult:
        """
        Create EMF tile pattern using processor.

        Args:
            params: Tile parameters
            context: Filter processing context

        Returns:
            TileResult with EMF pattern information
        """
        # Check cache first
        cache_key = self._generate_cache_key(params)
        if cache_key in self._pattern_cache:
            return self._pattern_cache[cache_key]

        # Create new tile pattern
        tile_result = self._emf_processor.process_tile(params, context)

        # Cache result
        self._pattern_cache[cache_key] = tile_result

        return tile_result

    def _generate_cache_key(self, params: TileParameters) -> str:
        """Generate cache key for tile parameters."""
        return f"{params.pattern_type}_{params.tile_region}_{params.source_region}_{params.scaling_x}_{params.scaling_y}"

    def _generate_blip_fill_tile_xml(self, tile_result: TileResult, context: FilterContext) -> str:
        """
        Generate DrawingML with a:blipFill and a:tile.

        Args:
            tile_result: EMF tile result
            context: Filter processing context

        Returns:
            DrawingML XML string with tile pattern
        """
        # Convert scaling to PowerPoint units (percentage * 1000)
        sx = int(tile_result.scaling_x * 100000)
        sy = int(tile_result.scaling_y * 100000)

        # Convert offsets to EMU
        tx = int(tile_result.offset_x * 12700) if hasattr(tile_result, 'offset_x') else 0
        ty = int(tile_result.offset_y * 12700) if hasattr(tile_result, 'offset_y') else 0

        # Generate unique embed ID for EMF
        embed_id = f"emf_tile_{tile_result.pattern_name}"

        return f'''<a:blipFill>
    <a:blip r:embed="{embed_id}">
        <a:extLst>
            <a:ext uri="{{28A0092B-C50C-407E-A947-70E740481C1C}}">
                <a14:useLocalDpi val="0"/>
            </a:ext>
        </a:extLst>
    </a:blip>
    <a:tile tx="{tx}" ty="{ty}" sx="{sx}" sy="{sy}" algn="tl" flip="none"/>
</a:blipFill>'''

    def _get_available_patterns(self) -> List[str]:
        """Get list of available EMF patterns."""
        return [
            "hatch_horizontal",
            "hatch_vertical",
            "hatch_diagonal",
            "crosshatch",
            "dots",
            "grid",
            "brick",
            "auto"
        ]

    def _calculate_optimal_density(self, width: float, height: float, pattern_type: str) -> float:
        """
        Calculate optimal pattern density based on region size.

        Args:
            width: Region width
            height: Region height
            pattern_type: Type of pattern

        Returns:
            Density value between 0.0 and 1.0
        """
        # Base density calculation
        area = width * height

        # Adjust density based on pattern type and area
        if pattern_type in ["dots", "grid"]:
            # Dot patterns need lower density for larger areas
            density = min(1.0, 1000.0 / area)
        elif pattern_type.startswith("hatch"):
            # Hatch patterns can handle higher density
            density = min(1.0, 2000.0 / area)
        else:
            # Default density calculation
            density = min(1.0, 1500.0 / area)

        return max(0.1, density)  # Minimum 0.1 density

    def _calculate_scaling_factors(self, tile_size: Tuple[float, float],
                                  source_size: Tuple[float, float]) -> Tuple[float, float]:
        """
        Calculate scaling factors for tile based on sizes.

        Args:
            tile_size: (width, height) of tile region
            source_size: (width, height) of source region

        Returns:
            Tuple of (scale_x, scale_y)
        """
        tile_width, tile_height = tile_size
        source_width, source_height = source_size

        if source_width == 0 or source_height == 0:
            return 1.0, 1.0

        scale_x = tile_width / source_width
        scale_y = tile_height / source_height

        return scale_x, scale_y

    def _optimize_tile_size(self, width: float, height: float) -> Tuple[float, float]:
        """
        Optimize tile size for performance.

        Args:
            width: Requested width
            height: Requested height

        Returns:
            Optimized (width, height)
        """
        # Round up to nearest multiple of 8 for efficiency
        optimized_width = math.ceil(width / 8) * 8
        optimized_height = math.ceil(height / 8) * 8

        return optimized_width, optimized_height

    def _calculate_adaptive_scaling(self, pattern_type: str, density: float,
                                   region_size: Tuple[float, float]) -> float:
        """
        Calculate adaptive scaling based on pattern density.

        Args:
            pattern_type: Type of pattern
            density: Pattern density (0.0 to 1.0)
            region_size: (width, height) of region

        Returns:
            Adaptive scaling factor
        """
        base_scale = 1.0

        # Adjust based on density
        if density > 0.7:
            # High density - use smaller scale
            base_scale *= 0.7
        elif density < 0.3:
            # Low density - use larger scale
            base_scale *= 1.5

        # Adjust based on pattern type
        if pattern_type == "dots":
            base_scale *= 0.8  # Dots look better slightly smaller
        elif pattern_type.startswith("hatch"):
            base_scale *= 1.2  # Hatches can be a bit larger

        return base_scale

    def _should_use_cached_pattern(self, params1: TileParameters,
                                  params2: TileParameters) -> bool:
        """Check if cached pattern can be reused."""
        return (params1.pattern_type == params2.pattern_type and
                params1.tile_region == params2.tile_region and
                params1.source_region == params2.source_region and
                params1.scaling_x == params2.scaling_x and
                params1.scaling_y == params2.scaling_y)

    def _optimize_for_memory(self, tile_region: Tuple[float, float, float, float],
                           source_region: Tuple[float, float, float, float]) -> TileParameters:
        """
        Optimize tile parameters for memory efficiency.

        Args:
            tile_region: Tile region coordinates
            source_region: Source region coordinates

        Returns:
            Optimized TileParameters
        """
        tx, ty, tw, th = tile_region
        sx, sy, sw, sh = source_region

        # Limit tile size to reasonable maximums
        max_size = 512
        if tw > max_size:
            tw = max_size
        if th > max_size:
            th = max_size

        return TileParameters(
            tile_region=(tx, ty, tw, th),
            source_region=source_region
        )

    def _create_custom_pattern(self, source_data: bytes) -> Optional[TileResult]:
        """Create custom pattern from source data."""
        try:
            # This would process source data to create custom EMF pattern
            # For now, return a placeholder
            return TileResult(
                emf_blob=source_data,
                pattern_name="custom",
                is_seamless=True
            )
        except Exception:
            return None

    def _get_pattern_with_fallback(self, pattern_name: str, source_data: bytes) -> TileResult:
        """Get pattern with fallback to standard patterns."""
        # Try custom pattern first
        custom_result = self._create_custom_pattern(source_data)
        if custom_result:
            return custom_result

        # Fallback to standard pattern
        fallback_pattern = "grid"  # Safe default
        emf_blob = self._emf_processor._get_or_create_pattern(
            fallback_pattern,
            TileParameters(
                tile_region=(0, 0, 100, 100),
                source_region=(0, 0, 25, 25),
                pattern_type=fallback_pattern
            )
        )

        return TileResult(
            emf_blob=emf_blob,
            pattern_name=fallback_pattern,
            is_seamless=True
        )