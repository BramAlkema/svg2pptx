#!/usr/bin/env python3
"""Create a PPTX test file to verify font sizes."""

import sys
sys.path.append('.')

from lxml import etree as ET
from src.svg2pptx import SVGToPowerPointConverter

try:
    # Use the SVGToPowerPointConverter class for conversion
    converter = SVGToPowerPointConverter()

    # Convert the test SVG
    svg_file = "debug_final_font_test.svg"
    output_file = "debug_font_sizes_fixed.pptx"

    with open(svg_file, 'r') as f:
        svg_content = f.read()

    # Convert to PPTX using convert_file method
    result_file = converter.convert_file(svg_file, output_file)

    print(f"✅ Successfully created {output_file}")
    print(f"📏 Expected font sizes in DrawingML:")
    print(f"   36pt → sz=72")
    print(f"   24pt → sz=48")
    print(f"   18pt → sz=36")
    print(f"   12pt → sz=24")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()