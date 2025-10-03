#!/usr/bin/env python3
"""
Task 4 Validation: Parser Filter Extraction for Path Elements

Tests that parser extracts filter attributes from all SVG shape types and
passes them to IR Path constructors.
"""

from core.parse import SVGParser
from core.analyze import SVGAnalyzer
from core.ir import Path


def test_rect_with_filter():
    """Test that rect elements preserve filter reference"""
    svg = '''<svg xmlns="http://www.w3.org/2000/svg">
        <rect id="r1" x="10" y="10" width="100" height="50"
              fill="red" filter="url(#blur)"/>
    </svg>'''

    parser = SVGParser()
    parse_result = parser.parse(svg)
    assert parse_result.success

    analyzer = SVGAnalyzer()
    analysis_result = analyzer.analyze(parse_result.svg_root)
    scene = analysis_result.scene

    assert len(scene) == 1
    path = scene[0]
    assert isinstance(path, Path)
    assert path.id == "r1"
    assert path.filter == "url(#blur)"

    print(f"✓ Rect filter extracted: {path.filter}")
    return True


def test_circle_with_filter():
    """Test that circle elements preserve filter reference"""
    svg = '''<svg xmlns="http://www.w3.org/2000/svg">
        <circle id="c1" cx="50" cy="50" r="25"
                fill="blue" filter="url(#shadow)"/>
    </svg>'''

    parser = SVGParser()
    parse_result = parser.parse(svg)
    assert parse_result.success

    analyzer = SVGAnalyzer()
    analysis_result = analyzer.analyze(parse_result.svg_root)
    scene = analysis_result.scene

    assert len(scene) == 1
    path = scene[0]
    assert isinstance(path, Path)
    assert path.id == "c1"
    assert path.filter == "url(#shadow)"

    print(f"✓ Circle filter extracted: {path.filter}")
    return True


def test_ellipse_with_filter():
    """Test that ellipse elements preserve filter reference"""
    svg = '''<svg xmlns="http://www.w3.org/2000/svg">
        <ellipse id="e1" cx="50" cy="50" rx="40" ry="20"
                 fill="green" filter="#glow"/>
    </svg>'''

    parser = SVGParser()
    parse_result = parser.parse(svg)
    assert parse_result.success

    analyzer = SVGAnalyzer()
    analysis_result = analyzer.analyze(parse_result.svg_root)
    scene = analysis_result.scene

    assert len(scene) == 1
    path = scene[0]
    assert isinstance(path, Path)
    assert path.id == "e1"
    assert path.filter == "#glow"

    print(f"✓ Ellipse filter extracted: {path.filter}")
    return True


def test_path_with_filter():
    """Test that path elements preserve filter reference"""
    svg = '''<svg xmlns="http://www.w3.org/2000/svg">
        <path id="p1" d="M 10 10 L 100 100"
              stroke="black" filter="url(#contrast)"/>
    </svg>'''

    parser = SVGParser()
    parse_result = parser.parse(svg)
    assert parse_result.success

    analyzer = SVGAnalyzer()
    analysis_result = analyzer.analyze(parse_result.svg_root)
    scene = analysis_result.scene

    assert len(scene) == 1
    path = scene[0]
    assert isinstance(path, Path)
    assert path.id == "p1"
    assert path.filter == "url(#contrast)"

    print(f"✓ Path filter extracted: {path.filter}")
    return True


def test_polygon_with_filter():
    """Test that polygon elements preserve filter reference"""
    svg = '''<svg xmlns="http://www.w3.org/2000/svg">
        <polygon id="poly1" points="10,10 50,10 30,40"
                 fill="orange" filter="url(#brightness)"/>
    </svg>'''

    parser = SVGParser()
    parse_result = parser.parse(svg)
    assert parse_result.success

    analyzer = SVGAnalyzer()
    analysis_result = analyzer.analyze(parse_result.svg_root)
    scene = analysis_result.scene

    assert len(scene) == 1
    path = scene[0]
    assert isinstance(path, Path)
    assert path.id == "poly1"
    assert path.filter == "url(#brightness)"

    print(f"✓ Polygon filter extracted: {path.filter}")
    return True


