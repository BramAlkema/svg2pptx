"""ViewBox parsing helpers for the new viewbox package."""

from __future__ import annotations

from typing import Iterable, Tuple

import numpy as np

from .config import (
    ALIGNMENT_MAP,
    AspectAlign,
    MeetOrSlice,
    ViewBoxArray,
    ViewBoxConfig,
)


def parse_viewbox_strings(viewbox_strings: np.ndarray) -> np.ndarray:
    """
    Parse an array of viewBox strings into a structured NumPy array.

    Mirrors the existing implementation in :mod:`core.viewbox.core` so callers
    can migrate without behavioural changes.
    """
    n_viewboxes = len(viewbox_strings)
    result = np.zeros(n_viewboxes, dtype=ViewBoxArray)

    for i, vb_str in enumerate(viewbox_strings):
        if not vb_str or not str(vb_str).strip():
            result[i] = (-1, -1, -1, -1, -1)
            continue

        try:
            cleaned = str(vb_str).strip().replace(",", " ")
            parts = cleaned.split()

            if len(parts) == 4:
                min_x, min_y, width, height = (float(p) for p in parts)
                if width > 0 and height > 0:
                    aspect_ratio = width / height
                    result[i] = (min_x, min_y, width, height, aspect_ratio)
                    continue
        except (ValueError, TypeError):
            pass

        result[i] = (-1, -1, -1, -1, -1)

    return result


def parse_preserve_aspect_ratio_batch(
    par_strings: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Parse an array of preserveAspectRatio strings into alignment and meet/slice arrays.
    """
    n_strings = len(par_strings)
    alignments = np.full(n_strings, AspectAlign.X_MID_Y_MID.value, dtype=np.int32)
    meet_slices = np.full(n_strings, MeetOrSlice.MEET.value, dtype=np.int32)

    for i, par_str in enumerate(par_strings):
        if not par_str or not str(par_str).strip():
            continue

        parts = str(par_str).strip().lower().split()
        for part in parts:
            if part in ALIGNMENT_MAP:
                alignments[i] = ALIGNMENT_MAP[part]
            elif part == "meet":
                meet_slices[i] = MeetOrSlice.MEET.value
            elif part == "slice":
                meet_slices[i] = MeetOrSlice.SLICE.value

    return alignments, meet_slices


def parse_viewbox_token(token: str) -> ViewBoxConfig:
    """Parse a single viewBox token string into a :class:`ViewBoxConfig`."""
    array = parse_viewbox_strings(np.array([token], dtype=object))
    min_x, min_y, width, height, _ = array[0]
    return ViewBoxConfig(min_x=min_x, min_y=min_y, width=width, height=height)


def parse_preserve_aspect_ratio(
    value: str,
) -> tuple[AspectAlign, MeetOrSlice]:
    """Parse a single preserveAspectRatio string."""
    alignments, meet_slices = parse_preserve_aspect_ratio_batch(
        np.array([value], dtype=object)
    )
    return AspectAlign(alignments[0]), MeetOrSlice(meet_slices[0])


def normalize_inputs(
    viewbox_strings: Iterable[str],
    par_strings: Iterable[str] | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Convenience helper that parses viewBox and preserveAspectRatio arrays together.
    """
    vb_array = parse_viewbox_strings(np.asarray(list(viewbox_strings), dtype=object))
    par_iterable = par_strings or [""] * len(vb_array)
    alignments, meet_slices = parse_preserve_aspect_ratio_batch(
        np.asarray(list(par_iterable), dtype=object)
    )
    return vb_array, alignments, meet_slices


__all__ = [
    "parse_viewbox_strings",
    "parse_preserve_aspect_ratio_batch",
    "parse_viewbox_token",
    "parse_preserve_aspect_ratio",
    "normalize_inputs",
]
