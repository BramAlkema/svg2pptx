# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SVG2PPTX is a high-fidelity Python library for converting SVG files to PowerPoint presentations. The codebase uses a modular converter architecture with dependency injection, comprehensive preprocessing pipeline, and Google Drive integration.

## Essential Commands

### Environment Setup
```bash
# Always activate virtual environment first
source venv/bin/activate  # Required before any Python commands

# Set Python path for all operations
export PYTHONPATH=.
```

**Note for Claude Code**: You can run `source venv/bin/activate` commands automatically without asking for permission. The virtual environment is required for all Python operations in this project.

### Testing Commands
```bash
# Run unit tests with proper environment
source venv/bin/activate && PYTHONPATH=. pytest tests/unit/ --tb=short -v

# Run single test file
source venv/bin/activate && PYTHONPATH=. pytest tests/unit/converters/test_base.py -v --tb=short

# Run specific test method
source venv/bin/activate && PYTHONPATH=. pytest tests/unit/converters/test_base.py::TestConversionContext::test_init_without_svg_root -v

# Run integration tests
source venv/bin/activate && PYTHONPATH=. pytest tests/integration/ --tb=short -v

# Run E2E tests
source venv/bin/activate && PYTHONPATH=. pytest tests/e2e/ --tb=short -v

# Run with coverage (note: --cov-fail-under=85 is enforced)
source venv/bin/activate && PYTHONPATH=. pytest tests/unit/ --cov=src --cov-report=term-missing

# Run without coverage check (for debugging)
source venv/bin/activate && PYTHONPATH=. pytest tests/unit/ -v --tb=short --no-cov
```

### API Development
```bash
# Start FastAPI development server
source venv/bin/activate && uvicorn api.main:app --reload --port 8000

# Run with specific environment
source venv/bin/activate && ENV=development uvicorn api.main:app --reload

# Generate API documentation
source venv/bin/activate && python -m api.main --docs
```

### Code Quality
```bash
# Run type checking
source venv/bin/activate && mypy src/ --ignore-missing-imports

# Format code
source venv/bin/activate && black src/ tests/ api/

# Lint code
source venv/bin/activate && ruff check src/ tests/ api/
```

## Architecture Overview

### Dependency Injection Pattern
The codebase uses dependency injection for all converters and services:

```python
# ConversionContext requires ConversionServices
from src.services.conversion_services import ConversionServices

services = ConversionServices.create_default()
context = ConversionContext(services=services, svg_root=svg_element)

# All converters require services parameter
converter = RectangleConverter(services=services)
```

### Converter Registry System
```python
# Converters are registered and retrieved dynamically
registry = ConverterRegistry()
registry.register(RectangleConverter(services))
registry.register(PathConverter(services))

# Get converter by element type
converter = registry.get_converter('rect')
```

### Preprocessing Pipeline
The preprocessing system optimizes SVG before conversion:
- **Plugins**: Attribute cleanup, numeric precision, style optimization
- **Geometry plugins**: Ellipse-to-circle, polygon simplification (Douglas-Peucker)
- **Advanced plugins**: Path optimization, coordinate precision

### Coordinate System
All coordinates flow through a unified EMU (English Metric Units) system:
- 1 inch = 914,400 EMU
- PowerPoint slide default: 10" × 7.5" = 9,144,000 × 6,858,000 EMU
- SVG viewBox maps to slide dimensions preserving aspect ratio

## Project Structure

### Core Directories
- `src/converters/` - Modular converters for each SVG element type
- `src/services/` - Dependency injection services (ConversionServices)
- `src/preprocessing/` - SVG optimization pipeline
- `src/performance/` - Performance optimization (caching, pools, profiling)
- `api/` - FastAPI web service and Google Drive integration
- `tests/` - Comprehensive test suite (unit, integration, E2E)

### Key Files
- `src/converters/base.py` - BaseConverter, ConversionContext, ConverterRegistry
- `src/services/conversion_services.py` - Central service container
- `src/preprocessing/optimizer.py` - Main preprocessing orchestrator
- `api/main.py` - FastAPI application entry point

