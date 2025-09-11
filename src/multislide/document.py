#!/usr/bin/env python3
"""
Multi-slide document management for SVG to PowerPoint conversion.

This module handles the creation and management of PowerPoint presentations
with multiple slides, supporting various use cases like animation sequences,
multi-page SVG documents, and batch conversions.
"""

import json
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum

from lxml import etree as ET


class SlideType(Enum):
    """Types of slides that can be generated."""
    CONTENT = "content"        # Regular content slide
    TITLE = "title"           # Title slide
    SECTION = "section"       # Section divider slide
    ANIMATION = "animation"   # Animation keyframe slide
    BLANK = "blank"          # Blank slide


@dataclass
class SlideContent:
    """Represents the content and metadata for a single slide."""
    
    slide_id: int
    slide_type: SlideType = SlideType.CONTENT
    title: Optional[str] = None
    shapes_xml: str = ""
    background_xml: str = ""
    animations_xml: str = ""
    notes: str = ""
    layout_id: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate slide content on creation."""
        if self.slide_id < 1:
            raise ValueError("Slide ID must be positive")
        
        # Set default title if not provided
        if not self.title:
            if self.slide_type == SlideType.TITLE:
                self.title = "Title Slide"
            elif self.slide_type == SlideType.SECTION:
                self.title = "Section"
            else:
                self.title = f"Slide {self.slide_id}"
    
    @property
    def slide_filename(self) -> str:
        """Get the filename for this slide."""
        return f"slide{self.slide_id}.xml"
    
    @property
    def slide_path(self) -> str:
        """Get the full path for this slide within PPTX."""
        return f"ppt/slides/{self.slide_filename}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert slide content to dictionary for serialization."""
        return {
            "slide_id": self.slide_id,
            "slide_type": self.slide_type.value,
            "title": self.title,
            "shapes_xml": self.shapes_xml,
            "background_xml": self.background_xml,
            "animations_xml": self.animations_xml,
            "notes": self.notes,
            "layout_id": self.layout_id,
            "metadata": self.metadata
        }


