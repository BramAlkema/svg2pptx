# Hardcoded EMU Conversion - Replacement Plan

**Date**: 2025-01-06
**Task**: Phase 0, Task 0.2 - Create Replacement Plan
**Status**: ✅ Complete
**Total Conversions to Replace**: 56

---

## Executive Summary

This document provides a **step-by-step replacement plan** for all 56 hardcoded `* 12700` conversions, organized by Priority and mapped to Phase 3 tasks.

### Replacement Order

1. **P0 Mappers** (40 instances) - Tasks 3.1-3.4 (26 hours)
2. **P1 Services** (12 instances) - Task 3.5 (8 hours)
3. **P2 Infrastructure** (4 instances) - Task 3.6 (4 hours)

**Total Effort**: 36 hours (Phase 3)

---

## Replacement Patterns

### Pattern 1: Coordinate Transformation (40 instances)

**Current (WRONG)**:
```python
x_emu = int(shape.x * 12700)
y_emu = int(shape.y * 12700)
```

**After Phase 2 (coordinates pre-transformed)** + **Phase 3 (fractional EMU)**:
```python
# Standard mode (int - backward compatible)
from core.units import unit
x_emu = unit(f"{shape.x}pt").to_emu()  # Returns int

# OR Precision mode (float - sub-pixel)
from core.fractional_emu import create_fractional_converter
converter = create_fractional_converter(precision_mode)  # "subpixel", "high", "ultra"
x_emu = converter.to_fractional_emu(shape.x)  # Returns float
```

**XML Output (both modes)**:
```python
# Always round to int for OOXML compliance
xml = f'<a:off x="{int(round(x_emu))}" y="{int(round(y_emu))}"/>'
```

---

### Pattern 2: Dimension Conversion (12 instances)

**Current (WRONG)**:
```python
width_emu = int(shape.width * 12700)
height_emu = int(shape.height * 12700)
```

**After Phase 2+3**:
```python
# Same as coordinates - dimensions also transformed
width_emu = converter.to_fractional_emu(shape.width)
height_emu = converter.to_fractional_emu(shape.height)
```

---

### Pattern 3: Stroke Width (2 instances)

**Current (WRONG)**:
```python
stroke_emu = int(stroke.width * 12700)
```

**After Phase 2+3**:
```python
# Stroke width needs viewport scale consideration
stroke_emu = converter.to_fractional_emu(stroke.width)
```

---

### Pattern 4: Filter Parameters (4 instances)

**Current (WRONG)**:
```python
blur_emu = int(std_deviation * 12700)
```

**After Phase 2+3**:
```python
# Filter parameters need careful scaling
blur_emu = converter.to_fractional_emu(std_deviation)
```

---

## Task 3.1: Circle and Ellipse Mappers (7 instances - 4 hours)

### File: `core/map/circle_mapper.py`

**Lines 77-79**:

**Before**:
```python
cx_emu = int(circle.center.x * 12700)
cy_emu = int(circle.center.y * 12700)
r_emu = int(circle.radius * 12700)
```

**After**:
```python
from core.fractional_emu import create_fractional_converter

# Get precision mode from context or use default
precision_mode = getattr(context, 'precision_mode', 'standard')

if precision_mode == 'standard':
    # Backward compatible - returns int
    from core.units import unit
    cx_emu = unit(f"{circle.center.x}pt").to_emu()
    cy_emu = unit(f"{circle.center.y}pt").to_emu()
    r_emu = unit(f"{circle.radius}pt").to_emu()
else:
    # High precision - returns float
    converter = create_fractional_converter(precision_mode)
    cx_emu = converter.to_fractional_emu(circle.center.x)
    cy_emu = converter.to_fractional_emu(circle.center.y)
    r_emu = converter.to_fractional_emu(circle.radius)

# XML generation works for both int and float
xml = f'<a:off x="{int(round(cx_emu))}" y="{int(round(cy_emu))}"/>'
```

**Tests to Update**:
- `tests/unit/core/map/test_circle_mapper.py`
- Add precision mode tests
- Verify backward compatibility

---

### File: `core/map/ellipse_mapper.py`

**Lines 63-66**:

**Before**:
```python
cx_emu = int(ellipse.center.x * 12700)
cy_emu = int(ellipse.center.y * 12700)
rx_emu = int(ellipse.radius_x * 12700)
ry_emu = int(ellipse.radius_y * 12700)
```

**After**: Same pattern as circle

