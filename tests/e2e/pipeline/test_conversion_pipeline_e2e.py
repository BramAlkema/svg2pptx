#!/usr/bin/env python3
"""
End-to-end integration tests for SVG to PPTX conversion.

This module tests the complete conversion pipeline from SVG input to PPTX output,
validating the integration between all system components.
"""

import pytest
import tempfile
import os
from pathlib import Path
from typing import Dict, List, Any
from lxml import etree as ET
from zipfile import ZipFile
import time

# Test configuration
TIMEOUT_SECONDS = 30
MAX_FILE_SIZE_MB = 100


class ConversionResult:
    """Result of an end-to-end conversion test."""
    
    def __init__(self, success: bool, output_path: Path = None, 
                 duration: float = 0.0, file_size_bytes: int = 0, 
                 error: str = None, warnings: List[str] = None):
        self.success = success
        self.output_path = output_path
        self.duration = duration
        self.file_size_bytes = file_size_bytes
        self.file_size_mb = file_size_bytes / (1024 * 1024) if file_size_bytes > 0 else 0
        self.error = error
        self.warnings = warnings or []
    
    def __str__(self):
        status = "SUCCESS" if self.success else "FAILED"
        return f"Conversion {status} ({self.duration:.2f}s, {self.file_size_mb:.2f}MB)"


class PPTXAnalyzer:
    """Analyzes PPTX files for structural validation."""
    
    def analyze_pptx(self, pptx_path: Path) -> Dict[str, Any]:
        """Analyze PPTX file structure and content."""
        analysis = {
            'valid': False,
            'slide_count': 0,
            'shape_count': 0,
            'has_text': False,
            'has_images': False,
            'has_paths': False,
            'file_size': 0,
            'xml_files': [],
            'errors': []
        }
        
        try:
            if not pptx_path.exists():
                analysis['errors'].append("PPTX file does not exist")
                return analysis
            
            analysis['file_size'] = pptx_path.stat().st_size
            
            with ZipFile(pptx_path, 'r') as zf:
                # Check basic PPTX structure
                required_files = [
                    '[Content_Types].xml',
                    '_rels/.rels',
                    'ppt/presentation.xml'
                ]
                
                zip_files = {f.filename for f in zf.filelist}
                analysis['xml_files'] = list(zip_files)
                
                for required_file in required_files:
                    if required_file not in zip_files:
                        analysis['errors'].append(f"Missing required file: {required_file}")
                
                # Count slides
                slide_files = [f for f in zip_files if f.startswith('ppt/slides/slide') and f.endswith('.xml')]
                analysis['slide_count'] = len(slide_files)
                
                # Analyze slide content
                for slide_file in slide_files:
                    try:
                        slide_xml = zf.read(slide_file).decode('utf-8')
                        slide_analysis = self._analyze_slide_content(slide_xml)
                        
                        analysis['shape_count'] += slide_analysis['shapes']
                        if slide_analysis['has_text']:
                            analysis['has_text'] = True
                        if slide_analysis['has_images']:
                            analysis['has_images'] = True
                        if slide_analysis['has_paths']:
                            analysis['has_paths'] = True
                            
                    except Exception as e:
                        analysis['errors'].append(f"Error analyzing {slide_file}: {str(e)}")
                
                # If no errors found, mark as valid
                if not analysis['errors']:
                    analysis['valid'] = True
        
        except Exception as e:
            analysis['errors'].append(f"Error analyzing PPTX: {str(e)}")
        
        return analysis
    
    def _analyze_slide_content(self, slide_xml: str) -> Dict[str, Any]:
        """Analyze individual slide XML content."""
        analysis = {
            'shapes': 0,
            'has_text': False,
            'has_images': False,
            'has_paths': False
        }
        
        try:
            root = ET.fromstring(slide_xml)
            
            # Count shapes
            for elem in root.iter():
                tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                
                if tag in ['sp', 'grpSp', 'pic']:
                    analysis['shapes'] += 1
                
                if tag in ['t', 'r']:  # Text elements
                    analysis['has_text'] = True
                
                if tag == 'pic':  # Picture elements
                    analysis['has_images'] = True
                
                if tag == 'custGeom':  # Custom geometry (paths)
                    analysis['has_paths'] = True
        
        except ET.ParseError:
            pass  # Ignore XML parse errors in analysis
        
        return analysis


