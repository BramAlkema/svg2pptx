#!/usr/bin/env python3
"""Fixture-driven coverage for the sliced SVGParser entry-points."""

from __future__ import annotations

from pathlib import Path

import pytest
from lxml import etree as ET

from core.parse.parser import SVGParser
from core.parse_split.models import ClipDefinition, ParseResult
from core.ir.geometry import BezierSegment, LineSegment, Point

from testing.fixtures.module_slicing import svg_with_mixed_clip_geometry


def _make_parser(enable_normalization: bool = False) -> SVGParser:
    parser = SVGParser(enable_normalization=enable_normalization)
    # Legacy helpers expect this attribute; bind it explicitly for tests.
    if not hasattr(parser, "_parse_path_data"):
        parser._parse_path_data = parser._ir_converter.parse_path_data  # type: ignore[attr-defined]
    return parser


def test_parse_fixture_collects_clip_definitions():
    parser = _make_parser()
    svg_content = svg_with_mixed_clip_geometry().replace('transform="translate(5 10)"', "")
    scene, result = parser.parse_to_ir(svg_content)

    assert result.success
    assert scene  # IR elements emitted

    # Clip definitions populated via collector and legacy helper
    clip_defs = parser._collect_clip_definitions(result.svg_root)
    assert isinstance(clip_defs, dict)
    assert "clip-complex" in clip_defs
    clip = clip_defs["clip-complex"]
    assert isinstance(clip, ClipDefinition)
    assert clip.segments
    assert clip.bounding_box is not None

    # clip-rule fallback picked from inline style
    clip_from_style = clip_defs.get("clip-style")
    assert clip_from_style is not None
    assert clip_from_style.clip_rule == "evenodd"


def test_prepare_content_normalizes_bom_and_xml_header():
    parser = _make_parser()
    original = "\ufeff   <svg xmlns='http://www.w3.org/2000/svg'></svg>"
    prepared = parser._prepare_content(original)

    assert prepared.startswith("<?xml")
    assert "\ufeff" not in prepared


def test_prepare_content_rejects_non_svg_payload():
    parser = _make_parser()
    with pytest.raises(ValueError):
        parser._prepare_content("<?xml version='1.0'?><div/>")


def test_parse_to_ir_surfaces_conversion_failure(monkeypatch):
    parser = _make_parser()
    svg = "<svg xmlns='http://www.w3.org/2000/svg' width='10' height='10'></svg>"

    monkeypatch.setattr(parser, "_convert_dom_to_ir", lambda root: (_ for _ in ()).throw(RuntimeError("boom")))

    scene, result = parser.parse_to_ir(svg)

    assert scene == []
    assert result.success is False
    assert "IR conversion failed" in (result.error or "")


def test_clip_child_to_segments_applies_transforms():
    parser = _make_parser()
    transform = parser._transform_parser.parse_to_matrix("translate(10, 5)")

    rect = ET.Element("rect", x="1", y="2", width="3", height="4")
    rect_segments = parser._clip_child_to_segments(rect, transform)
    assert isinstance(rect_segments[0], LineSegment)
    assert rect_segments[0].start == Point(11.0, 7.0)

    circle = ET.Element("circle", cx="0", cy="0", r="10")
    circle_segments = parser._clip_child_to_segments(circle, transform)
    assert isinstance(circle_segments[0], BezierSegment)
    assert circle_segments[0].start == Point(20.0, 5.0)

    path = ET.Element("path", d="M0 0 L10 0 L10 10 z")
    path_segments = parser._clip_child_to_segments(path, transform)
    assert isinstance(path_segments[0], LineSegment)
    assert path_segments[0].start == Point(10.0, 5.0)


def test_compute_segments_bbox_returns_bounds():
    parser = _make_parser()
    segments = [
        LineSegment(Point(0, 0), Point(10, 0)),
        LineSegment(Point(10, 0), Point(10, 5)),
    ]
    bbox = parser._compute_segments_bbox(segments)
    assert bbox.width == 10
    assert bbox.height == 5


def test_legacy_conversion_helpers_emit_ir_objects():
    parser = _make_parser()
    svg_root = ET.fromstring(svg_with_mixed_clip_geometry())
    parser._style_context = parser._create_style_context(svg_root)
    parser._clip_definitions = parser._collect_clip_definitions(svg_root)

    rect = ET.Element("rect", width="10", height="10")
    ir_rect = parser._convert_rect_to_ir(rect)
    assert ir_rect is not None
    assert hasattr(ir_rect, "bbox")

    text = ET.Element("text")
    text.text = "demo"
    ir_text = parser._convert_text_to_ir(text)
    assert ir_text is not None
    assert ir_text.runs


def test_parse_inline_navigation_handles_slide_links():
    parser = _make_parser()
    anchor = ET.Element("a", attrib={"data-slide": "3", "href": "#slide"})
    navigation = parser._parse_inline_navigation(anchor)
    assert navigation is not None
    assert navigation.slide.index == 3


