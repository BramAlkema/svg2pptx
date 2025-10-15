"""
Converter error handling abstractions.

Wraps :class:`PipelineErrorReporter` with a slimmer interface that notifies
optional sinks and centralises error reporting for the pipeline.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable, Protocol

from .error_reporter import (
    ErrorCategory,
    ErrorSeverity,
    PipelineErrorReporter,
)

logger = logging.getLogger(__name__)


class ErrorSink(Protocol):
    """Protocol representing consumers of pipeline error events."""

    def __call__(self, message: str) -> None:
        ...


@dataclass(slots=True)
class ErrorHandlerConfig:
    """Configuration for the error handler."""

    propagate_to_logger: bool = True
    sinks: Iterable[ErrorSink] | None = None


class ErrorHandler:
    """Adapter that orchestrates error reporting flow for the converter."""

    def __init__(self, reporter: PipelineErrorReporter, config: ErrorHandlerConfig | None = None) -> None:
        self.reporter = reporter
        self.config = config or ErrorHandlerConfig()
        self._sinks: list[ErrorSink] = list(self.config.sinks or [])

    def add_sink(self, sink: ErrorSink) -> None:
        """Register a callback that receives error messages."""
        self._sinks.append(sink)

    def _notify(self, message: str) -> None:
        for sink in self._sinks:
            try:
                sink(message)
            except Exception as sink_err:  # pragma: no cover - defensive path
                logger.debug("Error sink %s failed: %s", sink, sink_err)

        if self.config.propagate_to_logger:
            logger.error(message)

    def report_parsing_error(
        self,
        message: str,
        svg_content: str | None = None,
        exception: Exception | None = None,
    ):
        """Report a parsing error and notify sinks."""
        report = self.reporter.report_parsing_error(
            message=message,
            svg_content=svg_content,
            exception=exception,
        )
        self._notify(report.message)
        return report

    def report_analysis_error(
        self,
        message: str,
        element_count: int | None = None,
        complexity_score: float | None = None,
        exception: Exception | None = None,
    ):
        """Report an analysis error and notify sinks."""
        report = self.reporter.report_analysis_error(
            message=message,
            element_count=element_count,
            complexity_score=complexity_score,
            exception=exception,
        )
        self._notify(report.message)
        return report

    def report_mapping_error(
        self,
        message: str,
        element_type: str | None = None,
        mapper_name: str | None = None,
        exception: Exception | None = None,
    ):
        """Report a mapping error and notify sinks."""
        report = self.reporter.report_mapping_error(
            message=message,
            element_type=element_type,
            mapper_name=mapper_name,
            exception=exception,
        )
        self._notify(report.message)
        return report

    def report_pipeline_error(
        self,
        message: str,
        severity: ErrorSeverity,
        category: ErrorCategory,
        exception: Exception | None = None,
    ):
        """Report a general pipeline error."""
        report = self.reporter.report_error(
            message=message,
            severity=severity,
            category=category,
            exception=exception,
        )
        self._notify(report.message)
        return report

    def get_error_summary(self) -> dict:
        """Expose the reporter error summary."""
        return self.reporter.get_error_summary()

    def has_errors(self) -> bool:
        """Return True if any errors have been recorded."""
        return bool(self.reporter.error_history)
