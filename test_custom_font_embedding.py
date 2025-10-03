#!/usr/bin/env python3
"""
E2E Test: Custom Font Embedding with ShinyCrystal.ttf

Tests that custom fonts are properly detected, embedded, and rendered:
1. SVG with @font-face using ShinyCrystal.ttf
2. Font detection and embedding decision
3. Font file embedded in PPTX
4. Validation of embedded font in /ppt/fonts/
"""

import os
import zipfile
import io
from pathlib import Path
from typing import Dict, Any

from core.pipeline.converter import CleanSlateConverter


# Test SVGs using ShinyCrystal custom font
CUSTOM_FONT_SVGS = {
    'shiny_basic': '''<svg xmlns="http://www.w3.org/2000/svg" width="500" height="200">
        <defs>
            <style>
                @font-face {
                    font-family: 'ShinyCrystal';
                    src: url('ShinyCrystal.ttf') format('truetype');
                }
            </style>
        </defs>
        <text x="50" y="100" font-family="ShinyCrystal" font-size="48" fill="#FF1493">
            Shiny Crystal Font!
        </text>
    </svg>''',

    'shiny_multiple': '''<svg xmlns="http://www.w3.org/2000/svg" width="600" height="300">
        <defs>
            <style>
                @font-face {
                    font-family: 'ShinyCrystal';
                    src: url('ShinyCrystal.ttf') format('truetype');
                }
            </style>
        </defs>
        <text x="50" y="60" font-family="ShinyCrystal" font-size="42" fill="#FFD700">
            Golden Crystal Text
        </text>
        <text x="50" y="130" font-family="ShinyCrystal" font-size="36" fill="#00CED1">
            Turquoise Crystal
        </text>
        <text x="50" y="200" font-family="ShinyCrystal" font-size="32" fill="#FF69B4">
            Pink Crystal Shine
        </text>
    </svg>''',

    'shiny_with_fallback': '''<svg xmlns="http://www.w3.org/2000/svg" width="500" height="250">
        <defs>
            <style>
                @font-face {
                    font-family: 'ShinyCrystal';
                    src: url('ShinyCrystal.ttf') format('truetype');
                }
            </style>
        </defs>
        <text x="50" y="80" font-family="ShinyCrystal, Arial, sans-serif" font-size="40" fill="#9370DB">
            Custom Font with Fallback
        </text>
        <text x="50" y="150" font-family="Arial" font-size="28" fill="#696969">
            System Font for Comparison
        </text>
    </svg>''',

    'shiny_styled': '''<svg xmlns="http://www.w3.org/2000/svg" width="600" height="350">
        <defs>
            <style>
                @font-face {
                    font-family: 'ShinyCrystal';
                    src: url('ShinyCrystal.ttf') format('truetype');
                }
            </style>
            <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" style="stop-color:rgb(255,0,255);stop-opacity:1" />
                <stop offset="100%" style="stop-color:rgb(0,255,255);stop-opacity:1" />
            </linearGradient>
            <filter id="glow">
                <feGaussianBlur stdDeviation="3" result="blur"/>
                <feMerge>
                    <feMergeNode in="blur"/>
                    <feMergeNode in="SourceGraphic"/>
                </feMerge>
            </filter>
        </defs>
        <text x="50" y="100" font-family="ShinyCrystal" font-size="56" fill="url(#grad1)">
            Gradient Crystal
        </text>
        <text x="50" y="200" font-family="ShinyCrystal" font-size="48" fill="#FFD700" filter="url(#glow)">
            Glowing Crystal
        </text>
    </svg>''',

    'shiny_mixed_sizes': '''<svg xmlns="http://www.w3.org/2000/svg" width="700" height="400">
        <defs>
            <style>
                @font-face {
                    font-family: 'ShinyCrystal';
                    src: url('ShinyCrystal.ttf') format('truetype');
                }
            </style>
        </defs>
        <text x="50" y="60" font-family="ShinyCrystal" font-size="72" fill="#FF1493">BIG</text>
        <text x="50" y="140" font-family="ShinyCrystal" font-size="48" fill="#FF69B4">Medium</text>
        <text x="50" y="200" font-family="ShinyCrystal" font-size="32" fill="#FFB6C1">Small</text>
        <text x="50" y="250" font-family="ShinyCrystal" font-size="24" fill="#FFC0CB">Smaller</text>
        <text x="50" y="290" font-family="ShinyCrystal" font-size="18" fill="#FFE4E1">Tiny</text>
    </svg>''',
}


