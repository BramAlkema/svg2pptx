"""
Result Types for SVG Converter System

This module provides immutable result types for consistent error handling,
graceful fallback behavior, and comprehensive debugging support across
the StyleEngine and TextPathEngine implementations.

Key Features:
- Immutable dataclasses for thread-safe operations
- Factory methods for common result patterns
- Comprehensive error tracking and debugging support
- Type-safe success/error state management
- Graceful fallback content handling
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Union
from enum import Enum


class ConversionStatus(Enum):
    """Status enumeration for conversion results"""
    SUCCESS = "success"
    SUCCESS_WITH_FALLBACK = "success_with_fallback"
    ERROR_WITH_FALLBACK = "error_with_fallback"
    CRITICAL_ERROR = "critical_error"


@dataclass(frozen=True)
class ConversionError:
    """Immutable error information with context"""
    message: str
    error_type: str
    context: Dict[str, Any] = field(default_factory=dict)
    source_location: Optional[str] = None

    def __str__(self) -> str:
        return f"{self.error_type}: {self.message}"

    def __repr__(self) -> str:
        return f"ConversionError(type='{self.error_type}', message='{self.message}')"


@dataclass(frozen=True)
class StyleResult:
    """
    Immutable result of style processing with comprehensive error tracking.

    This result type enables graceful fallback behavior while maintaining
    full visibility into any issues encountered during style processing.
    """
    properties: Dict[str, Any] = field(default_factory=dict)
    errors: List[ConversionError] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    fallbacks_used: List[str] = field(default_factory=list)
    status: ConversionStatus = ConversionStatus.SUCCESS

    @property
    def has_errors(self) -> bool:
        """Check if any errors were encountered"""
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        """Check if any warnings were generated"""
        return len(self.warnings) > 0

    @property
    def has_fallbacks(self) -> bool:
        """Check if any fallbacks were used"""
        return len(self.fallbacks_used) > 0

    @property
    def is_success(self) -> bool:
        """Check if processing was successful (with or without fallbacks)"""
        return self.status in [ConversionStatus.SUCCESS, ConversionStatus.SUCCESS_WITH_FALLBACK]

    def __str__(self) -> str:
        status_info = [f"Status: {self.status.value}"]
        if self.properties:
            status_info.append(f"Properties: {len(self.properties)}")
        if self.has_errors:
            status_info.append(f"Errors: {len(self.errors)}")
        if self.has_warnings:
            status_info.append(f"Warnings: {len(self.warnings)}")
        if self.has_fallbacks:
            status_info.append(f"Fallbacks: {len(self.fallbacks_used)}")
        return f"StyleResult({', '.join(status_info)})"

    @classmethod
    def success(cls, properties: Dict[str, Any]) -> 'StyleResult':
        """Create successful result with properties"""
        return cls(
            properties=properties,
            status=ConversionStatus.SUCCESS
        )

    @classmethod
    def success_with_fallbacks(cls, properties: Dict[str, Any], fallbacks: List[str]) -> 'StyleResult':
        """Create successful result that used fallbacks"""
        return cls(
            properties=properties,
            fallbacks_used=fallbacks,
            status=ConversionStatus.SUCCESS_WITH_FALLBACK
        )

    @classmethod
    def error_with_fallback(cls, errors: List[ConversionError], fallback_properties: Dict[str, Any],
                           fallbacks: List[str]) -> 'StyleResult':
        """Create error result with fallback content"""
        return cls(
            properties=fallback_properties,
            errors=errors,
            fallbacks_used=fallbacks,
            status=ConversionStatus.ERROR_WITH_FALLBACK
        )


@dataclass(frozen=True)
class FillResult:
    """
    Immutable result of fill/gradient processing with fallback support.

    This ensures that gradient resolution always provides usable content,
    even when the requested gradient is invalid or missing.
    """
    content: str = ""
    is_fallback: bool = False
    original_request: str = ""
    fallback_reason: Optional[str] = None
    gradient_id: Optional[str] = None

    @property
    def has_content(self) -> bool:
        """Check if result contains drawable content"""
        return len(self.content.strip()) > 0

    def __str__(self) -> str:
        content_preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        status = "fallback" if self.is_fallback else "original"
        return f"FillResult({status}: '{content_preview}')"

    @classmethod
    def success(cls, content: str, gradient_id: Optional[str] = None) -> 'FillResult':
        """Create successful fill result"""
        return cls(
            content=content,
            is_fallback=False,
            gradient_id=gradient_id
        )

    @classmethod
    def fallback(cls, fallback_content: str, original_request: str, reason: str) -> 'FillResult':
        """Create fallback fill result with explanation"""
        return cls(
            content=fallback_content,
            is_fallback=True,
            original_request=original_request,
            fallback_reason=reason
        )


@dataclass(frozen=True)
class TextConversionConfig:
    """
    Immutable configuration for text conversion with validation.

    Provides sensible defaults and validation for text-to-path conversion
    settings while maintaining immutability for thread safety.
    """
    font_fallback_enabled: bool = True
    path_optimization_level: int = 1  # 0=none, 1=basic, 2=aggressive
    preserve_decorations: bool = True
    max_cache_size: int = 256
    coordinate_precision: int = 2  # Decimal places for coordinates
    fallback_font_family: str = "Arial, sans-serif"

    def __post_init__(self):
        """Validate configuration values"""
        if not (0 <= self.path_optimization_level <= 2):
            raise ValueError("path_optimization_level must be 0, 1, or 2")
        if self.max_cache_size < 0:
            raise ValueError("max_cache_size must be non-negative")
        if self.coordinate_precision < 0:
            raise ValueError("coordinate_precision must be non-negative")

    def __str__(self) -> str:
        return (f"TextConversionConfig(fallback={self.font_fallback_enabled}, "
                f"optimization={self.path_optimization_level}, "
                f"cache_size={self.max_cache_size})")

    @classmethod
    def minimal(cls) -> 'TextConversionConfig':
        """Create minimal configuration for basic text conversion"""
        return cls(
            font_fallback_enabled=True,
            path_optimization_level=0,
            preserve_decorations=False,
            max_cache_size=64
        )

    @classmethod
    def performance_optimized(cls) -> 'TextConversionConfig':
        """Create configuration optimized for performance"""
        return cls(
            font_fallback_enabled=True,
            path_optimization_level=2,
            preserve_decorations=True,
            max_cache_size=512
        )


@dataclass(frozen=True)
class ConversionResult:
    """
    Type-safe result with success/error states and graceful fallback support.

    This is the primary result type for text conversion operations,
    ensuring that operations never return empty content without explanation.
    """
    success: bool
    content: str
    errors: List[ConversionError] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    fallbacks: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def has_content(self) -> bool:
        """Check if result contains usable content"""
        return len(self.content.strip()) > 0

    @property
    def has_errors(self) -> bool:
        """Check if any errors were encountered"""
        return len(self.errors) > 0

    @property
    def has_fallbacks(self) -> bool:
        """Check if any fallbacks were used"""
        return len(self.fallbacks) > 0

    def __str__(self) -> str:
        status = "SUCCESS" if self.success else "ERROR"
        content_preview = self.content[:30] + "..." if len(self.content) > 30 else self.content
        details = []
        if self.has_errors:
            details.append(f"{len(self.errors)} errors")
        if self.has_fallbacks:
            details.append(f"{len(self.fallbacks)} fallbacks")
        detail_str = f" ({', '.join(details)})" if details else ""
        return f"ConversionResult({status}: '{content_preview}'{detail_str})"

    @classmethod
    def success_with_content(cls, content: str, metadata: Optional[Dict[str, Any]] = None) -> 'ConversionResult':
        """Create successful result with content"""
        return cls(
            success=True,
            content=content,
            metadata=metadata or {}
        )

    @classmethod
    def success_with_fallback(cls, content: str, fallbacks: List[str],
                             metadata: Optional[Dict[str, Any]] = None) -> 'ConversionResult':
        """Create successful result that used fallbacks"""
        return cls(
            success=True,
            content=content,
            fallbacks=fallbacks,
            metadata=metadata or {}
        )

    @classmethod
    def error_with_fallback(cls, error_message: str, fallback_content: str = "",
                           error_type: str = "ConversionError") -> 'ConversionResult':
        """Create error result with fallback content (never empty)"""
        # Ensure we always have some content, even for errors
        final_content = fallback_content if fallback_content.strip() else "<!-- Conversion failed -->"

        return cls(
            success=False,
            content=final_content,
            errors=[ConversionError(message=error_message, error_type=error_type)],
            fallbacks=["error_fallback"] if final_content else []
        )

    @classmethod
    def critical_error(cls, error_message: str, error_type: str = "CriticalError") -> 'ConversionResult':
        """Create critical error result with minimal fallback"""
        return cls(
            success=False,
            content="<!-- Critical conversion error -->",
            errors=[ConversionError(message=error_message, error_type=error_type)],
            fallbacks=["critical_error_fallback"]
        )


# Utility functions for common result patterns

def create_gradient_fallback_fill(original_url: str, reason: str) -> FillResult:
    """
    Create a standard gradient fallback fill result.

    This provides consistent fallback behavior when gradients are
    invalid or missing, ensuring visual output is always generated.
    """
    fallback_content = '<a:solidFill><a:srgbClr val="808080"/></a:solidFill>'
    return FillResult.fallback(
        fallback_content=fallback_content,
        original_request=original_url,
        reason=reason
    )


def create_text_shape_fallback(original_text: str, reason: str) -> ConversionResult:
    """
    Create a standard text shape fallback result.

    This ensures that text conversion always produces drawable content,
    even when font conversion fails or coordinate systems are unavailable.
    """
    # Create a basic text shape as fallback
    fallback_content = f'''
        <p:sp>
            <p:nvSpPr>
                <p:cNvPr id="1" name="Text Fallback"/>
                <p:cNvSpPr txBox="1"/>
                <p:nvPr/>
            </p:nvSpPr>
            <p:spPr>
                <a:xfrm>
                    <a:off x="0" y="0"/>
                    <a:ext cx="2000000" cy="400000"/>
                </a:xfrm>
                <a:prstGeom prst="rect">
                    <a:avLst/>
                </a:prstGeom>
                <a:noFill/>
            </p:spPr>
            <p:txBody>
                <a:bodyPr/>
                <a:lstStyle/>
                <a:p>
                    <a:r>
                        <a:rPr lang="en-US" sz="1200"/>
                        <a:t>{original_text[:100]}</a:t>
                    </a:r>
                </a:p>
            </p:txBody>
        </p:sp>'''

    return ConversionResult.error_with_fallback(
        error_message=reason,
        fallback_content=fallback_content.strip(),
        error_type="TextConversionError"
    )


# Type aliases for improved readability
ProcessingResult = Union[StyleResult, ConversionResult, FillResult]
ConfigurationType = Union[TextConversionConfig, Dict[str, Any]]