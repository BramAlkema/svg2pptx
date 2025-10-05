# OAuth Batch Integration Guide

**Version:** 2.0.0
**Date:** 2025-10-05
**Status:** Production Ready

## Overview

The batch processing system now supports OAuth-based Google Slides export, allowing you to convert multiple SVG files directly to Google Slides presentations using authenticated workflows.

## Quick Start

### Prerequisites
1. OAuth credentials configured (see [OAuth Setup](api/oauth-export-api.md))
2. User authenticated via CLI or API
3. SVG files or URLs to convert

### Python Example
```python
from core.auth import get_system_username
from core.batch.coordinator import coordinate_batch_workflow_clean_slate

# Authenticate user (one-time)
# Run: svg2pptx auth google

# Convert batch with Slides export
user_id = get_system_username()
result = coordinate_batch_workflow_clean_slate(
    job_id="batch_demo",
    file_paths=["diagram1.svg", "diagram2.svg"],
    user_id=user_id,
    export_to_slides=True,
    conversion_options={
        'title': 'Team Diagrams',
        'folder_id': 'optional_drive_folder_id'
    }
)

print(f"Slides URL: {result['slides_export']['slides_url']}")
```

### API Example
```bash
# 1. Create batch job with OAuth Slides export
curl -X POST http://localhost:8000/batch/jobs \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{
    "urls": ["https://example.com/diagram.svg"],
    "user_id": "alice",
    "export_to_slides": true,
    "slides_title": "My Presentation"
  }'

# 2. Check status
curl http://localhost:8000/batch/jobs/$JOB_ID \
  -H "Authorization: Bearer $API_KEY"
```

## API Reference

### Batch Job Creation

**Endpoint:** `POST /batch/jobs`

**New OAuth Parameters:**
```json
{
  "urls": ["https://example.com/file.svg"],
  "user_id": "alice",                    // Required for Slides export
  "export_to_slides": true,              // Enable OAuth Slides export
  "slides_title": "Presentation Title",  // Optional custom title
  "slides_folder_id": "folder_id"        // Optional Drive folder ID
}
```

**Response:**
```json
{
  "success": true,
  "job_id": "batch_abc123",
  "status": "created",
  "total_files": 1,
  "drive_integration_enabled": false,
  "estimated_processing_time": "3 seconds"
}
```

### Batch Job Status

**Endpoint:** `GET /batch/jobs/{job_id}`

**Response includes Slides export info:**
```json
{
  "job_id": "batch_abc123",
  "status": "completed",
  "total_files": 1,
  "completed_files": 1,
  "failed_files": 0,
  "slides_export_enabled": true,
  "slides_url": "https://docs.google.com/presentation/d/...",
  "slides_export_status": "completed"
}
```

**Slides Export Statuses:**
- `"not_started"` - No Slides export requested
- `"in_progress"` - Currently exporting to Slides
- `"completed"` - Successfully exported to Slides
- `"failed"` - Slides export failed (conversion still succeeded)

### Trace Data

**Endpoint:** `GET /batch/jobs/{job_id}/trace`

Includes Slides information in trace data:
```json
{
  "job_id": "batch_abc123",
  "trace_available": true,
  "architecture": "clean_slate",
  "trace_data": {
    "workflow": "conversion_and_slides_export",
    "slides_url": "https://docs.google.com/presentation/d/...",
    "page_count": 2
  }
}
```

## Batch Coordinator

### Function Signature
```python
@huey.task()
def coordinate_batch_workflow_clean_slate(
    job_id: str,
    file_paths: list[str],
    conversion_options: dict[str, Any] = None,
    user_id: str | None = None,          # NEW: OAuth user ID
    export_to_slides: bool = False,      # NEW: Enable Slides export
) -> dict[str, Any]:
```

### Conversion Options
```python
conversion_options = {
    'quality': 'high',                    # Conversion quality
    'title': 'Presentation Title',        # Slides title
    'folder_id': 'drive_folder_id',      # Optional Drive folder
}
```

### Return Value
```python
{
    'success': True,
    'job_id': 'batch_abc123',
    'conversion': {
        'page_count': 2,
        'output_size_bytes': 12345
    },
    'slides_export': {
        'slides_id': 'presentation_id',
        'slides_url': 'https://docs.google.com/presentation/d/...',
        'web_view_link': 'https://docs.google.com/presentation/d/.../edit'
    },
    'architecture': 'clean_slate',
    'workflow': 'conversion_and_slides_export'
}
```

## Workflow States

### Job Statuses
1. `"created"` - Job created, not yet processing
2. `"processing"` - Converting SVG files to PPTX
3. `"exporting_to_slides"` - Uploading to Google Slides (NEW)
4. `"completed"` - Successfully completed all steps
5. `"completed_slides_export_failed"` - Conversion OK, Slides export failed
6. `"failed"` - Job failed

### Slides Export Flow
```
SVG Files → Download → Convert to PPTX → Export to Slides → Update Status
                                              ↓
                                        Store Slides URL
                                        in trace_data
```

## Authentication

### User Authentication Check
Before creating a batch job with Slides export:

**Python:**
```python
from core.auth import get_cli_token_store

token_store = get_cli_token_store()
if not token_store.has_token(user_id):
    print("User not authenticated. Run: svg2pptx auth google")
```

**API:**
```bash
curl http://localhost:8000/oauth2/status/alice
# Response: {"is_authenticated": true, "email": "alice@example.com"}
```

### OAuth Setup
1. Configure credentials:
   ```bash
   export GOOGLE_DRIVE_CLIENT_ID="your-client-id"
   export GOOGLE_DRIVE_CLIENT_SECRET="your-secret"
   ```

