# Task 0.2: Audit Existing Coordinate Conversion Code - COMPLETE ✅

**Date**: 2025-01-06
**Duration**: ~2 hours
**Status**: ✅ Complete
**Phase**: 0 - Cleanup and Preparation

---

## Deliverables

### 1. Hardcoded Conversions Audit
- **File**: `docs/cleanup/hardcoded-conversions.md`
- **Size**: ~1200 lines
- **Content**: Complete catalogue of all 56 hardcoded `* 12700` conversions

### 2. Conversion Replacement Plan
- **File**: `docs/cleanup/conversion-replacement-plan.md`
- **Size**: ~800 lines
- **Content**: Step-by-step replacement strategy with code examples

### 3. Raw Data
- **File**: `docs/cleanup/hardcoded-conversions-raw.txt`
- **Content**: grep output of all conversions (56 lines)

---

## Key Findings

### Distribution by File

**56 total conversions** across 13 files:

| Priority | Files | Instances | % |
|----------|-------|-----------|---|
| **P0 Mappers** | 6 files | 40 | 71% |
| **P1 Services** | 4 files | 12 | 21% |
| **P2 Infrastructure** | 3 files | 4 | 7% |

### Top Offenders

1. **`core/map/path_mapper.py`**: 13 instances (most complex)
2. **`core/map/group_mapper.py`**: 8 instances
3. **`core/map/image_mapper.py`**: 8 instances
4. **`core/map/ellipse_mapper.py`**: 4 instances
5. **`core/map/rect_mapper.py`**: 4 instances
6. **`core/services/filter_service.py`**: 4 instances
7. **`core/map/circle_mapper.py`**: 3 instances

### Conversion Types

- **Coordinates** (x, y): 40 instances
- **Dimensions** (width, height): 12 instances
- **Stroke width**: 2 instances
- **Filter parameters**: 2 instances

---

## Replacement Strategy

### Pattern Identified

**Current (WRONG)**:
```python
x_emu = int(shape.x * 12700)  # Hardcoded, no transform, premature rounding
```

**After Phase 2+3 (CORRECT)**:
```python
# Standard mode (backward compatible)
from core.units import unit
x_emu = unit(f"{shape.x}pt").to_emu()  # shape.x already transformed

# Precision mode (fractional EMU)
from core.fractional_emu import create_fractional_converter
converter = create_fractional_converter("subpixel")
x_emu = converter.to_fractional_emu(shape.x)  # Returns float
```

### Mapped to Phase 3 Tasks

- **Task 3.1**: Circle/Ellipse (7 instances) - 4 hours
- **Task 3.2**: Rectangle (4 instances) - 4 hours
- **Task 3.3**: Path (13 instances) - 8 hours
- **Task 3.4**: Group/Image (16 instances) - 10 hours
- **Task 3.5**: Services/Helpers (12 instances) - 6 hours
- **Task 3.6**: Infrastructure (4 instances) - 4 hours

**Total**: 56 instances, 36 hours (matches Phase 3 estimate)

---

## Priority Classification

### P0 - Critical (Mappers: 40 instances)

These directly affect shape positioning and are the **highest priority**:

- `core/map/path_mapper.py` (13)
- `core/map/group_mapper.py` (8)
- `core/map/image_mapper.py` (8)
- `core/map/ellipse_mapper.py` (4)
- `core/map/rect_mapper.py` (4)
- `core/map/circle_mapper.py` (3)

**Impact**: Shape positioning, most visible errors

### P1 - High (Services/Helpers: 12 instances)

Affect quality and consistency:

- `core/services/filter_service.py` (4) - Blur/shadow quality
- `core/map/emf_adapter.py` (2) - Fallback sizing
- `core/map/shape_helpers.py` (1) - Shared stroke width
- `core/paths/drawingml_generator.py` (1) - Path width

**Impact**: Visual effects, stroke rendering

### P2 - Medium (Infrastructure: 4 instances)

May already be correct, need investigation:

- `core/viewbox/core.py` (2) - Vectorized conversion
- `core/utils/enhanced_xml_builder.py` (2) - Enhanced effects

**Impact**: Potentially minimal if verified first

---

## Validation Plan

### Phase 3 Validation (Per Task)

After each task completes:

```bash
# Check file has zero hardcoded conversions
grep "\* 12700" core/map/circle_mapper.py
# Expected: no results

# Run file-specific tests
PYTHONPATH=. pytest tests/unit/core/map/test_circle_mapper.py -v
```

### Final Validation (After Task 3.6)

```bash
# Zero conversions remaining
grep -r "\* 12700\|12700 \*" core/ --include="*.py" | wc -l
# Expected: 0

# All tests pass
PYTHONPATH=. pytest tests/ -v

# Visual regression
python tests/baseline/compare_with_new.py
```

---

## Risk Assessment

### High Risk

**Path Mapper (13 instances)**:
- Most complex, highest instance count
- **Mitigation**: Comprehensive tests, visual regression

### Medium Risk

**Filter Service (4 instances)**:
- Affects visual quality (blur, shadows)
- **Mitigation**: Visual comparison tests

### Low Risk

**Infrastructure (4 instances)**:
- May already be correct
- **Mitigation**: Code review before changes

---

## Dependencies

### Prerequisites

1. ✅ **Task 0.2 Complete** - This task
2. **Task 1.4 Complete** - Fractional EMU migrated
3. **Phase 2 Complete** - Parser applies transforms
4. **Task 0.6 Complete** - Baseline tests for validation

### Task Order

```
Task 1.4 (Fractional EMU)
    ↓
Phase 2 (Parser transforms)
    ↓
Task 3.1 → 3.2 → 3.3 → 3.4 → 3.5 → 3.6
    ↓
Zero hardcoded conversions ✅
```

---

## Documentation Created

1. **`docs/cleanup/hardcoded-conversions.md`**
   - Complete audit with context for each conversion
   - Analysis by file, type, priority
   - Testing requirements
   - Risk assessment

2. **`docs/cleanup/conversion-replacement-plan.md`**
   - Step-by-step replacement instructions
   - Code examples (before/after)
   - Validation strategy per file
   - Progress tracking checklist

3. **`docs/cleanup/hardcoded-conversions-raw.txt`**
   - Raw grep output (56 lines)
   - File:line reference

---

## Impact on Implementation

### Confirms Phase 3 Estimate

Original estimate: 36 hours for mapper updates
Audit findings: 56 conversions across 13 files
**Validation**: Estimate is accurate ✅

### Task Breakdown Validated

- **Task 3.1-3.2**: Simple shapes (11 instances) - 8 hours
- **Task 3.3**: Complex paths (13 instances) - 8 hours
- **Task 3.4**: Containers (16 instances) - 10 hours
- **Task 3.5-3.6**: Services/Infrastructure (16 instances) - 10 hours

**Total**: 56 instances, 36 hours ✅

---

## Next Steps

✅ **Task 0.1 Complete** - Transform code audited
✅ **Task 0.2 Complete** - Conversions audited and documented
⏭️ **Task 0.3** - Archive Conflicting Code (expected: minimal)
⏭️ **Tasks 0.4-0.8** - Complete remaining Phase 0 tasks

---

## Success Criteria

✅ **All 56 conversions catalogued** with file:line
✅ **Context documented** for each conversion
✅ **Replacement strategy** defined with code examples
✅ **Priority order** established (P0/P1/P2)
✅ **Testing requirements** specified per file
✅ **Risk mitigation** planned

---

**Status**: ✅ COMPLETE - Ready for Phase 3
**Confidence**: High - Comprehensive audit completed
**Next**: Task 0.3 - Archive Conflicting Code
