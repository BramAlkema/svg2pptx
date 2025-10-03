#!/usr/bin/env python3
"""
Enhanced Slide Builder with Proper XML Handling

Improvements:
- Proper XML manipulation using lxml.etree instead of string replace
- Schema validation support
- Mapper Protocol for consistent interfaces
- XML Builder pattern for cleaner construction
- Enhanced error context and logging
- Performance optimizations with caching
"""

import time
import logging
from typing import Dict, Any, Optional, List, Protocol, runtime_checkable
from dataclasses import dataclass
from enum import Enum
from lxml import etree as ET
from lxml.etree import Element, QName
import hashlib

from ..ir import SceneGraph, IRElement
from ..map.base import MapperResult
from ..policy import Policy
from .embedder import DrawingMLEmbedder, EmbedderResult

logger = logging.getLogger(__name__)

# OpenXML Namespaces
P_URI = "http://schemas.openxmlformats.org/presentationml/2006/main"
R_URI = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
A_URI = "http://schemas.openxmlformats.org/drawingml/2006/main"

NSMAP = {
    'p': P_URI,
    'r': R_URI,
    'a': A_URI
}


@runtime_checkable
class MapperProtocol(Protocol):
    """Protocol defining mapper interface"""

    def can_map(self, element: IRElement) -> bool:
        """Check if this mapper can handle the element"""
        ...

    def map(self, element: IRElement) -> MapperResult:
        """Map IR element to DrawingML"""
        ...

    def get_statistics(self) -> Dict[str, Any]:
        """Get mapper statistics"""
        ...

    def reset_statistics(self) -> None:
        """Reset mapper statistics"""
        ...


class SlideTemplate(Enum):
    """Standard slide templates"""
    BLANK = "blank"
    TITLE_SLIDE = "title_slide"
    CONTENT = "content"
    TWO_CONTENT = "two_content"
    COMPARISON = "comparison"


@dataclass
class SlideMetadata:
    """Metadata for generated slide"""
    template: SlideTemplate
    title: Optional[str] = None
    notes: Optional[str] = None
    layout_id: int = 1
    master_id: int = 1
    slide_index: Optional[int] = None  # For better error context


class SlideXMLBuilder:
    """Builder pattern for constructing slide XML"""

    def __init__(self):
        """Initialize XML builder"""
        self.root = None
        self._reset()

    def _reset(self):
        """Reset builder state"""
        self.root = Element(QName(P_URI, 'sld'), nsmap=NSMAP)
        self.cSld = ET.SubElement(self.root, QName(P_URI, 'cSld'))
        self.spTree = ET.SubElement(self.cSld, QName(P_URI, 'spTree'))
        self._add_group_shape_properties()

    def _add_group_shape_properties(self):
        """Add group shape properties"""
        nvGrpSpPr = ET.SubElement(self.spTree, QName(P_URI, 'nvGrpSpPr'))
        cNvPr = ET.SubElement(nvGrpSpPr, QName(P_URI, 'cNvPr'))
        cNvPr.set('id', '1')
        cNvPr.set('name', '')
        ET.SubElement(nvGrpSpPr, QName(P_URI, 'cNvGrpSpPr'))
        ET.SubElement(nvGrpSpPr, QName(P_URI, 'nvPr'))

        grpSpPr = ET.SubElement(self.spTree, QName(P_URI, 'grpSpPr'))
        xfrm = ET.SubElement(grpSpPr, QName(A_URI, 'xfrm'))
        off = ET.SubElement(xfrm, QName(A_URI, 'off'))
        off.set('x', '0')
        off.set('y', '0')
        ext = ET.SubElement(xfrm, QName(A_URI, 'ext'))
        ext.set('cx', '9144000')
        ext.set('cy', '6858000')

    def add_shape(self, shape_xml: Element) -> 'SlideXMLBuilder':
        """Add shape to slide"""
        self.spTree.append(shape_xml)
        return self

    def add_layout_reference(self, layout_id: int, rel_id: str = 'rId1') -> 'SlideXMLBuilder':
        """Add slide layout reference"""
        # Remove existing if present
        existing = self.root.find(f'.//p:sldLayoutIdLst', NSMAP)
        if existing is not None:
            self.root.remove(existing)

        sldLayoutIdLst = ET.SubElement(self.root, QName(P_URI, 'sldLayoutIdLst'))
        sldLayoutId = ET.SubElement(sldLayoutIdLst, QName(P_URI, 'sldLayoutId'))
        sldLayoutId.set('id', str(layout_id))
        sldLayoutId.set(QName(R_URI, 'id'), rel_id)
        return self

    def add_master_reference(self, master_id: int, rel_id: str = 'rId2') -> 'SlideXMLBuilder':
        """Add slide master reference"""
        # Remove existing if present
        existing = self.root.find(f'.//p:sldMasterIdLst', NSMAP)
        if existing is not None:
            self.root.remove(existing)

        sldMasterIdLst = ET.SubElement(self.root, QName(P_URI, 'sldMasterIdLst'))
        sldMasterId = ET.SubElement(sldMasterIdLst, QName(P_URI, 'sldMasterId'))
        sldMasterId.set('id', str(master_id))
        sldMasterId.set(QName(R_URI, 'id'), rel_id)
        return self

    def add_notes(self, notes_content: str) -> 'SlideXMLBuilder':
        """Add notes to slide"""
        # Remove existing if present
        existing = self.root.find(f'.//p:notes', NSMAP)
        if existing is not None:
            self.root.remove(existing)

        notes = ET.SubElement(self.root, QName(P_URI, 'notes'))
        notes.text = notes_content
        return self

    def add_timing(self, timing_xml: Element) -> 'SlideXMLBuilder':
        """Add timing/animation information"""
        self.root.append(timing_xml)
        return self

    def build(self) -> str:
        """Build final XML string"""
        return ET.tostring(self.root, xml_declaration=True,
                          encoding='UTF-8', pretty_print=True).decode('utf-8')

    def build_element(self) -> Element:
        """Build as Element for further manipulation"""
        return self.root


