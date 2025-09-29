#!/usr/bin/env python3
"""Debug the actual XML being generated."""

import sys
sys.path.append('.')

from lxml import etree as ET
from src.converters.text import TextConverter
from src.services.conversion_services import ConversionServices
from src.converters.base import ConversionContext

def debug_generated_xml():
    """Debug the actual XML being generated"""

    # Create test SVG
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

    print("=== Actual Generated XML Analysis ===")

    text_elements = root.findall('.//{http://www.w3.org/2000/svg}text')

    for i, text_elem in enumerate(text_elements):
        print(f"\n--- Text Element {i+1}: '{text_elem.text}' ---")

        try:
            # Get the actual XML output
            result = converter.convert(text_elem, context)

            if isinstance(result, str):
                # Parse and analyze the XML structure
                parsed = ET.fromstring(result)

                # Extract key attributes
                rPr = parsed.find('.//a:rPr', {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'})
                if rPr is not None:
                    font_size_drawingml = rPr.get('sz', 'N/A')
                    bold_attr = rPr.get('b', 'N/A')
                    italic_attr = rPr.get('i', 'N/A')

                    print(f"Font size (DrawingML units): {font_size_drawingml}")
                    if font_size_drawingml != 'N/A':
                        font_size_pt = int(font_size_drawingml) / 100
                        print(f"Font size (converted to pt): {font_size_pt}pt")
                    print(f"Bold attribute: {bold_attr}")
                    print(f"Italic attribute: {italic_attr}")

                # Extract color
                srgbClr = parsed.find('.//a:srgbClr', {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'})
                if srgbClr is not None:
                    color_val = srgbClr.get('val', 'N/A')
                    print(f"Color value: {color_val}")

                # Extract text content
                t_elem = parsed.find('.//a:t', {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'})
                if t_elem is not None:
                    print(f"Text content: '{t_elem.text}'")

                # Show compact XML for reference
                print("Compact XML snippet:")
                compact_xml = ET.tostring(rPr, encoding='unicode') if rPr is not None else "N/A"
                print(f"  {compact_xml}")

        except Exception as e:
            print(f"❌ Failed: {e}")

if __name__ == "__main__":
    debug_generated_xml()