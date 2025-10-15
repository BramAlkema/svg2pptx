import zipfile

from core.io.embedder import EmbedderResult
from core.io.package_writer import PackageWriter
from core.pipeline.converter import CleanSlateConverter


def make_embedder_result_with_image(image_bytes: bytes) -> EmbedderResult:
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
      <p:pic>
        <p:nvPicPr>
          <p:cNvPr id="2" name="Picture"/>
          <p:cNvPicPr/>
          <p:nvPr/>
        </p:nvPicPr>
        <p:blipFill>
          <a:blip r:embed="rIdImage1"/>
          <a:stretch>
            <a:fillRect/>
          </a:stretch>
        </p:blipFill>
        <p:spPr>
          <a:xfrm>
            <a:off x="0" y="0"/>
            <a:ext cx="3048000" cy="2286000"/>
          </a:xfrm>
        </p:spPr>
      </p:pic>
    </p:spTree>
  </p:cSld>
  <p:clrMapOvr>
    <a:masterClrMapping/>
  </p:clrMapOvr>
</p:sld>"""

    media_entry = {
        "filename": "image1.png",
        "content_type": "image/png",
        "data": image_bytes,
        "relationship_id": "rIdImage1",
    }

    relationship = {
        "id": "rIdImage1",
        "type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image",
        "target": "../media/image1.png",
        "content_type": "image/png",
        "element_type": "PicElement",
        "fallback_reason": "image",
    }

    return EmbedderResult(
        slide_xml=slide_xml,
        relationship_data=[relationship],
        media_files=[media_entry],
        elements_embedded=1,
        native_elements=1,
        emf_elements=0,
        processing_time_ms=1.0,
        total_size_bytes=len(slide_xml.encode("utf-8")) + len(image_bytes),
        estimated_quality=1.0,
        estimated_performance=1.0,
    )


def test_image_embedding_persists_media(tmp_path):
    image_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32  # minimal PNG header with padding
    embedder_result = make_embedder_result_with_image(image_bytes)

    package_writer = PackageWriter()
    output_path = tmp_path / "image_demo.pptx"
    package_writer.write_package([embedder_result], str(output_path))

    with zipfile.ZipFile(output_path, "r") as archive:
        media_files = [name for name in archive.namelist() if name.startswith("ppt/media/image1")]
        assert media_files, "Expected packaged PPTX to include the embedded image"

        stored_image = archive.read(media_files[0])
        assert stored_image.startswith(b"\x89PNG"), "Stored media should retain PNG signature"

        slide_xml = archive.read("ppt/slides/slide1.xml").decode("utf-8")
        assert 'r:embed="rIdImage1"' in slide_xml


def test_image_pipeline_generates_real_media(tmp_path):
    svg = """<svg xmlns="http://www.w3.org/2000/svg" width="4000" height="3000">
  <image href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/lHvvYwAAAABJRU5ErkJggg==" width="4000" height="3000" />
</svg>"""

    converter = CleanSlateConverter()
    result = converter.convert_string(svg)

    assert result.output_data, "Expected PPTX payload from converter"
    assert result.media_files == 1
    assert result.relationships == 1

    embed_media = result.embedder_result.media_files
    assert embed_media and embed_media[0]["filename"].startswith("image"), "Media entry should record a filename"

    output_path = tmp_path / "pipeline_image_demo.pptx"
    with open(output_path, "wb") as f:
        f.write(result.output_data)

    with zipfile.ZipFile(output_path, "r") as archive:
        media_entries = [name for name in archive.namelist() if name.startswith("ppt/media/image")]
        assert media_entries, "Converted PPTX should contain packaged media"

        slide_xml = archive.read("ppt/slides/slide1.xml").decode("utf-8")
        assert 'r:embed="' in slide_xml, "Slide XML should reference the embedded media relationship"

    assets = converter.presentation_composer.asset_embedder.prepared_assets
    assert assets and assets[0]["images"], "AssetEmbedder should record processed images"
