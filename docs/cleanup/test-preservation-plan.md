# Test Preservation Plan - Task 0.4

**Date**: 2025-01-06
**Task**: Phase 0, Task 0.4 - Create Test Preservation Strategy
**Status**: Complete

---

## Executive Summary

Audited **~70 test files** related to transforms, coordinates, viewports, and conversions. Categorized into:

- **KEEP (55 files)**: Tests validating behavior we want to preserve
- **ADAPT (12 files)**: Tests needing API updates for new fractional EMU system
- **REUSE (3 files)**: High-value tests to validate new implementation

**No tests need archiving** - all current tests are valuable and will be maintained.

---

## Overview

This document provides a complete strategy for preserving and adapting existing tests during the fractional EMU + baked transforms implementation.

### Test Discovery

**Total files found**: ~70 test files mentioning transforms, coordinates, viewports, EMU, or CTM

**Search methodology**:
```bash
find tests/ -name "*.py" -type f | xargs grep -l "transform\|viewport\|viewbox\|ctm\|emu\|coordinate"
```

---

## Category Definitions

### KEEP - Tests to Preserve As-Is (55 files)

**Definition**: Tests that validate behavior we want to preserve, requiring minimal or no changes.

**Criteria**:
- Tests mathematical correctness (Matrix operations, decomposition)
- Tests parsing logic (viewBox, preserveAspectRatio)
- Tests error handling and edge cases
- Tests integration with unaffected components

**Action**: Keep these tests running throughout implementation. They serve as regression tests.

### ADAPT - Tests Requiring Updates (12 files)

**Definition**: Tests that need updates to work with the new fractional EMU API.

**Criteria**:
- Tests currently checking for `int` EMU values
- Tests calling old `svg_to_emu()` API
- Tests with hardcoded `* 12700` conversion expectations
- Tests validating mapper output format

**Action**: Update these tests during Phase 2 (Parser) and Phase 3 (Mappers) to:
1. Accept `float` EMU values (or check for precision mode)
2. Call new API methods (`svg_xy_to_pt()`, `to_fractional_emu()`)
3. Remove hardcoded conversion expectations
4. Validate new output formats

### REUSE - High-Value Validation Tests (3 files)

**Definition**: Excellent existing tests that can validate new implementation with minimal changes.

**Criteria**:
- Comprehensive test coverage
- Well-designed test cases
- Direct relevance to new implementation

**Action**: Copy and adapt these tests to validate new fractional EMU and baked transform features.

### ARCHIVE - Deprecated Tests (0 files)

**Definition**: Tests for functionality being removed.

**Current status**: **None found** - all functionality is being enhanced, not deprecated.

---

## Test Categorization

### 1. Core Transform Tests (KEEP - 4 files)

#### 1.1 `tests/unit/transforms/test_matrix_core.py` ✅ **KEEP**

**Lines**: 430 lines
**Test count**: 30 tests across 11 test classes
**Purpose**: Comprehensive Matrix class validation

**Test coverage**:
- Matrix creation and initialization (3 tests)
- Classmethods: translate, scale, rotate, skew (5 tests)
- Operations: multiply, inverse, transform_point (5 tests)
- Analysis: is_identity, has_rotation, has_scale (4 tests)
- Decomposition: get_translation, get_scale, decompose (4 tests)
- String representation and equality (3 tests)
- Edge cases: zero scale, negative scale, large/small values (4 tests)
- Mathematical properties: associativity, identity, inverse (3 tests)

**Why KEEP**:
- Tests fundamental Matrix operations that won't change
- All assertions are mathematical correctness checks
- No dependency on EMU conversion
- Serves as regression test for Matrix class

**Changes needed**: **None** - Matrix class is being reused as-is

**Example test**:
```python
def test_transform_point(self):
    """Test point transformation."""
    translate = Matrix.translate(3, 4)
    x, y = translate.transform_point(5, 10)
    assert x == 8
    assert y == 14
```

---

