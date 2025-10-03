#!/usr/bin/env python3
"""
SVG2PPTX Generation Example
Demonstrates how to convert SVG to PowerPoint presentations
"""

from core.api import convert_svg_to_pptx

def main():
    print("🎯 SVG2PPTX Generation Example")
    print("=" * 40)

    # Example 1: Simple shapes
    simple_svg = """<svg width="300" height="200" xmlns="http://www.w3.org/2000/svg">
        <rect x="50" y="50" width="200" height="100" fill="#3498db" rx="10"/>
        <text x="150" y="110" text-anchor="middle" fill="white" font-size="18">
            Simple Example
        </text>
    </svg>"""

    print("📄 Converting simple SVG...")
    result = convert_svg_to_pptx(simple_svg, output_path="simple_example.pptx")
    print(f"✅ Result: {result.success}")
    print(f"📊 Time: {result.total_time_ms:.1f}ms")

    # Example 2: Complex shapes with gradients
    complex_svg = """<svg width="400" height="300" xmlns="http://www.w3.org/2000/svg">
        <defs>
            <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" style="stop-color:#ff6b6b;stop-opacity:1" />
                <stop offset="100%" style="stop-color:#4ecdc4;stop-opacity:1" />
            </linearGradient>
        </defs>

        <circle cx="100" cy="100" r="60" fill="url(#grad1)"/>
        <path d="M 50 200 L 200 150 L 350 200 L 300 250 L 100 250 Z"
              fill="#e74c3c" opacity="0.8"/>
        <text x="200" y="50" text-anchor="middle" font-size="24" fill="#2c3e50">
            Complex Example
        </text>
    </svg>"""

    print("\n📄 Converting complex SVG...")
    result = convert_svg_to_pptx(complex_svg, output_path="complex_example.pptx")
    print(f"✅ Result: {result.success}")
    print(f"📊 Time: {result.total_time_ms:.1f}ms")

    # Example 3: From file
    print("\n📄 You can also convert from files:")
    print("result = convert_svg_to_pptx('input.svg', output_path='output.pptx')")

    print("\n🎯 Key Features:")
    print("• Native PowerPoint shapes (not images)")
    print("• Editable text and shapes in PowerPoint")
    print("• Gradient and styling support")
    print("• Coordinate system transformation")
    print("• High-fidelity conversion")

    print(f"\n📁 Generated files:")
    print("• simple_example.pptx")
    print("• complex_example.pptx")

if __name__ == "__main__":
    main()