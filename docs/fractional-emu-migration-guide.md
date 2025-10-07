# Fractional EMU + Baked Transform Migration Guide

**Date**: 2025-01-06
**Version**: 1.0
**Status**: Implementation Ready

---

## Table of Contents

1. [Migration Overview](#migration-overview)
2. [Phase 1: Fractional EMU Infrastructure](#phase-1-fractional-emu-infrastructure-20h)
3. [Phase 2: Baked Transforms](#phase-2-baked-transforms-28h)
4. [Phase 3: Mapper Updates](#phase-3-mapper-updates-36h)
5. [Phase 4: Integration & Testing](#phase-4-integration--testing-26h)
6. [Risk Mitigation](#risk-mitigation)
7. [Rollback Procedures](#rollback-procedures)
8. [Validation Checkpoints](#validation-checkpoints)

---

## Migration Overview

### Four-Phase Implementation

**Total time**: 110 hours across 4 phases

| Phase | Focus | Duration | Risk |
|-------|-------|----------|------|
| **Phase 1** | Fractional EMU infrastructure | 20h | Low |
| **Phase 2** | Baked transforms at parse time | 28h | Medium |
| **Phase 3** | Replace 56 hardcoded conversions | 36h | Low |
| **Phase 4** | Integration and testing | 26h | Low |

### Phase Dependencies

```
Phase 0 (Cleanup) ───> Phase 1 (Infrastructure)
                           │
                           ├───> Phase 2 (Baked Transforms)
                           │         │
                           │         ├───> Phase 3 (Mappers)
                           │         │         │
                           └─────────┴─────────┴───> Phase 4 (Integration)
```

**Key dependency**: Phase 2 and Phase 3 both depend on Phase 1, but Phase 3 also depends on Phase 2 (for baked transforms)

### Validation Strategy

**Baseline test suite**: 24 test SVGs with automated comparison

**Phase-specific expectations**:
- Phase 1: 100% match with Phase 0 (infrastructure only)
- Phase 2: Transform tests WILL differ (expected - transforms baked)
- Phase 3: Minor precision improvements (<1 EMU)
- Phase 4: Match Phase 3 (integration complete)

---

## Phase 1: Fractional EMU Infrastructure (20h)

### Objective

Install fractional EMU system without changing mappers or parsers yet.

### Tasks

#### Task 1.1: Create Fractional EMU Package (SKIPPED ✅)

**Reason**: Excellent infrastructure already exists in `core/transforms/`

**Time saved**: 6 hours

**Decision**: Reuse existing Matrix, viewport_matrix(), parse_viewbox()

---

#### Task 1.2: Matrix and Transform Utilities (SKIPPED ✅)

**Reason**: Matrix class already production-quality

**Time saved**: 6 hours

**Evidence**: `core/transforms/core.py` contains comprehensive Matrix class

---

#### Task 1.3: ViewportContext Enhancement (2h)

**File**: `core/services/viewport_service.py`

**Objective**: Enhance ViewportService to return float instead of int

**Current code**:
```python
def svg_to_emu(self, svg_x: float, svg_y: float) -> tuple[int, int]:
    emu_x = int(svg_x * self.viewport_mapping['scale_x'] + ...)
    return emu_x, emu_y
```

**New code**:
```python
def svg_to_fractional_emu(
    self, svg_x: float, svg_y: float
) -> tuple[float, float]:
    """Return float EMU (not rounded to int)"""
    emu_x = svg_x * self.viewport_mapping['scale_x'] + \
            self.viewport_mapping['offset_x']
    emu_y = svg_y * self.viewport_mapping['scale_y'] + \
            self.viewport_mapping['offset_y']
    return emu_x, emu_y  # float, not int

def svg_to_emu(self, svg_x: float, svg_y: float) -> tuple[int, int]:
    """Backward compatible - returns int"""
    fractional_x, fractional_y = self.svg_to_fractional_emu(svg_x, svg_y)
    return int(round(fractional_x)), int(round(fractional_y))
```

**Test**:
```bash
PYTHONPATH=. pytest tests/unit/services/test_viewport_service.py -v
```

---

#### Task 1.4: Migrate Fractional EMU Implementation (8h)

**Source**: `archive/legacy-src/fractional_emu.py` (1313 lines)

**Destination**: `core/fractional_emu/` package

**Module structure**:
```
core/fractional_emu/
├── __init__.py                 # Public API exports
├── converter.py                # FractionalEMUConverter (~900 lines)
├── precision_engine.py         # VectorizedPrecisionEngine (~305 lines)
├── types.py                    # PrecisionMode, contexts (~50 lines)
├── errors.py                   # Custom exceptions (~20 lines)
└── constants.py                # EMU constants (~40 lines)
```

**Migration checklist** (see `docs/cleanup/fractional-emu-migration-checklist.md`):

1. **Create package structure** (30 min)
   ```bash
   mkdir -p core/fractional_emu
   touch core/fractional_emu/{__init__,converter,precision_engine,types,errors,constants}.py
   ```

2. **Migrate constants** (30 min)
   - Copy EMU_PER_POINT, EMU_PER_INCH from archive
   - Add to `constants.py`

3. **Migrate types** (1h)
   - PrecisionMode enum
   - ViewportContext dataclass
   - PrecisionContext dataclass

4. **Migrate converter** (3h)
   - FractionalEMUConverter class
   - to_fractional_emu() method
   - Backward-compatible to_emu() wrapper

5. **Migrate precision engine** (2h)
   - VectorizedPrecisionEngine class
   - NumPy batch conversions
   - Auto-selection logic

6. **Write tests** (1.5h)
   - Test precision modes
   - Test batch conversions
   - Test backward compatibility

**Test**:
```bash
PYTHONPATH=. pytest tests/unit/fractional_emu/ -v --tb=short
```

---

#### Task 1.5: Integrate with ConversionServices (2h)

**File**: `core/services/conversion_services.py`

**Changes**:
```python
from core.fractional_emu import FractionalEMUConverter, VectorizedPrecisionEngine

class ConversionServices:
    def __init__(self, config: Optional[ConversionConfig] = None):
        # ... existing services ...

        # NEW: Fractional EMU services
        self.fractional_emu_converter = FractionalEMUConverter(
            precision_mode=config.precision_mode if config else PrecisionMode.STANDARD
        )
        self.precision_engine = VectorizedPrecisionEngine()
```

**Test**:
```bash
PYTHONPATH=. pytest tests/unit/services/test_conversion_services.py -v
```

---

#### Task 1.6: Phase 1 Validation (2h)

**Baseline comparison**:
```bash
# Generate Phase 1 baseline
PYTHONPATH=. python tests/baseline/generate_baseline.py --phase phase1
PYTHONPATH=. python tests/baseline/extract_coordinates.py --phase phase1

# Compare with Phase 0
PYTHONPATH=. python tests/baseline/compare_with_baseline.py \
    --baseline phase0 \
    --compare phase1 \
    --save
```

**Expected result**:
```
Files compared:       24
Exact matches:        24  ✅
Minor differences:    0
Major differences:    0
```

**If differences found**: Bug in fractional EMU implementation - investigate and fix

---

### Phase 1 Success Criteria

- ✅ FractionalEMUConverter integrated with ConversionServices
- ✅ All existing tests pass
- ✅ 100% match with Phase 0 baseline (no coordinate changes yet)
- ✅ Backward compatible API (`to_emu()` returns int)

---

## Phase 2: Baked Transforms (28h)

### Objective

Apply transforms at parse time using CoordinateSpace, store transformed coordinates in IR.

### Tasks

#### Task 2.1: Create CoordinateSpace Class (6h)

**File**: `core/transforms/coordinate_space.py`

**Implementation**:
```python
from dataclasses import dataclass
from typing import List
from .core import Matrix

@dataclass
class CoordinateSpace:
    """Manages coordinate transformations during parsing

    Maintains CTM (Current Transformation Matrix) stack and applies
    transforms at parse time instead of storing them in IR.
    """

    def __init__(self, viewport_matrix: Matrix):
        """Initialize with viewport transformation"""
        self.ctm_stack: List[Matrix] = [viewport_matrix]

    def push_transform(self, transform: Matrix):
        """Push transform onto CTM stack (for entering groups)"""
        current_ctm = self.ctm_stack[-1]
        new_ctm = current_ctm.compose(transform)
        self.ctm_stack.append(new_ctm)

    def pop_transform(self):
        """Pop transform from CTM stack (for exiting groups)"""
        if len(self.ctm_stack) > 1:
            self.ctm_stack.pop()
        else:
            raise ValueError("Cannot pop viewport matrix from CTM stack")

    def apply_ctm(self, x: float, y: float) -> tuple[float, float]:
        """Apply current CTM to coordinates"""
        ctm = self.ctm_stack[-1]
        return ctm.transform_point(x, y)

    @property
    def current_ctm(self) -> Matrix:
        """Get current CTM"""
        return self.ctm_stack[-1]
```

**Test**:
```bash
PYTHONPATH=. pytest tests/unit/transforms/test_coordinate_space.py -v
```

**Test cases**:
- Test push/pop transform
- Test CTM composition
- Test apply_ctm with various transforms
- Test viewport matrix integration

---

#### Task 2.2: Integrate CoordinateSpace with Parser (12h)

**File**: `core/parse/parser.py`

**Changes**:

1. **Initialize CoordinateSpace** (2h)
   ```python
   class SVGToIRParser:
       def __init__(self, services: ConversionServices, svg_root: Element):
           self.services = services

           # Create viewport matrix
           viewport_matrix = create_viewport_matrix(svg_root, services)

           # NEW: Create coordinate space
           self.coord_space = CoordinateSpace(viewport_matrix)
   ```

2. **Handle transforms during parsing** (4h)
   ```python
   def parse_element(self, element: Element, parent_clip: Optional[str] = None):
       # Check for transform attribute
       transform_attr = element.get('transform')

       if transform_attr:
           # Parse transform string → Matrix
           transform_matrix = self._parse_transform(transform_attr)
           # Push onto CTM stack
           self.coord_space.push_transform(transform_matrix)

       # Parse element (coordinates will be transformed)
       ir_element = self._parse_element_by_type(element, parent_clip)

       # Pop transform when exiting element
       if transform_attr:
           self.coord_space.pop_transform()

       return ir_element
   ```

3. **Update coordinate extraction** (6h)
   ```python
   def _parse_rect(self, element: Element) -> Rectangle:
       # Extract SVG coordinates
       x_svg = float(element.get('x', 0))
       y_svg = float(element.get('y', 0))
       width_svg = float(element.get('width', 0))
       height_svg = float(element.get('height', 0))

       # NEW: Apply CTM to get transformed coordinates
       x_transformed, y_transformed = self.coord_space.apply_ctm(x_svg, y_svg)
       x2_transformed, y2_transformed = self.coord_space.apply_ctm(
           x_svg + width_svg, y_svg + height_svg
       )

       # Calculate transformed width/height
       width_transformed = x2_transformed - x_transformed
       height_transformed = y2_transformed - y_transformed

       # Store in IR (NO transform field)
       return Rectangle(
           bounds=Rect(
               x=x_transformed,
               y=y_transformed,
               width=width_transformed,
               height=height_transformed
           ),
           transform=None,  # ✅ No transform stored
           fill=self._parse_fill(element),
           stroke=self._parse_stroke(element),
           opacity=float(element.get('opacity', 1.0))
       )
   ```

**Test**:
```bash
PYTHONPATH=. pytest tests/unit/parse/test_svg_to_ir_parser.py -v
```

**Update test expectations**:
- Coordinates should be transformed
- IR should NOT have transform field

---

#### Task 2.3: Update All Shape Parsers (8h)

Apply CoordinateSpace to all shape parsers:

1. **Circle parser** (1h)
   - Transform center point
   - Handle radius with scale

2. **Ellipse parser** (1h)
   - Transform center point
   - Handle rx, ry with scale

3. **Path parser** (2h)
   - Transform all path commands
   - Handle moveto, lineto, curveto, etc.

4. **Polygon/Polyline parser** (2h)
   - Transform all points

5. **Text parser** (2h)
   - Transform position
   - Handle text-specific transforms

**Test each parser**:
```bash
PYTHONPATH=. pytest tests/unit/parse/ -k "rect or circle or ellipse" -v
```

---

#### Task 2.4: Phase 2 Validation (2h)

**Baseline comparison**:
```bash
# Generate Phase 2 baseline
PYTHONPATH=. python tests/baseline/generate_baseline.py --phase phase2
PYTHONPATH=. python tests/baseline/extract_coordinates.py --phase phase2

# Compare with Phase 0
PYTHONPATH=. python tests/baseline/compare_with_baseline.py \
    --baseline phase0 \
    --compare phase2 \
    --save
```

**Expected result**:
```
Files compared:       24
Exact matches:        17  ✅ (non-transform tests)
Minor differences:    7   ⚠️  (transform tests - EXPECTED)
Major differences:    0
```

**Transform tests SHOULD show differences** - this is correct!

**Example**:
```
complex_transforms.svg:
  Before (Phase 0): x=100 (SVG coordinate)
  After (Phase 2):  x=150 (transform baked in)
```

**If transform tests DON'T differ**: Bug - transforms not being baked!

---

### Phase 2 Success Criteria

- ✅ CoordinateSpace integrated with parser
- ✅ All shape parsers apply CTM
- ✅ IR does NOT store transform field
- ✅ Transform tests show expected differences
- ✅ Non-transform tests match Phase 0

---

## Phase 3: Mapper Updates (36h)

### Objective

Replace 56 hardcoded `* 12700` conversions with fractional EMU converter.

### Tasks

#### Task 3.1: Update Core Mappers (20h)

**56 conversions** across mappers:

**Distribution**:
- Mappers: 40 conversions
- Services: 12 conversions
- Infrastructure: 4 conversions

**Mapper update pattern**:

Before:
```python
class RectangleMapper:
    def map(self, ir_rect: Rectangle) -> Element:
        x_emu = int(ir_rect.bounds.x * 12700)  # ❌ Hardcoded
        y_emu = int(ir_rect.bounds.y * 12700)
        # ...
```

After:
```python
class RectangleMapper:
    def __init__(self, services: ConversionServices):
        self.services = services
        self.converter = services.fractional_emu_converter

    def map(self, ir_rect: Rectangle) -> Element:
        # Use fractional EMU
        x_emu_frac = self.converter.to_fractional_emu(ir_rect.bounds.x)
        y_emu_frac = self.converter.to_fractional_emu(ir_rect.bounds.y)

        # Round to int at XML creation
        x_emu = int(round(x_emu_frac))
        y_emu = int(round(y_emu_frac))
        # ...
```

**Mappers to update** (see `docs/cleanup/conversion-replacement-plan.md`):

1. **rect_mapper.py** (2h) - 8 conversions
2. **circle_mapper.py** (2h) - 6 conversions
3. **ellipse_mapper.py** (2h) - 6 conversions
4. **path_mapper.py** (4h) - 12 conversions
5. **text_mapper.py** (3h) - 8 conversions
6. **group_mapper.py** (2h) - 4 conversions
7. **image_mapper.py** (2h) - 4 conversions
8. **Other mappers** (3h) - Various

**Test each mapper**:
```bash
PYTHONPATH=. pytest tests/unit/core/map/test_rect_mapper.py -v
```

---

#### Task 3.2: Update Service Conversions (8h)

**Service files** with hardcoded conversions:

1. **viewport_service.py** (2h) - 4 conversions
2. **gradient_service.py** (2h) - 3 conversions
3. **pattern_service.py** (2h) - 3 conversions
4. **clip_service.py** (2h) - 2 conversions

**Test**:
```bash
PYTHONPATH=. pytest tests/unit/services/ -v
```

---

#### Task 3.3: Update Infrastructure (4h)

**Infrastructure files**:

1. **slide_builder.py** (2h) - 2 conversions
2. **embedder.py** (1h) - 1 conversion
3. **package_writer.py** (1h) - 1 conversion

**Test**:
```bash
PYTHONPATH=. pytest tests/unit/core/io/ -v
```

---

#### Task 3.4: Phase 3 Validation (4h)

**Baseline comparison**:
```bash
# Generate Phase 3 baseline
PYTHONPATH=. python tests/baseline/generate_baseline.py --phase phase3
PYTHONPATH=. python tests/baseline/extract_coordinates.py --phase phase3

# Compare with Phase 0
PYTHONPATH=. python tests/baseline/compare_with_baseline.py \
    --baseline phase0 \
    --compare phase3 \
    --save
```

**Expected result**:
```
Files compared:       24
Exact matches:        20  ✅
Minor differences:    4   📊 (precision improvements <1 EMU)
Major differences:    0
```

**Precision improvements expected** due to float64 throughout pipeline.

---

### Phase 3 Success Criteria

- ✅ All 56 hardcoded conversions replaced
- ✅ All mappers use FractionalEMUConverter
- ✅ All tests pass
- ✅ Minor precision improvements visible (<1 EMU)
- ✅ No major coordinate changes

---

## Phase 4: Integration & Testing (26h)

### Objective

Complete integration, comprehensive testing, performance validation.

### Tasks

#### Task 4.1: Integration Testing (12h)

**Test categories**:

1. **End-to-end pipeline** (4h)
   - SVG → Parse → IR → Map → PPTX
   - Validate complete flow

2. **Complex SVG scenarios** (4h)
   - Nested transforms
   - Multiple coordinate systems
   - Edge cases (extreme coordinates, tiny values)

3. **Performance benchmarks** (4h)
   - Path with 10,000 points
   - Batch conversion performance
   - Memory usage

**Test**:
```bash
PYTHONPATH=. pytest tests/e2e/ -v --tb=short
```

---

#### Task 4.2: Baseline Validation (4h)

**Final baseline comparison**:
```bash
# Generate Phase 4 baseline
PYTHONPATH=. python tests/baseline/generate_baseline.py --phase phase4
PYTHONPATH=. python tests/baseline/extract_coordinates.py --phase phase4

# Compare with Phase 3 (should match)
PYTHONPATH=. python tests/baseline/compare_with_baseline.py \
    --baseline phase3 \
    --compare phase4 \
    --save
```

**Expected result**:
```
Files compared:       24
Exact matches:        24  ✅
Minor differences:    0
Major differences:    0
```

**Phase 4 should match Phase 3** - integration shouldn't change coordinates.

---

#### Task 4.3: Performance Validation (6h)

**Benchmark suite**:

1. **Simple shapes** (2h)
   - Baseline: Current system
   - Target: Fractional EMU system
   - Expected: Similar performance (±10%)

2. **Complex paths** (2h)
   - Baseline: Current system (1,253 ms for 10,000 points)
   - Target: Vectorized engine (12.4 ms)
   - Expected: 70-100× speedup

3. **Batch operations** (2h)
   - Multiple SVGs in sequence
   - Memory usage tracking
   - Expected: No degradation

**Test**:
```bash
PYTHONPATH=. pytest tests/performance/ -v --tb=short
```

---

#### Task 4.4: Documentation Update (4h)

**Documentation to update**:

1. **README.md** - Precision improvements
2. **API documentation** - New FractionalEMUConverter API
3. **Migration notes** - For users
4. **Architecture docs** - System diagrams

---

### Phase 4 Success Criteria

- ✅ All integration tests pass
- ✅ Phase 4 matches Phase 3 baseline
- ✅ Performance targets met (70-100× for paths)
- ✅ Documentation updated
- ✅ Ready for release

---

## Risk Mitigation

### Risk Matrix

| Risk | Severity | Probability | Mitigation |
|------|----------|-------------|------------|
| Precision regression | High | Low | Baseline tests at each phase |
| Performance degradation | Medium | Low | Benchmark suite in Phase 4 |
| PowerPoint incompatibility | High | Very Low | Validated in Phase 0 |
| Mapper breakage | Medium | Low | Comprehensive mapper tests |
| Transform application bugs | High | Medium | Transform-specific tests |

---

### Risk 1: Precision Regression

**Scenario**: Fractional EMU introduces precision errors

**Likelihood**: Low (validated in Phase 0)

**Impact**: High (defeats purpose of implementation)

**Mitigation**:
1. ✅ Baseline test suite with 24 SVGs
2. ✅ Automated comparison at each phase
3. ✅ Exit on major differences
4. ✅ Precision mode validation tests

**Detection**:
```bash
# Phase 1 comparison
python tests/baseline/compare_with_baseline.py --baseline phase0 --compare phase1
# If major differences: STOP and investigate
```

---

### Risk 2: Performance Degradation

**Scenario**: Float operations slower than int

**Likelihood**: Low (benchmarked in Phase 0)

**Impact**: Medium (acceptable if <10% slower)

**Mitigation**:
1. ✅ NumPy vectorization for complex paths (70-100× speedup)
2. ✅ Auto-selection (vectorized vs scalar)
3. ✅ Performance benchmark suite

**Validation**:
```bash
# Run performance tests
PYTHONPATH=. pytest tests/performance/test_fractional_emu_performance.py -v
```

**Acceptance criteria**:
- Simple shapes: <10% slower
- Complex paths (>100 points): 50× faster minimum

---

### Risk 3: PowerPoint Incompatibility

**Scenario**: Float EMU produces invalid PPTX

**Likelihood**: Very Low (validated with PowerPoint)

**Impact**: High (blocker for release)

**Mitigation**:
1. ✅ Phase 0 validation with PowerPoint
2. ✅ Round to int at XML serialization
3. ✅ 24 test PPTX files opened in PowerPoint

**Validation**:
```bash
# Generate Phase 1 baseline and open in PowerPoint
python tests/baseline/generate_baseline.py --phase phase1
open tests/baseline/outputs/phase1/shapes/basic_rectangle.pptx
```

---

### Risk 4: Mapper Breakage

**Scenario**: Mapper updates break existing functionality

**Likelihood**: Low (comprehensive tests)

**Impact**: Medium (delays Phase 3)

**Mitigation**:
1. ✅ Mapper-specific test suite
2. ✅ Backward compatible API (`to_emu()` wrapper)
3. ✅ Phase-by-phase validation

**Test coverage**:
```bash
# Run all mapper tests
PYTHONPATH=. pytest tests/unit/core/map/ -v
```

---

### Risk 5: Transform Application Bugs

**Scenario**: CoordinateSpace applies transforms incorrectly

**Likelihood**: Medium (complex logic)

**Impact**: High (coordinates incorrect)

**Mitigation**:
1. ✅ Transform-specific tests in Phase 2
2. ✅ Baseline comparison detects transform bugs
3. ✅ Nested transform test cases

**Test cases**:
- Single translate
- Nested translates
- Rotate + translate
- Scale + rotate
- Matrix composition

**Validation**:
```bash
# Transform tests should DIFFER in Phase 2
python tests/baseline/compare_with_baseline.py --baseline phase0 --compare phase2
# Expect 7 files to differ (transform category)
```

---

## Rollback Procedures

### Phase 1 Rollback

**Trigger**: Phase 1 baseline doesn't match Phase 0

**Procedure**:
1. Revert `core/fractional_emu/` package
2. Revert `ConversionServices` changes
3. Run Phase 0 tests to confirm rollback
4. Investigate fractional EMU bug

**Rollback time**: 30 minutes

**Data loss**: None (infrastructure only)

---

### Phase 2 Rollback

**Trigger**: Transform bugs or major coordinate differences (non-transform tests)

**Procedure**:
1. Revert `CoordinateSpace` integration
2. Revert parser changes
3. Restore transform storage in IR
4. Run Phase 1 tests to confirm rollback
5. Investigate transform application bug

**Rollback time**: 1 hour

**Data loss**: Phase 2 work (28 hours)

**Mitigation**: Git branching strategy - keep Phase 1 on separate branch

---

### Phase 3 Rollback

**Trigger**: Mapper updates break functionality

**Procedure**:
1. Revert mapper changes
2. Restore hardcoded conversions
3. Keep FractionalEMUConverter (not used yet)
4. Run Phase 2 tests to confirm rollback
5. Investigate mapper bug

**Rollback time**: 2 hours

**Data loss**: Mapper updates only (can re-apply selectively)

**Mitigation**: Update mappers one at a time, test incrementally

---

### Phase 4 Rollback

**Trigger**: Integration issues or performance problems

**Procedure**:
1. Revert to Phase 3 state
2. Investigate integration bug
3. Re-run Phase 4 with fixes

**Rollback time**: 1 hour

**Data loss**: Integration work only

---

## Validation Checkpoints

### Checkpoint 1: After Phase 1

**Validation**:
```bash
# Generate Phase 1 baseline
PYTHONPATH=. python tests/baseline/generate_baseline.py --phase phase1
PYTHONPATH=. python tests/baseline/extract_coordinates.py --phase phase1

# Compare with Phase 0
PYTHONPATH=. python tests/baseline/compare_with_baseline.py \
    --baseline phase0 \
    --compare phase1 \
    --save
```

**Pass criteria**:
- ✅ All 24 tests match Phase 0 exactly
- ✅ 0 differences allowed
- ✅ All unit tests pass

**Fail action**: Rollback Phase 1, investigate fractional EMU bug

---

### Checkpoint 2: After Phase 2

**Validation**:
```bash
# Generate Phase 2 baseline
PYTHONPATH=. python tests/baseline/generate_baseline.py --phase phase2
PYTHONPATH=. python tests/baseline/extract_coordinates.py --phase phase2

# Compare with Phase 0
PYTHONPATH=. python tests/baseline/compare_with_baseline.py \
    --baseline phase0 \
    --compare phase2 \
    --save
```

**Pass criteria**:
- ✅ Transform tests (7 files) show differences (expected)
- ✅ Non-transform tests (17 files) match Phase 0
- ✅ All unit tests pass

**Fail action**:
- If transform tests DON'T differ: Bug in CoordinateSpace
- If non-transform tests differ: Regression bug

---

### Checkpoint 3: After Phase 3

**Validation**:
```bash
# Generate Phase 3 baseline
PYTHONPATH=. python tests/baseline/generate_baseline.py --phase phase3
PYTHONPATH=. python tests/baseline/extract_coordinates.py --phase phase3

# Compare with Phase 0
PYTHONPATH=. python tests/baseline/compare_with_baseline.py \
    --baseline phase0 \
    --compare phase3 \
    --save
```

**Pass criteria**:
- ✅ Most tests match Phase 0 (±1 EMU tolerance)
- ✅ Minor precision improvements acceptable
- ✅ All mapper tests pass

**Fail action**: Rollback Phase 3, investigate mapper bugs

---

### Checkpoint 4: After Phase 4

**Validation**:
```bash
# Generate Phase 4 baseline
PYTHONPATH=. python tests/baseline/generate_baseline.py --phase phase4
PYTHONPATH=. python tests/baseline/extract_coordinates.py --phase phase4

# Compare with Phase 3
PYTHONPATH=. python tests/baseline/compare_with_baseline.py \
    --baseline phase3 \
    --compare phase4 \
    --save

# Performance validation
PYTHONPATH=. pytest tests/performance/ -v
```

**Pass criteria**:
- ✅ All 24 tests match Phase 3
- ✅ Performance targets met
- ✅ All integration tests pass
- ✅ Documentation complete

**Fail action**: Rollback Phase 4, investigate integration bugs

---

## Success Metrics

### Technical Metrics

**Precision**:
- Current: ±0.02 pt
- Target: <1×10⁻⁶ pt
- **Improvement**: 20,000×

**Performance**:
- Simple shapes: ±10% (acceptable)
- Complex paths (>100 points): 50× faster minimum
- **Target**: 70-100× for 10,000 point paths

**Code quality**:
- Test coverage: >85% (maintained)
- Mapper simplification: Remove transform application logic
- API clarity: Backward compatible

---

### Process Metrics

**Phase completion**:
- Phase 1: 20h (infrastructure)
- Phase 2: 28h (baked transforms)
- Phase 3: 36h (mappers)
- Phase 4: 26h (integration)
- **Total**: 110h

**Validation**:
- 24 baseline tests
- 4 validation checkpoints
- Automated regression detection

---

## Migration Timeline

### Week 1 (Phase 0 Complete + Phase 1)

**Days 1-2**: Phase 0 completion
- Task 0.7: IR coordinate audit (0.5h)
- Task 0.8: Architecture documentation (2h)

**Days 3-5**: Phase 1 implementation
- Task 1.3: ViewportContext enhancement (2h)
- Task 1.4: Fractional EMU migration (8h)
- Task 1.5: ConversionServices integration (2h)
- Task 1.6: Phase 1 validation (2h)

**Checkpoint**: Phase 1 validation (must match Phase 0)

---

### Week 2 (Phase 2)

**Days 1-2**: CoordinateSpace
- Task 2.1: Create CoordinateSpace class (6h)
- Task 2.2: Parser integration (12h)

**Days 3-5**: Shape parsers
- Task 2.3: Update all shape parsers (8h)
- Task 2.4: Phase 2 validation (2h)

**Checkpoint**: Phase 2 validation (transform tests must differ)

---

### Week 3 (Phase 3)

**Days 1-3**: Mapper updates
- Task 3.1: Update core mappers (20h)

**Days 4-5**: Services and infrastructure
- Task 3.2: Update services (8h)
- Task 3.3: Update infrastructure (4h)
- Task 3.4: Phase 3 validation (4h)

**Checkpoint**: Phase 3 validation (precision improvements)

---

### Week 4 (Phase 4)

**Days 1-2**: Integration testing
- Task 4.1: Integration tests (12h)

**Day 3**: Baseline validation
- Task 4.2: Baseline validation (4h)

**Day 4**: Performance validation
- Task 4.3: Performance validation (6h)

**Day 5**: Documentation
- Task 4.4: Documentation update (4h)

**Checkpoint**: Phase 4 validation (ready for release)

---

## Conclusion

This migration guide provides:

✅ **4-phase implementation plan** (110 hours)
✅ **Detailed task breakdown** with estimates
✅ **Risk mitigation strategies** for 5 major risks
✅ **Rollback procedures** for each phase
✅ **Validation checkpoints** with pass/fail criteria
✅ **Success metrics** for precision and performance

**Next step**: Execute Phase 1 - Fractional EMU Infrastructure (20 hours)

**Confidence**: Very High - comprehensive planning and validation framework in place.

---

**Status**: Migration guide complete and ready for implementation ✅
