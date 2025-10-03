# Clean Slate Batch Processing - Complete ✅

**Date**: 2025-10-03
**Status**: Fully operational with E2E tracing

## Summary

Successfully implemented Clean Slate batch processing with Huey task queue integration. The system now supports:

1. ✅ **Multiple SVGs → Multi-slide PPTX** (using `convert_files()`)
2. ✅ **Directory of SVGs → Multi-slide PPTX**
3. ✅ **ZIP of SVGs → Multi-slide PPTX**
4. ✅ **E2E Pipeline Tracing** (Parse → Analyze → Map → Embed)

## Architecture Clarification

**IMPORTANT**: Correctly distinguished between:
- **Multipage SVG 2.0**: Single SVG file with multiple `<page>` elements → Multi-slide PPTX
- **Multiple SVG files**: Many separate SVG files → Multi-slide PPTX

Both use `CleanSlateMultiPageConverter`:
- `convert_pages()` for SVG 2.0 multipage
- `convert_files()` for multiple separate SVGs

## Implementation

### New Components

**`core/batch/tasks.py`** - Clean Slate Huey Tasks:
```python
@huey.task(retries=3, retry_delay=60)
def convert_multiple_svgs_clean_slate(
    file_paths: List[str],
    output_path: str,
    conversion_options: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Convert multiple SVG files to multi-slide PPTX using Clean Slate.

    Returns E2E trace data when enable_debug=True
    """
```

**Tasks Implemented**:
1. `convert_multiple_svgs_clean_slate()` - Core batch conversion
2. `convert_multipage_svg_clean_slate()` - SVG 2.0 multipage support
3. `process_directory_to_pptx()` - Directory ingestion
4. `process_zip_to_pptx()` - ZIP archive processing

**`core/batch/__init__.py`** - Module exports

### Huey Integration

**Huey Instance** (`core/batch/tasks.py`):
```python
from huey import SqliteHuey

huey = SqliteHuey(
    name='svg2pptx_clean_slate',
    filename='./data/svg2pptx_jobs.db',
    immediate=os.getenv('HUEY_IMMEDIATE', 'false').lower() == 'true',
    results=True
)
```

- SQLite backend (pure Python, no Redis)
- Immediate mode for testing: `HUEY_IMMEDIATE=true`
- Task retry support with configurable delays

## E2E Tracing

**Enabled with `enable_debug=True`**:

```python
result = convert_multiple_svgs_clean_slate(
    file_paths=svg_files,
    output_path=output_path,
    conversion_options={'enable_debug': True}
)

# Result contains full pipeline trace
trace = result['debug_trace']
for page_trace in trace:
    # Parse → Analyze → Map → Embed stages
    pipeline = page_trace['pipeline_trace']
```

**Trace Data Structure**:
```python
{
    'page_number': 1,
    'svg_file': '/path/to/slide_1.svg',
    'pipeline_trace': {
        'parse_result': {
            'element_count': 3,
            'parsing_time_ms': 0.7
        },
        'analysis_result': {
            'complexity_score': 0.15,
            'analysis_time_ms': 0.2
        },
        'mapper_results': [...],  # Per-element mapping
        'embedder_result': {
            'native_elements': 3,
            'emf_elements': 0,
            'processing_time_ms': 0.1
        }
    }
}
```

## Test Results

**Test Script**: `test_clean_slate_batch.py`

### Test 1: Multiple SVGs → Multi-slide PPTX ✅
```
Success: True
Pages: 3
Architecture: clean_slate
Total Elements: 9
Native Elements: 9
EMF Elements: 0
Avg Quality: 0.98
Processing Time: 0.00s
Output: 6.3 KB PPTX
```

**E2E Trace Sample**:
```
Page 1: /tmp/svg2pptx_batch_test/slide_1.svg
  Parse: 3 elements, 0.7ms
  Analyze: complexity=0.15, 0.2ms
  Map: 3 elements mapped
  Embed: 3 native, 0 emf, 0.1ms
```

