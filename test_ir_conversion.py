#!/usr/bin/env python3
"""
Test the SVG to IR conversion to identify the exact issue.
"""

import traceback
from lxml import etree as ET

def test_ir_conversion():
    """Test IR conversion to identify the exact issue."""

    print("🔍 Testing SVG to IR Conversion")
    print("=" * 60)

    # Simple test SVG
    test_svg = """<?xml version="1.0" encoding="UTF-8"?>
    <svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
        <rect x="10" y="10" width="80" height="80" fill="red"/>
        <text x="50" y="50">Test</text>
    </svg>"""

    try:
        # Test the parser directly
        from core.parse.parser import SVGParser

        parser = SVGParser()

        # Test 1: Basic parsing
        print("1️⃣ Testing basic parse...")
        parse_result = parser.parse(test_svg)
        print(f"   ✅ Parse successful: {parse_result.success}")
        print(f"   - Elements: {parse_result.element_count}")

        # Test 2: Parse to IR
        print("\n2️⃣ Testing parse_to_ir...")
        try:
            scene, parse_result = parser.parse_to_ir(test_svg)
            if scene is None:
                print(f"   ❌ Scene is None. Error: {parse_result.error}")
            else:
                print(f"   ✅ Scene created")
                print(f"   - Scene type: {type(scene)}")
                print(f"   - Is list: {isinstance(scene, list)}")
                if hasattr(scene, '__len__'):
                    print(f"   - Scene length: {len(scene)}")
                if hasattr(scene, '__iter__'):
                    print(f"   - Scene is iterable: Yes")
                    # Try to iterate
                    count = 0
                    for item in scene:
                        count += 1
                        print(f"     - Item {count}: {type(item).__name__}")
                else:
                    print(f"   - Scene is iterable: No")

        except Exception as e:
            print(f"   ❌ parse_to_ir failed: {e}")
            traceback.print_exc()

        # Test 3: Test the analyzer
        print("\n3️⃣ Testing SVGAnalyzer...")
        from core.analyze.analyzer import SVGAnalyzer

        analyzer = SVGAnalyzer()

        # Parse first
        parse_result = parser.parse(test_svg)
        if parse_result.success:
            try:
                analysis_result = analyzer.analyze(parse_result.svg_root)
                print(f"   ✅ Analysis successful")
                print(f"   - Complexity: {analysis_result.complexity_score}")
                print(f"   - Scene: {type(analysis_result.scene)}")
                if analysis_result.scene:
                    print(f"   - Scene elements: {len(analysis_result.scene) if hasattr(analysis_result.scene, '__len__') else 'N/A'}")
            except Exception as e:
                print(f"   ❌ Analyzer failed: {e}")
                traceback.print_exc()

        # Test 4: Full pipeline
        print("\n4️⃣ Testing full pipeline...")
        from core.pipeline.converter import CleanSlateConverter

        converter = CleanSlateConverter()
        try:
            result = converter.convert_string(test_svg)
            print(f"   ✅ Conversion successful")
            print(f"   - Elements processed: {result.elements_processed}")
        except Exception as e:
            print(f"   ❌ Pipeline failed: {e}")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    test_ir_conversion()