# Database Schema

This is the database schema implementation for the spec detailed in @.agent-os/specs/2025-09-09-unit-testing-system/spec.md

## Schema Changes

### New Tables

#### test_runs
Stores test execution history and metadata for tracking test suite performance over time.

```sql
CREATE TABLE test_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id VARCHAR(36) UNIQUE NOT NULL,
    branch VARCHAR(255) NOT NULL,
    commit_sha VARCHAR(40) NOT NULL,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    total_tests INTEGER DEFAULT 0,
    passed_tests INTEGER DEFAULT 0,
    failed_tests INTEGER DEFAULT 0,
    skipped_tests INTEGER DEFAULT 0,
    total_duration REAL DEFAULT 0.0,
    coverage_percentage REAL DEFAULT 0.0,
    status VARCHAR(20) DEFAULT 'running',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_branch_commit (branch, commit_sha),
    INDEX idx_started_at (started_at)
);
```

#### test_results
Individual test case results with detailed failure information.

```sql
CREATE TABLE test_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id VARCHAR(36) NOT NULL,
    test_name VARCHAR(500) NOT NULL,
    test_path VARCHAR(500) NOT NULL,
    module VARCHAR(255) NOT NULL,
    class_name VARCHAR(255),
    status VARCHAR(20) NOT NULL,
    duration REAL NOT NULL,
    error_message TEXT,
    stack_trace TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES test_runs(run_id) ON DELETE CASCADE,
    INDEX idx_run_test (run_id, test_name),
    INDEX idx_status (status)
);
```

#### performance_benchmarks
Performance metrics for tracking execution speed and resource usage.

```sql
CREATE TABLE performance_benchmarks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id VARCHAR(36) NOT NULL,
    benchmark_name VARCHAR(255) NOT NULL,
    module VARCHAR(255) NOT NULL,
    execution_time REAL NOT NULL,
    memory_usage INTEGER,
    cpu_usage REAL,
    operations_per_second REAL,
    percentile_95 REAL,
    percentile_99 REAL,
    min_time REAL,
    max_time REAL,
    std_deviation REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES test_runs(run_id) ON DELETE CASCADE,
    INDEX idx_benchmark_module (benchmark_name, module),
    INDEX idx_created_at (created_at)
);
```

#### visual_regression_results
Visual comparison results for SVG-to-PPTX conversion quality validation.

```sql
CREATE TABLE visual_regression_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id VARCHAR(36) NOT NULL,
    test_name VARCHAR(255) NOT NULL,
    svg_file VARCHAR(500) NOT NULL,
    baseline_image_path VARCHAR(500),
    actual_image_path VARCHAR(500),
    diff_image_path VARCHAR(500),
    similarity_score REAL NOT NULL,
    pixel_difference INTEGER,
    status VARCHAR(20) NOT NULL,
    threshold REAL DEFAULT 0.95,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES test_runs(run_id) ON DELETE CASCADE,
    INDEX idx_run_test (run_id, test_name),
    INDEX idx_status_score (status, similarity_score)
);
```

#### coverage_data
Code coverage metrics per module and file.

```sql
CREATE TABLE coverage_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id VARCHAR(36) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    module VARCHAR(255) NOT NULL,
    lines_total INTEGER NOT NULL,
    lines_covered INTEGER NOT NULL,
    lines_missed INTEGER NOT NULL,
    branches_total INTEGER DEFAULT 0,
    branches_covered INTEGER DEFAULT 0,
    branches_missed INTEGER DEFAULT 0,
    coverage_percentage REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES test_runs(run_id) ON DELETE CASCADE,
    INDEX idx_run_file (run_id, file_path),
    INDEX idx_coverage (coverage_percentage)
);
```

## Migrations

### Initial Migration
```sql
-- Migration: 001_create_testing_tables.sql
-- Description: Create tables for unit testing system

BEGIN TRANSACTION;

-- Create all tables as defined above
-- (Include all CREATE TABLE statements from above)

-- Create views for common queries
CREATE VIEW v_test_run_summary AS
SELECT 
    tr.run_id,
    tr.branch,
    tr.commit_sha,
    tr.started_at,
    tr.completed_at,
    tr.total_tests,
    tr.passed_tests,
    tr.failed_tests,
    tr.coverage_percentage,
    COUNT(DISTINCT pb.id) as benchmark_count,
    COUNT(DISTINCT vr.id) as visual_test_count
FROM test_runs tr
LEFT JOIN performance_benchmarks pb ON tr.run_id = pb.run_id
LEFT JOIN visual_regression_results vr ON tr.run_id = vr.run_id
GROUP BY tr.run_id;

COMMIT;
```

## Rationale

### Design Decisions
- **SQLite Database**: Lightweight, file-based database perfect for test data storage without external dependencies
- **UUID Run IDs**: Globally unique identifiers for test runs enable distributed testing and data merging
- **Denormalized Metrics**: Store calculated values (coverage_percentage, total_tests) for faster queries
- **Cascade Deletes**: Automatic cleanup of related data when test runs are deleted

### Performance Considerations
- **Indexes**: Strategic indexes on foreign keys, timestamps, and frequently queried columns
- **Partitioning**: Consider partitioning by created_at for large datasets (future enhancement)
- **Data Retention**: Implement automated cleanup of old test runs (>90 days) to manage database size

### Data Integrity Rules
- **Referential Integrity**: Foreign key constraints ensure data consistency
- **Status Validation**: Enum-like status fields with CHECK constraints (can be added)
- **Timestamp Management**: Automatic timestamps for audit trail
- **Unique Constraints**: Prevent duplicate test runs with same run_id