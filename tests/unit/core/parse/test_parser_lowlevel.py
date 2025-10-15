#!/usr/bin/env python3
from __future__ import annotations

import pytest
from lxml import etree as ET

from core.parse.parser import SVGParser
from core.pipeline.navigation import NavigationKind
from core.ir import Circle, Ellipse, Group, Path, Rectangle, RichTextFrame, TextFrame


def _make_parser() -> SVGParser:
    parser = SVGParser(enable_normalization=False)
    stub_root = ET.Element("svg", width="100", height="50")
    parser._style_context = parser._create_style_context(stub_root)
    parser.coord_space.reset_to_viewport()
    return parser


class TestPrepareContent:
    def test_adds_xml_header_and_strips_bom(self):
        parser = SVGParser()
        content = "\ufeff   <svg width='1' height='1'></svg>  "

        prepared = parser._prepare_content(content)

        assert prepared.startswith("<?xml version=\"1.0\" encoding=\"UTF-8\"?>")
        assert "<svg" in prepared

    def test_rejects_empty_or_non_svg_input(self):
        parser = SVGParser()

        with pytest.raises(ValueError):
            parser._prepare_content("  ")

        with pytest.raises(ValueError):
            parser._prepare_content("<div></div>")


class TestCollectClipDefinitions:
    def test_collects_segments_and_clip_rule(self):
        parser = _make_parser()
        svg_markup = """
        <svg xmlns="http://www.w3.org/2000/svg">
          <defs>
            <clipPath id="rectClip">
              <rect x="0" y="0" width="10" height="5"/>
            </clipPath>
            <clipPath id="translated">
              <rect x="0" y="0" width="4" height="4" transform="translate(2,3)"/>
            </clipPath>
            <clipPath id="styled" style="clip-rule:evenodd">
              <polygon points="0,0 6,0 6,6 0,6"/>
            </clipPath>
            <clipPath>
              <rect x="0" y="0" width="1" height="1"/>
            </clipPath>
          </defs>
        </svg>
        """
        svg_root = ET.fromstring(svg_markup)

        clip_defs = parser._collect_clip_definitions(svg_root)

        assert set(clip_defs) == {"rectClip", "translated", "styled"}

        rect_clip = clip_defs["rectClip"]
        assert len(rect_clip.segments) == 4
        assert rect_clip.bounding_box.width == pytest.approx(10)
        assert rect_clip.bounding_box.height == pytest.approx(5)

        translated = clip_defs["translated"]
        assert translated.bounding_box.x == pytest.approx(2)
        assert translated.bounding_box.y == pytest.approx(3)
        assert translated.bounding_box.width == pytest.approx(4)
        assert translated.bounding_box.height == pytest.approx(4)

        styled = clip_defs["styled"]
        assert styled.clip_rule == "evenodd"


class TestInlineNavigation:
    def test_data_slide_attributes_produce_navigation_spec(self):
        parser = SVGParser()
        anchor = ET.Element(
            "a",
            attrib={
                "data-slide": "3",
                "data-visited": "false",
            },
        )
        title = ET.SubElement(anchor, "title")
        title.text = "Go to slide"

        navigation = parser._parse_inline_navigation(anchor)

        assert navigation is not None
        assert navigation.kind is NavigationKind.SLIDE
        assert navigation.slide.index == 3
        assert navigation.visited is False
        assert navigation.tooltip == "Go to slide"

    def test_invalid_navigation_attributes_are_ignored(self, caplog):
        parser = SVGParser()
        caplog.set_level("WARNING")
        anchor = ET.Element("a", attrib={"data-slide": "bogus"})

        navigation = parser._parse_inline_navigation(anchor)

        assert navigation is None
        assert "Failed to parse navigation attributes" in caplog.text


class TestGeometryConversion:
    def test_rect_native_vs_path_fallback(self):
        parser = _make_parser()

        native_rect = ET.Element(
            "rect",
            attrib={"x": "10", "y": "20", "width": "30", "height": "40"},
        )
        result = parser._convert_rect_to_ir(native_rect)

        assert isinstance(result, Rectangle)
        assert result.bounds.x == pytest.approx(10)
        assert result.bounds.y == pytest.approx(20)
        assert result.bounds.width == pytest.approx(30)
        assert result.bounds.height == pytest.approx(40)

        clipped_rect = ET.Element(
            "rect",
            attrib={
                "x": "0",
                "y": "0",
                "width": "5",
                "height": "5",
                "clip-path": "url(#c)",
            },
        )
        clipped = parser._convert_rect_to_ir(clipped_rect)
        assert isinstance(clipped, Path)
        assert len(clipped.segments) >= 4

    def test_circle_native_geometry(self):
        parser = _make_parser()

        native_circle = ET.Element(
            "circle",
            attrib={"cx": "5", "cy": "6", "r": "4"},
        )
        result = parser._convert_circle_to_ir(native_circle)

        assert isinstance(result, Circle)
        assert result.center.x == pytest.approx(5)
        assert result.center.y == pytest.approx(6)
        assert result.radius == pytest.approx(4)

    def test_circle_mask_fallback_returns_path(self):
        parser = _make_parser()

        masked_circle = ET.Element(
            "circle",
            attrib={"cx": "0", "cy": "0", "r": "3", "mask": "url(#m)"},
        )

        fallback = parser._convert_circle_to_ir(masked_circle)

        assert isinstance(fallback, Path)
        assert len(fallback.segments) == 4


