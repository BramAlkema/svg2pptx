#!/usr/bin/env python3
"""
DrawingML Embedder

Embeds mapped IR elements into PowerPoint slide structures.
Handles XML injection, relationship management, and slide coordination.
"""

import time
import logging
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass
from lxml import etree as ET
from ..xml.safe_iter import walk

from ..map.base import MapperResult, OutputFormat
from ..ir import IRElement, SceneGraph, Rect

logger = logging.getLogger(__name__)


class EmbeddingError(Exception):
    """Exception raised when embedding fails"""
    def __init__(self, message: str, element: IRElement = None, cause: Exception = None):
        super().__init__(message)
        self.element = element
        self.cause = cause


@dataclass
class EmbedderResult:
    """Result of embedding mapper results into PPTX structure"""
    slide_xml: str
    relationship_data: List[Dict[str, Any]]
    media_files: List[Dict[str, Any]]

    # Statistics
    elements_embedded: int = 0
    native_elements: int = 0
    emf_elements: int = 0
    processing_time_ms: float = 0.0

    # Quality metrics
    total_size_bytes: int = 0
    estimated_quality: float = 1.0
    estimated_performance: float = 1.0


class DrawingMLEmbedder:
    """
    Embeds mapped IR elements into PowerPoint slide structures.

    Takes MapperResults and combines them into complete slide XML with
    proper relationships, media files, and coordinate positioning.
    """

    def __init__(self, slide_width_emu: int = 9144000, slide_height_emu: int = 6858000):
        """
        Initialize embedder with slide dimensions.

        Args:
            slide_width_emu: Slide width in EMU (default: 10 inches)
            slide_height_emu: Slide height in EMU (default: 7.5 inches)
        """
        self.slide_width_emu = slide_width_emu
        self.slide_height_emu = slide_height_emu
        self.logger = logging.getLogger(__name__)

        # Counters for unique IDs
        self._shape_id_counter = 1
        self._relationship_id_counter = 1

        # Statistics
        self._stats = {
            'total_embedded': 0,
            'native_count': 0,
            'emf_count': 0,
            'error_count': 0,
            'total_time_ms': 0.0
        }

    def embed_scene(self, scene: SceneGraph, mapper_results: List[MapperResult]) -> EmbedderResult:
        """
        Embed complete scene into PowerPoint slide.

        Args:
            scene: IR Scene containing layout information
            mapper_results: List of mapped IR elements

        Returns:
            EmbedderResult with complete slide XML and relationships

        Raises:
            EmbeddingError: If embedding fails
        """
        start_time = time.perf_counter()

        try:
            # Generate slide XML structure
            slide_xml = self._generate_slide_xml(scene, mapper_results)

            # Extract relationship data for EMF elements
            relationship_data = self._extract_relationships(mapper_results)

            # Extract media files for embedded content
            media_files = self._extract_media_files(mapper_results)

            # Calculate statistics
            native_count = sum(1 for r in mapper_results if r.output_format == OutputFormat.NATIVE_DML)
            emf_count = len(mapper_results) - native_count
            total_size = sum(r.output_size_bytes for r in mapper_results)
            avg_quality = sum(r.estimated_quality for r in mapper_results) / max(len(mapper_results), 1)
            avg_performance = sum(r.estimated_performance for r in mapper_results) / max(len(mapper_results), 1)

            processing_time = (time.perf_counter() - start_time) * 1000

            result = EmbedderResult(
                slide_xml=slide_xml,
                relationship_data=relationship_data,
                media_files=media_files,
                elements_embedded=len(mapper_results),
                native_elements=native_count,
                emf_elements=emf_count,
                processing_time_ms=processing_time,
                total_size_bytes=total_size,
                estimated_quality=avg_quality,
                estimated_performance=avg_performance
            )

            # Record statistics
            self._record_embedding(result)

            return result

        except Exception as e:
            self._record_error(e)
            raise EmbeddingError(f"Failed to embed scene: {e}", cause=e)

    def embed_elements(self, mapper_results: List[MapperResult],
                      viewport: Rect = None) -> EmbedderResult:
        """
        Embed list of mapped elements into slide structure.

        Args:
            mapper_results: List of mapped IR elements
            viewport: Optional viewport for coordinate transformation

        Returns:
            EmbedderResult with slide XML and relationships
        """
        # Create minimal scene if none provided
        if viewport is None:
            viewport = Rect(0, 0, self.slide_width_emu / 12700, self.slide_height_emu / 12700)

        minimal_scene = SceneGraph(
            elements=[],  # Elements already mapped
            viewport=viewport,
            background=None
        )

        return self.embed_scene(minimal_scene, mapper_results)

    def _generate_slide_xml(self, scene: SceneGraph, mapper_results: List[MapperResult]) -> str:
        """Generate complete slide XML with embedded elements"""
        try:
            # Generate background if present
            background_xml = ""
            # SceneGraph is a List[IRElement], so no background attribute
            # Background would be handled as an element in the scene list

            # Combine all element XML content
            shape_xmls = []
            for result in mapper_results:
                # Assign unique shape ID
                shape_xml = self._assign_shape_id(result.xml_content)
                shape_xmls.append(shape_xml)

            # Generate complete slide XML
            slide_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
       xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
       xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
    <p:cSld>
        {background_xml}
        <p:spTree>
            <p:nvGrpSpPr>
                <p:cNvPr id="1" name=""/>
                <p:cNvGrpSpPr/>
                <p:nvPr/>
            </p:nvGrpSpPr>
            <p:grpSpPr>
                <a:xfrm>
                    <a:off x="0" y="0"/>
                    <a:ext cx="{self.slide_width_emu}" cy="{self.slide_height_emu}"/>
                    <a:chOff x="0" y="0"/>
                    <a:chExt cx="{self.slide_width_emu}" cy="{self.slide_height_emu}"/>
                </a:xfrm>
            </p:grpSpPr>
            {chr(10).join(shape_xmls)}
        </p:spTree>
    </p:cSld>
    <p:clrMapOvr>
        <a:masterClrMapping/>
    </p:clrMapOvr>
