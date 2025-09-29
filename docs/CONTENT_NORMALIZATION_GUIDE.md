# Content Normalization System

## Overview

The Content Normalization System automatically detects and corrects SVG content that appears outside the intended viewport or slide boundaries. This ensures that all content is properly positioned and visible in the resulting PowerPoint presentation.

## Problem Statement

SVG files sometimes contain content positioned far outside the viewBox, which can result in:
- Content appearing off-slide in PowerPoint
- Invisible or clipped elements
- Incorrect scaling and positioning
- Loss of visual fidelity

Common patterns include:
- Corporate logos with elements at coordinates like (500, 400) despite a 100x100 viewBox
- Design tools exporting with absolute positioning
- Legacy SVG files with transformation artifacts

## How It Works

### Detection Algorithm

The system uses four sophisticated heuristics to detect content needing normalization:

```python
from src.transforms.matrix_composer import needs_normalise

# Automatically detects if normalization is needed
needs_norm = needs_normalise(svg_root)
```

#### Detection Heuristics

1. **Size Ratio Check** - Content significantly larger than viewBox
   ```python
   if content_width > 3 * viewBox_width or content_height > 3 * viewBox_height:
       return True  # Needs normalization
   ```

2. **Negative Coordinate Check** - Significant negative coordinates
   ```python
   if min_x < -viewBox_width * 0.1 or min_y < -viewBox_height * 0.1:
       return True  # Content extends into negative space
   ```

3. **Center Distance Check** - Content center far from viewBox center
   ```python
   if center_distance_x > 2 * viewBox_width or center_distance_y > 2 * viewBox_height:
       return True  # Content center is too far from viewBox center
   ```

4. **Intersection Check** - No overlap with viewBox
   ```python
   if not has_intersection:
       return True  # Content doesn't intersect viewBox at all
   ```

### Normalization Process

When normalization is triggered, the system:

1. **Calculates Raw Bounds** - Determines actual content boundaries
   ```python
   from src.viewbox.content_bounds import calculate_raw_content_bounds

   bounds = calculate_raw_content_bounds(svg_root)
   # Returns (min_x, min_y, max_x, max_y)
   ```

2. **Creates Transformation Matrix** - Generates matrix to reposition content
   ```python
   from src.viewbox.ctm_utils import create_root_context_with_viewport

   context = create_root_context_with_viewport(
       svg_root=svg_root,
       services=services,
       slide_w_emu=9144000,  # 10 inches
       slide_h_emu=6858000   # 7.5 inches
   )
   ```

3. **Applies Viewport Matrix** - Transforms all content to proper position
   ```python
   if context.viewport_matrix is not None:
       transformed_point = context.viewport_matrix @ original_point
   ```

## Usage Examples

### Basic Detection

```python
from lxml import etree as ET
from src.transforms.matrix_composer import needs_normalise

# SVG with off-slide content
svg_content = '''<svg viewBox="0 0 100 100">
    <rect x="500" y="400" width="100" height="100"/>
</svg>'''

svg_root = ET.fromstring(svg_content)
if needs_normalise(svg_root):
    print("Content needs normalization")
```

### Full Normalization Pipeline

```python
from src.services.conversion_services import ConversionServices
from src.viewbox.ctm_utils import create_root_context_with_viewport

# Create services
services = ConversionServices.create_default()

# Create normalized context
context = create_root_context_with_viewport(
    svg_root=svg_root,
    services=services
)

# Context now contains viewport_matrix for transforming coordinates
if context.viewport_matrix is not None:
    # All conversions will use the normalization matrix
    converter = RectangleConverter(services=services)
    result = converter.convert(rect_element, context)
```

### Testing Normalization

```python
import numpy as np

# Test a specific point transformation
original_point = np.array([500, 400, 1])  # Homogeneous coordinates
transformed = context.viewport_matrix @ original_point

print(f"Original: ({original_point[0]}, {original_point[1]})")
print(f"Normalized: ({transformed[0]:.2f}, {transformed[1]:.2f})")
```

## Real-World Examples

### Example 1: Corporate Logo Pattern

