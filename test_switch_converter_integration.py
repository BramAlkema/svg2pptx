#!/usr/bin/env python3
"""
Comprehensive validation test for switch element converter integration.
"""

import sys
sys.path.append('/Users/ynse/projects/svg2pptx')

try:
    from core.converters.switch_converter import SwitchProcessor, SwitchResult, create_switch_processor
    from lxml import etree as ET
    from unittest.mock import Mock

    print("🔄 Testing Switch Element Converter Integration")
    print("=" * 47)

    # Test processor creation
    print("1. Testing switch processor creation...")
    switch_processor = create_switch_processor()
    assert switch_processor is not None
    assert isinstance(switch_processor, SwitchProcessor)
    print("   ✅ Switch processor created successfully")

    # Test element recognition
    print("2. Testing switch element recognition...")

    # Create test switch element
    svg_with_switch = '''<svg xmlns="http://www.w3.org/2000/svg">
        <switch>
            <rect width="100" height="100" requiredFeatures="BasicStructure"/>
            <circle r="50" systemLanguage="en"/>
            <text>Fallback text</text>
        </switch>
    </svg>'''

    svg_root = ET.fromstring(svg_with_switch)
    switch_element = svg_root.find('.//{http://www.w3.org/2000/svg}switch')

    can_process = switch_processor.can_process(switch_element)
    assert can_process is True
    print("   ✅ Switch element correctly recognized")

    # Test non-switch element rejection
    rect_element = svg_root.find('.//{http://www.w3.org/2000/svg}rect')
    can_process_rect = switch_processor.can_process(rect_element)
    assert can_process_rect is False
    print("   ✅ Non-switch elements correctly rejected")

    # Test feature requirement evaluation
    print("3. Testing feature requirements evaluation...")

    # Create mock context for feature testing
    mock_context = Mock()

    # Test supported features
    rect_element = switch_element[0]  # First child with requiredFeatures
    conditions_met = switch_processor._evaluate_conditions(rect_element, None)
    assert conditions_met is True
    print("   ✅ Supported features correctly accepted")

    # Test unsupported features
    unsupported_svg = '''<rect requiredFeatures="UnsupportedFeature"/>'''
    unsupported_element = ET.fromstring(unsupported_svg)
    conditions_not_met = switch_processor._evaluate_conditions(unsupported_element, None)
    assert conditions_not_met is False
    print("   ✅ Unsupported features correctly rejected")

    # Test system language evaluation
    print("4. Testing system language evaluation...")

    circle_element = switch_element[1]  # Second child with systemLanguage
    language_conditions = switch_processor._evaluate_conditions(circle_element, None)
    assert language_conditions is True  # PowerPoint accepts all languages
    print("   ✅ System language conditions correctly evaluated")

    # Test required extensions evaluation
    print("5. Testing required extensions evaluation...")

    # Test unsupported extension
    extension_svg = '''<rect requiredExtensions="CustomUnsupportedExtension"/>'''
    extension_element = ET.fromstring(extension_svg)
    extension_conditions = switch_processor._evaluate_conditions(extension_element, None)
    assert extension_conditions is False  # Unsupported extensions rejected
    print("   ✅ Unsupported extensions correctly rejected")

    # Test supported/mimicked extension
    supported_extension_svg = '''<rect requiredExtensions="animation"/>'''
    supported_extension_element = ET.fromstring(supported_extension_svg)
    supported_extension_conditions = switch_processor._evaluate_conditions(supported_extension_element, None)
    assert supported_extension_conditions is True  # Animation can be mimicked in PowerPoint
    print("   ✅ Supported extensions correctly accepted")

    # Test child element selection
    print("6. Testing child element selection...")

    selected_child = switch_processor._select_child_element(switch_element, None)
    assert selected_child is not None
    assert selected_child.tag.endswith('rect')  # Should select first matching child
    print("   ✅ Child element selection working correctly")

    # Test processing with valid child
    print("7. Testing processing with valid child...")

    result = switch_processor.process(switch_element)
    assert result.selected_element is not None
    assert result.selected_element.tag.endswith('rect')
    assert result.fallback_used is False
    assert 'requiredFeatures' in result.matched_conditions
    print("   ✅ Processing with valid child successful")

    # Test processing with no matching children
    print("8. Testing processing with no matching children...")

    # Create switch with only unsupported children
    no_match_svg = '''<svg xmlns="http://www.w3.org/2000/svg">
        <switch>
            <rect requiredFeatures="UnsupportedFeature"/>
            <circle requiredExtensions="CustomExtension"/>
        </switch>
    </svg>'''

    no_match_root = ET.fromstring(no_match_svg)
    no_match_switch = no_match_root.find('.//{http://www.w3.org/2000/svg}switch')

    no_match_result = switch_processor.process(no_match_switch)
    assert no_match_result.selected_element is None
    assert no_match_result.fallback_used is True
    print("   ✅ No matching children handled correctly")

    # Test matched conditions extraction
    print("9. Testing matched conditions extraction...")

    conditions = switch_processor._get_matched_conditions(rect_element)
    assert 'requiredFeatures' in conditions
    assert conditions['requiredFeatures'] == 'BasicStructure'
    print("   ✅ Matched conditions extracted correctly")

    # Test complex switch scenario
    print("10. Testing complex switch scenario...")

    complex_svg = '''<svg xmlns="http://www.w3.org/2000/svg">
        <switch>
            <!-- First child: unsupported feature -->
            <rect width="100" height="100" requiredFeatures="Animation"/>
            <!-- Second child: supported feature -->
            <circle r="50" requiredFeatures="Shape"/>
            <!-- Third child: fallback -->
            <text>Fallback content</text>
        </switch>
    </svg>'''

    complex_root = ET.fromstring(complex_svg)
    complex_switch = complex_root.find('.//{http://www.w3.org/2000/svg}switch')

    selected_complex = switch_processor._select_child_element(complex_switch, None)
    assert selected_complex is not None
    assert selected_complex.tag.endswith('circle')  # Should select second child (circle)
    print("   ✅ Complex switch scenario handled correctly")

    # Test feature checking comprehensive coverage through policy engine
    print("11. Testing comprehensive feature support...")

    # Test various supported features through policy decisions
    supported_features = [
        'BasicStructure',
        'Shape',
        'BasicPaintAttribute',
        'BasicGraphicsAttribute',
        'Marker',
        'Transform',
        'BasicText'
    ]

    for feature in supported_features:
        decision = switch_processor.policy.decide_svg_switch_conditions(required_features=feature)
        assert decision.use_native is True

    print("   ✅ All supported features working correctly")

    # Test multiple features
    print("12. Testing multiple feature requirements...")

    multi_feature_svg = '''<rect requiredFeatures="Shape BasicPaintAttribute"/>'''
    multi_feature_element = ET.fromstring(multi_feature_svg)
    multi_feature_result = switch_processor._evaluate_conditions(multi_feature_element, None)
    assert multi_feature_result is True
    print("   ✅ Multiple feature requirements handled correctly")

    # Test comprehensive extension mimicking through policy engine
    print("13. Testing comprehensive extension mimicking...")

    # Test various mimicked extensions through policy decisions
    mimicked_extensions = [
        'animation',
        'svg-animation',
        'interactivity',
        'fonts',
        'filter-effects',
        'transform',
        '3d',
        'multimedia'
    ]

    for extension in mimicked_extensions:
        decision = switch_processor.policy.decide_svg_switch_conditions(required_extensions=extension)
        assert decision.use_native is True

    # Test mixed extensions (some supported, some not)
    mixed_extension_svg = '''<rect requiredExtensions="animation CustomUnsupported"/>'''
    mixed_extension_element = ET.fromstring(mixed_extension_svg)
    mixed_result = switch_processor._evaluate_conditions(mixed_extension_element, None)
    # Should be rejected because more unsupported than supported
    assert mixed_result is False

    # Test mostly supported extensions
    mostly_supported_svg = '''<rect requiredExtensions="animation filter-effects CustomUnsupported"/>'''
    mostly_supported_element = ET.fromstring(mostly_supported_svg)
    mostly_supported_result = switch_processor._evaluate_conditions(mostly_supported_element, None)
    # Should be accepted because more supported than unsupported (2 vs 1)
    assert mostly_supported_result is True

    print("   ✅ Extension mimicking system working correctly")

    print("\n🎉 All switch element converter tests passed!")
    print("📊 Conditional rendering successfully implemented")
    print("🚀 Coverage improvement: Switch element support added")
    print("🔄 Feature detection: BasicStructure, Shape, BasicPaintAttribute, Marker, Transform, BasicText")
    print("🌐 Language support: All system languages accepted")
    print("🔧 Extension mimicking: Animation, Interactivity, Fonts, Filters, Transform, 3D, Multimedia")
    print("⚡ Fallback handling: Graceful degradation when no conditions are met")

except Exception as e:
    print(f"❌ Switch element converter test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)