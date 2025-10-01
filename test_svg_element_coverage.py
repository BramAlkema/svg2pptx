#!/usr/bin/env python3
"""
Systematic test of SVG element coverage.
Tests each SVG element type to verify if it actually works end-to-end.
"""

from core.pipeline.converter import CleanSlateConverter

# Test each SVG element type individually
ELEMENT_TESTS = {
    # Basic Shapes
    "rect": """<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
        <rect x="10" y="10" width="80" height="60" fill="blue" stroke="black" stroke-width="2"/>
    </svg>""",

    "circle": """<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
        <circle cx="50" cy="50" r="40" fill="red" stroke="green" stroke-width="2"/>
    </svg>""",

    "ellipse": """<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
        <ellipse cx="50" cy="50" rx="40" ry="25" fill="purple"/>
    </svg>""",

    "line": """<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
        <line x1="10" y1="10" x2="90" y2="90" stroke="black" stroke-width="2"/>
    </svg>""",

    "polyline": """<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
        <polyline points="10,10 50,50 90,10" stroke="blue" fill="none" stroke-width="2"/>
    </svg>""",

    "polygon": """<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
        <polygon points="50,10 90,90 10,90" fill="orange" stroke="black"/>
    </svg>""",

    "path": """<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
        <path d="M10,50 Q50,10 90,50 T90,90" stroke="navy" fill="none" stroke-width="2"/>
    </svg>""",

    # Text
    "text": """<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100">
        <text x="10" y="50" font-family="Arial" font-size="20" fill="black">Hello SVG</text>
    </svg>""",

    "text_tspan": """<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100">
        <text x="10" y="30" font-size="16">
            <tspan fill="red">Red</tspan>
            <tspan fill="blue" x="10" dy="20">Blue</tspan>
        </text>
    </svg>""",

    "textPath": """<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100">
        <defs>
            <path id="curve" d="M10,50 Q100,10 190,50"/>
        </defs>
        <text font-size="14">
            <textPath href="#curve">Text on a curved path</textPath>
        </text>
    </svg>""",

    # Structural
    "group": """<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
        <g transform="translate(10,10)">
            <rect x="0" y="0" width="30" height="30" fill="red"/>
            <circle cx="50" cy="15" r="15" fill="blue"/>
        </g>
    </svg>""",

    "nested_groups": """<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
        <g id="outer">
            <g id="inner" transform="translate(20,20)">
                <rect width="20" height="20" fill="green"/>
            </g>
        </g>
    </svg>""",

    "symbol_use": """<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
        <defs>
            <symbol id="star" viewBox="0 0 10 10">
                <polygon points="5,0 6,4 10,4 7,6 8,10 5,7 2,10 3,6 0,4 4,4"/>
            </symbol>
        </defs>
        <use href="#star" x="10" y="10" width="20" height="20" fill="gold"/>
    </svg>""",

    # Paint Servers
    "linearGradient": """<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
        <defs>
            <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stop-color="red"/>
                <stop offset="100%" stop-color="blue"/>
            </linearGradient>
        </defs>
        <rect x="10" y="10" width="80" height="80" fill="url(#grad1)"/>
    </svg>""",

    "radialGradient": """<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
        <defs>
            <radialGradient id="grad2">
                <stop offset="0%" stop-color="yellow"/>
                <stop offset="100%" stop-color="red"/>
            </radialGradient>
        </defs>
        <circle cx="50" cy="50" r="40" fill="url(#grad2)"/>
    </svg>""",

    "pattern": """<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
        <defs>
            <pattern id="pat1" x="0" y="0" width="10" height="10" patternUnits="userSpaceOnUse">
                <rect width="5" height="5" fill="lightblue"/>
                <rect x="5" y="5" width="5" height="5" fill="lightblue"/>
            </pattern>
        </defs>
        <rect x="10" y="10" width="80" height="80" fill="url(#pat1)"/>
    </svg>""",

    # Clipping & Masking
    "clipPath": """<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
        <defs>
            <clipPath id="clip1">
                <circle cx="50" cy="50" r="30"/>
            </clipPath>
        </defs>
        <rect x="10" y="10" width="80" height="80" fill="purple" clip-path="url(#clip1)"/>
    </svg>""",

    "mask": """<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
        <defs>
            <mask id="mask1">
                <circle cx="50" cy="50" r="30" fill="white"/>
            </mask>
        </defs>
        <rect x="10" y="10" width="80" height="80" fill="orange" mask="url(#mask1)"/>
    </svg>""",

    # Filters
    "filter_blur": """<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
        <defs>
            <filter id="blur1">
                <feGaussianBlur stdDeviation="3"/>
            </filter>
        </defs>
        <rect x="10" y="10" width="80" height="80" fill="green" filter="url(#blur1)"/>
    </svg>""",

    "filter_dropshadow": """<svg xmlns="http://www.w3.org/2000/svg" width="120" height="120">
        <defs>
            <filter id="shadow">
                <feDropShadow dx="4" dy="4" stdDeviation="2"/>
            </filter>
        </defs>
        <rect x="20" y="20" width="60" height="60" fill="red" filter="url(#shadow)"/>
    </svg>""",

    # Images & References
    "image": """<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
        <image href="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAiIGhlaWdodD0iMTAiPjxyZWN0IHdpZHRoPSIxMCIgaGVpZ2h0PSIxMCIgZmlsbD0icmVkIi8+PC9zdmc+"
               x="10" y="10" width="80" height="80"/>
    </svg>""",

    "marker": """<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
        <defs>
            <marker id="arrow" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
                <polygon points="0,0 0,6 9,3" fill="black"/>
            </marker>
        </defs>
        <line x1="10" y1="50" x2="90" y2="50" stroke="black" marker-end="url(#arrow)"/>
    </svg>""",

    # Animation
    "animate": """<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
        <rect x="10" y="10" width="80" height="80" fill="blue">
            <animate attributeName="fill" from="blue" to="red" dur="2s" repeatCount="indefinite"/>
        </rect>
    </svg>""",

    # Transforms
    "transform_rotate": """<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
        <rect x="40" y="40" width="20" height="20" fill="purple" transform="rotate(45 50 50)"/>
    </svg>""",

    "transform_scale": """<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
        <rect x="25" y="25" width="20" height="20" fill="teal" transform="scale(2)"/>
    </svg>""",

    # Other
    "hyperlink": """<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
        <a href="https://example.com">
            <rect x="10" y="10" width="80" height="80" fill="cyan"/>
        </a>
    </svg>""",

    "switch": """<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
        <switch>
            <rect x="10" y="10" width="80" height="80" fill="lime"/>
            <rect x="10" y="10" width="80" height="80" fill="red"/>
        </switch>
    </svg>""",
}

