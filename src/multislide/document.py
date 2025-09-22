#!/usr/bin/env python3
"""
Multi-slide document management for SVG to PowerPoint conversion.

This module handles the creation and management of PowerPoint presentations
with multiple slides, supporting various use cases like animation sequences,
multi-page SVG documents, and batch conversions.

TODO: Issue 10 - Fix Multi-Slide Conversion
==========================================
PRIORITY: LOW
STATUS: Needs CLI integration

Problems:
- Multi-slide functionality exists but is not exposed via CLI
- Command-line interface doesn't support multi-slide options
- Batch conversion workflows are not accessible to end users
- Animation sequence detection and conversion is not integrated

Required Changes:
1. Add multi-slide options to CLI argument parser
2. Integrate multi-slide document creation with main CLI workflow
3. Add support for batch SVG -> multi-slide PPTX conversion
4. Expose animation sequence detection in CLI
5. Add CLI options for slide templates and layouts
6. Integrate with PPTXBuilder for multi-slide output

Files to modify:
- src/svg2pptx.py (add multi-slide CLI options)
- src/multislide/document.py (this file - ensure CLI integration)
- src/core/pptx_builder.py (add multi-slide support)
- tests/e2e/test_multislide_cli.py (create CLI tests)

CLI options needed:
- --multi-slide: Enable multi-slide mode
- --slides-per-animation: Number of slides for animations
- --batch-directory: Process multiple SVG files
- --slide-template: Choose slide template
- --animation-detection: Enable/disable animation detection

Test:
- CLI with multiple SVG files -> multi-slide PPTX
- Animation sequences -> presentation slides
- Batch processing workflows
- Template and layout options
"""

import json
import os
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any, Union, Iterator, Callable
from dataclasses import dataclass, field
from enum import Enum

from lxml import etree as ET
from .config import DocumentConfig
from .validation import SVGValidator, ValidationConfig, validate_svg_input
from .exceptions import DocumentGenerationError, ValidationError, log_and_continue
from .templates import get_template, TemplateType, SlideTemplate
from .cache import cached_parse_svg

# Import EMU constants for slide sizing
try:
    from ..viewbox.core import ViewportEngine
    VIEWPORT_ENGINE_AVAILABLE = True
