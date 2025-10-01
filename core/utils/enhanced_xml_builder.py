#!/usr/bin/env python3
"""
Enhanced XML Builder with Template-Based Generation

Uses XML templates from core/io/templates/ and lxml.etree DOM manipulation
to generate namespace-aware, validated PowerPoint OOXML documents.
"""

import logging
from typing import Dict, List, Optional, Any, Union
from lxml import etree as ET
from lxml.etree import Element, QName, SubElement
from ..io.template_loader import TemplateLoader, get_template_loader

logger = logging.getLogger(__name__)

# OpenXML Namespaces
P_URI = "http://schemas.openxmlformats.org/presentationml/2006/main"
A_URI = "http://schemas.openxmlformats.org/drawingml/2006/main"
R_URI = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
CONTENT_TYPES_URI = "http://schemas.openxmlformats.org/package/2006/content-types"
RELATIONSHIPS_URI = "http://schemas.openxmlformats.org/package/2006/relationships"

# Namespace map for lxml
NSMAP = {
    'p': P_URI,
    'a': A_URI,
    'r': R_URI
}

CONTENT_NSMAP = {
    None: CONTENT_TYPES_URI  # Default namespace
}

RELATIONSHIPS_NSMAP = {
    None: RELATIONSHIPS_URI  # Default namespace
}


