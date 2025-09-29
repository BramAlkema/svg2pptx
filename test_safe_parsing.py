#!/usr/bin/env python3
"""
Test safe transform parsing implementation
"""

import sys
from pathlib import Path
from lxml import etree as ET

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.utils.transform_utils import (
    get_transform_safe, has_transform_safe,
    parse_transform_safe, get_attribute_safe, has_attribute_safe
)

def test_safe_parsing():
    """Test safe parsing functions with various edge cases."""
    print("🧪 Testing Safe Transform Parsing")
    print("=" * 40)

    # Test with real DTDA logo SVG
    try:
        with open('dtda_logo.svg', 'r') as f:
            svg_content = f.read()

        svg_root = ET.fromstring(svg_content)

        # Test group element transform
        g_element = svg_root.find('.//{http://www.w3.org/2000/svg}g')
        if g_element is not None:
            transform = get_transform_safe(g_element)
            print(f"✅ Group transform: {transform}")
            print(f"✅ Has transform: {has_transform_safe(g_element)}")

        # Test path elements
        path_elements = svg_root.findall('.//{http://www.w3.org/2000/svg}path')
        print(f"✅ Found {len(path_elements)} path elements")

        for i, path in enumerate(path_elements[:3]):  # Test first 3
            transform = get_transform_safe(path)
            has_transform = has_transform_safe(path)
            print(f"   Path {i+1}: transform={transform is not None}, has_transform={has_transform}")

    except Exception as e:
        print(f"❌ Error testing with DTDA logo: {e}")
        import traceback
        traceback.print_exc()

    # Test edge cases
    print("\n🔍 Testing Edge Cases")
    print("-" * 25)

    # Test with None element
    try:
        result = get_transform_safe(None)
        print(f"✅ None element: {result}")
    except Exception as e:
        print(f"❌ None element failed: {e}")

    # Test with malformed XML element
    try:
        test_svg = '<g transform="translate(10 20)"></g>'
        test_element = ET.fromstring(test_svg)
        transform = get_transform_safe(test_element)
        print(f"✅ Valid transform: {transform}")
    except Exception as e:
        print(f"❌ Valid transform failed: {e}")

    # Test with empty transform
    try:
        test_svg = '<g transform=""></g>'
        test_element = ET.fromstring(test_svg)
        transform = get_transform_safe(test_element)
        print(f"✅ Empty transform: {transform}")
    except Exception as e:
        print(f"❌ Empty transform failed: {e}")

    # Test with no transform attribute
    try:
        test_svg = '<g></g>'
        test_element = ET.fromstring(test_svg)
        transform = get_transform_safe(test_element)
        print(f"✅ No transform: {transform}")
    except Exception as e:
        print(f"❌ No transform failed: {e}")

    print("\n🎉 Safe parsing tests completed!")

if __name__ == "__main__":
    test_safe_parsing()