#!/usr/bin/env python3
"""Debug what's actually being generated in the PPTX files."""

import sys
sys.path.append('.')

import zipfile
import tempfile
import os
from src.svg2pptx import convert_svg_to_pptx

def debug_actual_pptx_content():
    """Debug the actual XML content being generated."""

    # Test the basic shapes SVG that should have our fixes
    test_svg = '''<svg width="400" height="300" xmlns="http://www.w3.org/2000/svg">
        <rect x="10" y="10" width="100" height="80" fill="lightblue" stroke="blue" stroke-width="2"/>
        <circle cx="200" cy="50" r="40" fill="lightgreen" stroke="green" stroke-width="2"/>
        <ellipse cx="350" cy="50" rx="40" ry="25" fill="lightcoral" stroke="red" stroke-width="2"/>
        <line x1="10" y1="150" x2="390" y2="150" stroke="purple" stroke-width="3"/>
        <text x="200" y="200" text-anchor="middle" font-family="Arial" font-size="18" fill="darkblue">
            Basic Shapes Test
        </text>
    </svg>'''

    print("=== DEBUGGING ACTUAL PPTX OUTPUT ===")

    try:
        # Convert to PPTX
        fd, output_path = tempfile.mkstemp(suffix='.pptx')
        os.close(fd)

        result_path = convert_svg_to_pptx(
            svg_input=test_svg,
            output_path=output_path,
            slide_width=10.0,
            slide_height=7.5
        )

        print(f"✅ PPTX created: {result_path}")
        print(f"📁 File size: {os.path.getsize(result_path)} bytes")

        # Extract and examine the PPTX content
        with zipfile.ZipFile(result_path, 'r') as pptx_zip:
            # List all files in the PPTX
            print(f"\n📂 PPTX Contents ({len(pptx_zip.filelist)} files):")
            for file_info in pptx_zip.filelist:
                print(f"  - {file_info.filename} ({file_info.file_size} bytes)")

            # Read the main slide content
            slide_files = [f for f in pptx_zip.namelist() if 'slide1.xml' in f or 'slides/slide1.xml' in f]
            if slide_files:
                slide_file = slide_files[0]
                print(f"\n📄 Reading slide content: {slide_file}")

                slide_content = pptx_zip.read(slide_file).decode('utf-8')
                print(f"📏 Slide XML length: {len(slide_content)} characters")

                # Check for our specific fixes
                print(f"\n🔍 CHECKING FOR APPLIED FIXES:")

                # 1. Check for text elements and font sizes
                if '<p:sp>' in slide_content:
                    text_shapes = slide_content.count('<p:sp>')
                    print(f"✅ Found {text_shapes} shape elements")
                else:
                    print(f"❌ No shape elements found")

                # 2. Check for font size scaling (should be >1800 if our 1.5x fix worked)
                import re
                font_sizes = re.findall(r'sz="(\d+)"', slide_content)
                if font_sizes:
                    print(f"📝 Font sizes found: {font_sizes}")
                    max_font_size = max(int(size) for size in font_sizes)
                    if max_font_size > 1800:
                        print(f"✅ Font scaling applied: {max_font_size} units (>{max_font_size/100}pt)")
                    else:
                        print(f"❌ Font scaling NOT applied: {max_font_size} units ({max_font_size/100}pt)")
                else:
                    print(f"❌ No font sizes found in XML")

                # 3. Check for CSS colors like "lightblue", "lightgreen"
                color_values = re.findall(r'val="([A-Fa-f0-9]{6})"', slide_content)
                if color_values:
                    print(f"🎨 Color values found: {color_values}")
                    # lightblue should be ADD8E6, lightgreen should be 90EE90
                    expected_colors = ['ADD8E6', 'add8e6', '90EE90', '90ee90']
                    found_expected = any(color.upper() in [c.upper() for c in color_values] for color in expected_colors)
                    if found_expected:
                        print(f"✅ CSS colors applied correctly")
                    else:
                        print(f"❌ CSS colors NOT applied - expected lightblue/lightgreen")
                else:
                    print(f"❌ No color values found")

                # 4. Check for stroke width scaling (should be >6000 for stroke-width="3")
                stroke_widths = re.findall(r'w="(\d+)"', slide_content)
                if stroke_widths:
                    print(f"📏 Stroke widths found: {stroke_widths}")
                    max_stroke = max(int(w) for w in stroke_widths)
                    if max_stroke > 40000:  # 3px * 2 scaling * ~6800 EMU/px
                        print(f"✅ Stroke scaling applied: {max_stroke} EMU")
                    else:
                        print(f"❌ Stroke scaling NOT applied: {max_stroke} EMU")
                else:
                    print(f"❌ No stroke widths found")

                # 5. Check if there's any DrawingML content at all
                if '<a:' in slide_content:
                    drawingml_elements = len(re.findall(r'<a:\w+', slide_content))
                    print(f"🎨 DrawingML elements found: {drawingml_elements}")
                else:
                    print(f"❌ No DrawingML content found - this is the problem!")

                # Show a sample of the slide content
                print(f"\n📄 SLIDE XML SAMPLE (first 500 chars):")
                print(slide_content[:500] + "..." if len(slide_content) > 500 else slide_content)

            else:
                print(f"❌ No slide1.xml found in PPTX")

        # Clean up
        os.unlink(result_path)

    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_actual_pptx_content()