def test_polyline_with_filter():
    """Test that polyline elements preserve filter reference"""
    svg = '''<svg xmlns="http://www.w3.org/2000/svg">
        <polyline id="pline1" points="10,10 50,10 30,40"
                  stroke="purple" fill="none" filter="url(#blur)"/>
    </svg>'''

    parser = SVGParser()
    parse_result = parser.parse(svg)
    assert parse_result.success

    analyzer = SVGAnalyzer()
    analysis_result = analyzer.analyze(parse_result.svg_root)
    scene = analysis_result.scene

    assert len(scene) == 1
    path = scene[0]
    assert isinstance(path, Path)
    assert path.id == "pline1"
    assert path.filter == "url(#blur)"

    print(f"✓ Polyline filter extracted: {path.filter}")
    return True


def test_line_with_filter():
    """Test that line elements preserve filter reference"""
    svg = '''<svg xmlns="http://www.w3.org/2000/svg">
        <line id="l1" x1="10" y1="10" x2="100" y2="100"
              stroke="black" filter="url(#shadow)"/>
    </svg>'''

    parser = SVGParser()
    parse_result = parser.parse(svg)
    assert parse_result.success

    analyzer = SVGAnalyzer()
    analysis_result = analyzer.analyze(parse_result.svg_root)
    scene = analysis_result.scene

    assert len(scene) == 1
    path = scene[0]
    assert isinstance(path, Path)
    assert path.id == "l1"
    assert path.filter == "url(#shadow)"

    print(f"✓ Line filter extracted: {path.filter}")
    return True


def test_multiple_shapes_with_filters():
    """Test multiple shapes with different filters"""
    svg = '''<svg xmlns="http://www.w3.org/2000/svg">
        <rect id="r1" x="0" y="0" width="10" height="10" filter="url(#blur)"/>
        <circle id="c1" cx="50" cy="50" r="10" filter="url(#shadow)"/>
        <path id="p1" d="M 0 0 L 10 10" filter="url(#glow)"/>
    </svg>'''

    parser = SVGParser()
    parse_result = parser.parse(svg)
    assert parse_result.success

    analyzer = SVGAnalyzer()
    analysis_result = analyzer.analyze(parse_result.svg_root)
    scene = analysis_result.scene

    assert len(scene) == 3

    filters = {elem.id: elem.filter for elem in scene}
    assert filters["r1"] == "url(#blur)"
    assert filters["c1"] == "url(#shadow)"
    assert filters["p1"] == "url(#glow)"

    print(f"✓ Multiple shapes with different filters extracted correctly")
    print(f"  - rect: {filters['r1']}")
    print(f"  - circle: {filters['c1']}")
    print(f"  - path: {filters['p1']}")

    return True


def test_shapes_without_filter_backward_compat():
    """Test that shapes without filters still work (backward compatibility)"""
    svg = '''<svg xmlns="http://www.w3.org/2000/svg">
        <rect id="r1" x="0" y="0" width="10" height="10" fill="red"/>
        <circle id="c1" cx="50" cy="50" r="10" fill="blue"/>
        <path id="p1" d="M 0 0 L 10 10"/>
    </svg>'''

    parser = SVGParser()
    parse_result = parser.parse(svg)
    assert parse_result.success

    analyzer = SVGAnalyzer()
    analysis_result = analyzer.analyze(parse_result.svg_root)
    scene = analysis_result.scene

    assert len(scene) == 3

    for elem in scene:
        assert elem.filter is None, f"Element {elem.id} should have None filter"

    print(f"✓ Shapes without filters default to None (backward compat)")

    return True


