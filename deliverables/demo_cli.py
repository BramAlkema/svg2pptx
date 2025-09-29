#!/usr/bin/env python3
"""
SVG2PPTX Path System Demonstration CLI

This script demonstrates the complete SVG-to-PowerPoint conversion pipeline
using the new PathSystem architecture with comprehensive output and reporting.
"""

import sys
import time
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.svg2pptx import convert_svg_to_pptx
from core.paths import create_path_system

def main():
    print("=" * 80)
    print("🚀 SVG2PPTX Path System Demonstration")
    print("=" * 80)
    print()

    # Input and output paths
    svg_file = Path(__file__).parent / "test_complex_paths.svg"
    output_file = Path(__file__).parent / "demo_output.pptx"

    print(f"📁 Input SVG: {svg_file}")
    print(f"📁 Output PPTX: {output_file}")
    print()

    # Verify input exists
    if not svg_file.exists():
        print(f"❌ Error: Input file {svg_file} does not exist!")
        return 1

    print("🔍 Analyzing SVG file...")
    with open(svg_file, 'r') as f:
        svg_content = f.read()

    # Count paths in SVG
    path_count = svg_content.count('<path')
    print(f"   - Found {path_count} path elements")
    print(f"   - File size: {len(svg_content):,} bytes")
    print()

    # Test PathSystem directly first
    print("🔧 Testing PathSystem components...")
    try:
        # Create path system
        path_system = create_path_system(800, 600, (0, 0, 800, 600))
        print("   ✅ PathSystem created successfully")

        # Test a sample path
        test_path = "M 100 100 C 100 50 200 50 200 100 A 50 25 0 0 1 300 100 Z"
        result = path_system.process_path(test_path)
        print(f"   ✅ Sample path processed: {len(result.commands)} commands")
        print(f"   ✅ Generated XML: {len(result.path_xml)} bytes")
        print()

    except Exception as e:
        print(f"   ❌ PathSystem test failed: {e}")
        return 1

    # Perform conversion
    print("🔄 Converting SVG to PowerPoint...")
    start_time = time.time()

    try:
        # Convert using the main converter
        result = convert_svg_to_pptx(
            str(svg_file),
            str(output_file)
        )

        conversion_time = time.time() - start_time

        print(f"   ✅ Conversion completed in {conversion_time:.2f} seconds")
        print(f"   ✅ Output file: {output_file}")
        print(f"   ✅ File size: {output_file.stat().st_size:,} bytes")
        print()

    except Exception as e:
        print(f"   ❌ Conversion failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Generate statistics
    print("📊 Conversion Statistics:")
    print(f"   - Processing time: {conversion_time:.3f} seconds")
    print(f"   - Input size: {len(svg_content):,} bytes")
    print(f"   - Output size: {output_file.stat().st_size:,} bytes")
    print(f"   - Compression ratio: {output_file.stat().st_size / len(svg_content):.1f}x")
    print(f"   - Paths processed: {path_count}")
    print(f"   - Processing rate: {path_count / conversion_time:.1f} paths/second")
    print()

    # Generate metadata
    metadata = {
        "conversion_time": conversion_time,
        "timestamp": datetime.now().isoformat(),
        "input_file": str(svg_file),
        "output_file": str(output_file),
        "input_size": len(svg_content),
        "output_size": output_file.stat().st_size,
        "path_count": path_count,
        "path_system_version": "2.0.0"
    }

    # Save metadata
    metadata_file = Path(__file__).parent / "demo_metadata.json"
    import json
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)

    print(f"📋 Metadata saved to: {metadata_file}")
    print()

    print("🎉 Demonstration completed successfully!")
    print(f"🔗 Open {output_file} in PowerPoint to view the results")
    print()
    print("=" * 80)

    return 0

if __name__ == "__main__":
    sys.exit(main())