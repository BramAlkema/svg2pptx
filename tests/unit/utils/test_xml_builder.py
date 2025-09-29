#!/usr/bin/env python3
"""
Unit tests for centralized XML Builder utilities.

Tests the consolidated XML generation functionality.
"""

import pytest
import xml.etree.ElementTree as ET
from unittest.mock import Mock

from core.utils.xml_builder import (
    XMLBuilder, get_xml_builder,
    create_presentation_xml, create_slide_xml, create_content_types_xml, create_animation_xml
)


class TestXMLBuilder:
    """Test XMLBuilder functionality."""

    @pytest.fixture
    def xml_builder(self):
        """Create XMLBuilder instance for testing."""
        return XMLBuilder()

    def test_xml_builder_initialization(self, xml_builder):
        """Test XMLBuilder initialization."""
        assert xml_builder._id_counter == 1
        assert xml_builder.NAMESPACES['p'] == 'http://schemas.openxmlformats.org/presentationml/2006/main'

    def test_get_next_id(self, xml_builder):
        """Test ID generation."""
        first_id = xml_builder.get_next_id()
        second_id = xml_builder.get_next_id()

        assert first_id == 1
        assert second_id == 2
        assert xml_builder._id_counter == 3

    def test_escape_xml(self, xml_builder):
        """Test XML escaping."""
        assert xml_builder.escape_xml("test") == "test"
        assert xml_builder.escape_xml("test & more") == "test &amp; more"
        assert xml_builder.escape_xml("test <tag>") == "test &lt;tag&gt;"
        assert xml_builder.escape_xml("") == ""
        assert xml_builder.escape_xml(None) == ""

    def test_create_namespace_declaration(self, xml_builder):
        """Test namespace declaration creation."""
        # Test default namespaces
        ns_decl = xml_builder.create_namespace_declaration()
        assert 'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"' in ns_decl
        assert 'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"' in ns_decl

        # Test custom namespaces
        custom_ns = {'test': 'http://test.example.com'}
        custom_decl = xml_builder.create_namespace_declaration(custom_ns)
        assert 'xmlns:test="http://test.example.com"' in custom_decl

    def test_create_presentation_xml(self, xml_builder):
        """Test presentation XML creation."""
        width_emu = 9144000  # 10 inches
        height_emu = 6858000  # 7.5 inches
        slide_list = '<p:sldId id="256" r:id="rId2"/>'

        xml_content = xml_builder.create_presentation_xml(
            width_emu=width_emu,
            height_emu=height_emu,
            slide_list=slide_list
        )

        # Verify XML is well-formed
        root = ET.fromstring(xml_content)
        assert root.tag == '{http://schemas.openxmlformats.org/presentationml/2006/main}presentation'

        # Verify slide size
        slide_sz = root.find('.//{http://schemas.openxmlformats.org/presentationml/2006/main}sldSz')
        assert slide_sz.get('cx') == str(width_emu)
        assert slide_sz.get('cy') == str(height_emu)

        # Verify slide list is included
        assert slide_list in xml_content

    def test_create_slide_xml(self, xml_builder):
        """Test slide XML creation."""
        slide_content = '<p:sp><p:nvSpPr><p:cNvPr id="2" name="Test"/></p:nvSpPr></p:sp>'

        xml_content = xml_builder.create_slide_xml(slide_content=slide_content)

        # Verify XML is well-formed
        root = ET.fromstring(xml_content)
        assert root.tag == '{http://schemas.openxmlformats.org/presentationml/2006/main}sld'

        # Verify content is included
        assert slide_content in xml_content

        # Verify structure elements
        assert 'p:spTree' in xml_content
        assert 'p:clrMapOvr' in xml_content

    def test_create_content_types_xml(self, xml_builder):
        """Test content types XML creation."""
        additional_overrides = [
            {
                'PartName': '/ppt/slides/slide1.xml',
                'ContentType': 'application/vnd.openxmlformats-officedocument.presentationml.slide+xml'
            }
        ]

        xml_content = xml_builder.create_content_types_xml(additional_overrides=additional_overrides)

        # Verify XML is well-formed
        root = ET.fromstring(xml_content)
        assert root.tag == '{http://schemas.openxmlformats.org/package/2006/content-types}Types'

        # Verify standard defaults
        assert 'Extension="rels"' in xml_content
        assert 'Extension="xml"' in xml_content
        assert 'Extension="png"' in xml_content

        # Verify standard overrides
        assert '/ppt/presentation.xml' in xml_content
        assert '/ppt/theme/theme1.xml' in xml_content

        # Verify additional override
        assert '/ppt/slides/slide1.xml' in xml_content

    def test_create_animation_xml(self, xml_builder):
        """Test animation XML creation."""
        effect_type = "fade"
        target_shape_id = 123
        duration = 2.0
        delay = 0.5

        xml_content = xml_builder.create_animation_xml(
            effect_type=effect_type,
            target_shape_id=target_shape_id,
            duration=duration,
            delay=delay
        )

        # Verify XML structure
        assert '<p:par>' in xml_content
        assert f'spid="{target_shape_id}"' in xml_content
        assert 'dur="2000"' in xml_content  # Duration in milliseconds
        assert 'delay="500"' in xml_content  # Delay in milliseconds
        assert f'filter="{effect_type}"' in xml_content

    def test_create_relationships_xml(self, xml_builder):
        """Test relationships XML creation."""
        relationships = [
            {
                'Id': 'rId1',
                'Type': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster',
                'Target': 'slideMasters/slideMaster1.xml'
            },
            {
                'Id': 'rId2',
                'Type': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide',
                'Target': 'slides/slide1.xml'
            }
        ]

        xml_content = xml_builder.create_relationships_xml(relationships)

        # Verify XML is well-formed
        root = ET.fromstring(xml_content)
        assert root.tag == '{http://schemas.openxmlformats.org/package/2006/relationships}Relationships'

        # Verify relationships
        assert 'Id="rId1"' in xml_content
        assert 'Id="rId2"' in xml_content
        assert 'slideMaster1.xml' in xml_content
        assert 'slide1.xml' in xml_content

    def test_create_shape_xml(self, xml_builder):
        """Test shape XML creation."""
        shape_id = 42
        name = "Test Shape"
        shape_content = '<a:solidFill><a:schemeClr val="accent1"/></a:solidFill>'
        x, y = 100000, 200000  # EMU
        width, height = 500000, 300000  # EMU

        xml_content = xml_builder.create_shape_xml(
            shape_id=shape_id,
            name=name,
            shape_content=shape_content,
            x=x, y=y, width=width, height=height
        )

        # Verify structure
        assert '<p:sp>' in xml_content
        assert f'id="{shape_id}"' in xml_content
        assert f'name="{name}"' in xml_content
        assert f'x="{x}"' in xml_content
        assert f'y="{y}"' in xml_content
        assert f'cx="{width}"' in xml_content
        assert f'cy="{height}"' in xml_content
        assert shape_content in xml_content

    def test_validate_xml(self, xml_builder):
        """Test XML validation."""
        valid_xml = '<?xml version="1.0"?><root><child>content</child></root>'
        invalid_xml = '<?xml version="1.0"?><root><unclosed>'

        assert xml_builder.validate_xml(valid_xml) is True
        assert xml_builder.validate_xml(invalid_xml) is False

    def test_pretty_print_xml(self, xml_builder):
        """Test XML pretty printing."""
        compact_xml = '<root><child>content</child></root>'

        formatted_xml = xml_builder.pretty_print_xml(compact_xml)

        # Should contain proper indentation
        assert '    <child>' in formatted_xml
        assert '<?xml version=' in formatted_xml

        # Test with invalid XML
        invalid_xml = '<root><unclosed>'
        result = xml_builder.pretty_print_xml(invalid_xml)
        assert result == invalid_xml  # Should return original


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_get_xml_builder(self):
        """Test global XML builder access."""
        builder1 = get_xml_builder()
        builder2 = get_xml_builder()

        # Should return same instance (singleton)
        assert builder1 is builder2
        assert isinstance(builder1, XMLBuilder)

    def test_convenience_functions(self):
        """Test convenience wrapper functions."""
        # Test presentation XML
        pres_xml = create_presentation_xml(9144000, 6858000)
        assert 'p:presentation' in pres_xml
        assert 'cx="9144000"' in pres_xml

        # Test slide XML
        slide_xml = create_slide_xml("test content")
        assert 'p:sld' in slide_xml
        assert 'test content' in slide_xml

        # Test content types XML
        ct_xml = create_content_types_xml()
        assert 'Types' in ct_xml
        assert 'presentation.xml' in ct_xml

        # Test animation XML
        anim_xml = create_animation_xml("fade", 123)
        assert 'p:par' in anim_xml
        assert 'spid="123"' in anim_xml


class TestXMLIntegration:
    """Test integration scenarios."""

    def test_complete_presentation_structure(self):
        """Test creating a complete presentation structure."""
        xml_builder = get_xml_builder()

        # Create content types
        content_types = xml_builder.create_content_types_xml(
            additional_overrides=[
                {
                    'PartName': '/ppt/slides/slide1.xml',
                    'ContentType': 'application/vnd.openxmlformats-officedocument.presentationml.slide+xml'
                }
            ]
        )

        # Create presentation with slide
        presentation_xml = xml_builder.create_presentation_xml(
            width_emu=9144000,
            height_emu=6858000,
            slide_list='<p:sldId id="256" r:id="rId2"/>'
        )

        # Create slide
        slide_xml = xml_builder.create_slide_xml(
            slide_content='<p:sp><p:nvSpPr><p:cNvPr id="2" name="Test"/></p:nvSpPr></p:sp>'
        )

        # Verify all are valid XML
        assert xml_builder.validate_xml(content_types)
        assert xml_builder.validate_xml(presentation_xml)
        assert xml_builder.validate_xml(slide_xml)

        # Verify integration
        assert 'slide1.xml' in content_types
        assert 'p:sldId' in presentation_xml
        assert 'Test' in slide_xml