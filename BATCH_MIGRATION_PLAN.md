# Batch Migration & Integration Plan

**Goal**: Migrate Huey batching to Clean Slate + Add PPTX builder tracing

## Current Architecture

### API Flow (Legacy)
```
POST /batch/jobs (api/routes/batch.py)
  ↓
Creates BatchJob record
  ↓
Calls: coordinate_batch_workflow() [src/batch/drive_tasks.py]
  ↓
Calls: convert_svg_batch() [src/batch/tasks.py]
  ↓
Uses: svg_to_pptx (LEGACY - NO TRACING)
  ↓
Calls: upload_batch_files_to_drive() [src/batch/drive_tasks.py]
```

### Problem
- Legacy `svg_to_pptx` has NO tracing
- NO Clean Slate architecture (IR → Policy → Map → Embed)
- PackageWriter has NO tracing in PPTX assembly

## Target Architecture

### API Flow (Clean Slate)
```
POST /batch/jobs (api/routes/batch.py)
  ↓
Creates BatchJob record
  ↓
Calls: coordinate_batch_workflow_clean_slate() [NEW]
  ↓
Calls: convert_multiple_svgs_clean_slate() [core/batch/tasks.py]
  ↓
Uses: CleanSlateMultiPageConverter (✅ TRACED)
  ↓
Uses: PackageWriter.write_package() (✅ ADD TRACING)
  ↓
Calls: upload_batch_files_to_drive() [src/batch/drive_tasks.py]
  ↓
Returns: Full E2E trace data
```

## Migration Tasks

### 1. Add Tracing to PackageWriter ✨

**File**: `core/io/package_writer.py`

**Add debug collection**:
```python
class PackageWriter:
    def __init__(self, enable_debug: bool = False):
        self.enable_debug = enable_debug
        self._debug_data = {}

    def write_package(self, embedder_results: List[EmbedderResult],
                     output_path: str, manifest: PackageManifest = None) -> Dict[str, Any]:
        start_time = time.perf_counter()

        # Track packaging stages
        if self.enable_debug:
            self._debug_data['packaging_start'] = time.perf_counter()

        # Create package
        package_data = self._create_package_data(embedder_results, manifest)

        if self.enable_debug:
            self._debug_data['package_creation_ms'] = (time.perf_counter() - self._debug_data['packaging_start']) * 1000
            self._debug_data['package_size_bytes'] = len(package_data)
            self._debug_data['slides_count'] = len(embedder_results)

        # Write to file
        self._write_package_file(package_data, output_path)

        if self.enable_debug:
            self._debug_data['file_write_ms'] = (time.perf_counter() - start_time) * 1000 - self._debug_data['package_creation_ms']

        # Return result with debug data
        result = {
            'package_size_bytes': len(package_data),
            'slides_count': len(embedder_results),
            'processing_time_ms': (time.perf_counter() - start_time) * 1000
        }

        if self.enable_debug:
            result['debug_data'] = self._debug_data

        return result
```

**Trace structure**:
```python
{
    'package_creation_ms': 5.2,
    'file_write_ms': 1.3,
    'package_size_bytes': 6432,
    'slides_count': 3,
    'compression_ratio': 0.42,
    'zip_structure': {
        'slides': 3,
        'relationships': 8,
        'media_files': 0,
        'content_types': 12
    }
}
```

### 2. Update MultiPageConverter to Pass Debug Flag

**File**: `core/multipage/converter.py`

```python
def _generate_multipage_package(self, page_results: List[ConversionResult],
                               output_path: str) -> Dict[str, Any]:
    # Pass enable_debug to PackageWriter
    writer = PackageWriter(enable_debug=self.config.enable_debug)

    package_result = writer.write_package(
        embedder_results=[r.embedder_result for r in page_results],
        output_path=output_path
    )

    return package_result
```

### 3. Create Clean Slate Coordinator Task

**File**: `core/batch/coordinator.py` (NEW)

