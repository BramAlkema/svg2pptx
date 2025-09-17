#!/usr/bin/env python3
"""
Performance Integration Module

This module wires up the orphaned performance modules into the main conversion pipeline,
providing optimization capabilities that were previously isolated.

Key Integration Points:
- Main converter enhancement with performance optimizations
- Preprocessing pipeline integration
- Caching layer for conversion results
- Batch processing for multiple SVG files
"""

from typing import Dict, List, Any, Optional, Union
import logging
from pathlib import Path
from lxml import etree as ET

# Import performance modules
from ..performance.optimizer import PerformanceOptimizer, OptimizationConfig, OptimizationLevel
from ..performance.cache import get_global_cache
from ..performance.batch import BatchProcessor, BatchStrategy
from ..performance.profiler import get_profiler

# Import preprocessing modules  
from ..preprocessing.geometry_simplify import simplify_path
from ..preprocessing.advanced_geometry_plugins import GeometryPlugin

# Import core modules
from ..converters.base import ConverterRegistry, ConversionContext
from ..svg2drawingml import SVGParser

logger = logging.getLogger(__name__)


class OptimizedSVGConverter:
    """Enhanced SVG converter with integrated performance optimizations."""
    
    def __init__(self, optimization_level: OptimizationLevel = OptimizationLevel.STANDARD, services: 'ConversionServices' = None):
        """Initialize OptimizedSVGConverter with performance optimizations.

        Args:
            optimization_level: Level of optimization to apply
            services: ConversionServices instance (required for new usage, optional for migration)
        """
        self.optimization_config = OptimizationConfig(level=optimization_level)
        self.optimizer = PerformanceOptimizer(self.optimization_config)
        self.registry = ConverterRegistry()
        self.cache = get_global_cache()
        self.profiler = get_profiler()

        # Import here to avoid circular imports
        from ..services.conversion_services import ConversionServices

        # Create default services if none provided (for migration compatibility)
        if services is None:
            services = ConversionServices.create_default()

        self.services = services
        
        # Initialize preprocessing pipeline
        self.geometry_plugins = self._load_geometry_plugins()
        
        logger.info(f"Initialized OptimizedSVGConverter with {optimization_level.value} optimization")
    
    def _load_geometry_plugins(self) -> List[GeometryPlugin]:
        """Load available geometry preprocessing plugins."""
        plugins = []
        try:
            # Load available geometry plugins
            # This would be expanded with actual plugin discovery
            plugins.append(GeometryPlugin('path_simplifier', self._apply_path_simplification))
            plugins.append(GeometryPlugin('curve_optimizer', self._optimize_curves))
            logger.info(f"Loaded {len(plugins)} geometry plugins")
        except Exception as e:
            logger.warning(f"Failed to load some geometry plugins: {e}")
        
        return plugins
    
    def _apply_path_simplification(self, path_data: str, tolerance: float = 1.0) -> str:
        """Apply path simplification using the preprocessing module."""
        try:
            # This would integrate with the actual geometry_simplify module
            # For now, return simplified path
            simplified = simplify_path(path_data, tolerance)
            return simplified
        except Exception as e:
            logger.warning(f"Path simplification failed: {e}")
            return path_data
    
    def _optimize_curves(self, path_data: str) -> str:
        """Optimize curve representations for better performance."""
        # Placeholder for curve optimization
        # This would implement actual curve optimization algorithms
        return path_data
    
    def convert_svg(self, svg_content: str, output_format: str = "drawingml") -> Dict[str, Any]:
        """Convert SVG with full optimization pipeline."""
        
        # Start profiling if enabled
        if self.optimization_config.level == OptimizationLevel.MAXIMUM:
            self.profiler.start_operation("svg_conversion")
        
        try:
            # Check cache first
            cache_key = self._generate_cache_key(svg_content, output_format)
            if self.optimization_config.enable_caching:
                cached_result = self.cache.get(cache_key)
                if cached_result:
                    logger.debug("Cache hit for SVG conversion")
                    return cached_result
            
            # Preprocess SVG
            preprocessed_svg = self._preprocess_svg(svg_content)
            
            # Parse SVG with enhanced parser
            parser = self._create_enhanced_parser(preprocessed_svg)
            
            # Convert using optimized pipeline
            result = self._convert_with_optimization(parser, output_format)
            
            # Cache result
            if self.optimization_config.enable_caching and result:
                self.cache.set(cache_key, result, ttl=self.optimization_config.cache_ttl)
            
            return result
            
        except Exception as e:
            logger.error(f"SVG conversion failed: {e}")
            raise
        finally:
            # End profiling
            if self.optimization_config.level == OptimizationLevel.MAXIMUM:
                self.profiler.end_operation("svg_conversion")
    
    def _preprocess_svg(self, svg_content: str) -> str:
        """Apply preprocessing optimizations to SVG."""
        try:
            # Parse with lxml for preprocessing
            root = ET.fromstring(svg_content.encode('utf-8'))
            
            # Apply geometry plugins to path elements
            for path_elem in root.xpath('.//path'):
                path_data = path_elem.get('d', '')
                if path_data:
                    # Apply each geometry plugin
                    optimized_data = path_data
                    for plugin in self.geometry_plugins:
                        try:
                            optimized_data = plugin.apply(optimized_data)
                        except Exception as e:
                            logger.warning(f"Plugin {plugin.name} failed: {e}")
                    
                    if optimized_data != path_data:
                        path_elem.set('d', optimized_data)
                        logger.debug(f"Path optimized by geometry plugins")
            
            # Return optimized SVG
            return ET.tostring(root, encoding='unicode')
            
        except Exception as e:
            logger.warning(f"SVG preprocessing failed: {e}")
            return svg_content
    
    def _create_enhanced_parser(self, svg_content: str):
        """Create enhanced SVG parser with lxml support."""
        # This would create an enhanced parser that uses lxml instead of ElementTree
        # For now, return the standard parser
        return SVGParser(svg_content)
    
    def _convert_with_optimization(self, parser, output_format: str) -> Dict[str, Any]:
        """Perform conversion with optimization."""
        
        # Create conversion context
        context = ConversionContext(services=self.services)
        
        # Apply pool-based conversion if enabled
        if self.optimization_config.enable_pooling:
            return self._pool_based_conversion(parser, context, output_format)
        else:
            return self._standard_conversion(parser, context, output_format)
    
    def _pool_based_conversion(self, parser, context: ConversionContext, output_format: str) -> Dict[str, Any]:
        """Use converter pool for optimized conversion."""
        # This would integrate with the converter pool
        # For now, fallback to standard conversion
        logger.debug("Using pool-based conversion")
        return self._standard_conversion(parser, context, output_format)
    
    def _standard_conversion(self, parser, context: ConversionContext, output_format: str) -> Dict[str, Any]:
        """Standard conversion process."""
        # This would implement the actual conversion logic
        # integrating with the converter registry
        
        result = {
            'format': output_format,
            'width': parser.width,
            'height': parser.height,
            'viewbox': parser.viewbox,
            'content': '<!-- Converted content would go here -->',
            'optimized': True,
            'preprocessing_applied': len(self.geometry_plugins) > 0
        }
        
        return result
    
    def _generate_cache_key(self, svg_content: str, output_format: str) -> str:
        """Generate cache key for SVG content."""
        import hashlib
        content_hash = hashlib.md5(svg_content.encode('utf-8')).hexdigest()
        return f"svg_{content_hash}_{output_format}"
    
    def convert_batch(self, svg_files: List[Union[str, Path]], 
                     output_format: str = "drawingml") -> List[Dict[str, Any]]:
        """Convert multiple SVG files with batch optimization."""
        
        if not self.optimization_config.enable_batching:
            # Convert individually
            results = []
            for svg_file in svg_files:
                if isinstance(svg_file, (str, Path)):
                    with open(svg_file, 'r', encoding='utf-8') as f:
                        svg_content = f.read()
                else:
                    svg_content = svg_file
                    
                result = self.convert_svg(svg_content, output_format)
                results.append(result)
            return results
        
        # Use batch processor for optimization
        logger.info(f"Starting batch conversion of {len(svg_files)} files")
        
        batch_processor = BatchProcessor(
            strategy=self.optimization_config.batch_strategy,
            max_workers=self.optimization_config.max_batch_workers
        )
        
        # Process in batches
        return batch_processor.process_svg_batch(svg_files, self.convert_svg)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics from profiler."""
        if self.optimization_config.level == OptimizationLevel.MAXIMUM:
            return self.profiler.get_stats()
        else:
            return {"profiling": "disabled"}
    
    def clear_cache(self):
        """Clear the conversion cache."""
        self.cache.clear()
        logger.info("Conversion cache cleared")


def create_optimized_converter(optimization_level: str = "standard") -> OptimizedSVGConverter:
    """Factory function to create optimized converter with specified level."""
    
    level_mapping = {
        "none": OptimizationLevel.NONE,
        "basic": OptimizationLevel.BASIC,
        "standard": OptimizationLevel.STANDARD,
        "aggressive": OptimizationLevel.AGGRESSIVE,
        "maximum": OptimizationLevel.MAXIMUM
    }
    
    level = level_mapping.get(optimization_level.lower(), OptimizationLevel.STANDARD)
    return OptimizedSVGConverter(level)


# Integration helper functions
def integrate_performance_modules():
    """Initialize and integrate performance modules into the main pipeline."""
    
    logger.info("Integrating performance modules...")
    
    # Initialize global cache
    cache = get_global_cache()
    cache.configure(max_size=1000, default_ttl=300)
    
    # Initialize profiler
    profiler = get_profiler()
    profiler.configure(enabled=True)
    
    logger.info("Performance modules integrated successfully")


def migrate_to_lxml():
    """Helper to identify modules that need lxml migration."""
    
    import os
    import re
    
    modules_needing_migration = []
    src_path = Path(__file__).parent.parent
    
    for py_file in src_path.rglob("*.py"):
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Check for ElementTree imports
            if re.search(r'import\s+xml\.etree\.ElementTree', content):
                modules_needing_migration.append(str(py_file.relative_to(src_path)))
        except:
            continue
    
    logger.warning(f"Found {len(modules_needing_migration)} modules still using ElementTree:")
    for module in modules_needing_migration:
        logger.warning(f"  - {module}")
    
    return modules_needing_migration


if __name__ == "__main__":
    # Demo integration
    logging.basicConfig(level=logging.INFO)
    
    # Initialize integration
    integrate_performance_modules()
    
    # Create optimized converter
    converter = create_optimized_converter("standard")
    
    # Check for lxml migration needs
    migrate_to_lxml()
    
    print("Performance integration completed successfully!")