"""
File I/O helpers for the Clean Slate converter pipeline (Phase 2D refactor).

This module centralises SVG ingestion and PPTX/debug serialization so that
`converter.py` can remain focused on orchestration logic.
"""

from __future__ import annotations

import io
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence

from ..analyze import AnalysisResult
from ..data.embedded_font import EmbeddedFont
from ..io import EmbedderResult, PackageManifest, PackageWriter
from ..presentation import PresentationComposer
from .config import OutputFormat, PipelineConfig


FontMessageConsumer = Callable[[], list[str]]


@dataclass(slots=True)
class FileIOContext:
    """Aggregates collaborators required for pipeline serialization."""

    config: PipelineConfig
    presentation_composer: PresentationComposer | None
    package_writer: PackageWriter | None
    consume_font_messages: FontMessageConsumer | None = None


class FileIOStrategy:
    """Façade for reading SVG input and writing packaged outputs."""

    def __init__(self, context: FileIOContext) -> None:
        self._context = context

    def update_context(self, context: FileIOContext) -> None:
        """Refresh collaborators when the converter reconfigures dependencies."""
        self._context = context

    def read_svg(self, svg_path: str) -> str:
        """Read SVG file contents with UTF-8 decoding."""
        return Path(svg_path).read_text(encoding='utf-8')

    def resolve_output_path(self, svg_path: str, output_path: str | None) -> Path:
        """
        Determine the output path for the converted artifact.

        Mirrors the pre-refactor behaviour by deriving the extension when the
        caller does not provide an explicit destination.
        """
        if output_path:
            return Path(output_path)

        svg_file = Path(svg_path)
        output_format = self._context.config.output_format
        if output_format == OutputFormat.PPTX:
            return svg_file.with_suffix('.pptx')
        if output_format == OutputFormat.SLIDE_XML:
            return svg_file.with_suffix('.xml')
        if output_format == OutputFormat.DEBUG_JSON:
            return svg_file.with_suffix('.json')

        # Fallback keeps legacy semantics by defaulting to `.out`
        return svg_file.with_suffix('.out')

    def write_output(self, data: bytes, output_path: Path, output_format: OutputFormat) -> None:
        """Persist converted output to disk using the correct mode."""
        if output_format == OutputFormat.PPTX:
            output_path.write_bytes(data)
            return

        text = data.decode('utf-8')
        output_path.write_text(text, encoding='utf-8')

    def generate_output(
        self,
        embedder_results: Sequence[EmbedderResult],
        analysis_result: AnalysisResult,
        embedded_fonts: list[EmbeddedFont] | None = None,
    ) -> bytes:
        """
        Produce the output payload for the configured format.

        Delegates to the presentation composer when available, otherwise falls
        back to the `PackageWriter` using a constructed package manifest.
        """
        output_format = self._context.config.output_format

        if output_format == OutputFormat.PPTX:
            return self._generate_pptx_bytes(embedder_results, embedded_fonts)

        primary = embedder_results[0] if embedder_results else None
        if primary is None:
            raise ValueError("No embedder results available for serialization.")

        if output_format == OutputFormat.SLIDE_XML:
            return primary.slide_xml.encode('utf-8')

        if output_format == OutputFormat.DEBUG_JSON:
            return self._build_debug_payload(primary, analysis_result)

        raise ValueError(f"Unsupported output format: {output_format}")

    def _generate_pptx_bytes(
        self,
        embedder_results: Sequence[EmbedderResult],
        embedded_fonts: list[EmbeddedFont] | None,
    ) -> bytes:
        presentation_composer = self._context.presentation_composer
        package_writer = self._context.package_writer

        if presentation_composer is None and package_writer is None:
            raise ValueError("Package writer is not configured for PPTX output.")

        stream = io.BytesIO()
        slide_results = list(embedder_results)

        if presentation_composer is not None:
            presentation_composer.package_to_stream(
                slide_results,
                stream,
                embedded_fonts=embedded_fonts,
            )
        else:
            assert package_writer is not None  # narrow type for mypy
            manifest = self._build_package_manifest(slide_results, embedded_fonts)
            package_writer.write_package_stream(
                slide_results,
                stream,
                manifest=manifest,
            )

        return stream.getvalue()

    def _build_debug_payload(
        self,
        embedder_result: EmbedderResult,
        analysis_result: AnalysisResult,
    ) -> bytes:
        debug_data = {
            'analysis': {
                'complexity_score': analysis_result.complexity_score,
                'element_count': analysis_result.element_count,
                'recommended_format': analysis_result.recommended_output_format.value,
            },
            'embedding': {
                'elements_embedded': embedder_result.elements_embedded,
                'native_elements': embedder_result.native_elements,
                'emf_elements': embedder_result.emf_elements,
                'processing_time_ms': embedder_result.processing_time_ms,
                'emu_trace_summary': embedder_result.emu_trace_summary,
            },
            'slide_xml': embedder_result.slide_xml,
            'relationships': embedder_result.relationship_data,
            'media_files': [
                {k: v for k, v in media.items() if k != 'data'}
                for media in embedder_result.media_files
            ],
            'emu_traces': embedder_result.emu_traces,
        }

        consume_font_messages = self._context.consume_font_messages
        if consume_font_messages:
            font_messages = consume_font_messages()
            if font_messages:
                debug_data['font_embedding_messages'] = font_messages

        return json.dumps(debug_data, indent=2).encode('utf-8')

    def _build_package_manifest(
        self,
        embedder_results: list[EmbedderResult],
        embedded_fonts: list[EmbeddedFont] | None,
    ) -> PackageManifest:
        slides = [f"slide{i + 1}.xml" for i in range(len(embedder_results))]

        relationships: list[dict[str, Any]] = []
        media_files: list[dict[str, Any]] = []
        for result in embedder_results:
            if result.relationship_data:
                relationships.extend(result.relationship_data)
            if result.media_files:
                media_files.extend(result.media_files)

        content_types: list[dict[str, str]] = []
        seen_content: set[tuple[str, str]] = set()
        for media in media_files:
            filename = media.get('filename')
            if not filename:
                continue
            extension = Path(filename).suffix.lstrip('.').lower()
            if not extension:
                continue
            content_type = media.get('content_type', 'application/octet-stream')
            key = (extension, content_type)
            if key in seen_content:
                continue
            seen_content.add(key)
            content_types.append({'extension': extension, 'content_type': content_type})

        return PackageManifest(
            slides=slides,
            relationships=relationships,
            media_files=media_files,
            content_types=content_types,
            embedded_fonts=list(embedded_fonts or []),
        )
