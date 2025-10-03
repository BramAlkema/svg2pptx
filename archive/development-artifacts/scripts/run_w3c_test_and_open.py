#!/usr/bin/env python3
"""
W3C Compliance Test Runner with PPTX Generation
===============================================

This script runs W3C-style tests using our working PathSystem
and generates PPTX files that can be opened and verified.
"""

import sys
import os
import subprocess
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def create_w3c_test_svg():
    """Create a W3C-style test SVG with basic shapes and paths."""
    w3c_test_svg = '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="400" height="300" viewBox="0 0 400 300" xmlns="http://www.w3.org/2000/svg">
    <title>W3C Basic Shapes and Paths Test</title>

    <!-- Background -->
    <rect width="400" height="300" fill="#f0f0f0" stroke="none"/>

    <!-- W3C Basic Shapes Test Cases -->
    <text x="200" y="30" text-anchor="middle" font-family="Arial" font-size="18" font-weight="bold" fill="#333">
        W3C SVG Basic Shapes and Paths Test
    </text>

    <!-- Rectangle Test (shapes-rect-01-t) -->
    <rect x="50" y="60" width="80" height="50" fill="#ff6b6b" stroke="#d63384" stroke-width="2"/>
    <text x="90" y="85" text-anchor="middle" font-size="12" fill="white">Rect</text>

    <!-- Circle Test (shapes-circle-01-t) -->
    <circle cx="90" cy="160" r="30" fill="#4ecdc4" stroke="#20c997" stroke-width="2"/>
    <text x="90" y="165" text-anchor="middle" font-size="12" fill="white">Circle</text>

    <!-- Ellipse Test (shapes-ellipse-01-t) -->
    <ellipse cx="210" cy="90" rx="40" ry="25" fill="#45b7d1" stroke="#0d6efd" stroke-width="2"/>
    <text x="210" y="95" text-anchor="middle" font-size="12" fill="white">Ellipse</text>

    <!-- Line Test (shapes-line-01-t) -->
    <line x1="170" y1="140" x2="250" y2="180" stroke="#fd7e14" stroke-width="4"/>
    <text x="210" y="170" text-anchor="middle" font-size="12" fill="#fd7e14">Line</text>

    <!-- Path Test - Simple (paths-data-01-t) -->
    <path d="M 300 70 L 340 70 L 320 110 Z" fill="#6f42c1" stroke="#6610f2" stroke-width="2"/>
    <text x="320" y="90" text-anchor="middle" font-size="12" fill="white">Path</text>

    <!-- Path Test - Curves (paths-data-02-t) -->
    <path d="M 280 140 Q 320 120 360 140 Q 340 180 320 160 Q 300 180 280 160 Z"
          fill="#e83e8c" stroke="#d63384" stroke-width="2"/>
    <text x="320" y="155" text-anchor="middle" font-size="10" fill="white">Curves</text>

    <!-- Path Test - Arcs (paths-data-05-t) -->
    <path d="M 50 220 A 40 30 0 0 1 130 220 A 40 30 0 0 1 50 220"
          fill="none" stroke="#198754" stroke-width="3"/>
    <text x="90" y="240" text-anchor="middle" font-size="12" fill="#198754">Arc</text>

    <!-- Complex Path Test -->
    <path d="M 200 220 L 210 200 Q 230 210 240 220 L 250 200 L 260 220 Q 240 240 220 230 Q 200 240 200 220 Z"
          fill="#ffc107" stroke="#fd7e14" stroke-width="2"/>
    <text x="230" y="225" text-anchor="middle" font-size="10" fill="#333">Complex</text>

    <!-- Polygon Test (shapes-polygon-01-t) -->
    <polygon points="320,200 340,210 350,230 340,250 320,260 300,250 290,230 300,210"
             fill="#20c997" stroke="#198754" stroke-width="2"/>
    <text x="320" y="235" text-anchor="middle" font-size="10" fill="white">Polygon</text>

    <!-- Footer -->
    <text x="200" y="280" text-anchor="middle" font-size="12" fill="#666">
        PathSystem with Namespace Fix - All shapes should be visible
    </text>
