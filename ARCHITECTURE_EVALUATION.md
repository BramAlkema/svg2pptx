# Clean Slate Architecture Evaluation

## Your Proposal Assessment

Your "clean slate, heavy reuse" architecture is **excellent** and addresses the core architectural debt in the current codebase. After analyzing the current state, I can see exactly why this approach would work brilliantly.

## Current State vs Proposed Architecture

### Current Problems (Confirmed by Analysis)

1. **Mixed Responsibilities**: Converters handle both SVG parsing AND DrawingML generation
2. **Tight Coupling**: 65+ suspicious files in essential modules because they're not cleanly imported
3. **SVG Weirdness Everywhere**: Transform logic scattered across converters instead of preprocessed
4. **No Clear IR**: Direct DOM → DrawingML with business logic mixed throughout
5. **Adaptation Hell**: 33 suspicious converter files because functionality is duplicated/scattered

### Your Solution Strengths

✅ **Clean Separation**: `pre/` → `ir/` → `map/` → `io/` is exactly what's missing
✅ **Battle-Tested Reuse**: Wrap proven components (a2c, color parsing, font metrics) behind clean interfaces
✅ **Policy Centralization**: All "nearest PPTX equivalent" decisions in one place
✅ **Deterministic Pipeline**: Pure functions, no side effects in IR
✅ **Incremental Migration**: Can reuse 60-70% immediately while building clean foundation

## What We'd Immediately Reuse (High Value)

From current codebase analysis, these components are proven and reusable:

### Proven Components (Reuse via Adapters)
```python
# core/geom/ - Wrap existing math
src/paths/a2c.py              # Arc to cubic conversion (battle-tested)
src/paths/arc_converter.py    # Arc handling
src/viewbox/core.py           # Viewport transformations (4x performance target)
src/units/core.py             # EMU conversion system (197x faster)

# adapters/text/ - Wrap styling logic
src/converters/text.py        # Per-tspan styling, font resolution
TEXT_CONVERTER_FIXES.md       # Your documented fixes for anchor/baseline

# adapters/graphics/ - Wrap proven generators
src/paths/drawingml_generator.py  # DrawingML XML generation
src/color/                         # 97% test coverage, 29k ops/sec

# adapters/io/ - Wrap packaging
src/core/pptx_builder.py      # PPTX packaging & relationships
src/emf_packaging.py          # EMF fallback (when needed)
```

### External Libs (Already Identified)
```python
# Vendor/wrap these
lxml.etree                    # XML processing (mandated in CLAUDE.md)
fontTools                     # Font metrics (already using)
skia-pathops                  # Boolean operations (add)
numpy                         # Transform matrices (already using)
```

## Proposed Migration Strategy

### Phase 1: Foundation (2-3 weeks)
```
svg2pptx-next/
  core/
    ir/
      scene.py              # Path, TextFrame, Group, Clip dataclasses
      paint.py              # Solid, Gradient, Pattern types
      transform.py          # Mat3x3 wrapper over current engine
    policy/
      nearest_equivalent.py # All DML vs EMF decisions
  adapters/
    legacy_text.py          # Wrap current TextConverter fixes
    legacy_paths.py         # Wrap DrawingMLGenerator
    legacy_color.py         # Wrap color system
  tests/
    test_ir.py              # Golden tests for IR serialization
```

### Phase 2: Preprocessors (2-3 weeks)
```
  core/
    pre/
      expand_use.py         # Inline <use>/<symbol> (adapt current symbols.py logic)
      normalize_transforms.py # Push transforms to geometry (adapt current CTM)
      a2c.py                # Arc flattening (wrap current a2c.py)
      boolean_clip.py       # Geometric clipping (NEW: skia-pathops)
      text_layout_prep.py   # tspan→runs (adapt your documented fixes)
```

### Phase 3: Mappers (1-2 weeks)
```
  core/
    map/
      path_mapper.py        # IR.Path → DML (via legacy_paths adapter)
      text_mapper.py        # IR.TextFrame → DML (via legacy_text adapter)
      group_mapper.py       # Minimal container mapping
    io/
      pptx_writer.py        # Package assembly (wrap legacy PPTX builder)
```

## Immediate Benefits

1. **75% Code Reduction Maintained**: Keep essential 75 files, but organized properly
2. **Text Fixes Applied**: Your documented fixes implemented in clean adapters
3. **W3C Compliance Preserved**: Essential test suite (2 files) ensures standards compliance
4. **Google Slides Integration**: API endpoints (8 files) for side-by-side comparison
5. **Battle-Tested Logic**: Reuse proven components without architectural debt

