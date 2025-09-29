#!/usr/bin/env python3
"""
Centralized XML Builder Utilities for SVG2PPTX.

Consolidates XML generation functionality from across the codebase to eliminate
duplication and provide consistent, reusable XML building patterns.
"""

import logging
from typing import Dict, List, Optional, Any, Union
from xml.sax.saxutils import escape
from lxml import etree as ET

logger = logging.getLogger(__name__)


class XMLBuilder:
    """
    Centralized XML builder for PowerPoint and Office Open XML generation.

    Consolidates XML generation patterns from:
    - src/converters/animation_templates.py
    - [Removed] Old multislide implementation
    - src/emf_packaging.py
    - src/ooxml_templates.py
    """

    # Common XML namespaces used throughout the application
    NAMESPACES = {
        'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
        'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
        'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
        'content_types': 'http://schemas.openxmlformats.org/package/2006/content-types',
        'relationships': 'http://schemas.openxmlformats.org/package/2006/relationships'
    }

    def __init__(self):
        """Initialize XML builder with common settings."""
        self._id_counter = 1

    def get_next_id(self) -> int:
        """Get next unique ID for XML elements."""
        current_id = self._id_counter
        self._id_counter += 1
        return current_id

    def escape_xml(self, text: str) -> str:
        """Safely escape text for XML content."""
        if not text:
            return ""
        return escape(str(text))

    def create_namespace_declaration(self, namespaces: Optional[Dict[str, str]] = None) -> str:
        """
        Create XML namespace declarations.

        Args:
            namespaces: Optional custom namespaces, defaults to common ones

        Returns:
            Formatted namespace declaration string
        """
        if namespaces is None:
            namespaces = self.NAMESPACES

        declarations = []
        for prefix, uri in namespaces.items():
            if prefix == 'content_types' or prefix == 'relationships':
                # These are default namespaces
                declarations.append(f'xmlns="{uri}"')
            else:
                declarations.append(f'xmlns:{prefix}="{uri}"')

        return ' '.join(declarations)

    def create_presentation_xml(self, width_emu: int, height_emu: int,
                              slide_list: str = "", slide_type: str = "screen4x3") -> str:
        """
        Create PowerPoint presentation.xml content.

        Consolidated presentation XML generation for multi-page presentations.

        Args:
            width_emu: Slide width in EMU
            height_emu: Slide height in EMU
            slide_list: XML for slide ID list
            slide_type: Slide size type (screen4x3, screen16x9, etc.)

        Returns:
            Complete presentation.xml content
        """
        # Calculate notes size (standard aspect ratio)
        notes_width = height_emu
        notes_height = int(height_emu * 4/3)

        namespaces = self.create_namespace_declaration({
            'p': self.NAMESPACES['p'],
            'r': self.NAMESPACES['r']
        })

        return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation {namespaces}>
    <p:sldMasterIdLst>
        <p:sldMasterId id="2147483648" r:id="rId1"/>
    </p:sldMasterIdLst>
    <p:sldIdLst>
        {slide_list}
    </p:sldIdLst>
    <p:sldSz cx="{width_emu}" cy="{height_emu}" type="{slide_type}"/>
    <p:notesSz cx="{notes_width}" cy="{notes_height}"/>
</p:presentation>'''

    def create_slide_xml(self, slide_content: str = "", layout_id: int = 1) -> str:
        """
        Create PowerPoint slide XML content.

        Args:
            slide_content: Main slide content XML
            layout_id: Layout ID reference

        Returns:
            Complete slide XML content
        """
        namespaces = self.create_namespace_declaration({
            'p': self.NAMESPACES['p'],
            'a': self.NAMESPACES['a']
        })

        return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld {namespaces}>
    <p:cSld>
        <p:spTree>
            <p:nvGrpSpPr>
                <p:cNvPr id="1" name=""/>
                <p:cNvGrpSpPr/>
                <p:nvPr/>
            </p:nvGrpSpPr>
            <p:grpSpPr>
                <a:xfrm/>
            </p:grpSpPr>
            {slide_content}
        </p:spTree>
    </p:cSld>
    <p:clrMapOvr>
        <a:masterClrMapping/>
    </p:clrMapOvr>
</p:sld>'''

    def create_content_types_xml(self, additional_overrides: Optional[List[Dict[str, str]]] = None) -> str:
        """
        Create [Content_Types].xml for PowerPoint presentations.

        Args:
            additional_overrides: Additional override entries beyond standard ones

        Returns:
            Complete content types XML
        """
        # Standard overrides for PowerPoint
        standard_overrides = [
            {
                'PartName': '/ppt/presentation.xml',
                'ContentType': 'application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml'
            },
            {
                'PartName': '/ppt/theme/theme1.xml',
                'ContentType': 'application/vnd.openxmlformats-officedocument.theme+xml'
            },
            {
                'PartName': '/ppt/slideLayouts/slideLayout1.xml',
                'ContentType': 'application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml'
            },
            {
                'PartName': '/ppt/slideMasters/slideMaster1.xml',
                'ContentType': 'application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml'
            }
        ]

        # Combine with additional overrides
        all_overrides = standard_overrides.copy()
        if additional_overrides:
            all_overrides.extend(additional_overrides)

        # Generate override XML
        override_xml = []
        for override in all_overrides:
            override_xml.append(
                f'    <Override PartName="{override["PartName"]}" ContentType="{override["ContentType"]}"/>'
            )

        overrides_str = '\n'.join(override_xml)
        namespace = self.create_namespace_declaration({'content_types': self.NAMESPACES['content_types']})

        return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types {namespace}>
    <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
    <Default Extension="xml" ContentType="application/xml"/>
    <Default Extension="png" ContentType="image/png"/>
    <Default Extension="jpg" ContentType="image/jpeg"/>
    <Default Extension="jpeg" ContentType="image/jpeg"/>
    <Default Extension="gif" ContentType="image/gif"/>
    <Default Extension="bmp" ContentType="image/bmp"/>
    <Default Extension="webp" ContentType="image/webp"/>
{overrides_str}
</Types>'''

    def create_animation_xml(self, effect_type: str, target_shape_id: int,
                           duration: float = 1.0, delay: float = 0.0) -> str:
        """
        Create PowerPoint animation XML.

        Consolidates animation XML generation from animation_templates.py.

        Args:
            effect_type: Animation effect type (fade, grow, spin, etc.)
            target_shape_id: ID of target shape
            duration: Animation duration in seconds
            delay: Animation delay in seconds

        Returns:
            Animation XML content
        """
        animation_id = self.get_next_id()
        duration_ms = int(duration * 1000)
        delay_ms = int(delay * 1000)

        namespaces = self.create_namespace_declaration({
            'p': self.NAMESPACES['p'],
            'a': self.NAMESPACES['a']
        })

        # Basic animation template - can be extended for specific effect types
        return f'''<p:par>
    <p:cTn id="{animation_id}" dur="indefinite" nodeType="seq">
        <p:childTnLst>
            <p:par>
                <p:cTn id="{animation_id + 1}" dur="{duration_ms}" delay="{delay_ms}">
                    <p:childTnLst>
                        <p:animEffect transition="in" filter="{effect_type}">
                            <p:cBhvr>
                                <p:cTn id="{animation_id + 2}" dur="{duration_ms}"/>
                                <p:tgtEl>
                                    <p:spTgt spid="{target_shape_id}"/>
                                </p:tgtEl>
                            </p:cBhvr>
                        </p:animEffect>
                    </p:childTnLst>
                </p:cTn>
            </p:par>
        </p:childTnLst>
    </p:cTn>
