# API Specification

This is the API specification for the spec detailed in @.agent-os/specs/2025-09-09-unit-testing-system/spec.md

## Endpoints

### POST /api/v1/tests/run

**Purpose:** Trigger a test run for specific modules or the entire test suite
**Parameters:** 
- `modules` (array, optional): List of module names to test
- `markers` (array, optional): Pytest markers to filter tests (e.g., ["unit", "fast"])
- `coverage` (boolean, default: true): Enable coverage collection
- `parallel` (boolean, default: true): Enable parallel test execution
- `visual_regression` (boolean, default: false): Include visual regression tests

**Request Body:**
```json
{
  "modules": ["converters.shapes", "converters.paths"],
  "markers": ["unit"],
  "coverage": true,
  "parallel": true,
  "visual_regression": false
}
```

**Response:**
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "running",
  "started_at": "2025-09-09T10:00:00Z",
  "total_tests": 150,
  "websocket_url": "/ws/test-run/550e8400-e29b-41d4-a716-446655440000"
}
```

**Errors:** 
- 400: Invalid module names or markers
- 503: Test system unavailable

### GET /api/v1/tests/runs/{run_id}

**Purpose:** Get detailed results of a specific test run
**Parameters:** 
- `run_id` (string, required): UUID of the test run

**Response:**
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "started_at": "2025-09-09T10:00:00Z",
  "completed_at": "2025-09-09T10:05:00Z",
  "total_tests": 150,
  "passed_tests": 145,
  "failed_tests": 3,
  "skipped_tests": 2,
  "coverage_percentage": 85.5,
  "duration": 300.5,
  "failed_test_details": [
    {
      "test_name": "test_complex_path_conversion",
      "module": "converters.paths",
      "error_message": "AssertionError: Path conversion failed",
      "stack_trace": "..."
    }
  ]
}
```

**Errors:**
- 404: Test run not found

### GET /api/v1/tests/coverage/{run_id}

**Purpose:** Get code coverage report for a test run
**Parameters:**
- `run_id` (string, required): UUID of the test run
- `format` (string, optional): Report format (json, html, xml)

**Response:**
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "overall_coverage": 85.5,
  "modules": [
    {
      "module": "converters.shapes",
      "coverage": 92.3,
      "lines_total": 500,
      "lines_covered": 462,
      "lines_missed": 38,
      "uncovered_lines": [45, 67, 89]
    }
  ],
  "report_url": "/reports/coverage/550e8400-e29b-41d4-a716-446655440000.html"
}
```

**Errors:**
- 404: Coverage data not found

### POST /api/v1/tests/visual-regression

**Purpose:** Run visual regression tests for SVG conversions
**Parameters:**
- `svg_files` (array, optional): Specific SVG files to test
- `threshold` (float, default: 0.95): Similarity threshold (0-1)
- `update_baseline` (boolean, default: false): Update baseline images

**Request Body:**
```json
{
  "svg_files": ["test_shapes.svg", "test_gradients.svg"],
  "threshold": 0.95,
  "update_baseline": false
}
```

**Response:**
```json
{
  "run_id": "660e8400-e29b-41d4-a716-446655440001",
  "total_comparisons": 25,
  "passed": 23,
  "failed": 2,
  "failures": [
    {
      "svg_file": "test_gradients.svg",
      "similarity_score": 0.89,
      "threshold": 0.95,
      "diff_image_url": "/api/v1/tests/visual-regression/diff/test_gradients.png"
    }
  ]
}
```

**Errors:**
- 400: Invalid SVG files or threshold
- 404: Baseline images not found

### GET /api/v1/tests/benchmarks

**Purpose:** Get performance benchmark history and trends
**Parameters:**
- `module` (string, optional): Filter by module name
- `days` (integer, default: 30): Number of days of history
- `limit` (integer, default: 100): Maximum number of results

**Response:**
```json
{
  "benchmarks": [
    {
      "benchmark_name": "test_shape_conversion_performance",
      "module": "converters.shapes",
      "history": [
        {
          "run_id": "550e8400-e29b-41d4-a716-446655440000",
          "date": "2025-09-09",
          "execution_time": 0.045,
          "operations_per_second": 22.2,
          "memory_usage": 15360
        }
      ],
      "trend": "stable",
      "regression_detected": false
    }
  ]
}
```

**Errors:**
- 400: Invalid parameters

### WebSocket /ws/test-run/{run_id}

**Purpose:** Real-time streaming of test execution progress
**Parameters:**
- `run_id` (string, required): UUID of the test run

**Message Format:**
```json
{
  "type": "test_result",
  "data": {
    "test_name": "test_circle_conversion",
    "status": "passed",
    "duration": 0.023,
    "current_test": 45,
    "total_tests": 150
  }
}
```

**Message Types:**
- `test_result`: Individual test completion
- `coverage_update`: Coverage percentage update
- `run_complete`: Test run finished

## Controllers

### TestRunController
**Actions:**
- `create_run()`: Initialize new test run with configuration
- `execute_tests()`: Launch pytest subprocess with parameters
- `monitor_progress()`: Track test execution and update database
- `finalize_run()`: Calculate final metrics and generate reports

### CoverageController
**Actions:**
- `collect_coverage()`: Parse coverage.xml and store in database
- `generate_report()`: Create HTML/JSON coverage reports
- `check_thresholds()`: Validate coverage meets requirements
- `identify_gaps()`: Find uncovered code paths

### VisualRegressionController
**Actions:**
- `generate_images()`: Convert PPTX slides to PNG images
- `compare_images()`: Run SSIM algorithm for similarity scoring
- `update_baselines()`: Replace baseline images with new versions
- `generate_diff_report()`: Create visual diff overlays

### BenchmarkController
**Actions:**
- `collect_metrics()`: Gather performance data during test execution
- `analyze_trends()`: Statistical analysis for regression detection
- `generate_charts()`: Create performance trend visualizations
- `alert_regressions()`: Notify on significant performance drops

## Purpose

The API provides programmatic access to the unit testing system, enabling:
- **CI/CD Integration**: Automated test execution from build pipelines
- **Dashboard Creation**: Real-time test monitoring interfaces
- **Report Generation**: Custom test reports and analytics
- **Performance Tracking**: Historical benchmark analysis
- **Quality Gates**: Automated quality checks before deployment