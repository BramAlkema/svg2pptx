# ADR-001: Core Architecture Consolidation

**Status**: PROPOSED
**Date**: 2025-01-20
**Context**: Multiple parallel implementations causing import chaos and maintenance overhead

## Decision

Consolidate to **single implementation per domain** with clear module structure.

## Core Module Decisions

### 1. Units System
**CHOSEN**: `src/units/` (NEW - consolidate both systems)
**REMOVE**: `src/units.py`, `src/units_fast.py`, `src/units_adapter.py`

**Structure**:
```
src/units/
├── __init__.py          # Public API
├── core.py              # Core UnitConverter class
├── context.py           # ConversionContext class
└── constants.py         # EMU_PER_* constants
```

**Public API** (`src/units/__init__.py`):
```python
from .core import UnitConverter
from .context import ConversionContext
from .constants import EMU_PER_INCH, EMU_PER_POINT, EMU_PER_MM

__all__ = ['UnitConverter', 'ConversionContext', 'EMU_PER_INCH', 'EMU_PER_POINT', 'EMU_PER_MM']
```

**Core Class** (`src/units/core.py`):
```python
class UnitConverter:
    def __init__(self, context: ConversionContext = None):
        pass

    def to_emu(self, value: str, axis: str = 'x') -> int:
        pass

    def to_pixels(self, value: str) -> float:
        pass

    def batch_convert(self, values: List[str]) -> List[int]:
        pass
```

### 2. Transforms System
**CHOSEN**: `src/transforms/` (KEEP current structure)
**NO CHANGES** - Already clean

**Import Pattern**:
```python
from src.transforms import Transform, TransformBuilder
```

### 3. Path System
**CHOSEN**: `src/paths/` (NEW - consolidate both systems)
**REMOVE**: `src/converters/paths.py`, `src/paths/core.py`

**Structure**:
```
src/paths/
├── __init__.py          # Public API
├── engine.py            # PathEngine class
├── data.py              # PathData class
├── parser.py            # SVG path string parsing
└── operations.py        # Path operations (intersect, etc.)
```

**Public API** (`src/paths/__init__.py`):
```python
from .engine import PathEngine
from .data import PathData
from .parser import parse_path_string

__all__ = ['PathEngine', 'PathData', 'parse_path_string']
```

### 4. ViewBox System
**CHOSEN**: `src/viewbox/` (KEEP current, fix imports)
**NO CHANGES** - Fix import issues only

### 5. Color System
**CHOSEN**: `src/color/` (KEEP current)
**NO CHANGES** - Already well structured

## Import Standardization

### Services Integration
**File**: `src/services/conversion_services.py`
```python
# Modern ConversionServices pattern (recommended)
from src.services.conversion_services import ConversionServices

services = ConversionServices.create_default()
unit_converter = services.unit_converter
transform_parser = services.transform_parser
color_parser = services.color_parser
viewport_resolver = services.viewport_resolver
path_engine = services.path_engine

# Legacy imports (still supported with service-aware fallbacks)
from src.units import UnitConverter
from src.transforms import Transform as TransformParser  # Alias for compatibility
from src.color import Color
from src.viewbox import ViewportResolver
from src.paths import PathEngine
```

### Converter Base
**File**: `src/converters/base.py`
```python
from src.services.conversion_services import ConversionServices
from src.units import UnitConverter
from src.transforms import Transform
from src.paths import PathEngine
```

### Converter Implementations
**Pattern for all converters**:
```python
from ..base import BaseConverter
from src.services.conversion_services import ConversionServices

class RectangleConverter(BaseConverter):
    def __init__(self, services: ConversionServices):
        super().__init__(services)
        self.units = services.unit_converter
        self.paths = services.path_engine
```

## Migration Strategy

### Phase 1: Create New Consolidated Modules
1. Create `src/units/` with unified API
2. Create `src/paths/` with unified API
3. Keep old modules temporarily

### Phase 2: Update All Imports
1. Update `src/services/conversion_services.py`
2. Update all converter files
3. Update all test files

### Phase 3: Remove Old Modules
1. Delete `src/units.py`, `src/units_fast.py`, `src/units_adapter.py`
2. Delete `src/converters/paths.py`, `src/paths/core.py`
3. Remove backward compatibility code

## Testing Strategy

### Test Organization
```
tests/
├── unit/
│   ├── units/           # Unit system tests
│   ├── paths/           # Path system tests
│   ├── transforms/      # Transform tests
│   └── converters/      # Converter tests
└── e2e/
    ├── core_systems/   # System integration tests
    └── conversion/     # End-to-end conversion tests
```

### Test Import Pattern
```python
from src.units import UnitConverter
from src.paths import PathEngine
from src.transforms import Transform
```

## Benefits

1. **Single source of truth** per domain
2. **Clean import paths** - no more alias hacks
3. **Easier maintenance** - one implementation to maintain
4. **Clear ownership** - each module has specific responsibility
5. **Better testing** - focused test suites per module

## Risks

1. **Breaking changes** during migration
2. **Temporary duplication** during transition
3. **Import update effort** across codebase

## Implementation Timeline

- **Week 1**: Create consolidated modules
- **Week 2**: Update imports across codebase
- **Week 3**: Remove old modules and test
- **Week 4**: Documentation and cleanup