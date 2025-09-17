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

# Import types for type hints only
if TYPE_CHECKING:
    try:
        from ..units import UnitConverter
        from ..colors import ColorParser
        from ..transforms import TransformParser
        from ..viewbox import ViewportResolver
    except ImportError:
        from src.units import UnitConverter
        from src.colors import ColorParser
        from src.transforms import TransformParser
        from src.viewbox import ViewportResolver

logger = logging.getLogger(__name__)


class CoordinateSystem:
    """Manages coordinate transformations between SVG and DrawingML."""
    
    def __init__(self, viewbox: Tuple[float, float, float, float],
                 slide_width: float = 9144000, 
                 slide_height: float = 6858000):
        """
        Initialize coordinate system.
        
        Args:
            viewbox: SVG viewBox (x, y, width, height)
            slide_width: PowerPoint slide width in EMUs
            slide_height: PowerPoint slide height in EMUs
        """
        self.viewbox = viewbox
        self.slide_width = slide_width
        self.slide_height = slide_height
        
        # Extract SVG dimensions from viewbox for compatibility
        self.svg_width = viewbox[2]
        self.svg_height = viewbox[3]
        
        # Calculate scaling factors
        self.scale_x = slide_width / viewbox[2] if viewbox[2] > 0 else 1
        self.scale_y = slide_height / viewbox[3] if viewbox[3] > 0 else 1
        
        # Maintain aspect ratio option
        self.preserve_aspect_ratio = True
        if self.preserve_aspect_ratio:
            self.scale = min(self.scale_x, self.scale_y)
            self.scale_x = self.scale_y = self.scale
            
            # Center the content if aspect ratio is preserved
            self.offset_x = (slide_width - viewbox[2] * self.scale) / 2
            self.offset_y = (slide_height - viewbox[3] * self.scale) / 2
        else:
            self.offset_x = 0
            self.offset_y = 0
    
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
    """Context object passed through the conversion pipeline."""

    def __init__(self, svg_root: Optional[ET.Element] = None, services: ConversionServices = None):
        """Initialize ConversionContext with required services.

        Args:
            svg_root: Optional SVG root element
            services: ConversionServices instance (required)

        Raises:
            TypeError: If services is not provided
        """
        if services is None:
            raise TypeError("ConversionContext requires ConversionServices instance")

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
        self.unit_converter = services.unit_converter
        self.viewport_handler = services.viewport_resolver
        # Simplified viewport context initialization
        self.viewport_context = None

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
    
    def to_emu(self, value, axis: str = 'x') -> int:
        """Convert SVG length to EMUs using the context's unit converter."""
        return self.unit_converter.to_emu(value, self.viewport_context, axis)
    
    def to_pixels(self, value, axis: str = 'x') -> float:
        """Convert SVG length to pixels using the context's unit converter."""
        return self.unit_converter.to_pixels(value, self.viewport_context, axis)
    
    def batch_convert_to_emu(self, values: Dict[str, Any]) -> Dict[str, int]:
        """Convert multiple SVG lengths to EMUs in one call."""
        return self.unit_converter.batch_convert(values, self.viewport_context)
    
    def update_viewport_context(self, **kwargs):
        """Update viewport context parameters."""
        for key, value in kwargs.items():
            if hasattr(self.viewport_context, key):
                setattr(self.viewport_context, key, value)


