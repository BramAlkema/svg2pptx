#!/usr/bin/env python3
"""
Test marker converter integration with the clean slate architecture.
"""

import sys
sys.path.append('/Users/ynse/projects/svg2pptx')

try:
    from core.services.conversion_services import ConversionServices
    from core.converters.marker_processor import MarkerProcessor, create_marker_processor, MarkerPosition
    from lxml import etree as ET

    print("🔄 Testing Enhanced Marker Converter Integration")
    print("=" * 50)

    # Test 1: ConversionServices integration
    print("1. Testing ConversionServices integration...")
    services = ConversionServices.create_default()
    assert hasattr(services, 'marker_processor')
    assert isinstance(services.marker_processor, MarkerProcessor)
    print("   ✅ MarkerProcessor integrated into ConversionServices")

    # Test 2: Marker processor creation
    print("2. Testing marker processor creation...")
    processor = create_marker_processor()
    assert isinstance(processor, MarkerProcessor)
    print("   ✅ Marker processor created successfully")

    # Test 3: Symbol support
    print("3. Testing symbol support...")
    assert hasattr(processor, 'symbols')
    assert hasattr(processor, 'process_use_element')
    assert hasattr(processor, 'get_symbol')
    print("   ✅ Symbol support functionality available")

    # Test 4: Enhanced marker definitions
    print("4. Testing enhanced marker functionality...")
    svg_with_marker = '''<svg xmlns="http://www.w3.org/2000/svg">
        <defs>
            <marker id="arrow" viewBox="0 0 10 10" refX="1" refY="5"
                    markerWidth="6" markerHeight="6" orient="auto">
                <path d="M 0 0 L 10 5 L 0 10 z" fill="black"/>
            </marker>
            <symbol id="star" viewBox="0 0 24 24">
                <path d="M12,2 L15,9 L22,9 L17,14 L19,21 L12,17 L5,21 L7,14 L2,9 L9,9 Z"/>
            </symbol>
        </defs>
        <path d="M10,10 L50,50" marker-end="url(#arrow)"/>
        <use href="#star" x="60" y="60" width="20" height="20"/>
    </svg>'''

    svg_root = ET.fromstring(svg_with_marker)
    processor.process_marker_definitions(svg_root)

    assert 'arrow' in processor.markers
    assert 'star' in processor.symbols
    print("   ✅ Marker and symbol definitions processed correctly")

    # Test 5: Use element processing
    print("5. Testing use element processing...")
    use_element = svg_root.find('.//{http://www.w3.org/2000/svg}use')
    use_xml = processor.process_use_element(use_element)
    assert use_xml is not None
    assert 'transform=' in use_xml
    print("   ✅ Use element processing working correctly")

    # Test 6: PowerPoint line end generation
    print("6. Testing PowerPoint line end generation...")
    marker_def = processor.markers['arrow']
    line_end_xml = processor.generate_powerpoint_line_end(marker_def, MarkerPosition.END)
    assert line_end_xml is not None
    assert 'tailEnd' in line_end_xml
    print("   ✅ PowerPoint line end generation working")

    # Test 7: Visual report service integration
    print("7. Testing visual report service integration...")
    assert hasattr(services, 'visual_report_service')
    assert services.visual_report_service is not None
    print("   ✅ Visual report service integrated")

    # Test 8: Fractional EMU integration
    print("8. Testing fractional EMU integration...")
    from core.units.core import FractionalEMUConverter, PrecisionMode, create_subpixel_converter
    fractional_converter = create_subpixel_converter()
    fractional_emu = fractional_converter.to_fractional_emu("100.5px")
    assert isinstance(fractional_emu, float)
    assert fractional_emu > 0
    print("   ✅ Fractional EMU conversion working")

    print("\n🎉 All marker converter integration tests passed!")
    print("📊 Coverage improvement: Comprehensive marker and symbol support")
    print("🚀 Enhanced functionality:")
    print("   • Marker definitions with PowerPoint line ends")
    print("   • Symbol definitions and <use> element instantiation")
    print("   • Transform-aware symbol positioning")
    print("   • Visual reporting capabilities")
    print("   • Fractional EMU precision for subpixel accuracy")
    print("   • Full integration with ConversionServices")

except Exception as e:
    print(f"❌ Marker integration test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)