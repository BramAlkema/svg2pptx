#!/usr/bin/env python3
"""Simple element tracing smoke test for the Clean Slate pipeline."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict

from core.pipeline.converter import CleanSlateConverter
from svg2pptx.normalize_svg import normalize_svg_string


DEFAULT_SVG = """<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 200 80'>
  <style>
    text { font-family: Arial; font-size: 18px; fill: #333; }
  </style>
  <rect x='5' y='5' width='60' height='40' fill='#4F8EF7'/>
  <text x='80' y='40'>Tracer</text>
</svg>"""


@dataclass
class TraceReport:
    sample_name: str
    total_decisions: int
    native_decisions: int
    emf_decisions: int
    reason_counts: Dict[str, int]

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)


def run_tracer(svg_text: str = DEFAULT_SVG, *, output_path: Path | None = None) -> TraceReport:
    """Run the converter on the provided SVG and collect policy metrics."""
    converter = CleanSlateConverter()
    normalized = normalize_svg_string(svg_text)
    converter.convert_string(normalized)

    metrics = converter.policy.get_metrics()
    report = TraceReport(
        sample_name="default",
        total_decisions=metrics.total_decisions,
        native_decisions=metrics.native_decisions,
        emf_decisions=metrics.emf_decisions,
        reason_counts=dict(metrics.reason_counts),
    )

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report.to_json(), encoding="utf-8")

    return report


def main() -> None:
    report = run_tracer()
    print(report.to_json())


if __name__ == "__main__":
    main()