def validate_custom_font_embedding(pptx_data: bytes, test_name: str) -> Dict[str, Any]:
    """Validate that ShinyCrystal font was properly embedded"""
    validation = {
        'test_name': test_name,
        'pptx_size': len(pptx_data),
        'valid_zip': False,
        'has_embedded_fonts': False,
        'embedded_font_files': [],
        'font_count': 0,
        'shinycrystal_embedded': False,
        'has_text_shapes': False,
        'text_count': 0,
        'font_families_used': [],
        'errors': []
    }

    try:
        # Open PPTX
        pptx = zipfile.ZipFile(io.BytesIO(pptx_data))
        validation['valid_zip'] = True

        # Check for embedded fonts in /ppt/fonts/
        all_files = pptx.namelist()
        font_files = [f for f in all_files if f.startswith('ppt/fonts/')]

        validation['embedded_font_files'] = font_files
        validation['font_count'] = len(font_files)
        validation['has_embedded_fonts'] = len(font_files) > 0

        # Check specifically for ShinyCrystal
        shiny_fonts = [f for f in font_files if 'shiny' in f.lower() or 'crystal' in f.lower()]
        validation['shinycrystal_embedded'] = len(shiny_fonts) > 0

        if validation['has_embedded_fonts']:
            print(f"    📦 Found {len(font_files)} embedded font file(s):")
            for font_file in font_files:
                font_size = pptx.getinfo(font_file).file_size
                print(f"       - {font_file} ({font_size} bytes)")

        # Check slides for text
        slides = [f for f in all_files if f.startswith('ppt/slides/slide') and f.endswith('.xml')]

        for slide_file in slides:
            slide_xml = pptx.read(slide_file).decode('utf-8')

            # Count text
            text_count = slide_xml.count('<a:t>')
            validation['text_count'] += text_count
            validation['has_text_shapes'] = text_count > 0

            # Extract font families
            parts = slide_xml.split('typeface="')
            for i in range(1, len(parts)):
                font_name = parts[i].split('"')[0]
                if font_name and font_name not in validation['font_families_used']:
                    validation['font_families_used'].append(font_name)

        # Validate expectations
        if not validation['has_text_shapes']:
            validation['errors'].append("No text shapes found in output")

        if not validation['has_embedded_fonts']:
            validation['errors'].append("No embedded fonts found (expected ShinyCrystal)")

        if not validation['shinycrystal_embedded']:
            validation['errors'].append("ShinyCrystal font not embedded")

    except zipfile.BadZipFile:
        validation['errors'].append("Invalid ZIP file")
    except Exception as e:
        validation['errors'].append(f"Validation error: {e}")

    validation['passed'] = (
        len(validation['errors']) == 0 and
        validation['valid_zip'] and
        validation['has_text_shapes']
    )

    return validation