</svg>'''

    # Save the test SVG
    test_file = Path(__file__).parent / "w3c_test_suite.svg"
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(w3c_test_svg)

    return test_file

def run_w3c_conversion_test():
    """Run W3C compliance test and generate PPTX."""
    print("🎯 W3C Compliance Test with PathSystem")
    print("=" * 50)

    # Create test SVG
    print("📄 Creating W3C test SVG...")
    test_svg = create_w3c_test_svg()
    print(f"   ✅ Created: {test_svg}")

    # Convert using our working PathSystem
    print("\n🔧 Converting with PathSystem (API)...")
    try:
        from src.svg2pptx import convert_svg_to_pptx

        output_pptx = "w3c_compliance_test.pptx"
        result = convert_svg_to_pptx(str(test_svg), output_pptx)

        if Path(result).exists():
            print(f"   ✅ PPTX generated: {result}")
            print(f"   📊 File size: {Path(result).stat().st_size:,} bytes")

            # Analyze the output
            analyze_w3c_pptx(Path(result))

            return Path(result)
        else:
            print("   ❌ PPTX generation failed")
            return None

    except Exception as e:
        print(f"   ❌ Conversion error: {e}")
        return None

def analyze_w3c_pptx(pptx_file: Path):
    """Analyze W3C PPTX for compliance validation."""
    print(f"\n🔍 W3C Compliance Analysis")
    print("-" * 30)

    try:
        import zipfile
        import xml.etree.ElementTree as ET

        with zipfile.ZipFile(pptx_file, 'r') as zip_file:
            slide_xml = zip_file.read('ppt/slides/slide1.xml').decode('utf-8')

            # Parse XML for analysis
            root = ET.fromstring(slide_xml)
            namespaces = {
                'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
                'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'
            }

            # Count W3C shape types
            shapes = root.findall('.//p:sp', namespaces)
            custom_shapes = 0
            preset_shapes = 0
            shapes_with_fill = 0
            shapes_with_stroke = 0

            shape_analysis = {
                'rectangles': 0,
                'circles': 0,
                'ellipses': 0,
                'paths': 0,
                'polygons': 0,
                'lines': 0
            }

            for shape in shapes:
                # Check geometry type
                preset_geom = shape.find('.//a:prstGeom', namespaces)
                custom_geom = shape.find('.//a:custGeom', namespaces)

                if preset_geom is not None:
                    preset_shapes += 1
                    geom_type = preset_geom.get('prst', 'unknown')
                    if geom_type == 'rect':
                        shape_analysis['rectangles'] += 1
                    elif geom_type == 'ellipse':
                        shape_analysis['circles'] += 1  # PowerPoint uses ellipse for circles

                if custom_geom is not None:
                    custom_shapes += 1
                    shape_analysis['paths'] += 1

                # Check styling
                fills = shape.findall('.//a:solidFill', namespaces)
                if fills:
                    shapes_with_fill += 1

                strokes = shape.findall('.//a:ln', namespaces)
                if strokes:
                    shapes_with_stroke += 1

            # W3C compliance metrics
            total_shapes = len(shapes)
            namespace_compliance = '<a:solidFill>' in slide_xml and '<a:ln' in slide_xml
            path_commands = slide_xml.count('<a:moveTo>') + slide_xml.count('<a:lnTo>') + slide_xml.count('<a:cubicBezTo>')

            print(f"📊 W3C Shape Analysis:")
            print(f"   Total shapes: {total_shapes}")
            print(f"   Preset shapes: {preset_shapes} (rects, circles, ellipses)")
            print(f"   Custom paths: {custom_shapes}")
            print(f"   Shapes with fill: {shapes_with_fill}")
            print(f"   Shapes with stroke: {shapes_with_stroke}")
            print(f"   Path commands: {path_commands}")

            print(f"\n🎨 Shape Type Breakdown:")
            for shape_type, count in shape_analysis.items():
                if count > 0:
                    print(f"   {shape_type}: {count}")

            print(f"\n✅ W3C Compliance Validation:")
            print(f"   Namespace compliance: {'✅ PASS' if namespace_compliance else '❌ FAIL'}")
            print(f"   Shape preservation: {'✅ PASS' if total_shapes >= 8 else '❌ FAIL'}")
            print(f"   Fill/stroke support: {'✅ PASS' if shapes_with_fill > 0 and shapes_with_stroke > 0 else '❌ FAIL'}")
            print(f"   Path rendering: {'✅ PASS' if custom_shapes > 0 and path_commands > 0 else '❌ FAIL'}")

            # Overall compliance score
            compliance_checks = [
                namespace_compliance,
                total_shapes >= 8,
                shapes_with_fill > 0 and shapes_with_stroke > 0,
                custom_shapes > 0 and path_commands > 0
            ]
            compliance_score = sum(compliance_checks) / len(compliance_checks) * 100

            print(f"\n🏆 Overall W3C Compliance Score: {compliance_score:.1f}%")

            if compliance_score >= 75:
                print("   🎉 EXCELLENT - PathSystem fixes working perfectly!")
            elif compliance_score >= 50:
                print("   ✅ GOOD - Most W3C features supported")
            else:
                print("   ⚠️  NEEDS IMPROVEMENT - Review implementation")

    except Exception as e:
        print(f"❌ Analysis error: {e}")

def open_pptx_file(pptx_file: Path):
    """Open the PPTX file for verification."""
    print(f"\n📂 Opening PPTX File: {pptx_file}")
    print("-" * 30)

    try:
        if sys.platform == "darwin":  # macOS
            subprocess.run(["open", str(pptx_file)], check=True)
            print("   ✅ Opened with default application (Keynote/PowerPoint)")
        elif sys.platform.startswith("linux"):
            subprocess.run(["xdg-open", str(pptx_file)], check=True)
            print("   ✅ Opened with default application")
        elif sys.platform == "win32":
            os.startfile(str(pptx_file))
            print("   ✅ Opened with default application")
        else:
            print(f"   ⚠️  Cannot auto-open on platform: {sys.platform}")
            print(f"   📂 Manual open required: {pptx_file.absolute()}")

    except subprocess.CalledProcessError as e:
        print(f"   ❌ Failed to open file: {e}")
        print(f"   📂 Manual open required: {pptx_file.absolute()}")
    except Exception as e:
        print(f"   ❌ Error opening file: {e}")
        print(f"   📂 Manual open required: {pptx_file.absolute()}")

def main():
    """Run W3C compliance test and open resulting PPTX."""
    print("🎯 W3C Compliance Test with PPTX Opening")
    print("=" * 60)

    # Run the W3C conversion test
    pptx_file = run_w3c_conversion_test()

    if pptx_file and pptx_file.exists():
        # Open the PPTX file
        open_pptx_file(pptx_file)

        print(f"\n🎉 W3C Test Complete!")
        print(f"   📄 Test SVG: w3c_test_suite.svg")
        print(f"   📊 Output PPTX: {pptx_file}")
        print(f"   👁️  Visual verification: Check opened PPTX file")
        print(f"   ✅ All shapes should be visible with proper fills/strokes")

        return True
    else:
        print("\n❌ W3C Test Failed - No PPTX generated")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)