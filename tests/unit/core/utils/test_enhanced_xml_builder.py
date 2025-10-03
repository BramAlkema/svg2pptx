#!/usr/bin/env python3
"""
Test Enhanced XML Builder

Comprehensive tests for the enhanced XML builder that replaces
string interpolation with proper lxml.etree DOM manipulation.
"""

import pytest
from lxml import etree as ET
from lxml.etree import QName

from core.utils.enhanced_xml_builder import (
    EnhancedXMLBuilder, FluentShapeBuilder,
    create_presentation, create_slide, create_shape,
    create_content_types, create_relationships,
    P_URI, A_URI, R_URI, CONTENT_TYPES_URI, RELATIONSHIPS_URI,
    NSMAP, CONTENT_NSMAP, RELATIONSHIPS_NSMAP
)


class TestEnhancedXMLBuilder:
    """Test enhanced XML builder functionality"""

    @pytest.fixture
    def builder(self):
        """Create enhanced XML builder instance"""
        return EnhancedXMLBuilder()

    def test_initialization(self, builder):
        """Test builder initialization"""
        assert builder._id_counter == 1
        assert hasattr(builder, 'logger')

    def test_id_generation(self, builder):
        """Test unique ID generation"""
        id1 = builder.get_next_id()
        id2 = builder.get_next_id()
        id3 = builder.get_next_id()

        assert id1 == 1
        assert id2 == 2
        assert id3 == 3

        # Test reset
        builder.reset_id_counter()
        assert builder.get_next_id() == 1

    def test_create_presentation_element(self, builder):
        """Test presentation element creation with proper namespaces"""
        width_emu = 9144000
        height_emu = 6858000
        slide_type = "screen16x9"

        presentation = builder.create_presentation_element(width_emu, height_emu, slide_type)

        # Check element structure and namespaces
        assert presentation.tag == QName(P_URI, 'presentation')
        assert presentation.nsmap['p'] == P_URI
        assert presentation.nsmap['r'] == R_URI

        # Check slide master list
        master_list = presentation.find('.//p:sldMasterIdLst', NSMAP)
        assert master_list is not None
        master_id = master_list.find('.//p:sldMasterId', NSMAP)
        assert master_id is not None
        assert master_id.get('id') == '2147483648'
        assert master_id.get(QName(R_URI, 'id')) == 'rId1'

        # Check slide ID list exists (empty initially)
        slide_list = presentation.find('.//p:sldIdLst', NSMAP)
        assert slide_list is not None

        # Check slide size
        slide_size = presentation.find('.//p:sldSz', NSMAP)
        assert slide_size is not None
        assert slide_size.get('cx') == str(width_emu)
        assert slide_size.get('cy') == str(height_emu)
        assert slide_size.get('type') == slide_type

        # Check notes size
        notes_size = presentation.find('.//p:notesSz', NSMAP)
        assert notes_size is not None
        assert notes_size.get('cx') == str(height_emu)
        assert notes_size.get('cy') == str(int(height_emu * 4/3))

    def test_add_slide_to_presentation(self, builder):
        """Test adding slide reference to presentation"""
        presentation = builder.create_presentation_element(9144000, 6858000)

        # Add slide references
        builder.add_slide_to_presentation(presentation, 256, 'rId2')
        builder.add_slide_to_presentation(presentation, 257, 'rId3')

        # Check slide references
        slide_list = presentation.find('.//p:sldIdLst', NSMAP)
        slide_refs = slide_list.findall('.//p:sldId', NSMAP)

        assert len(slide_refs) == 2
        assert slide_refs[0].get('id') == '256'
        assert slide_refs[0].get(QName(R_URI, 'id')) == 'rId2'
        assert slide_refs[1].get('id') == '257'
        assert slide_refs[1].get(QName(R_URI, 'id')) == 'rId3'

    def test_create_slide_element(self, builder):
        """Test slide element creation with proper structure"""
        slide = builder.create_slide_element(layout_id=5)

        # Check element structure
        assert slide.tag == QName(P_URI, 'sld')
        assert slide.nsmap['p'] == P_URI
        assert slide.nsmap['a'] == A_URI

        # Check cSld structure
        cSld = slide.find('.//p:cSld', NSMAP)
        assert cSld is not None

        # Check shape tree
        spTree = cSld.find('.//p:spTree', NSMAP)
        assert spTree is not None

        # Check non-visual group shape properties
        nvGrpSpPr = spTree.find('.//p:nvGrpSpPr', NSMAP)
        assert nvGrpSpPr is not None

        cNvPr = nvGrpSpPr.find('.//p:cNvPr', NSMAP)
        assert cNvPr is not None
        assert cNvPr.get('id') == '1'
        assert cNvPr.get('name') == ''

        # Check group shape properties
        grpSpPr = spTree.find('.//p:grpSpPr', NSMAP)
        assert grpSpPr is not None

        xfrm = grpSpPr.find('.//a:xfrm', NSMAP)
        assert xfrm is not None

        # Check color map override
        clrMapOvr = slide.find('.//p:clrMapOvr', NSMAP)
        assert clrMapOvr is not None

        masterClrMapping = clrMapOvr.find('.//a:masterClrMapping', NSMAP)
        assert masterClrMapping is not None

    def test_create_shape_element(self, builder):
        """Test shape element creation"""
        shape_id = 10
        name = "Test Rectangle"
        x, y = 1000, 2000
        width, height = 5000, 3000

        shape = builder.create_shape_element(shape_id, name, x, y, width, height)

        # Check element structure
        assert shape.tag == QName(P_URI, 'sp')

        # Check non-visual shape properties
        nvSpPr = shape.find('.//p:nvSpPr', NSMAP)
        assert nvSpPr is not None

        cNvPr = nvSpPr.find('.//p:cNvPr', NSMAP)
        assert cNvPr is not None
        assert cNvPr.get('id') == str(shape_id)
        assert cNvPr.get('name') == name

        # Check shape properties and transform
        spPr = shape.find('.//p:spPr', NSMAP)
        assert spPr is not None

        xfrm = spPr.find('.//a:xfrm', NSMAP)
        assert xfrm is not None

        off = xfrm.find('.//a:off', NSMAP)
        assert off is not None
        assert off.get('x') == str(x)
        assert off.get('y') == str(y)

        ext = xfrm.find('.//a:ext', NSMAP)
        assert ext is not None
        assert ext.get('cx') == str(width)
        assert ext.get('cy') == str(height)

    def test_add_shape_to_slide(self, builder):
        """Test adding shape to slide"""
        slide = builder.create_slide_element()
        shape = builder.create_shape_element(2, "Test Shape")

        builder.add_shape_to_slide(slide, shape)

        # Check shape was added to spTree
        spTree = slide.find('.//p:spTree', NSMAP)
        shapes = spTree.findall('.//p:sp', NSMAP)

        assert len(shapes) == 1
        assert shapes[0] == shape

    def test_create_content_types_element(self, builder):
        """Test content types element creation"""
        additional_overrides = [
            {'PartName': '/ppt/slides/slide1.xml', 'ContentType': 'application/vnd.openxmlformats-officedocument.presentationml.slide+xml'}
        ]

        types = builder.create_content_types_element(additional_overrides)

        # Check element structure and namespace
        assert types.tag == QName(CONTENT_TYPES_URI, 'Types')
        assert None in types.nsmap  # Default namespace
        assert types.nsmap[None] == CONTENT_TYPES_URI

        # Check default entries (template-based has 2 defaults)
        defaults = types.findall('.//Default', {None: CONTENT_TYPES_URI})
        assert len(defaults) >= 2  # Template has rels and xml defaults

        # Find specific defaults (check rels which is in template)
        rels_default = None
        for default in defaults:
            if default.get('Extension') == 'rels':
                rels_default = default
                break

        assert rels_default is not None
        assert rels_default.get('ContentType') == 'application/vnd.openxmlformats-package.relationships+xml'

        # Check overrides (5 from template + 1 additional)
        overrides = types.findall('.//Override', {None: CONTENT_TYPES_URI})
        assert len(overrides) == 6  # Template has 5, we added 1

        # Check additional override
        slide_override = None
        for override in overrides:
            if override.get('PartName') == '/ppt/slides/slide1.xml':
                slide_override = override
                break

        assert slide_override is not None
        assert slide_override.get('ContentType') == 'application/vnd.openxmlformats-presentationml.slide+xml'

    def test_create_relationships_element(self, builder):
        """Test relationships element creation"""
        relationships = [
            {'Id': 'rId1', 'Type': 'http://example.com/type1', 'Target': 'target1.xml'},
            {'Id': 'rId2', 'Type': 'http://example.com/type2', 'Target': 'target2.xml'}
        ]

        rels = builder.create_relationships_element(relationships)

        # Check element structure and namespace
        assert rels.tag == QName(RELATIONSHIPS_URI, 'Relationships')
        assert None in rels.nsmap
        assert rels.nsmap[None] == RELATIONSHIPS_URI

        # Check relationship entries
        rel_elements = rels.findall('.//Relationship', {None: RELATIONSHIPS_URI})
        assert len(rel_elements) == 2

        # Check specific relationship
        rel1 = rel_elements[0]
        assert rel1.get('Id') == 'rId1'
        assert rel1.get('Type') == 'http://example.com/type1'
        assert rel1.get('Target') == 'target1.xml'

    def test_create_animation_element(self, builder):
        """Test animation element creation"""
        effect_type = "fadeIn"
        target_shape_id = 5
        duration = 2.0
        delay = 0.5

        animation = builder.create_animation_element(effect_type, target_shape_id, duration, delay)

        # Check basic structure
        assert animation.tag == QName(P_URI, 'par')

        # Check timing structure
        cTn = animation.find('.//p:cTn', NSMAP)
        assert cTn is not None
        assert cTn.get('dur') == 'indefinite'
        assert cTn.get('nodeType') == 'seq'

        # Check animation effect
        animEffect = animation.find('.//p:animEffect', NSMAP)
        assert animEffect is not None
        assert animEffect.get('transition') == 'in'
        assert animEffect.get('filter') == effect_type

        # Check target
        spTgt = animation.find('.//p:spTgt', NSMAP)
        assert spTgt is not None
        assert spTgt.get('spid') == str(target_shape_id)

        # Check timing values
        child_cTn = animation.find('.//p:childTnLst/p:par/p:cTn', NSMAP)
        assert child_cTn is not None
        assert child_cTn.get('dur') == '2000'  # 2 seconds in ms
        assert child_cTn.get('delay') == '500'  # 0.5 seconds in ms

    def test_element_to_string(self, builder):
        """Test element serialization to XML string"""
        slide = builder.create_slide_element()

        # Test with pretty printing
        xml_str = builder.element_to_string(slide, pretty_print=True)
        assert xml_str.startswith('<?xml version=')
        assert '<p:sld' in xml_str
        assert 'xmlns:p=' in xml_str

        # Test without pretty printing
        xml_str_compact = builder.element_to_string(slide, pretty_print=False)
        assert xml_str_compact.startswith('<?xml version=')
        assert len(xml_str_compact) < len(xml_str)  # Should be more compact

    def test_validate_element(self, builder):
        """Test XML element validation"""
        # Test valid element
        slide = builder.create_slide_element()
        assert builder.validate_element(slide) == True

        # Test that lxml prevents invalid XML characters
        invalid_element = ET.Element("invalid")
        # lxml prevents invalid characters at assignment time
        with pytest.raises(ValueError):
            invalid_element.text = "test\x00"  # Invalid XML character

    def test_add_text_to_element(self, builder):
        """Test adding text content with proper escaping"""
        element = ET.Element("test")

        # Test normal text
        builder.add_text_to_element(element, "Hello World")
        assert element.text == "Hello World"

        # Test text with special characters
        builder.add_text_to_element(element, "Text with <>&\"' characters")
        assert element.text == "Text with <>&\"' characters"

        # Test that XML serialization handles escaping
        xml_str = ET.tostring(element, encoding='unicode')
        assert "&lt;" in xml_str
        assert "&gt;" in xml_str
        assert "&amp;" in xml_str