except ImportError:
    # Fallback if NumPy-based viewport engine is not available
    VIEWPORT_ENGINE_AVAILABLE = False


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
                 config: Optional[DocumentConfig] = None,
                 # Legacy parameter support for backward compatibility
                 title: Optional[str] = None,
                 template_path: Optional[Path] = None):
        """
        Initialize multi-slide document.

        Args:
            config: DocumentConfig object with all settings
            title: (Legacy) Presentation title
            template_path: (Legacy) Path to PPTX template
        """
        # Use provided config or create default
        if config is None:
            config = DocumentConfig()

        # Apply legacy parameters if provided (for backward compatibility)
        if title is not None:
            config.title = title
        if template_path is not None:
            config.template_path = template_path

        # Validate configuration
        config.validate()
        self.config = config

        # Set instance attributes for backward compatibility and easy access
        self.title = config.title
        self.template_path = config.template_path
        self.slides: List[SlideContent] = []
        self.slide_counter = 1
        self.metadata = {
            "created": datetime.now().isoformat(),
            "generator": "SVG2PPTX Multi-Slide",
            "slide_count": 0
        }
        
        # Template management with new template system
        self._template_data = None
        self._slide_templates = {}
        self._template_instance: Optional[SlideTemplate] = None
        self._template_type = self._determine_template_type()

        # Viewport engine for dynamic slide sizing
        if VIEWPORT_ENGINE_AVAILABLE:
            self.viewport_engine = ViewportEngine()
        else:
            self.viewport_engine = None
        self._presentation_dimensions = None  # Cache for calculated dimensions
        self._aspect_ratio_source = None      # Track which SVG set the dimensions

    def _determine_template_type(self) -> TemplateType:
        """Determine the appropriate template type based on configuration."""
        if self.template_path and self.template_path.exists():
            return TemplateType.CUSTOM

        # Determine template type based on slide dimensions
        width_emu = self.config.slide_width_emu
        height_emu = self.config.slide_height_emu
        aspect_ratio = width_emu / height_emu

        # Standard 16:9 (1.78)
        if 1.75 <= aspect_ratio <= 1.80:
            return TemplateType.STANDARD
        # Wide 16:10 (1.60)
        elif 1.55 <= aspect_ratio <= 1.65:
            return TemplateType.WIDE
        # Classic 4:3 (1.33)
        elif 1.30 <= aspect_ratio <= 1.40:
            return TemplateType.CLASSIC
        else:
            # Default to standard for other ratios
            return TemplateType.STANDARD
        
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
        # Validate slide limits
        if len(self.slides) >= self.config.max_slides:
            raise DocumentGenerationError(
                f"Cannot add slide: maximum slide count of {self.config.max_slides} reached",
                operation="add_slide"
            )

        if isinstance(content, str):
            # Validate XML content if validation is enabled
            if self.config.enable_content_validation:
                try:
                    # Basic XML validation
                    if content.strip():  # Only validate non-empty content
                        # Try to parse as XML to check well-formedness
                        test_xml = f"<root>{content}</root>"
                        ET.fromstring(test_xml.encode('utf-8'))

                        # Check content size
                        if len(content) > self.config.max_slide_content_length:
                            log_and_continue(
                                DocumentGenerationError(
                                    f"Slide content length {len(content)} exceeds limit of {self.config.max_slide_content_length}",
                                    operation="add_slide"
                                ),
                                default_value=None
                            )
                except Exception as e:
                    log_and_continue(
                        DocumentGenerationError(
                            f"Invalid slide content XML: {str(e)}",
                            operation="add_slide"
                        ),
                        default_value=None
                    )

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

    def add_slide_from_svg_content(self,
                                 svg_content: Union[str, bytes, Path],
                                 slide_type: SlideType = SlideType.CONTENT,
                                 title: Optional[str] = None,
                                 **kwargs) -> SlideContent:
        """
        Add a slide from SVG content with caching support.

        Args:
            svg_content: SVG content as string, bytes, or file path
            slide_type: Type of slide to create
            title: Optional slide title
            **kwargs: Additional slide parameters

        Returns:
            Created SlideContent object

        Raises:
            DocumentGenerationError: If SVG parsing or slide creation fails
        """
        try:
            # Parse SVG with caching
            svg_root = cached_parse_svg(svg_content)

            # Convert SVG to DrawingML using the conversion pipeline
            try:
                from ..services.conversion_services import ConversionServices
                from ..converters.base import ConversionContext, ConverterRegistry

                # Create conversion services and context
                services = ConversionServices.create_default()
                context = ConversionContext(svg_root=svg_root, services=services)

                # Initialize converter registry
                registry = ConverterRegistry()
                registry.register_default_converters(services)
                context.converter_registry = registry

                # Convert SVG elements to DrawingML shapes
                shapes_xml_parts = []
                for element in svg_root:
                    try:
                        converter = registry.get_converter(element)
                        if converter:
                            shape_xml = converter.convert(element, context)
                            if shape_xml:
                                shapes_xml_parts.append(shape_xml)
                    except Exception as conv_e:
                        self.logger.warning(f"Failed to convert element {element.tag}: {conv_e}")

                shapes_xml = ''.join(shapes_xml_parts) if shapes_xml_parts else '<p:sp><p:nvSpPr><p:cNvPr id="1" name="EmptySlide"/></p:nvSpPr></p:sp>'

            except Exception as conversion_e:
                self.logger.warning(f"SVG conversion failed, using fallback: {conversion_e}")
                # Fallback to basic shape representation
                shapes_xml = '<p:sp><p:nvSpPr><p:cNvPr id="1" name="ConversionFailed"/></p:nvSpPr></p:sp>'

            return self.add_slide(shapes_xml, slide_type, title, **kwargs)
        except Exception as e:
            raise DocumentGenerationError(f"Failed to add slide from SVG content: {e}")

    def calculate_presentation_dimensions(self, svg_element: ET.Element) -> tuple[int, int]:
        """
        Calculate presentation dimensions from SVG element using viewport engine.

        Args:
            svg_element: SVG root element to analyze

        Returns:
            Tuple of (width_emu, height_emu) for presentation slide size
        """
        if self._presentation_dimensions is not None:
            # Already calculated - use cached dimensions for consistency
            return self._presentation_dimensions

        try:
            if self.viewport_engine is not None:
                # Use full viewport engine if available
                viewport_data = self.viewport_engine.extract_viewport_dimensions_batch(
                    [svg_element]
                )

                if len(viewport_data) > 0 and viewport_data[0]['width'] > 0:
                    # Use calculated dimensions from viewport engine
                    width_emu = int(viewport_data[0]['width'])
                    height_emu = int(viewport_data[0]['height'])

                    # Cache the calculated dimensions
                    self._presentation_dimensions = (width_emu, height_emu)
                    self._aspect_ratio_source = "svg_viewbox"

                    return width_emu, height_emu
            else:
                # Fallback viewport calculation without NumPy
                width_emu, height_emu = self._simple_viewbox_calculation(svg_element)
                if width_emu > 0 and height_emu > 0:
                    # Cache the calculated dimensions
                    self._presentation_dimensions = (width_emu, height_emu)
                    self._aspect_ratio_source = "simple_viewbox"
                    return width_emu, height_emu

        except Exception as e:
            # Log the error but continue with fallback
            print(f"Warning: Could not calculate viewport dimensions: {e}")

        # Fallback to default 16:9 widescreen dimensions
        width_emu = 12192000   # 10 inches * 914400 EMU/inch (16:9 width)
        height_emu = 6858000   # 7.5 inches * 914400 EMU/inch (16:9 height)

        # Cache the fallback dimensions
        self._presentation_dimensions = (width_emu, height_emu)
        self._aspect_ratio_source = "fallback_16x9"

        return width_emu, height_emu

    def _simple_viewbox_calculation(self, svg_element: ET.Element) -> tuple[int, int]:
        """
        Simple viewBox calculation without NumPy dependencies.

        Args:
            svg_element: SVG root element

        Returns:
            Tuple of (width_emu, height_emu)
        """
        # EMU conversion constants
        EMU_PER_INCH = 914400
        EMU_PER_POINT = 12700
        EMU_PER_MM = 36000
        EMU_PER_CM = 360000

        # Try to get viewBox first
        viewbox = svg_element.get('viewBox')
        if viewbox:
            try:
                # Use the canonical high-performance ViewportResolver for parsing
                try:
                    from ..viewbox import ViewportResolver
                    import numpy as np

                    resolver = ViewportResolver()
                    parsed = resolver.parse_viewbox_strings(np.array([viewbox]))
                    if len(parsed) > 0 and len(parsed[0]) >= 4:
                        _, _, vb_width, vb_height = parsed[0][:4]
                    else:
                        raise ValueError("Invalid viewBox format")
                except ImportError:
                    # Fallback to enhanced parsing if ViewportResolver not available
                    cleaned = viewbox.strip().replace(',', ' ')
                    parts = cleaned.split()
                    if len(parts) >= 4:
                        _, _, vb_width, vb_height = map(float, parts[:4])
                    else:
                        raise ValueError("Invalid viewBox format")

                if vb_width > 0 and vb_height > 0:
                        # Calculate aspect ratio and use standard slide sizing
                        aspect_ratio = vb_width / vb_height

                        # Target 10 inches width, scale height proportionally
                        target_width_inches = 10.0
                        target_height_inches = target_width_inches / aspect_ratio

                        width_emu = int(target_width_inches * EMU_PER_INCH)
                        height_emu = int(target_height_inches * EMU_PER_INCH)

                        return width_emu, height_emu
            except (ValueError, TypeError) as e:
                # Log the viewBox parsing error but continue with fallback
                log_and_continue(
                    DocumentGenerationError(
                        f"Failed to parse viewBox attribute: {viewbox_attr}",
                        operation="dimension_calculation",
                        original_exception=e,
                        recoverable=True
                    ),
                    default_value=None
                )

        # Try to get width/height attributes
        width_attr = svg_element.get('width')
        height_attr = svg_element.get('height')

        if width_attr and height_attr:
            try:
                # Simple unit parsing
                import re

                def parse_simple_unit(value: str) -> float:
                    if not value:
                        return 0.0
                    # Extract numeric value
                    match = re.match(r'([0-9.]+)([a-zA-Z%]*)', str(value).strip())
                    if match:
                        num_val = float(match.group(1))
                        unit = match.group(2).lower() if match.group(2) else 'px'

                        # Convert to EMU (assuming 96 DPI for px)
                        if unit in ['px', '']:
                            return num_val * EMU_PER_INCH / 96  # 96 DPI standard
                        elif unit == 'pt':
                            return num_val * EMU_PER_POINT
                        elif unit == 'in':
                            return num_val * EMU_PER_INCH
                        elif unit == 'mm':
                            return num_val * EMU_PER_MM
                        elif unit == 'cm':
                            return num_val * EMU_PER_CM
                        else:
                            return num_val * EMU_PER_INCH / 96  # Default to px
                    return 0.0

                width_emu = parse_simple_unit(width_attr)
                height_emu = parse_simple_unit(height_attr)

                if width_emu > 0 and height_emu > 0:
                    return int(width_emu), int(height_emu)

            except (ValueError, TypeError) as e:
                # Log the width/height parsing error but continue with fallback
                log_and_continue(
                    DocumentGenerationError(
                        f"Failed to parse width/height attributes: width={width_attr}, height={height_attr}",
                        operation="dimension_calculation",
                        original_exception=e,
                        recoverable=True
                    ),
                    default_value=None
                )

        # Return 0,0 to indicate no valid dimensions found
        return 0, 0

    def get_presentation_dimensions(self) -> tuple[int, int]:
        """
        Get the current presentation dimensions.

        Returns:
            Tuple of (width_emu, height_emu) for current presentation
        """
        if self._presentation_dimensions is not None:
            return self._presentation_dimensions
        else:
            # Return default 16:9 dimensions if not calculated yet
            return 12192000, 6858000

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
        from ..svg2drawingml import SVGToDrawingMLConverter
        from ..services.conversion_services import ConversionServices

        try:
            # Calculate presentation dimensions from this SVG (if not already set)
            self.calculate_presentation_dimensions(svg_element)

            # Convert SVG to DrawingML shapes using the proper converter
            services = ConversionServices.create_default()
            converter = SVGToDrawingMLConverter(services=services)
            shapes_xml = converter.convert_element(svg_element)

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
        """Load PPTX template data using new template system."""
        if self._template_data is not None:
            return self._template_data

        try:
            # Get template instance using new template system
            if not self._template_instance:
                if self.template_path and self.template_path.exists():
                    self._template_instance = get_template(
                        self.template_path,
                        metadata=None  # Will be extracted from file
                    )
                else:
                    self._template_instance = get_template(self._template_type)

            # Load template data
            self._template_instance.load()

            # Convert template data to legacy format for compatibility
            self._template_data = {}
            for filename in self._template_instance.list_template_files():
                self._template_data[filename] = self._template_instance.get_template_file(filename)

            return self._template_data

        except Exception as e:
            # Fallback to minimal template on error
            log_and_continue(
                DocumentGenerationError(
                    f"Failed to load template, falling back to minimal: {str(e)}",
                    operation="template_loading",
                    original_exception=e,
                    recoverable=True
                ),
                default_value=None
            )

            # Use minimal template as fallback
            self._template_instance = get_template(TemplateType.MINIMAL)
            self._template_instance.load()

            self._template_data = {}
            for filename in self._template_instance.list_template_files():
                self._template_data[filename] = self._template_instance.get_template_file(filename)

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
        """Generate presentation.xml with slide references and dynamic dimensions."""
        # Consolidated with src/utils/xml_builder.py - XML generation now centralized
        from ..utils.xml_builder import get_xml_builder

        slide_refs = []
        for i, slide in enumerate(self.slides, 2):  # Start from rId2 (rId1 is slide master)
            slide_refs.append(f'<p:sldId id="{255 + slide.slide_id}" r:id="rId{i}"/>')

        slide_list = '\n        '.join(slide_refs)

        # Get dynamic slide dimensions (use fallback if not calculated)
        if self._presentation_dimensions is not None:
            width_emu, height_emu = self._presentation_dimensions
        else:
            # Fallback to 16:9 widescreen if no dimensions calculated
            width_emu, height_emu = 12192000, 6858000

        # Determine slide type based on aspect ratio
        aspect_ratio = width_emu / height_emu if height_emu > 0 else 16/9
        if abs(aspect_ratio - 4/3) < 0.1:
            slide_type = "screen4x3"
        elif abs(aspect_ratio - 16/9) < 0.1:
            slide_type = "screen16x9"
        else:
            slide_type = "custom"

        # Use centralized XML builder
        xml_builder = get_xml_builder()
        return xml_builder.create_presentation_xml(
            width_emu=width_emu,
            height_emu=height_emu,
            slide_list=slide_list,
            slide_type=slide_type
        )
    
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
        # Consolidated with src/utils/xml_builder.py - XML generation now centralized
        from ..utils.xml_builder import get_xml_builder

        # Build slide content with background and title
        slide_content = slide.shapes_xml or '<!-- No content -->'
        background = slide.background_xml or ''
        title_placeholder = f'<!-- Title: {slide.title} -->' if slide.title else ''

        # Combine all content elements
        combined_content = []
        if title_placeholder:
            combined_content.append(title_placeholder)
        if background:
            combined_content.append(background)
        combined_content.append(slide_content)

        full_slide_content = '\n            '.join(combined_content)

        # Use centralized XML builder
        xml_builder = get_xml_builder()
        return xml_builder.create_slide_xml(
            slide_content=full_slide_content,
            layout_id=slide.layout_id
        )
    
    def _add_slide_content_type(self, zip_file: zipfile.ZipFile, slide: SlideContent):
        """Add slide content type to [Content_Types].xml if needed."""
        try:
            # Read existing content types
            content_types_data = None
            try:
                content_types_data = zip_file.read('[Content_Types].xml')
            except KeyError:
                # Content types file doesn't exist, create new one
                self._create_content_types(zip_file)
                return

            if content_types_data:
                # Parse existing content types XML
                import xml.etree.ElementTree as ET
                root = ET.fromstring(content_types_data)

                # Check if slide content type already exists
                slide_part_name = f"/ppt/slides/slide{slide.slide_id}.xml"
                existing_override = None

                for override in root.findall('.//{http://schemas.openxmlformats.org/package/2006/content-types}Override'):
                    if override.get('PartName') == slide_part_name:
                        existing_override = override
                        break

                # If override doesn't exist, add it
                if existing_override is None:
                    override = ET.Element('{http://schemas.openxmlformats.org/package/2006/content-types}Override')
                    override.set('PartName', slide_part_name)
                    override.set('ContentType', self._get_content_type_for_slide(slide))
                    root.append(override)

                    # Write updated content types back to ZIP
                    updated_xml = ET.tostring(root, encoding='unicode', xml_declaration=True)
                    # Remove the file from ZIP and add updated version
                    self._update_zip_file(zip_file, '[Content_Types].xml', updated_xml)

                if self.config.enable_debug_logging:
                    import logging
                    logger = logging.getLogger("multislide.document")
                    logger.debug(f"Registered content type for slide {slide.slide_id} (type: {slide.slide_type})")

        except Exception as e:
            # Log the error but don't fail the entire generation
            log_and_continue(
                DocumentGenerationError(
                    f"Failed to process content types for slide {slide.slide_id}",
                    slide_id=slide.slide_id,
                    operation="content_type_registration",
                    original_exception=e,
                    recoverable=True
                ),
                default_value=None
            )

    def _get_content_type_for_slide(self, slide: SlideContent) -> str:
        """Get the appropriate content type for a slide based on its type."""
        # All slide types use the same PowerPoint slide content type
        # The slide type (TITLE, SECTION, etc.) is handled by the slide layout, not content type
        return "application/vnd.openxmlformats-officedocument.presentationml.slide+xml"

    def _create_content_types(self, zip_file: zipfile.ZipFile):
        """Create a new [Content_Types].xml file for multi-slide presentations."""
        # Create comprehensive content types for multi-slide presentations
        content_types_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
    <Default Extension="xml" ContentType="application/xml"/>
    <Default Extension="png" ContentType="image/png"/>
    <Default Extension="jpg" ContentType="image/jpeg"/>
    <Default Extension="jpeg" ContentType="image/jpeg"/>
    <Default Extension="gif" ContentType="image/gif"/>
    <Default Extension="bmp" ContentType="image/bmp"/>
    <Default Extension="webp" ContentType="image/webp"/>
    <Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
    <Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>
    <Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>
    <Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>