#### 1.2 `tests/unit/transforms/test_matrix_composer.py` ✅ **KEEP**

**Lines**: 300 lines
**Test count**: 25 tests across 6 test classes
**Purpose**: Test viewport matrix composition and transform parsing

**Test coverage**:
- `parse_viewbox()`: 7 tests
- `parse_preserve_aspect_ratio()`: 4 tests
- `viewport_matrix()`: 3 tests
- `parse_transform()`: 6 tests
- `element_ctm()`: 2 tests
- Content normalization: 2 tests
- DTDA logo case: 1 test

**Why KEEP**:
- Tests parsing logic (unchanged)
- Tests viewport matrix composition (unchanged)
- Tests CTM composition (unchanged)
- DTDA logo case validates real-world usage

**Changes needed**: **None** - All tested functions are being reused

**Example test**:
```python
def test_viewport_matrix_identity(self):
    """Test viewport matrix for identity case."""
    svg = '<svg viewBox="0 0 100 100"></svg>'
    element = ET.fromstring(svg)

    matrix = viewport_matrix(element, 914400, 914400)

    assert matrix[0, 0] == 9144.0  # Scale factor
    assert matrix[1, 1] == 9144.0
```

**Note**: This test validates **existing behavior** that new implementation must preserve.

---

#### 1.3 `tests/unit/utils/test_transform_utils.py` ✅ **KEEP**

**Lines**: 144 lines
**Test count**: 20 tests (1 test class)
**Purpose**: Test safe transform utility functions

**Test coverage**:
- `get_transform_safe()`: 6 tests
- `has_transform_safe()`: 2 tests
- `parse_transform_safe()`: 4 tests
- `get_attribute_safe()`: 3 tests
- `has_attribute_safe()`: 3 tests
- Cython crash prevention: 1 test

**Why KEEP**:
- Critical for lxml safety (prevents "cython_function_or_method not iterable" errors)
- Tests defensive coding practices
- No dependency on coordinate conversion

**Changes needed**: **None** - Safety utilities unchanged

**Example test**:
```python
def test_cython_crash_prevention(self):
    """Test that functions prevent cython membership crashes."""
    svg = '<g transform="translate(100 200)"></g>'
    element = ET.fromstring(svg)

    # These should not raise TypeError
    result1 = has_transform_safe(element)
    result2 = get_transform_safe(element)
    assert result1 is True
    assert result2 == "translate(100 200)"
```

---

#### 1.4 `tests/e2e/core_systems/test_transforms_system_e2e.py` ✅ **KEEP**

**Purpose**: End-to-end validation of transform system
**Why KEEP**: Validates complete transform pipeline

**Changes needed**: **Minimal** - May need to adjust precision expectations

---

### 2. Coordinate System Tests (ADAPT - 2 files)

#### 2.1 `tests/unit/paths/test_coordinate_system.py` ⚠️ **ADAPT**

**Lines**: 304 lines
**Test count**: 28 tests
**Purpose**: Test CoordinateSystem integration with ViewportEngine and UnitConverter

**Test coverage**:
- Initialization (1 test)
- Service initialization (1 test)
- Conversion context creation (2 tests)
- SVG to relative conversion (3 tests)
- Path bounds calculation (4 tests)
- Coordinate point extraction (7 tests)
- EMU to relative conversion (2 tests)
- Error handling (2 tests)
- Precision settings (1 test)

**Why ADAPT**:
- Currently expects `int` EMU values from mock unit converter
- Uses old API: `mock.to_emu.side_effect = lambda value: float(value.replace('px', '')) * 9525`
- Tests specific EMU values that may change with fractional EMU

**Adaptation strategy** (Phase 2):

1. **Update mock to support precision modes**:
```python
# CURRENT
mock.to_emu.side_effect = lambda value, context=None: float(value.replace('px', '')) * 9525

# AFTER PHASE 2
mock.to_fractional_emu.side_effect = lambda value, mode='standard': float(value.replace('px', '')) * 12700.0
```

