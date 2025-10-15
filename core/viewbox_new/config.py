"""Configuration primitives for the refactored viewbox module."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

import numpy as np


class AspectAlign(IntEnum):
    """Aspect ratio alignment values for efficient indexing."""

    X_MIN_Y_MIN = 0
    X_MID_Y_MIN = 1
    X_MAX_Y_MIN = 2
    X_MIN_Y_MID = 3
    X_MID_Y_MID = 4  # Default
    X_MAX_Y_MID = 5
    X_MIN_Y_MAX = 6
    X_MID_Y_MAX = 7
    X_MAX_Y_MAX = 8
    NONE = 9


class MeetOrSlice(IntEnum):
    """Meet or slice scaling behavior."""

    MEET = 0  # Scale to fit entirely within viewport
    SLICE = 1  # Scale to fill entire viewport


ALIGNMENT_FACTORS = np.array(
    [
        [0.0, 0.0],  # X_MIN_Y_MIN
        [0.5, 0.0],  # X_MID_Y_MIN
        [1.0, 0.0],  # X_MAX_Y_MIN
        [0.0, 0.5],  # X_MIN_Y_MID
        [0.5, 0.5],  # X_MID_Y_MID (default)
        [1.0, 0.5],  # X_MAX_Y_MID
        [0.0, 1.0],  # X_MIN_Y_MAX
        [0.5, 1.0],  # X_MID_Y_MAX
        [1.0, 1.0],  # X_MAX_Y_MAX
        [0.0, 0.0],  # NONE (placeholder)
    ],
    dtype=np.float64,
)

ALIGNMENT_MAP = {
    "xminymin": AspectAlign.X_MIN_Y_MIN.value,
    "xmidymin": AspectAlign.X_MID_Y_MIN.value,
    "xmaxymin": AspectAlign.X_MAX_Y_MIN.value,
    "xminymid": AspectAlign.X_MIN_Y_MID.value,
    "xmidymid": AspectAlign.X_MID_Y_MID.value,
    "xmaxymid": AspectAlign.X_MAX_Y_MID.value,
    "xminymax": AspectAlign.X_MIN_Y_MAX.value,
    "xmidymax": AspectAlign.X_MID_Y_MAX.value,
    "xmaxymax": AspectAlign.X_MAX_Y_MAX.value,
    "none": AspectAlign.NONE.value,
}

ViewBoxArray = np.dtype(
    [
        ("min_x", "f8"),
        ("min_y", "f8"),
        ("width", "f8"),
        ("height", "f8"),
        ("aspect_ratio", "f8"),
    ]
)

ViewportArray = np.dtype(
    [
        ("width", "i8"),  # EMU
        ("height", "i8"),  # EMU
        ("aspect_ratio", "f8"),
    ]
)

ViewportMappingArray = np.dtype(
    [
        ("scale_x", "f8"),
        ("scale_y", "f8"),
        ("translate_x", "f8"),
        ("translate_y", "f8"),
        ("viewport_width", "i8"),
        ("viewport_height", "i8"),
        ("content_width", "i8"),
        ("content_height", "i8"),
        ("clip_needed", "?"),
        ("clip_x", "f8"),
        ("clip_y", "f8"),
        ("clip_width", "f8"),
        ("clip_height", "f8"),
    ]
)


@dataclass(slots=True)
class ViewBoxConfig:
    """Configuration surface describing a parsed viewBox and aspect ratio settings."""

    min_x: float = 0.0
    min_y: float = 0.0
    width: float = 0.0
    height: float = 0.0
    align: AspectAlign = AspectAlign.X_MID_Y_MID
    meet_or_slice: MeetOrSlice = MeetOrSlice.MEET

    @property
    def aspect_ratio(self) -> float:
        """Return width/height ratio, guarding zero division."""
        return self.width / self.height if self.height else 0.0


__all__ = [
    "AspectAlign",
    "MeetOrSlice",
    "ALIGNMENT_FACTORS",
    "ALIGNMENT_MAP",
    "ViewBoxArray",
    "ViewportArray",
    "ViewportMappingArray",
    "ViewBoxConfig",
]
