# API Specification

This is the API specification for the spec detailed in @.agent-os/specs/2025-09-11-batch-processing-api/spec.md

## Endpoints

### POST /batch/convert-zip

**Purpose:** Accept ZIP file upload containing multiple SVG files and initiate batch conversion process
**Content-Type:** multipart/form-data
**Parameters:** 
- `file` (required): ZIP file containing SVG files (max 100MB)
- `output_format` (optional): "single_pptx" (default) | "zip_archive"
- `slide_width` (optional): PowerPoint slide width in inches (default: 10)
- `slide_height` (optional): PowerPoint slide height in inches (default: 7.5)

**Response:**
```json
{
  "batch_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "total_files": 15,
  "created_at": "2025-09-11T10:30:00Z"
}
```

**Errors:**
- 400: Invalid ZIP file, no SVG files found, or file size exceeded
- 413: Request entity too large (>100MB)
- 429: Rate limit exceeded
- 500: Internal server error during job creation

### POST /batch/convert-files

**Purpose:** Accept multiple individual SVG file uploads for batch conversion
**Content-Type:** multipart/form-data
**Parameters:**
- `files` (required): Array of SVG files (max 20 files, 10MB each)
- `output_format` (optional): "single_pptx" (default) | "zip_archive"
- `slide_width` (optional): PowerPoint slide width in inches (default: 10)
- `slide_height` (optional): PowerPoint slide height in inches (default: 7.5)

**Response:**
```json
{
  "batch_id": "550e8400-e29b-41d4-a716-446655440001",
  "status": "queued", 
  "total_files": 8,
  "created_at": "2025-09-11T10:35:00Z"
}
```

**Errors:**
- 400: Invalid file format, no files provided, or file count exceeded
- 413: Individual file size exceeded (>10MB)
- 429: Rate limit exceeded
- 500: Internal server error during job creation

### GET /batch/status/{batch_id}

**Purpose:** Retrieve current status and progress of batch conversion job
**Parameters:** 
- `batch_id` (path): UUID of the batch job

**Response:**
```json
{
  "batch_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "progress": 0.65,
  "completed_files": 10,
  "total_files": 15,
  "failed_files": 1,
  "created_at": "2025-09-11T10:30:00Z",
  "updated_at": "2025-09-11T10:33:15Z",
  "errors": [
    {
      "filename": "corrupt.svg",
      "error": "Invalid SVG format: missing closing tag"
    }
  ]
}
```

**Status Values:**
- `queued`: Job accepted and waiting for processing
- `processing`: Currently converting files
- `completed`: All files processed successfully
- `completed_with_errors`: Some files failed but batch completed
- `failed`: Batch processing failed entirely

**Errors:**
- 404: Batch ID not found
- 500: Internal server error retrieving status

### GET /batch/download/{batch_id}

**Purpose:** Download completed batch conversion results
**Parameters:**
- `batch_id` (path): UUID of the completed batch job

**Response:**
- Content-Type: `application/vnd.openxmlformats-officedocument.presentationml.presentation` (single PPTX)
- Content-Type: `application/zip` (ZIP archive of PPTX files)
- Content-Disposition: `attachment; filename="batch_result.pptx"` or `"batch_results.zip"`

**Errors:**
- 404: Batch ID not found or files not available
- 400: Batch not completed or failed
- 410: Files expired (after 24 hours)
- 500: Internal server error during file delivery

## Controllers

### BatchController

**Actions:**
- `initiate_zip_batch()`: Process ZIP upload and create batch job
- `initiate_files_batch()`: Process multiple file uploads and create batch job  
- `get_batch_status()`: Retrieve current job status and progress
- `download_results()`: Serve completed conversion files

**Business Logic:**
- Validate input files and parameters
- Create unique batch job ID using UUID4
- Store job metadata and progress tracking
- Queue background processing task
- Handle partial failures gracefully
- Manage temporary file cleanup

**Error Handling:**
- Input validation with detailed error messages
- Graceful degradation for partial batch failures
- Timeout handling for long-running conversions
- Resource cleanup on errors
- Structured error responses with actionable information

## Rate Limiting

**Batch Endpoints:**
- 10 requests per hour per IP address
- 5 concurrent active batches per user
- Total system limit: 20 concurrent batch jobs

**Status Endpoints:**
- 100 requests per minute per IP address
- No concurrent request limits

## Authentication

**Current Implementation:** Extends existing API authentication patterns
**Future Considerations:** API key validation for enterprise usage