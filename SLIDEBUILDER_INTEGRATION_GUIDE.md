# SlideBuilder MediaRequest Integration Guide

**Date**: 2025-10-02
**Task**: 4.1 - Update SlideBuilder to Process MediaRequests
**Status**: 📋 IMPLEMENTATION GUIDE
**Context**: Session continuation with ImageMapper complete

---

## Current Architecture

### SlideBuilder Flow

```
Scene/Elements
  ↓
SlideBuilder.build_slide()
  ↓
_map_scene_elements() → List[MapperResult]
  ↓
embedder.embed_scene(scene, mapper_results) → EmbedderResult
  ↓
Result with slide_xml
```

### Key Files

1. **`core/io/slide_builder.py`** - Main slide builder (enhanced version)
2. **`core/io/embedder.py`** - DrawingMLEmbedder handles final assembly
3. **`core/io/package_writer.py`** - Writes files to PPTX package

---

## Integration Requirements

### 1. Add MediaRequest Processing to Embedder

**File**: `core/io/embedder.py`

The `embed_scene()` method receives `List[MapperResult]`, which now includes `media_requests` field.

**Required Changes**:

```python
from .relationship_manager import RelationshipManager
from .content_types import ContentTypesManager

class DrawingMLEmbedder:
    def __init__(self, ..., package_writer=None, content_types=None):
        # ... existing init ...
        self.package_writer = package_writer
        self.content_types = content_types or ContentTypesManager()

    def embed_scene(self, scene: SceneGraph, mapper_results: List[MapperResult]) -> EmbedderResult:
        # Initialize relationship manager for this slide
        rels = RelationshipManager(start_id=1)

        # Add slide layout relationship (required)
        layout_rid = rels.add_slide_layout()

        # Build slide XML skeleton
        slide_elem = self._create_slide_skeleton(layout_rid)
        sp_tree = slide_elem.find(".//p:spTree", NSMAP)

        # Process each mapper result
        for mr in mapper_results:
            # Parse XML content if string
            if isinstance(mr.xml_content, str):
                shape_elem = ET.fromstring(mr.xml_content)
            else:
                shape_elem = mr.xml_content

            # Add shape to slide
            sp_tree.append(shape_elem)

            # Process media requests
            if mr.media_requests:
                for media_req in mr.media_requests:
                    self._process_media_request(media_req, rels, shape_elem)

        # Convert to XML string
        slide_xml = ET.tostring(slide_elem, encoding='unicode')

        # Generate relationships XML
        rels_xml = rels.to_xml_bytes()

        return EmbedderResult(
            slide_xml=slide_xml,
            relationships_xml=rels_xml,
            media_files=[...]  # List of written files
        )
```

### 2. Implement Media Request Processing

**Add method to `DrawingMLEmbedder`**:

```python
def _process_media_request(
    self,
    media_req: MediaRequest,
    rels: RelationshipManager,
    shape_elem: Element
) -> None:
    """
    Process a single media request.

    Args:
        media_req: MediaRequest with file data and binding info
        rels: RelationshipManager for rId allocation
        shape_elem: XML element to patch
    """
    # 1. Write media file
    media_path = f"ppt/media/{media_req.filename}"
    if self.package_writer:
        self.package_writer.write_file(media_path, media_req.bytes_data)

    # 2. Register content type
    if self.content_types:
        self.content_types.ensure_image_type(media_req.content_type_ext)

    # 3. Add relationship
    rel_target = f"../media/{media_req.filename}"
    rid = rels.add_image(rel_target)

    # 4. Patch r:embed in XML element
    self._patch_relationship(shape_elem, media_req.bind_xpath, media_req.bind_attr, rid)
```

### 3. Implement XPath Patching

**Add method to `DrawingMLEmbedder`**:

```python
def _patch_relationship(
    self,
    elem: Element,
    xpath: str,
    attr: str,
    rid: str
) -> None:
    """
    Patch relationship attribute via XPath.

    Args:
        elem: Root element to search
        xpath: XPath to target element
        attr: Attribute to set (with namespace)
        rid: Relationship ID value
    """
    # Define namespaces for XPath
    nsmap = {
        'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
        'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
        'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
    }

    # Find target elements
    targets = elem.xpath(xpath, namespaces=nsmap)

    if targets:
        # Patch first match
        targets[0].set(attr, rid)
    else:
        logger.warning(f"Could not find element at {xpath} to patch relationship")
```

### 4. Update SlideBuilder to Pass Package Writer

**File**: `core/io/slide_builder.py`

```python
class SlideBuilder:
    def __init__(
        self,
        mappers: Dict[str, Any],
        embedder: DrawingMLEmbedder,
        policy: Policy,
        package_writer: Optional[PackageWriter] = None,  # ADD
        validate_schema: bool = False,
        schema_path: Optional[str] = None
    ):
        # ... existing init ...
        self.package_writer = package_writer

        # Ensure embedder has package_writer
        if package_writer and not embedder.package_writer:
            embedder.package_writer = package_writer
```

### 5. Update EmbedderResult

**File**: `core/io/embedder.py`

```python
@dataclass
class EmbedderResult:
    slide_xml: str
    relationships_xml: bytes = None  # ADD: Relationships XML
    media_files: List[str] = field(default_factory=list)  # Paths written
    # ... existing fields ...
```

---

## Implementation Steps

### Step 1: Import Managers (5 min)

```python
# In core/io/embedder.py
from .relationship_manager import RelationshipManager
from .content_types import ContentTypesManager
from ..map.base import MediaRequest
```

