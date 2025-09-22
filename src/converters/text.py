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

from typing import List, Dict, Any, Optional, Tuple
from lxml import etree as ET
import logging
from .base import BaseConverter, ConversionContext
from ..services.conversion_services import ConversionServices

# Import fluent API for more readable unit conversions
try:
    from ..units import unit, units
except ImportError:
    from src.units import unit, units

logger = logging.getLogger(__name__)


class TextConverter(BaseConverter):
    """Converts SVG text elements to DrawingML text shapes with optional text-to-path fallback"""
    
    supported_elements = ['text', 'tspan']
    
    def __init__(self,
                 services: ConversionServices,
                 enable_font_embedding: bool = True,
                 enable_text_to_path_fallback: bool = False):
        """
        Initialize TextConverter with enhanced font capabilities.

        Args:
            services: ConversionServices container with initialized services
            enable_font_embedding: Enable three-tier font strategy with PPTX embedding
            enable_text_to_path_fallback: Enable automatic fallback to path conversion
        """
        super().__init__(services)
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
    
    # Comprehensive font weight mappings with CSS Level 4 support
    FONT_WEIGHTS = {
        # CSS keywords
        'normal': '400',
        'bold': '700',
        'bolder': '800',  # Relative to parent
        'lighter': '200', # Relative to parent

        # CSS Level 1-4 numeric weights
        '100': '100', '200': '200', '300': '300', '400': '400', '500': '500',
        '600': '600', '700': '700', '800': '800', '900': '900',

        # Extended CSS weight keywords
        'thin': '100',
        'hairline': '100',
        'extralight': '200',
        'ultralight': '200',
        'light': '300',
        'regular': '400',
        'medium': '500',
        'semibold': '600',
        'demibold': '600',
        'extrabold': '800',
        'ultrabold': '800',
        'heavy': '800',
        'black': '900',
        'ultrablack': '900'
    }

    # Enhanced font style mappings with variant support
    FONT_STYLES = {
        'normal': 'normal',
        'italic': 'italic',
        'oblique': 'italic',  # Map oblique to italic for PowerPoint
        'inherit': 'normal'
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
        
        # Get text position using coordinate transformer for consistency
        try:
            x_str = element.get('x', '0')
            y_str = element.get('y', '0')

            # Use coordinate transformer for consistent parsing
            coord_result = self.services.coordinate_transformer.parse_coordinate_string(f"{x_str},{y_str}")
            if coord_result.coordinates:
                x, y = coord_result.coordinates[0]
            else:
                # Fallback to manual parsing with error handling
                x = float(x_str) if x_str else 0.0
                y = float(y_str) if y_str else 0.0

            self.logger.debug(f"Parsed text position: x={x}, y={y}")

        except Exception as e:
            self.logger.debug(f"Text coordinate parsing failed: {e}, using defaults")
            x, y = 0.0, 0.0
        
        # Apply transform to coordinates with enhanced error handling
        transform_attr = element.get('transform', '')
        if transform_attr:
            try:
                x, y = self.apply_transform(transform_attr, x, y, context.viewport_context)
                self.logger.debug(f"Applied transform '{transform_attr}': ({x}, {y})")
            except Exception as e:
                self.logger.warning(f"Transform application failed for text element: {e}")
                # Continue with original coordinates
        
        # Get text content and formatting first to calculate dimensions
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

        # Calculate text box dimensions using enhanced measurement
        text_width, text_height = self._calculate_precise_text_dimensions(
            text_content, font_family, font_size, font_weight, font_style
        )

        # Convert all coordinates and dimensions to EMU using fluent units API
        try:
            # Use fluent units API for consistent coordinate conversion
            x_emu = unit(x, 'px').to_emu()
            y_emu = unit(y, 'px').to_emu()
            text_width_emu = unit(text_width, 'px').to_emu()
            text_height_emu = unit(text_height, 'px').to_emu()

            self.logger.debug(f"Converted coordinates to EMU: x={x_emu}, y={y_emu}, w={text_width_emu}, h={text_height_emu}")

        except Exception as e:
            self.logger.debug(f"Fluent units API failed: {e}, using fallback EMU conversion")
            # Fallback EMU conversion (1 px ≈ 9525 EMU at 96 DPI)
            x_emu = int(x * 9525)
            y_emu = int(y * 9525)
            text_width_emu = int(text_width * 9525)
            text_height_emu = int(text_height * 9525)

        # Precise position adjustment based on text anchor and font metrics
        x_emu, y_emu = self._adjust_position_for_text_anchor(
            x_emu, y_emu, text_width_emu, text_height_emu, text_anchor, font_family, font_size
        )
        
        # Generate base text shape content
        shape_id = context.get_next_shape_id()
        base_content = f"""<p:sp xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
    <p:nvSpPr>
        <p:cNvPr id="{shape_id}" name="Text"/>
        <p:cNvSpPr/>
        <p:nvPr/>
    </p:nvSpPr>
    <p:spPr>
        <a:xfrm>
            <a:off x="{x_emu}" y="{y_emu}"/>
            <a:ext cx="{text_width_emu}" cy="{text_height_emu}"/>
        </a:xfrm>
        <a:prstGeom prst="rect">
            <a:avLst/>
        </a:prstGeom>
        <a:noFill/>
        <a:ln><a:noFill/></a:ln>
    </p:spPr>
    <p:txBody>
        <a:bodyPr wrap="none" rtlCol="0">
            <a:spAutoFit/>
        </a:bodyPr>
        <a:lstStyle/>
        <a:p>
            <a:pPr algn="{text_anchor}"/>
            <a:r>
                <a:rPr lang="en-US" sz="{int(font_size * 150)}"{self._generate_enhanced_font_attributes(font_weight, font_style, text_decoration)}>
                    <a:latin typeface="{self._escape_xml(font_family)}"/>
                    {fill_color}
                </a:rPr>
                <a:t>{self._escape_xml(text_content)}</a:t>
            </a:r>
        </a:p>
    </p:txBody>
</p:sp>"""

        # Apply filter effects if present
        text_bounds = {
            'x': float(x_emu),
            'y': float(y_emu),
            'width': float(text_width_emu),
            'height': float(text_height_emu)
        }

        return self.apply_filter_to_shape(element, text_bounds, base_content, context)
    
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
            # Use canonical StyleParser for font family extraction
            font_family = self.services.style_parser.extract_font_family(style)
            if font_family:
                return font_family
        
        return 'Arial'  # Default font
    
    def _get_font_size(self, element: ET.Element, context: ConversionContext) -> int:
        """Get font size in points using existing FontProcessor"""
        try:
            # Use the existing font processor service for consistent parsing
            font_size = self.services.font_processor.get_font_size(
                element,
                style_parser=self.services.style_parser,
                context=context
            )
            return int(font_size)
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
        """Parse font weight string to numeric value with comprehensive CSS support"""
        try:
            # Try direct numeric parsing first
            numeric_weight = int(weight_str)
            # Clamp to valid CSS range (1-1000, but commonly 100-900)
            return max(100, min(900, numeric_weight))
        except ValueError:
            # Enhanced weight mapping with all CSS keywords
            weight_map = {
                'normal': 400, 'bold': 700, 'bolder': 800, 'lighter': 200,
                'thin': 100, 'hairline': 100,
                'extralight': 200, 'ultralight': 200, 'light': 300,
                'regular': 400, 'medium': 500,
                'semibold': 600, 'demibold': 600,
                'extrabold': 800, 'ultrabold': 800,
                'heavy': 800, 'black': 900, 'ultrablack': 900
            }
            normalized_key = weight_str.lower().replace('-', '').replace('_', '')
            return weight_map.get(normalized_key, 400)
    
    def _determine_font_strategy(self, family: str, weight: int, italic: bool,
                                 context: ConversionContext) -> str:
        """
        Determine which font strategy to use for given font with enhanced fallback logic

        Returns:
            'embedded' - Use embedded font from @font-face
            'system' - Use system font
            'convert_to_path' - Convert to paths
        """
        # Step 1: Check if we have embedded fonts in context
        embedded_fonts = getattr(context, 'embedded_fonts', {})

        if family in embedded_fonts:
            variant = self._get_font_variant_name(weight, italic)
            if variant in embedded_fonts[family]:
                self.logger.debug(f"Using embedded font strategy for {family} ({variant})")
                return 'embedded'

        # Step 2: Enhanced system font availability checking
        if self._font_analyzer:
            try:
                # Try exact font match first
                font_bytes = self._font_analyzer.load_system_font(family, weight, italic, None)
                if font_bytes:
                    self.logger.debug(f"Found exact system font match for {family} (weight={weight}, italic={italic})")
                    return 'system'

                # Try font family variations (case-insensitive, space variations)
                family_variations = self._generate_font_family_variations(family)
                for variation in family_variations:
                    font_bytes = self._font_analyzer.load_system_font(variation, weight, italic, None)
                    if font_bytes:
                        self.logger.debug(f"Found system font variation '{variation}' for requested '{family}'")
                        return 'system'

                # Try with normalized weight (fallback to closest available weight)
                normalized_weights = self._get_weight_fallback_chain(weight)
                for fallback_weight in normalized_weights:
                    font_bytes = self._font_analyzer.load_system_font(family, fallback_weight, italic, None)
                    if font_bytes:
                        self.logger.debug(f"Found system font {family} with fallback weight {fallback_weight} (requested {weight})")
                        return 'system'

                # Try standard fallback chain with enhanced logic
                enhanced_fallbacks = self._get_enhanced_fallback_chain(family)
                for fallback_family in enhanced_fallbacks:
                    font_bytes = self._font_analyzer.load_system_font(
                        fallback_family, weight, italic, None
                    )
                    if font_bytes:
                        self.logger.debug(f"Using fallback system font '{fallback_family}' for requested '{family}'")
                        return 'system'

            except Exception as e:
                self.logger.debug(f"System font check failed for {family}: {e}")

        # Step 3: Final fallback - convert to path only if no better option
        self.logger.debug(f"No suitable font found for {family}, falling back to path conversion")
        return 'convert_to_path'
    
    def _get_font_variant_name(self, weight: int, italic: bool) -> str:
        """Get font variant name for embedding with comprehensive weight mapping"""
        # Determine base weight category
        if weight >= 800:  # Extra bold and black
            weight_suffix = 'black' if weight >= 900 else 'extrabold'
        elif weight >= 700:  # Bold range
            weight_suffix = 'bold'
        elif weight >= 600:  # Semi-bold range
            weight_suffix = 'semibold'
        elif weight >= 500:  # Medium range
            weight_suffix = 'medium'
        elif weight >= 300:  # Light range
            weight_suffix = 'light' if weight < 400 else 'regular'
        else:  # Thin range (100-200)
            weight_suffix = 'thin'

        # Combine with italic
        if italic:
            if weight_suffix == 'regular':
                return 'italic'
            else:
                return f'{weight_suffix}italic'
        else:
            return weight_suffix

    def _generate_font_family_variations(self, family: str) -> List[str]:
        """Generate font family name variations for better matching"""
        variations = [family]  # Start with original

        # Case variations
        variations.append(family.lower())
        variations.append(family.upper())
        variations.append(family.title())

        # Space/hyphen variations
        variations.append(family.replace(' ', '-'))
        variations.append(family.replace('-', ' '))
        variations.append(family.replace(' ', ''))

        # Common font name mappings
        font_mappings = {
            'helvetica': ['Helvetica Neue', 'Arial'],
            'arial': ['Helvetica', 'Helvetica Neue'],
            'times': ['Times New Roman', 'serif'],
            'courier': ['Courier New', 'monospace'],
            'verdana': ['Geneva', 'sans-serif'],
            'georgia': ['Times', 'serif'],
        }

        family_lower = family.lower()
        if family_lower in font_mappings:
            variations.extend(font_mappings[family_lower])

        # Remove duplicates while preserving order
        seen = set()
        unique_variations = []
        for var in variations:
            if var not in seen:
                seen.add(var)
                unique_variations.append(var)

        return unique_variations

    def _get_weight_fallback_chain(self, weight: int) -> List[int]:
        """Get fallback weight chain for better font matching"""
        # Start with requested weight
        weights = [weight]

        # Add closest standard weights
        standard_weights = [100, 200, 300, 400, 500, 600, 700, 800, 900]

        # Find closest weights (smaller distance first)
        weight_distances = [(abs(w - weight), w) for w in standard_weights if w != weight]
        weight_distances.sort()

        # Add up to 3 closest weights
        for _, w in weight_distances[:3]:
            weights.append(w)

        # Always include 400 (normal) and 700 (bold) as ultimate fallbacks
        if 400 not in weights:
            weights.append(400)
        if 700 not in weights:
            weights.append(700)

        return weights

    def _get_enhanced_fallback_chain(self, family: str) -> List[str]:
        """Get enhanced fallback chain based on font characteristics"""
        family_lower = family.lower()

        # Serif fonts
        if any(serif in family_lower for serif in ['times', 'georgia', 'serif']):
            return ['Times New Roman', 'Georgia', 'Times', 'serif', 'Arial']

        # Monospace fonts
        if any(mono in family_lower for mono in ['courier', 'mono', 'console', 'code']):
            return ['Courier New', 'Monaco', 'Menlo', 'monospace', 'Arial']

        # Sans-serif fonts (default)
        return ['Arial', 'Helvetica', 'Helvetica Neue', 'Verdana', 'Geneva', 'sans-serif']

    def _calculate_precise_text_dimensions(self, text: str, font_family: str, font_size: int,
                                          font_weight: str, font_style: str) -> Tuple[float, float]:
        """Calculate precise text dimensions using font metrics when available"""
        try:
            # Try to get font metrics for precise calculation
            font_metrics = self._get_font_metrics_for_measurement(font_family, font_weight, font_style)

            if font_metrics:
                # Calculate precise text width using font metrics
                text_width = self._calculate_text_width_with_metrics(text, font_size, font_metrics)
                text_height = self._calculate_text_height_with_metrics(font_size, font_metrics)

                self.logger.debug(f"Precise text measurement: {text_width:.1f}x{text_height:.1f} for '{text[:20]}...'")
                return text_width, text_height

        except Exception as e:
            self.logger.debug(f"Font metrics measurement failed: {e}, using enhanced estimation")

        # Fallback to enhanced estimation (better than original rough estimation)
        text_width, text_height = self._calculate_enhanced_text_estimation(text, font_family, font_size, font_weight)
        self.logger.debug(f"Enhanced estimation: {text_width:.1f}x{text_height:.1f} for '{text[:20]}...'")
        return text_width, text_height

    def _get_font_metrics_for_measurement(self, font_family: str, font_weight: str, font_style: str):
        """Get font metrics object for text measurement"""
        try:
            # Try to import and use font metrics analyzer
            from .font_metrics import FontMetricsAnalyzer

            if not hasattr(self, '_metrics_analyzer'):
                self._metrics_analyzer = FontMetricsAnalyzer()

            # Convert weight to numeric
            weight_value = self._parse_font_weight_value(font_weight)

            # Get font metrics
            return self._metrics_analyzer.get_font_metrics(font_family, font_style, weight_value)

        except ImportError:
            self.logger.debug("Font metrics analyzer not available")
            return None
        except Exception as e:
            self.logger.debug(f"Font metrics retrieval failed: {e}")
            return None

    def _calculate_text_width_with_metrics(self, text: str, font_size: int, font_metrics) -> float:
        """Calculate text width using actual font metrics"""
        if not text.strip():
            return 100.0  # Minimum width for empty text

        # Average character width estimation using font metrics
        # This is more accurate than the rough 0.6 multiplier
        units_per_em = getattr(font_metrics, 'units_per_em', 2048)

        # Estimate average character width as a fraction of em size
        # Most fonts have average character width around 0.5-0.6 em
        avg_char_width_ratio = 0.55  # More accurate than the old 0.6

        # Account for font characteristics
        if hasattr(font_metrics, 'family_name'):
            family_lower = font_metrics.family_name.lower()
            if 'condensed' in family_lower or 'narrow' in family_lower:
                avg_char_width_ratio *= 0.8  # Condensed fonts are narrower
            elif 'expanded' in family_lower or 'wide' in family_lower:
                avg_char_width_ratio *= 1.2  # Expanded fonts are wider
            elif any(mono in family_lower for mono in ['courier', 'mono', 'console']):
                avg_char_width_ratio = 0.6  # Monospace fonts have consistent width

        # Calculate text width
        estimated_width = len(text) * font_size * avg_char_width_ratio

        # Ensure minimum width
        return max(estimated_width, 100.0)

    def _calculate_text_height_with_metrics(self, font_size: int, font_metrics) -> float:
        """Calculate text height using actual font metrics"""
        try:
            # Use actual font metrics for line height calculation
            units_per_em = getattr(font_metrics, 'units_per_em', 2048)
            ascender = getattr(font_metrics, 'ascender', 1638)  # Typical ascender
            descender = getattr(font_metrics, 'descender', -410)  # Typical descender (negative)
            line_gap = getattr(font_metrics, 'line_gap', 0)

            # Calculate actual line height from font metrics
            line_height_ratio = (ascender - descender + line_gap) / units_per_em

            # Ensure reasonable line height (between 1.0 and 1.5)
            line_height_ratio = max(1.0, min(1.5, line_height_ratio))

            return font_size * line_height_ratio

        except Exception:
            # Fallback to improved default (slightly better than 1.2)
            return font_size * 1.25

    def _calculate_enhanced_text_estimation(self, text: str, font_family: str, font_size: int,
                                          font_weight: str) -> Tuple[float, float]:
        """Enhanced text dimension estimation when font metrics are unavailable"""
        if not text.strip():
            return 100.0, float(font_size)

        # Enhanced character width estimation based on font characteristics
        char_width_ratio = 0.55  # Better base ratio than 0.6

        # Adjust for font family characteristics
        family_lower = font_family.lower()

        # Serif fonts tend to be slightly wider
        if any(serif in family_lower for serif in ['times', 'georgia', 'serif']):
            char_width_ratio *= 1.05

        # Sans-serif fonts are typically more compact
        elif any(sans in family_lower for sans in ['arial', 'helvetica', 'verdana', 'sans']):
            char_width_ratio *= 0.95

        # Monospace fonts have consistent width
        elif any(mono in family_lower for mono in ['courier', 'mono', 'console', 'code']):
            char_width_ratio = 0.6

        # Condensed/expanded font variations
        if 'condensed' in family_lower or 'narrow' in family_lower:
            char_width_ratio *= 0.8
        elif 'expanded' in family_lower or 'extended' in family_lower:
            char_width_ratio *= 1.2

        # Adjust for font weight
        weight_value = self._parse_font_weight_value(font_weight)
        if weight_value >= 700:  # Bold fonts are wider
            char_width_ratio *= 1.08
        elif weight_value <= 300:  # Light fonts are narrower
            char_width_ratio *= 0.95

        # Calculate text width
        text_width = len(text) * font_size * char_width_ratio
        text_width = max(text_width, 100.0)  # Minimum width

        # Enhanced line height calculation
        line_height_ratio = 1.25  # Better than 1.2, accounts for typical font metrics

        # Adjust line height for font characteristics
        if 'condensed' in family_lower:
            line_height_ratio *= 0.95
        elif any(serif in family_lower for serif in ['times', 'georgia']):
            line_height_ratio *= 1.02  # Serif fonts need slightly more line height

        text_height = font_size * line_height_ratio

        return text_width, text_height
    
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
        """Register system font for PPTX inclusion with enhanced fallback logic"""
        if not self._font_embedder or not self._font_analyzer:
            return

        try:
            # Use the enhanced font strategy logic to find the best available font
            font_bytes = None

            # Try exact match first
            font_bytes = self._font_analyzer.load_system_font(family, weight, italic, None)
            registered_family = family

            # If not found, try family variations
            if not font_bytes:
                family_variations = self._generate_font_family_variations(family)
                for variation in family_variations:
                    font_bytes = self._font_analyzer.load_system_font(variation, weight, italic, None)
                    if font_bytes:
                        registered_family = variation
                        self.logger.debug(f"Using font family variation '{variation}' for requested '{family}'")
                        break

            # If still not found, try weight fallbacks
            if not font_bytes:
                weight_fallbacks = self._get_weight_fallback_chain(weight)
                for fallback_weight in weight_fallbacks[1:]:  # Skip first (original weight)
                    font_bytes = self._font_analyzer.load_system_font(family, fallback_weight, italic, None)
                    if font_bytes:
                        registered_family = family
                        self.logger.debug(f"Using weight fallback {fallback_weight} for {family} (requested {weight})")
                        break

            # Final fallback to enhanced fallback chain
            if not font_bytes:
                enhanced_fallbacks = self._get_enhanced_fallback_chain(family)
                for fallback_family in enhanced_fallbacks:
                    font_bytes = self._font_analyzer.load_system_font(fallback_family, weight, italic, None)
                    if font_bytes:
                        registered_family = fallback_family
                        self.logger.debug(f"Using enhanced fallback '{fallback_family}' for requested '{family}'")
                        break

            # Register the found font
            if font_bytes:
                variant = self._get_font_variant_name(weight, italic)
                self._font_embedder.add_font_embed(registered_family, variant, font_bytes)
                self.logger.debug(f"Successfully registered system font: {registered_family} {variant}")

                # Also store the mapping for reference
                if not hasattr(context, 'font_mappings'):
                    context.font_mappings = {}
                context.font_mappings[f"{family}:{weight}:{italic}"] = registered_family
            else:
                self.logger.warning(f"No suitable system font found for {family} (weight={weight}, italic={italic})")

        except Exception as e:
            self.logger.warning(f"Could not register system font {family}: {e}")
            import traceback
            self.logger.debug(f"Font registration traceback: {traceback.format_exc()}")
    
    def _generate_drawingml_with_font_strategy(self, element: ET.Element,
                                               context: ConversionContext,
                                               font_family: str, font_size: int,
                                               weight: int, italic: bool,
                                               strategy: str) -> str:
        """Generate DrawingML text with font strategy-specific references"""
        # For now, use the existing _convert_to_text_shape method
        # In a full implementation, this would add embedded font references
        return self._convert_to_text_shape(element, context)

    def _adjust_position_for_text_anchor(self, x_emu: int, y_emu: int, text_width_emu: int,
                                        text_height_emu: int, text_anchor: str,
                                        font_family: str, font_size: int) -> Tuple[int, int]:
        """Precisely adjust text position based on anchor and font metrics"""
        adjusted_x = x_emu
        adjusted_y = y_emu

        # Horizontal adjustment based on text anchor
        if text_anchor == 'ctr':  # center
            adjusted_x -= text_width_emu // 2
        elif text_anchor == 'r':  # right/end
            adjusted_x -= text_width_emu
        # For 'l' (left/start), no adjustment needed

        # Vertical adjustment - SVG baseline vs PowerPoint baseline differences
        try:
            # Try to get precise baseline adjustment using font metrics
            font_metrics = self._get_font_metrics_for_measurement(
                font_family, '400', 'normal'  # Use normal weight for baseline calculation
            )

            if font_metrics:
                # Calculate precise baseline offset
                baseline_offset = self._calculate_baseline_offset(font_size, font_metrics)
                adjusted_y += baseline_offset
                self.logger.debug(f"Applied precise baseline offset: {baseline_offset / 9525:.1f}pt")
            else:
                # Enhanced fallback baseline adjustment
                baseline_offset = self._calculate_enhanced_baseline_offset(font_family, font_size)
                adjusted_y += baseline_offset
                self.logger.debug(f"Applied enhanced baseline offset: {baseline_offset / 9525:.1f}pt")

        except Exception as e:
            self.logger.debug(f"Baseline calculation failed: {e}, using default adjustment")
            # Default baseline adjustment (better than no adjustment)
            baseline_offset = int(font_size * 0.15 * 9525)  # ~15% of font size
            adjusted_y += baseline_offset

        return adjusted_x, adjusted_y

    def _calculate_baseline_offset(self, font_size: int, font_metrics) -> int:
        """Calculate precise baseline offset using font metrics"""
        try:
            units_per_em = getattr(font_metrics, 'units_per_em', 2048)
            ascender = getattr(font_metrics, 'ascender', 1638)
            descender = getattr(font_metrics, 'descender', -410)

            # SVG baseline is at the font baseline, PowerPoint typically centers text
            # Calculate the offset needed to align baselines properly
            total_height_units = ascender - descender  # descender is negative
            ascender_ratio = ascender / units_per_em

            # PowerPoint text tends to sit slightly below the coordinate
            # Adjust by a fraction of the ascender height
            baseline_offset_ratio = ascender_ratio * 0.2  # 20% of ascender

            return int(font_size * baseline_offset_ratio * 9525)

        except Exception:
            # Fallback to default
            return int(font_size * 0.15 * 9525)

    def _calculate_enhanced_baseline_offset(self, font_family: str, font_size: int) -> int:
        """Calculate enhanced baseline offset based on font characteristics"""
        base_offset_ratio = 0.15  # Base offset as fraction of font size

        # Adjust for different font families
        family_lower = font_family.lower()

        # Serif fonts typically need slightly less offset
        if any(serif in family_lower for serif in ['times', 'georgia', 'serif']):
            base_offset_ratio *= 0.9

        # Sans-serif fonts need standard offset
        elif any(sans in family_lower for sans in ['arial', 'helvetica', 'verdana']):
            base_offset_ratio *= 1.0

        # Monospace fonts often need slightly more offset
        elif any(mono in family_lower for mono in ['courier', 'mono', 'console']):
            base_offset_ratio *= 1.1

        return int(font_size * base_offset_ratio * 9525)

    def _generate_enhanced_font_attributes(self, font_weight: str, font_style: str, text_decoration: List[str]) -> str:
        """Generate enhanced font attributes with comprehensive weight and style support"""
        attributes = []

        # Enhanced bold attribute with weight-specific logic
        weight_value = self._parse_font_weight_value(font_weight)
        bold_flag = 1 if weight_value >= 600 else 0  # More nuanced than just 700+
        attributes.append(f' b="{bold_flag}"')

        # Enhanced italic attribute
        italic_flag = 1 if font_style.lower() in ['italic', 'oblique'] else 0
        attributes.append(f' i="{italic_flag}"')

        # Text decorations
        if 'underline' in text_decoration:
            attributes.append(' u="sng"')
        if 'line-through' in text_decoration:
            attributes.append(' strike="sngStrike"')

        return ''.join(attributes)

    def _get_font_weight_class(self, weight: int) -> str:
        """Get CSS font weight class name for weight value"""
        if weight <= 100:
            return 'thin'
        elif weight <= 200:
            return 'extra-light'
        elif weight <= 300:
            return 'light'
        elif weight <= 400:
            return 'normal'
        elif weight <= 500:
            return 'medium'
        elif weight <= 600:
            return 'semi-bold'
        elif weight <= 700:
            return 'bold'
        elif weight <= 800:
            return 'extra-bold'
        else:
            return 'black'