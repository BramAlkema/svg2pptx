# Path-Only Shape Conversion - Archived Implementation

**Archive Date**: 2025-10-05
**Reason**: ADR-002 compliance - implementing native PowerPoint shape support
**Replacement**: Native Circle, Ellipse, Rectangle IR types with prstGeom output

---

## What Was Archived

### Code Removed
- **File**: `core/parse/parser.py`
- **Lines**: 600-749
- **Methods**:
  - `_convert_rect_to_ir()` - Converted SVG rect to Path with 4 line segments
  - `_convert_circle_to_ir()` - Converted SVG circle to Path with 4 Bezier curves
  - `_convert_ellipse_to_ir()` - Converted SVG ellipse to Path with 4 scaled Bezier curves

### Tests
**Status**: No dedicated tests found for these methods
- No test file `test_circle_conversion.py` or similar
- Shape conversion was likely tested through integration tests
- **Action Required**: New implementation must add comprehensive unit tests

---

## Why This Was Archived

### ADR-002 Violation
The old implementation violated **ADR-002: Converter Architecture Standardization**:

**ADR-002 Requirements** (lines 21-26):
```
src/converters/shapes/
├── rectangle.py
├── circle.py
├── ellipse.py
```

**Actual Implementation**:
- No separate converter classes
- All shapes converted to Path at parse time
- Single PathMapper for all geometry

### Loss of PowerPoint Fidelity
Converting circles/ellipses to custom geometry paths:
- ❌ Shapes are not editable as native objects in PowerPoint
- ❌ Cannot use PowerPoint's native resize/rotate/skew handles
- ❌ Larger file sizes (custom geometry XML is verbose)
- ❌ Missed optimization - simple shapes don't need Bezier approximation

---

## Technical Details

### Circle Bezier Approximation
**Magic constant**: `k = 0.552284749831`

This constant derives from the optimal Bezier control point distance for approximating a circular arc with a cubic Bezier curve:
```
k = 4 * (√2 - 1) / 3 ≈ 0.5522847498
```

**Algorithm**: 4 symmetric Bezier curves (one per quadrant)
```python
# Top right quadrant (0° to 90°)
start = (cx + r, cy)
control1 = (cx + r, cy - k*r)
control2 = (cx + k*r, cy - r)
end = (cx, cy - r)
```

### Ellipse Scaling
Ellipses use the same approach with scaled control points:
```python
kx = 0.552284749831 * rx
ky = 0.552284749831 * ry
```

### Rectangle Line Segments
Simple closed path with 4 line segments (no curves needed):
```python
(x, y) → (x+w, y) → (x+w, y+h) → (x, y+h) → (x, y)
```

**Limitation**: No support for rounded corners (`rx`/`ry` attributes ignored)

---

## Key Insights for New Implementation

### Reusable Logic
The Bezier approximation logic should be **preserved** for the fallback case:
- Complex shapes (with filters, clipping, complex transforms) still need Path conversion
- The k-constant and quadrant logic are correct and should be reused
- New implementation: Use in `CircleMapper._circle_to_path()` for fallback

### Missing Features
The old implementation lacked:
1. **Complexity detection** - No logic to decide "simple vs complex"
2. **Native shape output** - Never generated `<a:prstGeom>`
3. **Rounded rectangles** - `rx`/`ry` attributes were ignored
4. **Hyperlink handling** - `getattr(self, '_current_hyperlink', None)` does nothing

### Test Coverage Gap
**Critical**: The lack of unit tests means:
- Shape conversion behavior was untested
- Edge cases (zero radius, negative dimensions) may be unhandled
- New implementation MUST include comprehensive tests (Task 1.3, 2.4, 3.5)

---

## Migration Path

### DO NOT Create Backward Compatibility Shims
Per user directive: "Don't let double orphaned backward compatible shims in place"

**Approach**:
1. ✅ Archive old implementation (done)
2. ✅ Remove old methods from `parser.py` (will be done in new implementation)
3. ✅ Implement new Shape IR and mappers
4. ❌ **DO NOT** keep old methods with `_legacy` suffix
5. ❌ **DO NOT** create compatibility wrappers

### Breaking Changes Are Acceptable
This is internal architecture - no public API changes:
- Parser internals can change freely
- IR types can be extended
- Only requirement: Same visual output (or better)

---

## Files in This Archive

1. **`parser_methods.py`** - Extracted methods with annotations
2. **`README.md`** - This file

---

## Replacement Specification

**See**: `.agent-os/specs/2025-10-05-native-shape-support/`
- `spec.md` - Full technical specification
- `tasks.md` - Implementation task breakdown

**Key Changes**:
- New IR types: `Circle`, `Ellipse`, `Rectangle` (Phase 1)
- Policy engine: `decide_shape_strategy()` for native vs custom (Phase 2)
- Native mappers: `CircleMapper`, `EllipseMapper`, `RectMapper` (Phase 3)
- Parser update: Return Shape IR for simple shapes (Phase 4)

**Expected Outcome**:
- Simple circles → `<a:prstGeom prst="ellipse">` (native PowerPoint)
- Complex circles → `<a:custGeom>` with Bezier paths (fallback)
- 10-20% smaller file sizes for shape-heavy presentations
- Native editing in PowerPoint

---

## Archive Retention Policy

**Keep Indefinitely** - This archive documents:
1. Architectural decision to move away from path-only conversion
2. Bezier approximation constants and algorithms (may be reused)
3. Baseline for performance comparison
4. Evidence of ADR-002 compliance gap

**Reference Only** - Do not import or use archived code in production
