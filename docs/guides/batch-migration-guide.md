# Batch Processing Migration Guide

**From**: Legacy Batch System
**To**: Clean Slate Batch Architecture
**Version**: 2.0
**Date**: 2025-10-03

## Overview

This guide helps you migrate from the legacy batch processing system to the new Clean Slate architecture, which provides complete end-to-end tracing and improved reliability.

## Why Migrate?

### Benefits of Clean Slate

1. **Complete E2E Tracing** 📊
   - Visibility into every pipeline stage
   - Debug data from Parse through Package assembly
   - Performance metrics at each stage

2. **Better Error Handling** 🛡️
   - Detailed error messages
   - Partial success support
   - Graceful degradation

3. **Modern Architecture** 🏗️
   - IR → Policy → Map → Embed pipeline
   - Modular, testable components
   - Performance optimizations

4. **Security Improvements** 🔒
   - File size validation
   - Content type validation
   - Safe filename generation

5. **Future-Proof** 🚀
   - Active development
   - New features added regularly
   - Legacy sunset in Q4 2025

## Migration Path

### Timeline

```
Q1 2025 ─────→ Q2 2025 ─────→ Q3 2025 ─────→ Q4 2025
  Now          Default        Deprecated      Removed

✓ Both        → Clean Slate  → Legacy        → Clean Slate
  Supported     Default        Warnings        Only
```

### Phase 1: Testing (Now - Q2 2025)

**Goal**: Test Clean Slate with your workloads

**Action**: Use `use_clean_slate: true` parameter explicitly
```json
{
  "urls": ["https://example.com/test.svg"],
  "use_clean_slate": true
}
```

**Validation**:
- Compare output quality
- Check trace data availability
- Verify performance is acceptable
- Test error scenarios

### Phase 2: Adoption (Q2 2025)

**Goal**: Use Clean Slate as default

**Action**: Remove `use_clean_slate` parameter (defaults to true)
```json
{
  "urls": ["https://example.com/test.svg"]
}
```

**Monitoring**:
- Track conversion success rate
- Monitor processing times
- Review trace data for insights
- Handle any edge cases

### Phase 3: Complete Migration (Q3 2025)

**Goal**: Stop using legacy workflow

**Action**: Remove any `use_clean_slate: false` overrides

**Benefits**:
- Full access to new features
- Better support and updates
- Improved performance
- Complete tracing data

## API Changes

### Endpoint Compatibility

All endpoints remain the same:
- ✅ `POST /batch/jobs` - **Compatible** (new parameter)
- ✅ `GET /batch/jobs/{id}` - **Compatible** (same response)
- ✅ `GET /batch/jobs/{id}/drive-info` - **Compatible**
- ✅ `GET /batch/jobs/{id}/progress` - **Compatible**
- ✨ `GET /batch/jobs/{id}/trace` - **NEW**

### Request Changes

#### Before (Legacy - Implicit)
```json
{
  "urls": ["https://example.com/file.svg"],
  "drive_integration_enabled": true,
  "preprocessing_preset": "default"
}
```

#### After (Clean Slate - Explicit)
```json
{
  "urls": ["https://example.com/file.svg"],
  "drive_integration_enabled": true,
  "preprocessing_preset": "default",
  "use_clean_slate": true  // Optional, true by default in Q2 2025
}
```

#### Legacy Override (Temporary)
```json
{
  "urls": ["https://example.com/file.svg"],
  "use_clean_slate": false  // Use legacy workflow
}
```

### Response Changes

#### Job Status - New Values

Clean Slate introduces new status value:
```json
{
  "status": "completed_upload_failed"  // NEW
}
```

This indicates conversion succeeded but Drive upload failed.

**Migration**: Update status handling:
```javascript
// Before
if (status === 'completed') {
  // Success
}

// After
if (status === 'completed' || status === 'completed_upload_failed') {
  // Conversion succeeded
  if (status === 'completed_upload_failed') {
    console.warn('Upload failed, but conversion OK');
  }
}
```

#### Trace Data - New Endpoint

New endpoint provides E2E trace:
```bash
GET /batch/jobs/{job_id}/trace
```

**Response**:
```json
{
  "trace_available": true,
  "architecture": "clean_slate",
  "page_count": 2,
  "trace_data": {
    "debug_trace": [...]
  }
}
```

**Migration**: Add trace fetching after job completion:
```javascript
// After job completes
const trace = await fetch(`/batch/jobs/${jobId}/trace`);
const traceData = await trace.json();

if (traceData.trace_available) {
  // Analyze trace data
  analyzePerformance(traceData.trace_data);
}
```

## Code Examples

### Python Migration

#### Before (Legacy)
```python
import requests

def create_batch_job(urls):
    response = requests.post(
        'https://api.svg2pptx.com/batch/jobs',
        headers={'Authorization': f'Bearer {TOKEN}'},
        json={'urls': urls}
    )
    return response.json()['job_id']

def wait_for_completion(job_id):
    import time
    while True:
        status = requests.get(
            f'https://api.svg2pptx.com/batch/jobs/{job_id}',
            headers={'Authorization': f'Bearer {TOKEN}'}
        ).json()

        if status['status'] == 'completed':
            return True
        elif status['status'] == 'failed':
            return False

        time.sleep(2)
```