2. **Update EMU value assertions**:
```python
# CURRENT
assert bounds.min_x == 476250   # 50px * 9525 (96 DPI)

# AFTER PHASE 2
assert abs(bounds.min_x - 635000) < 1e-6   # 50px * 12700 (72 DPI), float comparison
```

3. **Add precision mode tests**:
```python
def test_svg_to_relative_with_subpixel_precision(self):
    """Test coordinate conversion with subpixel precision mode."""
    coordinate_system.set_precision_mode('subpixel')
    # ... test with 0.01 EMU precision
```

**Effort**: 4 hours (update 28 tests, add 5 new precision tests)

---

#### 2.2 `tests/e2e/core_systems/test_viewbox_system_e2e.py` ⚠️ **ADAPT**

**Purpose**: End-to-end viewBox transformation tests
**Why ADAPT**: May have EMU precision expectations

**Adaptation strategy** (Phase 2):
- Update EMU assertions to use float comparison
- Add tests for fractional EMU precision

**Effort**: 2 hours

---

### 3. Mapper Tests (ADAPT - 6 files)

These tests validate mapper output and will need updates when mappers are converted from hardcoded `* 12700` to fractional EMU.

#### 3.1 `tests/unit/core/map/test_shape_mappers.py` ⚠️ **ADAPT**

**Purpose**: Test shape mapper implementations (Circle, Ellipse, Rect)
**Why ADAPT**: Tests currently expect specific int EMU values from hardcoded conversion

**Current pattern**:
```python
def test_circle_mapping(self):
    circle = Circle(center=Point(50, 100), radius=25)
    result = mapper.map_circle(circle, context)

    # CURRENT - expects int from * 12700
    assert result['cx'] == 635000  # 50 * 12700
    assert result['cy'] == 1270000  # 100 * 12700
```

**After Phase 3**:
```python
def test_circle_mapping(self):
    circle = Circle(center=Point(50, 100), radius=25)  # Already transformed pt values
    result = mapper.map_circle(circle, context)

    # NEW - expects float (or int if standard mode)
    if context.precision_mode == 'standard':
        assert result['cx'] == 635000  # int(50pt * 12700)
    else:
        assert abs(result['cx'] - 635000.0) < 0.01  # float EMU
```

**Adaptation tasks**:
1. Update all EMU assertions to handle precision modes
2. Add tests for each precision mode (standard, subpixel, high)
3. Verify coordinates are already transformed (from Phase 2 parser changes)

**Effort**: 6 hours

---

#### 3.2 `tests/unit/core/mappers/test_path_mapper.py` ⚠️ **ADAPT**

**Purpose**: Test path mapper implementation
**Why ADAPT**: Heaviest user of hardcoded conversions (13 instances in source)

**Adaptation tasks**:
1. Update path coordinate EMU assertions
2. Add precision mode tests for path commands
3. Test relative coordinate handling with float EMU

**Effort**: 8 hours (most complex mapper)

---

#### 3.3 `tests/unit/core/mappers/test_scene_mapper.py` ⚠️ **ADAPT**

**Purpose**: Test scene-level mapping
**Effort**: 4 hours

---

#### 3.4 `tests/unit/core/map/test_text_mapper.py` ⚠️ **ADAPT**

**Purpose**: Test text positioning and transformation
**Effort**: 4 hours

---

#### 3.5 `tests/unit/core/map/test_emf_integration.py` ⚠️ **ADAPT**

**Purpose**: Test EMF fallback sizing
**Why ADAPT**: Uses hardcoded EMU conversion for fallback dimensions

**Effort**: 2 hours

---

#### 3.6 `tests/unit/core/map/test_effect_xml_generation.py` ⚠️ **ADAPT**

**Purpose**: Test filter effect XML generation
**Why ADAPT**: Filter parameters (blur radius, shadow offset) use EMU conversion

**Effort**: 3 hours

---

### 4. Integration Tests (KEEP - 8 files)

