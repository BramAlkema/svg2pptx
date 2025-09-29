#!/usr/bin/env python3
"""
Test Content Normalization Integration

This script tests the complete content normalization pipeline to verify
it works end-to-end for off-slide content patterns.
"""

from src.viewbox.ctm_utils import create_root_context_with_viewport
from src.services.conversion_services import ConversionServices
from lxml import etree as ET
import numpy as np

def test_normalization_integration():
    """Test complete normalization integration pipeline."""

    print("=== Content Normalization Integration Test ===")

    # Create services
    services = ConversionServices.create_default()

    # Test case: Off-slide content that should be normalized
    svg_content = '''<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
      <rect x="500" y="400" width="100" height="100" fill="red"/>
      <circle cx="550" cy="450" r="25" fill="blue"/>
    </svg>'''

    svg_root = ET.fromstring(svg_content)

    print(f"SVG viewBox: {svg_root.get('viewBox')}")

    # Test the bounds and detection
    from src.viewbox.content_bounds import calculate_raw_content_bounds
    from src.transforms.matrix_composer import needs_normalise

    bounds = calculate_raw_content_bounds(svg_root)
    needs_norm = needs_normalise(svg_root)

    print(f"Content bounds: {bounds}")
    print(f"Needs normalization: {needs_norm}")

    # Test the full viewport context creation
    try:
        context = create_root_context_with_viewport(
            svg_root=svg_root,
            services=services,
            slide_w_emu=9144000,  # 10 inches
            slide_h_emu=6858000   # 7.5 inches
        )

        print(f"✅ Viewport context created successfully")
        print(f"Context has viewport matrix: {context.viewport_matrix is not None}")

        if context.viewport_matrix is not None:
            print("Viewport matrix:")
            print(context.viewport_matrix)

            # Test transformation of a point
            if needs_norm:
                # Test point at original off-slide location
                original_point = np.array([500, 400, 1])
                transformed_point = context.viewport_matrix @ original_point

                print(f"Original point [500, 400] transforms to:")
                print(f"[{transformed_point[0]:.2f}, {transformed_point[1]:.2f}]")

                # Check if point is now on-slide (within reasonable EMU bounds)
                slide_center_x = 9144000 / 2  # 5 inches
                slide_center_y = 6858000 / 2  # 3.75 inches

                if (abs(transformed_point[0]) < 9144000 and
                    abs(transformed_point[1]) < 6858000):
                    print("✅ Content successfully normalized to on-slide position")
                else:
                    print("❌ Content still off-slide after normalization")
            else:
                print("ℹ️ No normalization applied (content already on-slide)")

    except Exception as e:
        print(f"❌ Error creating viewport context: {e}")
        import traceback
        traceback.print_exc()

def test_no_normalization_case():
    """Test that normal content doesn't get unnecessarily normalized."""

    print("\n=== Normal Content Test (Should Not Normalize) ===")

    services = ConversionServices.create_default()

    # Normal SVG content within viewBox
    svg_content = '''<svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
      <rect x="50" y="50" width="100" height="100" fill="green"/>
    </svg>'''

    svg_root = ET.fromstring(svg_content)

    from src.transforms.matrix_composer import needs_normalise
    needs_norm = needs_normalise(svg_root)

    print(f"Normal content needs normalization: {needs_norm}")

    if not needs_norm:
        print("✅ Normal content correctly identified as not needing normalization")
    else:
        print("⚠️ Normal content incorrectly flagged for normalization")

    # Create context anyway to test it works
    try:
        context = create_root_context_with_viewport(svg_root=svg_root, services=services)
        print("✅ Normal content viewport context created successfully")
    except Exception as e:
        print(f"❌ Error with normal content: {e}")

if __name__ == "__main__":
    test_normalization_integration()
    test_no_normalization_case()
    print("\n=== Integration Test Complete ===")