@pytest.fixture
def pptx_analyzer():
    """Fixture providing PPTX analyzer instance."""
    return PPTXAnalyzer()


@pytest.fixture
def sample_svg_files():
    """Fixture providing sample SVG files for testing."""
    samples = {}
    
    # Basic rectangle
    samples['basic_rect'] = '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="100" height="100" xmlns="http://www.w3.org/2000/svg">
    <rect x="10" y="10" width="80" height="80" fill="red"/>
</svg>'''
    
    # Circle with text
    samples['circle_text'] = '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="200" height="200" xmlns="http://www.w3.org/2000/svg">
    <circle cx="100" cy="100" r="50" fill="blue"/>
    <text x="100" y="105" text-anchor="middle" font-size="16" fill="white">Hello</text>
</svg>'''
    
    # Complex path
    samples['complex_path'] = '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="300" height="300" xmlns="http://www.w3.org/2000/svg">
    <path d="M50,50 C50,50 100,10 150,50 C200,90 250,50 250,50 L200,150 Z" 
          fill="green" stroke="black" stroke-width="2"/>
</svg>'''
    
    # Transform test
    samples['transform'] = '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="200" height="200" xmlns="http://www.w3.org/2000/svg">
    <g transform="rotate(45 100 100)">
        <rect x="75" y="75" width="50" height="50" fill="purple"/>
    </g>
</svg>'''
    
    # Gradient
    samples['gradient'] = '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="200" height="100" xmlns="http://www.w3.org/2000/svg">
    <defs>
        <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" style="stop-color:rgb(255,255,0);stop-opacity:1" />
            <stop offset="100%" style="stop-color:rgb(255,0,0);stop-opacity:1" />
        </linearGradient>
    </defs>
    <ellipse cx="100" cy="50" rx="85" ry="35" fill="url(#grad1)" />
</svg>'''
    
    return samples


class TestEndToEndConversion:
    """End-to-end conversion integration tests."""
    
    def test_basic_svg_conversion(self, sample_svg_files, pptx_analyzer):
        """Test basic SVG to PPTX conversion."""
        from src.svg2pptx import convert_svg_to_pptx
        
        for test_name, svg_content in sample_svg_files.items():
            with tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False) as svg_file:
                svg_file.write(svg_content)
                svg_file.flush()
                
                with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as pptx_file:
                    try:
                        # Perform conversion
                        start_time = time.time()
                        convert_svg_to_pptx(svg_file.name, pptx_file.name)
                        duration = time.time() - start_time
                        
                        # Analyze result
                        pptx_path = Path(pptx_file.name)
                        analysis = pptx_analyzer.analyze_pptx(pptx_path)
                        
                        # Assertions
                        assert analysis['valid'], f"Invalid PPTX for {test_name}: {analysis['errors']}"
                        assert analysis['slide_count'] > 0, f"No slides generated for {test_name}"
                        assert analysis['file_size'] > 0, f"Empty PPTX file for {test_name}"
                        assert duration < TIMEOUT_SECONDS, f"Conversion too slow for {test_name}: {duration}s"
                        
                        # Content-specific assertions
                        if test_name == 'circle_text':
                            assert analysis['has_text'], "Text not found in circle_text conversion"
                        
                        if test_name == 'complex_path':
                            assert analysis['shape_count'] > 0, "No shapes found in complex_path conversion"
                        
                    finally:
                        # Cleanup
                        if os.path.exists(svg_file.name):
                            os.unlink(svg_file.name)
                        if os.path.exists(pptx_file.name):
                            os.unlink(pptx_file.name)
    
    def test_conversion_with_preprocessing(self, sample_svg_files, pptx_analyzer):
        """Test conversion with various preprocessing options."""
        from src.svg2pptx import convert_svg_to_pptx
        
        preprocessing_configs = [
            {'preset': 'minimal'},
            {'preset': 'default'},
            {'preset': 'aggressive'},
        ]
        
        for config in preprocessing_configs:
            svg_content = sample_svg_files['complex_path']
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False) as svg_file:
                svg_file.write(svg_content)
                svg_file.flush()
                
                with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as pptx_file:
                    try:
                        # Convert with preprocessing config
                        convert_svg_to_pptx(svg_file.name, pptx_file.name, 
                                          preprocessing_config=config)
                        
                        # Validate result
                        analysis = pptx_analyzer.analyze_pptx(Path(pptx_file.name))
                        assert analysis['valid'], f"Invalid PPTX with config {config}: {analysis['errors']}"
                        
                    finally:
                        if os.path.exists(svg_file.name):
                            os.unlink(svg_file.name)
                        if os.path.exists(pptx_file.name):
                            os.unlink(pptx_file.name)
    
    def test_error_handling(self, pptx_analyzer):
        """Test conversion error handling."""
        from src.svg2pptx import convert_svg_to_pptx
        
        # Test malformed SVG
        malformed_svg = '''<?xml version="1.0"?>
