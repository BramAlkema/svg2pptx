"""Coordinate transformation helpers for viewbox computations."""

from __future__ import annotations

from typing import Iterable, Sequence, Tuple

import numpy as np

from .config import ViewportMappingArray


def svg_to_emu(points: np.ndarray, mappings: np.ndarray) -> np.ndarray:
    """Vectorized conversion of SVG coordinates to EMU space."""
    if points.ndim != 2 or points.shape[1] != 2:
        raise ValueError("points array must be of shape (N, 2)")
    transformed = np.zeros_like(points, dtype=np.int64)
    transformed[:, 0] = (points[:, 0] * mappings['scale_x'] + mappings['translate_x']).astype(np.int64)
    transformed[:, 1] = (points[:, 1] * mappings['scale_y'] + mappings['translate_y']).astype(np.int64)
    return transformed


def transform_matrices(mappings: np.ndarray) -> np.ndarray:
    """Generate affine transform matrices for viewport mappings."""
    if mappings.dtype != ViewportMappingArray:
        mappings = mappings.astype(ViewportMappingArray, copy=False)
    n_mappings = len(mappings)
    matrices = np.zeros((n_mappings, 3, 3), dtype=np.float64)
    matrices[:, 0, 0] = mappings['scale_x']
    matrices[:, 1, 1] = mappings['scale_y']
    matrices[:, 0, 2] = mappings['translate_x']
    matrices[:, 1, 2] = mappings['translate_y']
    matrices[:, 2, 2] = 1.0
    return matrices


__all__ = ["svg_to_emu", "transform_matrices"]