class TestFluentShapeBuilder:
    """Test fluent shape builder functionality"""

    @pytest.fixture
    def builder(self):
        """Create enhanced XML builder instance"""
        return EnhancedXMLBuilder()

    def test_fluent_shape_building(self, builder):
        """Test fluent interface for shape building"""
        shape_builder = FluentShapeBuilder(builder, 10, "Test Shape")

        # Test method chaining
        result = (shape_builder
                 .position(1000, 2000)
                 .size(5000, 3000))

        assert result == shape_builder  # Fluent interface

        # Build the shape
        shape = shape_builder.build()

        # Verify position
        off = shape.find('.//a:off', NSMAP)
        assert off.get('x') == '1000'
        assert off.get('y') == '2000'

        # Verify size
        ext = shape.find('.//a:ext', NSMAP)
        assert ext.get('cx') == '5000'
        assert ext.get('cy') == '3000'

    def test_geometry_addition(self, builder):
        """Test adding geometry to fluent shape builder"""
        shape_builder = FluentShapeBuilder(builder, 11, "Geometry Shape")

        # Create simple geometry element
        geometry = ET.Element(QName(A_URI, 'custGeom'))

        # Add geometry
        shape_builder.geometry(geometry)
        shape = shape_builder.build()

        # Check geometry was added
        spPr = shape.find('.//p:spPr', NSMAP)
        custGeom = spPr.find('.//a:custGeom', NSMAP)
        assert custGeom is not None