</p:par>'''

    def create_relationships_xml(self, relationships: List[Dict[str, str]]) -> str:
        """
        Create relationships XML (.rels files).

        Args:
            relationships: List of relationship dictionaries with Id, Type, Target

        Returns:
            Complete relationships XML
        """
        rel_xml = []
        for rel in relationships:
            rel_xml.append(
                f'    <Relationship Id="{rel["Id"]}" Type="{rel["Type"]}" Target="{rel["Target"]}"/>'
            )

        relationships_str = '\n'.join(rel_xml)
        namespace = self.create_namespace_declaration({'relationships': self.NAMESPACES['relationships']})

        return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships {namespace}>
{relationships_str}
</Relationships>'''

    def create_shape_xml(self, shape_id: int, name: str, shape_content: str,
                        x: int = 0, y: int = 0, width: int = 914400, height: int = 914400) -> str:
        """
        Create PowerPoint shape XML.

        Args:
            shape_id: Unique shape ID
            name: Shape name
            shape_content: Inner shape content (geometry, text, etc.)
            x, y: Position in EMU
            width, height: Size in EMU

        Returns:
            Shape XML content
        """
        return f'''<p:sp>
    <p:nvSpPr>
        <p:cNvPr id="{shape_id}" name="{self.escape_xml(name)}"/>
        <p:cNvSpPr/>
        <p:nvPr/>
    </p:nvSpPr>
    <p:spPr>
        <a:xfrm>
            <a:off x="{x}" y="{y}"/>
            <a:ext cx="{width}" cy="{height}"/>
        </a:xfrm>
        {shape_content}
    </p:spPr>
</p:sp>'''

    def validate_xml(self, xml_content: str) -> bool:
        """
        Validate XML content for well-formedness.

        Args:
            xml_content: XML string to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            ET.fromstring(xml_content)
            return True
        except ET.ParseError as e:
            logger.warning(f"XML validation failed: {e}")
            return False

    def pretty_print_xml(self, xml_content: str) -> str:
        """
        Format XML with proper indentation.

        Args:
            xml_content: Raw XML string

        Returns:
            Formatted XML string
        """
        try:
            # Parse and re-serialize with indentation
            root = ET.fromstring(xml_content)
            ET.indent(root, space="    ")
            return ET.tostring(root, encoding='unicode', xml_declaration=True)
        except ET.ParseError:
            logger.warning("Could not format XML - returning original")
            return xml_content


# Singleton instance for global access
xml_builder = XMLBuilder()


def get_xml_builder() -> XMLBuilder:
    """Get the global XML builder instance."""
    return xml_builder


# Convenience functions for common operations
def create_presentation_xml(width_emu: int, height_emu: int, **kwargs) -> str:
    """Convenience function for presentation XML creation."""
    return xml_builder.create_presentation_xml(width_emu, height_emu, **kwargs)


def create_slide_xml(slide_content: str = "", **kwargs) -> str:
    """Convenience function for slide XML creation."""
    return xml_builder.create_slide_xml(slide_content, **kwargs)


def create_content_types_xml(**kwargs) -> str:
    """Convenience function for content types XML creation."""
    return xml_builder.create_content_types_xml(**kwargs)


def create_animation_xml(effect_type: str, target_shape_id: int, **kwargs) -> str:
    """Convenience function for animation XML creation."""
    return xml_builder.create_animation_xml(effect_type, target_shape_id, **kwargs)