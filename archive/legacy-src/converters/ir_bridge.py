#!/usr/bin/env python3
"""
IR Converter Bridge

Bridge between existing converter system and clean slate IR architecture.
Provides seamless integration while maintaining backward compatibility.
"""

import logging
from typing import Dict, Any, Optional, List
from lxml import etree as ET

from .base import BaseConverter, ConversionContext
from ..services.conversion_services import ConversionServices
from ..config.hybrid_config import HybridConversionConfig

logger = logging.getLogger(__name__)


class IRConverterBridge(BaseConverter):
    """
    Bridge between existing converter system and clean slate IR.

    This converter acts as a proxy that routes SVG elements through
    the clean slate IR pipeline when enabled, falling back to
    existing converters when necessary.
    """

    supported_elements = ['*']  # Handles all elements through IR

    def __init__(self, services: ConversionServices, hybrid_config: HybridConversionConfig = None):
        """
        Initialize bridge converter with services and hybrid configuration.

        Args:
            services: ConversionServices instance (may include clean slate services)
            hybrid_config: Configuration for hybrid mode behavior

        Raises:
            ValueError: If required services are not available
        """
        super().__init__(services)

        self.hybrid_config = hybrid_config or HybridConversionConfig.create_existing_only()
        self.logger = logging.getLogger(__name__)

        # Validate clean slate services are available if needed
        if self._requires_clean_slate():
            self._validate_clean_slate_services()

        # Initialize statistics
        self._stats = {
            'total_elements': 0,
            'clean_slate_elements': 0,
            'existing_system_elements': 0,
            'conversion_failures': 0
        }

    def can_convert(self, element: ET.Element) -> bool:
        """
        Check if bridge can convert the element.

        Returns True if either clean slate is enabled for this element type
        or if there's a fallback converter available.

        Args:
            element: SVG element to check

        Returns:
            True if element can be converted via bridge
        """
        element_type = self.get_element_tag(element)

        # Check if clean slate should handle this element
        if self.hybrid_config.should_use_clean_slate_for_element(element_type):
            return self._has_clean_slate_support()

        # Check if existing system can handle it (fallback)
        return True  # Bridge always accepts as fallback

    def convert(self, element: ET.Element, context: ConversionContext) -> str:
        """
        Convert using clean slate IR pipeline or existing system.

        Args:
            element: SVG element to convert
            context: Conversion context with services and state

        Returns:
            DrawingML XML content

        Raises:
            ConversionError: If conversion fails on both paths
        """
        self._stats['total_elements'] += 1
        element_type = self.get_element_tag(element)

        try:
            # Check if we should use clean slate for this element
            if self._should_use_clean_slate(element, element_type):
                return self._convert_via_clean_slate(element, context)
            else:
                return self._convert_via_existing_system(element, context)

        except Exception as e:
            self._stats['conversion_failures'] += 1
            self.logger.error(f"Bridge conversion failed for {element_type}: {e}")

            # Try fallback if clean slate failed
            if self._should_use_clean_slate(element, element_type):
                self.logger.info(f"Attempting fallback to existing system for {element_type}")
                try:
                    return self._convert_via_existing_system(element, context)
                except Exception as fallback_error:
                    self.logger.error(f"Fallback conversion also failed: {fallback_error}")
                    raise
            else:
                raise

    def _should_use_clean_slate(self, element: ET.Element, element_type: str) -> bool:
        """
        Determine if clean slate should be used for this element.

        Args:
            element: SVG element
            element_type: Element tag name

        Returns:
            True if clean slate should be used
        """
        # Check configuration first
        if not self.hybrid_config.should_use_clean_slate_for_element(element_type):
            return False

        # Check if clean slate services are available
        if not self._has_clean_slate_support():
            return False

        # Apply policy-based decisions if policy engine is available
        if self.services.policy_engine:
            try:
                # Convert to IR for policy evaluation
                ir_element = self._svg_to_ir(element, None)
                policy_decision = self.services.policy_engine.decide(ir_element)

                # Log decision if enabled
                if self.hybrid_config.log_policy_decisions:
                    self.logger.debug(f"Policy decision for {element_type}: {policy_decision}")

                return policy_decision.use_clean_slate if hasattr(policy_decision, 'use_clean_slate') else True

            except Exception as e:
                self.logger.warning(f"Policy evaluation failed for {element_type}: {e}")
                return True  # Default to clean slate if configured

        return True

    def _convert_via_clean_slate(self, element: ET.Element, context: ConversionContext) -> str:
        """
        Convert element using clean slate IR pipeline.

        Args:
            element: SVG element to convert
            context: Conversion context

        Returns:
            DrawingML XML content

        Raises:
            Exception: If clean slate conversion fails
        """
        self._stats['clean_slate_elements'] += 1

        # 1. Convert SVG element to IR
        ir_element = self._svg_to_ir(element, context)

        # 2. Apply policy decision (if not already done)
        policy_decision = None
        if self.services.policy_engine:
            policy_decision = self.services.policy_engine.decide(ir_element)

        # 3. Map to DrawingML using appropriate mapper
        mapper = self._get_mapper_for_ir_element(ir_element)
        if not mapper:
            raise ValueError(f"No mapper available for IR element: {type(ir_element)}")

        mapper_result = mapper.map(ir_element, policy_decision)

        # 4. Return XML content
        return mapper_result.xml_content

    def _convert_via_existing_system(self, element: ET.Element, context: ConversionContext) -> str:
        """
        Convert element using existing converter system.

        Args:
            element: SVG element to convert
            context: Conversion context

        Returns:
            DrawingML XML content

        Raises:
            Exception: If existing system conversion fails
        """
        self._stats['existing_system_elements'] += 1

        # Use the converter registry to find appropriate converter
        from .base import ConverterRegistry

        # Get or create registry from context/services
        registry = getattr(context, 'converter_registry', None)
        if not registry:
            # Create minimal registry with basic converters
            registry = ConverterRegistry()
            # Registry will auto-discover converters from the system

        # Get converter for this element
        converter = registry.get_converter(self.get_element_tag(element))
        if not converter:
            # Fallback to base converter behavior
            return super().convert(element, context)

        # Convert using existing system
        return converter.convert(element, context)

    def _svg_to_ir(self, element: ET.Element, context: Optional[ConversionContext]):
        """
        Convert SVG element to IR representation.

        Args:
            element: SVG element
            context: Optional conversion context

        Returns:
            IRElement representation

        Raises:
            Exception: If IR conversion fails
        """
        if not self.services.ir_scene_factory:
            raise ValueError("IR Scene Factory not available")

        tag = self.get_element_tag(element)

        # Delegate to scene factory for IR creation
        if tag == 'path':
            return self._create_ir_path(element, context)
        elif tag == 'text':
            return self._create_ir_textframe(element, context)
        elif tag == 'g':
            return self._create_ir_group(element, context)
        elif tag == 'image':
            return self._create_ir_image(element, context)
        else:
            # Handle other shapes by converting to path
            return self._create_ir_path_from_shape(element, context)

    def _create_ir_path(self, element: ET.Element, context: Optional[ConversionContext]):
        """Create IR Path element from SVG path"""
        try:
            from core.ir import Path

            # Extract path data
            path_data = element.get('d', '')
            if not path_data:
                raise ValueError("Path element missing 'd' attribute")

            # Extract styling information
            fill = self._extract_fill_info(element)
            stroke = self._extract_stroke_info(element)
            transform = self._extract_transform_info(element)

            return Path(
                data=path_data,
                fill=fill,
                stroke=stroke,
                transform=transform
            )
        except ImportError:
            raise ValueError("Clean slate IR components not available")

    def _create_ir_textframe(self, element: ET.Element, context: Optional[ConversionContext]):
        """Create IR TextFrame element from SVG text"""
        try:
            from core.ir import TextFrame

            # Extract text content and styling
            text_content = self._extract_text_content(element)
            font_family = element.get('font-family', 'Arial')
            font_size = float(element.get('font-size', '12'))

            # Extract positioning
            x = float(element.get('x', '0'))
            y = float(element.get('y', '0'))

            return TextFrame(
                content=text_content,
                x=x,
                y=y,
                font_family=font_family,
                font_size_pt=font_size
            )
        except ImportError:
            raise ValueError("Clean slate IR components not available")

    def _create_ir_group(self, element: ET.Element, context: Optional[ConversionContext]):
        """Create IR Group element from SVG group"""
        try:
            from core.ir import Group

            # Extract group properties
            transform = self._extract_transform_info(element)

            # For now, create empty group (children would be processed separately)
            return Group(
                children=[],  # Children processed by parent converter
                transform=transform
            )
        except ImportError:
            raise ValueError("Clean slate IR components not available")

    def _create_ir_image(self, element: ET.Element, context: Optional[ConversionContext]):
        """Create IR Image element from SVG image"""
        try:
            from core.ir import Image

            # Extract image properties
            href = element.get('href') or element.get('{http://www.w3.org/1999/xlink}href', '')
            x = float(element.get('x', '0'))
            y = float(element.get('y', '0'))
            width = float(element.get('width', '100'))
            height = float(element.get('height', '100'))

            return Image(
                href=href,
                x=x,
                y=y,
                width=width,
                height=height
            )
        except ImportError:
            raise ValueError("Clean slate IR components not available")

    def _create_ir_path_from_shape(self, element: ET.Element, context: Optional[ConversionContext]):
        """Convert other SVG shapes to IR Path"""
        # Use existing shape-to-path conversion logic
        tag = self.get_element_tag(element)

        if tag == 'rect':
            path_data = self._rect_to_path_data(element)
        elif tag == 'circle':
            path_data = self._circle_to_path_data(element)
        elif tag == 'ellipse':
            path_data = self._ellipse_to_path_data(element)
        elif tag == 'line':
            path_data = self._line_to_path_data(element)
        elif tag == 'polygon':
            path_data = self._polygon_to_path_data(element)
        elif tag == 'polyline':
            path_data = self._polyline_to_path_data(element)
        else:
            raise ValueError(f"Unsupported shape type for path conversion: {tag}")

        # Create IR Path with converted data
        return self._create_ir_path_with_data(element, path_data, context)

    def _get_mapper_for_ir_element(self, ir_element):
        """Get appropriate mapper for IR element type"""
        if not self.services.mapper_registry:
            raise ValueError("Mapper registry not available")

        element_type = type(ir_element).__name__.lower()
        return self.services.mapper_registry.get_mapper(element_type)

    def _requires_clean_slate(self) -> bool:
        """Check if configuration requires clean slate services"""
        return (self.hybrid_config.conversion_mode != self.hybrid_config.ConversionMode.EXISTING_ONLY and
                len(self.hybrid_config.clean_slate_elements) > 0)

    def _has_clean_slate_support(self) -> bool:
        """Check if clean slate services are available"""
        return all([
            self.services.ir_scene_factory is not None,
            self.services.policy_engine is not None,
            self.services.mapper_registry is not None,
            self.services.drawingml_embedder is not None
        ])

    def _validate_clean_slate_services(self) -> None:
        """Validate that required clean slate services are available"""
        missing_services = []

        if self.services.ir_scene_factory is None:
            missing_services.append("ir_scene_factory")
        if self.services.policy_engine is None:
            missing_services.append("policy_engine")
        if self.services.mapper_registry is None:
            missing_services.append("mapper_registry")
        if self.services.drawingml_embedder is None:
            missing_services.append("drawingml_embedder")

        if missing_services:
            raise ValueError(f"Missing required clean slate services: {missing_services}")

    # Helper methods for shape-to-path conversion
    def _rect_to_path_data(self, element: ET.Element) -> str:
        """Convert rectangle to path data"""
        x = float(element.get('x', '0'))
        y = float(element.get('y', '0'))
        width = float(element.get('width', '0'))
        height = float(element.get('height', '0'))

        return f"M {x} {y} L {x + width} {y} L {x + width} {y + height} L {x} {y + height} Z"

    def _circle_to_path_data(self, element: ET.Element) -> str:
        """Convert circle to path data"""
        cx = float(element.get('cx', '0'))
        cy = float(element.get('cy', '0'))
        r = float(element.get('r', '0'))

        # Create circle using two arcs
        return (f"M {cx - r} {cy} "
                f"A {r} {r} 0 0 1 {cx + r} {cy} "
                f"A {r} {r} 0 0 1 {cx - r} {cy} Z")

    def _line_to_path_data(self, element: ET.Element) -> str:
        """Convert line to path data"""
        x1 = float(element.get('x1', '0'))
        y1 = float(element.get('y1', '0'))
        x2 = float(element.get('x2', '0'))
        y2 = float(element.get('y2', '0'))

        return f"M {x1} {y1} L {x2} {y2}"

    # Helper methods for attribute extraction
    def _extract_fill_info(self, element: ET.Element) -> Optional[Dict[str, Any]]:
        """Extract fill information from element"""
        fill = element.get('fill')
        if fill and fill != 'none':
            return {'color': fill}
        return None

    def _extract_stroke_info(self, element: ET.Element) -> Optional[Dict[str, Any]]:
        """Extract stroke information from element"""
        stroke = element.get('stroke')
        if stroke and stroke != 'none':
            return {
                'color': stroke,
                'width': float(element.get('stroke-width', '1'))
            }
        return None

    def _extract_transform_info(self, element: ET.Element) -> Optional[str]:
        """Extract transform information from element"""
        return element.get('transform')

    def _extract_text_content(self, element: ET.Element) -> str:
        """Extract text content from text element"""
        # Handle both direct text and tspan children
        content = element.text or ''
        for child in element:
            if child.tag.endswith('tspan'):
                content += child.text or ''
        return content.strip()

    def get_statistics(self) -> Dict[str, Any]:
        """Get bridge conversion statistics"""
        total = max(self._stats['total_elements'], 1)
        return {
            **self._stats,
            'clean_slate_ratio': self._stats['clean_slate_elements'] / total,
            'existing_system_ratio': self._stats['existing_system_elements'] / total,
            'failure_rate': self._stats['conversion_failures'] / total,
            'hybrid_config': self.hybrid_config.to_dict()
        }

    def reset_statistics(self) -> None:
        """Reset bridge statistics"""
        self._stats = {
            'total_elements': 0,
            'clean_slate_elements': 0,
            'existing_system_elements': 0,
            'conversion_failures': 0
        }


def create_ir_bridge(services: ConversionServices,
                    hybrid_config: HybridConversionConfig = None) -> IRConverterBridge:
    """
    Factory function to create IR converter bridge.

    Args:
        services: ConversionServices instance
        hybrid_config: Optional hybrid configuration

    Returns:
        Configured IRConverterBridge instance
    """
    return IRConverterBridge(services, hybrid_config)