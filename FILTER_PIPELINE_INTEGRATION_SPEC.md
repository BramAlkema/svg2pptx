# Filter Pipeline Integration Specification

**Status**: Design Specification
**Date**: 2025-10-01
**Author**: Architecture Analysis

## Executive Summary

The SVG2PPTX codebase has a **complete filter processing system** (19 filter implementations) but **no pipeline integration**. Filters are detected but silently dropped because:

1. No filter extraction step in pipeline (unlike gradients)
2. No filter field in IR dataclasses
3. No filter application in mappers

This specification defines the integration requirements to connect the existing filter system to the conversion pipeline.

---

## Current State Analysis

### What Exists ✅

**Filter System** (`core/filters/`):
```
blur.py              - feGaussianBlur → DrawingML blur
drop_shadow.py       - feDropShadow → DrawingML shadow
blend.py             - feBlend → DrawingML blending
color_matrix.py      - feColorMatrix → Color transforms
composite.py         - feComposite → Composite operations
component_transfer.py - feComponentTransfer → Channel ops
convolve_matrix.py   - feConvolveMatrix → Matrix convolution
diffuse_lighting.py  - feDiffuseLighting → 3D lighting
specular_lighting.py - feSpecularLighting → Specular effects
displacement_map.py  - feDisplacementMap → Distortion
flood.py             - feFlood → Solid color fill
image.py             - feImage → Image primitives
merge_filter.py      - feMerge → Layer merging
morphology.py        - feMorphology → Erode/dilate
offset.py            - feOffset → Position offset
tile.py              - feTile → Tiling patterns
turbulence.py        - feTurbulence → Noise generation
```

**Filter Service** (`core/services/filter_service.py`):
- `register_filter(filter_id, filter_element)` - Cache filter definitions
- `get_filter_content(filter_id, context)` - Convert to DrawingML
- `process_svg_filters(svg_root)` - Extract from `<defs>`
- FilterFactory integration with policy-driven processing

**Test Coverage**: 330+ tests passing for filter system

### What's Missing ❌

**Pipeline Integration**:
```python
# core/pipeline/converter.py:200
self.services.gradient_service.extract_from_svg(svg_root)  # ✅ Exists
# ❌ MISSING:
self.services.filter_service.extract_from_svg(svg_root)   # Not called
```

**IR Filter Field**:
```python
# core/ir/scene.py:55
@dataclass(frozen=True)
class Path:
    segments: List[SegmentType]
    fill: Paint = None
    stroke: Optional[Stroke] = None
    clip: Optional[ClipRef] = None
    # ❌ MISSING:
    filter: Optional[str] = None  # Filter reference like "url(#blur)"
```

**Parser Extraction**:
```python
# core/parse/parser.py - Path creation
element_id = element.get('id')
# ❌ MISSING:
filter_ref = element.get('filter')  # Not extracted
```

**Mapper Application**:
```python
# core/map/path_mapper.py - DrawingML generation
# ❌ MISSING:
if element.filter:
    filter_xml = self.services.filter_service.get_filter_content(element.filter)
    # Apply to shape
```

---

## Integration Architecture

### Phase 1: Pipeline Extraction (Core/pipeline/converter.py)

**Objective**: Extract filter definitions during pipeline initialization

**Location**: `core/pipeline/converter.py:200`

**Changes Required**:
```python
# Stage 1.5: Extract definitions from <defs>
self.services.gradient_service.extract_from_svg(parse_result.svg_root)
self.services.pattern_service.extract_from_svg(parse_result.svg_root)

# NEW: Extract filter definitions
self.services.filter_service.process_svg_filters(parse_result.svg_root)
```

**Implementation**:
```python
def convert_string(self, svg_content: str) -> ConversionResult:
    # ... existing parsing ...

    # Stage 1.5: Extract definitions from <defs>
    try:
        # Extract gradients (existing)
        self.services.gradient_service.extract_from_svg(parse_result.svg_root)

        # Extract patterns (existing)
        self.services.pattern_service.extract_from_svg(parse_result.svg_root)

        # NEW: Extract filters
        self.services.filter_service.process_svg_filters(parse_result.svg_root)

        self.logger.debug(
            f"Extracted definitions: "
            f"gradients={len(self.services.gradient_service._gradient_cache)}, "
            f"patterns={len(self.services.pattern_service._pattern_cache)}, "
            f"filters={len(self.services.filter_service._filter_cache)}"
        )
    except Exception as e:
        self.logger.warning(f"Definition extraction failed: {e}")
        # Non-fatal - continue with conversion

    # ... continue with analysis ...
```

