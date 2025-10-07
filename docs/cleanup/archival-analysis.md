# Archival Analysis - Task 0.3

**Date**: 2025-01-06
**Task**: Phase 0, Task 0.3 - Determine what needs archival
**Status**: Analysis Complete

---

## Executive Summary

Based on Tasks 0.1 and 0.2 audits, **minimal archival is needed**. The existing infrastructure is excellent and will be **reused**, not replaced.

### Archival Candidates: **0 files**

**Conclusion**: No files need archiving. The "baked transform architecture" is an **enhancement** of existing code, not a replacement.

---

## Audit Review

### Task 0.1 Findings: Transform Infrastructure

**Existing Components** (KEEP ALL):
- ✅ `core/transforms/core.py` - Matrix class (reuse)
- ✅ `core/transforms/parser.py` - TransformParser (reuse)
- ✅ `core/transforms/matrix_composer.py` - viewport_matrix, element_ctm (reuse)
- ✅ `core/transforms/engine.py` - TransformEngine (keep)
- ✅ `core/viewbox/core.py` - ViewportEngine (reuse)
- ✅ `core/viewbox/ctm_utils.py` - CTM propagation (reuse)
- ✅ `core/services/viewport_service.py` - Enhance (don't replace)

**Decision**: **KEEP ALL** - These are foundational and excellent

---

### Task 0.2 Findings: Hardcoded Conversions

**Files with hardcoded `* 12700`** (56 instances across 13 files):
- `core/map/*.py` (6 mappers) - **MODIFY**, don't archive
- `core/services/filter_service.py` - **MODIFY**, don't archive
- `core/utils/*.py` - **MODIFY**, don't archive

**Decision**: These files will be **updated in place** (Phase 3), not archived

---

## What Gets Archived vs Updated

### Files to ARCHIVE: **None**

**Rationale**: No conflicting implementations found

### Files to UPDATE (Not Archive):

**Phase 2 Updates** (Parser):
- `core/parse/parser.py` - Apply transforms at parse time
  - Change: Apply CoordinateSpace transformation
  - Keep: All existing parsing logic
  - **Action**: Modify, don't archive

**Phase 3 Updates** (Mappers):
- All mapper files - Replace `* 12700` with fractional EMU
  - Keep: All existing logic
  - Change: Just the conversion lines
  - **Action**: Modify, don't archive

**Phase 1 Updates** (Services):
- `core/services/viewport_service.py` - Add new methods
  - Keep: Existing methods for backward compatibility
  - Add: New methods (`svg_xy_to_pt`, `len_to_pt`)
  - **Action**: Enhance, don't archive

---

## Potential Future Archival

### IR Transform Fields (Later)

**After Phase 2 complete**, IR may no longer need `transform` fields:

```python
# Current IR (Phase 0-1)
@dataclass
class Circle:
    center: Point
    radius: float
    transform: np.ndarray | None  # ← Will be deprecated

# Future IR (Phase 2+)
@dataclass
class Circle:
    center: Point  # Already transformed coordinates
    radius: float
    # No transform field - coordinates are pre-transformed
```

**Action**: **Gradual deprecation**, not immediate archival
- Phase 2: Mark as deprecated, stop populating
- Phase 4: Remove field entirely
- Not an archival task - just field removal

---

## Archive Directory Structure

Since no archival is needed now, we'll create a **placeholder structure** for potential future use:

```bash
archive/
├── pre-baked-transforms/
│   ├── README.md          # Documentation of what gets archived (if anything)
│   ├── code/              # Archived code (empty for now)
│   ├── tests/             # Archived tests (empty for now)
│   └── docs/              # Archived docs (empty for now)
```

---

## Documentation Strategy

Instead of archiving code, we'll **document the evolution**:

### docs/cleanup/architecture-evolution.md

Document:
1. **Current State** (Phase 0): How transforms work now
2. **Enhanced State** (Phase 1-2): Baked transforms added
3. **Final State** (Phase 3-4): Hardcoded conversions replaced

This preserves knowledge without archiving working code.

---

## Test Preservation

### Tests to KEEP (All of them)

From Task 0.1 audit, ~100 existing transform tests:
- `tests/unit/transforms/test_matrix_core.py` (30 tests) - **KEEP**
- `tests/unit/transforms/test_matrix_composer.py` (25 tests) - **KEEP**
- `tests/unit/converters/test_ctm_propagation.py` (15 tests) - **KEEP**
- All mapper tests - **KEEP and UPDATE**

**Action**: **Adapt** existing tests for new API, don't archive

### Tests to ADD (Not replace)

- Fractional EMU precision tests
- Baked transform tests
- Parser transformation tests
- Precision mode tests

---

## Recommendation: Skip Full Archival

### Why No Archival is Needed

1. **No Conflicting Implementations**: Existing code will be reused
2. **Enhancement, Not Replacement**: We're adding features, not rebuilding
3. **Backward Compatibility**: Old APIs remain during transition
4. **Git History Sufficient**: Version control preserves history

### What We'll Do Instead

1. **Create placeholder archive directory** (for future use if needed)
2. **Document architecture evolution** (instead of archiving code)
3. **Update files in place** (with git history)
4. **Deprecate gradually** (not immediate removal)

---

## Task 0.3 Deliverables

### 1. Archive Directory (Placeholder)
```bash
mkdir -p archive/pre-baked-transforms/{code,tests,docs}
```

### 2. Archive README
Document what would be archived (and why nothing is currently)

### 3. Architecture Evolution Document
Track how the system evolves through phases

### 4. This Analysis Document
Explain why minimal archival is needed

---

## Conclusion

**Task 0.3 outcome: No archival needed** ✅

The audit revealed that existing infrastructure is excellent and will be **reused**, not replaced. This is a **huge win** - it means:

1. **Lower risk** - Building on proven code
2. **Faster implementation** - No need to rebuild
3. **Better quality** - Existing code is tested and production-ready
4. **Knowledge preservation** - Team expertise embedded in code

**Recommendation**: Mark Task 0.3 as complete with minimal work (create placeholder structure and document findings).

---

**Status**: ✅ Analysis Complete
**Decision**: Create placeholder archive, document evolution, no code archival needed
**Effort**: 1 hour (reduced from planned 4 hours)
**Time Saved**: 3 hours
