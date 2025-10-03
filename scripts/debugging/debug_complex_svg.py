#!/usr/bin/env python3
"""
Debug script for complex SVG features that cause E2E failure.
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

def debug_complex_svg_issue():
    """Debug the complex SVG that's failing in E2E tests."""

    # Exact SVG content from failing test
    complex_svg_content = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
     viewBox="0 0 400 300" width="400" height="300">
    <defs>
        <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" style="stop-color:rgb(255,255,0);stop-opacity:1" />
            <stop offset="100%" style="stop-color:rgb(255,0,0);stop-opacity:1" />
        </linearGradient>
        <pattern id="pattern1" patternUnits="userSpaceOnUse" width="20" height="20">
            <rect width="10" height="10" fill="blue"/>
            <rect x="10" y="10" width="10" height="10" fill="blue"/>
        </pattern>
    </defs>

    <!-- Basic shapes -->
    <rect x="10" y="10" width="100" height="60" fill="url(#grad1)" stroke="black" stroke-width="2"/>
    <circle cx="200" cy="50" r="40" fill="url(#pattern1)"/>
    <ellipse cx="320" cy="50" rx="60" ry="30" fill="green" opacity="0.7"/>

    <!-- Paths -->
    <path d="M 50 150 Q 100 100 150 150 T 250 150" stroke="purple" stroke-width="3" fill="none"/>
    <path d="M 20 200 L 50 180 L 80 200 Z" fill="orange"/>

    <!-- Text with transformations -->
    <g transform="translate(50, 250) rotate(15)">
        <text font-size="16" fill="darkblue">Transformed Text</text>
    </g>

    <!-- Groups and nested transforms -->
    <g transform="scale(0.8) translate(200, 180)">
        <g transform="rotate(30)">
            <rect width="60" height="40" fill="pink" stroke="navy"/>
            <text x="30" y="25" text-anchor="middle" font-size="12">Nested</text>
        </g>
    </g>
</svg>'''

    print("=== Debugging Complex SVG Issue ===")
    print(f"SVG content length: {len(complex_svg_content)}")

    try:
        # Test lxml parsing
        print("\n1. Testing lxml parsing...")
        from lxml import etree as ET

        svg_root = ET.fromstring(complex_svg_content.encode('utf-8'))
        print(f"   ✓ lxml parsing successful: {svg_root.tag}")
        print(f"   ✓ SVG has {len(svg_root)} child elements")

        # Test basic iteration
        print("\n2. Testing element iteration...")
        element_count = 0
        for element in svg_root:
            element_count += 1
            print(f"   - Element {element_count}: {element.tag} ({len(element)} children)")
        print(f"   ✓ Iteration successful: {element_count} elements")

    except Exception as e:
        print(f"   ✗ lxml parsing/iteration failed: {e}")
        import traceback
        traceback.print_exc()
        return

    try:
        # Test clean slate components step by step
        print("\n3. Testing clean slate parser...")
        from core.parse.parser import SVGParser
        from core.parse.svg_normalizer import SVGNormalizer

        # Test normalization
        normalizer = SVGNormalizer()
        try:
            normalized_element, changes = normalizer.normalize(svg_root)
            print(f"   ✓ SVG normalization successful")
            print(f"   - Changes applied: {len([k for k, v in changes.items() if v])}")
        except Exception as e:
            print(f"   ✗ Normalization failed: {e}")
            import traceback
            traceback.print_exc()
            return

        # Test parsing
        parser = SVGParser()
        try:
            parse_result = parser.parse(complex_svg_content)
            print(f"   ✓ Parser execution: {parse_result.success}")

            if not parse_result.success:
                print(f"   ✗ Parsing failed: {parse_result.error}")
                return

            print(f"   - SVG root type: {type(parse_result.svg_root)}")
            print(f"   - Processing time: {parse_result.processing_time_ms:.2f}ms")
        except Exception as e:
            print(f"   ✗ Parser failed: {e}")
            import traceback
            traceback.print_exc()
            return

    except Exception as e:
        print(f"   ✗ Clean slate parser components failed: {e}")
        import traceback
        traceback.print_exc()
        return

    try:
        # Test analyzer with detailed error tracking
        print("\n4. Testing clean slate analyzer...")
        from core.analyze.analyzer import SVGAnalyzer

        analyzer = SVGAnalyzer()
        try:
            analysis_result = analyzer.analyze(parse_result.svg_root)
            print(f"   ✓ Analysis completed")
            print(f"   - Element count: {analysis_result.element_count}")
            print(f"   - Complexity score: {analysis_result.complexity_score}")
            print(f"   - Scene object: {analysis_result.scene}")
            print(f"   - Scene type: {type(analysis_result.scene)}")
            print(f"   - Scene length: {len(analysis_result.scene) if analysis_result.scene else 'N/A'}")

            if analysis_result.scene is None:
                print("   ✗ CRITICAL ISSUE: Scene is None!")
                print(f"   - Recommended format: {analysis_result.recommended_output_format}")
                print(f"   - Recommended strategies: {analysis_result.recommended_strategies}")
                return
            else:
                print(f"   ✓ Scene created successfully with {len(analysis_result.scene)} elements")

        except Exception as e:
            print(f"   ✗ Analyzer failed: {e}")
            import traceback
            traceback.print_exc()
            return

    except Exception as e:
        print(f"   ✗ Analyzer component import failed: {e}")
        import traceback
        traceback.print_exc()
        return

    try:
        # Test the full pipeline like the E2E test does
        print("\n5. Testing full E2E pipeline...")
        from core.pipeline.converter import CleanSlateConverter

        converter = CleanSlateConverter()
        try:
            # Test the exact method that's failing
            mapper_results = converter._map_scene_elements(analysis_result.scene)
            print(f"   ✓ Scene mapping successful: {len(mapper_results)} results")

            # Try full conversion like E2E test
            temp_file = "/tmp/debug_complex.svg"
            with open(temp_file, 'w') as f:
                f.write(complex_svg_content)

            temp_output = "/tmp/debug_complex.pptx"
            result = converter.convert_file(temp_file, temp_output)
            print(f"   ✓ Full conversion result: success={result.success}")
            print(f"   - Elements processed: {result.elements_processed}")
            print(f"   - Processing time: {result.processing_time_ms:.2f}ms")

            if not result.success:
                print(f"   ✗ Conversion failed: {result.error}")

        except Exception as e:
            print(f"   ✗ Pipeline failed: {e}")
            import traceback
            traceback.print_exc()
            return

    except Exception as e:
        print(f"   ✗ Pipeline component import failed: {e}")
        import traceback
        traceback.print_exc()
        return

    print("\n=== Debug Complete ===")

if __name__ == "__main__":
    debug_complex_svg_issue()