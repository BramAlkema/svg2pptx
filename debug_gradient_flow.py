#!/usr/bin/env python3
"""Debug gradient flow from parser to mapper"""

from core.parse.parser import SVGParser
from core.pipeline.converter import CleanSlateConverter

# Simple SVG with mesh gradient
svg = '''<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">
  <defs>
    <meshgradient id="testMesh">
      <meshrow>
        <meshpatch>
          <stop path="c 50,0 50,50 0,50" stop-color="#ff0000"/>
          <stop path="c 0,50 -50,50 -50,0" stop-color="#00ff00"/>
          <stop path="c -50,0 -50,-50 0,-50" stop-color="#0000ff"/>
          <stop path="c 0,-50 50,-50 50,0" stop-color="#ffff00"/>
        </meshpatch>
      </meshrow>
    </meshgradient>
  </defs>
  <rect x="50" y="50" width="100" height="100" fill="url(#testMesh)"/>
</svg>'''

# Parse to IR
parser = SVGParser()
scene, result = parser.parse_to_ir(svg)

print(f"✅ Parsed {len(scene)} elements")

for i, elem in enumerate(scene):
    print(f"\nElement {i}: {type(elem).__name__}")
    if hasattr(elem, 'fill'):
        print(f"  Fill: {type(elem.fill).__name__ if elem.fill else 'None'}")
        if elem.fill:
            print(f"  Fill details: {elem.fill}")

# Now run through converter
print("\n" + "="*70)
print("Running full conversion...")
converter = CleanSlateConverter()
result = converter.convert_string(svg)
print(f"✅ Conversion complete: {len(result.output_data)} bytes")
