# Fractional EMU Migration Checklist

**Task**: Phase 1, Task 1.4 - Migrate Fractional EMU System
**Estimated Effort**: 8 hours
**Source**: `archive/legacy-src/fractional_emu.py` (1313 lines)
**Destination**: `core/fractional_emu/` (new package)

---

## Migration Plan

### Step 1: Create Package Structure (1 hour)

#### 1.1 Create Directory
```bash
mkdir -p core/fractional_emu
touch core/fractional_emu/__init__.py
```

#### 1.2 Split Monolithic File

**From `fractional_emu.py` (1313 lines) to:**

| Target File | Source Lines | Content | Lines |
|-------------|--------------|---------|-------|
| `constants.py` | 21-30, 37-52 | EMU constants, imports | ~40 |
| `types.py` | 71-104 | PrecisionMode, Exceptions, FractionalCoordinateContext | ~50 |
| `errors.py` | 79-92 | Custom exceptions | ~20 |
| `converter.py` | 106-1006 | FractionalEMUConverter class | ~900 |
| `precision_engine.py` | 1008-1313 | VectorizedPrecisionEngine class | ~305 |
| `__init__.py` | New | Public API exports | ~30 |

**Total**: ~1345 lines (comparable to original)

---

### Step 2: Module Implementation Details

#### 2.1 `constants.py`

```python
#!/usr/bin/env python3
"""
Fractional EMU Constants

EMU (English Metric Units) conversion constants for PowerPoint compatibility.
"""

# EMU conversion constants
EMU_PER_INCH = 914400
EMU_PER_POINT = 12700
EMU_PER_MM = 36000
EMU_PER_CM = 360000
DEFAULT_DPI = 96.0

# PowerPoint compatibility limits
POWERPOINT_MAX_EMU = EMU_PER_INCH * 1000  # 1000 inches max
POWERPOINT_MIN_EMU = 0.001  # Minimum meaningful EMU value

# Coordinate validation bounds
COORDINATE_MAX_VALUE = 1e10
COORDINATE_MIN_VALUE = -1e10
PRECISION_OVERFLOW_THRESHOLD = 1e15
```

**Checklist**:
- [ ] Create file with all constants
- [ ] Add docstrings explaining each constant
- [ ] Import in `__init__.py`

---

#### 2.2 `types.py`

```python
#!/usr/bin/env python3
"""
Fractional EMU Type Definitions

Enumerations, dataclasses, and type definitions for the fractional EMU system.
"""

from enum import Enum
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

# Import from units module
try:
    from core.units import UnitType, ViewportContext
except ImportError:
    from units import UnitType, ViewportContext  # Fallback


class PrecisionMode(Enum):
    """Mathematical precision modes for coordinate conversion."""
    STANDARD = "standard"           # Regular EMU precision (1x)
    SUBPIXEL = "subpixel"          # Sub-EMU fractional precision (100x)
    HIGH_PRECISION = "high"         # Maximum precision mode (1000x)
    ULTRA_PRECISION = "ultra"       # Ultra precision mode (10000x)


@dataclass
class FractionalCoordinateContext:
    """Extended context for sub-EMU precision calculations."""
    base_dpi: float = 96.0
    fractional_scale: float = 1.0
    rounding_mode: str = 'round_half_up'
    precision_threshold: float = 0.001
    max_decimal_places: int = 3  # PowerPoint compatibility
    adaptive_precision: bool = True
    performance_mode: bool = False
```

**Checklist**:
- [ ] Extract enums and dataclasses from original
- [ ] Add proper imports
- [ ] Update docstrings
- [ ] Import in `__init__.py`

---

#### 2.3 `errors.py`

```python
#!/usr/bin/env python3
"""
Fractional EMU Custom Exceptions

Error types for fractional EMU conversion and validation.
"""


class CoordinateValidationError(ValueError):
    """Exception raised when coordinate validation fails."""
    pass


class PrecisionOverflowError(ValueError):
    """Exception raised when precision calculations cause overflow."""
    pass


class EMUBoundaryError(ValueError):
    """Exception raised when EMU values exceed PowerPoint boundaries."""
    pass
```

**Checklist**:
- [ ] Extract exception classes
- [ ] Add usage examples in docstrings
- [ ] Import in `__init__.py`

---

#### 2.4 `converter.py`