**Trace Impact**:
- Tracer will show filter definitions registered
- Enables downstream filter resolution

---

### Phase 2: IR Filter References (Core/ir/scene.py)

**Objective**: Add filter field to IR elements

**Location**: `core/ir/scene.py`

**Changes Required**:

#### 2.1 Path Filter Field
```python
@dataclass(frozen=True)
class Path:
    """Canonical path representation"""
    segments: List[SegmentType]
    fill: Paint = None
    stroke: Optional[Stroke] = None
    clip: Optional[ClipRef] = None
    opacity: float = 1.0
    transform: Optional[np.ndarray] = None
    hyperlink: Optional['HyperlinkSpec'] = None
    navigation: Optional['NavigationSpec'] = None
    id: Optional[str] = None
    # NEW: Filter reference
    filter: Optional[str] = None  # e.g., "url(#blur)" or "#blur"
```

#### 2.2 Group Filter Field
```python
@dataclass(frozen=True)
class Group:
    """Container for nested elements"""
    children: List[Union['Path', 'TextFrame', 'Group', 'Image']]
    clip: Optional[ClipRef] = None
    opacity: float = 1.0
    transform: Optional[np.ndarray] = None
    hyperlink: Optional['HyperlinkSpec'] = None
    navigation: Optional['NavigationSpec'] = None
    id: Optional[str] = None
    # NEW: Filter reference (applies to entire group)
    filter: Optional[str] = None
```

#### 2.3 Image Filter Field
```python
@dataclass(frozen=True)
class Image:
    """Raster image element"""
    origin: Point
    size: Rect
    data: bytes
    format: Literal["png", "jpg", "gif", "svg"]
    href: Optional[str] = None
    clip: Optional[ClipRef] = None
    opacity: float = 1.0
    transform: Optional[np.ndarray] = None
    hyperlink: Optional['HyperlinkSpec'] = None
    navigation: Optional['NavigationSpec'] = None
    # NEW: Filter reference
    filter: Optional[str] = None
```

#### 2.4 TextFrame Filter Field (Optional)
```python
@dataclass(frozen=True)
class TextFrame:
    """Text element with resolved positioning and styling"""
    origin: Point
    runs: List[Run]
    anchor: TextAnchor
    bbox: Rect
    line_height: Optional[float] = None
    baseline_shift: float = 0.0
    hyperlink: Optional['HyperlinkSpec'] = None
    navigation: Optional['NavigationSpec'] = None
    id: Optional[str] = None
    # NEW: Filter reference (for text effects)
    filter: Optional[str] = None
```

**Backward Compatibility**: All filter fields are `Optional[str] = None`, maintaining compatibility with existing code.

---

### Phase 3: Parser Filter Extraction (Core/parse/parser.py)

**Objective**: Extract filter attributes when creating IR elements

**Location**: `core/parse/parser.py`

**Pattern**: Apply to all IR element creation sites (Path, Group, Image, TextFrame)

#### 3.1 Path Filter Extraction

**Locations**: Search for `return Path(` (4 occurrences)

**Implementation**:
```python
def _parse_rect_to_path(self, element: ET.Element) -> Optional[Path]:
    """Convert rect element to Path IR"""
    # ... existing coordinate/style parsing ...

    # Get hyperlink from current context if any
    hyperlink = getattr(self, '_current_hyperlink', None)

    # Get element ID for tracing
    element_id = element.get('id')

    # NEW: Get filter reference
    filter_ref = element.get('filter')

    return Path(
        segments=segments,
        fill=fill,
        stroke=stroke,
        opacity=opacity,
        hyperlink=hyperlink,
        id=element_id,
        filter=filter_ref  # NEW
    )
```

