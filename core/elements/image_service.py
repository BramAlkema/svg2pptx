#!/usr/bin/env python3
"""
Image Processor Service

High-level service that orchestrates image processing with preprocessing
integration and compatibility with the existing converter system.

Features:
- Integration with existing ImageConverter
- Preprocessing-aware image processing
- Performance optimization
- PowerPoint embedding optimization
"""

import logging
from typing import Dict, List, Optional, Any, Union
from lxml import etree as ET

from .image_processor import ImageProcessor, ImageAnalysis, ImageOptimization
from ..services.conversion_services import ConversionServices

logger = logging.getLogger(__name__)


class ImageProcessorService:
    """
    High-level service for orchestrating image processing.

    Integrates with the preprocessing pipeline and existing converter
    system to provide optimized image conversion.
    """

    def __init__(self, services: ConversionServices, image_processor: ImageProcessor):
        """
        Initialize image processor service.

        Args:
            services: ConversionServices container
            image_processor: Core image processor
        """
        self.services = services
        self.image_processor = image_processor
        self.logger = logging.getLogger(__name__)

        # Service statistics
        self.stats = {
            'elements_processed': 0,
            'optimizations_applied': 0,
            'preprocessing_applied': 0,
            'fallbacks_used': 0
        }

    def process_image_element(self, element: ET.Element, context: Any,
                            apply_optimizations: bool = True) -> Dict[str, Any]:
        """
        Process an image element with full analysis and optimization.

        Args:
            element: Image element to process
            context: Conversion context
            apply_optimizations: Whether to apply optimizations

        Returns:
            Processing result with image data and metadata
        """
        self.stats['elements_processed'] += 1

        try:
            # Analyze image element
            analysis = self.image_processor.analyze_image_element(element, context)

            # Apply preprocessing if needed
            processed_element = element
            if analysis.requires_preprocessing:
                processed_element = self._apply_preprocessing(element, analysis, context)
                self.stats['preprocessing_applied'] += 1

            # Apply optimizations if requested
            if apply_optimizations and analysis.optimization_opportunities:
                processed_element = self.image_processor.apply_image_optimizations(
                    processed_element, analysis, context
                )
                self.stats['optimizations_applied'] += 1

            # Convert to PowerPoint format
            conversion_result = self._convert_to_powerpoint(processed_element, analysis, context)

            return {
                'success': True,
                'element': processed_element,
                'analysis': analysis,
                'conversion_result': conversion_result,
                'preprocessing_applied': analysis.requires_preprocessing,
                'optimizations_applied': len(analysis.optimization_opportunities) if apply_optimizations else 0,
                'performance_impact': analysis.estimated_performance_impact
            }

        except Exception as e:
            self.logger.error(f"Image processing failed: {e}")
            self.stats['fallbacks_used'] += 1
            return self._create_fallback_result(element, str(e))

    def _apply_preprocessing(self, element: ET.Element, analysis: ImageAnalysis,
                           context: Any) -> ET.Element:
        """Apply preprocessing optimizations to image element."""
        processed_element = self.image_processor._copy_element(element)

        # Apply transform flattening if present
        if processed_element.get('transform'):
            processed_element = self._flatten_image_transform(processed_element, context)

        # Normalize coordinate system
        processed_element = self._normalize_image_coordinates(processed_element, analysis, context)

        # Prepare for clipping if needed
        if processed_element.get('clip-path'):
            processed_element = self._prepare_image_clipping(processed_element, context)

        # Add preprocessing metadata
        processed_element.set('data-preprocessing-applied', 'image')
        processed_element.set('data-original-format', analysis.format.value)

        return processed_element

    def _flatten_image_transform(self, element: ET.Element, context: Any) -> ET.Element:
        """Flatten transform matrix into image positioning."""
        transform_str = element.get('transform', '')
        if not transform_str:
            return element

        try:
            # Parse transform matrix (simplified implementation)
            if 'translate(' in transform_str:
                # Extract translation values
                import re
                match = re.search(r'translate\(\s*([\d.-]+)(?:\s*[,\s]\s*([\d.-]+))?\s*\)', transform_str)
                if match:
                    tx = float(match.group(1))
                    ty = float(match.group(2)) if match.group(2) else 0

                    # Apply translation to x,y attributes
                    current_x = float(element.get('x', '0'))
                    current_y = float(element.get('y', '0'))

                    element.set('x', str(current_x + tx))
                    element.set('y', str(current_y + ty))

                    # Remove transform attribute
                    if 'transform' in element.attrib:
                        del element.attrib['transform']

                    element.set('data-transform-flattened', 'translate')

        except Exception as e:
            self.logger.warning(f"Transform flattening failed: {e}")

        return element

    def _normalize_image_coordinates(self, element: ET.Element, analysis: ImageAnalysis,
                                   context: Any) -> ET.Element:
        """Normalize image coordinates to slide coordinate system."""
        # Get viewport information from context
        viewport_width = getattr(context, 'viewport_width', 1920)
        viewport_height = getattr(context, 'viewport_height', 1080)

        # Normalize position if specified as percentages
        x_str = element.get('x', '0')
        y_str = element.get('y', '0')

        if x_str.endswith('%'):
            x_percent = float(x_str[:-1]) / 100
            element.set('x', str(x_percent * viewport_width))
            element.set('data-x-normalized', 'true')

        if y_str.endswith('%'):
            y_percent = float(y_str[:-1]) / 100
            element.set('y', str(y_percent * viewport_height))
            element.set('data-y-normalized', 'true')

        return element

    def _prepare_image_clipping(self, element: ET.Element, context: Any) -> ET.Element:
        """Prepare image for clipping operations."""
        clip_path_ref = element.get('clip-path', '')
        if clip_path_ref:
            # Add clipping metadata for downstream processing
            element.set('data-requires-clipping', 'true')
            element.set('data-clip-ref', clip_path_ref)

            # Mark for special handling in PowerPoint
            element.set('data-powerpoint-clipping', 'crop-to-shape')

        return element

    def _convert_to_powerpoint(self, element: ET.Element, analysis: ImageAnalysis,
                             context: Any) -> Dict[str, Any]:
        """Convert image to PowerPoint format using existing converter."""
        try:
            # Get existing image converter from services
            if hasattr(self.services, 'converter_registry'):
                image_converter = self.services.converter_registry.get_converter('image')
                if image_converter:
                    # Use existing converter
                    return image_converter.convert(element, context)

            # Fallback: create basic conversion result
            return self._create_basic_conversion_result(element, analysis)

        except Exception as e:
            self.logger.warning(f"PowerPoint conversion failed: {e}")
            return self._create_basic_conversion_result(element, analysis)

    def _create_basic_conversion_result(self, element: ET.Element,
                                      analysis: ImageAnalysis) -> Dict[str, Any]:
        """Create basic conversion result for fallback."""
        return {
            'type': 'image',
            'href': analysis.href,
            'width': analysis.dimensions.width,
            'height': analysis.dimensions.height,
            'format': analysis.format.value,
            'embedded': analysis.is_embedded,
            'optimized': element.get('data-image-optimized') == 'true'
        }

    def _create_fallback_result(self, element: ET.Element, error_msg: str) -> Dict[str, Any]:
        """Create fallback result for failed processing."""
        return {
            'success': False,
            'element': element,
            'analysis': None,
            'conversion_result': None,
            'error': error_msg,
            'fallback_used': True
        }

    def get_optimization_recommendations(self, element: ET.Element,
                                       context: Any) -> List[str]:
        """Get optimization recommendations for an image element."""
        try:
            analysis = self.image_processor.analyze_image_element(element, context)

            recommendations = []

            for optimization in analysis.optimization_opportunities:
                if optimization == ImageOptimization.RESIZE:
                    recommendations.append(
                        f"Resize image from {analysis.dimensions.width}x{analysis.dimensions.height} "
                        f"to improve performance"
                    )
                elif optimization == ImageOptimization.EMBED_INLINE:
                    recommendations.append("Embed external image inline for better performance")
                elif optimization == ImageOptimization.CONVERT_FORMAT:
                    recommendations.append(
                        f"Convert {analysis.format.value} to raster format for PowerPoint compatibility"
                    )
                elif optimization == ImageOptimization.COMPRESS:
                    recommendations.append("Compress image to reduce file size")

            if not analysis.powerpoint_compatible:
                recommendations.append("Image format may not be fully compatible with PowerPoint")

            if analysis.estimated_performance_impact in ['high', 'very_high']:
                recommendations.append("Large image may impact presentation performance")

            return recommendations

        except Exception as e:
            self.logger.error(f"Failed to get recommendations: {e}")
            return ["Unable to analyze image for optimization recommendations"]

    def batch_process_images(self, elements: List[ET.Element], context: Any,
                           apply_optimizations: bool = True) -> Dict[str, Any]:
        """Process multiple image elements in batch."""
        results = []
        total_optimizations = 0
        total_preprocessing = 0

        for element in elements:
            try:
                result = self.process_image_element(element, context, apply_optimizations)
                results.append(result)

                if result.get('success'):
                    total_optimizations += result.get('optimizations_applied', 0)
                    if result.get('preprocessing_applied'):
                        total_preprocessing += 1

            except Exception as e:
                self.logger.error(f"Batch processing failed for element: {e}")
                results.append(self._create_fallback_result(element, str(e)))

        return {
            'total_processed': len(elements),
            'successful': sum(1 for r in results if r.get('success')),
            'failed': sum(1 for r in results if not r.get('success')),
            'total_optimizations': total_optimizations,
            'total_preprocessing': total_preprocessing,
            'results': results
        }

    def get_service_statistics(self) -> Dict[str, Any]:
        """Get comprehensive service statistics."""
        processor_stats = self.image_processor.get_processing_statistics()
        service_stats = self.stats.copy()

        return {
            'service_stats': service_stats,
            'processor_stats': processor_stats,
            'cache_efficiency': (
                processor_stats['cache_hits'] / max(processor_stats['images_processed'], 1)
            ) * 100
        }

    def reset_statistics(self) -> None:
        """Reset all statistics."""
        self.stats = {
            'elements_processed': 0,
            'optimizations_applied': 0,
            'preprocessing_applied': 0,
            'fallbacks_used': 0
        }
        self.image_processor.reset_statistics()


def create_image_processor_service(services: ConversionServices) -> ImageProcessorService:
    """
    Create an image processor service with dependencies.

    Args:
        services: ConversionServices container

    Returns:
        Configured ImageProcessorService
    """
    image_processor = ImageProcessor(services)
    return ImageProcessorService(services, image_processor)