**Structure**:
```python
#!/usr/bin/env python3
"""
Fractional EMU Converter

Main converter class providing fractional EMU coordinate conversion
with subpixel precision and comprehensive integration.
"""

import math
import logging
from typing import Optional, Union, Tuple, Dict, List, Any
from decimal import Decimal, ROUND_HALF_UP

# Relative imports within package
from .constants import *
from .types import PrecisionMode, FractionalCoordinateContext
from .errors import CoordinateValidationError, PrecisionOverflowError, EMUBoundaryError

# System imports with fallbacks
try:
    from core.units import UnitConverter, UnitType, ViewportContext
except ImportError:
    from units import UnitConverter, UnitType, ViewportContext

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np = None

try:
    import numba
    from numba import jit
    NUMBA_AVAILABLE = True
except ImportError:
    NUMBA_AVAILABLE = False
    numba = None
    jit = lambda func: func


class FractionalEMUConverter(UnitConverter):
    """
    Extended UnitConverter with fractional coordinate precision.

    ... (rest of implementation from lines 106-1006)
    """
```

**Checklist**:
- [ ] Extract main converter class (lines 106-1006)
- [ ] Update imports to use relative imports from package
- [ ] Update imports to use `core.units` instead of `units`
- [ ] Test backward compatibility with `to_emu()` override
- [ ] Verify integration methods still work

---

#### 2.5 `precision_engine.py`

```python
#!/usr/bin/env python3
"""
Vectorized Precision Engine

Ultra-fast vectorized precision arithmetic engine for batch EMU operations.
Provides 70-100x performance improvement over scalar operations through
NumPy vectorization.
"""

import numpy as np
from typing import Optional, Union, Tuple, Dict, List, Any

# Relative imports
from .constants import *
from .types import PrecisionMode, UnitType

try:
    import numba
    from numba import jit
    NUMBA_AVAILABLE = True
except ImportError:
    NUMBA_AVAILABLE = False
    numba = None
    jit = lambda func: func


class VectorizedPrecisionEngine:
    """
    Ultra-fast vectorized precision arithmetic engine for batch EMU operations.

    ... (rest of implementation from lines 1008-1313)
    """
```

**Checklist**:
- [ ] Extract VectorizedPrecisionEngine class (lines 1008-1313)
- [ ] Update imports to use relative imports
- [ ] Verify NumPy/Numba availability checks work
- [ ] Test vectorized operations independently

---

#### 2.6 `__init__.py`

```python
#!/usr/bin/env python3
"""
Fractional EMU - Subpixel-Accurate Coordinate Conversion

Provides fractional EMU (English Metric Units) conversion with subpixel precision
for advanced SVG features while maintaining PowerPoint compatibility.

Key Features:
- Float64 precision throughout calculation pipeline
- Configurable precision modes (standard, subpixel, high, ultra)
- 70-100x performance improvement with NumPy vectorization
- Comprehensive PowerPoint compatibility validation
- Backward compatible with existing UnitConverter API

Usage:
    from core.fractional_emu import create_fractional_converter

    # Create converter with subpixel precision
    converter = create_fractional_converter("subpixel")

    # Convert with fractional precision
    emu_value = converter.to_fractional_emu("100.5px")  # Returns float

    # Backward compatible integer conversion
    emu_int = converter.to_emu("100.5px")  # Returns int
"""

# Version info
__version__ = "1.0.0"
__author__ = "svg2pptx development team"

# Public API exports
from .constants import (
    EMU_PER_INCH,
    EMU_PER_POINT,
    EMU_PER_MM,
    EMU_PER_CM,
    DEFAULT_DPI,
    POWERPOINT_MAX_EMU,
    POWERPOINT_MIN_EMU
)

from .types import (
    PrecisionMode,
    FractionalCoordinateContext
)

from .errors import (
    CoordinateValidationError,
    PrecisionOverflowError,
    EMUBoundaryError
)

from .converter import (
    FractionalEMUConverter
)

from .precision_engine import (
    VectorizedPrecisionEngine
)

# Convenience function
def create_fractional_converter(precision_mode: str = "subpixel",
                               **kwargs) -> FractionalEMUConverter:
    """
    Create a FractionalEMUConverter with specified precision mode.

    Args:
        precision_mode: "standard", "subpixel", "high", or "ultra"
        **kwargs: Additional UnitConverter parameters

    Returns:
        Configured FractionalEMUConverter instance

    Example:
        >>> converter = create_fractional_converter("subpixel")
        >>> emu_value = converter.to_fractional_emu("100.5px")
        >>> print(emu_value)  # 957262.5
    """
    return FractionalEMUConverter(
        precision_mode=PrecisionMode(precision_mode),
        **kwargs
    )


__all__ = [
    # Constants
    'EMU_PER_INCH',
    'EMU_PER_POINT',
    'EMU_PER_MM',
    'EMU_PER_CM',
    'DEFAULT_DPI',
    'POWERPOINT_MAX_EMU',
    'POWERPOINT_MIN_EMU',

    # Types
    'PrecisionMode',
    'FractionalCoordinateContext',

    # Errors
    'CoordinateValidationError',
    'PrecisionOverflowError',
    'EMUBoundaryError',

    # Main classes
    'FractionalEMUConverter',
    'VectorizedPrecisionEngine',

    # Convenience functions
    'create_fractional_converter',
]
```

