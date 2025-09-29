#!/usr/bin/env python3
"""Direct conversion test for fixed font sizes."""

import sys
sys.path.append('.')

from lxml import etree as ET
from src.svg2drawingml import SVGToDrawingMLConverter

# Test with the fixed font size SVG
svg_file = "debug_fixed_font_test.svg"
output_file = "debug_fixed_font_test.pptx"

try:
    # Convert SVG to PPTX
    converter = SVGToDrawingMLConverter()
    converter.convert_file(svg_file, output_file)
    print(f"✅ Successfully converted {svg_file} to {output_file}")

    # Convert to PNG for visual verification
    import subprocess
    try:
        cmd = ["/Applications/LibreOffice.app/Contents/MacOS/soffice",
               "--headless", "--convert-to", "png",
               "--outdir", ".", output_file]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print(f"✅ PNG conversion successful: {output_file.replace('.pptx', '.png')}")
        else:
            print(f"❌ PNG conversion failed: {result.stderr}")
    except Exception as e:
        print(f"❌ PNG conversion error: {e}")

except Exception as e:
    print(f"❌ Conversion failed: {e}")
    import traceback
    traceback.print_exc()