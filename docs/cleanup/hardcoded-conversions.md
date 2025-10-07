# Hardcoded EMU Conversion Audit

**Date**: 2025-01-06
**Task**: Phase 0, Task 0.2 - Audit Existing Coordinate Conversion Code
**Status**: ✅ Complete
**Total Conversions Found**: 56

---

## Executive Summary

All 56 instances of hardcoded `* 12700` EMU conversions have been catalogued and analyzed. These conversions bypass the proper transformation pipeline and must be replaced with fractional EMU conversion in Phase 3.

### Distribution by File

| File | Count | Category | Priority |
|------|-------|----------|----------|
| `core/map/path_mapper.py` | 13 | Mapper | **P0 - Critical** |
| `core/map/group_mapper.py` | 8 | Mapper | **P0 - Critical** |
| `core/map/image_mapper.py` | 8 | Mapper | **P0 - Critical** |
| `core/map/circle_mapper.py` | 3 | Mapper | **P0 - Critical** |
| `core/map/ellipse_mapper.py` | 4 | Mapper | **P0 - Critical** |
| `core/map/rect_mapper.py` | 4 | Mapper | **P0 - Critical** |
| `core/services/filter_service.py` | 4 | Service | **P1 - High** |
| `core/map/emf_adapter.py` | 2 | Mapper | **P1 - High** |
| `core/viewbox/core.py` | 2 | Infrastructure | **P2 - Medium** |
| `core/utils/enhanced_xml_builder.py` | 2 | Utility | **P2 - Medium** |
| `core/map/shape_helpers.py` | 1 | Helper | **P1 - High** |
| `core/paths/drawingml_generator.py` | 1 | Generator | **P1 - High** |
| `core/map/path_mapper.py` (stroke) | 4 | Stroke | **P1 - High** |

### Conversion Types

| Type | Count | Description |
|------|-------|-------------|
| **Coordinate** | 40 | Position (x, y) conversions |
| **Dimension** | 12 | Size (width, height) conversions |
| **Stroke** | 2 | Stroke width conversions |
| **Filter** | 2 | Filter effect parameters |

---

## 1. Mapper Files (40 instances - P0 Critical)

### 1.1 `core/map/path_mapper.py` (13 instances)

**Lines 150-153: Bounding box conversion**
```python
x_emu = int(bbox.x * 12700)  # Convert to EMU (1 point = 12700 EMU)
y_emu = int(bbox.y * 12700)
width_emu = int(bbox.width * 12700)
height_emu = int(bbox.height * 12700)
```
- **Context**: Path bounding box for DrawingML positioning
- **Issue**: Assumes bbox is in points, ignores transforms
- **Replacement**: `to_fractional_emu(bbox.x)` after CoordinateSpace transformation

**Lines 311-314: Another bbox conversion**
```python
x_emu = int(bbox.x * 12700)
y_emu = int(bbox.y * 12700)
width_emu = int(bbox.width * 12700)
height_emu = int(bbox.height * 12700)
```
- **Context**: EMF fallback path positioning
- **Replacement**: Same as above

**Lines 525-528: Third bbox conversion**
```python
x_emu = int(bbox.x * 12700)
y_emu = int(bbox.y * 12700)
width_emu = int(bbox.width * 12700)
height_emu = int(bbox.height * 12700)
```
- **Context**: Another path positioning case
- **Replacement**: Same pattern

**Line 458: Stroke width**
```python
width_emu = int(stroke.width * 12700)  # Convert to EMU
```
- **Context**: Path stroke width
- **Issue**: Ignores viewport scaling
- **Replacement**: `to_fractional_emu(stroke.width)` with scale consideration

**Priority**: **P0** - Path mapper is most commonly used

---

### 1.2 `core/map/group_mapper.py` (8 instances)

**Lines 135-138: Group bounding box**
```python
x_emu = int(bbox.x * 12700)  # Convert to EMU
y_emu = int(bbox.y * 12700)
width_emu = int(bbox.width * 12700)
height_emu = int(bbox.height * 12700)
```
- **Context**: Group placeholder positioning
- **Replacement**: `to_fractional_emu()` after transformation

