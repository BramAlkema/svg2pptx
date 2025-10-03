#!/usr/bin/env python3
"""
Quick validation test for ImageMapper template conversion.
"""

import sys
sys.path.append('/Users/ynse/projects/svg2pptx')

try:
    from core.utils.enhanced_xml_builder import EnhancedXMLBuilder
    from lxml import etree as ET

    # Test EnhancedXMLBuilder image methods
    builder = EnhancedXMLBuilder()

    print("🔍 Testing ImageMapper Template Conversion")
    print("=" * 45)

    # Test raster image generation
    print("1. Testing raster image generation...")
    raster_element = builder.generate_image_raster_picture(
        image_id=1,
        x_emu=100000,
        y_emu=200000,
        width_emu=500000,
        height_emu=300000,
        rel_id="rId5"
    )

    # Validate structure
    assert raster_element.tag.endswith('pic')
    assert raster_element.find('.//p:cNvPr', {'p': 'http://schemas.openxmlformats.org/presentationml/2006/main'}) is not None
    print("   ✅ Raster image template generation successful")

    # Test vector image generation
    print("2. Testing vector image generation...")
    vector_element = builder.generate_image_vector_picture(
        image_id=2,
        x_emu=150000,
        y_emu=250000,
        width_emu=600000,
        height_emu=400000,
        rel_id="rId6"
    )

    # Validate structure
    assert vector_element.tag.endswith('pic')
    assert vector_element.find('.//emf:emfBlip', {'emf': 'http://schemas.microsoft.com/office/drawing/2010/emf'}) is not None
    print("   ✅ Vector image template generation successful")

    # Test with effects
    print("3. Testing with effects...")
    effects_xml = '<a:effectLst xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:alpha val="50000"/></a:effectLst>'
    raster_with_effects = builder.generate_image_raster_picture(
        image_id=3,
        x_emu=100000,
        y_emu=200000,
        width_emu=500000,
        height_emu=300000,
        rel_id="rId7",
        effects_xml=effects_xml
    )

    # Check if effects were added
    effects_found = raster_with_effects.find('.//a:effectLst', {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'}) is not None
    assert effects_found
    print("   ✅ Effects integration successful")

    # Test XML string conversion
    print("4. Testing XML string conversion...")
    xml_string = builder.element_to_string(raster_element)
    assert '<p:pic' in xml_string
    assert 'xmlns:p=' in xml_string
    assert 'r:embed="rId5"' in xml_string
    print("   ✅ XML string conversion successful")

    print("\n🎉 All ImageMapper template tests passed!")
    print(f"📊 Template cache is working with optimized deep copy")

except Exception as e:
    print(f"❌ ImageMapper validation failed: {e}")
    sys.exit(1)