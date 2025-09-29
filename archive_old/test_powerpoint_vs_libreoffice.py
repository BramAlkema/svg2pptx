#!/usr/bin/env python3
"""
Test to compare PowerPoint vs LibreOffice rendering of our PPTX files.

This helps us understand if the visual issues are:
1. In our conversion pipeline (XML generation)
2. In LibreOffice rendering (screenshot capture)
3. In PowerPoint-specific compatibility
"""

import sys
sys.path.append('.')

from src.svg2pptx import convert_svg_to_pptx
import tempfile
import os
import subprocess
import asyncio
from playwright.async_api import async_playwright

def create_test_pptx():
    """Create a simple test PPTX with obvious visual elements."""

    # Very simple, obvious SVG that should definitely be visible
    test_svg = '''<svg width="400" height="300" xmlns="http://www.w3.org/2000/svg">
        <!-- Large red rectangle that should be impossible to miss -->
        <rect x="50" y="50" width="300" height="200" fill="red" stroke="black" stroke-width="5"/>

        <!-- Large blue circle -->
        <circle cx="200" cy="150" r="80" fill="blue" stroke="yellow" stroke-width="3"/>

        <!-- Large text -->
        <text x="200" y="280" text-anchor="middle" font-family="Arial" font-size="24" fill="white">
            TEST VISIBILITY
        </text>
    </svg>'''

    print("🎯 Creating test PPTX with highly visible elements...")

    # Convert to PPTX
    fd, output_path = tempfile.mkstemp(suffix='.pptx')
    os.close(fd)

    result_path = convert_svg_to_pptx(
        svg_input=test_svg,
        output_path=output_path,
        slide_width=10.0,
        slide_height=7.5
    )

    # Copy to permanent location
    test_file = 'powerpoint_vs_libreoffice_test.pptx'
    import shutil
    shutil.copy(result_path, test_file)
    os.unlink(result_path)

    print(f"✅ Test PPTX created: {test_file}")
    print(f"📁 File size: {os.path.getsize(test_file)} bytes")

    return test_file

async def capture_libreoffice_screenshot(pptx_path):
    """Capture screenshot using LibreOffice (our current method)."""

    print("\n📊 Testing LibreOffice rendering...")

    try:
        # Convert to PDF first
        pdf_path = pptx_path.replace('.pptx', '_libreoffice.pdf')

        libreoffice_cmd = [
            '/Applications/LibreOffice.app/Contents/MacOS/soffice',
            '--headless',
            '--convert-to', 'pdf',
            '--outdir', os.path.dirname(pdf_path),
            pptx_path
        ]

        result = subprocess.run(libreoffice_cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0 and os.path.exists(pdf_path):
            print("✅ LibreOffice PDF conversion successful")

            # Screenshot the PDF
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=False)
                page = await browser.new_page()
                await page.goto(f'file://{pdf_path}')
                await page.wait_for_timeout(3000)  # Wait for rendering

                screenshot_path = pptx_path.replace('.pptx', '_libreoffice_screenshot.png')
                await page.screenshot(path=screenshot_path, full_page=True)
                print(f"📸 LibreOffice screenshot: {screenshot_path}")

                await browser.close()
                os.unlink(pdf_path)  # Clean up PDF

                return screenshot_path
        else:
            print(f"❌ LibreOffice conversion failed: {result.stderr}")
            return None

    except Exception as e:
        print(f"❌ LibreOffice screenshot failed: {e}")
        return None

def test_powerpoint_compatibility():
    """Test if the PPTX opens correctly in PowerPoint."""

    print("\n🔍 Testing PowerPoint compatibility...")

    test_file = create_test_pptx()

    # Check if we can at least open it
    print("📋 Please manually:")
    print(f"   1. Open {test_file} in Microsoft PowerPoint")
    print("   2. Check if the red rectangle, blue circle, and white text are visible")
    print("   3. Compare with LibreOffice screenshot below")

    return test_file

async def main():
    """Run the comparison test."""

    print("🔍 POWERPOINT vs LIBREOFFICE RENDERING TEST")
    print("=" * 55)

    # Create test file
    test_file = create_test_pptx()

    # Capture LibreOffice rendering
    libreoffice_screenshot = await capture_libreoffice_screenshot(test_file)

    # Instructions for PowerPoint testing
    print("\n🎯 MANUAL POWERPOINT TEST:")
    print("=" * 35)
    print(f"1. Open this file in PowerPoint: {test_file}")
    print("2. Take a screenshot or note what you see")
    print("3. Compare with LibreOffice screenshot:")
    if libreoffice_screenshot:
        print(f"   {libreoffice_screenshot}")

    print("\n📋 WHAT TO LOOK FOR:")
    print("- Large red rectangle (should cover most of slide)")
    print("- Blue circle with yellow border in center")
    print("- White text 'TEST VISIBILITY' at bottom")
    print("- If PowerPoint shows these but LibreOffice doesn't, we have a rendering issue")
    print("- If both show the same thing, our conversion is working correctly")

    print("\n🎯 EXPECTED RESULTS:")
    print("✅ GOOD: Both PowerPoint and LibreOffice show the same visual elements")
    print("❌ BAD: PowerPoint shows elements that LibreOffice screenshots miss")
    print("❌ BAD: Neither shows the elements (conversion pipeline issue)")

    # Open the file for manual inspection
    print(f"\n📂 Opening {test_file} for manual inspection...")
    os.system(f'open "{test_file}"')

if __name__ == "__main__":
    asyncio.run(main())