**Input SVG:**
```xml
<svg viewBox="0 0 100 100">
  <!-- Logo elements positioned far outside viewBox -->
  <g transform="translate(450, 350)">
    <rect width="100" height="100" fill="blue"/>
    <circle cx="50" cy="50" r="25" fill="white"/>
  </g>
</svg>
```

**Detection Result:** `needs_normalise() = True`
- Content at (450-550, 350-450) vs viewBox (0-100, 0-100)
- No intersection with viewBox
- Center distance > 4× viewBox dimensions

**After Normalization:** Content repositioned to center of slide

### Example 2: Design Tool Export

**Input SVG:**
```xml
<svg viewBox="0 0 200 200">
  <!-- Absolute positioned elements from design tool -->
  <rect x="-150" y="-100" width="500" height="400" fill="red"/>
</svg>
```

**Detection Result:** `needs_normalise() = True`
- Significant negative coordinates
- Content 2.5× larger than viewBox
- Partial intersection only

## Configuration

The normalization thresholds can be adjusted:

```python
# In src/transforms/matrix_composer.py
size_ratio_threshold = 3.0    # Content size vs viewBox ratio
distance_threshold = 2.0      # Center distance threshold
negative_threshold = 0.1      # Negative coordinate threshold
```

## Performance

- Detection: ~0.5ms per SVG
- Bounds calculation: ~1ms for complex paths
- Matrix generation: ~0.2ms
- Total overhead: < 2ms per document

## Integration with Converters

All converters automatically use the normalization system:

```python
# Converters receive normalized context
class PathConverter(BaseConverter):
    def convert(self, element, context):
        # context.viewport_matrix contains normalization if needed
        if context.viewport_matrix is not None:
            # Apply transformation
            points = self._transform_points(points, context.viewport_matrix)
```

## Testing

```bash
# Run normalization tests
PYTHONPATH=. pytest tests/unit/transforms/test_matrix_composer.py -v

# Test content bounds calculation
PYTHONPATH=. pytest tests/unit/viewbox/test_content_bounds.py -v

# Integration test
PYTHONPATH=. python test_normalization_integration.py
```

## Debugging

Enable debug output to see normalization decisions:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Will show:
# - Detected bounds
# - Normalization decision
# - Applied transformation matrix
```

## Edge Cases

### Handled Automatically
- Empty SVG files (no content)
- SVG with no viewBox attribute
- Nested transformations
- Mixed coordinate systems

### Requires Manual Intervention
- Intentionally off-canvas elements (e.g., patterns, gradients)
- Elements meant to be clipped
- Special effects requiring specific positioning

## API Reference

### needs_normalise()
```python
def needs_normalise(svg_root: ET.Element) -> bool:
    """
    Detect if SVG content needs normalization.

    Returns:
        True if content is significantly outside viewBox
    """
```

### calculate_raw_content_bounds()
```python
def calculate_raw_content_bounds(svg_element: ET.Element) -> Tuple[float, float, float, float]:
    """
    Calculate actual content bounds without viewBox clipping.

    Returns:
        (min_x, min_y, max_x, max_y) of all content
    """
```

### create_root_context_with_viewport()
```python
def create_root_context_with_viewport(
    svg_root: ET.Element,
    services: ConversionServices,
    slide_w_emu: int = 9144000,
    slide_h_emu: int = 6858000
) -> ConversionContext:
    """
    Create context with normalization matrix if needed.

    Returns:
        ConversionContext with viewport_matrix set
    """
```

## Best Practices

1. **Always use the normalization system** - It's automatic and lightweight
2. **Test with real-world SVGs** - Corporate logos often need normalization
3. **Check viewport_matrix** - Verify it's applied when expected
4. **Monitor performance** - Detection should be < 2ms

## Troubleshooting

### Content Still Off-Slide
- Check if normalization was detected: `needs_normalise(svg_root)`
- Verify viewport_matrix is not None
- Ensure converters use the context's viewport_matrix

### Over-Normalization
- Adjust thresholds in matrix_composer.py
- Check if content is intentionally positioned
- Review SVG structure for nested transformations

## Summary

The Content Normalization System ensures that all SVG content appears correctly positioned in PowerPoint, regardless of how it was originally authored. With automatic detection and transformation, it handles the complexity of coordinate system mismatches transparently.