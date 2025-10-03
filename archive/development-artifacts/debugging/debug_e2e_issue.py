#!/usr/bin/env python3
"""
Debug script for E2E pipeline issue analysis.
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

def debug_pipeline_issue():
    """Debug the E2E pipeline failure step by step."""

    # Test SVG content from the failing test
    svg_content = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
     viewBox="0 0 400 300" width="400" height="300">
    <defs>
        <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" style="stop-color:rgb(255,255,0);stop-opacity:1" />
            <stop offset="100%" style="stop-color:rgb(255,0,0);stop-opacity:1" />
        </linearGradient>
    </defs>
    <rect x="10" y="10" width="100" height="60" fill="url(#grad1)" stroke="black" stroke-width="2"/>
</svg>'''

    print("=== Debugging E2E Pipeline Issue ===")
    print(f"SVG content length: {len(svg_content)}")

    try:
        # Test lxml parsing directly
        print("\n1. Testing lxml parsing...")
        from lxml import etree as ET

        # Parse SVG
        svg_root = ET.fromstring(svg_content.encode('utf-8'))
        print(f"   ✓ lxml parsing successful: {svg_root.tag}")
        print(f"   ✓ SVG has {len(svg_root)} child elements")

        # Test iteration
        print("\n2. Testing element iteration...")
        element_count = 0
        for element in svg_root:
            element_count += 1
            print(f"   - Element {element_count}: {element.tag}")
        print(f"   ✓ Iteration successful: {element_count} elements")

    except Exception as e:
        print(f"   ✗ lxml parsing/iteration failed: {e}")
        return

    try:
        # Test clean slate components
        print("\n3. Testing clean slate parser...")
        from core.parse.parser import SVGParser
        from core.parse.svg_normalizer import SVGNormalizer

        # Test normalization
        normalizer = SVGNormalizer()
        normalized_element, changes = normalizer.normalize(svg_root)
        print(f"   ✓ SVG normalization successful")
        print(f"   - Changes applied: {len([k for k, v in changes.items() if v])}")

        # Test parsing
        parser = SVGParser()
        parse_result = parser.parse(svg_content)
        print(f"   ✓ Parser creation and execution: {parse_result.success}")

        if not parse_result.success:
            print(f"   ✗ Parsing failed: {parse_result.error}")
            return

    except Exception as e:
        print(f"   ✗ Clean slate parser failed: {e}")
        import traceback
        traceback.print_exc()
        return

    try:
        # Test analyzer
        print("\n4. Testing clean slate analyzer...")
        from core.analyze.analyzer import SVGAnalyzer

        analyzer = SVGAnalyzer()
        analysis_result = analyzer.analyze(parse_result.svg_root)
        print(f"   ✓ Analysis completed")
        print(f"   - Element count: {analysis_result.element_count}")
        print(f"   - Complexity score: {analysis_result.complexity_score}")
        print(f"   - Scene object: {analysis_result.scene}")
        print(f"   - Scene type: {type(analysis_result.scene)}")

        if analysis_result.scene is None:
            print("   ✗ ISSUE FOUND: Scene is None!")
            return

    except Exception as e:
        print(f"   ✗ Clean slate analyzer failed: {e}")
        import traceback
        traceback.print_exc()
        return

    try:
        # Test pipeline mapper
        print("\n5. Testing pipeline mapper...")
        from core.pipeline.converter import CleanSlateConverter

        converter = CleanSlateConverter()

        # Try the scene mapping that's failing
        if analysis_result.scene is not None:
            mapper_results = converter._map_scene_elements(analysis_result.scene)
            print(f"   ✓ Scene mapping successful: {len(mapper_results)} results")
        else:
            print("   ✗ Cannot test scene mapping - scene is None")

    except Exception as e:
        print(f"   ✗ Pipeline mapper failed: {e}")
        import traceback
        traceback.print_exc()
        return

    print("\n=== Debug Complete ===")

if __name__ == "__main__":
    debug_pipeline_issue()