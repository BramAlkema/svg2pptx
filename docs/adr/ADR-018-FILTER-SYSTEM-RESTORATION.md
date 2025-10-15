# ADR-018: SVG Filter Effects System Restoration

**Status**: Accepted
**Date**: 2025-10-15

## Context

During the "clean slate" refactoring effort, a comprehensive SVG filter effects system was archived to `archive/legacy-src/converters/filters/` but only a minimal stub (`core/services/filter_service.py`) was migrated. This resulted in a critical capability gap:

**Current State (Minimal Stub):**
- Only 2 filter primitives supported: `feGaussianBlur`, `feDropShadow`
- ~223 lines in `filter_service.py`
- All other filters return XML comments: `<!-- Filter: No supported primitives -->`
- W3C filter compliance estimated at 10-20%

**Archived State (Comprehensive System):**
- 13 filter implementation modules
- Complete filter primitive coverage:
  - **Geometric filters**: component_transfer, composite, diffuse_lighting, displacement_map, morphology, specular_lighting, tile, transforms
  - **Image filters**: blur, color, convolve_matrix
  - **Core infrastructure**: registry, chain, base converter
- Reported 330 tests passing (pre-archive)
- Estimated 60-80% W3C filter compliance

## Problem Statement

The current production pipeline cannot handle:
1. **Color transformations** (`feColorMatrix`) - critical for accessibility, theming
2. **Blending modes** (`feComposite`) - required for modern design effects
3. **Morphological operations** (`feMorphology`) - used in icon systems, logos
4. **Lighting effects** (`feDiffuseLighting`, `feSpecularLighting`) - 3D-style rendering
5. **Displacement/distortion** (`feDisplacementMap`) - artistic effects
6. **Custom convolution** (`feConvolveMatrix`) - edge detection, sharpening
7. **Filter chains** - multiple primitives composed together

This severely limits W3C SVG compliance and breaks real-world graphics workflows.

## Decision

**Restore the archived filter system to production with modernized architecture:**

### Phase 1: Copy Core Infrastructure (Immediate)
1. Migrate `archive/legacy-src/converters/filters/` → `core/filters/`
2. Preserve original implementations with minimal changes:
   - Update imports to use `lxml.etree` exclusively
   - Remove deprecated patterns (if any)
   - Keep all existing filter logic intact

### Phase 2: Service Integration
1. Extend `FilterService` to delegate to migrated filter classes
2. Maintain backward compatibility with current 2-filter stub
3. Add filter registry for dynamic primitive resolution
4. Implement policy-driven fallback strategies:
   - Native DrawingML conversion (preferred)
   - EMF rasterization fallback (complex filters)
   - Graceful degradation (unsupported combinations)

### Phase 3: Test Migration
1. Restore original filter test suite (330 tests)
2. Add integration tests for filter chains
3. Add E2E tests for W3C filter compliance scenarios
4. Validate DrawingML output correctness

### Phase 4: Documentation
1. Document supported filter primitives and limitations
2. Add filter conversion examples to developer guide
3. Update W3C compliance assessment with realistic estimates
4. Create migration guide for teams using filter effects

## Implementation Plan

### Directory Structure
```
core/filters/
├── __init__.py                    # Public API
├── base.py                        # BaseFilterConverter
├── registry.py                    # FilterRegistry
├── chain.py                       # Filter chain composition
├── context.py                     # FilterContext for conversions
├── geometric/
│   ├── __init__.py
│   ├── component_transfer.py     # feComponentTransfer
│   ├── composite.py              # feComposite (blending)
│   ├── diffuse_lighting.py       # feDiffuseLighting
│   ├── displacement_map.py       # feDisplacementMap
│   ├── morphology.py             # feMorphology
│   ├── specular_lighting.py      # feSpecularLighting
│   ├── tile.py                   # feTile
│   └── transforms.py             # Matrix transforms
├── image/
│   ├── __init__.py
│   ├── blur.py                   # feGaussianBlur (enhanced)
│   ├── color.py                  # feColorMatrix
│   └── convolve_matrix.py        # feConvolveMatrix
└── utils/
    ├── __init__.py
    └── parsing.py                # Filter attribute parsing
```

