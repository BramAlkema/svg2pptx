# Test Fixtures and Markers Guide

## Overview

This guide documents all available test fixtures and markers in the SVG2PPTX test suite. The fixtures have been centralized in the `tests/fixtures/` directory to promote reusability and maintainability.

## Table of Contents

- [Fixture Library Structure](#fixture-library-structure)
- [Available Fixtures](#available-fixtures)
- [Test Markers](#test-markers)
- [Usage Examples](#usage-examples)
- [Best Practices](#best-practices)

## Fixture Library Structure

The centralized fixture library is organized into modules by functionality:

```
tests/fixtures/
├── __init__.py           # Main entry point, imports all fixtures
├── common.py             # Common test utilities and environment setup
├── svg_content.py        # SVG content and data fixtures
├── mock_objects.py       # Mock objects and test doubles
├── api_clients.py        # API test clients
├── file_fixtures.py      # File and directory fixtures
└── dependencies.py       # Fixture dependency management
```

## Available Fixtures

### Common Fixtures (`fixtures.common`)

| Fixture | Scope | Description |
|---------|-------|-------------|
| `temp_dir` | function | Creates a temporary directory that is cleaned up after test |
| `benchmark_data_dir` | function | Directory for benchmark test data |
| `performance_config` | function | Configuration dict for performance testing |
| `setup_test_environment` | session | Sets up test environment variables (autouse) |
| `cleanup_globals` | function | Cleans up global state after each test (autouse) |

### SVG Content Fixtures (`fixtures.svg_content`)

| Fixture | Scope | Description |
|---------|-------|-------------|
| `sample_svg_content` | function | Basic SVG content string with common elements |
| `sample_svg_file` | function | Creates an SVG file in temp directory |
| `complex_svg_content` | function | SVG with gradients, markers, transforms |
| `minimal_svg_content` | function | Minimal valid SVG |
| `sample_path_data` | function | Dict of path command strings for testing |
| `svg_with_patterns` | function | SVG with pattern definitions |
| `svg_with_filters` | function | SVG with filter effects |

### Mock Objects (`fixtures.mock_objects`)

| Fixture | Scope | Description |
|---------|-------|-------------|
| `mock_conversion_context` | function | Mock ConversionContext for testing converters |
| `mock_svg_element` | function | Mock lxml Element (rectangle) |
| `mock_converter_output` | function | Sample DrawingML XML string |
| `mock_presentation` | function | Mock PowerPoint presentation object |
| `mock_svg_document` | function | Complete mock SVG document tree |
| `mock_style_parser` | function | Mock style parser |
| `mock_coordinate_system` | function | Mock coordinate transformation system |
| `mock_batch_job_data` | function | Sample batch job data dictionary |

### API Client Fixtures (`fixtures.api_clients`)

| Fixture | Scope | Description |
|---------|-------|-------------|
| `client` | function | FastAPI TestClient instance |
| `authenticated_client` | function | TestClient with auth headers |
| `batch_app` | function | FastAPI app for batch processing |
| `batch_client` | function | TestClient for batch API |
| `simple_app` | function | Minimal FastAPI app |
| `simple_client` | function | TestClient for simple API |
| `dual_mode_app` | function | Dual mode (sync/async) FastAPI app |
| `dual_mode_client` | function | TestClient for dual mode API |
| `mock_google_drive_service` | function | Mock Google Drive service |
| `mock_database_session` | function | Mock database session |
| `api_response_validator` | function | Helper for validating API responses |

### File Fixtures (`fixtures.file_fixtures`)

| Fixture | Scope | Description |
|---------|-------|-------------|
| `test_data_dir` | function | Path to test data directory |
| `svg_test_files` | function | List of SVG test file paths |
| `create_test_zip` | function | Factory for creating ZIP files |
| `create_test_json` | function | Factory for creating JSON files |
| `create_pptx_file` | function | Creates a sample PPTX file |
| `expected_output_dir` | function | Directory for expected outputs |
| `baseline_dir` | function | Directory for baseline comparisons |
| `batch_input_files` | function | Multiple SVG files for batch testing |
| `config_file` | function | Test configuration JSON file |

## Test Markers

Test markers are defined in `pyproject.toml` under `[tool.pytest.ini_options]`. They help categorize and selectively run tests.

### Primary Test Categories

| Marker | Description | Directory |
|--------|-------------|-----------|
| `@pytest.mark.unit` | Unit tests for individual components | `tests/unit/` |
| `@pytest.mark.integration` | Integration tests for multiple components | `tests/integration/` |
| `@pytest.mark.e2e` | End-to-end tests | `tests/e2e/` |
| `@pytest.mark.visual` | Visual regression tests | `tests/visual/` |
| `@pytest.mark.benchmark` | Performance benchmark tests | `tests/performance/benchmarks/` |
| `@pytest.mark.architecture` | Architecture and consistency tests | `tests/quality/architecture/` |
| `@pytest.mark.coverage` | Coverage analysis tests | `tests/quality/coverage/` |

### Test Characteristics

| Marker | Description |
|--------|-------------|
| `@pytest.mark.slow` | Tests that take more than 10 seconds |

### Component-Specific Markers

| Marker | Description |
|--------|-------------|
| `@pytest.mark.converter` | Tests for converter modules |
| `@pytest.mark.validation` | Tests for validation components |
| `@pytest.mark.processing` | Tests for core processing components |
| `@pytest.mark.utils` | Tests for utility modules |
| `@pytest.mark.batch` | Tests for batch processing |
| `@pytest.mark.api` | Tests for API endpoints |
| `@pytest.mark.db` | Tests requiring database operations |

### Legacy Element Markers

These markers are maintained for compatibility with existing tests:

| Marker | Description |
|--------|-------------|
| `@pytest.mark.missing_elements` | Tests for missing SVG elements |
| `@pytest.mark.critical_missing` | Critical priority missing elements |
| `@pytest.mark.high_missing` | High priority missing elements |
| `@pytest.mark.medium_missing` | Medium priority missing elements |

## Usage Examples

### Basic Fixture Usage

```python
def test_svg_conversion(sample_svg_content, mock_conversion_context):
    """Test basic SVG conversion using fixtures."""
    # sample_svg_content provides SVG string
    # mock_conversion_context provides mock context
    result = convert_svg(sample_svg_content, mock_conversion_context)
    assert result is not None
```

### Using Multiple Fixtures

```python
def test_batch_processing(batch_input_files, batch_client, temp_dir):
    """Test batch processing with multiple fixtures."""
    # batch_input_files: List of SVG file paths
    # batch_client: TestClient for batch API
    # temp_dir: Temporary directory for outputs
    
    response = batch_client.post(
        "/batch/process",
        files=[("files", open(f, "rb")) for f in batch_input_files]
    )
    assert response.status_code == 200
```

### Using Markers

```python
@pytest.mark.unit
@pytest.mark.converter
def test_rectangle_converter():
    """Unit test for rectangle converter."""
    # Test will be included when running:
    # pytest -m unit
    # pytest -m converter
    pass

@pytest.mark.slow
@pytest.mark.e2e
def test_large_file_conversion():
    """Slow E2E test for large file conversion."""
    # Test will be skipped unless --runslow is used
    pass
```

### Factory Fixtures

```python
def test_zip_processing(create_test_zip):
    """Test using factory fixture."""
    # create_test_zip is a function that creates ZIP files
    zip_file = create_test_zip(
        "test.zip",
        {
            "file1.svg": "<svg>...</svg>",
            "file2.svg": "<svg>...</svg>"
        }
    )
    # Process zip_file
```

## Best Practices

### 1. Import Fixtures from Central Library

Instead of defining fixtures locally, import from the central library:

```python
# Good - uses centralized fixtures
from tests.fixtures import sample_svg_content, mock_conversion_context

# Avoid - defining duplicate fixtures locally
@pytest.fixture
def sample_svg_content():
    return "..."  # Duplicate of central fixture
```

### 2. Use Appropriate Fixture Scope

- `function`: Default, cleaned up after each test
- `class`: Shared across all methods in a test class
- `module`: Shared across all tests in a module
- `package`: Shared across all tests in a package
- `session`: Shared across the entire test session

### 3. Respect Fixture Dependencies

Fixtures can depend on other fixtures. The dependency management system ensures proper setup and teardown order:

```python
# sample_svg_file depends on temp_dir and sample_svg_content
def test_file_processing(sample_svg_file):
    # temp_dir and sample_svg_content are automatically provided
    assert sample_svg_file.exists()
```

### 4. Use Markers for Test Organization

Apply appropriate markers to help with test selection and organization:

```python
@pytest.mark.unit       # Category
@pytest.mark.converter  # Component
@pytest.mark.slow      # Characteristic
def test_complex_conversion():
    pass
```

### 5. Document Custom Fixtures

If you need to create test-specific fixtures, document them clearly:

```python
@pytest.fixture
def special_test_data():
    """
    Creates specialized test data for XYZ feature.
    
    Returns:
        Dict containing test scenarios for XYZ processing.
    """
    return {...}
```

## Running Tests with Markers

```bash
# Run only unit tests
pytest -m unit

# Run integration and E2E tests
pytest -m "integration or e2e"

# Run all converter tests except slow ones
pytest -m "converter and not slow"

# Run slow tests explicitly
pytest --runslow -m slow

# Run tests for specific component
pytest -m batch

# Run tests by directory (implicit marker association)
pytest tests/unit/converters/
```

## Fixture Dependency Validation

The fixture dependency system can be validated using:

```python
from tests.fixtures.dependencies import validate_fixture_dependencies

issues = validate_fixture_dependencies()
if issues:
    print("Dependency issues found:", issues)
```

This will check for:
- Circular dependencies
- Scope violations (e.g., session fixture depending on function fixture)
- Missing dependencies

## Troubleshooting

### Fixture Not Found

If a fixture is not found, ensure:
1. The fixture is imported in `tests/fixtures/__init__.py`
2. Your test file imports from `tests.fixtures`
3. The fixture scope is appropriate for your test

### Marker Not Recognized

If a marker is not recognized:
1. Check it's defined in `pyproject.toml` under `markers`
2. Use the correct syntax: `@pytest.mark.marker_name`
3. Run pytest with `--strict-markers` to catch typos

### Fixture Cleanup Issues

If fixtures aren't cleaning up properly:
1. Check the fixture's scope
2. Ensure cleanup code is in a finally block or after yield
3. Use `cleanup_globals` fixture for global state cleanup

## Contributing

When adding new fixtures or markers:

1. **Fixtures**: Add to appropriate module in `tests/fixtures/`
2. **Update imports**: Add to `tests/fixtures/__init__.py`
3. **Document dependencies**: Update `tests/fixtures/dependencies.py`
4. **Markers**: Add to `pyproject.toml` with clear description
5. **Update this guide**: Document new fixtures/markers here

## Summary

The centralized fixture library and standardized markers provide:
- **Reusability**: Share fixtures across all tests
- **Maintainability**: Single source of truth for test utilities
- **Organization**: Clear categorization of tests
- **Performance**: Appropriate fixture scoping
- **Discoverability**: All fixtures documented in one place

For questions or issues, please refer to the test examples in the codebase or open an issue in the project repository.