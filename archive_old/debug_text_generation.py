#!/usr/bin/env python3
"""Debug what DrawingML is actually being generated for text."""

import sys
sys.path.append('.')

from lxml import etree as ET
from src.converters.text import TextConverter
from core.services.conversion_services import ConversionServices
from src.converters.base import ConversionContext

# Simple test SVG
svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300" viewBox="0 0 400 300">
    <text x="200" y="150" font-size="48pt" fill="red" text-anchor="middle">TEST</text>
</svg>'''

root = ET.fromstring(svg_content)
text_element = root.find('.//{http://www.w3.org/2000/svg}text')

services = ConversionServices.create_default()
context = ConversionContext(services=services, svg_root=root)
context.svg_width = 400
context.svg_height = 300

converter = TextConverter(services)

print("=== Text Element Attributes ===")
for attr, value in text_element.attrib.items():
    print(f"  {attr}: {value}")

print(f"\n=== Text Content ===")
print(f"  Text: '{text_element.text}'")

print(f"\n=== FontProcessor Results ===")
font_size = services.font_processor.get_font_size(text_element, None, context)
print(f"  Font size: {font_size}pt")

print(f"\n=== Converting Element ===")
try:
    result = converter.convert(text_element, context)
    print(f"  Result type: {type(result)}")

    if isinstance(result, str):
        print(f"  Result length: {len(result)} characters")
        print(f"  First 500 chars:")
        print(result[:500])

        # Look for key DrawingML elements
        if '<p:sp>' in result:
            print("  ✅ Found shape element")
        else:
            print("  ❌ No shape element found")

        if 'sz=' in result:
            import re
            sz_match = re.search(r'sz="(\d+)"', result)
            if sz_match:
                print(f"  ✅ Font size: sz={sz_match.group(1)}")
            else:
                print("  ❌ No sz attribute found")

        if '<a:t>' in result:
            print("  ✅ Found text content element")
        else:
            print("  ❌ No text content element")

    else:
        print("  Result is not a string!")

except Exception as e:
    print(f"  ❌ Conversion failed: {e}")
    import traceback
    traceback.print_exc()