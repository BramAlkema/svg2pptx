#!/usr/bin/env python3
"""Test single gradient conversion."""

import sys
sys.path.append('.')

from src.svg2pptx import convert_svg_to_pptx
import tempfile
import os

def test_gradient():
    """Test gradient conversion specifically."""

    gradient_svg = '''<svg width="400" height="300" xmlns="http://www.w3.org/2000/svg">
        <defs>
            <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" style="stop-color:rgb(255,255,0);stop-opacity:1" />
                <stop offset="100%" style="stop-color:rgb(255,0,0);stop-opacity:1" />
            </linearGradient>
        </defs>
        <rect x="10" y="10" width="180" height="120" fill="url(#grad1)" stroke="black"/>
    </svg>'''

    print("Testing gradient conversion...")

    try:
        # Create temporary output
        fd, output_path = tempfile.mkstemp(suffix='.pptx')
        os.close(fd)

        # Convert
        result_path = convert_svg_to_pptx(
            svg_input=gradient_svg,
            output_path=output_path,
            slide_width=10.0,
            slide_height=7.5
        )

        print(f"✅ Conversion successful: {result_path}")
        print(f"📁 File size: {os.path.getsize(result_path)} bytes")

        # Clean up
        os.unlink(result_path)

    except Exception as e:
        print(f"❌ Conversion failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_gradient()