class TestEllipseConversion:
    def test_native_ellipse_preserves_radii(self):
        parser = _make_parser()

        ellipse_el = ET.Element(
            "ellipse",
            attrib={"cx": "10", "cy": "20", "rx": "5", "ry": "3"},
        )

        result = parser._convert_ellipse_to_ir(ellipse_el)

        assert isinstance(result, Ellipse)
        assert result.center.x == pytest.approx(10)
        assert result.center.y == pytest.approx(20)
        assert result.radius_x == pytest.approx(5)
        assert result.radius_y == pytest.approx(3)

    def test_ellipse_with_mask_falls_back_to_path(self):
        parser = _make_parser()

        masked = ET.Element(
            "ellipse",
            attrib={"cx": "0", "cy": "0", "rx": "4", "ry": "2", "mask": "url(#m)"},
        )

        fallback = parser._convert_ellipse_to_ir(masked)

        assert isinstance(fallback, Path)
        assert len(fallback.segments) == 4


class TestPathConversion:
    def test_simple_path_generates_segments(self):
        parser = _make_parser()

        path_el = ET.Element("path", attrib={"d": "M0 0 L10 0 L10 10 Z"})
        result = parser._convert_path_to_ir(path_el)

        assert isinstance(result, Path)
        assert len(result.segments) >= 2

    def test_missing_path_data_returns_none(self):
        parser = _make_parser()
        empty_path = ET.Element("path")

        assert parser._convert_path_to_ir(empty_path) is None


class TestImageConversion:
    def test_image_with_href_sets_origin_and_format(self):
        parser = _make_parser()

        image_el = ET.Element(
            "image",
            attrib={
                "x": "1",
                "y": "2",
                "width": "3",
                "height": "4",
                "href": "assets/photo.jpg",
            },
        )

        result = parser._convert_image_to_ir(image_el)

        assert result is not None
        assert result.format == "jpg"
        assert result.href.endswith("photo.jpg")
        assert result.origin.x == pytest.approx(1)
        assert result.origin.y == pytest.approx(2)
        assert result.size.width == pytest.approx(3)
        assert result.size.height == pytest.approx(4)

    def test_image_without_href_returns_none(self):
        parser = _make_parser()
        image_el = ET.Element(
            "image",
            attrib={"x": "0", "y": "0", "width": "1", "height": "1"},
        )

        assert parser._convert_image_to_ir(image_el) is None


class TestGroupConversion:
    def test_group_collects_children_and_transform(self):
        parser = _make_parser()

        group_el = ET.Element("g", attrib={"transform": "translate(10,5)"})
        ET.SubElement(
            group_el,
            "rect",
            attrib={"x": "0", "y": "0", "width": "2", "height": "3"},
        )

        result = parser._convert_group_to_ir(group_el)

        assert isinstance(result, Group)
        assert len(result.children) == 1
        assert result.transform is not None
        assert result.transform.shape == (3, 3)
        assert result.transform[0, 2] == pytest.approx(10)
        assert result.transform[1, 2] == pytest.approx(5)
        assert result.clip is None


class TestTextConversion:
    def test_simple_text_produces_text_frame(self):
        parser = _make_parser()
        text_el = ET.Element("text", attrib={"x": "0", "y": "0"})
        text_el.text = "Hello"

        frame = parser._convert_text_to_ir(text_el)

        assert isinstance(frame, TextFrame)
        assert frame.runs
        assert frame.runs[0].text == "Hello"
        assert frame.runs[0].navigation is None

    def test_complex_text_uses_rich_text_frame(self):
        parser = _make_parser()
        complex_text = ET.fromstring(
            "<text x='0' y='0'>"
            "<tspan>Line1</tspan>"
            "<tspan x='0' y='20'>Line2</tspan>"
            "</text>"
        )

        frame = parser._convert_text_to_ir(complex_text)

        assert isinstance(frame, RichTextFrame)
        assert frame.line_count == 2
        assert frame.lines[0].runs[0].text == "Line1"
        assert frame.lines[1].runs[0].text == "Line2"

    def test_anchor_runs_receive_navigation_spec(self):
        parser = _make_parser()
        text_el = ET.fromstring(
            "<text x='0' y='0'>"
            "<a data-slide='5'>Jump</a>"
            "</text>"
        )

        frame = parser._convert_text_to_ir(text_el)

        assert frame.runs
        run = frame.runs[0]
        assert run.text == "Jump"
        assert run.navigation is not None
        assert run.navigation.kind is NavigationKind.SLIDE
        assert run.navigation.slide.index == 5


class TestForeignObjectConversion:
    def test_nested_svg_payload_creates_clipped_group(self):
        parser = _make_parser()
        foreign_el = ET.fromstring(
            """
            <foreignObject x="0" y="0" width="10" height="12">
              <svg xmlns="http://www.w3.org/2000/svg">
                <rect x="0" y="0" width="4" height="4"/>
              </svg>
            </foreignObject>
            """
        )

        result = parser._convert_foreignobject_to_ir(foreign_el)

        assert isinstance(result, Group)
        assert result.clip is not None
        assert result.clip.clip_id.startswith("bbox:")
        assert result.clip.bounding_box.width == pytest.approx(10)
        assert result.clip.bounding_box.height == pytest.approx(12)
        assert result.children
