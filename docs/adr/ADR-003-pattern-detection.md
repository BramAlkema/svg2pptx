# ADR-003: Comprehensive SVG Pattern Detection for Native a:pattFill

## Status
**REJECTED** - Will not implement comprehensive pattern detection system

## Context

A sophisticated pattern detection system was proposed to automatically detect when SVG `<pattern>` elements are "close enough" to PowerPoint's preset patterns to use native `a:pattFill` instead of EMF fallbacks.

### Proposed System Overview

The comprehensive detector would implement a deterministic, scale-robust pipeline:

1. **Flatten everything**: Apply `patternUnits`, `patternContentUnits`, `patternTransform`, and element transforms
2. **Canonicalise the tile**: Compute final tile rect, clip primitives, expand stroked paths
3. **Feature extraction**:
   - Angle histogram with 5° bins, peak finding for line families
   - Pitch/spacing detection per family with 1D peak finding
   - Orthogonality checking (Δθ ≈ 90°)
   - Dot grid clustering (square vs hex lattice)
   - Ink coverage fraction calculation
4. **Snap to preset with scoring**:
   - Angle snapping to {0°, 90°, 45°, 135°} with 3° tolerance
   - Duty cycle classification (light < 0.10, dark > 0.22)
   - Pattern mapping: 1 family → hatch, 2 orthogonal → cross, dots → percent
5. **Emit native or fallback**: Generate `a:pattFill` XML or EMF tile

### Technical Specifications

- **Tolerances**: Angle snap 3°, pitch CV ≤ 0.10, minimum score ≥ 0.7
- **Robustness**: Line family extraction via angle-weighted Hough/RANSAC
- **Performance**: Fast, explainable, doesn't lie about spacing
- **Coverage**: 24 PowerPoint presets (horz/vert/diag × light/normal/dark + cross + pct5-90)

## Decision

**We will NOT implement the comprehensive pattern detection system.**

## Rationale

### 1. **Complexity vs. Value Trade-off**

The proposed system, while technically impressive, represents a massive engineering effort:

- **~2000+ lines of code** for robust implementation
- **Complex geometry processing** (Hough transforms, RANSAC, clustering)
- **Extensive test coverage** needed for edge cases
- **Performance optimization** for real-time processing

**Value delivered**: Marginal improvement in file size and native feel for a small subset of patterns.

### 2. **EMF Fallback Already Works Well**

Our current EMF-based approach provides:

- **Universal compatibility**: Handles ANY pattern, no matter how complex
- **Perfect visual fidelity**: Exact rendering of original SVG pattern
- **Reliable performance**: No complex detection algorithms to fail
- **Maintainable codebase**: Simple, predictable behavior

### 3. **Pattern Usage Reality**

In real-world SVG files:

- **Most patterns are complex**: Gradients, images, complex geometry
- **Custom patterns dominate**: Rarely match PowerPoint's 24 presets exactly
- **Designer intent**: Authors usually want exact visual preservation
- **File size impact**: Minimal in practice (EMF compression is effective)

### 4. **Maintenance Burden**

A comprehensive detector would require:

- **Constant tuning**: Tolerance adjustments based on user feedback
- **Edge case handling**: Geometric corner cases, floating-point precision
- **PowerPoint compatibility**: Different Office versions have different preset behaviors
- **Regression testing**: Ensuring detection doesn't break over time

### 5. **Development Opportunity Cost**

The effort required for comprehensive pattern detection could instead deliver:

- **More SVG filter effects**: Better coverage of actual user needs
- **Performance optimizations**: Faster conversion for all users
- **Accessibility features**: Better PowerPoint compatibility
- **Bug fixes**: Resolving existing conversion issues

### 6. **User Experience Considerations**

- **Predictability**: Users prefer consistent behavior over sometimes-native, sometimes-EMF
- **Debug complexity**: Pattern detection failures would be hard to diagnose
- **False positives**: Incorrect preset mapping could surprise users
- **Configuration burden**: Users would need controls for detection sensitivity

## Consequences

### Positive
- **Simpler codebase**: Maintain current EMF-based pattern handling
- **Reliable behavior**: Consistent visual fidelity across all patterns
- **Development focus**: Resources directed toward high-impact features
- **Maintainability**: Fewer complex subsystems to maintain

### Negative
- **File size**: Slightly larger output for simple patterns that could be native
- **Native feel**: Miss opportunity for true PowerPoint-native pattern rendering
- **Performance**: EMF patterns may render slightly slower than native presets

## Implementation

1. **Keep current EMF approach**: Continue using vector-first EMF tiles for all patterns
2. **Document the decision**: Placeholder implementation with comprehensive documentation
3. **Optimize EMF path**: Focus on improving EMF compression and rendering performance
4. **Future reconsideration**: Re-evaluate if PowerPoint preset usage becomes dominant

## References

- **Placeholder implementation**: `src/converters/pattern_detection.py`
- **Current EMF approach**: `src/emf_blob.py`, `src/converters/filters/geometric/tile.py`
- **Pattern processing**: Task 2.7 implementation documentation

## Revision History

- **2025-09-15**: Initial decision - Reject comprehensive pattern detection
- **Decision maker**: Engineering team consensus
- **Review date**: 2026-Q1 (if PowerPoint pattern usage patterns change significantly)