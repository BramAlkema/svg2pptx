#!/usr/bin/env python3
"""
Base Mapper Interface

Defines the common interface for all IR-to-output mappers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from enum import Enum

from ..ir import IRElement
from ..policy import Policy, PolicyDecision


class OutputFormat(Enum):
    """Output format for mapped elements"""
    NATIVE_DML = "native_dml"    # Native DrawingML
    EMF_VECTOR = "emf_vector"    # EMF vector fallback
    EMF_RASTER = "emf_raster"    # EMF raster fallback


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

    # Media files (for EMF blobs, images, etc.)
    media_files: Optional[List[Dict[str, Any]]] = None

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

    def __init__(self, policy: Policy):
        """
        Initialize mapper with policy engine.

        Args:
            policy: Policy engine for decision making
        """
        self.policy = policy
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