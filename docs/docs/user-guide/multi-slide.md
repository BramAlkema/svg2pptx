---
sidebar_position: 3
---

# Multi-slide Conversion

Learn how to create PowerPoint presentations with multiple slides from complex SVG documents or multiple SVG files.

## Overview

SVG2PPTX can automatically detect slide boundaries within a single SVG document or combine multiple SVG files into a cohesive presentation. This is particularly useful for:

- **Process diagrams** with multiple steps
- **Animation sequences** converted to slide progressions  
- **Layered illustrations** with different views
- **Document sections** that should be separate slides
- **Batch processing** multiple related SVGs

## Automatic Slide Detection

### Basic Multi-slide Conversion

```python
from svg2pptx import MultiSlideConverter

# Create converter with slide detection enabled
converter = MultiSlideConverter(
    enable_multislide_detection=True,
    animation_threshold=3  # Minimum animations for slide sequence
)

# Convert with automatic boundary detection
result = converter.convert_svg_to_pptx(
    'complex_diagram.svg',
    'multi_slide_presentation.pptx'
)

print(f"Created {result['slide_count']} slides")
print(f"Strategy used: {result['strategy']}")
print(f"Boundaries detected: {result['boundaries']}")
```

### Detection Strategies

SVG2PPTX uses several strategies to detect slide boundaries:

#### 1. Animation Sequence Detection

Converts SVG animations into slide progressions:

```xml
<svg viewBox="0 0 200 200">
  <!-- Elements with different animation timings become different slides -->
  <circle cx="50" cy="50" r="10" fill="red">
    <animate attributeName="cx" values="50;150;50" dur="3s" begin="0s"/>
  </circle>
  <rect x="100" y="100" width="20" height="20" fill="blue">
    <animate attributeName="x" values="100;50;100" dur="3s" begin="1s"/>
  </rect>
  <text x="10" y="180">
    <animate attributeName="opacity" values="0;1;0" dur="2s" begin="2s"/>
    Step-by-step animation
  </text>
</svg>
```

#### 2. Layer Group Detection

Groups with layer-like names become separate slides:

```xml
<svg viewBox="0 0 400 300">
  <!-- Each group becomes a slide -->
  <g id="layer1" class="slide-layer">
    <rect x="0" y="0" width="400" height="300" fill="lightblue"/>
    <text x="200" y="150" text-anchor="middle">Slide 1</text>
  </g>
  
  <g id="background-layer" class="slide-content">
    <rect x="0" y="0" width="400" height="300" fill="lightgreen"/>
    <text x="200" y="150" text-anchor="middle">Slide 2</text>
  </g>
  
  <g id="step-3">
    <rect x="0" y="0" width="400" height="300" fill="lightyellow"/>
    <text x="200" y="150" text-anchor="middle">Slide 3</text>
  </g>
</svg>
```

#### 3. Nested SVG Pages

Nested SVG elements with page-like dimensions:

```xml
<svg viewBox="0 0 800 600">
  <!-- Each nested SVG becomes a slide -->
  <svg x="0" y="0" width="400" height="300" id="page1">
    <rect width="400" height="300" fill="white"/>
    <text x="200" y="150" text-anchor="middle">Page 1</text>
  </svg>
  
  <svg x="400" y="0" width="400" height="300" id="page2">
    <rect width="400" height="300" fill="lightgray"/>
    <text x="200" y="150" text-anchor="middle">Page 2</text>
  </svg>
  
  <svg x="0" y="300" width="800" height="300" id="full-width-page">
    <rect width="800" height="300" fill="navy"/>
    <text x="400" y="150" text-anchor="middle" fill="white">Full Width Page</text>
  </svg>
</svg>
```

#### 4. Section Marker Detection

Text elements that look like section headers:

```xml
<svg viewBox="0 0 600 800">
  <!-- Large text elements become slide boundaries -->
  <text x="50" y="50" font-size="24" font-weight="bold">Introduction</text>
  <text x="50" y="80" font-size="14">This is the intro content...</text>
  
  <text x="50" y="200" font-size="24" font-weight="bold">Main Content</text>
  <text x="50" y="230" font-size="14">This is the main content...</text>
  
  <text x="50" y="400" font-size="24" font-weight="bold">Conclusion</text>
  <text x="50" y="430" font-size="14">This is the conclusion...</text>
</svg>
```

## Explicit Slide Boundaries

For precise control, use explicit slide boundary markers:

### Data Attributes

