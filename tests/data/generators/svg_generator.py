#!/usr/bin/env python3
"""
SVG test fixture generator.

This module programmatically generates SVG test cases for comprehensive testing
of the SVG2PPTX conversion pipeline.
"""

import random
import math
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path
import json


@dataclass
class SVGGeneratorConfig:
    """Configuration for SVG generation."""
    width: int = 200
    height: int = 200
    element_count_range: Tuple[int, int] = (1, 10)
    coordinate_range: Tuple[float, float] = (0, 200)
    size_range: Tuple[float, float] = (10, 50)
    color_palette: List[str] = None
    include_transforms: bool = True
    include_groups: bool = True
    include_text: bool = True
    
    def __post_init__(self):
        if self.color_palette is None:
            self.color_palette = [
                '#FF0000', '#00FF00', '#0000FF', '#FFFF00', '#FF00FF', '#00FFFF',
                '#FFA500', '#800080', '#008000', '#000080', '#800000', '#808000'
            ]


class SVGGenerator:
    """Generates SVG test fixtures programmatically."""
    
    def __init__(self, config: SVGGeneratorConfig = None):
        self.config = config or SVGGeneratorConfig()
        self.random = random.Random(42)  # Deterministic seed for reproducible tests
    
    def generate_basic_shapes_svg(self) -> str:
        """Generate SVG with basic shapes (rect, circle, ellipse, line, polygon)."""
        elements = []
        
        # Rectangle
        elements.append(self._generate_rect())
        
        # Circle
        elements.append(self._generate_circle())
        
        # Ellipse
        elements.append(self._generate_ellipse())
        
        # Line
        elements.append(self._generate_line())
        
        # Polygon
        elements.append(self._generate_polygon())
        
        return self._wrap_svg(elements, "basic_shapes")
    
    def generate_complex_paths_svg(self) -> str:
        """Generate SVG with complex path elements."""
        elements = []
        
        # Bezier curves
        elements.append(self._generate_bezier_path())
        
        # Arc path
        elements.append(self._generate_arc_path())
        
        # Complex multi-command path
        elements.append(self._generate_complex_path())
        
        return self._wrap_svg(elements, "complex_paths")
    
    def generate_text_rendering_svg(self) -> str:
        """Generate SVG with various text elements."""
        elements = []
        
        # Simple text
        elements.append(self._generate_text("Simple Text", 50, 30))
        
        # Text with styling
        elements.append(self._generate_styled_text("Styled Text", 50, 60, 
                                                  font_size=16, font_weight="bold", 
                                                  fill="blue"))
        
        # Multi-line text
        elements.append(self._generate_multiline_text(["Line 1", "Line 2", "Line 3"], 50, 100))
        
        # Text with tspan
        elements.append(self._generate_tspan_text("Text with ", "highlighted", " word", 50, 140))
        
        return self._wrap_svg(elements, "text_rendering")
    
    def generate_transforms_svg(self) -> str:
        """Generate SVG with various transform operations."""
        elements = []
        
        # Rotation
        rect1 = self._generate_rect(x=75, y=75, width=50, height=50, fill="red")
        elements.append(f'<g transform="rotate(45 100 100)">{rect1}</g>')
        
        # Scale
        rect2 = self._generate_rect(x=25, y=125, width=25, height=25, fill="green")
        elements.append(f'<g transform="scale(2)">{rect2}</g>')
        
        # Translation
        circle1 = self._generate_circle(cx=50, cy=50, r=20, fill="blue")
        elements.append(f'<g transform="translate(100, 100)">{circle1}</g>')
        
        # Combined transforms
        rect3 = self._generate_rect(x=10, y=10, width=20, height=20, fill="purple")
        elements.append(f'<g transform="translate(150, 50) rotate(30) scale(1.5)">{rect3}</g>')
        
        return self._wrap_svg(elements, "transforms")
    
    def generate_gradients_svg(self) -> str:
        """Generate SVG with gradient fills."""
        defs = []
        elements = []
        
        # Linear gradient
        defs.append('''
        <linearGradient id="linear1" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stop-color="red"/>
            <stop offset="100%" stop-color="blue"/>
        </linearGradient>''')
        
        elements.append(self._generate_rect(x=10, y=10, width=80, height=40, fill="url(#linear1)"))
        
        # Radial gradient
        defs.append('''
        <radialGradient id="radial1" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stop-color="yellow"/>
            <stop offset="100%" stop-color="red"/>
        </radialGradient>''')
        
        elements.append(self._generate_circle(cx=130, cy=70, r=30, fill="url(#radial1)"))
        
        return self._wrap_svg(elements, "gradients", defs)
    
    def generate_pathological_svg(self) -> str:
        """Generate pathological SVG for stress testing."""
        elements = []
        
        # Extremely long path with many segments
        path_d = "M0,0"
        for i in range(1000):
            x = (i % 100) * 2
            y = math.sin(i * 0.1) * 50 + 100
            path_d += f" L{x},{y}"
        elements.append(f'<path d="{path_d}" stroke="red" fill="none"/>')
        
        # Deeply nested groups
        nested_group = self._generate_rect(x=150, y=10, width=30, height=30, fill="blue")
        for _ in range(20):
            nested_group = f'<g transform="translate(1,1)">{nested_group}</g>'
        elements.append(nested_group)
        
        # Many small elements
        for i in range(200):
            x = (i % 20) * 10
            y = (i // 20) * 10 + 50
            elements.append(self._generate_circle(cx=x, cy=y, r=2, fill=self._random_color()))
        
        return self._wrap_svg(elements, "pathological", canvas_height=400)
    
    def generate_edge_cases_svg(self) -> str:
        """Generate SVG with edge cases and boundary conditions."""
        elements = []
        
        # Zero-size elements
        elements.append(self._generate_rect(x=10, y=10, width=0, height=0, fill="red"))
        elements.append(self._generate_circle(cx=20, cy=20, r=0, fill="blue"))
        
        # Negative coordinates
        elements.append(self._generate_rect(x=-10, y=-10, width=30, height=30, fill="green"))
        
        # Very large coordinates
        elements.append(self._generate_rect(x=10000, y=10000, width=50, height=50, fill="purple"))
        
        # Very small coordinates
        elements.append(self._generate_rect(x=0.001, y=0.001, width=0.5, height=0.5, fill="orange"))
        
        # Invalid/extreme colors
        elements.append(self._generate_rect(x=50, y=50, width=30, height=30, fill="rgb(300, -50, 999)"))
        
        # Empty text
        elements.append(self._generate_text("", 100, 100))
        
        # Text with special characters
        elements.append(self._generate_text("Special: <>&\"'", 10, 150))
        
        return self._wrap_svg(elements, "edge_cases")
    
    def _generate_rect(self, x: float = None, y: float = None, width: float = None, 
                      height: float = None, fill: str = None, **attrs) -> str:
        """Generate a rectangle element."""
        x = x if x is not None else self._random_coordinate()
        y = y if y is not None else self._random_coordinate()
        width = width if width is not None else self._random_size()
        height = height if height is not None else self._random_size()
        fill = fill or self._random_color()
        
        attr_str = ' '.join(f'{k}="{v}"' for k, v in attrs.items())
        return f'<rect x="{x}" y="{y}" width="{width}" height="{height}" fill="{fill}" {attr_str}/>'
    
    def _generate_circle(self, cx: float = None, cy: float = None, r: float = None, 
                        fill: str = None, **attrs) -> str:
        """Generate a circle element."""
        cx = cx if cx is not None else self._random_coordinate()
        cy = cy if cy is not None else self._random_coordinate()
        r = r if r is not None else self._random_size() / 2
        fill = fill or self._random_color()
        
        attr_str = ' '.join(f'{k}="{v}"' for k, v in attrs.items())
        return f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}" {attr_str}/>'
    
    def _generate_ellipse(self, cx: float = None, cy: float = None, rx: float = None, 
                         ry: float = None, fill: str = None, **attrs) -> str:
        """Generate an ellipse element."""
        cx = cx if cx is not None else self._random_coordinate()
        cy = cy if cy is not None else self._random_coordinate()
        rx = rx if rx is not None else self._random_size() / 2
        ry = ry if ry is not None else self._random_size() / 2
        fill = fill or self._random_color()
        
        attr_str = ' '.join(f'{k}="{v}"' for k, v in attrs.items())
        return f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{fill}" {attr_str}/>'
    
    def _generate_line(self, x1: float = None, y1: float = None, x2: float = None, 
                      y2: float = None, stroke: str = None, **attrs) -> str:
        """Generate a line element."""
        x1 = x1 if x1 is not None else self._random_coordinate()
        y1 = y1 if y1 is not None else self._random_coordinate()
        x2 = x2 if x2 is not None else self._random_coordinate()
        y2 = y2 if y2 is not None else self._random_coordinate()
        stroke = stroke or self._random_color()
        
        attr_str = ' '.join(f'{k}="{v}"' for k, v in attrs.items())
        return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" {attr_str}/>'
    
    def _generate_polygon(self, points: List[Tuple[float, float]] = None, 
                         fill: str = None, **attrs) -> str:
        """Generate a polygon element."""
        if points is None:
            # Generate triangle
            points = [
                (self._random_coordinate(), self._random_coordinate()),
                (self._random_coordinate(), self._random_coordinate()),
                (self._random_coordinate(), self._random_coordinate())
            ]
        
        points_str = ' '.join(f'{x},{y}' for x, y in points)
        fill = fill or self._random_color()
        
        attr_str = ' '.join(f'{k}="{v}"' for k, v in attrs.items())
        return f'<polygon points="{points_str}" fill="{fill}" {attr_str}/>'
    
    def _generate_text(self, text: str, x: float, y: float, **attrs) -> str:
        """Generate a text element."""
        attr_str = ' '.join(f'{k}="{v}"' for k, v in attrs.items())
        return f'<text x="{x}" y="{y}" {attr_str}>{text}</text>'
    
    def _generate_styled_text(self, text: str, x: float, y: float, font_size: int = 12,
                             font_weight: str = "normal", fill: str = "black", **attrs) -> str:
        """Generate a styled text element."""
        attrs.update({
            'font-size': font_size,
            'font-weight': font_weight,
            'fill': fill
        })
        return self._generate_text(text, x, y, **attrs)
    
    def _generate_multiline_text(self, lines: List[str], x: float, y: float, 
                                line_height: float = 20) -> str:
        """Generate multi-line text using tspan elements."""
        tspans = []
        for i, line in enumerate(lines):
            dy = line_height if i > 0 else 0
            tspans.append(f'<tspan x="{x}" dy="{dy}">{line}</tspan>')
        
        return f'<text x="{x}" y="{y}">{"".join(tspans)}</text>'
    
    def _generate_tspan_text(self, prefix: str, highlight: str, suffix: str, 
                            x: float, y: float) -> str:
        """Generate text with tspan highlighting."""
        return f'''<text x="{x}" y="{y}">
            {prefix}
            <tspan fill="red" font-weight="bold">{highlight}</tspan>
            {suffix}
        </text>'''
    
    def _generate_bezier_path(self) -> str:
        """Generate a path with Bezier curves."""
        x1, y1 = self._random_coordinate(), self._random_coordinate()
        x2, y2 = self._random_coordinate(), self._random_coordinate()
        cx1, cy1 = self._random_coordinate(), self._random_coordinate()
        cx2, cy2 = self._random_coordinate(), self._random_coordinate()
        
        d = f"M{x1},{y1} C{cx1},{cy1} {cx2},{cy2} {x2},{y2}"
        return f'<path d="{d}" stroke="{self._random_color()}" fill="none" stroke-width="2"/>'
    
    def _generate_arc_path(self) -> str:
        """Generate a path with arc commands."""
        x1, y1 = self._random_coordinate(), self._random_coordinate()
        x2, y2 = self._random_coordinate(), self._random_coordinate()
        rx, ry = self._random_size() / 2, self._random_size() / 2
        
        d = f"M{x1},{y1} A{rx},{ry} 0 0 1 {x2},{y2}"
        return f'<path d="{d}" stroke="{self._random_color()}" fill="none" stroke-width="2"/>'
    
    def _generate_complex_path(self) -> str:
        """Generate a complex path with multiple commands."""
        commands = ["M50,50"]
        
        # Add various path commands
        for _ in range(5):
            cmd_type = self.random.choice(['L', 'Q', 'C', 'S'])
            if cmd_type == 'L':
                x, y = self._random_coordinate(), self._random_coordinate()
                commands.append(f"L{x},{y}")
            elif cmd_type == 'Q':
                x1, y1 = self._random_coordinate(), self._random_coordinate()
                x, y = self._random_coordinate(), self._random_coordinate()
                commands.append(f"Q{x1},{y1} {x},{y}")
            elif cmd_type == 'C':
                x1, y1 = self._random_coordinate(), self._random_coordinate()
                x2, y2 = self._random_coordinate(), self._random_coordinate()
                x, y = self._random_coordinate(), self._random_coordinate()
                commands.append(f"C{x1},{y1} {x2},{y2} {x},{y}")
            elif cmd_type == 'S':
                x2, y2 = self._random_coordinate(), self._random_coordinate()
                x, y = self._random_coordinate(), self._random_coordinate()
                commands.append(f"S{x2},{y2} {x},{y}")
        
        commands.append("Z")  # Close path
        d = " ".join(commands)
        return f'<path d="{d}" fill="{self._random_color()}" stroke="black" stroke-width="1"/>'
    
    def _random_coordinate(self) -> float:
        """Generate a random coordinate within the configured range."""
        return round(self.random.uniform(*self.config.coordinate_range), 2)
    
    def _random_size(self) -> float:
        """Generate a random size within the configured range."""
        return round(self.random.uniform(*self.config.size_range), 2)
    
    def _random_color(self) -> str:
        """Select a random color from the configured palette."""
        return self.random.choice(self.config.color_palette)
    
    def _wrap_svg(self, elements: List[str], title: str = "Generated SVG", 
                 defs: List[str] = None, canvas_width: int = None, 
                 canvas_height: int = None) -> str:
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
    
    def generate_test_suite(self, output_dir: Path) -> Dict[str, str]:
        """Generate complete test suite and save to files."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        generators = {
            'basic_shapes': self.generate_basic_shapes_svg,
            'complex_paths': self.generate_complex_paths_svg,
            'text_rendering': self.generate_text_rendering_svg,
            'transforms': self.generate_transforms_svg,
            'gradients': self.generate_gradients_svg,
            'pathological': self.generate_pathological_svg,
            'edge_cases': self.generate_edge_cases_svg,
        }
        
        generated_files = {}
        
        for test_name, generator_func in generators.items():
            svg_content = generator_func()
            file_path = output_dir / f"{test_name}.svg"
            
            with open(file_path, 'w') as f:
                f.write(svg_content)
            
            generated_files[test_name] = str(file_path)
        
        # Generate metadata
        metadata = {
            'generated_files': generated_files,
            'config': {
                'width': self.config.width,
                'height': self.config.height,
                'seed': 42,
                'color_palette': self.config.color_palette
            },
            'categories': list(generators.keys())
        }
        
        metadata_path = output_dir / "test_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        return generated_files


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python svg_generator.py <output_directory> [test_type]")
        print("Test types: basic_shapes, complex_paths, text_rendering, transforms,")
        print("           gradients, pathological, edge_cases, all")
        sys.exit(1)
    
    output_dir = Path(sys.argv[1])
    test_type = sys.argv[2] if len(sys.argv) > 2 else "all"
    
    generator = SVGGenerator()
    
    if test_type == "all":
        generated = generator.generate_test_suite(output_dir)
        print(f"Generated {len(generated)} test SVG files in {output_dir}")
        for name, path in generated.items():
            print(f"  {name}: {path}")
    else:
        # Generate specific test type
        generators = {
            'basic_shapes': generator.generate_basic_shapes_svg,
            'complex_paths': generator.generate_complex_paths_svg,
            'text_rendering': generator.generate_text_rendering_svg,
            'transforms': generator.generate_transforms_svg,
            'gradients': generator.generate_gradients_svg,
            'pathological': generator.generate_pathological_svg,
            'edge_cases': generator.generate_edge_cases_svg,
        }
        
        if test_type not in generators:
            print(f"Unknown test type: {test_type}")
            sys.exit(1)
        
        svg_content = generators[test_type]()
        output_file = output_dir / f"{test_type}.svg"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            f.write(svg_content)
        
        print(f"Generated {test_type} test SVG: {output_file}")
        print(f"Content preview:")
        print(svg_content[:500] + "..." if len(svg_content) > 500 else svg_content)