def test_filter_format_variations():
    """Test various filter reference formats"""
    test_cases = [
        ("url(#blur)", "url(#blur)"),
        ("#shadow", "#shadow"),
        ("url(#my-filter)", "url(#my-filter)"),
    ]

    for filter_attr, expected in test_cases:
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg">
            <rect x="0" y="0" width="10" height="10" filter="{filter_attr}"/>
        </svg>'''

        parser = SVGParser()
        parse_result = parser.parse(svg)
        assert parse_result.success

        analyzer = SVGAnalyzer()
        analysis_result = analyzer.analyze(parse_result.svg_root)
        scene = analysis_result.scene

        assert len(scene) == 1
        assert scene[0].filter == expected

    print(f"✓ All filter format variations supported:")
    for fmt, _ in test_cases:
        print(f"  - {fmt}")

    return True


def test_filter_with_other_attributes():
    """Test that filters work alongside all other attributes"""
    svg = '''<svg xmlns="http://www.w3.org/2000/svg">
        <rect id="r1" x="10" y="10" width="100" height="50"
              fill="red" stroke="black" stroke-width="2"
              opacity="0.8" filter="url(#blur)"/>
    </svg>'''

    parser = SVGParser()
    parse_result = parser.parse(svg)
    assert parse_result.success

    analyzer = SVGAnalyzer()
    analysis_result = analyzer.analyze(parse_result.svg_root)
    scene = analysis_result.scene

    assert len(scene) == 1
    path = scene[0]

    assert path.id == "r1"
    assert path.filter == "url(#blur)"
    assert path.opacity == 0.8
    assert path.fill is not None
    assert path.stroke is not None

    print(f"✓ Filter works alongside all other attributes:")
    print(f"  - ID: {path.id}")
    print(f"  - Filter: {path.filter}")
    print(f"  - Opacity: {path.opacity}")
    print(f"  - Has fill: {path.fill is not None}")
    print(f"  - Has stroke: {path.stroke is not None}")

    return True


if __name__ == '__main__':
    print("=" * 60)
    print("Task 4 Validation: Parser Filter Extraction")
    print("=" * 60)
    print()

    try:
        print("Test 1: Rect with filter")
        print("-" * 60)
        test_rect_with_filter()
        print()

        print("Test 2: Circle with filter")
        print("-" * 60)
        test_circle_with_filter()
        print()

        print("Test 3: Ellipse with filter")
        print("-" * 60)
        test_ellipse_with_filter()
        print()

        print("Test 4: Path with filter")
        print("-" * 60)
        test_path_with_filter()
        print()

        print("Test 5: Polygon with filter")
        print("-" * 60)
        test_polygon_with_filter()
        print()

        print("Test 6: Polyline with filter")
        print("-" * 60)
        test_polyline_with_filter()
        print()

        print("Test 7: Line with filter")
        print("-" * 60)
        test_line_with_filter()
        print()

        print("Test 8: Multiple shapes with different filters")
        print("-" * 60)
        test_multiple_shapes_with_filters()
        print()

        print("Test 9: Shapes without filters (backward compatibility)")
        print("-" * 60)
        test_shapes_without_filter_backward_compat()
        print()

        print("Test 10: Filter format variations")
        print("-" * 60)
        test_filter_format_variations()
        print()

        print("Test 11: Filter with other attributes")
        print("-" * 60)
        test_filter_with_other_attributes()
        print()

        print("=" * 60)
        print("✅ ALL TASK 4 TESTS PASSED")
        print("=" * 60)
        print()
        print("Task 4 Complete:")
        print("  ✓ Filter extraction in rect parser")
        print("  ✓ Filter extraction in circle parser")
        print("  ✓ Filter extraction in ellipse parser")
        print("  ✓ Filter extraction in path parser")
        print("  ✓ Filter extraction in polygon parser")
        print("  ✓ Filter extraction in polyline parser")
        print("  ✓ Filter extraction in line parser")
        print("  ✓ All 7 shape types support filters")
        print("  ✓ Filter references passed to IR Path constructors")
        print("  ✓ Backward compatibility maintained")
        print()
        print("Pipeline Status:")
        print("  SVG → [Parse ✓] → IR with filters → [Map ⏳] → PPTX")

    except AssertionError as e:
        print()
        print("=" * 60)
        print(f"❌ TEST FAILED: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        raise
    except Exception as e:
        print()
        print("=" * 60)
        print(f"❌ UNEXPECTED ERROR: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        raise