def test_parse_from_file_uses_latin1_fallback(tmp_path: Path):
    parser = _make_parser()
    payload = "<svg xmlns='http://www.w3.org/2000/svg'><text>café</text></svg>"
    file_path = tmp_path / "latin1.svg"
    file_path.write_bytes(payload.encode("latin-1"))

    result = parser.parse_from_file(str(file_path))
    assert result.success
    assert result.svg_root is not None


def test_extract_clip_rule_from_style_parses_declaration():
    assert SVGParser._extract_clip_rule_from_style("fill:red; clip-rule:evenodd;") == "evenodd"
    assert SVGParser._extract_clip_rule_from_style(None) is None


def test_parse_handles_xml_syntax_error(monkeypatch):
    parser = _make_parser()

    def boom(_content):
        raise ET.XMLSyntaxError("broken", 0, 0, 0)

    monkeypatch.setattr(parser._xml_parser, "parse", boom)

    result = parser.parse("<svg>")

    assert result.success is False
    assert "XML syntax error" in (result.error or "")


def test_parse_handles_generic_exception(monkeypatch):
    parser = _make_parser()
    monkeypatch.setattr(parser._xml_parser, "parse", lambda *_: (_ for _ in ()).throw(RuntimeError("unexpected")))

    result = parser.parse("<svg>")

    assert result.success is False
    assert "Parse error" in (result.error or "")


def test_parse_to_ir_returns_parse_failure(monkeypatch):
    parser = _make_parser()
    failure = ParseResult(success=False, error="nope", processing_time_ms=0.1)
    monkeypatch.setattr(parser, "parse", lambda content: failure)

    scene, result = parser.parse_to_ir("<svg></svg>")

    assert scene == []
    assert result is failure


def test_legacy_traverse_initializes_style_context():
    parser = _make_parser()
    parser._style_context = None
    parser._clip_definitions = {}
    group = ET.Element("g")
    ET.SubElement(group, "rect", width="5", height="5")

    ir_nodes = parser._legacy_traverse(group, navigation=None)

    assert parser._style_context is not None
    assert isinstance(ir_nodes, list)


def test_parse_records_stats_and_external_refs(monkeypatch):
    parser = _make_parser(enable_normalization=True)
    svg_content = """
        <svg xmlns="http://www.w3.org/2000/svg" width="10" height="20">
            <image href="http://example.com/image.png" width="5" height="5"/>
            <style>@import url("http://example.com/style.css");</style>
            <text font-family="url(http://example.com/fonts.ttf)">hello</text>
        </svg>
    """

    monkeypatch.setattr(parser._xml_parser, "collect_statistics", lambda root: {"element_count": 3, "namespace_count": 1})
    monkeypatch.setattr(parser._validator, "validate", lambda root: None)
    monkeypatch.setattr(parser.normalizer, "normalize", lambda root: (root, {"normalized": True}))

    clip_def = ClipDefinition(
        clip_id="stub",
        segments=(LineSegment(Point(0, 0), Point(1, 0)),),
        bounding_box=None,
        clip_rule=None,
        transform=None,
    )
    monkeypatch.setattr(parser._clip_extractor, "collect", lambda root, _: {"stub": clip_def})

    scene, result = parser.parse_to_ir(svg_content)

    assert result.success
    assert result.element_count == 3
    assert result.namespace_count == 1
    assert result.has_external_references is True
    assert result.normalization_changes == {"normalized": True}
    assert parser._clip_definitions["stub"] == clip_def
    assert scene


def test_prepare_content_empty_raises():
    parser = _make_parser()
    with pytest.raises(ValueError):
        parser._prepare_content("   ")


def test_prepare_content_respects_existing_declaration():
    parser = _make_parser()
    content = "<?xml version='1.0'?><svg></svg>"
    assert parser._prepare_content(content) == content


def test_validate_svg_structure_flags_namespace(caplog):
    parser = _make_parser()
    svg = ET.Element("svg")
    parser._validate_svg_structure(svg)
    assert "SVG namespace not found" in caplog.text


def test_extract_namespaces_adds_defaults():
    parser = _make_parser()
    svg = ET.Element("{http://www.w3.org/2000/svg}svg", nsmap={"xlink": "http://www.w3.org/1999/xlink"})
    namespaces = parser._extract_namespaces(svg)
    assert namespaces[None] == "http://www.w3.org/2000/svg"
    assert namespaces["xlink"] == "http://www.w3.org/1999/xlink"


def test_parse_from_file_defaults_to_utf8(tmp_path: Path):
    parser = _make_parser()
    file_path = tmp_path / "sample.svg"
    file_path.write_text("<svg xmlns='http://www.w3.org/2000/svg'></svg>", encoding="utf-8")

    result = parser.parse_from_file(str(file_path))
    assert result.success


