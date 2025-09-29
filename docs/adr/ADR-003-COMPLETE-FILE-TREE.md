# ADR-003: Complete File Tree Structure

**Status**: PROPOSED
**Date**: 2025-01-20
**Context**: Define complete file structure for consolidated architecture

## Complete Directory Tree

```
svg2pptx/
├── src/
│   ├── __init__.py
│   │
│   ├── units/                          # Consolidated unit conversion
│   │   ├── __init__.py                 # from .core import UnitConverter
│   │   ├── core.py                     # class UnitConverter
│   │   ├── context.py                  # class ConversionContext
│   │   └── constants.py                # EMU_PER_INCH, EMU_PER_POINT, etc.
│   │
│   ├── transforms/                     # Transform system (KEEP)
│   │   ├── __init__.py                 # from .core import Transform
│   │   └── core.py                     # class Transform, TransformBuilder
│   │
│   ├── paths/                          # Consolidated path processing
│   │   ├── __init__.py                 # from .engine import PathEngine
│   │   ├── engine.py                   # class PathEngine
│   │   ├── data.py                     # class PathData
│   │   ├── parser.py                   # parse_path_string()
│   │   └── operations.py               # path intersection, union, etc.
│   │
│   ├── viewbox/                        # ViewBox system (KEEP, fix imports)
│   │   ├── __init__.py                 # from .core import ViewportResolver
│   │   └── core.py                     # class ViewportResolver
│   │
│   ├── color/                          # Color system (KEEP)
│   │   ├── __init__.py                 # from .core import Color
│   │   ├── core.py                     # class Color
│   │   ├── harmony.py                  # ColorHarmony
│   │   ├── accessibility.py            # ColorAccessibility
│   │   ├── manipulation.py             # ColorManipulation
│   │   └── batch.py                    # ColorBatch
│   │
│   ├── services/                       # Dependency injection
│   │   ├── __init__.py
│   │   ├── conversion_services.py      # class ConversionServices
│   │   ├── font_service.py             # class FontService
│   │   └── font_embedding_engine.py    # class FontEmbeddingEngine
│   │
│   ├── converters/                     # Modular converters
│   │   ├── __init__.py                 # Public API, registry
│   │   ├── base.py                     # class BaseConverter(ABC)
│   │   ├── registry.py                 # class ConverterRegistry
│   │   ├── result_types.py             # ConversionResult, BoundingBox
│   │   │
│   │   ├── shapes/                     # Shape converters
│   │   │   ├── __init__.py
│   │   │   ├── rectangle.py            # class RectangleConverter(BaseConverter)
│   │   │   ├── circle.py               # class CircleConverter(BaseConverter)
│   │   │   ├── ellipse.py              # class EllipseConverter(BaseConverter)
│   │   │   ├── polygon.py              # class PolygonConverter(BaseConverter)
│   │   │   ├── polyline.py             # class PolylineConverter(BaseConverter)
│   │   │   ├── line.py                 # class LineConverter(BaseConverter)
│   │   │   └── path.py                 # class PathConverter(BaseConverter)
│   │   │
│   │   ├── text/                       # Text converters
│   │   │   ├── __init__.py
│   │   │   ├── text.py                 # class TextConverter(BaseConverter)
│   │   │   └── tspan.py                # class TSpanConverter(BaseConverter)
│   │   │
│   │   ├── graphics/                   # Graphics converters
│   │   │   ├── __init__.py
│   │   │   ├── image.py                # class ImageConverter(BaseConverter)
│   │   │   ├── use.py                  # class UseConverter(BaseConverter)
│   │   │   └── symbol.py               # class SymbolConverter(BaseConverter)
│   │   │
│   │   ├── containers/                 # Container converters
│   │   │   ├── __init__.py
│   │   │   ├── group.py                # class GroupConverter(BaseConverter)
│   │   │   ├── defs.py                 # class DefsConverter(BaseConverter)
│   │   │   └── svg.py                  # class SvgConverter(BaseConverter)
│   │   │
│   │   └── effects/                    # Effects converters
│   │       ├── __init__.py
│   │       ├── gradients.py            # class GradientConverter(BaseConverter)
│   │       ├── patterns.py             # class PatternConverter(BaseConverter)
│   │       ├── filters.py              # class FilterConverter(BaseConverter)
│   │       └── clippath.py             # class ClipPathConverter(BaseConverter)
│   │
│   ├── preprocessing/                  # SVG preprocessing (KEEP)
│   │   ├── __init__.py
│   │   ├── optimizer.py
│   │   ├── plugins/
│   │   └── geometry/
│   │
│   ├── output/                         # Output generation (KEEP)
│   │   ├── __init__.py
│   │   ├── pptx_builder.py
│   │   └── templates/
│   │
│   ├── svg2pptx.py                     # Main conversion class
│   │
│   └── REMOVED_FILES/                  # Files to be deleted
│       ├── units.py                    # REMOVE - replaced by units/
│       ├── units_fast.py               # REMOVE - replaced by units/
│       ├── units_adapter.py            # REMOVE - replaced by units/
│       ├── fractional_emu.py           # REMOVE - integrate into units/
│       └── converters/paths.py         # REMOVE - replaced by paths/
│
├── tests/
│   ├── unit/
│   │   ├── units/                      # Unit system tests
│   │   │   ├── test_core.py            # UnitConverter tests
│   │   │   ├── test_context.py         # ConversionContext tests
│   │   │   └── test_constants.py       # Constants tests
│   │   │
│   │   ├── transforms/                 # Transform tests (KEEP)
│   │   │   └── test_core.py
│   │   │
│   │   ├── paths/                      # Path system tests
│   │   │   ├── test_engine.py          # PathEngine tests
│   │   │   ├── test_data.py            # PathData tests
│   │   │   ├── test_parser.py          # Parser tests
│   │   │   └── test_operations.py      # Operations tests
│   │   │
│   │   ├── viewbox/                    # ViewBox tests (KEEP)
│   │   │   └── test_core.py
│   │   │
│   │   ├── color/                      # Color tests (KEEP)
│   │   │   ├── test_core.py
│   │   │   ├── test_harmony.py
│   │   │   ├── test_accessibility.py
│   │   │   ├── test_manipulation.py
│   │   │   └── test_batch.py
│   │   │
│   │   ├── services/                   # Service tests
│   │   │   ├── test_conversion_services.py
│   │   │   └── test_font_service.py
│   │   │
│   │   └── converters/                 # Converter tests
│   │       ├── test_base.py            # BaseConverter tests
│   │       ├── test_registry.py        # Registry tests
│   │       ├── shapes/                 # Shape converter tests
│   │       │   ├── test_rectangle.py
│   │       │   ├── test_circle.py
│   │       │   ├── test_ellipse.py
│   │       │   ├── test_polygon.py
│   │       │   ├── test_line.py
│   │       │   └── test_path.py
│   │       ├── text/                   # Text converter tests
│   │       │   ├── test_text.py
│   │       │   └── test_tspan.py
│   │       ├── graphics/               # Graphics converter tests
│   │       │   ├── test_image.py
│   │       │   ├── test_use.py
│   │       │   └── test_symbol.py
│   │       ├── containers/             # Container converter tests
│   │       │   ├── test_group.py
│   │       │   ├── test_defs.py
│   │       │   └── test_svg.py
│   │       └── effects/                # Effects converter tests
│   │           ├── test_gradients.py
│   │           ├── test_patterns.py
│   │           ├── test_filters.py
│   │           └── test_clippath.py
│   │
│   ├── integration/                    # Integration tests
│   │   ├── test_converter_pipeline.py
│   │   ├── test_service_integration.py
│   │   └── test_preprocessing_integration.py
│   │
│   └── e2e/                           # End-to-end tests
│       ├── core_systems/              # Core system E2E tests
│       │   ├── test_units_system_e2e.py
│       │   ├── test_transforms_system_e2e.py
│       │   ├── test_paths_system_e2e.py
│       │   └── test_viewbox_system_e2e.py
│       ├── conversion/                # Conversion E2E tests
│       │   ├── test_shape_conversion_e2e.py
│       │   ├── test_text_conversion_e2e.py
│       │   └── test_complex_svg_e2e.py
│       └── multislide/                # Multislide tests (TO BE FIXED)
│           ├── __init__.py
│           ├── conftest.py
│           └── test_multislide_e2e.py # TO BE CREATED
│
├── api/                               # FastAPI application (KEEP)
│   ├── __init__.py
│   ├── main.py
│   ├── routes/
│   └── models/
│
├── docs/
│   ├── adr/                           # Architecture Decision Records
│   │   ├── ADR-001-CORE-ARCHITECTURE-CONSOLIDATION.md
│   │   ├── ADR-002-CONVERTER-ARCHITECTURE.md
│   │   └── ADR-003-COMPLETE-FILE-TREE.md
│   └── api/                           # API documentation
│
├── reports/                           # Analysis reports (KEEP)
├── scripts/                           # Utility scripts (KEEP)
├── development/                       # Development files (KEEP)
│
├── requirements.txt
├── pytest.ini
├── pyproject.toml
├── README.md
└── CLAUDE.md
```