**Checklist**:
- [ ] Create comprehensive public API
- [ ] Add package-level docstring with examples
- [ ] Export all necessary symbols
- [ ] Add convenience factory function
- [ ] Define `__all__` for clean imports

---

### Step 3: Fix Imports (2 hours)

#### 3.1 Update Internal Imports

**In all module files**:
- [ ] Replace `from .` imports with `from core.fractional_emu.` where needed
- [ ] Use relative imports within package (`.constants`, `.types`, etc.)
- [ ] Fix circular import issues if any

#### 3.2 Update External Imports

**Units module imports**:
```python
# BEFORE
from . import units as units_module

# AFTER
try:
    from core.units import UnitConverter, UnitType, ViewportContext
except ImportError:
    from units import UnitConverter, UnitType, ViewportContext  # Fallback
```

**ConversionServices imports**:
```python
# BEFORE
from .services.conversion_services import ConversionServices

# AFTER
try:
    from core.services.conversion_services import ConversionServices
except ImportError:
    # Graceful degradation if services not available
    ConversionServices = None
```

#### 3.3 Test Import Paths

```bash
# Test imports from various contexts
cd /Users/ynse/projects/svg2pptx

# Test package import
python -c "from core.fractional_emu import create_fractional_converter; print('✅ Package import works')"

# Test public API
python -c "from core.fractional_emu import FractionalEMUConverter, PrecisionMode; print('✅ Public API import works')"

# Test convenience function
python -c "from core.fractional_emu import create_fractional_converter; c = create_fractional_converter('subpixel'); print('✅ Convenience function works')"
```

---

### Step 4: Integration Updates (1 hour)

#### 4.1 Update ConversionServices

**File**: `core/services/conversion_services.py`

**Add fractional EMU converter**:
```python
from core.fractional_emu import create_fractional_converter

class ConversionServices:
    def __init__(self, ...):
        # ... existing services ...

        # Add fractional EMU converter
        self.fractional_emu_converter = create_fractional_converter("subpixel")

    @classmethod
    def create_default(cls):
        # ... existing setup ...
        services.fractional_emu_converter = create_fractional_converter("subpixel")
        return services
```

**Checklist**:
- [ ] Add fractional EMU converter to services
- [ ] Test `ConversionServices.create_default()`
- [ ] Verify no circular import issues

#### 4.2 Update Viewport Service Integration

**File**: `core/services/viewport_service.py`

**Optional enhancement**:
```python
# In ViewportService class
def svg_xy_to_fractional_emu(self, x, y, precision_mode='subpixel'):
    """
    Convert SVG coordinates to fractional EMUs with subpixel precision.

    Uses fractional EMU converter for higher accuracy.
    """
    from core.fractional_emu import create_fractional_converter

    converter = create_fractional_converter(precision_mode)
    # ... implementation
```

**Checklist**:
- [ ] Add fractional EMU methods to ViewportService (optional Phase 1)
- [ ] Test integration with existing viewport methods

---

### Step 5: Add Tests (3 hours)

#### 5.1 Port Tests from Benchmark Scripts

**Create**: `tests/unit/core/fractional_emu/test_converter.py`