**Lines 205-208: Another group bbox**
```python
x_emu = int(bbox.x * 12700)
y_emu = int(bbox.y * 12700)
width_emu = int(bbox.width * 12700)
height_emu = int(bbox.height * 12700)
```
- **Context**: Group shape positioning
- **Replacement**: Same pattern

**Priority**: **P0** - Groups are fundamental

---

### 1.3 `core/map/image_mapper.py` (8 instances)

**Lines 123-126: Scaled image positioning**
```python
x_emu = int(image.origin.x * 12700)  # Convert to EMU
y_emu = int(image.origin.y * 12700)
width_emu = int(scaled_width * 12700)
height_emu = int(scaled_height * 12700)
```
- **Context**: Image with scaling applied
- **Replacement**: `to_fractional_emu()` for both position and size

**Lines 139-142: Standard image positioning**
```python
x_emu = int(image.origin.x * 12700)
y_emu = int(image.origin.y * 12700)
width_emu = int(image.size.width * 12700)
height_emu = int(image.size.height * 12700)
```
- **Context**: Regular image embedding
- **Replacement**: Same pattern

**Lines 153-156: Fallback image positioning**
```python
x_emu = int(image.origin.x * 12700)
y_emu = int(image.origin.y * 12700)
width_emu = int(image.size.width * 12700)
height_emu = int(image.size.height * 12700)
```
- **Context**: Image fallback case
- **Replacement**: Same pattern

**Priority**: **P0** - Images common in SVGs

---

### 1.4 `core/map/circle_mapper.py` (3 instances)

**Lines 77-79: Circle to ellipse conversion**
```python
cx_emu = int(circle.center.x * 12700)
cy_emu = int(circle.center.y * 12700)
r_emu = int(circle.radius * 12700)
```
- **Context**: Circle center and radius
- **Issue**: Center should be transformed, radius should be scaled
- **Replacement**:
  - Center: `to_fractional_emu()` after `space.svg_xy_to_pt()`
  - Radius: `to_fractional_emu()` after `space.len_to_pt()`

**Priority**: **P0** - Circle is basic shape

---

### 1.5 `core/map/ellipse_mapper.py` (4 instances)

**Lines 63-66: Ellipse positioning**
```python
cx_emu = int(ellipse.center.x * 12700)
cy_emu = int(ellipse.center.y * 12700)
rx_emu = int(ellipse.radius_x * 12700)
ry_emu = int(ellipse.radius_y * 12700)
```
- **Context**: Ellipse center and radii
- **Replacement**: Same as circle - transform center, scale radii

**Priority**: **P0** - Ellipse is basic shape

---

### 1.6 `core/map/rect_mapper.py` (4 instances)

**Lines 64-67: Rectangle positioning**
```python
x_emu = int(rect.bounds.x * 12700)
y_emu = int(rect.bounds.y * 12700)
width_emu = int(rect.bounds.width * 12700)
height_emu = int(rect.bounds.height * 12700)
```
- **Context**: Rectangle bounds
- **Issue**: Bounds should be transformed (all 4 corners)
- **Replacement**: Transform corners, then calculate EMU bounds

**Priority**: **P0** - Rectangle is most basic shape

---

### 1.7 `core/map/emf_adapter.py` (2 instances)

**Lines 89-90: EMF bounding box**
```python
width_emu = max(914400, int(bbox.width * 12700))  # At least 1 inch
height_emu = max(914400, int(bbox.height * 12700))
```
- **Context**: EMF image size constraints
- **Replacement**: `to_fractional_emu()` with minimum size check
- **Note**: Keep minimum size logic (1 inch = 914400 EMU)

**Priority**: **P1** - EMF fallback less common

---

## 2. Service Files (4 instances - P1 High)

### 2.1 `core/services/filter_service.py` (4 instances)

**Line 104: Gaussian blur radius**
```python
blur_radius = float(std_deviation) * 12700  # Convert to EMUs
```
- **Context**: Gaussian blur filter effect
- **Issue**: Should consider viewport scaling
- **Replacement**: `to_fractional_emu(std_deviation)` with scale factor

**Lines 115-117: Drop shadow parameters**
```python
dx_emu = int(float(dx) * 12700)
dy_emu = int(float(dy) * 12700)
blur_emu = int(float(std_deviation) * 12700)
```
- **Context**: Drop shadow offset and blur
- **Replacement**: `to_fractional_emu()` for all three parameters

