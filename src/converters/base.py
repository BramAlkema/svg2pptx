#!/usr/bin/env python3
"""
Base converter classes and registry for SVG to DrawingML conversion.

This module provides the foundation for a modular converter architecture
where each SVG element type has its own specialized converter.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Optional, Any, Type
import xml.etree.ElementTree as ET
import logging
import re

# Import the new universal utilities
from ..utils.units import UniversalUnitConverter
from ..utils.colors import UniversalColorParser
from ..utils.transforms import UniversalTransformEngine
from ..utils.viewbox import ViewportHandler

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
    
    def apply_transform(self, transform: str, x: float, y: float) -> Tuple[float, float]:
        """Apply SVG transform to coordinates."""
        # Parse transform string (simplified - full implementation needed)
        if 'translate' in transform:
            match = re.search(r'translate\(([^,]+),?\s*([^)]*)\)', transform)
            if match:
                tx = float(match.group(1))
                ty = float(match.group(2)) if match.group(2) else 0
                x += tx
                y += ty
        
        if 'scale' in transform:
            match = re.search(r'scale\(([^,]+),?\s*([^)]*)\)', transform)
            if match:
                sx = float(match.group(1))
                sy = float(match.group(2)) if match.group(2) else sx
                x *= sx
                y *= sy
        
        # TODO: Add rotate, skew, matrix transforms
        
        return x, y


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
        
        # Initialize unit converter and viewport context
        self.unit_converter = UniversalUnitConverter()
        self.viewport_handler = ViewportHandler()
        if svg_root is not None:
            self.viewport_context = self.viewport_handler.create_viewport_context(svg_root)
        else:
            self.viewport_context = self.viewport_handler.get_default_context()
        
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
        return self.unit_converter.convert_to_emu(value, self.viewport_context, axis)
    
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
    
    def parse_color(self, color: str) -> str:
        """Parse SVG color to DrawingML hex format."""
        if not color or color == 'none':
            return None
            
        if color.startswith('#'):
            # Hex color
            hex_color = color[1:].upper()
            if len(hex_color) == 3:
                # Convert 3-digit to 6-digit hex
                hex_color = ''.join([c*2 for c in hex_color])
            return hex_color
            
        elif color.startswith('rgb(') or color.startswith('rgba('):
            # RGB/RGBA color
            match = re.match(r'rgba?\(([^)]+)\)', color)
            if match:
                parts = [p.strip() for p in match.group(1).split(',')]
                if len(parts) >= 3:
                    r = int(float(parts[0]))
                    g = int(float(parts[1]))
                    b = int(float(parts[2]))
                    return f'{r:02X}{g:02X}{b:02X}'
        
        elif color.startswith('url('):
            # Reference to gradient or pattern
            return color
            
        else:
            # Named color
            return self.named_color_to_hex(color)
    
    def named_color_to_hex(self, name: str) -> str:
        """Convert named SVG color to hex."""
        colors = {
            'aliceblue': 'F0F8FF', 'antiquewhite': 'FAEBD7', 'aqua': '00FFFF',
            'aquamarine': '7FFFD4', 'azure': 'F0FFFF', 'beige': 'F5F5DC',
            'bisque': 'FFE4C4', 'black': '000000', 'blanchedalmond': 'FFEBCD',
            'blue': '0000FF', 'blueviolet': '8A2BE2', 'brown': 'A52A2A',
            'burlywood': 'DEB887', 'cadetblue': '5F9EA0', 'chartreuse': '7FFF00',
            'chocolate': 'D2691E', 'coral': 'FF7F50', 'cornflowerblue': '6495ED',
            'cornsilk': 'FFF8DC', 'crimson': 'DC143C', 'cyan': '00FFFF',
            'darkblue': '00008B', 'darkcyan': '008B8B', 'darkgoldenrod': 'B8860B',
            'darkgray': 'A9A9A9', 'darkgrey': 'A9A9A9', 'darkgreen': '006400',
            'darkkhaki': 'BDB76B', 'darkmagenta': '8B008B', 'darkolivegreen': '556B2F',
            'darkorange': 'FF8C00', 'darkorchid': '9932CC', 'darkred': '8B0000',
            'darksalmon': 'E9967A', 'darkseagreen': '8FBC8F', 'darkslateblue': '483D8B',
            'darkslategray': '2F4F4F', 'darkslategrey': '2F4F4F', 'darkturquoise': '00CED1',
            'darkviolet': '9400D3', 'deeppink': 'FF1493', 'deepskyblue': '00BFFF',
            'dimgray': '696969', 'dimgrey': '696969', 'dodgerblue': '1E90FF',
            'firebrick': 'B22222', 'floralwhite': 'FFFAF0', 'forestgreen': '228B22',
            'fuchsia': 'FF00FF', 'gainsboro': 'DCDCDC', 'ghostwhite': 'F8F8FF',
            'gold': 'FFD700', 'goldenrod': 'DAA520', 'gray': '808080',
            'grey': '808080', 'green': '008000', 'greenyellow': 'ADFF2F',
            'honeydew': 'F0FFF0', 'hotpink': 'FF69B4', 'indianred': 'CD5C5C',
            'indigo': '4B0082', 'ivory': 'FFFFF0', 'khaki': 'F0E68C',
            'lavender': 'E6E6FA', 'lavenderblush': 'FFF0F5', 'lawngreen': '7CFC00',
            'lemonchiffon': 'FFFACD', 'lightblue': 'ADD8E6', 'lightcoral': 'F08080',
            'lightcyan': 'E0FFFF', 'lightgoldenrodyellow': 'FAFAD2', 'lightgray': 'D3D3D3',
            'lightgrey': 'D3D3D3', 'lightgreen': '90EE90', 'lightpink': 'FFB6C1',
            'lightsalmon': 'FFA07A', 'lightseagreen': '20B2AA', 'lightskyblue': '87CEFA',
            'lightslategray': '778899', 'lightslategrey': '778899', 'lightsteelblue': 'B0C4DE',
            'lightyellow': 'FFFFE0', 'lime': '00FF00', 'limegreen': '32CD32',
            'linen': 'FAF0E6', 'magenta': 'FF00FF', 'maroon': '800000',
            'mediumaquamarine': '66CDAA', 'mediumblue': '0000CD', 'mediumorchid': 'BA55D3',
            'mediumpurple': '9370DB', 'mediumseagreen': '3CB371', 'mediumslateblue': '7B68EE',
            'mediumspringgreen': '00FA9A', 'mediumturquoise': '48D1CC', 'mediumvioletred': 'C71585',
            'midnightblue': '191970', 'mintcream': 'F5FFFA', 'mistyrose': 'FFE4E1',
            'moccasin': 'FFE4B5', 'navajowhite': 'FFDEAD', 'navy': '000080',
            'oldlace': 'FDF5E6', 'olive': '808000', 'olivedrab': '6B8E23',
            'orange': 'FFA500', 'orangered': 'FF4500', 'orchid': 'DA70D6',
            'palegoldenrod': 'EEE8AA', 'palegreen': '98FB98', 'paleturquoise': 'AFEEEE',
            'palevioletred': 'DB7093', 'papayawhip': 'FFEFD5', 'peachpuff': 'FFDAB9',
            'peru': 'CD853F', 'pink': 'FFC0CB', 'plum': 'DDA0DD',
            'powderblue': 'B0E0E6', 'purple': '800080', 'red': 'FF0000',
            'rosybrown': 'BC8F8F', 'royalblue': '4169E1', 'saddlebrown': '8B4513',
            'salmon': 'FA8072', 'sandybrown': 'F4A460', 'seagreen': '2E8B57',
            'seashell': 'FFF5EE', 'sienna': 'A0522D', 'silver': 'C0C0C0',
            'skyblue': '87CEEB', 'slateblue': '6A5ACD', 'slategray': '708090',
            'slategrey': '708090', 'snow': 'FFFAFA', 'springgreen': '00FF7F',
            'steelblue': '4682B4', 'tan': 'D2B48C', 'teal': '008080',
            'thistle': 'D8BFD8', 'tomato': 'FF6347', 'turquoise': '40E0D0',
            'violet': 'EE82EE', 'wheat': 'F5DEB3', 'white': 'FFFFFF',
            'whitesmoke': 'F5F5F5', 'yellow': 'FFFF00', 'yellowgreen': '9ACD32'
        }
        return colors.get(name.lower(), '000000')
    
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
                return '<a:solidFill><a:srgbClr val="808080"/></a:solidFill>'
        
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
            
        # Convert stroke width to EMUs (1px = 12700 EMUs)
        width = self.parse_length(stroke_width)
        width_emu = int(width * 12700)
        
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
        return '<a:solidFill><a:srgbClr val="808080"/></a:solidFill>'
    
    def generate_pattern_fill(self, pattern: Dict, opacity: str = '1') -> str:
        """Generate DrawingML pattern fill."""
        # This is a placeholder - patterns are complex in DrawingML
        return '<a:solidFill><a:srgbClr val="808080"/></a:solidFill>'


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