# E2E Testing Guide for Google Drive Integration

Comprehensive guide for end-to-end testing of SVG2PPTX batch processing with Google Drive integration.

## Overview

This guide covers testing procedures, test data requirements, and validation steps for the complete batch processing workflow including Google Drive upload and organization.

## Test Environment Setup

### Prerequisites

1. **Python Environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements-test.txt
   ```

2. **Test Dependencies:**
   ```bash
   # Core testing libraries
   pytest>=7.3.1
   pytest-asyncio>=0.21.0
   pytest-mock>=3.10.0
   pytest-cov>=4.0.0
   
   # HTTP testing
   httpx>=0.24.0
   fastapi[testing]>=0.100.0
   
   # Database testing
   sqlite3
   sqlalchemy>=1.4.0
   ```

3. **Google Drive Test Setup:**
   ```bash
   # Create test service account
   gcloud iam service-accounts create svg2pptx-e2e-test \
     --display-name="SVG2PPTX E2E Testing"
   
   # Generate test credentials
   gcloud iam service-accounts keys create test_credentials.json \
     --iam-account=svg2pptx-e2e-test@project-id.iam.gserviceaccount.com
   ```

### Environment Variables

```bash
# Test environment configuration
export TESTING=true
export TEST_DB_PATH="/tmp/test_batch_jobs.db"
export TEST_DRIVE_CREDENTIALS_PATH="./test_credentials.json"
export HUEY_IMMEDIATE=true

# Test Drive folder (isolated from production)
export TEST_DRIVE_FOLDER_PATTERN="E2E-Tests/{date}/test-{job_id}/"
export TEST_CLEANUP_AFTER_RUN=true
```

## Test Data Requirements

### SVG Test Files

Create comprehensive test SVG files in `tests/fixtures/svg/`:

**Basic Test Files:**
```
tests/fixtures/svg/
├── simple/
│   ├── basic_rectangle.svg      # Simple shapes
│   ├── basic_circle.svg
│   └── basic_text.svg
├── complex/
│   ├── nested_groups.svg        # Complex hierarchies
│   ├── gradients_filters.svg    # Advanced styling
│   └── animations.svg           # Animation elements
├── edge_cases/
│   ├── empty.svg               # Edge cases
│   ├── malformed.svg
│   └── very_large.svg
└── real_world/
    ├── logo_design.svg         # Real-world examples
    ├── technical_diagram.svg
    └── infographic.svg
```

### ZIP Test Archives

Create test ZIP files in `tests/fixtures/zip/`:

**Structured Archives:**
```
tests/fixtures/zip/
├── flat_structure.zip          # All files in root
├── nested_structure.zip        # Multi-level folders
├── mixed_content.zip           # SVG + non-SVG files
├── large_archive.zip           # 20+ files
└── empty_folders.zip           # Contains empty directories
```

**Example nested_structure.zip:**
```
nested_structure.zip
├── icons/
│   ├── ui/
│   │   ├── home.svg
│   │   └── settings.svg
│   └── social/
│       ├── facebook.svg
│       └── twitter.svg
├── diagrams/
│   ├── flowchart.svg
│   └── architecture.svg
└── assets/
    └── logo.svg
```

### Test Configuration Files

Create test configuration in `tests/fixtures/config/`:

**test_drive_config.yaml:**
```yaml
google_drive:
  credentials_path: "./test_credentials.json"
  test_mode: true
  cleanup_after_test: true
  test_folder_prefix: "E2E-Tests"
  
batch_processing:
  database_path: "/tmp/test_batch_jobs.db"
  max_test_files: 10
  test_timeout: 300

performance:
  max_parallel_uploads: 1  # Reduced for testing
  retry_attempts: 2
  timeout_seconds: 60
```

## E2E Test Suites

### Test Suite Structure

```
tests/e2e_api/
├── test_batch_drive_e2e.py           # Core E2E infrastructure
├── test_batch_multifile_drive_e2e.py # Multi-file scenarios
├── test_batch_zip_simple_e2e.py      # ZIP processing
├── test_batch_zip_structure_e2e.py   # ZIP structure preservation
├── test_batch_error_scenarios_e2e.py # Error handling
└── test_batch_performance_e2e.py     # Performance validation
```

### Running E2E Tests

**Full E2E Test Suite:**
```bash
# Run all E2E tests
PYTHONPATH=. pytest tests/e2e_api/ -v --tb=short

