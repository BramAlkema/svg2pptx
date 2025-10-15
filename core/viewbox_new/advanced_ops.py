"""Advanced viewbox operations such as nesting and bounds analysis."""

from __future__ import annotations

from typing import Iterable, List, Sequence, Tuple

import numpy as np

from .config import MeetOrSlice, AspectAlign


AdvancedScaleResult = np.dtype([
    ('scale_x', 'f8'),
    ('scale_y', 'f8'),
    ('uniform_scale', 'f8'),
    ('clip_ratio', 'f8'),
    ('precision_loss', 'f8'),
    ('needs_fallback', '?'),
])


def vectorized_meet_slice_calculations(
    viewbox_aspects: np.ndarray,
    viewport_aspects: np.ndarray,
    meet_slice_modes: np.ndarray,
) -> np.ndarray:
    n_calcs = len(viewbox_aspects)
    result = np.zeros(n_calcs, dtype=AdvancedScaleResult)

    aspect_diff = np.abs(viewport_aspects - viewbox_aspects)
    perfect_match = aspect_diff < 1e-10

    scale_x_candidates = np.ones(n_calcs, dtype=np.float64)
    scale_y_candidates = np.ones(n_calcs, dtype=np.float64)

    imperfect_mask = ~perfect_match
    if np.any(imperfect_mask):
        meet_mask = (meet_slice_modes == MeetOrSlice.MEET.value) & imperfect_mask
        if np.any(meet_mask):
            min_scale = np.minimum(viewport_aspects[meet_mask], viewbox_aspects[meet_mask])
            scale_x_candidates[meet_mask] = min_scale / viewbox_aspects[meet_mask]
            scale_y_candidates[meet_mask] = min_scale / viewport_aspects[meet_mask]

        slice_mask = (meet_slice_modes == MeetOrSlice.SLICE.value) & imperfect_mask
        if np.any(slice_mask):
            max_scale = np.maximum(viewport_aspects[slice_mask], viewbox_aspects[slice_mask])
            scale_x_candidates[slice_mask] = max_scale / viewbox_aspects[slice_mask]
            scale_y_candidates[slice_mask] = max_scale / viewport_aspects[slice_mask]

    result['scale_x'] = scale_x_candidates
    result['scale_y'] = scale_y_candidates
    result['uniform_scale'] = np.sqrt(scale_x_candidates * scale_y_candidates)
    result['clip_ratio'] = np.maximum(
        scale_x_candidates / np.clip(scale_y_candidates, 1e-10, None),
        scale_y_candidates / np.clip(scale_x_candidates, 1e-10, None),
    )
    result['precision_loss'] = aspect_diff
    result['needs_fallback'] = ~perfect_match & (result['clip_ratio'] > 10)
    return result


def calculate_shape_bounding_box_and_relative_coords(
    svg_coords: Sequence[Tuple[float, float]],
    viewport_mapping,
) -> Tuple[int, int, int, int, List[Tuple[int, int]]]:
    if not svg_coords:
        return 0, 0, 1, 1, []

    scale_x = float(viewport_mapping['scale_x'])
    scale_y = float(viewport_mapping['scale_y'])
    translate_x = float(viewport_mapping['translate_x'])
    translate_y = float(viewport_mapping['translate_y'])

    x_coords = [coord[0] for coord in svg_coords]
    y_coords = [coord[1] for coord in svg_coords]

    min_x = min(x_coords)
    max_x = max(x_coords)
    min_y = min(y_coords)
    max_y = max(y_coords)

    width = max_x - min_x
    height = max_y - min_y

    if width <= 0:
        width = 1
    if height <= 0:
        height = 1

    emu_x = int(min_x * scale_x + translate_x)
    emu_y = int(min_y * scale_y + translate_y)
    emu_width = int(width * scale_x)
    emu_height = int(height * scale_y)

    relative_coords: List[Tuple[int, int]] = []
    for x, y in svg_coords:
        rel_x = int(((x - min_x) / width) * 100000)
        rel_y = int(((y - min_y) / height) * 100000)
        relative_coords.append((rel_x, rel_y))

    return emu_x, emu_y, emu_width, emu_height, relative_coords


__all__ = [
    "vectorized_meet_slice_calculations",
    "calculate_shape_bounding_box_and_relative_coords",
]