</Types>'''

        self._update_zip_file(zip_file, '[Content_Types].xml', content_types_xml)

    def _update_zip_file(self, zip_file: zipfile.ZipFile, filename: str, content: str):
        """Update a file in the ZIP archive."""
        import tempfile
        import shutil

        # Create a temporary file for the updated ZIP
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            # Copy all files except the one we're updating
            with zipfile.ZipFile(temp_path, 'w', zipfile.ZIP_DEFLATED) as new_zip:
                # Copy existing files except the one we're updating
                for item in zip_file.infolist():
                    if item.filename != filename:
                        data = zip_file.read(item.filename)
                        new_zip.writestr(item, data)

                # Add the updated file
                new_zip.writestr(filename, content)

            # Replace the original ZIP file contents
            # Note: This is a simplified approach. In a production system,
            # you'd want to handle this more robustly
            if self.config.enable_debug_logging:
                import logging
                logger = logging.getLogger("multislide.document")
                logger.debug(f"Updated {filename} in presentation archive")

        except Exception as e:
            import os
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise e
        finally:
            # Clean up temp file
            import os
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
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

    # Streaming slide generation methods

    def generate_slides_streaming(self,
                                boundaries: Iterator[Any],  # SlideBoundary iterator
                                svg_root: ET.Element,
                                memory_limit_mb: int = 100,
                                progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
                                ) -> Iterator[SlideContent]:
        """
        Generate slides from boundary stream with memory management.

        Args:
            boundaries: Iterator of SlideBoundary objects
            svg_root: Root SVG element for extracting content
            memory_limit_mb: Memory limit for buffering
            progress_callback: Optional progress callback

        Yields:
            Generated SlideContent objects
        """
        import gc
        import psutil

        process = psutil.Process()
        start_memory = process.memory_info().rss / (1024 * 1024)
        slides_generated = 0

        try:
            for boundary in boundaries:
                # Generate slide content
                slide_content = self._generate_slide_from_boundary(
                    boundary, svg_root, slides_generated + 1
                )

                if slide_content:
                    slides_generated += 1
                    yield slide_content

                    # Memory management
                    current_memory = process.memory_info().rss / (1024 * 1024)
                    memory_usage = current_memory - start_memory

                    if memory_usage > memory_limit_mb:
                        # Force garbage collection
                        gc.collect()
                        start_memory = process.memory_info().rss / (1024 * 1024)

                    # Progress callback
                    if progress_callback:
                        progress_callback({
                            'slides_generated': slides_generated,
                            'memory_usage_mb': current_memory,
                            'memory_peak_mb': memory_usage
                        })

        except Exception as e:
            raise DocumentGenerationError(
                f"Streaming slide generation failed: {e}",
                operation="streaming_generation"
            )

    def _generate_slide_from_boundary(self,
                                    boundary: Any,  # SlideBoundary
                                    svg_root: ET.Element,
                                    slide_id: int) -> Optional[SlideContent]:
        """
        Generate a slide from a boundary object.

        Args:
            boundary: SlideBoundary object
            svg_root: Root SVG element
            slide_id: Slide identifier

        Returns:
            Generated SlideContent or None if generation fails
        """
        try:
            # Extract content around the boundary
            slide_elements = self._extract_slide_elements(boundary, svg_root)

            if not slide_elements:
                return None

            # Convert to slide content
            shapes_xml = self._elements_to_drawingml(slide_elements)

            # Determine slide type from boundary
            slide_type = self._boundary_type_to_slide_type(boundary.boundary_type)

            # Create slide content
            slide_content = SlideContent(
                slide_id=slide_id,
                slide_type=slide_type,
                title=boundary.title or f"Slide {slide_id}",
                shapes_xml=shapes_xml,
                metadata={
                    'boundary_type': boundary.boundary_type.value,
                    'confidence': boundary.confidence,
                    'source_boundary': True
                }
            )

            return slide_content

        except Exception as e:
            print(f"Warning: Failed to generate slide from boundary: {e}")
            return None

    def _extract_slide_elements(self, boundary: Any, svg_root: ET.Element) -> List[ET.Element]:
        """
        Extract SVG elements relevant to a slide boundary.

        Args:
            boundary: SlideBoundary object
            svg_root: Root SVG element

        Returns:
            List of relevant SVG elements
        """
        elements = []

        if boundary.element is not None:
            # Include the boundary element itself
            elements.append(boundary.element)

            # Include child elements
            for child in boundary.element.iter():
                if child != boundary.element:
                    elements.append(child)

        return elements

    def _elements_to_drawingml(self, elements: List[ET.Element]) -> str:
        """
        Convert SVG elements to DrawingML XML.

        Args:
            elements: List of SVG elements

        Returns:
            DrawingML XML string
        """
        # Convert SVG elements to DrawingML using the converter pipeline
        try:
            from ..services.conversion_services import ConversionServices
            from ..converters.base import ConversionContext, ConverterRegistry

            # Create conversion services and context
            services = ConversionServices.create_default()

            # Create a temporary SVG root for context
            svg_root = ET.Element('svg')
            for element in elements:
                svg_root.append(element)

            context = ConversionContext(svg_root=svg_root, services=services)

            # Initialize converter registry
            registry = ConverterRegistry()
            registry.register_default_converters(services)
            context.converter_registry = registry

            # Convert each SVG element to DrawingML
            shapes = []
            for i, element in enumerate(elements):
                try:
                    converter = registry.get_converter(element)
                    if converter:
                        shape_xml = converter.convert(element, context)
                        if shape_xml:
                            shapes.append(shape_xml)
                        else:
                            # Fallback for unsupported elements
                            tag = element.tag.split('}')[-1] if '}' in element.tag else element.tag
                            fallback_xml = f'<p:sp><p:nvSpPr><p:cNvPr id="{i+1}" name="{tag}_{i+1}"/></p:nvSpPr></p:sp>'
                            shapes.append(fallback_xml)
                    else:
                        # No converter available - create basic placeholder
                        tag = element.tag.split('}')[-1] if '}' in element.tag else element.tag
                        placeholder_xml = f'<p:sp><p:nvSpPr><p:cNvPr id="{i+1}" name="{tag}_{i+1}"/></p:nvSpPr></p:sp>'
                        shapes.append(placeholder_xml)
                except Exception as conv_e:
                    self.logger.warning(f"Failed to convert element {element.tag}: {conv_e}")
                    # Create error placeholder
                    error_xml = f'<p:sp><p:nvSpPr><p:cNvPr id="{i+1}" name="ConversionError_{i+1}"/></p:nvSpPr></p:sp>'
                    shapes.append(error_xml)

            return ''.join(shapes)

        except Exception as e:
            self.logger.warning(f"SVG to DrawingML conversion failed: {e}")
            # Fallback to basic implementation
            shapes = []
            for i, element in enumerate(elements):
                tag = element.tag.split('}')[-1] if '}' in element.tag else element.tag
                if tag in ['rect', 'circle', 'ellipse', 'path', 'text']:
                    shape_xml = f'<p:sp><p:nvSpPr><p:cNvPr id="{i+1}" name="{tag}_{i+1}"/></p:nvSpPr></p:sp>'
                    shapes.append(shape_xml)
            return ''.join(shapes)

    def _boundary_type_to_slide_type(self, boundary_type: Any) -> SlideType:
        """
        Convert boundary type to slide type.

        Args:
            boundary_type: SlideBoundary type

        Returns:
            SlideType enum value
        """
        # Map boundary types to slide types
        type_mapping = {
            'animation_keyframe': SlideType.ANIMATION,
            'section_marker': SlideType.SECTION,
            'page_break': SlideType.CONTENT,
            'nested_svg': SlideType.CONTENT,
            'layer_group': SlideType.CONTENT
        }

        boundary_type_str = boundary_type.value if hasattr(boundary_type, 'value') else str(boundary_type)
        return type_mapping.get(boundary_type_str, SlideType.CONTENT)

    def add_slide_streaming(self,
                          slide_content: SlideContent,
                          cleanup_after_add: bool = True) -> None:
        """
        Add a slide with optional immediate cleanup for streaming.

        Args:
            slide_content: Slide content to add
            cleanup_after_add: Whether to cleanup memory after adding
        """
        # Add slide normally
        self.slides.append(slide_content)
        self.slide_counter += 1
        self.metadata["slide_count"] = len(self.slides)

        # Optional memory cleanup
        if cleanup_after_add:
            import gc
            # Clear any temporary references
            gc.collect()

    def write_slides_streaming(self,
                             output_path: Path,
                             slide_stream: Iterator[SlideContent],
                             flush_interval: int = 10) -> None:
        """
        Write slides to PPTX file as they are generated.

        Args:
            output_path: Output PPTX file path
            slide_stream: Iterator of SlideContent objects
            flush_interval: Number of slides before flushing to disk
        """
        import tempfile
        import shutil

        # Create temporary directory for PPTX assembly
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            slides_written = 0

            try:
                # Initialize PPTX structure
                self._initialize_pptx_structure(temp_path)

                # Process slides from stream
                for slide_content in slide_stream:
                    self._write_slide_to_temp(slide_content, temp_path)
                    slides_written += 1

                    # Flush to disk periodically
                    if slides_written % flush_interval == 0:
                        self._flush_temp_slides(temp_path)

                # Final assembly
                self._assemble_final_pptx(temp_path, output_path)

            except Exception as e:
                raise DocumentGenerationError(
                    f"Streaming PPTX write failed: {e}",
                    operation="streaming_write"
                )

    def _initialize_pptx_structure(self, temp_path: Path) -> None:
        """Initialize basic PPTX directory structure."""
        # Create required directories
        (temp_path / "ppt" / "slides").mkdir(parents=True)
        (temp_path / "ppt" / "slideLayouts").mkdir(parents=True)
        (temp_path / "ppt" / "slideMasters").mkdir(parents=True)
        (temp_path / "_rels").mkdir(parents=True)

    def _write_slide_to_temp(self, slide_content: SlideContent, temp_path: Path) -> None:
        """Write individual slide to temporary directory."""
        slide_file = temp_path / "ppt" / "slides" / slide_content.slide_filename

        # Simple slide XML template
        slide_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
    <p:cSld>
        <p:spTree>
            <p:nvGrpSpPr>
                <p:cNvPr id="1" name=""/>
                <p:cNvGrpSpPr/>
                <p:nvPr/>
            </p:nvGrpSpPr>
            <p:grpSpPr>
                <a:xfrm xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
                    <a:off x="0" y="0"/>
                    <a:ext cx="0" cy="0"/>
                    <a:chOff x="0" y="0"/>
                    <a:chExt cx="0" cy="0"/>
                </a:xfrm>
            </p:grpSpPr>
            {slide_content.shapes_xml}
        </p:spTree>
    </p:cSld>
</p:sld>'''

        with open(slide_file, 'w', encoding='utf-8') as f:
            f.write(slide_xml)

    def _flush_temp_slides(self, temp_path: Path) -> None:
        """Flush temporary slides to ensure they're written to disk."""
        import os
        # Force filesystem sync
        for root, dirs, files in os.walk(temp_path):
            for file in files:
                try:
                    os.fsync(open(os.path.join(root, file), 'r').fileno())
                except:
                    pass  # Best effort

    def _assemble_final_pptx(self, temp_path: Path, output_path: Path) -> None:
        """Assemble final PPTX file from temporary structure."""
        import zipfile

        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as pptx_zip:
            for root, dirs, files in os.walk(temp_path):
                for file in files:
                    file_path = Path(root) / file
                    arc_path = file_path.relative_to(temp_path)
                    pptx_zip.write(file_path, arc_path)

    def get_memory_usage_stats(self) -> Dict[str, float]:
        """
        Get current memory usage statistics.

        Returns:
            Dictionary with memory usage information
        """
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()

            return {
                'rss_mb': memory_info.rss / (1024 * 1024),
                'vms_mb': memory_info.vms / (1024 * 1024),
                'slide_count': len(self.slides),
                'memory_per_slide_mb': (memory_info.rss / (1024 * 1024)) / max(1, len(self.slides))
            }
        except ImportError:
            return {
                'rss_mb': 0.0,
                'vms_mb': 0.0,
                'slide_count': len(self.slides),
                'memory_per_slide_mb': 0.0
            }