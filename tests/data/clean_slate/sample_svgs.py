#!/usr/bin/env python3
"""
Sample SVG Test Data

Provides standardized SVG test data for clean slate testing.
"""

from typing import Dict, List

# Simple SVG samples for basic testing
SIMPLE_SVGS = {
    'rectangle': '''<svg width="100" height="100" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
    <rect x="10" y="10" width="50" height="30" fill="red"/>
</svg>''',

    'circle': '''<svg width="100" height="100" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
    <circle cx="50" cy="50" r="25" fill="blue"/>
</svg>''',

    'path_simple': '''<svg width="100" height="100" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
    <path d="M 10 10 L 50 30 L 90 10 Z" fill="green"/>
</svg>''',

    'text_simple': '''<svg width="200" height="100" viewBox="0 0 200 100" xmlns="http://www.w3.org/2000/svg">
    <text x="10" y="30" font-family="Arial" font-size="12">Hello World</text>
</svg>''',

    'group_simple': '''<svg width="100" height="100" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
    <g transform="translate(10, 10)">
        <rect x="0" y="0" width="30" height="20" fill="red"/>
        <circle cx="40" cy="10" r="10" fill="blue"/>
    </g>
</svg>'''
}

# Complex SVG samples for advanced testing
COMPLEX_SVGS = {
    'gradient_path': '''<svg width="200" height="100" viewBox="0 0 200 100" xmlns="http://www.w3.org/2000/svg">
    <defs>
        <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" style="stop-color:rgb(255,255,0);stop-opacity:1" />
            <stop offset="100%" style="stop-color:rgb(255,0,0);stop-opacity:1" />
        </linearGradient>
    </defs>
    <path d="M 10 10 C 40 40, 80 40, 110 10 S 170 -20, 190 10 L 190 50 L 10 50 Z"
          fill="url(#grad1)" stroke="black" stroke-width="2"/>
</svg>''',

    'nested_groups': '''<svg width="200" height="200" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
    <g transform="translate(20, 20)" opacity="0.8">
        <g transform="rotate(45 50 50)">
            <rect x="25" y="25" width="50" height="50" fill="red"/>
            <g transform="scale(0.5)">
                <circle cx="50" cy="50" r="20" fill="blue"/>
            </g>
        </g>
        <text x="10" y="120" font-family="Arial" font-size="14">Nested Groups</text>
    </g>
</svg>''',

    'complex_text': '''<svg width="300" height="150" viewBox="0 0 300 150" xmlns="http://www.w3.org/2000/svg">
    <text x="10" y="30" font-family="Arial" font-size="16">
        <tspan fill="red" font-weight="bold">Bold Red </tspan>
        <tspan fill="blue" font-style="italic">Italic Blue </tspan>
        <tspan fill="green">Normal Green</tspan>
    </text>
    <text x="10" y="60" font-family="Times" font-size="12" text-anchor="middle">Centered Text</text>
    <text x="10" y="90" font-family="Courier" font-size="10" transform="rotate(45 10 90)">Rotated Text</text>
</svg>''',

    'paths_and_curves': '''<svg width="300" height="200" viewBox="0 0 300 200" xmlns="http://www.w3.org/2000/svg">
    <path d="M 50 50 L 100 50 Q 150 25, 200 50 T 250 50"
          stroke="red" stroke-width="3" fill="none"/>
    <path d="M 50 100 C 75 75, 125 75, 150 100 S 200 125, 250 100"
          stroke="blue" stroke-width="2" fill="none"/>
    <path d="M 50 150 A 25 25 0 0 1 100 150 A 25 25 0 0 1 150 150"
          stroke="green" stroke-width="2" fill="none"/>
</svg>''',

    'with_clipping': '''<svg width="200" height="200" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
    <defs>
        <clipPath id="clip1">
            <circle cx="100" cy="100" r="50"/>
        </clipPath>
    </defs>
    <g clip-path="url(#clip1)">
        <rect x="50" y="50" width="100" height="100" fill="red"/>
        <path d="M 0 0 L 200 200 M 200 0 L 0 200" stroke="blue" stroke-width="5"/>
    </g>
</svg>'''
}

# Edge case SVG samples for robustness testing
EDGE_CASE_SVGS = {
    'empty_elements': '''<svg width="100" height="100" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
    <path d="" fill="red"/>
    <text x="10" y="20"></text>
    <g></g>
</svg>''',

    'zero_dimensions': '''<svg width="0" height="0" viewBox="0 0 0 0" xmlns="http://www.w3.org/2000/svg">
    <rect x="0" y="0" width="0" height="0" fill="red"/>
    <circle cx="0" cy="0" r="0" fill="blue"/>
</svg>''',

    'extreme_coordinates': '''<svg width="100" height="100" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
    <path d="M -1000000 -1000000 L 1000000 1000000" stroke="red"/>
    <circle cx="1e6" cy="1e6" r="1e3" fill="blue"/>
</svg>''',

    'malformed_attributes': '''<svg width="100" height="100" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
    <rect x="abc" y="def" width="xyz" height="123abc" fill="not-a-color"/>
    <circle cx="" cy="" r="negative" fill=""/>
</svg>''',

    'special_characters': '''<svg width="200" height="100" viewBox="0 0 200 100" xmlns="http://www.w3.org/2000/svg">
    <text x="10" y="30" font-family="Arial" font-size="12">Special: &lt;&gt;&amp;"'</text>
    <text x="10" y="60" font-family="Arial" font-size="12">Unicode: 世界 مرحبا ∑∏∆</text>
</svg>'''
}