```python
#!/usr/bin/env python3
"""
Clean Slate Batch Coordinator

Coordinates complete batch workflow: conversion + Drive upload.
Integrates Clean Slate tasks with existing Drive infrastructure.
"""

from huey import SqliteHuey
from pathlib import Path
from typing import List, Dict, Any
import logging

from .tasks import convert_multiple_svgs_clean_slate

# Import Drive tasks from legacy (keep using them)
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.batch.drive_tasks import upload_batch_files_to_drive
from src.batch.models import BatchJob, DEFAULT_DB_PATH

logger = logging.getLogger(__name__)

# Use same Huey instance
from .tasks import huey


@huey.task()
def coordinate_batch_workflow_clean_slate(
    job_id: str,
    file_paths: List[str],  # Changed from URLs to file paths
    conversion_options: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Coordinate complete batch workflow using Clean Slate.

    Flow:
    1. Convert multiple SVGs using Clean Slate (with tracing)
    2. Upload to Drive (if enabled)
    3. Return complete trace data
    """
    try:
        logger.info(f"Clean Slate batch workflow for job {job_id}")

        # Get batch job
        batch_job = BatchJob.get_by_id(job_id, DEFAULT_DB_PATH)
        if not batch_job:
            return {
                'success': False,
                'error_message': f'Job {job_id} not found'
            }

        # Update status
        batch_job.status = "processing"
        batch_job.save(DEFAULT_DB_PATH)

        # Step 1: Convert SVGs using Clean Slate
        options = conversion_options or {}
        output_path = f"/tmp/batch_output/{job_id}.pptx"

        conversion_result = convert_multiple_svgs_clean_slate(
            file_paths=file_paths,
            output_path=output_path,
            conversion_options={
                'enable_debug': True,  # Always enable for batch
                'quality': options.get('quality', 'high')
            }
        )

        # Handle Huey Result wrapper
        if hasattr(conversion_result, '__call__'):
            conversion_result = conversion_result()

        if not conversion_result.get('success'):
            batch_job.status = "failed"
            batch_job.save(DEFAULT_DB_PATH)
            return conversion_result

        # Step 2: Upload to Drive if enabled
        if batch_job.drive_integration_enabled:
            batch_job.status = "uploading"
            batch_job.drive_upload_status = "in_progress"
            batch_job.save(DEFAULT_DB_PATH)

            files = [{
                'path': output_path,
                'original_name': f'{job_id}.pptx',
                'converted_name': f'{job_id}.pptx'
            }]

            upload_result = upload_batch_files_to_drive(
                job_id=job_id,
                files=files,
                folder_pattern=batch_job.drive_folder_pattern,
                generate_previews=options.get('generate_previews', True)
            )

            # Handle Huey Result wrapper
            if hasattr(upload_result, '__call__'):
                upload_result = upload_result()

            if upload_result.get('success'):
                batch_job.status = "completed"
                batch_job.drive_upload_status = "completed"
            else:
                batch_job.status = "failed"
                batch_job.drive_upload_status = "failed"

            batch_job.save(DEFAULT_DB_PATH)

            return {
                'success': True,
                'job_id': job_id,
                'conversion': conversion_result,
                'upload': upload_result,
                'architecture': 'clean_slate'
            }
        else:
            # No Drive upload
            batch_job.status = "completed"
            batch_job.save(DEFAULT_DB_PATH)

            return {
                'success': True,
                'job_id': job_id,
                'conversion': conversion_result,
                'architecture': 'clean_slate'
            }

    except Exception as e:
        logger.error(f"Batch workflow error for job {job_id}: {e}")

        if batch_job:
            batch_job.status = "failed"
            batch_job.save(DEFAULT_DB_PATH)

        return {
            'success': False,
            'job_id': job_id,
            'error_message': str(e),
            'architecture': 'clean_slate'
        }
```

### 4. Update API to Use Clean Slate

**File**: `api/routes/batch.py`

**Change line 159**:
```python
# OLD
from src.batch.drive_tasks import coordinate_batch_workflow

# NEW
from core.batch.coordinator import coordinate_batch_workflow_clean_slate
```

**Change line 168**:
```python
# OLD
task = coordinate_batch_workflow(job_id, job_request.urls, conversion_options)

# NEW
# First, download SVG files from URLs to temp paths
svg_file_paths = []
for url in job_request.urls:
    # Download SVG content
    import requests
    response = requests.get(url)
    temp_path = f"/tmp/batch_input/{job_id}_{len(svg_file_paths)}.svg"
    Path(temp_path).parent.mkdir(exist_ok=True)
    Path(temp_path).write_bytes(response.content)
    svg_file_paths.append(temp_path)

# Schedule Clean Slate workflow
task = coordinate_batch_workflow_clean_slate(
    job_id,
    svg_file_paths,  # File paths instead of URLs
    conversion_options
)
```