### Updated FilterService API
```python
class FilterService:
    def __init__(self, policy_engine: Optional[PolicyEngine] = None):
        self._filter_cache: dict[str, ET.Element] = {}
        self._registry = FilterRegistry()  # NEW: Dynamic filter resolution
        self._policy_engine = policy_engine

    def get_supported_filters(self) -> list[str]:
        """Returns all registered filter primitives."""
        return self._registry.list_filters()
        # Expected: ['feGaussianBlur', 'feDropShadow', 'feColorMatrix',
        #            'feComposite', 'feMorphology', 'feDiffuseLighting',
        #            'feSpecularLighting', 'feDisplacementMap',
        #            'feConvolveMatrix', 'feComponentTransfer', 'feTile']
```

## Migration Strategy

### Backward Compatibility
- Keep existing `FilterService.get_filter_content()` signature
- Existing code using blur/shadow continues working
- New filters added incrementally via registry

### Breaking Changes
- None (additive only)

### Deprecations
- None (stub behavior is enhanced, not replaced)

## Consequences

### Positive
- **W3C Compliance**: 10-20% → 60-80% filter support
- **Real-world graphics**: Supports modern design tools (Figma, Sketch, Illustrator)
- **Accessibility**: Color matrix enables WCAG compliance transformations
- **Performance**: Policy engine can selectively rasterize complex filters
- **Maintainability**: Modular architecture, each filter independently testable

### Negative
- **Code size**: +~2,000-3,000 lines of filter implementation code
- **Testing burden**: 330+ tests to validate (but these already existed)
- **Complexity**: Filter chains require careful composition logic
- **DrawingML limitations**: Not all SVG filters have direct PowerPoint equivalents
  - Mitigation: EMF fallback for unsupported combinations

### Risks
- **Performance regression**: Complex filter chains may be slow
  - Mitigation: Policy engine can enforce rasterization thresholds
- **DrawingML accuracy**: Some filters may not match SVG pixel-perfect
  - Mitigation: Visual regression testing, acceptance criteria
- **Maintenance overhead**: 11 filter modules to keep updated
  - Mitigation: Comprehensive test coverage, clear ownership

## Success Metrics

1. **Coverage**: 11+ filter primitives supported (up from 2)
2. **Tests**: 330+ filter tests passing
3. **W3C Compliance**: 60%+ pass rate on W3C filter test suite
4. **Performance**: Filter conversion <100ms for typical use cases
5. **Integration**: Zero breaking changes to existing code

## Timeline

- **Phase 1 (Copy)**: 1-2 hours (mechanical file copy + import fixes)
- **Phase 2 (Integration)**: 4-6 hours (registry, service wiring)
- **Phase 3 (Tests)**: 6-8 hours (test migration, validation)
- **Phase 4 (Docs)**: 2-3 hours (documentation, examples)

**Total estimate**: 2-3 days of focused work

## References

- Original filter implementations: `archive/legacy-src/converters/filters/`
- Current stub: `core/services/filter_service.py:178` (2 filters only)
- W3C Filter Effects Spec: https://www.w3.org/TR/filter-effects-1/
- Related: ADR-015 (Clipping Pipeline), ADR-011 (Animation Fidelity)

## Decision Rationale

The archived filter system represents significant engineering effort and business value that should not be lost. Restoring it with minimal changes is lower risk than:
1. Rewriting from scratch (high effort, high risk)
2. Leaving stub in place (unacceptable W3C compliance gap)
3. External filter library (license, integration complexity)

The modular architecture allows incremental rollout and policy-driven fallbacks for edge cases.

---

**Approved by**: [Engineering Lead]
**Implementation**: [Assigned Developer]
**Review Date**: 2025-10-15
