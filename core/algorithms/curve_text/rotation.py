"""Rotation angle utilities for curve text positioning."""

from __future__ import annotations

import math
from typing import Sequence

from ...ir.text_path import PathPoint


def rotation_angles(path_points: Sequence[PathPoint]) -> list[float]:
    return [point.tangent_angle for point in path_points]


def normalize_angle(angle: float) -> float:
    return math.atan2(math.sin(angle), math.cos(angle))


__all__ = ["rotation_angles", "normalize_angle"]
