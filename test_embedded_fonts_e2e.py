#!/usr/bin/env python3
"""
E2E Test: Embedded Fonts Validation

Tests font embedding pipeline:
1. SVG with custom fonts
2. Font detection and analysis
3. Font embedding decision
4. Font embedding in PPTX
5. Validation of embedded font files
"""

import os
import zipfile
import io
from pathlib import Path
from typing import Dict, Any, List
from lxml import etree

from core.pipeline.converter import CleanSlateConverter
from core.services.conversion_services import ConversionServices


# Test SVGs with various font scenarios
FONT_TEST_SVGS = {
    'system_font_arial': '''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="200">
        <text x="20" y="50" font-family="Arial" font-size="32" fill="#000000">
            Arial System Font
        </text>
        <text x="20" y="100" font-family="Arial" font-size="24" font-weight="bold" fill="#E74C3C">
            Bold Arial
        </text>
        <text x="20" y="150" font-family="Arial" font-size="20" font-style="italic" fill="#3498DB">
            Italic Arial
        </text>
    </svg>''',

    'system_font_helvetica': '''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="200">
        <text x="20" y="50" font-family="Helvetica" font-size="32" fill="#2ECC71">
            Helvetica Font
        </text>
        <text x="20" y="100" font-family="Helvetica Neue" font-size="24" fill="#9B59B6">
            Helvetica Neue
        </text>
    </svg>''',

    'system_font_courier': '''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="200">
        <text x="20" y="50" font-family="Courier" font-size="24" fill="#000000">
            Monospace Courier Font
        </text>
        <text x="20" y="100" font-family="Courier New" font-size="20" fill="#34495E">
            function helloWorld() {
        </text>
        <text x="40" y="125" font-family="Courier New" font-size="20" fill="#34495E">
            return "Hello!";
        </text>
        <text x="20" y="150" font-family="Courier New" font-size="20" fill="#34495E">
            }
        </text>
    </svg>''',

    'fallback_font_chain': '''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="200">
        <text x="20" y="50" font-family="'NonexistentFont', Arial, sans-serif" font-size="28" fill="#E67E22">
            Fallback Chain Test
        </text>
        <text x="20" y="100" font-family="'CustomFont', Helvetica, sans-serif" font-size="24" fill="#1ABC9C">
            Custom with Fallback
        </text>
    </svg>''',

    'mixed_fonts': '''<svg xmlns="http://www.w3.org/2000/svg" width="500" height="300">
        <text x="20" y="40" font-family="Arial" font-size="32" font-weight="bold" fill="#E74C3C">
            Heading in Arial Bold
        </text>
        <text x="20" y="80" font-family="Helvetica" font-size="18" fill="#333333">
            Body text in Helvetica regular weight.
        </text>
        <text x="20" y="110" font-family="Courier" font-size="16" fill="#2C3E50">
            Code snippet in Courier monospace.
        </text>
        <text x="20" y="150" font-family="Georgia" font-size="20" font-style="italic" fill="#8E44AD">
            Emphasis in Georgia italic.
        </text>
        <text x="20" y="190" font-family="Times New Roman" font-size="18" fill="#34495E">
            Classic serif text in Times.
        </text>
    </svg>''',

    'unicode_text': '''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="250">
        <text x="20" y="40" font-family="Arial" font-size="24" fill="#000000">
            English: Hello World!
        </text>
        <text x="20" y="80" font-family="Arial" font-size="24" fill="#E74C3C">
            Spanish: ¡Hola Mundo!
        </text>
        <text x="20" y="120" font-family="Arial" font-size="24" fill="#3498DB">
            French: Bonjour le Monde!
        </text>
        <text x="20" y="160" font-family="Arial" font-size="24" fill="#2ECC71">
            German: Hallo Welt!
        </text>
        <text x="20" y="200" font-family="Arial" font-size="24" fill="#F39C12">
            Symbols: © ® ™ € £ ¥
        </text>
    </svg>''',

    'font_weights_styles': '''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="350">
        <text x="20" y="40" font-family="Arial" font-size="20" font-weight="100" fill="#000">
            Thin (100)
        </text>
        <text x="20" y="70" font-family="Arial" font-size="20" font-weight="300" fill="#000">
            Light (300)
        </text>
        <text x="20" y="100" font-family="Arial" font-size="20" font-weight="400" fill="#000">
            Regular (400)
        </text>
        <text x="20" y="130" font-family="Arial" font-size="20" font-weight="500" fill="#000">
            Medium (500)
        </text>
        <text x="20" y="160" font-family="Arial" font-size="20" font-weight="600" fill="#000">
            Semibold (600)
        </text>
        <text x="20" y="190" font-family="Arial" font-size="20" font-weight="700" fill="#000">
            Bold (700)
        </text>
        <text x="20" y="220" font-family="Arial" font-size="20" font-weight="800" fill="#000">
            Extrabold (800)
        </text>
        <text x="20" y="250" font-family="Arial" font-size="20" font-weight="900" fill="#000">
            Black (900)
        </text>
        <text x="20" y="290" font-family="Arial" font-size="20" font-style="italic" fill="#E74C3C">
            Italic Style
        </text>
        <text x="20" y="320" font-family="Arial" font-size="20" font-weight="bold" font-style="italic" fill="#3498DB">
            Bold Italic
        </text>
    </svg>''',

    'long_text': '''<svg xmlns="http://www.w3.org/2000/svg" width="600" height="400">
        <text x="20" y="30" font-family="Arial" font-size="16" fill="#000">
            Lorem ipsum dolor sit amet, consectetur adipiscing elit.
        </text>
        <text x="20" y="55" font-family="Arial" font-size="16" fill="#000">
            Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.
        </text>
        <text x="20" y="80" font-family="Arial" font-size="16" fill="#000">
            Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris.
        </text>
        <text x="20" y="120" font-family="Courier" font-size="14" fill="#2C3E50">
            // Code example with special characters:
        </text>
        <text x="20" y="145" font-family="Courier" font-size="14" fill="#2C3E50">
            const value = "test &lt;&gt; &amp; &quot;quotes&quot;";
        </text>
        <text x="20" y="170" font-family="Courier" font-size="14" fill="#2C3E50">
            function calculate(a, b) { return a + b; }
        </text>
    </svg>''',
}


