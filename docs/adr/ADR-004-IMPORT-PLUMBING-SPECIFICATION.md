# ADR-004: Import Plumbing Specification

**Status**: PROPOSED
**Date**: 2025-01-20
**Context**: Detailed import specifications to prevent drift and ensure consistency

## Core Module Import Contracts

### 1. Units Module (`src/units/`)

#### `src/units/__init__.py`
```python
"""
Consolidated unit conversion system.
Single API for all unit operations.
"""
from .core import UnitConverter
from .context import ConversionContext
from .constants import (
    EMU_PER_INCH, EMU_PER_POINT, EMU_PER_MM, EMU_PER_CM,
    DEFAULT_DPI, DEFAULT_SLIDE_WIDTH, DEFAULT_SLIDE_HEIGHT
)

__all__ = [
    'UnitConverter',
    'ConversionContext',
    'EMU_PER_INCH',
    'EMU_PER_POINT',
    'EMU_PER_MM',
    'EMU_PER_CM',
    'DEFAULT_DPI',
    'DEFAULT_SLIDE_WIDTH',
    'DEFAULT_SLIDE_HEIGHT'
]

__version__ = '2.0.0'
```

#### `src/units/core.py`
```python
"""Core unit conversion implementation."""
import numpy as np
from typing import Union, List, Optional, Dict, Any
from .context import ConversionContext
from .constants import EMU_PER_INCH, EMU_PER_POINT, EMU_PER_MM

class UnitConverter:
    """Unified unit converter with NumPy optimization."""

    def __init__(self, context: Optional[ConversionContext] = None):
        self.context = context or ConversionContext()

    def to_emu(self, value: Union[str, float, int], axis: str = 'x') -> int:
        """Convert value to EMU."""
        pass

    def to_pixels(self, value: Union[str, float, int]) -> float:
        """Convert value to pixels."""
        pass

    def batch_convert(self, values: List[Union[str, float, int]], axis: str = 'x') -> List[int]:
        """Batch convert values to EMU."""
        pass
```

#### `src/units/context.py`
```python
"""Conversion context for units."""
from dataclasses import dataclass
from typing import Optional

@dataclass
class ConversionContext:
    """Context for unit conversions."""
    width: float = 800.0
    height: float = 600.0
    font_size: float = 16.0
    dpi: float = 96.0
    parent_width: Optional[float] = None
    parent_height: Optional[float] = None
```

#### `src/units/constants.py`
```python
"""Unit conversion constants."""

# EMU conversion constants
EMU_PER_INCH = 914400
EMU_PER_POINT = 12700
EMU_PER_MM = 36000
EMU_PER_CM = 360000

# Default values
DEFAULT_DPI = 96.0
DEFAULT_SLIDE_WIDTH = 9144000  # 10 inches in EMU
DEFAULT_SLIDE_HEIGHT = 6858000  # 7.5 inches in EMU
```

### 2. Paths Module (`src/paths/`)

#### `src/paths/__init__.py`
```python
"""
Consolidated path processing system.
Single API for all path operations.
"""
from .engine import PathEngine
from .data import PathData, PathCommand
from .parser import parse_path_string, parse_path_commands
from .operations import (
    path_intersection, path_union, path_bounds,
    simplify_path, optimize_path
)

__all__ = [
    'PathEngine',
    'PathData',
    'PathCommand',
    'parse_path_string',
    'parse_path_commands',
    'path_intersection',
    'path_union',
    'path_bounds',
    'simplify_path',
    'optimize_path'
]

__version__ = '2.0.0'
```

#### `src/paths/engine.py`
```python
"""Path processing engine."""
import numpy as np
from typing import List, Dict, Any, Optional, Union
from .data import PathData
from .parser import parse_path_string

class PathEngine:
    """High-performance path processing engine."""

    def __init__(self, cache_size: int = 1000):
        self.cache_size = cache_size
        self._cache = {}

    def process_path(self, path_string: str) -> PathData:
        """Process SVG path string into PathData."""
        pass

    def batch_process(self, path_strings: List[str]) -> List[PathData]:
        """Process multiple paths efficiently."""
        pass

    def transform_path(self, path_data: PathData, matrix: np.ndarray) -> PathData:
        """Transform path using matrix."""
        pass
```

