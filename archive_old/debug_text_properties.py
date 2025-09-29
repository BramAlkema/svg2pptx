#!/usr/bin/env python3
"""Debug text property extraction from SVG."""

import sys
sys.path.append('.')

from lxml import etree as ET
from src.converters.text import TextConverter
from src.services.conversion_services import ConversionServices
from src.converters.base import ConversionContext

def debug_text_property_extraction():
    """Debug what properties are being extracted from SVG text elements"""

    # Create test SVG with explicit properties
    svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300" viewBox="0 0 400 300">
        <text x="200" y="150" font-size="24pt" fill="red">FIXED TEXT</text>
        <text x="100" y="50" font-size="18pt" fill="blue" font-weight="bold">Bold Blue</text>
        <text x="300" y="250" font-size="16pt" fill="green" font-style="italic">Italic Green</text>
    </svg>'''

    root = ET.fromstring(svg_content)

    # Set up conversion context
    services = ConversionServices.create_default()
    context = ConversionContext(services=services, svg_root=root)
    context.svg_width = 400
    context.svg_height = 300

    # Create TextConverter
    converter = TextConverter(services)

    print("=== Debugging Text Property Extraction ===")

    text_elements = root.findall('.//{http://www.w3.org/2000/svg}text')

    for i, text_elem in enumerate(text_elements):
        print(f"\n--- Text Element {i+1}: '{text_elem.text}' ---")

        # Debug raw attributes
        print("Raw SVG attributes:")
        for attr, value in text_elem.attrib.items():
            print(f"  {attr}: '{value}'")

        # Debug extracted properties using TextConverter methods
        try:
            font_family = converter._get_font_family(text_elem)
            font_size = converter._get_font_size(text_elem, context)
            font_weight = converter._get_font_weight(text_elem)
            font_style = converter._get_font_style(text_elem)
            text_anchor = converter._get_text_anchor(text_elem)
            fill_color = converter._get_fill_color(text_elem)

            print("Extracted properties:")
            print(f"  font_family: '{font_family}'")
            print(f"  font_size: {font_size} pt")
            print(f"  font_weight: '{font_weight}'")
            print(f"  font_style: '{font_style}'")
            print(f"  text_anchor: '{text_anchor}'")
            print(f"  fill_color: '{fill_color}'")

            # Debug conversions used in XML builder
            bold = font_weight in ['bold', '700', '800', '900']
            italic = font_style == 'italic'

            # Test the new color extraction method
            try:
                rgb_color = converter._extract_color_value(fill_color)
                print(f"  _extract_color_value result: '{rgb_color}'")
            except Exception as e:
                print(f"  _extract_color_value failed: {e}")
                rgb_color = 'FF0000'

            print("XML builder inputs:")
            print(f"  bold: {bold}")
            print(f"  italic: {italic}")
            print(f"  rgb_color: '{rgb_color}'")
            print(f"  font_size_pt * 100: {font_size * 100}")

        except Exception as e:
            print(f"❌ Property extraction failed: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    debug_text_property_extraction()