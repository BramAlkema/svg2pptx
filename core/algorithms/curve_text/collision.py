"""Collision detection helpers for curve text positioning."""

from __future__ import annotations

from typing import List, Sequence, Tuple

from ...ir.text_path import PathPoint


def detect_collisions(path_points: Sequence[PathPoint], glyph_width: float) -> List[int]:
    collisions: List[int] = []
    for idx in range(1, len(path_points)):
        prev = path_points[idx - 1]
        curr = path_points[idx]
        if curr.distance_along_path - prev.distance_along_path < glyph_width:
            collisions.append(idx)
    return collisions


__all__ = ["detect_collisions"]
