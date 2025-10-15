#!/usr/bin/env python3
"""Slides regression automation harness.

Designed to be scheduled (e.g., nightly) to render a corpus of SVG samples,
optionally export them to Google Slides, and capture policy/quality metadata.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Callable, Iterable, List, Optional

from core.pipeline.converter import CleanSlateConverter
from svg2pptx.normalize_svg import normalize_svg_string


@dataclass
class SlideSample:
    name: str
    svg_text: str
    metadata: dict | None = None


class SlidesRegressionRunner:
    def __init__(
        self,
        samples: Iterable[SlideSample],
        output_dir: Path,
        export_enabled: bool = False,
        exporter: Optional[Callable[..., dict]] = None,
    ) -> None:
        self.samples = list(samples)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.export_enabled = export_enabled
        self.exporter = exporter

    def run(self) -> List[dict]:
        reports: List[dict] = []

        for sample in self.samples:
            report = self._process_sample(sample)
            reports.append(report)
            self._write_report(sample.name, report)

        return reports

    def _process_sample(self, sample: SlideSample) -> dict:
        converter = CleanSlateConverter()
        normalized_svg = normalize_svg_string(sample.svg_text)
        result = converter.convert_string(normalized_svg)

        metrics = converter.policy.get_metrics()
        policy_metrics = {
            'total_decisions': metrics.total_decisions,
            'native_decisions': metrics.native_decisions,
            'emf_decisions': metrics.emf_decisions,
            'reason_counts': dict(metrics.reason_counts),
        }

        slides_metadata: dict = {}
        warnings: List[str] = []

        if self.export_enabled and self.exporter:
            slides_metadata = self.exporter(
                pptx_bytes=result.output_data,
                title=sample.name,
                metadata=sample.metadata or {},
            ) or {}
            warnings = slides_metadata.get('warnings', [])

        return {
            'name': sample.name,
            'policy_metrics': policy_metrics,
            'warnings': warnings,
            'slides_metadata': slides_metadata,
            'conversion_stats': {
                'output_size_bytes': len(result.output_data),
                'native_percentage': metrics.native_percentage,
                'emf_percentage': metrics.emf_percentage,
            },
            'sample_metadata': sample.metadata or {},
        }

    def _write_report(self, sample_name: str, report: dict) -> None:
        safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", sample_name)
        report_path = self.output_dir / f"{safe_name}.json"
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")


def build_sample_corpus() -> List[SlideSample]:
    """Return a small default corpus covering fonts, warps, and outlines."""
    samples = [
        SlideSample(
            name="basic_font",
            svg_text="""<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 160 60'>
              <text x='10' y='35' font-family='Roboto' font-size='24'>Roboto Sample</text>
            </svg>""",
            metadata={'category': 'fonts'},
        ),
        SlideSample(
            name="text_on_path",
            svg_text="""<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 200 80'>
              <defs>
                <path id='curve' d='M10,60 C60,10 140,10 190,60' />
              </defs>
              <text font-family='Arial' font-size='18'>
                <textPath href='#curve'>Curved Regression Sample</textPath>
              </text>
            </svg>""",
            metadata={'category': 'text-on-path'},
        ),
    ]
    return samples


def main() -> None:
    runner = SlidesRegressionRunner(
        samples=build_sample_corpus(),
        output_dir=Path("reports/slides_regression"),
        export_enabled=False,
    )
    reports = runner.run()
    print(json.dumps(reports, indent=2))


if __name__ == "__main__":
    main()
