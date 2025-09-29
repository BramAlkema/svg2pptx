#!/usr/bin/env python3
"""
Demo: Create a minimal PPTX file from SVG content.
"""

import sys
from pathlib import Path

# Add project root to path for proper imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pptx_minimal import svg_to_pptx

# Sample SVG content
sample_svg = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">
    <rect x="50" y="50" width="100" height="80" fill="blue" stroke="black" stroke-width="2"/>
    <circle cx="300" cy="100" r="50" fill="red" stroke="darkred" stroke-width="3"/>
    <text x="200" y="120" font-size="16" fill="black">Hello PPTX!</text>
</svg>'''

def main():
    print("Creating minimal PPTX file from SVG...")

    output_path = "demo_output.pptx"

    try:
        svg_to_pptx(sample_svg, output_path)
        print(f"✅ PPTX file created: {output_path}")

        # Check file size
        file_size = Path(output_path).stat().st_size
        print(f"📊 File size: {file_size:,} bytes")

        print("📋 Generated PPTX contains:")
        print("   - Dynamic aspect ratio based on SVG viewBox (400x200 → 2:1)")
        print("   - Minimal OOXML structure")
        print("   - Placeholder DrawingML content")
        print("   - Ready to open in PowerPoint!")

    except Exception as e:
        print(f"❌ Error creating PPTX: {e}")
        return 1

    return 0

if __name__ == "__main__":
    exit(main())