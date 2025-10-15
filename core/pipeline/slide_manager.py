"""
Slide coordination utilities for the converter pipeline.

Provides a lightweight layer that tracks slide artifacts so the orchestrator
can manage single- and multi-slide outputs uniformly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Tuple


@dataclass(slots=True)
class SlideArtifact:
    """Represents a slide-level result ready for packaging."""

    payload: Any
    metadata: dict[str, Any] = field(default_factory=dict)


class SlideManager:
    """Coordinator for collecting slide artifacts during conversion."""

    def __init__(self) -> None:
        self._slides: list[SlideArtifact] = []

    def reset(self) -> None:
        """Clear tracked slide artifacts."""
        self._slides.clear()

    def add_slide(self, payload: Any, metadata: dict[str, Any] | None = None) -> int:
        """
        Record a slide artifact and return its index.

        Args:
            payload: Slide-level value (typically an EmbedderResult).
            metadata: Optional contextual metadata for downstream consumers.
        """
        artifact = SlideArtifact(payload=payload, metadata=metadata or {})
        self._slides.append(artifact)
        return len(self._slides) - 1

    def iter_payloads(self) -> Tuple[Any, ...]:
        """Return the recorded slide payloads."""
        return tuple(artifact.payload for artifact in self._slides)

    def iter_artifacts(self) -> Tuple[SlideArtifact, ...]:
        """Return recorded artifacts with metadata."""
        return tuple(self._slides)

    def primary_payload(self) -> Any | None:
        """Return the first slide payload if present."""
        return self._slides[0].payload if self._slides else None