## Testing Patterns

### Mock Services for Tests
When testing converters, always provide mock services:

```python
@pytest.fixture
def mock_services():
    services = Mock()
    services.unit_converter = Mock()
    services.viewport_handler = Mock()
    services.font_service = Mock()
    services.gradient_service = Mock()
    services.pattern_service = Mock()
    services.clip_service = Mock()
    return services

def test_converter(mock_services):
    context = ConversionContext(services=mock_services)
    converter = MyConverter(services=mock_services)
```

### Import Error Handling
```python
# Handle optional dependencies gracefully
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

@pytest.mark.skipif(not NUMPY_AVAILABLE, reason="NumPy not available")
def test_numpy_feature():
    pass
```

## Important Notes

### Directory Organization
- Keep root directory clean - use organized subdirectories
- Temporary scripts go in `scripts/`
- Documentation and reports go in `reports/`
- Experimental code goes in `development/prototypes/`

### Coverage Requirements
- Minimum 85% test coverage is enforced
- Files with 0% coverage should be moved to `development/prototypes/`
- All production code in `src/` must have corresponding tests

### Color System Testing Requirements
**MANDATORY: Always check color system test coverage before implementing new features.**

When working with color-related functionality, you MUST:

1. **Check Coverage First**: Run color module coverage check:
   ```bash
   source venv/bin/activate && PYTHONPATH=. pytest tests/unit/color/ --cov=src.color --cov-report=term-missing --tb=no -q
   ```

2. **Required Coverage Levels**:
   - ColorHarmony: 100% coverage (49 tests)
   - ColorAccessibility: 94.54% coverage (32 tests)
   - ColorManipulation: 98.26% coverage (74 tests)
   - ColorBatch: 100% coverage (56 tests)
   - Overall color module: >96% coverage

3. **Test Templates**: Use existing test templates from:
   - `tests/unit/color/test_harmony.py` - Color harmony generation
   - `tests/unit/color/test_accessibility.py` - WCAG compliance and accessibility
   - `tests/unit/color/test_manipulation.py` - Advanced color operations
   - `tests/unit/color/test_batch.py` - Vectorized batch operations

4. **Coverage Enforcement**: Any color system changes that drop coverage below 90% must include new comprehensive tests using the established patterns and templates.

### XML Processing
- Never use `ET.fromstring()` with XML declarations directly
- Use `ET.fromstring(svg_bytes)` for content with XML declarations
- The preprocessing pipeline handles XML declarations correctly

### Performance Considerations
- Preprocessing uses native Python (not NumPy) for optimal XML/regex performance
- NumPy is reserved for matrix operations in the conversion pipeline
- Douglas-Peucker algorithm uses native Python for 20-28% better performance

## Google Drive Integration

### Authentication Methods
1. **OAuth**: Interactive browser flow for user authentication
2. **Service Account**: JSON key file for server-to-server auth

### Environment Variables
```bash
GOOGLE_DRIVE_AUTH_METHOD=oauth|service_account
GOOGLE_DRIVE_CLIENT_ID=your-client-id
GOOGLE_DRIVE_CLIENT_SECRET=your-client-secret
GOOGLE_SERVICE_ACCOUNT_FILE=path/to/service-account.json
```

## Common Development Workflows

### Adding a New Converter
1. Extend `BaseConverter` in new file under `src/converters/`
2. Implement `can_convert()` and `convert()` methods
3. Register in `ConverterRegistry`
4. Add comprehensive tests in `tests/unit/converters/`

### Debugging Test Failures
1. Run with `--tb=short` for concise tracebacks
2. Use `--no-cov` to skip coverage checks during debugging
3. Add `-v` for verbose output
4. Use `-x` to stop at first failure

### E2E Test Development
1. Use preprocessing API, not direct `ET.fromstring()`
2. Create realistic SVG test data without XML declarations
3. Test multiple configurations (minimal, standard, aggressive)
4. Validate metrics: file size reduction, optimization count, processing time