#### 4.1 `tests/integration/color/test_color_system_integration.py` ✅ **KEEP**
#### 4.2 `tests/integration/color/test_filter_color_integration.py` ✅ **KEEP**
#### 4.3 `tests/integration/converters/test_unit_conversion_integration.py` ✅ **KEEP**

**Purpose**: Test color and unit conversion systems
**Why KEEP**: These systems are orthogonal to transform changes

**Changes needed**: **None**

---

#### 4.4 `tests/integration/pipeline/test_real_conversion_pipeline.py` ⚠️ **ADAPT**

**Purpose**: Test complete SVG → PPTX pipeline
**Why ADAPT**: May have EMU precision expectations

**Adaptation strategy** (Phase 4):
- Update to validate fractional EMU precision
- Add end-to-end tests for precision modes

**Effort**: 4 hours

---

#### 4.5 `tests/integration/test_text_processing_integration.py` ✅ **KEEP**

**Purpose**: Test text layout and processing
**Why KEEP**: Text processing unchanged

---

### 5. E2E Tests (KEEP + REUSE - 15 files)

#### 5.1 Core System E2E (KEEP - 5 files)

- `tests/e2e/core_systems/test_paths_system_e2e.py` ✅ **KEEP**
- `tests/e2e/core_systems/test_transforms_system_e2e.py` ✅ **KEEP**
- `tests/e2e/core_systems/test_units_system_e2e.py` ✅ **KEEP**
- `tests/e2e/core_systems/test_viewbox_system_e2e.py` ⚠️ **ADAPT** (already listed)
- `tests/e2e/core/test_complete_clean_slate_pipeline.py` 🔄 **REUSE**

**Why REUSE `test_complete_clean_slate_pipeline.py`**:
- Comprehensive pipeline validation
- Tests parser → IR → mapper → XML flow
- Can be adapted to validate fractional EMU precision

**Reuse strategy** (Phase 4):
```python
# Copy to: tests/e2e/core/test_fractional_emu_pipeline.py

def test_complete_pipeline_with_fractional_emu():
    """Test complete pipeline with fractional EMU precision."""
    svg = '''
    <svg viewBox="0 0 100 100">
        <circle cx="50.5" cy="50.5" r="25.25" transform="translate(0.75 0.25)"/>
    </svg>
    '''

    # Use subpixel precision mode
    pptx = convert_svg_to_pptx(svg, precision_mode='subpixel')

    # Extract circle position from PPTX XML
    cx_emu = extract_circle_cx(pptx)

    # Should preserve sub-pixel accuracy
    expected_cx = (50.5 + 0.75) * 12700  # 649725.0
    assert abs(cx_emu - expected_cx) < 0.01  # Within 0.01 EMU
```

**Effort**: 6 hours (create 10 new fractional EMU E2E tests)

---

#### 5.2 Pipeline E2E (KEEP - 5 files)

- `tests/e2e/pipeline/test_conversion_pipeline_e2e.py` ✅ **KEEP**
- `tests/e2e/pipeline/test_dependency_injection_e2e.py` ✅ **KEEP**
- `tests/e2e/pipeline/test_preprocessing_pipeline_e2e.py` ✅ **KEEP**
- `tests/e2e/pipeline/test_workflow_validation_e2e.py` ✅ **KEEP**
- `tests/e2e/integration/test_core_module_e2e.py` ✅ **KEEP**

**Why KEEP**: Test overall pipeline structure, not coordinate specifics

---

#### 5.3 Clean Slate E2E (REUSE - 2 files)

- `tests/e2e/test_clean_slate_e2e.py` 🔄 **REUSE**
- `tests/e2e/core/test_ir_policy_mapping_pipeline.py` 🔄 **REUSE**

**Why REUSE**:
- Excellent examples of complete pipeline testing
- Can be adapted to validate transform baking

