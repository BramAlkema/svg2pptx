#!/usr/bin/env python3
"""
Debug the specific analyzer error with complex SVG.
"""

def debug_analyzer_error():
    """Debug the cython iteration error."""

    print("🔍 DEBUGGING ANALYZER ERROR")
    print("=" * 60)

    # Use the exact complex SVG that fails
    complex_svg = """<?xml version="1.0" encoding="UTF-8"?>
    <svg xmlns="http://www.w3.org/2000/svg" width="800" height="600" viewBox="0 0 800 600">
        <!-- Basic rect -->
        <rect x="50" y="50" width="200" height="100" fill="blue" stroke="black" stroke-width="2"/>

        <!-- Basic text -->
        <text x="100" y="200" font-size="24" fill="black">Basic Text</text>

        <!-- Rotated text (should trigger WordArt consideration) -->
        <text x="400" y="200" font-size="36" fill="red" transform="rotate(45 400 200)">
            Rotated Text
        </text>

        <!-- Text with gradient (should trigger WordArt) -->
        <defs>
            <linearGradient id="textGrad">
                <stop offset="0%" stop-color="purple"/>
                <stop offset="100%" stop-color="orange"/>
            </linearGradient>
        </defs>
        <text x="100" y="350" font-size="48" fill="url(#textGrad)">
            Gradient Text
        </text>

        <!-- Text on path -->
        <defs>
            <path id="curve" d="M100,450 Q250,400 400,450" fill="none" stroke="gray"/>
        </defs>
        <text font-size="20" fill="green">
            <textPath href="#curve">Text flowing on a curved path!</textPath>
        </text>

        <!-- Circle -->
        <circle cx="600" cy="100" r="50" fill="yellow" stroke="red" stroke-width="3"/>
    </svg>"""

    try:
        # Step 1: Test basic parsing
        from core.parse.parser import SVGParser
        parser = SVGParser()
        parse_result = parser.parse(complex_svg)

        print(f"✅ Parse result: {parse_result.success}")

        if not parse_result.success:
            print(f"❌ Parse failed: {parse_result.error}")
            return

        # Step 2: Test the walk function directly on the parsed SVG
        print(f"\n🚶 Testing walk function...")
        from core.xml.safe_iter import walk, is_element

        try:
            elements = list(walk(parse_result.svg_root))
            print(f"✅ Walk successful: {len(elements)} elements")
        except Exception as e:
            print(f"❌ Walk failed: {e}")
            print(f"   SVG root type: {type(parse_result.svg_root)}")
            print(f"   SVG root tag: {parse_result.svg_root.tag}")

            # Try to iterate manually
            try:
                print(f"   Trying manual iteration...")
                for i, child in enumerate(parse_result.svg_root):
                    if i < 5:  # Only first few
                        print(f"     Child {i}: {type(child)} - {getattr(child, 'tag', 'no tag')}")
                        print(f"       Is element: {is_element(child)}")
            except Exception as e2:
                print(f"   Manual iteration failed: {e2}")
            return

        # Step 3: Test analyzer
        print(f"\n📊 Testing analyzer...")
        from core.analyze.analyzer import SVGAnalyzer

        analyzer = SVGAnalyzer()
        try:
            analysis_result = analyzer.analyze(parse_result.svg_root)
            print(f"✅ Analysis successful")
            print(f"   Scene elements: {len(analysis_result.scene) if analysis_result.scene else 0}")
        except Exception as e:
            print(f"❌ Analysis failed: {e}")
            import traceback
            traceback.print_exc()

    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_analyzer_error()