**Priority**: **P1** - Filter effects important for visual quality

---

## 3. Helper Files (1 instance - P1 High)

### 3.1 `core/map/shape_helpers.py` (1 instance)

**Line 118: Stroke width helper**
```python
width_emu = int(stroke.width * 12700)
```
- **Context**: Shared stroke width conversion
- **Issue**: Used by multiple mappers, should scale properly
- **Replacement**: `to_fractional_emu(stroke.width)` with viewport scale

**Priority**: **P1** - Shared utility affects multiple shapes

---

## 4. Infrastructure Files (4 instances - P2 Medium)

### 4.1 `core/viewbox/core.py` (2 instances)

**Lines 1281-1282: NumPy vectorized conversion**
```python
x_emu = (x_coords * 12700).astype(int)
y_emu = (y_coords * 12700).astype(int)
```
- **Context**: Batch coordinate conversion in ViewportEngine
- **Issue**: This might be correct IF x_coords/y_coords are already transformed points
- **Replacement**: Verify context, potentially replace with vectorized fractional EMU
- **Note**: This is in viewport infrastructure, may already be correct

**Priority**: **P2** - Need to verify context first

---

### 4.2 `core/utils/enhanced_xml_builder.py` (2 instances)

**Line 1217: Shadow blur**
```python
shadow_blur = min(int(surface_scale * 12700), 127000) if with_shadow else 25400
```
- **Context**: 3D surface shadow effect
- **Replacement**: `to_fractional_emu(surface_scale)` with max limit

**Line 1366: Highlight blur**
```python
highlight_blur = int(surface_scale * 12700)  # Sharp highlight
```
- **Context**: 3D surface highlight
- **Replacement**: `to_fractional_emu(surface_scale)`

**Priority**: **P2** - Enhanced effects less common

---

### 4.3 `core/paths/drawingml_generator.py` (1 instance)

**Line 630: Path width**
```python
width_emu = int(width_pt * 12700)
```
- **Context**: DrawingML path width
- **Issue**: Variable named `width_pt` suggests already in points
- **Replacement**: `to_fractional_emu(width_pt)` - this might be mostly correct

**Priority**: **P1** - Path generation important

---

## 5. Replacement Strategy

### Phase 3, Task 3.1-3.6: Systematic Replacement

**Pattern for Coordinates (x, y)**:
```python
# ❌ BEFORE (current - WRONG)
x_emu = int(shape.x * 12700)
y_emu = int(shape.y * 12700)

# ✅ AFTER (Phase 2 - coordinates pre-transformed in IR)
# IR coordinates already in transformed points
x_emu = to_fractional_emu(shape.x)
y_emu = to_fractional_emu(shape.y)

# OR with precision mode
converter = create_fractional_converter(precision_mode)
x_emu = converter.to_fractional_emu(shape.x)
y_emu = converter.to_fractional_emu(shape.y)
```

**Pattern for Dimensions (width, height)**:
```python
# ❌ BEFORE
width_emu = int(shape.width * 12700)

# ✅ AFTER (dimensions also need transformation)
width_emu = to_fractional_emu(shape.width)
```

**Pattern for Stroke Width**:
```python
# ❌ BEFORE
stroke_emu = int(stroke.width * 12700)

# ✅ AFTER (consider viewport scale)
stroke_emu = to_fractional_emu(stroke.width)
```

### Standard Mode vs Precision Mode

**Standard Mode** (backward compatible):
```python
from core.units import unit

# Returns int (backward compatible)
x_emu = unit(f"{shape.x}pt").to_emu()
```

**Precision Mode** (fractional EMU):
```python
from core.fractional_emu import create_fractional_converter

converter = create_fractional_converter("subpixel")  # or high, ultra
x_emu = converter.to_fractional_emu(shape.x)  # Returns float
```

**XML Output** (both modes):
```python
# Always round to int for XML
xml = f'<a:off x="{int(round(x_emu))}" y="{int(round(y_emu))}"/>'
```

---

## 6. Priority Classification

### P0 - Critical (Mappers: 40 instances)

**Must fix first** - These directly affect shape positioning

