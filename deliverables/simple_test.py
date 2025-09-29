#!/usr/bin/env python3
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.svg2drawingml import SVGToDrawingMLConverter

# Test simple path with explicit stroke
simple_svg = '''<svg width="200" height="200" xmlns="http://www.w3.org/2000/svg">
    <path d="M 50 50 L 150 50 L 150 150 Z" stroke="#ff0000" stroke-width="3" fill="none"/>
</svg>'''

converter = SVGToDrawingMLConverter()
result = converter.convert(simple_svg)
print("Conversion result length:", len(result))
print("Contains stroke:", "<a:ln" in result)
print("Contains solid fill in stroke:", "solidFill" in result)