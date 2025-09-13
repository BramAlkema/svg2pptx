# Google Drive Integration Configuration

Complete guide for configuring Google Drive integration in SVG2PPTX batch processing.

## Overview

The Google Drive integration allows automatic upload and organization of converted PowerPoint files directly to Google Drive with customizable folder structures and hierarchical organization.

## Prerequisites

### Google Cloud Setup

1. **Create Google Cloud Project:**
   ```bash
   # Using gcloud CLI
   gcloud projects create svg2pptx-drive-integration
   gcloud config set project svg2pptx-drive-integration
   ```

2. **Enable Required APIs:**
   ```bash
   # Enable Drive API
   gcloud services enable drive.googleapis.com
   
   # Enable Slides API (for preview generation)
   gcloud services enable slides.googleapis.com
   ```

3. **Create Service Account:**
   ```bash
   # Create service account
   gcloud iam service-accounts create svg2pptx-drive \
     --display-name="SVG2PPTX Drive Integration"
   
   # Generate key file
   gcloud iam service-accounts keys create credentials.json \
     --iam-account=svg2pptx-drive@svg2pptx-drive-integration.iam.gserviceaccount.com
   ```

### OAuth 2.0 Scopes

Required scopes for Drive integration:

```python
REQUIRED_SCOPES = [
    'https://www.googleapis.com/auth/drive.file',    # Upload files
    'https://www.googleapis.com/auth/drive.folder',  # Create folders
    'https://www.googleapis.com/auth/slides',        # Generate previews
]
```

## Environment Configuration

### Environment Variables

```bash
# Google Drive Authentication
GOOGLE_DRIVE_CREDENTIALS_PATH="/path/to/credentials.json"
GOOGLE_DRIVE_TOKEN_PATH="/path/to/token.json"

# Drive Integration Settings
DRIVE_INTEGRATION_ENABLED=true
DRIVE_DEFAULT_FOLDER_PATTERN="SVG2PPTX-Batches/{date}/batch-{job_id}/"
DRIVE_MAX_PARALLEL_UPLOADS=3
DRIVE_RETRY_ATTEMPTS=3
DRIVE_TIMEOUT_SECONDS=300

# Rate Limiting
DRIVE_REQUESTS_PER_SECOND=10
DRIVE_BURST_LIMIT=100

# Database Configuration
BATCH_DB_PATH="/data/batch_jobs.db"
DATABASE_POOL_SIZE=10
```

### Configuration File

Create `drive_config.yaml`:

```yaml
google_drive:
  # Authentication
  credentials_path: "/path/to/credentials.json" 
  token_path: "/path/to/token.json"
  scopes:
    - "https://www.googleapis.com/auth/drive.file"
    - "https://www.googleapis.com/auth/drive.folder"
    - "https://www.googleapis.com/auth/slides"

  # Upload Settings
  max_parallel_uploads: 3
  retry_attempts: 3
  timeout_seconds: 300
  chunk_size_mb: 8

  # Folder Organization
  default_folder_pattern: "SVG2PPTX-Batches/{date}/batch-{job_id}/"
  preserve_zip_structure: true
  create_date_folders: true

  # Rate Limiting
  requests_per_second: 10
  burst_limit: 100
  quota_project_id: "svg2pptx-drive-integration"

  # Preview Generation
  generate_previews: true
  preview_format: "png"
  preview_size: "LARGE"

batch_processing:
  # Database
  database_path: "/data/batch_jobs.db"
  connection_pool_size: 10
  
  # Huey Task Queue
  huey_config:
    name: "svg2pptx_tasks"
    results: true
    store_none: false
    immediate: false
    utc: true
```

## Folder Pattern Configuration

### Pattern Variables

Available variables for `drive_folder_pattern`:

| Variable | Description | Example |
|----------|-------------|---------|
| `{date}` | Current date (YYYY-MM-DD) | `2025-09-12` |
| `{job_id}` | Unique batch job ID | `batch-abc123` |
| `{timestamp}` | Unix timestamp | `1631456400` |
| `{user_id}` | API key user ID | `user-xyz789` |
| `{month}` | Current month (MM) | `09` |
| `{year}` | Current year (YYYY) | `2025` |

### Pattern Examples