**Tests to Update**:
- `tests/unit/core/map/test_ellipse_mapper.py`

---

## Task 3.2: Rectangle Mapper (4 instances - 4 hours)

### File: `core/map/rect_mapper.py`

**Lines 64-67**:

**Before**:
```python
x_emu = int(rect.bounds.x * 12700)
y_emu = int(rect.bounds.y * 12700)
width_emu = int(rect.bounds.width * 12700)
height_emu = int(rect.bounds.height * 12700)
```

**After**:
```python
from core.fractional_emu import create_fractional_converter

precision_mode = getattr(context, 'precision_mode', 'standard')

if precision_mode == 'standard':
    from core.units import unit
    x_emu = unit(f"{rect.bounds.x}pt").to_emu()
    y_emu = unit(f"{rect.bounds.y}pt").to_emu()
    width_emu = unit(f"{rect.bounds.width}pt").to_emu()
    height_emu = unit(f"{rect.bounds.height}pt").to_emu()
else:
    converter = create_fractional_converter(precision_mode)
    x_emu = converter.to_fractional_emu(rect.bounds.x)
    y_emu = converter.to_fractional_emu(rect.bounds.y)
    width_emu = converter.to_fractional_emu(rect.bounds.width)
    height_emu = converter.to_fractional_emu(rect.bounds.height)

# XML output (int rounding)
xml = f'<a:off x="{int(round(x_emu))}" y="{int(round(y_emu))}"/>'
xml += f'<a:ext cx="{int(round(width_emu))}" cy="{int(round(height_emu))}"/>'
```

**Tests to Update**:
- `tests/unit/core/map/test_rect_mapper.py`

---

## Task 3.3: Path Mapper (13 instances - 8 hours)

### File: `core/map/path_mapper.py`

This is the most complex mapper with 13 conversions across multiple contexts.

**Context 1: Lines 150-153 (Bounding box)**

**Before**:
```python
x_emu = int(bbox.x * 12700)  # Convert to EMU (1 point = 12700 EMU)
y_emu = int(bbox.y * 12700)
width_emu = int(bbox.width * 12700)
height_emu = int(bbox.height * 12700)
```

**After**: Use standard pattern with precision mode support

**Context 2: Line 458 (Stroke width)**

**Before**:
```python
width_emu = int(stroke.width * 12700)  # Convert to EMU
```

**After**:
```python
precision_mode = getattr(context, 'precision_mode', 'standard')

if precision_mode == 'standard':
    from core.units import unit
    width_emu = unit(f"{stroke.width}pt").to_emu()
else:
    converter = create_fractional_converter(precision_mode)
    width_emu = converter.to_fractional_emu(stroke.width)
```

**Context 3: Lines 311-314, 525-528**: Same bbox pattern as Context 1

**Tests to Update**:
- `tests/unit/core/map/test_path_mapper.py`
- Test stroke width scaling
- Test bbox positioning for various path types

**Estimated Effort**: 8 hours (most complex, highest instance count)

---

## Task 3.4: Group and Image Mappers (16 instances - 10 hours)

### File: `core/map/group_mapper.py` (8 instances)

**Lines 135-138 and 205-208**: Two identical bbox conversions

**Before**:
```python
x_emu = int(bbox.x * 12700)  # Convert to EMU
y_emu = int(bbox.y * 12700)
width_emu = int(bbox.width * 12700)
height_emu = int(bbox.height * 12700)
```

**After**: Standard pattern with precision mode

**Tests to Update**:
- `tests/unit/core/map/test_group_mapper.py`
- Test nested group positioning

---

### File: `core/map/image_mapper.py` (8 instances)

**Three contexts**: Lines 123-126, 139-142, 153-156

All use same pattern:
```python
x_emu = int(image.origin.x * 12700)  # Convert to EMU
y_emu = int(image.origin.y * 12700)
width_emu = int(image.size.width * 12700)  # or scaled_width
height_emu = int(image.size.height * 12700)  # or scaled_height
```

**After**: Standard pattern

**Special Consideration**: Lines 123-126 use `scaled_width/scaled_height` - ensure scaling is applied before EMU conversion

**Tests to Update**:
- `tests/unit/core/map/test_image_mapper.py`
- Test image scaling accuracy
- Test image positioning

**Estimated Effort**: 10 hours (2 files, 16 instances, testing complexity)

---

## Task 3.5: Services and Helpers (6 instances - 6 hours)

### File: `core/services/filter_service.py` (4 instances)