**Test cases** (from `scripts/test_fractional_emu_simple.py`):
```python
import pytest
import numpy as np
from core.fractional_emu import (
    create_fractional_converter,
    FractionalEMUConverter,
    PrecisionMode
)

class TestFractionalEMUConverter:
    def test_create_converter(self):
        """Test converter creation with different precision modes."""
        converter = create_fractional_converter("subpixel")
        assert converter.precision_mode == PrecisionMode.SUBPIXEL
        assert converter.precision_factor == 100.0

    def test_fractional_pixel_conversion(self):
        """Test fractional pixel to EMU conversion."""
        converter = create_fractional_converter("subpixel")
        # 100.5px at 96 DPI = 100.5 * (914400 / 96) = 957262.5
        result = converter.to_fractional_emu("100.5px")
        expected = 957262.5
        assert abs(result - expected) < 0.01

    def test_backward_compatibility(self):
        """Test backward compatible to_emu() returns int."""
        converter = create_fractional_converter("subpixel")
        result = converter.to_emu("100.5px")
        assert isinstance(result, int)
        # Should round fractional EMU to int
        assert result == 957263  # Round up from 957262.5

    @pytest.mark.skipif(not np.NUMPY_AVAILABLE, reason="NumPy not available")
    def test_vectorized_conversion(self):
        """Test vectorized batch conversion performance."""
        converter = create_fractional_converter("subpixel")

        coords = [100.5, 200.25, 300.125]
        unit_types = [UnitType.PIXEL] * 3

        results = converter.vectorized_batch_convert(coords, unit_types)

        assert len(results) == 3
        assert all(isinstance(r, float) for r in results)
```

**Checklist**:
- [ ] Create test file structure
- [ ] Port 20+ tests from simple test script
- [ ] Add precision mode tests
- [ ] Add integration tests with UnitConverter
- [ ] Add transform integration tests

#### 5.2 Create Integration Tests

**Create**: `tests/integration/test_fractional_emu_integration.py`

```python
def test_conversion_services_integration():
    """Test fractional EMU integration with ConversionServices."""
    from core.services.conversion_services import ConversionServices

    services = ConversionServices.create_default()

    assert hasattr(services, 'fractional_emu_converter')
    assert services.fractional_emu_converter is not None

    # Test conversion through services
    result = services.fractional_emu_converter.to_fractional_emu("100.5px")
    assert result > 0
```

**Checklist**:
- [ ] Test ConversionServices integration
- [ ] Test transform integration
- [ ] Test unit system integration
- [ ] Test viewport service integration (if added)

#### 5.3 Run Validation Scripts

```bash
# Run simple validation
PYTHONPATH=. python scripts/test_fractional_emu_simple.py

# Expected output:
# ✅ NumPy available for vectorized operations
# ✅ Numba available for JIT compilation
# === Test 1: NumPy Precision Arithmetic ===
# Precision maintained: ✅ YES
# === Test 2: Vectorized Operations ===
# Speedup: 70.5x
# Target (15x): ✅ ACHIEVED
# ...
# 🎯 TASK 1.4 STATUS: ✅ COMPLETED SUCCESSFULLY

# Run performance benchmark
PYTHONPATH=. python scripts/fractional_emu_performance_benchmark.py

# Expected output:
# 🚀 Fractional EMU Performance Benchmark Suite
# === Scalar vs Vectorized EMU Conversion Benchmark ===
# Maximum speedup: 92.3x
# 15x Target: ✅ ACHIEVED
# 40x Stretch: ✅ ACHIEVED
# ...
# 🎯 TASK 1.4 COMPLETION: ✅ SUCCESSFUL
```

**Checklist**:
- [ ] Simple validation passes all tests
- [ ] Performance benchmark shows 15-40x speedup
- [ ] Precision accuracy < 1×10⁻⁶ pt
- [ ] No regressions from original implementation

---

### Step 6: Documentation (1 hour)

#### 6.1 Create Usage Guide

**File**: `docs/fractional-emu-usage-guide.md`

**Content**:
- Installation and setup
- Basic usage examples
- Precision mode selection guide
- Integration with existing code
- Performance optimization tips
- Troubleshooting common issues

#### 6.2 Create Migration Guide

**File**: `docs/fractional-emu-migration-guide.md`

**Content**:
- Changes from archived implementation
- Import path updates
- API changes (if any)
- Backward compatibility notes
- Performance comparison

#### 6.3 Update API Documentation

**Generate API docs**:
```bash
# Generate documentation with pdoc or sphinx
cd /Users/ynse/projects/svg2pptx
pdoc core/fractional_emu --html --output-dir docs/api/
```

**Checklist**:
- [ ] Create usage guide
- [ ] Create migration guide
- [ ] Generate API documentation
- [ ] Add examples to README

---

## Post-Migration Tasks

### Archive Cleanup

#### Move Prototype to Archive

