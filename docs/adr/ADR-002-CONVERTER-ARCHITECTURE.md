# ADR-002: Converter Architecture Standardization

**Status**: PROPOSED
**Date**: 2025-01-20
**Context**: Inconsistent converter implementations and service injection patterns

## Decision

Standardize converter architecture with **consistent dependency injection** and **modular design**.

## Converter Module Structure

### Base Directory: `src/converters/`
```
src/converters/
├── __init__.py          # Public API and registry
├── base.py              # BaseConverter abstract class
├── registry.py          # ConverterRegistry class
├── result_types.py      # ConversionResult types
├── shapes/              # Shape converters
│   ├── __init__.py
│   ├── rectangle.py
│   ├── circle.py
│   ├── ellipse.py
│   ├── polygon.py
│   └── line.py
├── text/                # Text converters
│   ├── __init__.py
│   ├── text.py
│   └── tspan.py
├── graphics/            # Graphics converters
│   ├── __init__.py
│   ├── image.py
│   ├── use.py
│   └── symbol.py
├── containers/          # Container converters
│   ├── __init__.py
│   ├── group.py
│   ├── defs.py
│   └── svg.py
└── effects/             # Effects converters
    ├── __init__.py
    ├── gradients.py
    ├── patterns.py
    ├── filters.py
    └── clippath.py
```

## Standard Converter Implementation

### Base Converter Contract
**File**: `src/converters/base.py`
```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from lxml import etree as ET
from src.services.conversion_services import ConversionServices

class BaseConverter(ABC):
    """Base class for all SVG element converters."""

    def __init__(self, services: ConversionServices):
        self.services = services
        self.units = services.unit_converter
        self.transforms = services.transform_parser
        self.colors = services.color_parser
        self.paths = services.path_engine
        self.viewbox = services.viewport_resolver

    @abstractmethod
    def can_convert(self, element: ET.Element) -> bool:
        """Check if this converter can handle the element."""
        pass

    @abstractmethod
    def convert(self, element: ET.Element, context: ConversionContext) -> ConversionResult:
        """Convert SVG element to DrawingML."""
        pass

    def get_element_bounds(self, element: ET.Element) -> BoundingBox:
        """Get element bounding box using units service."""
        # Standard bounds calculation
        pass

    def apply_transforms(self, element: ET.Element) -> Transform:
        """Apply transforms using transform service."""
        # Standard transform application
        pass
```

### Standard Converter Template
**Pattern for all converters**:
```python
from ..base import BaseConverter, ConversionContext, ConversionResult
from src.services.conversion_services import ConversionServices
from lxml import etree as ET

class RectangleConverter(BaseConverter):
    """Converts SVG <rect> elements to DrawingML shapes."""

    def can_convert(self, element: ET.Element) -> bool:
        return element.tag.endswith('rect')

    def convert(self, element: ET.Element, context: ConversionContext) -> ConversionResult:
        # Get dimensions using units service
        x = self.units.to_emu(element.get('x', '0'))
        y = self.units.to_emu(element.get('y', '0'))
        width = self.units.to_emu(element.get('width', '0'))
        height = self.units.to_emu(element.get('height', '0'))

        # Apply transforms using transform service
        transform = self.apply_transforms(element)

        # Create DrawingML
        shape_xml = self._create_rectangle_xml(x, y, width, height, transform)

        return ConversionResult(
            xml=shape_xml,
            bounds=BoundingBox(x, y, width, height),
            transforms=[transform]
        )

    def _create_rectangle_xml(self, x: int, y: int, width: int, height: int, transform: Transform) -> str:
        """Create DrawingML XML for rectangle."""
        # Implementation specific to rectangles
        pass
```

## Converter Registry Pattern

### Registry Implementation
**File**: `src/converters/registry.py`
```python
from typing import Dict, List, Optional, Type
from .base import BaseConverter
from src.services.conversion_services import ConversionServices

class ConverterRegistry:
    """Registry for managing converter instances."""

    def __init__(self, services: ConversionServices):
        self.services = services
        self._converters: List[BaseConverter] = []
        self._cache: Dict[str, BaseConverter] = {}

    def register(self, converter_class: Type[BaseConverter]):
        """Register a converter class."""
        converter = converter_class(self.services)
        self._converters.append(converter)

    def get_converter(self, element: ET.Element) -> Optional[BaseConverter]:
        """Get appropriate converter for element."""
        element_key = f"{element.tag}:{element.get('class', '')}"

        if element_key in self._cache:
            return self._cache[element_key]

        for converter in self._converters:
            if converter.can_convert(element):
                self._cache[element_key] = converter
                return converter

        return None

    def register_all_standard_converters(self):
        """Register all standard converters."""
        from .shapes.rectangle import RectangleConverter
        from .shapes.circle import CircleConverter
        from .shapes.ellipse import EllipseConverter
        from .text.text import TextConverter
        # ... register all converters
```