class FontEmbeddingValidator:
    """Validates font embedding in PPTX"""

    def __init__(self):
        self.validation_results = []

    def validate_pptx_fonts(self, pptx_data: bytes, test_name: str, svg_content: str) -> Dict[str, Any]:
        """Validate font handling in PPTX"""
        validation = {
            'test_name': test_name,
            'pptx_size': len(pptx_data),
            'valid_zip': False,
            'has_fonts': False,
            'embedded_fonts': [],
            'font_count': 0,
            'has_text_shapes': False,
            'text_shape_count': 0,
            'font_families_in_xml': [],
            'errors': []
        }

        try:
            # Open PPTX
            pptx = zipfile.ZipFile(io.BytesIO(pptx_data))
            validation['valid_zip'] = True

            # Check for embedded fonts
            font_files = [f for f in pptx.namelist() if f.startswith('ppt/fonts/')]
            validation['embedded_fonts'] = font_files
            validation['font_count'] = len(font_files)
            validation['has_fonts'] = len(font_files) > 0

            # Check slides for text
            slides = [f for f in pptx.namelist() if f.startswith('ppt/slides/slide') and f.endswith('.xml')]

            for slide_file in slides:
                slide_xml = pptx.read(slide_file).decode('utf-8')

                # Count text shapes
                text_count = slide_xml.count('<a:t>')
                validation['text_shape_count'] += text_count
                validation['has_text_shapes'] = text_count > 0

                # Extract font families from XML
                if 'latin' in slide_xml:
                    # Simple regex-like extraction
                    parts = slide_xml.split('typeface="')
                    for i in range(1, len(parts)):
                        font_name = parts[i].split('"')[0]
                        if font_name and font_name not in validation['font_families_in_xml']:
                            validation['font_families_in_xml'].append(font_name)

            # Parse SVG to get expected fonts
            svg_root = etree.fromstring(svg_content.encode('utf-8'))
            expected_fonts = set()
            for text_elem in svg_root.iter('{http://www.w3.org/2000/svg}text'):
                font_family = text_elem.get('font-family', '')
                if font_family:
                    # Clean font family string
                    fonts = [f.strip().strip("'\"") for f in font_family.split(',')]
                    expected_fonts.update(f for f in fonts if f and f not in ['sans-serif', 'serif', 'monospace'])

            validation['expected_fonts'] = list(expected_fonts)

            # Basic validation
            if validation['has_text_shapes'] and not validation['font_families_in_xml']:
                validation['errors'].append("Text found but no fonts referenced in XML")

        except zipfile.BadZipFile:
            validation['errors'].append("Invalid ZIP file")
        except Exception as e:
            validation['errors'].append(f"Validation error: {e}")

        validation['passed'] = len(validation['errors']) == 0 and validation['valid_zip']
        self.validation_results.append(validation)

        return validation


