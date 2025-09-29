# SVG Filter Effects System v2.0.0

## Overview

The SVG2PPTX Filter Effects System provides comprehensive support for SVG filter primitives, converting them to PowerPoint DrawingML effects. This system was fully unlocked and validated with 330 passing tests, offering production-ready filter transformations.

## Architecture

### Core Components

```
src/converters/filters/
├── core/
│   ├── base.py        # Filter, FilterContext, FilterResult base classes
│   ├── registry.py    # FilterRegistry for dynamic filter discovery
│   └── chain.py       # FilterChain for composite filter operations
├── image/
│   ├── blur.py        # GaussianBlurFilter, MotionBlurFilter
│   └── color.py       # ColorMatrixFilter, color transformations
└── geometric/
    ├── transforms.py  # OffsetFilter, TurbulenceFilter
    └── morphology.py  # Morphology operations (erode, dilate)
```

## Quick Start

### Basic Usage

```python
from src.converters.filters.image.blur import GaussianBlurFilter
from src.converters.filters.core.base import FilterContext
from lxml import etree as ET

# Create filter instance
blur_filter = GaussianBlurFilter()

# Parse SVG filter element
blur_element = ET.fromstring('<feGaussianBlur stdDeviation="2"/>')

# Create context with required services
context = FilterContext(
    element=blur_element,
    viewport={'width': 100, 'height': 100},
    unit_converter=services.unit_converter,
    transform_parser=services.transform_parser,
    color_parser=services.color_parser
)

# Apply filter
result = blur_filter.apply(blur_element, context)
if result.success:
    print(result.drawingml)  # <a:blur r="50800"/>
```

## Supported Filters

### Image Filters

#### GaussianBlurFilter
Applies Gaussian blur effect to elements.

**SVG Input:**
```xml
<feGaussianBlur stdDeviation="3" edgeMode="duplicate"/>
```

**DrawingML Output:**
```xml
<a:blur r="76200"/>
```

**Parameters:**
- `stdDeviation`: Blur radius (supports anisotropic X,Y values)
- `edgeMode`: Edge handling mode (duplicate, wrap, none)

#### ColorMatrixFilter
Transforms colors using a 5x4 matrix.

**SVG Input:**
```xml
<feColorMatrix type="matrix" values="
  1 0 0 0 0
  0 1 0 0 0
  0 0 1 0 0
  0 0 0 1 0"/>
```

**DrawingML Output:**
```xml
<a:clrChange>
  <a:clrFrom>...</a:clrFrom>
  <a:clrTo>...</a:clrTo>
</a:clrChange>
```

### Geometric Filters

#### OffsetFilter
Creates drop shadows and offset effects.

**SVG Input:**
```xml
<feOffset dx="5" dy="3" in="SourceGraphic"/>
```

**DrawingML Output:**
```xml
<a:outerShdw dist="127000" dir="3100000">
  <a:srgbClr val="000000">
    <a:alpha val="50000"/>
  </a:srgbClr>
</a:outerShdw>
```

#### TurbulenceFilter
Generates noise and turbulence patterns.

**SVG Input:**
```xml
<feTurbulence baseFrequency="0.2" numOctaves="3" type="turbulence"/>
```

## Filter Registry

The system uses a registry pattern for filter discovery:

```python
from src.converters.filters.core.registry import FilterRegistry

# Create and populate registry
registry = FilterRegistry()
registry.register(GaussianBlurFilter())
registry.register(ColorMatrixFilter())
registry.register(OffsetFilter())

# Retrieve filter by type
blur = registry.get_filter('gaussian_blur')

# Get applicable filters for an element
applicable = registry.get_applicable_filters(element, context)
```

## Filter Chains

Combine multiple filters for complex effects:

```python
from src.converters.filters.core.chain import FilterChain

# Create filter chain
chain = FilterChain()
chain.add_filter(GaussianBlurFilter())
chain.add_filter(OffsetFilter())

# Apply chain to element
result = chain.apply(element, context)

# Get chain statistics
stats = chain.get_statistics()
# {'total_nodes': 2, 'filter_types': ['gaussian_blur', 'offset']}
```

## Unit Conversion

Filters use the fluent unit conversion API:

```python
from src.converters.filters.image.blur import unit

# Convert blur radius to EMUs
radius_emu = unit(f"{radius}px").to_emu()
```

## Performance Considerations

- Filters are stateless - safe for concurrent use
- Filter instances can be reused across multiple operations
- Registry caches filter lookups for performance
- Processing time typically < 1ms per filter

## Error Handling

Filters return `FilterResult` objects with success status:

```python
result = filter.apply(element, context)
if not result.success:
    print(f"Filter failed: {result.error_message}")
    print(f"Error details: {result.metadata['error']}")
```

## Testing

The filter system includes 330+ comprehensive tests:

```bash
# Run all filter tests
PYTHONPATH=. pytest tests/unit/converters/filters/ -v

# Test specific filter
PYTHONPATH=. pytest tests/unit/converters/filters/image/test_blur.py -v

# Integration tests
PYTHONPATH=. pytest tests/unit/converters/filters/test_filter_system_integration.py -v
```

## Advanced Usage

### Custom Filter Implementation

```python
from src.converters.filters.core.base import Filter, FilterResult

class CustomFilter(Filter):
    def __init__(self):
        super().__init__()
        self.filter_type = 'custom'

    def can_apply(self, element, context):
        return element.tag.endswith('feCustom')

    def apply(self, element, context):
        # Implementation
        drawingml = self._generate_effect(element)
        return FilterResult(
            success=True,
            filter_type=self.filter_type,
            drawingml=drawingml,
            metadata={'custom': 'data'}
        )
```

### Batch Processing

```python
# Process multiple elements efficiently
elements = root.xpath('.//*[starts-with(local-name(), "fe")]')
results = []

for element in elements:
    for filter in registry.list_filters():
        if filter.can_apply(element, context):
            result = filter.apply(element, context)
            results.append(result)
```

## Limitations

- Complex filter compositions may require simplification
- Some SVG filter primitives have no direct DrawingML equivalent
- Performance-intensive filters may benefit from caching

## Migration from v1.x

The v2.0.0 system uses updated method names:

```python
# Old (v1.x)
filter.can_process(element, context)
filter.process(element, context)

# New (v2.0.0)
filter.can_apply(element, context)
filter.apply(element, context)
```

## API Reference

### FilterContext

```python
FilterContext(
    element: ET.Element,           # Filter element
    viewport: Dict[str, float],    # Viewport dimensions
    unit_converter: UnitConverter, # Unit conversion service
    transform_parser: Any,         # Transform parser service
    color_parser: Any             # Color parser service
)
```

### FilterResult

```python
FilterResult(
    success: bool,           # Operation success
    filter_type: str,       # Filter type identifier
    drawingml: str,         # Generated DrawingML
    metadata: Dict = None,  # Additional metadata
    error_message: str = None  # Error details if failed
)
```

## Support

For issues or questions about the filter effects system:
1. Check the comprehensive test suite for usage examples
2. Review the integration tests for complex scenarios
3. Consult the inline documentation in filter implementations