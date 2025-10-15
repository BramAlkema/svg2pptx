from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, BinaryIO, Iterable, List, Optional, Sequence, TYPE_CHECKING

from ..io import DrawingMLEmbedder, EmbedderResult, PackageManifest, PackageWriter

if TYPE_CHECKING:
    from ..ir import SceneGraph
    from ..map.base import MapperResult
    from ..services.conversion_services import ConversionServices
    from ..data.embedded_font import EmbeddedFont


@dataclass
class AssetEmbedder:
    """Coordinate asset preparation across slides before packaging."""

    prepared_assets: list[dict[str, Any]] = field(default_factory=list)
    tracked_fonts: dict[tuple[str, str, str], dict[str, Any]] = field(default_factory=dict)
    tracked_images: dict[str, dict[str, Any]] = field(default_factory=dict)
    slides: list[dict[str, Any]] = field(default_factory=list)

    def prepare_scene_assets(
        self,
        scene: "SceneGraph | None",
        mapper_results: Sequence["MapperResult"],
    ) -> dict[str, Any]:
        """Collect asset metadata for a single scene."""
        slide_index = len(self.slides) + 1

        fonts = self._collect_fonts(mapper_results, slide_index)
        images = self._collect_images(mapper_results, slide_index)

        assets = {
            "index": slide_index,
            "fonts": fonts,
            "images": images,
            "has_scene": scene is not None,
        }

        mapper_meta: list[dict[str, Any]] = []
        for result in mapper_results:
            mapper_meta.append(
                {
                    "element_type": type(result.element).__name__ if result.element else None,
                    "output_format": getattr(result.output_format, "value", str(result.output_format)),
                    "media_files": list(result.media_files or []),
                    "metadata": dict(result.metadata),
                },
            )
        assets["mapper_metadata"] = mapper_meta

        assets["media_count"] = sum(len(entry.get("media_files", [])) for entry in mapper_meta)

        self.slides.append(assets)
        self.prepared_assets.append(assets)
        return assets

    def reset(self) -> None:
        """Clear accumulated asset records so composers can reuse the instance."""
        self.prepared_assets.clear()
        self.tracked_fonts.clear()
        self.tracked_images.clear()
        self.slides.clear()

    def iter_tracked_fonts(self) -> Iterable[dict[str, Any]]:
        """Yield tracked font metadata."""
        for font in self.tracked_fonts.values():
            yield {
                "font_name": font.get("font_name"),
                "font_family": font.get("font_family"),
                "font_weight": font.get("font_weight", "regular"),
                "font_style": font.get("font_style", "normal"),
                "characters": sorted(font.get("characters", [])),
                "embedded_size": font.get("embedded_size", 0),
                "original_size": font.get("original_size", 0),
                "slides": sorted(font.get("slides", [])),
            }

    def iter_tracked_images(self) -> Iterable[dict[str, Any]]:
        """Yield tracked image metadata."""
        for image in self.tracked_images.values():
            yield dict(image)

    def register_embedded_fonts(
        self,
        fonts: Sequence["EmbeddedFont"],
        slide_index: int | None = None,
    ) -> None:
        """Record embedded fonts produced by the converter pipeline."""
        for font in fonts or []:
            family = font.font_family or font.font_name
            weight = font.font_weight or "regular"
            style = font.font_style or "normal"

            if not family:
                continue

            key = (family, weight, style)
            if not key:
                continue

            tracked = self.tracked_fonts.setdefault(
                key,
                {
                    "font_name": font.font_name,
                    "font_family": family,
                    "font_weight": weight,
                    "font_style": style,
                    "original_size": font.original_size,
                    "embedded_size": font.embedded_size,
                    "characters": set(),
                    "slides": [],
                },
            )

            tracked["embedded_size"] = font.embedded_size
            tracked["original_size"] = font.original_size
            tracked["characters"].update(font.subset_characters)

            if slide_index is not None and slide_index not in tracked["slides"]:
                tracked["slides"].append(slide_index)

            if slide_index is not None and 0 < slide_index <= len(self.slides):
                slide_record = self.slides[slide_index - 1]
                slide_fonts = slide_record.setdefault("fonts", [])
                if not any(
                    entry.get("font_name") == font.font_name
                    and entry.get("font_weight") == weight
                    and entry.get("font_style") == style
                    for entry in slide_fonts
                ):
                    slide_fonts.append(
                        {
                            "font_name": font.font_name,
                            "font_family": family,
                            "font_weight": weight,
                            "font_style": style,
                            "characters": sorted(font.subset_characters),
                            "embedded_size": font.embedded_size,
                        },
                    )

    def _collect_fonts(self, mapper_results: Sequence["MapperResult"], slide_index: int) -> list[dict[str, Any]]:
        fonts = []

        for result in mapper_results:
            font_info = result.metadata.get("font_embedding")
            if not font_info:
                continue

            cache_key = font_info.get("cache_key") or font_info.get("font_name")
            if not cache_key:
                continue

            tracked = self.tracked_fonts.setdefault(
                cache_key,
                {
                    "font_name": font_info.get("font_name"),
                    "cache_key": cache_key,
                    "original_size": font_info.get("original_size"),
                    "characters": set(),
                    "slides": [],
                },
            )

            characters = font_info.get("characters") or []
            tracked["characters"].update(characters)
            tracked["slides"].append(slide_index)

            fonts.append(
                {
                    "font_name": font_info.get("font_name"),
                    "cache_key": cache_key,
                    "characters": list(characters),
                },
            )

        return fonts

    def _collect_images(self, mapper_results: Sequence["MapperResult"], slide_index: int) -> list[dict[str, Any]]:
        images = []

        for result in mapper_results:
            for media in result.media_files or []:
                if not media:
                    continue

                filename = media.get("filename")
                if not filename:
                    continue

                tracked = self.tracked_images.setdefault(
                    filename,
                    {
                        "filename": filename,
                        "content_type": media.get("content_type"),
                        "slides": [],
                        "source": media.get("source"),
                    },
                )
                tracked["slides"].append(slide_index)

                images.append(
                    {
                        "filename": filename,
                        "content_type": media.get("content_type"),
                        "source": media.get("source"),
                    },
                )

        return images


