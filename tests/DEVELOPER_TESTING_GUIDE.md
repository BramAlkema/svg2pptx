# Developer Testing Guide

## Quick Start

### Setup
```bash
# Install development dependencies
pip install -e ".[dev]"

# Activate virtual environment
source venv/bin/activate
```

### Running Tests
```bash
# Run all tests
pytest

# Run specific category
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/

# Run with markers
pytest -m unit
pytest -m "not slow"
```

## Test Organization

Tests are organized by type:
- `unit/` - Fast, isolated component tests
- `integration/` - Component interaction tests  
- `e2e/` - Full workflow tests
- `performance/` - Benchmark and profiling tests
- `quality/` - Code quality and coverage tests

## Writing Tests

### 1. Use Centralized Fixtures
```python
from tests.fixtures import *

def test_something(sample_svg_content, mock_conversion_context):
    # Fixtures are automatically available
    pass
```

### 2. Apply Markers
```python
@pytest.mark.unit
@pytest.mark.converter
def test_converter():
    pass
```

### 3. Follow Naming Convention
Files: `test_[module]_[functionality].py`
Classes: `TestClassName`
Methods: `test_method_name`

## Common Commands

```bash
# Run with coverage
pytest --cov=src --cov=api

# Run specific file
pytest tests/unit/converters/test_rectangle_converter.py

# Run with verbose output
pytest -v

# Run parallel
pytest -n auto
```

## Resources

- [Fixture Guide](FIXTURE_AND_MARKER_GUIDE.md)
- [Testing Conventions](TESTING_CONVENTIONS.md)
- [Directory Structure](DIRECTORY_STRUCTURE.md)

## Help

For issues or questions:
- Check troubleshooting in guides
- Review existing test examples
- Open an issue in the repository