### Public API
**File**: `src/converters/__init__.py`
```python
from .base import BaseConverter, ConversionContext, ConversionResult
from .registry import ConverterRegistry
from .result_types import BoundingBox, ConversionError

# Shape converters
from .shapes.rectangle import RectangleConverter
from .shapes.circle import CircleConverter
from .shapes.ellipse import EllipseConverter

# Text converters
from .text.text import TextConverter

# Container converters
from .containers.group import GroupConverter

__all__ = [
    'BaseConverter', 'ConversionContext', 'ConversionResult',
    'ConverterRegistry', 'BoundingBox', 'ConversionError',
    'RectangleConverter', 'CircleConverter', 'EllipseConverter',
    'TextConverter', 'GroupConverter'
]
```

## Service Integration Pattern

### Services Usage in Converters
```python
class ShapeConverter(BaseConverter):
    def convert(self, element: ET.Element, context: ConversionContext) -> ConversionResult:
        # Units service usage
        x = self.units.to_emu(element.get('x', '0'), axis='x')
        y = self.units.to_emu(element.get('y', '0'), axis='y')

        # Transform service usage
        transform_str = element.get('transform', '')
        transform = self.transforms.parse(transform_str)

        # Color service usage
        fill = element.get('fill', 'black')
        fill_color = self.colors.parse(fill)

        # Path service usage (for complex shapes)
        path_data = element.get('d', '')
        if path_data:
            path = self.paths.parse_path_string(path_data)

        # ViewBox service usage
        viewbox = self.viewbox.resolve_viewport(element, context.viewport)
```

## Converter Naming Conventions

### File Naming
- **Snake case** for files: `rectangle.py`, `text_span.py`
- **Module names** match SVG element names where possible

### Class Naming
- **PascalCase** ending in "Converter": `RectangleConverter`, `TextSpanConverter`
- Clear mapping to SVG elements

### Method Naming
- **Snake case**: `can_convert()`, `get_element_bounds()`
- **Descriptive**: `_create_rectangle_xml()`, `_apply_stroke_properties()`

## Error Handling Pattern

### Standard Error Handling
```python
from .result_types import ConversionError, ConversionResult

class BaseConverter(ABC):
    def safe_convert(self, element: ET.Element, context: ConversionContext) -> ConversionResult:
        """Convert with error handling."""
        try:
            return self.convert(element, context)
        except Exception as e:
            return ConversionResult.error(
                message=f"Failed to convert {element.tag}: {str(e)}",
                element=element,
                converter=self.__class__.__name__
            )
```

## Testing Pattern

### Test Structure
```
tests/unit/converters/
├── test_base.py                    # BaseConverter tests
├── test_registry.py               # Registry tests
├── shapes/
│   ├── test_rectangle.py          # Rectangle converter tests
│   ├── test_circle.py             # Circle converter tests
│   └── test_ellipse.py            # Ellipse converter tests
├── text/
│   └── test_text.py               # Text converter tests
└── containers/
    └── test_group.py              # Group converter tests
```

### Standard Test Pattern
```python
import pytest
from unittest.mock import Mock
from src.converters.shapes.rectangle import RectangleConverter
from src.services.conversion_services import ConversionServices

class TestRectangleConverter:
    @pytest.fixture
    def mock_services(self):
        services = Mock(spec=ConversionServices)
        services.unit_converter = Mock()
        services.transform_parser = Mock()
        services.color_parser = Mock()
        return services

    @pytest.fixture
    def converter(self, mock_services):
        return RectangleConverter(mock_services)

    def test_can_convert_rect_element(self, converter):
        element = Mock()
        element.tag = 'rect'
        assert converter.can_convert(element) is True

    def test_convert_basic_rectangle(self, converter, mock_services):
        # Test implementation
        pass
```

## Benefits

1. **Consistent patterns** across all converters
2. **Clear service dependencies** through injection
3. **Testable design** with mockable services
4. **Modular structure** for easy maintenance
5. **Standard error handling** across converters

## Implementation Priority

1. **High Priority**: Shapes (rectangle, circle, ellipse)
2. **Medium Priority**: Text converters
3. **Low Priority**: Complex effects and filters