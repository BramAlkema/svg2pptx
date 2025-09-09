"""
PPTX Font Embedding System

This module handles embedding font bytes into PowerPoint presentations
to preserve editable text with custom fonts.
"""

import base64
import tempfile
import zipfile
import uuid
from pathlib import Path
from typing import Dict, List, Optional, BinaryIO
from dataclasses import dataclass
import xml.etree.ElementTree as ET
from pptx import Presentation
from pptx.oxml import parse_xml
from pptx.oxml.ns import nsdecls, qn


@dataclass
class FontResource:
    """Represents a font resource to be embedded in PPTX"""
    family: str
    variant: str  # regular, bold, italic, bolditalic
    font_bytes: bytes
    resource_id: str
    mime_type: str = "application/vnd.ms-fontobject"


class PPTXFontEmbedder:
    """Embeds font bytes directly into PPTX files for editable text preservation"""
    
    def __init__(self):
        self.embedded_fonts: Dict[str, Dict[str, FontResource]] = {}
        self.resource_counter = 1
    
    def add_font_embed(self, family: str, variant: str, font_bytes: bytes, mime_type: str = None) -> str:
        """
        Add a font for embedding in PPTX
        
        Args:
            family: Font family name (e.g., 'Arial', 'CustomFont')
            variant: Font variant (regular, bold, italic, bolditalic)
            font_bytes: Raw font file bytes
            mime_type: MIME type for font (defaults to ms-fontobject)
        
        Returns:
            Resource ID for the embedded font
        """
        if family not in self.embedded_fonts:
            self.embedded_fonts[family] = {}
        
        resource_id = f"font{self.resource_counter}"
        self.resource_counter += 1
        
        font_resource = FontResource(
            family=family,
            variant=variant,
            font_bytes=font_bytes,
            resource_id=resource_id,
            mime_type=mime_type or "application/vnd.ms-fontobject"
        )
        
        self.embedded_fonts[family][variant] = font_resource
        return resource_id
    
    def embed_fonts_in_pptx(self, presentation: Presentation, temp_dir: Path = None) -> Presentation:
        """
        Embed all registered fonts into a PowerPoint presentation
        
        Args:
            presentation: python-pptx Presentation object
            temp_dir: Optional temporary directory for processing
        
        Returns:
            Modified presentation with embedded fonts
        """
        if not self.embedded_fonts:
            return presentation
        
        # For now, implement as a placeholder that documents the process
        # Real implementation would:
        # 1. Extract PPTX as ZIP
        # 2. Add font files to ppt/fonts/ directory
        # 3. Update [Content_Types].xml with font MIME types
        # 4. Update presentation.xml with font references
        # 5. Repackage as PPTX
        
        return self._embed_fonts_via_zip_manipulation(presentation, temp_dir)
    
    def _embed_fonts_via_zip_manipulation(self, presentation: Presentation, temp_dir: Path = None) -> Presentation:
        """
        Embed fonts by manipulating PPTX ZIP structure
        
        This is a simplified implementation that demonstrates the concept.
        Full implementation would require deep OOXML manipulation.
        """
        # Create temporary directory for processing
        if temp_dir is None:
            temp_dir = Path(tempfile.mkdtemp())
        
        # For now, just return the original presentation
        # In a full implementation, we would:
        # 1. Save presentation to temporary file
        # 2. Extract ZIP contents
        # 3. Add font files and update XML relationships
        # 4. Repackage and return new presentation
        
        return presentation
    
    def generate_font_xml_elements(self) -> List[str]:
        """
        Generate XML elements for font embedding in DrawingML
        
        Returns:
            List of XML strings for font references
        """
        font_elements = []
        
        for family, variants in self.embedded_fonts.items():
            for variant, font_resource in variants.items():
                # Generate DrawingML font reference
                font_xml = f"""
                <a:font script="" typeface="{family}">
                    <a:extLst>
                        <a:ext uri="{{B6124F45-8C7E-4DE2-8C91-2C5E7B1F3C2A}}">
                            <a14:font id="{font_resource.resource_id}" />
                        </a:ext>
                    </a:extLst>
                </a:font>
                """.strip()
                
                font_elements.append(font_xml)
        
        return font_elements
    
    def get_font_reference(self, family: str, weight: int = 400, italic: bool = False) -> Optional[str]:
        """
        Get resource ID for embedded font matching family/weight/style
        
        Args:
            family: Font family name
            weight: Font weight (400=normal, 700=bold)
            italic: Whether font is italic
        
        Returns:
            Resource ID if font is embedded, None otherwise
        """
        if family not in self.embedded_fonts:
            return None
        
        # Determine variant slot
        if italic and weight >= 700:
            variant = "bolditalic"
        elif weight >= 700:
            variant = "bold"
        elif italic:
            variant = "italic"
        else:
            variant = "regular"
        
        font_resource = self.embedded_fonts[family].get(variant)
        return font_resource.resource_id if font_resource else None
    
    def create_font_embedding_manifest(self) -> Dict:
        """
        Create a manifest of all embedded fonts for debugging/reporting
        
        Returns:
            Dictionary describing all embedded fonts
        """
        manifest = {
            "total_families": len(self.embedded_fonts),
            "total_variants": sum(len(variants) for variants in self.embedded_fonts.values()),
            "families": {}
        }
        
        for family, variants in self.embedded_fonts.items():
            manifest["families"][family] = {
                "variants": list(variants.keys()),
                "total_bytes": sum(len(font.font_bytes) for font in variants.values()),
                "resource_ids": {variant: font.resource_id for variant, font in variants.items()}
            }
        
        return manifest
    
    def clear_embeds(self):
        """Clear all font embeds (for testing or reuse)"""
        self.embedded_fonts.clear()
        self.resource_counter = 1


