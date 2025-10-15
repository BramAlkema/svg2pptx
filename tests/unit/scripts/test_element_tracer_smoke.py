from pathlib import Path

from scripts.testing.test_element_tracer import run_tracer


def test_element_tracer_generates_report(tmp_path: Path):
    output_path = tmp_path / "trace.json"
    report = run_tracer(output_path=output_path)

    assert report.total_decisions >= 1
    assert output_path.exists()
