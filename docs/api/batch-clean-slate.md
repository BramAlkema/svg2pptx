# Clean Slate Batch Processing API

**Version**: 2.0
**Architecture**: Clean Slate
**Status**: Production Ready

## Overview

The Clean Slate batch processing system provides complete end-to-end tracing from SVG input through PPTX package assembly, with integrated Google Drive upload support.

## Key Features

- ✅ **Complete E2E Tracing**: Visibility into every pipeline stage
- ✅ **URL Downloading**: Automatic SVG URL download with validation
- ✅ **Clean Slate Pipeline**: Modern IR → Policy → Map → Embed architecture
- ✅ **Drive Integration**: Optional Google Drive upload with previews
- ✅ **Error Recovery**: Comprehensive error handling and partial success support
- ✅ **Backward Compatible**: Legacy workflow still available

## Architecture

```
API Request → URL Download → Clean Slate Conversion → Drive Upload → Trace Storage
     ↓              ↓                    ↓                   ↓              ↓
 Validate      Temp Files         Parse → Analyze      Upload Files    Metadata
   URLs         + Validate        Map → Embed          (optional)     in Database
                                  Package
```

## API Endpoints

### 1. Create Batch Job

**Endpoint**: `POST /batch/jobs`

**Description**: Create a new batch processing job with Clean Slate architecture (default) or legacy workflow.

**Authentication**: Required (`Bearer` token)

**Request Body**:
```json
{
  "urls": ["https://example.com/file1.svg", "https://example.com/file2.svg"],
  "drive_integration_enabled": true,
  "drive_folder_pattern": "batch_{timestamp}",
  "preprocessing_preset": "aggressive",
  "generate_previews": true,
  "use_clean_slate": null
}
```

**Parameters**:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `urls` | array | Yes | - | List of SVG URLs (1-50) |
| `drive_integration_enabled` | boolean | No | `true` | Enable Drive upload |
| `drive_folder_pattern` | string | No | `null` | Custom folder naming |
| `preprocessing_preset` | string | No | `"default"` | `"minimal"`, `"default"`, or `"aggressive"` |
| `generate_previews` | boolean | No | `true` | Generate PNG previews |
| `use_clean_slate` | boolean | No | `null` | `null`/`true` = Clean Slate, `false` = Legacy |

**Response** (200 OK):
```json
{
  "success": true,
  "job_id": "batch_abc123def456",
  "message": "Batch job created successfully with 2 files",
  "status": "created",
  "total_files": 2,
  "drive_integration_enabled": true,
  "estimated_processing_time": "6 seconds"
}
```

**Error Response** (400 Bad Request):
```json
{
  "detail": "Invalid URL format: not-a-url"
}
```

**Example cURL**:
```bash
curl -X POST https://api.svg2pptx.com/batch/jobs \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "urls": ["https://www.w3.org/TR/SVG/images/coords/PreserveAspectRatio.svg"],
    "drive_integration_enabled": false
  }'
```

---

### 2. Get Job Status

**Endpoint**: `GET /batch/jobs/{job_id}`

**Description**: Retrieve current status and progress information for a batch job.

**Authentication**: Required

**Response** (200 OK):
```json
{
  "job_id": "batch_abc123def456",
  "status": "completed",
  "total_files": 2,
  "completed_files": 2,
  "failed_files": 0,
  "drive_integration_enabled": true,
  "drive_folder_id": "1234567890abcdef",
  "drive_folder_url": "https://drive.google.com/drive/folders/1234567890abcdef",
  "drive_upload_status": "completed",
  "drive_upload_progress": {
    "total_files": 2,
    "uploaded_files": 2,
    "failed_files": 0,
    "pending_files": 0,
    "progress_percentage": 100.0,
    "upload_status": "completed"
  },
  "created_at": "2025-10-03T10:30:00Z",
  "updated_at": "2025-10-03T10:30:15Z",
  "estimated_completion_time": null,
  "errors": []
}
```

**Job Statuses**:
- `created` - Job created, not yet processing
- `processing` - Converting SVGs
- `uploading` - Uploading to Drive
- `completed` - Successfully completed
- `completed_upload_failed` - Conversion OK, upload failed
- `failed` - Job failed

---

### 3. Get E2E Trace Data (NEW)

**Endpoint**: `GET /batch/jobs/{job_id}/trace`

**Description**: Retrieve complete end-to-end trace data from the Clean Slate pipeline.

**Authentication**: Required