class MultiSlideDocument:
    """
    Manages the creation and assembly of multi-slide PowerPoint presentations.
    
    This class provides the core infrastructure for generating PPTX files with
    multiple slides from various SVG sources and conversion scenarios.
    """
    
    def __init__(self, 
                 title: str = "SVG Presentation",
                 template_path: Optional[Path] = None):
        """
        Initialize multi-slide document.
        
        Args:
            title: Presentation title
            template_path: Path to PPTX template (uses minimal if None)
        """
        self.title = title
        self.template_path = template_path
        self.slides: List[SlideContent] = []
        self.slide_counter = 1
        self.metadata = {
            "created": datetime.now().isoformat(),
            "generator": "SVG2PPTX Multi-Slide",
            "slide_count": 0
        }
        
        # Template management
        self._template_data = None
        self._slide_templates = {}
        
    def add_slide(self, 
                  content: Union[SlideContent, str],
                  slide_type: SlideType = SlideType.CONTENT,
                  title: Optional[str] = None,
                  **kwargs) -> SlideContent:
        """
        Add a new slide to the presentation.
        
        Args:
            content: SlideContent object or DrawingML XML string
            slide_type: Type of slide to create
            title: Slide title
            **kwargs: Additional slide properties
            
        Returns:
            The created SlideContent object
        """
        if isinstance(content, str):
            # Create SlideContent from XML string
            slide = SlideContent(
                slide_id=self.slide_counter,
                slide_type=slide_type,
                title=title,
                shapes_xml=content,
                **kwargs
            )
        elif isinstance(content, SlideContent):
            slide = content
            slide.slide_id = self.slide_counter
        else:
            raise TypeError("Content must be SlideContent or XML string")
        
        self.slides.append(slide)
        self.slide_counter += 1
        self.metadata["slide_count"] = len(self.slides)
        
        return slide
    
    def add_svg_slide(self, 
                      svg_element: ET.Element,
                      context: Any = None,
                      title: Optional[str] = None) -> SlideContent:
        """
        Convert SVG element to slide and add it to presentation.
        
        Args:
            svg_element: SVG element to convert
            context: Conversion context
            title: Slide title
            
        Returns:
            The created SlideContent object
        """
        # This would integrate with existing converter system
        from ..svg2drawingml import convert_svg_to_drawingml
        
        try:
            # Convert SVG to DrawingML shapes
            shapes_xml = convert_svg_to_drawingml(svg_element, context)
            
            # Extract title from SVG if not provided
            if not title:
                title_elem = svg_element.find('.//{http://www.w3.org/2000/svg}title')
                if title_elem is not None and title_elem.text:
                    title = title_elem.text.strip()
            
            return self.add_slide(
                content=shapes_xml,
                title=title,
                metadata={"svg_source": True}
            )
            
        except Exception as e:
            # Create error slide
            error_content = f'<!-- SVG conversion failed: {str(e)} -->'
            return self.add_slide(
                content=error_content,
                title=f"Conversion Error - Slide {self.slide_counter}",
                metadata={"error": str(e)}
            )
    
    def add_animation_sequence(self,
                              keyframes: List[ET.Element],
                              base_title: str = "Animation") -> List[SlideContent]:
        """
        Add multiple slides from animation keyframes.
        
        Args:
            keyframes: List of SVG elements representing animation states
            base_title: Base title for animation slides
            
        Returns:
            List of created SlideContent objects
        """
        created_slides = []
        
        for i, keyframe in enumerate(keyframes):
            slide_title = f"{base_title} - Frame {i + 1}"
            slide = self.add_svg_slide(
                svg_element=keyframe,
                title=slide_title
            )
            slide.slide_type = SlideType.ANIMATION
            slide.metadata["animation_frame"] = i + 1
            slide.metadata["total_frames"] = len(keyframes)
            created_slides.append(slide)
        
        return created_slides
    
    def insert_slide(self, 
                     position: int, 
                     content: Union[SlideContent, str],
                     **kwargs) -> SlideContent:
        """
        Insert slide at specific position.
        
        Args:
            position: Position to insert (1-based)
            content: Slide content
            **kwargs: Additional slide properties
            
        Returns:
            The inserted SlideContent object
        """
        if position < 1 or position > len(self.slides) + 1:
            raise ValueError("Invalid slide position")
        
        # Create slide without incrementing counter
        if isinstance(content, str):
            slide = SlideContent(
                slide_id=position,
                shapes_xml=content,
                **kwargs
            )
        else:
            slide = content
        
        # Insert and renumber slides
        self.slides.insert(position - 1, slide)
        self._renumber_slides()
        
        return slide
    
    def remove_slide(self, slide_id: int) -> bool:
        """
        Remove slide by ID.
        
        Args:
            slide_id: ID of slide to remove
            
        Returns:
            True if slide was removed, False if not found
        """
        for i, slide in enumerate(self.slides):
            if slide.slide_id == slide_id:
                del self.slides[i]
                self._renumber_slides()
                return True
        return False
    
    def get_slide(self, slide_id: int) -> Optional[SlideContent]:
        """Get slide by ID."""
        for slide in self.slides:
            if slide.slide_id == slide_id:
                return slide
        return None
    
    def _renumber_slides(self):
        """Renumber all slides sequentially."""
        for i, slide in enumerate(self.slides, 1):
            slide.slide_id = i
        
        self.slide_counter = len(self.slides) + 1
        self.metadata["slide_count"] = len(self.slides)
    
    def _load_template(self) -> Dict[str, Any]:
        """Load PPTX template data."""
        if self._template_data is not None:
            return self._template_data
        
        if self.template_path and self.template_path.exists():
            # Load custom template
            self._template_data = self._load_custom_template()
        else:
            # Use minimal template
            self._template_data = self._get_minimal_template()
        
        return self._template_data
    
    def _load_custom_template(self) -> Dict[str, Any]:
        """Load custom PPTX template."""
        template_data = {}
        
        try:
            with zipfile.ZipFile(self.template_path, 'r') as zip_file:
                # Load template structure
                for filename in zip_file.namelist():
                    if filename.endswith('.xml') or filename.endswith('.rels'):
                        content = zip_file.read(filename).decode('utf-8')
                        template_data[filename] = content
                
        except Exception as e:
            raise RuntimeError(f"Failed to load template: {e}")
        
        return template_data
    
    def _get_minimal_template(self) -> Dict[str, Any]:
        """Get minimal PPTX template structure."""
        return {
            "[Content_Types].xml": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
    <Default Extension="xml" ContentType="application/xml"/>
    <Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-presentationml.presentation.main+xml"/>
    <Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-presentationml.slideMaster+xml"/>
    <Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-presentationml.slideLayout+xml"/>
</Types>""",
            
            "_rels/.rels": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
</Relationships>""",
            
            "ppt/_rels/presentation.xml.rels": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>
</Relationships>""",
            
            "ppt/presentation.xml": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" 
                xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
    <p:sldMasterIdLst>
        <p:sldMasterId id="2147483648" r:id="rId1"/>
    </p:sldMasterIdLst>
    <p:sldIdLst>
        <!-- Slides will be inserted here -->
    </p:sldIdLst>
    <p:sldSz cx="9144000" cy="6858000" type="screen4x3"/>
    <p:notesSz cx="6858000" cy="9144000"/>
</p:presentation>""",
            
            "ppt/slideMasters/slideMaster1.xml": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldMaster xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
             xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
    <p:cSld>
        <p:bg>
            <p:bgRef idx="1001">
                <a:solidFill>
                    <a:srgbClr val="FFFFFF"/>
                </a:solidFill>
            </p:bgRef>
        </p:bg>
        <p:spTree>
            <p:nvGrpSpPr>
                <p:cNvPr id="1" name=""/>
                <p:cNvGrpSpPr/>
                <p:nvPr/>
            </p:nvGrpSpPr>
            <p:grpSpPr>
                <a:xfrm>
                    <a:off x="0" y="0"/>
                    <a:ext cx="0" cy="0"/>
                    <a:chOff x="0" y="0"/>
                    <a:chExt cx="0" cy="0"/>
                </a:xfrm>
            </p:grpSpPr>
        </p:spTree>
    </p:cSld>
</p:sldMaster>""",
            
            "ppt/slideLayouts/slideLayout1.xml": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldLayout xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
             xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
    <p:cSld name="Content Layout">
        <p:spTree>
            <p:nvGrpSpPr>
                <p:cNvPr id="1" name=""/>
                <p:cNvGrpSpPr/>
                <p:nvPr/>
            </p:nvGrpSpPr>
            <p:grpSpPr>
                <a:xfrm>
                    <a:off x="0" y="0"/>
                    <a:ext cx="0" cy="0"/>
                    <a:chOff x="0" y="0"/>
                    <a:chExt cx="0" cy="0"/>
                </a:xfrm>
            </p:grpSpPr>
        </p:spTree>
    </p:cSld>
</p:sldLayout>"""
        }
    
    def generate_pptx(self, output_path: Path) -> Path:
        """
        Generate final multi-slide PPTX file.
        
        Args:
            output_path: Path where PPTX file should be saved
            
        Returns:
            Path to generated PPTX file
        """
        if not self.slides:
            raise ValueError("No slides to generate")
        
        # Load template
        template_data = self._load_template()
        
        # Generate presentation XML with slide references
        presentation_xml = self._generate_presentation_xml()
        
        # Generate slide relationship XML
        presentation_rels = self._generate_presentation_rels()
        
        # Create PPTX file
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Write template files
            for filename, content in template_data.items():
                if filename not in ["ppt/presentation.xml", "ppt/_rels/presentation.xml.rels"]:
                    zip_file.writestr(filename, content)
            
            # Write updated presentation files
            zip_file.writestr("ppt/presentation.xml", presentation_xml)
            zip_file.writestr("ppt/_rels/presentation.xml.rels", presentation_rels)
            
            # Write slide files
            for slide in self.slides:
                slide_xml = self._generate_slide_xml(slide)
                zip_file.writestr(slide.slide_path, slide_xml)
                
                # Add slide to content types if not template slide
                self._add_slide_content_type(zip_file, slide)
        
        return output_path
    
    def _generate_presentation_xml(self) -> str:
        """Generate presentation.xml with slide references."""
        slide_refs = []
        
        for i, slide in enumerate(self.slides, 2):  # Start from rId2 (rId1 is slide master)
            slide_refs.append(f'<p:sldId id="{255 + slide.slide_id}" r:id="rId{i}"/>')
        
        slide_list = '\n        '.join(slide_refs)
        
        return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" 
                xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
    <p:sldMasterIdLst>
        <p:sldMasterId id="2147483648" r:id="rId1"/>
    </p:sldMasterIdLst>
    <p:sldIdLst>
        {slide_list}
    </p:sldIdLst>
    <p:sldSz cx="9144000" cy="6858000" type="screen4x3"/>
    <p:notesSz cx="6858000" cy="9144000"/>
