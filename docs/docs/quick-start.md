---
sidebar_position: 3
---

# Quick Start

Get up and running with SVG2PPTX in minutes. This guide covers the most common use cases to help you start converting SVG files to PowerPoint presentations.

## Your First Conversion

Let's start with a simple SVG to PPTX conversion:

```python
from svg2pptx import convert_svg_to_pptx

# Convert SVG file to PowerPoint
convert_svg_to_pptx('my_diagram.svg', 'presentation.pptx')
```

That's it! Your SVG is now a PowerPoint presentation.

## Basic Usage Patterns

### Command Line Interface

SVG2PPTX includes a command-line tool:

```bash
# Basic conversion
svg2pptx input.svg output.pptx

# With options
svg2pptx input.svg output.pptx --title "My Presentation" --optimize

# Batch conversion
svg2pptx *.svg --output-dir presentations/
```

### Python Script

```python
import svg2pptx

# Simple conversion
svg2pptx.convert_svg_to_pptx(
    input_file='chart.svg',
    output_file='chart_presentation.pptx'
)

# With basic options
svg2pptx.convert_svg_to_pptx(
    input_file='diagram.svg',
    output_file='diagram.pptx',
    title='Technical Diagram',
    author='Your Name'
)
```

## Multi-Slide Conversion

Convert complex SVGs with multiple sections into multi-slide presentations:

```python
from svg2pptx import MultiSlideConverter

# Create converter with multi-slide detection
converter = MultiSlideConverter(
    enable_multislide_detection=True,
    animation_threshold=3
)

# Convert with automatic slide detection
result = converter.convert_svg_to_pptx(
    'complex_diagram.svg',
    'multi_slide_presentation.pptx',
    options={
        'title': 'Process Flow',
        'slide_titles': {
            '1': 'Overview',
            '2': 'Details',
            '3': 'Summary'
        }
    }
)

print(f"Created {result['slide_count']} slides")
print(f"Strategy used: {result['strategy']}")
```

## Preprocessing for Better Results

Enable preprocessing to optimize your SVG before conversion:

```python
from svg2pptx import convert_svg_to_pptx
from svg2pptx.preprocessing import create_optimizer

# Create preprocessor
optimizer = create_optimizer(
    precision=3,           # Decimal places for numbers
    remove_empty=True,     # Remove empty elements
    optimize_paths=True,   # Simplify path data
    merge_paths=False      # Keep paths separate
)

# Convert with preprocessing
convert_svg_to_pptx(
    'complex.svg',
    'optimized.pptx',
    preprocessor=optimizer
)
```

## Working with Different SVG Types

### Simple Graphics

Perfect for icons, logos, and basic diagrams:

```python
# Icons and logos
svg2pptx.convert_svg_to_pptx('logo.svg', 'logo_slide.pptx')

# Charts and graphs  
svg2pptx.convert_svg_to_pptx('sales_chart.svg', 'quarterly_report.pptx')
```

### Complex Illustrations

Handle detailed graphics with many elements:

```python
from svg2pptx.preprocessing import create_optimizer

# Optimize for complex graphics
optimizer = create_optimizer(
    precision=2,                    # Lower precision
    remove_hidden_elements=True,    # Remove invisible elements
    simplify_transforms=True,       # Simplify transformations
    optimize_viewbox=True          # Optimize coordinate systems
)

svg2pptx.convert_svg_to_pptx(
    'detailed_illustration.svg',
    'illustration_presentation.pptx',
    preprocessor=optimizer
)
```

### Technical Diagrams

Maintain precision for engineering or architectural drawings:

```python
# High precision for technical content
converter = MultiSlideConverter()
result = converter.convert_svg_to_pptx(
    'technical_drawing.svg',
    'engineering_presentation.pptx',
    options={
        'preserve_precision': True,
        'maintain_coordinates': True,
        'title': 'Technical Specifications'
    }
)
```

## Batch Processing

Convert multiple SVG files at once:

```python
from pathlib import Path
from svg2pptx import MultiSlideConverter

# Setup
converter = MultiSlideConverter()
svg_files = list(Path('svg_folder').glob('*.svg'))

# Convert each SVG to its own PPTX
for svg_file in svg_files:
    output_file = Path('presentations') / f'{svg_file.stem}.pptx'
    converter.convert_svg_to_pptx(str(svg_file), str(output_file))

print(f"Converted {len(svg_files)} files")
```