### 3. Services Integration (`src/services/`)

#### `src/services/conversion_services.py`
```python
"""
ConversionServices dependency injection container.
Central service registry for all converters.
"""
from dataclasses import dataclass, field
from typing import Optional, ClassVar
import logging

# Core service imports
from src.units import UnitConverter, ConversionContext
from src.transforms import Transform as TransformParser  # Alias for compatibility
from src.color import Color
from src.viewbox import ViewportResolver
from src.paths import PathEngine

logger = logging.getLogger(__name__)

@dataclass
class ConversionServices:
    """Central service container for dependency injection."""

    # Core conversion services
    unit_converter: UnitConverter = field(default_factory=UnitConverter)
    transform_parser: TransformParser = field(default_factory=TransformParser)
    color_parser: Color = field(default_factory=Color)
    viewport_resolver: ViewportResolver = field(default_factory=ViewportResolver)
    path_engine: PathEngine = field(default_factory=PathEngine)

    # Configuration
    _config: Optional['ConversionConfig'] = field(default=None)

    @classmethod
    def create_default(cls) -> 'ConversionServices':
        """Create services with default configuration."""
        return cls()

    @classmethod
    def create_with_config(cls, config: 'ConversionConfig') -> 'ConversionServices':
        """Create services with custom configuration."""
        context = ConversionContext(
            width=config.slide_width,
            height=config.slide_height,
            dpi=config.dpi
        )

        return cls(
            unit_converter=UnitConverter(context),
            path_engine=PathEngine(cache_size=config.cache_size),
            _config=config
        )

@dataclass
class ConversionConfig:
    """Configuration for conversion services."""
    slide_width: float = 800.0
    slide_height: float = 600.0
    dpi: float = 96.0
    cache_size: int = 1000
    enable_optimization: bool = True
```

### 4. Converter Base (`src/converters/`)

#### `src/converters/__init__.py`
```python
"""
SVG to DrawingML converter system.
Modular converter architecture with dependency injection.
"""
from .base import BaseConverter, ConversionContext, ConversionResult
from .registry import ConverterRegistry
from .result_types import BoundingBox, ConversionError

# Shape converters
from .shapes import (
    RectangleConverter, CircleConverter, EllipseConverter,
    PolygonConverter, LineConverter, PathConverter
)

# Text converters
from .text import TextConverter, TSpanConverter

# Container converters
from .containers import GroupConverter, SvgConverter, DefsConverter

# Graphics converters
from .graphics import ImageConverter, UseConverter, SymbolConverter

# Effects converters
from .effects import (
    GradientConverter, PatternConverter,
    FilterConverter, ClipPathConverter
)

__all__ = [
    # Base classes
    'BaseConverter', 'ConversionContext', 'ConversionResult',
    'ConverterRegistry', 'BoundingBox', 'ConversionError',

    # Shape converters
    'RectangleConverter', 'CircleConverter', 'EllipseConverter',
    'PolygonConverter', 'LineConverter', 'PathConverter',

    # Text converters
    'TextConverter', 'TSpanConverter',

    # Container converters
    'GroupConverter', 'SvgConverter', 'DefsConverter',

    # Graphics converters
    'ImageConverter', 'UseConverter', 'SymbolConverter',

    # Effects converters
    'GradientConverter', 'PatternConverter',
    'FilterConverter', 'ClipPathConverter'
]

# Convenience function for creating configured registry
def create_converter_registry(services: 'ConversionServices') -> ConverterRegistry:
    """Create converter registry with all standard converters."""
    from src.services.conversion_services import ConversionServices

    registry = ConverterRegistry(services)
    registry.register_all_standard_converters()
    return registry
```

