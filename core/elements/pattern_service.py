#!/usr/bin/env python3
"""
Pattern Processor Service

High-level service that orchestrates pattern processing with preprocessing
integration and compatibility with the existing pattern service.

Features:
- Integration with existing PatternService
- Preprocessing-aware pattern processing
- PowerPoint preset detection and mapping
- EMF fallback optimization
- Performance optimization and caching
"""

import logging
from typing import Dict, List, Optional, Any, Union
from lxml import etree as ET

from .pattern_processor import PatternProcessor, PatternAnalysis, PatternOptimization, PatternType
from ..services.conversion_services import ConversionServices

logger = logging.getLogger(__name__)


class PatternProcessorService:
    """
    High-level service for orchestrating pattern processing.

    Integrates with the preprocessing pipeline and existing pattern
    service to provide optimized pattern conversion.
    """

    def __init__(self, services: ConversionServices, pattern_processor: PatternProcessor):
        """
        Initialize pattern processor service.

        Args:
            services: ConversionServices container
            pattern_processor: Core pattern processor
        """
        self.services = services
        self.pattern_processor = pattern_processor
        self.logger = logging.getLogger(__name__)

        # Service statistics
        self.stats = {
            'elements_processed': 0,
            'optimizations_applied': 0,
            'preprocessing_applied': 0,
            'preset_conversions': 0,
            'emf_fallbacks': 0,
            'pattern_service_used': 0
        }

    def process_pattern_element(self, element: ET.Element, context: Any,
                              apply_optimizations: bool = True) -> Dict[str, Any]:
        """
        Process a pattern element with full analysis and optimization.

        Args:
            element: Pattern element to process
            context: Conversion context
            apply_optimizations: Whether to apply optimizations

        Returns:
            Processing result with pattern data and metadata
        """
        self.stats['elements_processed'] += 1

        try:
            # Analyze pattern element
            analysis = self.pattern_processor.analyze_pattern_element(element, context)

            # Apply preprocessing if needed
            processed_element = element
            if analysis.requires_preprocessing:
                processed_element = self._apply_preprocessing(element, analysis, context)
                self.stats['preprocessing_applied'] += 1

            # Apply optimizations if requested
            if apply_optimizations and analysis.optimization_opportunities:
                processed_element = self._apply_optimizations(processed_element, analysis, context)
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
                'performance_impact': analysis.estimated_performance_impact,
                'conversion_method': conversion_result.get('method', 'unknown')
            }

        except Exception as e:
            self.logger.error(f"Pattern processing failed: {e}")
            return self._create_fallback_result(element, str(e))

    def _apply_preprocessing(self, element: ET.Element, analysis: PatternAnalysis,
                           context: Any) -> ET.Element:
        """Apply preprocessing optimizations to pattern element."""
        processed_element = self._copy_element(element)

        # Apply transform flattening if beneficial
        if PatternOptimization.TRANSFORM_FLATTENING in analysis.optimization_opportunities:
            processed_element = self._flatten_pattern_transforms(processed_element, analysis, context)

        # Apply color simplification if needed
        if PatternOptimization.COLOR_SIMPLIFICATION in analysis.optimization_opportunities:
            processed_element = self._simplify_pattern_colors(processed_element, analysis, context)

        # Apply tile optimization if beneficial
        if PatternOptimization.TILE_OPTIMIZATION in analysis.optimization_opportunities:
            processed_element = self._optimize_pattern_tile(processed_element, analysis, context)

        # Add preprocessing metadata
        processed_element.set('data-preprocessing-applied', 'pattern')
        processed_element.set('data-original-complexity', analysis.complexity.value)
        processed_element.set('data-pattern-type', analysis.pattern_type.value)

        return processed_element

    def _flatten_pattern_transforms(self, element: ET.Element, analysis: PatternAnalysis,
                                  context: Any) -> ET.Element:
        """Flatten pattern transforms for better performance."""
        transform_str = element.get('patternTransform', '')
        if not transform_str:
            return element

        try:
            # Mark for transform flattening
            element.set('data-transform-flattened', 'true')
            element.set('data-original-transform', transform_str)

            # Simplified transform flattening
            # In a real implementation, this would apply the transform to the pattern content
            if 'translate(' in transform_str:
                # Extract translation values and apply to pattern positioning
                import re
                match = re.search(r'translate\s*\(\s*([\d.-]+)(?:\s*,?\s*([\d.-]+))?\s*\)', transform_str)
                if match:
                    tx = float(match.group(1))
                    ty = float(match.group(2)) if match.group(2) else 0

                    # Apply translation to pattern geometry (simplified)
                    element.set('data-translate-x', str(tx))
                    element.set('data-translate-y', str(ty))

        except Exception as e:
            self.logger.warning(f"Transform flattening failed: {e}")

        return element

    def _simplify_pattern_colors(self, element: ET.Element, analysis: PatternAnalysis,
                               context: Any) -> ET.Element:
        """Simplify pattern colors to improve compatibility."""
        children = list(element)
        colors_normalized = 0

        for child in children:
            # Normalize fill colors
            fill_color = child.get('fill')
            if fill_color and fill_color not in ['none', 'transparent']:
                try:
                    # Use modern color system
                    if hasattr(self.services, 'color_parser'):
                        normalized_color = self.services.color_parser.normalize_color(fill_color)
                        child.set('fill', normalized_color)
                        colors_normalized += 1
                    else:
                        # Fallback to direct Color usage
                        from ...color import Color
                        color_obj = Color(fill_color)
                        hex_color = color_obj.hex()
                        child.set('fill', hex_color)
                        colors_normalized += 1

                except Exception as e:
                    self.logger.warning(f"Color normalization failed for '{fill_color}': {e}")

            # Normalize stroke colors
            stroke_color = child.get('stroke')
            if stroke_color and stroke_color not in ['none', 'transparent']:
                try:
                    if hasattr(self.services, 'color_parser'):
                        normalized_color = self.services.color_parser.normalize_color(stroke_color)
                        child.set('stroke', normalized_color)
                        colors_normalized += 1
                    else:
                        from ...color import Color
                        color_obj = Color(stroke_color)
                        hex_color = color_obj.hex()
                        child.set('stroke', hex_color)
                        colors_normalized += 1

                except Exception as e:
                    self.logger.warning(f"Color normalization failed for '{stroke_color}': {e}")

        if colors_normalized > 0:
            element.set('data-colors-simplified', str(colors_normalized))

        return element

    def _optimize_pattern_tile(self, element: ET.Element, analysis: PatternAnalysis,
                             context: Any) -> ET.Element:
        """Optimize pattern tile size for better performance."""
        # Check if tile is too large
        if analysis.geometry.tile_width > 100 or analysis.geometry.tile_height > 100:
            # Scale down large tiles
            scale_factor = min(100 / analysis.geometry.tile_width, 100 / analysis.geometry.tile_height)

            new_width = analysis.geometry.tile_width * scale_factor
            new_height = analysis.geometry.tile_height * scale_factor

            element.set('width', str(new_width))
            element.set('height', str(new_height))
            element.set('data-tile-optimized', 'true')
            element.set('data-scale-factor', str(scale_factor))

        return element

    def _apply_optimizations(self, element: ET.Element, analysis: PatternAnalysis,
                           context: Any) -> ET.Element:
        """Apply pattern-specific optimizations."""
        optimized_element = element

        # Apply preset mapping if possible
        if PatternOptimization.PRESET_MAPPING in analysis.optimization_opportunities:
            optimized_element.set('data-preset-candidate', analysis.preset_candidate or 'unknown')

        # Mark EMF optimization if recommended
        if PatternOptimization.EMF_OPTIMIZATION in analysis.optimization_opportunities:
            optimized_element.set('data-emf-optimized', 'true')

        # Mark as optimized
        optimized_element.set('data-pattern-optimized', 'true')

        return optimized_element

    def _convert_to_powerpoint(self, element: ET.Element, analysis: PatternAnalysis,
                             context: Any) -> Dict[str, Any]:
        """Convert pattern to PowerPoint format using best available method."""
        try:
            # Try preset mapping first if available
            if analysis.preset_candidate and analysis.powerpoint_compatible:
                result = self._try_preset_conversion(element, analysis, context)
                if result['success']:
                    self.stats['preset_conversions'] += 1
                    return result

            # Try existing pattern service
            result = self._try_pattern_service(element, analysis, context)
            if result['success']:
                self.stats['pattern_service_used'] += 1
                return result

            # Fall back to EMF
            return self._create_emf_fallback_result(element, analysis)

        except Exception as e:
            self.logger.warning(f"PowerPoint conversion failed: {e}")
            return self._create_emf_fallback_result(element, analysis)

    def _try_preset_conversion(self, element: ET.Element, analysis: PatternAnalysis,
                             context: Any) -> Dict[str, Any]:
        """Try converting pattern to PowerPoint preset."""
        if not analysis.preset_candidate:
            return {'success': False, 'method': 'preset', 'error': 'No preset candidate'}

        try:
            # Extract foreground and background colors
            fg_color, bg_color = self._extract_pattern_colors(element, analysis)

            # Generate PowerPoint preset XML
            preset_xml = f"""<a:pattFill prst="{analysis.preset_candidate}">
    <a:fgClr><a:srgbClr val="{fg_color}"/></a:fgClr>
    <a:bgClr><a:srgbClr val="{bg_color}"/></a:bgClr>
</a:pattFill>"""

            return {
                'success': True,
                'method': 'preset',
                'preset': analysis.preset_candidate,
                'drawingml_xml': preset_xml,
                'foreground_color': fg_color,
                'background_color': bg_color
            }

        except Exception as e:
            return {'success': False, 'method': 'preset', 'error': str(e)}

    def _try_pattern_service(self, element: ET.Element, analysis: PatternAnalysis,
                           context: Any) -> Dict[str, Any]:
        """Try using the existing pattern service."""
        try:
            # Get pattern ID
            pattern_id = element.get('id', '')
            if not pattern_id:
                return {'success': False, 'method': 'pattern_service', 'error': 'No pattern ID'}

            # Check if pattern service is available
            if hasattr(self.services, 'pattern_service'):
                pattern_service = self.services.pattern_service

                # Register pattern if not already registered
                pattern_service.register_pattern(pattern_id, element)

                # Get pattern content
                pattern_content = pattern_service.get_pattern_content(pattern_id, context)

                if pattern_content:
                    return {
                        'success': True,
                        'method': 'pattern_service',
                        'pattern_id': pattern_id,
                        'drawingml_xml': pattern_content
                    }

        except Exception as e:
            self.logger.debug(f"Pattern service failed: {e}")

        return {'success': False, 'method': 'pattern_service', 'error': 'Service failed'}

    def _extract_pattern_colors(self, element: ET.Element, analysis: PatternAnalysis) -> Tuple[str, str]:
        """Extract foreground and background colors from pattern."""
        fg_color = "000000"  # Default black foreground
        bg_color = "FFFFFF"  # Default white background

        # Analyze pattern content for colors
        children = list(element)
        colors_found = []

        for child in children:
            # Check fill color
            fill = child.get('fill')
            if fill and fill not in ['none', 'transparent']:
                colors_found.append(fill)

            # Check stroke color
            stroke = child.get('stroke')
            if stroke and stroke not in ['none', 'transparent']:
                colors_found.append(stroke)

        # Extract the most common colors
        if colors_found:
            # Use first color as foreground
            try:
                from ...color import Color
                color_obj = Color(colors_found[0])
                fg_color = color_obj.hex()[1:]  # Remove # prefix
            except Exception:
                fg_color = "000000"

            # If there's a second color, use it as background
            if len(colors_found) > 1:
                try:
                    color_obj = Color(colors_found[1])
                    bg_color = color_obj.hex()[1:]  # Remove # prefix
                except Exception:
                    bg_color = "FFFFFF"

        return fg_color, bg_color

    def _create_emf_fallback_result(self, element: ET.Element, analysis: PatternAnalysis) -> Dict[str, Any]:
        """Create EMF fallback result."""
        self.stats['emf_fallbacks'] += 1

        return {
            'success': True,
            'method': 'emf_fallback',
            'pattern_type': analysis.pattern_type.value,
            'complexity': analysis.complexity.value,
            'recommendation': 'Use EMF vector tile with blipFill',
            'optimizations_available': [opt.value for opt in analysis.optimization_opportunities]
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

    def _copy_element(self, element: ET.Element) -> ET.Element:
        """Create a deep copy of an element."""
        # Create new element with same tag
        copied = ET.Element(element.tag)

        # Copy attributes
        for key, value in element.attrib.items():
            copied.set(key, value)

        # Copy text content
        if element.text:
            copied.text = element.text
        if element.tail:
            copied.tail = element.tail

        # Copy children recursively
        for child in element:
            copied.append(self._copy_element(child))

        return copied

    def get_optimization_recommendations(self, element: ET.Element,
                                       context: Any) -> List[str]:
        """Get optimization recommendations for a pattern element."""
        try:
            analysis = self.pattern_processor.analyze_pattern_element(element, context)

            recommendations = []

            for optimization in analysis.optimization_opportunities:
                if optimization == PatternOptimization.PRESET_MAPPING:
                    recommendations.append(
                        f"Pattern can be mapped to PowerPoint preset: {analysis.preset_candidate}"
                    )
                elif optimization == PatternOptimization.COLOR_SIMPLIFICATION:
                    recommendations.append("Simplify pattern colors for better compatibility")
                elif optimization == PatternOptimization.TRANSFORM_FLATTENING:
                    recommendations.append("Flatten pattern transforms for better performance")
                elif optimization == PatternOptimization.EMF_OPTIMIZATION:
                    recommendations.append("Use EMF fallback for optimal rendering quality")
                elif optimization == PatternOptimization.TILE_OPTIMIZATION:
                    recommendations.append("Optimize pattern tile size for better performance")

            if not analysis.powerpoint_compatible:
                recommendations.append("Pattern may not be fully compatible with PowerPoint")

            if analysis.emf_fallback_recommended:
                recommendations.append("EMF fallback recommended for this pattern complexity")

            if analysis.estimated_performance_impact in ['high', 'very_high']:
                recommendations.append("Complex pattern may impact presentation performance")

            return recommendations

        except Exception as e:
            self.logger.error(f"Failed to get recommendations: {e}")
            return ["Unable to analyze pattern for optimization recommendations"]

    def batch_process_patterns(self, elements: List[ET.Element], context: Any,
                             apply_optimizations: bool = True) -> Dict[str, Any]:
        """Process multiple pattern elements in batch."""
        results = []
        total_optimizations = 0
        total_preprocessing = 0
        conversion_methods = {'preset': 0, 'pattern_service': 0, 'emf_fallback': 0}

        for element in elements:
            try:
                result = self.process_pattern_element(element, context, apply_optimizations)
                results.append(result)

                if result.get('success'):
                    total_optimizations += result.get('optimizations_applied', 0)
                    if result.get('preprocessing_applied'):
                        total_preprocessing += 1

                    method = result.get('conversion_method', 'unknown')
                    if method in conversion_methods:
                        conversion_methods[method] += 1

            except Exception as e:
                self.logger.error(f"Batch processing failed for element: {e}")
                results.append(self._create_fallback_result(element, str(e)))

        return {
            'total_processed': len(elements),
            'successful': sum(1 for r in results if r.get('success')),
            'failed': sum(1 for r in results if not r.get('success')),
            'total_optimizations': total_optimizations,
            'total_preprocessing': total_preprocessing,
            'conversion_methods': conversion_methods,
            'results': results
        }

    def get_service_statistics(self) -> Dict[str, Any]:
        """Get comprehensive service statistics."""
        processor_stats = self.pattern_processor.get_processing_statistics()
        service_stats = self.stats.copy()

        return {
            'service_stats': service_stats,
            'processor_stats': processor_stats,
            'cache_efficiency': (
                processor_stats['cache_hits'] / max(processor_stats['patterns_analyzed'], 1)
            ) * 100,
            'preset_success_rate': (
                service_stats['preset_conversions'] / max(service_stats['elements_processed'], 1)
            ) * 100
        }

    def reset_statistics(self) -> None:
        """Reset all statistics."""
        self.stats = {
            'elements_processed': 0,
            'optimizations_applied': 0,
            'preprocessing_applied': 0,
            'preset_conversions': 0,
            'emf_fallbacks': 0,
            'pattern_service_used': 0
        }
        self.pattern_processor.reset_statistics()


def create_pattern_processor_service(services: ConversionServices) -> PatternProcessorService:
    """
    Create a pattern processor service with dependencies.

    Args:
        services: ConversionServices container

    Returns:
        Configured PatternProcessorService
    """
    pattern_processor = PatternProcessor(services)
    return PatternProcessorService(services, pattern_processor)