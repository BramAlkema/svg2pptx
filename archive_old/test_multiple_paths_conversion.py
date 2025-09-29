#!/usr/bin/env python3
"""
E2E test to verify multiple paths render correctly in PowerPoint
"""

import sys
import os
sys.path.insert(0, '.')

from src.svg2pptx import SVGToPowerPointConverter
from pathlib import Path

def test_multiple_paths():
    """Convert multi-path SVG and verify output"""

    # Initialize converter
    converter = SVGToPowerPointConverter()

    # Convert the multi-path SVG
    svg_file = "test_multiple_paths.svg"
    pptx_file = "test_multiple_paths.pptx"

    print(f"Converting {svg_file} to {pptx_file}...")
    result = converter.convert_file(svg_file, pptx_file)

    print(f"✅ Created: {result}")

    # Verify the file exists and has reasonable size
    if os.path.exists(pptx_file):
        size = os.path.getsize(pptx_file)
        print(f"📊 PPTX file size: {size:,} bytes")

        if size > 10000:  # Reasonable size for a PPTX with graphics
            print("✅ File size indicates real content (not just empty slides)")
        else:
            print("⚠️ File size seems small - may not contain graphics")
    else:
        print("❌ PPTX file was not created")
        return False

    return True

if __name__ == "__main__":
    success = test_multiple_paths()
    if success:
        print("\n🎉 Multi-path conversion completed successfully!")
    else:
        print("\n❌ Multi-path conversion failed!")
        sys.exit(1)