#### `src/converters/base.py`
```python
"""Base converter implementation."""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass
from lxml import etree as ET

# Service imports
from src.services.conversion_services import ConversionServices
from src.units import UnitConverter, ConversionContext
from src.transforms import Transform
from src.color import Color
from src.paths import PathEngine
from src.viewbox import ViewportResolver

@dataclass
class ConversionContext:
    """Context for element conversion."""
    viewport_width: float
    viewport_height: float
    parent_transform: Optional[Transform] = None
    clip_path: Optional[str] = None
    opacity: float = 1.0

class BaseConverter(ABC):
    """Abstract base class for all converters."""

    def __init__(self, services: ConversionServices):
        """Initialize converter with injected services."""
        self.services = services

        # Direct service references for convenience
        self.units: UnitConverter = services.unit_converter
        self.transforms: Transform = services.transform_parser
        self.colors: Color = services.color_parser
        self.paths: PathEngine = services.path_engine
        self.viewbox: ViewportResolver = services.viewport_resolver

    @abstractmethod
    def can_convert(self, element: ET.Element) -> bool:
        """Check if this converter can handle the element."""
        pass

    @abstractmethod
    def convert(self, element: ET.Element, context: ConversionContext) -> 'ConversionResult':
        """Convert SVG element to DrawingML."""
        pass

    # Standard helper methods
    def get_element_bounds(self, element: ET.Element, context: ConversionContext) -> 'BoundingBox':
        """Calculate element bounding box."""
        pass

    def apply_transforms(self, element: ET.Element) -> Transform:
        """Parse and apply element transforms."""
        transform_str = element.get('transform', '')
        return self.transforms.parse(transform_str) if transform_str else Transform.identity()

    def parse_color(self, color_str: str, default: str = 'black') -> Color:
        """Parse color with fallback."""
        try:
            return self.colors.parse(color_str or default)
        except Exception:
            return self.colors.parse(default)
```

### 5. Specific Converter Implementation

#### `src/converters/shapes/rectangle.py`
```python
"""Rectangle converter implementation."""
from typing import Optional
from lxml import etree as ET

# Converter base imports
from ..base import BaseConverter, ConversionContext, ConversionResult
from ..result_types import BoundingBox

# Service imports (via base class)
from src.services.conversion_services import ConversionServices

class RectangleConverter(BaseConverter):
    """Converts SVG <rect> elements to DrawingML rectangles."""

    def can_convert(self, element: ET.Element) -> bool:
        """Check if element is a rectangle."""
        return element.tag.endswith('rect')

    def convert(self, element: ET.Element, context: ConversionContext) -> ConversionResult:
        """Convert rectangle element."""
        # Use services through base class
        x = self.units.to_emu(element.get('x', '0'), axis='x')
        y = self.units.to_emu(element.get('y', '0'), axis='y')
        width = self.units.to_emu(element.get('width', '0'), axis='x')
        height = self.units.to_emu(element.get('height', '0'), axis='y')

        # Apply transforms
        transform = self.apply_transforms(element)

        # Parse colors
        fill = self.parse_color(element.get('fill', 'black'))
        stroke = self.parse_color(element.get('stroke', 'none'))

        # Create bounds
        bounds = BoundingBox(x, y, width, height)

        # Generate DrawingML
        xml = self._create_rectangle_xml(bounds, fill, stroke, transform)

        return ConversionResult(
            xml=xml,
            bounds=bounds,
            element_type='rectangle'
        )

    def _create_rectangle_xml(self, bounds: BoundingBox, fill: Color,
                            stroke: Color, transform: Transform) -> str:
        """Generate DrawingML XML for rectangle."""
        # Implementation details...
        pass
```

### 6. Shape Converter Module (`src/converters/shapes/`)

#### `src/converters/shapes/__init__.py`
```python
"""Shape converters module."""
from .rectangle import RectangleConverter
from .circle import CircleConverter
from .ellipse import EllipseConverter
from .polygon import PolygonConverter
from .polyline import PolylineConverter
from .line import LineConverter
from .path import PathConverter

__all__ = [
    'RectangleConverter',
    'CircleConverter',
    'EllipseConverter',
    'PolygonConverter',
    'PolylineConverter',
    'LineConverter',
    'PathConverter'
]
```