**Line 104: Gaussian blur**

**Before**:
```python
blur_radius = float(std_deviation) * 12700  # Convert to EMUs
```

**After**:
```python
# Note: Already returns float, which is good
precision_mode = getattr(context, 'precision_mode', 'standard')

if precision_mode == 'standard':
    from core.units import unit
    blur_radius = float(unit(f"{std_deviation}pt").to_emu())
else:
    converter = create_fractional_converter(precision_mode)
    blur_radius = converter.to_fractional_emu(std_deviation)
```

**Lines 115-117: Drop shadow**

**Before**:
```python
dx_emu = int(float(dx) * 12700)
dy_emu = int(float(dy) * 12700)
blur_emu = int(float(std_deviation) * 12700)
```

**After**: Same pattern as blur, but for all three parameters

**Tests to Update**:
- `tests/unit/services/test_filter_service.py`
- Test filter effect accuracy
- Verify blur radius scaling

---

### File: `core/map/shape_helpers.py` (1 instance)

**Line 118: Stroke width helper**

**Before**:
```python
width_emu = int(stroke.width * 12700)
```

**After**:
```python
# This is a shared helper - needs precision mode parameter
def convert_stroke_width(stroke_width: float, precision_mode: str = 'standard') -> int | float:
    """Convert stroke width to EMU with precision mode support."""
    if precision_mode == 'standard':
        from core.units import unit
        return unit(f"{stroke_width}pt").to_emu()
    else:
        converter = create_fractional_converter(precision_mode)
        return converter.to_fractional_emu(stroke_width)
```

**Tests to Update**:
- `tests/unit/core/map/test_shape_helpers.py`
- Test stroke width conversion in both modes

---

### File: `core/map/emf_adapter.py` (2 instances)

**Lines 89-90: EMF size constraints**

**Before**:
```python
width_emu = max(914400, int(bbox.width * 12700))  # At least 1 inch
height_emu = max(914400, int(bbox.height * 12700))
```

**After**:
```python
precision_mode = getattr(context, 'precision_mode', 'standard')

if precision_mode == 'standard':
    from core.units import unit
    width_emu = max(914400, unit(f"{bbox.width}pt").to_emu())
    height_emu = max(914400, unit(f"{bbox.height}pt").to_emu())
else:
    converter = create_fractional_emu(precision_mode)
    # Note: Keep minimum as int for comparison
    width_emu = max(914400, converter.to_fractional_emu(bbox.width))
    height_emu = max(914400, converter.to_fractional_emu(bbox.height))
```

**Tests to Update**:
- Test EMF minimum size constraint
- Verify fallback works correctly

---

## Task 3.6: Infrastructure and Utilities (4 instances - 4 hours)

### File: `core/viewbox/core.py` (2 instances)

**Lines 1281-1282: NumPy vectorized conversion**

**Before**:
```python
x_emu = (x_coords * 12700).astype(int)
y_emu = (y_coords * 12700).astype(int)
```

**Investigation Needed**:
- **Check context**: Are `x_coords`/`y_coords` already transformed points?
- **If yes**: This might be correct, just needs fractional EMU support
- **If no**: Needs full transformation pipeline

**Potential After**:
```python
# If already transformed points
from core.fractional_emu import EMU_PER_PT

# Precision mode from context
if precision_mode == 'standard':
    x_emu = (x_coords * EMU_PER_PT).astype(int)
    y_emu = (y_coords * EMU_PER_PT).astype(int)
else:
    # Fractional EMU - keep as float until final XML
    x_emu = x_coords * EMU_PER_PT  # float array
    y_emu = y_coords * EMU_PER_PT  # float array
```

**Action**:
1. Read `core/viewbox/core.py` lines 1270-1290 to understand context
2. Determine if coords are pre-transformed
3. Update accordingly

---

### File: `core/utils/enhanced_xml_builder.py` (2 instances)

**Line 1217: Shadow blur**

**Before**:
```python
shadow_blur = min(int(surface_scale * 12700), 127000) if with_shadow else 25400
```

**After**:
```python
if with_shadow:
    precision_mode = getattr(context, 'precision_mode', 'standard')

    if precision_mode == 'standard':
        from core.units import unit
        blur_emu = unit(f"{surface_scale}pt").to_emu()
    else:
        converter = create_fractional_converter(precision_mode)
        blur_emu = converter.to_fractional_emu(surface_scale)

    shadow_blur = min(int(round(blur_emu)), 127000)
else:
    shadow_blur = 25400
```