def test_element_coverage():
    """Test each SVG element type"""

    print("=" * 80)
    print("SVG ELEMENT COVERAGE TEST")
    print("=" * 80)
    print()

    converter = CleanSlateConverter()
    results = {}

    for element_name, svg_content in ELEMENT_TESTS.items():
        print(f"Testing: {element_name:20s} ", end="")

        try:
            result = converter.convert_string(svg_content)

            if result.elements_processed > 0:
                status = "✅ WORKS"
                details = f"({result.elements_processed} element(s) processed)"
            else:
                status = "⚠️ PARSED"
                details = "(0 elements processed)"

            results[element_name] = {
                'status': 'working' if result.elements_processed > 0 else 'parsed_only',
                'elements': result.elements_processed,
                'native': result.native_elements,
                'emf': result.emf_elements,
                'size': len(result.output_data)
            }

        except Exception as e:
            status = "❌ FAILED"
            details = f"({str(e)[:40]}...)"
            results[element_name] = {
                'status': 'failed',
                'error': str(e)
            }

        print(f"{status:12s} {details}")

    # Summary
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)

    working = [k for k, v in results.items() if v['status'] == 'working']
    parsed_only = [k for k, v in results.items() if v['status'] == 'parsed_only']
    failed = [k for k, v in results.items() if v['status'] == 'failed']

    total = len(ELEMENT_TESTS)
    print(f"Total elements tested: {total}")
    print(f"✅ Working (processed elements): {len(working)} ({len(working)/total*100:.1f}%)")
    print(f"⚠️  Parsed but not processed: {len(parsed_only)} ({len(parsed_only)/total*100:.1f}%)")
    print(f"❌ Failed: {len(failed)} ({len(failed)/total*100:.1f}%)")

    if parsed_only:
        print(f"\n⚠️  Elements parsed but not processed:")
        for elem in parsed_only:
            print(f"  - {elem}")

    if failed:
        print(f"\n❌ Failed elements:")
        for elem in failed:
            print(f"  - {elem}: {results[elem].get('error', 'Unknown error')[:60]}")

    # Create detailed report
    print(f"\n📊 Detailed Results:")
    print(f"{'Element':<25} {'Status':<12} {'Processed':<10} {'Native':<8} {'EMF':<6} {'Size (bytes)'}")
    print("-" * 80)
    for elem, data in sorted(results.items()):
        if data['status'] == 'working':
            print(f"{elem:<25} {'✅ Working':<12} {data['elements']:<10} {data['native']:<8} {data['emf']:<6} {data['size']}")
        elif data['status'] == 'parsed_only':
            print(f"{elem:<25} {'⚠️ Parsed':<12} {data['elements']:<10} {data['native']:<8} {data['emf']:<6} {data['size']}")
        else:
            print(f"{elem:<25} {'❌ Failed':<12} {'N/A':<10} {'N/A':<8} {'N/A':<6} {'N/A'}")

    return results

if __name__ == "__main__":
    results = test_element_coverage()