def test_parse_from_file_handles_missing_file(tmp_path: Path):
    parser = _make_parser()
    missing = tmp_path / "missing.svg"
    result = parser.parse_from_file(str(missing))
    assert result.success is False
    assert "Failed to read file" in (result.error or "")


def test_parse_from_file_unicode_error_secondary_failure(monkeypatch):
    parser = _make_parser()

    def fake_open(path, mode="r", encoding=None):
        if encoding == "utf-8":
            raise UnicodeDecodeError("utf-8", b"", 0, 1, "bad byte")
        raise OSError("no latin1 either")

    monkeypatch.setattr("builtins.open", fake_open)

    result = parser.parse_from_file("fake.svg")
    assert result.success is False
    assert "Failed to read file fake.svg" in (result.error or "")


def test_filter_service_registration(monkeypatch):
    parser = _make_parser()
    registered = {}
    monkeypatch.setattr(parser._ir_converter, "register_filter_service", lambda service: registered.setdefault("service", service))

    parser.filter_service = "filters"
    assert registered["service"] == "filters"


def test_convert_dom_to_ir_handles_none():
    parser = _make_parser()
    assert parser._convert_dom_to_ir(None) == []


def test_convert_group_to_ir_traverses_children():
    parser = _make_parser()
    parser._style_context = None
    parser._clip_definitions = {}
    group = ET.Element("g")
    ET.SubElement(group, "rect", width="2", height="2")
    ET.SubElement(group, "text").text = "hi"

    result = parser._convert_group_to_ir(group)
    assert result is not None
    assert len(result.children) >= 1  # type: ignore[attr-defined]


def test_set_normalization_enabled_instantiates_normalizer():
    parser = _make_parser(enable_normalization=False)
    parser.normalizer = None
    parser.set_normalization_enabled(True)
    assert parser.normalizer is not None


def test_parse_xml_helper_wraps_xml_parser():
    parser = _make_parser()
    root = parser._parse_xml("<svg xmlns='http://www.w3.org/2000/svg'></svg>")
    assert root.tag.endswith("svg")


def test_collect_clip_definitions_skips_invalid_entries():
    parser = _make_parser()
    svg = ET.fromstring(
        """
        <svg xmlns="http://www.w3.org/2000/svg">
            <defs>
                <clipPath>
                    <rect width="0" height="0"/>
                </clipPath>
                <clipPath id="valid">
                    <polyline points="0,0 5,5"/>
                </clipPath>
            </defs>
        </svg>
        """
    )

    definitions = parser._collect_clip_definitions(svg)
    assert "valid" in definitions


def test_collect_clip_definitions_handles_xpath_error():
    parser = _make_parser()

    class DummyRoot:
        nsmap: dict[str, str] = {}

        @staticmethod
        def xpath(*_args, **_kwargs):
            raise RuntimeError("xpath failure")

    assert parser._collect_clip_definitions(DummyRoot()) == {}


def test_convert_helpers_cover_shapes():
    parser = _make_parser()
    parser._style_context = parser._create_style_context(ET.fromstring("<svg xmlns='http://www.w3.org/2000/svg' width='10' height='10'></svg>"))
    parser._clip_definitions = {}

    circle = ET.Element("circle", cx="1", cy="1", r="1")
    ellipse = ET.Element("ellipse", cx="1", cy="1", rx="1", ry="2")
    line = ET.Element("line", x1="0", y1="0", x2="1", y2="1")
    path = ET.Element("path", d="M0 0 L1 1")
    polygon = ET.Element("polygon", points="0,0 1,0 1,1")
    polyline = ET.Element("polyline", points="0,0 1,0 1,1")
    image = ET.Element("image", href="data:image/png;base64,AA==", width="1", height="1")
    foreign = ET.Element("foreignObject")

    assert parser._convert_circle_to_ir(circle) is not None
    assert parser._convert_ellipse_to_ir(ellipse) is not None
    assert parser._convert_line_to_ir(line) is not None
    assert parser._convert_path_to_ir(path) is not None
    assert parser._convert_polygon_to_ir(polygon) is not None
    assert parser._convert_polygon_to_ir(polyline, closed=False) is not None
    assert parser._convert_image_to_ir(image) is not None
    assert parser._convert_foreignobject_to_ir(foreign) is None  # placeholder path returns None


def test_collect_clip_definitions_allows_missing_segments():
    parser = _make_parser()
    svg = ET.fromstring(
        """
        <svg xmlns="http://www.w3.org/2000/svg">
            <defs>
                <clipPath id="empty">
                    <rect width="0" height="0"/>
                </clipPath>
            </defs>
        </svg>
        """
    )
    assert parser._collect_clip_definitions(svg) == {}


def test_validate_svg_structure_raises_for_non_svg():
    parser = _make_parser()
    with pytest.raises(ValueError):
        parser._validate_svg_structure(ET.Element("g"))