### Step 2: Update EmbedderResult (5 min)

Add `relationships_xml` field to hold the generated relationships.

### Step 3: Update Embedder.__init__() (10 min)

Add `package_writer` and `content_types` parameters.

### Step 4: Implement _process_media_request() (30 min)

Following the pseudocode above.

### Step 5: Implement _patch_relationship() (20 min)

XPath-based attribute patching.

### Step 6: Update embed_scene() (40 min)

- Initialize RelationshipManager
- Process media_requests
- Return relationships_xml

### Step 7: Update SlideBuilder (15 min)

Pass package_writer to embedder.

### Step 8: Testing (30 min)

Create integration test with actual Image mapping.

**Total Estimated Time**: ~2.5 hours

---

## Testing Plan

### Unit Test: Media Request Processing

```python
def test_process_media_request():
    # Create mock package writer
    package_writer = Mock()
    content_types = ContentTypesManager()

    embedder = DrawingMLEmbedder(package_writer=package_writer,
                                  content_types=content_types)

    # Create media request
    media_req = MediaRequest(
        filename="image1.png",
        mime_type="image/png",
        bytes_data=b"fake image data",
        content_type_ext="png",
        bind_xpath=".//a:blip",
        bind_attr="{...}embed"
    )

    # Create shape element with blip
    shape_elem = ET.fromstring("""
        <p:pic xmlns:p="..." xmlns:a="...">
            <p:blipFill>
                <a:blip/>
            </p:blipFill>
        </p:pic>
    """)

    rels = RelationshipManager()
    embedder._process_media_request(media_req, rels, shape_elem)

    # Verify
    assert package_writer.write_file.called
    assert len(rels.relationships) == 1

    # Check r:embed patched
    blip = shape_elem.find(".//a:blip", NSMAP)
    assert blip.get("{...}embed") == "rId1"
```

### Integration Test: Full Pipeline

```python
def test_image_embedding_pipeline():
    # Create Image IR
    image = Image(
        href="data:...",
        source_type="data_url",
        mime_type="image/png",
        format_ext="png",
        x=100, y=200, width=300, height=400,
        image_data=b"PNG data..."
    )

    # Map with ImageMapper
    mapper = ImageMapper(policy)
    result = mapper.map(image)

    # Embed with Embedder
    embedder = DrawingMLEmbedder(package_writer=writer)
    embed_result = embedder.embed_scene(scene, [result])

    # Verify slide XML
    assert "<p:pic>" in embed_result.slide_xml
    assert "<a:blip" in embed_result.slide_xml
    assert 'r:embed="rId' in embed_result.slide_xml

    # Verify relationships XML
    assert embed_result.relationships_xml
    assert b"<Relationship" in embed_result.relationships_xml
    assert b'Type="...image"' in embed_result.relationships_xml

    # Verify media file written
    assert writer.write_file.called_with("ppt/media/image1.png", b"PNG data...")
```

---

## Alternative: Minimal Integration

If full embedder rewrite is complex, add post-processing:

```python
class SlideBuilder:
    def build_slide(self, scene, metadata=None):
        # ... existing code ...

        # Map scene elements
        mapper_results = self._map_scene_elements(scene, ...)

        # Process media requests BEFORE embedding
        media_files, rels_xml = self._process_media_requests(mapper_results)

        # Patch mapper results with rIds
        mapper_results = self._patch_media_rids(mapper_results, rels_xml)

        # Continue with existing embedding
        result = self.embedder.embed_scene(scene, mapper_results)

        # Add relationships and media files to result
        result.relationships_xml = rels_xml
        result.media_files.extend(media_files)

        return result
```

This approach:
- ✅ Minimal changes to embedder
- ✅ Keeps existing logic intact
- ✅ Adds MediaRequest processing as separate step
- ⚠️ Still requires XPath patching

---

## Rollback Plan

If issues arise:

1. **Embedder issues**: Revert embedder changes, keep media processing separate
2. **XPath issues**: Fall back to string replacement temporarily
3. **Package writer issues**: Write media files via alternative method

---

## Success Criteria

✅ **Functional**
- Media files written to ppt/media/
- Relationships XML generated correctly
- r:embed attributes patched via XPath
- Content types registered
- Full pipeline works: Image IR → MapperResult → Slide XML

✅ **Non-Functional**
- No breaking changes to existing slides
- Performance acceptable (<50ms overhead)
- Error handling graceful

✅ **Testing**
- Unit tests for media processing
- Integration test for full pipeline
- Manual PowerPoint validation

---

## Next Developer Actions

1. **Read this guide** - Understand integration points
2. **Choose approach** - Full rewrite or minimal integration
3. **Implement in order** - Follow steps 1-8
4. **Test incrementally** - After each major change
5. **Validate with PowerPoint** - Open generated PPTX files

---

## Files to Modify

1. `core/io/embedder.py` - Add media processing (primary changes)
2. `core/io/slide_builder.py` - Pass package_writer (minor change)
3. `tests/integration/test_image_pipeline.py` - New integration test

**Estimated Lines Changed**: ~150 lines added, ~20 modified

---

**Status**: 📋 **IMPLEMENTATION GUIDE COMPLETE**

**Ready For**: Next developer to implement Task 4.1

**Confidence**: 🌟🌟🌟 **HIGH** - Clear requirements, proven patterns

---

*SlideBuilder Integration Guide - SVG2PPTX v1.0.0*
*Date: 2025-10-02*
