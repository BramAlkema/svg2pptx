# Test Directory Structure

## Overview

This document describes the consolidated test directory structure for the SVG2PPTX project. The structure has been reorganized to improve maintainability, discoverability, and consistency.

## Current Structure

```
tests/
├── __init__.py                    # Package initialization
├── conftest.py                    # Root fixture configuration
├── fixtures/                      # Centralized fixture library
│   ├── __init__.py
│   ├── common.py                  # Common utilities and environment
│   ├── svg_content.py            # SVG content fixtures
│   ├── mock_objects.py           # Mock objects and test doubles
│   ├── api_clients.py            # API test clients
│   ├── file_fixtures.py          # File and path fixtures
│   └── dependencies.py           # Fixture dependency management
│
├── unit/                          # Unit tests
│   ├── __init__.py
│   ├── conftest.py               # Unit-specific fixtures
│   ├── batch/                    # Batch processing tests
│   │   ├── __init__.py
│   │   ├── test_api_integration.py
│   │   ├── test_celery_tasks.py
│   │   ├── test_dual_mode_functionality.py
│   │   └── test_simple_api.py
│   ├── converters/               # Converter module tests
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── test_circle_converter_enhancements.py
│   │   ├── test_ellipse_converter_enhancements.py
│   │   ├── test_font_metrics.py
│   │   ├── test_image_converter.py
│   │   ├── test_line_converter_enhancements.py
│   │   ├── test_missing_svg_elements.py
│   │   ├── test_path_generator.py
│   │   ├── test_polygon_converter_enhancements.py
│   │   ├── test_rectangle_converter_enhancements.py
│   │   ├── test_style_converter.py
│   │   └── test_text_to_path.py
│   ├── processing/               # Processing module tests
│   │   ├── __init__.py
│   │   └── test_configuration.py
│   └── validation/               # Validation module tests
│       └── __init__.py
│
├── integration/                   # Integration tests
│   ├── __init__.py
│   ├── test_api_response_schema_compliance.py
│   ├── test_converter_registry_integration.py
│   ├── test_database_transaction_integrity.py
│   ├── test_drive_service_coordination.py
│   ├── test_end_to_end_conversion.py
│   └── test_preprocessing_pipeline.py
│
├── e2e/                          # End-to-end tests
│   ├── __init__.py
│   ├── api/                      # API E2E tests
│   │   ├── __init__.py
│   │   ├── test_batch_drive_e2e.py
│   │   ├── test_batch_multifile_drive_e2e.py
│   │   ├── test_batch_zip_simple_e2e.py
│   │   ├── test_batch_zip_structure_e2e.py
│   │   ├── test_fastapi_e2e.py
│   │   ├── test_httpx_client_e2e.py
│   │   └── test_multipart_upload_e2e.py
│   ├── integration/              # Integration E2E tests
│   │   ├── __init__.py
│   │   ├── test_comprehensive_e2e.py
│   │   ├── test_converter_specific_e2e.py
│   │   └── test_core_module_e2e.py
│   ├── library/                  # Library E2E tests
│   │   ├── __init__.py
│   │   └── test_svg_test_library_e2e.py
│   └── visual/                   # Visual E2E tests
│       ├── __init__.py
│       └── test_visual_fidelity_e2e.py
│
├── performance/                   # Performance tests
│   ├── __init__.py
│   ├── benchmarks/               # Benchmark tests
│   │   ├── __init__.py
│   │   ├── test_performance_speedrun_benchmark.py
│   │   ├── test_performance_speedrun_cache.py
│   │   └── test_performance_speedrun_optimizer.py
│   └── profiling/                # Profiling tests
│       └── __init__.py
│
├── quality/                      # Code quality tests
│   ├── __init__.py
│   ├── architecture/            # Architecture tests
│   │   └── __init__.py
│   └── coverage/                # Coverage tests
│       ├── __init__.py
│       └── test_converter_module_coverage.py
│
├── visual/                       # Visual regression tests
│   ├── __init__.py
│   └── test_golden_standards_visual.py
│
├── data/                         # Test data and assets
│   ├── svg/                     # Sample SVG files
│   ├── expected/                 # Expected outputs
│   └── baselines/               # Baseline comparisons
│
└── documentation/                # Test-specific documentation
    ├── FIXTURE_AND_MARKER_GUIDE.md
    ├── TESTING_CONVENTIONS.md
    ├── DIRECTORY_STRUCTURE.md
    └── CURRENT_NAMING_AUDIT.md
```

## Directory Purposes

### `/unit`
- **Purpose**: Test individual components in isolation
- **Scope**: Single functions, classes, or modules
- **Dependencies**: Minimal, uses mocks extensively
- **Execution time**: Fast (< 1 second per test)

### `/integration`
- **Purpose**: Test interaction between multiple components
- **Scope**: Component interfaces, data flow, coordination
- **Dependencies**: May use real implementations
- **Execution time**: Moderate (1-5 seconds per test)

### `/e2e`
- **Purpose**: Test complete user workflows
- **Scope**: Full application stack
- **Dependencies**: Requires full environment
- **Execution time**: Slower (5+ seconds per test)

### `/performance`
- **Purpose**: Test performance characteristics
- **Scope**: Benchmarks, load testing, profiling
- **Dependencies**: Specific to performance metrics
- **Execution time**: Variable, often longer

### `/quality`
- **Purpose**: Test code quality metrics
- **Scope**: Architecture compliance, coverage analysis
- **Dependencies**: Static analysis tools
- **Execution time**: Moderate to long

