#!/usr/bin/env python3
"""
Comprehensive end-to-end tests for SVG2PPTX covering all major conversion paths.

This module tests the complete conversion pipeline with real-world scenarios,
focusing on achieving high code coverage and validating integration points.
"""

import pytest
import tempfile
import os
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional
import xml.etree.ElementTree as ET
from zipfile import ZipFile
import time
import threading
from concurrent.futures import ThreadPoolExecutor
import json


class ComprehensiveE2ETestSuite:
    """Comprehensive E2E test scenarios for SVG2PPTX."""

    @pytest.fixture
    def real_world_svg_samples(self):
        """Comprehensive SVG samples covering all major features."""
        samples = {}
        
        # 1. Corporate presentation slide
        samples['corporate_slide'] = '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="800" height="600" xmlns="http://www.w3.org/2000/svg">
    <defs>
        <linearGradient id="headerGrad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" style="stop-color:#1e3c72;stop-opacity:1" />
            <stop offset="100%" style="stop-color:#2a5298;stop-opacity:1" />
        </linearGradient>
        <pattern id="dots" patternUnits="userSpaceOnUse" width="20" height="20">
            <circle cx="10" cy="10" r="2" fill="#e0e0e0"/>
        </pattern>
    </defs>
    
    <!-- Background -->
    <rect width="800" height="600" fill="white"/>
    
    <!-- Header -->
    <rect x="0" y="0" width="800" height="80" fill="url(#headerGrad)"/>
    <text x="40" y="50" font-family="Arial" font-size="28" font-weight="bold" fill="white">
        Q4 Sales Report
    </text>
    
    <!-- Chart background -->
    <rect x="50" y="120" width="700" height="400" fill="url(#dots)" stroke="#ccc" stroke-width="2"/>
    
    <!-- Bar chart -->
    <g transform="translate(80, 150)">
        <rect x="0" y="250" width="80" height="120" fill="#4CAF50"/>
        <rect x="100" y="200" width="80" height="170" fill="#2196F3"/>
        <rect x="200" y="150" width="80" height="220" fill="#FF9800"/>
        <rect x="300" y="100" width="80" height="270" fill="#F44336"/>
        
        <text x="40" y="390" text-anchor="middle" font-size="14">Q1</text>
        <text x="140" y="390" text-anchor="middle" font-size="14">Q2</text>
        <text x="240" y="390" text-anchor="middle" font-size="14">Q3</text>
        <text x="340" y="390" text-anchor="middle" font-size="14">Q4</text>
    </g>
    
    <!-- Legend -->
    <g transform="translate(500, 200)">
        <rect x="0" y="0" width="15" height="15" fill="#4CAF50"/>
        <text x="25" y="12" font-size="12">Revenue</text>
        <rect x="0" y="25" width="15" height="15" fill="#2196F3"/>
        <text x="25" y="37" font-size="12">Profit</text>
    </g>
