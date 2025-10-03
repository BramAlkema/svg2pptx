#!/usr/bin/env python3
"""
Relationship Manager for PPTX OPC Relationships

Manages relationship IDs (rId) and relationship XML generation
following ECMA-376 Open Packaging Conventions.
"""

from dataclasses import dataclass
from typing import List, Dict
from lxml import etree as ET
from lxml.etree import Element, QName

REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
REL_IMAGE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"
REL_SLIDE_LAYOUT = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout"


@dataclass
class Relationship:
    """Represents an OPC relationship"""
    rid: str                    # e.g., "rId1"
    rel_type: str               # Relationship type URI
    target: str                 # Target path (relative to source)
    external: bool = False      # TargetMode="External"


class RelationshipManager:
    """Manages relationships for a single part (e.g., slide)"""

    def __init__(self, start_id: int = 1):
        """
        Initialize relationship manager.

        Args:
            start_id: Starting ID number for rId allocation
        """
        self._counter = start_id
        self._relationships: List[Relationship] = []
        self._by_target: Dict[str, str] = {}  # target → rId (for deduplication)

    def next_id(self) -> str:
        """Allocate next relationship ID"""
        rid = f"rId{self._counter}"
        self._counter += 1
        return rid

    def add_image(self, target_path: str) -> str:
        """
        Add image relationship.

        Args:
            target_path: Relative path to image (e.g., "../media/image1.png")

        Returns:
            rId for this relationship
        """
        # Check if already added (deduplication)
        if target_path in self._by_target:
            return self._by_target[target_path]

        rid = self.next_id()
        rel = Relationship(
            rid=rid,
            rel_type=REL_IMAGE,
            target=target_path,
            external=False
        )
        self._relationships.append(rel)
        self._by_target[target_path] = rid
        return rid

    def add_slide_layout(self, target_path: str = "../slideLayouts/slideLayout1.xml") -> str:
        """Add slide layout relationship"""
        rid = self.next_id()
        rel = Relationship(
            rid=rid,
            rel_type=REL_SLIDE_LAYOUT,
            target=target_path,
            external=False
        )
        self._relationships.append(rel)
        return rid

    def add_custom(self, rel_type: str, target: str, external: bool = False) -> str:
        """
        Add custom relationship.

        Args:
            rel_type: Relationship type URI
            target: Target path or URL
            external: True for external references (http://, etc.)

        Returns:
            rId for this relationship
        """
        # Check deduplication for non-external
        if not external and target in self._by_target:
            return self._by_target[target]

        rid = self.next_id()
        rel = Relationship(
            rid=rid,
            rel_type=rel_type,
            target=target,
            external=external
        )
        self._relationships.append(rel)

        if not external:
            self._by_target[target] = rid

        return rid

    @property
    def relationships(self) -> List[Relationship]:
        """Get all relationships"""
        return self._relationships

    def to_xml(self) -> Element:
        """Generate <Relationships> XML element"""
        root = Element(QName(REL_NS, "Relationships"), nsmap={None: REL_NS})

        for rel in self._relationships:
            rel_elem = ET.SubElement(root, QName(REL_NS, "Relationship"))
            rel_elem.set("Id", rel.rid)
            rel_elem.set("Type", rel.rel_type)
            rel_elem.set("Target", rel.target)
            if rel.external:
                rel_elem.set("TargetMode", "External")

        return root

    def to_xml_bytes(self) -> bytes:
        """Generate XML bytes with declaration"""
        root = self.to_xml()
        return ET.tostring(root, xml_declaration=True, encoding="UTF-8", pretty_print=True)