**Date-based Organization:**
```yaml
# Organizes by year/month/day
drive_folder_pattern: "SVG-Conversions/{year}/{month}/{date}/batch-{job_id}/"

# Result: SVG-Conversions/2025/09/12/batch-abc123/
```

**Project-based Organization:**
```yaml
# Client or project-specific folders
drive_folder_pattern: "Client-Projects/{user_id}/Batch-{job_id}/"

# Result: Client-Projects/user-xyz789/Batch-abc123/
```

**Hierarchical Organization:**
```yaml
# Deep folder structure
drive_folder_pattern: "Archive/{year}/Q{quarter}/{date}/SVG-Batch-{job_id}/Conversions/"

# Custom quarter calculation required
```

### ZIP Structure Preservation

Configure how ZIP folder structures are preserved:

```yaml
zip_processing:
  preserve_structure: true
  flatten_structure: false
  max_depth: 10
  ignore_hidden_folders: true
  
  # Folder mapping rules
  folder_mappings:
    "icons": "UI-Icons"
    "images": "Graphics" 
    "diagrams": "Technical-Diagrams"
```

## Database Configuration

### SQLite Configuration

```yaml
database:
  type: "sqlite"
  path: "/data/batch_jobs.db"
  
  # Connection settings
  timeout: 30
  check_same_thread: false
  
  # Performance tuning
  pragma_settings:
    journal_mode: "WAL"
    synchronous: "NORMAL"
    cache_size: 10000
    temp_store: "MEMORY"
    
  # Backup settings
  backup:
    enabled: true
    interval_hours: 24
    retention_days: 30
    backup_path: "/backups/batch_jobs/"
```

### Connection Pooling

```python
# Database manager configuration
DATABASE_CONFIG = {
    'db_path': '/data/batch_jobs.db',
    'pool_size': 10,
    'max_connections': 20,
    'connection_timeout': 30,
    'retry_attempts': 3,
    'enable_foreign_keys': True,
    'enable_wal_mode': True
}
```

## Performance Tuning

### Upload Performance

```yaml
performance:
  # Parallel upload configuration
  max_parallel_uploads: 3
  upload_chunk_size_mb: 8
  connection_timeout: 300
  read_timeout: 300
  
  # Memory management
  max_memory_usage_mb: 512
  cleanup_temp_files: true
  temp_dir: "/tmp/svg2pptx"
  
  # Retry configuration
  retry_policy:
    max_attempts: 3
    initial_delay: 1
    backoff_multiplier: 2
    max_delay: 30
```

### Queue Configuration

```yaml
huey_config:
  # Task queue settings
  name: "svg2pptx_drive_tasks"
  results: true
  store_none: false
  immediate: false  # Set to true for testing
  
  # Redis backend (optional)
  redis_config:
    host: "localhost"
    port: 6379
    db: 0
    password: null
    
  # Worker configuration
  workers: 4
  worker_type: "thread"
  max_tasks_per_worker: 100
  
  # Task timeouts
  task_timeout: 1800  # 30 minutes
  result_ttl: 86400   # 24 hours
```

## Security Configuration

### API Key Management

```yaml
security:
  # API key validation
  api_key_length: 64
  api_key_expiry_days: 365
  require_https: true
  
  # Rate limiting per API key
  rate_limits:
    requests_per_minute: 60
    batches_per_hour: 10
    files_per_batch: 50
    
  # Google Drive security
  drive_security:
    verify_ssl: true
    token_refresh_buffer_seconds: 300
    max_token_age_hours: 24
```

### File Security

```yaml
file_security:
  # File validation
  allowed_extensions: [".svg"]
  max_file_size_mb: 50
  max_batch_size_mb: 100
  scan_for_malware: false
  
  # Upload security
  temp_file_encryption: false
  secure_delete: true
  virus_scan_uploads: false
```

## Monitoring and Logging

### Logging Configuration

```yaml
logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  
  # Log files
  file_handler:
    enabled: true
    path: "/logs/svg2pptx-drive.log"
    max_size_mb: 100
    backup_count: 5
    
  # Drive-specific logging
  drive_logging:
    log_api_calls: true
    log_upload_progress: false
    log_rate_limiting: true
    
  # Database logging
  database_logging:
    log_queries: false
    log_slow_queries: true
    slow_query_threshold_ms: 1000
```

### Metrics Collection