# Run with coverage
PYTHONPATH=. pytest tests/e2e_api/ \
  --cov=src --cov=api --cov-report=html --cov-report=term-missing

# Run specific test categories
PYTHONPATH=. pytest tests/e2e_api/test_batch_drive_e2e.py -v
```

**Integration Test Suite:**
```bash
# Database and service integration
PYTHONPATH=. pytest tests/integration/ -v

# API schema validation
PYTHONPATH=. pytest tests/integration/test_api_response_schema_compliance.py -v
```

**Performance Testing:**
```bash
# Load testing with multiple concurrent jobs
PYTHONPATH=. pytest tests/e2e_api/test_batch_performance_e2e.py \
  --benchmark-only --benchmark-sort=mean
```

## Test Scenarios

### 1. Basic Batch Processing E2E

**Test Case:** `test_basic_batch_processing_e2e`

**Scenario:**
1. Upload 3 SVG files via `/batch/convert-files`
2. Enable Drive integration with default folder pattern
3. Monitor job progress via `/batch/jobs/{job_id}`
4. Verify Drive upload via `/batch/jobs/{job_id}/drive-info`
5. Validate folder structure in Google Drive
6. Clean up test data

**Expected Results:**
- All files converted successfully
- Drive folder created with correct pattern
- All files uploaded to Drive with proper naming
- API responses match expected schema

**Code Example:**
```python
def test_basic_batch_processing_e2e(client, test_db_path):
    # Step 1: Create batch job
    files = [
        ("files", ("test1.svg", svg_content_1, "image/svg+xml")),
        ("files", ("test2.svg", svg_content_2, "image/svg+xml")),
        ("files", ("test3.svg", svg_content_3, "image/svg+xml")),
    ]
    
    data = {
        "enable_drive_integration": "true",
        "drive_folder_pattern": "E2E-Tests/{date}/basic-{job_id}/"
    }
    
    # Submit batch
    response = client.post("/batch/convert-files", files=files, data=data)
    assert response.status_code == 200
    
    job_data = response.json()
    job_id = job_data["batch_id"]
    
    # Step 2: Monitor processing
    max_wait_time = 300  # 5 minutes
    start_time = time.time()
    
    while time.time() - start_time < max_wait_time:
        status_response = client.get(f"/batch/jobs/{job_id}")
        status_data = status_response.json()
        
        if status_data["status"] == "completed":
            break
        elif status_data["status"] == "failed":
            pytest.fail(f"Job failed: {status_data}")
            
        time.sleep(5)
    
    # Step 3: Verify Drive integration
    drive_response = client.get(f"/batch/jobs/{job_id}/drive-info")
    assert drive_response.status_code == 200
    
    drive_data = drive_response.json()
    assert len(drive_data["uploaded_files"]) == 3
    assert drive_data["drive_folder_url"] is not None
```

### 2. ZIP Structure Preservation E2E

**Test Case:** `test_zip_structure_preservation_e2e`

**Scenario:**
1. Create ZIP with nested folder structure
2. Upload via `/batch/convert-zip` with `preserve_folder_structure=true`
3. Verify Drive maintains original folder hierarchy
4. Check file placement matches ZIP structure

**Validation Points:**
- Folder hierarchy preserved in Drive
- File naming consistent with original structure
- Empty folders handled appropriately
- Metadata correctly associated with files

### 3. Error Recovery E2E

**Test Case:** `test_error_recovery_e2e`

**Scenario:**
1. Submit batch with mix of valid/invalid files
2. Simulate Drive API failures
3. Test retry mechanisms
4. Verify partial success handling

**Error Scenarios:**
- Invalid SVG files
- Network timeouts during upload
- Drive API quota exceeded
- Authentication failures
- Database connection issues

### 4. Large Batch Processing E2E

**Test Case:** `test_large_batch_processing_e2e`

**Scenario:**
1. Submit maximum allowed files (50 SVG files)
2. Mix of simple and complex SVG content
3. Monitor memory usage and processing time
4. Verify all files processed within timeout

**Performance Metrics:**
- Total processing time < 30 minutes
- Memory usage < 1GB
- All files successfully converted
- Drive uploads complete within timeout

## Test Data Management

### Test Data Generation

**SVG Generator Script:**
```python
#!/usr/bin/env python3
"""Generate test SVG files for E2E testing."""

