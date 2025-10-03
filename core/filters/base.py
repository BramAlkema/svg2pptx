#!/usr/bin/env python3
"""
FilterProcessor Base Classes for Clean Slate Architecture

Provides the foundation for all SVG filter implementations with policy
integration, template-based XML generation, and fallback strategies.

This module combines the best aspects of the archive filter system with
the clean slate architecture patterns for maximum effectiveness.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union, TYPE_CHECKING
from dataclasses import dataclass
from enum import Enum
import logging
from lxml import etree as ET

if TYPE_CHECKING:
    from ..policy.engine import Policy
    from ..policy.targets import PolicyDecision
    from ..services.conversion_services import ConversionServices

logger = logging.getLogger(__name__)


class FilterException(Exception):
    """Base exception class for filter-related errors."""
    pass


class FilterValidationError(FilterException, ValueError):
    """Exception raised when filter parameters or context are invalid."""
    pass


class FilterStrategy(Enum):
    """Rendering strategies for filter processing."""
    NATIVE = "native"  # Use PowerPoint native effects
    APPROXIMATION = "approximation"  # Approximate with simpler effects
    EMF_RASTERIZE = "emf_rasterize"  # Fallback to EMF rasterization


@dataclass
class FilterContext:
    """
    Context object containing shared state and dependencies for filter processing.

    Adapted from archive FilterContext but integrated with clean slate
    ConversionServices pattern for dependency injection.

    Attributes:
        element: The SVG element being processed
        viewport: Viewport dimensions and information
        services: ConversionServices container with all dependencies
        properties: Element properties and attributes
        cache: Cache for storing computed values during processing
    """
    element: ET.Element
    viewport: Dict[str, Any]
    services: 'ConversionServices'
    properties: Optional[Dict[str, Any]] = None
    cache: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Initialize context after dataclass creation."""
        # Validate required dependencies
        if self.element is None:
            raise FilterValidationError("FilterContext requires a valid SVG element")

        if self.services is None:
            raise FilterValidationError("FilterContext requires ConversionServices")

        # Validate viewport
        if not self.viewport or not isinstance(self.viewport, dict):
            raise FilterValidationError("FilterContext requires valid viewport dictionary")

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

    def get_element_attribute(self, key: str, default: Any = None) -> Any:
        """
        Get an attribute value from the SVG element.

        Args:
            key: Attribute name to retrieve
            default: Default value if attribute doesn't exist

        Returns:
            Attribute value or default if not found
        """
        return self.element.get(key, default)

    def get_viewport_dimension(self, key: str, default: float = 0.0) -> float:
        """
        Get a viewport dimension.

        Args:
            key: Dimension key ('width', 'height', etc.)
            default: Default value if not found

        Returns:
            Viewport dimension as float
        """
        return float(self.viewport.get(key, default))

    @property
    def unit_converter(self):
        """Access to unit converter from services."""
        return self.services.unit_converter

    @property
    def color_parser(self):
        """Access to color parser from services."""
        return self.services.color_parser

    @property
    def transform_parser(self):
        """Access to transform parser from services."""
        return self.services.transform_parser


@dataclass
class FilterResult:
    """
    Result of applying a filter to an SVG element.

    Enhanced from archive FilterResult with policy decision metadata
    and strategy information for the clean slate architecture.

    Attributes:
        success: Whether the filter was applied successfully
        drawingml: Generated DrawingML XML string (if successful)
        strategy: Rendering strategy used
        policy_decision: Policy decision that drove the strategy choice
        metadata: Additional information about the processing
        error_message: Error description (if failed)
    """
    success: bool
    drawingml: Optional[str] = None
    strategy: FilterStrategy = FilterStrategy.NATIVE
    policy_decision: Optional['PolicyDecision'] = None
    metadata: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

    def __post_init__(self):
        """Validate FilterResult after creation."""
        if self.success:
            # Allow empty drawingml for valid cases (e.g., no-op filters)
            if self.drawingml is None:
                self.drawingml = ""
        else:
            if not self.error_message:
                raise FilterValidationError(
                    "Failed FilterResult must have non-empty error_message"
                )

        # Initialize metadata if not provided
        if self.metadata is None:
            self.metadata = {}

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

    def get_strategy(self) -> FilterStrategy:
        """Get the rendering strategy used."""
        return self.strategy

    def requires_emf(self) -> bool:
        """Check if this result requires EMF rasterization."""
        return self.strategy == FilterStrategy.EMF_RASTERIZE

    def is_native_rendering(self) -> bool:
        """Check if this uses native PowerPoint rendering."""
        return self.strategy == FilterStrategy.NATIVE

    def get_quality_estimate(self) -> float:
        """Get estimated output quality (0.0 to 1.0)."""
        if self.policy_decision:
            return self.policy_decision.estimated_quality
        return 1.0 if self.is_native_rendering() else 0.7