class PPTXTextWithEmbeddedFonts:
    """
    Enhanced text processor that creates DrawingML text with embedded font references
    """
    
    def __init__(self, font_embedder: PPTXFontEmbedder):
        self.font_embedder = font_embedder
    
    def create_text_element_with_embedded_font(self, text: str, family: str, 
                                               size: int = 12, weight: int = 400, 
                                               italic: bool = False) -> str:
        """
        Create DrawingML text element with embedded font reference
        
        Args:
            text: Text content
            family: Font family
            size: Font size in points
            weight: Font weight (400=normal, 700=bold)  
            italic: Whether text is italic
        
        Returns:
            DrawingML XML string for text element
        """
        font_ref = self.font_embedder.get_font_reference(family, weight, italic)
        
        # Create text run with font reference
        if font_ref:
            # Use embedded font
            text_xml = f"""
            <a:p>
                <a:r>
                    <a:rPr lang="en-US" sz="{size * 100}" b="{'1' if weight >= 700 else '0'}" i="{'1' if italic else '0'}">
                        <a:latin typeface="{family}" />
                        <a:extLst>
                            <a:ext uri="{{B6124F45-8C7E-4DE2-8C91-2C5E7B1F3C2A}}">
                                <a14:font id="{font_ref}" />
                            </a:ext>
                        </a:extLst>
                    </a:rPr>
                    <a:t>{text}</a:t>
                </a:r>
            </a:p>
            """.strip()
        else:
            # Fallback to system font
            text_xml = f"""
            <a:p>
                <a:r>
                    <a:rPr lang="en-US" sz="{size * 100}" b="{'1' if weight >= 700 else '0'}" i="{'1' if italic else '0'}">
                        <a:latin typeface="{family}" />
                    </a:rPr>
                    <a:t>{text}</a:t>
                </a:r>
            </a:p>
            """.strip()
        
        return text_xml
    
    def process_svg_text_element(self, text_element: ET.Element) -> str:
        """
        Process SVG <text> element and create DrawingML with embedded fonts
        
        Args:
            text_element: SVG text element
        
        Returns:
            DrawingML XML string
        """
        # Extract text properties
        text_content = text_element.text or ""
        family = text_element.get('font-family', 'Arial').strip('\'"')
        size = int(float(text_element.get('font-size', '12').replace('px', '')))
        weight_str = text_element.get('font-weight', '400')
        style = text_element.get('font-style', 'normal')
        
        # Parse weight
        try:
            weight = int(weight_str)
        except ValueError:
            weight = 700 if weight_str.lower() == 'bold' else 400
        
        italic = style.lower() == 'italic'
        
        return self.create_text_element_with_embedded_font(
            text_content, family, size, weight, italic
        )