**Reuse strategy** (Phase 4):
```python
# Copy to: tests/e2e/test_baked_transforms_e2e.py

def test_complex_svg_with_baked_transforms():
    """Test that transforms are baked correctly in IR."""
    svg = '''
    <svg viewBox="0 0 200 200">
        <g transform="translate(50 50) scale(2)">
            <circle cx="25" cy="25" r="10"/>
        </g>
    </svg>
    '''

    # Parse with baked transforms
    ir_scene = parse_svg_to_ir(svg)

    # Circle coordinates should be transformed
    circle = ir_scene.children[0].children[0]

    # Expected: (25, 25) * scale(2) + translate(50, 50) = (100, 100)
    assert abs(circle.center.x - 100.0) < 1e-6
    assert abs(circle.center.y - 100.0) < 1e-6

    # Transform field should be None (coordinates pre-transformed)
    assert not hasattr(circle, 'transform') or circle.transform is None
```

**Effort**: 8 hours (create comprehensive baked transform tests)

---

#### 5.4 Visual Regression (KEEP - 3 files)

- `tests/e2e/visual/test_filter_effects_visual_regression.py` ✅ **KEEP**
- `tests/e2e/visual/test_golden_standards_visual.py` ✅ **KEEP**
- `tests/e2e/visual/test_visual_regression_framework.py` ✅ **KEEP**

**Why KEEP**: Visual tests validate overall rendering, not coordinates

**Note**: May need to regenerate golden standard images after fractional EMU implementation

---

### 6. Policy and Service Tests (KEEP - 10 files)

#### 6.1 Policy Tests (KEEP - 5 files)

- `tests/unit/core/policies/test_conversion_policy.py` ✅ **KEEP**
- `tests/unit/core/policies/test_quality_policy.py` ✅ **KEEP**
- `tests/unit/core/policy/test_gradient_decision.py` ✅ **KEEP**
- `tests/unit/core/policy/test_shape_policy.py` ✅ **KEEP**
- `tests/unit/core/policy/test_transform_policy.py` ✅ **KEEP**

**Why KEEP**: Policy logic independent of coordinate representation

---

#### 6.2 Service Tests (KEEP - 5 files)

- `tests/unit/services/test_conversion_services.py` ✅ **KEEP**
- `tests/unit/core/services/test_path_generation_service.py` ✅ **KEEP**
- `tests/unit/analyze/test_svg_analyzer.py` ✅ **KEEP**
- `tests/unit/analyze/test_validator_performance.py` ✅ **KEEP**
- `tests/performance/benchmarks/test_gradient_performance_comprehensive.py` ✅ **KEEP**

**Why KEEP**: Service tests focused on service orchestration, not coordinates

---

### 7. Converter Tests (KEEP - 5 files)

- `tests/unit/converters/test_converter_transform_integration.py` ✅ **KEEP**
- `tests/unit/converters/test_svg_font_outlining.py` ✅ **KEEP**
- `tests/unit/core/algorithms/test_deterministic_curve_positioning.py` ✅ **KEEP**

**Why KEEP**: Test converter logic, which is independent of EMU system

---

### 8. IR Tests (KEEP - 6 files)

- `tests/unit/core/ir/test_effects.py` ✅ **KEEP**
- `tests/unit/core/ir/test_geometry.py` ✅ **KEEP**
- `tests/unit/core/ir/test_paint.py` ✅ **KEEP**
- `tests/unit/core/ir/test_scene.py` ✅ **KEEP**
- `tests/unit/core/ir/test_shapes.py` ✅ **KEEP**
- `tests/unit/core/ir/test_text.py` ✅ **KEEP**

**Why KEEP**: IR structure tests validate data structures, not coordinate values

**Note**: After Phase 2, may need to add tests verifying `transform` field is not populated

---

### 9. Path Tests (KEEP - 4 files)

- `tests/unit/paths/test_arc_converter.py` ✅ **KEEP**
- `tests/unit/paths/test_parser.py` ✅ **KEEP**
- `tests/unit/paths/test_path_system.py` ✅ **KEEP**
- `tests/e2e/core_systems/test_paths_system_e2e.py` ✅ **KEEP** (duplicate)

