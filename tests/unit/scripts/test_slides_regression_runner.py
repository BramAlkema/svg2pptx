import json
from pathlib import Path

from scripts.automation.slides_regression import SlideSample, SlidesRegressionRunner


def test_slides_regression_runner_writes_reports(tmp_path: Path):
    samples = [
        SlideSample(name="sample1", svg_text="""<svg xmlns='http://www.w3.org/2000/svg'><text x='0' y='12'>Hi</text></svg>"""),
        SlideSample(name="sample2", svg_text="""<svg xmlns='http://www.w3.org/2000/svg'><rect x='1' y='1' width='10' height='10'/></svg>"""),
    ]

    def fake_exporter(**kwargs):
        return {'warnings': ['stubbed'], 'slides_url': 'https://example.com/presentation'}

    runner = SlidesRegressionRunner(
        samples=samples,
        output_dir=tmp_path,
        export_enabled=True,
        exporter=fake_exporter,
    )

    reports = runner.run()

    assert len(reports) == 2
    for sample in samples:
        report_path = tmp_path / f"{sample.name}.json"
        assert report_path.exists()
        payload = json.loads(report_path.read_text())
        assert payload['warnings'] == ['stubbed']
        assert 'policy_metrics' in payload
