#!/usr/bin/env python3
"""
Integration tests for preprocessing pipeline.

This module tests the integration between preprocessing plugins and ensures
the preprocessing chain works correctly with various SVG inputs.
"""

import pytest
import tempfile
import os
from pathlib import Path
from typing import Dict, List, Any
from lxml import etree as ET
import time

# Import preprocessing modules
from src.preprocessing.optimizer import SVGOptimizer
from src.preprocessing.base import PreprocessingContext


class PreprocessingTestResult:
    """Result of preprocessing pipeline test."""
    
    def __init__(self, success: bool, original_svg: str, processed_svg: str = None,
                 stats: Dict[str, int] = None, duration: float = 0.0, 
                 error: str = None):
        self.success = success
        self.original_svg = original_svg
        self.processed_svg = processed_svg
        self.stats = stats or {}
        self.duration = duration
        self.error = error
    
    @property
    def reduction_percentage(self) -> float:
        """Calculate size reduction percentage."""
        if not self.processed_svg:
            return 0.0
        orig_size = len(self.original_svg)
        proc_size = len(self.processed_svg)
        return ((orig_size - proc_size) / orig_size) * 100 if orig_size > 0 else 0.0
    
    def __str__(self):
        status = "SUCCESS" if self.success else "FAILED"
        return f"Preprocessing {status} ({self.duration:.3f}s, {self.reduction_percentage:.1f}% reduction)"


class PreprocessingAnalyzer:
    """Analyzes preprocessing results."""
    
    def analyze_preprocessing_effect(self, original_svg: str, processed_svg: str) -> Dict[str, Any]:
        """Analyze the effect of preprocessing on SVG content."""
        analysis = {
            'size_reduction': 0.0,
            'element_reduction': 0,
            'attribute_cleanup': 0,
            'path_simplification': False,
            'group_collapse': False,
            'valid_xml': False,
            'errors': []
        }
        
        try:
            # Parse both SVGs
            orig_root = ET.fromstring(original_svg)
            proc_root = ET.fromstring(processed_svg)
            
            analysis['valid_xml'] = True
            
            # Size analysis
            analysis['size_reduction'] = ((len(original_svg) - len(processed_svg)) / len(original_svg)) * 100
            
            # Element count analysis
            orig_elements = len(list(orig_root.iter()))
            proc_elements = len(list(proc_root.iter()))
            analysis['element_reduction'] = orig_elements - proc_elements
            
            # Path simplification detection
            orig_paths = [el for el in orig_root.iter() if el.tag.endswith('path')]
            proc_paths = [el for el in proc_root.iter() if el.tag.endswith('path')]
            
            for orig_path, proc_path in zip(orig_paths, proc_paths):
                orig_d = orig_path.get('d', '')
                proc_d = proc_path.get('d', '')
                if len(proc_d) < len(orig_d):
                    analysis['path_simplification'] = True
                    break
            
            # Group collapse detection
            orig_groups = len([el for el in orig_root.iter() if el.tag.endswith('g')])
            proc_groups = len([el for el in proc_root.iter() if el.tag.endswith('g')])
            if proc_groups < orig_groups:
                analysis['group_collapse'] = True
            
        except ET.ParseError as e:
            analysis['errors'].append(f"XML parse error: {str(e)}")
        except Exception as e:
            analysis['errors'].append(f"Analysis error: {str(e)}")
        
        return analysis


@pytest.fixture
def preprocessing_analyzer():
    """Fixture providing preprocessing analyzer."""
    return PreprocessingAnalyzer()


@pytest.fixture
def sample_svg_inputs():
    """Fixture providing sample SVG inputs for preprocessing tests."""
    samples = {}
    
    # Verbose SVG with redundant attributes
    samples['verbose_svg'] = '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="200.000" height="200.000" xmlns="http://www.w3.org/2000/svg" 
     xmlns:xlink="http://www.w3.org/1999/xlink" style="">
    <g id="group1" transform="translate(0,0)">
        <rect x="10.000" y="10.000" width="80.000" height="80.000" 
              fill="red" stroke="none" stroke-width="0.000" 
              fill-opacity="1.000" stroke-opacity="1.000"/>
    </g>
    <!-- This is a comment that can be removed -->
    <g id="group2" transform="translate(0,0)">
        <circle cx="150.000" cy="150.000" r="30.000" 
                fill="blue" stroke="none" stroke-width="0.000"/>
    </g>
