import zipfile

import pytest

from core.data.embedded_font import EmbeddedFont
from core.io.embedder import EmbedderResult
from core.io.package_writer import PackageManifest, PackageWriter
from core.pipeline.converter import CleanSlateConverter, ConversionError
from core.pipeline.config import PipelineConfig
from core.policy.config import PolicyConfig


def make_embedder_result() -> EmbedderResult:
    """Create a minimal embedder result with a simple shape."""
    slide_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
       xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
       xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <p:cSld>
    <p:spTree>
      <p:nvGrpSpPr>
        <p:cNvPr id="1" name=""/>
        <p:cNvGrpSpPr/>
        <p:nvPr/>
      </p:nvGrpSpPr>
      <p:grpSpPr>
        <a:xfrm>
          <a:off x="0" y="0"/>
          <a:ext cx="9144000" cy="6858000"/>
          <a:chOff x="0" y="0"/>
          <a:chExt cx="9144000" cy="6858000"/>
        </a:xfrm>
      </p:grpSpPr>
      <p:sp>
        <p:nvSpPr>
          <p:cNvPr id="2" name="Title"/>
          <p:cNvSpPr/>
          <p:nvPr/>
        </p:nvSpPr>
        <p:spPr>
          <a:xfrm>
            <a:off x="914400" y="914400"/>
            <a:ext cx="7315200" cy="914400"/>
          </a:xfrm>
        </p:spPr>
        <p:txBody>
          <a:bodyPr/>
          <a:lstStyle/>
          <a:p>
            <a:r>
              <a:rPr lang="en-US" sz="3200"/>
              <a:t>Embedded Font Demo</a:t>
            </a:r>
          </a:p>
        </p:txBody>
      </p:sp>
    </p:spTree>
  </p:cSld>
  <p:clrMapOvr>
    <a:masterClrMapping/>
  </p:clrMapOvr>
</p:sld>"""

    return EmbedderResult(
        slide_xml=slide_xml,
        relationship_data=[],
        media_files=[],
        elements_embedded=1,
        native_elements=1,
        emf_elements=0,
        processing_time_ms=1.0,
        total_size_bytes=len(slide_xml.encode("utf-8")),
        estimated_quality=1.0,
        estimated_performance=1.0,
    )


def make_embedded_font() -> EmbeddedFont:
    """Create a minimal embedded font payload."""
    font_bytes = b"\x01\x23\x45\x67" * 32  # synthetic payload
    return EmbeddedFont.create_from_font(
        font_name="TestFont",
        font_data=font_bytes,
        characters={"A", "B", "C"},
        original_size=len(font_bytes) * 2,
        font_family="TestFont",
        font_weight="normal",
        font_style="normal",
    )


def test_font_embedding_roundtrip_emits_pptx_font_parts(tmp_path):
    package_writer = PackageWriter()
    embedder_result = make_embedder_result()
    embedded_font = make_embedded_font()

    manifest = PackageManifest(
        slides=["slide1.xml"],
        relationships=[],
        media_files=[],
        content_types=[],
        embedded_fonts=[embedded_font],
    )

    output_path = tmp_path / "font_demo.pptx"
    package_writer.write_package([embedder_result], str(output_path), manifest)

    with zipfile.ZipFile(output_path, "r") as archive:
        font_parts = [name for name in archive.namelist() if name.startswith("ppt/fonts/")]
        assert font_parts, "Expected PPTX to contain embedded font parts"

        presentation_xml = archive.read("ppt/presentation.xml").decode("utf-8")
        assert "<p:embeddedFontLst" in presentation_xml
        assert "TestFont" in presentation_xml

        rels_xml = archive.read("ppt/_rels/presentation.xml.rels").decode("utf-8")
        assert "fonts/" in rels_xml


def test_clean_slate_converter_embeds_fonts(tmp_path):
    svg = """<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"400\" height=\"100\">
  <text x=\"10\" y=\"60\" font-family=\"Arial\" font-size=\"48\">Font Embed</text>
</svg>"""

    converter = CleanSlateConverter()
    result = converter.convert_string(svg)

    if not result.embedded_fonts:
        pytest.skip("No embedded fonts produced; system font may be unavailable")

    output_path = tmp_path / "converter_font_demo.pptx"
    with open(output_path, "wb") as handle:
        handle.write(result.output_data)

    with zipfile.ZipFile(output_path, "r") as archive:
        font_parts = [name for name in archive.namelist() if name.startswith("ppt/fonts/")]
        assert font_parts, "Expected converter to embed fonts in PPTX"

        presentation_xml = archive.read("ppt/presentation.xml").decode("utf-8")
        assert "embeddedFont" in presentation_xml


def test_multi_weight_font_embedding_produces_variants():
    svg = """<svg xmlns="http://www.w3.org/2000/svg" width="600" height="200">
  <text x="20" y="80" font-family="Arial" font-size="48">Regular Weight</text>
  <text x="20" y="150" font-family="Arial" font-size="48" font-weight="bold">Bold Weight</text>
</svg>"""

    converter = CleanSlateConverter()
    result = converter.convert_string(svg)

    embedded = result.embedded_fonts or []
    weights = {font.font_weight for font in embedded if font.font_family and "arial" in font.font_family.lower()}

    if len(weights) < 2:
        pytest.skip("System Arial variants not available for embedding on this environment.")

    assert "regular" in weights
    assert "bold" in weights


def test_outline_fallback_for_missing_cjk_font():
    svg = """<svg xmlns="http://www.w3.org/2000/svg" width="400" height="120">
  <text x="10" y="80" font-family="MissingCJKFont" font-size="48">你好世界</text>
</svg>"""

    config = PipelineConfig(
        policy_config=PolicyConfig(font_missing_behavior="outline")
    )
    converter = CleanSlateConverter(config=config)
    result = converter.convert_string(svg)

    assert not result.embedded_fonts
    assert result.emf_elements > 0


def test_missing_font_error_mode_raises():
    svg = """<svg xmlns="http://www.w3.org/2000/svg" width="200" height="80">
  <text x="10" y="50" font-family="NoSuchFont123" font-size="24">Missing Fonts</text>
</svg>"""

    config = PipelineConfig(
        policy_config=PolicyConfig(font_missing_behavior="error")
    )
    converter = CleanSlateConverter(config=config)

    with pytest.raises(ConversionError):
        converter.convert_string(svg)
