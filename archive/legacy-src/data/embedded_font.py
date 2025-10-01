"""
Embedded Font Data Structures

This module provides data structures for managing embedded fonts in PowerPoint presentations.
These structures support font subsetting, embedding validation, and metadata tracking.
"""

from dataclasses import dataclass, field
from typing import Set, Dict, Any, Optional
from enum import Enum


class EmbeddingPermission(Enum):
    """Font embedding permission levels based on OS/2 fsType field."""
    INSTALLABLE = "installable"              # fsType bit 0 clear
    RESTRICTED = "restricted"                # fsType bit 1 set
    PREVIEW_PRINT = "preview_print"          # fsType bit 2 set
    EDITABLE = "editable"                    # fsType bit 3 set
    NO_SUBSETTING = "no_subsetting"         # fsType bit 8 set
    BITMAP_ONLY = "bitmap_only"             # fsType bit 9 set


@dataclass(frozen=True)
class EmbeddedFont:
    """
    Immutable data structure for embedded font information.

    Contains all metadata needed for font embedding in PowerPoint presentations,
    including subsetting information and embedding permissions.
    """
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
    content_type: str = "application/vnd.ms-fontobject"

    def __post_init__(self):
        """Validate embedded font data."""
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
        """
        Calculate compression ratio from subsetting.

        Returns:
            Ratio of embedded size to original size (0.0 to 1.0)
        """
        if self.original_size == 0:
            return 0.0
        return self.embedded_size / self.original_size

    @property
    def size_reduction_bytes(self) -> int:
        """Calculate size reduction in bytes."""
        return max(0, self.original_size - self.embedded_size)

    @property
    def size_reduction_percentage(self) -> float:
        """Calculate size reduction as percentage."""
        if self.original_size == 0:
            return 0.0
        return (self.size_reduction_bytes / self.original_size) * 100

    @property
    def character_count(self) -> int:
        """Get number of characters in subset."""
        return len(self.subset_characters)

    @property
    def can_subset(self) -> bool:
        """Check if font allows subsetting."""
        return self.embedding_permission != EmbeddingPermission.NO_SUBSETTING

    @property
    def is_bitmap_only(self) -> bool:
        """Check if font is bitmap-only."""
        return self.embedding_permission == EmbeddingPermission.BITMAP_ONLY

    def get_metadata(self) -> Dict[str, Any]:
        """
        Get comprehensive metadata dictionary.

        Returns:
            Dictionary with all font metadata
        """
        return {
            'font_name': self.font_name,
            'font_family': self.font_family,
            'font_weight': self.font_weight,
            'font_style': self.font_style,
            'file_format': self.file_format,
            'original_size': self.original_size,
            'embedded_size': self.embedded_size,
            'compression_ratio': self.compression_ratio,
            'size_reduction_percentage': self.size_reduction_percentage,
            'character_count': self.character_count,
            'embedding_permission': self.embedding_permission.value,
            'embedding_allowed': self.embedding_allowed,
            'can_subset': self.can_subset,
            'is_bitmap_only': self.is_bitmap_only,
            'relationship_id': self.relationship_id,
            'content_type': self.content_type
        }

    @classmethod
    def create_from_font(cls, font_name: str, font_data: bytes, characters: Set[str],
                        original_size: int, **kwargs) -> 'EmbeddedFont':
        """
        Factory method to create EmbeddedFont from font data.

        Args:
            font_name: Name of the font
            font_data: Subsetted font binary data
            characters: Set of characters included in subset
            original_size: Size of original font file
            **kwargs: Additional optional parameters

        Returns:
            New EmbeddedFont instance
        """
        return cls(
            font_name=font_name,
            font_data=font_data,
            subset_characters=characters,
            original_size=original_size,
            embedded_size=len(font_data),
            **kwargs
        )


@dataclass
class FontSubsetRequest:
    """
    Request for font subsetting operation.

    Contains all information needed to create a font subset.
    """
    font_path: str
    characters: Set[str]
    font_name: str = ""
    target_format: str = "ttf"
    optimization_level: str = "basic"  # "none", "basic", "aggressive"
    preserve_hinting: bool = True
    preserve_layout_tables: bool = True

    def __post_init__(self):
        """Validate subset request."""
        if not self.font_path:
            raise ValueError("font_path cannot be empty")
        if not self.characters:
            raise ValueError("characters set cannot be empty")

    @property
    def character_list(self) -> list:
        """Get characters as sorted list."""
        return sorted(list(self.characters))

    @property
    def character_count(self) -> int:
        """Get number of characters to subset."""
        return len(self.characters)

    def add_characters(self, additional_chars: Set[str]):
        """Add more characters to the subset request."""
        self.characters.update(additional_chars)

    def get_cache_key(self) -> str:
        """
        Generate cache key for this subset request.

        Returns:
            String that uniquely identifies this subset request
        """
        chars_hash = hash(frozenset(self.characters))
        return f"{self.font_path}:{chars_hash}:{self.target_format}:{self.optimization_level}"


@dataclass
class FontEmbeddingStats:
    """
    Statistics for font embedding operations.

    Tracks performance and efficiency metrics.
    """
    total_fonts_processed: int = 0
    total_fonts_embedded: int = 0
    total_fonts_failed: int = 0
    total_original_size: int = 0
    total_embedded_size: int = 0
    total_characters_subsetted: int = 0
    average_compression_ratio: float = 0.0
    embedding_errors: list = field(default_factory=list)

    def add_successful_embedding(self, embedded_font: EmbeddedFont):
        """Record successful font embedding."""
        self.total_fonts_processed += 1
        self.total_fonts_embedded += 1
        self.total_original_size += embedded_font.original_size
        self.total_embedded_size += embedded_font.embedded_size
        self.total_characters_subsetted += embedded_font.character_count
        self._update_average_compression()

    def add_failed_embedding(self, error_message: str):
        """Record failed font embedding."""
        self.total_fonts_processed += 1
        self.total_fonts_failed += 1
        self.embedding_errors.append(error_message)

    def _update_average_compression(self):
        """Update average compression ratio."""
        if self.total_original_size > 0:
            self.average_compression_ratio = self.total_embedded_size / self.total_original_size

    @property
    def success_rate(self) -> float:
        """Calculate embedding success rate as percentage."""
        if self.total_fonts_processed == 0:
            return 0.0
        return (self.total_fonts_embedded / self.total_fonts_processed) * 100

    @property
    def total_size_reduction(self) -> int:
        """Calculate total size reduction in bytes."""
        return max(0, self.total_original_size - self.total_embedded_size)

    @property
    def total_size_reduction_percentage(self) -> float:
        """Calculate total size reduction as percentage."""
        if self.total_original_size == 0:
            return 0.0
        return (self.total_size_reduction / self.total_original_size) * 100

    def get_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics summary.

        Returns:
            Dictionary with all statistics
        """
        return {
            'fonts_processed': self.total_fonts_processed,
            'fonts_embedded': self.total_fonts_embedded,
            'fonts_failed': self.total_fonts_failed,
            'success_rate_percentage': self.success_rate,
            'original_size_mb': self.total_original_size / (1024 * 1024),
            'embedded_size_mb': self.total_embedded_size / (1024 * 1024),
            'size_reduction_mb': self.total_size_reduction / (1024 * 1024),
            'size_reduction_percentage': self.total_size_reduction_percentage,
            'average_compression_ratio': self.average_compression_ratio,
            'total_characters_subsetted': self.total_characters_subsetted,
            'error_count': len(self.embedding_errors)
        }