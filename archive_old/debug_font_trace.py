#!/usr/bin/env python3
"""Debug script to trace font size conversion process."""

import sys
sys.path.append('.')

from lxml import etree as ET
from src.utils.font_processor import FontProcessor
from src.converters.text import TextConverter
from src.services.conversion_services import ConversionServices

# Create test SVG with 24pt font
svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300" viewBox="0 0 400 300">
    <text x="200" y="150" font-size="24pt" fill="red" text-anchor="middle">Fixed Font Size Test</text>
</svg>'''

# Parse SVG
root = ET.fromstring(svg_content)
text_element = root.find('.//{http://www.w3.org/2000/svg}text')

print("=== Font Size Tracing ===")
print(f"Original SVG font-size attribute: {text_element.get('font-size')}")

# Test FontProcessor directly
processor = FontProcessor()
font_size_result = processor.get_font_size(text_element, None, None)
print(f"FontProcessor.get_font_size() result: {font_size_result}pt")

# Test FontProcessor internal parsing
internal_result = processor._parse_font_size(text_element.get('font-size'), None)
print(f"FontProcessor._parse_font_size() result: {internal_result}pt")

# Now test through the full conversion pipeline
print("\n=== Full Conversion Pipeline ===")
services = ConversionServices.create_default()

# Create converter and process
from src.converters.base import ConversionContext
context = ConversionContext(services=services, svg_root=root)
context.svg_width = 400
context.svg_height = 300

converter = TextConverter(services)

# Add debug to converter by temporarily patching
original_font_size_func = converter.services.font_processor.get_font_size

def debug_font_size(element, style_parser=None, context=None):
    raw_size = element.get('font-size')
    result = original_font_size_func(element, style_parser, context)
    print(f"  Font size conversion: {raw_size} -> {result}pt")
    return result

converter.services.font_processor.get_font_size = debug_font_size

# Convert element
result = converter.convert(text_element, context)
print(f"\nFinal DrawingML result:")
print(ET.tostring(result, pretty_print=True, encoding='unicode'))