# Huey Queue System - Setup & Testing

## Overview

The SVG2PPTX batch processing system uses **Huey** with **SQLite backend** for job queue management. This is a pure Python solution with no external dependencies (Redis, RabbitMQ, etc.).

## Components

### 1. Huey Configuration
- **File**: `core/batch/huey_app.py`
- **Database**: `data/svg2pptx_jobs.db` (SQLite)
- **Features**:
  - Task retries (3 attempts with 60s delay)
  - Result storage
  - UTC timestamps
  - Immediate mode for testing

### 2. Tasks
- **File**: `core/batch/tasks.py`
- **Main Task**: `convert_single_svg(file_data, conversion_options)`
  - Accepts SVG file data (bytes)
  - Uses CleanSlateConverter
  - Returns PPTX output
  - Automatic error handling and retries

### 3. Worker Process
- **Script**: `start_huey_worker.sh`
- **Workers**: 4 concurrent workers
- **Logs**: `huey.log`

## Testing

### Immediate Mode (Synchronous)
For testing without running a separate worker:

```bash
PYTHONPATH=. HUEY_IMMEDIATE=true python test_huey_job.py
```

**Result**: ✅ Job completes synchronously, output written to `/tmp/svg2pptx_output/`

### Async Mode (Production)

**Terminal 1 - Start Worker:**
```bash
./start_huey_worker.sh
```

**Terminal 2 - Push Jobs:**
```bash
PYTHONPATH=. python test_huey_job.py
```

## Test Results

### ✅ Immediate Mode Test
```
✅ Job pushed to queue
   Task ID: 0b5eb518-9895-4fe1-a046-0cc4b58370cd

✅ Job completed!
   ✅ Output: /tmp/svg2pptx_output/c75ccf56/test_huey.pptx
   ⏱️  Time: 0.01s
```

### Output Validation
```bash
$ ls -lh /tmp/svg2pptx_output/*/test_huey.pptx
-rw-r--r--  1 user  wheel   5.5K  test_huey.pptx
```

## Architecture

```
┌─────────────────┐
│  Push Job       │
│  (API/CLI)      │
└────────┬────────┘
         │
         ▼
┌─────────────────────┐
│  Huey Queue         │
│  (SQLite)           │
│  data/jobs.db       │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Worker Pool        │
│  (4 workers)        │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  CleanSlateConverter│
│  SVG → PPTX         │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Output File        │
│  /tmp/svg2pptx/     │
└─────────────────────┘
```

## Integration with API

The batch system integrates with FastAPI routes in:
- `api/routes/batch.py` - Batch conversion endpoints
- `api/routes/google_slides.py` - Google Drive integration

## Next Steps

1. ✅ Huey working with CleanSlateConverter
2. ⏭️ Test async worker mode
3. ⏭️ Test batch processing (multiple files)
4. ⏭️ Test Google Drive integration
5. ⏭️ Performance testing with concurrent jobs

## Fixes Applied

### Task Module Update
**File**: `core/batch/tasks.py`
- ❌ Old: `from ..svg2pptx import svg_to_pptx` (archived)
- ✅ New: `from ..pipeline.converter import CleanSlateConverter`
- ✅ Method: `converter.convert_string(svg_content)`
- ✅ Output: Writes `conversion_result.output_data` to file

## Status

**✅ Huey queue system operational with Clean Slate pipeline**
- Jobs can be pushed successfully
- Conversion completes without errors
- Output files generated correctly
- Ready for async worker testing