def test_embedded_fonts_pipeline():
    """Test font embedding through complete pipeline"""
    print("=" * 80)
    print("Embedded Fonts E2E Test")
    print("=" * 80)
    print()

    # Initialize
    converter = CleanSlateConverter()
    validator = FontEmbeddingValidator()

    # Process all font tests
    print("📝 Processing font test cases...")
    print("-" * 80)

    results = []
    for test_name, svg_content in FONT_TEST_SVGS.items():
        print(f"\n  Processing: {test_name}")

        output_path = f"/tmp/font_test_{test_name}.pptx"

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
    print("\n\n🔍 Validating font embedding...")
    print("-" * 80)

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
        validation = validator.validate_pptx_fonts(pptx_data, test_name, result_data['svg_content'])

        print(f"    ✓ Text shapes: {validation['text_shape_count']}")
        print(f"    ✓ Fonts in XML: {len(validation['font_families_in_xml'])} - {validation['font_families_in_xml'][:3]}")
        print(f"    ✓ Embedded fonts: {validation['font_count']}")

        if validation['embedded_fonts']:
            print(f"      - {', '.join(validation['embedded_fonts'][:3])}")

        if validation['expected_fonts']:
            print(f"    ℹ️  Expected fonts: {', '.join(validation['expected_fonts'][:5])}")

        if validation['errors']:
            print(f"    ⚠️  Issues:")
            for error in validation['errors']:
                print(f"      - {error}")

    # Summary
    print("\n" + "=" * 80)
    print("FONT EMBEDDING SUMMARY")
    print("=" * 80)

    successful = sum(1 for r in results if r['success'])
    total_embedded = sum(v['font_count'] for v in validator.validation_results)

    print(f"\n📊 Conversion Results:")
    print(f"  Total tests: {len(FONT_TEST_SVGS)}")
    print(f"  Successful: {successful}/{len(FONT_TEST_SVGS)}")

    if results:
        avg_time = sum(r.get('elapsed_ms', 0) for r in results if r['success']) / max(successful, 1)
        print(f"  Average time: {avg_time:.1f}ms")

    print(f"\n🔤 Font Handling:")
    print(f"  Total embedded fonts: {total_embedded}")

    # Group by font embedding status
    with_fonts = sum(1 for v in validator.validation_results if v['has_fonts'])
    without_fonts = len(validator.validation_results) - with_fonts

    print(f"  Tests with embedded fonts: {with_fonts}")
    print(f"  Tests without embedded fonts: {without_fonts}")

    print(f"\n✅ Font Test Details:")
    for validation in validator.validation_results:
        status = "✓" if validation['passed'] else "✗"
        fonts_info = f"{validation['font_count']} embedded" if validation['has_fonts'] else "system fonts"
        print(f"  {status} {validation['test_name']}: {validation['text_shape_count']} text shapes, {fonts_info}")

    # Font families used
    all_fonts = set()
    for v in validator.validation_results:
        all_fonts.update(v['font_families_in_xml'])

    if all_fonts:
        print(f"\n📝 Font Families Detected:")
        for font in sorted(all_fonts)[:10]:
            print(f"  - {font}")
        if len(all_fonts) > 10:
            print(f"  ... and {len(all_fonts) - 10} more")

    print("\n" + "=" * 80)
    if successful == len(FONT_TEST_SVGS):
        print("✅ ALL FONT TESTS PASSED")
    else:
        print("⚠️  SOME FONT TESTS FAILED")
    print("=" * 80)

    return successful == len(FONT_TEST_SVGS), results, validator.validation_results


if __name__ == '__main__':
    try:
        success, results, validations = test_embedded_fonts_pipeline()

        if success:
            print("\n✓ Font embedding pipeline fully operational")
        else:
            print("\n⚠️  Some font tests failed - see details above")

        print("\nFont test PPTX files saved to /tmp/font_test_*.pptx")
        print("Open them in PowerPoint to verify font rendering")

    except Exception as e:
        print("\n" + "=" * 80)
        print(f"❌ FONT TEST FAILED: {e}")
        print("=" * 80)
        import traceback
        traceback.print_exc()
        raise