### `/visual`
- **Purpose**: Visual regression testing
- **Scope**: Output comparison, rendering accuracy
- **Dependencies**: Baseline images/outputs
- **Execution time**: Moderate

### `/fixtures`
- **Purpose**: Centralized test fixtures
- **Scope**: Shared across all test types
- **Dependencies**: Managed dependency graph
- **Usage**: Import via `from tests.fixtures import *`

### `/data`
- **Purpose**: Test data and assets
- **Scope**: Static test files, expected outputs
- **Dependencies**: None
- **Usage**: Referenced by fixtures and tests

## Migration History

### Before Consolidation
- 91 test files scattered across multiple locations
- 36 files at root level
- Inconsistent naming conventions
- Duplicate fixtures in multiple files
- Configuration spread across pytest.ini, setup.cfg, pyproject.toml

### After Consolidation
- Organized into logical directories by test type
- 40 files migrated to appropriate subdirectories
- 37 `__init__.py` files added for proper packaging
- Centralized fixture library with 50+ reusable fixtures
- Single configuration source in pyproject.toml

### Migration Statistics
- **Files moved**: 40
- **Files renamed**: 15
- **Fixtures consolidated**: 12 duplicates removed
- **Markers standardized**: 17 markers defined
- **Coverage improved**: From scattered to systematic

## File Naming Conventions

### Standard Pattern
```
test_[module]_[functionality].py
```

### Examples
- `test_rectangle_converter_enhancements.py` - Rectangle converter enhancements
- `test_batch_drive_e2e.py` - Batch Drive integration E2E
- `test_performance_speedrun_benchmark.py` - Performance speedrun benchmarks

### Special Cases
- `conftest.py` - Pytest configuration and fixtures
- `__init__.py` - Python package markers

## Test Discovery

### Pytest Configuration
Tests are discovered using patterns defined in `pyproject.toml`:
```toml
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
```

### Running Specific Test Categories
```bash
# Run all unit tests
pytest tests/unit/

# Run converter tests only
pytest tests/unit/converters/

# Run integration tests
pytest tests/integration/

# Run E2E tests
pytest tests/e2e/

# Run performance benchmarks
pytest tests/performance/benchmarks/
```

## Best Practices

### 1. Test Placement
- Place tests in the directory matching their type (unit, integration, e2e)
- Group related tests in subdirectories
- Keep test files close to their logical grouping

### 2. Fixture Usage
- Import fixtures from centralized library
- Don't duplicate fixtures locally
- Document custom fixtures if needed

### 3. Test Organization
- One test class per major functionality
- Group related test methods in the same class
- Use descriptive test names

### 4. Dependencies
- Unit tests: Use mocks, avoid real dependencies
- Integration tests: Use real components when testing interactions
- E2E tests: Use full application stack

### 5. Performance
- Keep unit tests fast (< 1 second)
- Mark slow tests with `@pytest.mark.slow`
- Use appropriate fixtures scope to optimize setup/teardown

## Adding New Tests

### 1. Determine Test Type
- Is it testing a single component? → `/unit`
- Is it testing component interaction? → `/integration`
- Is it testing a complete workflow? → `/e2e`
- Is it measuring performance? → `/performance`

### 2. Create Test File
```python
# tests/unit/new_module/test_new_functionality.py
"""Tests for new functionality."""

import pytest
from tests.fixtures import *  # Import centralized fixtures

class TestNewFunctionality:
    """Test suite for new functionality."""
    
    @pytest.mark.unit
    def test_basic_operation(self):
        """Test basic operation."""
        pass
```

### 3. Add Markers
Apply appropriate markers for test categorization:
- `@pytest.mark.unit`
- `@pytest.mark.integration`
- `@pytest.mark.e2e`
- Component-specific markers

### 4. Update Documentation
- Add to this document if creating new directories
- Update fixture guide if adding fixtures
- Document in TESTING_CONVENTIONS.md if establishing new patterns

## Maintenance

### Regular Tasks
1. Run `pytest --collect-only` to verify test discovery
2. Check for duplicate fixtures periodically
3. Update directory structure documentation when adding categories
4. Maintain consistent naming conventions

### Cleanup
1. Remove obsolete tests
2. Consolidate similar test files
3. Update imports after refactoring
4. Keep fixture library organized

## Troubleshooting

### Test Not Found
- Check file naming (must start with `test_`)
- Verify `__init__.py` exists in parent directories
- Check `testpaths` in pyproject.toml

### Import Errors
- Ensure `__init__.py` files are present
- Check Python path includes project root
- Verify fixture imports from `tests.fixtures`

### Fixture Issues
- Check fixture is defined in centralized library
- Verify fixture scope is appropriate
- Check dependency chain in fixtures/dependencies.py

## Future Improvements

### Planned
- [ ] Add mutation testing directory
- [ ] Create security testing category
- [ ] Add contract testing for APIs
- [ ] Implement property-based testing

### Under Consideration
- Separate directories for different SVG element tests
- Performance regression tracking
- Automated test generation for new converters
- Visual diff reporting system

## Summary

The consolidated test directory structure provides:
- **Organization**: Clear categorization by test type
- **Discoverability**: Easy to find and run specific tests
- **Maintainability**: Centralized fixtures and configuration
- **Scalability**: Room for growth with clear patterns
- **Consistency**: Standardized naming and structure

This structure supports efficient test development, execution, and maintenance while providing clear guidelines for contributors.