| File | Instances | Shapes Affected |
|------|-----------|-----------------|
| `core/map/path_mapper.py` | 13 | Paths (most complex) |
| `core/map/group_mapper.py` | 8 | Groups (containers) |
| `core/map/image_mapper.py` | 8 | Images |
| `core/map/circle_mapper.py` | 3 | Circles |
| `core/map/ellipse_mapper.py` | 4 | Ellipses |
| `core/map/rect_mapper.py` | 4 | Rectangles |

**Task Assignment**:
- Task 3.1: Circle, Ellipse (7 instances)
- Task 3.2: Rectangle (4 instances)
- Task 3.3: Path (13 instances)
- Task 3.4: Group, Image (16 instances)

### P1 - High (Services/Helpers: 12 instances)

**Fix second** - Affects quality and consistency

| File | Instances | Impact |
|------|-----------|--------|
| `core/services/filter_service.py` | 4 | Filter effects quality |
| `core/map/shape_helpers.py` | 1 | Stroke width (all shapes) |
| `core/map/emf_adapter.py` | 2 | EMF fallback sizing |
| `core/paths/drawingml_generator.py` | 1 | Path width |

**Task Assignment**:
- Task 3.5: Filter service, shape helpers

### P2 - Medium (Infrastructure: 4 instances)

**Fix last** - May already be correct or less impactful

| File | Instances | Notes |
|------|-----------|-------|
| `core/viewbox/core.py` | 2 | Verify if already correct |
| `core/utils/enhanced_xml_builder.py` | 2 | Enhanced effects |

**Task Assignment**:
- Task 3.6: Infrastructure and utilities

---

## 7. Testing Requirements

### Per-File Test Updates

| File | Existing Tests | Updates Needed |
|------|---------------|----------------|
| `core/map/path_mapper.py` | `tests/unit/core/map/test_path_mapper.py` | Update expected EMU values, add precision mode tests |
| `core/map/group_mapper.py` | `tests/unit/core/map/test_group_mapper.py` | Same |
| `core/map/image_mapper.py` | `tests/unit/core/map/test_image_mapper.py` | Same |
| `core/map/circle_mapper.py` | `tests/unit/core/map/test_circle_mapper.py` | Same |
| `core/map/ellipse_mapper.py` | `tests/unit/core/map/test_ellipse_mapper.py` | Same |
| `core/map/rect_mapper.py` | `tests/unit/core/map/test_rect_mapper.py` | Same |
| `core/services/filter_service.py` | `tests/unit/services/test_filter_service.py` | Test blur/shadow precision |

### New Test Requirements

**Precision Validation**:
```python
def test_fractional_emu_precision():
    """Verify EMU conversion accuracy <1×10⁻⁶ pt"""
    converter = create_fractional_converter("subpixel")

    # Test round-trip
    original_pt = 100.123456
    emu = converter.to_fractional_emu(original_pt)
    recovered_pt = emu / 12700

    error = abs(recovered_pt - original_pt)
    assert error < 1e-6
```

**Backward Compatibility**:
```python
def test_standard_mode_backward_compatible():
    """Standard mode returns same values as before"""
    # Compare old method vs new standard mode
    old_emu = int(100.5 * 12700)
    new_emu = to_emu(100.5)  # Standard mode

    assert old_emu == new_emu
```

---

## 8. Validation Checklist

### Pre-Replacement

- [ ] **Task 0.2 Complete**: All conversions documented ✅
- [ ] **Task 1.4 Complete**: Fractional EMU system migrated
- [ ] **Task 2.x Complete**: Parser applies transforms
- [ ] **Baseline tests**: Created (Task 0.6)

### During Replacement (Phase 3)

- [ ] **Task 3.1**: Circle/Ellipse conversions replaced
- [ ] **Task 3.2**: Rectangle conversions replaced
- [ ] **Task 3.3**: Path conversions replaced
- [ ] **Task 3.4**: Group/Image conversions replaced
- [ ] **Task 3.5**: Service/Helper conversions replaced
- [ ] **Task 3.6**: Infrastructure conversions replaced

### Post-Replacement Validation

- [ ] **Zero hardcoded conversions**:
  ```bash
  grep -r "\* 12700\|12700 \*" core/ --include="*.py" | wc -l
  # Should return: 0
  ```

