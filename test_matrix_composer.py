#!/usr/bin/env python3
"""
Test matrix composer with DTDA logo
"""

import sys
from pathlib import Path
from lxml import etree as ET
import numpy as np

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.transforms.matrix_composer import (
    viewport_matrix, parse_viewbox, parse_preserve_aspect_ratio,
    parse_transform, element_ctm, needs_normalise, normalise_content_matrix
)

def test_dtda_matrix_composer():
    """Test matrix composer with real DTDA logo."""
    print("🧪 Testing Matrix Composer with DTDA Logo")
    print("=" * 50)

    # Load DTDA logo
    try:
        with open('dtda_logo.svg', 'rb') as f:
            svg_content = f.read()

        svg_root = ET.fromstring(svg_content)

        # Test viewBox parsing
        vb_x, vb_y, vb_w, vb_h = parse_viewbox(svg_root)
        print(f"✅ ViewBox: ({vb_x}, {vb_y}, {vb_w}, {vb_h})")

        # Test preserveAspectRatio
        alignment, meet_slice = parse_preserve_aspect_ratio(svg_root)
        print(f"✅ PreserveAspectRatio: {alignment} {meet_slice}")

        # Test viewport matrix creation
        slide_w_emu = 9144000  # 10 inches
        slide_h_emu = 6858000  # 7.5 inches

        matrix = viewport_matrix(svg_root, slide_w_emu, slide_h_emu)
        print(f"✅ Viewport Matrix:")
        print(f"   Scale: ({matrix[0,0]:.1f}, {matrix[1,1]:.1f})")
        print(f"   Translate: ({matrix[0,2]:.1f}, {matrix[1,2]:.1f})")

        # Test group transform
        g_element = svg_root.find('.//{http://www.w3.org/2000/svg}g')
        if g_element is not None:
            group_transform = g_element.get('transform', '')
            group_matrix = parse_transform(group_transform)
            print(f"✅ Group Transform: {group_transform}")
            print(f"   Matrix: translate({group_matrix[0,2]}, {group_matrix[1,2]})")

            # Test CTM composition
            ctm = element_ctm(g_element, None, matrix)
            print(f"✅ Group CTM:")
            print(f"   Final scale: ({ctm[0,0]:.1f}, {ctm[1,1]:.1f})")
            print(f"   Final translate: ({ctm[0,2]:.1f}, {ctm[1,2]:.1f})")

        # Test normalization heuristic
        needs_norm = needs_normalise(svg_root)
        print(f"✅ Needs normalization: {needs_norm}")

        if needs_norm:
            # This would be where we apply content bounds normalization
            print("   → Large coordinate space detected - normalization recommended")

        # Test coordinate transformation
        test_point = np.array([16, 0, 1])  # Approximate content location
        transformed = matrix @ test_point
        print(f"✅ Test point (16, 0) → ({transformed[0]:.0f}, {transformed[1]:.0f}) EMU")
        print(f"   In inches: ({transformed[0]/914400:.2f}\", {transformed[1]/914400:.2f}\")")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_matrix_composition_performance():
    """Test matrix composition performance."""
    print("\n⚡ Performance Test")
    print("-" * 20)

    import time

    # Create test matrices
    viewport = np.array([[9144, 0, 0], [0, 9144, 0], [0, 0, 1]], dtype=float)
    local = np.array([[1, 0, 100], [0, 1, 200], [0, 0, 1]], dtype=float)

    start_time = time.time()

    # Perform 10000 matrix multiplications
    for _ in range(10000):
        result = viewport @ local

    end_time = time.time()
    elapsed = end_time - start_time

    print(f"✅ 10,000 matrix multiplications: {elapsed*1000:.1f}ms")
    print(f"   Average per operation: {elapsed*1000000/10000:.1f}μs")

    # Should be very fast
    assert elapsed < 0.1, f"Matrix operations too slow: {elapsed:.3f}s"

if __name__ == "__main__":
    success = test_dtda_matrix_composer()
    if success:
        test_matrix_composition_performance()
        print("\n🎉 Matrix composer tests completed successfully!")
    else:
        print("\n❌ Matrix composer tests failed!")
        sys.exit(1)