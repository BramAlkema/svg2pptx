#!/usr/bin/env python3
"""Test font sizing with units system integration."""

import sys
sys.path.append('.')

from lxml import etree as ET
from core.units import unit

# Test the units system directly
print("=== Units System Font Size Testing ===")

test_sizes = ["24pt", "18pt", "12pt", "36pt", "8pt"]

for size in test_sizes:
    drawingml_size = unit(size).to_drawingml_font_size()
    back_to_points = drawingml_size / 2
    print(f"{size} → DrawingML sz={drawingml_size} → {back_to_points}pt")

print("\n=== Expected Results ===")
print("24pt → sz=48 → 24pt ✓")
print("18pt → sz=36 → 18pt ✓")
print("12pt → sz=24 → 12pt ✓")
print("36pt → sz=72 → 36pt ✓")
print("8pt → sz=16 → 8pt ✓")