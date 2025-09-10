#!/usr/bin/env python3
"""
Generate comprehensive SVG sample files for missing elements testing.
"""

from pathlib import Path

def create_svg_samples():
    """Create all SVG sample files for missing elements"""
    
    samples = {
        # Polyline samples
        'polyline_basic.svg': '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 100">
  <polyline points="10,10 50,25 90,10 120,40 150,20" fill="none" stroke="blue" stroke-width="2"/>
</svg>''',
        
        'polyline_complex.svg': '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 200">
  <polyline points="0,0 10,20 30,15 50,40 80,25 100,50 130,35 160,60 190,45 220,70" 
            fill="none" stroke="green" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
</svg>''',

        # Tspan samples (Critical Priority)
        'tspan_styling.svg': '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 100">
  <text x="50" y="50" font-family="Arial" font-size="16">
    <tspan fill="red" font-weight="bold">Bold Red</tspan>
    <tspan fill="blue" font-style="italic" dx="10">Italic Blue</tspan>
  </text>
</svg>''',
        
        'tspan_nested.svg': '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 100">
  <text x="20" y="40" font-family="Times New Roman">
    <tspan>Normal <tspan fill="red" font-weight="bold">nested bold red</tspan> text</tspan>
  </text>
</svg>''',

        'tspan_positioning.svg': '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 150">
  <text x="10" y="30" font-size="14" fill="black">
    <tspan x="20" y="40">Absolute position</tspan>
    <tspan dx="5" dy="-10">Relative offset</tspan>
    <tspan dx="10,5,3" dy="0,2,-1">Multiple deltas</tspan>
  </text>
</svg>''',

        'tspan_complex_formatting.svg': '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">
  <text x="10" y="30" font-family="Arial" font-size="12">
    <tspan font-size="18" font-weight="bold" fill="darkblue">Title: </tspan>
    <tspan font-style="italic" text-decoration="underline" fill="blue">Subtitle</tspan>
    <tspan x="10" y="60" font-family="Courier" fill="green">Code: </tspan>
    <tspan font-family="Courier" font-size="10" fill="darkgreen">function() { return true; }</tspan>
    <tspan x="10" y="90" font-variant="small-caps" letter-spacing="2">Small Caps</tspan>
    <tspan x="10" y="120" word-spacing="4" fill="purple">Wide Spaced Words</tspan>
  </text>
</svg>''',

        'tspan_inheritance.svg': '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 100">
  <text x="10" y="30" font-family="Arial" font-size="14" fill="black" font-weight="normal">
    Parent text properties: 
    <tspan fill="red">Override fill only</tspan>
    <tspan font-weight="bold">Override weight only</tspan>
    <tspan>Inherit all parent properties</tspan>
  </text>
</svg>''',

        # Image samples (Critical Priority)
        'image_embedded.svg': '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">
  <image x="10" y="10" width="100" height="80" href="test.jpg"/>
</svg>''',
        
        'image_base64.svg': '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">
  <image x="50" y="50" width="50" height="50" 
         href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="/>
</svg>''',

        'image_xlink_href.svg': '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 200 200">
  <image x="20" y="20" width="80" height="60" xlink:href="legacy.png"/>
</svg>''',

        'image_with_transforms.svg': '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 300">
  <image x="50" y="50" width="100" height="100" href="rotated.jpg" 
         transform="rotate(15, 100, 100) scale(0.8)"/>
  <image x="150" y="150" width="80" height="80" href="scaled.png" 
         transform="translate(10, 10)"/>
</svg>''',

        'image_opacity_clipping.svg': '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 250 250">
  <defs>
    <clipPath id="circle-clip">
      <circle cx="75" cy="75" r="40"/>
    </clipPath>
  </defs>
  <image x="25" y="25" width="100" height="100" href="clipped.jpg" 
         clip-path="url(#circle-clip)" opacity="0.7"/>
</svg>''',

        # Symbol and Use samples
        'symbol_use_reusable.svg': '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">
  <defs>
    <symbol id="star" viewBox="0 0 20 20">
      <path d="M10,2 L12,8 L18,8 L13,12 L15,18 L10,14 L5,18 L7,12 L2,8 L8,8 Z" fill="gold"/>
    </symbol>
  </defs>
  <use href="#star" x="50" y="50" width="30" height="30"/>
  <use href="#star" x="100" y="100" width="20" height="20"/>
</svg>''',

        'symbol_complex.svg': '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 200">
  <defs>
    <symbol id="arrow" viewBox="0 0 40 20">
      <path d="M0,10 L30,10 M25,5 L30,10 L25,15" stroke="black" stroke-width="2" fill="none"/>
    </symbol>
  </defs>
  <use href="#arrow" x="50" y="50" transform="rotate(0)"/>
  <use href="#arrow" x="150" y="50" transform="rotate(45, 170, 60)"/>
  <use href="#arrow" x="50" y="120" transform="rotate(90, 60, 130)"/>
</svg>''',

        # Pattern samples
        'pattern_dots.svg': '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">
  <defs>
    <pattern id="dots" patternUnits="userSpaceOnUse" width="20" height="20">
      <circle cx="10" cy="10" r="3" fill="black"/>
    </pattern>
  </defs>
  <rect x="50" y="50" width="100" height="80" fill="url(#dots)"/>
</svg>''',

        'pattern_stripes.svg': '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">
  <defs>
    <pattern id="stripes" patternUnits="userSpaceOnUse" width="10" height="10">
      <rect width="5" height="10" fill="red"/>
      <rect x="5" width="5" height="10" fill="blue"/>
    </pattern>
  </defs>
  <ellipse cx="100" cy="100" rx="60" ry="40" fill="url(#stripes)"/>
</svg>''',

        # Filter effects samples
        'filter_gaussian_blur.svg': '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">
  <defs>
    <filter id="blur">
      <feGaussianBlur in="SourceGraphic" stdDeviation="3"/>
    </filter>
  </defs>
  <circle cx="100" cy="100" r="40" fill="blue" filter="url(#blur)"/>
</svg>''',

        'filter_drop_shadow.svg': '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">
  <defs>
    <filter id="shadow">
      <feDropShadow dx="3" dy="3" stdDeviation="2" flood-color="black" flood-opacity="0.3"/>
    </filter>
  </defs>
  <rect x="50" y="50" width="100" height="60" fill="red" filter="url(#shadow)"/>
</svg>''',

        'filter_drop_shadow_variations.svg': '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300">
  <defs>
    <filter id="light-shadow">
      <feDropShadow dx="1" dy="1" stdDeviation="1" flood-color="gray" flood-opacity="0.2"/>
    </filter>
    <filter id="heavy-shadow">
      <feDropShadow dx="5" dy="5" stdDeviation="3" flood-color="black" flood-opacity="0.6"/>
    </filter>
    <filter id="colored-shadow">
      <feDropShadow dx="2" dy="2" stdDeviation="2" flood-color="blue" flood-opacity="0.4"/>
    </filter>
    <filter id="offset-shadow">
      <feDropShadow dx="8" dy="-3" stdDeviation="1" flood-color="red" flood-opacity="0.5"/>
    </filter>
  </defs>
  
  <rect x="50" y="50" width="80" height="40" fill="lightblue" filter="url(#light-shadow)"/>
  <circle cx="250" cy="70" r="30" fill="yellow" filter="url(#heavy-shadow)"/>
  <ellipse cx="120" cy="150" rx="40" ry="25" fill="green" filter="url(#colored-shadow)"/>
  <polygon points="300,120 340,140 320,180 280,160" fill="orange" filter="url(#offset-shadow)"/>
</svg>''',

        'filter_drop_shadow_text.svg': '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 150">
  <defs>
    <filter id="text-shadow">
      <feDropShadow dx="2" dy="2" stdDeviation="1" flood-color="black" flood-opacity="0.4"/>
    </filter>
    <filter id="glow-shadow">
      <feDropShadow dx="0" dy="0" stdDeviation="3" flood-color="white" flood-opacity="0.8"/>
    </filter>
  </defs>
  
  <text x="50" y="50" font-family="Arial" font-size="24" font-weight="bold" 
        fill="darkblue" filter="url(#text-shadow)">Shadowed Text</text>
  <text x="50" y="100" font-family="Arial" font-size="20" 
        fill="darkred" filter="url(#glow-shadow)">Glowing Text</text>
</svg>''',

        'filter_drop_shadow_complex.svg': '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 200">
  <defs>
    <filter id="multi-shadow" x="-50%" y="-50%" width="200%" height="200%">
      <feDropShadow dx="2" dy="2" stdDeviation="1" flood-color="red" flood-opacity="0.3" result="shadow1"/>
      <feDropShadow dx="-2" dy="-2" stdDeviation="1" flood-color="blue" flood-opacity="0.3" result="shadow2"/>
    </filter>
  </defs>
  
  <g filter="url(#multi-shadow)">
    <rect x="50" y="50" width="80" height="60" fill="white" stroke="black" stroke-width="2"/>
    <text x="90" y="85" text-anchor="middle" font-family="Arial" font-size="14" fill="black">Multi Shadow</text>
  </g>
</svg>''',

        # Style element samples
        'style_css_classes.svg': '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">
  <style>
    .red-circle { fill: red; stroke: black; stroke-width: 2; }
    .blue-rect { fill: blue; opacity: 0.7; }
    #special { fill: green; transform: rotate(45deg); }
  </style>
  <circle class="red-circle" cx="100" cy="50" r="30"/>
  <rect class="blue-rect" x="50" y="100" width="60" height="40"/>
  <polygon id="special" points="150,150 170,120 190,150"/>
</svg>''',

        # Nested SVG samples
        'nested_svg.svg': '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">
  <svg x="50" y="50" width="100" height="100" viewBox="0 0 50 50">
    <rect x="10" y="10" width="30" height="30" fill="blue"/>
  </svg>
  <circle cx="150" cy="150" r="20" fill="green"/>
</svg>''',

        # Comprehensive test combining multiple missing elements
        'comprehensive_missing.svg': '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300">
  <style>
    .highlight { fill: yellow; stroke: red; }
  </style>
  <defs>
    <pattern id="grid" patternUnits="userSpaceOnUse" width="20" height="20">
      <path d="M 20 0 L 0 0 0 20" fill="none" stroke="gray" stroke-width="1"/>
    </pattern>
    <filter id="glow">
      <feGaussianBlur stdDeviation="4" result="coloredBlur"/>
      <feDropShadow dx="2" dy="2" stdDeviation="2"/>
    </filter>
    <symbol id="icon">
      <circle r="8" fill="orange"/>
      <text y="4" text-anchor="middle" font-size="10">!</text>
    </symbol>
  </defs>
  
  <rect x="10" y="10" width="380" height="280" fill="url(#grid)" opacity="0.3"/>
  <polyline points="50,50 100,30 150,70 200,40 250,80" stroke="blue" stroke-width="3" fill="none"/>
  
  <text x="50" y="120" class="highlight">
    <tspan font-weight="bold">Bold</tspan> <tspan font-style="italic">Italic</tspan>
  </text>
  
  <use href="#icon" x="300" y="50"/>
  <use href="#icon" x="320" y="70"/>
  
  <image x="50" y="150" width="80" height="60" href="sample.png"/>
  
  <rect x="200" y="150" width="100" height="80" fill="purple" filter="url(#glow)"/>
  
  <svg x="320" y="150" width="60" height="60" viewBox="0 0 30 30">
    <circle cx="15" cy="15" r="10" fill="pink"/>
  </svg>
</svg>'''
    }
    
    # Get current directory
    current_dir = Path(__file__).parent
    
    # Create sample files
    for filename, content in samples.items():
        file_path = current_dir / filename
        file_path.write_text(content, encoding='utf-8')
        print(f"Created: {filename}")
    
    print(f"\nGenerated {len(samples)} SVG sample files in {current_dir}")
    
    # Create README
    readme_content = '''# SVG Sample Files for Missing Elements Testing

This directory contains comprehensive SVG sample files for testing the 10 critical missing SVG elements:

## Elements Covered:

1. **polyline** - Multi-point line elements
   - polyline_basic.svg - Simple polyline
   - polyline_complex.svg - Complex polyline with styling

2. **tspan** - Text span elements for rich text formatting
   - tspan_styling.svg - Basic tspan styling
   - tspan_nested.svg - Nested tspan elements

3. **image** - Embedded image elements
   - image_embedded.svg - External image reference
   - image_base64.svg - Base64 encoded image

4. **symbol + use** - Reusable graphics definitions
   - symbol_use_reusable.svg - Basic symbol and use
   - symbol_complex.svg - Complex symbol with transforms

5. **pattern** - Pattern fills and strokes
   - pattern_dots.svg - Dot pattern fill
   - pattern_stripes.svg - Stripe pattern fill

6. **feGaussianBlur** - Gaussian blur filter effect
   - filter_gaussian_blur.svg - Basic blur effect

7. **feDropShadow** - Drop shadow filter effect
   - filter_drop_shadow.svg - Drop shadow effect

8. **style** - CSS stylesheet elements
   - style_css_classes.svg - CSS classes and selectors

9. **svg** - Nested SVG elements
   - nested_svg.svg - SVG within SVG

10. **defs** - Definition containers (used in multiple samples above)

## Special Files:

- **comprehensive_missing.svg** - Combines multiple missing elements for integration testing
- **generate_samples.py** - This script for regenerating samples

## Usage:

These files are used by the test suite in `test_missing_svg_elements.py` to validate
parsing, conversion, and PPTX output generation for missing SVG elements.
'''
    
    readme_path = current_dir / 'README.md'
    readme_path.write_text(readme_content, encoding='utf-8')
    print(f"Created: README.md")

if __name__ == "__main__":
    create_svg_samples()