**Apply same pattern to**:
- `_parse_circle_to_path()` - Circle elements
- `_parse_ellipse_to_path()` - Ellipse elements
- `_parse_path_element()` - Path elements
- `_parse_polygon_to_path()` - Polygon elements
- `_parse_polyline_to_path()` - Polyline elements
- `_parse_line_to_path()` - Line elements

#### 3.2 Group Filter Extraction

**Locations**: Search for `return Group(` (3 occurrences)

**Implementation**:
```python
def _parse_group(self, element: ET.Element) -> Optional[Group]:
    """Parse SVG group element"""
    # ... existing child parsing ...

    # Get hyperlink from current context if any
    hyperlink = getattr(self, '_current_hyperlink', None)

    # Get element ID for tracing
    element_id = element.get('id')

    # NEW: Get filter reference
    filter_ref = element.get('filter')

    return Group(
        children=child_nodes,
        opacity=float(element.get('opacity', 1.0)),
        hyperlink=hyperlink,
        id=element_id,
        filter=filter_ref  # NEW
    )
```

#### 3.3 Image Filter Extraction

**Locations**: Search for `return Image(` in image parsing

**Implementation**:
```python
def _parse_image(self, element: ET.Element) -> Optional[Image]:
    """Parse SVG image element"""
    # ... existing image data parsing ...

    # NEW: Get filter reference
    filter_ref = element.get('filter')

    return Image(
        origin=origin,
        size=size,
        data=image_data,
        format=image_format,
        href=href,
        opacity=opacity,
        filter=filter_ref  # NEW
    )
```

#### 3.4 TextFrame Filter Extraction

**Locations**: Search for `return TextFrame(` (2 occurrences)

**Implementation**:
```python
def _parse_text(self, element: ET.Element) -> Optional[TextFrame]:
    """Parse SVG text element"""
    # ... existing text parsing ...

    # Get hyperlink from current context if any
    hyperlink = getattr(self, '_current_hyperlink', None)

    # Get element ID for tracing
    element_id = element.get('id')

    # NEW: Get filter reference
    filter_ref = element.get('filter')

    return TextFrame(
        origin=position,
        runs=line.runs,
        bbox=Rect(x, y, estimated_width, estimated_height),
        anchor=line.anchor,
        hyperlink=hyperlink,
        id=element_id,
        filter=filter_ref  # NEW
    )
```

**Tracer Impact**:
- `has_filter_metadata` will now be `true` for filtered elements
- Filter references preserved through IR stage

---

### Phase 4: Mapper Filter Application

**Objective**: Apply filters when generating DrawingML

**Location**: All mappers (`core/map/*.py`)

#### 4.1 PathMapper Filter Application

**File**: `core/map/path_mapper.py`

**Location**: `_map_to_drawingml()` method

**Implementation**:
```python
def _map_to_drawingml(self, element: Path, decision: PathDecision) -> MapperResult:
    """Map path to native DrawingML format"""
    try:
        # Generate base shape XML
        shape_xml = self._generate_path_xml(element)

        # NEW: Apply filter effects if present
        if element.filter and self.services.filter_service:
            filter_xml = self._apply_filter_effects(element.filter, shape_xml)
            if filter_xml:
                shape_xml = filter_xml
                self.logger.debug(f"Applied filter {element.filter} to path {element.id}")

        return MapperResult(
            element=element,
            output_format=OutputFormat.NATIVE_DML,
            xml_content=shape_xml,
            # ... existing fields ...
        )
    except Exception as e:
        raise MappingError(f"Failed to map path: {e}", element, e)

def _apply_filter_effects(self, filter_ref: str, base_xml: str) -> Optional[str]:
    """
    Apply filter effects to shape XML.

    Args:
        filter_ref: Filter reference like "url(#blur)" or "#blur"
        base_xml: Base shape XML to enhance

    Returns:
        Enhanced XML with filter effects, or None if filter not found
    """
    try:
        # Get filter DrawingML from service
        filter_content = self.services.filter_service.get_filter_content(
            filter_ref, context=None
        )

        if not filter_content:
            self.logger.warning(f"Filter not found: {filter_ref}")
            return None

        # Inject filter effects into shape XML
        # Strategy: Insert <a:effectLst> before closing </p:spPr>
        if '<a:effectLst>' in filter_content:
            # Find insertion point
            insertion_point = base_xml.rfind('</p:spPr>')
            if insertion_point != -1:
                enhanced_xml = (
                    base_xml[:insertion_point] +
                    filter_content +
                    '\n' +
                    base_xml[insertion_point:]
                )
                return enhanced_xml

        return None

    except Exception as e:
        self.logger.error(f"Filter application failed for {filter_ref}: {e}")
        return None
```

