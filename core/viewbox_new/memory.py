"""Memory management utilities for viewbox batching."""

from __future__ import annotations

import gc
import sys
from typing import Any


def get_memory_usage(alignment_factors, unit_engine: Any | None = None) -> dict[str, float]:
    gc.collect()
    total_bytes = alignment_factors.nbytes if alignment_factors is not None else 0
    total_bytes += sys.getsizeof(alignment_factors)

    if unit_engine and hasattr(unit_engine, "get_memory_usage"):
        unit_stats = unit_engine.get_memory_usage()
        if isinstance(unit_stats, dict) and "total_bytes" in unit_stats:
            total_bytes += unit_stats["total_bytes"]

    return {
        "total_bytes": total_bytes,
        "total_mb": total_bytes / (1024 * 1024),
        "alignment_factors_bytes": alignment_factors.nbytes if alignment_factors is not None else 0,
    }


__all__ = ["get_memory_usage"]
