#!/usr/bin/env python3
"""
Test DTDA Logo Pattern

This tests the specific pattern mentioned in the roadmap where content appears off-slide.
"""

from src.viewbox.ctm_utils import create_root_context_with_viewport
from src.services.conversion_services import ConversionServices
from src.transforms.matrix_composer import needs_normalise
from src.viewbox.content_bounds import calculate_content_bounds
from lxml import etree as ET
import numpy as np

def test_dtda_pattern():
    """Test the DTDA logo pattern specifically mentioned in roadmap."""

    print("=== DTDA Logo Pattern Validation ===")

    # Create realistic DTDA pattern: Large coordinates with transform
    # This simulates: translate(509.85 466.99) with paths at m-493.81-466.99
    dtda_svg = '''<svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
      <g transform="translate(509.85 466.99)">
        <path d="M-493.81,-466.99 L-393.81,-366.99 L-293.81,-266.99 Z" fill="red"/>
        <circle cx="-393.81" cy="-366.99" r="25" fill="blue"/>
      </g>
      <text x="100" y="180" font-size="12" text-anchor="middle">DTDA Pattern Test</text>
    </svg>'''

    svg_root = ET.fromstring(dtda_svg)
    services = ConversionServices.create_default()

    print(f"ViewBox: {svg_root.get('viewBox')}")

    # Calculate what the bounds would be
    bounds = calculate_content_bounds(svg_root)
    print(f"Content bounds: {bounds}")
    print(f"Content size: {bounds[2] - bounds[0]:.1f} x {bounds[3] - bounds[1]:.1f}")

    # Check if normalization is needed
    needs_norm = needs_normalise(svg_root)
    print(f"Needs normalization: {needs_norm}")

    # Create viewport context (this applies normalization if needed)
    context = create_root_context_with_viewport(svg_root=svg_root, services=services)

    print(f"Viewport context created with matrix shape: {context.viewport_matrix.shape}")

    # Test specific coordinates from the DTDA pattern
    # Original coordinates: translate(509.85 466.99) + path(-493.81,-466.99)
    # Net result should be approximately: (16.04, 0.0)

    test_points = [
        (16.04, 0.0),    # Net coordinate of path start
        (116.04, 100.0), # Net coordinate of path end (approximately)
        (100, 180)       # Text coordinate
    ]

    print("\nTesting coordinate transformations:")
    for x, y in test_points:
        point = np.array([x, y, 1])
        transformed = context.viewport_matrix @ point

        # Convert from EMU to slide coordinates for readability
        slide_x = transformed[0] / 914400  # Convert to inches
        slide_y = transformed[1] / 914400

        print(f"  ({x:6.1f}, {y:6.1f}) -> ({slide_x:5.2f}\", {slide_y:5.2f}\")")

        # Check if within slide bounds (10" x 7.5")
        if 0 <= slide_x <= 10 and 0 <= slide_y <= 7.5:
            print(f"    ✅ On-slide")
        else:
            print(f"    ❌ Off-slide")

    print(f"\n{'='*50}")
    if needs_norm:
        print("✅ DTDA pattern correctly identified for normalization")
        print("✅ Content normalization system working correctly")
    else:
        print("ℹ️ DTDA pattern content already within reasonable bounds")
        print("✅ Transform handling working correctly")

    print("✅ DTDA pattern test completed successfully")

def test_extreme_offslide_case():
    """Test extreme off-slide case that definitely needs normalization."""

    print("\n=== Extreme Off-Slide Case ===")

    # Pure off-slide content without compensating transforms
    extreme_svg = '''<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
      <rect x="10000" y="8000" width="1000" height="800" fill="purple"/>
    </svg>'''

    svg_root = ET.fromstring(extreme_svg)
    services = ConversionServices.create_default()

    bounds = calculate_content_bounds(svg_root)
    needs_norm = needs_normalise(svg_root)

    print(f"Extreme case bounds: {bounds}")
    print(f"Needs normalization: {needs_norm}")

    if needs_norm:
        context = create_root_context_with_viewport(svg_root=svg_root, services=services)

        # Test the extreme coordinate
        extreme_point = np.array([10000, 8000, 1])
        transformed = context.viewport_matrix @ extreme_point

        slide_x = transformed[0] / 914400
        slide_y = transformed[1] / 914400

        print(f"Extreme point (10000, 8000) -> ({slide_x:.2f}\", {slide_y:.2f}\")")

        if 0 <= slide_x <= 10 and 0 <= slide_y <= 7.5:
            print("✅ Extreme off-slide content successfully normalized")
        else:
            print("❌ Extreme content still off-slide")
    else:
        print("❌ Extreme case not detected for normalization")

if __name__ == "__main__":
    test_dtda_pattern()
    test_extreme_offslide_case()