#### 4.2 TextMapper Filter Application

**File**: `core/map/text_mapper.py`

**Location**: `_map_to_drawingml()` method

**Implementation**:
```python
def _map_to_drawingml(self, element, decision: TextDecision) -> MapperResult:
    """Map text to native DrawingML format with all fixes applied"""
    try:
        # ... existing text XML generation ...

        # NEW: Apply filter effects if present
        if hasattr(element, 'filter') and element.filter and self.services:
            filter_service = getattr(self.services, 'filter_service', None)
            if filter_service:
                filter_xml = self._apply_text_filter_effects(element.filter, xml_content)
                if filter_xml:
                    xml_content = filter_xml
                    self.logger.debug(f"Applied filter {element.filter} to text {element.id}")

        return MapperResult(
            # ... existing result ...
        )
    except Exception as e:
        raise MappingError(f"Failed to generate DrawingML for text: {e}", element, e)

def _apply_text_filter_effects(self, filter_ref: str, base_xml: str) -> Optional[str]:
    """Apply filter effects to text shape XML"""
    # Similar implementation to PathMapper._apply_filter_effects()
    # Adapted for text shape structure
    pass
```

#### 4.3 GroupMapper Filter Application

**File**: `core/map/group_mapper.py`

**Implementation**:
```python
def _map_to_drawingml(self, element: Group, decision: GroupDecision) -> MapperResult:
    """Map group to DrawingML"""
    try:
        # Map child elements first
        child_results = [self._map_child(child) for child in element.children]

        # Generate group container XML
        group_xml = self._generate_group_xml(child_results)

        # NEW: Apply group-level filter if present
        if element.filter and self.services.filter_service:
            filter_xml = self._apply_group_filter(element.filter, group_xml)
            if filter_xml:
                group_xml = filter_xml
                self.logger.debug(f"Applied filter {element.filter} to group {element.id}")

        return MapperResult(
            # ... existing result ...
        )
    except Exception as e:
        raise MappingError(f"Failed to map group: {e}", element, e)
```

#### 4.4 ImageMapper Filter Application

**File**: `core/map/image_mapper.py`

**Implementation**: Similar pattern to PathMapper

**Note**: Image filters may require EMF rasterization for complex effects

---

### Phase 5: Policy Integration

**Objective**: Let policy engine decide filter processing strategy

**Location**: `core/policy/engine.py`

**New Decision Class**:
```python
@dataclass
class FilterDecision:
    """Policy decision for filter processing"""
    use_native: bool = True              # Use DrawingML effects
    use_emf_fallback: bool = False       # Rasterize complex filters
    filter_type: str = "unknown"         # Filter primitive type
    complexity_score: int = 0            # Filter complexity
    estimated_quality: float = 0.95      # Expected quality
    estimated_performance: float = 0.90  # Expected performance
    reason: str = ""                     # Decision rationale
```

**New Policy Method**:
```python
def decide_filter(self, filter_ref: str, element: IRElement) -> FilterDecision:
    """
    Decide filter processing strategy.

    Args:
        filter_ref: Filter reference like "url(#blur)"
        element: IR element with filter

    Returns:
        FilterDecision with processing strategy
    """
    # Simple filters → Native DrawingML
    simple_filters = {'feGaussianBlur', 'feDropShadow', 'feOffset', 'feFlood'}

    # Complex filters → May need EMF
    complex_filters = {
        'feConvolveMatrix', 'feTurbulence', 'feDisplacementMap',
        'feComponentTransfer', 'feMorphology'
    }

    # Check filter complexity
    complexity = self._calculate_filter_complexity(filter_ref)

    if complexity <= 3:
        # Simple filter - use native
        return FilterDecision(
            use_native=True,
            use_emf_fallback=False,
            complexity_score=complexity,
            estimated_quality=0.95,
            estimated_performance=0.95,
            reason="Simple filter supports native DrawingML"
        )
    else:
        # Complex filter - may need EMF
        return FilterDecision(
            use_native=False,
            use_emf_fallback=True,
            complexity_score=complexity,
            estimated_quality=0.98,  # EMF preserves full fidelity
            estimated_performance=0.80,  # Slower than native
            reason="Complex filter requires EMF rasterization"
        )
```

