#!/usr/bin/env python3
"""
Minimal converter registry stubs for integration tests.

These lightweight implementations provide enough behavior for the SVG test
library to integrate with the modern path system without relying on the
retired monolithic converter stack. They intentionally keep the surface area
small while mimicking the public API that downstream code expects.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Optional

from ...paths.coordinate_system import CoordinateSystem
from ...services.conversion_services import ConversionServices


def _local_tag(element) -> str:
    """Return the localname for an SVG element taking namespaces into account."""
    tag = getattr(element, 'tag', '')
    return tag.split('}')[-1] if '}' in tag else tag


@dataclass
class ConversionContext:
    """Minimal conversion context used by the integration tests."""

    svg_root: object
    coordinate_system: CoordinateSystem | None = None
    services: ConversionServices | None = None
    metadata: dict[str, object] = field(default_factory=dict)

    def with_coordinate_system(self, coord_system: CoordinateSystem) -> 'ConversionContext':
        """Fluent helper to attach a coordinate system."""
        self.coordinate_system = coord_system
        return self


class SimpleShapeConverter:
    """Very small converter that handles a single SVG tag."""

    def __init__(self, tag: str):
        self.tag = tag

    def can_convert(self, element) -> bool:
        return _local_tag(element) == self.tag

    def convert(self, element, context: ConversionContext) -> str:
        # Return a tiny stub DrawingML fragment to satisfy integration tests.
        return f"<converted tag='{self.tag}'/>"


class ConverterRegistry:
    """Collection of converters with helper methods matching the historical API."""

    def __init__(self, converters: Iterable[SimpleShapeConverter]):
        self.converters: list[SimpleShapeConverter] = list(converters)

    def get_converter(self, element) -> Optional[SimpleShapeConverter]:
        for converter in self.converters:
            if converter.can_convert(element):
                return converter
        return None

    def convert_element(self, element, context: ConversionContext) -> Optional[str]:
        converter = self.get_converter(element)
        if converter is None:
            return None
        return converter.convert(element, context)


class ConverterRegistryFactory:
    """
    Factory for creating converter registries.

    The historic converter stack exposed multiple factory helpers. For the SVG
    library integration we only need a default registry that can handle basic
    geometric primitives (rect, circle, ellipse, path).
    """

    @classmethod
    def get_registry(cls, services: ConversionServices | None = None) -> ConverterRegistry:
        """Return a registry populated with simple shape converters."""
        converters: List[SimpleShapeConverter] = [
            SimpleShapeConverter('rect'),
            SimpleShapeConverter('circle'),
            SimpleShapeConverter('ellipse'),
            SimpleShapeConverter('path'),
        ]
        return ConverterRegistry(converters)
