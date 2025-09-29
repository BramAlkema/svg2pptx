#!/usr/bin/env python3
"""
Pipeline Error Reporter

Comprehensive error reporting and debugging system for the conversion pipeline.
Provides detailed error context, recovery suggestions, and debug information.
"""

import time
import logging
import traceback
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification"""
    PARSING = "parsing"
    ANALYSIS = "analysis"
    MAPPING = "mapping"
    EMBEDDING = "embedding"
    PACKAGING = "packaging"
    CONFIGURATION = "configuration"
    RESOURCE = "resource"
    VALIDATION = "validation"


@dataclass
class ErrorContext:
    """Detailed error context information"""
    timestamp: float = field(default_factory=time.perf_counter)
    stage: str = ""
    operation: str = ""
    input_data: Optional[Dict[str, Any]] = None
    system_state: Optional[Dict[str, Any]] = None
    performance_metrics: Optional[Dict[str, float]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'timestamp': self.timestamp,
            'stage': self.stage,
            'operation': self.operation,
            'input_data': self.input_data,
            'system_state': self.system_state,
            'performance_metrics': self.performance_metrics
        }


@dataclass
class ErrorReport:
    """Comprehensive error report"""
    error_id: str
    message: str
    severity: ErrorSeverity
    category: ErrorCategory
    context: ErrorContext
    exception: Optional[Exception] = None
    stack_trace: Optional[str] = None
    recovery_suggestions: List[str] = field(default_factory=list)
    debug_info: Dict[str, Any] = field(default_factory=dict)
    related_errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'error_id': self.error_id,
            'message': self.message,
            'severity': self.severity.value,
            'category': self.category.value,
            'context': self.context.to_dict(),
            'exception_type': type(self.exception).__name__ if self.exception else None,
            'stack_trace': self.stack_trace,
            'recovery_suggestions': self.recovery_suggestions,
            'debug_info': self.debug_info,
            'related_errors': self.related_errors
        }


class PipelineErrorReporter:
    """
    Comprehensive error reporting system for the conversion pipeline.

    Features:
    - Detailed error context capture
    - Recovery suggestion generation
    - Performance impact analysis
    - Error correlation and pattern detection
    """

    def __init__(self):
        self.error_history: List[ErrorReport] = []
        self.error_counts: Dict[str, int] = {}
        self.session_start = time.perf_counter()

    def report_error(
        self,
        message: str,
        severity: ErrorSeverity,
        category: ErrorCategory,
        context: Optional[ErrorContext] = None,
        exception: Optional[Exception] = None,
        recovery_suggestions: Optional[List[str]] = None
    ) -> ErrorReport:
        """
        Report a comprehensive error with full context.

        Args:
            message: Human-readable error description
            severity: Error severity level
            category: Error category for classification
            context: Detailed error context
            exception: Original exception if available
            recovery_suggestions: Suggested recovery actions

        Returns:
            ErrorReport: Comprehensive error report
        """
        error_id = f"{category.value}_{int(time.time())}_{len(self.error_history)}"

        if context is None:
            context = ErrorContext()

        if recovery_suggestions is None:
            recovery_suggestions = self._generate_recovery_suggestions(category, exception)

        # Capture stack trace
        stack_trace = None
        if exception:
            stack_trace = ''.join(traceback.format_exception(
                type(exception), exception, exception.__traceback__
            ))

        # Generate debug info
        debug_info = self._generate_debug_info(category, exception, context)

        # Create error report
        report = ErrorReport(
            error_id=error_id,
            message=message,
            severity=severity,
            category=category,
            context=context,
            exception=exception,
            stack_trace=stack_trace,
            recovery_suggestions=recovery_suggestions,
            debug_info=debug_info
        )

        # Store and track
        self.error_history.append(report)
        category_key = category.value
        self.error_counts[category_key] = self.error_counts.get(category_key, 0) + 1

        # Log based on severity
        log_level = self._get_log_level(severity)
        logger.log(log_level, f"Pipeline Error [{error_id}]: {message}")

        if severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            logger.error(f"Error details: {report.to_dict()}")

        return report

    def report_parsing_error(
        self,
        message: str,
        svg_content: Optional[str] = None,
        exception: Optional[Exception] = None
    ) -> ErrorReport:
        """Report parsing-specific error with SVG context"""
        context = ErrorContext(
            stage="parsing",
            operation="svg_parsing",
            input_data={
                'svg_length': len(svg_content) if svg_content else 0,
                'svg_sample': svg_content[:200] + "..." if svg_content and len(svg_content) > 200 else svg_content
            }
        )

        return self.report_error(
            message=message,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.PARSING,
            context=context,
            exception=exception
        )

    def report_analysis_error(
        self,
        message: str,
        element_count: Optional[int] = None,
        complexity_score: Optional[float] = None,
        exception: Optional[Exception] = None
    ) -> ErrorReport:
        """Report analysis-specific error with complexity context"""
        context = ErrorContext(
            stage="analysis",
            operation="svg_analysis",
            input_data={
                'element_count': element_count,
                'complexity_score': complexity_score
            }
        )

        return self.report_error(
            message=message,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.ANALYSIS,
            context=context,
            exception=exception
        )

    def report_mapping_error(
        self,
        message: str,
        element_type: Optional[str] = None,
        mapper_name: Optional[str] = None,
        exception: Optional[Exception] = None
    ) -> ErrorReport:
        """Report mapping-specific error with element context"""
        context = ErrorContext(
            stage="mapping",
            operation="element_mapping",
            input_data={
                'element_type': element_type,
                'mapper_name': mapper_name
            }
        )

        return self.report_error(
            message=message,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.MAPPING,
            context=context,
            exception=exception
        )

    def get_error_summary(self) -> Dict[str, Any]:
        """Get comprehensive error summary for debugging"""
        session_duration = time.perf_counter() - self.session_start

        return {
            'session_duration_ms': session_duration * 1000,
            'total_errors': len(self.error_history),
            'error_counts_by_category': self.error_counts.copy(),
            'severity_distribution': self._get_severity_distribution(),
            'recent_errors': [
                error.to_dict() for error in self.error_history[-5:]
            ],
            'error_patterns': self._detect_error_patterns()
        }

    def _generate_recovery_suggestions(
        self,
        category: ErrorCategory,
        exception: Optional[Exception]
    ) -> List[str]:
        """Generate context-aware recovery suggestions"""
        suggestions = []

        # Category-specific suggestions
        if category == ErrorCategory.PARSING:
            suggestions.extend([
                "Validate SVG file structure and encoding",
                "Check for malformed XML or missing namespaces",
                "Try preprocessing with SVG optimization tools",
                "Verify file is valid SVG (not corrupted)"
            ])
        elif category == ErrorCategory.ANALYSIS:
            suggestions.extend([
                "Check SVG complexity and element count",
                "Verify all referenced resources exist",
                "Try with simplified SVG version",
                "Check for unsupported SVG features"
            ])
        elif category == ErrorCategory.MAPPING:
            suggestions.extend([
                "Verify mapper is registered for element type",
                "Check element has required attributes",
                "Try converting problematic elements manually",
                "Update mapper configuration"
            ])
        elif category == ErrorCategory.EMBEDDING:
            suggestions.extend([
                "Check DrawingML template validity",
                "Verify slide dimensions and constraints",
                "Check available system resources",
                "Try reducing output complexity"
            ])
        elif category == ErrorCategory.PACKAGING:
            suggestions.extend([
                "Verify output directory permissions",
                "Check available disk space",
                "Try alternative output format",
                "Check PPTX template integrity"
            ])

        # Exception-specific suggestions
        if exception:
            exception_type = type(exception).__name__
            if "Memory" in exception_type:
                suggestions.append("Increase available memory or reduce SVG complexity")
            elif "Permission" in exception_type:
                suggestions.append("Check file and directory permissions")
            elif "FileNotFound" in exception_type:
                suggestions.append("Verify all required files and resources exist")
            elif "Timeout" in exception_type:
                suggestions.append("Increase timeout limits or optimize processing")

        return suggestions

    def _generate_debug_info(
        self,
        category: ErrorCategory,
        exception: Optional[Exception],
        context: ErrorContext
    ) -> Dict[str, Any]:
        """Generate detailed debug information"""
        debug_info = {
            'python_version': __import__('sys').version,
            'session_errors': len(self.error_history),
            'category_error_count': self.error_counts.get(category.value, 0)
        }

        # Add exception details
        if exception:
            debug_info.update({
                'exception_type': type(exception).__name__,
                'exception_args': str(exception.args),
                'exception_str': str(exception)
            })

        # Add context-specific debug info
        if context.performance_metrics:
            debug_info['performance_metrics'] = context.performance_metrics

        return debug_info

    def _get_log_level(self, severity: ErrorSeverity) -> int:
        """Get appropriate log level for severity"""
        mapping = {
            ErrorSeverity.LOW: logging.INFO,
            ErrorSeverity.MEDIUM: logging.WARNING,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL
        }
        return mapping.get(severity, logging.ERROR)

    def _get_severity_distribution(self) -> Dict[str, int]:
        """Get distribution of errors by severity"""
        distribution = {}
        for error in self.error_history:
            severity = error.severity.value
            distribution[severity] = distribution.get(severity, 0) + 1
        return distribution

    def _detect_error_patterns(self) -> List[Dict[str, Any]]:
        """Detect patterns in error history"""
        patterns = []

        # Detect repeated errors
        error_messages = [error.message for error in self.error_history]
        message_counts = {}
        for message in error_messages:
            message_counts[message] = message_counts.get(message, 0) + 1

        for message, count in message_counts.items():
            if count > 1:
                patterns.append({
                    'type': 'repeated_error',
                    'message': message,
                    'count': count
                })

        # Detect error cascades (multiple errors in short time)
        if len(self.error_history) >= 3:
            recent_errors = self.error_history[-3:]
            time_span = recent_errors[-1].context.timestamp - recent_errors[0].context.timestamp
            if time_span < 1.0:  # Less than 1 second
                patterns.append({
                    'type': 'error_cascade',
                    'error_count': 3,
                    'time_span_ms': time_span * 1000
                })

        return patterns