#### After (Clean Slate)
```python
import requests

def create_batch_job(urls, use_clean_slate=True):
    response = requests.post(
        'https://api.svg2pptx.com/batch/jobs',
        headers={'Authorization': f'Bearer {TOKEN}'},
        json={
            'urls': urls,
            'use_clean_slate': use_clean_slate  # Explicit control
        }
    )
    return response.json()['job_id']

def wait_for_completion(job_id):
    import time
    while True:
        status = requests.get(
            f'https://api.svg2pptx.com/batch/jobs/{job_id}',
            headers={'Authorization': f'Bearer {TOKEN}'}
        ).json()

        # Handle new status values
        if status['status'] in ['completed', 'completed_upload_failed']:
            return True
        elif status['status'] == 'failed':
            return False

        time.sleep(2)

def get_trace_data(job_id):
    """NEW: Fetch E2E trace data"""
    response = requests.get(
        f'https://api.svg2pptx.com/batch/jobs/{job_id}/trace',
        headers={'Authorization': f'Bearer {TOKEN}'}
    )
    return response.json()

# Usage with trace
job_id = create_batch_job(['https://example.com/test.svg'])
if wait_for_completion(job_id):
    trace = get_trace_data(job_id)
    if trace['trace_available']:
        print(f"Converted {trace['page_count']} pages")
        for page in trace['trace_data']['debug_trace']:
            print(f"  Page {page['page_number']}: "
                  f"{page['pipeline_trace']['parse_result']['element_count']} elements")
```

### JavaScript/TypeScript Migration

#### Before (Legacy)
```typescript
interface BatchJobResponse {
  job_id: string;
  status: 'created' | 'processing' | 'completed' | 'failed';
}

async function createBatchJob(urls: string[]): Promise<string> {
  const response = await fetch('https://api.svg2pptx.com/batch/jobs', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${TOKEN}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ urls })
  });

  const data: BatchJobResponse = await response.json();
  return data.job_id;
}
```

#### After (Clean Slate)
```typescript
interface BatchJobResponse {
  job_id: string;
  status: 'created' | 'processing' | 'completed' | 'failed' | 'completed_upload_failed';  // NEW
}

interface TraceData {
  trace_available: boolean;
  architecture: 'clean_slate' | 'legacy';
  page_count: number;
  trace_data?: {
    debug_trace: PageTrace[];
  };
}

interface PageTrace {
  page_number: number;
  pipeline_trace: {
    parse_result: any;
    analysis_result: any;
    mapper_results: any[];
    embedder_result: any;
  };
  package_trace: {
    package_creation_ms: number;
    file_write_ms: number;
    package_size_bytes: number;
  };
}

async function createBatchJob(
  urls: string[],
  useCleanSlate: boolean = true  // Default to Clean Slate
): Promise<string> {
  const response = await fetch('https://api.svg2pptx.com/batch/jobs', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${TOKEN}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      urls,
      use_clean_slate: useCleanSlate
    })
  });

  const data: BatchJobResponse = await response.json();
  return data.job_id;
}

async function getTraceData(jobId: string): Promise<TraceData> {
  const response = await fetch(
    `https://api.svg2pptx.com/batch/jobs/${jobId}/trace`,
    {
      headers: { 'Authorization': `Bearer ${TOKEN}` }
    }
  );

  return await response.json();
}

// Usage
const jobId = await createBatchJob(['https://example.com/test.svg']);
await waitForCompletion(jobId);

const trace = await getTraceData(jobId);
if (trace.trace_available) {
  console.log(`Architecture: ${trace.architecture}`);
  console.log(`Pages: ${trace.page_count}`);

  trace.trace_data!.debug_trace.forEach(page => {
    console.log(`Page ${page.page_number}:`);
    console.log(`  Parse: ${page.pipeline_trace.parse_result.element_count} elements`);
    console.log(`  Package: ${page.package_trace.package_creation_ms.toFixed(2)}ms`);
  });
}
```

## Testing Strategy

### 1. Parallel Testing

Run both legacy and Clean Slate in parallel:
```python
# Test both workflows
urls = ['https://example.com/test.svg']

# Legacy
legacy_job = create_batch_job(urls, use_clean_slate=False)
wait_for_completion(legacy_job)
legacy_result = get_job_status(legacy_job)

# Clean Slate
clean_slate_job = create_batch_job(urls, use_clean_slate=True)
wait_for_completion(clean_slate_job)
clean_slate_result = get_job_status(clean_slate_job)
clean_slate_trace = get_trace_data(clean_slate_job)

# Compare
assert legacy_result['status'] == clean_slate_result['status']
print(f"Clean Slate trace: {clean_slate_trace['page_count']} pages")
```

### 2. Gradual Rollout

Roll out to percentage of users:
```python
import random

