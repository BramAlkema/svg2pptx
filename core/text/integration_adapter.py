#!/usr/bin/env python3
"""
Text Integration Adapter

Provides integration between the new text pipeline and the existing
text converter system, allowing for gradual migration and compatibility.

Features:
- Backward compatibility with existing TextConverter
- Progressive enhancement with preprocessing
- Service integration
"""

import logging
from typing import Optional, Any, Dict
from lxml import etree as ET

from .converter_service import TextConverterService
from ..services.conversion_services import ConversionServices

logger = logging.getLogger(__name__)


class TextIntegrationAdapter:
    """
    Adapter that integrates the new text pipeline with existing systems.

    Provides backward compatibility while enabling progressive enhancement
    with preprocessing and documented fixes.
    """

    def __init__(self, services: ConversionServices, enable_preprocessing: bool = True):
        """
        Initialize text integration adapter.

        Args:
            services: ConversionServices container
            enable_preprocessing: Whether to enable preprocessing pipeline
        """
        self.services = services
        self.enable_preprocessing = enable_preprocessing
        self.logger = logging.getLogger(__name__)

        # Initialize new text converter service
        self.text_service = TextConverterService(services)

        # Track usage for monitoring
        self.usage_stats = {
            'preprocessed_conversions': 0,
            'fallback_conversions': 0,
            'errors': 0
        }

    def convert_text_with_enhancement(self, element: ET.Element, context: Any,
                                    force_preprocessing: Optional[bool] = None) -> str:
        """
        Convert text element with optional preprocessing enhancement.

        Args:
            element: SVG text element
            context: Conversion context
            force_preprocessing: Override default preprocessing setting

        Returns:
            DrawingML XML string
        """
        use_preprocessing = (force_preprocessing if force_preprocessing is not None
                           else self.enable_preprocessing)

        try:
            # Use new text pipeline
            result = self.text_service.convert_text_element(
                element, context, apply_preprocessing=use_preprocessing
            )

            # Update stats
            if use_preprocessing:
                self.usage_stats['preprocessed_conversions'] += 1
            else:
                self.usage_stats['fallback_conversions'] += 1

            self.logger.debug(f"Text conversion successful (preprocessing={use_preprocessing})")
            return result

        except Exception as e:
            self.usage_stats['errors'] += 1
            self.logger.error(f"Enhanced text conversion failed: {e}")

            # Fallback to basic conversion
            return self._fallback_conversion(element, context)

    def _fallback_conversion(self, element: ET.Element, context: Any) -> str:
        """Fallback conversion without preprocessing."""
        try:
            # Use text service without preprocessing
            return self.text_service.convert_text_element(
                element, context, apply_preprocessing=False
            )
        except Exception as e:
            self.logger.error(f"Fallback conversion also failed: {e}")
            # Return minimal shape
            return self._create_minimal_text_shape(element, context)

    def _create_minimal_text_shape(self, element: ET.Element, context: Any) -> str:
        """Create minimal text shape when all else fails."""
        content = element.text or "Error"
        x = int(float(element.get('x', '0')) * 9525)
        y = int(float(element.get('y', '0')) * 9525)
        width = int(len(content) * 12 * 9525 * 0.6)
        height = int(12 * 9525 * 1.2)

        shape_id = getattr(context, 'next_shape_id', 1)
        if hasattr(context, 'get_next_shape_id'):
            shape_id = context.get_next_shape_id()

        escaped_content = (content.replace('&', '&amp;')
                          .replace('<', '&lt;')
                          .replace('>', '&gt;'))

        return f'''<p:sp>
    <p:nvSpPr>
        <p:cNvPr id="{shape_id}" name="Text {shape_id}"/>
        <p:cNvSpPr/>
        <p:nvPr/>
    </p:nvSpPr>
    <p:spPr>
        <a:xfrm>
            <a:off x="{x}" y="{y}"/>
            <a:ext cx="{width}" cy="{height}"/>
        </a:xfrm>
        <a:prstGeom prst="rect">
            <a:avLst/>
        </a:prstGeom>
    </p:spPr>
    <p:txBody>
        <a:bodyPr/>
        <a:lstStyle/>
        <a:p>
            <a:r>
                <a:rPr sz="1200">
                    <a:solidFill><a:srgbClr val="000000"/></a:solidFill>
                    <a:latin typeface="Arial"/>
                </a:rPr>
                <a:t>{escaped_content}</a:t>
            </a:r>
        </a:p>
    </p:txBody>
</p:sp>'''

    def get_usage_statistics(self) -> Dict[str, int]:
        """Get usage statistics for monitoring."""
        return self.usage_stats.copy()

    def reset_statistics(self) -> None:
        """Reset usage statistics."""
        self.usage_stats = {
            'preprocessed_conversions': 0,
            'fallback_conversions': 0,
            'errors': 0
        }

    def validate_text_element(self, element: ET.Element) -> Dict[str, Any]:
        """
        Validate text element and provide preprocessing recommendations.

        Args:
            element: SVG text element

        Returns:
            Validation report with recommendations
        """
        report = {
            'valid': True,
            'issues': [],
            'recommendations': [],
            'preprocessing_benefits': []
        }

        # Check for complex text anchor
        text_anchor = element.get('text-anchor')
        if text_anchor and text_anchor not in ['start', 'middle', 'end']:
            report['issues'].append(f"Invalid text-anchor: {text_anchor}")
            report['preprocessing_benefits'].append("Text anchor normalization")

        # Check for tspan elements
        tspan_elements = element.xpath("./svg:tspan", namespaces={'svg': 'http://www.w3.org/2000/svg'})
        if tspan_elements:
            report['preprocessing_benefits'].append("Multi-run text layout")

            # Check for positioned tspans
            positioned_tspans = [t for t in tspan_elements if t.get('x') or t.get('y')]
            if positioned_tspans:
                report['preprocessing_benefits'].append("Line break detection")

        # Check for complex positioning
        if (element.get('dx') or element.get('dy') or element.get('rotate')):
            report['preprocessing_benefits'].append("Complex positioning handling")

        # Check for font properties
        if (element.get('font-family') or element.get('font-size') or
            any('font-' in attr for attr in element.attrib)):
            report['preprocessing_benefits'].append("Font cascade resolution")

        # Check for coordinate system issues
        x = element.get('x', '0')
        y = element.get('y', '0')
        try:
            x_val = float(x)
            y_val = float(y)
            if abs(x_val) > 10000 or abs(y_val) > 10000:
                report['issues'].append("Extreme coordinates detected")
                report['preprocessing_benefits'].append("Coordinate system normalization")
        except ValueError:
            report['issues'].append("Invalid coordinate format")
            report['preprocessing_benefits'].append("Coordinate validation")

        # Overall validation
        if report['issues']:
            report['valid'] = False

        # Recommendations
        if report['preprocessing_benefits']:
            report['recommendations'].append("Enable preprocessing for enhanced text handling")

        if len(report['preprocessing_benefits']) >= 2:
            report['recommendations'].append("Text element will benefit significantly from preprocessing")

        return report