---

## Implementation Order

### Priority 1: Core Integration (Required)
1. **Phase 1**: Pipeline extraction - Add filter extraction call
2. **Phase 2**: IR filter fields - Add optional filter field to dataclasses
3. **Phase 3**: Parser extraction - Extract filter attributes

**Validation**: After Phase 1-3, tracer should show:
- `has_filter_metadata: true`
- Filter references in IR elements
- No filters applied yet (mappers not updated)

### Priority 2: Basic Filter Application (MVP)
4. **Phase 4.1**: PathMapper filter application
5. **Phase 4.2**: TextMapper filter application (optional)

**Validation**: Filters should appear in generated DrawingML

### Priority 3: Advanced Features (Enhancement)
6. **Phase 4.3**: GroupMapper filter application
7. **Phase 4.4**: ImageMapper filter application
8. **Phase 5**: Policy-driven filter decisions

---

## Testing Strategy

### Unit Tests

**Test Filter Extraction**:
```python
def test_filter_extraction_in_pipeline():
    """Test that filters are extracted from SVG defs"""
    svg = '''<svg>
        <defs>
            <filter id="blur">
                <feGaussianBlur stdDeviation="2"/>
            </filter>
        </defs>
        <rect filter="url(#blur)"/>
    </svg>'''

    converter = CleanSlateConverter()
    result = converter.convert_string(svg)

    # Verify filter was extracted
    assert 'blur' in converter.services.filter_service._filter_cache
```

**Test IR Filter Field**:
```python
def test_ir_path_has_filter_field():
    """Test that Path IR element preserves filter reference"""
    parser = SVGParser()
    svg = '<svg><rect id="r1" filter="url(#blur)"/></svg>'

    result = parser.parse(svg)
    scene = result.scene

    assert len(scene) == 1
    path = scene[0]
    assert isinstance(path, Path)
    assert path.filter == "url(#blur)"
```

**Test Filter Application**:
```python
def test_mapper_applies_filter():
    """Test that mapper generates filter DrawingML"""
    services = ConversionServices.create_default()
    policy = PolicyEngine()

    # Register filter
    filter_def = ET.fromstring('<filter id="blur"><feGaussianBlur stdDeviation="2"/></filter>')
    services.filter_service.register_filter('blur', filter_def)

    # Create filtered path
    path = Path(
        segments=[...],
        filter="url(#blur)"
    )

    # Map with filter
    mapper = PathMapper(policy, services=services)
    result = mapper.map(path)

    # Verify filter in output
    assert '<a:blur' in result.xml_content
```

### Integration Tests

**Test E2E Filter Flow**:
```python
def test_e2e_blur_filter():
    """Test complete blur filter pipeline"""
    svg = '''<svg>
        <defs>
            <filter id="blur">
                <feGaussianBlur stdDeviation="3"/>
            </filter>
        </defs>
        <rect x="10" y="10" width="100" height="50"
              fill="red" filter="url(#blur)"/>
    </svg>'''

    converter = CleanSlateConverter()
    result = converter.convert_string(svg)

    # Verify PPTX contains blur effect
    pptx = zipfile.ZipFile(io.BytesIO(result.output_data))
    slide_xml = pptx.read('ppt/slides/slide1.xml').decode('utf-8')

    assert '<a:effectLst>' in slide_xml
    assert '<a:blur' in slide_xml
```

### Tracer Validation

**Expected Trace After Integration**:
```json
{
  "element_id": "rect1",
  "svg_tag": "rect",
  "filter_ids": ["blur"],
  "pipeline_compliant": true,
  "stages": {
    "parse": {
      "filter_detected": true,
      "filter_ref": "url(#blur)"
    },
    "ir": {
      "has_filter_metadata": true,
      "filter": "url(#blur)"
    },
    "map": {
      "filters_applied": ["blur"],
      "filter_strategy": "native_drawingml"
    },
    "embed": {
      "filter_effects_present": true
    }
  }
}
```

