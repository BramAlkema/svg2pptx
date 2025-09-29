#!/usr/bin/env python3
"""
Debug what viewport dimensions are being generated
"""

import sys
sys.path.insert(0, 'src')

from lxml import etree as ET
from src.viewbox import ViewportEngine
from src.services.conversion_services import ConversionServices

# Read the star SVG
with open('debug_star.svg', 'r') as f:
    svg_content = f.read()

svg_root = ET.fromstring(svg_content)
print(f"SVG attributes: width={svg_root.get('width')}, height={svg_root.get('height')}")
print(f"SVG viewBox: {svg_root.get('viewBox')}")

# Create ViewportEngine
services = ConversionServices.create_default()
# Use standard PowerPoint slide dimensions
STANDARD_SLIDE_WIDTH_EMU = 9144000   # 10 inches
STANDARD_SLIDE_HEIGHT_EMU = 6858000  # 7.5 inches

viewport_mapping = (ViewportEngine(services.unit_converter)
                   .for_svg(svg_root)
                   .with_slide_size(STANDARD_SLIDE_WIDTH_EMU, STANDARD_SLIDE_HEIGHT_EMU)
                   .center()
                   .meet()
                   .resolve_single())

print("\nViewport mapping result:")
print(f"  scale_x: {viewport_mapping['scale_x']}")
print(f"  scale_y: {viewport_mapping['scale_y']}")
print(f"  translate_x: {viewport_mapping['translate_x']}")
print(f"  translate_y: {viewport_mapping['translate_y']}")
print(f"  viewport_width: {viewport_mapping['viewport_width']}")
print(f"  viewport_height: {viewport_mapping['viewport_height']}")

print(f"\nResult: SVG (400×300) -> Slide ({viewport_mapping['viewport_width']}×{viewport_mapping['viewport_height']})")
print(f"This creates a slide that's {viewport_mapping['viewport_width']/914400:.2f}\" × {viewport_mapping['viewport_height']/914400:.2f}\"")
print(f"Standard PowerPoint slide: 10\" × 7.5\" = {10*914400} × {7.5*914400} EMU")