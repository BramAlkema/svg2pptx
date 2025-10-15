"""
Reusable fixtures supporting the module-slicing refactor tests.

These helpers provide deterministic SVG snippets and XML fragments that
exercise the sliced parser, XML builder generators, and the new viewport
engine flows without depending on external assets.
"""

from __future__ import annotations

from textwrap import dedent

from lxml import etree as ET

SVG_NS = "http://www.w3.org/2000/svg"
A_URI = "http://schemas.openxmlformats.org/drawingml/2006/main"


def svg_with_mixed_clip_geometry() -> str:
    """SVG containing clipPath definitions covering multiple element types."""
    return dedent(
        f"""
        <svg xmlns="{SVG_NS}" width="200" height="120" viewBox="0 0 200 120">
            <defs>
                <clipPath id="clip-complex" clipPathUnits="userSpaceOnUse" transform="translate(5 10)">
                    <path d="M0 0 L100 0 L100 40 L0 40 z"/>
                    <rect x="20" y="15" width="30" height="20" />
                    <circle cx="75" cy="60" r="12" />
                    <ellipse cx="120" cy="55" rx="10" ry="18" />
                    <polygon points="150,25 170,35 160,55" />
                    <polyline points="15,75 25,90 10,105" />
                </clipPath>
                <clipPath id="clip-style" style="clip-rule:evenodd">
                    <rect x="0" y="0" width="80" height="40" />
                </clipPath>
            </defs>
            <rect x="0" y="0" width="200" height="120" fill="#eeeeee" clip-path="url(#clip-complex)"/>
            <rect x="100" y="0" width="50" height="40" fill="#cccccc" clip-path="url(#clip-style)"/>
            <a href="https://example.test" data-slide="4">
                <text x="10" y="110">demo</text>
            </a>
        </svg>
        """
    ).strip()


def svg_with_viewbox(width: str = "800px", height: str = "600px", viewbox: str = "0 0 1600 900") -> ET.Element:
    """Return an SVG element with configurable width/height strings and viewBox."""
    svg_xml = f'<svg xmlns="{SVG_NS}" width="{width}" height="{height}" viewBox="{viewbox}"></svg>'
    return ET.fromstring(svg_xml)


def svg_batch_samples() -> list[ET.Element]:
    """Provide a small batch of SVG elements for viewport engine tests."""
    return [
        svg_with_viewbox("800px", "600px", "0 0 800 600"),
        svg_with_viewbox("1024px", "768px", "0 0 1024 768"),
        svg_with_viewbox("5in", "3in", "0 0 500 300"),
    ]


def path_fill_xml() -> str:
    """Return DrawingML fill fragment used by the path shape generator tests."""
    return dedent(
        f"""
        <a:solidFill xmlns:a="{A_URI}">
            <a:srgbClr val="FF3366"/>
        </a:solidFill>
        """
    ).strip()


def path_stroke_xml() -> str:
    """Return DrawingML stroke fragment used by the path shape generator tests."""
    return dedent(
        f"""
        <a:ln xmlns:a="{A_URI}" w="12700">
            <a:solidFill>
                <a:srgbClr val="222222"/>
            </a:solidFill>
        </a:ln>
        """
    ).strip()


def path_clip_xml() -> str:
    """Return DrawingML clip fragment used by EMF placeholder tests."""
    return dedent(
        f"""
        <a:clipPath xmlns:a="{A_URI}">
            <a:pathLst>
                <a:path w="10000" h="5000"/>
            </a:pathLst>
        </a:clipPath>
        """
    ).strip()


__all__ = [
    "svg_with_mixed_clip_geometry",
    "svg_with_viewbox",
    "svg_batch_samples",
    "path_fill_xml",
    "path_stroke_xml",
    "path_clip_xml",
]
