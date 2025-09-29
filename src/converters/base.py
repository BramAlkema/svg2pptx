#!/usr/bin/env python3
"""
Base converter classes and registry for SVG to DrawingML conversion.

This module provides the foundation for a modular converter architecture
where each SVG element type has its own specialized converter.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Optional, Any, Type, TYPE_CHECKING
from lxml import etree as ET
import logging
import re
import time
import math

# Import services for dependency injection
try:
    from ..services.conversion_services import ConversionServices, ConversionConfig
except ImportError:
    # Fallback for test environments
    from src.services.conversion_services import ConversionServices, ConversionConfig

# Import fluent API for unit conversions
try:
    from ..units import unit, units
except ImportError:
    # Fallback for test environments
    from src.units import unit, units

# Import types for type hints only
if TYPE_CHECKING:
    try:
        from ..units import UnitConverter
        from ..color import Color
        from ..transforms import Transform
        from ..viewbox import ViewportEngine
    except ImportError:
        from src.units import UnitConverter
        from src.color import Color
        from src.transforms import Transform
        from src.viewbox import ViewportEngine

logger = logging.getLogger(__name__)


class CoordinateSystem:
    """Manages coordinate transformations between SVG and DrawingML with SVG-compliant alignment."""

    def __init__(self, viewbox: Tuple[float, float, float, float],
                 slide_width: Optional[float] = None,
                 slide_height: Optional[float] = None,
                 preserve_aspect_ratio: bool = True,
                 align: str = "xMidYMid"):
        """
        Initialize coordinate system with SVG preserveAspectRatio support.

        Args:
            viewbox: SVG viewBox (x, y, width, height)
            slide_width: PowerPoint slide width in EMUs (defaults to standard 10" slide)
            slide_height: PowerPoint slide height in EMUs (defaults to standard 7.5" slide)
            preserve_aspect_ratio: Whether to preserve aspect ratio (SVG 'meet' behavior)
            align: SVG alignment mode - one of 9 modes:
                   xMinYMin, xMidYMin, xMaxYMin,
                   xMinYMid, xMidYMid, xMaxYMid,
                   xMinYMax, xMidYMax, xMaxYMax
        """
        # Import slide constants from units module
        try:
            from ..units.core import SLIDE_WIDTH_EMU, SLIDE_HEIGHT_EMU
        except ImportError:
            # Fallback for test environments
            from src.units.core import SLIDE_WIDTH_EMU, SLIDE_HEIGHT_EMU

        self.viewbox = viewbox
        self.slide_width = slide_width if slide_width is not None else SLIDE_WIDTH_EMU
        self.slide_height = slide_height if slide_height is not None else SLIDE_HEIGHT_EMU
        self.preserve_aspect_ratio = preserve_aspect_ratio
        self.align = align or "xMidYMid"

        # Extract SVG dimensions from viewbox for compatibility
        self.svg_width = viewbox[2]
        self.svg_height = viewbox[3]

        # Calculate scaling factors
        self.scale_x = self.slide_width / viewbox[2] if viewbox[2] > 0 else 1
        self.scale_y = self.slide_height / viewbox[3] if viewbox[3] > 0 else 1

        if self.preserve_aspect_ratio:
            # Uniform scaling (SVG 'meet' behavior)
            self.scale = min(self.scale_x, self.scale_y)
            self.scale_x = self.scale_y = self.scale
            # Calculate alignment offsets
            self.offset_x, self.offset_y = self._compute_alignment_offsets()
        else:
            # Non-uniform scaling (SVG 'none' behavior - stretch to fit)
            self.offset_x = 0.0
            self.offset_y = 0.0

    def _compute_alignment_offsets(self) -> Tuple[float, float]:
        """
        Compute alignment offsets for SVG-compliant positioning.

        Supports all 9 SVG alignment modes:
        - X alignment: xMin (left), xMid (center), xMax (right)
        - Y alignment: YMin (top), YMid (middle), YMax (bottom)

        Returns:
            Tuple of (offset_x, offset_y) in EMU units
        """
        # Calculate scaled dimensions
        scaled_width = self.viewbox[2] * self.scale
        scaled_height = self.viewbox[3] * self.scale

        # Available space for alignment
        extra_width = self.slide_width - scaled_width
        extra_height = self.slide_height - scaled_height

        # Horizontal alignment
        if self.align.startswith("xMin"):
            offset_x = 0.0
        elif self.align.startswith("xMax"):
            offset_x = extra_width
        else:  # xMid (default)
            offset_x = extra_width / 2.0

        # Vertical alignment
        if self.align.endswith("YMin"):
            offset_y = 0.0
        elif self.align.endswith("YMax"):
            offset_y = extra_height
        else:  # YMid (default)
            offset_y = extra_height / 2.0

        return offset_x, offset_y
    
    def svg_to_emu(self, x: float, y: float) -> Tuple[int, int]:
        """Convert SVG coordinates to EMUs."""
        # Adjust for viewbox offset
        x -= self.viewbox[0]
        y -= self.viewbox[1]
        
        # Scale and add centering offset
        emu_x = int(x * self.scale_x + self.offset_x)
        emu_y = int(y * self.scale_y + self.offset_y)
        
        return emu_x, emu_y
    
    def svg_length_to_emu(self, length: float, axis: str = 'x') -> int:
        """Convert SVG length to EMU."""
        scale = self.scale_x if axis == 'x' else self.scale_y
        return int(length * scale)
    


class ConversionContext:
    """Context object passed through the conversion pipeline.

    ✅ FIXED: ConversionContext.viewport_context now populated from SVG metadata
    =========================================================================
    IMPLEMENTATION: ConversionContext._create_viewport_context extracts viewBox
    and dimensions from svg_root during __init__ and creates proper viewport_context
    with SVG's actual dimensions. Falls back to 800×600 default when no metadata available.
    """

    def __init__(self, svg_root: Optional[ET.Element] = None, services: ConversionServices = None,
                 parent_ctm: Optional['numpy.ndarray'] = None, viewport_matrix: Optional['numpy.ndarray'] = None,
                 parent_style: Optional[Dict[str, str]] = None):
        """Initialize ConversionContext with CTM and CSS style support.

        Args:
            svg_root: Optional SVG root element
            services: ConversionServices instance (auto-created if None for backward compatibility)
            parent_ctm: Parent element's Current Transformation Matrix (3x3 numpy array)
            viewport_matrix: Root viewport transformation matrix (3x3 numpy array)
            parent_style: Parent element's computed CSS style for inheritance
        """
        # Backward compatibility: auto-create services if not provided
        if services is None:
            from ..services.conversion_services import ConversionServices
            services = ConversionServices.create_default(svg_root=svg_root)
            # Issue deprecation warning
            import warnings
            warnings.warn(
                "ConversionContext created without explicit ConversionServices. "
                "This usage is deprecated and will be removed in future versions. "
                "Please provide ConversionServices explicitly.",
                DeprecationWarning,
                stacklevel=2
            )

        self.coordinate_system: Optional[CoordinateSystem] = None
        self.gradients: Dict[str, Dict] = {}
        self.patterns: Dict[str, Dict] = {}
        self.clips: Dict[str, Any] = {}
        self.fonts: Dict[str, Dict] = {}
        self.shape_id_counter: int = 1000
        self.group_stack: List[Dict] = []
        self.current_transform: Optional[str] = None
        self.style_stack: List[Dict] = []
        self.svg_root = svg_root

        # Use services for all service access
        self.services = services

        # CSS style inheritance
        self.parent_style = parent_style or {}

        # Initialize viewport context from SVG metadata
        self.viewport_context = self._create_viewport_context(svg_root)

        # Initialize coordinate system from services or SVG metadata
        if hasattr(services, 'coordinate_system') and services.coordinate_system is not None:
            # Use coordinate system from services (includes proper viewport mapping)
            self.coordinate_system = services.coordinate_system
        else:
            # Fallback to creating coordinate system from SVG metadata
            self.coordinate_system = self._create_coordinate_system(svg_root)

        # Initialize CTM (Current Transformation Matrix) support
        self.parent_ctm = parent_ctm
        self.viewport_matrix = viewport_matrix
        self.element_ctm: Optional['numpy.ndarray'] = None

        # Calculate element CTM if we have the necessary components
        if svg_root is not None and viewport_matrix is not None:
            try:
                from ..transforms.matrix_composer import element_ctm
                self.element_ctm = element_ctm(svg_root, parent_ctm, viewport_matrix)
            except ImportError:
                # Transforms module not available, use fallback
                self.element_ctm = None

        # Initialize converter registry for nested conversions
        self.converter_registry: Optional[ConverterRegistry] = None

        # Initialize filter processing components
        self._filter_processors: Dict[str, Any] = {}
        self._filter_cache: Dict[str, Any] = {}
        self._filter_context_stack: List[Dict] = []

    def set_filter_processor(self, processor_name: str, processor: Any):
        """Register a filter processor component."""
        self._filter_processors[processor_name] = processor

    def get_filter_processor(self, processor_name: str) -> Optional[Any]:
        """Get a registered filter processor component."""
        return self._filter_processors.get(processor_name)

    def push_filter_context(self, filter_info: Dict):
        """Push filter context onto the stack for nested processing."""
        self._filter_context_stack.append(filter_info)

    def pop_filter_context(self) -> Optional[Dict]:
        """Pop filter context from the stack."""
        return self._filter_context_stack.pop() if self._filter_context_stack else None

    def get_current_filter_context(self) -> Optional[Dict]:
        """Get the current filter context without popping."""
        return self._filter_context_stack[-1] if self._filter_context_stack else None

    def get_filter_context_depth(self) -> int:
        """Get the current depth of filter context nesting."""
        return len(self._filter_context_stack)

    def clear_filter_context_stack(self):
        """Clear all filter contexts (for cleanup)."""
        self._filter_context_stack.clear()

    def get_filter_cache_stats(self) -> Dict[str, Any]:
        """Get filter cache statistics for debugging."""
        return {
            'cache_size': len(self._filter_cache),
            'context_stack_depth': len(self._filter_context_stack),
            'processor_count': len(self._filter_processors),
            'cached_keys': list(self._filter_cache.keys()) if len(self._filter_cache) < 10 else f"{len(self._filter_cache)} keys"
        }

    def add_filter_debug_info(self, key: str, value: Any):
        """Add debugging information about filter processing."""
        if 'debug_info' not in self._filter_cache:
            self._filter_cache['debug_info'] = {}
        self._filter_cache['debug_info'][key] = value

    def get_filter_debug_info(self) -> Dict[str, Any]:
        """Get all filter debugging information."""
        return self._filter_cache.get('debug_info', {})
        
    def get_next_shape_id(self) -> int:
        """Get the next available shape ID."""
        shape_id = self.shape_id_counter
        self.shape_id_counter += 1
        return shape_id
    
    def push_group(self, attributes: Dict):
        """Push group attributes onto the stack."""
        self.group_stack.append(attributes)
        
    def pop_group(self):
        """Pop group attributes from the stack."""
        if self.group_stack:
            self.group_stack.pop()
    
    def get_inherited_style(self) -> Dict:
        """Get merged style from parent groups."""
        merged = {}
        for group in self.group_stack:
            merged.update(group)
        return merged
    
    def _get_fluent_context_kwargs(self) -> Dict[str, Any]:
        """Extract viewport context attributes for fluent API context."""
        context_kwargs = {}
        if self.viewport_context:
            for attr in ['dpi', 'font_size', 'width', 'height', 'parent_width', 'parent_height']:
                if hasattr(self.viewport_context, attr):
                    value = getattr(self.viewport_context, attr)
                    if value is not None:
                        context_kwargs[attr] = value
        return context_kwargs

    def to_emu(self, value, axis: str = 'x') -> int:
        """Convert SVG length to EMUs using the context's unit converter with fluent API."""
        unit_value = unit(value, self.services.unit_converter)
        context_kwargs = self._get_fluent_context_kwargs()
        if context_kwargs:
            unit_value = unit_value.with_context(**context_kwargs)
        return unit_value.to_emu(axis)

    def to_pixels(self, value, axis: str = 'x') -> float:
        """Convert SVG length to pixels using the context's unit converter with fluent API."""
        unit_value = unit(value, self.services.unit_converter)
        context_kwargs = self._get_fluent_context_kwargs()
        if context_kwargs:
            unit_value = unit_value.with_context(**context_kwargs)
        return unit_value.to_pixels(axis)

    def batch_convert_to_emu(self, values: Dict[str, Any]) -> Dict[str, int]:
        """Convert multiple SVG lengths to EMUs in one call using fluent API."""
        batch_converter = units(values, self.services.unit_converter)
        context_kwargs = self._get_fluent_context_kwargs()
        if context_kwargs:
            batch_converter = batch_converter.with_context(**context_kwargs)
        return batch_converter.to_emu()
    
    def update_viewport_context(self, **kwargs):
        """Update viewport context parameters."""
        for key, value in kwargs.items():
            if hasattr(self.viewport_context, key):
                setattr(self.viewport_context, key, value)

    def _create_viewport_context(self, svg_root: Optional[ET.Element]):
        """
        Create viewport context from SVG root element metadata.

        Extracts viewBox and dimensions from SVG to create proper viewport context
        for percentage and relative unit resolution.

        Args:
            svg_root: Optional SVG root element

        Returns:
            ConversionContext for viewport operations, or None if no SVG provided
        """
        if svg_root is None:
            return None

        # Extract viewport dimensions from SVG
        width, height = self._extract_svg_dimensions(svg_root)

        # Create viewport context using the unit converter service
        return self.services.unit_converter.create_context(
            width=width,
            height=height,
            dpi=96.0,  # Standard web DPI
            font_size=16.0  # Default font size
        )

    def _create_coordinate_system(self, svg_root: Optional[ET.Element]) -> Optional[CoordinateSystem]:
        """
        Create coordinate system from SVG root element with preserveAspectRatio support.

        Args:
            svg_root: Optional SVG root element

        Returns:
            CoordinateSystem instance or None if no SVG provided
        """
        if svg_root is None:
            return None

        # Extract SVG dimensions and viewBox
        width, height = self._extract_svg_dimensions(svg_root)

        # Try to extract viewBox, fallback to dimensions
        viewbox_attr = svg_root.get('viewBox')
        if viewbox_attr:
            try:
                viewbox_parts = viewbox_attr.strip().split()
                if len(viewbox_parts) == 4:
                    viewbox = tuple(float(x) for x in viewbox_parts)
                else:
                    viewbox = (0, 0, width, height)
            except (ValueError, AttributeError):
                viewbox = (0, 0, width, height)
        else:
            viewbox = (0, 0, width, height)

        # Parse preserveAspectRatio attribute (SVG 'meet|slice|none' + alignment)
        preserve_aspect_ratio_attr = (svg_root.get('preserveAspectRatio') or '').strip()
        if not preserve_aspect_ratio_attr:
            # Default to SVG specification default
            preserve_aspect_ratio_attr = 'xMidYMid meet'

        preserve_aspect_ratio, align = self._parse_preserve_aspect_ratio(preserve_aspect_ratio_attr)

        logger.debug(f"SVG preserveAspectRatio: '{preserve_aspect_ratio_attr}' -> "
                    f"preserve={preserve_aspect_ratio}, align='{align}'")

        # Create and return coordinate system with SVG-compliant parameters
        return CoordinateSystem(viewbox,
                              preserve_aspect_ratio=preserve_aspect_ratio,
                              align=align)

    def _parse_preserve_aspect_ratio(self, preserve_aspect_ratio_attr: str) -> Tuple[bool, str]:
        """
        Parse SVG preserveAspectRatio attribute.

        Format: [<align>] [meet | slice | none]
        - align: xMinYMin | xMidYMin | xMaxYMin | xMinYMid | xMidYMid | xMaxYMid |
                 xMinYMax | xMidYMax | xMaxYMax
        - meet: preserve aspect ratio, scale to fit entirely (default)
        - slice: preserve aspect ratio, scale to fill entirely (crop if needed)
        - none: do not preserve aspect ratio (stretch to fit)

        Args:
            preserve_aspect_ratio_attr: The preserveAspectRatio attribute value

        Returns:
            Tuple of (preserve_aspect_ratio: bool, align: str)
        """
        if preserve_aspect_ratio_attr.lower() == 'none':
            return False, 'xMidYMid'

        # Split into components
        parts = preserve_aspect_ratio_attr.split()

        # Extract alignment (first part if it looks like an alignment, otherwise default)
        align = 'xMidYMid'  # SVG default
        meet_or_slice = 'meet'  # SVG default

        for part in parts:
            part = part.strip()
            if part in ('xMinYMin', 'xMidYMin', 'xMaxYMin',
                       'xMinYMid', 'xMidYMid', 'xMaxYMid',
                       'xMinYMax', 'xMidYMax', 'xMaxYMax'):
                align = part
            elif part.lower() in ('meet', 'slice', 'none'):
                meet_or_slice = part.lower()

        # For now, we only support 'meet' and 'none' behaviors
        # 'slice' would require cropping support which is more complex
        preserve = meet_or_slice in ('meet', 'slice')

        if meet_or_slice == 'slice':
            logger.warning(f"preserveAspectRatio 'slice' not fully supported, treating as 'meet'")

        return preserve, align

    def _extract_svg_dimensions(self, svg_root: ET.Element) -> tuple[float, float]:
        """
        Extract width and height from SVG element.

        Tries multiple strategies:
        1. viewBox attribute parsing
        2. width/height attributes
        3. Default fallback (800x600)

        Args:
            svg_root: SVG root element

        Returns:
            Tuple of (width, height) in pixels
        """
        # Strategy 1: Try viewBox first
        viewbox = svg_root.get('viewBox')
        if viewbox:
            try:
                # Use ConversionServices for ViewportEngine
                import numpy as np

                # Try to get from services if available
                if hasattr(self, 'services') and self.services and hasattr(self.services, 'viewport_resolver'):
                    resolver = self.services.viewport_resolver
                else:
                    # Fallback to ConversionServices
                    from ..services.conversion_services import ConversionServices
                    services = ConversionServices.create_default()
                    resolver = services.viewport_resolver

                parsed = resolver.parse_viewbox_strings(np.array([viewbox]))
                if len(parsed) > 0 and len(parsed[0]) >= 4:
                    # viewBox format: "x y width height"
                    _, _, width, height = parsed[0][:4]
                    return float(width), float(height)
            except (ImportError, Exception):
                # Fallback parsing
                try:
                    parts = viewbox.replace(',', ' ').split()
                    if len(parts) >= 4:
                        _, _, width, height = parts[:4]
                        return float(width), float(height)
                except (ValueError, IndexError):
                    pass

        # Strategy 2: Try width/height attributes
        try:
            width_attr = svg_root.get('width', '')
            height_attr = svg_root.get('height', '')

            if width_attr and height_attr:
                # Parse length values (remove units for now)
                width = self._parse_svg_length(width_attr)
                height = self._parse_svg_length(height_attr)
                if width > 0 and height > 0:
                    return width, height
        except (ValueError, TypeError):
            pass

        # Strategy 3: Default fallback
        return 800.0, 600.0

    def _parse_svg_length(self, length_str: str) -> float:
        """
        Parse SVG length value, removing units and returning numeric value.

        Args:
            length_str: Length string like "100px", "50%", "20"

        Returns:
            Numeric value (units stripped)
        """
        if not length_str:
            return 0.0

        length_str = length_str.strip()
        if not length_str:
            return 0.0

        # Remove common SVG units
        for unit in ['px', 'pt', 'em', 'ex', 'pc', 'mm', 'cm', 'in', '%']:
            if length_str.endswith(unit):
                length_str = length_str[:-len(unit)]
                break

        try:
            return float(length_str)
        except ValueError:
            return 0.0

    def _extract_css_transforms(self, element: ET.Element) -> str:
        """Extract transform from CSS style attribute."""
        style = element.get('style', '')
        if not style:
            return ''

        # Parse style attribute for CSS transforms
        styles = self.parse_style_attribute(style)
        return styles.get('transform', '')

    def apply_transform_to_points(self, transform: str, points: list,
                                 viewport_context: Optional = None) -> list:
        """Apply transform to a list of coordinate points."""
        if not transform or not transform.strip() or not points:
            return points

        try:
            matrix = self.services.transform_parser.parse_to_matrix(transform, viewport_context)

            transformed_points = []
            for point in points:
                if len(point) >= 2:
                    x, y = point[0], point[1]
                    if math.isfinite(x) and math.isfinite(y):
                        new_x, new_y = matrix.transform_point(x, y)
                        if math.isfinite(new_x) and math.isfinite(new_y):
                            transformed_points.append((new_x, new_y))
                        else:
                            transformed_points.append((x, y))  # Keep original if transform fails
                    else:
                        transformed_points.append((x, y))  # Keep original if invalid
                else:
                    transformed_points.append(point)  # Keep original if malformed

            return transformed_points

        except Exception as e:
            logger.warning(f"Batch transform failed for '{transform}': {e}, returning original points")
            return points

    def get_cumulative_transform(self, element: ET.Element, viewport_context: Optional = None):
        """
        Get cumulative transform matrix using robust composition with multiple fallback strategies.

        Uses the new compose() API when available, with graceful fallbacks for reliability.
        Maintains parent→child composition order per SVG specification.
        """
        transforms = []
        current = element

        # Collect transforms from element up to root (child→parent order)
        while current is not None:
            transform_attr = current.get('transform', '')
            if transform_attr and transform_attr.strip():
                transforms.append(transform_attr)

            # Check for CSS transforms as well
            css_transform = self._extract_css_transforms(current)
            if css_transform and css_transform.strip():
                transforms.append(css_transform)

            current = current.getparent()

        if not transforms:
            # No transforms found, return identity
            parser = self.services.transform_parser
            if hasattr(parser, 'identity'):
                return parser.identity()
            else:
                return parser.parse_to_matrix('', viewport_context)

        # Use parser's compose() method if available (primary path)
        parser = self.services.transform_parser
        try:
            if hasattr(parser, 'compose'):
                # Parent→child order (reverse collected order)
                return parser.compose(reversed(transforms), viewport_context)

            # Fallback: incremental multiplication using @ operator
            from ..transforms.core import Matrix
            result = Matrix.identity()
            for transform_str in reversed(transforms):
                try:
                    transform_matrix = parser.parse_to_matrix(transform_str, viewport_context)
                    result = result @ transform_matrix if hasattr(result, '__matmul__') else result.multiply(transform_matrix)
                except Exception as e:
                    logger.debug(f"Failed to parse transform '{transform_str}': {e}, skipping")
                    continue

            return result

        except Exception as e:
            logger.warning(f"Transform composition failed: {e}, using identity matrix")
            # Final fallback: return identity matrix
            if hasattr(parser, 'identity'):
                return parser.identity()
            else:
                return parser.parse_to_matrix('', viewport_context)

    def transform_point(self, x: float, y: float) -> Tuple[float, float]:
        """
        Transform a point using the current element's CTM or coordinate system.

        Args:
            x, y: Point coordinates in SVG user units

        Returns:
            Transformed coordinates (x, y) in EMU
        """
        if self.element_ctm is not None:
            from ..viewbox.ctm_utils import transform_point_with_ctm
            return transform_point_with_ctm(self.element_ctm, x, y)
        elif self.coordinate_system:
            return self.coordinate_system.svg_to_emu(x, y)
        else:
            return x, y

    def transform_length(self, length: float, direction: str = 'x') -> float:
        """
        Transform a length using the current element's CTM scale or coordinate system.

        Args:
            length: Length value in SVG user units
            direction: 'x' or 'y' for directional scaling

        Returns:
            Transformed length in EMU
        """
        if self.element_ctm is not None:
            from ..viewbox.ctm_utils import extract_scale_from_ctm
            scale = extract_scale_from_ctm(self.element_ctm, direction)
            return length * scale
        elif self.coordinate_system:
            return self.coordinate_system.svg_length_to_emu(length, direction)
        else:
            return length

    def create_child_context(self, child_element: ET.Element) -> 'ConversionContext':
        """
        Create a child ConversionContext with proper CTM and CSS style inheritance.

        Args:
            child_element: Child SVG element

        Returns:
            New ConversionContext with proper CTM chain and inherited styles
        """
        from ..viewbox.ctm_utils import create_child_context_with_ctm

        # Create child context with CTM propagation
        child_context = create_child_context_with_ctm(self, child_element)

        # Compute styles for the child element with inheritance
        if hasattr(self.services, 'style_service'):
            computed_style = self.services.style_service.compute_style(
                child_element,
                self.parent_style
            )
            child_context.parent_style = computed_style

        return child_context


class BaseConverter(ABC):
    """
    Abstract base class for all SVG element converters.

    This class provides the foundation for converting SVG elements to DrawingML
    using dependency injection for service management. All concrete converters
    must inherit from this class and implement the abstract methods.

    The converter uses ConversionServices for dependency injection, providing
    access to UnitConverter, ColorParser, Transform, and ViewportEngine
    through both direct service access and backward-compatible property accessors.

    Example:
        # New dependency injection pattern (preferred)
        services = ConversionServices.create_default()
        converter = MyConverter(services=services)

        # Legacy migration pattern
        converter = MyConverter.create_with_default_services()

    Attributes:
        supported_elements: List of SVG element tag names this converter handles
        services: ConversionServices container with injected dependencies
    """

    # Element types this converter handles
    supported_elements: List[str] = []

    def __init__(self, services: ConversionServices) -> None:
        """
        Initialize converter with dependency injection.

        Args:
            services: ConversionServices container with initialized services

        Raises:
            TypeError: If services parameter is missing or invalid
        """
        if services is None:
            raise ValueError(
                "ConversionServices is required. Use ConversionServices.create_default() "
                "if you need default services."
            )

        self.logger = logging.getLogger(self.__class__.__name__)
        self.services = services

        # Initialize filter components
        self._filter_complexity_analyzer = None
        self._filter_optimization_strategy = None
        self._filter_fallback_chain = None
        self._filter_bounds_calculator = None


    def validate_services(self) -> bool:
        """Validate that all required services are available."""
        return self.services.validate_services()


    @classmethod
    def create_with_default_services(cls, config: Optional[ConversionConfig] = None) -> 'BaseConverter':
        """
        Create converter instance with default services for migration compatibility.

        This method provides a migration path for existing code that doesn't yet
        use explicit dependency injection. New code should prefer direct service
        injection through the constructor.

        Args:
            config: Optional configuration for services. If None, uses defaults.

        Returns:
            Converter instance with default ConversionServices

        Example:
            # Migration pattern
            converter = MyConverter.create_with_default_services()

            # Preferred pattern
            services = ConversionServices.create_default()
            converter = MyConverter(services=services)

        Note:
            This is a migration utility. New code should inject services explicitly.
        """
        services = ConversionServices.create_default(config)
        return cls(services=services)

    @abstractmethod
    def can_convert(self, element: ET.Element) -> bool:
        """
        Check if this converter can handle the given element.
        
        Args:
            element: SVG element to check
            
        Returns:
            True if this converter can handle the element
        """
        pass
    
    @abstractmethod
    def convert(self, element: ET.Element, context: ConversionContext) -> str:
        """
        Convert SVG element to DrawingML.
        
        Args:
            element: SVG element to convert
            context: Conversion context with shared state
            
        Returns:
            DrawingML XML string
        """
        pass
    
    def get_element_tag(self, element: ET.Element) -> str:
        """Extract the tag name without namespace."""
        tag = element.tag
        if '}' in tag:
            tag = tag.split('}')[-1]
        return tag
    
    def parse_style_attribute(self, style: str) -> Dict[str, str]:
        """Parse SVG style attribute into dictionary."""
        styles = {}
        if not style:
            return styles
            
        for item in style.split(';'):
            if ':' in item:
                key, value = item.split(':', 1)
                styles[key.strip()] = value.strip()
        
        return styles
    
    def get_attribute_with_style(self, element: ET.Element, attr_name: str, 
                                 default: Optional[str] = None) -> Optional[str]:
        """
        Get attribute value, checking both direct attributes and style.
        
        Priority: direct attribute > style attribute > inherited > default
        """
        # Direct attribute
        value = element.get(attr_name)
        if value:
            return value
        
        # Style attribute
        style = self.parse_style_attribute(element.get('style', ''))
        value = style.get(attr_name)
        if value:
            return value
        
        return default
    
    def apply_transform(self, transform: str, x: float, y: float,
                       viewport_context: Optional = None) -> Tuple[float, float]:
        """Apply SVG transform to coordinates using the enhanced TransformEngine."""
        if not transform or not transform.strip():
            return x, y

        try:
            # Parse transform to Matrix using the enhanced Transform engine
            matrix = self.services.transform_parser.parse_to_matrix(transform, viewport_context)

            # Validate input coordinates
            if not (isinstance(x, (int, float)) and isinstance(y, (int, float))):
                logger.warning(f"Invalid coordinates for transform: x={x}, y={y}")
                return x, y

            if not (math.isfinite(x) and math.isfinite(y)):
                logger.warning(f"Non-finite coordinates for transform: x={x}, y={y}")
                return x, y

            # Apply transformation to point using Matrix
            result = matrix.transform_point(x, y)

            # Validate result coordinates
            if not (math.isfinite(result[0]) and math.isfinite(result[1])):
                logger.warning(f"Transform produced non-finite result for '{transform}': {result}")
                return x, y  # Return original coordinates as fallback

            return result

        except Exception as e:
            logger.warning(f"Transform application failed for '{transform}': {e}, using original coordinates")
            return x, y
    
    def get_element_transform_matrix(self, element: ET.Element, viewport_context: Optional = None):
        """Get the Matrix for an SVG element with enhanced error handling."""
        transform_attr = element.get('transform', '')

        # Check both transform attribute and CSS transform property
        if not transform_attr:
            style_transforms = self._extract_css_transforms(element)
            if style_transforms:
                transform_attr = style_transforms

        if not transform_attr:
            return self.services.transform_parser.parse_to_matrix('', viewport_context)  # Identity transform

        try:
            matrix = self.services.transform_parser.parse_to_matrix(transform_attr, viewport_context)

            # Validate the resulting transform
            if matrix.is_identity():
                return matrix

            # Additional validation for non-identity transforms
            try:
                # Test the transform with a simple point transformation
                test_result = matrix.transform_point(0, 0)
                if not (math.isfinite(test_result[0]) and math.isfinite(test_result[1])):
                    logger.warning(f"Transform produces invalid results, using identity")
                    return self.services.transform_parser.parse_to_matrix('', viewport_context)
            except Exception:
                logger.warning(f"Transform validation failed, using identity")
                return self.services.transform_parser.parse_to_matrix('', viewport_context)

            return matrix

        except Exception as e:
            logger.warning(f"Failed to parse transform '{transform_attr}': {e}, using identity")
            return self.services.transform_parser.parse_to_matrix('', viewport_context)
    
    def parse_color(self, color: str) -> str:
        """Parse SVG color to DrawingML hex format using modern Color system."""
        if not color or color == 'none':
            return None

        # Handle gradient/pattern references directly
        if color.startswith('url('):
            return color

        # Use the modern Color system for all other colors
        try:
            color_obj = self.services.color_parser(color)

            # Handle transparent colors
            if color_obj._alpha == 0:
                return None

            # Get RGB values and return hex format compatible with existing code
            r, g, b = color_obj.rgb()
            return f'{r:02X}{g:02X}{b:02X}'
        except Exception:
            return None
    
    
    def to_emu(self, value: str, axis: str = 'x') -> int:
        """Convert SVG length to EMUs using the unit converter."""
        return self.services.unit_converter.to_emu(value, axis=axis)
    
    def parse_length(self, value: str, viewport_size: float = 100) -> float:
        """Parse SVG length value with units."""
        if not value:
            return 0
            
        value = str(value).strip()
        
        # Percentage
        if value.endswith('%'):
            return float(value[:-1]) * viewport_size / 100
            
        # Pixels (default unit)
        if value.endswith('px'):
            return float(value[:-2])
            
        # Points
        if value.endswith('pt'):
            return float(value[:-2]) * 1.33333  # 1pt = 1.33333px
            
        # Inches
        if value.endswith('in'):
            return float(value[:-2]) * 96  # 1in = 96px
            
        # Centimeters
        if value.endswith('cm'):
            return float(value[:-2]) * 37.7953  # 1cm = 37.7953px
            
        # Millimeters
        if value.endswith('mm'):
            return float(value[:-2]) * 3.77953  # 1mm = 3.77953px
            
        # Em units (approximate)
        if value.endswith('em'):
            return float(value[:-2]) * 16  # Assuming 16px font size
            
        # No unit specified - assume pixels
        try:
            return float(value)
        except ValueError:
            return 0
    
    def generate_fill(self, fill: str, opacity: str = '1', context: ConversionContext = None) -> str:
        """Generate DrawingML fill element."""
        if not fill or fill == 'none':
            return '<a:noFill/>'
            
        if fill.startswith('url('):
            # Gradient or pattern reference
            ref_id = fill[5:-1] if fill.endswith(')') else fill[5:]
            if ref_id.startswith('#'):
                ref_id = ref_id[1:]
                
            if context and ref_id in context.gradients:
                # Handle gradient fill - pass both gradient data and ID
                return self.generate_gradient_fill_with_id(ref_id, context.gradients[ref_id], opacity)
            elif context and ref_id in context.patterns:
                # Handle pattern fill - pass both pattern data and ID
                return self.generate_pattern_fill_with_id(ref_id, context.patterns[ref_id], opacity)
            else:
                # Fallback to gray if reference not found
                gray_color = self.parse_color('gray')
                return f'<a:solidFill><a:srgbClr val="{gray_color}"/></a:solidFill>'
        
        # Solid color fill
        color = self.parse_color(fill)
        if color:
            alpha = int(float(opacity) * 100000)
            if alpha < 100000:
                return f'''<a:solidFill>
                    <a:srgbClr val="{color}">
                        <a:alpha val="{alpha}"/>
                    </a:srgbClr>
                </a:solidFill>'''
            else:
                return f'<a:solidFill><a:srgbClr val="{color}"/></a:solidFill>'
        
        return '<a:noFill/>'
    
    def generate_stroke(self, stroke: str, stroke_width: str = '1', 
                       opacity: str = '1', context: ConversionContext = None) -> str:
        """Generate DrawingML line (stroke) element."""
        if not stroke or stroke == 'none':
            return ''
            
        color = self.parse_color(stroke)
        if not color:
            return ''
            
        # Convert stroke width to EMUs with minimum thickness for PowerPoint visibility
        stroke_width_value = float(stroke_width)
        # Apply minimum stroke width of 2px and scale factor for better PowerPoint visibility
        adjusted_stroke_width = max(stroke_width_value * 2.0, 2.0)
        width_emu = self.services.unit_converter.to_emu(f"{adjusted_stroke_width}px")
        
        alpha = int(float(opacity) * 100000)
        
        if alpha < 100000:
            return f'''<a:ln w="{width_emu}">
                <a:solidFill>
                    <a:srgbClr val="{color}">
                        <a:alpha val="{alpha}"/>
                    </a:srgbClr>
                </a:solidFill>
            </a:ln>'''
        else:
            return f'''<a:ln w="{width_emu}">
                <a:solidFill>
                    <a:srgbClr val="{color}"/>
                </a:solidFill>
            </a:ln>'''
    
    def generate_gradient_fill_with_id(self, gradient_id: str, gradient: Dict, opacity: str = '1') -> str:
        """Generate DrawingML gradient fill using gradient ID and data."""
        if gradient_id and self.services.gradient_service:
            # Use gradient service to convert to DrawingML
            gradient_content = self.services.gradient_service.get_gradient_content(gradient_id)
            if gradient_content:
                return gradient_content

        # Fallback to gray if gradient not found or service unavailable
        gray_color = self.parse_color('gray')
        return f'<a:solidFill><a:srgbClr val="{gray_color}"/></a:solidFill>'

    def generate_gradient_fill(self, gradient: Dict, opacity: str = '1') -> str:
        """Generate DrawingML gradient fill (legacy method)."""
        # Extract gradient ID from the gradient dictionary
        gradient_id = gradient.get('id', '')
        if not gradient_id:
            # Try to get ID from href attribute (gradient references)
            gradient_id = gradient.get('href', '').replace('#', '')

        return self.generate_gradient_fill_with_id(gradient_id, gradient, opacity)
    
    def generate_pattern_fill_with_id(self, pattern_id: str, pattern: Dict, opacity: str = '1') -> str:
        """Generate DrawingML pattern fill using pattern ID and data."""
        if pattern_id and self.services.pattern_service:
            # Use pattern service to convert to DrawingML
            pattern_content = self.services.pattern_service.get_pattern_content(pattern_id)
            if pattern_content:
                return pattern_content

        # Fallback to gray if pattern not found or service unavailable
        gray_color = self.parse_color('gray')
        return f'<a:solidFill><a:srgbClr val="{gray_color}"/></a:solidFill>'

    def generate_pattern_fill(self, pattern: Dict, opacity: str = '1') -> str:
        """Generate DrawingML pattern fill (legacy method)."""
        # Extract pattern ID from the pattern dictionary
        pattern_id = pattern.get('id', '')
        if not pattern_id:
            # Try to get ID from href attribute (pattern references)
            pattern_id = pattern.get('href', '').replace('#', '')

        return self.generate_pattern_fill_with_id(pattern_id, pattern, opacity)

    # Filter processing methods

    def initialize_filter_components(self, context: ConversionContext):
        """
        Initialize filter processing components if not already done.

        Args:
            context: Conversion context with filter processors
        """
        if self._filter_complexity_analyzer is None:
            self._filter_complexity_analyzer = context.get_filter_processor('complexity_analyzer')

        if self._filter_optimization_strategy is None:
            self._filter_optimization_strategy = context.get_filter_processor('optimization_strategy')

        if self._filter_fallback_chain is None:
            self._filter_fallback_chain = context.get_filter_processor('fallback_chain')

        if self._filter_bounds_calculator is None:
            self._filter_bounds_calculator = context.get_filter_processor('bounds_calculator')

    def extract_filter_attributes(self, element: ET.Element) -> Optional[Dict[str, Any]]:
        """
        Extract filter-related attributes from an SVG element.

        Args:
            element: SVG element to analyze

        Returns:
            Dictionary of filter attributes or None if no filters
        """
        filter_attr = element.get('filter')
        if not filter_attr:
            return None

        # Handle filter reference (e.g., "url(#filter-id)")
        if filter_attr.startswith('url(') and filter_attr.endswith(')'):
            filter_id = filter_attr[5:-1]  # Remove 'url(' and ')'
            if filter_id.startswith('#'):
                filter_id = filter_id[1:]  # Remove '#'

            return {
                'type': 'reference',
                'filter_id': filter_id,
                'original_attr': filter_attr
            }

        # Handle direct filter effects (if supported)
        return {
            'type': 'direct',
            'filter_value': filter_attr,
            'original_attr': filter_attr
        }

    def resolve_filter_definition(self, filter_ref: Dict[str, Any], context: ConversionContext) -> Optional[Dict[str, Any]]:
        """
        Resolve filter reference to actual filter definition.

        Args:
            filter_ref: Filter reference information
            context: Conversion context with filter definitions

        Returns:
            Resolved filter definition or None if not found
        """
        if filter_ref['type'] != 'reference':
            return None

        filter_id = filter_ref['filter_id']

        # Try FilterService first for better integration
        if hasattr(self.services, 'filter_service') and self.services.filter_service:
            filter_content = self.services.filter_service.get_filter_content(filter_id, context)
            if filter_content:
                return {
                    'id': filter_id,
                    'type': 'filter_service',
                    'content': filter_content,
                    'drawingml': filter_content
                }

        # Fall back to legacy filter parsing
        if context.svg_root is not None:
            # Find filter definition by ID
            filter_elements = context.svg_root.xpath(f"//svg:filter[@id='{filter_id}']",
                                                  namespaces={'svg': 'http://www.w3.org/2000/svg'})
            if filter_elements:
                return self._parse_filter_element(filter_elements[0])

            # Also check without namespace
            filter_elements = context.svg_root.xpath(f"//*[@id='{filter_id}']")
            for elem in filter_elements:
                if elem.tag.endswith('filter'):
                    return self._parse_filter_element(elem)

        return None

    def _parse_filter_element(self, filter_element: ET.Element) -> Dict[str, Any]:
        """
        Parse SVG filter element into internal representation.

        Args:
            filter_element: SVG filter element

        Returns:
            Internal filter definition
        """
        primitives = []

        for child in filter_element:
            tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag

            if tag == 'feGaussianBlur':
                primitives.append({
                    'type': 'feGaussianBlur',
                    'stdDeviation': child.get('stdDeviation', '0'),
                    'in': child.get('in', 'SourceGraphic'),
                    'result': child.get('result', '')
                })
            elif tag == 'feOffset':
                primitives.append({
                    'type': 'feOffset',
                    'dx': child.get('dx', '0'),
                    'dy': child.get('dy', '0'),
                    'in': child.get('in', 'SourceGraphic'),
                    'result': child.get('result', '')
                })
            elif tag == 'feDropShadow':
                primitives.append({
                    'type': 'feDropShadow',
                    'dx': child.get('dx', '0'),
                    'dy': child.get('dy', '0'),
                    'stdDeviation': child.get('stdDeviation', '0'),
                    'flood-color': child.get('flood-color', 'black'),
                    'flood-opacity': child.get('flood-opacity', '1'),
                    'result': child.get('result', '')
                })
            elif tag == 'feColorMatrix':
                primitives.append({
                    'type': 'feColorMatrix',
                    'type': child.get('type', 'matrix'),
                    'values': child.get('values', '1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 1 0'),
                    'in': child.get('in', 'SourceGraphic'),
                    'result': child.get('result', '')
                })
            elif tag == 'feComposite':
                primitives.append({
                    'type': 'feComposite',
                    'operator': child.get('operator', 'over'),
                    'in': child.get('in', 'SourceGraphic'),
                    'in2': child.get('in2', ''),
                    'result': child.get('result', '')
                })

        if len(primitives) == 1:
            return primitives[0]
        elif len(primitives) > 1:
            return {
                'type': 'chain',
                'primitives': primitives,
                'primitive_count': len(primitives)
            }
        else:
            return {'type': 'empty', 'primitives': [], 'primitive_count': 0}

    def apply_filter_to_shape(self, element: ET.Element, shape_bounds: Dict[str, float],
                            drawingml_content: str, context: ConversionContext) -> str:
        """
        Apply filter effects to a shape during rendering.

        Args:
            element: Original SVG element
            shape_bounds: Calculated bounds of the shape
            drawingml_content: Generated DrawingML content
            context: Conversion context

        Returns:
            Modified DrawingML content with filter effects applied
        """
        # Extract filter attributes
        filter_attributes = self.extract_filter_attributes(element)
        if not filter_attributes:
            return drawingml_content

        # Initialize filter components
        self.initialize_filter_components(context)
        if not self._filter_complexity_analyzer:
            self.logger.warning("Filter complexity analyzer not available")
            return drawingml_content

        # Resolve filter definition
        filter_definition = self.resolve_filter_definition(filter_attributes, context)
        if not filter_definition:
            self.logger.warning(f"Could not resolve filter: {filter_attributes}")
            return drawingml_content

        # Calculate filter complexity and select strategy
        complexity = self._filter_complexity_analyzer.calculate_complexity_score(filter_definition)
        strategy = None
        if self._filter_optimization_strategy:
            strategy = self._filter_optimization_strategy.select_strategy(filter_definition, complexity_score=complexity)

        # Calculate expanded bounds for filter effects
        expanded_bounds = shape_bounds
        if self._filter_bounds_calculator:
            expanded_bounds = self._filter_bounds_calculator.calculate_filter_bounds(shape_bounds, filter_definition)

        # Track filter processing for debugging
        self.track_filter_processing(filter_definition, strategy, context)

        # Push filter context for nested processing
        filter_context = {
            'definition': filter_definition,
            'complexity': complexity,
            'strategy': strategy,
            'original_bounds': shape_bounds,
            'expanded_bounds': expanded_bounds,
            'start_time': time.time()
        }
        context.push_filter_context(filter_context)

        try:
            # Validate pipeline state before processing
            issues = self.validate_filter_pipeline_state(context)
            if issues:
                self.logger.warning(f"Filter pipeline validation issues: {issues}")

            # Apply filter based on strategy
            result_content = drawingml_content
            if strategy and hasattr(strategy, 'name'):
                if strategy.name == 'NATIVE_DML':
                    result_content = self._apply_native_dml_filter(filter_definition, drawingml_content, context)
                elif strategy.name == 'DML_HACK':
                    result_content = self._apply_dml_hack_filter(filter_definition, drawingml_content, context)
                elif strategy.name == 'RASTERIZE':
                    result_content = self._apply_rasterization_filter(filter_definition, drawingml_content, context)
                else:
                    result_content = self._apply_default_filter(filter_definition, drawingml_content, context)
            else:
                # Fallback to default filter application
                result_content = self._apply_default_filter(filter_definition, drawingml_content, context)

            # Add processing time to debug info
            end_time = time.time()
            processing_time = end_time - filter_context['start_time']
            context.add_filter_debug_info(f'processing_time_{id(filter_definition)}', processing_time)

            return result_content

        finally:
            # Always pop filter context
            context.pop_filter_context()

    def _apply_native_dml_filter(self, filter_def: Dict[str, Any], content: str, context: ConversionContext) -> str:
        """Apply filter using native DrawingML effects."""
        # Handle FilterService-generated content
        if filter_def.get('type') == 'filter_service':
            drawingml = filter_def.get('drawingml', '')
            if drawingml and not drawingml.strip().startswith('<!--'):
                # Insert filter effects into content (handle both PowerPoint and DrawingML formats)
                if '</p:spPr>' in content:
                    return content.replace('</p:spPr>', f'{drawingml}</p:spPr>')
                elif '</a:spPr>' in content:
                    return content.replace('</a:spPr>', f'{drawingml}</a:spPr>')
                else:
                    # Fallback: append to content
                    return content + drawingml
            else:
                return content

        if filter_def['type'] == 'feGaussianBlur':
            blur_radius = float(filter_def.get('stdDeviation', '0'))
            blur_radius_emu = int(blur_radius * 12700)  # Convert to EMUs

            return content.replace(
                '</a:spPr>',
                f'<a:effectLst><a:blur rad="{blur_radius_emu}"/></a:effectLst></a:spPr>'
            )
        elif filter_def['type'] == 'feDropShadow':
            dx = float(filter_def.get('dx', '0'))
            dy = float(filter_def.get('dy', '0'))
            blur = float(filter_def.get('stdDeviation', '0'))

            dx_emu = int(dx * 12700)
            dy_emu = int(dy * 12700)
            blur_emu = int(blur * 12700)

            return content.replace(
                '</a:spPr>',
                f'<a:effectLst><a:outerShdw blurRad="{blur_emu}" dist="{int((dx_emu**2 + dy_emu**2)**0.5)}" dir="{int(math.atan2(dy, dx) * 180 / math.pi * 60000)}"><a:srgbClr val="000000"><a:alpha val="50000"/></a:srgbClr></a:outerShdw></a:effectLst></a:spPr>'
            )
        elif filter_def['type'] == 'feColorMatrix':
            return self._apply_color_matrix_filter(filter_def, content, context)
        elif filter_def['type'] == 'feComposite':
            return self._apply_composite_filter(filter_def, content, context)
        elif filter_def['type'] == 'chain':
            return self._apply_filter_chain(filter_def, content, context)

        return content

    def _apply_color_matrix_filter(self, filter_def: Dict[str, Any], content: str, context: ConversionContext) -> str:
        """Apply color matrix effects using DrawingML."""
        matrix_type = filter_def.get('type', 'matrix')

        if matrix_type == 'saturate':
            saturation_value = float(filter_def.get('values', '1'))
            saturation_pct = int(saturation_value * 100000)  # Convert to percentage in EMUs

            # Use DrawingML color effects for saturation
            effect_xml = f'<a:duotone><a:srgbClr val="000000"><a:sat val="{saturation_pct}"/></a:srgbClr><a:srgbClr val="FFFFFF"><a:sat val="{saturation_pct}"/></a:srgbClr></a:duotone>'

            return content.replace('</a:spPr>', f'<a:effectLst>{effect_xml}</a:effectLst></a:spPr>')
        elif matrix_type == 'hueRotate':
            hue_rotation = float(filter_def.get('values', '0'))
            hue_rotation_deg = int(hue_rotation * 60000)  # Convert to DrawingML units

            effect_xml = f'<a:recolor><a:clrTo><a:hslClr hue="{hue_rotation_deg}" sat="100000" lum="50000"/></a:clrTo></a:recolor>'
            return content.replace('</a:spPr>', f'<a:effectLst>{effect_xml}</a:effectLst></a:spPr>')
        elif matrix_type == 'luminanceToAlpha':
            # Convert to grayscale with alpha
            effect_xml = '<a:grayscl/>'
            return content.replace('</a:spPr>', f'<a:effectLst>{effect_xml}</a:effectLst></a:spPr>')

        return content

    def _apply_composite_filter(self, filter_def: Dict[str, Any], content: str, context: ConversionContext) -> str:
        """Apply composite operations and blending modes."""
        operator = filter_def.get('operator', 'over')

        # DrawingML has limited blending mode support, but we can approximate
        if operator == 'multiply':
            # Use shadow with multiply blend mode approximation
            effect_xml = '<a:innerShdw blurRad="0" dist="0"><a:srgbClr val="000000"><a:alpha val="25000"/></a:srgbClr></a:innerShdw>'
            return content.replace('</a:spPr>', f'<a:effectLst>{effect_xml}</a:effectLst></a:spPr>')
        elif operator == 'screen':
            # Use glow effect for screen-like blending
            effect_xml = '<a:glow rad="25400"><a:srgbClr val="FFFFFF"><a:alpha val="50000"/></a:srgbClr></a:glow>'
            return content.replace('</a:spPr>', f'<a:effectLst>{effect_xml}</a:effectLst></a:spPr>')
        elif operator == 'darken':
            # Use inner shadow for darkening
            effect_xml = '<a:innerShdw blurRad="12700" dist="0"><a:srgbClr val="000000"><a:alpha val="40000"/></a:srgbClr></a:innerShdw>'
            return content.replace('</a:spPr>', f'<a:effectLst>{effect_xml}</a:effectLst></a:spPr>')
        elif operator == 'lighten':
            # Use outer glow for lightening
            effect_xml = '<a:outerShdw blurRad="25400" dist="0"><a:srgbClr val="FFFFFF"><a:alpha val="30000"/></a:srgbClr></a:outerShdw>'
            return content.replace('</a:spPr>', f'<a:effectLst>{effect_xml}</a:effectLst></a:spPr>')
        elif operator in ['over', 'atop', 'in', 'out', 'xor']:
            # For standard compositing operations, apply transparency effects
            alpha_val = 75000 if operator == 'over' else 50000  # Different alpha based on operation
            effect_xml = f'<a:glow rad="0"><a:srgbClr val="FFFFFF"><a:alpha val="{alpha_val}"/></a:srgbClr></a:glow>'
            return content.replace('</a:spPr>', f'<a:effectLst>{effect_xml}</a:effectLst></a:spPr>')

        return content

    def _apply_filter_chain(self, filter_def: Dict[str, Any], content: str, context: ConversionContext) -> str:
        """Apply complex filter chain with multiple effects and blending."""
        primitives = filter_def.get('primitives', [])
        if not primitives:
            return content

        current_content = content
        effect_elements = []

        # Process each primitive in the chain
        for i, primitive in enumerate(primitives):
            if primitive['type'] == 'feGaussianBlur':
                blur_radius = float(primitive.get('stdDeviation', '0'))
                blur_radius_emu = int(blur_radius * 12700)
                effect_elements.append(f'<a:blur rad="{blur_radius_emu}"/>')

            elif primitive['type'] == 'feOffset':
                dx = float(primitive.get('dx', '0'))
                dy = float(primitive.get('dy', '0'))
                dx_emu = int(dx * 12700)
                dy_emu = int(dy * 12700)

                # Offset is typically combined with shadow effects
                if i < len(primitives) - 1 and primitives[i + 1]['type'] in ['feDropShadow', 'feComposite']:
                    # Will be handled by the next effect
                    continue
                else:
                    # Standalone offset - use shadow with offset
                    effect_elements.append(f'<a:outerShdw blurRad="0" dist="{int((dx_emu**2 + dy_emu**2)**0.5)}" dir="{int(math.atan2(dy, dx) * 180 / math.pi * 60000)}"><a:srgbClr val="000000"><a:alpha val="25000"/></a:srgbClr></a:outerShdw>')

            elif primitive['type'] == 'feDropShadow':
                dx = float(primitive.get('dx', '0'))
                dy = float(primitive.get('dy', '0'))
                blur = float(primitive.get('stdDeviation', '0'))

                dx_emu = int(dx * 12700)
                dy_emu = int(dy * 12700)
                blur_emu = int(blur * 12700)

                effect_elements.append(f'<a:outerShdw blurRad="{blur_emu}" dist="{int((dx_emu**2 + dy_emu**2)**0.5)}" dir="{int(math.atan2(dy, dx) * 180 / math.pi * 60000)}"><a:srgbClr val="000000"><a:alpha val="50000"/></a:srgbClr></a:outerShdw>')

            elif primitive['type'] == 'feColorMatrix':
                matrix_type = primitive.get('type', 'matrix')
                if matrix_type == 'saturate':
                    saturation_value = float(primitive.get('values', '1'))
                    saturation_pct = int(saturation_value * 100000)
                    effect_elements.append(f'<a:duotone><a:srgbClr val="000000"><a:sat val="{saturation_pct}"/></a:srgbClr><a:srgbClr val="FFFFFF"><a:sat val="{saturation_pct}"/></a:srgbClr></a:duotone>')

            elif primitive['type'] == 'feComposite':
                operator = primitive.get('operator', 'over')
                if operator == 'multiply':
                    effect_elements.append('<a:innerShdw blurRad="0" dist="0"><a:srgbClr val="000000"><a:alpha val="25000"/></a:srgbClr></a:innerShdw>')
                elif operator == 'screen':
                    effect_elements.append('<a:glow rad="25400"><a:srgbClr val="FFFFFF"><a:alpha val="50000"/></a:srgbClr></a:glow>')

        # Combine all effects
        if effect_elements:
            effects_xml = ''.join(effect_elements)
            return current_content.replace('</a:spPr>', f'<a:effectLst>{effects_xml}</a:effectLst></a:spPr>')

        return current_content

    def _apply_dml_hack_filter(self, filter_def: Dict[str, Any], content: str, context: ConversionContext) -> str:
        """Apply filter using DrawingML hacks and workarounds."""
        # Implement creative DrawingML solutions for unsupported effects
        self.logger.info(f"Applying DML hack for filter: {filter_def.get('type', 'unknown')}")
        return content

    def _apply_rasterization_filter(self, filter_def: Dict[str, Any], content: str, context: ConversionContext) -> str:
        """Apply filter using rasterization fallback."""
        # This would involve rasterizing the content with filter applied
        self.logger.info(f"Applying rasterization for filter: {filter_def.get('type', 'unknown')}")
        return content

    def _apply_default_filter(self, filter_def: Dict[str, Any], content: str, context: ConversionContext) -> str:
        """Apply default filter processing."""
        return self._apply_native_dml_filter(filter_def, content, context)

    # Pipeline coordination and state management methods

    def track_filter_processing(self, filter_definition: Dict[str, Any], strategy: Any, context: ConversionContext):
        """Track filter processing for debugging and monitoring."""
        filter_id = id(filter_definition)
        filter_type = filter_definition.get('type', 'unknown')
        strategy_name = getattr(strategy, 'name', str(strategy)) if strategy else 'none'

        debug_info = {
            'filter_id': filter_id,
            'filter_type': filter_type,
            'strategy_used': strategy_name,
            'context_depth': context.get_filter_context_depth(),
            'timestamp': time.time()
        }

        context.add_filter_debug_info(f'filter_{filter_id}', debug_info)

    def cleanup_filter_resources(self, context: ConversionContext):
        """Clean up filter-related resources."""
        # Clear filter component references
        self._filter_complexity_analyzer = None
        self._filter_optimization_strategy = None
        self._filter_fallback_chain = None
        self._filter_bounds_calculator = None

        # Clear filter context if it exists
        if context:
            context.clear_filter_context_stack()

        self.logger.debug("Filter resources cleaned up")

    def get_filter_processing_stats(self, context: ConversionContext) -> Dict[str, Any]:
        """Get comprehensive filter processing statistics."""
        stats = {
            'pipeline_state': 'active' if context.get_filter_context_depth() > 0 else 'idle',
            'context_depth': context.get_filter_context_depth(),
            'cache_stats': context.get_filter_cache_stats(),
            'debug_info_count': len(context.get_filter_debug_info()),
            'components_initialized': {
                'complexity_analyzer': self._filter_complexity_analyzer is not None,
                'optimization_strategy': self._filter_optimization_strategy is not None,
                'fallback_chain': self._filter_fallback_chain is not None,
                'bounds_calculator': self._filter_bounds_calculator is not None,
            }
        }
        return stats

    def validate_filter_pipeline_state(self, context: ConversionContext) -> List[str]:
        """Validate the current state of the filter pipeline and return any issues."""
        issues = []

        # Check for context stack imbalance
        if context.get_filter_context_depth() > 10:
            issues.append(f"Filter context stack is very deep ({context.get_filter_context_depth()} levels) - possible memory leak")

        # Check for uninitialized components when they should be available
        current_context = context.get_current_filter_context()
        if current_context:
            if not self._filter_complexity_analyzer and context.get_filter_processor('complexity_analyzer'):
                issues.append("Complexity analyzer not initialized despite being available in context")

            if not self._filter_optimization_strategy and context.get_filter_processor('optimization_strategy'):
                issues.append("Optimization strategy not initialized despite being available in context")

        # Check cache size
        cache_stats = context.get_filter_cache_stats()
        if cache_stats['cache_size'] > 1000:
            issues.append(f"Filter cache is large ({cache_stats['cache_size']} entries) - consider cleanup")

        return issues

    def create_filter_processing_report(self, context: ConversionContext) -> str:
        """Create a comprehensive filter processing report for debugging."""
        stats = self.get_filter_processing_stats(context)
        issues = self.validate_filter_pipeline_state(context)
        debug_info = context.get_filter_debug_info()

        report_lines = [
            "=== Filter Pipeline Processing Report ===",
            f"Pipeline State: {stats['pipeline_state']}",
            f"Context Depth: {stats['context_depth']}",
            f"Cache Size: {stats['cache_stats']['cache_size']}",
            f"Processors: {stats['cache_stats']['processor_count']}",
            "",
            "Component Status:",
        ]

        for component, initialized in stats['components_initialized'].items():
            status = "✓ Initialized" if initialized else "✗ Not initialized"
            report_lines.append(f"  {component}: {status}")

        if issues:
            report_lines.extend([
                "",
                "Issues Found:",
            ])
            for issue in issues:
                report_lines.append(f"  ⚠ {issue}")

        if debug_info:
            report_lines.extend([
                "",
                "Debug Information:",
            ])
            for key, value in debug_info.items():
                if isinstance(value, dict) and 'filter_type' in value:
                    report_lines.append(f"  {key}: {value['filter_type']} ({value.get('strategy_used', 'unknown')})")
                else:
                    report_lines.append(f"  {key}: {value}")

        return "\n".join(report_lines)

    # Performance optimization methods

    def batch_filter_operations(self, elements_with_filters: List[Tuple[ET.Element, Dict, str]],
                               context: ConversionContext) -> List[str]:
        """
        Process multiple filtered elements in an optimized batch.

        Args:
            elements_with_filters: List of (element, bounds, content) tuples
            context: Conversion context

        Returns:
            List of processed DrawingML content strings
        """
        if not elements_with_filters:
            return []

        # Group elements by filter type for batch processing
        filter_groups = {}
        for element, bounds, content in elements_with_filters:
            filter_attributes = self.extract_filter_attributes(element)
            if filter_attributes:
                filter_definition = self.resolve_filter_definition(filter_attributes, context)
                if filter_definition:
                    filter_type = filter_definition.get('type', 'unknown')
                    if filter_type not in filter_groups:
                        filter_groups[filter_type] = []
                    filter_groups[filter_type].append((element, bounds, content, filter_definition))

        # Process each group optimally
        results = []
        for filter_type, group_items in filter_groups.items():
            if filter_type in ['feGaussianBlur', 'feDropShadow']:
                # These can be batched efficiently
                batch_results = self._batch_process_simple_filters(group_items, context)
                results.extend(batch_results)
            else:
                # Process individually for complex filters
                for element, bounds, content, filter_def in group_items:
                    result = self.apply_filter_to_shape(element, bounds, content, context)
                    results.append(result)

        return results

    def _batch_process_simple_filters(self, group_items: List[Tuple], context: ConversionContext) -> List[str]:
        """Process simple filters (blur, drop shadow) in batch for better performance."""
        results = []

        # Initialize filter components once for the batch
        self.initialize_filter_components(context)

        for element, bounds, content, filter_definition in group_items:
            # Use cached complexity calculation if available
            complexity = None
            if self._filter_complexity_analyzer:
                complexity = self._filter_complexity_analyzer.calculate_complexity_score(filter_definition)

            # Apply optimized filter processing
            result = self._apply_native_dml_filter(filter_definition, content, context)
            results.append(result)

        return results

    def optimize_filter_chain_processing(self, filter_definition: Dict[str, Any], context: ConversionContext) -> Dict[str, Any]:
        """
        Optimize complex filter chain processing by reordering and combining operations.

        Args:
            filter_definition: Filter chain definition
            context: Conversion context

        Returns:
            Optimized filter definition
        """
        if filter_definition.get('type') != 'chain':
            return filter_definition

        primitives = filter_definition.get('primitives', [])
        if len(primitives) <= 1:
            return filter_definition

        optimized_primitives = []
        i = 0

        while i < len(primitives):
            current = primitives[i]

            # Combine consecutive blur operations
            if current['type'] == 'feGaussianBlur' and i + 1 < len(primitives):
                next_primitive = primitives[i + 1]
                if next_primitive['type'] == 'feGaussianBlur':
                    # Combine blur radii (approximate)
                    curr_radius = float(current.get('stdDeviation', '0'))
                    next_radius = float(next_primitive.get('stdDeviation', '0'))
                    combined_radius = (curr_radius**2 + next_radius**2)**0.5

                    optimized_primitives.append({
                        'type': 'feGaussianBlur',
                        'stdDeviation': str(combined_radius),
                        'in': current.get('in', 'SourceGraphic'),
                        'result': next_primitive.get('result', '')
                    })
                    i += 2  # Skip next primitive
                    continue

            # Merge offset + blur into drop shadow
            if (current['type'] == 'feOffset' and
                i + 1 < len(primitives) and
                primitives[i + 1]['type'] == 'feGaussianBlur'):

                offset = primitives[i]
                blur = primitives[i + 1]

                optimized_primitives.append({
                    'type': 'feDropShadow',
                    'dx': offset.get('dx', '0'),
                    'dy': offset.get('dy', '0'),
                    'stdDeviation': blur.get('stdDeviation', '0'),
                    'flood-color': 'black',
                    'result': blur.get('result', '')
                })
                i += 2
                continue

            # Keep primitive as-is
            optimized_primitives.append(current)
            i += 1

        return {
            'type': 'chain',
            'primitives': optimized_primitives,
            'primitive_count': len(optimized_primitives)
        }

    def implement_filter_caching_strategy(self, context: ConversionContext):
        """
        Implement intelligent caching strategy for filter operations.
        """
        cache_stats = context.get_filter_cache_stats()

        # Clear old cache entries if cache is getting large
        if cache_stats['cache_size'] > 500:
            debug_info = context.get_filter_debug_info()
            current_time = time.time()

            # Remove entries older than 5 minutes
            expired_keys = []
            for key, value in debug_info.items():
                if isinstance(value, dict) and 'timestamp' in value:
                    if current_time - value['timestamp'] > 300:  # 5 minutes
                        expired_keys.append(key)

            for key in expired_keys:
                debug_info.pop(key, None)

            self.logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

    def monitor_memory_usage(self, context: ConversionContext) -> Dict[str, Any]:
        """
        Monitor memory usage during filter processing.

        Returns:
            Memory usage statistics
        """
        try:
            import psutil
            import os

            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()

            stats = {
                'rss_mb': memory_info.rss / 1024 / 1024,  # Resident memory in MB
                'vms_mb': memory_info.vms / 1024 / 1024,  # Virtual memory in MB
                'filter_cache_size': context.get_filter_cache_stats()['cache_size'],
                'context_stack_depth': context.get_filter_context_depth(),
            }

            # Add warning if memory usage is high
            if stats['rss_mb'] > 1000:  # 1GB
                self.logger.warning(f"High memory usage detected: {stats['rss_mb']:.1f}MB RSS")

            return stats

        except ImportError:
            # psutil not available, return basic stats
            return {
                'rss_mb': 'unavailable',
                'vms_mb': 'unavailable',
                'filter_cache_size': context.get_filter_cache_stats()['cache_size'],
                'context_stack_depth': context.get_filter_context_depth(),
            }

    def optimize_drawingml_output(self, content: str) -> str:
        """
        Optimize generated DrawingML content for better performance.

        Args:
            content: Raw DrawingML content

        Returns:
            Optimized DrawingML content
        """
        # Remove redundant whitespace
        optimized = re.sub(r'\s+', ' ', content)

        # Remove empty effect lists
        optimized = re.sub(r'<a:effectLst\s*></a:effectLst>', '', optimized)

        # Combine consecutive similar effects (basic optimization)
        # This is a simplified optimization - real implementation would be more complex

        return optimized.strip()


class ConverterRegistry:
    """Registry for managing and dispatching converters."""

    def __init__(self, services: Optional[ConversionServices] = None):
        """
        Initialize registry with optional service injection.

        Args:
            services: ConversionServices container for dependency injection
        """
        self.services = services
        self.converters: List[BaseConverter] = []
        self.element_map: Dict[str, List[BaseConverter]] = {}
        self.ir_bridge: Optional[BaseConverter] = None  # IRConverterBridge for hybrid mode
        
    def register(self, converter: BaseConverter):
        """Register a converter."""
        self.converters.append(converter)
        
        # Map element types to converters for quick lookup
        for element_type in converter.supported_elements:
            if element_type not in self.element_map:
                self.element_map[element_type] = []
            self.element_map[element_type].append(converter)
        
        logger.info(f"Registered converter: {converter.__class__.__name__} "
                   f"for elements: {converter.supported_elements}")

    def register_ir_bridge(self, ir_bridge: BaseConverter):
        """
        Register IRConverterBridge for hybrid mode.

        Args:
            ir_bridge: IRConverterBridge instance for clean slate integration
        """
        self.ir_bridge = ir_bridge
        logger.info(f"Registered IR bridge: {ir_bridge.__class__.__name__}")

    def register_class(self, converter_class: Type[BaseConverter]):
        """Register a converter class (instantiates it with services)."""
        if self.services:
            converter = converter_class(services=self.services)
        else:
            # Fallback to legacy pattern during migration
            converter = converter_class.create_with_default_services()
        self.register(converter)
    
    def get_converter(self, element: ET.Element) -> Optional[BaseConverter]:
        """Get appropriate converter for an element."""
        # Check IR bridge first if available and it can handle the element
        if self.ir_bridge and self.ir_bridge.can_convert(element):
            return self.ir_bridge

        # Extract tag without namespace
        tag = element.tag
        if '}' in tag:
            tag = tag.split('}')[-1]

        # Check mapped converters first
        if tag in self.element_map:
            for converter in self.element_map[tag]:
                if converter.can_convert(element):
                    return converter

        # Fallback to checking all converters
        for converter in self.converters:
            if converter.can_convert(element):
                return converter

        return None
    
    def convert_element(self, element: ET.Element, context: ConversionContext) -> Optional[str]:
        """Convert an element using the appropriate converter."""
        converter = self.get_converter(element)
        if converter:
            try:
                return converter.convert(element, context)
            except Exception as e:
                logger.error(f"Error converting element {element.tag}: {e}")
                return f"<!-- Error converting {element.tag}: {e} -->"
        else:
            tag = element.tag.split('}')[-1] if '}' in element.tag else element.tag
            logger.warning(f"No converter found for element: {tag}")
            return None

    @classmethod
    def create_with_default_services(cls, config: Optional[ConversionConfig] = None):
        """
        Create registry with default services for migration compatibility.

        Args:
            config: Optional configuration for services

        Returns:
            ConverterRegistry instance with default ConversionServices
        """
        services = ConversionServices.create_default(config)
        return cls(services=services)
    
    def register_default_converters(self):
        """Register all default converters for SVG elements."""
        converters_registered = []
        
        # Register shape converters (enhanced with ViewportEngine)
        try:
            from .shapes import RectangleConverter, CircleConverter, EllipseConverter, PolygonConverter, LineConverter
            self.register_class(RectangleConverter)
            self.register_class(CircleConverter)
            self.register_class(EllipseConverter)
            self.register_class(PolygonConverter)
            self.register_class(LineConverter)
            converters_registered.extend(['RectangleConverter', 'CircleConverter', 'EllipseConverter', 'PolygonConverter', 'LineConverter'])
        except ImportError as e:
            logger.warning(f"Failed to import shape converters: {e}")
        
        # Register path converter
        try:
            from .paths import PathConverter
            self.register_class(PathConverter)
            converters_registered.append('PathConverter')
        except ImportError as e:
            logger.warning(f"Failed to import PathConverter: {e}")
        
        # Register text converter
        try:
            from .text import TextConverter
            self.register_class(TextConverter)
            converters_registered.append('TextConverter')
        except ImportError as e:
            logger.warning(f"Failed to import TextConverter: {e}")
        
        # Register gradient converter
        try:
            from .gradients import GradientConverter
            self.register_class(GradientConverter)
            converters_registered.append('GradientConverter')
        except ImportError as e:
            logger.warning(f"Failed to import GradientConverter: {e}")
        
        # Transform converter replaced with direct transform engine usage
        # TransformConverter is no longer registered as a separate converter
        
        # Register group handler
        try:
            from .groups import GroupHandler
            self.register_class(GroupHandler)
            converters_registered.append('GroupHandler')
        except ImportError as e:
            logger.warning(f"Failed to import GroupHandler: {e}")
        
        # Register new converters
        try:
            from .image import ImageConverter
            self.register_class(ImageConverter)
            converters_registered.append('ImageConverter')
        except ImportError as e:
            logger.warning(f"Failed to import ImageConverter: {e}")
        
        try:
            from .style import StyleConverter
            self.register_class(StyleConverter)
            converters_registered.append('StyleConverter')
        except ImportError as e:
            logger.warning(f"Failed to import StyleConverter: {e}")
        
        try:
            from .symbols import SymbolConverter
            self.register_class(SymbolConverter)
            converters_registered.append('SymbolConverter')
        except ImportError as e:
            logger.warning(f"Failed to import SymbolConverter: {e}")
        
        try:
            from .filters import FilterConverter
            self.register_class(FilterConverter)
            converters_registered.append('FilterConverter')
        except ImportError as e:
            logger.warning(f"Failed to import FilterConverter: {e}")

        # Register animation converter (new modular system)
        try:
            from .animation_converter import AnimationConverter
            self.register_class(AnimationConverter)
            converters_registered.append('AnimationConverter')
        except ImportError as e:
            logger.warning(f"Failed to import AnimationConverter: {e}")

        logger.info(f"Registered {len(converters_registered)} converters: {', '.join(converters_registered)}")


class ConverterRegistryFactory:
    """Factory for creating and configuring converter registries.

    FIXED: ConversionServices now properly passed through to registry
    =================================================================
    The factory now accepts services parameter and passes it to
    ConverterRegistry constructor, ensuring custom DPI/color parsers
    and other services flow through to all converters.
    """

    _registry_instance = None
    
    @classmethod
    def get_registry(cls, services: Optional[ConversionServices] = None, force_new: bool = False) -> ConverterRegistry:
        """Get a configured converter registry instance.

        Args:
            services: ConversionServices container for dependency injection (optional)
            force_new: If True, create a new registry instead of using singleton

        Returns:
            Configured ConverterRegistry instance
        """
        if force_new or cls._registry_instance is None:
            registry = ConverterRegistry(services=services)
            registry.register_default_converters()

            # Register IR bridge if clean slate services are available
            if services and cls._has_clean_slate_services(services):
                cls._register_ir_bridge(registry, services)

            if not force_new:
                cls._registry_instance = registry

            return registry

        return cls._registry_instance

    @classmethod
    def get_hybrid_registry(cls, services: ConversionServices, hybrid_config: Optional[Any] = None) -> ConverterRegistry:
        """
        Get a registry configured for hybrid mode with IR bridge.

        Args:
            services: ConversionServices with clean slate components
            hybrid_config: Optional hybrid configuration

        Returns:
            ConverterRegistry with IR bridge configured
        """
        registry = ConverterRegistry(services=services)
        registry.register_default_converters()

        # Always register IR bridge for hybrid mode
        cls._register_ir_bridge(registry, services, hybrid_config)

        return registry

    @classmethod
    def _has_clean_slate_services(cls, services: ConversionServices) -> bool:
        """Check if services has clean slate components available"""
        return all([
            hasattr(services, 'ir_scene_factory') and services.ir_scene_factory is not None,
            hasattr(services, 'policy_engine') and services.policy_engine is not None,
            hasattr(services, 'mapper_registry') and services.mapper_registry is not None,
            hasattr(services, 'drawingml_embedder') and services.drawingml_embedder is not None
        ])

    @classmethod
    def _register_ir_bridge(cls, registry: ConverterRegistry, services: ConversionServices, hybrid_config: Optional[Any] = None):
        """Register IR bridge converter with the registry"""
        try:
            from .ir_bridge import IRConverterBridge
            from ..config.hybrid_config import HybridConversionConfig

            # Use provided config or create default hybrid config
            if hybrid_config is None:
                hybrid_config = HybridConversionConfig.create_hybrid_paths_only()

            # Create and register IR bridge
            ir_bridge = IRConverterBridge(services, hybrid_config)
            registry.register_ir_bridge(ir_bridge)

            logger.info(f"IR bridge registered with mode: {hybrid_config.conversion_mode.value}")

        except ImportError as e:
            logger.warning(f"Failed to register IR bridge: {e}")
        except Exception as e:
            logger.error(f"Error registering IR bridge: {e}")
    
    @classmethod
    def create_test_registry(cls) -> ConverterRegistry:
        """Create a registry for testing with minimal converters."""
        registry = ConverterRegistry()
        
        # Register only basic shape converters for testing
        try:
            from .shapes import RectangleConverter, CircleConverter
            registry.register_class(RectangleConverter)
            registry.register_class(CircleConverter)
        except ImportError:
            logger.warning("Failed to import basic shape converters for test registry")
            
        return registry
    
    @classmethod
    def reset(cls):
        """Reset the singleton registry instance."""
        cls._registry_instance = None




