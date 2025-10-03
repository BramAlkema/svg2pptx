#!/usr/bin/env python3
"""
Quick validation test for diffuse lighting filter integration.
"""

import sys
sys.path.append('/Users/ynse/projects/svg2pptx')

try:
    from core.services.filter_service import FilterService
    from lxml import etree as ET

    print("🔍 Testing Diffuse Lighting Filter Integration")
    print("=" * 45)

    # Test filter service creation
    print("1. Testing filter service creation...")
    filter_service = FilterService()
    assert filter_service is not None
    print("   ✅ Filter service created successfully")

    # Test supported filters list
    print("2. Testing supported filters list...")
    supported = filter_service.get_supported_filters()
    assert 'feDiffuseLighting' in supported
    print(f"   ✅ Supported filters: {supported}")

    # Test diffuse lighting filter with distant light
    print("3. Testing diffuse lighting with distant light...")
    svg_with_diffuse = '''<svg xmlns="http://www.w3.org/2000/svg">
        <defs>
            <filter id="diffuse-light">
                <feDiffuseLighting surfaceScale="2" diffuseConstant="1.5" lighting-color="white">
                    <feDistantLight azimuth="45" elevation="30"/>
                </feDiffuseLighting>
            </filter>
        </defs>
    </svg>'''

    svg_root = ET.fromstring(svg_with_diffuse)
    filter_service.extract_filters_from_svg(svg_root)

    diffuse_result = filter_service.get_filter_content('diffuse-light')
    assert diffuse_result is not None
    assert 'a:sp3d' in diffuse_result
    assert 'a:bevelT' in diffuse_result
    assert 'a:lightRig' in diffuse_result
    print("   ✅ Distant light diffuse lighting converted successfully")
    print(f"   📋 Generated XML (truncated): {diffuse_result[:100]}...")

    # Test diffuse lighting filter with point light
    print("4. Testing diffuse lighting with point light...")
    svg_with_point_light = '''<svg xmlns="http://www.w3.org/2000/svg">
        <defs>
            <filter id="point-light">
                <feDiffuseLighting surfaceScale="1" diffuseConstant="2">
                    <fePointLight x="10" y="10" z="20"/>
                </feDiffuseLighting>
            </filter>
        </defs>
    </svg>'''

    svg_root = ET.fromstring(svg_with_point_light)
    filter_service.extract_filters_from_svg(svg_root)

    point_result = filter_service.get_filter_content('point-light')
    assert point_result is not None
    assert 'a:sp3d' in point_result
    print("   ✅ Point light diffuse lighting converted successfully")

    # Test diffuse lighting filter with spot light
    print("5. Testing diffuse lighting with spot light...")
    svg_with_spot_light = '''<svg xmlns="http://www.w3.org/2000/svg">
        <defs>
            <filter id="spot-light">
                <feDiffuseLighting surfaceScale="3" diffuseConstant="1">
                    <feSpotLight x="0" y="0" z="10" pointsAtX="5" pointsAtY="5" pointsAtZ="0" specularExponent="2"/>
                </feDiffuseLighting>
            </filter>
        </defs>
    </svg>'''

    svg_root = ET.fromstring(svg_with_spot_light)
    filter_service.extract_filters_from_svg(svg_root)

    spot_result = filter_service.get_filter_content('spot-light')
    assert spot_result is not None
    assert 'a:sp3d' in spot_result
    assert 'a:innerShdw' in spot_result  # Should have inner shadow due to surface scale > 1
    print("   ✅ Spot light diffuse lighting converted successfully")

    # Test PowerPoint 3D effects structure
    print("6. Testing PowerPoint 3D effects structure...")
    assert 'a:bevelT' in diffuse_result
    assert 'a:lightRig' in diffuse_result
    assert 'w=' in diffuse_result  # bevel width
    assert 'h=' in diffuse_result  # bevel height
    assert 'rig=' in diffuse_result  # light rig direction
    print("   ✅ PowerPoint 3D effects structure validated")

    # Test filter combination with other effects
    print("7. Testing filter combination...")
    svg_with_combo = '''<svg xmlns="http://www.w3.org/2000/svg">
        <defs>
            <filter id="combo-filter">
                <feGaussianBlur stdDeviation="2"/>
                <feDiffuseLighting surfaceScale="1.5" diffuseConstant="1">
                    <feDistantLight azimuth="90" elevation="45"/>
                </feDiffuseLighting>
            </filter>
        </defs>
    </svg>'''

    svg_root = ET.fromstring(svg_with_combo)
    filter_service.extract_filters_from_svg(svg_root)

    combo_result = filter_service.get_filter_content('combo-filter')
    assert combo_result is not None
    assert 'a:blur' in combo_result  # Gaussian blur
    assert 'a:sp3d' in combo_result  # Diffuse lighting
    print("   ✅ Filter combination working correctly")

    print("\n🎉 All diffuse lighting filter tests passed!")
    print("📊 Vector-first 3D lighting effects successfully integrated")
    print("🚀 Coverage improvement: feDiffuseLighting support added")

except Exception as e:
    print(f"❌ Diffuse lighting filter test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)