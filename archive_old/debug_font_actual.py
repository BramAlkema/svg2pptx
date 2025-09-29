#!/usr/bin/env python3
"""Debug to see actual DrawingML font size values being generated."""

import sys
sys.path.append('.')

from lxml import etree as ET
from src.converters.text import TextConverter
from src.services.conversion_services import ConversionServices
from src.converters.base import ConversionContext

# Create test SVG with explicit font sizes
svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300" viewBox="0 0 400 300">
    <text x="200" y="100" font-size="24pt" fill="red" text-anchor="middle">24pt Test</text>
    <text x="200" y="150" font-size="18pt" fill="blue" text-anchor="middle">18pt Test</text>
    <text x="200" y="200" font-size="12pt" fill="green" text-anchor="middle">12pt Test</text>
</svg>'''

root = ET.fromstring(svg_content)
text_elements = root.findall('.//{http://www.w3.org/2000/svg}text')

services = ConversionServices.create_default()
context = ConversionContext(services=services, svg_root=root)
context.svg_width = 400
context.svg_height = 300

converter = TextConverter(services)

print("=== DrawingML Font Size Generation ===")

for i, element in enumerate(text_elements):
    font_size_attr = element.get('font-size')
    text_content = element.text

    print(f"\nTest {i+1}: {text_content}")
    print(f"  SVG font-size: {font_size_attr}")

    # Get font size from FontProcessor
    font_size_points = services.font_processor.get_font_size(element, None, context)
    print(f"  FontProcessor result: {font_size_points}pt")

    # Convert to DrawingML
    result = converter.convert(element, context)

    # Extract sz attribute from the generated DrawingML
    if isinstance(result, str):
        # Parse the string to find sz attribute
        import re
        sz_match = re.search(r'sz="(\d+)"', result)
        if sz_match:
            sz_value = int(sz_match.group(1))
            calculated_points = sz_value / 100
            print(f"  DrawingML sz value: {sz_value}")
            print(f"  DrawingML equivalent points: {calculated_points}pt")
        else:
            print(f"  No sz attribute found in result")
    else:
        print(f"  Result type: {type(result)}")