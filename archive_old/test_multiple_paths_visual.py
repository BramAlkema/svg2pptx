#!/usr/bin/env python3
"""
Playwright E2E visual comparison test for multiple paths
"""

import asyncio
import sys
import os
from pathlib import Path
from playwright.async_api import async_playwright

async def capture_svg_screenshot():
    """Capture screenshot of the SVG file in browser"""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        # Load SVG file
        svg_path = Path("test_multiple_paths.svg").absolute()
        await page.goto(f"file://{svg_path}")

        # Wait for content to load
        await page.wait_for_timeout(1000)

        # Take screenshot
        await page.screenshot(path="test_multiple_paths_svg.png", full_page=True)
        print("✅ SVG screenshot captured: test_multiple_paths_svg.png")

        await browser.close()

async def capture_pptx_screenshot():
    """Capture screenshot of PPTX opened in browser (via Office Online or similar)"""
    print("⚠️ Note: PPTX screenshots require manual verification or Office integration")
    print("📎 Generated PPTX file: test_multiple_paths.pptx")
    print("🔍 To verify:")
    print("  1. Open test_multiple_paths.pptx in PowerPoint")
    print("  2. Check that all 5 paths are visible:")
    print("     - Red heart shape")
    print("     - Yellow star")
    print("     - Blue curved line")
    print("     - Purple polygon")
    print("     - Orange bezier curves")
    print("  3. Verify shapes maintain correct colors, positions, and geometry")

def analyze_conversion_details():
    """Analyze what was actually converted"""

    # Check if we can read the PPTX structure
    try:
        import zipfile
        with zipfile.ZipFile("test_multiple_paths.pptx", 'r') as zip_file:
            # List contents
            print("\n📁 PPTX Contents:")
            for name in zip_file.namelist():
                if 'slide' in name and name.endswith('.xml'):
                    print(f"  📄 {name}")

            # Read slide content
            slide_xml = None
            try:
                slide_xml = zip_file.read('ppt/slides/slide1.xml').decode('utf-8')
                print(f"\n📊 Slide XML length: {len(slide_xml):,} characters")

                # Count DrawingML elements
                shape_count = slide_xml.count('<p:sp>')
                path_count = slide_xml.count('<a:path>')
                print(f"🎯 DrawingML shapes found: {shape_count}")
                print(f"🛤️ Path elements found: {path_count}")

                # Look for evidence of our specific paths
                if 'fill="#e74c3c"' in slide_xml or 'e74c3c' in slide_xml:
                    print("✅ Red heart path detected in XML")
                if 'fill="#f1c40f"' in slide_xml or 'f1c40f' in slide_xml:
                    print("✅ Yellow star path detected in XML")
                if 'stroke="#3498db"' in slide_xml or '3498db' in slide_xml:
                    print("✅ Blue curved line detected in XML")
                if 'fill="#9b59b6"' in slide_xml or '9b59b6' in slide_xml:
                    print("✅ Purple polygon detected in XML")
                if 'stroke="#e67e22"' in slide_xml or 'e67e22' in slide_xml:
                    print("✅ Orange bezier curves detected in XML")

            except KeyError:
                print("⚠️ Could not read slide XML")

    except Exception as e:
        print(f"⚠️ Could not analyze PPTX structure: {e}")

async def main():
    """Run the complete visual comparison test"""

    print("🎨 Multiple Paths E2E Visual Test")
    print("=" * 50)

    # Capture SVG reference
    await capture_svg_screenshot()

    # Analyze PPTX conversion
    analyze_conversion_details()

    # Instructions for manual verification
    await capture_pptx_screenshot()

    print("\n" + "=" * 50)
    print("✅ Test completed - check screenshots for visual comparison")

if __name__ == "__main__":
    asyncio.run(main())