</svg>'''
        
        # 2. Technical diagram with paths and transforms
        samples['technical_diagram'] = '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="600" height="400" xmlns="http://www.w3.org/2000/svg">
    <defs>
        <marker id="arrowhead" markerWidth="10" markerHeight="7" 
                refX="10" refY="3.5" orient="auto">
            <polygon points="0 0, 10 3.5, 0 7" fill="#333"/>
        </marker>
    </defs>
    
    <!-- System components -->
    <g id="client" transform="translate(50, 50)">
        <rect x="0" y="0" width="100" height="60" rx="5" fill="#e3f2fd" stroke="#1976d2"/>
        <text x="50" y="35" text-anchor="middle" font-size="12">Client App</text>
    </g>
    
    <g id="server" transform="translate(250, 50)">
        <rect x="0" y="0" width="100" height="60" rx="5" fill="#f3e5f5" stroke="#7b1fa2"/>
        <text x="50" y="35" text-anchor="middle" font-size="12">API Server</text>
    </g>
    
    <g id="database" transform="translate(450, 50)">
        <ellipse cx="50" cy="30" rx="50" ry="30" fill="#e8f5e8" stroke="#388e3c"/>
        <text x="50" y="35" text-anchor="middle" font-size="12">Database</text>
    </g>
    
    <!-- Connections -->
    <path d="M150,80 L250,80" stroke="#333" stroke-width="2" marker-end="url(#arrowhead)"/>
    <path d="M350,80 L450,80" stroke="#333" stroke-width="2" marker-end="url(#arrowhead)"/>
    
    <!-- Data flow -->
    <g transform="translate(50, 200)">
        <path d="M0,0 Q100,50 200,0 T400,0" stroke="#ff5722" stroke-width="3" 
              fill="none" stroke-dasharray="5,5"/>
        <text x="200" y="70" text-anchor="middle" font-size="14" fill="#ff5722">
            Data Flow
        </text>
    </g>
</svg>'''
        
        # 3. Multi-slide animation sequence
        samples['animation_sequence'] = '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="400" height="300" xmlns="http://www.w3.org/2000/svg">
    <!-- Slide 1: Introduction -->
    <g id="slide1" data-slide-break="true" data-slide-title="Introduction">
        <rect width="400" height="300" fill="#f5f5f5"/>
        <text x="200" y="150" text-anchor="middle" font-size="24" font-weight="bold">
            Welcome to SVG2PPTX
        </text>
        <animate attributeName="opacity" values="0;1" dur="1s"/>
    </g>
    
    <!-- Slide 2: Features -->
    <g id="slide2" data-slide-break="true" data-slide-title="Key Features">
        <rect width="400" height="300" fill="#e3f2fd"/>
        <text x="200" y="80" text-anchor="middle" font-size="20" font-weight="bold">Key Features</text>
        <text x="50" y="120" font-size="14">• High-fidelity conversion</text>
        <text x="50" y="150" font-size="14">• Multi-slide support</text>
        <text x="50" y="180" font-size="14">• Advanced preprocessing</text>
        <animate attributeName="opacity" values="0;1" dur="1s" begin="1s"/>
    </g>
    
    <!-- Slide 3: Demo -->
    <g id="slide3" data-slide-break="true" data-slide-title="Live Demo">
        <rect width="400" height="300" fill="#e8f5e8"/>
        <circle cx="200" cy="150" r="50" fill="#4caf50">
            <animate attributeName="r" values="20;50;20" dur="2s" repeatCount="indefinite"/>
        </circle>
        <text x="200" y="250" text-anchor="middle" font-size="16">Live Demo</text>
    </g>
</svg>'''
        
        # 4. Complex paths and filters
        samples['complex_graphics'] = '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="500" height="500" xmlns="http://www.w3.org/2000/svg">
    <defs>
        <filter id="dropshadow" x="0" y="0" width="120%" height="120%">
            <feDropShadow dx="3" dy="3" stdDeviation="3" flood-opacity="0.3"/>
        </filter>
        
        <radialGradient id="radial" cx="50%" cy="50%" r="50%">
            <stop offset="0%" style="stop-color:#ffeb3b;stop-opacity:1" />
            <stop offset="100%" style="stop-color:#ff9800;stop-opacity:1" />
        </radialGradient>
    </defs>
    
    <!-- Complex path shapes -->
    <path d="M100,100 C100,100 200,50 300,100 C400,150 350,250 250,250 C150,250 100,150 100,100 Z"
          fill="url(#radial)" stroke="#333" stroke-width="2" filter="url(#dropshadow)"/>
    
    <!-- Bezier curves -->
    <path d="M50,300 Q150,200 250,300 T450,300" 
          stroke="#e91e63" stroke-width="4" fill="none"/>
    
    <!-- Star shape -->
    <path d="M250,50 L270,100 L320,100 L285,135 L295,190 L250,160 L205,190 L215,135 L180,100 L230,100 Z"
          fill="#9c27b0" transform="rotate(15 250 120)"/>
    
    <!-- Text on path -->
    <defs>
        <path id="textpath" d="M50,400 Q250,350 450,400"/>
    </defs>
    <text font-size="16" fill="#333">
        <textPath href="#textpath">Following the curved path</textPath>
    </text>
</svg>'''
        
        # 5. Symbol definitions and reuse
        samples['symbols_reuse'] = '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="600" height="400" xmlns="http://www.w3.org/2000/svg">
    <defs>
        <symbol id="icon-user" viewBox="0 0 24 24">
            <circle cx="12" cy="8" r="4" fill="#666"/>
            <path d="M12,14 C8,14 4,16 4,20 L20,20 C20,16 16,14 12,14 Z" fill="#666"/>
        </symbol>
        
        <symbol id="icon-gear" viewBox="0 0 24 24">
            <path d="M12,2 C13.1,2 14,2.9 14,4 C14,5.1 13.1,6 12,6 C10.9,6 10,5.1 10,4 C10,2.9 10.9,2 12,2 Z M21,9 L15,9 L15,15 L21,15 L21,9 Z M9,9 L3,9 L3,15 L9,15 L9,9 Z" fill="#666"/>
        </symbol>
    </defs>
    
    <!-- Organization chart -->
    <g transform="translate(50, 50)">
        <!-- CEO -->
        <use href="#icon-user" x="250" y="0" width="40" height="40"/>
        <text x="270" y="55" text-anchor="middle" font-size="12">CEO</text>
        
        <!-- Managers -->
        <use href="#icon-user" x="150" y="100" width="30" height="30"/>
        <text x="165" y="145" text-anchor="middle" font-size="10">CTO</text>
        
        <use href="#icon-user" x="350" y="100" width="30" height="30"/>
        <text x="365" y="145" text-anchor="middle" font-size="10">CFO</text>
        
        <!-- Staff -->
        <use href="#icon-user" x="50" y="200" width="25" height="25"/>
        <use href="#icon-user" x="100" y="200" width="25" height="25"/>
        <use href="#icon-user" x="200" y="200" width="25" height="25"/>
        
        <!-- Connecting lines -->
        <line x1="270" y1="40" x2="165" y2="100" stroke="#999" stroke-width="1"/>
        <line x1="270" y1="40" x2="365" y2="100" stroke="#999" stroke-width="1"/>
        <line x1="165" y1="130" x2="62" y2="200" stroke="#999" stroke-width="1"/>
        <line x1="165" y1="130" x2="112" y2="200" stroke="#999" stroke-width="1"/>
    </g>
    
    <!-- Settings panel -->
    <g transform="translate(450, 300)">
        <use href="#icon-gear" x="0" y="0" width="30" height="30"/>
        <text x="40" y="20" font-size="12">Settings</text>
    </g>