class BaseConverter(ABC):
    """
    Abstract base class for all SVG element converters.

    This class provides the foundation for converting SVG elements to DrawingML
    using dependency injection for service management. All concrete converters
    must inherit from this class and implement the abstract methods.

    The converter uses ConversionServices for dependency injection, providing
    access to UnitConverter, ColorParser, TransformParser, and ViewportResolver
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
        self.logger = logging.getLogger(self.__class__.__name__)
        self.services = services

        # Initialize filter components
        self._filter_complexity_analyzer = None
        self._filter_optimization_strategy = None
        self._filter_fallback_chain = None
        self._filter_bounds_calculator = None

    @property
    def unit_converter(self) -> 'UnitConverter':
        """Get UnitConverter from services for backward compatibility."""
        return self.services.unit_converter

    @property
    def color_parser(self) -> 'ColorParser':
        """Get ColorParser from services for backward compatibility."""
        return self.services.color_parser

    @property
    def transform_parser(self) -> 'TransformParser':
        """Get TransformParser from services for backward compatibility."""
        return self.services.transform_parser

    @property
    def viewport_resolver(self) -> 'ViewportResolver':
        """Get ViewportResolver from services for backward compatibility."""
        return self.services.viewport_resolver

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
        """Apply SVG transform to coordinates using the universal TransformParser."""
        if not transform:
            return x, y
        
        # Parse transform to matrix using the sophisticated TransformParser
        matrix = self.transform_parser.parse_to_matrix(transform, viewport_context)
        
        # Apply matrix transformation to point
        return matrix.transform_point(x, y)
    
    def get_element_transform_matrix(self, element: ET.Element, viewport_context: Optional = None):
        """Get the transformation matrix for an SVG element."""
        transform_attr = element.get('transform', '')
        if not transform_attr:
            return self.transform_parser.parse_to_matrix('', viewport_context)  # Identity matrix
        
        return self.transform_parser.parse_to_matrix(transform_attr, viewport_context)
    
    def parse_color(self, color: str) -> str:
        """Parse SVG color to DrawingML hex format using ColorParser."""
        if not color or color == 'none':
            return None
            
        # Handle gradient/pattern references directly
        if color.startswith('url('):
            return color
        
        # Use the sophisticated ColorParser for all other colors
        color_info = self.color_parser.parse(color)
        if color_info is None:
            return None
            
        # Handle transparent colors
        if color_info.alpha == 0:
            return None
            
        # Return hex format compatible with existing code
        return f'{color_info.red:02X}{color_info.green:02X}{color_info.blue:02X}'
    
    
    def to_emu(self, value: str, axis: str = 'x') -> int:
        """Convert SVG length to EMUs using the unit converter."""
        return self.unit_converter.to_emu(value, axis=axis)
    
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
                # Handle gradient fill
                return self.generate_gradient_fill(context.gradients[ref_id], opacity)
            elif context and ref_id in context.patterns:
                # Handle pattern fill
                return self.generate_pattern_fill(context.patterns[ref_id], opacity)
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
            
        # Convert stroke width to EMUs using proper unit converter
        width_emu = self.unit_converter.to_emu(f"{stroke_width}px")
        
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
    
    def generate_gradient_fill(self, gradient: Dict, opacity: str = '1') -> str:
        """Generate DrawingML gradient fill."""
        # This is a placeholder - should be implemented in GradientConverter
        gray_color = self.parse_color('gray')
        return f'<a:solidFill><a:srgbClr val="{gray_color}"/></a:solidFill>'
    
    def generate_pattern_fill(self, pattern: Dict, opacity: str = '1') -> str:
        """Generate DrawingML pattern fill."""
        # This is a placeholder - patterns are complex in DrawingML
        gray_color = self.parse_color('gray')
        return f'<a:solidFill><a:srgbClr val="{gray_color}"/></a:solidFill>'

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

        # Look for filter definition in SVG document
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
        
        # Register shape converters (enhanced with ViewportResolver)
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
        
        # Register transform converter
        try:
            from .transforms import TransformConverter
            self.register_class(TransformConverter)
            converters_registered.append('TransformConverter')
        except ImportError as e:
            logger.warning(f"Failed to import TransformConverter: {e}")
        
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
        
        logger.info(f"Registered {len(converters_registered)} converters: {', '.join(converters_registered)}")


class ConverterRegistryFactory:
    """Factory for creating and configuring converter registries."""
    
    _registry_instance = None
    
    @classmethod
    def get_registry(cls, force_new: bool = False) -> ConverterRegistry:
        """Get a configured converter registry instance.
        
        Args:
            force_new: If True, create a new registry instead of using singleton
            
        Returns:
            Configured ConverterRegistry instance
        """
        if force_new or cls._registry_instance is None:
            registry = ConverterRegistry()
            registry.register_default_converters()
            
            if not force_new:
                cls._registry_instance = registry
                
            return registry
        
        return cls._registry_instance
    
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