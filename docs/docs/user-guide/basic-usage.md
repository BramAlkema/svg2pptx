---
sidebar_position: 1
---

# Basic Usage

Learn the fundamental features of SVG2PPTX and how to use them effectively in your projects.

## Core Functions

SVG2PPTX provides several main functions for different use cases:

### `convert_svg_to_pptx()`

The primary function for single SVG to PPTX conversion:

```python
from svg2pptx import convert_svg_to_pptx

# Basic usage
convert_svg_to_pptx('input.svg', 'output.pptx')

# With options
convert_svg_to_pptx(
    input_file='diagram.svg',
    output_file='presentation.pptx',
    title='My Presentation',
    author='John Doe',
    subject='Technical Documentation'
)
```

**Parameters:**
- `input_file`: Path to SVG file
- `output_file`: Path for output PPTX file  
- `title`: Presentation title (optional)
- `author`: Presentation author (optional)
- `subject`: Presentation subject (optional)

### Working with SVG Elements

SVG2PPTX supports a wide range of SVG elements:

#### Basic Shapes

```xml
<!-- Rectangle -->
<rect x="10" y="10" width="100" height="50" fill="blue"/>

<!-- Circle -->
<circle cx="50" cy="50" r="25" stroke="red" fill="none"/>

<!-- Ellipse -->
<ellipse cx="75" cy="50" rx="30" ry="20" fill="green"/>

<!-- Line -->
<line x1="0" y1="0" x2="100" y2="100" stroke="black"/>

<!-- Polygon -->
<polygon points="50,5 100,50 50,95 5,50" fill="yellow"/>
```

#### Advanced Graphics

```xml
<!-- Path with curves -->
<path d="M10,10 C20,20 40,20 50,10 S80,0 90,10" stroke="purple" fill="none"/>

<!-- Text -->
<text x="20" y="35" font-family="Arial" font-size="16" fill="black">
  Hello World
</text>

<!-- Groups -->
<g transform="translate(100,100)">
  <rect x="0" y="0" width="50" height="30" fill="lightblue"/>
  <text x="25" y="20" text-anchor="middle">Label</text>
</g>
```

## Coordinate Systems and Transforms

SVG2PPTX handles various coordinate systems and transformations:

### ViewBox and Viewport

```python
# SVG with viewBox is automatically scaled to fit slide
convert_svg_to_pptx('scalable.svg', 'fitted.pptx')

# Custom slide dimensions
convert_svg_to_pptx(
    'diagram.svg', 
    'custom_size.pptx',
    slide_width=1920,  # 16:9 widescreen
    slide_height=1080
)
```

### Transform Handling

SVG transforms are converted to PowerPoint equivalents:

```xml
<!-- Supported transforms -->
<g transform="translate(50,50)">
  <rect transform="rotate(45)" width="30" height="30" fill="red"/>
  <circle transform="scale(2)" r="10" fill="blue"/>
</g>

<!-- Matrix transforms -->
<path transform="matrix(1,0,0,1,10,10)" d="M0,0 L10,10"/>
```

## Styling and Appearance

### Fill and Stroke

```python
# SVG with various fills
svg_content = '''
<svg viewBox="0 0 200 100">
  <!-- Solid colors -->
  <rect x="10" y="10" width="30" height="30" fill="red"/>
  
  <!-- Gradients -->
  <defs>
    <linearGradient id="grad1">
      <stop offset="0%" stop-color="blue"/>
      <stop offset="100%" stop-color="green"/>
    </linearGradient>
  </defs>
  <rect x="50" y="10" width="30" height="30" fill="url(#grad1)"/>
  
  <!-- Patterns -->
  <rect x="90" y="10" width="30" height="30" stroke="black" stroke-width="2" fill="none"/>
</svg>
'''

# Convert to PPTX
with open('styled.svg', 'w') as f:
    f.write(svg_content)
convert_svg_to_pptx('styled.svg', 'styled_presentation.pptx')
```

### CSS Styles

SVG2PPTX processes both inline styles and CSS:

```xml
<svg>
  <style>
    .header { font-size: 18px; font-weight: bold; fill: navy; }
    .body-text { font-size: 12px; fill: black; }
  </style>
  
  <text x="10" y="20" class="header">Title</text>
  <text x="10" y="40" class="body-text">Body text</text>
</svg>
```

## Error Handling and Validation

### Graceful Error Handling

```python
from svg2pptx import convert_svg_to_pptx
from svg2pptx.exceptions import SVGConversionError

try:
    result = convert_svg_to_pptx(
        'problematic.svg', 
        'output.pptx',
        strict_mode=False  # More forgiving
    )
    print("Conversion completed successfully")
    
except FileNotFoundError as e:
    print(f"File not found: {e}")
    
except SVGConversionError as e:
    print(f"Conversion error: {e}")
    print(f"Failed at element: {e.element_info}")
    
except Exception as e:
    print(f"Unexpected error: {e}")
```

### Validation and Quality Checks

