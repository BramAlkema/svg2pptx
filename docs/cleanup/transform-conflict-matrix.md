# Transform System Conflict Matrix

**Date**: 2025-01-06
**Task**: Phase 0, Task 0.1 - Create Conflict Matrix
**Purpose**: Identify naming, API, and conceptual conflicts between existing and proposed systems

---

## 1. Naming Conflicts

### 1.1 Core Components

| # | Existing Name | Proposed Name (ADR-004) | Conflict Level | Resolution Strategy |
|---|---------------|------------------------|----------------|---------------------|
| 1 | `ViewportService` | `CoordinateSpace` | 🟡 Medium | **MERGE**: Enhance ViewportService to become CoordinateSpace, add alias |
| 2 | `viewport_matrix()` | `CoordinateSpace._compute_viewport_matrix()` | 🟢 Low | **REUSE**: Call existing function internally |
| 3 | `element_ctm()` | `CoordinateSpace.element_ctm_px()` | 🟢 Low | **WRAP**: Expose existing function as method |
| 4 | `TransformParser` | Transform parsing in CoordinateSpace | 🟢 Low | **INTEGRATE**: Use existing parser |
| 5 | `Matrix` class | Matrix operations in spec | 🟢 Low | **REUSE**: Existing Matrix is perfect |

### 1.2 Functions and Methods

| # | Existing | Proposed | Conflict | Resolution |
|---|----------|----------|----------|------------|
| 6 | `svg_to_emu(svg_x, svg_y) -> tuple[int, int]` | `svg_xy_to_pt(x, y, element) -> tuple[float, float]` | 🔴 High | **COEXIST**: Keep both, deprecate old gradually |
| 7 | `parse_to_matrix(transform_str)` | Transform parsing in CoordinateSpace | 🟢 Low | **INTEGRATE**: Use TransformParser |
| 8 | `create_root_context_with_viewport()` | Initialize CoordinateSpace | 🟡 Medium | **WRAP**: Use in CoordinateSpace.__init__() |
| 9 | `create_child_context_with_ctm()` | CTM propagation | 🟢 Low | **ADAPT**: Pattern for nested transforms |

---

## 2. API Conflicts

### 2.1 Method Signatures

| Conflict | Existing API | Proposed API | Breaking? | Migration Path |
|----------|--------------|--------------|-----------|----------------|
| **Return Type** | `svg_to_emu() -> tuple[int, int]` | `svg_xy_to_pt() -> tuple[float, float]` | ✅ Yes | Add new method, deprecate old |
| **Unit System** | Returns EMU (int) | Returns Points (float) | ✅ Yes | Document conversion: pt × 12700 = EMU |
| **Parameters** | `svg_to_emu(x, y)` | `svg_xy_to_pt(x, y, element)` | ✅ Yes | `element` needed for CTM lookup |
| **Context** | Service-based | Method-based | ❌ No | Both approaches compatible |

### 2.2 Data Structures

| Structure | Current | Proposed | Conflict | Resolution |
|-----------|---------|----------|----------|------------|
| **IR Circle** | Has `transform: np.ndarray \| None` | No transform field | ✅ Yes | **REMOVE**: Coordinates pre-transformed |
| **IR Rectangle** | Has `transform: np.ndarray \| None` | No transform field | ✅ Yes | **REMOVE**: Coordinates pre-transformed |
| **IR Path** | Has `transform: np.ndarray \| None` | No transform field | ✅ Yes | **REMOVE**: Coordinates pre-transformed |
| **Point** | `x: float, y: float` | `x: float, y: float` | ❌ No | ✅ Already compatible |

### 2.3 Service Dependencies

| Service | Current Usage | Proposed Usage | Conflict | Resolution |
|---------|---------------|----------------|----------|------------|
| **ViewportService** | Injected into context | Replaced by CoordinateSpace | 🟡 Medium | **DEPRECATE**: Add migration period |
| **TransformParser** | Standalone service | Used by CoordinateSpace | 🟢 Low | **INTEGRATE**: Dependency injection |
| **UnitConverter** | Separate service | Part of CoordinateSpace | 🟡 Medium | **INTEGRATE**: Compose services |