def generate_simple_svg(name: str, color: str = "blue") -> str:
    """Generate simple SVG with basic shapes."""
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="200" height="200" xmlns="http://www.w3.org/2000/svg">
    <rect x="10" y="10" width="180" height="180" 
          fill="{color}" stroke="black" stroke-width="2"/>
    <text x="100" y="110" text-anchor="middle" 
          font-family="Arial" font-size="16">{name}</text>
</svg>'''

def generate_complex_svg(name: str) -> str:
    """Generate complex SVG with gradients and groups."""
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="300" height="300" xmlns="http://www.w3.org/2000/svg">
    <defs>
        <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" style="stop-color:rgb(255,255,0);stop-opacity:1" />
            <stop offset="100%" style="stop-color:rgb(255,0,0);stop-opacity:1" />
        </linearGradient>
    </defs>
    <g id="main-group">
        <circle cx="150" cy="150" r="100" fill="url(#grad1)"/>
        <g id="text-group">
            <text x="150" y="155" text-anchor="middle" 
                  font-family="Arial" font-size="20" fill="white">{name}</text>
        </g>
    </g>
</svg>'''

# Generate test files
test_files = [
    ("simple_red.svg", generate_simple_svg("Red Test", "red")),
    ("simple_blue.svg", generate_simple_svg("Blue Test", "blue")),
    ("complex_gradient.svg", generate_complex_svg("Gradient Test")),
]

for filename, content in test_files:
    with open(f"tests/fixtures/svg/generated/{filename}", "w") as f:
        f.write(content)
```

### ZIP Archive Creation

**Archive Generator Script:**
```python
#!/usr/bin/env python3
"""Generate test ZIP archives for E2E testing."""

import zipfile
from pathlib import Path

def create_nested_structure_zip():
    """Create ZIP with nested folder structure."""
    with zipfile.ZipFile("tests/fixtures/zip/nested_structure.zip", "w") as zf:
        # Add files with directory structure
        structure = {
            "icons/ui/home.svg": generate_simple_svg("Home", "green"),
            "icons/ui/settings.svg": generate_simple_svg("Settings", "blue"),
            "icons/social/facebook.svg": generate_simple_svg("Facebook", "blue"),
            "diagrams/flowchart.svg": generate_complex_svg("Flowchart"),
            "assets/logo.svg": generate_complex_svg("Logo"),
        }
        
        for path, content in structure.items():
            zf.writestr(path, content)

def create_large_archive():
    """Create ZIP with many files for performance testing."""
    with zipfile.ZipFile("tests/fixtures/zip/large_archive.zip", "w") as zf:
        for i in range(25):
            filename = f"batch_file_{i:03d}.svg"
            content = generate_simple_svg(f"File {i}", f"hsl({i * 14}, 70%, 50%)")
            zf.writestr(filename, content)
```

### Database Test Data

**Test Database Setup:**
```python
def setup_test_database(db_path: str):
    """Set up test database with sample data."""
    from src.batch.models import init_database, BatchJob, BatchDriveMetadata
    
    # Initialize clean database
    init_database(db_path)
    
    # Create sample batch jobs for testing
    test_jobs = [
        {
            "job_id": "e2e_test_001",
            "status": "completed",
            "total_files": 3,
            "drive_integration_enabled": True,
        },
        {
            "job_id": "e2e_test_002", 
            "status": "processing",
            "total_files": 5,
            "drive_integration_enabled": False,
        }
    ]
    
    for job_data in test_jobs:
        job = BatchJob(**job_data)
        job.save(db_path)