## Critical Import Patterns

### Core Services Import
```python
# In src/services/conversion_services.py
from src.units import UnitConverter
from src.transforms import Transform as TransformParser  # Alias for compatibility
from src.color import Color
from src.viewbox import ViewportResolver
from src.paths import PathEngine
```

### Converter Import Pattern
```python
# In any converter file (e.g., src/converters/shapes/rectangle.py)
from ..base import BaseConverter, ConversionContext, ConversionResult
from src.services.conversion_services import ConversionServices
from lxml import etree as ET
```

### Main API Import
```python
# In src/svg2pptx.py
from .services.conversion_services import ConversionServices
from .converters import ConverterRegistry
from .preprocessing import SVGOptimizer
from .output import PPTXBuilder
```

### Test Import Pattern
```python
# In test files
import pytest
from unittest.mock import Mock
from src.units import UnitConverter
from src.converters.shapes.rectangle import RectangleConverter
from src.services.conversion_services import ConversionServices
```

## Files to Remove (Phase 3)

```
REMOVE_LIST = [
    'src/units.py',
    'src/units_fast.py',
    'src/units_adapter.py',
    'src/fractional_emu.py',
    'src/converters/paths.py',
    'src/paths/core.py'  # If exists separate from paths/ module
]
```

## Migration Order

### Phase 1: Create New Modules
1. Create `src/units/` module with consolidated API
2. Create `src/paths/` module with consolidated API
3. Keep old modules for now

### Phase 2: Update Imports
1. Update `src/services/conversion_services.py`
2. Update all files in `src/converters/`
3. Update all test files
4. Update main `src/svg2pptx.py`

### Phase 3: Clean Up
1. Remove old module files
2. Remove backward compatibility code
3. Clean up imports

## Key Dependencies

### Internal Dependencies Flow
```
src/svg2pptx.py
├── services/conversion_services.py
│   ├── units/
│   ├── transforms/
│   ├── color/
│   ├── viewbox/
│   └── paths/
├── converters/
│   ├── base.py (uses services)
│   └── shapes/rectangle.py (extends base)
├── preprocessing/
└── output/
```

This structure ensures:
1. **Single source of truth** for each domain
2. **Clear dependency flow**
3. **Consistent import patterns**
4. **Modular testing structure**
5. **Easy maintenance and extension**