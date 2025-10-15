# ADR-019: SVG Marker and Symbol System Migration

**Status**: Accepted
**Date**: 2025-10-15

## Context

SVG markers (arrowheads, line decorations) and symbols (reusable graphics) are critical for technical diagrams, flowcharts, and professional graphics. The comprehensive marker system was archived during clean slate refactoring but never migrated to production.

**Current State:**
- No marker support in production pipeline
- `marker-start`, `marker-mid`, `marker-end` properties ignored
- `<marker>` and `<symbol>` elements not processed
- Technical diagrams lose critical visual information
- W3C compliance gap for marker test cases

**Archived Implementation:**
- 696 lines of comprehensive marker handling
- Complete marker positioning: start, mid, end
- Symbol definition and `<use>` element instantiation
- Arrowhead scaling and orientation
- Transform-aware marker positioning
- Overflow handling and clipping

## Problem Statement

Without marker support, the conversion pipeline fails for:

1. **Technical Diagrams** - Flowcharts, UML diagrams, network diagrams
2. **Arrows and Connectors** - Directional indicators, relationship lines
3. **Custom Line Decorations** - Dots, circles, custom shapes on paths
4. **Symbol Libraries** - Reusable icon systems, diagram components
5. **Engineering Drawings** - CAD exports, technical specifications

This represents a **major W3C compliance gap** for professional graphics workflows.

## Decision

**Migrate the archived marker system to `core/map/` with integration into the mapper pipeline.**

### Architecture

```
core/map/
├── marker_processor.py      # MarkerProcessor (main logic from markers.py)
├── marker_mapper.py          # MarkerMapper (pipeline integration)
└── symbol_mapper.py          # SymbolMapper (for <symbol>/<use> elements)
```

### Key Components

#### 1. MarkerProcessor (from markers.py)
```python
class MarkerProcessor:
    """Processes SVG marker definitions and instances."""

    def process_marker_definition(self, marker_elem: ET.Element) -> MarkerDefinition
    def process_symbol_definition(self, symbol_elem: ET.Element) -> SymbolDefinition
    def apply_markers_to_path(self, path_elem: ET.Element, context) -> List[Shape]
    def calculate_marker_transform(self, position, angle, definition) -> Matrix
    def render_marker_content(self, definition, transform) -> str
```

#### 2. MarkerMapper (new - pipeline integration)
```python
class MarkerMapper(BaseMapper):
    """Maps SVG elements with markers to PowerPoint shapes."""

    def can_map(self, element: ET.Element) -> bool:
        # Check for marker-start/mid/end properties

    def map(self, element: ET.Element, context) -> List[Shape]:
        # Convert base path + add marker shapes
```

#### 3. SymbolMapper (new - for symbol/use)
```python
class SymbolMapper(BaseMapper):
    """Maps SVG <use> elements referencing symbols."""

    def can_map(self, element: ET.Element) -> bool:
        # Check for <use> elements

    def map(self, element: ET.Element, context) -> List[Shape]:
        # Instantiate symbol with transforms
```

## Implementation Plan

### Phase 1: Core Migration (Immediate)
1. Copy `markers.py` → `core/map/marker_processor.py`
2. Update imports (remove BaseConverter dependency)
3. Refactor to use mapper architecture patterns
4. Fix lxml usage (verify safe patterns)

### Phase 2: Mapper Integration
1. Create `MarkerMapper` in `core/map/marker_mapper.py`
2. Create `SymbolMapper` in `core/map/symbol_mapper.py`
3. Register mappers in converter pipeline
4. Add marker registry to `ConversionServices`

### Phase 3: Testing
1. Unit tests for MarkerProcessor
2. Integration tests for marker-decorated paths
3. E2E tests for real-world diagrams (flowcharts, UML)
4. Symbol instantiation tests

### Phase 4: W3C Compliance
1. Run W3C marker test suite
2. Validate marker positioning accuracy
3. Test marker orientation (auto, auto-start-reverse, angles)
4. Verify symbol with viewBox transformations

## Marker Features Supported

### Marker Properties
- ✅ `marker-start` - Marker at path start
- ✅ `marker-mid` - Markers at path vertices
- ✅ `marker-end` - Marker at path end
- ✅ `markerUnits` - strokeWidth vs userSpaceOnUse
- ✅ `orient` - auto, auto-start-reverse, angle
- ✅ `refX`, `refY` - Reference point positioning
- ✅ `markerWidth`, `markerHeight` - Marker dimensions
- ✅ `viewBox` - Marker coordinate system
- ✅ `overflow` - Marker clipping behavior

