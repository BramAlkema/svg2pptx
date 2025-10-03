#!/usr/bin/env python3
"""
Unit Tests for RelationshipManager

Tests the OPC relationship management functionality including:
- rId allocation and deduplication
- Image relationship creation
- Slide layout relationships
- Custom relationship types
- XML generation
"""

import pytest
from lxml import etree as ET

from core.io.relationship_manager import (
    RelationshipManager,
    Relationship,
    REL_IMAGE,
    REL_SLIDE_LAYOUT,
)

# Define hyperlink constant for tests
REL_HYPERLINK = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink"


class TestRelationshipManagerInitialization:
    """Test RelationshipManager initialization"""

    def test_init_default(self):
        """Test initialization with default start_id"""
        manager = RelationshipManager()
        assert manager._counter == 1
        assert len(manager._relationships) == 0
        assert len(manager._by_target) == 0

    def test_init_custom_start_id(self):
        """Test initialization with custom start_id"""
        manager = RelationshipManager(start_id=5)
        assert manager._counter == 5

    def test_init_negative_start_id(self):
        """Test that negative start_id still works"""
        manager = RelationshipManager(start_id=-1)
        assert manager._counter == -1


class TestRelationshipIDAllocation:
    """Test rId allocation"""

    def test_next_id_sequential(self):
        """Test that next_id() returns sequential IDs"""
        manager = RelationshipManager()
        assert manager.next_id() == "rId1"
        assert manager.next_id() == "rId2"
        assert manager.next_id() == "rId3"

    def test_next_id_custom_start(self):
        """Test next_id() with custom start"""
        manager = RelationshipManager(start_id=10)
        assert manager.next_id() == "rId10"
        assert manager.next_id() == "rId11"

    def test_counter_increments(self):
        """Test that _counter increments correctly"""
        manager = RelationshipManager()
        initial = manager._counter
        manager.next_id()
        assert manager._counter == initial + 1


class TestImageRelationships:
    """Test image relationship creation"""

    def test_add_image_basic(self):
        """Test adding a basic image relationship"""
        manager = RelationshipManager()
        rid = manager.add_image("../media/image1.png")

        assert rid == "rId1"
        assert len(manager._relationships) == 1

        rel = manager._relationships[0]
        assert rel.rid == "rId1"
        assert rel.rel_type == REL_IMAGE
        assert rel.target == "../media/image1.png"

    def test_add_image_deduplication(self):
        """Test that same target returns same rId"""
        manager = RelationshipManager()

        rid1 = manager.add_image("../media/image1.png")
        rid2 = manager.add_image("../media/image1.png")

        assert rid1 == rid2
        assert len(manager._relationships) == 1
        assert "../media/image1.png" in manager._by_target

    def test_add_multiple_unique_images(self):
        """Test adding multiple unique images"""
        manager = RelationshipManager()

        rid1 = manager.add_image("../media/image1.png")
        rid2 = manager.add_image("../media/image2.jpg")
        rid3 = manager.add_image("../media/image3.gif")

        assert rid1 == "rId1"
        assert rid2 == "rId2"
        assert rid3 == "rId3"
        assert len(manager._relationships) == 3

    def test_add_image_mixed_duplicates(self):
        """Test adding mix of unique and duplicate images"""
        manager = RelationshipManager()

        rid1 = manager.add_image("../media/image1.png")
        rid2 = manager.add_image("../media/image2.png")
        rid3 = manager.add_image("../media/image1.png")  # Duplicate
        rid4 = manager.add_image("../media/image3.png")
        rid5 = manager.add_image("../media/image2.png")  # Duplicate

        assert rid1 == "rId1"
        assert rid2 == "rId2"
        assert rid3 == "rId1"  # Same as first
        assert rid4 == "rId3"
        assert rid5 == "rId2"  # Same as second
        assert len(manager._relationships) == 3  # Only 3 unique