def create_text_integration_adapter(services: ConversionServices,
                                  enable_preprocessing: bool = True) -> TextIntegrationAdapter:
    """
    Create a text integration adapter.

    Args:
        services: ConversionServices container
        enable_preprocessing: Whether to enable preprocessing by default

    Returns:
        Configured TextIntegrationAdapter
    """
    return TextIntegrationAdapter(services, enable_preprocessing)


def patch_existing_text_converter(text_converter, services: ConversionServices,
                                enable_preprocessing: bool = True) -> None:
    """
    Patch an existing TextConverter to use the new pipeline.

    Args:
        text_converter: Existing TextConverter instance
        services: ConversionServices container
        enable_preprocessing: Whether to enable preprocessing
    """
    # Create adapter
    adapter = create_text_integration_adapter(services, enable_preprocessing)

    # Store original convert method
    original_convert = text_converter.convert

    def enhanced_convert(element: ET.Element, context: Any) -> str:
        """Enhanced convert method with preprocessing support."""
        try:
            # Try new pipeline first
            return adapter.convert_text_with_enhancement(element, context)
        except Exception as e:
            logger.debug(f"Enhanced conversion failed, falling back to original: {e}")
            # Fallback to original method
            return original_convert(element, context)

    # Replace convert method
    text_converter.convert = enhanced_convert
    text_converter._enhancement_adapter = adapter

    logger.info("Patched TextConverter with preprocessing enhancement")