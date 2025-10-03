#!/usr/bin/env python3
"""
Base Mapper Interface

Defines the common interface for all IR-to-output mappers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Union, Optional, Dict, Any, List
from enum import Enum
import time

from ..ir import IRElement, Path, TextFrame, Group, Image, get_effective_navigation
from ..policy import Policy, PolicyDecision
from ..pipeline.hyperlinks import HyperlinkSpec
from ..pipeline.navigation import NavigationSpec


class OutputFormat(Enum):
    """Output format for mapped elements"""
    NATIVE_DML = "native_dml"    # Native DrawingML
    EMF_VECTOR = "emf_vector"    # EMF vector fallback
    EMF_RASTER = "emf_raster"    # EMF raster fallback


@dataclass
class MediaRequest:
    """
    Request for media file to be embedded in PPTX.

    The embedder (SlideBuilder) will:
    1. Write bytes_data to ppt/media/{filename}
    2. Allocate an rId via RelationshipManager
    3. Register content type via ContentTypesManager
    4. Patch the XML element at bind_xpath to set bind_attr="{rId}"
    """
    filename: str                # e.g., "image1.png"
    mime_type: str               # e.g., "image/png"
    bytes_data: bytes            # Raw file content
    content_type_ext: str        # e.g., "png" (for content types)

    # Where to patch relationship ID in the returned XML
    bind_xpath: str              # e.g., ".//a:blip"
    bind_attr: str = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed"

    # Deduplication
    sha256: Optional[str] = None # For deduplication


@dataclass
class MapperResult:
    """Result of mapping an IR element to output format"""
    element: IRElement
    output_format: OutputFormat
    xml_content: str
    policy_decision: PolicyDecision
    metadata: Dict[str, Any]

    # Quality metrics
    estimated_quality: float = 1.0       # 0.0-1.0
    estimated_performance: float = 1.0   # 0.0-1.0
    processing_time_ms: float = 0.0

    # Size metrics
    output_size_bytes: int = 0
    compression_ratio: float = 1.0

    # Media embedding (new pattern)
    media_requests: Optional[List[MediaRequest]] = None  # Media files to embed (images, etc.)

    # Media files (legacy - for EMF blobs, images, etc.)
    media_files: Optional[List[Dict[str, Any]]] = None

    # Navigation support (both legacy and enhanced)
    hyperlinks: Optional[List[HyperlinkSpec]] = None  # Legacy hyperlink support (deprecated)
    navigation: Optional[List[NavigationSpec]] = None  # Enhanced navigation support
    shape_id: Optional[str] = None                    # Unique identifier for shape linking (cNvPr @id/@name)
    linked_runs: Optional[List[Dict[str, Any]]] = None  # Text runs with navigation (for text-level linking)

    def __post_init__(self):
        if not (0.0 <= self.estimated_quality <= 1.0):
            raise ValueError(f"Quality must be 0.0-1.0, got {self.estimated_quality}")
        if not (0.0 <= self.estimated_performance <= 1.0):
            raise ValueError(f"Performance must be 0.0-1.0, got {self.estimated_performance}")


class MappingError(Exception):
    """Exception raised when mapping fails"""
    def __init__(self, message: str, element: IRElement = None, cause: Exception = None):
        super().__init__(message)
        self.element = element
        self.cause = cause


class Mapper(ABC):
    """
    Base class for IR to output format mappers.

    Each mapper is responsible for converting a specific IR element type
    to the appropriate output format based on policy decisions.
    """

    def __init__(self, policy: Policy, services=None):
        """
        Initialize mapper with policy engine and optional services.

        Args:
            policy: Policy engine for decision making
            services: Optional ConversionServices for advanced functionality
        """
        self.policy = policy
        self.services = services
        self._stats = {
            'total_mapped': 0,
            'native_count': 0,
            'emf_count': 0,
            'error_count': 0,
            'total_time_ms': 0.0
        }

    @abstractmethod
    def can_map(self, element: IRElement) -> bool:
        """
        Check if this mapper can handle the given element.

        Args:
            element: IR element to check

        Returns:
            True if mapper can handle this element type
        """
        pass

    @abstractmethod
    def map(self, element: IRElement) -> MapperResult:
        """
        Map IR element to output format.

        Args:
            element: IR element to map

        Returns:
            MapperResult with output XML and metadata

        Raises:
            MappingError: If mapping fails
        """
        pass

    def _record_mapping(self, result: MapperResult) -> None:
        """Record mapping statistics"""
        self._stats['total_mapped'] += 1
        self._stats['total_time_ms'] += result.processing_time_ms

        if result.output_format == OutputFormat.NATIVE_DML:
            self._stats['native_count'] += 1
        else:
            self._stats['emf_count'] += 1

    def _record_error(self, error: Exception) -> None:
        """Record mapping error"""
        self._stats['error_count'] += 1

    def get_statistics(self) -> Dict[str, Any]:
        """Get mapping statistics"""
        total = max(self._stats['total_mapped'], 1)
        return {
            **self._stats,
            'native_ratio': self._stats['native_count'] / total,
            'emf_ratio': self._stats['emf_count'] / total,
            'error_ratio': self._stats['error_count'] / total,
            'avg_time_ms': self._stats['total_time_ms'] / total
        }

    def reset_statistics(self) -> None:
        """Reset mapping statistics"""
        self._stats = {
            'total_mapped': 0,
            'native_count': 0,
            'emf_count': 0,
            'error_count': 0,
            'total_time_ms': 0.0
        }

    def _extract_hyperlink_info(self, element: IRElement) -> Dict[str, Any]:
        """
        Extract navigation information from IR element.

        Supports both NavigationSpec (preferred) and HyperlinkSpec (legacy) formats.
        Uses get_effective_navigation() to provide seamless conversion between formats.

        Args:
            element: IR element that may have navigation metadata

        Returns:
            Dictionary with navigation info for MapperResult:
            - navigation: List[NavigationSpec] or None (preferred format)
            - hyperlinks: List[HyperlinkSpec] or None (legacy format for backward compatibility)
            - shape_id: str or None
            - linked_runs: List[Dict] or None (for text elements)
        """
        hyperlink_info = {
            'navigation': None,
            'hyperlinks': None,
            'shape_id': None,
            'linked_runs': None
        }

        # Get effective navigation using the utility function
        effective_navigation = get_effective_navigation(element)

        if effective_navigation is not None:
            hyperlink_info['navigation'] = [effective_navigation]
            # Generate unique shape ID for linking
            hyperlink_info['shape_id'] = f"shape_{id(element)}"

            # For backward compatibility, also provide legacy hyperlink if original was HyperlinkSpec
            if hasattr(element, 'hyperlink') and element.hyperlink is not None:
                hyperlink_info['hyperlinks'] = [element.hyperlink]

            # For text elements, prepare linked runs info
            if hasattr(element, 'runs') and element.runs:
                text_content = self._get_text_content(element)
                hyperlink_info['linked_runs'] = [
                    {
                        'start_index': 0,
                        'end_index': len(text_content),
                        'text': text_content,
                        'navigation': effective_navigation,
                        # Legacy field for backward compatibility
                        'hyperlink': element.hyperlink if hasattr(element, 'hyperlink') else None
                    }
                ]

        return hyperlink_info

    def _get_text_content(self, element: IRElement) -> str:
        """
        Extract text content from text elements.

        Args:
            element: IR element that may contain text

        Returns:
            Concatenated text content from all runs
        """
        if hasattr(element, 'text_content'):
            return element.text_content
        elif hasattr(element, 'runs') and element.runs:
            return ''.join(run.text for run in element.runs)
        else:
            return ''


def validate_mapper_result(result: MapperResult) -> bool:
    """
    Validate mapper result for correctness.

    Args:
        result: Mapper result to validate

    Returns:
        True if result is valid

    Raises:
        ValueError: If result is invalid
    """
    if not result.xml_content.strip():
        raise ValueError("XML content cannot be empty")

    if result.output_size_bytes < 0:
        raise ValueError("Output size cannot be negative")

    if not result.policy_decision:
        raise ValueError("Policy decision is required")

    # Basic XML validation
    try:
        from xml.etree import ElementTree as ET
        ET.fromstring(f"<root>{result.xml_content}</root>")
    except ET.ParseError as e:
        raise ValueError(f"Invalid XML content: {e}")

    return True