#!/usr/bin/env python3
"""
SVG Test Corpus Generator

This script generates a comprehensive collection of SVG test files
for validating the SVG2PPTX conversion system across all supported
features and edge cases.
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Tuple
from lxml import etree as ET


class SVGTestCorpusGenerator:
    """Generate comprehensive SVG test corpus."""
    
    def __init__(self, output_dir: str = "tests/test_data/svg_corpus"):
        """Initialize test corpus generator.
        
        Args:
            output_dir: Directory to create test corpus
        """
        self.output_dir = Path(output_dir)
        self.test_metadata = {}
    
    def generate_corpus(self):
        """Generate the complete test corpus."""
        print("🔨 Generating SVG test corpus...")
        
        # Create directory structure
        self._create_directories()
        
        # Generate test files by category
        self._generate_basic_shapes()
        self._generate_complex_paths()
        self._generate_text_elements()
        self._generate_gradients()
        self._generate_transforms()
        self._generate_groups_and_nesting()
        self._generate_filters_and_effects()
        self._generate_edge_cases()
        self._generate_stress_tests()
        
        # Generate test metadata
        self._generate_metadata()
        
        print(f"✅ Generated {len(self.test_metadata)} SVG test files")
    
    def _create_directories(self):
        """Create directory structure for test corpus."""
        categories = [
            'basic_shapes', 'complex_paths', 'text', 'gradients',
            'transforms', 'groups', 'filters', 'edge_cases', 'stress_tests'
        ]
        
        for category in categories:
            (self.output_dir / category).mkdir(parents=True, exist_ok=True)
    
    def _generate_basic_shapes(self):
        """Generate basic shape SVG test files."""
        
        # Basic Rectangle
        rect_svg = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200">
    <desc>Basic rectangle with fill and stroke properties</desc>
    <rect x="50" y="50" width="100" height="80" 
          fill="#3498db" stroke="#2c3e50" stroke-width="2"/>
</svg>'''
        self._write_test_file('basic_shapes/basic_rectangle.svg', rect_svg, {
            'category': 'basic_shapes',
            'complexity': 'basic',
            'features': ['rectangle', 'fill', 'stroke'],
            'expected_elements': 1
        })
        
        # Basic Circle
        circle_svg = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200">
    <desc>Basic circle with fill and stroke properties</desc>
    <circle cx="100" cy="100" r="60" 
            fill="#e74c3c" stroke="#c0392b" stroke-width="3"/>
</svg>'''
        self._write_test_file('basic_shapes/basic_circle.svg', circle_svg, {
            'category': 'basic_shapes',
            'complexity': 'basic',
            'features': ['circle', 'fill', 'stroke'],
            'expected_elements': 1
        })
        
        # Basic Ellipse
        ellipse_svg = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200">
    <desc>Basic ellipse with various dimensions</desc>
    <ellipse cx="100" cy="100" rx="80" ry="50" 
             fill="#2ecc71" stroke="#27ae60" stroke-width="2"/>
</svg>'''
        self._write_test_file('basic_shapes/basic_ellipse.svg', ellipse_svg, {
            'category': 'basic_shapes',
            'complexity': 'basic',
            'features': ['ellipse', 'fill', 'stroke'],
            'expected_elements': 1
        })
        
        # Basic Line
        line_svg = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200">
    <desc>Single line with stroke properties</desc>
    <line x1="20" y1="20" x2="180" y2="180" 
          stroke="#9b59b6" stroke-width="4" stroke-linecap="round"/>
</svg>'''
        self._write_test_file('basic_shapes/basic_line.svg', line_svg, {
            'category': 'basic_shapes',
            'complexity': 'basic',
            'features': ['line', 'stroke', 'stroke-linecap'],
            'expected_elements': 1
        })
        
        # Basic Polygon
        polygon_svg = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200">
    <desc>Simple polygon with multiple points</desc>
    <polygon points="100,20 160,60 160,140 100,180 40,140 40,60" 
             fill="#f39c12" stroke="#e67e22" stroke-width="2"/>
</svg>'''
        self._write_test_file('basic_shapes/basic_polygon.svg', polygon_svg, {
            'category': 'basic_shapes',
            'complexity': 'basic',
            'features': ['polygon', 'fill', 'stroke'],
            'expected_elements': 1
        })
        
        # Basic Polyline
        polyline_svg = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200">
    <desc>Polyline with stroke styling</desc>
    <polyline points="20,20 60,80 120,40 180,100 150,160 80,140" 
              fill="none" stroke="#1abc9c" stroke-width="3" stroke-linejoin="round"/>
</svg>'''
        self._write_test_file('basic_shapes/basic_polyline.svg', polyline_svg, {
            'category': 'basic_shapes',
            'complexity': 'basic',
            'features': ['polyline', 'stroke', 'stroke-linejoin'],
            'expected_elements': 1
        })
    
    def _generate_complex_paths(self):
        """Generate complex path SVG test files."""
        
        # Bezier Curves
        bezier_svg = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200">
    <desc>Cubic and quadratic Bézier curves</desc>
    <path d="M20,100 Q100,20 180,100 C180,120 150,160 100,150 Q60,140 20,100 Z"
          fill="#8e44ad" stroke="#6c3483" stroke-width="2"/>
</svg>'''
        self._write_test_file('complex_paths/bezier_curves.svg', bezier_svg, {
            'category': 'complex_paths',
            'complexity': 'advanced',
            'features': ['path', 'bezier_curves', 'quadratic_curves', 'cubic_curves'],
            'expected_elements': 1
        })
        
        # Arc Segments
        arc_svg = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200">
    <desc>Elliptical arc segments</desc>
    <path d="M30,100 A50,30 0 0,1 100,50 A50,30 0 0,1 170,100 A50,30 0 0,1 100,150 A50,30 0 0,1 30,100 Z"
          fill="#34495e" stroke="#2c3e50" stroke-width="2"/>
</svg>'''
        self._write_test_file('complex_paths/arc_segments.svg', arc_svg, {
            'category': 'complex_paths',
            'complexity': 'advanced',
            'features': ['path', 'elliptical_arcs'],
            'expected_elements': 1
        })
        
        # Mixed Path Commands
        mixed_path_svg = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200">
    <desc>Paths with multiple command types</desc>
    <path d="M50,50 L150,50 Q170,70 150,90 L150,150 C130,170 70,170 50,150 L50,90 Q30,70 50,50 Z"
          fill="#e67e22" stroke="#d35400" stroke-width="2"/>
</svg>'''
        self._write_test_file('complex_paths/mixed_path_commands.svg', mixed_path_svg, {
            'category': 'complex_paths',
            'complexity': 'intermediate',
            'features': ['path', 'line_commands', 'curve_commands', 'mixed_commands'],
            'expected_elements': 1
        })
    
    def _generate_text_elements(self):
        """Generate text element SVG test files."""
        
        # Simple Text
        text_svg = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="300" height="200" viewBox="0 0 300 200">
    <desc>Basic text with font styling</desc>
    <text x="150" y="100" text-anchor="middle" 
          font-family="Arial, sans-serif" font-size="24" fill="#2c3e50">
        Hello, SVG2PPTX!
    </text>
</svg>'''
        self._write_test_file('text/simple_text.svg', text_svg, {
            'category': 'text',
            'complexity': 'basic',
            'features': ['text', 'font-family', 'font-size', 'text-anchor'],
            'expected_elements': 1
        })
        
        # Styled Text
        styled_text_svg = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300" viewBox="0 0 400 300">
    <desc>Text with various font properties</desc>
    <text x="50" y="50" font-family="serif" font-size="18" font-weight="bold" fill="#e74c3c">
        Bold Text
    </text>
    <text x="50" y="100" font-family="serif" font-size="18" font-style="italic" fill="#3498db">
        Italic Text
    </text>
    <text x="50" y="150" font-family="monospace" font-size="16" text-decoration="underline" fill="#2ecc71">
        Monospace Underlined Text
    </text>
    <text x="50" y="200" font-family="sans-serif" font-size="20" font-weight="300" fill="#9b59b6" opacity="0.8">
        Light Weight Text
    </text>
</svg>'''
        self._write_test_file('text/styled_text.svg', styled_text_svg, {
            'category': 'text',
            'complexity': 'intermediate',
            'features': ['text', 'font_variations', 'font-weight', 'font-style', 'opacity'],
            'expected_elements': 4
        })
    
    def _generate_gradients(self):
        """Generate gradient SVG test files."""
        
        # Linear Gradient
        linear_gradient_svg = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200">
    <desc>Simple linear gradient</desc>
    <defs>
        <linearGradient id="linearGrad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" style="stop-color:#3498db;stop-opacity:1" />
            <stop offset="100%" style="stop-color:#e74c3c;stop-opacity:1" />
        </linearGradient>
    </defs>
    <rect x="50" y="50" width="100" height="100" fill="url(#linearGrad)"/>
</svg>'''
        self._write_test_file('gradients/linear_gradient.svg', linear_gradient_svg, {
            'category': 'gradients',
            'complexity': 'intermediate',
            'features': ['linear_gradient', 'gradient_stops', 'defs'],
            'expected_elements': 1
        })
        
        # Radial Gradient
        radial_gradient_svg = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200">
    <desc>Radial gradient with color stops</desc>
    <defs>
        <radialGradient id="radialGrad" cx="50%" cy="50%" r="50%">
            <stop offset="0%" style="stop-color:#f1c40f;stop-opacity:1" />
            <stop offset="50%" style="stop-color:#e67e22;stop-opacity:1" />
            <stop offset="100%" style="stop-color:#c0392b;stop-opacity:1" />
        </radialGradient>
    </defs>
    <circle cx="100" cy="100" r="80" fill="url(#radialGrad)"/>
</svg>'''
        self._write_test_file('gradients/radial_gradient.svg', radial_gradient_svg, {
            'category': 'gradients',
            'complexity': 'intermediate',
            'features': ['radial_gradient', 'multiple_stops', 'defs'],
            'expected_elements': 1
        })
    
    def _generate_transforms(self):
        """Generate transform SVG test files."""
        
        # Transform Example
        transform_svg = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="300" height="300" viewBox="0 0 300 300">
    <desc>Multiple combined transformations</desc>
    <rect x="100" y="100" width="40" height="40" fill="#3498db"/>
    <rect x="100" y="100" width="40" height="40" fill="#e74c3c" 
          transform="translate(50, 20) rotate(45)"/>
    <rect x="100" y="100" width="40" height="40" fill="#2ecc71" 
          transform="scale(1.5) translate(30, 40)"/>
    <rect x="100" y="100" width="40" height="40" fill="#f39c12" 
          transform="translate(80, 80) rotate(30) scale(0.8)"/>
</svg>'''
        self._write_test_file('transforms/complex_transforms.svg', transform_svg, {
            'category': 'transforms',
            'complexity': 'advanced',
            'features': ['transforms', 'translate', 'rotate', 'scale', 'combined_transforms'],
            'expected_elements': 4
        })
    
    def _generate_groups_and_nesting(self):
        """Generate group and nesting SVG test files."""
        
        # Nested Groups
        nested_groups_svg = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200">
    <desc>Multiple levels of nesting</desc>
    <g transform="translate(50, 50)" fill="#3498db">
        <g transform="rotate(15)">
            <g transform="scale(0.8)">
                <rect x="0" y="0" width="40" height="40"/>
                <circle cx="60" cy="20" r="15"/>
            </g>
        </g>
        <g transform="translate(60, 0)" fill="#e74c3c">
            <ellipse cx="20" cy="20" rx="15" ry="25"/>
        </g>
    </g>
</svg>'''
        self._write_test_file('groups/nested_groups.svg', nested_groups_svg, {
            'category': 'groups',
            'complexity': 'advanced',
            'features': ['groups', 'nested_groups', 'group_transforms', 'group_attributes'],
            'expected_elements': 3
        })
    
    def _generate_filters_and_effects(self):
        """Generate filter and effects SVG test files."""
        
        # Drop Shadow (placeholder - actual filter implementation may vary)
        drop_shadow_svg = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200">
    <desc>Drop shadow filter effect</desc>
    <defs>
        <filter id="dropshadow">
            <feDropShadow dx="3" dy="3" stdDeviation="2" flood-color="#000000" flood-opacity="0.3"/>
        </filter>
    </defs>
    <rect x="50" y="50" width="100" height="80" fill="#3498db" filter="url(#dropshadow)"/>
</svg>'''
        self._write_test_file('filters/drop_shadow.svg', drop_shadow_svg, {
            'category': 'filters',
            'complexity': 'advanced',
            'features': ['filters', 'drop_shadow', 'filter_effects'],
            'expected_elements': 1
        })
        
        # Gaussian Blur
        gaussian_blur_svg = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200">
    <desc>Gaussian blur filter</desc>
    <defs>
        <filter id="blur">
            <feGaussianBlur stdDeviation="3"/>
        </filter>
    </defs>
    <circle cx="100" cy="100" r="60" fill="#e74c3c" filter="url(#blur)"/>
</svg>'''
        self._write_test_file('filters/gaussian_blur.svg', gaussian_blur_svg, {
            'category': 'filters',
            'complexity': 'advanced',
            'features': ['filters', 'gaussian_blur', 'filter_effects'],
            'expected_elements': 1
        })
    
    def _generate_edge_cases(self):
        """Generate edge case SVG test files."""
        
        # Zero Dimensions
        zero_dimensions_svg = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200">
    <desc>Elements with zero width/height</desc>
    <rect x="50" y="50" width="0" height="100" fill="#3498db" stroke="#2c3e50" stroke-width="2"/>
    <rect x="100" y="50" width="100" height="0" fill="#e74c3c" stroke="#c0392b" stroke-width="2"/>
    <circle cx="150" cy="150" r="0" fill="#2ecc71" stroke="#27ae60" stroke-width="2"/>
</svg>'''
        self._write_test_file('edge_cases/zero_dimensions.svg', zero_dimensions_svg, {
            'category': 'edge_cases',
            'complexity': 'edge_case',
            'features': ['zero_dimensions', 'edge_cases', 'degenerate_shapes'],
            'expected_elements': 3,
            'expected_behavior': 'graceful_degradation'
        })
        
        # Extreme Coordinates
        extreme_coordinates_svg = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200">
    <desc>Very large or very small coordinates</desc>
    <rect x="1000000" y="50" width="50" height="50" fill="#3498db"/>
    <circle cx="-500" cy="100" r="30" fill="#e74c3c"/>
    <line x1="0.001" y1="0.001" x2="0.002" y2="0.002" stroke="#2ecc71" stroke-width="1"/>
</svg>'''
        self._write_test_file('edge_cases/extreme_coordinates.svg', extreme_coordinates_svg, {
            'category': 'edge_cases',
            'complexity': 'edge_case',
            'features': ['extreme_coordinates', 'large_numbers', 'small_numbers'],
            'expected_elements': 3,
            'expected_behavior': 'coordinate_normalization'
        })
    
    def _generate_stress_tests(self):
        """Generate stress test SVG test files."""
        
        # Many Elements
        many_elements_svg = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="400" height="400" viewBox="0 0 400 400">
    <desc>Large number of elements</desc>'''
        
        # Add many rectangles
        for i in range(100):
            x = (i % 10) * 40
            y = (i // 10) * 40
            color = f"hsl({i * 3.6}, 70%, 50%)"
            many_elements_svg += f'\n    <rect x="{x}" y="{y}" width="35" height="35" fill="{color}"/>'
        
        many_elements_svg += '\n</svg>'
        
        self._write_test_file('stress_tests/many_elements.svg', many_elements_svg, {
            'category': 'stress_tests',
            'complexity': 'stress',
            'features': ['many_elements', 'performance_test'],
            'expected_elements': 100,
            'performance_threshold': 5.0  # seconds
        })
    
    def _write_test_file(self, relative_path: str, content: str, metadata: Dict):
        """Write test file and store metadata."""
        file_path = self.output_dir / relative_path
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Store metadata
        metadata.update({
            'file_path': relative_path,
            'file_size': len(content.encode('utf-8')),
            'generated': True
        })
        
        self.test_metadata[relative_path] = metadata
        print(f"   Generated: {relative_path}")
    
    def _generate_metadata(self):
        """Generate test corpus metadata file."""
        corpus_metadata = {
            'corpus_info': {
                'generated_by': 'SVGTestCorpusGenerator',
                'total_files': len(self.test_metadata),
                'categories': list(set(meta['category'] for meta in self.test_metadata.values())),
                'complexity_levels': list(set(meta.get('complexity', 'unknown') for meta in self.test_metadata.values())),
                'total_elements': sum(meta.get('expected_elements', 0) for meta in self.test_metadata.values())
            },
            'test_files': self.test_metadata
        }
        
        metadata_path = self.output_dir / 'corpus_metadata.json'
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(corpus_metadata, f, indent=2)
        
        print(f"✅ Generated metadata: {metadata_path}")


def main():
    """Main function to generate test corpus."""
    generator = SVGTestCorpusGenerator()
    generator.generate_corpus()
    
    print("\n📊 Test Corpus Summary:")
    print(f"   Files: {len(generator.test_metadata)}")
    print(f"   Categories: {len(set(meta['category'] for meta in generator.test_metadata.values()))}")
    print(f"   Total Elements: {sum(meta.get('expected_elements', 0) for meta in generator.test_metadata.values())}")
    print(f"   Output Directory: {generator.output_dir}")


if __name__ == '__main__':
    main()