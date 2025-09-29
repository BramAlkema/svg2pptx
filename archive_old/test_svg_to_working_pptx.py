#!/usr/bin/env python3
"""Test SVG to PPTX conversion using the working generator."""

import sys
sys.path.append('.')

from lxml import etree as ET
from working_pptx_generator import WorkingPPTXGenerator

def convert_svg_to_pptx(svg_file, output_file):
    """Convert SVG file to PPTX using working generator"""

    # Parse the SVG
    with open(svg_file, 'r') as f:
        svg_content = f.read()

    root = ET.fromstring(svg_content)

    # Extract viewBox dimensions
    viewbox = root.get('viewBox', '0 0 400 300')
    _, _, svg_width, svg_height = map(float, viewbox.split())

    print(f"SVG dimensions: {svg_width} x {svg_height}")

    # Create the generator
    generator = WorkingPPTXGenerator()

    # Find all text elements in the SVG
    for text_elem in root.findall('.//{http://www.w3.org/2000/svg}text'):
        # Extract text properties
        x = float(text_elem.get('x', 0))
        y = float(text_elem.get('y', 0))
        text_content = text_elem.text or ''

        # Extract font size (default to 24pt if not specified)
        font_size_attr = text_elem.get('font-size', '24pt')
        if font_size_attr.endswith('pt'):
            font_size = float(font_size_attr[:-2])
        else:
            font_size = 24

        # Extract color (default to red)
        fill_color = text_elem.get('fill', 'red')
        if fill_color == 'red':
            color = 'FF0000'
        elif fill_color == 'blue':
            color = '0000FF'
        elif fill_color == 'green':
            color = '00FF00'
        else:
            color = '000000'  # Black default

        print(f"Found text: '{text_content}' at ({x}, {y}) size={font_size}pt color={color}")

        # Add to generator
        generator.add_text(text_content, x, y, font_size, color)

    # Generate the PPTX
    generator.generate(output_file)
    print(f"✅ Created {output_file}")

if __name__ == "__main__":
    # Test with our simple SVG
    convert_svg_to_pptx('debug_simple_visible_test.svg', 'debug_svg_to_working_pptx.pptx')
    print("✅ SVG to PPTX conversion complete using working generator!")