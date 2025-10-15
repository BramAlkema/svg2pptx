"""Embedded font data structures for PPTX packaging."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, Set


class EmbeddingPermission(Enum):
    """Font embedding permission levels derived from the OS/2 fsType field."""

    INSTALLABLE = "installable"
    RESTRICTED = "restricted"
    PREVIEW_PRINT = "preview_print"
    EDITABLE = "editable"
    NO_SUBSETTING = "no_subsetting"
    BITMAP_ONLY = "bitmap_only"


@dataclass(frozen=True)
class EmbeddedFont:
    """Immutable metadata container for an embedded font subset."""

    font_name: str
    font_data: bytes
    subset_characters: Set[str] = field(default_factory=set)
    original_size: int = 0
    embedded_size: int = 0
    embedding_allowed: bool = True
    embedding_permission: EmbeddingPermission = EmbeddingPermission.INSTALLABLE
    font_family: str = ""
    font_weight: str = "normal"
    font_style: str = "normal"
    units_per_em: int = 1000
    file_format: str = "ttf"
    relationship_id: Optional[str] = None
    content_type: str = "application/vnd.openxmlformats-officedocument.obfuscatedFont"

    def __post_init__(self) -> None:
        if not self.font_name:
            raise ValueError("font_name cannot be empty")
        if not self.font_data:
            raise ValueError("font_data cannot be empty")
        if self.original_size < 0:
            raise ValueError("original_size cannot be negative")
        if self.embedded_size < 0:
            raise ValueError("embedded_size cannot be negative")

    @property
    def compression_ratio(self) -> float:
        if self.original_size == 0:
            return 0.0
        return self.embedded_size / self.original_size

    @property
    def size_reduction_bytes(self) -> int:
        return max(0, self.original_size - self.embedded_size)

    @property
    def size_reduction_percentage(self) -> float:
        if self.original_size == 0:
            return 0.0
        return (self.size_reduction_bytes / self.original_size) * 100

    @property
    def character_count(self) -> int:
        return len(self.subset_characters)

    @property
    def can_subset(self) -> bool:
        return self.embedding_permission != EmbeddingPermission.NO_SUBSETTING

    @property
    def is_bitmap_only(self) -> bool:
        return self.embedding_permission == EmbeddingPermission.BITMAP_ONLY

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "font_name": self.font_name,
            "font_family": self.font_family,
            "font_weight": self.font_weight,
            "font_style": self.font_style,
            "file_format": self.file_format,
            "original_size": self.original_size,
            "embedded_size": self.embedded_size,
            "compression_ratio": self.compression_ratio,
            "size_reduction_percentage": self.size_reduction_percentage,
            "character_count": self.character_count,
            "embedding_permission": self.embedding_permission.value,
            "embedding_allowed": self.embedding_allowed,
            "can_subset": self.can_subset,
            "is_bitmap_only": self.is_bitmap_only,
            "relationship_id": self.relationship_id,
            "content_type": self.content_type,
        }

    @classmethod
    def create_from_font(
        cls,
        font_name: str,
        font_data: bytes,
        characters: Set[str],
        original_size: int,
        **kwargs,
    ) -> "EmbeddedFont":
        return cls(
            font_name=font_name,
            font_data=font_data,
            subset_characters=characters,
            original_size=original_size,
            embedded_size=len(font_data),
            **kwargs,
        )


@dataclass
class FontSubsetRequest:
    """Request payload for font subsetting operations."""

    font_path: str
    characters: Set[str]
    font_name: str = ""
    font_family: str = ""
    font_weight: str = "regular"
    font_style: str = "normal"
    target_format: str = "ttf"
    optimization_level: str = "basic"
    preserve_hinting: bool = True
    preserve_layout_tables: bool = True
    preserve_kerning: bool | None = None

    def __post_init__(self) -> None:
        if not self.font_path:
            raise ValueError("font_path cannot be empty")
        if not self.characters:
            raise ValueError("characters set cannot be empty")

    @property
    def character_list(self) -> list[str]:
        return sorted(self.characters)

    @property
    def character_count(self) -> int:
        return len(self.characters)

    def add_characters(self, additional_chars: Set[str]) -> None:
        self.characters.update(additional_chars)

    def get_cache_key(self) -> str:
        chars_hash = hash(frozenset(self.characters))
        return f"{self.font_path}:{chars_hash}:{self.target_format}:{self.optimization_level}"


@dataclass
class FontEmbeddingStats:
    """Telemetry for font embedding operations."""

    total_fonts_processed: int = 0
    successful_embeddings: int = 0
    failed_embeddings: int = 0
    total_original_size: int = 0
    total_embedded_size: int = 0
    notes: list[str] = field(default_factory=list)

    def add_successful_embedding(self, embedded_font: EmbeddedFont) -> None:
        self.total_fonts_processed += 1
        self.successful_embeddings += 1
        self.total_original_size += embedded_font.original_size
        self.total_embedded_size += embedded_font.embedded_size

    def add_failed_embedding(self, message: str) -> None:
        self.total_fonts_processed += 1
        self.failed_embeddings += 1
        self.notes.append(message)

    def get_summary(self) -> Dict[str, Any]:
        reduction = self.total_original_size - self.total_embedded_size
        reduction_pct = (
            (reduction / self.total_original_size) * 100
            if self.total_original_size
            else 0.0
        )
        return {
            "total_fonts_processed": self.total_fonts_processed,
            "successful_embeddings": self.successful_embeddings,
            "failed_embeddings": self.failed_embeddings,
            "total_original_size": self.total_original_size,
            "total_embedded_size": self.total_embedded_size,
            "size_reduction_bytes": reduction,
            "size_reduction_percentage": reduction_pct,
            "notes": list(self.notes),
        }


__all__ = [
    "EmbeddedFont",
    "EmbeddingPermission",
    "FontEmbeddingStats",
    "FontSubsetRequest",
]
