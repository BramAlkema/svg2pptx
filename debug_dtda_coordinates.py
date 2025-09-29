#!/usr/bin/env python3
"""
Debug DTDA logo coordinate transformation
"""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.svg2drawingml import SVGToDrawingMLConverter

def debug_coordinates():
    """Debug coordinate transformation for DTDA logo."""
    print("🔍 DTDA Logo Coordinate Debug")
    print("=" * 40)

    # Load SVG
    with open('dtda_logo.svg', 'r') as f:
        svg_content = f.read()

    print("📄 Original SVG coordinates:")
    print(f"   ViewBox: 0 0 174.58 42.967")
    print(f"   Group transform: translate(509.85 466.99)")
    print(f"   First path starts: m-493.81-466.99")
    print(f"   Effective start: ({509.85 + (-493.81)}, {466.99 + (-466.99)}) = ({16.04}, {0})")

    # Try conversion with debugging
    converter = SVGToDrawingMLConverter()

    try:
        result = converter.convert_file('dtda_logo.svg')
        print(f"\n✅ Conversion succeeded")
        print(f"   Result length: {len(result)} characters")

        # Check if result contains actual drawing content
        if 'a:path' in result:
            print(f"   ✅ Contains path elements")
        else:
            print(f"   ❌ No path elements found")

        if 'a:off' in result:
            print(f"   ✅ Contains positioning")
        else:
            print(f"   ❌ No positioning found")

    except Exception as e:
        print(f"\n❌ Conversion failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_coordinates()