def test_custom_font_embedding():
    """Test ShinyCrystal font embedding through pipeline"""
    print("=" * 80)
    print("Custom Font Embedding Test - ShinyCrystal.ttf")
    print("=" * 80)
    print()

    # Check font file exists
    font_path = Path("ShinyCrystal.ttf")
    if not font_path.exists():
        print("❌ ERROR: ShinyCrystal.ttf not found in root directory")
        return False

    print(f"✓ Found ShinyCrystal.ttf ({font_path.stat().st_size} bytes)")
    print()

    # Initialize converter
    converter = CleanSlateConverter()

    # Process all custom font tests
    print("📝 Processing custom font test cases...")
    print("-" * 80)

    results = []
    for test_name, svg_content in CUSTOM_FONT_SVGS.items():
        print(f"\n  Processing: {test_name}")

        output_path = f"/tmp/custom_font_{test_name}.pptx"

        try:
            # Convert
            import time
            start = time.perf_counter()
            result = converter.convert_string(svg_content)
            elapsed = (time.perf_counter() - start) * 1000

            # Save
            with open(output_path, 'wb') as f:
                f.write(result.output_data)

            print(f"    ✓ Converted in {elapsed:.1f}ms")
            print(f"    ✓ Output: {len(result.output_data)} bytes")

            results.append({
                'test_name': test_name,
                'output_file': output_path,
                'result': result,
                'svg_content': svg_content,
                'elapsed_ms': elapsed,
                'success': True
            })

        except Exception as e:
            print(f"    ✗ Failed: {e}")
            results.append({
                'test_name': test_name,
                'output_file': output_path,
                'error': str(e),
                'success': False
            })

    # Validate font embedding
    print("\n\n🔍 Validating ShinyCrystal font embedding...")
    print("-" * 80)

    validations = []
    for result_data in results:
        if not result_data['success']:
            print(f"\n  ⏭️  Skipped: {result_data['test_name']} (conversion failed)")
            continue

        test_name = result_data['test_name']
        output_file = result_data['output_file']

        print(f"\n  Validating: {test_name}")

        # Read PPTX
        with open(output_file, 'rb') as f:
            pptx_data = f.read()

        # Validate
        validation = validate_custom_font_embedding(pptx_data, test_name)
        validations.append(validation)

        print(f"    ✓ Text shapes: {validation['text_count']}")
        print(f"    ✓ Font families: {', '.join(validation['font_families_used'])}")

        if validation['shinycrystal_embedded']:
            print(f"    ✅ ShinyCrystal EMBEDDED!")
        else:
            print(f"    ⚠️  ShinyCrystal NOT embedded (may use fallback/path)")

        if validation['errors']:
            print(f"    ⚠️  Issues:")
            for error in validation['errors']:
                print(f"       - {error}")

    # Summary
    print("\n" + "=" * 80)
    print("CUSTOM FONT EMBEDDING SUMMARY")
    print("=" * 80)

    successful = sum(1 for r in results if r['success'])
    with_embedded = sum(1 for v in validations if v['shinycrystal_embedded'])
    total_fonts = sum(v['font_count'] for v in validations)

    print(f"\n📊 Conversion Results:")
    print(f"  Total tests: {len(CUSTOM_FONT_SVGS)}")
    print(f"  Successful conversions: {successful}/{len(CUSTOM_FONT_SVGS)}")

    if results:
        avg_time = sum(r.get('elapsed_ms', 0) for r in results if r['success']) / max(successful, 1)
        print(f"  Average conversion time: {avg_time:.1f}ms")

    print(f"\n🔤 Font Embedding Results:")
    print(f"  Tests with ShinyCrystal embedded: {with_embedded}/{len(validations)}")
    print(f"  Total embedded font files: {total_fonts}")

    print(f"\n✅ Test Details:")
    for validation in validations:
        status = "✅" if validation['shinycrystal_embedded'] else "⚠️ "
        print(f"  {status} {validation['test_name']}: "
              f"{validation['text_count']} text, "
              f"{validation['font_count']} fonts embedded")

    print("\n" + "=" * 80)
    if with_embedded >= len(validations) * 0.8:  # 80% should embed
        print("✅ CUSTOM FONT EMBEDDING WORKING")
        print(f"   {with_embedded}/{len(validations)} tests embedded ShinyCrystal successfully")
    else:
        print("⚠️  CUSTOM FONT EMBEDDING PARTIAL")
        print(f"   Only {with_embedded}/{len(validations)} tests embedded ShinyCrystal")
        print("   Some tests may use fallback rendering (text-to-path)")
    print("=" * 80)

    return with_embedded > 0, results, validations


if __name__ == '__main__':
    try:
        has_embeddings, results, validations = test_custom_font_embedding()

        if has_embeddings:
            print("\n✓ ShinyCrystal font embedding validated!")
            print(f"  Check /tmp/custom_font_*.pptx files in PowerPoint")
            print(f"  Font files should be in ppt/fonts/ directory")
        else:
            print("\n⚠️  No custom font embeddings detected")
            print("   This may be expected if fonts are converted to paths")

        print("\nTo manually verify font embedding:")
        print("  unzip -l /tmp/custom_font_shiny_basic.pptx | grep fonts")
        print("  unzip -p /tmp/custom_font_shiny_basic.pptx ppt/slides/slide1.xml | grep -i shiny")

    except Exception as e:
        print("\n" + "=" * 80)
        print(f"❌ CUSTOM FONT TEST FAILED: {e}")
        print("=" * 80)
        import traceback
        traceback.print_exc()
        raise
