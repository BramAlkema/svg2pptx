"""Lightweight presentation builder utilities for Clean Slate services."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Presentation:
    """In-memory representation of a presentation for quick validation."""
    slides: list[dict[str, Any]] = field(default_factory=list)


class PresentationBuilder:
    """Minimal presentation builder used by ConversionServices validation."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        """Reset internal state."""
        self._presentation = Presentation()

    def create_presentation(self) -> Presentation:
        """Create a new presentation container."""
        self.reset()
        return self._presentation

    def add_slide(self, presentation: Presentation | None = None) -> dict[str, Any]:
        """Add a slide placeholder to the presentation."""
        target = presentation or self._presentation
        slide = {"index": len(target.slides) + 1, "shapes": []}
        target.slides.append(slide)
        return slide

__all__ = ["Presentation", "PresentationBuilder"]