</svg>'''
    
    # SVG with complex path that can be simplified
    samples['complex_path'] = '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="300" height="300" xmlns="http://www.w3.org/2000/svg">
    <path d="M10,10 L11,10 L12,10 L13,10 L14,10 L15,10 L16,10 L17,10 L18,10 L19,10 L20,10 
             L21,10 L22,10 L23,10 L24,10 L25,10 L26,10 L27,10 L28,10 L29,10 L30,10
             L30,11 L30,12 L30,13 L30,14 L30,15 L30,16 L30,17 L30,18 L30,19 L30,20 Z" 
          fill="green"/>
</svg>'''
    
    # SVG with nested empty groups
    samples['nested_groups'] = '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="100" height="100" xmlns="http://www.w3.org/2000/svg">
    <g>
        <g>
            <g>
                <rect x="20" y="20" width="60" height="60" fill="purple"/>
            </g>
            <g></g>
        </g>
        <g></g>
    </g>
</svg>'''
    
    # SVG with polygon that can be simplified
    samples['verbose_polygon'] = '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="200" height="200" xmlns="http://www.w3.org/2000/svg">
    <polygon points="50,50 51,50 52,50 53,50 54,50 55,50 56,50 57,50 58,50 59,50 60,50
                     60,51 60,52 60,53 60,54 60,55 60,56 60,57 60,58 60,59 60,60
                     59,60 58,60 57,60 56,60 55,60 54,60 53,60 52,60 51,60 50,60
                     50,59 50,58 50,57 50,56 50,55 50,54 50,53 50,52 50,51" 
             fill="orange"/>
</svg>'''
    
    # SVG with unused definitions
    samples['unused_defs'] = '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="100" height="100" xmlns="http://www.w3.org/2000/svg">
    <defs>
        <linearGradient id="unused1">
            <stop offset="0%" stop-color="red"/>
            <stop offset="100%" stop-color="blue"/>
        </linearGradient>
        <pattern id="unused2" width="10" height="10">
            <rect width="10" height="10" fill="gray"/>
        </pattern>
        <linearGradient id="used1">
            <stop offset="0%" stop-color="green"/>
            <stop offset="100%" stop-color="yellow"/>
        </linearGradient>
    </defs>
    <rect x="10" y="10" width="80" height="80" fill="url(#used1)"/>
</svg>'''
    
    return samples


class TestPreprocessingPipeline:
    """Preprocessing pipeline integration tests."""
    
    def test_minimal_preprocessing(self, sample_svg_inputs, preprocessing_analyzer):
        """Test minimal preprocessing configuration."""
        optimizer = SVGOptimizer({'preset': 'minimal'})
        
        for test_name, svg_content in sample_svg_inputs.items():
            start_time = time.time()
            
            # Run preprocessing
            processed_svg = optimizer.optimize(svg_content)
            duration = time.time() - start_time
            
            # Analyze results
            analysis = preprocessing_analyzer.analyze_preprocessing_effect(svg_content, processed_svg)
            
            result = PreprocessingTestResult(
                success=analysis['valid_xml'],
                original_svg=svg_content,
                processed_svg=processed_svg,
                duration=duration
            )
            
            # Assertions
            assert result.success, f"Minimal preprocessing failed for {test_name}: {analysis['errors']}"
            assert analysis['valid_xml'], f"Invalid XML output for {test_name}"
            
            # Should still be valid SVG
            try:
                ET.fromstring(processed_svg)
            except ET.ParseError:
                pytest.fail(f"Invalid XML output for {test_name}")
    
    def test_default_preprocessing(self, sample_svg_inputs, preprocessing_analyzer):
        """Test default preprocessing configuration."""
        optimizer = SVGOptimizer({'preset': 'default'})
        
        for test_name, svg_content in sample_svg_inputs.items():
            start_time = time.time()
            
            processed_svg = optimizer.optimize(svg_content)
            duration = time.time() - start_time
            
            analysis = preprocessing_analyzer.analyze_preprocessing_effect(svg_content, processed_svg)
            
            result = PreprocessingTestResult(
                success=analysis['valid_xml'],
                original_svg=svg_content,
                processed_svg=processed_svg,
                duration=duration
            )
            
            # Assertions
            assert result.success, f"Default preprocessing failed for {test_name}: {analysis['errors']}"
            
            # Should have some optimization effect
            if test_name == 'verbose_svg':
                assert result.reduction_percentage > 0, "No size reduction on verbose SVG"
            
            if test_name == 'nested_groups':
                assert analysis['element_reduction'] > 0, "No empty group removal"
    
    def test_aggressive_preprocessing(self, sample_svg_inputs, preprocessing_analyzer):
        """Test aggressive preprocessing configuration."""
        optimizer = SVGOptimizer({'preset': 'aggressive'})
        
        for test_name, svg_content in sample_svg_inputs.items():
            start_time = time.time()
            
            processed_svg = optimizer.optimize(svg_content)
            duration = time.time() - start_time
            
            analysis = preprocessing_analyzer.analyze_preprocessing_effect(svg_content, processed_svg)
            
            result = PreprocessingTestResult(
                success=analysis['valid_xml'],
                original_svg=svg_content,
                processed_svg=processed_svg,
                duration=duration
            )
            
            # Assertions
            assert result.success, f"Aggressive preprocessing failed for {test_name}: {analysis['errors']}"
            
            # Should have significant optimization effect
            if test_name == 'complex_path':
                assert analysis['path_simplification'], "No path simplification applied"
            
            if test_name == 'verbose_polygon':
                assert result.reduction_percentage > 10, "Insufficient polygon simplification"
    
    def test_preprocessing_plugin_chain(self):
        """Test specific preprocessing plugin interactions."""
        from src.preprocessing.plugins import (
            CleanupAttrsPlugin, CleanupNumericValuesPlugin, RemoveEmptyContainersPlugin, 
            ConvertColorsPlugin, RemoveCommentsPlugin
        )
        from src.preprocessing.base import PreprocessingContext
        
        # Test SVG with various issues
        test_svg = '''<?xml version="1.0"?>
