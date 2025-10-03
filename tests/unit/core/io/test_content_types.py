#!/usr/bin/env python3
"""
Unit Tests for ContentTypesManager

Tests the [Content_Types].xml management functionality including:
- Initialization and skeleton creation
- Default type registration
- Override type registration
- Image type auto-registration
- Presentation type registration
- XML generation and serialization
"""

import pytest
from lxml import etree as ET

from core.io.content_types import ContentTypesManager, CT_NS


class TestContentTypesManagerInitialization:
    """Test ContentTypesManager initialization"""

    def test_init_default(self):
        """Test initialization with default skeleton"""
        manager = ContentTypesManager()

        assert manager.root is not None
        assert manager.root.tag == f"{{{CT_NS}}}Types"

        # Should have default types (xml, rels)
        defaults = manager.root.findall(f"{{{CT_NS}}}Default")
        assert len(defaults) == 2

        extensions = [d.get("Extension") for d in defaults]
        assert "xml" in extensions
        assert "rels" in extensions

    def test_init_with_base_xml(self):
        """Test initialization with existing XML"""
        existing_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="png" ContentType="image/png"/>
</Types>"""

        manager = ContentTypesManager(base_xml=existing_xml)

        defaults = manager.root.findall(f"{{{CT_NS}}}Default")
        assert len(defaults) == 1
        assert defaults[0].get("Extension") == "png"

    def test_skeleton_structure(self):
        """Test skeleton XML structure is correct"""
        manager = ContentTypesManager()

        # Check namespace
        assert manager.root.nsmap[None] == CT_NS

        # Check tag
        assert manager.root.tag.endswith("}Types")


class TestDefaultTypeRegistration:
    """Test Default type registration"""

    def test_add_default_basic(self):
        """Test adding a basic default type"""
        manager = ContentTypesManager()
        manager.add_default("png", "image/png")

        defaults = manager.root.findall(f"{{{CT_NS}}}Default")
        png_defaults = [d for d in defaults if d.get("Extension") == "png"]

        assert len(png_defaults) == 1
        assert png_defaults[0].get("ContentType") == "image/png"

    def test_add_default_deduplication(self):
        """Test that duplicate extensions are deduplicated"""
        manager = ContentTypesManager()

        manager.add_default("png", "image/png")
        manager.add_default("png", "image/png")  # Duplicate

        defaults = manager.root.findall(f"{{{CT_NS}}}Default")
        png_defaults = [d for d in defaults if d.get("Extension") == "png"]

        assert len(png_defaults) == 1  # Only one entry

    def test_add_multiple_defaults(self):
        """Test adding multiple default types"""
        manager = ContentTypesManager()

        manager.add_default("png", "image/png")
        manager.add_default("jpg", "image/jpeg")
        manager.add_default("gif", "image/gif")

        defaults = manager.root.findall(f"{{{CT_NS}}}Default")
        extensions = [d.get("Extension") for d in defaults]

        assert "png" in extensions
        assert "jpg" in extensions
        assert "gif" in extensions


class TestOverrideTypeRegistration:
    """Test Override type registration"""

    def test_add_override_basic(self):
        """Test adding a basic override"""
        manager = ContentTypesManager()
        manager.add_override(
            "/ppt/slides/slide1.xml",
            "application/vnd.openxmlformats-officedocument.presentationml.slide+xml"
        )

        overrides = manager.root.findall(f"{{{CT_NS}}}Override")
        assert len(overrides) == 1

        override = overrides[0]
        assert override.get("PartName") == "/ppt/slides/slide1.xml"
        assert "slide+xml" in override.get("ContentType")

    def test_add_override_deduplication(self):
        """Test that duplicate part names are deduplicated"""
        manager = ContentTypesManager()

        manager.add_override("/ppt/slides/slide1.xml", "type1")
        manager.add_override("/ppt/slides/slide1.xml", "type2")  # Duplicate

        overrides = manager.root.findall(f"{{{CT_NS}}}Override")
        slide_overrides = [o for o in overrides if o.get("PartName") == "/ppt/slides/slide1.xml"]

        assert len(slide_overrides) == 1

    def test_add_multiple_overrides(self):
        """Test adding multiple overrides"""
        manager = ContentTypesManager()

        manager.add_override("/ppt/slides/slide1.xml", "type1")
        manager.add_override("/ppt/slides/slide2.xml", "type2")
        manager.add_override("/ppt/presentation.xml", "type3")

        overrides = manager.root.findall(f"{{{CT_NS}}}Override")
        part_names = [o.get("PartName") for o in overrides]

        assert "/ppt/slides/slide1.xml" in part_names
        assert "/ppt/slides/slide2.xml" in part_names
        assert "/ppt/presentation.xml" in part_names


class TestImageTypeRegistration:
    """Test image type auto-registration"""

    def test_ensure_image_type_png(self):
        """Test PNG image type registration"""
        manager = ContentTypesManager()
        manager.ensure_image_type("png")

        defaults = manager.root.findall(f"{{{CT_NS}}}Default")
        png_defaults = [d for d in defaults if d.get("Extension") == "png"]

        assert len(png_defaults) == 1
        assert png_defaults[0].get("ContentType") == "image/png"

    def test_ensure_image_type_jpg(self):
        """Test JPG/JPEG image type registration"""
        manager = ContentTypesManager()

        manager.ensure_image_type("jpg")
        manager.ensure_image_type("jpeg")

        defaults = manager.root.findall(f"{{{CT_NS}}}Default")

        jpg_defaults = [d for d in defaults if d.get("Extension") == "jpg"]
        jpeg_defaults = [d for d in defaults if d.get("Extension") == "jpeg"]

        assert len(jpg_defaults) == 1
        assert len(jpeg_defaults) == 1
        assert jpg_defaults[0].get("ContentType") == "image/jpeg"
        assert jpeg_defaults[0].get("ContentType") == "image/jpeg"

    def test_ensure_image_type_case_insensitive(self):
        """Test case-insensitive image type lookup"""
        manager = ContentTypesManager()

        manager.ensure_image_type("PNG")
        manager.ensure_image_type("JpG")

        defaults = manager.root.findall(f"{{{CT_NS}}}Default")
        extensions = [d.get("Extension") for d in defaults]

        assert "PNG" in extensions
        assert "JpG" in extensions

    def test_ensure_image_type_all_formats(self):
        """Test all supported image formats"""
        manager = ContentTypesManager()

        formats = ["png", "jpg", "jpeg", "gif", "bmp", "tif", "tiff", "webp", "svg"]
        for fmt in formats:
            manager.ensure_image_type(fmt)

        defaults = manager.root.findall(f"{{{CT_NS}}}Default")
        extensions = [d.get("Extension") for d in defaults]

        for fmt in formats:
            assert fmt in extensions

    def test_ensure_image_type_unknown_fallback(self):
        """Test unknown image type falls back to image/png"""
        manager = ContentTypesManager()
        manager.ensure_image_type("unknown")

        defaults = manager.root.findall(f"{{{CT_NS}}}Default")
        unknown_defaults = [d for d in defaults if d.get("Extension") == "unknown"]

        assert len(unknown_defaults) == 1
        assert unknown_defaults[0].get("ContentType") == "image/png"


class TestPresentationTypeRegistration:
    """Test presentation type registration"""

    def test_ensure_presentation_types(self):
        """Test all presentation types are registered"""
        manager = ContentTypesManager()
        manager.ensure_presentation_types()

        overrides = manager.root.findall(f"{{{CT_NS}}}Override")
        part_names = [o.get("PartName") for o in overrides]

        assert "/ppt/presentation.xml" in part_names
        assert "/ppt/presProps.xml" in part_names
        assert "/ppt/tableStyles.xml" in part_names
        assert "/ppt/viewProps.xml" in part_names

    def test_add_slide(self):
        """Test slide registration"""
        manager = ContentTypesManager()
        manager.add_slide(1)

        overrides = manager.root.findall(f"{{{CT_NS}}}Override")
        slide_overrides = [o for o in overrides if "/slides/" in o.get("PartName")]

        assert len(slide_overrides) == 1
        assert slide_overrides[0].get("PartName") == "/ppt/slides/slide1.xml"
        assert "slide+xml" in slide_overrides[0].get("ContentType")

    def test_add_multiple_slides(self):
        """Test adding multiple slides"""
        manager = ContentTypesManager()

        for i in range(1, 6):
            manager.add_slide(i)

        overrides = manager.root.findall(f"{{{CT_NS}}}Override")
        slide_overrides = [o for o in overrides if "/slides/" in o.get("PartName")]

        assert len(slide_overrides) == 5

    def test_add_slide_layout(self):
        """Test slide layout registration"""
        manager = ContentTypesManager()
        manager.add_slide_layout(1)

        overrides = manager.root.findall(f"{{{CT_NS}}}Override")
        layout_overrides = [o for o in overrides if "/slideLayouts/" in o.get("PartName")]

        assert len(layout_overrides) == 1
        assert layout_overrides[0].get("PartName") == "/ppt/slideLayouts/slideLayout1.xml"

    def test_add_slide_master(self):
        """Test slide master registration"""
        manager = ContentTypesManager()
        manager.add_slide_master(1)

        overrides = manager.root.findall(f"{{{CT_NS}}}Override")
        master_overrides = [o for o in overrides if "/slideMasters/" in o.get("PartName")]

        assert len(master_overrides) == 1
        assert master_overrides[0].get("PartName") == "/ppt/slideMasters/slideMaster1.xml"


class TestXMLGeneration:
    """Test XML generation and serialization"""

    def test_to_xml(self):
        """Test to_xml() returns Element"""
        manager = ContentTypesManager()
        manager.add_default("png", "image/png")

        xml = manager.to_xml()

        assert xml is not None
        assert isinstance(xml, ET._Element)
        assert xml.tag == f"{{{CT_NS}}}Types"

    def test_to_xml_bytes(self):
        """Test to_xml_bytes() returns bytes"""
        manager = ContentTypesManager()
        manager.add_default("png", "image/png")

        xml_bytes = manager.to_xml_bytes()

        assert isinstance(xml_bytes, bytes)
        assert b"<?xml version=" in xml_bytes
        assert b"Types" in xml_bytes
        assert b"image/png" in xml_bytes

    def test_to_xml_bytes_well_formed(self):
        """Test to_xml_bytes() produces well-formed XML"""
        manager = ContentTypesManager()
        manager.add_default("png", "image/png")
        manager.add_override("/ppt/slides/slide1.xml", "type1")

        xml_bytes = manager.to_xml_bytes()

        # Should be parseable
        parsed = ET.fromstring(xml_bytes)
        assert parsed is not None
        assert len(parsed) == 4  # 2 defaults (xml, rels) + 1 png + 1 override

    def test_to_xml_bytes_namespace_preservation(self):
        """Test namespace is preserved in serialization"""
        manager = ContentTypesManager()
        xml_bytes = manager.to_xml_bytes()

        assert CT_NS.encode() in xml_bytes


class TestContentTypesManagerIntegration:
    """Integration tests for ContentTypesManager"""

    def test_realistic_pptx_scenario(self):
        """Test realistic PPTX content types scenario"""
        manager = ContentTypesManager()

        # Register presentation types
        manager.ensure_presentation_types()

        # Register slides
        manager.add_slide(1)
        manager.add_slide_layout(1)
        manager.add_slide_master(1)

        # Register images
        manager.ensure_image_type("png")
        manager.ensure_image_type("jpg")

        # Generate XML
        xml_bytes = manager.to_xml_bytes()
        parsed = ET.fromstring(xml_bytes)

        defaults = parsed.findall(f"{{{CT_NS}}}Default")
        overrides = parsed.findall(f"{{{CT_NS}}}Override")

        # Should have defaults: xml, rels, png, jpg
        assert len(defaults) >= 4

        # Should have overrides: presentation, presProps, tableStyles, viewProps, slide, layout, master
        assert len(overrides) >= 7

    def test_mixed_operations(self):
        """Test mixed default and override operations"""
        manager = ContentTypesManager()

        # Mix of operations
        manager.add_default("png", "image/png")
        manager.add_override("/ppt/slides/slide1.xml", "type1")
        manager.add_default("jpg", "image/jpeg")
        manager.add_slide(2)
        manager.ensure_image_type("gif")

        xml_bytes = manager.to_xml_bytes()
        parsed = ET.fromstring(xml_bytes)

        defaults = parsed.findall(f"{{{CT_NS}}}Default")
        overrides = parsed.findall(f"{{{CT_NS}}}Override")

        # Verify structure
        assert len(defaults) >= 5  # xml, rels, png, jpg, gif
        assert len(overrides) == 2  # slide1, slide2


class TestEdgeCases:
    """Test edge cases and error conditions"""

    def test_empty_manager(self):
        """Test empty manager still has skeleton"""
        manager = ContentTypesManager()

        xml_bytes = manager.to_xml_bytes()
        parsed = ET.fromstring(xml_bytes)

        # Should have at least xml and rels defaults
        defaults = parsed.findall(f"{{{CT_NS}}}Default")
        assert len(defaults) >= 2

    def test_special_characters_in_part_name(self):
        """Test special characters in part names"""
        manager = ContentTypesManager()
        manager.add_override("/ppt/slides/slide-1.xml", "type1")

        overrides = manager.root.findall(f"{{{CT_NS}}}Override")
        assert overrides[0].get("PartName") == "/ppt/slides/slide-1.xml"

    def test_unicode_in_content_type(self):
        """Test unicode in content type"""
        manager = ContentTypesManager()
        manager.add_default("test", "application/test+xml; charset=utf-8")

        defaults = manager.root.findall(f"{{{CT_NS}}}Default")
        test_defaults = [d for d in defaults if d.get("Extension") == "test"]

        assert len(test_defaults) == 1
        assert "utf-8" in test_defaults[0].get("ContentType")

    def test_very_long_content_type(self):
        """Test very long content type string"""
        manager = ContentTypesManager()
        long_type = "application/" + "a" * 1000 + "+xml"
        manager.add_default("test", long_type)

        defaults = manager.root.findall(f"{{{CT_NS}}}Default")
        test_defaults = [d for d in defaults if d.get("Extension") == "test"]

        assert len(test_defaults) == 1
        assert len(test_defaults[0].get("ContentType")) > 1000

    def test_many_registrations(self):
        """Test handling many registrations"""
        manager = ContentTypesManager()

        # Add 100 unique defaults
        for i in range(100):
            manager.add_default(f"ext{i}", f"type{i}")

        defaults = manager.root.findall(f"{{{CT_NS}}}Default")
        assert len(defaults) >= 102  # 100 + xml + rels


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
