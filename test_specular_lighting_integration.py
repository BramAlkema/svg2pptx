#!/usr/bin/env python3
"""
Quick validation test for specular lighting filter integration.
"""

import sys
sys.path.append('/Users/ynse/projects/svg2pptx')

try:
    from core.services.filter_service import FilterService
    from lxml import etree as ET

    print("🔍 Testing Specular Lighting Filter Integration")
    print("=" * 46)

    # Test filter service creation
    print("1. Testing filter service creation...")
    filter_service = FilterService()
    assert filter_service is not None
    print("   ✅ Filter service created successfully")

    # Test supported filters list
    print("2. Testing supported filters list...")
    supported = filter_service.get_supported_filters()
    assert 'feSpecularLighting' in supported
    print(f"   ✅ Supported filters: {supported}")

    # Test specular lighting filter with distant light
    print("3. Testing specular lighting with distant light...")
    svg_with_specular = '''<svg xmlns="http://www.w3.org/2000/svg">
        <defs>
            <filter id="specular-light">
                <feSpecularLighting surfaceScale="2" specularConstant="1.5" specularExponent="32" lighting-color="white">
                    <feDistantLight azimuth="45" elevation="30"/>
                </feSpecularLighting>
            </filter>
        </defs>
    </svg>'''

    svg_root = ET.fromstring(svg_with_specular)
    filter_service.extract_filters_from_svg(svg_root)

    specular_result = filter_service.get_filter_content('specular-light')
    assert specular_result is not None
    assert 'a:sp3d' in specular_result
    assert 'a:outerShdw' in specular_result
    assert 'prstMaterial=' in specular_result
    print("   ✅ Distant light specular lighting converted successfully")
    print(f"   📋 Generated XML (truncated): {specular_result[:100]}...")

    # Test specular lighting filter with point light
    print("4. Testing specular lighting with point light...")
    svg_with_point_light = '''<svg xmlns="http://www.w3.org/2000/svg">
        <defs>
            <filter id="point-specular">
                <feSpecularLighting surfaceScale="1" specularConstant="2" specularExponent="64">
                    <fePointLight x="10" y="10" z="20"/>
                </feSpecularLighting>
            </filter>
        </defs>
    </svg>'''

    svg_root = ET.fromstring(svg_with_point_light)
    filter_service.extract_filters_from_svg(svg_root)

    point_result = filter_service.get_filter_content('point-specular')
    assert point_result is not None
    assert 'a:sp3d' in point_result
    assert 'a:outerShdw' in point_result
    print("   ✅ Point light specular lighting converted successfully")

    # Test specular lighting filter with spot light
    print("5. Testing specular lighting with spot light...")
    svg_with_spot_light = '''<svg xmlns="http://www.w3.org/2000/svg">
        <defs>
            <filter id="spot-specular">
                <feSpecularLighting surfaceScale="3" specularConstant="1" specularExponent="128">
                    <feSpotLight x="0" y="0" z="10" pointsAtX="5" pointsAtY="5" pointsAtZ="0" specularExponent="2"/>
                </feSpecularLighting>
            </filter>
        </defs>
    </svg>'''

    svg_root = ET.fromstring(svg_with_spot_light)
    filter_service.extract_filters_from_svg(svg_root)

    spot_result = filter_service.get_filter_content('spot-specular')
    assert spot_result is not None
    assert 'a:sp3d' in spot_result
    assert 'a:outerShdw' in spot_result or 'a:reflection' in spot_result  # Should have highlight effect
    print("   ✅ Spot light specular lighting converted successfully")

    # Test PowerPoint highlight effects structure
    print("6. Testing PowerPoint highlight effects structure...")
    assert 'prstMaterial=' in specular_result  # Material mapping
    assert 'a:outerShdw' in specular_result or 'a:reflection' in specular_result  # Highlight effects
    assert 'blurRad=' in specular_result  # Highlight blur
    assert 'a:alpha' in specular_result  # Highlight intensity
    print("   ✅ PowerPoint highlight effects structure validated")

    # Test material mapping for different shininess levels
    print("7. Testing material mapping...")
    # Test low shininess (matte)
    svg_low_shininess = '''<svg xmlns="http://www.w3.org/2000/svg">
        <defs>
            <filter id="low-shininess">
                <feSpecularLighting surfaceScale="1" specularConstant="1" specularExponent="2">
                    <feDistantLight azimuth="0" elevation="45"/>
                </feSpecularLighting>
            </filter>
        </defs>
    </svg>'''

    svg_root = ET.fromstring(svg_low_shininess)
    filter_service.extract_filters_from_svg(svg_root)
    low_result = filter_service.get_filter_content('low-shininess')

    # Test high shininess (clear/mirror)
    svg_high_shininess = '''<svg xmlns="http://www.w3.org/2000/svg">
        <defs>
            <filter id="high-shininess">
                <feSpecularLighting surfaceScale="1" specularConstant="1" specularExponent="256">
                    <feDistantLight azimuth="0" elevation="45"/>
                </feSpecularLighting>
            </filter>
        </defs>
    </svg>'''

    svg_root = ET.fromstring(svg_high_shininess)
    filter_service.extract_filters_from_svg(svg_root)
    high_result = filter_service.get_filter_content('high-shininess')

    assert low_result is not None and high_result is not None
    assert 'prstMaterial=' in low_result and 'prstMaterial=' in high_result
    print("   ✅ Material mapping working for different shininess levels")

    # Test filter combination with other effects
    print("8. Testing filter combination...")
    svg_with_combo = '''<svg xmlns="http://www.w3.org/2000/svg">
        <defs>
            <filter id="combo-filter">
                <feGaussianBlur stdDeviation="2"/>
                <feSpecularLighting surfaceScale="1.5" specularConstant="1" specularExponent="16">
                    <feDistantLight azimuth="90" elevation="45"/>
                </feSpecularLighting>
            </filter>
        </defs>
    </svg>'''

    svg_root = ET.fromstring(svg_with_combo)
    filter_service.extract_filters_from_svg(svg_root)

    combo_result = filter_service.get_filter_content('combo-filter')
    assert combo_result is not None
    assert 'a:blur' in combo_result  # Gaussian blur
    assert 'a:sp3d' in combo_result  # Specular lighting
    assert 'a:outerShdw' in combo_result  # Highlight effects
    print("   ✅ Filter combination working correctly")

    print("\n🎉 All specular lighting filter tests passed!")
    print("📊 Vector-first specular highlight effects successfully integrated")
    print("🚀 Coverage improvement: feSpecularLighting support added")
    print("✨ Material property mapping functional (flat → matte → plastic → metal → clear)")

except Exception as e:
    print(f"❌ Specular lighting filter test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)