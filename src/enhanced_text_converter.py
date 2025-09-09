"""
Enhanced Text Conversion System

Integrates the three-tier font strategy:
1. @font-face embedded fonts (highest priority)
2. System fonts (fallback)  
3. SVG font outlining (legacy only)

This module combines FontEmbeddingAnalyzer, PPTXFontEmbedder, and TextToPathConverter
into a unified system that preserves editable text with embedded fonts when possible,
and only falls back to path conversion when absolutely necessary.
"""

import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Union
from pathlib import Path
from dataclasses import dataclass

# Import our font embedding components
try:
    from .font_embedding import FontEmbeddingAnalyzer, FontEmbedResult
    from .text_to_path import TextToPathConverter  
    from .base import BaseConverter, ConversionContext
except ImportError:
    # For standalone testing
    import sys
    sys.path.append('src')
    from converters.font_embedding import FontEmbeddingAnalyzer, FontEmbedResult
    from converters.text_to_path import TextToPathConverter
    from converters.base import BaseConverter, ConversionContext


@dataclass
class EnhancedTextResult:
    """Result of enhanced text conversion"""
    processed_svg: str  # SVG with text converted as needed
    embedded_fonts: Dict[str, Dict[str, bytes]]  # Fonts for PPTX embedding
    conversion_strategy: Dict[str, str]  # Which strategy was used per font family
    drawingml_elements: List[str]  # Generated DrawingML text elements


class EnhancedTextConverter(BaseConverter):
    """
    Enhanced text converter implementing three-tier font strategy
    
    Strategy priority:
    1. Embedded fonts (@font-face with data: URLs) -> embed in PPTX
    2. Available system fonts -> embed in PPTX  
    3. Unavailable fonts -> convert to paths
    4. Legacy SVG fonts -> convert to paths
    """
    
    def __init__(self, enable_path_fallback: bool = True):
        """
        Initialize enhanced text converter
        
        Args:
            enable_path_fallback: Whether to fall back to path conversion when fonts unavailable
        """
        super().__init__()
        self.font_analyzer = FontEmbeddingAnalyzer()
        self.path_converter = TextToPathConverter() if enable_path_fallback else None
        self.enable_path_fallback = enable_path_fallback
        
    def supports_element(self, element: ET.Element) -> bool:
        """Check if element is supported (text or tspan)"""
        tag = self._get_tag_name(element)
        return tag in ['text', 'tspan']
    
    def convert_svg_with_enhanced_text(self, svg_content: str, 
                                       context: Optional[ConversionContext] = None) -> EnhancedTextResult:
        """
        Convert SVG with enhanced text handling using three-tier strategy
        
        Args:
            svg_content: SVG content as string
            context: Conversion context (optional)
        
        Returns:
            Enhanced conversion result with fonts and DrawingML
        """
        # Step 1: Analyze fonts in SVG
        font_result = self.font_analyzer.analyze_svg_fonts(svg_content)
        
        # Step 2: Categorize text elements by font availability
        root = ET.fromstring(svg_content)
        text_elements = self._find_all_text_elements(root)
        
        strategy_map = {}
        drawingml_elements = []
        
        for elem in text_elements:
            family = elem.get('font-family', 'Arial').strip('\'"')
            weight = self._parse_font_weight(elem.get('font-weight', '400'))
            italic = elem.get('font-style', 'normal').lower() == 'italic'
            
            strategy = self._determine_font_strategy(family, weight, italic, font_result.embeds)
            strategy_map[family] = strategy
            
            if strategy in ['embedded', 'system']:
                # Generate DrawingML text with embedded font
                drawingml = self._create_drawingml_text(elem, font_result.embeds)
                drawingml_elements.append(drawingml)
            elif strategy == 'convert_to_path':
                # Use path conversion fallback
                if self.path_converter and context:
                    path_xml = self.path_converter.convert(elem, context)
                    drawingml_elements.append(path_xml)
                else:
                    # Fallback to regular text without embedded font
                    drawingml = self._create_drawingml_text(elem, {})
                    drawingml_elements.append(drawingml)
        
        return EnhancedTextResult(
            processed_svg=font_result.processed_svg,
            embedded_fonts=font_result.embeds,
            conversion_strategy=strategy_map,
            drawingml_elements=drawingml_elements
        )
    
    def _find_all_text_elements(self, root: ET.Element) -> List[ET.Element]:
        """Find all text and tspan elements in SVG"""
        text_elements = []
        
        # Find text elements
        text_elements.extend(root.findall('.//{http://www.w3.org/2000/svg}text'))
        text_elements.extend(root.findall('.//text'))
        
        # Find tspan elements
        text_elements.extend(root.findall('.//{http://www.w3.org/2000/svg}tspan'))
        text_elements.extend(root.findall('.//tspan'))
        
        return text_elements
    
    def _parse_font_weight(self, weight_str: str) -> int:
        """Parse font weight from string to integer"""
        try:
            return int(weight_str)
        except ValueError:
            weight_map = {
                'normal': 400,
                'bold': 700,
                'lighter': 300,
                'bolder': 700,
                'thin': 100,
                'light': 300,
                'medium': 500,
                'semibold': 600,
                'heavy': 800,
                'black': 900
            }
            return weight_map.get(weight_str.lower(), 400)
    
    def _determine_font_strategy(self, family: str, weight: int, italic: bool, 
                                 embeds: Dict[str, Dict[str, bytes]]) -> str:
        """
        Determine which font strategy to use for given font
        
        Returns:
            'embedded' - Use embedded font from @font-face
            'system' - Use system font  
            'convert_to_path' - Convert to paths
        """
        # Check if font is embedded via @font-face
        if family in embeds:
            slot = FontEmbeddingAnalyzer.get_font_slot(weight, italic)
            if slot in embeds[family]:
                return 'embedded'
        
        # Check if system font is available
        font_bytes = self.font_analyzer.load_system_font(
            family, weight, italic, ['Arial', 'Helvetica', 'sans-serif']
        )
        if font_bytes:
            return 'system'
        
        # Fall back to path conversion
        return 'convert_to_path'
    
    def _create_drawingml_text(self, text_elem: ET.Element, 
                               embeds: Dict[str, Dict[str, bytes]]) -> str:
        """Create DrawingML text element from SVG text"""
        text_content = text_elem.text or ""
        family = text_elem.get('font-family', 'Arial').strip('\'"')
        size = self._parse_font_size(text_elem.get('font-size', '12'))
        weight = self._parse_font_weight(text_elem.get('font-weight', '400'))
        italic = text_elem.get('font-style', 'normal').lower() == 'italic'
        
        # Get position
        x = float(text_elem.get('x', '0'))
        y = float(text_elem.get('y', '0'))
        
        # Check if font is embedded
        has_embedded_font = False
        if family in embeds:
            slot = FontEmbeddingAnalyzer.get_font_slot(weight, italic)
            has_embedded_font = slot in embeds[family]
        
        # Create DrawingML text element
        text_xml = f"""
        <a:txBody>
            <a:bodyPr />
            <a:lstStyle />
            <a:p>
                <a:r>
                    <a:rPr lang="en-US" sz="{size * 100}" b="{'1' if weight >= 700 else '0'}" i="{'1' if italic else '0'}">
                        <a:latin typeface="{family}" />
                        {self._create_font_reference(family, weight, italic) if has_embedded_font else ''}
                    </a:rPr>
                    <a:t>{text_content}</a:t>
                </a:r>
            </a:p>
        </a:txBody>
        """.strip()
        
        return text_xml
    
    def _parse_font_size(self, size_str: str) -> int:
        """Parse font size from string"""
        try:
            # Remove units and convert
            size_num = float(size_str.replace('px', '').replace('pt', '').replace('em', ''))
            return int(size_num)
        except ValueError:
            return 12  # Default size
    
    def _create_font_reference(self, family: str, weight: int, italic: bool) -> str:
        """Create font reference XML for embedded fonts"""
        # This would reference the embedded font ID
        # For now, return empty string as placeholder
        return ""
    
    def convert(self, element: ET.Element, context: ConversionContext) -> str:
        """
        Convert a single text element using enhanced strategy
        
        This is the BaseConverter interface implementation
        """
        # Create minimal SVG containing just this element for analysis
        svg_wrapper = f"""
        <svg xmlns="http://www.w3.org/2000/svg">
            {ET.tostring(element, encoding='unicode')}
        </svg>
        """
        
        result = self.convert_svg_with_enhanced_text(svg_wrapper, context)
        
        if result.drawingml_elements:
            return result.drawingml_elements[0]
        
        # Fallback to basic text conversion
        return self._create_drawingml_text(element, {})


