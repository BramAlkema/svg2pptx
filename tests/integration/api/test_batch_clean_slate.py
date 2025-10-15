import json
import sys
import types
from pathlib import Path

from fastapi.testclient import TestClient

# Provide lightweight stubs for external services that the conversion service imports.
if "api.services.google_drive" not in sys.modules:
    google_drive_stub = types.ModuleType("api.services.google_drive")

    class _DriveStub:
        def __init__(self, *args, **kwargs):
            pass

    google_drive_stub.GoogleDriveService = _DriveStub
    google_drive_stub.GoogleDriveError = RuntimeError
    sys.modules["api.services.google_drive"] = google_drive_stub

if "api.services.google_slides" not in sys.modules:
    google_slides_stub = types.ModuleType("api.services.google_slides")

    class _SlidesStub:
        def __init__(self, *args, **kwargs):
            pass

        def generate_preview_summary(self, *args, **kwargs):
            return {"previews": {"available": 0, "total": 0}, "urls": {}}

    google_slides_stub.GoogleSlidesService = _SlidesStub
    google_slides_stub.GoogleSlidesError = RuntimeError
    sys.modules["api.services.google_slides"] = google_slides_stub

if "core.svg2pptx" not in sys.modules:
    svg2pptx_stub = types.ModuleType("core.svg2pptx")

    def _convert_stub(svg_content: str, output_path: str | None = None):
        if output_path:
            Path(output_path).write_bytes(b"stub-pptx")
        return b"stub-pptx"

    svg2pptx_stub.convert_svg_to_pptx = _convert_stub
    sys.modules["core.svg2pptx"] = svg2pptx_stub

from api.main import app
from core.batch.models import BatchJob


def test_batch_job_lifecycle(monkeypatch, tmp_path):
    client = TestClient(app)

    def fake_download_svgs_to_temp(urls, job_id):
        file_path = Path(tmp_path) / f"{job_id}.svg"
        file_path.write_text(
            "<svg xmlns='http://www.w3.org/2000/svg' width='10' height='10'>"
            "<rect x='0' y='0' width='10' height='10' fill='red' />"
            "</svg>",
            encoding="utf-8",
        )

        class Result:
            success = True
            file_paths = [str(file_path)]
            errors: list[str] = []

        return Result()

    monkeypatch.setattr(
        "api.routes.batch.download_svgs_to_temp",
        fake_download_svgs_to_temp,
    )

    def immediate_schedule(job_id, file_paths, conversion_options, user_id, export_to_slides):
        job = BatchJob.get_by_id(job_id)
        job.status = "completed"
        job.trace_data = {
            "architecture": "clean_slate",
            "page_count": 1,
            "workflow": "conversion_only",
            "debug_trace": [],
        }
        job.save()

    monkeypatch.setattr(
        "api.routes.batch._schedule_clean_slate_workflow",
        immediate_schedule,
    )

    response = client.post(
        "/batch/jobs",
        headers={"Authorization": "Bearer dev-api-key-12345"},
        json={
            "urls": ["https://example.com/sample.svg"],
            "preprocessing_preset": "default",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    job_id = payload["job_id"]

    status_response = client.get(
        f"/batch/jobs/{job_id}",
        headers={"Authorization": "Bearer dev-api-key-12345"},
    )
    assert status_response.status_code == 200
    status_payload = status_response.json()
    assert status_payload["job_id"] == job_id
    assert status_payload["status"] == "completed"
    assert status_payload["total_files"] == 1
    assert status_payload["slides_export_enabled"] is False

    trace_response = client.get(
        f"/batch/jobs/{job_id}/trace",
        headers={"Authorization": "Bearer dev-api-key-12345"},
    )
    assert trace_response.status_code == 200
    trace_payload = trace_response.json()
    assert trace_payload["trace_available"] is True
    assert trace_payload["trace"]["workflow"] == "conversion_only"