**Line 1366: Highlight blur**

**Before**:
```python
highlight_blur = int(surface_scale * 12700)  # Sharp highlight
```

**After**: Same pattern

**Tests to Update**:
- Test enhanced XML builder effects
- Verify maximum blur constraint

---

### File: `core/paths/drawingml_generator.py` (1 instance)

**Line 630: Path width**

**Before**:
```python
width_emu = int(width_pt * 12700)
```

**Note**: Variable name suggests already in points

**After**:
```python
# Variable name suggests width_pt is already in points
precision_mode = getattr(context, 'precision_mode', 'standard')

if precision_mode == 'standard':
    width_emu = int(round(width_pt * 12700))  # Keep current behavior
else:
    converter = create_fractional_converter(precision_mode)
    width_emu = converter.to_fractional_emu(width_pt)
```

---

## Validation Strategy

### Step 1: Per-File Validation

After each file is updated:

```bash
# Run file-specific tests
PYTHONPATH=. pytest tests/unit/core/map/test_circle_mapper.py -v

# Check for hardcoded conversions in updated file
grep "\* 12700\|12700 \*" core/map/circle_mapper.py
# Should return: no results
```

### Step 2: Integration Testing

After each task (3.1-3.6):

```bash
# Run all mapper tests
PYTHONPATH=. pytest tests/unit/core/map/ -v

# Run integration tests
PYTHONPATH=. pytest tests/integration/ -v
```

### Step 3: Visual Regression

After all conversions replaced:

```bash
# Compare with baseline (from Task 0.6)
python tests/baseline/compare_with_new.py

# Manual visual inspection
open tests/baseline/outputs/pptx/*.pptx
```

### Step 4: Final Validation

```bash
# Zero hardcoded conversions
grep -r "\* 12700\|12700 \*" core/ --include="*.py" | wc -l
# Expected: 0

# All tests pass
PYTHONPATH=. pytest tests/ -v

# Precision validation
PYTHONPATH=. pytest tests/unit/fractional_emu/ -v
```

---

## Risk Mitigation

### High-Risk Files

**`core/map/path_mapper.py`** (13 instances):
- Most complex mapper
- Many edge cases (different path types)
- **Mitigation**: Comprehensive path tests, visual regression

### Medium-Risk Files

**`core/services/filter_service.py`** (4 instances):
- Affects visual quality
- **Mitigation**: Visual comparison with baseline

### Low-Risk Files

**`core/viewbox/core.py`** (2 instances):
- May already be correct
- **Mitigation**: Code review before changing

---

## Progress Tracking

### Task 3.1: Circle/Ellipse ← 4 hours
- [ ] `core/map/circle_mapper.py` (3 instances)
- [ ] `core/map/ellipse_mapper.py` (4 instances)
- [ ] Update tests
- [ ] Verify precision

### Task 3.2: Rectangle ← 4 hours
- [ ] `core/map/rect_mapper.py` (4 instances)
- [ ] Update tests
- [ ] Visual regression

### Task 3.3: Path ← 8 hours
- [ ] `core/map/path_mapper.py` (13 instances)
- [ ] Update extensive tests
- [ ] Edge case validation

### Task 3.4: Group/Image ← 10 hours
- [ ] `core/map/group_mapper.py` (8 instances)
- [ ] `core/map/image_mapper.py` (8 instances)
- [ ] Nested group tests
- [ ] Image scaling tests

### Task 3.5: Services/Helpers ← 6 hours
- [ ] `core/services/filter_service.py` (4 instances)
- [ ] `core/map/shape_helpers.py` (1 instance)
- [ ] `core/map/emf_adapter.py` (2 instances)
- [ ] Filter effect tests

### Task 3.6: Infrastructure ← 4 hours
- [ ] `core/viewbox/core.py` (2 instances) - Investigate first
- [ ] `core/utils/enhanced_xml_builder.py` (2 instances)
- [ ] `core/paths/drawingml_generator.py` (1 instance)
- [ ] Infrastructure tests

---

## Success Criteria

✅ **All 56 conversions replaced**
✅ **Zero hardcoded `* 12700` remaining**
✅ **All tests passing**
✅ **Visual regression tests pass**
✅ **Precision validation <1×10⁻⁶ pt**
✅ **Backward compatibility maintained (standard mode)**

---

**Status**: ✅ **COMPLETE**
**Date**: 2025-01-06
**Next**: Task 0.3 - Archive Conflicting Code