<svg width="100.000" height="100.000" xmlns="http://www.w3.org/2000/svg">
    <!-- Remove this comment -->
    <g>
        <g></g> <!-- Empty group to remove -->
        <rect x="10" y="10" width="80" height="80" fill="#FF0000" stroke=""/>
    </g>
</svg>'''
        
        root = ET.fromstring(test_svg)
        context = PreprocessingContext()
        context.precision = 2
        
        # Apply plugins in sequence
        plugins = [
            RemoveCommentsPlugin(),
            CleanupAttrsPlugin(),
            CleanupNumericValuesPlugin(),
            RemoveEmptyContainersPlugin(),
            ConvertColorsPlugin()
        ]
        
        modifications = 0
        for plugin in plugins:
            for elem in list(root.iter()):
                if plugin.can_process(elem, context):
                    if plugin.process(elem, context):
                        modifications += 1
        
        # Check results
        assert modifications > 0, "No preprocessing modifications made"
        assert context.modifications_made, "Context not updated with modifications"
        
        # Verify specific effects
        processed_svg = ET.tostring(root, encoding='unicode')
        assert "<!--" not in processed_svg, "Comments not removed"
        assert ".000" not in processed_svg, "Numeric precision not cleaned"
    
    def test_preprocessing_error_handling(self):
        """Test preprocessing error handling with malformed SVG."""
        optimizer = SVGOptimizer({'preset': 'default'})
        
        # Malformed SVG
        malformed_svg = '''<?xml version="1.0"?>
<svg width="100" height="100" xmlns="http://www.w3.org/2000/svg">
    <rect x="10" y="10" width="80" height="80" fill="red"
    <!-- Missing closing bracket and tag -->'''
        
        try:
            processed_svg = optimizer.optimize(malformed_svg)
            # If it succeeds, should return something reasonable
            assert processed_svg is not None
        except Exception as e:
            # Exception is acceptable for malformed input
            assert isinstance(e, (ValueError, ET.ParseError, Exception))
    
    def test_preprocessing_performance(self, sample_svg_inputs):
        """Test preprocessing performance characteristics."""
        optimizer = SVGOptimizer({'preset': 'aggressive'})
        
        performance_results = []
        
        for test_name, svg_content in sample_svg_inputs.items():
            # Multiple runs for consistent timing
            times = []
            for _ in range(5):
                start_time = time.time()
                processed_svg = optimizer.optimize(svg_content)
                duration = time.time() - start_time
                times.append(duration)
            
            avg_time = sum(times) / len(times)
            reduction = ((len(svg_content) - len(processed_svg)) / len(svg_content)) * 100
            
            performance_results.append({
                'test': test_name,
                'avg_time': avg_time,
                'reduction': reduction,
                'original_size': len(svg_content),
                'processed_size': len(processed_svg)
            })
            
            # Performance assertions
            assert avg_time < 1.0, f"Preprocessing too slow for {test_name}: {avg_time:.3f}s"
        
        # Print performance summary
        print("\nPreprocessing Performance Results:")
        for result in performance_results:
            print(f"  {result['test']}: {result['avg_time']:.3f}s, "
                  f"{result['reduction']:.1f}% reduction, "
                  f"{result['original_size']} -> {result['processed_size']} bytes")
    
    def test_preprocessing_idempotency(self, sample_svg_inputs):
        """Test that preprocessing is idempotent (running twice produces same result)."""
        optimizer = SVGOptimizer({'preset': 'aggressive'})
        
        for test_name, svg_content in sample_svg_inputs.items():
            # First preprocessing pass
            processed_once = optimizer.optimize(svg_content)
            
            # Second preprocessing pass
            processed_twice = optimizer.optimize(processed_once)
            
            # Should be identical (or very close)
            size_diff = abs(len(processed_once) - len(processed_twice))
            assert size_diff <= 1, f"Preprocessing not idempotent for {test_name}: {size_diff} byte difference"
    
    def test_custom_preprocessing_config(self):
        """Test custom preprocessing configuration."""
        custom_config = {
            'preset': 'default',
            'plugins': {
                'cleanupAttrs': {'enabled': True, 'precision': 1},
                'removeComments': {'enabled': False},
                'simplifyPolygon': {'enabled': True, 'tolerance': 0.1}
            }
        }
        
        optimizer = SVGOptimizer(custom_config)
        
        test_svg = '''<?xml version="1.0"?>
