#!/usr/bin/env python3
"""
ClipPath test fixtures and utilities.

This module provides test data and utilities for clipPath analysis and conversion testing.
"""

from lxml import etree as ET
from typing import Dict, List
from src.converters.clippath_types import ClipPathDefinition, ClippingType


def create_svg_element(tag_name: str, **attrs) -> ET.Element:
    """Create an SVG element with namespace."""
    element = ET.Element(f"{{http://www.w3.org/2000/svg}}{tag_name}")
    for key, value in attrs.items():
        element.set(key, str(value))
    return element


def create_simple_rect_clippath() -> ClipPathDefinition:
    """Create a simple rectangular clipPath definition."""
    rect = create_svg_element('rect', x=10, y=10, width=100, height=50)
    return ClipPathDefinition(
        id='simple_rect',
        units='userSpaceOnUse',
        clip_rule='nonzero',
        shapes=[rect],
        clipping_type=ClippingType.SHAPE_BASED
    )


def create_simple_path_clippath() -> ClipPathDefinition:
    """Create a simple path-based clipPath definition."""
    return ClipPathDefinition(
        id='simple_path',
        units='userSpaceOnUse',
        clip_rule='nonzero',
        path_data='M 0 0 L 100 0 L 100 100 L 0 100 Z',
        clipping_type=ClippingType.PATH_BASED
    )


def create_complex_path_clippath() -> ClipPathDefinition:
    """Create a complex path with curves."""
    return ClipPathDefinition(
        id='complex_path',
        units='userSpaceOnUse',
        clip_rule='evenodd',
        path_data='M 50 0 C 77.6 0 100 22.4 100 50 C 100 77.6 77.6 100 50 100 C 22.4 100 0 77.6 0 50 C 0 22.4 22.4 0 50 0 Z',
        clipping_type=ClippingType.PATH_BASED
    )


def create_text_clippath() -> ClipPathDefinition:
    """Create a clipPath containing text elements."""
    text = create_svg_element('text', x=10, y=30)
    text.text = "Sample Text"
    return ClipPathDefinition(
        id='text_clip',
        units='userSpaceOnUse',
        clip_rule='nonzero',
        shapes=[text],
        clipping_type=ClippingType.COMPLEX
    )


def create_filter_clippath() -> ClipPathDefinition:
    """Create a clipPath with filter effects."""
    rect = create_svg_element('rect', x=0, y=0, width=100, height=100)
    rect.set('filter', 'url(#blur)')
    return ClipPathDefinition(
        id='filter_clip',
        units='userSpaceOnUse',
        clip_rule='nonzero',
        shapes=[rect],
        clipping_type=ClippingType.COMPLEX
    )


def create_animation_clippath() -> ClipPathDefinition:
    """Create a clipPath with animations."""
    rect = create_svg_element('rect', x=0, y=0, width=100, height=100)
    animate = create_svg_element('animate', attributeName='width',
                                dur='2s')
    animate.set('from', '100')
    animate.set('to', '200')
    rect.append(animate)

    return ClipPathDefinition(
        id='animated_clip',
        units='userSpaceOnUse',
        clip_rule='nonzero',
        shapes=[rect],
        clipping_type=ClippingType.COMPLEX
    )


def create_transform_clippath() -> ClipPathDefinition:
    """Create a clipPath with complex transforms."""
    rect = create_svg_element('rect', x=0, y=0, width=100, height=100,
                             transform='matrix(1.5 0.5 -0.5 1.5 50 25)')
    return ClipPathDefinition(
        id='transform_clip',
        units='userSpaceOnUse',
        clip_rule='nonzero',
        shapes=[rect],
        clipping_type=ClippingType.COMPLEX,
        transform='rotate(45 50 50) scale(1.2)'
    )


def create_nested_clippath_definitions() -> Dict[str, ClipPathDefinition]:
    """Create a set of nested clipPath definitions."""
    # Base clipPath
    base_rect = create_svg_element('rect', x=0, y=0, width=200, height=200)
    base_clip = ClipPathDefinition(
        id='base_clip',
        units='userSpaceOnUse',
        clip_rule='nonzero',
        shapes=[base_rect],
        clipping_type=ClippingType.SHAPE_BASED
    )

    # Nested clipPath that references base
    nested_rect = create_svg_element('rect', x=50, y=50, width=100, height=100)
    nested_rect.set('clip-path', 'url(#base_clip)')
    nested_clip = ClipPathDefinition(
        id='nested_clip',
        units='userSpaceOnUse',
        clip_rule='nonzero',
        shapes=[nested_rect],
        clipping_type=ClippingType.SHAPE_BASED
    )

    return {
        'base_clip': base_clip,
        'nested_clip': nested_clip
    }


