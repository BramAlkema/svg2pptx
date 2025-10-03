# ClipPath Preprocessor Specification

## Current State Analysis

### ✅ What Already Exists
- **MaskingConverter** in `src/converters/masking.py` - Complete converter for `<mask>` and `<clipPath>`
- **SVGOptimizer pipeline** in `src/preprocessing/optimizer.py` - Plugin architecture with presets
- **Shape-to-path conversion** via `ConvertShapeToPathPlugin`
- **Path canonicalization** via `ConvertPathDataPlugin` (abs commands, arc→cubic)
- **Transform processing** via `ConvertTransformPlugin`
- **CTM calculation** via `ConversionContext.get_cumulative_transform()`

### 🎯 Strategic Advantage
**Resolve all clipPath → ordinary paths in preprocessor**, so DrawingML converters never see clipping at all.

## Architecture Overview

### Current Flow (Complex)
```
SVG with clip-path → MaskingConverter → PowerPoint clipping hacks → Limited support
```

### Proposed Flow (Clean)
```
SVG with clip-path → ResolveClipPathsPlugin → Pure paths → DrawingMLGenerator → Perfect support
```

## Implementation Strategy

### Phase 1: Boolean Engine Infrastructure (4 hours)
Create pluggable backend system for path boolean operations:

#### A. Core Interface (`src/preprocessing/geometry/path_boolean_engine.py`)
```python
class PathBooleanEngine(Protocol):
    def intersect(self, subject: PathSpec, clips: List[PathSpec]) -> str
    def union(self, paths: List[PathSpec]) -> str
    def difference(self, subject: PathSpec, clips: List[PathSpec]) -> str

PathSpec = Tuple[str, FillRule]  # (svg_d_string, "nonzero"|"evenodd")
```

#### B. Skia PathOps Backend (Preferred - Curve-Faithful)
- **Location**: `src/preprocessing/geometry/backends/pathops_backend.py`
- **Dependency**: `pip install skia-python` (optional)
- **Advantage**: Keeps Bezier curves intact, fastest performance
- **Integration**: Uses adapters to/from existing path system

#### C. PyClipper Fallback Backend (Polygon-Based)
- **Location**: `src/preprocessing/geometry/backends/pyclipper_backend.py`
- **Dependency**: `pip install pyclipper` (fallback)
- **Process**: Flatten curves → integer polygon ops → rebuild SVG paths
- **Advantage**: No external native deps, still all-vector

### Phase 2: Preprocessor Plugin (6 hours)

#### A. ResolveClipPathsPlugin
- **Location**: `src/preprocessing/plugins/resolve_clip_paths.py`
- **Position**: After shape→path, after path canonicalization, before merging
- **Process**:
  1. Find elements with `clip-path="url(#id)"`
  2. Convert element to canonical path (existing converters)
  3. Convert clipPath children to paths with transforms applied
  4. Boolean intersect subject ∩ clip(s)
  5. Replace element with result path, remove `clip-path` attribute

#### B. Enhanced Plugin Order
```python
AGGRESSIVE_PLUGINS = [
    # ... existing plugins ...
    ConvertShapeToPathPlugin,     # rect/circle → path
    ConvertPathDataPlugin,        # abs commands, arc→cubic
    ConvertTransformPlugin,       # normalize transforms
    FlattenTransformsPlugin,      # bake CTM into geometry (if needed)
    ResolveClipPathsPlugin,       # ← NEW: clip-path → boolean intersection
    MergePathsPlugin,            # optional cleanup
]
```

### Phase 3: Adapter Integration (3 hours)

Wire existing systems into new backends via small adapter functions:

#### A. Path System Adapters
- `element_to_abs_path_d(element, context)` - Uses existing shape converters + CTM baking
- `path_bounds(d_string)` - Extract bbox from canonical path
- `map_path_coords(d, sx, sy, tx, ty)` - Scale/translate path coordinates

#### B. Backend-Specific Adapters
**For PathOps**:
- `to_skia_path(d_string, fill_rule)` - Parse SVG → skia.Path with winding rule
- `from_skia_path(skia_path)` - Serialize skia.Path → SVG d-string

**For PyClipper**:
- `flatten_path(d_string, tolerance)` - Curves → polylines (existing flattening)
- `polygons_to_svg_path(polygons)` - Rebuild SVG path from polygon list

## Specification Details

### clipPathUnits Support
- **`userSpaceOnUse`** (default): Use absolute coordinates as-is
- **`objectBoundingBox`**: Map clip children from [0,1] unit box to target element bbox