class TestFactoryFunctions:
    """Test factory functions for convenience"""

    def test_create_presentation(self):
        """Test presentation factory function"""
        presentation = create_presentation(9144000, 6858000, slide_type="screen4x3")

        assert presentation.tag == QName(P_URI, 'presentation')
        slide_size = presentation.find('.//p:sldSz', NSMAP)
        assert slide_size.get('type') == 'screen4x3'

    def test_create_slide(self):
        """Test slide factory function"""
        slide = create_slide(layout_id=2)

        assert slide.tag == QName(P_URI, 'sld')
        # Layout ID is not directly stored in the slide element itself
        # It would be used by the caller for relationship setup

    def test_create_shape(self):
        """Test shape factory function"""
        shape_builder = create_shape(15, "Factory Shape")

        assert isinstance(shape_builder, FluentShapeBuilder)
        shape = shape_builder.build()

        cNvPr = shape.find('.//p:cNvPr', NSMAP)
        assert cNvPr.get('id') == '15'
        assert cNvPr.get('name') == 'Factory Shape'

    def test_create_content_types(self):
        """Test content types factory function"""
        types = create_content_types()

        assert types.tag == QName(CONTENT_TYPES_URI, 'Types')

    def test_create_relationships(self):
        """Test relationships factory function"""
        rels_data = [{'Id': 'rId1', 'Type': 'test', 'Target': 'test.xml'}]
        rels = create_relationships(rels_data)

        assert rels.tag == QName(RELATIONSHIPS_URI, 'Relationships')


