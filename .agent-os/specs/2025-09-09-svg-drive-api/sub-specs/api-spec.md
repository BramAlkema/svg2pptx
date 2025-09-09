# API Specification

This is the API specification for the spec detailed in @.agent-os/specs/2025-09-09-svg-drive-api/spec.md

## Endpoints

### POST /convert

**Purpose:** Convert SVG from URL to PPTX and upload to Google Drive
**Parameters:** 
- `url` (query, required): URL of the SVG file to convert
- `fileId` (query, optional): Google Drive file ID to update instead of creating new file
- `Authorization` (header, required): Bearer token for API authentication

**Response:** JSON object with conversion results
```json
{
  "success": true,
  "fileId": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
  "shareableLink": "https://drive.google.com/file/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/view",
  "fileName": "converted_presentation.pptx",
  "fileSize": 45621
}
```

**Errors:** 
- `400`: Invalid SVG URL or malformed request
- `401`: Invalid or missing API key
- `404`: SVG URL not accessible or fileId not found
- `422`: SVG conversion failed or invalid SVG format
- `500`: Google Drive upload failed or internal server error