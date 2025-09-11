#!/usr/bin/env python3
"""
Base converter classes and registry for SVG to DrawingML conversion.

This module provides the foundation for a modular converter architecture
where each SVG element type has its own specialized converter.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Optional, Any, Type
from lxml import etree as ET
import logging
import re

# Import the utilities from src level
from ..units import UnitConverter
from ..colors import ColorParser
from ..transforms import TransformParser
from ..viewbox import ViewportResolver

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
    
    def __init__(self, svg_root: Optional[ET.Element] = None):
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
        
        # Initialize unit converter and viewport context
        self.unit_converter = UnitConverter()
        self.viewport_handler = ViewportResolver()
        # Simplified viewport context initialization
        self.viewport_context = None
        
        # Initialize converter registry for nested conversions
        self.converter_registry: Optional[ConverterRegistry] = None
        
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
    """Abstract base class for all SVG element converters."""
    
    # Element types this converter handles
    supported_elements: List[str] = []
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.unit_converter = UnitConverter()
        self.transform_parser = TransformParser()
        self.color_parser = ColorParser()
        self.viewport_resolver = ViewportResolver()
        
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


class ConverterRegistry:
    """Registry for managing and dispatching converters."""
    
    def __init__(self):
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
        """Register a converter class (instantiates it)."""
        self.register(converter_class())
    
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