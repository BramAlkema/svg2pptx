"""
Converter-Specific E2E Tests

Tests designed to specifically trigger individual converter modules
with complex SVG features that require their functionality.
"""

import pytest
import tempfile
import os
from pathlib import Path
import logging
from src.svg2pptx import convert_svg_to_pptx
from tests.integration.test_end_to_end_conversion import PPTXAnalyzer

logger = logging.getLogger(__name__)

class TestConverterSpecificE2E:
    """E2E tests targeting specific converter modules."""
    
    @pytest.fixture
    def complex_svg_samples(self):
        """Complex SVG samples designed to trigger specific converters."""
        return {
            # Complex paths to trigger paths.py converter
            'complex_paths': '''<?xml version="1.0"?>
<svg width="400" height="300" xmlns="http://www.w3.org/2000/svg">
    <path d="M150,50 C150,50 300,50 300,150 C300,250 150,250 150,150 Z" 
          fill="blue" stroke="red" stroke-width="2"/>
    <path d="M50,50 Q100,25 150,50 T250,50" 
          fill="none" stroke="green" stroke-width="3"/>
    <path d="M50,200 L150,100 L250,200 L200,250 L100,250 Z" 
          fill="orange" opacity="0.8"/>
    <path d="M300,200 A50,25 0 0,1 350,250" 
          fill="none" stroke="purple" stroke-width="4"/>
</svg>''',
            
            # Complex shapes to trigger shapes.py converter
            'complex_shapes': '''<?xml version="1.0"?>
<svg width="400" height="300" xmlns="http://www.w3.org/2000/svg">
    <circle cx="100" cy="100" r="50" fill="red" opacity="0.7"/>
    <ellipse cx="250" cy="100" rx="60" ry="30" fill="blue" stroke="black" stroke-width="2"/>
    <rect x="50" y="200" width="100" height="60" rx="10" ry="10" fill="green"/>
    <polygon points="200,200 250,180 300,200 280,250 220,250" fill="yellow" stroke="orange" stroke-width="3"/>
    <line x1="10" y1="10" x2="390" y2="290" stroke="purple" stroke-width="2"/>
    <polyline points="320,50 340,60 360,40 380,70" fill="none" stroke="brown" stroke-width="2"/>
</svg>''',
            
            # Gradients to trigger gradients.py converter
            'gradients_and_patterns': '''<?xml version="1.0"?>
<svg width="400" height="300" xmlns="http://www.w3.org/2000/svg">
    <defs>
        <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" style="stop-color:rgb(255,255,0);stop-opacity:1" />
            <stop offset="100%" style="stop-color:rgb(255,0,0);stop-opacity:1" />
        </linearGradient>
        <radialGradient id="grad2" cx="50%" cy="50%" r="50%">
            <stop offset="0%" style="stop-color:rgb(255,255,255);stop-opacity:0" />
            <stop offset="100%" style="stop-color:rgb(0,0,255);stop-opacity:1" />
        </radialGradient>
        <pattern id="stripe" patternUnits="userSpaceOnUse" width="10" height="10">
            <rect width="5" height="10" fill="red"/>
            <rect x="5" width="5" height="10" fill="white"/>
        </pattern>
    </defs>
    <rect x="50" y="50" width="100" height="80" fill="url(#grad1)"/>
    <circle cx="250" cy="100" r="60" fill="url(#grad2)"/>
    <rect x="150" y="200" width="100" height="60" fill="url(#stripe)"/>
</svg>''',
            
            # Text elements to trigger text.py converter
            'text_elements': '''<?xml version="1.0"?>
<svg width="400" height="300" xmlns="http://www.w3.org/2000/svg">
    <text x="50" y="50" font-family="Arial" font-size="20" fill="black">Simple Text</text>
    <text x="50" y="100" font-family="Times" font-size="16" font-weight="bold" fill="blue">Bold Text</text>
    <text x="50" y="150" font-family="Helvetica" font-size="14" font-style="italic" fill="red">Italic Text</text>
    <text x="50" y="200" font-family="Courier" font-size="12" text-decoration="underline" fill="green">
        <tspan x="50" dy="0">Multi-line</tspan>
        <tspan x="50" dy="20">Text Element</tspan>
    </text>
    <text x="200" y="100" transform="rotate(45 200,100)" font-size="18" fill="purple">Rotated Text</text>
</svg>''',
            
            # Complex transforms to trigger transforms.py converter
            'transforms': '''<?xml version="1.0"?>
<svg width="400" height="300" xmlns="http://www.w3.org/2000/svg">
    <rect x="50" y="50" width="50" height="50" fill="red" transform="translate(100,50)"/>
    <rect x="50" y="50" width="50" height="50" fill="blue" transform="rotate(45 75,75)"/>
    <rect x="50" y="50" width="50" height="50" fill="green" transform="scale(1.5,0.5)"/>
    <rect x="50" y="50" width="50" height="50" fill="yellow" transform="skewX(30)"/>
    <rect x="50" y="50" width="50" height="50" fill="orange" transform="matrix(1,0.2,0.2,1,0,0)"/>
    <g transform="translate(200,150) rotate(30) scale(1.2)">
        <circle cx="0" cy="0" r="30" fill="purple"/>
        <rect x="-10" y="-10" width="20" height="20" fill="white"/>
    </g>
</svg>''',
            
            # Groups and nested elements to trigger groups.py converter
            'nested_groups': '''<?xml version="1.0"?>
<svg width="400" height="300" xmlns="http://www.w3.org/2000/svg">
    <g id="group1" fill="red" stroke="black" stroke-width="2">
        <rect x="50" y="50" width="50" height="50"/>
        <circle cx="125" cy="75" r="25"/>
    </g>
    <g id="group2" transform="translate(150,0)" opacity="0.8">
        <g id="nested" fill="blue" transform="rotate(15)">
            <rect x="50" y="50" width="40" height="60"/>
            <ellipse cx="70" cy="80" rx="20" ry="30"/>
        </g>
    </g>
    <g id="group3" clip-path="circle(50px at 300px 150px)">
        <rect x="250" y="100" width="100" height="100" fill="green"/>
        <circle cx="300" cy="150" r="60" fill="yellow"/>
    </g>
</svg>''',
            
            # Filters and effects to trigger filters.py converter
            'filters_effects': '''<?xml version="1.0"?>
<svg width="400" height="300" xmlns="http://www.w3.org/2000/svg">
    <defs>
        <filter id="blur" x="0" y="0">
            <feGaussianBlur in="SourceGraphic" stdDeviation="3"/>
        </filter>
        <filter id="shadow" x="0" y="0" width="200%" height="200%">
            <feOffset result="offOut" in="SourceGraphic" dx="20" dy="20"/>
            <feColorMatrix result="matrixOut" in="offOut" type="matrix" 
                           values="0.2 0 0 0 0 0 0.2 0 0 0 0 0 0.2 0 0 0 0 0 1 0"/>
            <feMerge>
                <feMergeNode in="matrixOut"/>
                <feMergeNode in="SourceGraphic"/>
            </feMerge>
        </filter>
    </defs>
    <rect x="50" y="50" width="80" height="60" fill="red" filter="url(#blur)"/>
    <circle cx="250" cy="100" r="40" fill="blue" filter="url(#shadow)"/>
</svg>''',
            
            # Masking to trigger masking.py converter
            'masking_clipping': '''<?xml version="1.0"?>
<svg width="400" height="300" xmlns="http://www.w3.org/2000/svg">
    <defs>
        <mask id="mask1">
            <rect x="0" y="0" width="200" height="150" fill="white"/>
            <circle cx="100" cy="75" r="50" fill="black"/>
        </mask>
        <clipPath id="clip1">
            <circle cx="300" cy="150" r="60"/>
        </clipPath>
    </defs>
    <rect x="0" y="0" width="200" height="150" fill="red" mask="url(#mask1)"/>
    <rect x="240" y="90" width="120" height="120" fill="blue" clip-path="url(#clip1)"/>
</svg>''',
            
            # Markers to trigger markers.py converter
            'markers_arrows': '''<?xml version="1.0"?>
<svg width="400" height="300" xmlns="http://www.w3.org/2000/svg">
    <defs>
        <marker id="arrow" markerWidth="10" markerHeight="10" refX="9" refY="3" 
                orient="auto" markerUnits="strokeWidth">
            <path d="M0,0 L0,6 L9,3 z" fill="black"/>
        </marker>
        <marker id="dot" markerWidth="5" markerHeight="5" refX="2.5" refY="2.5">
            <circle cx="2.5" cy="2.5" r="2" fill="red"/>
        </marker>
    </defs>
    <line x1="50" y1="50" x2="200" y2="100" stroke="black" stroke-width="2" 
          marker-end="url(#arrow)"/>
    <polyline points="50,150 100,120 150,180 200,140" fill="none" stroke="blue" 
              stroke-width="2" marker-start="url(#dot)" marker-mid="url(#dot)" marker-end="url(#arrow)"/>
    <path d="M250,50 Q300,100 350,50" fill="none" stroke="green" stroke-width="3" 
          marker-end="url(#arrow)"/>
</svg>''',
            
            # Animations to trigger animations.py converter  
            'animations': '''<?xml version="1.0"?>
<svg width="400" height="300" xmlns="http://www.w3.org/2000/svg">
    <rect x="50" y="50" width="50" height="50" fill="red">
        <animateTransform attributeName="transform" type="translate" 
                          values="0,0; 100,0; 100,100; 0,100; 0,0" dur="5s" repeatCount="indefinite"/>
    </rect>
    <circle cx="200" cy="100" r="20" fill="blue">
        <animate attributeName="r" values="20;40;20" dur="2s" repeatCount="indefinite"/>
        <animate attributeName="fill" values="blue;red;blue" dur="2s" repeatCount="indefinite"/>
    </circle>
    <text x="300" y="150" font-size="20" fill="green">Fade
        <animate attributeName="opacity" values="1;0;1" dur="3s" repeatCount="indefinite"/>
    </text>
</svg>'''
        }
    
    @pytest.mark.converter
    def test_paths_converter_coverage(self, complex_svg_samples):
        """Test complex paths to ensure paths.py converter is invoked."""
        svg_content = complex_svg_samples['complex_paths']
        
        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as temp_file:
            try:
                result_path = convert_svg_to_pptx(svg_content, temp_file.name)
                assert os.path.exists(result_path)
                
                # Validate PPTX structure
                analyzer = PPTXAnalyzer()
                slides = analyzer.analyze_pptx(result_path)
                assert len(slides) >= 1
                
                # Check that conversion succeeded (basic validation)
                assert os.path.getsize(result_path) > 20000  # Reasonable PPTX size
                
                logger.info(f"Complex paths conversion successful: {os.path.getsize(result_path)} bytes")
                
            finally:
                if os.path.exists(temp_file.name):
                    os.unlink(temp_file.name)
    
    @pytest.mark.converter
    def test_shapes_converter_coverage(self, complex_svg_samples):
        """Test complex shapes to ensure shapes.py converter is invoked."""
        svg_content = complex_svg_samples['complex_shapes']
        
        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as temp_file:
            try:
                result_path = convert_svg_to_pptx(svg_content, temp_file.name)
                assert os.path.exists(result_path)
                
                # Validate PPTX structure
                analyzer = PPTXAnalyzer()
                slides = analyzer.analyze_pptx(result_path)
                assert len(slides) >= 1
                
                logger.info(f"Complex shapes conversion successful: {os.path.getsize(result_path)} bytes")
                
            finally:
                if os.path.exists(temp_file.name):
                    os.unlink(temp_file.name)
    
    @pytest.mark.converter
    def test_gradients_converter_coverage(self, complex_svg_samples):
        """Test gradients and patterns to ensure gradients.py converter is invoked."""
        svg_content = complex_svg_samples['gradients_and_patterns']
        
        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as temp_file:
            try:
                result_path = convert_svg_to_pptx(svg_content, temp_file.name)
                assert os.path.exists(result_path)
                
                analyzer = PPTXAnalyzer()
                slides = analyzer.analyze_pptx(result_path)
                assert len(slides) >= 1
                
                logger.info(f"Gradients conversion successful: {os.path.getsize(result_path)} bytes")
                
            finally:
                if os.path.exists(temp_file.name):
                    os.unlink(temp_file.name)
    
    @pytest.mark.converter 
    def test_text_converter_coverage(self, complex_svg_samples):
        """Test text elements to ensure text.py converter is invoked."""
        svg_content = complex_svg_samples['text_elements']
        
        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as temp_file:
            try:
                result_path = convert_svg_to_pptx(svg_content, temp_file.name)
                assert os.path.exists(result_path)
                
                analyzer = PPTXAnalyzer()
                slides = analyzer.analyze_pptx(result_path)
                assert len(slides) >= 1
                
                logger.info(f"Text conversion successful: {os.path.getsize(result_path)} bytes")
                
            finally:
                if os.path.exists(temp_file.name):
                    os.unlink(temp_file.name)
    
    @pytest.mark.converter
    def test_transforms_converter_coverage(self, complex_svg_samples):
        """Test transforms to ensure transforms.py converter is invoked."""
        svg_content = complex_svg_samples['transforms']
        
        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as temp_file:
            try:
                result_path = convert_svg_to_pptx(svg_content, temp_file.name)
                assert os.path.exists(result_path)
                
                analyzer = PPTXAnalyzer()
                slides = analyzer.analyze_pptx(result_path)
                assert len(slides) >= 1
                
                logger.info(f"Transforms conversion successful: {os.path.getsize(result_path)} bytes")
                
            finally:
                if os.path.exists(temp_file.name):
                    os.unlink(temp_file.name)
    
    @pytest.mark.converter
    def test_groups_converter_coverage(self, complex_svg_samples):
        """Test nested groups to ensure groups.py converter is invoked."""
        svg_content = complex_svg_samples['nested_groups']
        
        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as temp_file:
            try:
                result_path = convert_svg_to_pptx(svg_content, temp_file.name)
                assert os.path.exists(result_path)
                
                analyzer = PPTXAnalyzer()
                slides = analyzer.analyze_pptx(result_path)
                assert len(slides) >= 1
                
                logger.info(f"Groups conversion successful: {os.path.getsize(result_path)} bytes")
                
            finally:
                if os.path.exists(temp_file.name):
                    os.unlink(temp_file.name)
    
    @pytest.mark.converter
    def test_filters_converter_coverage(self, complex_svg_samples):
        """Test filters and effects to ensure filters.py converter is invoked."""
        svg_content = complex_svg_samples['filters_effects']
        
        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as temp_file:
            try:
                result_path = convert_svg_to_pptx(svg_content, temp_file.name)
                assert os.path.exists(result_path)
                
                analyzer = PPTXAnalyzer()
                slides = analyzer.analyze_pptx(result_path)
                assert len(slides) >= 1
                
                logger.info(f"Filters conversion successful: {os.path.getsize(result_path)} bytes")
                
            finally:
                if os.path.exists(temp_file.name):
                    os.unlink(temp_file.name)
    
    @pytest.mark.converter
    def test_masking_converter_coverage(self, complex_svg_samples):
        """Test masking and clipping to ensure masking.py converter is invoked."""
        svg_content = complex_svg_samples['masking_clipping']
        
        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as temp_file:
            try:
                result_path = convert_svg_to_pptx(svg_content, temp_file.name)
                assert os.path.exists(result_path)
                
                analyzer = PPTXAnalyzer()
                slides = analyzer.analyze_pptx(result_path)
                assert len(slides) >= 1
                
                logger.info(f"Masking conversion successful: {os.path.getsize(result_path)} bytes")
                
            finally:
                if os.path.exists(temp_file.name):
                    os.unlink(temp_file.name)
    
    @pytest.mark.converter
    def test_markers_converter_coverage(self, complex_svg_samples):
        """Test markers and arrows to ensure markers.py converter is invoked."""
        svg_content = complex_svg_samples['markers_arrows']
        
        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as temp_file:
            try:
                result_path = convert_svg_to_pptx(svg_content, temp_file.name)
                assert os.path.exists(result_path)
                
                analyzer = PPTXAnalyzer()
                slides = analyzer.analyze_pptx(result_path)
                assert len(slides) >= 1
                
                logger.info(f"Markers conversion successful: {os.path.getsize(result_path)} bytes")
                
            finally:
                if os.path.exists(temp_file.name):
                    os.unlink(temp_file.name)
    
    @pytest.mark.converter
    def test_animations_converter_coverage(self, complex_svg_samples):
        """Test animations to ensure animations.py converter is invoked."""
        svg_content = complex_svg_samples['animations']
        
        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as temp_file:
            try:
                result_path = convert_svg_to_pptx(svg_content, temp_file.name)
                assert os.path.exists(result_path)
                
                analyzer = PPTXAnalyzer()
                slides = analyzer.analyze_pptx(result_path)
                assert len(slides) >= 1
                
                logger.info(f"Animations conversion successful: {os.path.getsize(result_path)} bytes")
                
            finally:
                if os.path.exists(temp_file.name):
                    os.unlink(temp_file.name)
    
    @pytest.mark.e2e
    def test_all_converter_combinations(self, complex_svg_samples):
        """Test combined SVG features to trigger multiple converters simultaneously."""
        # Combine multiple features in one SVG
        combined_svg = '''<?xml version="1.0"?>
<svg width="800" height="600" xmlns="http://www.w3.org/2000/svg">
    <defs>
        <linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" style="stop-color:rgb(255,255,0);stop-opacity:1" />
            <stop offset="100%" style="stop-color:rgb(255,0,0);stop-opacity:1" />
        </linearGradient>
        <marker id="arrow" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
            <path d="M0,0 L0,6 L9,3 z" fill="black"/>
        </marker>
        <filter id="shadow" x="0" y="0" width="200%" height="200%">
            <feDropShadow dx="2" dy="2" stdDeviation="3"/>
        </filter>
    </defs>
    
    <!-- Group with transforms -->
    <g transform="translate(100,50) rotate(15)">
        <!-- Shapes with gradients -->
        <rect x="0" y="0" width="100" height="60" fill="url(#grad)" filter="url(#shadow)"/>
        <circle cx="50" cy="80" r="30" fill="blue" opacity="0.8"/>
    </g>
    
    <!-- Complex paths with markers -->
    <path d="M200,200 Q300,150 400,200 T600,200" fill="none" stroke="green" 
          stroke-width="3" marker-end="url(#arrow)"/>
    
    <!-- Text with transforms -->
    <text x="300" y="300" font-size="24" fill="purple" transform="rotate(30 300,300)">
        Complex SVG Test
        <animate attributeName="opacity" values="1;0.5;1" dur="2s" repeatCount="indefinite"/>
    </text>
    
    <!-- Nested groups with different features -->
    <g id="complex-group" transform="translate(500,400)">
        <polygon points="0,0 40,20 20,60 -20,60 -40,20" fill="orange" stroke="black"/>
        <ellipse cx="0" cy="0" rx="50" ry="25" fill="none" stroke="red" stroke-width="2"/>
    </g>
</svg>'''
        
        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as temp_file:
            try:
                result_path = convert_svg_to_pptx(combined_svg, temp_file.name)
                assert os.path.exists(result_path)
                
                analyzer = PPTXAnalyzer()
                slides = analyzer.analyze_pptx(result_path)
                assert len(slides) >= 1
                
                # Should produce a substantial PPTX with multiple features
                file_size = os.path.getsize(result_path)
                assert file_size > 25000, f"Expected substantial PPTX, got {file_size} bytes"
                
                logger.info(f"Combined features conversion successful: {file_size} bytes")
                
            finally:
                if os.path.exists(temp_file.name):
                    os.unlink(temp_file.name)