class EnhancedSlideBuilder:
    """
    Enhanced slide builder with proper XML handling and validation.

    Improvements over original:
    - Proper XML manipulation using lxml
    - Schema validation support
    - Consistent mapper interfaces
    - Better error context
    - Performance optimizations
    """

    def __init__(self, mappers: Dict[str, MapperProtocol],
                 embedder: DrawingMLEmbedder,
                 policy: Policy,
                 validate_schema: bool = False,
                 schema_path: Optional[str] = None):
        """
        Initialize enhanced slide builder.

        Args:
            mappers: Dictionary of element type -> mapper
            embedder: DrawingML embedder for final slide assembly
            policy: Policy engine for mapping decisions
            validate_schema: Enable XML schema validation
            schema_path: Path to OOXML schema file
        """
        self.mappers = self._validate_mappers(mappers)
        self.embedder = embedder
        self.policy = policy
        self.validate_schema = validate_schema
        self.logger = logging.getLogger(__name__)

        # Load schema if validation enabled
        self.schema = None
        if validate_schema and schema_path:
            try:
                with open(schema_path, 'rb') as f:
                    schema_doc = ET.parse(f)
                    self.schema = ET.XMLSchema(schema_doc)
            except Exception as e:
                self.logger.warning(f"Failed to load schema: {e}")
                self.validate_schema = False

        # Performance cache
        self._xml_cache = {}
        self._cache_hits = 0
        self._cache_misses = 0

        # Statistics
        self._stats = {
            'slides_built': 0,
            'total_elements': 0,
            'total_time_ms': 0.0,
            'avg_elements_per_slide': 0.0,
            'xml_parse_errors': 0,
            'schema_validation_errors': 0,
            'cache_hit_rate': 0.0
        }

    def _validate_mappers(self, mappers: Dict[str, Any]) -> Dict[str, MapperProtocol]:
        """Validate that all mappers implement the protocol"""
        validated = {}
        for name, mapper in mappers.items():
            if not isinstance(mapper, MapperProtocol):
                self.logger.warning(f"Mapper '{name}' doesn't implement MapperProtocol")
                # Wrap in adapter if needed
                validated[name] = self._create_mapper_adapter(mapper)
            else:
                validated[name] = mapper
        return validated

    def _create_mapper_adapter(self, mapper: Any) -> MapperProtocol:
        """Create adapter for non-protocol mappers"""
        class MapperAdapter:
            def __init__(self, wrapped):
                self.wrapped = wrapped

            def can_map(self, element: IRElement) -> bool:
                if hasattr(self.wrapped, 'can_map'):
                    return self.wrapped.can_map(element)
                return False

            def map(self, element: IRElement) -> MapperResult:
                return self.wrapped.map(element)

            def get_statistics(self) -> Dict[str, Any]:
                if hasattr(self.wrapped, 'get_statistics'):
                    return self.wrapped.get_statistics()
                return {}

            def reset_statistics(self) -> None:
                if hasattr(self.wrapped, 'reset_statistics'):
                    self.wrapped.reset_statistics()

        return MapperAdapter(mapper)

    def build_slide(self, scene: SceneGraph, metadata: SlideMetadata = None) -> EmbedderResult:
        """
        Build complete slide from IR scene with enhanced XML handling.

        Args:
            scene: IR scene to convert
            metadata: Optional slide metadata

        Returns:
            EmbedderResult with complete slide structure
        """
        start_time = time.perf_counter()

        try:
            # Handle scene as either a list (SceneGraph) or an object with .elements
            elements = scene if isinstance(scene, list) else scene.elements
            if not scene or not elements:
                raise ValueError("Scene must contain elements")

            # Apply default metadata
            if metadata is None:
                metadata = SlideMetadata(template=SlideTemplate.BLANK)

            # Check cache for identical scenes
            scene_hash = self._compute_scene_hash(elements)
            if scene_hash in self._xml_cache:
                self._cache_hits += 1
                cached_result = self._xml_cache[scene_hash]
                self.logger.debug(f"Cache hit for scene {scene_hash[:8]}")
                return cached_result

            self._cache_misses += 1

            # Map all scene elements
            mapper_results = self._map_scene_elements(elements, metadata.slide_index)

            # Embed into slide structure
            result = self.embedder.embed_scene(scene, mapper_results)

            # Apply hyperlinks after embedding but before metadata
            result.slide_xml = self._apply_hyperlinks(result.slide_xml, mapper_results)

            # Apply metadata with proper XML handling
            result.slide_xml = self._apply_slide_metadata_xml(
                result.slide_xml, metadata
            )

            # Validate if enabled
            if self.validate_schema:
                self._validate_slide_xml(result.slide_xml, metadata.slide_index)

            # Cache result
            if len(self._xml_cache) < 100:  # Limit cache size
                self._xml_cache[scene_hash] = result

            # Record statistics
            processing_time = (time.perf_counter() - start_time) * 1000
            self._record_slide_build(len(elements), processing_time)

            return result

        except Exception as e:
            slide_info = f"slide {metadata.slide_index}" if metadata and metadata.slide_index else "slide"
            self.logger.error(f"Failed to build {slide_info}: {e}")
            raise RuntimeError(f"Slide building failed for {slide_info}: {e}") from e

    def _compute_scene_hash(self, elements: List[IRElement]) -> str:
        """Compute hash of scene for caching"""
        # Simple hash based on element count and types
        # In production, would need more sophisticated hashing
        content = f"{len(elements)}:{[type(e).__name__ for e in elements]}"
        return hashlib.md5(content.encode()).hexdigest()

    def _apply_slide_metadata_xml(self, slide_xml: str, metadata: SlideMetadata) -> str:
        """
        Apply slide metadata using proper XML manipulation.

        This replaces string manipulation with proper lxml operations.
        """
        try:
            # Parse XML
            if isinstance(slide_xml, bytes):
                tree = ET.fromstring(slide_xml)
            else:
                tree = ET.fromstring(slide_xml.encode('utf-8'))

            # Validate root element
            if tree.tag != QName(P_URI, 'sld'):
                raise ValueError(f"Invalid slide root element: {tree.tag}")

            # Use builder pattern for clean construction
            builder = SlideXMLBuilder()

            # Copy existing content
            for child in tree:
                if child.tag == QName(P_URI, 'cSld'):
                    # Copy slide content
                    for shape in child.find(f'.//p:spTree', NSMAP):
                        if shape.tag not in [QName(P_URI, 'nvGrpSpPr'), QName(P_URI, 'grpSpPr')]:
                            builder.add_shape(shape)

            # Add metadata
            builder.add_layout_reference(metadata.layout_id)
            builder.add_master_reference(metadata.master_id)

            if metadata.notes:
                builder.add_notes(metadata.notes)

            # Add any timing/animation from original
            timing = tree.find(f'.//p:timing', NSMAP)
            if timing is not None:
                builder.add_timing(timing)

            return builder.build()

        except ET.XMLSyntaxError as e:
            self._stats['xml_parse_errors'] += 1
            slide_info = f"slide {metadata.slide_index}" if metadata.slide_index else "slide"
            self.logger.warning(f"XML parse error for {slide_info}: {e}")
            # Return unmodified on parse error
            return slide_xml
        except Exception as e:
            slide_info = f"slide {metadata.slide_index}" if metadata.slide_index else "slide"
            self.logger.warning(f"Failed to apply metadata to {slide_info}: {e}")
            return slide_xml

    def _apply_hyperlinks(self, slide_xml: str, mapper_results: List[MapperResult]) -> str:
        """
        Apply hyperlinks to slide XML based on MapperResult hyperlink data.

        Args:
            slide_xml: Current slide XML content
            mapper_results: List of mapper results potentially containing hyperlinks

        Returns:
            Modified slide XML with hyperlinks applied

        Process:
        1. Extract mapper results that have hyperlinks
        2. Build shape index from slide XML (cNvPr @id/@name -> shape element)
        3. For each hyperlink result:
           - Find target shape by shape_id
           - Apply shape-level hyperlinks using embedder.attach_hlink_to_shape()
           - Apply text-level hyperlinks using embedder.attach_hlink_to_run()
        4. Return modified slide XML
        """
        try:
            # Filter results that have hyperlinks
            hyperlink_results = [r for r in mapper_results
                               if r.hyperlinks and len(r.hyperlinks) > 0]

            if not hyperlink_results:
                # No hyperlinks to apply
                return slide_xml

            self.logger.debug(f"Applying hyperlinks from {len(hyperlink_results)} mapper results")

            # Parse slide XML for shape identification and manipulation
            namespaces = {
                'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
                'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
                'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
            }

            # Parse XML with namespace support
            if isinstance(slide_xml, bytes):
                tree = ET.fromstring(slide_xml)
            else:
                tree = ET.fromstring(slide_xml.encode('utf-8'))

            # Build shape index: shape_id -> shape_element
            shape_index = self._build_shape_index(tree, namespaces)

            # Apply hyperlinks from each mapper result
            for result in hyperlink_results:
                try:
                    self._apply_result_hyperlinks(tree, result, shape_index, namespaces)
                except Exception as e:
                    self.logger.error(f"Failed to apply hyperlinks for {type(result.element).__name__}: {e}")
                    # Continue with other results

            # Convert back to string
            modified_xml = ET.tostring(tree, encoding='unicode')
            return modified_xml

        except ET.XMLSyntaxError as e:
            self.logger.error(f"Failed to parse slide XML for hyperlink application: {e}")
            return slide_xml  # Return original on parse failure
        except Exception as e:
            self.logger.error(f"Failed to apply hyperlinks: {e}")
            return slide_xml  # Return original on any failure

    def _build_shape_index(self, tree: Element, namespaces: Dict[str, str]) -> Dict[str, Element]:
        """
        Build index of shape_id -> shape element for hyperlink targeting.

        Args:
            tree: Parsed slide XML tree
            namespaces: XML namespace mapping

        Returns:
            Dictionary mapping shape IDs to shape elements
        """
        shape_index = {}

        try:
            # Find all cNvPr elements (which contain shape IDs)
            for cnvpr in tree.xpath('.//p:cNvPr', namespaces=namespaces):
                # Get shape ID from id attribute
                shape_id = cnvpr.get('id')
                if shape_id:
                    # Find the parent shape element
                    shape_elem = cnvpr.getparent()
                    while shape_elem is not None:
                        if shape_elem.tag.endswith(('sp', 'pic', 'grpSp', 'cxnSp')):
                            shape_index[shape_id] = shape_elem
                            break
                        shape_elem = shape_elem.getparent()

                # Also index by name attribute if present
                shape_name = cnvpr.get('name')
                if shape_name and shape_name != '':
                    shape_elem = cnvpr.getparent()
                    while shape_elem is not None:
                        if shape_elem.tag.endswith(('sp', 'pic', 'grpSp', 'cxnSp')):
                            shape_index[shape_name] = shape_elem
                            break
                        shape_elem = shape_elem.getparent()

            self.logger.debug(f"Built shape index with {len(shape_index)} entries")
            return shape_index

        except Exception as e:
            self.logger.error(f"Failed to build shape index: {e}")
            return {}

    def _apply_result_hyperlinks(self, tree: Element, result: MapperResult,
                                shape_index: Dict[str, Element], namespaces: Dict[str, str]) -> None:
        """
        Apply hyperlinks from a single MapperResult to the slide tree.

        Args:
            tree: Slide XML tree (modified in place)
            result: MapperResult containing hyperlinks
            shape_index: Dictionary mapping shape IDs to elements
            namespaces: XML namespace mapping
        """
        try:
            if not result.hyperlinks:
                return

            # Determine target shape for hyperlinks
            target_shape = None
            if result.shape_id:
                target_shape = shape_index.get(result.shape_id)
                if target_shape is None:
                    self.logger.warning(f"Shape with ID '{result.shape_id}' not found in slide")
                    return

            # Apply each hyperlink
            for i, hyperlink in enumerate(result.hyperlinks):
                try:
                    if result.linked_runs and i < len(result.linked_runs):
                        # Text-level hyperlink
                        self._apply_text_hyperlink(tree, target_shape, hyperlink,
                                                 result.linked_runs[i], namespaces)
                    elif target_shape is not None:
                        # Shape-level hyperlink
                        self._apply_shape_hyperlink(target_shape, hyperlink, namespaces)
                    else:
                        self.logger.warning(f"No target found for hyperlink {hyperlink.href}")

                except Exception as e:
                    self.logger.error(f"Failed to apply hyperlink {hyperlink.href}: {e}")

        except Exception as e:
            self.logger.error(f"Failed to apply hyperlinks for result: {e}")

    def _apply_shape_hyperlink(self, shape_elem: Element, hyperlink, namespaces: Dict[str, str]) -> None:
        """
        Apply hyperlink to entire shape element.

        Args:
            shape_elem: Target shape element
            hyperlink: HyperlinkSpec object
            namespaces: XML namespace mapping
        """
        try:
            # Find cNvPr element within the shape
            cnvpr = shape_elem.xpath('.//p:cNvPr', namespaces=namespaces)
            if not cnvpr:
                self.logger.warning("No cNvPr element found in shape for hyperlink attachment")
                return

            cnvpr_elem = cnvpr[0]

            # Get relationship ID from embedder
            rel_id = self.embedder.ensure_hlink_relationship(hyperlink)

            # Create hyperlink click element
            hlink_click = ET.Element(
                "{http://schemas.openxmlformats.org/drawingml/2006/main}hlinkClick"
            )
            hlink_click.set(
                "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id",
                rel_id
            )

            # Add tooltip if present
            if hyperlink.tooltip:
                hlink_click.set("tooltip", hyperlink.tooltip)

            # Add visited state
            if hyperlink.visited:
                hlink_click.set("history", "1")

            # Append to cNvPr
            cnvpr_elem.append(hlink_click)

            self.logger.debug(f"Applied shape hyperlink {hyperlink.href} with {rel_id}")

        except Exception as e:
            self.logger.error(f"Failed to apply shape hyperlink: {e}")

    def _apply_text_hyperlink(self, tree: Element, shape_elem: Element, hyperlink,
                             linked_run: Dict[str, Any], namespaces: Dict[str, str]) -> None:
        """
        Apply hyperlink to specific text run within shape.

        Args:
            tree: Full slide tree
            shape_elem: Target shape element
            hyperlink: HyperlinkSpec object
            linked_run: Text run specification with start, end, hyperlink_index
            namespaces: XML namespace mapping
        """
        try:
            # This is a simplified implementation
            # In practice, would need to split text runs at specified positions
            self.logger.debug(f"Applying text hyperlink {hyperlink.href} to run {linked_run}")

            # For now, apply as shape-level hyperlink
            # Full text run splitting would be implemented here
            self._apply_shape_hyperlink(shape_elem, hyperlink, namespaces)

        except Exception as e:
            self.logger.error(f"Failed to apply text hyperlink: {e}")

    def _validate_slide_xml(self, slide_xml: str, slide_index: Optional[int]) -> bool:
        """Validate slide XML against schema"""
        if not self.schema:
            return True

        try:
            doc = ET.fromstring(slide_xml.encode('utf-8'))
            self.schema.assertValid(doc)
            return True
        except ET.DocumentInvalid as e:
            self._stats['schema_validation_errors'] += 1
            slide_info = f"slide {slide_index}" if slide_index else "slide"
            self.logger.warning(f"Schema validation failed for {slide_info}: {e}")
            return False

    def _map_scene_elements(self, elements: List[IRElement], slide_index: Optional[int]) -> List[MapperResult]:
        """Map all elements in scene with better error context"""
        mapper_results = []

        for i, element in enumerate(elements):
            try:
                # Find appropriate mapper
                mapper = self._find_mapper(element)
                if not mapper:
                    element_info = f"element {i} ({type(element).__name__})"
                    slide_info = f"slide {slide_index}" if slide_index else "scene"
                    self.logger.warning(f"No mapper for {element_info} in {slide_info}")
                    continue

                # Map element
                result = mapper.map(element)
                mapper_results.append(result)

            except Exception as e:
                element_info = f"element {i} ({type(element).__name__})"
                slide_info = f"slide {slide_index}" if slide_index else "scene"
                self.logger.error(f"Failed to map {element_info} in {slide_info}: {e}")
                # Continue with other elements

        return mapper_results

    def _find_mapper(self, element: IRElement) -> Optional[MapperProtocol]:
        """Find appropriate mapper for IR element"""
        element_type = type(element).__name__.lower()

        # Direct type mapping
        if element_type in self.mappers:
            return self.mappers[element_type]

        # Check mapper capabilities
        for mapper in self.mappers.values():
            if mapper.can_map(element):
                return mapper

        return None

    def _record_slide_build(self, element_count: int, processing_time: float) -> None:
        """Record enhanced statistics"""
        self._stats['slides_built'] += 1
        self._stats['total_elements'] += element_count
        self._stats['total_time_ms'] += processing_time

        # Update averages
        if self._stats['slides_built'] > 0:
            self._stats['avg_elements_per_slide'] = (
                self._stats['total_elements'] / self._stats['slides_built']
            )

        # Update cache hit rate
        total_requests = self._cache_hits + self._cache_misses
        if total_requests > 0:
            self._stats['cache_hit_rate'] = self._cache_hits / total_requests

    def get_statistics(self) -> Dict[str, Any]:
        """Get enhanced statistics including cache and validation metrics"""
        return {
            **self._stats,
            'avg_time_per_slide_ms': (
                self._stats['total_time_ms'] / max(self._stats['slides_built'], 1)
            ),
            'cache_hits': self._cache_hits,
            'cache_misses': self._cache_misses,
            'cache_size': len(self._xml_cache),
            'mapper_stats': {
                name: mapper.get_statistics()
                for name, mapper in self.mappers.items()
            },
            'embedder_stats': self.embedder.get_statistics()
        }

    def reset_statistics(self) -> None:
        """Reset all statistics and clear cache"""
        self._stats = {
            'slides_built': 0,
            'total_elements': 0,
            'total_time_ms': 0.0,
            'avg_elements_per_slide': 0.0,
            'xml_parse_errors': 0,
            'schema_validation_errors': 0,
            'cache_hit_rate': 0.0
        }

        # Clear cache
        self._xml_cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0

        # Reset mapper and embedder stats
        for mapper in self.mappers.values():
            mapper.reset_statistics()
        self.embedder.reset_statistics()

    def build_from_elements(self, elements: List[IRElement],
                           metadata: SlideMetadata = None) -> EmbedderResult:
        """Build slide from list of IR elements"""
        # SceneGraph is just a type alias for List[IRElement]
        scene = elements
        return self.build_slide(scene, metadata)

    def add_mapper(self, element_type: str, mapper: MapperProtocol) -> None:
        """Add or replace mapper with validation"""
        validated_mapper = self._validate_mappers({element_type: mapper})[element_type]
        self.mappers[element_type] = validated_mapper

    def get_supported_elements(self) -> List[str]:
        """Get list of supported element types"""
        return list(self.mappers.keys())


def create_enhanced_slide_builder(mappers: Dict[str, Any],
                                 embedder: DrawingMLEmbedder,
                                 policy: Policy,
                                 validate_schema: bool = False,
                                 schema_path: Optional[str] = None) -> EnhancedSlideBuilder:
    """
    Create enhanced SlideBuilder with improved XML handling.

    Args:
        mappers: Dictionary of element type -> mapper
        embedder: DrawingML embedder
        policy: Policy engine
        validate_schema: Enable XML schema validation
        schema_path: Path to OOXML schema file

    Returns:
        Configured EnhancedSlideBuilder
    """
    return EnhancedSlideBuilder(mappers, embedder, policy, validate_schema, schema_path)