---

## Migration Notes

### Backward Compatibility

**Safe Changes**:
- All filter fields are `Optional[str] = None`
- Existing code without filters continues to work
- No breaking changes to existing IR element creation

**Gradual Rollout**:
1. Phase 1-3: Filters preserved but not applied (no visual changes)
2. Phase 4: Filters begin appearing in output (visual enhancements)
3. Phase 5: Policy-driven optimization (quality improvements)

### Performance Considerations

**Filter Processing Overhead**:
- Filter extraction: ~0.5-1ms per filter definition
- Filter application: ~0.1-0.5ms per filtered element
- Complex filters (EMF): ~10-50ms per element

**Caching**:
- FilterService already caches filter definitions
- FilterService caches DrawingML conversions
- No additional caching needed

### Known Limitations

**DrawingML Filter Coverage**:
- ✅ Full support: blur, drop shadow, offset, flood
- ⚠️ Partial support: blend, composite, color matrix
- ❌ Limited support: turbulence, displacement map, convolve matrix

**EMF Fallback Strategy**:
- Complex filters may need rasterization
- Policy engine decides fallback on per-filter basis
- Quality vs. performance tradeoff

---

## Success Criteria

### Definition of Done

1. **Extraction**: `filter_service.process_svg_filters()` called in pipeline ✓
2. **IR Fields**: All IR elements have `filter: Optional[str]` field ✓
3. **Parser**: All element creation sites extract `filter` attribute ✓
4. **Mappers**: PathMapper and TextMapper apply filters ✓
5. **Tests**: Unit and integration tests pass ✓
6. **Tracer**: Element tracer shows filter flow end-to-end ✓

### Validation Metrics

**Before Integration**:
- Filtered elements: 0% render with effects
- Tracer shows: `has_filter_metadata: false`
- User experience: Silent filter loss

**After Integration**:
- Filtered elements: 90%+ render with effects
- Tracer shows: Complete filter pipeline flow
- User experience: Visual fidelity matches SVG source

---

## Appendix: Filter Coverage Matrix

| SVG Filter Primitive | DrawingML Equivalent | Support Level | Strategy |
|---------------------|---------------------|---------------|----------|
| feGaussianBlur | `<a:blur>` | ✅ Full | Native |
| feDropShadow | `<a:outerShdw>` | ✅ Full | Native |
| feOffset | Position transform | ✅ Full | Native |
| feFlood | `<a:solidFill>` | ✅ Full | Native |
| feBlend | Blend modes | ⚠️ Partial | Native |
| feColorMatrix | Color transforms | ⚠️ Partial | Native |
| feComposite | Composite ops | ⚠️ Partial | Native |
| feDiffuseLighting | `<a:sp3d>` | ⚠️ Partial | Native |
| feSpecularLighting | `<a:sp3d>` | ⚠️ Partial | Native |
| feComponentTransfer | Channel ops | ❌ Limited | EMF |
| feConvolveMatrix | Matrix ops | ❌ Limited | EMF |
| feDisplacementMap | Distortion | ❌ Limited | EMF |
| feMorphology | Erode/dilate | ❌ Limited | EMF |
| feTile | Tiling | ❌ Limited | EMF |
| feTurbulence | Noise | ❌ Limited | EMF |
| feImage | Image primitive | ⚠️ Partial | Native |
| feMerge | Layer merge | ⚠️ Partial | Native |

**Legend**:
- ✅ Full: Direct DrawingML equivalent exists
- ⚠️ Partial: Approximate DrawingML rendering possible
- ❌ Limited: Requires EMF rasterization for full fidelity

---

## References

- **Filter System Tests**: `tests/unit/filters/` (330+ tests)
- **Filter Service**: `core/services/filter_service.py`
- **Filter Implementations**: `core/filters/*.py` (19 filters)
- **Element Tracer**: `core/debug/tracer.py`
- **Pipeline Converter**: `core/pipeline/converter.py`
