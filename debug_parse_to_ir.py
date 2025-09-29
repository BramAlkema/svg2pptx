#!/usr/bin/env python3
"""
Debug script to test parse_to_ir method that's failing in the analyzer
"""

import sys
sys.path.insert(0, '.')

from lxml import etree as ET
from core.parse.parser import SVGParser

# Sample complex SVG content (simplified version of the E2E test SVG)
complex_svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600">
    <defs>
        <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" style="stop-color:rgb(255,255,0);stop-opacity:1" />
            <stop offset="100%" style="stop-color:rgb(255,0,0);stop-opacity:1" />
        </linearGradient>
        <pattern id="pattern1" patternUnits="userSpaceOnUse" width="20" height="20">
            <circle cx="10" cy="10" r="5" fill="blue"/>
        </pattern>
    </defs>

    <g transform="translate(50,50) scale(1.2)">
        <rect x="0" y="0" width="100" height="80" fill="url(#grad1)"/>
        <path d="M 10 10 L 50 50 Q 80 10 100 50" stroke="black" fill="none"/>
        <text x="20" y="40">Sample Text</text>
    </g>

    <circle cx="200" cy="100" r="30" fill="url(#pattern1)"/>
</svg>'''

def main():
    print("🔍 Testing parse_to_ir method...")

    try:
        # Create parser
        parser = SVGParser()
        print(f"✅ SVGParser created")

        # Test parse_to_ir
        print("🔄 Calling parse_to_ir...")
        scene, parse_result = parser.parse_to_ir(complex_svg)

        print(f"📊 Parse result:")
        print(f"   Success: {parse_result.success}")
        print(f"   Scene: {scene}")
        print(f"   Error: {getattr(parse_result, 'error', 'None')}")

        if scene is not None:
            print(f"   Scene type: {type(scene)}")
            print(f"   Scene length: {len(scene) if hasattr(scene, '__len__') else 'N/A'}")
            print(f"✅ parse_to_ir succeeded")
        else:
            print(f"❌ parse_to_ir returned None scene")

    except Exception as e:
        print(f"❌ Error in parse_to_ir test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()