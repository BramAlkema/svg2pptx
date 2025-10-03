#!/usr/bin/env python3
"""
FilterFactory for Dynamic Filter Creation

Implements factory pattern for creating appropriate filter processors
based on SVG filter primitive types with policy-driven selection
and fallback handling.
"""

from typing import Dict, Optional, Type, Set, TYPE_CHECKING
import logging
from lxml import etree as ET

from .base import FilterProcessor, FilterContext

if TYPE_CHECKING:
    from ..policy.engine import Policy

logger = logging.getLogger(__name__)


class FilterRegistrationError(Exception):
    """Exception raised when filter registration fails."""
    pass


class FilterNotFoundError(Exception):
    """Exception raised when requested filter is not available."""
    pass


class FilterFactory:
    """
    Factory for creating appropriate filter processors dynamically.

    Manages filter registration, creation, and policy-based selection
    of rendering strategies. Provides fallback handling for unsupported
    or missing filter implementations.
    """

    def __init__(self, policy: Optional['Policy'] = None):
        """
        Initialize FilterFactory with optional policy engine.

        Args:
            policy: Policy engine for filter selection decisions
        """
        self.policy = policy
        self._filter_registry: Dict[str, Type[FilterProcessor]] = {}
        self._supported_filters: Set[str] = set()
        self._fallback_handlers: Dict[str, FilterProcessor] = {}
        self.logger = logging.getLogger(__name__)

        # Initialize with core SVG filter primitives
        self._initialize_core_filters()

    def register_filter(self, filter_type: str, processor_class: Type[FilterProcessor]) -> None:
        """
        Register a filter processor class for a specific filter type.

        Args:
            filter_type: SVG filter primitive name (e.g., 'feBlur', 'feOffset')
            processor_class: FilterProcessor subclass to handle this filter

        Raises:
            FilterRegistrationError: If registration fails
        """
        if not filter_type:
            raise FilterRegistrationError("Filter type cannot be empty")

        if not issubclass(processor_class, FilterProcessor):
            raise FilterRegistrationError(
                f"Processor class must inherit from FilterProcessor, got {processor_class}"
            )

        # Check for duplicate registration
        if filter_type in self._filter_registry:
            existing = self._filter_registry[filter_type]
            if existing != processor_class:
                self.logger.warning(
                    f"Overriding existing filter registration for {filter_type}: "
                    f"{existing} -> {processor_class}"
                )

        self._filter_registry[filter_type] = processor_class
        self._supported_filters.add(filter_type)

        self.logger.debug(f"Registered filter processor: {filter_type} -> {processor_class.__name__}")

    def unregister_filter(self, filter_type: str) -> bool:
        """
        Unregister a filter processor.

        Args:
            filter_type: Filter type to unregister

        Returns:
            True if filter was unregistered, False if not found
        """
        if filter_type in self._filter_registry:
            del self._filter_registry[filter_type]
            self._supported_filters.discard(filter_type)
            self.logger.debug(f"Unregistered filter: {filter_type}")
            return True
        return False

    def create_filter(self, filter_type: str) -> Optional[FilterProcessor]:
        """
        Create a filter processor for the given filter type.

        Args:
            filter_type: SVG filter primitive name

        Returns:
            FilterProcessor instance if available, None if not supported

        Raises:
            FilterRegistrationError: If filter creation fails
        """
        # Normalize filter type (remove namespace if present)
        normalized_type = self._normalize_filter_type(filter_type)

        # Check if we have a registered processor
        if normalized_type in self._filter_registry:
            try:
                processor_class = self._filter_registry[normalized_type]
                processor = processor_class(normalized_type, self.policy)
                self.logger.debug(f"Created filter processor: {normalized_type}")
                return processor
            except Exception as e:
                raise FilterRegistrationError(
                    f"Failed to create filter processor for {normalized_type}: {e}"
                ) from e

        # Check for fallback handler
        if normalized_type in self._fallback_handlers:
            self.logger.debug(f"Using fallback handler for {normalized_type}")
            return self._fallback_handlers[normalized_type]

        # No processor available
        self.logger.warning(f"No filter processor available for {normalized_type}")
        return None

    def create_filter_for_element(self, element: ET.Element) -> Optional[FilterProcessor]:
        """
        Create appropriate filter processor for an SVG element.

        Args:
            element: SVG filter primitive element

        Returns:
            FilterProcessor instance if available, None otherwise
        """
        if element is None:
            return None

        # Extract filter type from element tag
        tag_name = self._get_element_tag_name(element)
        if not tag_name:
            return None

        return self.create_filter(tag_name)

    def is_filter_supported(self, filter_type: str) -> bool:
        """
        Check if a filter type is supported.

        Args:
            filter_type: Filter type to check

        Returns:
            True if filter is supported (directly, via fallback, or marked as core)
        """
        normalized_type = self._normalize_filter_type(filter_type)
        return (
            normalized_type in self._filter_registry or
            normalized_type in self._fallback_handlers or
            normalized_type in self._supported_filters
        )

    def get_supported_filters(self) -> Set[str]:
        """
        Get set of all supported filter types.

        Returns:
            Set of supported filter type names
        """
        return self._supported_filters.copy()

    def get_filter_coverage(self) -> Dict[str, bool]:
        """
        Get coverage report for all standard SVG filter primitives.

        Returns:
            Dictionary mapping filter types to availability status
        """
        standard_filters = {
            'feBlend', 'feColorMatrix', 'feComponentTransfer', 'feComposite',
            'feConvolveMatrix', 'feDiffuseLighting', 'feDisplacementMap',
            'feDropShadow', 'feFlood', 'feGaussianBlur', 'feImage', 'feMerge',
            'feMorphology', 'feOffset', 'feSpecularLighting', 'feTile', 'feTurbulence'
        }

        return {
            filter_type: self.is_filter_supported(filter_type)
            for filter_type in standard_filters
        }

    def register_fallback_handler(self, filter_type: str, handler: FilterProcessor) -> None:
        """
        Register a fallback handler for unsupported filters.

        Args:
            filter_type: Filter type to handle
            handler: FilterProcessor instance to use as fallback
        """
        self._fallback_handlers[filter_type] = handler
        self.logger.debug(f"Registered fallback handler for {filter_type}")

    def _initialize_core_filters(self) -> None:
        """
        Initialize factory with core filter registrations.

        This method registers the basic filters that are always available
        without requiring explicit imports or setup.
        """
        # Import and register actual filter processors
        try:
            from .turbulence import TurbulenceProcessor
            from .image import ImageProcessor
            from .blur import GaussianBlurProcessor
            from .drop_shadow import DropShadowProcessor
            from .diffuse_lighting import DiffuseLightingProcessor
            from .specular_lighting import SpecularLightingProcessor
            from .offset import OffsetProcessor
            from .flood import FloodProcessor
            from .blend import BlendProcessor
            from .color_matrix import ColorMatrixProcessor
            from .composite import CompositeProcessor
            from .morphology import MorphologyProcessor
            from .component_transfer import ComponentTransferProcessor
            from .convolve_matrix import ConvolveMatrixProcessor
            from .displacement_map import DisplacementMapProcessor
            from .tile import TileProcessor

            # Register core filter processors
            core_filters = {
                'feTurbulence': TurbulenceProcessor,
                'feImage': ImageProcessor,
                'feGaussianBlur': GaussianBlurProcessor,
                'feDropShadow': DropShadowProcessor,
                'feDiffuseLighting': DiffuseLightingProcessor,
                'feSpecularLighting': SpecularLightingProcessor,
                'feOffset': OffsetProcessor,
                'feFlood': FloodProcessor,
                'feBlend': BlendProcessor,
                'feColorMatrix': ColorMatrixProcessor,
                'feComposite': CompositeProcessor,
                'feMorphology': MorphologyProcessor,
                'feComponentTransfer': ComponentTransferProcessor,
                'feConvolveMatrix': ConvolveMatrixProcessor,
                'feDisplacementMap': DisplacementMapProcessor,
                'feTile': TileProcessor,
            }

            # Register each filter processor
            for filter_type, processor_class in core_filters.items():
                try:
                    self.register_filter(filter_type, processor_class)
                except Exception as e:
                    self.logger.warning(f"Failed to register {filter_type}: {e}")

            self.logger.debug(f"Initialized core filters: {list(core_filters.keys())}")

        except ImportError as e:
            # Fallback to marking as supported without actual processors
            self.logger.warning(f"Could not import filter processors: {e}")

            legacy_filters = {
                'feGaussianBlur', 'feDropShadow', 'feDiffuseLighting',
                'feSpecularLighting', 'feMerge'
            }
            self._supported_filters.update(legacy_filters)
            self.logger.debug(f"Initialized legacy filter placeholders: {list(legacy_filters)}")

    def _normalize_filter_type(self, filter_type: str) -> str:
        """
        Normalize filter type name by removing namespace and cleaning.

        Args:
            filter_type: Raw filter type name

        Returns:
            Normalized filter type name
        """
        if not filter_type:
            return ""

        # Remove namespace prefix if present
        if filter_type.startswith("{"):
            # Handle {namespace}localname format
            if "}" in filter_type:
                filter_type = filter_type.split("}", 1)[1]

        # Remove any whitespace
        filter_type = filter_type.strip()

        return filter_type

    def _get_element_tag_name(self, element: ET.Element) -> str:
        """
        Extract tag name from SVG element.

        Args:
            element: SVG element

        Returns:
            Tag name without namespace
        """
        if element is None or element.tag is None:
            return ""

        return self._normalize_filter_type(element.tag)

    def validate_configuration(self) -> Dict[str, any]:
        """
        Validate factory configuration and return status report.

        Returns:
            Dictionary with validation results and statistics
        """
        coverage = self.get_filter_coverage()
        supported_count = sum(1 for supported in coverage.values() if supported)
        total_count = len(coverage)

        validation_result = {
            'total_filters': total_count,
            'supported_filters': supported_count,
            'coverage_percentage': (supported_count / total_count * 100) if total_count > 0 else 0,
            'registered_processors': len(self._filter_registry),
            'fallback_handlers': len(self._fallback_handlers),
            'missing_filters': [
                filter_type for filter_type, supported in coverage.items()
                if not supported
            ],
            'configuration_valid': True
        }

        # Log validation results
        self.logger.info(
            f"Filter factory validation: {supported_count}/{total_count} filters supported "
            f"({validation_result['coverage_percentage']:.1f}%)"
        )

        if validation_result['missing_filters']:
            self.logger.warning(
                f"Missing filter support: {validation_result['missing_filters']}"
            )

        return validation_result

    def __str__(self) -> str:
        """String representation of factory state."""
        return (
            f"FilterFactory(registered={len(self._filter_registry)}, "
            f"fallbacks={len(self._fallback_handlers)}, "
            f"policy={'enabled' if self.policy else 'disabled'})"
        )

    def __repr__(self) -> str:
        """Detailed string representation."""
        return (
            f"FilterFactory(policy={self.policy}, "
            f"registered_filters={list(self._filter_registry.keys())}, "
            f"fallback_handlers={list(self._fallback_handlers.keys())})"
        )


def create_filter_factory(policy: Optional['Policy'] = None) -> FilterFactory:
    """
    Factory function to create FilterFactory with proper configuration.

    Args:
        policy: Optional policy engine for filter decisions

    Returns:
        Configured FilterFactory instance
    """
    factory = FilterFactory(policy)
    return factory