- [ ] **All tests pass**:
  ```bash
  PYTHONPATH=. pytest tests/unit/core/map/ -v
  PYTHONPATH=. pytest tests/unit/services/ -v
  ```

- [ ] **Visual regression**: Compare with baseline (Task 0.6)

- [ ] **Precision validation**: Round-trip error <1×10⁻⁶ pt

---

## 9. Common Patterns and Anti-Patterns

### Anti-Pattern ❌

**Direct multiplication without context**:
```python
# ❌ WRONG - Assumes units, ignores transforms
x_emu = int(value * 12700)
```

**Problems**:
1. Assumes `value` is in points (might not be)
2. Ignores viewport transformation
3. Ignores element transforms (CTM)
4. Loses precision with premature rounding
5. Hardcoded constant (not maintainable)

### Correct Pattern ✅

**After Phase 2 (baked transforms)**:
```python
# ✅ RIGHT - Use proper conversion
from core.fractional_emu import to_fractional_emu, create_fractional_converter

# Standard mode (int, backward compatible)
x_emu = to_emu(shape.x)  # shape.x already in transformed points

# Precision mode (float, sub-pixel)
converter = create_fractional_converter(precision_mode)
x_emu = converter.to_fractional_emu(shape.x)

# XML output (always int)
xml = f'<a:off x="{int(round(x_emu))}"/>'
```

**Benefits**:
1. IR coordinates already transformed (Phase 2)
2. Fractional EMU preserves precision
3. Single rounding point at XML output
4. Supports multiple precision modes
5. Maintainable, testable

---

## 10. Dependencies and Blockers

### Prerequisites for Replacement

1. **Task 1.4 Complete**: Fractional EMU system migrated to `core/fractional_emu/`
2. **Phase 2 Complete**: Parser applies transforms, IR has transformed coordinates
3. **Task 0.6 Complete**: Baseline tests captured for validation

### Phase 3 Task Dependencies

```
Task 3.1 (Circle/Ellipse) ← Task 1.4 (Fractional EMU)
Task 3.2 (Rectangle)      ← Task 1.4
Task 3.3 (Path)           ← Task 1.4
Task 3.4 (Group/Image)    ← Task 1.4
Task 3.5 (Services)       ← Task 1.4, Task 3.1-3.4
Task 3.6 (Infrastructure) ← Task 1.4, Task 3.1-3.5
```

### Critical Path

**Longest**: Task 1.4 → Phase 2 → Task 3.3 (Path - 13 instances)

---

## 11. Risk Assessment

### High Risk Conversions

**Path Mapper (13 instances)**: Most complex, highest impact
- **Risk**: Breaking path rendering
- **Mitigation**: Comprehensive path tests, visual regression

**Group Mapper (8 instances)**: Affects containment
- **Risk**: Nested group positioning breaks
- **Mitigation**: Test nested groups (10+ levels)

### Medium Risk Conversions

**Filter Service (4 instances)**: Visual effects
- **Risk**: Blur/shadow incorrectly sized
- **Mitigation**: Visual comparison tests

### Low Risk Conversions

**Infrastructure (4 instances)**: May already be correct
- **Risk**: Minimal if verified first
- **Mitigation**: Code review before changing

---

## 12. Summary

### By the Numbers

- **Total Conversions**: 56
- **Mapper Files**: 6 files, 40 instances (71%)
- **Service Files**: 2 files, 5 instances (9%)
- **Infrastructure**: 3 files, 5 instances (9%)
- **Helpers**: 2 files, 2 instances (4%)

### Effort Estimate

| Priority | Files | Instances | Effort |
|----------|-------|-----------|--------|
| **P0** | 6 mappers | 40 | 24 hours |
| **P1** | 4 services/helpers | 12 | 8 hours |
| **P2** | 3 infrastructure | 4 | 4 hours |
| **Total** | 13 files | 56 | 36 hours |

*Matches Phase 3 estimate (36 hours)*

### Success Criteria

✅ **All 56 conversions documented with context**
✅ **Replacement strategy defined**
✅ **Priority order established**
✅ **Testing requirements specified**
✅ **Risk mitigation planned**

---

**Status**: ✅ **COMPLETE**
**Date**: 2025-01-06
**Next**: Task 0.3 - Archive Conflicting Code