# Performance test SVG samples
PERFORMANCE_SVGS = {
    'many_elements': '''<svg width="1000" height="1000" viewBox="0 0 1000 1000" xmlns="http://www.w3.org/2000/svg">
    {}
</svg>'''.format('\n    '.join([
        f'<rect x="{x}" y="{y}" width="10" height="10" fill="rgb({x%256},{y%256},{(x+y)%256})"/>'
        for x in range(0, 1000, 20) for y in range(0, 1000, 20)
    ])),

    'complex_paths': '''<svg width="500" height="500" viewBox="0 0 500 500" xmlns="http://www.w3.org/2000/svg">
    {}
</svg>'''.format('\n    '.join([
        f'<path d="M {i*10} {i*10} C {i*15} {i*5}, {i*20} {i*15}, {i*25} {i*10} Z" fill="hsl({i*10}, 70%, 50%)"/>'
        for i in range(20)
    ]))
}

# Expected IR representations for validation
EXPECTED_IR_STRUCTURES = {
    'rectangle': {
        'type': 'Scene',
        'elements': [
            {
                'type': 'Path',
                'fill': {'type': 'SolidPaint', 'color': 'ff0000'},
                'stroke': None,
                'segments_count': 4,
                'is_closed': True
            }
        ],
        'viewbox': (0, 0, 100, 100),
        'element_count': 1
    },

    'text_simple': {
        'type': 'Scene',
        'elements': [
            {
                'type': 'TextFrame',
                'runs_count': 1,
                'x': 10,
                'y': 30,
                'content': 'Hello World'
            }
        ],
        'element_count': 1
    },

    'group_simple': {
        'type': 'Scene',
        'elements': [
            {
                'type': 'Group',
                'children_count': 2,
                'transform': 'translate(10, 10)'
            }
        ],
        'element_count': 1
    }
}

# Test scenarios for different testing purposes
TEST_SCENARIOS = {
    'smoke_test': {
        'svgs': ['rectangle', 'circle', 'text_simple'],
        'description': 'Basic smoke test with simple elements',
        'expected_processing_time_ms': 50
    },

    'feature_coverage': {
        'svgs': ['gradient_path', 'complex_text', 'nested_groups', 'with_clipping'],
        'description': 'Comprehensive feature coverage test',
        'expected_processing_time_ms': 200
    },

    'robustness': {
        'svgs': ['empty_elements', 'zero_dimensions', 'extreme_coordinates', 'malformed_attributes'],
        'description': 'Edge cases and error handling test',
        'expected_processing_time_ms': 100
    },

    'performance': {
        'svgs': ['many_elements', 'complex_paths'],
        'description': 'Performance and scalability test',
        'expected_processing_time_ms': 1000
    }
}


def get_svg_by_name(name: str) -> str:
    """Get SVG content by name from all categories"""
    all_svgs = {**SIMPLE_SVGS, **COMPLEX_SVGS, **EDGE_CASE_SVGS, **PERFORMANCE_SVGS}
    return all_svgs.get(name, '')


def get_test_scenario(scenario_name: str) -> Dict:
    """Get test scenario configuration"""
    return TEST_SCENARIOS.get(scenario_name, {})


def get_expected_ir_structure(svg_name: str) -> Dict:
    """Get expected IR structure for validation"""
    return EXPECTED_IR_STRUCTURES.get(svg_name, {})


def list_available_svgs() -> Dict[str, List[str]]:
    """List all available SVG test data by category"""
    return {
        'simple': list(SIMPLE_SVGS.keys()),
        'complex': list(COMPLEX_SVGS.keys()),
        'edge_cases': list(EDGE_CASE_SVGS.keys()),
        'performance': list(PERFORMANCE_SVGS.keys())
    }


# Export for use in tests
__all__ = [
    'SIMPLE_SVGS',
    'COMPLEX_SVGS',
    'EDGE_CASE_SVGS',
    'PERFORMANCE_SVGS',
    'EXPECTED_IR_STRUCTURES',
    'TEST_SCENARIOS',
    'get_svg_by_name',
    'get_test_scenario',
    'get_expected_ir_structure',
    'list_available_svgs'
]