#!/usr/bin/env python3
from __future__ import annotations

import pytest

from core.services.svg_font_analyzer import SVGFontAnalyzer, analyze_svg_for_fonts
from core.data.embedded_font import FontSubsetRequest


def _svg_with_embedded_font(font_family: str = "CustomSans") -> str:
    return f"""
    <svg xmlns="http://www.w3.org/2000/svg">
      <defs>
        <style>
          @font-face {{
            font-family: '{font_family}';
            font-style: normal;
            font-weight: bold;
            src: url(data:font/ttf;base64,AAAA);
          }}
        </style>
        <font id="inlineFont" horiz-origin-x="0">
          <font-face font-family="{font_family}" font-weight="bold" unicode-range="U+0020-007F"/>
        </font>
      </defs>
      <text style="font-family: '{font_family}'; font-weight: bold;">Hello!</text>
      <text>Secondary</text>
    </svg>
    """.strip()


def _svg_without_embedded_fonts() -> str:
    return """
    <svg xmlns="http://www.w3.org/2000/svg">
      <text font-family="Arial">Plain Text</text>
    </svg>
    """.strip()


class _StubFontService:
    def __init__(self, expected_family: str):
        self.expected_family = expected_family.lower()
        self.calls: list[tuple[str, str, str]] = []

    def find_font_file(self, family: str, weight: str, style: str) -> str | None:
        self.calls.append((family, weight, style))
        if family.lower() == self.expected_family:
            return f"/fonts/{family}-{weight}-{style}.ttf"
        return None


def test_analyze_svg_fonts_detects_embedded_css_font():
    svg_content = _svg_with_embedded_font()
    analyzer = SVGFontAnalyzer()

    result = analyzer.analyze_svg_fonts(svg_content)

    assert result["has_embedded_fonts"] is True
    assert result["embedded_fonts_count"] >= 1
    assert result["has_text_elements"] is True
    assert result["should_embed_fonts"] is True
    assert result["embedding_recommendation"] == "svg_has_embedded_fonts"

    # Font requirements should include CustomSans bold usage
    requirements = result["font_requirements"]
    assert "CustomSans:bold:normal" in requirements
    req = requirements["CustomSans:bold:normal"]
    assert req["total_character_count"] >= len("Hello!")
    assert req["usage_count"] >= 1
    assert req["has_embedded_data"] is True


def test_create_font_subset_requests_uses_font_service(tmp_path):
    svg_content = _svg_with_embedded_font("SubsetFont")
    analyzer = SVGFontAnalyzer()
    font_service = _StubFontService("SubsetFont")

    subset_requests = analyzer.create_font_subset_requests(svg_content, font_service=font_service)

    assert len(subset_requests) == 1
    request = subset_requests[0]
    assert isinstance(request, FontSubsetRequest)
    assert request.font_name == "SubsetFont"
    assert request.font_path.endswith("SubsetFont-bold-normal.ttf")
    assert "H" in request.characters  # characters from "Hello!"
    assert font_service.calls  # ensure service was queried


def test_create_font_subset_requests_without_embedded_fonts_returns_empty():
    analyzer = SVGFontAnalyzer()
    subset_requests = analyzer.create_font_subset_requests(_svg_without_embedded_fonts())
    assert subset_requests == []


def test_get_text_content_summary_reports_usage():
    analyzer = SVGFontAnalyzer()
    summary = analyzer.get_text_content_summary(_svg_with_embedded_font())

    assert summary["has_text"] is True
    assert summary["text_elements_count"] == 2
    assert summary["total_characters"] >= len("Hello!")
    assert "CustomSans" in summary["font_families_used"]
    assert summary["embedding_recommended"] is True


def test_analyze_svg_with_no_embedded_fonts():
    analyzer = SVGFontAnalyzer()
    result = analyzer.analyze_svg_fonts(_svg_without_embedded_fonts())

    assert result["has_embedded_fonts"] is False
    assert result["should_embed_fonts"] is False
    assert result["text_elements_count"] == 1
    assert result["embedding_recommendation"] == "no_embedded_fonts"


def test_analyze_svg_handles_invalid_svg():
    invalid_svg = "<svg><text>unclosed"
    analyzer = SVGFontAnalyzer()
    result = analyzer.analyze_svg_fonts(invalid_svg)

    assert result["has_embedded_fonts"] is False
    assert result["should_embed_fonts"] is False
    assert result["embedding_recommendation"] == "invalid_svg"
    assert "error" in result


def test_analyze_svg_for_fonts_convenience_function():
    result = analyze_svg_for_fonts(_svg_without_embedded_fonts())
    assert isinstance(result, dict)
    assert result["has_text_elements"] is True
