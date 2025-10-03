#!/usr/bin/env python3
"""
Image Mapper - MediaRequest Pattern

Maps IR.Image elements to DrawingML <p:pic> using the MediaRequest pattern
for proper OPC relationship management.
"""

import logging
import hashlib
from typing import Optional
from lxml import etree as ET
from lxml.etree import Element, QName

from .base import Mapper, MapperResult, OutputFormat, MediaRequest
from ..ir import IRElement, Image
from ..policy import ImageDecision

logger = logging.getLogger(__name__)

# Namespace URIs
P_URI = "http://schemas.openxmlformats.org/presentationml/2006/main"
A_URI = "http://schemas.openxmlformats.org/drawingml/2006/main"
R_URI = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

NSMAP = {'p': P_URI, 'a': A_URI, 'r': R_URI}


class ImageMapper(Mapper):
    """Maps Image IR elements to DrawingML <p:pic>"""

    def __init__(self, policy, services=None):
        super().__init__(policy, services)
        self._counter = 1
        self._embedded_sha256 = set()

    def can_map(self, ir_element: IRElement) -> bool:
        return isinstance(ir_element, Image)

    def map(self, ir_element: IRElement) -> MapperResult:
        if not isinstance(ir_element, Image):
            raise ValueError(f"Expected Image, got {type(ir_element)}")

        image: Image = ir_element

        # Get policy decision
        decision = self.policy.decide_image(image, self._embedded_sha256)

        # Handle based on decision
        if not decision.embed_inline:
            # External reference (not implemented yet)
            return self._create_external_reference(image, decision)

        # Embed inline
        if image.sha256 and image.sha256 in self._embedded_sha256:
            # Already embedded - reuse (TODO: track rId mapping)
            logger.debug(f"Image already embedded: {image.sha256[:8]}...")

        # Load image data if not already loaded
        image_data = image.image_data or image.data  # Support legacy field
        if not image_data:
            image_data = self._load_image_data(image)

        # Calculate SHA-256 if not present
        sha256 = image.sha256
        if not sha256 and image_data:
            sha256 = hashlib.sha256(image_data).hexdigest()

        # Track as embedded
        if sha256:
            self._embedded_sha256.add(sha256)

        # Build <p:pic> XML element
        pic_elem = self._build_picture_xml(image)

        # Convert to XML string
        pic_xml = ET.tostring(pic_elem, encoding='unicode')

        # Create media request
        format_ext = image.format_ext or image.format or "png"  # Support legacy
        filename = f"image{self._counter}.{format_ext}"
        self._counter += 1

        media_req = MediaRequest(
            filename=filename,
            mime_type=image.mime_type or self._get_mime_type(format_ext),
            bytes_data=image_data,
            content_type_ext=format_ext,
            bind_xpath=".//a:blip",
            bind_attr=f"{{{R_URI}}}embed",
            sha256=sha256
        )

        return MapperResult(
            element=ir_element,
            output_format=OutputFormat.NATIVE_DML,
            xml_content=pic_xml,
            policy_decision=decision,
            media_requests=[media_req],
            metadata={
                'format': format_ext,
                'size_bytes': len(image_data) if image_data else 0,
                'sha256': sha256[:8] if sha256 else None,
                'dimensions': (image.width, image.height),
            }
        )

    def _load_image_data(self, image: Image) -> bytes:
        """Load image bytes from source"""
        # Check if data already populated
        if image.image_data:
            return image.image_data
        if image.data:  # Legacy field
            return image.data

        # Determine source type
        source_type = getattr(image, 'source_type', None)

        if source_type == "data_url":
            # Already decoded during parse
            raise ValueError("data_url should have image_data populated")

        elif source_type == "file" or not source_type:
            # Load from file
            href = image.href
            if href.startswith("file://"):
                href = href[7:]  # Remove file:// prefix

            try:
                with open(href, 'rb') as f:
                    return f.read()
            except FileNotFoundError:
                logger.error(f"Image file not found: {href}")
                raise

        elif source_type in ("http", "https"):
            # Fetch from URL
            try:
                import requests
                resp = requests.get(image.href, timeout=10)
                resp.raise_for_status()
                return resp.content
            except ImportError:
                raise ValueError("HTTP image source requires 'requests' library")
            except Exception as e:
                logger.error(f"Failed to fetch image from {image.href}: {e}")
                raise

        else:
            raise ValueError(f"Unsupported source type: {source_type}")

    def _build_picture_xml(self, image: Image) -> Element:
        """Build DrawingML <p:pic> element WITHOUT r:embed (filled later)"""
        # Convert SVG units to EMUs (1px ≈ 9525 EMU)
        # Use new fields with fallback to legacy
        x = image.x if hasattr(image, 'x') else (image.origin.x if hasattr(image, 'origin') else 0)
        y = image.y if hasattr(image, 'y') else (image.origin.y if hasattr(image, 'origin') else 0)
        width = image.width if hasattr(image, 'width') else (image.size.width if hasattr(image, 'size') else 0)
        height = image.height if hasattr(image, 'height') else (image.size.height if hasattr(image, 'size') else 0)

        x_emu = str(int(x * 9525))
        y_emu = str(int(y * 9525))
        cx_emu = str(int(width * 9525))
        cy_emu = str(int(height * 9525))

        pic = Element(QName(P_URI, "pic"), nsmap=NSMAP)

        # Non-visual properties
        nvPicPr = Element(QName(P_URI, "nvPicPr"))
        cNvPr = Element(QName(P_URI, "cNvPr"))
        cNvPr.set("id", str(self._counter))
        cNvPr.set("name", getattr(image, 'title', None) or f"Picture {self._counter}")
        if hasattr(image, 'desc') and image.desc:
            cNvPr.set("descr", image.desc)
        nvPicPr.append(cNvPr)
        nvPicPr.append(Element(QName(P_URI, "cNvPicPr")))
        nvPicPr.append(Element(QName(P_URI, "nvPr")))
        pic.append(nvPicPr)

        # Blip fill (r:embed will be set by embedder)
        blipFill = Element(QName(P_URI, "blipFill"))
        blip = Element(QName(A_URI, "blip"))
        # Note: r:embed NOT set here - embedder will patch it
        blipFill.append(blip)

        stretch = Element(QName(A_URI, "stretch"))
        stretch.append(Element(QName(A_URI, "fillRect")))
        blipFill.append(stretch)
        pic.append(blipFill)

        # Shape properties
        spPr = Element(QName(P_URI, "spPr"))
        xfrm = Element(QName(A_URI, "xfrm"))
        xfrm.append(Element(QName(A_URI, "off"), x=x_emu, y=y_emu))
        xfrm.append(Element(QName(A_URI, "ext"), cx=cx_emu, cy=cy_emu))
        spPr.append(xfrm)

        prstGeom = Element(QName(A_URI, "prstGeom"), prst="rect")
        prstGeom.append(Element(QName(A_URI, "avLst")))
        spPr.append(prstGeom)
        pic.append(spPr)

        return pic

    def _get_mime_type(self, format_ext: str) -> str:
        """Get MIME type from file extension"""
        mime_map = {
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "gif": "image/gif",
            "bmp": "image/bmp",
            "tif": "image/tiff",
            "tiff": "image/tiff",
            "webp": "image/webp",
        }
        return mime_map.get(format_ext.lower(), "image/png")

    def _create_external_reference(self, image: Image, decision: ImageDecision) -> MapperResult:
        """Create external image reference (for http:// URLs)"""
        # Not implemented yet - would use TargetMode="External"
        raise NotImplementedError("External image references not yet implemented")


def create_image_mapper(policy, services=None) -> ImageMapper:
    """
    Create ImageMapper with policy engine.

    Args:
        policy: Policy engine for decisions
        services: Optional services for image processing integration

    Returns:
        Configured ImageMapper
    """
    return ImageMapper(policy, services)
