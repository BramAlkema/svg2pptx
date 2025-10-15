from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from core.pipeline.config import OutputFormat, PipelineConfig
from core.pipeline.file_io import FileIOContext, FileIOStrategy


def _make_embedder_result() -> SimpleNamespace:
    return SimpleNamespace(
        slide_xml="<p:sld/>",
        elements_embedded=1,
        native_elements=1,
        emf_elements=0,
        processing_time_ms=5.0,
        emu_trace_summary={"shapes": 1},
        relationship_data=[{"id": "rId1", "type": "slide"}],
        media_files=[
            {
                "filename": "ppt/media/image1.png",
                "content_type": "image/png",
                "data": b"binary",
            }
        ],
        emu_traces=[{"transform": [1, 0, 0, 1, 0, 0]}],
    )


def _make_analysis_result() -> SimpleNamespace:
    return SimpleNamespace(
        complexity_score=0.5,
        element_count=3,
        recommended_output_format=SimpleNamespace(value="pptx"),
    )


class ComposerSpy:
    def __init__(self) -> None:
        self.calls: list[tuple[list, bytes | None]] = []

    def package_to_stream(self, slides, stream, embedded_fonts=None) -> None:
        self.calls.append((list(slides), embedded_fonts))
        stream.write(b"PPTX_FROM_COMPOSER")


class PackageWriterSpy:
    def __init__(self) -> None:
        self.calls: list = []

    def write_package_stream(self, slides, stream, manifest):
        self.calls.append(manifest)
        stream.write(b"PPTX_FROM_WRITER")


def test_read_svg_and_write_output_round_trip(tmp_path: Path) -> None:
    svg_path = tmp_path / "input.svg"
    svg_path.write_text("<svg/>", encoding="utf-8")

    config = PipelineConfig(output_format=OutputFormat.PPTX)
    strategy = FileIOStrategy(
        FileIOContext(
            config=config,
            presentation_composer=None,
            package_writer=PackageWriterSpy(),
        ),
    )

    assert strategy.read_svg(str(svg_path)) == "<svg/>"

    output_path = tmp_path / "output.pptx"
    strategy.write_output(b"content", output_path, OutputFormat.PPTX)
    assert output_path.read_bytes() == b"content"


def test_resolve_output_path_defaults_and_overrides(tmp_path: Path) -> None:
    config = PipelineConfig(output_format=OutputFormat.SLIDE_XML)
    strategy = FileIOStrategy(FileIOContext(config=config, presentation_composer=None, package_writer=None))

    derived_path = strategy.resolve_output_path(str(tmp_path / "sample.svg"), None)
    assert derived_path.name == "sample.xml"

    override = tmp_path / "custom.pptx"
    resolved_override = strategy.resolve_output_path(str(tmp_path / "sample.svg"), str(override))
    assert resolved_override == override


def test_generate_output_uses_presentation_composer() -> None:
    composer = ComposerSpy()
    context = FileIOContext(
        config=PipelineConfig(output_format=OutputFormat.PPTX),
        presentation_composer=composer,
        package_writer=None,
    )
    strategy = FileIOStrategy(context)

    result = strategy.generate_output(
        embedder_results=[_make_embedder_result()],
        analysis_result=_make_analysis_result(),
        embedded_fonts=["FontA"],
    )

    assert result == b"PPTX_FROM_COMPOSER"
    assert composer.calls, "Composer was not invoked"
    slides, fonts = composer.calls[0]
    assert len(slides) == 1
    assert fonts == ["FontA"]


def test_generate_output_uses_package_writer_manifest() -> None:
    writer = PackageWriterSpy()
    context = FileIOContext(
        config=PipelineConfig(output_format=OutputFormat.PPTX),
        presentation_composer=None,
        package_writer=writer,
    )
    strategy = FileIOStrategy(context)

    result = strategy.generate_output(
        embedder_results=[_make_embedder_result()],
        analysis_result=_make_analysis_result(),
    )

    assert result == b"PPTX_FROM_WRITER"
    assert writer.calls, "Package writer was not invoked"
    manifest = writer.calls[0]
    assert manifest.slides == ["slide1.xml"]
    assert manifest.relationships
    assert manifest.media_files


def test_generate_output_debug_json_includes_font_messages() -> None:
    strategy = FileIOStrategy(
        FileIOContext(
            config=PipelineConfig(output_format=OutputFormat.DEBUG_JSON),
            presentation_composer=None,
            package_writer=None,
            consume_font_messages=lambda: ["font-warning"],
        ),
    )

    payload = strategy.generate_output(
        embedder_results=[_make_embedder_result()],
        analysis_result=_make_analysis_result(),
    )

    data = json.loads(payload.decode("utf-8"))
    assert data["analysis"]["element_count"] == 3
    assert data["embedding"]["native_elements"] == 1
    assert data["font_embedding_messages"] == ["font-warning"]


def test_generate_output_handles_multiple_slides_with_composer() -> None:
    composer = ComposerSpy()
    context = FileIOContext(
        config=PipelineConfig(output_format=OutputFormat.PPTX),
        presentation_composer=composer,
        package_writer=None,
    )
    strategy = FileIOStrategy(context)

    slides = [_make_embedder_result(), _make_embedder_result()]
    result = strategy.generate_output(
        embedder_results=slides,
        analysis_result=_make_analysis_result(),
    )

    assert result == b"PPTX_FROM_COMPOSER"
    assert composer.calls and len(composer.calls[0][0]) == 2


def test_generate_output_requires_writer_for_pptx() -> None:
    strategy = FileIOStrategy(
        FileIOContext(
            config=PipelineConfig(output_format=OutputFormat.PPTX),
            presentation_composer=None,
            package_writer=None,
        ),
    )

    with pytest.raises(ValueError):
        strategy.generate_output(
            embedder_results=[_make_embedder_result()],
            analysis_result=_make_analysis_result(),
        )