### 5. Add Trace Endpoint

**File**: `api/routes/batch.py`

```python
@router.get("/jobs/{job_id}/trace", response_model=Dict[str, Any])
async def get_batch_job_trace(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get E2E trace data for batch job.

    Returns complete pipeline trace showing:
    - Parse → Analyze → Map → Embed for each page
    - Package assembly timing
    - Drive upload details
    """
    batch_job = BatchJob.get_by_id(job_id, DEFAULT_DB_PATH)
    if not batch_job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Retrieve trace data from job metadata or result storage
    # This would need to be stored when job completes

    return {
        'job_id': job_id,
        'trace_data': batch_job.trace_data,  # Stored trace
        'architecture': 'clean_slate'
    }
```

## Implementation Order

1. ✅ **DONE**: Create `core/batch/tasks.py` with Clean Slate tasks
2. ✅ **DONE**: Test batch tasks independently
3. **TODO**: Add tracing to `PackageWriter`
4. **TODO**: Update `MultiPageConverter` to pass debug flag to `PackageWriter`
5. **TODO**: Create `core/batch/coordinator.py` with workflow orchestration
6. **TODO**: Update `api/routes/batch.py` to use Clean Slate coordinator
7. **TODO**: Add trace endpoint to API
8. **TODO**: Test complete flow: API → Huey → Batch → Drive
9. **TODO**: Deprecate legacy `src/batch/tasks.py`

## Testing Strategy

### Unit Tests
- `test_package_writer_tracing.py` - Verify PackageWriter debug data
- `test_coordinator.py` - Test batch coordinator

### Integration Tests
- `test_batch_api_clean_slate.py` - API → Clean Slate batch flow
- `test_batch_drive_integration.py` - Batch → Drive upload

### E2E Tests
- `test_complete_batch_flow.py` - Full API → Huey → Batch → Drive → Trace

## Trace Data Flow

```
User Request
  ↓
API creates BatchJob
  ↓
Huey schedules: coordinate_batch_workflow_clean_slate()
  ↓
Calls: convert_multiple_svgs_clean_slate()
  ↓
Returns: {
    'page_count': 3,
    'debug_trace': [
        {
            'page_number': 1,
            'pipeline_trace': {
                'parse_result': {...},
                'analysis_result': {...},
                'mapper_results': [...],
                'embedder_result': {...}
            }
        },
        ...
    ],
    'package_trace': {  # NEW
        'package_creation_ms': 5.2,
        'file_write_ms': 1.3,
        'compression_ratio': 0.42
    }
}
  ↓
Stores trace in BatchJob.metadata
  ↓
User GET /jobs/{id}/trace retrieves full trace
```

## Benefits

1. **Complete Tracing**: Parse → Analyze → Map → Embed → Package → Drive
2. **Clean Architecture**: All batch uses Clean Slate IR → Policy flow
3. **Backward Compatible**: Reuses existing Drive upload tasks
4. **Incremental Migration**: Can run alongside legacy during transition
5. **E2E Visibility**: Full pipeline instrumentation

## Migration Checklist

- [ ] Add `enable_debug` parameter to `PackageWriter.__init__()`
- [ ] Add debug data collection in `PackageWriter.write_package()`
- [ ] Update `MultiPageConverter._generate_multipage_package()` to pass debug flag
- [ ] Create `core/batch/coordinator.py`
- [ ] Create `core/batch/__init__.py` export for coordinator
- [ ] Update `api/routes/batch.py` to import Clean Slate coordinator
- [ ] Add URL → file path download logic in API
- [ ] Add `/jobs/{id}/trace` endpoint
- [ ] Write tests for PackageWriter tracing
- [ ] Write tests for coordinator
- [ ] Write E2E test for complete flow
- [ ] Update API documentation
- [ ] Mark legacy `src/batch/tasks.py` as deprecated
- [ ] Add migration notes to CHANGELOG

---

**Next Step**: Start with adding tracing to `PackageWriter`