```python
from svg2pptx.validation import validate_svg, validate_pptx

# Validate SVG before conversion
svg_validation = validate_svg('input.svg')
if not svg_validation.is_valid:
    print("SVG issues found:")
    for warning in svg_validation.warnings:
        print(f"  ⚠️  {warning}")

# Convert
convert_svg_to_pptx('input.svg', 'output.pptx')

# Validate PPTX after conversion  
pptx_validation = validate_pptx('output.pptx')
print(f"Generated {pptx_validation.slide_count} slides")
print(f"Total elements: {pptx_validation.element_count}")
```

## Configuration Options

### Global Configuration

```python
from svg2pptx.config import SVGConfig

# Create custom configuration
config = SVGConfig(
    default_font_family='Arial',
    default_font_size=12,
    preserve_aspect_ratio=True,
    max_image_resolution=300,  # DPI
    enable_text_to_path_fallback=True
)

# Use configuration
convert_svg_to_pptx(
    'input.svg', 
    'output.pptx',
    config=config
)
```

### Per-Conversion Options

```python
# Detailed conversion options
convert_svg_to_pptx(
    'complex.svg',
    'detailed.pptx',
    
    # Slide properties
    title='Complex Diagram',
    author='Designer',
    
    # Quality settings
    image_quality=95,        # JPEG quality for rasterized elements
    vector_precision=3,      # Decimal places for coordinates
    
    # Conversion behavior
    fallback_to_image=True,  # Rasterize unsupported elements
    preserve_text=True,      # Keep text as text (not paths)
    embed_fonts=False,       # Don't embed fonts
    
    # Performance
    optimize_output=True,    # Optimize final PPTX
    max_shapes_per_slide=500 # Split complex slides
)
```

## Font Handling

### Font Mapping

```python
# Custom font mapping
font_map = {
    'MyCustomFont': 'Arial',     # Map custom to standard
    'serif': 'Times New Roman',  # Generic to specific
    'sans-serif': 'Calibri'      # Default mapping
}

convert_svg_to_pptx(
    'text_heavy.svg',
    'fonts_mapped.pptx',
    font_mapping=font_map
)
```

### Text-to-Path Conversion

For precise text rendering when fonts aren't available:

```python
convert_svg_to_pptx(
    'precise_text.svg',
    'text_as_paths.pptx',
    convert_text_to_paths=True,  # Convert all text to vector paths
    preserve_text_searchability=False
)
```

## Working with Large Files

### Memory Management

```python
from svg2pptx import convert_svg_to_pptx
from svg2pptx.preprocessing import create_optimizer

# Optimize for large files
optimizer = create_optimizer(
    precision=2,                    # Reduce precision
    remove_tiny_elements=True,      # Remove very small elements
    simplify_paths=True,           # Simplify complex paths
    max_path_complexity=1000       # Limit path complexity
)

# Convert with optimization
convert_svg_to_pptx(
    'large_file.svg',
    'optimized_output.pptx',
    preprocessor=optimizer,
    streaming_mode=True,           # Process in chunks
    max_memory_mb=512             # Memory limit
)
```

### Progress Monitoring

```python
def progress_callback(stage, progress, message):
    print(f"{stage}: {progress:.1%} - {message}")

convert_svg_to_pptx(
    'complex.svg',
    'monitored.pptx',
    progress_callback=progress_callback
)
```

## Best Practices

### 1. SVG Preparation

- **Use standard SVG elements** for better compatibility
- **Avoid external dependencies** (external stylesheets, fonts)
- **Test with simple SVGs first** before complex ones
- **Validate SVG** before conversion

### 2. Performance Optimization

- **Preprocess large files** to reduce complexity
- **Use appropriate precision** - don't over-specify coordinates
- **Consider rasterization** for very complex elements
- **Monitor memory usage** with large batches

### 3. Quality Assurance

- **Validate output** after conversion
- **Test in PowerPoint** - open and check the result
- **Compare visual output** with original SVG
- **Handle errors gracefully** in automated workflows

### 4. Production Usage

```python
import logging
from svg2pptx import convert_svg_to_pptx

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def production_convert(svg_file, pptx_file):
    """Production-ready conversion with full error handling."""
    try:
        # Validate input
        if not os.path.exists(svg_file):
            raise FileNotFoundError(f"SVG file not found: {svg_file}")
            
        # Convert with robust settings
        result = convert_svg_to_pptx(
            svg_file,
            pptx_file,
            strict_mode=False,           # Forgiving mode
            fallback_to_image=True,      # Rasterize if needed
            optimize_output=True,        # Optimize result
            validate_output=True         # Validate after conversion
        )
        
        logger.info(f"Successfully converted {svg_file} to {pptx_file}")
        return result
        
    except Exception as e:
        logger.error(f"Conversion failed for {svg_file}: {e}")
        raise
```

## Next Steps

- **[Multi-slide Conversion](multi-slide)** - Create presentations with multiple slides  
- **[Contributing](../contributing)** - Development and extending functionality
- **[API Reference](../api/core-functions)** - Detailed function documentation