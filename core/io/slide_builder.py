#!/usr/bin/env python3
"""
Slide Builder with Enhanced XML Handling

High-level slide construction from IR scenes using the mapper + embedder pipeline.
Features proper XML manipulation, schema validation, and performance optimization.
"""

import time
import logging
import hashlib
from typing import Dict, Any, Optional, List, Protocol, runtime_checkable
from dataclasses import dataclass
from enum import Enum
from lxml import etree as ET
from lxml.etree import Element, QName

from ..ir import SceneGraph, IRElement
from ..map.base import Mapper, MapperResult
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
    """Protocol defining mapper interface for consistent implementations"""

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


class SlideBuilder:
    """
    Enhanced slide builder with proper XML handling and validation.

    Improvements:
    - Proper XML manipulation using lxml instead of string replace
    - Optional schema validation support
    - Consistent mapper interfaces via Protocol
    - Better error context with slide indices
    - Performance optimizations with caching
    """

    def __init__(self, mappers: Dict[str, Any], embedder: DrawingMLEmbedder,
                 policy: Policy, validate_schema: bool = False,
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

    def _validate_mappers(self, mappers: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and adapt mappers to ensure protocol compliance"""
        validated = {}
        for name, mapper in mappers.items():
            # Check if mapper has required methods
            if not hasattr(mapper, 'map'):
                self.logger.warning(f"Mapper '{name}' missing required 'map' method")
                continue

            # Wrap non-protocol mappers if needed
            if not isinstance(mapper, MapperProtocol):
                validated[name] = self._create_mapper_adapter(mapper)
            else:
                validated[name] = mapper
        return validated

    def _create_mapper_adapter(self, mapper: Any) -> Any:
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

        Raises:
            ValueError: If scene is invalid
            RuntimeError: If building fails
        """
        start_time = time.perf_counter()

        try:
            if not scene or not scene.elements:
                raise ValueError("Scene must contain elements")

            # Apply default metadata
            if metadata is None:
                metadata = SlideMetadata(template=SlideTemplate.BLANK)

            # Check cache for identical scenes
            scene_hash = self._compute_scene_hash(scene)
            if scene_hash in self._xml_cache:
                self._cache_hits += 1
                cached_result = self._xml_cache[scene_hash]
                self.logger.debug(f"Cache hit for scene {scene_hash[:8]}")
                return cached_result

            self._cache_misses += 1

            # Map all scene elements with context
            mapper_results = self._map_scene_elements(scene, metadata.slide_index)

            # Embed into slide structure
            result = self.embedder.embed_scene(scene, mapper_results)

            # Apply metadata with proper XML handling
            result.slide_xml = self._apply_slide_metadata_xml(result.slide_xml, metadata)

            # Validate if enabled
            if self.validate_schema:
                self._validate_slide_xml(result.slide_xml, metadata.slide_index)

            # Cache result (limit cache size)
            if len(self._xml_cache) < 100:
                self._xml_cache[scene_hash] = result

            # Record statistics
            processing_time = (time.perf_counter() - start_time) * 1000
            self._record_slide_build(len(scene.elements), processing_time)

            return result

        except Exception as e:
            slide_info = f"slide {metadata.slide_index}" if metadata and metadata.slide_index else "slide"
            self.logger.error(f"Failed to build {slide_info}: {e}")
            raise RuntimeError(f"Slide building failed for {slide_info}: {e}") from e

    def _compute_scene_hash(self, scene: SceneGraph) -> str:
        """Compute hash of scene for caching"""
        content = f"{len(scene.elements)}:{[type(e).__name__ for e in scene.elements]}"
        return hashlib.md5(content.encode()).hexdigest()

    def build_from_elements(self, elements: List[IRElement],
                           metadata: SlideMetadata = None) -> EmbedderResult:
        """
        Build slide from list of IR elements.

        Args:
            elements: List of IR elements
            metadata: Optional slide metadata

        Returns:
            EmbedderResult with complete slide structure
        """
        # Create minimal scene
        scene = SceneGraph(
            elements=elements,
            viewport=None,  # Will use embedder defaults
            background=None
        )

        return self.build_slide(scene, metadata)

    def _map_scene_elements(self, scene: SceneGraph, slide_index: Optional[int] = None) -> List[MapperResult]:
        """Map all elements in scene with better error context"""
        mapper_results = []

        for i, element in enumerate(scene.elements):
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

    def _find_mapper(self, element: IRElement) -> Optional[Mapper]:
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

    def _apply_slide_metadata_xml(self, slide_xml: str, metadata: SlideMetadata) -> str:
        """
        Apply slide metadata using proper XML manipulation.

        This replaces string manipulation with proper lxml operations.
        """
        try:
            # Parse XML properly
            if isinstance(slide_xml, bytes):
                tree = ET.fromstring(slide_xml)
            else:
                tree = ET.fromstring(slide_xml.encode('utf-8'))

            # Validate root element
            if tree.tag != QName(P_URI, 'sld'):
                raise ValueError(f"Invalid slide root element: {tree.tag}")

            # Remove existing metadata elements if present
            for elem_name in ['sldLayoutIdLst', 'sldMasterIdLst', 'notes']:
                existing = tree.find(f'.//p:{elem_name}', NSMAP)
                if existing is not None:
                    tree.remove(existing)

            # Add layout reference
            layout_list = ET.SubElement(tree, QName(P_URI, 'sldLayoutIdLst'))
            layout_id_elem = ET.SubElement(layout_list, QName(P_URI, 'sldLayoutId'))
            layout_id_elem.set('id', str(metadata.layout_id))
            layout_id_elem.set(QName(R_URI, 'id'), 'rId1')

            # Add master reference
            master_list = ET.SubElement(tree, QName(P_URI, 'sldMasterIdLst'))
            master_id_elem = ET.SubElement(master_list, QName(P_URI, 'sldMasterId'))
            master_id_elem.set('id', str(metadata.master_id))
            master_id_elem.set(QName(R_URI, 'id'), 'rId2')

            # Add notes if present
            if metadata.notes:
                notes_elem = ET.SubElement(tree, QName(P_URI, 'notes'))
                notes_elem.text = metadata.notes

            # Return formatted XML
            return ET.tostring(tree, xml_declaration=True,
                             encoding='UTF-8', pretty_print=True).decode('utf-8')

        except ET.XMLSyntaxError as e:
            self._stats['xml_parse_errors'] += 1
            slide_info = f"slide {metadata.slide_index}" if metadata.slide_index else "slide"
            self.logger.warning(f"XML parse error for {slide_info}: {e}")
            return slide_xml  # Return unmodified on parse error
        except Exception as e:
            slide_info = f"slide {metadata.slide_index}" if metadata.slide_index else "slide"
            self.logger.warning(f"Failed to apply metadata to {slide_info}: {e}")
            return slide_xml

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
        mapper_stats = {}
        for name, mapper in self.mappers.items():
            if hasattr(mapper, 'get_statistics'):
                mapper_stats[name] = mapper.get_statistics()

        embedder_stats = {}
        if hasattr(self.embedder, 'get_statistics'):
            embedder_stats = self.embedder.get_statistics()

        return {
            **self._stats,
            'avg_time_per_slide_ms': (
                self._stats['total_time_ms'] / max(self._stats['slides_built'], 1)
            ),
            'cache_hits': self._cache_hits,
            'cache_misses': self._cache_misses,
            'cache_size': len(self._xml_cache),
            'mapper_stats': mapper_stats,
            'embedder_stats': embedder_stats
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
            if hasattr(mapper, 'reset_statistics'):
                mapper.reset_statistics()
        if hasattr(self.embedder, 'reset_statistics'):
            self.embedder.reset_statistics()

    def add_mapper(self, element_type: str, mapper: Mapper) -> None:
        """Add or replace mapper for element type"""
        self.mappers[element_type] = mapper

    def get_supported_elements(self) -> List[str]:
        """Get list of supported element types"""
        return list(self.mappers.keys())


def create_slide_builder(mappers: Dict[str, Any],
                        embedder: DrawingMLEmbedder,
                        policy: Policy,
                        validate_schema: bool = False,
                        schema_path: Optional[str] = None) -> SlideBuilder:
    """
    Create SlideBuilder with enhanced XML handling.

    Args:
        mappers: Dictionary of element type -> mapper
        embedder: DrawingML embedder
        policy: Policy engine
        validate_schema: Enable XML schema validation
        schema_path: Path to OOXML schema file

    Returns:
        Configured SlideBuilder with enhanced features
    """
    return SlideBuilder(mappers, embedder, policy, validate_schema, schema_path)