class TestSlideLayoutRelationships:
    """Test slide layout relationship creation"""

    def test_add_slide_layout_default(self):
        """Test adding slide layout with default target"""
        manager = RelationshipManager()
        rid = manager.add_slide_layout()

        assert rid == "rId1"
        assert len(manager._relationships) == 1

        rel = manager._relationships[0]
        assert rel.rid == "rId1"
        assert rel.rel_type == REL_SLIDE_LAYOUT
        assert rel.target == "../slideLayouts/slideLayout1.xml"

    def test_add_slide_layout_custom_target(self):
        """Test adding slide layout with custom target"""
        manager = RelationshipManager()
        rid = manager.add_slide_layout("../slideLayouts/custom.xml")

        rel = manager._relationships[0]
        assert rel.target == "../slideLayouts/custom.xml"

    def test_add_slide_layout_no_deduplication(self):
        """Test slide layout does NOT deduplicate (by design)"""
        manager = RelationshipManager()

        rid1 = manager.add_slide_layout()
        rid2 = manager.add_slide_layout()  # Same target

        # Note: add_slide_layout() does NOT deduplicate
        assert rid1 != rid2
        assert rid1 == "rId1"
        assert rid2 == "rId2"
        assert len(manager._relationships) == 2


class TestCustomRelationships:
    """Test custom relationship types"""

    def test_add_custom_basic(self):
        """Test adding a custom relationship"""
        manager = RelationshipManager()
        rid = manager.add_custom(
            rel_type=REL_HYPERLINK,
            target="https://example.com",
            external=True
        )

        assert rid == "rId1"
        assert len(manager._relationships) == 1

        rel = manager._relationships[0]
        assert rel.rid == "rId1"
        assert rel.rel_type == REL_HYPERLINK
        assert rel.target == "https://example.com"
        assert rel.external == True

    def test_add_custom_without_external(self):
        """Test custom relationship without external flag"""
        manager = RelationshipManager()
        rid = manager.add_custom(
            rel_type="http://custom/type",
            target="custom.xml"
        )

        rel = manager._relationships[0]
        assert rel.external == False

    def test_add_custom_deduplication(self):
        """Test custom relationship deduplication"""
        manager = RelationshipManager()

        rid1 = manager.add_custom(REL_HYPERLINK, "https://example.com")
        rid2 = manager.add_custom(REL_HYPERLINK, "https://example.com")

        assert rid1 == rid2
        assert len(manager._relationships) == 1


class TestRelationshipProperties:
    """Test relationship property access"""

    def test_relationships_property(self):
        """Test relationships property returns list"""
        manager = RelationshipManager()
        manager.add_image("../media/image1.png")
        manager.add_slide_layout()

        rels = manager.relationships
        assert isinstance(rels, list)
        assert len(rels) == 2

    def test_get_by_target(self):
        """Test getting relationship by target"""
        manager = RelationshipManager()
        manager.add_image("../media/image1.png")
        manager.add_image("../media/image2.png")

        assert "../media/image1.png" in manager._by_target
        assert manager._by_target["../media/image1.png"] == "rId1"
        assert manager._by_target["../media/image2.png"] == "rId2"


class TestXMLGeneration:
    """Test XML generation"""

    def test_to_xml_empty(self):
        """Test XML generation with no relationships"""
        manager = RelationshipManager()
        root = manager.to_xml()

        assert root.tag.endswith("}Relationships")
        assert len(root) == 0  # No children

    def test_to_xml_single_relationship(self):
        """Test XML with single relationship"""
        manager = RelationshipManager()
        manager.add_image("../media/image1.png")

        root = manager.to_xml()
        assert len(root) == 1

        rel_elem = root[0]
        assert rel_elem.get("Id") == "rId1"
        assert rel_elem.get("Type") == REL_IMAGE
        assert rel_elem.get("Target") == "../media/image1.png"
        assert rel_elem.get("TargetMode") is None

    def test_to_xml_multiple_relationships(self):
        """Test XML with multiple relationships"""
        manager = RelationshipManager()
        manager.add_image("../media/image1.png")
        manager.add_slide_layout()
        manager.add_custom(REL_HYPERLINK, "https://example.com", "External")

        root = manager.to_xml()
        assert len(root) == 3

        # Check each relationship
        ids = [elem.get("Id") for elem in root]
        assert "rId1" in ids
        assert "rId2" in ids
        assert "rId3" in ids

    def test_to_xml_with_external(self):
        """Test XML includes TargetMode when external=True"""
        manager = RelationshipManager()
        manager.add_custom(REL_HYPERLINK, "https://example.com", external=True)

        root = manager.to_xml()
        rel_elem = root[0]
        assert rel_elem.get("TargetMode") == "External"

    def test_to_xml_bytes(self):
        """Test to_xml_bytes() returns bytes"""
        manager = RelationshipManager()
        manager.add_image("../media/image1.png")

        xml_bytes = manager.to_xml_bytes()
        assert isinstance(xml_bytes, bytes)
        assert b"<?xml version=" in xml_bytes
        assert b"Relationships" in xml_bytes
        assert b"rId1" in xml_bytes

    def test_to_xml_bytes_well_formed(self):
        """Test to_xml_bytes() produces well-formed XML"""
        manager = RelationshipManager()
        manager.add_image("../media/image1.png")
        manager.add_slide_layout()

        xml_bytes = manager.to_xml_bytes()

        # Should be parseable
        parsed = ET.fromstring(xml_bytes)
        assert parsed is not None
        assert len(parsed) == 2


