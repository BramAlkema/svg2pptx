# Batch API Endpoints

Complete API reference for SVG2PPTX batch processing endpoints with Google Drive integration.

## Overview

The Batch API provides endpoints for processing multiple SVG files simultaneously with optional Google Drive integration for automatic upload and organization.

## Authentication

All batch endpoints require API key authentication:

```http
Authorization: Bearer your-api-key
```

## Core Batch Endpoints

### `POST /batch/convert-files`

Convert multiple SVG files to PowerPoint presentations.

**Request:**
```http
POST /batch/convert-files
Content-Type: multipart/form-data

files: [file1.svg, file2.svg, ...]
slide_width: 10.0 (optional, default: 10.0)
slide_height: 7.5 (optional, default: 7.5) 
output_format: "single_pptx" | "zip_archive" (optional, default: "single_pptx")
quality: "low" | "medium" | "high" (optional, default: "medium")

# Google Drive Integration Parameters (NEW)
enable_drive_integration: true | false (optional, default: false)
drive_folder_pattern: "string" (optional, see Drive Integration section)
```

**Response:**
```json
{
    "batch_id": "batch-12345",
    "status": "PENDING",
    "message": "Batch processing started",
    "total_files": 5,
    "drive_integration_enabled": true,
    "drive_upload_status": "pending"
}
```

### `POST /batch/convert-zip`

Convert SVG files from a ZIP archive with optional folder structure preservation.

**Request:**
```http
POST /batch/convert-zip
Content-Type: multipart/form-data

zip_file: archive.zip
output_format: "zip_archive" | "single_pptx" (optional, default: "zip_archive")

# Google Drive Integration Parameters (NEW)
enable_drive_integration: true | false (optional, default: false)
preserve_folder_structure: true | false (optional, default: true)
drive_folder_pattern: "string" (optional)
```

**Response:**
```json
{
    "batch_id": "batch-67890", 
    "status": "PENDING",
    "message": "ZIP processing started",
    "total_files": 12,
    "drive_integration_enabled": true,
    "folder_structure_preserved": true
}
```

## Status and Monitoring

### `GET /batch/jobs/{job_id}`

Get detailed status of a batch job.

**Response:**
```json
{
    "job_id": "batch-12345",
    "status": "completed" | "pending" | "processing" | "failed",
    "total_files": 5,
    "completed_files": 5,
    "failed_files": 0,
    "progress": 100.0,
    "drive_integration_enabled": true,
    "drive_upload_status": "completed" | "pending" | "uploading" | "failed",
    "drive_folder_pattern": "SVG2PPTX-Batches/{date}/batch-{job_id}/",
    "created_at": "2025-09-12T10:30:00Z",
    "updated_at": "2025-09-12T10:35:00Z"
}
```

### `GET /batch/jobs/{job_id}/drive-info` (NEW)

Get Google Drive integration details for a batch job.

**Response:**
```json
{
    "batch_job_id": "batch-12345",
    "drive_integration_enabled": true,
    "drive_folder_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
    "drive_folder_url": "https://drive.google.com/drive/folders/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
    "uploaded_files": [
        {
            "original_filename": "diagram1.svg",
            "drive_file_id": "1FGhij789KLmnop012QRstu345VWxyz678",
            "drive_file_url": "https://drive.google.com/file/d/1FGhij789KLmnop012QRstu345VWxyz678/view",
            "preview_url": "https://docs.google.com/presentation/d/1FGhij789KLmnop012QRstu345VWxyz678/preview",
            "uploaded_at": "2025-09-12T10:33:00Z"
        }
    ],
    "upload_summary": {
        "total_files": 5,
        "uploaded_files": 5,
        "failed_uploads": 0
    }
}
```

## Google Drive Integration

### Overview

When `enable_drive_integration: true` is specified, converted PowerPoint files are automatically uploaded to Google Drive with organized folder structure.

### Folder Patterns

Control Drive folder organization using patterns:

**Default Pattern:**
```
SVG2PPTX-Batches/{date}/batch-{job_id}/
```

**Custom Patterns:**
```
# Date-based organization
"Projects/{date}/SVG-Conversions/"

# Project-based organization  
"Client-Work/Project-{job_id}/"

# Hierarchical organization
"SVG-Archive/{date}/Batch-{job_id}/Conversions/"
```

