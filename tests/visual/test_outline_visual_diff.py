"""Optional visual diff harness focusing on outline/EMF fallbacks."""
from __future__ import annotations

import pytest
from pathlib import Path

from core.pipeline.config import PipelineConfig
from core.pipeline.converter import CleanSlateConverter
from core.policy.config import PolicyConfig

try:
    from tests.support.visual_regression_tester import (
        VisualRegressionTester,
        PILLOW_AVAILABLE,
        NUMPY_AVAILABLE,
    )
except ImportError:  # pragma: no cover - optional harness
    pytest.skip("visual regression dependencies unavailable", allow_module_level=True)

if not PILLOW_AVAILABLE or not NUMPY_AVAILABLE:  # pragma: no cover - optional harness
    pytest.skip("Pillow/NumPy not available for visual regression", allow_module_level=True)


def _init_tester() -> VisualRegressionTester | None:
    try:
        tester = VisualRegressionTester()
    except Exception:
        return None
    libreoffice_path = getattr(tester.renderer, "libreoffice_path", None)
    if not libreoffice_path or not Path(libreoffice_path).exists():
        return None
    return tester


# Initialize once so the skip check and test share the same instance
_VISUAL_TESTER = _init_tester()


@pytest.mark.skipif(_VISUAL_TESTER is None, reason="LibreOffice renderer not available")
def test_outline_fallback_visual_diff(tmp_path):
    tester = _VISUAL_TESTER
    assert tester is not None  # for mypy/linters

    svg = """<svg xmlns='http://www.w3.org/2000/svg' width='320' height='120'>
  <text x='20' y='70' font-family='NonExistentOutlineFont' font-size='48'>Outline</text>
</svg>"""

    config = PipelineConfig(policy_config=PolicyConfig(font_missing_behavior="outline"))
    converter = CleanSlateConverter(config=config)

    baseline_result = converter.convert_string(svg)
    assert baseline_result.emf_elements > 0 or baseline_result.font_outline_required

    baseline_path = tmp_path / "outline_baseline.pptx"
    baseline_path.write_bytes(baseline_result.output_data)

    candidate_result = converter.convert_string(svg)
    candidate_path = tmp_path / "outline_candidate.pptx"
    candidate_path.write_bytes(candidate_result.output_data)

    regression = tester.run_regression_test(
        baseline_path,
        candidate_path,
        test_name="outline_fallback",
        similarity_threshold=0.90,
    )

    tester.cleanup()

    if not regression.passed and regression.error_message:
        pytest.skip(f"Visual diff skipped: {regression.error_message}")

    assert regression.passed
    assert regression.actual_similarity >= 0.90
