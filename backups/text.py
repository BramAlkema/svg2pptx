"""
SVG Text to DrawingML Converter

Handles SVG text elements with support for:
- Basic text content and positioning
- Font family, size, weight, style
- Text anchoring (start, middle, end)
- Text decorations (underline, strikethrough)
- Multi-line text with tspan elements
- Text paths (basic support)
- Text-to-path fallback when fonts are unavailable
"""

from typing import List, Dict, Any, Optional
import xml.etree.ElementTree as ET
import logging
from .base import BaseConverter, ConversionContext

logger = logging.getLogger(__name__)


class TextConverter(BaseConverter):
    """Converts SVG text elements to DrawingML text shapes with optional text-to-path fallback"""
    
    supported_elements = ['text', 'tspan']
    
    def __init__(self, 
                 enable_font_embedding: bool = True,
                 enable_text_to_path_fallback: bool = False):
        """
        Initialize TextConverter with enhanced font capabilities.
        
        Args:
            enable_font_embedding: Enable three-tier font strategy with PPTX embedding
            enable_text_to_path_fallback: Enable automatic fallback to path conversion
        """
        super().__init__()
        self.enable_font_embedding = enable_font_embedding
        self.enable_text_to_path_fallback = enable_text_to_path_fallback
        
        # Font embedding components
        self._font_analyzer = None
        self._font_embedder = None
        
        if self.enable_font_embedding:
            try:
                from .font_embedding import FontEmbeddingAnalyzer
                from ..pptx_font_embedder import PPTXFontEmbedder
                self._font_analyzer = FontEmbeddingAnalyzer()
                self._font_embedder = PPTXFontEmbedder()
                logger.info("Font embedding enabled with three-tier strategy")
            except ImportError as e:
                logger.warning(f"Could not enable font embedding: {e}")
                self.enable_font_embedding = False
        
        # Text-to-path fallback
        self._text_to_path_converter = None
        
        if self.enable_text_to_path_fallback:
            try:
                from .text_to_path import TextToPathConverter
                self._text_to_path_converter = TextToPathConverter()
                logger.info("Text-to-path fallback enabled")
            except ImportError as e:
                logger.warning(f"Could not enable text-to-path fallback: {e}")
                self.enable_text_to_path_fallback = False
    
    def can_convert(self, element):
        """Check if this converter can handle the given element."""
        tag = self.get_element_tag(element)
        return tag in self.supported_elements
    
    # Font weight mappings
    FONT_WEIGHTS = {
        'normal': '400',
        'bold': '700',
        'bolder': '800',
        'lighter': '200',
        '100': '100', '200': '200', '300': '300', '400': '400', '500': '500',
        '600': '600', '700': '700', '800': '800', '900': '900'
    }
    
    # Text anchor mappings
    TEXT_ANCHORS = {
        'start': 'l',    # left
        'middle': 'ctr', # center
        'end': 'r'       # right
    }
    
    def convert(self, element: ET.Element, context: ConversionContext) -> str:
        """Convert SVG text to DrawingML using three-tier font strategy"""
        
        # Extract font information for strategy decision
        font_family = self._get_font_family(element)
        font_weight = self._get_font_weight(element)
        font_style = self._get_font_style(element)
        is_italic = font_style.lower() == 'italic'
        weight_value = self._parse_font_weight_value(font_weight)
        
        # Apply three-tier font strategy if enabled
        if self.enable_font_embedding and self._font_analyzer:
            strategy = self._determine_font_strategy(font_family, weight_value, is_italic, context)
            
            if strategy == 'convert_to_path':
                # Tier 3: Convert to path when font unavailable
                if (self.enable_text_to_path_fallback and 
                    self._text_to_path_converter):
                    logger.debug(f"Using text-to-path conversion for unavailable font: {font_family}")
                    return self._text_to_path_converter.convert(element, context)
                else:
                    # Fallback to regular text without specific font
                    logger.debug(f"Font {font_family} unavailable, using fallback text conversion")
                    return self._convert_to_text_shape_with_font_strategy(element, context, 'fallback')
            
            elif strategy in ['embedded', 'system']:
                # Tier 1 & 2: Use embedded or system fonts 
                logger.debug(f"Using {strategy} font strategy for: {font_family}")
                return self._convert_to_text_shape_with_font_strategy(element, context, strategy)
        
        # Legacy path: Try text-to-path fallback if font embedding disabled
        elif (self.enable_text_to_path_fallback and 
              self._text_to_path_converter and 
              self._text_to_path_converter.should_convert_to_path(element, context)):
            
            logger.debug(f"Using text-to-path fallback for element: {font_family}")
            return self._text_to_path_converter.convert(element, context)
        
        # Default: Use regular text conversion
        return self._convert_to_text_shape(element, context)
    
    def _convert_to_text_shape(self, element: ET.Element, context: ConversionContext) -> str:
        """Convert SVG text to regular DrawingML text shape"""
        
        # Get text position
        x = float(element.get('x', '0'))
        y = float(element.get('y', '0'))
        
        # Apply transform to coordinates
        transform_attr = element.get('transform', '')
        if transform_attr:
            x, y = self.apply_transform(transform_attr, x, y, context.viewport_context)
        
        # Convert coordinates to EMU
        x_emu, y_emu = context.coordinate_system.svg_to_emu(x, y)
        
        # Get text content and formatting
        text_content = self._extract_text_content(element)
        if not text_content.strip():
            return ""
        
        # Get text properties
        font_family = self._get_font_family(element)
        font_size = self._get_font_size(element, context)
        font_weight = self._get_font_weight(element)
        font_style = self._get_font_style(element)
        text_anchor = self._get_text_anchor(element)
        text_decoration = self._get_text_decoration(element)
        fill_color = self._get_fill_color(element)
        
        # Calculate text box dimensions (approximate)
        text_width = max(len(text_content) * font_size * 0.6, 100)  # Rough estimation
        text_height = font_size * 1.2  # Line height approximation
        
        # Adjust position based on text anchor
        text_width_emu = self.to_emu(f"{text_width}px")
        if text_anchor == 'ctr':
            x_emu -= text_width_emu // 2
        elif text_anchor == 'r':
            x_emu -= text_width_emu
        
        # Create text shape
        return f"""<a:sp>
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
            <a:pPr algn="{text_anchor}"/>
            <a:r>
                <a:rPr lang="en-US" sz="{font_size * 100}" b="{1 if font_weight in ['700', '800', '900', 'bold'] else 0}" i="{1 if font_style == 'italic' else 0}"{' u="sng"' if 'underline' in text_decoration else ''}{' strike="sngStrike"' if 'line-through' in text_decoration else ''}>
                    <a:latin typeface="{font_family}"/>
                    {fill_color}
                </a:rPr>
                <a:t>{self._escape_xml(text_content)}</a:t>
            </a:r>
        </a:p>
    </a:txBody>
</a:sp>"""
    
    def _extract_text_content(self, element: ET.Element) -> str:
        """Extract text content from element including nested tspan elements"""
        text_parts = []
        
        # Add direct text content
        if element.text:
            text_parts.append(element.text.strip())
        
        # Process child elements (mainly tspan)
        for child in element:
            if child.tag.endswith('tspan'):
                if child.text:
                    text_parts.append(child.text.strip())
            if child.tail:
                text_parts.append(child.tail.strip())
        
        return ' '.join(text_parts)
    
    def _get_font_family(self, element: ET.Element) -> str:
        """Get font family from element or inherited styles"""
        # Check direct attribute
        font_family = element.get('font-family')
        if font_family:
            # Clean up font family (remove quotes, get first font)
            font_family = font_family.split(',')[0].strip()
            # Remove surrounding quotes
            if font_family.startswith(("'", '"')) and font_family.endswith(("'", '"')):
                font_family = font_family[1:-1]
            return font_family
        
        # Check style attribute
        style = element.get('style', '')
        if 'font-family:' in style:
            for part in style.split(';'):
                if part.strip().startswith('font-family:'):
                    font_family = part.split(':', 1)[1].strip()
                    font_family = font_family.split(',')[0].strip()
                    # Remove surrounding quotes
                    if font_family.startswith(("'", '"')) and font_family.endswith(("'", '"')):
                        font_family = font_family[1:-1]
                    return font_family
        
        return 'Arial'  # Default font
    
    def _get_font_size(self, element: ET.Element, context: ConversionContext) -> int:
        """Get font size in points"""
        # Check direct attribute
        font_size = element.get('font-size')
        if font_size:
            return self._parse_font_size(font_size, context)
        
        # Check style attribute
        style = element.get('style', '')
        if 'font-size:' in style:
            for part in style.split(';'):
                if part.strip().startswith('font-size:'):
                    font_size = part.split(':', 1)[1].strip()
                    return self._parse_font_size(font_size, context)
        
        return 12  # Default font size
    
    def _parse_font_size(self, font_size: str, context: ConversionContext) -> int:
        """Parse font size with units"""
        try:
            # Use base converter's parse_length method
            pixels = self.parse_length(font_size)
            # Convert pixels to points for PowerPoint
            points = pixels * 72.0 / 96.0  # Assume 96 DPI
            return int(points)
        except:
            return 12  # Default font size in points
    
    def _get_font_weight(self, element: ET.Element) -> str:
        """Get font weight"""
        # Check direct attribute
        font_weight = element.get('font-weight')
        if font_weight and font_weight in self.FONT_WEIGHTS:
            return self.FONT_WEIGHTS[font_weight]
        
        # Check style attribute
        style = element.get('style', '')
        if 'font-weight:' in style:
            for part in style.split(';'):
                if part.strip().startswith('font-weight:'):
                    weight = part.split(':', 1)[1].strip()
                    return self.FONT_WEIGHTS.get(weight, '400')
        
        return '400'  # Normal weight
    
    def _get_font_style(self, element: ET.Element) -> str:
        """Get font style (normal, italic)"""
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
    
    def _get_text_anchor(self, element: ET.Element) -> str:
        """Get text anchor alignment"""
        # Check direct attribute
        text_anchor = element.get('text-anchor', 'start')
        return self.TEXT_ANCHORS.get(text_anchor, 'l')
    
    def _get_text_decoration(self, element: ET.Element) -> List[str]:
        """Get text decorations (underline, line-through)"""
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
    
    def _get_fill_color(self, element: ET.Element) -> str:
        """Get text fill color"""
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
        
        # Default black color
        return '<a:solidFill><a:srgbClr val="000000"/></a:solidFill>'
    
    
    def _escape_xml(self, text: str) -> str:
        """Escape XML special characters"""
        return (text.replace('&', '&amp;')
                   .replace('<', '&lt;')
                   .replace('>', '&gt;')
                   .replace('"', '&quot;')
                   .replace("'", '&apos;'))
    
    # === Three-Tier Font Strategy Methods ===
    
    def _parse_font_weight_value(self, weight_str: str) -> int:
        """Parse font weight string to numeric value"""
        try:
            return int(weight_str)
        except ValueError:
            weight_map = {
                'normal': 400, 'bold': 700, 'bolder': 800, 'lighter': 200,
                'thin': 100, 'light': 300, 'medium': 500, 'semibold': 600,
                'extra-bold': 800, 'black': 900
            }
            return weight_map.get(weight_str.lower(), 400)
    
    def _determine_font_strategy(self, family: str, weight: int, italic: bool, 
                                 context: ConversionContext) -> str:
        """
        Determine which font strategy to use for given font
        
        Returns:
            'embedded' - Use embedded font from @font-face
            'system' - Use system font  
            'convert_to_path' - Convert to paths
        """
        # Check if we have embedded fonts in context
        embedded_fonts = getattr(context, 'embedded_fonts', {})
        
        # Check if font is embedded via @font-face
        if family in embedded_fonts:
            variant = self._get_font_variant_name(weight, italic)
            if variant in embedded_fonts[family]:
                return 'embedded'
        
        # Check if system font is available
        if self._font_analyzer:
            try:
                font_bytes = self._font_analyzer.load_system_font(
                    family, weight, italic, ['Arial', 'Helvetica', 'sans-serif']
                )
                if font_bytes:
                    return 'system'
            except Exception as e:
                logger.debug(f"System font check failed for {family}: {e}")
        
        # Fall back to path conversion
        return 'convert_to_path'
    
    def _get_font_variant_name(self, weight: int, italic: bool) -> str:
        """Get font variant name for embedding (regular, bold, italic, bolditalic)"""
        if italic and weight >= 700:
            return 'bolditalic'
        elif weight >= 700:
            return 'bold'
        elif italic:
            return 'italic'
        else:
            return 'regular'
    
    def _convert_to_text_shape_with_font_strategy(self, element: ET.Element, 
                                                  context: ConversionContext, 
                                                  strategy: str) -> str:
        """Convert SVG text to DrawingML with specific font strategy"""
        # Get basic text properties
        text_content = self._extract_text_content(element)
        if not text_content.strip():
            return ""
        
        font_family = self._get_font_family(element)
        font_size = self._get_font_size(element, context)
        font_weight = self._get_font_weight(element)
        font_style = self._get_font_style(element)
        weight_value = self._parse_font_weight_value(font_weight)
        is_italic = font_style.lower() == 'italic'
        
        # Handle font embedding if strategy requires it
        if strategy == 'embedded':
            self._register_embedded_font(font_family, weight_value, is_italic, context)
        elif strategy == 'system':
            self._register_system_font(font_family, weight_value, is_italic, context)
        
        # Generate DrawingML with appropriate font references
        return self._generate_drawingml_with_font_strategy(
            element, context, font_family, font_size, weight_value, is_italic, strategy
        )
    
    def _register_embedded_font(self, family: str, weight: int, italic: bool, 
                                context: ConversionContext):
        """Register embedded font for PPTX inclusion"""
        if not self._font_embedder:
            return
            
        embedded_fonts = getattr(context, 'embedded_fonts', {})
        if family in embedded_fonts:
            variant = self._get_font_variant_name(weight, italic)
            if variant in embedded_fonts[family]:
                font_bytes = embedded_fonts[family][variant]
                self._font_embedder.add_font_embed(family, variant, font_bytes)
                logger.debug(f"Registered embedded font: {family} {variant}")
    
    def _register_system_font(self, family: str, weight: int, italic: bool, 
                              context: ConversionContext):
        """Register system font for PPTX inclusion"""
        if not self._font_embedder or not self._font_analyzer:
            return
            
        try:
            font_bytes = self._font_analyzer.load_system_font(
                family, weight, italic, ['Arial', 'Helvetica', 'sans-serif']
            )
            if font_bytes:
                variant = self._get_font_variant_name(weight, italic)
                self._font_embedder.add_font_embed(family, variant, font_bytes)
                logger.debug(f"Registered system font: {family} {variant}")
        except Exception as e:
            logger.warning(f"Could not register system font {family}: {e}")
    
    def _generate_drawingml_with_font_strategy(self, element: ET.Element, 
                                               context: ConversionContext,
                                               font_family: str, font_size: int,
                                               weight: int, italic: bool, 
                                               strategy: str) -> str:
        """Generate DrawingML text with font strategy-specific references"""
        # For now, use the existing _convert_to_text_shape method
        # In a full implementation, this would add embedded font references
        return self._convert_to_text_shape(element, context)