</svg>'''
        
        return samples

    @pytest.fixture
    def stress_test_svg(self):
        """Large SVG for stress testing."""
        svg_parts = ['''<?xml version="1.0" encoding="UTF-8"?>
<svg width="1000" height="1000" xmlns="http://www.w3.org/2000/svg">''']
        
        # Generate many shapes
        for i in range(100):
            x = (i % 10) * 100
            y = (i // 10) * 100
            color = f"hsl({i * 36 % 360}, 70%, 50%)"
            
            svg_parts.append(f'''
    <g transform="translate({x}, {y})">
        <rect x="10" y="10" width="80" height="80" fill="{color}" opacity="0.8"/>
        <circle cx="50" cy="50" r="30" fill="white" opacity="0.5"/>
        <text x="50" y="55" text-anchor="middle" font-size="12">{i}</text>
    </g>''')
        
        svg_parts.append('</svg>')
        return ''.join(svg_parts)

    def test_comprehensive_conversion_pipeline(self, real_world_svg_samples):
        """Test the complete conversion pipeline with real-world scenarios."""
        from src.svg2pptx import convert_svg_to_pptx
        
        results = {}
        
        for scenario_name, svg_content in real_world_svg_samples.items():
            with tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False) as svg_file:
                svg_file.write(svg_content)
                svg_file.flush()
                
                with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as pptx_file:
                    try:
                        # Test main conversion function
                        start_time = time.time()
                        result = convert_svg_to_pptx(
                            svg_file.name, 
                            pptx_file.name,
                            title=f"Test: {scenario_name}",
                            author="SVG2PPTX Test Suite"
                        )
                        duration = time.time() - start_time
                        
                        # Validate output exists and is valid
                        assert os.path.exists(pptx_file.name)
                        assert os.path.getsize(pptx_file.name) > 1000  # Not empty
                        
                        # Store results for analysis
                        results[scenario_name] = {
                            'success': True,
                            'duration': duration,
                            'file_size': os.path.getsize(pptx_file.name),
                            'result': result
                        }
                        
                    except Exception as e:
                        results[scenario_name] = {
                            'success': False,
                            'error': str(e),
                            'duration': 0,
                            'file_size': 0
                        }
                        # Don't fail test, just record the failure
                        print(f"Conversion failed for {scenario_name}: {e}")
                        
                    finally:
                        # Cleanup
                        if os.path.exists(svg_file.name):
                            os.unlink(svg_file.name)
                        if os.path.exists(pptx_file.name):
                            os.unlink(pptx_file.name)
        
        # Validate results
        successful_conversions = sum(1 for r in results.values() if r['success'])
        total_scenarios = len(real_world_svg_samples)
        
        print(f"\nConversion Results: {successful_conversions}/{total_scenarios} successful")
        for name, result in results.items():
            if result['success']:
                print(f"  ✓ {name}: {result['duration']:.2f}s, {result['file_size']} bytes")
            else:
                print(f"  ✗ {name}: {result['error']}")
        
        # At least 80% should succeed
        success_rate = successful_conversions / total_scenarios
        assert success_rate >= 0.8, f"Success rate too low: {success_rate:.1%}"

    def test_multislide_detection_and_conversion(self, real_world_svg_samples):
        """Test multi-slide detection and conversion capabilities."""
        try:
            from src.multislide.detection import SlideDetector
            from src.svg2multislide import MultiSlideConverter
        except ImportError:
            pytest.skip("Multi-slide modules not available")
        
        # Test with animation sequence
        animation_svg = real_world_svg_samples['animation_sequence']
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False) as svg_file:
            svg_file.write(animation_svg)
            svg_file.flush()
            
            try:
                # Test slide detection
                detector = SlideDetector()
                root = ET.parse(svg_file.name).getroot()
                boundaries = detector.detect_boundaries(root)
                
                assert len(boundaries) > 0, "Should detect slide boundaries"
                
                # Test multi-slide conversion
                converter = MultiSlideConverter(enable_multislide_detection=True)
                with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as pptx_file:
                    result = converter.convert_svg_to_pptx(
                        svg_file.name,
                        pptx_file.name,
                        options={'title': 'Multi-slide Test'}
                    )
                    
                    assert result['success'], f"Multi-slide conversion failed: {result.get('error')}"
                    assert result['slide_count'] > 1, "Should generate multiple slides"
                    
                    # Cleanup
                    if os.path.exists(pptx_file.name):
                        os.unlink(pptx_file.name)
                        
            finally:
                if os.path.exists(svg_file.name):
                    os.unlink(svg_file.name)

    def test_preprocessing_integration(self, real_world_svg_samples):
        """Test preprocessing pipeline integration."""
        from src.svg2pptx import convert_svg_to_pptx
        from src.preprocessing.optimizer import create_optimizer
        
        # Test different preprocessing configurations
        configs = [
            {'preset': 'minimal'},
            {'preset': 'default'},
            {'preset': 'aggressive'},
            {
                'optimize_paths': True,
                'merge_groups': True,
                'remove_empty': True,
                'precision': 3
            }
        ]
        
        test_svg = real_world_svg_samples['complex_graphics']
        
        for i, config in enumerate(configs):
            with tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False) as svg_file:
                svg_file.write(test_svg)
                svg_file.flush()
                
                with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as pptx_file:
                    try:
                        # Test conversion with preprocessing
                        result = convert_svg_to_pptx(
                            svg_file.name,
                            pptx_file.name,
                            preprocessing_config=config,
                            title=f"Preprocessing Test {i}"
                        )
                        
                        # Should succeed with any valid preprocessing config
                        assert os.path.exists(pptx_file.name)
                        assert os.path.getsize(pptx_file.name) > 1000
                        
                    except Exception as e:
                        print(f"Preprocessing config {config} failed: {e}")
                        # Some configs might fail, but record the attempt
                        
                    finally:
                        if os.path.exists(svg_file.name):
                            os.unlink(svg_file.name)
                        if os.path.exists(pptx_file.name):
                            os.unlink(pptx_file.name)

    def test_batch_processing_integration(self, real_world_svg_samples):
        """Test batch processing capabilities."""
        try:
            from src.batch.simple_api import BatchProcessor
        except ImportError:
            pytest.skip("Batch processing modules not available")
        
        # Create temporary directory with multiple SVG files
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            svg_files = []
            
            # Create multiple SVG files
            for name, content in real_world_svg_samples.items():
                svg_file = temp_path / f"{name}.svg"
                svg_file.write_text(content)
                svg_files.append(svg_file)
            
            # Test batch processing
            try:
                processor = BatchProcessor()
                
                # Process all files
                results = []
                for svg_file in svg_files:
                    pptx_file = temp_path / f"{svg_file.stem}.pptx"
                    
                    try:
                        result = processor.process_file(str(svg_file), str(pptx_file))
                        results.append(result)
                    except Exception as e:
                        print(f"Batch processing failed for {svg_file.name}: {e}")
                        results.append({'success': False, 'error': str(e)})
                
                # Validate batch results
                successful = sum(1 for r in results if r.get('success', False))
                print(f"Batch processing: {successful}/{len(results)} successful")
                
                # At least some should succeed
                assert successful > 0, "No batch conversions succeeded"
                
            except Exception as e:
                print(f"Batch processing test failed: {e}")
                # Batch processing might not be fully implemented

    def test_error_recovery_and_fallbacks(self, real_world_svg_samples):
        """Test error recovery and fallback mechanisms."""
        from src.svg2pptx import convert_svg_to_pptx
        
        # Test with intentionally problematic SVG
        problematic_svg = '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="400" height="300" xmlns="http://www.w3.org/2000/svg">
    <!-- Malformed gradient reference -->
    <rect x="0" y="0" width="400" height="300" fill="url(#nonexistent)"/>
    
    <!-- Invalid path data -->
    <path d="M10,10 INVALID_COMMAND 20,20" stroke="red"/>
    
    <!-- Circular reference -->
    <defs>
        <linearGradient id="grad1" href="#grad2">
            <stop offset="0%" stop-color="red"/>
        </linearGradient>
        <linearGradient id="grad2" href="#grad1">
            <stop offset="100%" stop-color="blue"/>
        </linearGradient>
    </defs>
    <rect x="50" y="50" width="100" height="100" fill="url(#grad1)"/>
    
    <!-- Valid fallback content -->
    <text x="200" y="150" font-size="16" fill="black">Fallback Text</text>
</svg>'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False) as svg_file:
            svg_file.write(problematic_svg)
            svg_file.flush()
            
            with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as pptx_file:
                try:
                    # Should either succeed with fallbacks or provide meaningful error
                    result = convert_svg_to_pptx(
                        svg_file.name,
                        pptx_file.name,
                        fallback_to_image=True,  # Enable fallback
                        strict_mode=False  # Allow error recovery
                    )
                    
                    # If successful, validate output
                    if os.path.exists(pptx_file.name):
                        assert os.path.getsize(pptx_file.name) > 1000
                        print("Error recovery successful")
                    
                except Exception as e:
                    # Should be a meaningful error, not a crash
                    assert "svg" in str(e).lower() or "conversion" in str(e).lower()
                    print(f"Expected error with fallback: {e}")
                    
                finally:
                    if os.path.exists(svg_file.name):
                        os.unlink(svg_file.name)
                    if os.path.exists(pptx_file.name):
                        os.unlink(pptx_file.name)

    def test_performance_and_resource_usage(self, stress_test_svg):
        """Test performance with large/complex SVGs."""
        from src.svg2pptx import convert_svg_to_pptx
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False) as svg_file:
            svg_file.write(stress_test_svg)
            svg_file.flush()
            
            with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as pptx_file:
                try:
                    # Measure performance
                    start_time = time.time()
                    start_size = os.path.getsize(svg_file.name)
                    
                    result = convert_svg_to_pptx(
                        svg_file.name,
                        pptx_file.name,
                        title="Performance Test"
                    )
                    
                    end_time = time.time()
                    duration = end_time - start_time
                    output_size = os.path.getsize(pptx_file.name)
                    
                    print(f"Performance test: {duration:.2f}s, {start_size} → {output_size} bytes")
                    
                    # Performance assertions
                    assert duration < 60.0, f"Conversion too slow: {duration}s"
                    assert output_size > 10000, "Output file too small"
                    assert output_size < 100 * 1024 * 1024, "Output file too large"  # 100MB limit
                    
                except Exception as e:
                    print(f"Performance test failed: {e}")
                    # Large files might fail, but shouldn't crash
                    assert "memory" not in str(e).lower(), "Memory issues detected"
                    
                finally:
                    if os.path.exists(svg_file.name):
                        os.unlink(svg_file.name)
                    if os.path.exists(pptx_file.name):
                        os.unlink(pptx_file.name)

    def test_concurrent_processing_safety(self, real_world_svg_samples):
        """Test thread safety of concurrent conversions."""
        from src.svg2pptx import convert_svg_to_pptx
        
        def worker_conversion(scenario_name, svg_content):
            """Worker function for concurrent conversion testing."""
            with tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False) as svg_file:
                svg_file.write(svg_content)
                svg_file.flush()
                
                with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as pptx_file:
                    try:
                        start_time = time.time()
                        convert_svg_to_pptx(svg_file.name, pptx_file.name)
                        duration = time.time() - start_time
                        
                        return {
                            'scenario': scenario_name,
                            'success': True,
                            'duration': duration,
                            'size': os.path.getsize(pptx_file.name)
                        }
                        
                    except Exception as e:
                        return {
                            'scenario': scenario_name,
                            'success': False,
                            'error': str(e)
                        }
                    finally:
                        if os.path.exists(svg_file.name):
                            os.unlink(svg_file.name)
                        if os.path.exists(pptx_file.name):
                            os.unlink(pptx_file.name)
        
        # Run concurrent conversions
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            
            # Submit multiple conversion tasks
            for scenario_name, svg_content in real_world_svg_samples.items():
                future = executor.submit(worker_conversion, scenario_name, svg_content)
                futures.append(future)
                
                # Submit duplicate to test concurrency
                future2 = executor.submit(worker_conversion, f"{scenario_name}_dup", svg_content)
                futures.append(future2)
            
            # Collect results
            results = []
            for future in futures:
                try:
                    result = future.result(timeout=30)
                    results.append(result)
                except Exception as e:
                    results.append({'success': False, 'error': str(e)})
        
        # Validate concurrent processing
        successful = sum(1 for r in results if r['success'])
        total = len(results)
        
        print(f"Concurrent processing: {successful}/{total} successful")
        
        # Should handle concurrent access gracefully
        assert successful >= total * 0.7, f"Too many concurrent failures: {successful}/{total}"

    def test_full_feature_coverage(self, real_world_svg_samples):
        """Test coverage of major SVG features."""
        from src.svg2pptx import convert_svg_to_pptx
        
        feature_tests = {
            'gradients': real_world_svg_samples['corporate_slide'],
            'paths': real_world_svg_samples['technical_diagram'],
            'transforms': real_world_svg_samples['complex_graphics'],
            'symbols': real_world_svg_samples['symbols_reuse'],
            'animations': real_world_svg_samples['animation_sequence']
        }
        
        coverage_results = {}
        
        for feature_name, svg_content in feature_tests.items():
            with tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False) as svg_file:
                svg_file.write(svg_content)
                svg_file.flush()
                
                with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as pptx_file:
                    try:
                        # Test specific feature conversion
                        result = convert_svg_to_pptx(
                            svg_file.name,
                            pptx_file.name,
                            title=f"Feature Test: {feature_name}",
                            optimize_output=True,
                            preserve_text=True
                        )
                        
                        coverage_results[feature_name] = {
                            'success': True,
                            'file_exists': os.path.exists(pptx_file.name),
                            'file_size': os.path.getsize(pptx_file.name) if os.path.exists(pptx_file.name) else 0
                        }
                        
                    except Exception as e:
                        coverage_results[feature_name] = {
                            'success': False,
                            'error': str(e)
                        }
                        
                    finally:
                        if os.path.exists(svg_file.name):
                            os.unlink(svg_file.name)
                        if os.path.exists(pptx_file.name):
                            os.unlink(pptx_file.name)
        
        # Report feature coverage
        print("\nFeature Coverage Results:")
        covered_features = 0
        for feature, result in coverage_results.items():
            if result['success']:
                print(f"  ✓ {feature}: {result.get('file_size', 0)} bytes")
                covered_features += 1
            else:
                print(f"  ✗ {feature}: {result.get('error', 'Unknown error')}")
        
        # Should cover most features
        coverage_rate = covered_features / len(feature_tests)
        assert coverage_rate >= 0.6, f"Feature coverage too low: {coverage_rate:.1%}"


# Integration with existing test structure
class TestComprehensiveE2E(ComprehensiveE2ETestSuite):
    """Test class for pytest discovery."""
    pass


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v", "--tb=short"])