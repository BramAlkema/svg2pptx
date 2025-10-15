from __future__ import annotations

from core.pipeline.error_handler import ErrorHandler, ErrorHandlerConfig
from core.pipeline.error_reporter import (
    ErrorCategory,
    ErrorSeverity,
    PipelineErrorReporter,
)


def test_error_handler_reports_and_notifies_sinks():
    reporter = PipelineErrorReporter()
    received: list[str] = []
    handler = ErrorHandler(
        reporter=reporter,
        config=ErrorHandlerConfig(
            propagate_to_logger=False,
            sinks=[received.append],
        ),
    )

    handler.report_parsing_error("parse failed", svg_content="<svg/>")

    assert handler.has_errors()
    assert received == ["parse failed"]
    summary = handler.get_error_summary()
    assert summary["total_errors"] == 1


def test_error_handler_reports_other_categories():
    reporter = PipelineErrorReporter()
    handler = ErrorHandler(reporter, ErrorHandlerConfig(propagate_to_logger=False))

    handler.report_analysis_error(
        "analysis issue",
        element_count=10,
        complexity_score=0.8,
    )
    handler.report_mapping_error(
        "mapping issue",
        element_type="Rect",
        mapper_name="RectangleMapper",
    )
    handler.report_pipeline_error(
        "general failure",
        severity=ErrorSeverity.HIGH,
        category=ErrorCategory.PACKAGING,
    )

    assert handler.has_errors()
    assert handler.get_error_summary()["total_errors"] == 3