```bash
# Move prototype implementation to archive
mkdir -p archive/research/fractional-emu-numpy-prototype
mv development/prototypes/precision-research/fractional_emu_numpy.py \
   archive/research/fractional-emu-numpy-prototype/

# Create README explaining why archived
cat > archive/research/fractional-emu-numpy-prototype/README.md << 'EOF'
# NumPy Fractional EMU Prototype

**Status**: Archived - Research Prototype
**Date**: 2025-01-06

This prototype explored a pure NumPy implementation of the fractional EMU system.

Key findings validated in production implementation:
- Vectorized operations achieve 70-100x speedup
- Advanced rounding algorithms (banker's, adaptive, smart quantization)
- Batch processing patterns

**Why Archived**:
- Archive implementation (`fractional_emu.py`) selected for migration
- More complete feature set with proper system integration
- This prototype served its research purpose successfully

**Migrated Implementation**: `core/fractional_emu/`
EOF
```

**Checklist**:
- [ ] Move prototype to archive with README
- [ ] Keep benchmark scripts in `scripts/`
- [ ] Document why prototype archived

#### Update Original Archive Location

```bash
# Add note to original archived file
cat > archive/legacy-src/FRACTIONAL_EMU_MIGRATED.md << 'EOF'
# Fractional EMU - MIGRATED

**Status**: ✅ Migrated to `core/fractional_emu/`
**Date**: 2025-01-06

This implementation has been successfully migrated to the core package:
- **New Location**: `core/fractional_emu/`
- **Migration Task**: Phase 1, Task 1.4
- **Status**: Production Ready

**Usage**:
```python
from core.fractional_emu import create_fractional_converter

converter = create_fractional_converter("subpixel")
emu_value = converter.to_fractional_emu("100.5px")
```

See `docs/fractional-emu-usage-guide.md` for complete documentation.
EOF
```

**Checklist**:
- [ ] Mark original archive file as migrated
- [ ] Add pointer to new location
- [ ] Keep original file for reference

---

## Validation Checklist

### Functional Validation

- [ ] **Import Tests**: All imports work from `core.fractional_emu`
- [ ] **Precision Tests**: <1×10⁻⁶ pt accuracy maintained
- [ ] **Unit Tests**: All unit tests pass
- [ ] **Integration Tests**: Integration with services/transforms/units works
- [ ] **Backward Compatibility**: `to_emu()` returns int correctly
- [ ] **Error Handling**: All validation and error cases work

### Performance Validation

- [ ] **Vectorized Speedup**: 15-40x speedup achieved (benchmark script)
- [ ] **Memory Efficiency**: No memory regressions
- [ ] **Cache Performance**: Caching provides expected speedup
- [ ] **Large Dataset**: Can process 100k+ coordinates efficiently

### Integration Validation

- [ ] **ConversionServices**: Fractional EMU in services
- [ ] **Transform Integration**: Coordinate transformation with precision works
- [ ] **Unit System**: All unit types convert correctly
- [ ] **Viewport Service**: Integration working (if implemented)

### Documentation Validation

- [ ] **Usage Guide**: Clear examples for common use cases
- [ ] **Migration Guide**: Covers all breaking changes
- [ ] **API Docs**: Complete API documentation generated
- [ ] **Docstrings**: All classes and methods documented

---

## Success Criteria

✅ **Package created**: `core/fractional_emu/` with proper structure
✅ **All modules working**: converter, precision_engine, types, errors, constants
✅ **Imports correct**: All import paths updated and tested
✅ **Tests passing**: Unit tests, integration tests, validation scripts
✅ **Performance met**: 15-40x vectorized speedup achieved
✅ **Precision validated**: <1×10⁻⁶ pt accuracy confirmed
✅ **Backward compatible**: `to_emu()` API preserved
✅ **Documentation complete**: Usage guide, migration guide, API docs
✅ **Archive cleaned**: Prototype archived, original marked as migrated

---

## Timeline

**Total Effort**: 8 hours

| Step | Task | Hours |
|------|------|-------|
| 1 | Create package structure | 1 |
| 2 | Split monolithic file | (included in 1) |
| 3 | Fix imports | 2 |
| 4 | Integration updates | 1 |
| 5 | Add tests | 3 |
| 6 | Documentation | 1 |

**Execution**: Phase 1, Task 1.4
**Dependencies**: Task 0.5 complete (this task provides migration plan)

---

**Status**: Ready for execution
**Created**: 2025-01-06
**Phase**: 0 (Preparation Complete) → Ready for Phase 1