</p:sld>"""

            return slide_xml

        except Exception as e:
            raise EmbeddingError(f"Failed to generate slide XML: {e}", cause=e)

    def _assign_shape_id(self, shape_xml: str) -> str:
        """Assign unique ID to shape XML"""
        try:
            # Parse XML to modify ID attribute
            root = ET.fromstring(f"<root>{shape_xml}</root>")

            # Find first element with cNvPr and update ID
            for elem in walk(root):
                if elem.tag.endswith('cNvPr'):
                    elem.set('id', str(self._shape_id_counter))
                    elem.set('name', f"Shape_{self._shape_id_counter}")
                    self._shape_id_counter += 1
                    break

            # Extract modified content
            modified_xml = "".join(ET.tostring(child, encoding='unicode') for child in root)
            return modified_xml

        except ET.ParseError:
            # If XML parsing fails, return original with basic ID replacement
            self._shape_id_counter += 1
            return shape_xml.replace('id="1"', f'id="{self._shape_id_counter - 1}"')

    def _extract_relationships(self, mapper_results: List[MapperResult]) -> List[Dict[str, Any]]:
        """Extract relationship data for EMF and media elements"""
        relationships = []

        for result in mapper_results:
            if result.output_format in [OutputFormat.EMF_VECTOR, OutputFormat.EMF_RASTER]:
                # EMF elements need relationship entries
                rel_id = f"rId{self._relationship_id_counter}"
                self._relationship_id_counter += 1

                relationships.append({
                    'id': rel_id,
                    'type': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/image',
                    'target': f'../media/emf{self._relationship_id_counter}.emf',
                    'content_type': 'application/emf',
                    'element_type': type(result.element).__name__,
                    'fallback_reason': result.metadata.get('fallback_reason', 'Complex element requires EMF')
                })

        return relationships

    def _extract_media_files(self, mapper_results: List[MapperResult]) -> List[Dict[str, Any]]:
        """Extract media files that need to be included in PPTX package"""
        media_files = []

        for result in mapper_results:
            # Check if element has embedded media data
            if 'media_data' in result.metadata:
                media_files.append({
                    'filename': result.metadata.get('media_filename', 'unknown'),
                    'content_type': result.metadata.get('content_type', 'application/octet-stream'),
                    'data': result.metadata['media_data'],
                    'element_type': type(result.element).__name__
                })

            # EMF elements also generate media files
            elif result.output_format in [OutputFormat.EMF_VECTOR, OutputFormat.EMF_RASTER]:
                media_files.append({
                    'filename': f'emf{len(media_files) + 1}.emf',
                    'content_type': 'application/emf',
                    'data': b'',  # EMF data would be generated separately
                    'element_type': type(result.element).__name__,
                    'requires_rendering': True
                })

        return media_files

    def _generate_background_xml(self, background: Any) -> str:
        """Generate background XML if scene has background"""
        if not background:
            return ""

        # Simplified background generation
        return '<p:bg><p:bgPr><a:solidFill><a:srgbClr val="FFFFFF"/></a:solidFill></p:bgPr></p:bg>'

    def _record_embedding(self, result: EmbedderResult) -> None:
        """Record embedding statistics"""
        self._stats['total_embedded'] += result.elements_embedded
        self._stats['native_count'] += result.native_elements
        self._stats['emf_count'] += result.emf_elements
        self._stats['total_time_ms'] += result.processing_time_ms

    def _record_error(self, error: Exception) -> None:
        """Record embedding error"""
        self._stats['error_count'] += 1

    def get_statistics(self) -> Dict[str, Any]:
        """Get embedding statistics"""
        total = max(self._stats['total_embedded'], 1)
        return {
            **self._stats,
            'native_ratio': self._stats['native_count'] / total,
            'emf_ratio': self._stats['emf_count'] / total,
            'avg_time_ms': self._stats['total_time_ms'] / max(self._stats['total_embedded'], 1),
            'current_shape_id': self._shape_id_counter,
            'current_rel_id': self._relationship_id_counter
        }

    def reset_statistics(self) -> None:
        """Reset embedding statistics"""
        self._stats = {
            'total_embedded': 0,
            'native_count': 0,
            'emf_count': 0,
            'error_count': 0,
            'total_time_ms': 0.0
        }

    def get_slide_dimensions(self) -> Tuple[int, int]:
        """Get slide dimensions in EMU"""
        return (self.slide_width_emu, self.slide_height_emu)

    def set_slide_dimensions(self, width_emu: int, height_emu: int) -> None:
        """Set slide dimensions in EMU"""
        self.slide_width_emu = width_emu
        self.slide_height_emu = height_emu


def create_embedder(slide_width_emu: int = 9144000,
                   slide_height_emu: int = 6858000) -> DrawingMLEmbedder:
    """
    Create DrawingMLEmbedder with specified slide dimensions.

    Args:
        slide_width_emu: Slide width in EMU (default: 10 inches)
        slide_height_emu: Slide height in EMU (default: 7.5 inches)

    Returns:
        Configured DrawingMLEmbedder
    """
    return DrawingMLEmbedder(slide_width_emu, slide_height_emu)