class SlideAssembler:
    """Wraps DrawingMLEmbedder so higher-level builders can orchestrate slides."""

    def __init__(self, embedder: DrawingMLEmbedder | None = None):
        self.embedder = embedder

    def configure(
        self,
        *,
        slide_width_emu: int | None = None,
        slide_height_emu: int | None = None,
        services: "ConversionServices | None" = None,
    ) -> None:
        """Ensure the underlying embedder matches the pipeline geometry and services."""
        if self.embedder is None:
            if services is None or slide_width_emu is None or slide_height_emu is None:
                raise RuntimeError(
                    "SlideAssembler.configure requires services and slide dimensions when no embedder is set.",
                )
            self.embedder = DrawingMLEmbedder(
                slide_width_emu=slide_width_emu,
                slide_height_emu=slide_height_emu,
                services=services,
            )
            return

        if slide_width_emu is not None or slide_height_emu is not None:
            width = slide_width_emu if slide_width_emu is not None else self.embedder.slide_width_emu
            height = slide_height_emu if slide_height_emu is not None else self.embedder.slide_height_emu
            self.embedder.set_slide_dimensions(width, height)

        if services is not None:
            self.embedder.attach_services(services)

    def assemble_scene(
        self,
        scene: "SceneGraph",
        mapper_results: List["MapperResult"],
        animation_xml: str | None = None,
    ) -> EmbedderResult:
        """Produce a slide via the wrapped embedder."""
        embedder = self._require_embedder()
        return embedder.embed_scene(scene, mapper_results, animation_xml=animation_xml)

    def assemble_elements(
        self,
        mapper_results: List["MapperResult"],
    ) -> EmbedderResult:
        """Produce a slide when no IR scene is available."""
        embedder = self._require_embedder()
        return embedder.embed_elements(mapper_results)

    def _require_embedder(self) -> DrawingMLEmbedder:
        if self.embedder is None:
            raise RuntimeError("SlideAssembler requires an embedded DrawingMLEmbedder instance.")
        return self.embedder


class PresentationComposer:
    """Coordinates slide assembly, asset preparation, and final PPTX packaging."""

    def __init__(
        self,
        *,
        slide_assembler: SlideAssembler | None = None,
        package_writer: PackageWriter | None = None,
        asset_embedder: AssetEmbedder | None = None,
    ):
        self.slide_assembler = slide_assembler or SlideAssembler()
        writer = package_writer or PackageWriter()
        self.package_assembler = PackageAssembler(writer)
        self.package_writer = writer
        self.asset_embedder = asset_embedder or AssetEmbedder()

    def configure_pipeline(
        self,
        *,
        slide_width_emu: int,
        slide_height_emu: int,
        services: "ConversionServices",
    ) -> None:
        """Align the slide assembler with pipeline geometry/services."""
        self.slide_assembler.configure(
            slide_width_emu=slide_width_emu,
            slide_height_emu=slide_height_emu,
            services=services,
        )

    def assemble_scene(
        self,
        scene: "SceneGraph",
        mapper_results: List["MapperResult"],
        animation_xml: str | None = None,
    ) -> EmbedderResult:
        """Prepare scene assets and assemble a slide."""
        self.asset_embedder.prepare_scene_assets(scene, mapper_results)
        return self.slide_assembler.assemble_scene(scene, mapper_results, animation_xml=animation_xml)

    def assemble_elements(
        self,
        mapper_results: List["MapperResult"],
    ) -> EmbedderResult:
        """Assemble slide elements without a scene."""
        self.asset_embedder.prepare_scene_assets(None, mapper_results)
        return self.slide_assembler.assemble_elements(mapper_results)

    def package_to_stream(
        self,
        embedder_results: list[EmbedderResult],
        stream: BinaryIO,
        embedded_fonts: Sequence["EmbeddedFont"] | None = None,
    ) -> dict[str, Any]:
        """Write the composed presentation to an in-memory stream."""
        return self.package_assembler.write_stream(embedder_results, stream, embedded_fonts)

    def package_to_path(
        self,
        embedder_results: list[EmbedderResult],
        output_path: str,
        embedded_fonts: Sequence["EmbeddedFont"] | None = None,
    ) -> dict[str, Any]:
        """Write the composed presentation to disk."""
        return self.package_assembler.write_path(embedder_results, output_path, embedded_fonts)
@dataclass
class PackageAssembler:
    """Assemble manifests and delegate writing to the package writer."""

    package_writer: PackageWriter

    def build_manifest(
        self,
        embedder_results: list[EmbedderResult],
        embedded_fonts: Sequence["EmbeddedFont"] | None = None,
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

    def write_stream(
        self,
        embedder_results: list[EmbedderResult],
        stream: BinaryIO,
        embedded_fonts: Sequence["EmbeddedFont"] | None = None,
    ) -> dict[str, Any]:
        manifest = self.build_manifest(embedder_results, embedded_fonts)
        return self.package_writer.write_package_stream(embedder_results, stream, manifest=manifest)

    def write_path(
        self,
        embedder_results: list[EmbedderResult],
        output_path: str,
        embedded_fonts: Sequence["EmbeddedFont"] | None = None,
    ) -> dict[str, Any]:
        manifest = self.build_manifest(embedder_results, embedded_fonts)
        return self.package_writer.write_package(embedder_results, output_path, manifest)