def create_enhanced_text_demo():
    """
    Demonstration of the enhanced text conversion system
    """
    # Sample SVG with mixed font types
    svg_content = """
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600">
        <style>
            @font-face {
                font-family: 'EmbeddedFont';
                src: url(data:font/woff2;base64,VEVTVERBVEExMjM=);
            }
        </style>
        <defs>
            <font id="legacy">
                <font-face font-family="LegacyFont" />
                <glyph unicode="X" d="M0,0 L100,100 M100,0 L0,100" />
            </font>
        </defs>
        
        <!-- Embedded font - should be preserved as text -->
        <text x="50" y="100" font-family="EmbeddedFont" font-size="24">
            This uses embedded font
        </text>
        
        <!-- System font - should be preserved as text -->
        <text x="50" y="200" font-family="Arial" font-size="18" font-weight="bold">
            This uses system Arial Bold
        </text>
        
        <!-- Unavailable font - should convert to path -->
        <text x="50" y="300" font-family="UnavailableFont" font-size="16">
            This should convert to paths
        </text>
        
        <!-- Legacy SVG font - should convert to path -->
        <text x="50" y="400" font-family="LegacyFont" font-size="20">
            X
        </text>
    </svg>
    """
    
    converter = EnhancedTextConverter(enable_path_fallback=True)
    result = converter.convert_svg_with_enhanced_text(svg_content)
    
    print("Enhanced Text Conversion Demo")
    print("=" * 50)
    print(f"Embedded font families: {list(result.embedded_fonts.keys())}")
    print(f"Font strategies:")
    for family, strategy in result.conversion_strategy.items():
        print(f"  {family}: {strategy}")
    
    print(f"Generated {len(result.drawingml_elements)} DrawingML elements")
    print(f"Processed SVG length: {len(result.processed_svg)} characters")
    
    return result


if __name__ == "__main__":
    # Run demo if script is executed directly
    result = create_enhanced_text_demo()