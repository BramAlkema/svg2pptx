# API Specification

This is the API specification for the spec detailed in @.agent-os/specs/2025-09-12-batch-drive-integration/spec.md

## Endpoints

### POST /batch/convert-files (Enhanced)

**Purpose:** Extended batch file conversion with optional Google Drive integration
**Parameters:** 
- `files`: Multiple SVG files (existing)
- `output_format`: "single_pptx" or "zip_archive" (existing)
- `drive_upload`: boolean (NEW) - Enable Google Drive upload
- `drive_folder_name`: string (NEW, optional) - Custom folder name
- `generate_previews`: boolean (NEW, optional) - Generate PNG previews via Google Slides API

**Response:** 
```json
{
  "job_id": "batch_abc123",
  "status": "processing",
  "drive_integration": {
    "enabled": true,
    "folder_name": "My SVG Batch",
    "estimated_folder_path": "SVG2PPTX-Batches/2025-09-12/batch_abc123/"
  },
  "files": [
    {
      "filename": "design1.svg",
      "status": "queued",
      "drive_upload_status": "pending"
    }
  ]
}
```

**Errors:** 
- 401: Invalid Google Drive authentication
- 403: Google Drive API quota exceeded
- 413: Batch size exceeds Drive upload limits

### POST /batch/convert-zip (Enhanced)

**Purpose:** Extended ZIP batch conversion with Google Drive folder structure preservation
**Parameters:**
- `zip_file`: ZIP containing SVG files (existing)
- `output_format`: "single_pptx" or "zip_archive" (existing)  
- `drive_upload`: boolean (NEW) - Enable Google Drive upload
- `preserve_structure`: boolean (NEW) - Maintain ZIP folder structure in Drive
- `drive_folder_name`: string (NEW, optional) - Custom root folder name

**Response:**
```json
{
  "job_id": "batch_xyz789",
  "status": "processing",
  "drive_integration": {
    "enabled": true,
    "preserve_structure": true,
    "folder_structure": ["designs/", "icons/", "logos/"]
  }
}
```

**Errors:**
- 400: ZIP structure too complex for Drive organization
- 507: Google Drive storage quota exceeded

### GET /batch/status/{job_id} (Enhanced)

**Purpose:** Extended batch job status with Google Drive upload progress
**Parameters:** 
- `job_id`: Batch job identifier (existing)

**Response:**
```json
{
  "job_id": "batch_abc123",
  "status": "completed",
  "conversion_progress": {
    "total": 5,
    "completed": 5,
    "failed": 0
  },
  "drive_integration": {
    "enabled": true,
    "folder_id": "1A2B3C4D5E6F",
    "folder_url": "https://drive.google.com/drive/folders/1A2B3C4D5E6F",
    "upload_progress": {
      "total": 5,
      "uploaded": 4,
      "failed": 1
    }
  },
  "files": [
    {
      "filename": "design1.svg",
      "conversion_status": "completed",
      "local_url": "/download/batch_abc123/design1.pptx",
      "drive_file_id": "1G2H3I4J5K6L",
      "drive_url": "https://docs.google.com/presentation/d/1G2H3I4J5K6L",
      "preview_url": "https://drive.google.com/thumbnail?id=1G2H3I4J5K6L"
    }
  ]
}
```

**Errors:**
- 404: Job not found
- 500: Drive API communication error

### GET /batch/results/{job_id} (Enhanced)

**Purpose:** Extended batch results with comprehensive Google Drive links
**Parameters:**
- `job_id`: Batch job identifier (existing)

**Response:**
```json
{
  "job_id": "batch_abc123",
  "download_urls": {
    "local_zip": "/download/batch_abc123.zip",
    "individual_files": ["/download/batch_abc123/design1.pptx"]
  },
  "drive_integration": {
    "folder_url": "https://drive.google.com/drive/folders/1A2B3C4D5E6F",
    "files": [
      {
        "filename": "design1.pptx",
        "drive_url": "https://docs.google.com/presentation/d/1G2H3I4J5K6L",
        "preview_url": "https://drive.google.com/thumbnail?id=1G2H3I4J5K6L",
        "sharing_url": "https://drive.google.com/file/d/1G2H3I4J5K6L/view"
      }
    ]
  }
}
```

### POST /batch/simple/convert-files (Enhanced)

**Purpose:** Extended synchronous batch conversion with Drive upload
**Parameters:**
- All existing parameters plus new Drive integration options
- Limited to 10 files max when Drive upload enabled (API rate limiting)

**Response:** Complete results immediately with Drive URLs

## Controllers

### BatchDriveController

**Actions:**
- `create_batch_folder()` - Creates organized Google Drive folder structure
- `upload_batch_files()` - Handles parallel file uploads with error recovery
- `generate_batch_previews()` - Creates PNG previews for all files via Google Slides API
- `update_drive_status()` - Updates job status with Drive upload progress

**Business Logic:**
- Integrates with existing GoogleDriveService from single-file conversion
- Manages folder hierarchy creation and file organization
- Handles partial upload failures with detailed error reporting
- Coordinates with Huey task queue for async processing

**Error Handling:**
- Graceful fallback to local-only results if Drive upload fails
- Detailed per-file error tracking and user notification
- Retry logic for transient Google API errors
- Quota management and rate limiting compliance