### Transform Handling
Accumulate transforms in order:
1. **Element cumulative transform** (via existing `get_cumulative_transform()`)
2. **clipPath own transform** attribute (rare but spec-compliant)
3. **Each clip child transform** (applied before bbox mapping)

### Fill Rule Compliance
- **Subject element**: Uses `fill-rule` attribute (nonzero|evenodd)
- **Clip children**: Uses `clip-rule` attribute (inherits from `fill-rule` if unspecified)
- **Boolean ops**: Backend must respect winding rules for both subject and clips

### Multiple Children in clipPath
Per SVG spec: **Union all clip children first**, then intersect with subject:
```
result = subject ∩ (clip_child_1 ∪ clip_child_2 ∪ ... ∪ clip_child_n)
```

### Edge Cases Handled
- **Unknown clip reference**: Remove `clip-path` attribute silently
- **Empty intersection**: Remove element entirely (fully clipped out)
- **Nested clipPath**: Resolve recursively on multiple passes
- **Transform hierarchies**: All CTM calculation via existing services
- **Performance**: Optional caching by `(clip_id, target_bbox_hash)`

## Benefits Over Current MaskingConverter

### 1. **Converter Simplification**
- DrawingML converters only see normal `<path>` elements
- No need for PowerPoint clipping "hacks" or approximations
- Single code path for all geometry

### 2. **Perfect Fidelity**
- Boolean intersection gives mathematically exact results
- No rasterization - stays vector throughout
- Handles complex clip shapes that PowerPoint can't

### 3. **Performance**
- Preprocessing once vs per-element conversion
- Reusable clip definitions cached
- PathOps backend uses hardware-optimized curves

### 4. **Maintainability**
- One source of truth for geometry math
- Standard SVG → standard paths (no special cases)
- Pluggable backends for different accuracy/performance needs

## Integration Points

### Required Adapters (Your Existing Code)
1. **Shape→Path**: `ConvertShapeToPathPlugin` logic extracted to utility
2. **CTM Baking**: `get_cumulative_transform()` + coordinate transformation
3. **Path Parsing**: Existing path command iteration from `drawingml_generator.py`
4. **Bounds Calculation**: Extract from existing geometry systems

### Optional Dependencies
- **skia-python**: For PathOps backend (preferred)
- **pyclipper**: For polygon backend (fallback)
- Both deps are optional with graceful fallbacks

### Configuration Support
```python
# In optimizer config
{
  "plugins": {
    "resolveClipPaths": {
      "enabled": True,
      "backend": "pathops",  # "pathops" | "pyclipper" | "auto"
      "tolerance": 0.25,     # for pyclipper flattening
      "cache": True          # cache clip definitions
    }
  }
}
```

## Testing Strategy

### Unit Tests
- Each backend with simple cases (rect ∩ circle)
- clipPathUnits variations (userSpaceOnUse vs objectBoundingBox)
- Transform combinations (element + clipPath + children)
- Fill rule variations (nonzero vs evenodd)

### Integration Tests
- Full preprocessing pipeline with clipped elements
- Performance benchmarks (large clips, many targets)
- Visual regression tests (SVG reference vs processed result)

### Edge Case Tests
- Nested clipPath references
- Complex transform hierarchies
- Degenerate cases (no intersection, self-intersecting clips)
- Multiple children with different fill rules

## Migration Path

### Phase 1: Add New Infrastructure (No Breaking Changes)
- Add boolean engine and backends
- Add ResolveClipPathsPlugin (disabled by default)
- Add adapter utilities

### Phase 2: Enable in Aggressive Preset
- Test with complex SVG corpus
- Performance validation
- Bug fixes and optimization

### Phase 3: Enable by Default
- Move to default preset once stable
- Deprecate MaskingConverter gradually
- Document migration for custom pipelines

## Success Criteria

1. **Zero DrawingML clipping code**: Converters never see `clip-path` attributes
2. **Perfect visual fidelity**: Boolean intersection matches SVG reference exactly
3. **Performance neutral**: Preprocessing overhead offset by simpler converters
4. **Spec compliance**: Handles all SVG clipPath features correctly
5. **Graceful degradation**: Falls back cleanly when backends unavailable

## Risk Assessment

**Low Risk**: Plugin architecture integration, adapter creation
**Medium Risk**: Backend selection and configuration complexity
**High Risk**: Complex transform math, edge case compatibility

**Mitigation**: Extensive testing with real-world SVG corpus, fallback backends, comprehensive error handling