**Pattern Variables:**
- `{date}`: Current date (YYYY-MM-DD format)
- `{job_id}`: Unique batch job identifier
- `{timestamp}`: Unix timestamp

### ZIP Structure Preservation

When processing ZIP files with `preserve_folder_structure: true`:

**Original ZIP Structure:**
```
archive.zip
├── icons/
│   ├── home.svg
│   └── user.svg
├── diagrams/
│   └── flowchart.svg
└── logo.svg
```

**Drive Folder Structure:**
```
SVG2PPTX-Batches/2025-09-12/batch-abc123/
├── icons/
│   ├── home.pptx
│   └── user.pptx  
├── diagrams/
│   └── flowchart.pptx
└── logo.pptx
```

## Error Responses

### Standard Error Format

All error responses follow this format:

```json
{
    "detail": "Error description",
    "error_code": "BATCH_ERROR_001", 
    "timestamp": "2025-09-12T10:30:00Z"
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `BATCH_ERROR_001` | 400 | Invalid file format |
| `BATCH_ERROR_002` | 400 | File size limit exceeded |
| `BATCH_ERROR_003` | 400 | Too many files |
| `BATCH_ERROR_004` | 404 | Batch job not found |
| `DRIVE_ERROR_001` | 500 | Google Drive authentication failed |
| `DRIVE_ERROR_002` | 500 | Drive upload failed |
| `DRIVE_ERROR_003` | 429 | Drive API quota exceeded |

## Rate Limits

### Batch Processing Limits

- **Files per batch:** Maximum 50 files
- **File size:** Maximum 100MB total per batch
- **Concurrent batches:** Maximum 5 per API key
- **Processing timeout:** 30 minutes per batch

### Drive Integration Limits

- **Upload rate:** Respects Google Drive API quotas
- **Folder creation:** Maximum 100 folders per day
- **File size:** Individual files up to 5GB

## Usage Examples

### Basic Batch Conversion

```bash
curl -X POST "https://api.svg2pptx.com/batch/convert-files" \
  -H "Authorization: Bearer your-api-key" \
  -F "files=@diagram1.svg" \
  -F "files=@diagram2.svg" \
  -F "output_format=single_pptx" \
  -F "quality=high"
```

### Batch with Drive Integration

```bash  
curl -X POST "https://api.svg2pptx.com/batch/convert-files" \
  -H "Authorization: Bearer your-api-key" \
  -F "files=@diagram1.svg" \
  -F "files=@diagram2.svg" \
  -F "enable_drive_integration=true" \
  -F "drive_folder_pattern=Projects/{date}/SVG-Batch/"
```

### ZIP with Structure Preservation

```bash
curl -X POST "https://api.svg2pptx.com/batch/convert-zip" \
  -H "Authorization: Bearer your-api-key" \
  -F "zip_file=@svg_collection.zip" \
  -F "enable_drive_integration=true" \
  -F "preserve_folder_structure=true"
```

### Check Drive Integration Status

```bash
curl -X GET "https://api.svg2pptx.com/batch/jobs/batch-12345/drive-info" \
  -H "Authorization: Bearer your-api-key"
```

## Migration Guide

### From v1 to v2 (Drive Integration)

The Drive integration is backward compatible. Existing applications will continue to work without changes.

**Optional Migration Steps:**

1. **Add Drive Integration** (optional):
   ```diff
   + enable_drive_integration: true
   + drive_folder_pattern: "Your-Project/{date}/"
   ```

2. **Monitor Drive Uploads** (optional):
   ```diff
   // Check standard status
   GET /batch/jobs/{job_id}
   
   + // Check Drive integration details  
   + GET /batch/jobs/{job_id}/drive-info
   ```

3. **Handle New Response Fields** (optional):
   ```diff
   {
     "batch_id": "...",
     "status": "...",
   + "drive_integration_enabled": true,
   + "drive_upload_status": "completed"
   }
   ```

### Configuration Requirements

To enable Drive integration, ensure your API key has:

- Google Drive API access enabled
- Appropriate OAuth 2.0 scopes:
  - `https://www.googleapis.com/auth/drive.file`
  - `https://www.googleapis.com/auth/drive.folder`

Contact support for Drive integration setup assistance.