---

## 3. Conceptual Conflicts

### 3.1 Transformation Pipeline

#### Current Approach
```
Parse → Store Transform in IR → Apply in Mapper
```

**Issues**:
- Transform applied late (in mapper)
- Multiple rounding errors accumulate
- Hardcoded `* 12700` conversions

#### Proposed Approach
```
Parse + CoordinateSpace → Baked Coordinates in IR → No Transform
```

**Benefits**:
- Single transformation at parse time
- Single rounding point at XML output
- Sub-pixel precision preserved

**Conflict Level**: 🔴 **High** - Fundamental architecture change

**Resolution**:
1. **Phase 2**: Update parser to use CoordinateSpace
2. **Phase 3**: Update mappers to expect pre-transformed coordinates
3. **Transition**: Keep transform field temporarily, mark deprecated
4. **Validation**: Baseline tests ensure no regression

---

### 3.2 Coordinate Units

| Stage | Current Units | Proposed Units | Conflict | Impact |
|-------|---------------|----------------|----------|--------|
| **Parse** | SVG user units | SVG user units | ❌ No | ✅ Same |
| **IR** | SVG user units | Transformed points | ✅ Yes | 🔴 High - Breaking change |
| **Mapper** | SVG → EMU conversion | Points → EMU conversion | ✅ Yes | 🟡 Medium - API change |
| **XML** | Integer EMU | Integer EMU | ❌ No | ✅ Same |

**Conflict**: IR coordinates change from "SVG user units" to "transformed points"

**Resolution**:
- **Document**: Clear migration guide
- **Baseline**: Task 0.6 captures current behavior
- **Gradual**: Feature flag for transition period

---

### 3.3 Precision Model

#### Current Model: Integer EMU Throughout
```
float (SVG) → int (Mapper * 12700) → int (XML)
               ↑ PROBLEM: Premature rounding
```

**Cumulative Error**: ±0.02 pt across nested transforms

#### Proposed Model: Fractional EMU with Late Rounding
```
float (SVG) → float (Points) → float (Mapper to_fractional_emu) → int (XML round)
                                                                   ↑ SINGLE rounding point
```

**Cumulative Error**: <1×10⁻⁶ pt

**Conflict Level**: 🟡 **Medium** - Backward compatible with "standard" mode

**Resolution**:
- **Standard mode**: `to_emu()` returns `int` (backward compatible)
- **Precision modes**: `to_fractional_emu()` returns `float`
- **XML**: Always `int(round(emu))` for PowerPoint compatibility

---

## 4. Code Organization Conflicts

### 4.1 Directory Structure

| Component | Current Location | Proposed Location | Conflict | Resolution |
|-----------|-----------------|-------------------|----------|------------|
| Matrix operations | `core/transforms/core.py` | `core/transforms/matrix_ops.py` (spec) | 🟢 Low | **KEEP** current location |
| Transform parser | `core/transforms/parser.py` | `core/transforms/parser.py` (spec) | ❌ No | ✅ Already aligned |
| CoordinateSpace | N/A (ViewportService exists) | `core/geometry/space.py` (spec) | 🟡 Medium | **NEW** directory, enhance ViewportService |
| Fractional EMU | Archive/prototypes | `core/fractional_emu/` (spec) | 🟢 Low | **MIGRATE** from archive |

### 4.2 Module Dependencies

**Current Dependencies**:
```
core/transforms/ → numpy, lxml
core/viewbox/ → core/transforms/, core/converters/
core/services/viewport_service.py → core/viewbox/, core/units/
```

**Proposed Dependencies**:
```
core/geometry/space.py → core/transforms/, core/fractional_emu/, core/units/
core/parse/parser.py → core/geometry/space.py
core/map/*.py → core/fractional_emu/
```

**Potential Conflict**: Circular dependencies if not careful

**Resolution**:
- **Base layer**: `core/transforms/`, `core/fractional_emu/`, `core/units/`
- **Mid layer**: `core/geometry/space.py`
- **Top layer**: `core/parse/`, `core/map/`