class FilterProcessor(ABC):
    """
    Abstract base class for all SVG filter processors in clean slate architecture.

    This class combines the archive Filter interface with policy-driven
    decision making and template-based XML generation for consistent
    integration with the clean slate architecture.

    Key improvements over archive Filter:
    - Policy engine integration for fallback decisions
    - Clean slate ConversionServices dependency injection
    - Template-based XML generation support
    - Enhanced metadata and strategy reporting
    """

    def __init__(self, filter_type: str, policy: Optional['Policy'] = None):
        """
        Initialize the filter processor.

        Args:
            filter_type: String identifier for this filter type
            policy: Policy engine for decision making (optional)
        """
        self.filter_type = filter_type
        self.policy = policy
        self.logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")

    @abstractmethod
    def can_apply(self, element: ET.Element, context: FilterContext) -> bool:
        """
        Check if this filter can be applied to the given element.

        Args:
            element: SVG element to check
            context: Filter processing context

        Returns:
            True if this filter can process the element
        """
        pass

    @abstractmethod
    def apply(self, element: ET.Element, context: FilterContext) -> FilterResult:
        """
        Apply the filter to the given element.

        This is the main processing method that should implement the filter's
        core functionality, using policy decisions to choose appropriate
        rendering strategies.

        Args:
            element: SVG element to process
            context: Filter processing context

        Returns:
            FilterResult with generated DrawingML and metadata
        """
        pass

    def validate_parameters(self, element: ET.Element, context: FilterContext) -> bool:
        """
        Validate filter parameters and context.

        Default implementation performs basic validation. Override in
        subclasses for filter-specific validation logic.

        Args:
            element: SVG element to validate
            context: Filter processing context

        Returns:
            True if parameters are valid, False otherwise
        """
        try:
            # Basic validation
            if element is None:
                return False

            if context is None:
                return False

            # Check for required filter attributes
            if not self._has_required_attributes(element):
                return False

            return True

        except Exception as e:
            self.logger.warning(f"Parameter validation failed for {self.filter_type}: {e}")
            return False

    def _has_required_attributes(self, element: ET.Element) -> bool:
        """
        Check if element has required attributes for this filter.

        Default implementation always returns True. Override in subclasses
        to implement filter-specific attribute requirements.

        Args:
            element: SVG element to check

        Returns:
            True if required attributes are present
        """
        return True

    def _make_policy_decision(self, element: ET.Element, context: FilterContext,
                             complexity: float = 0.0, **kwargs) -> 'PolicyDecision':
        """
        Make a policy-based decision for filter rendering strategy.

        Args:
            element: SVG element being processed
            context: Filter processing context
            complexity: Complexity score (0.0 to 1.0)
            **kwargs: Additional parameters for policy decision

        Returns:
            PolicyDecision indicating recommended strategy
        """
        if self.policy is None:
            # Default policy: use native rendering
            from ..policy.targets import PolicyDecision, DecisionReason
            return PolicyDecision(
                use_native=True,
                reasons=[DecisionReason.SIMPLE_CONTENT],
                confidence=0.8,
                estimated_quality=0.9,
                estimated_performance=0.8
            )

        # Use policy engine for decision
        return self.policy.decide_filter_strategy(
            filter_type=self.filter_type,
            complexity=complexity,
            **kwargs
        )

    def _create_success_result(self, drawingml: str, strategy: FilterStrategy,
                              policy_decision: Optional['PolicyDecision'] = None,
                              **metadata) -> FilterResult:
        """
        Create a successful FilterResult.

        Args:
            drawingml: Generated DrawingML XML
            strategy: Rendering strategy used
            policy_decision: Policy decision that drove the choice
            **metadata: Additional metadata to include

        Returns:
            FilterResult indicating success
        """
        result_metadata = {
            'filter_type': self.filter_type,
            'processing_strategy': strategy.value,
            **metadata
        }

        return FilterResult(
            success=True,
            drawingml=drawingml,
            strategy=strategy,
            policy_decision=policy_decision,
            metadata=result_metadata
        )

    def _create_failure_result(self, error_message: str, **metadata) -> FilterResult:
        """
        Create a failed FilterResult.

        Args:
            error_message: Description of the failure
            **metadata: Additional metadata to include

        Returns:
            FilterResult indicating failure
        """
        result_metadata = {
            'filter_type': self.filter_type,
            'error': error_message,
            **metadata
        }

        return FilterResult(
            success=False,
            error_message=error_message,
            metadata=result_metadata
        )

    def _get_element_localname(self, element: ET.Element) -> str:
        """
        Get the local name of an element (without namespace).

        Args:
            element: SVG element

        Returns:
            Local name of the element
        """
        tag = element.tag
        if tag is None:
            return ""
        if tag.startswith("{"):
            return tag.split("}", 1)[1]
        return tag

    def __str__(self) -> str:
        """String representation of the filter processor."""
        return f"{self.__class__.__name__}(type={self.filter_type})"

    def __repr__(self) -> str:
        """Detailed string representation."""
        return f"{self.__class__.__name__}(filter_type='{self.filter_type}', policy={self.policy})"


def create_filter_context(element: ET.Element, services: 'ConversionServices',
                         viewport: Optional[Dict[str, Any]] = None) -> FilterContext:
    """
    Factory function to create FilterContext with proper defaults.

    Args:
        element: SVG element being processed
        services: ConversionServices container
        viewport: Viewport information (optional)

    Returns:
        FilterContext instance ready for processing
    """
    if viewport is None:
        viewport = {'width': 800.0, 'height': 600.0}

    return FilterContext(
        element=element,
        viewport=viewport,
        services=services
    )