#!/usr/bin/env python3
"""
Content Types Manager for PPTX [Content_Types].xml

Manages content type registrations for PPTX package parts
following ECMA-376 Open Packaging Conventions.
"""

from lxml import etree as ET
from lxml.etree import Element, QName

CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"


class ContentTypesManager:
    """Manages [Content_Types].xml for PPTX package"""

    def __init__(self, base_xml: bytes = None):
        """
        Initialize content types manager.

        Args:
            base_xml: Optional existing [Content_Types].xml bytes to load
        """
        if base_xml:
            self.root = ET.fromstring(base_xml)
        else:
            self.root = self._create_skeleton()

    def _create_skeleton(self) -> Element:
        """Create minimal [Content_Types].xml skeleton"""
        root = Element(QName(CT_NS, "Types"), nsmap={None: CT_NS})

        # Set root first so add_default() can use it
        self.root = root

        # Common defaults
        defaults = [
            ("xml", "application/xml"),
            ("rels", "application/vnd.openxmlformats-package.relationships+xml"),
        ]
        for ext, ct in defaults:
            self.add_default(ext, ct)

        return root

    def add_default(self, extension: str, content_type: str):
        """
        Add <Default Extension="..." ContentType="..."/>

        Args:
            extension: File extension (e.g., "png")
            content_type: MIME type (e.g., "image/png")
        """
        # Check if exists
        for node in self.root.findall(f"{{{CT_NS}}}Default"):
            if node.get("Extension") == extension:
                return  # Already exists

        default = ET.SubElement(self.root, QName(CT_NS, "Default"))
        default.set("Extension", extension)
        default.set("ContentType", content_type)

    def add_override(self, part_name: str, content_type: str):
        """
        Add <Override PartName="..." ContentType="..."/>

        Args:
            part_name: Part name with leading slash (e.g., "/ppt/slides/slide1.xml")
            content_type: MIME type (e.g., "application/vnd.openxmlformats-officedocument.presentationml.slide+xml")
        """
        # Check if exists
        for node in self.root.findall(f"{{{CT_NS}}}Override"):
            if node.get("PartName") == part_name:
                return  # Already exists

        override = ET.SubElement(self.root, QName(CT_NS, "Override"))
        override.set("PartName", part_name)
        override.set("ContentType", content_type)

    def ensure_image_type(self, extension: str):
        """
        Ensure image extension is registered.

        Args:
            extension: Image file extension (e.g., "png", "jpg")
        """
        mime_map = {
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "gif": "image/gif",
            "bmp": "image/bmp",
            "tif": "image/tiff",
            "tiff": "image/tiff",
            "webp": "image/webp",
            "svg": "image/svg+xml",
        }
        content_type = mime_map.get(extension.lower(), "image/png")
        self.add_default(extension, content_type)

    def ensure_presentation_types(self):
        """Ensure common presentation types are registered"""
        # Common PPTX overrides
        overrides = [
            ("/ppt/presentation.xml", "application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"),
            ("/ppt/presProps.xml", "application/vnd.openxmlformats-officedocument.presentationml.presProps+xml"),
            ("/ppt/tableStyles.xml", "application/vnd.openxmlformats-officedocument.presentationml.tableStyles+xml"),
            ("/ppt/viewProps.xml", "application/vnd.openxmlformats-officedocument.presentationml.viewProps+xml"),
        ]

        for part_name, content_type in overrides:
            self.add_override(part_name, content_type)

    def add_slide(self, slide_num: int):
        """
        Register slide part.

        Args:
            slide_num: Slide number (1-indexed)
        """
        part_name = f"/ppt/slides/slide{slide_num}.xml"
        content_type = "application/vnd.openxmlformats-officedocument.presentationml.slide+xml"
        self.add_override(part_name, content_type)

    def add_slide_layout(self, layout_num: int):
        """
        Register slide layout part.

        Args:
            layout_num: Layout number (1-indexed)
        """
        part_name = f"/ppt/slideLayouts/slideLayout{layout_num}.xml"
        content_type = "application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"
        self.add_override(part_name, content_type)

    def add_slide_master(self, master_num: int):
        """
        Register slide master part.

        Args:
            master_num: Master number (1-indexed)
        """
        part_name = f"/ppt/slideMasters/slideMaster{master_num}.xml"
        content_type = "application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"
        self.add_override(part_name, content_type)

    def to_xml(self) -> Element:
        """Get XML element"""
        return self.root

    def to_xml_bytes(self) -> bytes:
        """Serialize to XML bytes"""
        return ET.tostring(self.root, xml_declaration=True, encoding="UTF-8", pretty_print=True)