### Combine Multiple SVGs into One Presentation

```python
from svg2pptx import convert_multiple_svgs_to_pptx

# List of SVG files
svg_files = [
    'intro.svg',
    'main_content.svg', 
    'conclusion.svg'
]

# Create single presentation
result = convert_multiple_svgs_to_pptx(
    svg_files,
    'combined_presentation.pptx',
    title='Complete Presentation',
    slide_titles={
        '1': 'Introduction',
        '2': 'Main Content', 
        '3': 'Conclusion'
    }
)

print(f"Combined presentation has {result['slide_count']} slides")
```

## Error Handling

Handle conversion errors gracefully:

```python
from svg2pptx import convert_svg_to_pptx
from svg2pptx.exceptions import SVGConversionError, PPTXGenerationError

try:
    convert_svg_to_pptx('input.svg', 'output.pptx')
    print("Conversion successful!")
    
except FileNotFoundError:
    print("SVG file not found")
    
except SVGConversionError as e:
    print(f"SVG conversion failed: {e}")
    
except PPTXGenerationError as e:
    print(f"PowerPoint generation failed: {e}")
    
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Configuration Examples

### Custom Settings

```python
from svg2pptx import convert_svg_to_pptx

# Custom slide dimensions (16:9 aspect ratio)
convert_svg_to_pptx(
    'diagram.svg',
    'widescreen.pptx',
    slide_width=1920,   # pixels
    slide_height=1080,  # pixels
    dpi=96             # dots per inch
)

# Custom styling
convert_svg_to_pptx(
    'chart.svg',
    'styled.pptx',
    background_color='#F5F5F5',  # Light gray background
    default_font='Arial',        # Default font family
    preserve_fonts=True         # Try to preserve original fonts
)
```

### Performance Optimization

```python
from svg2pptx import MultiSlideConverter

# Performance-focused settings
converter = MultiSlideConverter(
    enable_multislide_detection=False,  # Skip if not needed
    animation_threshold=10              # Higher threshold
)

# Optimize for speed
result = converter.convert_svg_to_pptx(
    'large_file.svg',
    'fast_conversion.pptx',
    options={
        'low_quality_mode': True,    # Faster but lower quality
        'simplify_gradients': True,  # Convert complex gradients
        'rasterize_complex': True,   # Rasterize very complex elements
        'max_shapes_per_slide': 100  # Limit complexity
    }
)
```

## Validation and Quality Checks

Ensure your conversions are successful:

```python
from svg2pptx import convert_svg_to_pptx
from svg2pptx.validation import validate_pptx

# Convert with validation
convert_svg_to_pptx('input.svg', 'output.pptx')

# Validate the result
validation_result = validate_pptx('output.pptx')

if validation_result.is_valid:
    print("✅ PPTX file is valid")
    print(f"Slides: {validation_result.slide_count}")
    print(f"Elements: {validation_result.element_count}")
else:
    print("❌ PPTX file has issues:")
    for error in validation_result.errors:
        print(f"  - {error}")
```

## Next Steps

Now that you've got the basics down:

- **[User Guide](user-guide/basic-usage)** - Learn advanced features
- **[Multi-slide Guide](user-guide/multi-slide)** - Master multi-slide conversion
- **[Contributing Guide](contributing)** - Optimize your SVGs and contribute
- **[API Reference](api/core-functions)** - Detailed function documentation

## Common Questions

**Q: Can I convert animated SVGs?**
A: Yes! SVG2PPTX can detect animation sequences and convert them to multiple slides.

**Q: What about SVGs with external images?**
A: External images are embedded automatically if accessible, or you'll get a warning.

**Q: How do I handle very large SVG files?**
A: Use preprocessing to optimize the SVG first, or enable streaming mode for better memory usage.

**Q: Can I customize the PowerPoint template?**
A: Yes, you can provide your own PPTX template file as a starting point.

Ready to dive deeper? Check out the [User Guide](user-guide/basic-usage) for comprehensive coverage of all features!