## Implementation Priorities

### Week 1-2: IR + Basic Pipeline
```python
@dataclass
class Path:
    segments: List[Segment]    # Already a2c'ed via adapter
    fill: Paint               # Solid/Gradient/None
    stroke: Stroke
    clip: Optional[ClipRef]
    transform: Mat3x3         # Pre-normalized

@dataclass
class TextFrame:
    origin: Point
    runs: List[Run]           # Each run = one tspan (your fixes)
    anchor: Literal["start","middle","end"]
    bbox: Rect

# Golden test: SVG → IR → JSON serialization
```

### Week 3-4: Preprocessors + Text Fixes
```python
# core/pre/text_layout_prep.py
def prepare_text(text_element: ET.Element) -> TextFrame:
    """Apply your documented fixes:
    - Raw SVG anchors (start|middle|end)
    - Per-tspan runs with styling inheritance
    - Conservative baseline handling
    - ConversionContext coordinate pipeline
    """
    runs = collect_text_runs(text_element)  # Your per-tspan logic
    anchor = get_raw_text_anchor(text_element)  # No double mapping
    return TextFrame(origin=point, runs=runs, anchor=anchor, bbox=bbox)
```

### Week 5-6: Mappers + Policy
```python
# core/map/text_mapper.py
def map_text_frame(frame: TextFrame, policy: Policy) -> str:
    """Generate DML using policy decisions"""
    if policy.use_native_text(frame):
        return adapters.legacy_text.generate_dml(frame)  # Wrap current generator
    else:
        return adapters.emf_text.generate_outlines(frame)  # Fallback

# core/policy/nearest_equivalent.py
def use_native_text(frame: TextFrame) -> bool:
    """Policy: native DML vs EMF fallback"""
    return (
        all(font_available(run.font_family) for run in frame.runs) and
        len(frame.runs) < 20 and  # Complexity threshold
        not has_complex_effects(frame)
    )
```

## Migration Benefits Analysis

### Code Quality Gains
- **Single Responsibility**: Each preprocessor/mapper has one clear job
- **Testable**: IR is pure data, functions are deterministic
- **Policy Transparency**: All tradeoff decisions visible in one place
- **Adapter Isolation**: Legacy code contained behind clean interfaces

### Performance Preserved
- **Proven Hotpaths**: Keep current unit converter (197x faster), viewbox (4x target)
- **Incremental Optimization**: Replace adapters when better implementations available
- **Benchmark Continuity**: Can A/B test old vs new pipeline during migration

### Feature Completeness
- **W3C Compliance**: Preserve essential test suite (2 files)
- **Visual Fidelity**: Keep E2E visual tests (7 files) for regression detection
- **Google Slides**: Maintain API integration (8 files) for comparison workflows
- **Text Fidelity**: Your fixes applied in clean architecture

## Risk Mitigation

### Low Risk Elements (Reuse Directly)
- Mathematical components (a2c, units, viewbox)
- PPTX packaging (proven, no architectural debt)
- Color system (97% test coverage)

### Medium Risk Elements (Adapt)
- Text converter (your fixes address main issues)
- DrawingML generation (functional but tightly coupled)
- Symbol/use handling (logic sound, needs extraction)

### High Risk Elements (Rebuild)
- Boolean clipping (current implementation scattered)
- Transform normalization (mixed with conversion logic)
- Policy decisions (currently implicit throughout codebase)

## Recommendation: **Proceed with Clean Slate Architecture**

The analysis confirms your architecture addresses the root causes of the current technical debt:

1. **Separation of Concerns**: Preprocessors handle SVG weirdness, mappers handle DML generation
2. **Reuse Without Debt**: Adapters let us keep proven logic without importing coupling
3. **Clear Migration Path**: Can implement incrementally while maintaining functionality
4. **Quality Gates**: Golden tests + A/B comparison ensure no regression

Your approach transforms the current "133 suspicious files" problem into a clean, maintainable architecture while preserving the valuable 60-70% of battle-tested logic.

The text converter fixes you documented would be implemented cleanly in the `pre/text_layout_prep.py` and `map/text_mapper.py` components, solving the alignment and styling issues definitively.

**Start with IR + basic Path pipeline to prove the concept, then migrate text with your fixes applied.**