```yaml
metrics:
  enabled: true
  export_format: "prometheus"
  export_port: 8090
  
  # Custom metrics
  track_metrics:
    - "batch_jobs_created"
    - "drive_uploads_completed" 
    - "drive_uploads_failed"
    - "processing_time_seconds"
    - "api_requests_total"
    
  # Alerts
  alert_thresholds:
    high_error_rate: 0.05  # 5% error rate
    slow_response_time: 10  # 10 seconds
    queue_backup: 100      # 100 queued jobs
```

## Development vs Production

### Development Configuration

```yaml
# development.yaml
environment: "development"

google_drive:
  # Use test credentials
  credentials_path: "./test_credentials.json"
  
huey_config:
  # Immediate processing for testing
  immediate: true
  
logging:
  level: "DEBUG"
  
performance:
  max_parallel_uploads: 1
```

### Production Configuration

```yaml
# production.yaml
environment: "production"

google_drive:
  credentials_path: "/secure/credentials.json"
  
huey_config:
  immediate: false
  workers: 8
  
logging:
  level: "WARNING"
  
performance:
  max_parallel_uploads: 5
  
security:
  require_https: true
  rate_limits:
    requests_per_minute: 100
```

## Configuration Validation

### Validation Script

```python
#!/usr/bin/env python3
"""
Configuration validation script for Drive integration.
"""

import yaml
import json
from pathlib import Path
from typing import Dict, Any, List

def validate_drive_config(config_path: str) -> List[str]:
    """Validate Drive configuration file."""
    errors = []
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
    except Exception as e:
        errors.append(f"Failed to load config: {e}")
        return errors
    
    # Validate required sections
    required_sections = ['google_drive', 'batch_processing']
    for section in required_sections:
        if section not in config:
            errors.append(f"Missing required section: {section}")
    
    # Validate Drive configuration
    if 'google_drive' in config:
        drive_config = config['google_drive']
        
        # Check credentials path
        creds_path = drive_config.get('credentials_path')
        if not creds_path or not Path(creds_path).exists():
            errors.append(f"Credentials file not found: {creds_path}")
        
        # Validate scopes
        scopes = drive_config.get('scopes', [])
        required_scopes = [
            'https://www.googleapis.com/auth/drive.file',
            'https://www.googleapis.com/auth/drive.folder'
        ]
        for scope in required_scopes:
            if scope not in scopes:
                errors.append(f"Missing required scope: {scope}")
    
    # Validate performance settings
    if 'performance' in config:
        perf = config['performance']
        max_uploads = perf.get('max_parallel_uploads', 3)
        if max_uploads > 10:
            errors.append("max_parallel_uploads should not exceed 10")
    
    return errors

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: validate_config.py <config_file>")
        sys.exit(1)
    
    errors = validate_drive_config(sys.argv[1])
    if errors:
        print("Configuration errors found:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
    else:
        print("Configuration is valid!")
```

## Troubleshooting

### Common Issues

**Authentication Errors:**
```bash
# Check credentials file
ls -la /path/to/credentials.json

# Verify service account permissions
gcloud projects get-iam-policy svg2pptx-drive-integration

# Test authentication
python -c "
from google.oauth2 import service_account
credentials = service_account.Credentials.from_service_account_file(
    '/path/to/credentials.json',
    scopes=['https://www.googleapis.com/auth/drive.file']
)
print('Authentication successful')
"
```

**Upload Failures:**
```bash
# Check disk space
df -h /tmp

# Verify network connectivity
curl -I https://www.googleapis.com/upload/drive/v3/files

# Check API quotas
gcloud logging read "resource.type=api" --limit=50
```

**Database Issues:**
```bash
# Check database file permissions
ls -la /data/batch_jobs.db

# Test database connectivity
sqlite3 /data/batch_jobs.db ".schema"

# Check for corruption
sqlite3 /data/batch_jobs.db "PRAGMA integrity_check;"
```

### Configuration Testing

Use the provided validation script to test configuration:

```bash
# Validate configuration
python validate_config.py drive_config.yaml

# Test Drive connectivity
python -c "
from src.batch.drive_controller import BatchDriveController
controller = BatchDriveController()
print('Drive integration configured successfully')
"

# Test database setup
python -c "
from src.batch.models import init_database
init_database('/data/batch_jobs.db')
print('Database setup successful')
"
```