**Response** (200 OK):
```json
{
  "job_id": "batch_abc123def456",
  "trace_available": true,
  "architecture": "clean_slate",
  "page_count": 2,
  "trace_data": {
    "architecture": "clean_slate",
    "page_count": 2,
    "workflow": "conversion_and_drive",
    "debug_trace": [
      {
        "page_number": 1,
        "pipeline_trace": {
          "parse_result": {
            "element_count": 15,
            "parse_time_ms": 2.3,
            "svg_dimensions": {
              "width": 400,
              "height": 300
            }
          },
          "analysis_result": {
            "scene_elements": 12,
            "complexity_score": 0.7
          },
          "mapper_results": [
            {
              "element_type": "rect",
              "mapped_successfully": true,
              "drawingml_shape_type": "rectangle"
            }
          ],
          "embedder_result": {
            "shapes_embedded": 12,
            "media_files_embedded": 0
          }
        },
        "package_trace": {
          "package_creation_ms": 5.2,
          "file_write_ms": 1.3,
          "package_size_bytes": 6432,
          "compression_ratio": 0.42,
          "total_time_ms": 6.5,
          "zip_structure": {
            "slides": 2,
            "relationships": 4,
            "media_files": 0,
            "content_types": 12
          }
        }
      }
    ]
  }
}
```

**Response - No Trace Available** (200 OK):
```json
{
  "job_id": "batch_xyz789",
  "trace_available": false,
  "message": "No trace data available (job may use legacy workflow or still processing)"
}
```

**Response - Job Not Found** (404 Not Found):
```json
{
  "detail": "Batch job batch_xyz789 not found"
}
```

**Trace Data Structure**:
```typescript
interface TraceData {
  architecture: "clean_slate" | "legacy";
  page_count: number;
  workflow: "conversion_only" | "conversion_and_drive" | "conversion_only_upload_failed";
  debug_trace: PageTrace[];
}

interface PageTrace {
  page_number: number;
  pipeline_trace: {
    parse_result: ParseMetrics;
    analysis_result: AnalysisMetrics;
    mapper_results: MapperResult[];
    embedder_result: EmbedderMetrics;
  };
  package_trace: PackageMetrics;
}
```

---

### 4. Get Drive Information

**Endpoint**: `GET /batch/jobs/{job_id}/drive-info`

**Description**: Get Google Drive integration details including uploaded files and preview URLs.

**Authentication**: Required

**Response** (200 OK):
```json
{
  "job_id": "batch_abc123def456",
  "drive_folder_id": "1234567890abcdef",
  "drive_folder_url": "https://drive.google.com/drive/folders/1234567890abcdef",
  "uploaded_files": [
    {
      "original_filename": "file1.svg",
      "drive_file_id": "abcdef123456",
      "drive_file_url": "https://drive.google.com/file/d/abcdef123456",
      "uploaded_at": "2025-10-03T10:30:10Z",
      "upload_status": "completed"
    }
  ],
  "preview_urls": [
    {
      "filename": "file1.svg",
      "file_id": "abcdef123456",
      "preview_url": "https://drive.google.com/thumbnail?id=abcdef123456"
    }
  ],
  "upload_summary": {
    "total_files": 2,
    "successful_uploads": 2,
    "failed_uploads": 0,
    "success_rate": "100.0%",
    "upload_status": "completed"
  }
}
```

---

## Quality Parameters

The `preprocessing_preset` parameter is automatically mapped to Clean Slate quality settings:

| Preset | Clean Slate Quality | Description |
|--------|-------------------|-------------|
| `"minimal"` | `"fast"` | Minimal preprocessing, fastest conversion |
| `"default"` | `"balanced"` | Standard quality, good balance |
| `"aggressive"` | `"high"` | Maximum quality, slower conversion |

## Workflow Types

The trace data includes a `workflow` field indicating the execution path:

- `"conversion_only"` - Conversion completed, no Drive upload requested
- `"conversion_and_drive"` - Complete workflow with Drive upload
- `"conversion_only_upload_failed"` - Conversion succeeded, Drive upload failed

## Error Handling

### Download Errors

If URL download fails, the job is immediately marked as `failed`:

```json
{
  "success": false,
  "status": "failed",
  "detail": "Failed to download 2 URLs"
}
```

### Conversion Errors

If conversion fails, trace data includes error details:

```json
{
  "success": false,
  "error_type": "parse_error",
  "error_message": "Invalid SVG structure: missing xmlns attribute"
}
```

### Upload Errors (Partial Success)

If conversion succeeds but upload fails, job status reflects partial success:

```json
{
  "status": "completed_upload_failed",
  "drive_upload_status": "failed"
}
```

The conversion output is still available and trace data is captured.

## Rate Limits

- **Max URLs per job**: 50
- **Max file size**: 10MB per URL
- **Timeout per download**: 30 seconds (configurable)
- **Concurrent jobs**: Depends on Huey worker configuration

## Best Practices

### 1. URL Validation

Ensure all URLs are:
- Valid HTTP/HTTPS URLs
- Publicly accessible (no authentication required)
- Serving valid SVG content
- Under 10MB file size

### 2. Polling for Status

Poll the status endpoint at reasonable intervals:
```javascript
const checkStatus = async (jobId) => {
  const response = await fetch(`/batch/jobs/${jobId}`);
  const status = await response.json();

  if (status.status === 'completed') {
    // Fetch trace data
    const trace = await fetch(`/batch/jobs/${jobId}/trace`);
    return trace.json();
  } else if (status.status === 'failed') {
    throw new Error('Job failed');
  }

  // Poll again in 2 seconds
  setTimeout(() => checkStatus(jobId), 2000);
};
```