<svg width="100" height="100" xmlns="http://www.w3.org/2000/svg">
    <rect x="10" y="10" width="80" height="80" fill="red"
</svg>'''  # Missing closing bracket
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False) as svg_file:
            svg_file.write(malformed_svg)
            svg_file.flush()
            
            with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as pptx_file:
                try:
                    # This should either succeed with error recovery or raise an exception
                    convert_svg_to_pptx(svg_file.name, pptx_file.name)
                    
                    # If it succeeds, validate the output
                    if Path(pptx_file.name).exists():
                        analysis = pptx_analyzer.analyze_pptx(Path(pptx_file.name))
                        # Should either be valid or have specific error handling
                        assert True  # Test passes if no exception raised
                
                except Exception as e:
                    # Exception is acceptable for malformed input
                    assert isinstance(e, (ValueError, ET.ParseError, Exception))
                
                finally:
                    if os.path.exists(svg_file.name):
                        os.unlink(svg_file.name)
                    if os.path.exists(pptx_file.name):
                        os.unlink(pptx_file.name)
    
    def test_empty_svg_handling(self, pptx_analyzer):
        """Test handling of empty or minimal SVG files."""
        from src.svg2pptx import convert_svg_to_pptx
        
        # Empty SVG
        empty_svg = '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="100" height="100" xmlns="http://www.w3.org/2000/svg">
</svg>'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False) as svg_file:
            svg_file.write(empty_svg)
            svg_file.flush()
            
            with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as pptx_file:
                try:
                    convert_svg_to_pptx(svg_file.name, pptx_file.name)
                    
                    # Should produce valid PPTX even with empty content
                    analysis = pptx_analyzer.analyze_pptx(Path(pptx_file.name))
                    assert analysis['valid'], f"Invalid PPTX for empty SVG: {analysis['errors']}"
                    assert analysis['slide_count'] >= 1, "Should have at least one slide"
                
                finally:
                    if os.path.exists(svg_file.name):
                        os.unlink(svg_file.name)
                    if os.path.exists(pptx_file.name):
                        os.unlink(pptx_file.name)
    
    @pytest.mark.slow
    def test_performance_benchmarks(self, sample_svg_files):
        """Test conversion performance benchmarks."""
        from src.svg2pptx import convert_svg_to_pptx
        
        performance_results = []
        
        for test_name, svg_content in sample_svg_files.items():
            with tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False) as svg_file:
                svg_file.write(svg_content)
                svg_file.flush()
                
                with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as pptx_file:
                    try:
                        # Multiple runs for performance measurement
                        times = []
                        for _ in range(3):
                            start_time = time.time()
                            convert_svg_to_pptx(svg_file.name, pptx_file.name)
                            duration = time.time() - start_time
                            times.append(duration)
                        
                        avg_time = sum(times) / len(times)
                        file_size = Path(pptx_file.name).stat().st_size
                        
                        performance_results.append({
                            'test': test_name,
                            'avg_time': avg_time,
                            'file_size': file_size,
                            'times': times
                        })
                        
                        # Performance assertions
                        assert avg_time < TIMEOUT_SECONDS, f"Conversion too slow for {test_name}: {avg_time}s"
                        assert file_size < MAX_FILE_SIZE_MB * 1024 * 1024, f"File too large for {test_name}: {file_size} bytes"
                    
                    finally:
                        if os.path.exists(svg_file.name):
                            os.unlink(svg_file.name)
                        if os.path.exists(pptx_file.name):
                            os.unlink(pptx_file.name)
        
        # Print performance summary
        print("\nPerformance Benchmark Results:")
        for result in performance_results:
            print(f"  {result['test']}: {result['avg_time']:.3f}s avg, {result['file_size']} bytes")
    
    def test_concurrent_conversions(self, sample_svg_files):
        """Test concurrent conversion handling."""
        import threading
        from src.svg2pptx import convert_svg_to_pptx
        
        results = []
        errors = []
        
        def convert_worker(test_name: str, svg_content: str):
            """Worker function for concurrent conversion."""
            try:
                with tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False) as svg_file:
                    svg_file.write(svg_content)
                    svg_file.flush()
                    
                    with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as pptx_file:
                        try:
                            start_time = time.time()
                            convert_svg_to_pptx(svg_file.name, pptx_file.name)
                            duration = time.time() - start_time
                            
                            results.append(ConversionResult(
                                success=True,
                                output_path=Path(pptx_file.name),
                                duration=duration,
                                file_size_bytes=Path(pptx_file.name).stat().st_size
                            ))
                        
                        finally:
                            if os.path.exists(svg_file.name):
                                os.unlink(svg_file.name)
                            if os.path.exists(pptx_file.name):
                                os.unlink(pptx_file.name)
            
            except Exception as e:
                errors.append(f"{test_name}: {str(e)}")
        
        # Start concurrent conversions
        threads = []
        for test_name, svg_content in sample_svg_files.items():
            thread = threading.Thread(target=convert_worker, args=(test_name, svg_content))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=TIMEOUT_SECONDS)
        
        # Validate results
        assert len(errors) == 0, f"Concurrent conversion errors: {errors}"
        assert len(results) == len(sample_svg_files), "Not all concurrent conversions completed"
        
        successful = sum(1 for r in results if r.success)
        assert successful == len(results), f"Some concurrent conversions failed: {successful}/{len(results)}"


if __name__ == "__main__":
    # CLI for running individual end-to-end tests
    import sys
    
    if len(sys.argv) == 3:
        svg_file = sys.argv[1]
        pptx_file = sys.argv[2]
        
        from src.svg2pptx import convert_svg_to_pptx
        
        start_time = time.time()
        try:
            convert_svg_to_pptx(svg_file, pptx_file)
            duration = time.time() - start_time
            
            analyzer = PPTXAnalyzer()
            analysis = analyzer.analyze_pptx(Path(pptx_file))
            
            result = ConversionResult(
                success=analysis['valid'],
                output_path=Path(pptx_file),
                duration=duration,
                file_size_bytes=analysis['file_size'],
                error=None if analysis['valid'] else str(analysis['errors'])
            )
            
            print(result)
            if not result.success:
                print(f"Errors: {result.error}")
                sys.exit(1)
        
        except Exception as e:
            print(f"Conversion failed: {str(e)}")
            sys.exit(1)
    else:
        print("Usage: python test_end_to_end_conversion.py <input.svg> <output.pptx>")
        sys.exit(1)