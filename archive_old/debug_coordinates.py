#!/usr/bin/env python3
"""
Debug coordinate transformation from SVG to EMU
"""

import sys
sys.path.insert(0, 'src')

from src.svg2drawingml import SVGToDrawingMLConverter

def debug_coordinates():
    converter = SVGToDrawingMLConverter()

    # Test polygon coordinates: M300,200 in a 400x300 viewBox
    print("=== COORDINATE TRANSFORMATION ANALYSIS ===")
    print("SVG ViewBox: 0 0 400 300")
    print("Polygon coordinates: x=300-355, y=180-235")
    print("Expected position: right side, middle-bottom of slide")

    # Calculate what the EMU coordinates should be
    viewbox_width = 400
    viewbox_height = 300
    slide_width_emu = 9144000  # 10 inches
    slide_height_emu = 6858000  # 7.5 inches

    # Scale factors
    scale_x = slide_width_emu / viewbox_width
    scale_y = slide_height_emu / viewbox_height

    print(f"\nScale factors:")
    print(f"X scale: {scale_x} EMU per SVG unit")
    print(f"Y scale: {scale_y} EMU per SVG unit")

    # Test polygon bounds
    svg_x_min, svg_x_max = 290, 355
    svg_y_min, svg_y_max = 180, 235

    emu_x_min = svg_x_min * scale_x
    emu_x_max = svg_x_max * scale_x
    emu_y_min = svg_y_min * scale_y
    emu_y_max = svg_y_max * scale_y

    print(f"\nPolygon EMU coordinates:")
    print(f"X range: {emu_x_min} - {emu_x_max} EMU")
    print(f"Y range: {emu_y_min} - {emu_y_max} EMU")

    # Convert to inches for human understanding
    emu_per_inch = 914400
    print(f"\nPolygon position in inches:")
    print(f"X range: {emu_x_min/emu_per_inch:.2f} - {emu_x_max/emu_per_inch:.2f} inches")
    print(f"Y range: {emu_y_min/emu_per_inch:.2f} - {emu_y_max/emu_per_inch:.2f} inches")
    print(f"Slide size: {slide_width_emu/emu_per_inch:.1f} × {slide_height_emu/emu_per_inch:.1f} inches")

    # Check if coordinates are within slide bounds
    if emu_x_max <= slide_width_emu and emu_y_max <= slide_height_emu:
        print("\n✅ Coordinates are within slide bounds")
    else:
        print("\n❌ Coordinates exceed slide bounds!")
        if emu_x_max > slide_width_emu:
            print(f"   X exceeds by: {(emu_x_max - slide_width_emu)/emu_per_inch:.2f} inches")
        if emu_y_max > slide_height_emu:
            print(f"   Y exceeds by: {(emu_y_max - slide_height_emu)/emu_per_inch:.2f} inches")

if __name__ == "__main__":
    debug_coordinates()