```xml
<svg viewBox="0 0 400 300">
  <!-- Explicit slide breaks -->
  <g data-slide-break="true" data-slide-title="Overview">
    <rect x="0" y="0" width="400" height="300" fill="lightblue"/>
    <text x="200" y="150" text-anchor="middle">Overview Slide</text>
  </g>
  
  <g data-slide-break="true" data-slide-title="Details">
    <rect x="0" y="0" width="400" height="300" fill="lightcoral"/>  
    <text x="200" y="150" text-anchor="middle">Details Slide</text>
  </g>
</svg>
```

### Custom Detection

```python
from svg2pptx.multislide.detection import SlideDetector, SlideType, SlideBoundary

# Create custom detector
detector = SlideDetector(
    enable_animation_detection=True,
    enable_nested_svg_detection=True,
    enable_layer_detection=True,
    animation_threshold=2  # Lower threshold
)

# Manual boundary detection
boundaries = detector.detect_boundaries(svg_element)

# Review detected boundaries
for boundary in boundaries:
    print(f"Type: {boundary.boundary_type}")
    print(f"Title: {boundary.title}")  
    print(f"Confidence: {boundary.confidence}")
    print(f"Position: {boundary.position}")
```

## Multiple SVG Files

Combine multiple SVG files into a single presentation:

### Basic Batch Conversion

```python
from svg2pptx import convert_multiple_svgs_to_pptx

# List of SVG files in order
svg_files = [
    'intro.svg',
    'overview.svg', 
    'details.svg',
    'conclusion.svg'
]

# Create combined presentation
result = convert_multiple_svgs_to_pptx(
    svg_files,
    'complete_presentation.pptx',
    title='Project Presentation',
    slide_titles={
        '1': 'Introduction',
        '2': 'Project Overview',
        '3': 'Technical Details',
        '4': 'Conclusion & Next Steps'
    }
)

print(f"Combined {len(svg_files)} files into {result['slide_count']} slides")
```

### Advanced Batch Processing

```python
from pathlib import Path
from svg2pptx import MultiSlideConverter

# Setup converter
converter = MultiSlideConverter(
    enable_multislide_detection=True,
    template_path='presentation_template.pptx'  # Optional template
)

# Process directory of SVG files
svg_directory = Path('svg_slides')
svg_files = sorted(svg_directory.glob('*.svg'))

# Convert with error handling
successful_slides = []
failed_files = []

for svg_file in svg_files:
    try:
        # Each SVG might become multiple slides
        result = converter.convert_svg_to_pptx(
            str(svg_file),
            f'temp_{svg_file.stem}.pptx'
        )
        successful_slides.extend(result.get('slides', []))
        
    except Exception as e:
        print(f"Failed to convert {svg_file}: {e}")
        failed_files.append(svg_file)

print(f"Successfully processed: {len(successful_slides)} slides")
print(f"Failed files: {len(failed_files)}")
```

## Configuration Options

### Slide Detection Settings

```python
converter = MultiSlideConverter(
    # Detection toggles
    enable_multislide_detection=True,
    enable_animation_detection=True,
    enable_nested_svg_detection=True,
    enable_layer_detection=True,
    
    # Thresholds
    animation_threshold=3,           # Min animations for sequence
    min_layer_elements=5,           # Min elements for layer detection
    section_font_size_threshold=18, # Min font size for section headers
    
    # Template
    template_path='my_template.pptx'
)
```

### Slide Generation Options

```python
result = converter.convert_svg_to_pptx(
    'complex.svg',
    'presentation.pptx',
    options={
        # Presentation metadata
        'title': 'Technical Documentation',
        'author': 'Engineering Team',
        'subject': 'System Architecture',
        
        # Slide titles
        'slide_titles': {
            '1': 'System Overview',
            '2': 'Component Details',
            '3': 'Data Flow',
            '4': 'Security Model'
        },
        
        # Generation behavior
        'include_overview_slide': True,    # Add overview slide
        'add_slide_numbers': True,         # Number slides
        'duplicate_shared_elements': False, # Reuse common elements
        
        # Quality settings
        'slide_transition': 'fade',        # Slide transition effect
        'preserve_animation_timing': True, # Keep timing info as notes
    }
)
```

## Working with Templates

### Using PowerPoint Templates

```python
from svg2pptx import MultiSlideConverter

# Use existing PowerPoint template
converter = MultiSlideConverter(
    template_path='corporate_template.pptx'
)

result = converter.convert_svg_to_pptx(
    'charts.svg',
    'branded_presentation.pptx',
    options={
        'master_slide_layout': 'Title and Content',  # Template layout
        'preserve_template_styling': True,
        'apply_template_fonts': True
    }
)
```

### Custom Slide Layouts

