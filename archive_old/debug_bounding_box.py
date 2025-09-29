#!/usr/bin/env python3
"""
Debug bounding box calculation for path conversion
"""

import sys
sys.path.insert(0, 'src')

from lxml import etree as ET
from src.svg2drawingml import SVGToDrawingMLConverter
from src.services.conversion_services import ConversionServices

# Create a simple path SVG to test
test_svg = '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="200" height="200" xmlns="http://www.w3.org/2000/svg">
  <path d="M50,50 L150,50 L150,150 L50,150 Z" fill="red"/>
</svg>'''

print("Testing simple rectangle path: M50,50 L150,50 L150,150 L50,150 Z")
print("Expected: Rectangle from (50,50) to (150,150)")
print()

# Convert using our current system
services = ConversionServices.create_default()
converter = SVGToDrawingMLConverter(services=services)

try:
    result = converter.convert(test_svg)
    print("✅ Conversion successful")
    print()

    # Look for coordinate values in the result
    import re
    coords = re.findall(r'x="([^"]*)".*?y="([^"]*)"', result)
    if coords:
        print("Found coordinates in DrawingML:")
        for i, (x, y) in enumerate(coords[:10]):  # First 10 coordinates
            print(f"  Point {i+1}: x={x}, y={y}")

    # Look for width/height values
    sizes = re.findall(r'(?:cx|cy|w|h)="([^"]*)"', result)
    if sizes:
        print()
        print("Found size values:", sizes[:10])

    print()
    print("Generated DrawingML (first 1000 chars):")
    print(result[:1000])

except Exception as e:
    print(f"❌ Conversion failed: {e}")
    import traceback
    traceback.print_exc()