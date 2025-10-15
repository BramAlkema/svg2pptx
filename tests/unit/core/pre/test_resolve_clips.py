#!/usr/bin/env python3

from lxml import etree as ET

from core.pre.resolve_clips import ResolveClipsPreprocessor


def _ns() -> dict[str, str]:
    return {'svg': 'http://www.w3.org/2000/svg'}


def test_resolve_clips_preserves_clip_reference():
    svg_markup = """
    <svg xmlns="http://www.w3.org/2000/svg">
        <defs>
            <clipPath id="clip1">
                <rect x="0" y="0" width="10" height="10"/>
            </clipPath>
        </defs>
        <rect id="target" clip-path="url(#clip1)" x="0" y="0" width="20" height="20"/>
    </svg>
    """

    root = ET.fromstring(svg_markup)
    preprocessor = ResolveClipsPreprocessor()
    result = preprocessor.process(root)

    rect_nodes = result.xpath(".//svg:rect[@id='target']", namespaces=_ns())
    assert rect_nodes, "Expected to find processed rectangle element"
    rect = rect_nodes[0]

    assert rect.get('clip-path') == "url(#clip1)"
    assert rect.get('data-clip-source') == "clip1"
    assert rect.get('data-clip-operation') == "intersect"
    assert rect.get('data-clip-resolved') == "true"
    assert "clip1" in preprocessor.processed_clips