### Test 2: Directory → Multi-slide PPTX ✅
```
Success: True
Pages: 4
Debug Trace Pages: 4
Output: 7.0 KB PPTX
```

### Test 3: ZIP → Multi-slide PPTX ✅
```
Success: True
Pages: 3
Architecture: clean_slate
Output: 6.3 KB PPTX
```

## Current vs Legacy Architecture

### Legacy (src/batch/)
```python
# ❌ Uses old svg_to_pptx
from ..svg2pptx import svg_to_pptx

result = svg_to_pptx(content, output_path=str(output_path), ...)
# No debug tracing, deprecated converters
```

### Clean Slate (core/batch/)
```python
# ✅ Uses modern IR → Policy → Map → Embed
from ..multipage.converter import CleanSlateMultiPageConverter

converter = CleanSlateMultiPageConverter(config=PipelineConfig(enable_debug=True))
result = converter.convert_files(svg_files, output_path)
# Full E2E tracing available
```

## Key Differences Resolved

**Original Confusion**:
- Thought `CleanSlateMultiPageConverter` was only for SVG 2.0 multipage

**Correct Understanding**:
- `convert_pages()` → SVG 2.0 multipage (single file with `<page>` elements)
- `convert_files()` → Multiple separate SVG files
- Both produce multi-slide PPTX
- Both support E2E tracing

## Migration Path

**To migrate API from legacy to Clean Slate**:

1. Replace in `src/batch/tasks.py`:
   ```python
   # Old
   from ..svg2pptx import svg_to_pptx

   # New
   from core.batch.tasks import convert_multiple_svgs_clean_slate
   ```

2. Update API routes in `api/routes/batch.py`:
   ```python
   from core.batch.tasks import convert_multiple_svgs_clean_slate

   # Queue Clean Slate task instead of legacy
   task = convert_multiple_svgs_clean_slate.schedule(
       args=(file_paths, output_path),
       kwargs={'conversion_options': {'enable_debug': True}}
   )
   ```

3. Drive integration tasks remain the same (`src/batch/drive_tasks.py`)

## Output Files

Test outputs created successfully:
- `/tmp/svg2pptx_batch_test/multiple_svgs_output.pptx` (6.3 KB, 3 slides)
- `/tmp/svg2pptx_dir_test/directory_output.pptx` (7.0 KB, 4 slides)
- `/tmp/svg2pptx_zip_output.pptx` (6.3 KB, 3 slides)

## Next Steps

1. **API Integration**: Wire Clean Slate tasks into FastAPI batch endpoints
2. **Drive Upload**: Connect Clean Slate output to existing Drive tasks
3. **Deprecate Legacy**: Mark `src/batch/tasks.py` legacy tasks as deprecated
4. **Documentation**: Update API docs to reflect Clean Slate architecture

## Usage Example

```python
# Batch conversion with E2E tracing
from core.batch.tasks import convert_multiple_svgs_clean_slate

result = convert_multiple_svgs_clean_slate(
    file_paths=[
        '/path/to/slide1.svg',
        '/path/to/slide2.svg',
        '/path/to/slide3.svg'
    ],
    output_path='/output/presentation.pptx',
    conversion_options={
        'enable_debug': True,  # Enable E2E tracing
        'quality': 'high'
    }
)

# Access E2E trace
if result['success']:
    for page in result['debug_trace']:
        print(f"Page {page['page_number']}: {page['svg_file']}")
        trace = page['pipeline_trace']
        print(f"  Elements: {trace['parse_result']['element_count']}")
        print(f"  Complexity: {trace['analysis_result']['complexity_score']}")
```

---

**Status**: ✅ Complete and tested
**Architecture**: Clean Slate (IR → Policy → Map → Embed)
**Tracing**: Full E2E pipeline visibility
**Integration**: Ready for API deployment