---

## 5. Testing Conflicts

### 5.1 Test Coverage

| Test Category | Existing Tests | Proposed Tests | Conflict | Resolution |
|---------------|----------------|----------------|----------|------------|
| **Matrix ops** | `test_matrix_core.py` (30 tests) | Similar in spec | 🟢 Low | **REUSE** existing tests |
| **Transform parser** | Partial coverage | 30+ tests (spec) | 🟢 Low | **ENHANCE** existing |
| **Viewport** | `test_matrix_composer.py` (25 tests) | 100+ tests (spec) | 🟡 Medium | **EXPAND** existing |
| **Coordinate transform** | `test_ctm_propagation.py` (15 tests) | 100+ tests (spec) | 🟡 Medium | **ADAPT** for CoordinateSpace |
| **Fractional EMU** | None (archived) | 40+ tests (spec) | 🟢 Low | **NEW** tests |

### 5.2 Test Fixtures

| Fixture Type | Current | Proposed | Conflict | Resolution |
|--------------|---------|----------|----------|------------|
| **SVG samples** | Various in tests/ | More comprehensive | 🟢 Low | **EXPAND** collection |
| **Reference coords** | Limited | Extensive | 🟢 Low | **ADD** new fixtures |
| **Baseline outputs** | Manual | Automated (Task 0.6) | 🟢 Low | **CREATE** baseline suite |

---

## 6. Priority Conflict Resolution

### 6.1 Critical Path Conflicts (Must Resolve First)

| Priority | Conflict | Impact | Resolution | Task |
|----------|----------|--------|------------|------|
| **P0** | IR has transform field, new arch doesn't | High | Gradual removal, baseline tests | 0.6, 2.x |
| **P0** | `svg_to_emu() -> int` vs `svg_xy_to_pt() -> float` | High | Add new method, deprecate old | 1.3 |
| **P0** | Parser stores transform vs applies it | Critical | Modify parser in Phase 2 | 2.1-2.5 |

### 6.2 High Priority Conflicts

| Priority | Conflict | Impact | Resolution | Task |
|----------|----------|--------|------------|------|
| **P1** | Hardcoded `* 12700` conversions (56 instances) | High | Replace all in Phase 3 | 3.1-3.6 |
| **P1** | ViewportService vs CoordinateSpace naming | Medium | Merge/enhance ViewportService | 1.3 |
| **P1** | Integer vs fractional EMU | Medium | Support both modes | 1.4, 3.x |

### 6.3 Low Priority Conflicts

| Priority | Conflict | Impact | Resolution | Task |
|----------|----------|--------|------------|------|
| **P2** | Directory structure (geometry/ new) | Low | Create new directory | 1.3 |
| **P2** | Test organization | Low | Expand existing tests | 4.1-4.2 |
| **P2** | Documentation updates | Low | Update in Phase 4 | 4.5 |

---

## 7. Conflict Resolution Checklist

### Pre-Implementation (Phase 0)

- [x] **Task 0.1**: Audit all existing transform code ✅
- [ ] **Task 0.2**: Audit hardcoded conversions
- [ ] **Task 0.3**: Archive conflicting code (minimal expected)
- [ ] **Task 0.4**: Create test preservation strategy
- [ ] **Task 0.6**: Create baseline test suite

### Phase 1 (Infrastructure)

- [ ] Decide: Enhance ViewportService vs create CoordinateSpace
- [ ] Ensure: No circular dependencies
- [ ] Validate: Existing Matrix class meets all requirements
- [ ] Integrate: Fractional EMU without breaking existing code

### Phase 2 (Parser)

- [ ] Update: Parser to apply transforms (not just store)
- [ ] Maintain: Backward compatibility during transition
- [ ] Test: Baseline tests pass with new parser

### Phase 3 (Mappers)

- [ ] Replace: All 56 hardcoded conversions
- [ ] Support: Both integer and fractional EMU modes
- [ ] Validate: Visual regression tests

### Phase 4 (Cleanup)