### 3. Trace Data Usage

Use trace data for:
- **Debugging**: Identify which stage failed
- **Performance Analysis**: Find bottlenecks
- **Quality Metrics**: Track conversion quality over time
- **Billing**: Track processing time per job

### 4. Error Recovery

Implement retry logic for transient failures:
```javascript
const createJobWithRetry = async (urls, maxRetries = 3) => {
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await createBatchJob(urls);
    } catch (error) {
      if (i === maxRetries - 1) throw error;
      await sleep(1000 * Math.pow(2, i)); // Exponential backoff
    }
  }
};
```

## Migration from Legacy

### Step 1: Update API Calls

**Before** (Legacy - Implicit):
```javascript
const response = await fetch('/batch/jobs', {
  method: 'POST',
  body: JSON.stringify({ urls: [...] })
});
```

**After** (Clean Slate - Explicit):
```javascript
const response = await fetch('/batch/jobs', {
  method: 'POST',
  body: JSON.stringify({
    urls: [...],
    use_clean_slate: true  // Optional, true by default
  })
});
```

### Step 2: Handle Trace Endpoint

New endpoint available for trace data:
```javascript
// After job completion
const trace = await fetch(`/batch/jobs/${jobId}/trace`);
const traceData = await trace.json();

if (traceData.trace_available) {
  console.log('Pipeline stages:', traceData.trace_data.debug_trace);
}
```

### Step 3: Update Status Polling

New status values to handle:
```javascript
const handleStatus = (status) => {
  switch (status.status) {
    case 'completed':
      return 'Success';
    case 'completed_upload_failed':
      return 'Conversion OK, Upload Failed';
    case 'failed':
      return 'Failed';
    default:
      return 'Processing';
  }
};
```

## Deprecation Timeline

- **Current**: Legacy and Clean Slate both supported
- **Q2 2025**: Clean Slate becomes default
- **Q3 2025**: Legacy marked as deprecated with warnings
- **Q4 2025**: Legacy workflow removed

## Support

- **Documentation**: https://docs.svg2pptx.com
- **API Reference**: https://api.svg2pptx.com/docs
- **GitHub Issues**: https://github.com/svg2pptx/issues
- **Email**: support@svg2pptx.com

## Examples

### Example 1: Simple Batch Conversion

```python
import requests

# Create job
response = requests.post(
    'https://api.svg2pptx.com/batch/jobs',
    headers={'Authorization': 'Bearer YOUR_TOKEN'},
    json={
        'urls': [
            'https://example.com/logo.svg',
            'https://example.com/icon.svg'
        ],
        'drive_integration_enabled': False
    }
)

job_id = response.json()['job_id']

# Poll for completion
import time
while True:
    status = requests.get(
        f'https://api.svg2pptx.com/batch/jobs/{job_id}',
        headers={'Authorization': 'Bearer YOUR_TOKEN'}
    ).json()

    if status['status'] == 'completed':
        break
    elif status['status'] == 'failed':
        raise Exception('Job failed')

    time.sleep(2)

# Get trace data
trace = requests.get(
    f'https://api.svg2pptx.com/batch/jobs/{job_id}/trace',
    headers={'Authorization': 'Bearer YOUR_TOKEN'}
).json()

print(f"Converted {trace['page_count']} pages")
for page in trace['trace_data']['debug_trace']:
    print(f"Page {page['page_number']}: "
          f"{page['pipeline_trace']['parse_result']['element_count']} elements")
```

### Example 2: Batch with Drive Upload

```python
response = requests.post(
    'https://api.svg2pptx.com/batch/jobs',
    headers={'Authorization': 'Bearer YOUR_TOKEN'},
    json={
        'urls': ['https://example.com/file1.svg', 'https://example.com/file2.svg'],
        'drive_integration_enabled': True,
        'drive_folder_pattern': 'SVG_Batch_{timestamp}',
        'generate_previews': True,
        'preprocessing_preset': 'aggressive'
    }
)

job_id = response.json()['job_id']

# Wait for completion...

# Get Drive info
drive_info = requests.get(
    f'https://api.svg2pptx.com/batch/jobs/{job_id}/drive-info',
    headers={'Authorization': 'Bearer YOUR_TOKEN'}
).json()

print(f"Drive folder: {drive_info['drive_folder_url']}")
print(f"Uploaded {drive_info['upload_summary']['successful_uploads']} files")
```

## Changelog

### Version 2.0 (2025-10-03)
- ✨ Added Clean Slate batch processing
- ✨ Added `/trace` endpoint for E2E visibility
- ✨ Added automatic URL downloading
- ✨ Added package assembly tracing
- 🔄 Made Clean Slate the default architecture
- 📚 Updated API documentation

### Version 1.0 (Legacy)
- Initial batch processing implementation
- Basic Drive integration
- Legacy conversion pipeline