class EnhancedXMLBuilder:
    """
    Enhanced XML builder using template-based generation with lxml.etree DOM manipulation.

    Loads XML templates from core/io/templates/ and modifies them using proper
    DOM operations for namespace-aware, validated PowerPoint OOXML documents.
    """

    def __init__(self, template_loader: Optional[TemplateLoader] = None):
        """Initialize enhanced XML builder.

        Args:
            template_loader: Optional custom template loader.
                           Uses default loader if None.
        """
        self._id_counter = 1
        self.logger = logging.getLogger(__name__)
        self._template_loader = template_loader or get_template_loader()

        # Validate critical templates are available
        self._validate_templates()

    def _validate_templates(self) -> None:
        """
        Validate that critical templates are available and well-formed.

        Raises:
            FileNotFoundError: If critical templates are missing
            ET.XMLSyntaxError: If templates contain invalid XML
        """
        critical_templates = [
            "presentation.xml",
            "slide_template.xml",
            "content_types.xml",
            "group_shape.xml",
            "group_picture.xml",
            "path_shape.xml",
            "path_emf_picture.xml",
            "path_emf_placeholder.xml",
            "text_shape.xml",
            "text_emf_picture.xml",
            "text_paragraph.xml",
            "text_run.xml"
        ]

        for template_name in critical_templates:
            try:
                # This will raise FileNotFoundError or XMLSyntaxError if invalid
                self._template_loader.load_template(template_name)
                self.logger.debug(f"Template validated: {template_name}")
            except Exception as e:
                self.logger.error(f"Critical template validation failed: {template_name} - {e}")
                raise

    def get_next_id(self) -> int:
        """Get next unique ID for XML elements."""
        current_id = self._id_counter
        self._id_counter += 1
        return current_id

    def reset_id_counter(self) -> None:
        """Reset ID counter for testing or new documents."""
        self._id_counter = 1

    def create_presentation_element(self, width_emu: int, height_emu: int,
                                  slide_type: str = "screen4x3") -> Element:
        """
        Create PowerPoint presentation element using template-based generation.

        Args:
            width_emu: Slide width in EMU
            height_emu: Slide height in EMU
            slide_type: Slide size type

        Returns:
            presentation Element ready for slide insertion
        """
        # Load presentation template
        presentation = self._template_loader.load_template("presentation.xml")

        # Update slide size
        slide_size = presentation.find('.//p:sldSz', namespaces={'p': P_URI})
        if slide_size is not None:
            slide_size.set('cx', str(width_emu))
            slide_size.set('cy', str(height_emu))
            slide_size.set('type', slide_type)

        # Update notes size (standard aspect ratio)
        notes_width = height_emu
        notes_height = int(height_emu * 4/3)
        notes_size = presentation.find('.//p:notesSz', namespaces={'p': P_URI})
        if notes_size is not None:
            notes_size.set('cx', str(notes_width))
            notes_size.set('cy', str(notes_height))

        # Clear existing slides from template (we'll add them dynamically)
        slide_list = presentation.find('.//p:sldIdLst', namespaces={'p': P_URI})
        if slide_list is not None:
            slide_list.clear()

        return presentation

    def add_slide_to_presentation(self, presentation: Element, slide_id: int,
                                rel_id: str) -> None:
        """
        Add slide reference to presentation element.

        Args:
            presentation: presentation Element
            slide_id: Unique slide ID
            rel_id: Relationship ID (e.g., 'rId2')
        """
        slide_list = presentation.find(f'.//p:sldIdLst', NSMAP)
        if slide_list is None:
            raise ValueError("Presentation element missing slide ID list")

        slide_ref = SubElement(slide_list, QName(P_URI, 'sldId'))
        slide_ref.set('id', str(slide_id))
        slide_ref.set(QName(R_URI, 'id'), rel_id)

    def create_slide_element(self, layout_id: int = 1) -> Element:
        """
        Create PowerPoint slide element using template-based generation.

        Args:
            layout_id: Layout ID reference

        Returns:
            slide Element ready for content insertion
        """
        # Load slide template
        slide = self._template_loader.load_template("slide_template.xml")

        # The template already has the proper structure with spTree,
        # nvGrpSpPr, grpSpPr, and clrMapOvr - no need to recreate

        # Remove the placeholder comment since we'll add shapes dynamically
        spTree = slide.find('.//p:spTree', namespaces={'p': P_URI})
        if spTree is not None:
            for comment in spTree.iter():
                if hasattr(comment, 'tag') and hasattr(comment.tag, 'function'):
                    # This is an lxml comment node
                    continue
                parent = comment.getparent()
                if parent is not None and comment.tail and 'SHAPES WILL BE INSERTED HERE' in comment.tail:
                    comment.tail = comment.tail.replace('SHAPES WILL BE INSERTED HERE', '').strip()

        return slide

    def add_shape_to_slide(self, slide: Element, shape_element: Element) -> None:
        """
        Add shape element to slide's shape tree.

        Args:
            slide: slide Element
            shape_element: Shape Element to add
        """
        spTree = slide.find('.//p:spTree', NSMAP)
        if spTree is None:
            raise ValueError("Slide element missing shape tree")

        spTree.append(shape_element)

    def create_shape_element(self, shape_id: int, name: str, x: int = 0, y: int = 0,
                           width: int = 914400, height: int = 914400) -> Element:
        """
        Create PowerPoint shape element with proper structure.

        Args:
            shape_id: Unique shape ID
            name: Shape name
            x, y: Position in EMU
            width, height: Size in EMU

        Returns:
            Complete shape Element
        """
        # Create shape element
        shape = Element(QName(P_URI, 'sp'))

        # Add non-visual shape properties
        nvSpPr = SubElement(shape, QName(P_URI, 'nvSpPr'))
        cNvPr = SubElement(nvSpPr, QName(P_URI, 'cNvPr'))
        cNvPr.set('id', str(shape_id))
        cNvPr.set('name', name)
        SubElement(nvSpPr, QName(P_URI, 'cNvSpPr'))
        SubElement(nvSpPr, QName(P_URI, 'nvPr'))

        # Add shape properties
        spPr = SubElement(shape, QName(P_URI, 'spPr'))

        # Add transform
        xfrm = SubElement(spPr, QName(A_URI, 'xfrm'))
        off = SubElement(xfrm, QName(A_URI, 'off'))
        off.set('x', str(x))
        off.set('y', str(y))
        ext = SubElement(xfrm, QName(A_URI, 'ext'))
        ext.set('cx', str(width))
        ext.set('cy', str(height))

        return shape

    def add_geometry_to_shape(self, shape: Element, geometry_element: Element) -> None:
        """
        Add geometry element to shape properties.

        Args:
            shape: Shape Element
            geometry_element: Geometry Element (custGeom, prstGeom, etc.)
        """
        spPr = shape.find('.//p:spPr', NSMAP)
        if spPr is None:
            raise ValueError("Shape element missing spPr")

        spPr.append(geometry_element)

    def create_content_types_element(self, additional_overrides: Optional[List[Dict[str, str]]] = None) -> Element:
        """
        Create [Content_Types].xml element using template-based generation.

        Args:
            additional_overrides: Additional override entries

        Returns:
            Complete Types Element
        """
        # Load content types template
        types = self._template_loader.load_template("content_types.xml")

        # Add additional overrides if provided
        if additional_overrides:
            for override_data in additional_overrides:
                override = SubElement(types, QName(CONTENT_TYPES_URI, 'Override'))
                override.set('PartName', override_data['PartName'])
                override.set('ContentType', override_data['ContentType'])

        return types

    def create_relationships_element(self, relationships: List[Dict[str, str]]) -> Element:
        """
        Create relationships element using proper DOM manipulation.

        Args:
            relationships: List of relationship dictionaries with Id, Type, Target

        Returns:
            Complete Relationships Element
        """
        # Create root Relationships element
        rels = Element(QName(RELATIONSHIPS_URI, 'Relationships'), nsmap=RELATIONSHIPS_NSMAP)

        for rel_data in relationships:
            relationship = SubElement(rels, QName(RELATIONSHIPS_URI, 'Relationship'))
            relationship.set('Id', rel_data['Id'])
            relationship.set('Type', rel_data['Type'])
            relationship.set('Target', rel_data['Target'])

        return rels

    def create_animation_element(self, effect_type: str, target_shape_id: int,
                               duration: float = 1.0, delay: float = 0.0) -> Element:
        """
        Create PowerPoint animation element using proper DOM manipulation.

        Args:
            effect_type: Animation effect type
            target_shape_id: ID of target shape
            duration: Animation duration in seconds
            delay: Animation delay in seconds

        Returns:
            Animation Element
        """
        animation_id = self.get_next_id()
        duration_ms = int(duration * 1000)
        delay_ms = int(delay * 1000)

        # Create animation par element
        par = Element(QName(P_URI, 'par'))
        cTn = SubElement(par, QName(P_URI, 'cTn'))
        cTn.set('id', str(animation_id))
        cTn.set('dur', 'indefinite')
        cTn.set('nodeType', 'seq')

        # Add child timing list
        childTnLst = SubElement(cTn, QName(P_URI, 'childTnLst'))
        child_par = SubElement(childTnLst, QName(P_URI, 'par'))
        child_cTn = SubElement(child_par, QName(P_URI, 'cTn'))
        child_cTn.set('id', str(animation_id + 1))
        child_cTn.set('dur', str(duration_ms))
        child_cTn.set('delay', str(delay_ms))

        # Add animation effect
        child_childTnLst = SubElement(child_cTn, QName(P_URI, 'childTnLst'))
        animEffect = SubElement(child_childTnLst, QName(P_URI, 'animEffect'))
        animEffect.set('transition', 'in')
        animEffect.set('filter', effect_type)

        # Add behavior
        cBhvr = SubElement(animEffect, QName(P_URI, 'cBhvr'))
        bhvr_cTn = SubElement(cBhvr, QName(P_URI, 'cTn'))
        bhvr_cTn.set('id', str(animation_id + 2))
        bhvr_cTn.set('dur', str(duration_ms))

        # Add target element
        tgtEl = SubElement(cBhvr, QName(P_URI, 'tgtEl'))
        spTgt = SubElement(tgtEl, QName(P_URI, 'spTgt'))
        spTgt.set('spid', str(target_shape_id))

        return par

    def element_to_string(self, element: Element, pretty_print: bool = True) -> str:
        """
        Convert Element to XML string with proper encoding.

        Args:
            element: Element to convert
            pretty_print: Whether to format with indentation

        Returns:
            XML string with declaration
        """
        return ET.tostring(element, xml_declaration=True, encoding='UTF-8',
                          pretty_print=pretty_print).decode('utf-8')

    def validate_element(self, element: Element, schema_path: Optional[str] = None) -> bool:
        """
        Validate XML element structure.

        Args:
            element: Element to validate
            schema_path: Optional path to XSD schema

        Returns:
            True if valid, False otherwise
        """
        try:
            # Basic well-formedness check
            xml_str = ET.tostring(element)
            ET.fromstring(xml_str)

            # Optional schema validation
            if schema_path:
                try:
                    with open(schema_path, 'rb') as f:
                        schema_doc = ET.parse(f)
                        schema = ET.XMLSchema(schema_doc)
                        schema.assertValid(element)
                except Exception as e:
                    self.logger.warning(f"Schema validation failed: {e}")
                    return False

            return True
        except ET.XMLSyntaxError as e:
            self.logger.error(f"XML validation failed: {e}")
            return False

    def add_text_to_element(self, element: Element, text: str) -> None:
        """
        Add text content to element with proper escaping.

        Args:
            element: Element to add text to
            text: Text content (will be properly escaped)
        """
        if text:
            element.text = str(text)  # lxml handles escaping automatically

    def generate_group_shape(self, group_id: int, x_emu: int, y_emu: int,
                           width_emu: int, height_emu: int,
                           child_elements: List[Element],
                           opacity: Optional[float] = None,
                           clip_xml: Optional[str] = None) -> Element:
        """
        Generate group shape using template-based generation.

        Args:
            group_id: Unique group ID
            x_emu: X position in EMU
            y_emu: Y position in EMU
            width_emu: Width in EMU
            height_emu: Height in EMU
            child_elements: List of child shape elements
            opacity: Optional opacity (0.0 to 1.0)
            clip_xml: Optional clipping XML

        Returns:
            Group shape Element
        """
        # Load group shape template
        group_shape = self._template_loader.load_template("group_shape.xml")

        # Update group ID and name
        cnv_pr = group_shape.find('.//p:cNvPr', NSMAP)
        if cnv_pr is not None:
            cnv_pr.set('id', str(group_id))
            cnv_pr.set('name', f'Group{group_id}')

        # Update transform (position and size)
        xfrm = group_shape.find('.//a:xfrm', NSMAP)
        if xfrm is not None:
            # Set offset (position)
            off = xfrm.find('.//a:off', NSMAP)
            if off is not None:
                off.set('x', str(x_emu))
                off.set('y', str(y_emu))

            # Set extent (size)
            ext = xfrm.find('.//a:ext', NSMAP)
            if ext is not None:
                ext.set('cx', str(width_emu))
                ext.set('cy', str(height_emu))

            # Set child extent
            ch_ext = xfrm.find('.//a:chExt', NSMAP)
            if ch_ext is not None:
                ch_ext.set('cx', str(width_emu))
                ch_ext.set('cy', str(height_emu))

        # Find group properties for effects insertion
        grp_sp_pr = group_shape.find('.//p:grpSpPr', NSMAP)
        if grp_sp_pr is not None:
            # Add opacity effect if needed
            if opacity is not None and opacity < 1.0:
                opacity_val = int(opacity * 100000)
                effect_lst = ET.SubElement(grp_sp_pr, QName(A_URI, 'effectLst'))
                alpha_elem = ET.SubElement(effect_lst, QName(A_URI, 'alpha'))
                alpha_elem.set('val', str(opacity_val))

            # Add clipping if provided
            if clip_xml:
                # Parse clip XML and append to group properties
                try:
                    clip_element = ET.fromstring(clip_xml)
                    grp_sp_pr.append(clip_element)
                except ET.XMLSyntaxError:
                    self.logger.warning(f"Invalid clip XML provided: {clip_xml}")

        # Add child elements
        if child_elements:
            # Find the comment placeholder and replace with actual children
            for comment in group_shape.xpath('//comment()[contains(., "CHILD ELEMENTS")]'):
                parent = comment.getparent()
                if parent is not None:
                    # Remove comment
                    parent.remove(comment)
                    # Add all child elements
                    for child in child_elements:
                        parent.append(child)
                    break

        return group_shape

    def generate_group_picture(self, group_id: int, x_emu: int, y_emu: int,
                             width_emu: int, height_emu: int,
                             embed_id: str,
                             opacity: Optional[float] = None,
                             clip_xml: Optional[str] = None) -> Element:
        """
        Generate group picture using template-based generation.

        Args:
            group_id: Unique group ID
            x_emu: X position in EMU
            y_emu: Y position in EMU
            width_emu: Width in EMU
            height_emu: Height in EMU
            embed_id: Embedded resource ID (e.g., "rId1")
            opacity: Optional opacity (0.0 to 1.0)
            clip_xml: Optional clipping XML

        Returns:
            Group picture Element
        """
        # Load group picture template
        group_pic = self._template_loader.load_template("group_picture.xml")

        # Update picture ID and name
        cnv_pr = group_pic.find('.//p:cNvPr', NSMAP)
        if cnv_pr is not None:
            cnv_pr.set('id', str(group_id))
            cnv_pr.set('name', f'GroupPicture{group_id}')

        # Update embed reference
        blip = group_pic.find('.//a:blip', NSMAP)
        if blip is not None:
            blip.set(QName(R_URI, 'embed'), embed_id)

        # Update transform (position and size)
        xfrm = group_pic.find('.//a:xfrm', NSMAP)
        if xfrm is not None:
            # Set offset (position)
            off = xfrm.find('.//a:off', NSMAP)
            if off is not None:
                off.set('x', str(x_emu))
                off.set('y', str(y_emu))

            # Set extent (size)
            ext = xfrm.find('.//a:ext', NSMAP)
            if ext is not None:
                ext.set('cx', str(width_emu))
                ext.set('cy', str(height_emu))

        # Find shape properties for effects insertion
        sp_pr = group_pic.find('.//p:spPr', NSMAP)
        if sp_pr is not None:
            # Add opacity effect if needed
            if opacity is not None and opacity < 1.0:
                opacity_val = int(opacity * 100000)
                effect_lst = ET.SubElement(sp_pr, QName(A_URI, 'effectLst'))
                alpha_elem = ET.SubElement(effect_lst, QName(A_URI, 'alpha'))
                alpha_elem.set('val', str(opacity_val))

            # Add clipping if provided
            if clip_xml:
                # Parse clip XML and append to shape properties
                try:
                    clip_element = ET.fromstring(clip_xml)
                    sp_pr.append(clip_element)
                except ET.XMLSyntaxError:
                    self.logger.warning(f"Invalid clip XML provided: {clip_xml}")

        return group_pic

    def element_to_string(self, element: Element) -> str:
        """
        Convert Element to properly formatted XML string.

        Args:
            element: lxml Element to convert

        Returns:
            Formatted XML string
        """
        return ET.tostring(element, encoding='unicode', pretty_print=True)

    def generate_path_shape(self, path_id: int, x_emu: int, y_emu: int,
                           width_emu: int, height_emu: int,
                           path_data: str,
                           fill_xml: Optional[str] = None,
                           stroke_xml: Optional[str] = None,
                           clip_xml: Optional[str] = None) -> Element:
        """
        Generate path shape using template-based generation.

        Args:
            path_id: Unique path ID
            x_emu: X position in EMU
            y_emu: Y position in EMU
            width_emu: Width in EMU
            height_emu: Height in EMU
            path_data: DrawingML path data
            fill_xml: Optional fill XML
            stroke_xml: Optional stroke XML
            clip_xml: Optional clipping XML

        Returns:
            Path shape Element
        """
        # Load path shape template
        path_shape = self._template_loader.load_template("path_shape.xml")

        # Update path ID and name
        cnv_pr = path_shape.find('.//p:cNvPr', NSMAP)
        if cnv_pr is not None:
            cnv_pr.set('id', str(path_id))
            cnv_pr.set('name', f'Path{path_id}')

        # Update transform (position and size)
        xfrm = path_shape.find('.//a:xfrm', NSMAP)
        if xfrm is not None:
            # Set offset (position)
            off = xfrm.find('.//a:off', NSMAP)
            if off is not None:
                off.set('x', str(x_emu))
                off.set('y', str(y_emu))

            # Set extent (size)
            ext = xfrm.find('.//a:ext', NSMAP)
            if ext is not None:
                ext.set('cx', str(width_emu))
                ext.set('cy', str(height_emu))

        # Update path data
        path_element = path_shape.find('.//a:path', NSMAP)
        if path_element is not None:
            # Clear the comment placeholder
            path_element.clear()
            # Parse path data as XML and insert as child elements
            # path_data contains DrawingML commands like <a:moveTo>, <a:lnTo>, etc.
            if path_data and path_data.strip():
                try:
                    # Wrap in temporary container to parse multiple elements
                    wrapped = f'<container xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">{path_data}</container>'
                    container = ET.fromstring(wrapped)
                    # Insert all child elements into path
                    for child in container:
                        path_element.append(child)
                except ET.XMLSyntaxError as e:
                    self.logger.error(f"Failed to parse path data as XML: {e}")
                    self.logger.error(f"Path data: {path_data[:200]}")
                    # Fallback: set as text (will be escaped, but won't crash)
                    path_element.text = path_data

        # Find shape properties for fill, stroke, clipping insertion
        sp_pr = path_shape.find('.//p:spPr', NSMAP)
        if sp_pr is not None:
            # Insert fill XML if provided
            if fill_xml:
                try:
                    fill_element = ET.fromstring(fill_xml)
                    sp_pr.append(fill_element)
                except ET.XMLSyntaxError:
                    self.logger.warning(f"Invalid fill XML provided: {fill_xml}")

            # Insert stroke XML if provided
            if stroke_xml:
                try:
                    stroke_element = ET.fromstring(stroke_xml)
                    sp_pr.append(stroke_element)
                except ET.XMLSyntaxError:
                    self.logger.warning(f"Invalid stroke XML provided: {stroke_xml}")

            # Insert clipping XML if provided
            if clip_xml:
                try:
                    clip_element = ET.fromstring(clip_xml)
                    sp_pr.append(clip_element)
                except ET.XMLSyntaxError:
                    self.logger.warning(f"Invalid clip XML provided: {clip_xml}")

        return path_shape

    def generate_path_emf_picture(self, path_id: int, x_emu: int, y_emu: int,
                                 width_emu: int, height_emu: int,
                                 embed_id: str) -> Element:
        """
        Generate path EMF picture using template-based generation.

        Args:
            path_id: Unique path ID
            x_emu: X position in EMU
            y_emu: Y position in EMU
            width_emu: Width in EMU
            height_emu: Height in EMU
            embed_id: Embedded resource ID (e.g., "rId1")

        Returns:
            Path EMF picture Element
        """
        # Load path EMF picture template
        emf_pic = self._template_loader.load_template("path_emf_picture.xml")

        # Update picture ID and name
        cnv_pr = emf_pic.find('.//p:cNvPr', NSMAP)
        if cnv_pr is not None:
            cnv_pr.set('id', str(path_id))
            cnv_pr.set('name', f'EMF_Path{path_id}')

        # Update embed reference
        blip = emf_pic.find('.//a:blip', NSMAP)
        if blip is not None:
            blip.set(QName(R_URI, 'embed'), embed_id)

        # Update transform (position and size)
        xfrm = emf_pic.find('.//a:xfrm', NSMAP)
        if xfrm is not None:
            # Set offset (position)
            off = xfrm.find('.//a:off', NSMAP)
            if off is not None:
                off.set('x', str(x_emu))
                off.set('y', str(y_emu))

            # Set extent (size)
            ext = xfrm.find('.//a:ext', NSMAP)
            if ext is not None:
                ext.set('cx', str(width_emu))
                ext.set('cy', str(height_emu))

        return emf_pic

    def generate_path_emf_placeholder(self, path_id: int, x_emu: int, y_emu: int,
                                    width_emu: int, height_emu: int,
                                    embed_id: str,
                                    fill_xml: Optional[str] = None,
                                    stroke_xml: Optional[str] = None,
                                    clip_xml: Optional[str] = None) -> Element:
        """
        Generate path EMF placeholder using template-based generation.

        Args:
            path_id: Unique path ID
            x_emu: X position in EMU
            y_emu: Y position in EMU
            width_emu: Width in EMU
            height_emu: Height in EMU
            embed_id: Embedded resource ID (e.g., "rId1")
            fill_xml: Optional fill XML
            stroke_xml: Optional stroke XML
            clip_xml: Optional clipping XML

        Returns:
            Path EMF placeholder Element
        """
        # Load path EMF placeholder template
        emf_placeholder = self._template_loader.load_template("path_emf_placeholder.xml")

        # Update placeholder ID and name
        cnv_pr = emf_placeholder.find('.//p:cNvPr', NSMAP)
        if cnv_pr is not None:
            cnv_pr.set('id', str(path_id))
            cnv_pr.set('name', f'EMF_Placeholder{path_id}')

        # Update embed reference
        blip = emf_placeholder.find('.//a:blip', NSMAP)
        if blip is not None:
            blip.set(QName(R_URI, 'embed'), embed_id)

        # Update transform (position and size)
        xfrm = emf_placeholder.find('.//a:xfrm', NSMAP)
        if xfrm is not None:
            # Set offset (position)
            off = xfrm.find('.//a:off', NSMAP)
            if off is not None:
                off.set('x', str(x_emu))
                off.set('y', str(y_emu))

            # Set extent (size)
            ext = xfrm.find('.//a:ext', NSMAP)
            if ext is not None:
                ext.set('cx', str(width_emu))
                ext.set('cy', str(height_emu))

        # Find shape properties for fill, stroke, clipping insertion
        sp_pr = emf_placeholder.find('.//p:spPr', NSMAP)
        if sp_pr is not None:
            # Insert fill XML if provided
            if fill_xml:
                try:
                    fill_element = ET.fromstring(fill_xml)
                    sp_pr.append(fill_element)
                except ET.XMLSyntaxError:
                    self.logger.warning(f"Invalid fill XML provided: {fill_xml}")

            # Insert stroke XML if provided
            if stroke_xml:
                try:
                    stroke_element = ET.fromstring(stroke_xml)
                    sp_pr.append(stroke_element)
                except ET.XMLSyntaxError:
                    self.logger.warning(f"Invalid stroke XML provided: {stroke_xml}")

            # Insert clipping XML if provided
            if clip_xml:
                try:
                    clip_element = ET.fromstring(clip_xml)
                    sp_pr.append(clip_element)
                except ET.XMLSyntaxError:
                    self.logger.warning(f"Invalid clip XML provided: {clip_xml}")

        return emf_placeholder

    def generate_text_shape(self, text_id: int, x_emu: int, y_emu: int,
                           width_emu: int, height_emu: int,
                           paragraphs_xml: str,
                           effects_xml: Optional[str] = None) -> Element:
        """
        Generate text shape using template-based generation.

        Args:
            text_id: Unique text ID
            x_emu: X position in EMU
            y_emu: Y position in EMU
            width_emu: Width in EMU
            height_emu: Height in EMU
            paragraphs_xml: XML content for paragraphs
            effects_xml: Optional effects XML

        Returns:
            Text shape Element
        """
        # Load text shape template
        text_shape = self._template_loader.load_template("text_shape.xml")

        # Update text ID and name
        cnv_pr = text_shape.find('.//p:cNvPr', NSMAP)
        if cnv_pr is not None:
            cnv_pr.set('id', str(text_id))
            cnv_pr.set('name', f'TextFrame{text_id}')

        # Update transform (position and size)
        xfrm = text_shape.find('.//a:xfrm', NSMAP)
        if xfrm is not None:
            # Set offset (position)
            off = xfrm.find('.//a:off', NSMAP)
            if off is not None:
                off.set('x', str(x_emu))
                off.set('y', str(y_emu))

            # Set extent (size)
            ext = xfrm.find('.//a:ext', NSMAP)
            if ext is not None:
                ext.set('cx', str(width_emu))
                ext.set('cy', str(height_emu))

        # Find txBody for paragraph insertion
        tx_body = text_shape.find('.//p:txBody', NSMAP)
        if tx_body is not None:
            # Insert paragraphs XML
            if paragraphs_xml:
                try:
                    # Parse paragraphs XML and append to txBody
                    paragraphs_fragment = f"<root xmlns:a='{A_URI}'>{paragraphs_xml}</root>"
                    paragraphs_root = ET.fromstring(paragraphs_fragment)
                    for paragraph in paragraphs_root:
                        tx_body.append(paragraph)
                except ET.XMLSyntaxError:
                    self.logger.warning(f"Invalid paragraphs XML provided: {paragraphs_xml}")

        # Find shape properties for effects insertion
        sp_pr = text_shape.find('.//p:spPr', NSMAP)
        if sp_pr is not None and effects_xml:
            try:
                effects_element = ET.fromstring(effects_xml)
                sp_pr.append(effects_element)
            except ET.XMLSyntaxError:
                self.logger.warning(f"Invalid effects XML provided: {effects_xml}")

        return text_shape

    def generate_text_emf_picture(self, text_id: int, x_emu: int, y_emu: int,
                                 width_emu: int, height_emu: int,
                                 embed_id: str,
                                 effects_xml: Optional[str] = None) -> Element:
        """
        Generate text EMF picture using template-based generation.

        Args:
            text_id: Unique text ID
            x_emu: X position in EMU
            y_emu: Y position in EMU
            width_emu: Width in EMU
            height_emu: Height in EMU
            embed_id: Embedded resource ID (e.g., "rId1")
            effects_xml: Optional effects XML

        Returns:
            Text EMF picture Element
        """
        # Load text EMF picture template
        emf_pic = self._template_loader.load_template("text_emf_picture.xml")

        # Update picture ID and name
        cnv_pr = emf_pic.find('.//p:cNvPr', NSMAP)
        if cnv_pr is not None:
            cnv_pr.set('id', str(text_id))
            cnv_pr.set('name', f'EMF_Text{text_id}')

        # Update embed reference
        blip = emf_pic.find('.//a:blip', NSMAP)
        if blip is not None:
            blip.set(QName(R_URI, 'embed'), embed_id)

        # Update transform (position and size)
        xfrm = emf_pic.find('.//a:xfrm', NSMAP)
        if xfrm is not None:
            # Set offset (position)
            off = xfrm.find('.//a:off', NSMAP)
            if off is not None:
                off.set('x', str(x_emu))
                off.set('y', str(y_emu))

            # Set extent (size)
            ext = xfrm.find('.//a:ext', NSMAP)
            if ext is not None:
                ext.set('cx', str(width_emu))
                ext.set('cy', str(height_emu))

        # Find shape properties for effects insertion
        sp_pr = emf_pic.find('.//p:spPr', NSMAP)
        if sp_pr is not None and effects_xml:
            try:
                effects_element = ET.fromstring(effects_xml)
                sp_pr.append(effects_element)
            except ET.XMLSyntaxError:
                self.logger.warning(f"Invalid effects XML provided: {effects_xml}")

        return emf_pic

    def generate_text_paragraph(self, runs_xml: str) -> Element:
        """
        Generate text paragraph using template-based generation.

        Args:
            runs_xml: XML content for text runs

        Returns:
            Text paragraph Element
        """
        # Load text paragraph template
        paragraph = self._template_loader.load_template("text_paragraph.xml")

        # Insert text runs XML
        if runs_xml:
            try:
                # Parse runs XML and append to paragraph
                runs_fragment = f"<root xmlns:a='{A_URI}'>{runs_xml}</root>"
                runs_root = ET.fromstring(runs_fragment)
                for run in runs_root:
                    paragraph.append(run)
            except ET.XMLSyntaxError:
                self.logger.warning(f"Invalid runs XML provided: {runs_xml}")

        return paragraph

    def generate_text_run(self, text_content: str, font_family: str = "Arial",
                         font_size: int = 1200, bold: bool = False,
                         italic: bool = False, color: str = "000000",
                         formatting_xml: Optional[str] = None) -> Element:
        """
        Generate text run using template-based generation.

        Args:
            text_content: Text content
            font_family: Font family name
            font_size: Font size in hundredths of a point
            bold: Bold formatting
            italic: Italic formatting
            color: Text color (hex without #)
            formatting_xml: Optional additional formatting XML

        Returns:
            Text run Element
        """
        # Load text run template
        text_run = self._template_loader.load_template("text_run.xml")

        # Update text content
        text_elem = text_run.find('.//a:t', NSMAP)
        if text_elem is not None:
            text_elem.text = text_content

        # Update run properties
        r_pr = text_run.find('.//a:rPr', NSMAP)
        if r_pr is not None:
            # Set font size
            r_pr.set('sz', str(font_size))

            # Set bold/italic
            r_pr.set('b', '1' if bold else '0')
            r_pr.set('i', '1' if italic else '0')

            # Update color
            srgb_clr = r_pr.find('.//a:srgbClr', NSMAP)
            if srgb_clr is not None:
                srgb_clr.set('val', color)

            # Update font family
            latin = r_pr.find('.//a:latin', NSMAP)
            if latin is not None:
                latin.set('typeface', font_family)

            # Insert additional formatting if provided
            if formatting_xml:
                try:
                    formatting_element = ET.fromstring(formatting_xml)
                    r_pr.append(formatting_element)
                except ET.XMLSyntaxError:
                    self.logger.warning(f"Invalid formatting XML provided: {formatting_xml}")

        return text_run

    def generate_image_raster_picture(self, image_id: int, x_emu: int, y_emu: int,
                                     width_emu: int, height_emu: int,
                                     rel_id: str,
                                     effects_xml: Optional[str] = None) -> Element:
        """
        Generate raster image picture element from template.

        Args:
            image_id: Unique image ID
            x_emu: X position in EMU
            y_emu: Y position in EMU
            width_emu: Width in EMU
            height_emu: Height in EMU
            rel_id: Relationship ID for image embedding
            effects_xml: Optional effects XML (opacity, clipping, etc.)

        Returns:
            Raster image picture Element
        """
        # Load raster image template
        image_pic = self._template_loader.load_template("image_raster_picture.xml")

        # Update image ID and name
        cnv_pr = image_pic.find('.//p:cNvPr', NSMAP)
        if cnv_pr is not None:
            cnv_pr.set('id', str(image_id))
            cnv_pr.set('name', f'Image_{image_id}')

        # Update position and size
        xfrm = image_pic.find('.//a:xfrm', NSMAP)
        if xfrm is not None:
            off = xfrm.find('.//a:off', NSMAP)
            if off is not None:
                off.set('x', str(x_emu))
                off.set('y', str(y_emu))

            ext = xfrm.find('.//a:ext', NSMAP)
            if ext is not None:
                ext.set('cx', str(width_emu))
                ext.set('cy', str(height_emu))

        # Update relationship ID
        blip = image_pic.find('.//a:blip', NSMAP)
        if blip is not None:
            blip.set(QName(R_URI, 'embed'), rel_id)

        # Insert effects if provided
        if effects_xml:
            try:
                effects_element = ET.fromstring(effects_xml)
                sp_pr = image_pic.find('.//p:spPr', NSMAP)
                if sp_pr is not None:
                    # Simply append effects at the end of spPr
                    sp_pr.append(effects_element)
            except ET.XMLSyntaxError:
                self.logger.warning(f"Invalid effects XML provided: {effects_xml}")

        return image_pic

    def generate_image_vector_picture(self, image_id: int, x_emu: int, y_emu: int,
                                     width_emu: int, height_emu: int,
                                     rel_id: str,
                                     effects_xml: Optional[str] = None) -> Element:
        """
        Generate vector image picture element from template.

        Args:
            image_id: Unique image ID
            x_emu: X position in EMU
            y_emu: Y position in EMU
            width_emu: Width in EMU
            height_emu: Height in EMU
            rel_id: Relationship ID for image embedding
            effects_xml: Optional effects XML (opacity, clipping, etc.)

        Returns:
            Vector image picture Element
        """
        # Load vector image template
        image_pic = self._template_loader.load_template("image_vector_picture.xml")

        # Update image ID and name
        cnv_pr = image_pic.find('.//p:cNvPr', NSMAP)
        if cnv_pr is not None:
            cnv_pr.set('id', str(image_id))
            cnv_pr.set('name', f'VectorImage_{image_id}')

        # Update position and size
        xfrm = image_pic.find('.//a:xfrm', NSMAP)
        if xfrm is not None:
            off = xfrm.find('.//a:off', NSMAP)
            if off is not None:
                off.set('x', str(x_emu))
                off.set('y', str(y_emu))

            ext = xfrm.find('.//a:ext', NSMAP)
            if ext is not None:
                ext.set('cx', str(width_emu))
                ext.set('cy', str(height_emu))

        # Update relationship ID
        blip = image_pic.find('.//a:blip', NSMAP)
        if blip is not None:
            blip.set(QName(R_URI, 'embed'), rel_id)

        # Insert effects if provided
        if effects_xml:
            try:
                effects_element = ET.fromstring(effects_xml)
                sp_pr = image_pic.find('.//p:spPr', NSMAP)
                if sp_pr is not None:
                    # Simply append effects at the end of spPr
                    sp_pr.append(effects_element)
            except ET.XMLSyntaxError:
                self.logger.warning(f"Invalid effects XML provided: {effects_xml}")

        return image_pic

    def generate_diffuse_lighting_3d(self, light_direction: str = "tl",
                                    bevel_width: int = 50800, bevel_height: int = 25400,
                                    with_shadow: bool = False,
                                    shadow_blur: int = 25400, shadow_alpha: int = 25000) -> Element:
        """
        Generate 3D diffuse lighting effects using template.

        Args:
            light_direction: Light direction (tl, t, tr, r, br, b, bl, l)
            bevel_width: Bevel width in EMU
            bevel_height: Bevel height in EMU
            with_shadow: Whether to include inner shadow
            shadow_blur: Inner shadow blur radius in EMU
            shadow_alpha: Inner shadow alpha value (0-100000)

        Returns:
            3D lighting effects Element
        """
        template_name = "diffuse_lighting_with_shadow.xml" if with_shadow else "diffuse_lighting_3d.xml"
        lighting_element = self._template_loader.load_template(template_name)

        # Update bevel dimensions
        bevel_t = lighting_element.find('.//a:bevelT', NSMAP)
        if bevel_t is not None:
            bevel_t.set('w', str(bevel_width))
            bevel_t.set('h', str(bevel_height))

        # Update light direction
        light_rig = lighting_element.find('.//a:lightRig', NSMAP)
        if light_rig is not None:
            light_rig.set('rig', light_direction)

        # Update shadow properties if present
        if with_shadow:
            inner_shdw = lighting_element.find('.//a:innerShdw', NSMAP)
            if inner_shdw is not None:
                inner_shdw.set('blurRad', str(shadow_blur))

                # Update shadow alpha
                alpha_elem = inner_shdw.find('.//a:alpha', NSMAP)
                if alpha_elem is not None:
                    alpha_elem.set('val', str(shadow_alpha))

        return lighting_element

    def generate_diffuse_lighting_for_filter(self, light_type: Optional[str],
                                           light_params: Dict[str, float],
                                           surface_scale: float,
                                           diffuse_constant: float) -> str:
        """
        Generate diffuse lighting effects XML for filter processing.

        Args:
            light_type: Type of light source (distant, point, spot)
            light_params: Light source parameters
            surface_scale: Surface elevation scaling
            diffuse_constant: Material diffuse reflection constant

        Returns:
            XML string for diffuse lighting effects
        """
        # Calculate bevel depth based on surface scale
        bevel_width = min(int(surface_scale * 25400), 2540000)  # Cap at 100pt in EMU
        bevel_height = bevel_width // 2

        # Calculate light intensity based on diffuse constant
        light_intensity = min(int(diffuse_constant * 100000), 100000)  # 0-100%

        # Determine light direction based on light type
        light_direction = "tl"  # default top-left
        if light_type == 'distant' and light_params:
            azimuth = light_params.get('azimuth', 0)

            # Map azimuth to PowerPoint light directions
            if 0 <= azimuth < 45 or 315 <= azimuth < 360:
                light_direction = "t"  # top
            elif 45 <= azimuth < 135:
                light_direction = "tr"  # top-right
            elif 135 <= azimuth < 225:
                light_direction = "r"  # right
            elif 225 <= azimuth < 315:
                light_direction = "br"  # bottom-right

        # Include shadow for elevated surfaces
        with_shadow = surface_scale > 1.0
        shadow_blur = min(int(surface_scale * 12700), 127000) if with_shadow else 25400
        shadow_alpha = min(light_intensity // 2, 25000) if with_shadow else 25000

        # Generate lighting element using template
        lighting_element = self.generate_diffuse_lighting_3d(
            light_direction=light_direction,
            bevel_width=bevel_width,
            bevel_height=bevel_height,
            with_shadow=with_shadow,
            shadow_blur=shadow_blur,
            shadow_alpha=shadow_alpha
        )

        return self.element_to_string(lighting_element)

    def generate_specular_highlight_3d(self, light_direction: str = "tl",
                                      bevel_width: int = 50800, bevel_height: int = 25400,
                                      material: str = "metal",
                                      highlight_blur: int = 25400, highlight_alpha: int = 60000,
                                      highlight_color: str = "FFFFFF") -> Element:
        """
        Generate 3D specular highlight effects using template.

        Args:
            light_direction: Light direction (tl, t, tr, r, br, b, bl, l)
            bevel_width: Bevel width in EMU
            bevel_height: Bevel height in EMU
            material: PowerPoint material preset (metal, plastic, clear, etc.)
            highlight_blur: Highlight blur radius in EMU
            highlight_alpha: Highlight alpha value (0-100000)
            highlight_color: Highlight color (hex without #)

        Returns:
            lxml Element for specular highlight effects
        """
        highlight_element = self._template_loader.load_template("specular_highlight.xml")

        # Update 3D material properties
        sp3d = highlight_element.find('.//a:sp3d', {'a': A_URI})
        if sp3d is not None:
            sp3d.set('extrusionH', str(bevel_width))
            sp3d.set('contourW', str(bevel_height))
            sp3d.set('prstMaterial', material)

            # Update light rig direction
            lightrig = sp3d.find('.//a:lightRig', {'a': A_URI})
            if lightrig is not None:
                lightrig.set('dir', light_direction)

        # Update highlight shadow properties
        outer_shadow = highlight_element.find('.//a:outerShdw', {'a': A_URI})
        if outer_shadow is not None:
            outer_shadow.set('blurRad', str(highlight_blur))

            # Update highlight color and alpha
            srgb_clr = outer_shadow.find('.//a:srgbClr', {'a': A_URI})
            if srgb_clr is not None:
                srgb_clr.set('val', highlight_color)

                alpha = srgb_clr.find('.//a:alpha', {'a': A_URI})
                if alpha is not None:
                    alpha.set('val', str(highlight_alpha))

        return highlight_element

    def generate_reflection_effect_3d(self, light_direction: str = "tl",
                                     bevel_width: int = 76200, bevel_height: int = 38100,
                                     material: str = "clear",
                                     reflection_blur: int = 6350, reflection_alpha: int = 50000) -> Element:
        """
        Generate 3D reflection effects using template.

        Args:
            light_direction: Light direction for lighting rig
            bevel_width: Bevel width in EMU
            bevel_height: Bevel height in EMU
            material: PowerPoint material preset (clear, metal, etc.)
            reflection_blur: Reflection blur radius in EMU
            reflection_alpha: Reflection start alpha value (0-100000)

        Returns:
            lxml Element for reflection effects
        """
        reflection_element = self._template_loader.load_template("reflection_effect.xml")

        # Update 3D material properties
        sp3d = reflection_element.find('.//a:sp3d', {'a': A_URI})
        if sp3d is not None:
            sp3d.set('extrusionH', str(bevel_width))
            sp3d.set('contourW', str(bevel_height))
            sp3d.set('prstMaterial', material)

            # Update light rig direction
            lightrig = sp3d.find('.//a:lightRig', {'a': A_URI})
            if lightrig is not None:
                lightrig.set('dir', light_direction)

        # Update reflection properties
        reflection = reflection_element.find('.//a:reflection', {'a': A_URI})
        if reflection is not None:
            reflection.set('blurRad', str(reflection_blur))
            reflection.set('stA', str(reflection_alpha))

        return reflection_element

    def generate_specular_lighting_for_filter(self, light_type: Optional[str],
                                            light_params: Dict[str, float],
                                            surface_scale: float,
                                            specular_constant: float,
                                            specular_exponent: float,
                                            lighting_color: str = "FFFFFF") -> str:
        """
        Generate specular lighting effects XML for filter processing.

        Args:
            light_type: Type of light source (distant, point, spot)
            light_params: Light source parameters
            surface_scale: Surface elevation scaling
            specular_constant: Material specular reflection constant
            specular_exponent: Shininess/focus of specular highlights
            lighting_color: Light color (hex without #)

        Returns:
            XML string for specular lighting effects
        """
        # Calculate bevel dimensions based on surface scale
        bevel_width = min(int(abs(surface_scale) * 25400), 2540000)  # Cap at 100pt in EMU
        bevel_height = bevel_width // 2

        # Map specular exponent to material properties
        material = self._map_shininess_to_material(specular_exponent)

        # Determine light direction based on light type
        light_direction = "tl"  # default top-left
        if light_type == "distant" and light_params:
            azimuth = light_params.get('azimuth', 0)

            # Map azimuth to PowerPoint light directions
            if 0 <= azimuth < 45 or 315 <= azimuth < 360:
                light_direction = "t"  # top
            elif 45 <= azimuth < 135:
                light_direction = "tr"  # top-right
            elif 135 <= azimuth < 225:
                light_direction = "r"  # right
            elif 225 <= azimuth < 315:
                light_direction = "br"  # bottom-right

        # Calculate highlight parameters based on specular properties
        if specular_exponent >= 64.0:
            highlight_blur = int(surface_scale * 12700)  # Sharp highlight
            highlight_alpha = 80000  # High intensity for shiny surfaces
        elif specular_exponent >= 16.0:
            highlight_blur = int(surface_scale * 25400)  # Medium highlight
            highlight_alpha = 60000  # Medium intensity
        else:
            highlight_blur = int(surface_scale * 50800)  # Soft highlight
            highlight_alpha = 40000  # Lower intensity for matte surfaces

        # Scale highlight based on specular constant
        highlight_alpha = min(80000, int(specular_constant * 30000))

        # Use high reflectivity template for very shiny surfaces
        if specular_exponent > 100.0:
            lighting_element = self.generate_reflection_effect_3d(
                light_direction=light_direction,
                bevel_width=bevel_width,
                bevel_height=bevel_height,
                material=material,
                reflection_blur=highlight_blur // 4,
                reflection_alpha=highlight_alpha
            )
        else:
            lighting_element = self.generate_specular_highlight_3d(
                light_direction=light_direction,
                bevel_width=bevel_width,
                bevel_height=bevel_height,
                material=material,
                highlight_blur=highlight_blur,
                highlight_alpha=highlight_alpha,
                highlight_color=lighting_color
            )

        return self.element_to_string(lighting_element)

    def _map_shininess_to_material(self, specular_exponent: float) -> str:
        """
        Map specular exponent (shininess) to PowerPoint material properties.

        Args:
            specular_exponent: SVG specular exponent value

        Returns:
            PowerPoint preset material name
        """
        if specular_exponent <= 1.0:
            return "flat"         # No shininess - flat material
        elif specular_exponent <= 4.0:
            return "matte"        # Low shininess - matte material
        elif specular_exponent <= 16.0:
            return "plastic"      # Medium shininess - plastic material
        elif specular_exponent <= 32.0:
            return "softEdge"     # Medium-high shininess - soft edge material
        elif specular_exponent <= 64.0:
            return "metal"        # High shininess - metallic material
        elif specular_exponent <= 128.0:
            return "warmMatte"    # Very high shininess - warm matte (glass-like)
        else:
            return "clear"        # Extreme shininess - clear/mirror-like material


class FluentShapeBuilder:
    """
    Fluent builder for complex PowerPoint shapes.

    Provides a chainable interface for building shapes with geometry,
    styling, and other properties.
    """

    def __init__(self, xml_builder: EnhancedXMLBuilder, shape_id: int, name: str):
        """
        Initialize fluent shape builder.

        Args:
            xml_builder: Enhanced XML builder instance
            shape_id: Unique shape ID
            name: Shape name
        """
        self.xml_builder = xml_builder
        self.shape_element = xml_builder.create_shape_element(shape_id, name)

    def position(self, x: int, y: int) -> 'FluentShapeBuilder':
        """Set shape position."""
        xfrm = self.shape_element.find('.//a:xfrm', NSMAP)
        if xfrm is not None:
            off = xfrm.find('.//a:off', NSMAP)
            if off is not None:
                off.set('x', str(x))
                off.set('y', str(y))
        return self

    def size(self, width: int, height: int) -> 'FluentShapeBuilder':
        """Set shape size."""
        xfrm = self.shape_element.find('.//a:xfrm', NSMAP)
        if xfrm is not None:
            ext = xfrm.find('.//a:ext', NSMAP)
            if ext is not None:
                ext.set('cx', str(width))
                ext.set('cy', str(height))
        return self

    def geometry(self, geometry_element: Element) -> 'FluentShapeBuilder':
        """Add geometry to shape."""
        self.xml_builder.add_geometry_to_shape(self.shape_element, geometry_element)
        return self

    def build(self) -> Element:
        """Build and return the shape element."""
        return self.shape_element


# Singleton instance for global access (backward compatibility)
enhanced_xml_builder = EnhancedXMLBuilder()


def get_enhanced_xml_builder() -> EnhancedXMLBuilder:
    """Get the global enhanced XML builder instance."""
    return enhanced_xml_builder


# Factory functions for fluent building
def create_presentation(width_emu: int, height_emu: int, **kwargs) -> Element:
    """Create presentation element with enhanced builder."""
    return enhanced_xml_builder.create_presentation_element(width_emu, height_emu, **kwargs)


def create_slide(layout_id: int = 1) -> Element:
    """Create slide element with enhanced builder."""
    return enhanced_xml_builder.create_slide_element(layout_id)


def create_shape(shape_id: int, name: str) -> FluentShapeBuilder:
    """Create fluent shape builder."""
    return FluentShapeBuilder(enhanced_xml_builder, shape_id, name)


def create_content_types(**kwargs) -> Element:
    """Create content types element with enhanced builder."""
    return enhanced_xml_builder.create_content_types_element(**kwargs)


def create_relationships(relationships: List[Dict[str, str]]) -> Element:
    """Create relationships element with enhanced builder."""
    return enhanced_xml_builder.create_relationships_element(relationships)