#!/usr/bin/env python3
"""
Template Patterns for SVG Test Generation.

This module provides template-driven test generation that integrates
with the existing SVG generators to create comprehensive test suites
for all converter modules.
"""

from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass
import random
import json
from pathlib import Path

from ..data.generators.converter_patterns import ConverterPatternLibrary, ConverterType, ConverterTestPattern


@dataclass
class TestGenerationConfig:
    """Configuration for template-driven test generation."""
    width: int = 200
    height: int = 200
    seed: int = 42
    element_count_range: Tuple[int, int] = (1, 5)
    coordinate_range: Tuple[float, float] = (10, 190)
    size_range: Tuple[float, float] = (10, 50)
    color_palette: Optional[List[str]] = None
    include_edge_cases: bool = True
    include_performance_variants: bool = True

    def __post_init__(self):
        if self.color_palette is None:
            self.color_palette = [
                '#FF0000', '#00FF00', '#0000FF', '#FFFF00', '#FF00FF', '#00FFFF',
                '#FFA500', '#800080', '#008000', '#000080', '#800000', '#808000'
            ]


class TemplatePatternGenerator:
    """Generates SVG test cases using converter-specific templates."""

    def __init__(self, config: Optional[TestGenerationConfig] = None):
        """Initialize template pattern generator."""
        self.config = config or TestGenerationConfig()
        self.pattern_library = ConverterPatternLibrary()
        self.random = random.Random(self.config.seed)

    def generate_converter_test_suite(self, converter_type: ConverterType,
                                    output_dir: Optional[Path] = None) -> Dict[str, str]:
        """Generate complete test suite for specific converter."""
        pattern = self.pattern_library.get_pattern(converter_type)
        if not pattern:
            raise ValueError(f"No pattern found for converter type: {converter_type}")

        test_suite = {}

        # Generate basic scenario tests
        for scenario in pattern.test_scenarios:
            svg_content = self._generate_scenario_svg(pattern, scenario)
            test_suite[f"{converter_type.value}_{scenario}"] = svg_content

        # Generate edge case tests if enabled
        if self.config.include_edge_cases:
            for edge_case in pattern.edge_cases:
                svg_content = self._generate_edge_case_svg(pattern, edge_case)
                test_suite[f"{converter_type.value}_{edge_case}"] = svg_content

        # Generate performance variant tests if enabled
        if self.config.include_performance_variants:
            for variant in pattern.performance_variants:
                svg_content = self._generate_performance_variant_svg(pattern, variant)
                test_suite[f"{converter_type.value}_{variant}"] = svg_content

        # Save to files if output directory specified
        if output_dir:
            self._save_test_suite(test_suite, output_dir, converter_type)

        return test_suite

    def generate_comprehensive_test_suite(self, output_dir: Optional[Path] = None) -> Dict[str, Dict[str, str]]:
        """Generate test suites for all converter types."""
        comprehensive_suite = {}

        for converter_type in ConverterType:
            try:
                converter_suite = self.generate_converter_test_suite(converter_type, output_dir)
                comprehensive_suite[converter_type.value] = converter_suite
            except ValueError as e:
                print(f"Warning: {e}")
                continue

        return comprehensive_suite

    def _generate_scenario_svg(self, pattern: ConverterTestPattern, scenario: str) -> str:
        """Generate SVG for specific test scenario."""
        # Map scenarios to generation methods
        scenario_generators = {
            # Shapes scenarios
            'basic_shapes_individual': self._generate_basic_shapes_individual,
            'basic_shapes_with_styling': self._generate_basic_shapes_with_styling,
            'shapes_with_transforms': self._generate_shapes_with_transforms,
            'batch_processing_multiple_shapes': self._generate_batch_shapes,

            # Paths scenarios
            'simple_line_paths': self._generate_simple_line_paths,
            'bezier_curve_paths': self._generate_bezier_curve_paths,
            'complex_mixed_commands': self._generate_complex_mixed_commands,

            # Text scenarios
            'simple_text_elements': self._generate_simple_text_elements,
            'text_with_font_styling': self._generate_text_with_font_styling,
            'multiline_text_with_tspan': self._generate_multiline_text_with_tspan,

            # Gradients scenarios
            'simple_linear_gradients': self._generate_simple_linear_gradients,
            'simple_radial_gradients': self._generate_simple_radial_gradients,
            'gradients_with_multiple_stops': self._generate_gradients_with_multiple_stops,

            # Generic fallback
            'default': self._generate_default_scenario
        }

        generator = scenario_generators.get(scenario, scenario_generators['default'])
        return generator(pattern, scenario)

    def _generate_edge_case_svg(self, pattern: ConverterTestPattern, edge_case: str) -> str:
        """Generate SVG for specific edge case."""
        # Map edge cases to generation methods
        edge_case_generators = {
            'zero_dimensions_shapes': self._generate_zero_dimensions_shapes,
            'negative_coordinates': self._generate_negative_coordinates,
            'extremely_large_shapes': self._generate_extremely_large_shapes,
            'extremely_small_shapes': self._generate_extremely_small_shapes,
            'empty_path_data': self._generate_empty_path_data,
            'invalid_path_commands': self._generate_invalid_path_commands,
            'empty_text_content': self._generate_empty_text_content,
            'text_with_unicode_characters': self._generate_text_with_unicode_characters,
            'default': self._generate_default_edge_case
        }

        generator = edge_case_generators.get(edge_case, edge_case_generators['default'])
        return generator(pattern, edge_case)

    def _generate_performance_variant_svg(self, pattern: ConverterTestPattern, variant: str) -> str:
        """Generate SVG for performance testing variant."""
        # Map performance variants to generation methods
        performance_generators = {
            'single_shape_conversion': lambda p, v: self._generate_single_element(p),
            'batch_10_shapes': lambda p, v: self._generate_batch_elements(p, 10),
            'batch_100_shapes': lambda p, v: self._generate_batch_elements(p, 100),
            'batch_1000_shapes': lambda p, v: self._generate_batch_elements(p, 1000),
            'complex_styling_batch': lambda p, v: self._generate_complex_styling_batch(p),
            'default': self._generate_default_performance_variant
        }

        generator = performance_generators.get(variant, performance_generators['default'])
        return generator(pattern, variant)

    # Basic scenario generators
    def _generate_basic_shapes_individual(self, pattern: ConverterTestPattern, scenario: str) -> str:
        """Generate individual basic shapes."""
        elements = []
        y_offset = 20

        for element_type in pattern.svg_elements:
            if element_type == 'rect':
                elements.append(f'<rect x="20" y="{y_offset}" width="40" height="30" fill="red" stroke="black" stroke-width="1"/>')
            elif element_type == 'circle':
                elements.append(f'<circle cx="100" cy="{y_offset + 15}" r="15" fill="blue" stroke="black" stroke-width="1"/>')
            elif element_type == 'ellipse':
                elements.append(f'<ellipse cx="160" cy="{y_offset + 15}" rx="20" ry="15" fill="green" stroke="black" stroke-width="1"/>')
            elif element_type == 'line':
                elements.append(f'<line x1="20" y1="{y_offset}" x2="60" y2="{y_offset + 30}" stroke="purple" stroke-width="2"/>')
            elif element_type == 'polygon':
                points = f"20,{y_offset} 40,{y_offset} 30,{y_offset + 20}"
                elements.append(f'<polygon points="{points}" fill="orange" stroke="black" stroke-width="1"/>')

            y_offset += 50

        return self._wrap_svg(elements, f"Basic Shapes Individual - {scenario}")

    def _generate_basic_shapes_with_styling(self, pattern: ConverterTestPattern, scenario: str) -> str:
        """Generate basic shapes with various styling options."""
        elements = []
        colors = self.config.color_palette

        x_offset = 20
        for i, element_type in enumerate(pattern.svg_elements[:4]):  # Limit to 4 for styling demo
            color = colors[i % len(colors)]
            if element_type == 'rect':
                elements.append(f'''<rect x="{x_offset}" y="20" width="35" height="25"
                              fill="{color}" stroke="black" stroke-width="2"
                              opacity="0.8" rx="5" ry="5"/>''')
            elif element_type == 'circle':
                elements.append(f'''<circle cx="{x_offset + 17}" cy="75" r="15"
                              fill="{color}" stroke="darkblue" stroke-width="3"
                              stroke-dasharray="5,5" opacity="0.9"/>''')

            x_offset += 45

        return self._wrap_svg(elements, f"Basic Shapes with Styling - {scenario}")

    def _generate_shapes_with_transforms(self, pattern: ConverterTestPattern, scenario: str) -> str:
        """Generate shapes with various transforms."""
        elements = []

        # Rectangle with rotation
        elements.append('''<rect x="50" y="50" width="30" height="20" fill="red"
                          transform="rotate(45 65 60)"/>''')

        # Circle with scaling
        elements.append('''<circle cx="120" cy="60" r="15" fill="blue"
                          transform="scale(1.5)"/>''')

        # Group with combined transforms
        elements.append('''<g transform="translate(50, 100) rotate(30) scale(0.8)">
                            <rect x="0" y="0" width="40" height="25" fill="green"/>
                            <circle cx="50" cy="12" r="10" fill="orange"/>
                          </g>''')

        return self._wrap_svg(elements, f"Shapes with Transforms - {scenario}")

    def _generate_batch_shapes(self, pattern: ConverterTestPattern, scenario: str) -> str:
        """Generate batch of shapes for performance testing."""
        elements = []
        count = 20  # Reasonable number for display

        for i in range(count):
            x = (i % 10) * 20
            y = (i // 10) * 20 + 20
            color = self.config.color_palette[i % len(self.config.color_palette)]

            # Rotate between different shape types
            shape_type = pattern.svg_elements[i % len(pattern.svg_elements)]

            if shape_type == 'rect':
                elements.append(f'<rect x="{x}" y="{y}" width="15" height="15" fill="{color}"/>')
            elif shape_type == 'circle':
                elements.append(f'<circle cx="{x + 7}" cy="{y + 7}" r="7" fill="{color}"/>')
            elif shape_type == 'ellipse':
                elements.append(f'<ellipse cx="{x + 7}" cy="{y + 7}" rx="9" ry="6" fill="{color}"/>')

        return self._wrap_svg(elements, f"Batch Shapes - {scenario}", canvas_height=300)

    # Path scenario generators
    def _generate_simple_line_paths(self, pattern: ConverterTestPattern, scenario: str) -> str:
        """Generate simple line paths."""
        elements = [
            '<path d="M20,20 L80,20" stroke="red" stroke-width="2" fill="none"/>',
            '<path d="M20,40 L80,60 L120,40" stroke="blue" stroke-width="2" fill="none"/>',
            '<path d="M20,80 L40,100 L60,80 L80,100" stroke="green" stroke-width="2" fill="none"/>'
        ]
        return self._wrap_svg(elements, f"Simple Line Paths - {scenario}")

    def _generate_bezier_curve_paths(self, pattern: ConverterTestPattern, scenario: str) -> str:
        """Generate Bezier curve paths."""
        elements = [
            '<path d="M20,100 Q100,20 180,100" stroke="purple" stroke-width="3" fill="none"/>',
            '<path d="M20,150 C40,120 80,120 100,150 S140,180 180,150" stroke="orange" stroke-width="3" fill="none"/>'
        ]
        return self._wrap_svg(elements, f"Bezier Curve Paths - {scenario}")

    def _generate_complex_mixed_commands(self, pattern: ConverterTestPattern, scenario: str) -> str:
        """Generate complex paths with mixed commands."""
        elements = [
            '''<path d="M50,50 L100,50 Q120,70 100,90 L100,140 C80,160 20,160 20,140 L20,90 Q0,70 20,50 Z"
               fill="lightblue" stroke="darkblue" stroke-width="2"/>'''
        ]
        return self._wrap_svg(elements, f"Complex Mixed Commands - {scenario}")

    # Text scenario generators
    def _generate_simple_text_elements(self, pattern: ConverterTestPattern, scenario: str) -> str:
        """Generate simple text elements."""
        elements = [
            '<text x="20" y="30" font-family="Arial" font-size="16" fill="black">Simple Text</text>',
            '<text x="20" y="60" font-family="serif" font-size="14" fill="blue">Serif Text</text>',
            '<text x="20" y="90" font-family="monospace" font-size="12" fill="green">Monospace Text</text>'
        ]
        return self._wrap_svg(elements, f"Simple Text Elements - {scenario}")

    def _generate_text_with_font_styling(self, pattern: ConverterTestPattern, scenario: str) -> str:
        """Generate text with various font styling."""
        elements = [
            '<text x="20" y="30" font-family="Arial" font-size="16" font-weight="bold" fill="red">Bold Text</text>',
            '<text x="20" y="60" font-family="Arial" font-size="16" font-style="italic" fill="blue">Italic Text</text>',
            '<text x="20" y="90" font-family="Arial" font-size="16" text-decoration="underline" fill="green">Underlined Text</text>'
        ]
        return self._wrap_svg(elements, f"Text with Font Styling - {scenario}")

    def _generate_multiline_text_with_tspan(self, pattern: ConverterTestPattern, scenario: str) -> str:
        """Generate multiline text with tspan elements."""
        elements = [
            '''<text x="20" y="30" font-family="Arial" font-size="14" fill="black">
                 <tspan x="20" dy="0">First line of text</tspan>
                 <tspan x="20" dy="20">Second line of text</tspan>
                 <tspan x="20" dy="20" fill="red" font-weight="bold">Third line in red bold</tspan>
               </text>'''
        ]
        return self._wrap_svg(elements, f"Multiline Text with Tspan - {scenario}")

    # Gradient scenario generators
    def _generate_simple_linear_gradients(self, pattern: ConverterTestPattern, scenario: str) -> str:
        """Generate simple linear gradients."""
        defs = [
            '''<linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="0%">
                 <stop offset="0%" stop-color="red"/>
                 <stop offset="100%" stop-color="blue"/>
               </linearGradient>'''
        ]
        elements = [
            '<rect x="20" y="20" width="100" height="60" fill="url(#grad1)"/>'
        ]
        return self._wrap_svg(elements, f"Simple Linear Gradients - {scenario}", defs)

    def _generate_simple_radial_gradients(self, pattern: ConverterTestPattern, scenario: str) -> str:
        """Generate simple radial gradients."""
        defs = [
            '''<radialGradient id="radial1" cx="50%" cy="50%" r="50%">
                 <stop offset="0%" stop-color="yellow"/>
                 <stop offset="100%" stop-color="red"/>
               </radialGradient>'''
        ]
        elements = [
            '<circle cx="100" cy="100" r="50" fill="url(#radial1)"/>'
        ]
        return self._wrap_svg(elements, f"Simple Radial Gradients - {scenario}", defs)

    def _generate_gradients_with_multiple_stops(self, pattern: ConverterTestPattern, scenario: str) -> str:
        """Generate gradients with multiple color stops."""
        defs = [
            '''<linearGradient id="multiGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                 <stop offset="0%" stop-color="red"/>
                 <stop offset="25%" stop-color="orange"/>
                 <stop offset="50%" stop-color="yellow"/>
                 <stop offset="75%" stop-color="green"/>
                 <stop offset="100%" stop-color="blue"/>
               </linearGradient>'''
        ]
        elements = [
            '<rect x="20" y="20" width="160" height="40" fill="url(#multiGrad)"/>'
        ]
        return self._wrap_svg(elements, f"Gradients with Multiple Stops - {scenario}", defs)

    # Edge case generators
    def _generate_zero_dimensions_shapes(self, pattern: ConverterTestPattern, scenario: str) -> str:
        """Generate shapes with zero dimensions."""
        elements = [
            '<rect x="50" y="50" width="0" height="50" fill="red" stroke="black" stroke-width="2"/>',
            '<rect x="70" y="50" width="50" height="0" fill="blue" stroke="black" stroke-width="2"/>',
            '<circle cx="130" cy="75" r="0" fill="green" stroke="black" stroke-width="2"/>'
        ]
        return self._wrap_svg(elements, f"Zero Dimensions Shapes - {scenario}")

    def _generate_negative_coordinates(self, pattern: ConverterTestPattern, scenario: str) -> str:
        """Generate shapes with negative coordinates."""
        elements = [
            '<rect x="-10" y="-10" width="40" height="30" fill="red"/>',
            '<circle cx="-5" cy="50" r="20" fill="blue"/>',
            '<line x1="-20" y1="80" x2="50" y2="100" stroke="green" stroke-width="2"/>'
        ]
        return self._wrap_svg(elements, f"Negative Coordinates - {scenario}")

    def _generate_extremely_large_shapes(self, pattern: ConverterTestPattern, scenario: str) -> str:
        """Generate extremely large shapes."""
        elements = [
            '<rect x="10000" y="10000" width="50000" height="30000" fill="red"/>',
            '<circle cx="5000" cy="5000" r="25000" fill="blue"/>',
        ]
        return self._wrap_svg(elements, f"Extremely Large Shapes - {scenario}", canvas_width=100000, canvas_height=100000)

    def _generate_extremely_small_shapes(self, pattern: ConverterTestPattern, scenario: str) -> str:
        """Generate extremely small shapes."""
        elements = [
            '<rect x="0.001" y="0.001" width="0.5" height="0.3" fill="red"/>',
            '<circle cx="1.001" cy="1.001" r="0.25" fill="blue"/>',
        ]
        return self._wrap_svg(elements, f"Extremely Small Shapes - {scenario}")

    def _generate_empty_path_data(self, pattern: ConverterTestPattern, scenario: str) -> str:
        """Generate paths with empty data."""
        elements = [
            '<path d="" stroke="red" stroke-width="2" fill="none"/>',
            '<path d="  " stroke="blue" stroke-width="2" fill="none"/>',
        ]
        return self._wrap_svg(elements, f"Empty Path Data - {scenario}")

    def _generate_invalid_path_commands(self, pattern: ConverterTestPattern, scenario: str) -> str:
        """Generate paths with invalid commands."""
        elements = [
            '<path d="X20,20 Y80,80" stroke="red" stroke-width="2" fill="none"/>',
            '<path d="M20,20 Z20,80" stroke="blue" stroke-width="2" fill="none"/>',
        ]
        return self._wrap_svg(elements, f"Invalid Path Commands - {scenario}")

    def _generate_empty_text_content(self, pattern: ConverterTestPattern, scenario: str) -> str:
        """Generate text elements with empty content."""
        elements = [
            '<text x="20" y="30" font-family="Arial" font-size="16" fill="black"></text>',
            '<text x="20" y="60" font-family="Arial" font-size="16" fill="blue">   </text>',
        ]
        return self._wrap_svg(elements, f"Empty Text Content - {scenario}")

    def _generate_text_with_unicode_characters(self, pattern: ConverterTestPattern, scenario: str) -> str:
        """Generate text with Unicode characters."""
        elements = [
            '<text x="20" y="30" font-family="Arial" font-size="16" fill="black">Unicode: α β γ δ ε</text>',
            '<text x="20" y="60" font-family="Arial" font-size="16" fill="blue">Emoji: 🌟 🚀 💡 🎨</text>',
            '<text x="20" y="90" font-family="Arial" font-size="16" fill="green">Chinese: 你好世界</text>',
        ]
        return self._wrap_svg(elements, f"Text with Unicode Characters - {scenario}")

    # Performance generators
    def _generate_single_element(self, pattern: ConverterTestPattern) -> str:
        """Generate single element for performance baseline."""
        element_type = pattern.svg_elements[0] if pattern.svg_elements else 'rect'

        if element_type == 'rect':
            elements = ['<rect x="50" y="50" width="40" height="30" fill="blue"/>']
        elif element_type == 'circle':
            elements = ['<circle cx="100" cy="100" r="25" fill="red"/>']
        elif element_type == 'path':
            elements = ['<path d="M50,50 L100,100 L150,50 Z" fill="green"/>']
        else:
            elements = ['<rect x="50" y="50" width="40" height="30" fill="blue"/>']  # Fallback

        return self._wrap_svg(elements, f"Single Element Performance Test")

    def _generate_batch_elements(self, pattern: ConverterTestPattern, count: int) -> str:
        """Generate batch of elements for performance testing."""
        elements = []
        element_type = pattern.svg_elements[0] if pattern.svg_elements else 'rect'

        # Calculate grid dimensions
        cols = int(count ** 0.5) + 1
        rows = (count + cols - 1) // cols

        for i in range(count):
            col = i % cols
            row = i // cols
            x = col * 20 + 10
            y = row * 20 + 10
            color = self.config.color_palette[i % len(self.config.color_palette)]

            if element_type == 'rect':
                elements.append(f'<rect x="{x}" y="{y}" width="15" height="15" fill="{color}"/>')
            elif element_type == 'circle':
                elements.append(f'<circle cx="{x + 7}" cy="{y + 7}" r="7" fill="{color}"/>')
            elif element_type == 'path':
                elements.append(f'<path d="M{x},{y} L{x+15},{y} L{x+7},{y+15} Z" fill="{color}"/>')

        canvas_width = cols * 20 + 20
        canvas_height = rows * 20 + 20

        return self._wrap_svg(elements, f"Batch {count} Elements Performance Test",
                            canvas_width=canvas_width, canvas_height=canvas_height)

    def _generate_complex_styling_batch(self, pattern: ConverterTestPattern) -> str:
        """Generate batch with complex styling for performance testing."""
        elements = []
        count = 25

        for i in range(count):
            x = (i % 5) * 40 + 10
            y = (i // 5) * 40 + 10
            color = self.config.color_palette[i % len(self.config.color_palette)]

            # Complex styling with gradients, transforms, etc.
            elements.append(f'''<rect x="{x}" y="{y}" width="30" height="30"
                              fill="{color}" stroke="black" stroke-width="2"
                              opacity="0.8" rx="5" ry="5"
                              transform="rotate({i * 15} {x + 15} {y + 15})"/>''')

        return self._wrap_svg(elements, f"Complex Styling Batch Performance Test",
                            canvas_width=250, canvas_height=250)

    # Default generators
    def _generate_default_scenario(self, pattern: ConverterTestPattern, scenario: str) -> str:
        """Default scenario generator."""
        elements = ['<rect x="50" y="50" width="40" height="30" fill="gray"/>']
        return self._wrap_svg(elements, f"Default Scenario - {scenario}")

    def _generate_default_edge_case(self, pattern: ConverterTestPattern, edge_case: str) -> str:
        """Default edge case generator."""
        elements = ['<rect x="50" y="50" width="0" height="0" fill="red"/>']
        return self._wrap_svg(elements, f"Default Edge Case - {edge_case}")

    def _generate_default_performance_variant(self, pattern: ConverterTestPattern, variant: str) -> str:
        """Default performance variant generator."""
        elements = ['<rect x="50" y="50" width="40" height="30" fill="blue"/>']
        return self._wrap_svg(elements, f"Default Performance Variant - {variant}")

    # Utility methods
    def _wrap_svg(self, elements: List[str], title: str = "Generated SVG",
                 defs: Optional[List[str]] = None,
                 canvas_width: Optional[int] = None,
                 canvas_height: Optional[int] = None) -> str:
        """Wrap elements in a complete SVG document."""
        width = canvas_width or self.config.width
        height = canvas_height or self.config.height

        svg_parts = [
            f'<?xml version="1.0" encoding="UTF-8"?>',
            f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">',
            f'  <title>{title}</title>'
        ]

        if defs:
            svg_parts.append('  <defs>')
            svg_parts.extend(f'    {def_elem}' for def_elem in defs)
            svg_parts.append('  </defs>')

        svg_parts.extend(f'  {element}' for element in elements)
        svg_parts.append('</svg>')

        return '\n'.join(svg_parts)

    def _save_test_suite(self, test_suite: Dict[str, str], output_dir: Path,
                        converter_type: ConverterType):
        """Save test suite to files."""
        output_dir = Path(output_dir)
        converter_dir = output_dir / converter_type.value
        converter_dir.mkdir(parents=True, exist_ok=True)

        # Save SVG files
        for test_name, svg_content in test_suite.items():
            file_path = converter_dir / f"{test_name}.svg"
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(svg_content)

        # Save metadata
        metadata = {
            'converter_type': converter_type.value,
            'test_count': len(test_suite),
            'test_files': list(test_suite.keys()),
            'generation_config': {
                'width': self.config.width,
                'height': self.config.height,
                'seed': self.config.seed,
                'include_edge_cases': self.config.include_edge_cases,
                'include_performance_variants': self.config.include_performance_variants
            }
        }

        metadata_path = converter_dir / 'test_metadata.json'
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)


# Convenience functions
def generate_test_suite_for_converter(converter_type: ConverterType,
                                    output_dir: Optional[Path] = None,
                                    config: Optional[TestGenerationConfig] = None) -> Dict[str, str]:
    """Generate test suite for specific converter type."""
    generator = TemplatePatternGenerator(config)
    return generator.generate_converter_test_suite(converter_type, output_dir)


def generate_comprehensive_test_suite(output_dir: Optional[Path] = None,
                                    config: Optional[TestGenerationConfig] = None) -> Dict[str, Dict[str, str]]:
    """Generate comprehensive test suite for all converter types."""
    generator = TemplatePatternGenerator(config)
    return generator.generate_comprehensive_test_suite(output_dir)