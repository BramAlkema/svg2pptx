"""
Text-to-Path Converter for SVG Text Elements

This module provides text-to-path conversion as a fallback system when fonts are
unavailable or when text needs to be converted to paths for better PowerPoint compatibility.

Key Features:
- Automatic font availability detection and fallback
- Text-to-path conversion with proper layout preservation
- Integration with existing TextConverter for seamless fallback
- Support for complex text properties (positioning, styling, decorations)
- Multi-line text and tspan element handling
"""

import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional, Tuple
import logging
import re

from .base import BaseConverter, ConversionContext
from .font_metrics import FontMetricsAnalyzer, FontMetrics
from .path_generator import PathGenerator


logger = logging.getLogger(__name__)


class TextToPathConverter(BaseConverter):
    """
    Converts SVG text elements to DrawingML paths when fonts are unavailable.
    
    This converter serves as a fallback system that automatically detects when
    fonts specified in SVG text elements are not available on the system and
    converts the text to vector paths to maintain visual fidelity.
    """
    
    supported_elements = ['text', 'tspan']
    
    # Configuration for text-to-path conversion
    DEFAULT_CONFIG = {
        'font_detection_enabled': True,
        'fallback_threshold': 0.8,  # Confidence threshold for font detection
        'path_optimization_level': 1,  # 0=none, 1=basic, 2=aggressive
        'preserve_text_decorations': True,
        'max_cache_size': 256
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize TextToPathConverter with configuration.
        
        Args:
            config: Configuration dictionary for converter behavior
        """
        super().__init__()
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
        
        # Initialize core components
        self.font_analyzer = FontMetricsAnalyzer(font_cache_size=self.config['max_cache_size'])
        self.path_generator = PathGenerator(optimization_level=self.config['path_optimization_level'])
        
        # Statistics tracking
        self.conversion_stats = {
            'total_conversions': 0,
            'successful_conversions': 0,
            'fallback_conversions': 0,
            'failed_conversions': 0
        }
    
    def can_convert(self, element: ET.Element) -> bool:
        """Check if this converter can handle the given element."""
        tag = self.get_element_tag(element)
        return tag in self.supported_elements
    
    def should_convert_to_path(self, element: ET.Element, context: ConversionContext) -> bool:
        """
        Determine if text element should be converted to path.
        
        Args:
            element: SVG text element
            context: Conversion context
            
        Returns:
            True if element should be converted to path, False otherwise
        """
        if not self.config['font_detection_enabled']:
            return True  # Always convert if detection is disabled
        
        # Get font family from element
        font_families = self._get_font_families(element)
        
        if not font_families:
            return True  # No font specified, convert to path
        
        # Check if any requested font is available
        for font_family in font_families:
            if self.font_analyzer.detect_font_availability(font_family):
                return False  # Font available, use regular text
        
        # No requested fonts available, check fallback chain
        fallback_chain = self.font_analyzer.get_font_fallback_chain(font_families)
        
        if not fallback_chain:
            return True  # No fallbacks available, convert to path
        
        # Check if fallback fonts provide good coverage
        primary_font = fallback_chain[0] if fallback_chain else None
        if primary_font and primary_font.lower() in ['arial', 'times new roman', 'helvetica']:
            return False  # Good fallback available, use regular text
        
        return True  # Convert to path for better fidelity
    
    def convert(self, element: ET.Element, context: ConversionContext) -> str:
        """
        Convert SVG text element to DrawingML path or regular text.
        
        Args:
            element: SVG text element to convert
            context: Conversion context
            
        Returns:
            DrawingML representation (path or text shape)
        """
        self.conversion_stats['total_conversions'] += 1
        
        try:
            # Extract text content
            text_content = self._extract_text_content(element)
            if not text_content.strip():
                return ""
            
            # Get text properties
            text_props = self._extract_text_properties(element, context)
            
            # Decide conversion method
            if self.should_convert_to_path(element, context):
                return self._convert_to_path(element, text_content, text_props, context)
            else:
                # Fallback to regular text conversion (could delegate to TextConverter)
                return self._convert_to_regular_text(element, text_content, text_props, context)
                
        except Exception as e:
            logger.error(f"Failed to convert text element: {e}")
            self.conversion_stats['failed_conversions'] += 1
            return ""
    
    def _convert_to_path(self, element: ET.Element, text_content: str, 
                        text_props: Dict[str, Any], context: ConversionContext) -> str:
        """Convert text to DrawingML path representation."""
        try:
            # Get font chain with fallback
            font_families = text_props['font_families']
            fallback_chain = self.font_analyzer.get_font_fallback_chain(font_families)
            
            if not fallback_chain:
                logger.warning(f"No fonts available for text: {text_content}")
                self.conversion_stats['failed_conversions'] += 1
                return ""
            
            # Use first available font
            selected_font = fallback_chain[0]
            logger.info(f"Converting text to path using font: {selected_font}")
            
            # Handle multi-line text
            lines = self._split_text_lines(text_content, element)
            
            if not lines:
                return ""
            
            # Generate paths for each line
            line_paths = []
            current_y = text_props['y']
            line_height = text_props['font_size'] * 1.2  # Standard line height
            
            for line_text in lines:
                if line_text.strip():  # Skip empty lines
                    line_path = self.path_generator.generate_text_path(
                        text=line_text,
                        font_metrics_analyzer=self.font_analyzer,
                        font_family=selected_font,
                        font_size=text_props['font_size'],
                        x=text_props['x'],
                        y=current_y,
                        font_style=text_props['font_style'],
                        font_weight=text_props['font_weight']
                    )
                    
                    if line_path:
                        line_paths.append(line_path)
                
                current_y += line_height
            
            if line_paths:
                # Combine lines into final shape
                result = self._create_text_path_shape(line_paths, text_props, context)
                self.conversion_stats['successful_conversions'] += 1
                self.conversion_stats['fallback_conversions'] += 1
                return result
            else:
                self.conversion_stats['failed_conversions'] += 1
                return ""
                
        except Exception as e:
            logger.error(f"Path conversion failed for text '{text_content}': {e}")
            self.conversion_stats['failed_conversions'] += 1
            return ""
    
    def _convert_to_regular_text(self, element: ET.Element, text_content: str,
                                text_props: Dict[str, Any], context: ConversionContext) -> str:
        """Convert to regular DrawingML text shape (fallback method)."""
        # This is a simplified version - in practice, you might delegate to TextConverter
        try:
            x_emu, y_emu = context.coordinate_system.svg_to_emu(text_props['x'], text_props['y'])
            
            # Calculate text box dimensions (approximate)
            text_width = max(len(text_content) * text_props['font_size'] * 0.6, 100)
            text_height = text_props['font_size'] * 1.2
            
            # Adjust position based on text anchor
            text_width_emu = self.to_emu(f"{text_width}px")
            if text_props['text_anchor'] == 'middle':
                x_emu -= text_width_emu // 2
            elif text_props['text_anchor'] == 'end':
                x_emu -= text_width_emu
            
            # Generate DrawingML text shape
            shape = f"""<a:sp>
    <a:nvSpPr>
        <a:cNvPr id="{context.get_next_shape_id()}" name="Text"/>
        <a:cNvSpPr txBox="1"/>
    </a:nvSpPr>
    <a:spPr>
        <a:xfrm>
            <a:off x="{x_emu}" y="{y_emu}"/>
            <a:ext cx="{self.to_emu(f'{text_width}px')}" cy="{self.to_emu(f'{text_height}px')}"/>
        </a:xfrm>
        <a:prstGeom prst="rect">
            <a:avLst/>
        </a:prstGeom>
        <a:noFill/>
        <a:ln><a:noFill/></a:ln>
    </a:spPr>
    <a:txBody>
        <a:bodyPr wrap="none" rtlCol="0">
            <a:spAutoFit/>
        </a:bodyPr>
        <a:lstStyle/>
        <a:p>
            <a:pPr algn="{self._get_alignment_code(text_props['text_anchor'])}"/>
            <a:r>
                <a:rPr lang="en-US" sz="{text_props['font_size'] * 100}" b="{1 if text_props['font_weight'] >= 700 else 0}" i="{1 if text_props['font_style'] == 'italic' else 0}">
                    <a:latin typeface="{text_props['font_families'][0] if text_props['font_families'] else 'Arial'}"/>
                    {text_props['fill_color']}
                </a:rPr>
                <a:t>{self._escape_xml(text_content)}</a:t>
            </a:r>
        </a:p>
    </a:txBody>
</a:sp>"""
            
            self.conversion_stats['successful_conversions'] += 1
            return shape
            
        except Exception as e:
            logger.error(f"Regular text conversion failed: {e}")
            self.conversion_stats['failed_conversions'] += 1
            return ""
    
    def _extract_text_properties(self, element: ET.Element, context: ConversionContext) -> Dict[str, Any]:
        """Extract comprehensive text properties from SVG element."""
        # Get position
        x = float(element.get('x', '0'))
        y = float(element.get('y', '0'))
        
        # Get font properties
        font_families = self._get_font_families(element)
        font_size = self._get_font_size(element, context)
        font_weight = self._get_font_weight_numeric(element)
        font_style = self._get_font_style(element)
        text_anchor = element.get('text-anchor', 'start')
        
        # Get colors and decorations
        fill_color = self._get_fill_color_xml(element)
        decorations = self._get_text_decorations(element)
        
        return {
            'x': x,
            'y': y,
            'font_families': font_families,
            'font_size': font_size,
            'font_weight': font_weight,
            'font_style': font_style,
            'text_anchor': text_anchor,
            'fill_color': fill_color,
            'decorations': decorations
        }
    
    def _get_font_families(self, element: ET.Element) -> List[str]:
        """Extract font families from element."""
        families = []
        
        # Check direct attribute
        font_family = element.get('font-family')
        if font_family:
            families.extend(self._parse_font_family_list(font_family))
        
        # Check style attribute
        style = element.get('style', '')
        if 'font-family:' in style:
            for part in style.split(';'):
                if part.strip().startswith('font-family:'):
                    font_family = part.split(':', 1)[1].strip()
                    families.extend(self._parse_font_family_list(font_family))
                    break
        
        return families if families else ['Arial']
    
    def _parse_font_family_list(self, font_family: str) -> List[str]:
        """Parse comma-separated font family list."""
        families = []
        for family in font_family.split(','):
            clean_family = family.strip().strip('"\'')
            if clean_family:
                families.append(clean_family)
        return families
    
    def _get_font_size(self, element: ET.Element, context: ConversionContext) -> float:
        """Get font size in points."""
        # Check direct attribute
        font_size = element.get('font-size')
        if font_size:
            return self._parse_font_size(font_size)
        
        # Check style attribute
        style = element.get('style', '')
        if 'font-size:' in style:
            for part in style.split(';'):
                if part.strip().startswith('font-size:'):
                    font_size = part.split(':', 1)[1].strip()
                    return self._parse_font_size(font_size)
        
        return 12.0  # Default font size
    
    def _parse_font_size(self, font_size: str) -> float:
        """Parse font size with units to points."""
        try:
            # Remove units and convert to float
            size_str = re.sub(r'[a-zA-Z%]', '', font_size.strip())
            size_value = float(size_str)
            
            # Convert units to points (approximate)
            if 'px' in font_size:
                return size_value * 72.0 / 96.0  # Assume 96 DPI
            elif 'em' in font_size:
                return size_value * 12.0  # Assume 12pt base
            elif 'pt' in font_size:
                return size_value
            else:
                # Default to treating as pixels
                return size_value * 72.0 / 96.0
                
        except:
            return 12.0
    
    def _get_font_weight_numeric(self, element: ET.Element) -> int:
        """Get font weight as numeric value."""
        weight_map = {
            'normal': 400, 'bold': 700, 'bolder': 800, 'lighter': 200,
            '100': 100, '200': 200, '300': 300, '400': 400, '500': 500,
            '600': 600, '700': 700, '800': 800, '900': 900
        }
        
        # Check direct attribute
        font_weight = element.get('font-weight')
        if font_weight:
            return weight_map.get(font_weight, 400)
        
        # Check style attribute
        style = element.get('style', '')
        if 'font-weight:' in style:
            for part in style.split(';'):
                if part.strip().startswith('font-weight:'):
                    weight = part.split(':', 1)[1].strip()
                    return weight_map.get(weight, 400)
        
        return 400
    
    def _get_font_style(self, element: ET.Element) -> str:
        """Get font style."""
        # Check direct attribute
        font_style = element.get('font-style', 'normal')
        if font_style in ['italic', 'oblique']:
            return 'italic'
        
        # Check style attribute
        style = element.get('style', '')
        if 'font-style:' in style:
            for part in style.split(';'):
                if part.strip().startswith('font-style:'):
                    style_val = part.split(':', 1)[1].strip()
                    return 'italic' if style_val in ['italic', 'oblique'] else 'normal'
        
        return 'normal'
    
    def _get_fill_color_xml(self, element: ET.Element) -> str:
        """Get fill color as DrawingML XML."""
        # Check direct fill attribute
        fill = element.get('fill')
        if fill and fill != 'none':
            color = self.parse_color(fill)
            if color:
                return f'<a:solidFill><a:srgbClr val="{color}"/></a:solidFill>'
        
        # Check style attribute
        style = element.get('style', '')
        if 'fill:' in style:
            for part in style.split(';'):
                if part.strip().startswith('fill:'):
                    fill = part.split(':', 1)[1].strip()
                    if fill and fill != 'none':
                        color = self.parse_color(fill)
                        if color:
                            return f'<a:solidFill><a:srgbClr val="{color}"/></a:solidFill>'
        
        # Default black
        return '<a:solidFill><a:srgbClr val="000000"/></a:solidFill>'
    
    def _get_text_decorations(self, element: ET.Element) -> List[str]:
        """Get text decorations."""
        decorations = []
        
        # Check direct attribute
        text_decoration = element.get('text-decoration', '')
        if text_decoration:
            decorations.extend(text_decoration.split())
        
        # Check style attribute
        style = element.get('style', '')
        if 'text-decoration:' in style:
            for part in style.split(';'):
                if part.strip().startswith('text-decoration:'):
                    decoration_val = part.split(':', 1)[1].strip()
                    decorations.extend(decoration_val.split())
        
        return decorations
    
    def _extract_text_content(self, element: ET.Element) -> str:
        """Extract text content including tspan elements."""
        text_parts = []
        
        # Add direct text content
        if element.text:
            text_parts.append(element.text)
        
        # Process child elements
        for child in element:
            if self.get_element_tag(child) == 'tspan':
                if child.text:
                    text_parts.append(child.text)
            if child.tail:
                text_parts.append(child.tail)
        
        return ''.join(text_parts)
    
    def _split_text_lines(self, text: str, element: ET.Element) -> List[str]:
        """Split text into lines considering line breaks and tspan elements."""
        # For now, simple line splitting - could be enhanced for tspan positioning
        lines = text.split('\n')
        return [line.strip() for line in lines if line.strip()]
    
    def _create_text_path_shape(self, line_paths: List[str], text_props: Dict[str, Any], 
                               context: ConversionContext) -> str:
        """Create final DrawingML shape from line paths."""
        if len(line_paths) == 1:
            # Single line - return the path directly with proper shape ID and fill
            path = line_paths[0]
            path = path.replace('{shape_id}', str(context.get_next_shape_id()))
            path = path.replace('{fill_color}', self._extract_color_hex(text_props['fill_color']))
            return path
        else:
            # Multiple lines - create group
            x_emu, y_emu = context.coordinate_system.svg_to_emu(text_props['x'], text_props['y'])
            
            # Replace placeholders in paths
            numbered_paths = []
            for i, path in enumerate(line_paths):
                numbered_path = path.replace('{shape_id}', f"{context.get_next_shape_id()}_{i}")
                numbered_path = numbered_path.replace('{fill_color}', self._extract_color_hex(text_props['fill_color']))
                numbered_paths.append(numbered_path)
            
            return f'''<a:grpSp>
    <a:nvGrpSpPr>
        <a:cNvPr id="{context.get_next_shape_id()}" name="TextPathGroup"/>
        <a:cNvGrpSpPr/>
    </a:nvGrpSpPr>
    <a:grpSpPr>
        <a:xfrm>
            <a:off x="{x_emu}" y="{y_emu}"/>
            <a:ext cx="1270000" cy="1270000"/>
            <a:chOff x="0" y="0"/>
            <a:chExt cx="1270000" cy="1270000"/>
        </a:xfrm>
    </a:grpSpPr>
    {''.join(numbered_paths)}
</a:grpSp>'''
    
    def _extract_color_hex(self, fill_xml: str) -> str:
        """Extract hex color from DrawingML fill XML."""
        match = re.search(r'val="([A-Fa-f0-9]{6})"', fill_xml)
        return match.group(1) if match else "000000"
    
    def _get_alignment_code(self, text_anchor: str) -> str:
        """Convert SVG text-anchor to DrawingML alignment."""
        alignment_map = {
            'start': 'l',    # left
            'middle': 'ctr', # center
            'end': 'r'       # right
        }
        return alignment_map.get(text_anchor, 'l')
    
    def _escape_xml(self, text: str) -> str:
        """Escape XML special characters."""
        return (text.replace('&', '&amp;')
                   .replace('<', '&lt;')
                   .replace('>', '&gt;')
                   .replace('"', '&quot;')
                   .replace("'", '&apos;'))
    
    def get_conversion_stats(self) -> Dict[str, Any]:
        """Get conversion statistics for monitoring."""
        stats = self.conversion_stats.copy()
        
        if stats['total_conversions'] > 0:
            stats['success_rate'] = stats['successful_conversions'] / stats['total_conversions']
            stats['fallback_rate'] = stats['fallback_conversions'] / stats['total_conversions']
        else:
            stats['success_rate'] = 0.0
            stats['fallback_rate'] = 0.0
        
        return stats
    
    def reset_stats(self) -> None:
        """Reset conversion statistics."""
        self.conversion_stats = {
            'total_conversions': 0,
            'successful_conversions': 0,
            'fallback_conversions': 0,
            'failed_conversions': 0
        }
    
    def clear_caches(self) -> None:
        """Clear all internal caches."""
        self.font_analyzer.clear_cache()
        self.reset_stats()