### Symbol Features
- ✅ `<symbol>` - Reusable graphic definitions
- ✅ `<use>` - Symbol instantiation with transforms
- ✅ `preserveAspectRatio` - Aspect ratio handling
- ✅ `viewBox` - Symbol coordinate system
- ✅ Nested transforms and styling

## PowerPoint Mapping Strategy

### Approach 1: Composite Shapes (Primary)
```xml
<p:grpSpPr>
  <!-- Base path -->
  <p:sp> ... </p:sp>

  <!-- Marker shapes positioned at path points -->
  <p:sp> ... </p:sp>
  <p:sp> ... </p:sp>
</p:grpSpPr>
```

**Pros:**
- Full control over marker geometry
- Supports custom marker shapes
- Transform-aware positioning

**Cons:**
- Multiple shapes per decorated path
- Complexity for mid-markers on long paths

### Approach 2: PowerPoint Line Ends (Fallback)
```xml
<a:ln>
  <a:headEnd type="arrow"/>
  <a:tailEnd type="arrow"/>
</a:ln>
```

**Pros:**
- Single shape for simple arrows
- PowerPoint native rendering

**Cons:**
- Limited to predefined arrow types
- No support for custom markers
- No mid-markers

**Decision:** Use **Approach 1** for full SVG fidelity, fallback to **Approach 2** for standard arrows when policy permits.

## Migration Strategy

### Backward Compatibility
- Marker support is additive (no breaking changes)
- Paths without markers continue working unchanged
- Marker registry optional (graceful degradation)

### Performance Considerations
- Cache marker definitions (avoid re-parsing)
- Lazy marker rendering (only when referenced)
- Batch marker transform calculations
- Symbol deduplication

## Consequences

### Positive
- **W3C Compliance**: Closes major marker test gap
- **Professional Graphics**: Flowcharts, UML, engineering drawings supported
- **Real-world Tools**: Figma, Sketch, Illustrator marker exports work
- **Technical Accuracy**: Proper arrowhead orientation and scaling
- **Symbol Libraries**: Reusable component systems functional

### Negative
- **Code Size**: +696 lines (marker processor)
- **Shape Complexity**: Decorated paths become shape groups
- **Performance**: Mid-markers on complex paths may be slow
  - Mitigation: Policy-driven marker simplification
- **DrawingML Limitations**: PowerPoint line ends don't match all SVG markers
  - Mitigation: Composite shape approach

### Risks
- **Positioning Accuracy**: Marker transforms may not be pixel-perfect
  - Mitigation: Comprehensive test suite, visual validation
- **Path Tangent Calculation**: Accurate angles at path points required
  - Mitigation: Use existing path geometry utilities
- **Symbol Complexity**: Nested symbols and circular references
  - Mitigation: Reference tracking, max depth limits

## Success Metrics

1. **Coverage**: marker-start/mid/end + symbol/use support
2. **W3C Compliance**: 80%+ pass rate on marker test suite
3. **Performance**: <50ms marker processing for typical diagrams
4. **Integration**: Zero breaking changes to existing code
5. **Visual Fidelity**: 90%+ accuracy on real-world diagrams

## Timeline

- **Phase 1 (Migration)**: 2-3 hours
- **Phase 2 (Integration)**: 3-4 hours
- **Phase 3 (Testing)**: 4-5 hours
- **Phase 4 (W3C Validation)**: 2-3 hours

**Total estimate**: 2 days of focused work

## References

- Archived implementation: `archive/legacy-src/converters/markers.py`
- W3C Marker Spec: https://www.w3.org/TR/SVG2/painting.html#Markers
- W3C Symbol Spec: https://www.w3.org/TR/SVG2/struct.html#SymbolElement
- Related: ADR-018 (Filter System), ADR-015 (Clipping Pipeline)

## Decision Rationale

Markers are essential for technical graphics and represent a significant W3C compliance gap. The archived implementation is comprehensive and well-tested. Migrating it with mapper integration is lower risk than:

1. Rewriting from scratch (high effort, high risk)
2. Leaving gaps (unacceptable for professional workflows)
3. External marker library (license, integration complexity)

The mapper architecture allows incremental rollout and policy-driven complexity management.

---

**Approved by**: [Engineering Lead]
**Implementation**: In Progress
**Review Date**: 2025-10-15
