"""
Shared resource management for the converter pipeline.

Consolidates font/image tracking, font subsetting, and asset registration so
`converter.py` can remain focused on orchestration.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

from ..data.embedded_font import EmbeddedFont, FontSubsetRequest
from ..ir.text import TextFrame
from ..services.font_fetcher import FontSource


@dataclass(slots=True)
class FontResource:
    """Tracked font metadata for a conversion run."""

    family: str
    weight: str
    style: str
    characters: set[str] = field(default_factory=set)


class ResourceManager:
    """Coordinator for font and image resources used during conversion."""

    def __init__(
        self,
        services: Any,
        font_embedding_engine: Any,
        font_fetcher: Any,
        config: Any,
        logger: logging.Logger,
        conversion_error_cls: type[Exception],
    ) -> None:
        self.services = services
        self.font_embedding_engine = font_embedding_engine
        self.font_fetcher = font_fetcher
        self.config = config
        self.logger = logger
        self._conversion_error_cls = conversion_error_cls

        self.fonts: dict[tuple[str, str, str], FontResource] = {}
        self.images: list[Any] = []
        self._font_subset_cache: dict[tuple[str, str, str, str], EmbeddedFont] = {}
        self._font_face_sources: list[dict[str, Any]] = []
        self._font_outline_required = False
        self._font_embedding_messages: list[str] = []

    def update_dependencies(
        self,
        services: Any,
        font_embedding_engine: Any,
        font_fetcher: Any,
        config: Any,
    ) -> None:
        """Refresh external dependencies after converter reconfiguration."""
        self.services = services
        self.font_embedding_engine = font_embedding_engine
        self.font_fetcher = font_fetcher
        self.config = config

    def reset_for_conversion(self) -> None:
        """Reset per-conversion caches and telemetry."""
        self.fonts.clear()
        self.images.clear()
        self._font_subset_cache = {}
        self._font_outline_required = False
        self._font_embedding_messages = []

    def set_font_face_sources(self, sources: Iterable[dict[str, Any]]) -> None:
        """Provide discovered @font-face declarations for this conversion."""
        self._font_face_sources = list(sources or [])

    def record_media_files(self, media_files: Sequence[dict[str, Any]]) -> None:
        """Track media descriptors emitted by the embedder."""
        self.images.extend(media_files or [])

    def prepare_embedded_fonts(self, mapper_results: list[Any]) -> list[EmbeddedFont]:
        """Gather font usage from mapped text elements and produce embedded fonts."""
        if not self.font_embedding_engine:
            return []

        policy_config = getattr(self.config, "policy_config", None)
        if policy_config and not getattr(policy_config, "enable_font_embedding", True):
            return []

        font_service = getattr(self.services, "font_service", None)
        if font_service is None:
            return []

        font_characters: dict[tuple[str, str, str], set[str]] = {}
        font_behavior = 'embedded'
        if policy_config and getattr(policy_config, 'font_missing_behavior', None):
            font_behavior = str(policy_config.font_missing_behavior).lower()

        for result in mapper_results:
            if getattr(result, "metadata", None) and hasattr(result.metadata, "get"):
                if result.metadata.get('font_outline_fallback'):
                    self._font_outline_required = True

            element = getattr(result, "element", None)
            if not isinstance(element, TextFrame):
                continue

            runs = getattr(element, "runs", []) or []
            for run in runs:
                text = getattr(run, "text", "")
                if not text:
                    continue

                family = (
                    getattr(run, "effective_font_family", None)
                    or getattr(run, "font_family", None)
                )
                if not family:
                    continue

                weight = (
                    getattr(run, "effective_font_weight", None)
                    or getattr(run, "font_weight", None)
                )
                if not weight:
                    weight = "bold" if getattr(run, "bold", False) else "regular"
                else:
                    weight = str(weight).strip()
                    if getattr(run, "bold", False) and weight.lower() in {"regular", "normal"}:
                        weight = "bold"

                style = (
                    getattr(run, "effective_font_style", None)
                    or getattr(run, "font_style", None)
                )
                if not style:
                    style = "italic" if getattr(run, "italic", False) else "normal"
                else:
                    style = str(style).strip()
                    if getattr(run, "italic", False) and style.lower() in {"normal", ""}:
                        style = "italic"

                family = str(family).strip()
                weight = str(weight).lower()
                style = str(style).lower()

                key = (family, weight, style)
                chars = font_characters.setdefault(key, set())
                chars.update(set(text))
                resource = self.fonts.setdefault(
                    key,
                    FontResource(family=family, weight=weight, style=style),
                )
                resource.characters.update(set(text))

        embedded_fonts: list[EmbeddedFont] = []
        font_registry = getattr(self.services, 'font_registry', None)
        per_call_cache: dict[tuple[str, str, str, str], EmbeddedFont] = {}

        for (family, weight, style), characters in font_characters.items():
            if not characters:
                continue

            variant_info = None
            if font_registry is not None:
                try:
                    variant_info = font_registry.find_variant(
                        family,
                        font_weight=weight,
                        font_style=style,
                    )
                except Exception as variant_err:
                    self.logger.debug(f"font_registry.find_variant failed: {variant_err}")

            if variant_info is None and hasattr(font_service, 'find_variant'):
                try:
                    variant_info = font_service.find_variant(
                        family,
                        font_weight=weight,
                        font_style=style,
                    )
                except Exception:
                    variant_info = None

            normalized_family = family
            normalized_weight = weight
            normalized_style = style
            font_path = None

            if variant_info:
                normalized_family = variant_info.get('font_family', family) or family
                normalized_weight = variant_info.get('font_weight', weight) or weight
                normalized_style = variant_info.get('font_style', style) or style
                font_path = variant_info.get('path')

            if not font_path:
                font_path = font_service.find_font_file(
                    normalized_family,
                    font_weight=normalized_weight,
                    font_style=normalized_style,
                )
            if not font_path:
                font_path = self._resolve_external_font(normalized_family, normalized_weight, normalized_style)
                if not font_path:
                    message = f"Font file not found for {family} ({weight}, {style})"
                    if font_behavior == 'error':
                        raise self._conversion_error_cls(message, stage="embedding")
                    if font_behavior == 'outline':
                        self._font_outline_required = True
                        self._font_embedding_messages.append(message + "; falling back to outline")
                        continue
                    if font_behavior == 'emf':
                        self._font_embedding_messages.append(message + "; will render as EMF")
                        continue
                    if font_behavior == 'fallback_family':
                        self._font_embedding_messages.append(message + "; using fallback font family")
                        continue
                    self.logger.debug(message)
                    self._font_embedding_messages.append(message)
                    continue

            normalized_key = (
                (normalized_family or family).lower(),
                (normalized_weight or weight).lower(),
                (normalized_style or style).lower(),
            )
            character_signature = ''.join(sorted(characters))
            cache_key = (*normalized_key, character_signature)

            cached_font = per_call_cache.get(cache_key) or self._font_subset_cache.get(cache_key)
            if cached_font is not None:
                embedded_fonts.append(cached_font)
                continue

            try:
                request = FontSubsetRequest(
                    font_path=font_path,
                    characters=set(characters),
                    font_name=f"{normalized_family}-{normalized_weight}-{normalized_style}",
                    font_family=family,
                    font_weight=normalized_weight,
                    font_style=normalized_style,
                )
                embedded_font = self.font_embedding_engine.create_font_subset(request)
            except Exception as exc:
                message = f"Font subsetting failed for {family} ({weight}, {style}): {exc}"
                self.logger.warning(message)
                self._font_embedding_messages.append(message)
                embedded_font = None

            if embedded_font:
                embedded_font = EmbeddedFont(
                    font_name=embedded_font.font_name,
                    font_data=embedded_font.font_data,
                    subset_characters=embedded_font.subset_characters,
                    original_size=embedded_font.original_size,
                    embedded_size=embedded_font.embedded_size,
                    embedding_allowed=embedded_font.embedding_allowed,
                    embedding_permission=embedded_font.embedding_permission,
                    font_family=family,
                    font_weight=normalized_weight,
                    font_style=normalized_style,
                    units_per_em=embedded_font.units_per_em,
                    file_format=embedded_font.file_format,
                    relationship_id=embedded_font.relationship_id,
                    content_type=embedded_font.content_type,
                )
                embedded_fonts.append(embedded_font)
                per_call_cache[cache_key] = embedded_font
                self._font_subset_cache[cache_key] = embedded_font
            else:
                self._font_embedding_messages.append(
                    f"Font embedding skipped after subsetting for {family} ({weight}, {style}).",
                )

        return embedded_fonts

    def register_embedded_fonts(
        self,
        presentation_composer: Any,
        embedded_fonts: Sequence[EmbeddedFont],
        slide_index: int,
    ) -> None:
        """Forward embedded font metadata to the presentation composer."""
        if not presentation_composer or not embedded_fonts:
            return
        try:
            presentation_composer.asset_embedder.register_embedded_fonts(
                embedded_fonts,
                slide_index=slide_index,
            )
        except Exception as exc:  # pragma: no cover - defensive path
            self.logger.debug("Failed to register embedded fonts with composer: %s", exc)

    def consume_font_messages(self) -> list[str]:
        """Return accumulated font warnings and clear the buffer."""
        messages = list(self._font_embedding_messages)
        self._font_embedding_messages = []
        return messages

    @property
    def font_outline_required(self) -> bool:
        """Whether any font required outline fallback during conversion."""
        return self._font_outline_required

    def _resolve_external_font(self, family: str, weight: str, style: str) -> str | None:
        """Attempt to fetch font files from discovered @font-face rules."""
        if not self._font_face_sources or not self.font_fetcher:
            return None

        candidate_urls: list[str] = []
        for entry in self._font_face_sources:
            entry_family = entry.get('font_family')
            if not entry_family or entry_family.lower() != (family or '').lower():
                continue
            entry_weight = entry.get('font_weight', 'regular').lower()
            entry_style = entry.get('font_style', 'normal').lower()
            if entry_weight != (weight or 'regular').lower():
                continue
            if entry_style != (style or 'normal').lower():
                continue
            candidate_urls.extend(entry.get('sources', []))

        font_service = getattr(self.services, 'font_service', None)

        for url in candidate_urls:
            source = FontSource(url=url, font_family=family, font_weight=weight, font_style=style)
            path = self.font_fetcher.fetch(source)
            if path:
                if font_service is not None:
                    try:
                        font_service.register_font_path(str(path))
                    except Exception as register_err:  # pragma: no cover - logging only
                        self.logger.debug("Failed to register downloaded font %s: %s", path, register_err)
                return str(path)

        return None