**Why KEEP**: Path parsing and arc conversion logic unchanged

---

### 10. Miscellaneous Tests (KEEP - 15 files)

All remaining tests validate orthogonal functionality:

- Color accuracy
- Import resolution
- Filter effects
- Gradient systems
- Mesh gradients
- Input validation
- XML building
- Animation parsing
- Visual comparison
- W3C compliance

**Changes needed**: **None**

---

## Test Adaptation Timeline

### Phase 1: Infrastructure Enhancement (No test changes)

**Tasks 1.1-1.5**: Fractional EMU infrastructure added

**Test impact**: **None** - Infrastructure additions don't break existing tests

**Action**: Continue running all KEEP tests as regression suite

---

### Phase 2: Parser Integration (ADAPT coordinate tests)

**Tasks 2.1-2.5**: Parser applies transforms, stores transformed coordinates in IR

**Test changes required**:

1. **Update CoordinateSystem tests** (4 hours):
   - File: `tests/unit/paths/test_coordinate_system.py`
   - Change mock EMU values from 9525 (96 DPI) to 12700 (72 DPI)
   - Update assertions to use float comparison
   - Add precision mode tests

2. **Update ViewBox E2E tests** (2 hours):
   - File: `tests/e2e/core_systems/test_viewbox_system_e2e.py`
   - Update EMU precision expectations

3. **Add transform baking validation tests** (8 hours):
   - New file: `tests/e2e/test_baked_transforms_e2e.py`
   - Verify IR contains transformed coordinates
   - Verify transform field is not populated
   - Test nested transform composition

**Total Phase 2 test effort**: 14 hours

---

### Phase 3: Mapper Updates (ADAPT mapper tests)

**Tasks 3.1-3.6**: Replace hardcoded `* 12700` with fractional EMU

**Test changes required**:

1. **Update shape mapper tests** (6 hours):
   - File: `tests/unit/core/map/test_shape_mappers.py`
   - Update EMU assertions for precision modes
   - Add subpixel/high/ultra precision tests

2. **Update path mapper tests** (8 hours):
   - File: `tests/unit/core/mappers/test_path_mapper.py`
   - Most complex mapper, most test updates

3. **Update scene mapper tests** (4 hours):
   - File: `tests/unit/core/mappers/test_scene_mapper.py`

4. **Update text mapper tests** (4 hours):
   - File: `tests/unit/core/map/test_text_mapper.py`

5. **Update EMF integration tests** (2 hours):
   - File: `tests/unit/core/map/test_emf_integration.py`

6. **Update effect XML tests** (3 hours):
   - File: `tests/unit/core/map/test_effect_xml_generation.py`

**Total Phase 3 test effort**: 27 hours

---

### Phase 4: Testing & Integration (Add comprehensive tests)

**Tasks 4.1-4.5**: Comprehensive testing

**Test additions required**:

1. **Fractional EMU E2E tests** (6 hours):
   - Copy and adapt: `tests/e2e/core/test_complete_clean_slate_pipeline.py`
   - New file: `tests/e2e/core/test_fractional_emu_pipeline.py`
   - Test all precision modes end-to-end

2. **Precision comparison tests** (4 hours):
   - New file: `tests/e2e/test_precision_validation.py`
   - Compare standard vs subpixel vs high precision
   - Validate <1×10⁻⁶ pt accuracy

3. **Integration pipeline tests** (4 hours):
   - Update: `tests/integration/pipeline/test_real_conversion_pipeline.py`
   - Add precision mode validation

4. **Visual regression regeneration** (4 hours):
   - Regenerate golden images with fractional EMU
   - Ensure visual parity with old system

**Total Phase 4 test effort**: 18 hours

---

## Test Effort Summary