def create_multiple_shapes_clippath() -> ClipPathDefinition:
    """Create a clipPath with multiple shapes."""
    rect = create_svg_element('rect', x=0, y=0, width=100, height=100)
    circle = create_svg_element('circle', cx=50, cy=50, r=30)
    ellipse = create_svg_element('ellipse', cx=75, cy=25, rx=20, ry=15)

    return ClipPathDefinition(
        id='multi_shapes',
        units='userSpaceOnUse',
        clip_rule='nonzero',
        shapes=[rect, circle, ellipse],
        clipping_type=ClippingType.COMPLEX
    )


def create_circular_reference_clippath() -> Dict[str, ClipPathDefinition]:
    """Create clipPaths with circular references."""
    # ClipPath A references B
    rect_a = create_svg_element('rect', x=0, y=0, width=100, height=100)
    rect_a.set('clip-path', 'url(#clip_b)')
    clip_a = ClipPathDefinition(
        id='clip_a',
        units='userSpaceOnUse',
        clip_rule='nonzero',
        shapes=[rect_a],
        clipping_type=ClippingType.SHAPE_BASED
    )

    # ClipPath B references A (circular)
    rect_b = create_svg_element('rect', x=25, y=25, width=50, height=50)
    rect_b.set('clip-path', 'url(#clip_a)')
    clip_b = ClipPathDefinition(
        id='clip_b',
        units='userSpaceOnUse',
        clip_rule='nonzero',
        shapes=[rect_b],
        clipping_type=ClippingType.SHAPE_BASED
    )

    return {
        'clip_a': clip_a,
        'clip_b': clip_b
    }


def create_test_svg_with_clippath() -> ET.Element:
    """Create a complete test SVG with clipPath definitions."""
    svg = create_svg_element('svg', width=200, height=200, viewBox='0 0 200 200')

    # Add defs section
    defs = ET.SubElement(svg, 'defs')

    # Add simple clipPath
    clippath = ET.SubElement(defs, 'clipPath')
    clippath.set('id', 'test_clip')
    rect = ET.SubElement(clippath, 'rect')
    rect.set('x', '10')
    rect.set('y', '10')
    rect.set('width', '100')
    rect.set('height', '50')

    # Add element that uses clipPath
    test_rect = ET.SubElement(svg, 'rect')
    test_rect.set('x', '0')
    test_rect.set('y', '0')
    test_rect.set('width', '200')
    test_rect.set('height', '200')
    test_rect.set('clip-path', 'url(#test_clip)')
    test_rect.set('fill', 'blue')

    return svg


# Sample SVG data for different test scenarios
SAMPLE_SVG_DATA = {
    'simple_rect_clip': '''<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">
        <defs>
            <clipPath id="clip1">
                <rect x="10" y="10" width="100" height="50"/>
            </clipPath>
        </defs>
        <rect x="0" y="0" width="200" height="200" fill="blue" clip-path="url(#clip1)"/>
    </svg>''',

    'nested_clips': '''<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">
        <defs>
            <clipPath id="outer">
                <rect x="0" y="0" width="200" height="200"/>
            </clipPath>
            <clipPath id="inner">
                <rect x="50" y="50" width="100" height="100" clip-path="url(#outer)"/>
            </clipPath>
        </defs>
        <rect x="0" y="0" width="200" height="200" fill="red" clip-path="url(#inner)"/>
    </svg>''',

    'text_in_clippath': '''<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">
        <defs>
            <clipPath id="textClip">
                <text x="10" y="30" font-size="20">CLIP</text>
            </clipPath>
        </defs>
        <rect x="0" y="0" width="200" height="200" fill="green" clip-path="url(#textClip)"/>
    </svg>''',

    'complex_path_clip': '''<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">
        <defs>
            <clipPath id="starClip">
                <path d="M100,0 L124,76 L200,76 L138,124 L162,200 L100,152 L38,200 L62,124 L0,76 L76,76 Z"/>
            </clipPath>
        </defs>
        <rect x="0" y="0" width="200" height="200" fill="purple" clip-path="url(#starClip)"/>
    </svg>'''
}


def parse_svg_string(svg_string: str) -> ET.Element:
    """Parse SVG string into element tree."""
    return ET.fromstring(svg_string)


def get_clippath_definitions_from_svg(svg_element: ET.Element) -> Dict[str, ET.Element]:
    """Extract clipPath definitions from SVG element."""
    clippath_defs = {}
    for clippath in svg_element.findall('.//clipPath'):
        clip_id = clippath.get('id')
        if clip_id:
            clippath_defs[clip_id] = clippath
    return clippath_defs