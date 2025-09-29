#!/usr/bin/env python3
"""
Debug star bounding box position and size
"""

import sys
sys.path.insert(0, 'src')

from lxml import etree as ET
from src.svg2drawingml import SVGToDrawingMLConverter
from core.services.conversion_services import ConversionServices
import re

# Read the star SVG
with open('debug_star.svg', 'r') as f:
    svg_content = f.read()

print("=== Star SVG Analysis ===")
print("SVG content:")
print(svg_content)

# Parse the path coordinates manually
path_match = re.search(r'd="([^"]*)"', svg_content)
if path_match:
    path_data = path_match.group(1)
    print(f"\nPath data: {path_data}")

    # Extract coordinates from path
    coords = re.findall(r'(\d+(?:\.\d+)?),(\d+(?:\.\d+)?)', path_data)
    if coords:
        x_coords = [float(x) for x, y in coords]
        y_coords = [float(y) for x, y in coords]

        min_x, max_x = min(x_coords), max(x_coords)
        min_y, max_y = min(y_coords), max(y_coords)

        print(f"\nSVG coordinates:")
        print(f"  X range: {min_x} to {max_x} (width: {max_x - min_x})")
        print(f"  Y range: {min_y} to {max_y} (height: {max_y - min_y})")
        print(f"  Bounding box: ({min_x}, {min_y}) to ({max_x}, {max_y})")

print("\n=== Conversion Analysis ===")

# Convert and analyze the output
services = ConversionServices.create_default()
converter = SVGToDrawingMLConverter(services=services)

try:
    result = converter.convert(svg_content)

    # Extract position and size from DrawingML
    off_match = re.search(r'<a:off x="([^"]*)" y="([^"]*)"/>', result)
    ext_match = re.search(r'<a:ext cx="([^"]*)" cy="([^"]*)"/>', result)

    if off_match and ext_match:
        emu_x = int(off_match.group(1))
        emu_y = int(off_match.group(2))
        emu_width = int(ext_match.group(1))
        emu_height = int(ext_match.group(2))

        print(f"DrawingML bounding box:")
        print(f"  Position: ({emu_x}, {emu_y}) EMU")
        print(f"  Size: {emu_width} × {emu_height} EMU")
        print(f"  Position in inches: ({emu_x/914400:.3f}\", {emu_y/914400:.3f}\")")
        print(f"  Size in inches: {emu_width/914400:.3f}\" × {emu_height/914400:.3f}\"")
        print(f"  Slide dimensions: 10\" × 7.5\"")

        # Calculate relative position on slide
        rel_x = (emu_x / 9144000) * 100
        rel_y = (emu_y / 6858000) * 100
        rel_w = (emu_width / 9144000) * 100
        rel_h = (emu_height / 6858000) * 100

        print(f"  Relative position on slide:")
        print(f"    X: {rel_x:.1f}% from left")
        print(f"    Y: {rel_y:.1f}% from top")
        print(f"    Width: {rel_w:.1f}% of slide width")
        print(f"    Height: {rel_h:.1f}% of slide height")

    # Look for path coordinates
    path_match = re.search(r'<a:pathLst>.*?</a:pathLst>', result, re.DOTALL)
    if path_match:
        path_section = path_match.group(0)
        print(f"\nPath coordinates section:")
        print(path_section)

        # Extract specific coordinate values
        pt_matches = re.findall(r'<a:pt x="([^"]*)" y="([^"]*)"/>', path_section)
        if pt_matches:
            print(f"\nPath point coordinates:")
            for i, (x, y) in enumerate(pt_matches[:5]):  # First 5 points
                print(f"  Point {i+1}: ({x}, {y})")
    else:
        print(f"\nDrawingML output (first 1000 chars):")
        print(result[:1000] + "..." if len(result) > 1000 else result)

except Exception as e:
    print(f"❌ Conversion failed: {e}")
    import traceback
    traceback.print_exc()