class TestNamespaceHandling:
    """Test namespace handling and compliance"""

    @pytest.fixture
    def builder(self):
        return EnhancedXMLBuilder()

    def test_namespace_constants(self):
        """Test namespace URI constants"""
        assert P_URI == "http://schemas.openxmlformats.org/presentationml/2006/main"
        assert A_URI == "http://schemas.openxmlformats.org/drawingml/2006/main"
        assert R_URI == "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

    def test_nsmap_consistency(self):
        """Test namespace map consistency"""
        assert NSMAP['p'] == P_URI
        assert NSMAP['a'] == A_URI
        assert NSMAP['r'] == R_URI

    def test_qname_usage(self, builder):
        """Test proper QName usage in elements"""
        slide = builder.create_slide_element()

        # Check that all elements use proper QNames
        def check_qnames(element):
            # Element tag should be a QName or have proper namespace
            if hasattr(element.tag, 'namespace'):
                assert element.tag.namespace in [P_URI, A_URI, R_URI]

            # Check all children recursively
            for child in element:
                check_qnames(child)

        check_qnames(slide)

    def test_xml_serialization_namespaces(self, builder):
        """Test that serialized XML contains proper namespace declarations"""
        presentation = builder.create_presentation_element(9144000, 6858000)
        xml_str = builder.element_to_string(presentation)

        # Check namespace declarations in XML
        assert 'xmlns:p=' in xml_str
        assert 'xmlns:a=' in xml_str or 'xmlns:r=' in xml_str
        assert P_URI in xml_str


class TestPerformanceAndCompatibility:
    """Test performance improvements and backward compatibility"""

    @pytest.fixture
    def builder(self):
        return EnhancedXMLBuilder()

    def test_element_reuse(self, builder):
        """Test that elements can be reused and modified"""
        slide = builder.create_slide_element()
        shape1 = builder.create_shape_element(1, "Shape1")
        shape2 = builder.create_shape_element(2, "Shape2")

        # Add both shapes
        builder.add_shape_to_slide(slide, shape1)
        builder.add_shape_to_slide(slide, shape2)

        # Verify both are present
        spTree = slide.find('.//p:spTree', NSMAP)
        shapes = spTree.findall('.//p:sp', NSMAP)
        assert len(shapes) == 2

    def test_large_document_creation(self, builder):
        """Test creating larger documents efficiently"""
        presentation = builder.create_presentation_element(9144000, 6858000)

        # Add multiple slides
        for i in range(10):
            builder.add_slide_to_presentation(presentation, 256 + i, f'rId{i+2}')

        # Verify all slides added
        slide_list = presentation.find('.//p:sldIdLst', NSMAP)
        slide_refs = slide_list.findall('.//p:sldId', NSMAP)
        assert len(slide_refs) == 10

        # Test serialization performance (should complete quickly)
        import time
        start_time = time.time()
        xml_str = builder.element_to_string(presentation)
        end_time = time.time()

        # Should complete in reasonable time (less than 1 second for this size)
        assert end_time - start_time < 1.0
        assert len(xml_str) > 800  # Should produce substantial XML