def create_batch_job_with_rollout(urls, rollout_percentage=10):
    # 10% of users get Clean Slate
    use_clean_slate = random.random() < (rollout_percentage / 100)

    return create_batch_job(urls, use_clean_slate=use_clean_slate)
```

### 3. Feature Flag

Use feature flag for control:
```python
class FeatureFlags:
    CLEAN_SLATE_BATCH = os.getenv('CLEAN_SLATE_BATCH', 'false') == 'true'

def create_batch_job_with_flag(urls):
    return create_batch_job(
        urls,
        use_clean_slate=FeatureFlags.CLEAN_SLATE_BATCH
    )
```

## Troubleshooting

### Issue: Different Output Quality

**Symptom**: Clean Slate output looks different

**Solution**:
1. Check preprocessing preset mapping:
   - `minimal` → `fast`
   - `default` → `balanced`
   - `aggressive` → `high`

2. Use same quality level:
```json
{
  "preprocessing_preset": "aggressive",  // Maps to quality: "high"
  "use_clean_slate": true
}
```

### Issue: Slower Performance

**Symptom**: Clean Slate takes longer

**Solution**:
1. URL download adds ~1-2 seconds overhead (one-time)
2. Trace collection adds ~5ms per page (negligible)
3. Overall difference should be minimal (<10%)

Check trace data for bottlenecks:
```python
trace = get_trace_data(job_id)
for page in trace['trace_data']['debug_trace']:
    parse_time = page['pipeline_trace']['parse_result'].get('parse_time_ms', 0)
    package_time = page['package_trace']['package_creation_ms']
    print(f"Page {page['page_number']}: Parse={parse_time}ms, Package={package_time}ms")
```

### Issue: Upload Failed Status

**Symptom**: Status is `completed_upload_failed`

**Solution**:
This is expected behavior - conversion succeeded:
```python
status = get_job_status(job_id)
if status['status'] == 'completed_upload_failed':
    # Conversion worked, upload failed
    print("Conversion output available")
    print(f"Upload error: {status.get('drive_upload_error')}")

    # Retry upload if needed
    retry_drive_upload(job_id)
```

### Issue: No Trace Data

**Symptom**: `trace_available: false`

**Causes**:
1. Job used legacy workflow (`use_clean_slate: false`)
2. Job still processing
3. Job failed before trace collection

**Solution**:
```python
trace = get_trace_data(job_id)
if not trace['trace_available']:
    job_status = get_job_status(job_id)

    if job_status['status'] in ['created', 'processing']:
        print("Job still processing, try again later")
    elif 'use_clean_slate' in job_status and not job_status['use_clean_slate']:
        print("Job used legacy workflow (no trace)")
    else:
        print("Trace data not available")
```

## Rollback Plan

If you encounter critical issues:

### Step 1: Revert to Legacy
```json
{
  "urls": ["..."],
  "use_clean_slate": false
}
```

### Step 2: Report Issue
- GitHub: https://github.com/svg2pptx/issues
- Email: support@svg2pptx.com
- Include: job_id, trace data (if available), error messages

### Step 3: Gradual Re-enable
After fix is deployed:
```python
# Start with 1% rollout
rollout_percentage = 1

def should_use_clean_slate():
    return random.random() < (rollout_percentage / 100)
```

## FAQ

**Q: Will my existing jobs continue to work?**
A: Yes, all existing API calls remain compatible.

**Q: Do I need to change my code?**
A: Not required, but recommended to use trace endpoint.

**Q: What happens to legacy workflow?**
A: Supported until Q4 2025, then removed.

**Q: Can I use both workflows?**
A: Yes, use `use_clean_slate` parameter to choose.

**Q: Is there a performance difference?**
A: Minimal (<10%), mostly from URL download overhead.

**Q: Will trace data cost more?**
A: No, trace collection is free and minimal overhead.

**Q: Can I disable tracing?**
A: No, tracing is always enabled for batch jobs (negligible impact).

**Q: What if Clean Slate doesn't support my SVG?**
A: Report the issue and use legacy as fallback temporarily.

## Support

Need help with migration?

- **Documentation**: https://docs.svg2pptx.com/migration
- **API Reference**: https://docs.svg2pptx.com/api/batch
- **GitHub**: https://github.com/svg2pptx/issues
- **Email**: support@svg2pptx.com
- **Chat**: Available in API dashboard

## Checklist

Use this checklist to track your migration:

- [ ] Read migration guide
- [ ] Test Clean Slate with sample jobs
- [ ] Compare output quality with legacy
- [ ] Verify performance is acceptable
- [ ] Update code to handle new status values
- [ ] Implement trace data fetching
- [ ] Test error scenarios
- [ ] Update monitoring/alerts for new statuses
- [ ] Roll out to 1% of users
- [ ] Monitor for issues
- [ ] Roll out to 10% of users
- [ ] Roll out to 50% of users
- [ ] Roll out to 100% of users
- [ ] Remove `use_clean_slate` parameter
- [ ] Remove legacy fallback code
- [ ] Update documentation
- [ ] Celebrate! 🎉

---

**Last Updated**: 2025-10-03
**Version**: 2.0
**Status**: Production Ready