</p:presentation>"""
    
    def _generate_presentation_rels(self) -> str:
        """Generate presentation relationship XML."""
        relationships = ['<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>']
        
        for i, slide in enumerate(self.slides, 2):
            relationships.append(
                f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/{slide.slide_filename}"/>'
            )
        
        relationships_xml = '\n    '.join(relationships)
        
        return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    {relationships_xml}
</Relationships>"""
    
    def _generate_slide_xml(self, slide: SlideContent) -> str:
        """Generate XML content for individual slide."""
        # Build slide content
        slide_content = slide.shapes_xml or '<!-- No content -->'
        background = slide.background_xml or ''
        title_placeholder = f'<!-- Title: {slide.title} -->' if slide.title else ''
        
        return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" 
       xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
    {title_placeholder}
    <p:cSld>
        {background}
        <p:spTree>
            <p:nvGrpSpPr>
                <p:cNvPr id="1" name=""/>
                <p:cNvGrpSpPr/>
                <p:nvPr/>
            </p:nvGrpSpPr>
            <p:grpSpPr>
                <a:xfrm>
                    <a:off x="0" y="0"/>
                    <a:ext cx="0" cy="0"/>
                    <a:chOff x="0" y="0"/>
                    <a:chExt cx="0" cy="0"/>
                </a:xfrm>
            </p:grpSpPr>
            {slide_content}
        </p:spTree>
    </p:cSld>
    <p:clrMapOvr>
        <a:masterClrMapping/>
    </p:clrMapOvr>
</p:sld>"""
    
    def _add_slide_content_type(self, zip_file: zipfile.ZipFile, slide: SlideContent):
        """Add slide content type to [Content_Types].xml if needed."""
        # This would need to update the content types XML
        # For now, we assume the template handles standard slide types
        pass
    
    def export_metadata(self, output_path: Optional[Path] = None) -> Dict[str, Any]:
        """
        Export presentation metadata.
        
        Args:
            output_path: Optional path to save metadata JSON
            
        Returns:
            Metadata dictionary
        """
        metadata = {
            **self.metadata,
            "title": self.title,
            "slides": [slide.to_dict() for slide in self.slides]
        }
        
        if output_path:
            with open(output_path, 'w') as f:
                json.dump(metadata, f, indent=2)
        
        return metadata