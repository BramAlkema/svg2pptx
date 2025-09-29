#!/usr/bin/env python3
"""
Test the centralized coordinate transformation fix
"""

import sys
sys.path.insert(0, 'src')

from src.svg2drawingml import ViewportMapping
import numpy as np

# Create a mock viewport mapping
mock_viewport = np.array([(1.0, 1.0, 0.0, 0.0, 400, 300, 0, 0, False)],
                        dtype=[('scale_x', 'f8'), ('scale_y', 'f8'),
                               ('translate_x', 'f8'), ('translate_y', 'f8'),
                               ('viewport_width', 'i4'), ('viewport_height', 'i4'),
                               ('content_width', 'i4'), ('content_height', 'i4'),
                               ('clip_needed', 'bool')])[0]

viewport_mapping = ViewportMapping(mock_viewport)

# Test with simple rectangle coordinates: (50,50) to (150,150)
svg_coords = [(50, 50), (150, 50), (150, 150), (50, 150)]

emu_x, emu_y, emu_width, emu_height, relative_coords = viewport_mapping.calculate_shape_bounding_box_and_relative_coords(svg_coords)

print("SVG Rectangle coordinates:", svg_coords)
print("Expected: Rectangle from (50,50) to (150,150)")
print()
print(f"Bounding box EMU: position=({emu_x}, {emu_y}), size=({emu_width}, {emu_height})")
print("Relative coordinates for DrawingML:")
for i, (rel_x, rel_y) in enumerate(relative_coords):
    print(f"  Point {i+1}: ({rel_x}, {rel_y})")

print()
print("Expected relative coordinates:")
print("  Point 1: (0, 0)      # Top-left corner")
print("  Point 2: (100000, 0) # Top-right corner")
print("  Point 3: (100000, 100000) # Bottom-right corner")
print("  Point 4: (0, 100000) # Bottom-left corner")