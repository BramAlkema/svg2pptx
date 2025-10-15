"""Convenience helpers wrapping the shared EnhancedXMLBuilder instance."""

from __future__ import annotations

from typing import Dict, List

from lxml.etree import Element

from .builder import EnhancedXMLBuilder, enhanced_xml_builder, get_enhanced_xml_builder
from .fluent import FluentShapeBuilder

__all__ = [
    "EnhancedXMLBuilder",
    "FluentShapeBuilder",
    "create_animation",
    "create_content_types",
    "create_presentation",
    "create_relationships",
    "create_shape",
    "create_slide",
    "enhanced_xml_builder",
    "get_enhanced_xml_builder",
    "xml_builder",
]


def create_presentation(width_emu: int, height_emu: int, **kwargs) -> Element:
    """Create presentation element with the shared builder."""
    return enhanced_xml_builder.create_presentation_element(width_emu, height_emu, **kwargs)


def create_slide(layout_id: int = 1) -> Element:
    """Create slide element with the shared builder."""
    return enhanced_xml_builder.create_slide_element(layout_id)


def create_shape(shape_id: int, name: str) -> FluentShapeBuilder:
    """Construct a fluent shape builder bound to the shared builder."""
    return FluentShapeBuilder(get_enhanced_xml_builder(), shape_id, name)


def create_content_types(**kwargs) -> Element:
    """Create [Content_Types].xml element with the shared builder."""
    return enhanced_xml_builder.create_content_types_element(**kwargs)


def create_relationships(relationships: List[Dict[str, str]]) -> Element:
    """Create relationships element with the shared builder."""
    return enhanced_xml_builder.create_relationships_element(relationships)


def create_animation(
        effect_type: str,
        target_shape_id: int,
        *,
        duration: float = 1.0,
        delay: float = 0.0,
) -> Element:
    """Create an animation element with the shared builder."""
    return enhanced_xml_builder.create_animation_element(
        effect_type,
        target_shape_id,
        duration=duration,
        delay=delay,
    )


# Backwards-compatible alias historically exposed by builder.py
xml_builder = enhanced_xml_builder
