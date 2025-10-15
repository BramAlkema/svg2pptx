"""Performance benchmarking hooks for the refactored viewbox module."""

from __future__ import annotations

import time
from typing import Iterable, Mapping

import numpy as np
from lxml import etree as ET


def benchmark_parsing(viewbox_strings: np.ndarray, parser) -> dict[str, float]:
    start = time.perf_counter()
    parser(viewbox_strings)
    duration = time.perf_counter() - start
    n = len(viewbox_strings)
    return {
        "operations_per_second": n / duration if duration else 0.0,
        "total_time_seconds": duration,
        "n_operations": n,
    }


def benchmark_batch(engine, svg_elements: list[ET.Element], context=None) -> dict[str, float]:
    start = time.perf_counter()
    engine.batch_resolve_svg_viewports(svg_elements, None, [context] if context else None)
    duration = time.perf_counter() - start
    n = len(svg_elements)
    return {
        "elements_per_second": n / duration if duration else 0.0,
        "total_time_seconds": duration,
        "average_time_per_element_us": (duration / n) * 1_000_000 if n else 0.0,
        "n_elements": n,
    }


__all__ = ["benchmark_parsing", "benchmark_batch"]