### 7. Main API (`src/svg2pptx.py`)

#### `src/svg2pptx.py`
```python
"""
Main SVG2PPTX conversion API.
Entry point for all SVG to PowerPoint conversions.
"""
from typing import Optional, Dict, Any, Union
from pathlib import Path
from lxml import etree as ET

# Core service imports
from .services.conversion_services import ConversionServices, ConversionConfig
from .converters import ConverterRegistry, create_converter_registry
from .preprocessing import SVGOptimizer
from .output import PPTXBuilder

class SVG2PPTX:
    """Main SVG to PowerPoint converter."""

    def __init__(self, config: Optional[ConversionConfig] = None):
        """Initialize converter with configuration."""
        self.config = config or ConversionConfig()
        self.services = ConversionServices.create_with_config(self.config)
        self.registry = create_converter_registry(self.services)
        self.optimizer = SVGOptimizer()
        self.builder = PPTXBuilder()

    def convert_file(self, svg_path: Union[str, Path],
                    output_path: Optional[Union[str, Path]] = None) -> Path:
        """Convert SVG file to PPTX."""
        pass

    def convert_string(self, svg_content: str) -> bytes:
        """Convert SVG string to PPTX bytes."""
        pass
```

## Test Import Patterns

### Unit Test Pattern
```python
"""Test template for unit tests."""
import pytest
from unittest.mock import Mock, patch
from lxml import etree as ET

# Import what we're testing
from src.converters.shapes.rectangle import RectangleConverter
from src.services.conversion_services import ConversionServices, ConversionConfig
from src.units import UnitConverter, ConversionContext
from src.converters.base import ConversionContext as ConverterContext

class TestRectangleConverter:
    """Test suite for RectangleConverter."""

    @pytest.fixture
    def mock_services(self) -> ConversionServices:
        """Create mock services for testing."""
        services = Mock(spec=ConversionServices)
        services.unit_converter = Mock(spec=UnitConverter)
        services.transform_parser = Mock()
        services.color_parser = Mock()
        services.path_engine = Mock()
        services.viewport_resolver = Mock()
        return services

    @pytest.fixture
    def converter(self, mock_services: ConversionServices) -> RectangleConverter:
        """Create converter instance."""
        return RectangleConverter(mock_services)

    def test_can_convert_rect_element(self, converter: RectangleConverter):
        """Test rectangle element detection."""
        element = ET.Element('rect')
        assert converter.can_convert(element) is True
```

### Integration Test Pattern
```python
"""Integration test template."""
import pytest
from src.services.conversion_services import ConversionServices
from src.converters import create_converter_registry
from src.svg2pptx import SVG2PPTX

class TestConverterIntegration:
    """Integration tests for converter system."""

    @pytest.fixture
    def services(self) -> ConversionServices:
        """Create real services."""
        return ConversionServices.create_default()

    @pytest.fixture
    def svg2pptx(self) -> SVG2PPTX:
        """Create configured SVG2PPTX instance."""
        return SVG2PPTX()

    def test_full_conversion_pipeline(self, svg2pptx: SVG2PPTX):
        """Test complete conversion workflow."""
        svg_content = '''<svg><rect x="10" y="10" width="100" height="50"/></svg>'''
        result = svg2pptx.convert_string(svg_content)
        assert isinstance(result, bytes)
```

## Import Validation Commands

### Check Import Consistency
```bash
# Validate all imports work
python -c "from src.units import UnitConverter; print('✓ Units')"
python -c "from src.paths import PathEngine; print('✓ Paths')"
python -c "from src.transforms import Transform; print('✓ Transforms')"
python -c "from src.services.conversion_services import ConversionServices; print('✓ Services')"
python -c "from src.converters import RectangleConverter; print('✓ Converters')"
python -c "from src.svg2pptx import SVG2PPTX; print('✓ Main API')"
```

This import specification ensures:
1. **Consistent import patterns** across all modules
2. **Clear dependency flow** from main API down to core services
3. **Proper service injection** through dependency injection
4. **Testable architecture** with mockable dependencies
5. **No import drift** through explicit contracts