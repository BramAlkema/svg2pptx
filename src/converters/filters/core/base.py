"""
Abstract base classes and core types for the SVG filter system.

This module provides the foundational interfaces and data structures
that all filter implementations must follow, ensuring consistency
and interoperability across the filter processing pipeline.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass
import logging
from lxml import etree

logger = logging.getLogger(__name__)


class FilterException(Exception):
    """Base exception class for filter-related errors."""
    pass


class FilterValidationError(FilterException, ValueError):
    """Exception raised when filter parameters or context are invalid."""
    pass


@dataclass
class FilterContext:
    """
    Context object containing shared state and dependencies for filter processing.

    This class encapsulates all the information and tools needed by filters
    to process SVG elements, including viewport information, conversion utilities,
    and element properties.

    Attributes:
        element: The SVG element being processed
        viewport: Viewport dimensions and information
        unit_converter: Utility for converting SVG units to EMUs
        transform_parser: Utility for parsing SVG transforms
        color_parser: Utility for parsing SVG colors
        properties: Element properties and attributes
        cache: Cache for storing computed values during processing

    Example:
        >>> context = FilterContext(
        ...     element=svg_element,
        ...     viewport={'width': 100, 'height': 200},
        ...     unit_converter=unit_converter,
        ...     transform_parser=transform_parser,
        ...     color_parser=color_parser
        ... )
        >>> property_value = context.get_property('opacity', '1.0')
    """
    element: etree.Element
    viewport: Dict[str, Any]
    unit_converter: Any
    transform_parser: Any
    color_parser: Any
    properties: Optional[Dict[str, Any]] = None
    cache: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Initialize context after dataclass creation."""
        # Validate required dependencies
        if self.element is None:
            raise FilterValidationError("FilterContext requires a valid SVG element")

        if self.unit_converter is None:
            raise FilterValidationError("FilterContext requires a unit_converter")

        if self.transform_parser is None:
            raise FilterValidationError("FilterContext requires a transform_parser")

        if self.color_parser is None:
            raise FilterValidationError("FilterContext requires a color_parser")

        # Initialize optional attributes
        if self.properties is None:
            self.properties = {}

        if self.cache is None:
            self.cache = {}

    def get_property(self, key: str, default: Any = None) -> Any:
        """
        Get a property value from the element properties.

        Args:
            key: Property name to retrieve
            default: Default value if property doesn't exist

        Returns:
            Property value or default if not found
        """
        if not self.properties:
            return default
        return self.properties.get(key, default)


@dataclass
class FilterResult:
    """
    Result of applying a filter to an SVG element.

    This class encapsulates the output of filter processing, including
    the generated DrawingML, success/failure status, and metadata.

    Attributes:
        success: Whether the filter was applied successfully
        drawingml: Generated DrawingML XML string (if successful)
        error_message: Error description (if failed)
        metadata: Additional information about the processing

    Example:
        >>> result = FilterResult(
        ...     success=True,
        ...     drawingml='<a:blur r="50000"/>',
        ...     metadata={'filter_type': 'blur', 'processing_time': 0.123}
        ... )
        >>> if result.is_success():
        ...     xml = result.get_drawingml()
    """
    success: bool
    drawingml: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Validate FilterResult after creation."""
        if self.success:
            # Allow empty drawingml for valid cases (e.g., no-op filters, empty chains)
            if self.drawingml is None:
                self.drawingml = ""
        else:
            if not self.error_message:
                raise FilterValidationError(
                    "Failed FilterResult must have non-empty error_message"
                )

    def is_success(self) -> bool:
        """Check if the filter was applied successfully."""
        return self.success

    def get_drawingml(self) -> Optional[str]:
        """Get the generated DrawingML XML string."""
        return self.drawingml if self.success else None

    def get_error_message(self) -> Optional[str]:
        """Get the error message if processing failed."""
        return self.error_message if not self.success else None

    def get_metadata(self) -> Dict[str, Any]:
        """Get processing metadata."""
        return self.metadata or {}


class Filter(ABC):
    """
    Abstract base class for all SVG filter implementations.

    This class defines the interface that all filter implementations must
    follow, providing a consistent API for filter processing and ensuring
    proper integration with the filter pipeline.

    All concrete filter classes must inherit from this base class and
    implement the abstract methods: can_apply, apply, and validate_parameters.

    Attributes:
        filter_type: String identifier for the filter type

    Example:
        >>> class BlurFilter(Filter):
        ...     def can_apply(self, element, context):
        ...         return element.tag.endswith('blur')
        ...
        ...     def apply(self, element, context):
        ...         # Process blur filter
        ...         return FilterResult(success=True, drawingml='<a:blur r="50000"/>')
        ...
        ...     def validate_parameters(self, element, context):
        ...         return True
    """

    def __init__(self, filter_type: str):
        """
        Initialize the filter with its type identifier.

        Args:
            filter_type: String identifier for this filter type
        """
        self.filter_type = filter_type
        self.logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")

    @abstractmethod
    def can_apply(self, element: etree.Element, context: FilterContext) -> bool:
        """
        Check if this filter can be applied to the given element.

        This method allows filters to declare whether they are capable
        of processing a specific SVG element based on its tag, attributes,
        or other characteristics.

        Args:
            element: SVG element to check
            context: Filter processing context

        Returns:
            True if this filter can process the element, False otherwise
        """
        pass

    @abstractmethod
    def apply(self, element: etree.Element, context: FilterContext) -> FilterResult:
        """
        Apply this filter to the given SVG element.

        This is the main processing method where the filter performs its
        transformation on the SVG element and generates the corresponding
        DrawingML output.

        Args:
            element: SVG element to process
            context: Filter processing context with shared state and utilities

        Returns:
            FilterResult containing the processing outcome

        Raises:
            FilterException: If processing fails due to filter-specific issues
        """
        pass

    @abstractmethod
    def validate_parameters(self, element: etree.Element, context: FilterContext) -> bool:
        """
        Validate that the element has the required parameters for this filter.

        This method checks that the SVG element contains all necessary
        attributes and values required for successful filter processing.

        Args:
            element: SVG element to validate
            context: Filter processing context

        Returns:
            True if element parameters are valid, False otherwise
        """
        pass

    def get_filter_type(self) -> str:
        """Get the filter type identifier."""
        return self.filter_type

    def __str__(self) -> str:
        """String representation of the filter."""
        return f"{self.__class__.__name__}(type='{self.filter_type}')"

    def __repr__(self) -> str:
        """Detailed string representation of the filter."""
        return (
            f"{self.__class__.__name__}("
            f"filter_type='{self.filter_type}', "
            f"module='{self.__class__.__module__}')"
        )