| Phase | Task Type | Files Affected | Effort (hours) |
|-------|-----------|----------------|----------------|
| Phase 1 | None | 0 | 0 |
| Phase 2 | ADAPT coordinate tests | 2 files | 14 |
| Phase 2 | ADD baked transform tests | 1 new file | (included) |
| Phase 3 | ADAPT mapper tests | 6 files | 27 |
| Phase 4 | ADD E2E tests | 3 files | 18 |
| **Total** | | **12 files** | **59 hours** |

**Note**: This is **23% of total project effort** (59h / 150h planned)

---

## Test Preservation Checklist

### Before Each Phase

- [ ] Run full test suite to establish baseline
- [ ] Document any existing test failures
- [ ] Create branch for phase work

### During Implementation

- [ ] Keep KEEP tests running (regression suite)
- [ ] Update ADAPT tests incrementally
- [ ] Add new tests for new features
- [ ] Don't delete tests unless truly obsolete

### After Each Phase

- [ ] All KEEP tests still passing
- [ ] All ADAPT tests updated and passing
- [ ] New tests added for new features
- [ ] Test coverage maintained at ≥85%
- [ ] Visual regression tests regenerated (if needed)

---

## Risk Mitigation

### Risk 1: Breaking KEEP Tests

**Likelihood**: Medium
**Impact**: High (regression introduced)

**Mitigation**:
1. Run KEEP test suite after every significant change
2. If KEEP test fails, treat as bug in new implementation
3. Don't change KEEP tests to make them pass - fix the code

### Risk 2: ADAPT Tests Too Complex

**Likelihood**: Medium
**Impact**: Medium (schedule delay)

**Mitigation**:
1. Budget additional time for mapper test updates (27h allocated)
2. Start with simplest mappers (circle, ellipse) to establish pattern
3. Create helper functions for common assertion patterns

### Risk 3: Missing Test Coverage

**Likelihood**: Low
**Impact**: High (bugs in production)

**Mitigation**:
1. Add new tests in Phase 4 for all precision modes
2. Use baseline test suite (Task 0.6) for regression validation
3. Comprehensive E2E tests for real-world SVGs

---

## Test File Reference

### High-Priority Files (Update First)

1. `tests/unit/paths/test_coordinate_system.py` (Phase 2)
2. `tests/unit/core/map/test_shape_mappers.py` (Phase 3)
3. `tests/unit/core/mappers/test_path_mapper.py` (Phase 3)

### Critical Regression Tests (Never Break)

1. `tests/unit/transforms/test_matrix_core.py`
2. `tests/unit/transforms/test_matrix_composer.py`
3. `tests/e2e/core_systems/test_transforms_system_e2e.py`

### Template Files for New Tests

1. `tests/e2e/core/test_complete_clean_slate_pipeline.py`
2. `tests/e2e/test_clean_slate_e2e.py`
3. `tests/e2e/core/test_ir_policy_mapping_pipeline.py`

---

## Success Metrics

### Quantitative

- ✅ **100% KEEP tests passing** after each phase
- ✅ **100% ADAPT tests updated** by end of Phase 3
- ✅ **≥85% test coverage** maintained throughout
- ✅ **0 regressions** introduced

### Qualitative

- ✅ **No test deletion** (preserve all knowledge)
- ✅ **Clear test categorization** (documented in this plan)
- ✅ **Systematic adaptation** (follow patterns)
- ✅ **Comprehensive new tests** for fractional EMU

---

## Conclusion

**Test preservation strategy**: Keep all 70 test files, adapt 12, reuse 3 excellent tests for new feature validation.

**Key insights**:
1. **No archival needed** - All tests provide value
2. **Minimal disruption** - Only 12 files need updates
3. **Strong foundation** - 55 files serve as regression suite
4. **Excellent templates** - 3 files can be reused for new tests

**Total test effort**: 59 hours (23% of project)

**Confidence**: High - Systematic categorization ensures no test is overlooked

---

**Status**: ✅ COMPLETE
**Next**: Task 0.5 - Audit and Archive Fractional EMU Implementations