2. Authenticate user:
   ```bash
   # CLI
   svg2pptx auth google

   # API
   curl -X POST http://localhost:8000/oauth2/start \
     -d '{"user_id": "alice"}'
   # Visit returned auth_url
   ```

## Examples

Complete working examples are provided:

### 1. Python CLI Example
**File:** `examples/batch_oauth_slides_export.py`

Features:
- Downloads SVG URLs to temp files
- Authenticates user via OAuth
- Converts batch to PPTX
- Exports to Google Slides
- Shows progress and final Slides URL

Run:
```bash
python examples/batch_oauth_slides_export.py
```

### 2. Shell API Example
**File:** `examples/api_batch_oauth_example.sh`

Features:
- Checks OAuth authentication status
- Creates batch job with Slides export
- Polls for job completion
- Displays Slides URL
- Retrieves trace data

Run:
```bash
./examples/api_batch_oauth_example.sh
```

## Error Handling

### Common Errors

**1. User Not Authenticated**
```json
{
  "success": false,
  "error_message": "User alice not authenticated"
}
```
**Solution:** Authenticate user via `svg2pptx auth google`

**2. OAuth Credentials Not Configured**
```json
{
  "success": false,
  "error_message": "OAuth credentials not configured"
}
```
**Solution:** Set `GOOGLE_DRIVE_CLIENT_ID` and `GOOGLE_DRIVE_CLIENT_SECRET`

**3. Slides Export Failed**
```json
{
  "status": "completed_slides_export_failed",
  "slides_export": {
    "success": false,
    "error_message": "Token expired"
  }
}
```
**Solution:** Re-authenticate user, conversion PPTX is still available

## Best Practices

### 1. Pre-flight Checks
Always verify authentication before creating batch job:
```python
if export_to_slides and not token_store.has_token(user_id):
    raise HTTPException(401, f"User {user_id} not authenticated")
```

### 2. Error Recovery
Handle partial success gracefully:
```python
if result['success'] and result.get('slides_export'):
    if result['slides_export'].get('success'):
        print(f"Slides URL: {result['slides_export']['slides_url']}")
    else:
        print(f"Warning: Slides export failed, PPTX available at {output_path}")
```

### 3. Status Polling
For API usage, poll with exponential backoff:
```bash
ATTEMPT=0
while [ "$STATUS" != "completed" ]; do
  sleep $((2 ** ATTEMPT))
  ATTEMPT=$((ATTEMPT + 1))
  # Fetch status...
done
```

### 4. Title Generation
Provide meaningful titles:
```python
conversion_options = {
    'title': f'{project_name} - {date.today().isoformat()}'
}
```

## Backwards Compatibility

OAuth Slides export is fully backwards compatible:
- Works alongside legacy Drive integration
- OAuth parameters are optional
- Existing batch workflows continue to work
- No database schema changes required

**Priority:** OAuth Slides export takes precedence over legacy Drive upload when both are enabled.

## Monitoring & Debugging

### Coordinator Info
Check OAuth availability:
```python
from core.batch.coordinator import get_coordinator_info

info = get_coordinator_info()
print(f"OAuth available: {info['capabilities']['oauth_slides_export']}")
```

### Trace Data
Debug workflow using trace endpoint:
```bash
curl http://localhost:8000/batch/jobs/$JOB_ID/trace | jq '.trace_data'
```

### Logs
Monitor coordinator logs for OAuth operations:
```
INFO: Slides export enabled for user alice
INFO: ✅ Exported to Slides: https://docs.google.com/presentation/d/...
```

## Security Considerations

1. **Token Storage:** Tokens encrypted with Fernet (AES-128)
2. **User Isolation:** Each user has separate encrypted tokens
3. **Auto-Refresh:** Access tokens refreshed automatically
4. **Error Handling:** Invalid tokens trigger re-authentication

## Performance

- **Single Presentation:** Creates one merged presentation per batch
- **Parallel Processing:** Conversion happens in parallel (Huey tasks)
- **Slides Upload:** Single API call for PPTX → Slides conversion
- **Typical Timing:** ~3 seconds per SVG + Slides upload overhead

## Limitations

1. **Single Presentation Output:** Currently creates one merged presentation
   - Future: Could create separate presentations per SVG

2. **No Automatic Retry:** Failed Slides exports require manual retry
   - Future: Could implement retry mechanism

3. **CLI Token Store:** Uses CLI token store by default
   - Alternative: Can be configured for API token store

## Troubleshooting

### Issue: "User not authenticated"
**Cause:** No OAuth token for user
**Fix:** Run `svg2pptx auth google` or use API OAuth flow

### Issue: "OAuth credentials not configured"
**Cause:** Missing environment variables
**Fix:** Set `GOOGLE_DRIVE_CLIENT_ID` and `GOOGLE_DRIVE_CLIENT_SECRET`

### Issue: Slides URL is null
**Cause:** Slides export disabled or failed
**Fix:** Check `slides_export_status` and trace data for errors

### Issue: "Token expired"
**Cause:** Refresh token expired or revoked
**Fix:** Re-authenticate user

## Related Documentation

- [OAuth Setup Guide](api/oauth-export-api.md)
- [CLI Documentation](../cli/README.md)
- [Batch API Reference](api/batch-api.md)
- [Phase 4 Implementation Summary](.agent-os/specs/2025-10-05-oauth-drive-export/PHASE_4_SUMMARY.md)

## Version History

- **v2.0.0** (2025-10-05): OAuth Slides export for batch processing
- **v1.0.0**: Initial batch processing with Drive integration

---

**Maintained by:** SVG2PPTX Contributors
**Last Updated:** 2025-10-05