class TestRelationshipManagerIntegration:
    """Integration tests for RelationshipManager"""

    def test_realistic_slide_scenario(self):
        """Test realistic scenario with images and layout"""
        manager = RelationshipManager(start_id=1)

        # Add slide layout (always first)
        layout_rid = manager.add_slide_layout()
        assert layout_rid == "rId1"

        # Add images
        img1_rid = manager.add_image("../media/image1.png")
        img2_rid = manager.add_image("../media/image2.jpg")
        img3_rid = manager.add_image("../media/image1.png")  # Duplicate

        assert img1_rid == "rId2"
        assert img2_rid == "rId3"
        assert img3_rid == "rId2"  # Deduplicated

        # Total should be 3 unique relationships
        assert len(manager.relationships) == 3

        # Generate XML
        xml_bytes = manager.to_xml_bytes()
        parsed = ET.fromstring(xml_bytes)
        assert len(parsed) == 3

    def test_mixed_relationship_types(self):
        """Test handling multiple relationship types"""
        manager = RelationshipManager()

        # Mix of different types
        manager.add_slide_layout()
        manager.add_image("../media/logo.png")
        manager.add_custom(REL_HYPERLINK, "https://example.com", external=True)
        manager.add_image("../media/chart.png")
        manager.add_custom("http://custom/type", "custom.xml", external=False)

        assert len(manager.relationships) == 5

        xml = manager.to_xml()
        types = [elem.get("Type") for elem in xml]
        assert REL_SLIDE_LAYOUT in types
        assert REL_IMAGE in types
        assert REL_HYPERLINK in types
        assert "http://custom/type" in types


class TestEdgeCases:
    """Test edge cases and error conditions"""

    def test_empty_target(self):
        """Test handling empty target string"""
        manager = RelationshipManager()
        rid = manager.add_image("")

        assert rid == "rId1"
        assert manager._relationships[0].target == ""

    def test_special_characters_in_target(self):
        """Test handling special characters in target"""
        manager = RelationshipManager()
        rid = manager.add_image("../media/image with spaces.png")

        assert manager._relationships[0].target == "../media/image with spaces.png"

    def test_unicode_in_target(self):
        """Test handling unicode in target"""
        manager = RelationshipManager()
        rid = manager.add_image("../media/图片.png")

        assert rid is not None
        assert manager._relationships[0].target == "../media/图片.png"

    def test_very_long_target(self):
        """Test handling very long target path"""
        manager = RelationshipManager()
        long_target = "../media/" + "a" * 1000 + ".png"
        rid = manager.add_image(long_target)

        assert rid is not None
        assert manager._relationships[0].target == long_target

    def test_many_relationships(self):
        """Test handling many relationships"""
        manager = RelationshipManager()

        # Add 100 unique images
        for i in range(100):
            manager.add_image(f"../media/image{i}.png")

        assert len(manager.relationships) == 100
        assert manager._counter == 101  # Next would be 101

    def test_xml_namespace_preservation(self):
        """Test that XML namespace is correct"""
        manager = RelationshipManager()
        manager.add_image("../media/image1.png")

        root = manager.to_xml()
        assert root.tag == "{http://schemas.openxmlformats.org/package/2006/relationships}Relationships"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