```

## Test Validation

### Response Schema Validation

**Schema Validation Helper:**
```python
def validate_batch_job_response(response_data: dict):
    """Validate batch job API response schema."""
    required_fields = [
        "job_id", "status", "total_files", "drive_integration_enabled"
    ]
    
    for field in required_fields:
        assert field in response_data, f"Missing field: {field}"
    
    # Validate field types
    assert isinstance(response_data["job_id"], str)
    assert response_data["status"] in ["pending", "processing", "completed", "failed"]
    assert isinstance(response_data["total_files"], int)
    assert isinstance(response_data["drive_integration_enabled"], bool)

def validate_drive_info_response(response_data: dict):
    """Validate Drive info API response schema."""
    required_fields = ["drive_folder_id", "drive_folder_url", "uploaded_files"]
    
    for field in required_fields:
        assert field in response_data, f"Missing field: {field}"
    
    # Validate uploaded files structure
    for file_info in response_data["uploaded_files"]:
        file_required = ["original_filename", "drive_file_id", "drive_file_url"]
        for field in file_required:
            assert field in file_info, f"Missing file field: {field}"
```

### Performance Validation

**Performance Test Helpers:**
```python
import time
import psutil
import threading

class PerformanceMonitor:
    """Monitor system resources during E2E tests."""
    
    def __init__(self):
        self.start_time = None
        self.peak_memory = 0
        self.monitoring = False
        
    def start_monitoring(self):
        """Start performance monitoring."""
        self.start_time = time.time()
        self.monitoring = True
        self.peak_memory = 0
        
        # Start memory monitoring thread
        threading.Thread(target=self._monitor_memory, daemon=True).start()
    
    def stop_monitoring(self):
        """Stop monitoring and return results."""
        self.monitoring = False
        duration = time.time() - self.start_time
        
        return {
            "duration_seconds": duration,
            "peak_memory_mb": self.peak_memory / 1024 / 1024
        }
    
    def _monitor_memory(self):
        """Monitor memory usage in background thread."""
        while self.monitoring:
            current_memory = psutil.Process().memory_info().rss
            self.peak_memory = max(self.peak_memory, current_memory)
            time.sleep(0.1)

# Usage in tests
def test_performance_monitoring_example():
    monitor = PerformanceMonitor()
    monitor.start_monitoring()
    
    # Run E2E test
    run_batch_processing_test()
    
    results = monitor.stop_monitoring()
    
    # Assert performance requirements
    assert results["duration_seconds"] < 300  # 5 minutes max
    assert results["peak_memory_mb"] < 1024   # 1GB max memory
```

## Test Execution

### Continuous Integration

**GitHub Actions Workflow:**
```yaml
name: E2E Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  e2e-tests:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements-test.txt
    
    - name: Setup test environment
      run: |
        export TESTING=true
        export HUEY_IMMEDIATE=true
        
    - name: Run E2E tests
      run: |
        PYTHONPATH=. pytest tests/e2e_api/ \
          --cov=src --cov=api \
          --cov-report=xml \
          --junit-xml=test-results.xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

### Local Development

**Test Execution Scripts:**
```bash
#!/bin/bash
# run_e2e_tests.sh

set -e

echo "Setting up E2E test environment..."
export TESTING=true
export TEST_DB_PATH="/tmp/e2e_test_batch_jobs.db"
export HUEY_IMMEDIATE=true

echo "Cleaning up previous test data..."
rm -f /tmp/e2e_test_batch_jobs.db
rm -rf /tmp/svg2pptx_test_*

echo "Running E2E test suite..."
PYTHONPATH=. pytest tests/e2e_api/ \
  --tb=short \
  --maxfail=5 \
  -x \
  "$@"

echo "E2E tests completed successfully!"
```

### Test Reporting

**Generate Test Report:**
```bash
# Generate comprehensive test report
PYTHONPATH=. pytest tests/e2e_api/ \
  --html=reports/e2e_test_report.html \
  --self-contained-html \
  --cov=src --cov=api \
  --cov-report=html:reports/coverage_html

# View results
open reports/e2e_test_report.html
open reports/coverage_html/index.html
```

This comprehensive E2E testing guide ensures thorough validation of the Google Drive integration feature across all user scenarios and edge cases.