- [ ] Remove: Deprecated IR transform fields
- [ ] Remove: Old `svg_to_emu()` method (if fully migrated)
- [ ] Document: All breaking changes in migration guide

---

## 8. Risk Assessment by Conflict

### High-Risk Conflicts (Require Careful Migration)

1. **IR Transform Field Removal**
   - **Risk**: Breaking change to IR structure
   - **Mitigation**: Gradual deprecation, baseline tests, clear timeline
   - **Timeline**: Phase 2 (soft removal), Phase 4 (hard removal)

2. **Parser Transformation Application**
   - **Risk**: Fundamental behavior change
   - **Mitigation**: Baseline suite, side-by-side testing, feature flag
   - **Timeline**: Phase 2

3. **ViewportService → CoordinateSpace**
   - **Risk**: API breaking change
   - **Mitigation**: Add new methods, deprecate old, provide migration guide
   - **Timeline**: Phase 1

### Medium-Risk Conflicts

4. **Hardcoded Conversion Replacement (56 instances)**
   - **Risk**: Many code changes, potential for errors
   - **Mitigation**: Automated search/replace, comprehensive tests
   - **Timeline**: Phase 3

5. **Coordinate Unit Changes**
   - **Risk**: Confusion about units at each stage
   - **Mitigation**: Clear documentation, type hints, unit tests
   - **Timeline**: Phase 2-3

### Low-Risk Conflicts

6. **Directory Structure**
   - **Risk**: Import path changes
   - **Mitigation**: Gradual migration, aliases
   - **Timeline**: Phase 1

7. **Test Organization**
   - **Risk**: Minimal
   - **Mitigation**: Expand existing tests
   - **Timeline**: All phases

---

## 9. Decision Matrix

### Key Architectural Decisions

| Decision Point | Option A | Option B | Recommendation | Rationale |
|----------------|----------|----------|----------------|-----------|
| **ViewportService vs CoordinateSpace** | Enhance ViewportService | Create new CoordinateSpace | **Option A** | Less disruption, gradual enhancement |
| **Transform field in IR** | Keep deprecated | Remove immediately | **Keep → Remove** | Gradual migration safer |
| **Fractional EMU** | Separate system | Integrated with units | **Integrated** | Cleaner API, backward compatible |
| **Matrix class** | Reuse existing | Rewrite | **Reuse** | Existing is excellent, tested |
| **Transform parser** | Reuse existing | Rewrite | **Reuse** | Works well, comprehensive |

### Implementation Strategy Decisions

| Decision Point | Approach A | Approach B | Recommendation | Rationale |
|----------------|------------|------------|----------------|-----------|
| **Migration** | Big bang | Gradual | **Gradual** | Lower risk, easier rollback |
| **Testing** | Rewrite tests | Adapt existing | **Adapt** | Preserve institutional knowledge |
| **Deprecation** | Immediate removal | Soft deprecation | **Soft** | Give users time to migrate |
| **Feature flag** | Use env var | Code branches | **Env var** | Easier to toggle, cleaner code |

---

## 10. Summary

### Total Conflicts Identified

- **Naming Conflicts**: 9 (4 low, 4 medium, 1 high)
- **API Conflicts**: 12 (7 breaking, 5 compatible)
- **Conceptual Conflicts**: 3 (1 critical, 2 medium)
- **Code Organization**: 4 (3 low, 1 medium)
- **Testing**: 6 (all resolvable)

### Resolution Strategy

1. **Reuse > Replace**: 80% of existing code can be reused
2. **Gradual > Big Bang**: Phased migration reduces risk
3. **Enhance > Rebuild**: Improve existing components
4. **Baseline > Hope**: Comprehensive testing ensures safety

### Critical Success Factors

✅ **Baseline test suite** (Task 0.6) - Validates no regression
✅ **Feature flag** - Allows gradual rollout
✅ **Clear migration guide** - Helps users adapt
✅ **Deprecation timeline** - Gives users time to migrate

---

**Status**: ✅ **COMPLETE**
**Date**: 2025-01-06
**Next**: Task 0.2 - Audit Hardcoded Conversions
