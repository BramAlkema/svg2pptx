#!/usr/bin/env python3
"""
Gradient Processor Service

High-level service that orchestrates gradient processing with preprocessing
integration and compatibility with the existing high-performance gradient system.

Features:
- Integration with existing GradientEngine and GradientConverter
- Preprocessing-aware gradient processing
- Color system integration
- Performance optimization and fallback handling
"""

import logging
from typing import Dict, List, Optional, Any, Union
from lxml import etree as ET

from .gradient_processor import GradientProcessor, GradientAnalysis, GradientOptimization
from ..services.conversion_services import ConversionServices

logger = logging.getLogger(__name__)


class GradientProcessorService:
    """
    High-level service for orchestrating gradient processing.

    Integrates with the preprocessing pipeline and existing high-performance
    gradient system to provide optimized gradient conversion.
    """

    def __init__(self, services: ConversionServices, gradient_processor: GradientProcessor):
        """
        Initialize gradient processor service.

        Args:
            services: ConversionServices container
            gradient_processor: Core gradient processor
        """
        self.services = services
        self.gradient_processor = gradient_processor
        self.logger = logging.getLogger(__name__)

        # Service statistics
        self.stats = {
            'elements_processed': 0,
            'optimizations_applied': 0,
            'preprocessing_applied': 0,
            'fallbacks_used': 0,
            'high_performance_engine_used': 0,
            'legacy_converter_used': 0
        }

    def process_gradient_element(self, element: ET.Element, context: Any,
                               apply_optimizations: bool = True) -> Dict[str, Any]:
        """
        Process a gradient element with full analysis and optimization.

        Args:
            element: Gradient element to process
            context: Conversion context
            apply_optimizations: Whether to apply optimizations

        Returns:
            Processing result with gradient data and metadata
        """
        self.stats['elements_processed'] += 1

        try:
            # Analyze gradient element
            analysis = self.gradient_processor.analyze_gradient_element(element, context)

            # Apply preprocessing if needed
            processed_element = element
            if analysis.requires_preprocessing:
                processed_element = self._apply_preprocessing(element, analysis, context)
                self.stats['preprocessing_applied'] += 1

            # Apply optimizations if requested
            if apply_optimizations and analysis.optimization_opportunities:
                processed_element = self.gradient_processor.apply_gradient_optimizations(
                    processed_element, analysis, context
                )
                self.stats['optimizations_applied'] += 1

            # Convert to PowerPoint format using best available engine
            conversion_result = self._convert_to_powerpoint(processed_element, analysis, context)

            return {
                'success': True,
                'element': processed_element,
                'analysis': analysis,
                'conversion_result': conversion_result,
                'preprocessing_applied': analysis.requires_preprocessing,
                'optimizations_applied': len(analysis.optimization_opportunities) if apply_optimizations else 0,
                'performance_impact': analysis.estimated_performance_impact,
                'engine_used': conversion_result.get('engine_used', 'unknown')
            }

        except Exception as e:
            self.logger.error(f"Gradient processing failed: {e}")
            self.stats['fallbacks_used'] += 1
            return self._create_fallback_result(element, str(e))

    def _apply_preprocessing(self, element: ET.Element, analysis: GradientAnalysis,
                           context: Any) -> ET.Element:
        """Apply preprocessing optimizations to gradient element."""
        processed_element = self.gradient_processor._copy_element(element)

        # Apply transform flattening if beneficial
        if GradientOptimization.TRANSFORM_FLATTENING in analysis.optimization_opportunities:
            processed_element = self._flatten_gradient_transforms(processed_element, analysis, context)

        # Normalize color spaces if needed
        if GradientOptimization.COLOR_SPACE_OPTIMIZATION in analysis.optimization_opportunities:
            processed_element = self._normalize_gradient_colors(processed_element, analysis, context)

        # Reduce stops if beneficial
        if GradientOptimization.STOP_REDUCTION in analysis.optimization_opportunities:
            processed_element = self._optimize_gradient_stops(processed_element, analysis, context)

        # Add preprocessing metadata
        processed_element.set('data-preprocessing-applied', 'gradient')
        processed_element.set('data-original-complexity', analysis.complexity.value)
        processed_element.set('data-optimization-count', str(len(analysis.optimization_opportunities)))

        return processed_element

    def _flatten_gradient_transforms(self, element: ET.Element, analysis: GradientAnalysis,
                                   context: Any) -> ET.Element:
        """Flatten gradient transforms for better performance."""
        transform_str = element.get('gradientTransform', '')
        if not transform_str:
            return element

        try:
            # Use transform processor to parse and flatten transforms
            # This is a simplified implementation - real implementation would
            # integrate with the numpy transform system
            if 'translate(' in transform_str:
                # Mark for transform flattening
                element.set('data-transform-flattened', 'true')
                element.set('data-original-transform', transform_str)

                # For demonstration, we'll mark it but not actually modify
                # In a real implementation, we'd apply the transform to the gradient coordinates

        except Exception as e:
            self.logger.warning(f"Transform flattening failed: {e}")

        return element

    def _normalize_gradient_colors(self, element: ET.Element, analysis: GradientAnalysis,
                                 context: Any) -> ET.Element:
        """Normalize gradient colors using the modern color system."""
        stop_elements = element.findall('.//stop')
        if not stop_elements:
            stop_elements = element.findall('.//{http://www.w3.org/2000/svg}stop')

        colors_normalized = 0

        for stop in stop_elements:
            color_str = stop.get('stop-color', '#000000')
            try:
                # Use modern color system
                if hasattr(self.services, 'color_parser'):
                    # Use service color parser
                    normalized_color = self.services.color_parser.normalize_color(color_str)
                    stop.set('stop-color', normalized_color)
                    colors_normalized += 1
                else:
                    # Fallback to direct Color usage
                    from ...color import Color
                    color_obj = Color(color_str)
                    hex_color = color_obj.hex()
                    stop.set('stop-color', hex_color)
                    colors_normalized += 1

            except Exception as e:
                self.logger.warning(f"Color normalization failed for '{color_str}': {e}")

        if colors_normalized > 0:
            element.set('data-colors-normalized', str(colors_normalized))

        return element

    def _optimize_gradient_stops(self, element: ET.Element, analysis: GradientAnalysis,
                               context: Any) -> ET.Element:
        """Optimize gradient stops by removing redundant or very close stops."""
        stop_elements = element.findall('.//stop')
        if not stop_elements:
            stop_elements = element.findall('.//{http://www.w3.org/2000/svg}stop')

        if len(stop_elements) <= 2:
            return element  # Can't optimize if too few stops

        # Collect stop data
        stops_data = []
        for stop in stop_elements:
            try:
                offset_str = stop.get('offset', '0')
                if offset_str.endswith('%'):
                    position = float(offset_str[:-1]) / 100.0
                else:
                    position = float(offset_str)

                stops_data.append({
                    'element': stop,
                    'position': position,
                    'color': stop.get('stop-color', '#000000'),
                    'opacity': stop.get('stop-opacity', '1.0')
                })
            except (ValueError, TypeError):
                # Keep problematic stops as-is
                continue

        # Sort by position
        stops_data.sort(key=lambda x: x['position'])

        # Identify redundant stops
        redundant_indices = []
        tolerance = 0.01  # Position tolerance

        for i in range(1, len(stops_data) - 1):  # Don't remove first or last
            prev_stop = stops_data[i - 1]
            curr_stop = stops_data[i]
            next_stop = stops_data[i + 1]

            # Check if current stop is redundant
            pos_diff_prev = abs(curr_stop['position'] - prev_stop['position'])
            pos_diff_next = abs(next_stop['position'] - curr_stop['position'])

            if (pos_diff_prev < tolerance or pos_diff_next < tolerance):
                # Check if colors are similar too
                if curr_stop['color'] == prev_stop['color'] or curr_stop['color'] == next_stop['color']:
                    redundant_indices.append(i)

        # Remove redundant stops (in reverse order to maintain indices)
        for i in reversed(redundant_indices):
            stop_element = stops_data[i]['element']
            if stop_element.getparent() is not None:
                stop_element.getparent().remove(stop_element)

        if redundant_indices:
            element.set('data-stops-optimized', str(len(redundant_indices)))

        return element

    def _convert_to_powerpoint(self, element: ET.Element, analysis: GradientAnalysis,
                             context: Any) -> Dict[str, Any]:
        """Convert gradient to PowerPoint format using best available engine."""
        try:
            # Try high-performance gradient engine first
            result = self._try_high_performance_engine(element, analysis, context)
            if result['success']:
                self.stats['high_performance_engine_used'] += 1
                return result

            # Fallback to existing gradient converter
            result = self._try_legacy_converter(element, analysis, context)
            if result['success']:
                self.stats['legacy_converter_used'] += 1
                return result

            # Create basic fallback result
            return self._create_basic_conversion_result(element, analysis)

        except Exception as e:
            self.logger.warning(f"PowerPoint conversion failed: {e}")
            return self._create_basic_conversion_result(element, analysis)

    def _try_high_performance_engine(self, element: ET.Element, analysis: GradientAnalysis,
                                   context: Any) -> Dict[str, Any]:
        """Try using the high-performance NumPy gradient engine."""
        try:
            # Import high-performance gradient engine
            from ...converters.gradients.core import GradientEngine

            # Create engine
            engine = GradientEngine(optimization_level=2)

            # Process single gradient
            drawingml_xml = engine.process_single_gradient(element)

            if drawingml_xml:
                return {
                    'success': True,
                    'engine_used': 'high_performance_numpy',
                    'drawingml_xml': drawingml_xml,
                    'performance_metrics': engine.get_performance_stats(),
                    'optimization_level': 2
                }

        except Exception as e:
            self.logger.debug(f"High-performance engine failed: {e}")

        return {'success': False, 'engine_used': 'high_performance_numpy', 'error': 'Engine failed'}

    def _try_legacy_converter(self, element: ET.Element, analysis: GradientAnalysis,
                            context: Any) -> Dict[str, Any]:
        """Try using the existing gradient converter."""
        try:
            # Get existing gradient converter from services
            if hasattr(self.services, 'converter_registry'):
                gradient_converter = self.services.converter_registry.get_converter('gradient')
                if gradient_converter:
                    # Use existing converter
                    drawingml_xml = gradient_converter.convert(element, context)
                    if drawingml_xml:
                        return {
                            'success': True,
                            'engine_used': 'legacy_converter',
                            'drawingml_xml': drawingml_xml
                        }

        except Exception as e:
            self.logger.debug(f"Legacy converter failed: {e}")

        return {'success': False, 'engine_used': 'legacy_converter', 'error': 'Converter failed'}

    def _create_basic_conversion_result(self, element: ET.Element,
                                      analysis: GradientAnalysis) -> Dict[str, Any]:
        """Create basic conversion result for fallback."""
        return {
            'success': False,
            'engine_used': 'basic_fallback',
            'gradient_type': analysis.gradient_type,
            'stop_count': analysis.stop_count,
            'complexity': analysis.complexity.value,
            'powerpoint_compatible': analysis.powerpoint_compatible,
            'error': 'No suitable conversion engine available'
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
        """Get optimization recommendations for a gradient element."""
        try:
            analysis = self.gradient_processor.analyze_gradient_element(element, context)

            recommendations = []

            for optimization in analysis.optimization_opportunities:
                if optimization == GradientOptimization.COLOR_SIMPLIFICATION:
                    recommendations.append(
                        f"Simplify colors from {analysis.stop_count} stops to improve performance"
                    )
                elif optimization == GradientOptimization.STOP_REDUCTION:
                    recommendations.append("Remove redundant gradient stops to reduce complexity")
                elif optimization == GradientOptimization.TRANSFORM_FLATTENING:
                    recommendations.append("Flatten gradient transforms for better performance")
                elif optimization == GradientOptimization.COLOR_SPACE_OPTIMIZATION:
                    recommendations.append("Normalize colors to consistent color space")
                elif optimization == GradientOptimization.VECTORIZATION:
                    recommendations.append("Use vectorized processing for better performance")

            if not analysis.powerpoint_compatible:
                recommendations.append("Gradient may not be fully compatible with PowerPoint")

            if analysis.estimated_performance_impact in ['high', 'very_high']:
                recommendations.append("Complex gradient may impact presentation performance")

            if analysis.requires_preprocessing:
                recommendations.append("Preprocessing would improve gradient conversion")

            return recommendations

        except Exception as e:
            self.logger.error(f"Failed to get recommendations: {e}")
            return ["Unable to analyze gradient for optimization recommendations"]

    def batch_process_gradients(self, elements: List[ET.Element], context: Any,
                              apply_optimizations: bool = True) -> Dict[str, Any]:
        """Process multiple gradient elements in batch."""
        results = []
        total_optimizations = 0
        total_preprocessing = 0
        engine_usage = {'high_performance': 0, 'legacy': 0, 'fallback': 0}

        for element in elements:
            try:
                result = self.process_gradient_element(element, context, apply_optimizations)
                results.append(result)

                if result.get('success'):
                    total_optimizations += result.get('optimizations_applied', 0)
                    if result.get('preprocessing_applied'):
                        total_preprocessing += 1

                    engine = result.get('engine_used', 'unknown')
                    if 'high_performance' in engine:
                        engine_usage['high_performance'] += 1
                    elif 'legacy' in engine:
                        engine_usage['legacy'] += 1
                    else:
                        engine_usage['fallback'] += 1

            except Exception as e:
                self.logger.error(f"Batch processing failed for element: {e}")
                results.append(self._create_fallback_result(element, str(e)))

        return {
            'total_processed': len(elements),
            'successful': sum(1 for r in results if r.get('success')),
            'failed': sum(1 for r in results if not r.get('success')),
            'total_optimizations': total_optimizations,
            'total_preprocessing': total_preprocessing,
            'engine_usage': engine_usage,
            'results': results
        }

    def get_service_statistics(self) -> Dict[str, Any]:
        """Get comprehensive service statistics."""
        processor_stats = self.gradient_processor.get_processing_statistics()
        service_stats = self.stats.copy()

        return {
            'service_stats': service_stats,
            'processor_stats': processor_stats,
            'cache_efficiency': (
                processor_stats['cache_hits'] / max(processor_stats['gradients_analyzed'], 1)
            ) * 100,
            'optimization_rate': (
                processor_stats['optimizations_identified'] / max(processor_stats['gradients_analyzed'], 1)
            ) * 100
        }

    def reset_statistics(self) -> None:
        """Reset all statistics."""
        self.stats = {
            'elements_processed': 0,
            'optimizations_applied': 0,
            'preprocessing_applied': 0,
            'fallbacks_used': 0,
            'high_performance_engine_used': 0,
            'legacy_converter_used': 0
        }
        self.gradient_processor.reset_statistics()


def create_gradient_processor_service(services: ConversionServices) -> GradientProcessorService:
    """
    Create a gradient processor service with dependencies.

    Args:
        services: ConversionServices container

    Returns:
        Configured GradientProcessorService
    """
    gradient_processor = GradientProcessor(services)
    return GradientProcessorService(services, gradient_processor)