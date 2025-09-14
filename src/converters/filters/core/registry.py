"""
Filter registry for dynamic filter discovery and instantiation.

This module provides the FilterRegistry class that manages the registration,
discovery, and instantiation of filter implementations with thread-safe
operations and comprehensive error handling.
"""

import threading
from typing import Dict, List, Optional, Type, Any
import logging
from lxml import etree

from .base import Filter, FilterContext, FilterException

logger = logging.getLogger(__name__)


class FilterRegistrationError(FilterException):
    """Exception raised when filter registration fails."""
    pass


class FilterNotFoundError(FilterException):
    """Exception raised when a requested filter is not found."""

    def __init__(self, filter_type: str):
        self.filter_type = filter_type
        super().__init__(f"Filter not found: {filter_type}")


class FilterRegistry:
    """
    Registry for managing and dispatching filter implementations.

    This class provides a centralized registry for all filter implementations,
    enabling dynamic filter discovery, registration, and instantiation. It supports
    thread-safe operations and maintains efficient lookup structures for fast
    filter retrieval.

    The registry uses a combination of type-based and element-based lookup to
    quickly find appropriate filters for SVG elements during processing.

    Attributes:
        filters: Dictionary mapping filter types to filter instances
        filter_map: Dictionary mapping element patterns to applicable filters
        lock: Thread synchronization lock for safe concurrent access

    Example:
        >>> registry = FilterRegistry()
        >>> registry.register(BlurFilter())
        >>> registry.register(ShadowFilter())
        >>>
        >>> blur_filter = registry.get_filter('blur')
        >>> filters_list = registry.list_filters()
        >>>
        >>> # Find filter for specific element
        >>> filter_obj = registry.find_filter_for_element(svg_element, context)
    """

    def __init__(self, allow_duplicates: bool = False):
        """
        Initialize the filter registry.

        Args:
            allow_duplicates: Whether to allow multiple filters with the same type
        """
        self.filters: Dict[str, Filter] = {}
        self.filter_map: Dict[str, List[Filter]] = {}
        self.lock = threading.RLock()  # Reentrant lock for nested operations
        self.allow_duplicates = allow_duplicates

        self.logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")

    def register(self, filter_instance: Filter) -> None:
        """
        Register a filter instance with the registry.

        Args:
            filter_instance: Filter instance to register

        Raises:
            FilterRegistrationError: If registration fails due to invalid filter
                                   or duplicate registration when not allowed
        """
        if filter_instance is None:
            raise FilterRegistrationError("Cannot register None as a filter")

        if not isinstance(filter_instance, Filter):
            raise FilterRegistrationError(
                f"Object must be an instance of Filter, got {type(filter_instance)}"
            )

        filter_type = filter_instance.get_filter_type()

        with self.lock:
            # Check for duplicates if not allowed
            if not self.allow_duplicates and filter_type in self.filters:
                raise FilterRegistrationError(
                    f"Filter type '{filter_type}' is already registered. "
                    f"Use allow_duplicates=True or unregister the existing filter first."
                )

            # Register the filter
            self.filters[filter_type] = filter_instance

            # Update element mapping for quick lookup
            self._update_element_mapping(filter_instance)

            self.logger.debug(f"Registered filter: {filter_type} ({filter_instance.__class__.__name__})")

    def register_class(self, filter_class: Type[Filter]) -> None:
        """
        Register a filter class by instantiating it.

        Args:
            filter_class: Filter class to instantiate and register

        Raises:
            FilterRegistrationError: If instantiation or registration fails
        """
        try:
            if not issubclass(filter_class, Filter):
                raise FilterRegistrationError(
                    f"Class must be a subclass of Filter, got {filter_class}"
                )

            filter_instance = filter_class()
            self.register(filter_instance)

        except Exception as e:
            raise FilterRegistrationError(f"Failed to register filter class {filter_class}: {e}")

    def register_filter(self, filter_instance: Filter) -> None:
        """
        Register a filter instance (alias for register method).

        Args:
            filter_instance: Filter instance to register
        """
        self.register(filter_instance)

    def get_filter(self, filter_type: str) -> Filter:
        """
        Get a registered filter by its type identifier.

        Args:
            filter_type: Type identifier of the filter to retrieve

        Returns:
            Filter instance for the requested type

        Raises:
            FilterNotFoundError: If no filter is registered for the given type
        """
        with self.lock:
            if filter_type not in self.filters:
                raise FilterNotFoundError(filter_type)

            return self.filters[filter_type]

    def list_filters(self) -> List[str]:
        """
        Get a list of all registered filter types.

        Returns:
            List of filter type identifiers
        """
        with self.lock:
            return list(self.filters.keys())

    def find_filter_for_element(
        self,
        element: etree.Element,
        context: FilterContext
    ) -> Optional[Filter]:
        """
        Find the most appropriate filter for a given SVG element.

        This method checks all registered filters to find one that can
        process the given element based on the filter's can_apply method.

        Args:
            element: SVG element to find a filter for
            context: Filter processing context

        Returns:
            Filter instance that can process the element, or None if no
            suitable filter is found
        """
        with self.lock:
            # First try element mapping for fast lookup
            element_tag = element.tag
            if element_tag in self.filter_map:
                for filter_obj in self.filter_map[element_tag]:
                    try:
                        if filter_obj.can_apply(element, context):
                            return filter_obj
                    except Exception as e:
                        self.logger.warning(
                            f"Filter {filter_obj.filter_type} raised exception in can_apply: {e}"
                        )

            # Fallback to checking all filters
            for filter_obj in self.filters.values():
                try:
                    if filter_obj.can_apply(element, context):
                        return filter_obj
                except Exception as e:
                    self.logger.warning(
                        f"Filter {filter_obj.filter_type} raised exception in can_apply: {e}"
                    )

            return None

    def get_applicable_filters(
        self,
        element: etree.Element,
        context: FilterContext
    ) -> List[Filter]:
        """
        Get all filters that can be applied to a given SVG element.

        Args:
            element: SVG element to check
            context: Filter processing context

        Returns:
            List of Filter instances that can process the element
        """
        applicable_filters = []

        with self.lock:
            for filter_obj in self.filters.values():
                try:
                    if filter_obj.can_apply(element, context):
                        applicable_filters.append(filter_obj)
                except Exception as e:
                    self.logger.warning(
                        f"Filter {filter_obj.filter_type} raised exception in can_apply: {e}"
                    )

        return applicable_filters

    def unregister(self, filter_type: str) -> bool:
        """
        Unregister a filter by its type identifier.

        Args:
            filter_type: Type identifier of the filter to remove

        Returns:
            True if the filter was found and removed, False otherwise
        """
        with self.lock:
            if filter_type in self.filters:
                filter_instance = self.filters[filter_type]
                del self.filters[filter_type]

                # Remove from element mapping
                self._remove_from_element_mapping(filter_instance)

                self.logger.debug(f"Unregistered filter: {filter_type}")
                return True

            return False

    def clear(self) -> None:
        """Remove all registered filters from the registry."""
        with self.lock:
            self.filters.clear()
            self.filter_map.clear()
            self.logger.debug("Cleared all filters from registry")

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get registry statistics and information.

        Returns:
            Dictionary containing registry statistics
        """
        with self.lock:
            return {
                'total_filters': len(self.filters),
                'filter_types': list(self.filters.keys()),
                'element_mappings': len(self.filter_map),
                'allow_duplicates': self.allow_duplicates
            }

    def register_default_filters(self) -> None:
        """
        Register default filter implementations.

        This method loads and registers the standard set of filters
        that are commonly used for SVG processing. It's typically
        called during initialization to set up a working filter system.
        """
        try:
            self._load_default_filters()
            self.logger.info("Default filters registered successfully")
        except Exception as e:
            self.logger.error(f"Failed to register default filters: {e}")
            raise FilterRegistrationError(f"Default filter registration failed: {e}")

    def _load_default_filters(self) -> None:
        """
        Load default filter implementations.

        This method will be implemented to load standard filters
        from the image and geometric modules when they are available.
        """
        # TODO: Implement default filter loading when filter modules are ready
        # from ..image.blur import GaussianBlurFilter, MotionBlurFilter
        # from ..image.color import ColorMatrixFilter, FloodFilter
        # from ..geometric.transforms import OffsetFilter, TurbulenceFilter
        #
        # default_filters = [
        #     GaussianBlurFilter(),
        #     MotionBlurFilter(),
        #     ColorMatrixFilter(),
        #     FloodFilter(),
        #     OffsetFilter(),
        #     TurbulenceFilter(),
        # ]
        #
        # for filter_obj in default_filters:
        #     self.register(filter_obj)

        pass

    def _update_element_mapping(self, filter_instance: Filter) -> None:
        """
        Update element mapping for efficient filter lookup.

        This internal method maintains a mapping from SVG element tags
        to applicable filters for fast lookup during processing.

        Args:
            filter_instance: Filter to add to element mapping
        """
        # This is a simplified mapping strategy
        # In practice, you might want more sophisticated mapping based on
        # filter capabilities, element attributes, etc.

        filter_type = filter_instance.get_filter_type()

        # Map common element patterns to filter types
        element_mappings = {
            'blur': ['{http://www.w3.org/2000/svg}feGaussianBlur',
                    '{http://www.w3.org/2000/svg}feBlur'],
            'shadow': ['{http://www.w3.org/2000/svg}feDropShadow',
                      '{http://www.w3.org/2000/svg}feShadow'],
            'color': ['{http://www.w3.org/2000/svg}feColorMatrix',
                     '{http://www.w3.org/2000/svg}feFlood'],
            'offset': ['{http://www.w3.org/2000/svg}feOffset'],
            'composite': ['{http://www.w3.org/2000/svg}feComposite',
                         '{http://www.w3.org/2000/svg}feBlend'],
            'morph': ['{http://www.w3.org/2000/svg}feMorphology'],
            'convolution': ['{http://www.w3.org/2000/svg}feConvolveMatrix'],
            'turbulence': ['{http://www.w3.org/2000/svg}feTurbulence'],
            'lighting': ['{http://www.w3.org/2000/svg}feDiffuseLighting',
                        '{http://www.w3.org/2000/svg}feSpecularLighting'],
        }

        if filter_type in element_mappings:
            for element_tag in element_mappings[filter_type]:
                if element_tag not in self.filter_map:
                    self.filter_map[element_tag] = []
                self.filter_map[element_tag].append(filter_instance)

    def _remove_from_element_mapping(self, filter_instance: Filter) -> None:
        """
        Remove filter from element mapping.

        Args:
            filter_instance: Filter to remove from element mapping
        """
        for element_tag, filter_list in self.filter_map.items():
            if filter_instance in filter_list:
                filter_list.remove(filter_instance)

        # Clean up empty mappings
        empty_mappings = [tag for tag, filter_list in self.filter_map.items() if not filter_list]
        for tag in empty_mappings:
            del self.filter_map[tag]

    def __str__(self) -> str:
        """String representation of the registry."""
        with self.lock:
            return f"FilterRegistry(filters={len(self.filters)}, types={list(self.filters.keys())})"

    def __repr__(self) -> str:
        """Detailed string representation of the registry."""
        with self.lock:
            return (
                f"FilterRegistry("
                f"filters={len(self.filters)}, "
                f"types={list(self.filters.keys())}, "
                f"mappings={len(self.filter_map)}, "
                f"allow_duplicates={self.allow_duplicates})"
            )