```python
# Define custom layouts per slide type
layout_mapping = {
    'title_slide': 'Title Slide',
    'content_slide': 'Title and Content', 
    'section_slide': 'Section Header',
    'blank_slide': 'Blank'
}

converter = MultiSlideConverter(template_path='template.pptx')
result = converter.convert_svg_to_pptx(
    'mixed_content.svg',
    'structured_presentation.pptx',
    options={
        'layout_mapping': layout_mapping,
        'auto_detect_slide_types': True
    }
)
```

## Advanced Features

### Slide Transitions and Animations

```python
# Configure slide behavior
result = converter.convert_svg_to_pptx(
    'animated.svg',
    'dynamic_presentation.pptx',
    options={
        'slide_transitions': {
            'default': 'fade',
            'section_slides': 'push',
            'detail_slides': 'wipe'
        },
        'animation_duration': 0.5,  # seconds
        'preserve_svg_animations': 'as_notes'  # Keep as slide notes
    }
)
```

### Content Distribution

```python
# Control how content is distributed across slides
converter = MultiSlideConverter(
    max_elements_per_slide=50,      # Split busy slides
    min_content_per_slide=5,        # Merge sparse slides
    balance_slide_content=True      # Even distribution
)
```

### Quality Control

```python
from svg2pptx.validation import validate_multislide_conversion

# Convert with validation
result = converter.convert_svg_to_pptx('input.svg', 'output.pptx')

# Validate the multi-slide result
validation = validate_multislide_conversion(
    original_svg='input.svg',
    generated_pptx='output.pptx',
    conversion_result=result
)

if validation.is_valid:
    print("✅ Multi-slide conversion successful")
    print(f"Quality score: {validation.quality_score:.2f}")
else:
    print("❌ Issues found:")
    for issue in validation.issues:
        print(f"  - {issue}")
```

## Best Practices

### 1. SVG Preparation for Multi-slide

- **Use consistent naming** for layers/groups (layer1, layer2, etc.)
- **Add explicit markers** when automatic detection isn't sufficient
- **Structure content logically** - group related elements
- **Test detection** before final conversion

### 2. Performance with Multiple Slides

- **Limit complexity per slide** - split very complex SVGs
- **Optimize shared elements** - reuse common graphics
- **Use appropriate precision** - don't over-specify coordinates
- **Monitor memory usage** with many slides

### 3. Quality Assurance

```python
# Comprehensive validation workflow
def validate_multislide_workflow(svg_file, output_file):
    # 1. Detect boundaries first
    detector = SlideDetector()
    boundaries = detector.detect_boundaries(svg_element)
    
    if len(boundaries) == 0:
        print("No slide boundaries detected - using single slide")
        return convert_svg_to_pptx(svg_file, output_file)
    
    # 2. Review detection strategy
    strategy = detector.recommend_conversion_strategy(boundaries)
    print(f"Recommended strategy: {strategy['strategy']}")
    print(f"Confidence: {strategy['confidence']:.2f}")
    
    if strategy['confidence'] < 0.7:
        print("Low confidence - consider manual boundaries")
    
    # 3. Convert with monitoring
    converter = MultiSlideConverter()
    result = converter.convert_svg_to_pptx(
        svg_file, output_file,
        options={'validate_output': True}
    )
    
    return result
```

### 4. Error Handling

```python
def robust_multislide_conversion(svg_file, output_file):
    try:
        converter = MultiSlideConverter()
        result = converter.convert_svg_to_pptx(svg_file, output_file)
        
        if result['slide_count'] == 1:
            print("Only one slide generated - check boundary detection")
        
        return result
        
    except Exception as e:
        print(f"Multi-slide conversion failed: {e}")
        print("Falling back to single-slide conversion...")
        
        # Fallback to single slide
        return convert_svg_to_pptx(svg_file, output_file)
```

## Troubleshooting

### Common Issues

**Issue**: No slide boundaries detected
- **Solution**: Add explicit `data-slide-break="true"` attributes
- **Check**: Layer names, animation timing, section headers

**Issue**: Too many slides generated  
- **Solution**: Increase thresholds or disable sensitive detection
- **Adjust**: `animation_threshold`, `min_layer_elements`

**Issue**: Slides have inconsistent content
- **Solution**: Use templates and standardize layouts
- **Enable**: `balance_slide_content=True`

**Issue**: Poor slide transitions
- **Solution**: Choose appropriate transition types
- **Configure**: Transition mapping per slide type

## Next Steps

- **[API Reference](../api/core-functions)** - Detailed multi-slide API
- **[Contributing](../contributing)** - Extending slide detection functionality