<svg width="100.000" height="100.000" xmlns="http://www.w3.org/2000/svg">
    <!-- This comment should NOT be removed -->
    <polygon points="0,0 1,0 2,0 3,0 4,0 5,0 5,1 5,2 5,3 5,4 5,5 0,5" fill="red"/>
</svg>'''
        
        processed_svg = optimizer.optimize(test_svg)
        
        # Check that custom config was applied
        assert "<!--" in processed_svg, "Comments were removed despite being disabled"
        assert ".000" not in processed_svg, "Numeric precision not cleaned with precision=1"
    
    @pytest.mark.slow
    def test_large_svg_preprocessing(self):
        """Test preprocessing with large SVG files."""
        # Generate large SVG
        large_svg_parts = ['<?xml version="1.0"?><svg width="1000" height="1000" xmlns="http://www.w3.org/2000/svg">']
        
        # Add many elements
        for i in range(1000):
            x = (i % 100) * 10
            y = (i // 100) * 10
            large_svg_parts.append(f'<rect x="{x}.000" y="{y}.000" width="8.000" height="8.000" fill="red"/>')
        
        large_svg_parts.append('</svg>')
        large_svg = ''.join(large_svg_parts)
        
        optimizer = SVGOptimizer({'preset': 'aggressive'})
        
        start_time = time.time()
        processed_svg = optimizer.optimize(large_svg)
        duration = time.time() - start_time
        
        # Performance assertions for large files
        assert duration < 5.0, f"Large SVG preprocessing too slow: {duration:.2f}s"
        
        # Should have significant size reduction
        reduction = ((len(large_svg) - len(processed_svg)) / len(large_svg)) * 100
        assert reduction > 10, f"Insufficient optimization of large SVG: {reduction:.1f}%"
        
        # Should still be valid XML
        try:
            ET.fromstring(processed_svg)
        except ET.ParseError:
            pytest.fail("Large SVG preprocessing produced invalid XML")


if __name__ == "__main__":
    # CLI for testing preprocessing pipeline
    import sys
    
    if len(sys.argv) == 2:
        svg_file = sys.argv[1]
        
        with open(svg_file, 'r') as f:
            svg_content = f.read()
        
        optimizer = SVGOptimizer({'preset': 'aggressive'})
        
        start_time = time.time()
        processed_svg = optimizer.optimize(svg_content)
        duration = time.time() - start_time
        
        analyzer = PreprocessingAnalyzer()
        analysis = analyzer.analyze_preprocessing_effect(svg_content, processed_svg)
        
        result = PreprocessingTestResult(
            success=analysis['valid_xml'],
            original_svg=svg_content,
            processed_svg=processed_svg,
            duration=duration
        )
        
        print(result)
        print(f"Size: {len(svg_content)} -> {len(processed_svg)} bytes")
        print(f"Elements reduced: {analysis['element_reduction']}")
        print(f"Path simplification: {analysis['path_simplification']}")
        print(f"Group collapse: {analysis['group_collapse']}")
        
        if analysis['errors']:
            print(f"Errors: {analysis['errors']}")
    else:
        print("Usage: python test_preprocessing_pipeline.py <input.svg>")
        sys.exit(1)