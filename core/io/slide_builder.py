#!/usr/bin/env python3
"""
Slide Builder

High-level slide construction from IR scenes using the mapper + embedder pipeline.
"""

import time
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

from ..ir import SceneGraph, IRElement
from ..map.base import Mapper, MapperResult
from ..policy import Policy
from .embedder import DrawingMLEmbedder, EmbedderResult

logger = logging.getLogger(__name__)


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


class SlideBuilder:
    """
    High-level slide construction from IR scenes.

    Orchestrates the mapper + embedder pipeline to convert IR scenes
    into complete PowerPoint slides with proper structure and relationships.
    """

    def __init__(self, mappers: Dict[str, Mapper], embedder: DrawingMLEmbedder,
                 policy: Policy):
        """
        Initialize slide builder.

        Args:
            mappers: Dictionary of element type -> mapper
            embedder: DrawingML embedder for final slide assembly
            policy: Policy engine for mapping decisions
        """
        self.mappers = mappers
        self.embedder = embedder
        self.policy = policy
        self.logger = logging.getLogger(__name__)

        # Statistics
        self._stats = {
            'slides_built': 0,
            'total_elements': 0,
            'total_time_ms': 0.0,
            'avg_elements_per_slide': 0.0
        }

    def build_slide(self, scene: SceneGraph, metadata: SlideMetadata = None) -> EmbedderResult:
        """
        Build complete slide from IR scene.

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

            # Map all scene elements
            mapper_results = self._map_scene_elements(scene)

            # Embed into slide structure
            result = self.embedder.embed_scene(scene, mapper_results)

            # Add slide metadata
            result.slide_xml = self._apply_slide_metadata(result.slide_xml, metadata)

            # Record statistics
            processing_time = (time.perf_counter() - start_time) * 1000
            self._record_slide_build(len(scene.elements), processing_time)

            return result

        except Exception as e:
            self.logger.error(f"Failed to build slide: {e}")
            raise RuntimeError(f"Slide building failed: {e}") from e

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

    def _map_scene_elements(self, scene: SceneGraph) -> List[MapperResult]:
        """Map all elements in scene using appropriate mappers"""
        mapper_results = []

        for element in scene.elements:
            try:
                # Find appropriate mapper
                mapper = self._find_mapper(element)
                if not mapper:
                    self.logger.warning(f"No mapper found for element type: {type(element)}")
                    continue

                # Map element
                result = mapper.map(element)
                mapper_results.append(result)

            except Exception as e:
                self.logger.error(f"Failed to map element {type(element)}: {e}")
                # Continue with other elements rather than failing entire slide

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

    def _apply_slide_metadata(self, slide_xml: str, metadata: SlideMetadata) -> str:
        """Apply slide metadata to XML"""
        try:
            # Add layout and master references
            layout_ref = f'<p:sldLayoutId id="{metadata.layout_id}" r:id="rId1"/>'
            master_ref = f'<p:sldMasterId id="{metadata.master_id}" r:id="rId2"/>'

            # Insert references before closing sld tag
            slide_xml = slide_xml.replace(
                '</p:sld>',
                f'    <p:sldLayoutIdLst>{layout_ref}</p:sldLayoutIdLst>\n'
                f'    <p:sldMasterIdLst>{master_ref}</p:sldMasterIdLst>\n'
                '</p:sld>'
            )

            # Add notes if present
            if metadata.notes:
                notes_xml = f'<p:notes>{metadata.notes}</p:notes>'
                slide_xml = slide_xml.replace(
                    '</p:sld>',
                    f'    {notes_xml}\n</p:sld>'
                )

            return slide_xml

        except Exception as e:
            self.logger.warning(f"Failed to apply slide metadata: {e}")
            return slide_xml

    def _record_slide_build(self, element_count: int, processing_time: float) -> None:
        """Record slide building statistics"""
        self._stats['slides_built'] += 1
        self._stats['total_elements'] += element_count
        self._stats['total_time_ms'] += processing_time

        # Update average
        if self._stats['slides_built'] > 0:
            self._stats['avg_elements_per_slide'] = (
                self._stats['total_elements'] / self._stats['slides_built']
            )

    def get_statistics(self) -> Dict[str, Any]:
        """Get slide building statistics"""
        return {
            **self._stats,
            'avg_time_per_slide_ms': (
                self._stats['total_time_ms'] / max(self._stats['slides_built'], 1)
            ),
            'mapper_stats': {
                name: mapper.get_statistics()
                for name, mapper in self.mappers.items()
            },
            'embedder_stats': self.embedder.get_statistics()
        }

    def reset_statistics(self) -> None:
        """Reset slide building statistics"""
        self._stats = {
            'slides_built': 0,
            'total_elements': 0,
            'total_time_ms': 0.0,
            'avg_elements_per_slide': 0.0
        }

        # Reset mapper and embedder stats
        for mapper in self.mappers.values():
            mapper.reset_statistics()
        self.embedder.reset_statistics()

    def add_mapper(self, element_type: str, mapper: Mapper) -> None:
        """Add or replace mapper for element type"""
        self.mappers[element_type] = mapper

    def get_supported_elements(self) -> List[str]:
        """Get list of supported element types"""
        return list(self.mappers.keys())


def create_slide_builder(mappers: Dict[str, Mapper],
                        embedder: DrawingMLEmbedder,
                        policy: Policy) -> SlideBuilder:
    """
    Create SlideBuilder with mappers and embedder.

    Args:
        mappers: Dictionary of element type -> mapper
        embedder: DrawingML embedder
        policy: Policy engine

    Returns:
        Configured SlideBuilder
    """
    return SlideBuilder(mappers, embedder, policy)